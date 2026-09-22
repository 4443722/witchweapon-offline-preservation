"""Read-only scan of packaged lessons for the asynchronous role-out/reentry race."""
from pathlib import Path
import sys,json,zipfile,collections,copy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/python'))
import UnityPy

def scan(name,g):
    roles=g.get('derivedData',{}).get('claimInfo',{}).get('role',[])
    def role(a,key):
        i=a.get(key,0 if key=='_roleIdx' else -1)
        return str(roles[i].get('roleSN')) if 0<=i<len(roles) else None
    nodes={str(n['$id']):n for n in g.get('nodes',[]) if '$id' in n}
    edges=collections.defaultdict(list)
    for e in g.get('connections',[]):
        if not e.get('_isDisabled'):edges[str(e['_sourceNode']['$ref'])].append(str(e['_targetNode']['$ref']))
    streams={};parallel=[]
    for nid,n in nodes.items():
        ri=n.get('_roundInfo',{});stream=[]
        for key in ['_b4cmdActionList','_a4cmdActionList']:
            if key=='_a4cmdActionList' and ri.get('execMode') not in ('onlyCMDList','skipUserAction'):
                stream.append({'$type':'USER_WAIT'})
            task=ri.get(key,{})
            if task.get('executionMode') in ('ActionsRunInParallel',1):parallel.append(nid+':'+key)
            for i,a in enumerate(task.get('actions',[])):
                if not a.get('_isDisabled'):stream.append(dict(a,location=f'{nid}:{key}:{i}'))
        streams[nid]=stream
    # Only reachable graph nodes are executable; follow all branches conservatively.
    todo=[str(g.get('primeNode',{}).get('$ref',''))];reachable=set()
    while todo:
        nid=todo.pop()
        if nid in reachable or nid not in nodes:continue
        reachable.add(nid);todo.extend(edges[nid])
    found=[];exits=0
    for nid in reachable:
        for i,a in enumerate(streams[nid]):
            if not a.get('$type','').endswith('.C_roleOut'):continue
            sn=role(a,'roleIdx');exits+=1
            if sn is None:continue
            queue=[(nid,i+1,0.,0)];seen=set()
            while queue:
                nn,ii,delay,waits=queue.pop()
                marker=(nn,ii,round(delay,4),waits)
                if marker in seen:continue
                seen.add(marker)
                if delay>=0.5 or waits>1:continue
                if ii>=len(streams[nn]):
                    queue.extend((dst,0,delay,waits) for dst in edges[nn] if dst in streams);continue
                b=streams[nn][ii];typ=b.get('$type','').split('.')[-1]
                if typ in ('C_end','C_Begin','EndLesson'):continue
                if typ=='USER_WAIT':waits+=1
                if typ=='DelayTime':delay+=float(b.get('delaytime',0))
                if typ=='C_roleSpeak' and role(b,'_roleIdx')==sn:
                    if delay<0.5 and waits<=1:
                        found.append(dict(lesson=name,role=sn,exit=a['location'],reentry=b['location'],sentence_index=b.get('sentenceIdx'),word=b.get('wordStr',''),explicit_delay=delay,user_waits=waits,category='automatic' if waits==0 else 'requires_fast_next'))
                    continue
                queue.append((nn,ii+1,delay,waits))
    return dict(nodes=len(nodes),reachable_nodes=len(reachable),exits=exits,parallel_lists=parallel,candidates=found)

def main():
    graphs={}
    with zipfile.ZipFile(ROOT/'build/witchweapon-stage1-test.apk') as z:
        for path in z.namelist():
            if not(path.startswith('assets/assetbundle/assets/resources/guide/lesson/lesson') and path.endswith('.ab')):continue
            env=UnityPy.load(z.read(path))
            for obj in env.objects:
                if obj.type.name=='MonoBehaviour':
                    t=obj.read_typetree()
                    if t.get('_serializedGraph'):graphs[Path(path).stem]=json.loads(t['_serializedGraph'],strict=False)
    results={k:scan(k,g) for k,g in graphs.items()}
    inventory=json.loads((ROOT/'evidence/story_inventory.json').read_text('utf8'))
    entries=[]
    for r in inventory:
        scan_result=results.get('lesson'+r['file'])
        entries.append(dict(r,scan=scan_result))
    # Counterfactual regression check: remove only the delays introduced by this fix.
    before=copy.deepcopy(graphs['lesson303190']);removed=0
    for n in before['nodes']:
        a=n['_roundInfo']['_b4cmdActionList']['actions'];keep=[]
        for i,x in enumerate(a):
            if i and a[i-1]['$type'].endswith('.C_roleOut') and x['$type'].endswith('.DelayTime') and x.get('delaytime')==0.5:removed+=1
            else:keep.append(x)
        n['_roundInfo']['_b4cmdActionList']['actions']=keep
    before_scan=scan('lesson303190_before_fix',before)
    output=dict(packaged_graphs=len(graphs),results=results,entries=entries,before_fix_star19=before_scan,removed_fix_delays=removed)
    (ROOT/'evidence/role_reentry_audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),'utf8')
    for category in ['automatic','requires_fast_next']:
        hits=[(k,[c for c in r['candidates'] if c['category']==category]) for k,r in results.items()]
        hits=[(k,c) for k,c in hits if c]
        print(category,'graphs',len(hits),'locations',sum(len(c) for k,c in hits))
        print([(k,len(c)) for k,c in hits])
    print('Before fix',collections.Counter(c['category'] for c in before_scan['candidates']))
    print('Parallel lists',[(k,r['parallel_lists']) for k,r in results.items() if r['parallel_lists']])
    print('Packaged graphs',len(graphs),'visible playable entries',sum(r['visible']=='1' and r['playable'] for r in inventory))

if __name__=='__main__':main()
