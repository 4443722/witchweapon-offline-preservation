"""Patch only unresolved expressions and one PC-authored black-background passage."""
from pathlib import Path
import os,sys,json,zipfile,hashlib,difflib,collections,copy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/python'))
import UnityPy
from pc_exact_alignment import pc_dialogs
from pc_story_match import norm
SOURCE=Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk'))

def write_graph(z,file,graph):
    name='assets/assetbundle/assets/resources/guide/lesson/lesson'+file+'.ab';env=UnityPy.load(z.read(name))
    for o in env.objects:
        if o.type.name=='MonoBehaviour':
            t=o.read_typetree()
            if '_serializedGraph' in t:t['_serializedGraph']=json.dumps(graph,ensure_ascii=False,separators=(',',':'));o.save_typetree(t)
    data=env.file.save(packer='original');target=ROOT/'overrides'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    return dict(bundle=name,sha256=hashlib.sha256(data).hexdigest())

def main():
    roles={x['role']:x for x in json.loads((ROOT/'evidence/pc_restored_roles.json').read_text('utf8'))['assets']};G=json.loads((ROOT/'evidence/original_lesson_graphs.json').read_text('utf8'));S=json.loads((ROOT/'evidence/original_sentence_tables.json').read_text('utf8'));M=json.loads((ROOT/'evidence/pc_content_matches.json').read_text('utf8'))['lessons'];E=json.loads((ROOT/'evidence/pc_role_mapping_evidence.json').read_text('utf8'));A=json.loads((ROOT/'evidence/pc_exact_alignment.json').read_text('utf8'))['observations'];I=json.loads((ROOT/'evidence/story_inventory.json').read_text('utf8'))
    exact={(o['file'],o['sentence'],o['role']):o for o in A};patches=[];graphs={};assets=[];failures=[];exclusions={}
    with zipfile.ZipFile(SOURCE) as z:
        for entry in I:
            if entry['visible']!='1' or entry['group'] in ['6030005','6030006']:continue
            f=entry['file'];g=copy.deepcopy(G.get('lesson'+f));match=M.get(f,{}).get('candidates',[])
            if not g or not match:continue
            pc=pc_dialogs(ROOT/'pc_story_source'/match[0]['path'],E['characters']);table={int(r[0])-1:r[2] for r in S.get('sentence_'+f,[]) if len(r)>2 and r[0].isdigit()};claim=g['derivedData']['claimInfo']['role'];changed=False
            for n in g['nodes']:
                for v in n.get('_roundInfo',{}).values():
                    if not isinstance(v,dict):continue
                    for a in v.get('actions',[]):
                        if a.get('_isDisabled') or not a.get('$type','').endswith('C_roleSpeak'):continue
                        sn=claim[a.get('_roleIdx',0)].get('roleSN');role=roles.get(sn);face=a.get('faceStr','')
                        if not role or not role['has_faces'] or not face or face in role['faces']:continue
                        idx=a.get('sentenceIdx');exp=None;basis=None;o=exact.get((f,idx,sn));char=role['character']
                        if o and o['character']==char:exp=o['expression'];basis='exact ordered dialogue alignment'
                        if not exp:
                            text=norm(table.get(idx,a.get('wordStr','')));candidates=[]
                            for d in pc:
                                score=1 if text==d['norm'] else difflib.SequenceMatcher(None,text,d['norm']).ratio() if len(text)>=8 else 0
                                if score<.95:continue
                                for ch,ex in d['state']:
                                    if ch==char:candidates.append((score,ex))
                            if candidates:
                                score=max(c[0] for c in candidates);choices={e for s,e in candidates if s==score}
                                if len(choices)==1:exp=next(iter(choices));basis='unique same-character PC dialogue state'
                        if not exp:
                            votes={k:v for k,v in E['face_votes'].get(sn+'_'+face,{}).items() if k.startswith(char+':')}
                            if len(votes)==1:exp=next(iter(votes)).split(':',1)[1];basis='unanimous matched-dialogue observation'
                        key='pc_'+str(exp)
                        if exp and key in role['faces']:
                            a['faceStr']=key;changed=True;patches.append(dict(file=f,sentence=idx,role=sn,old_face=face,new_face=key,basis=basis))
                        else:failures.append(dict(file=f,sentence=idx,role=sn,face=face))
            if f=='30313':
                # EXE explicitly hides the background during this exact passage; it has no Haredi picture.
                active=False
                for n in g['nodes']:
                    for section in ['_b4cmdActionList','_a4cmdActionList']:
                        v=n.get('_roundInfo',{}).get(section,{})
                        for a in v.get('actions',[]):
                            if str(a.get('picName','')).lower()=='bg_stardust_haredi':a['_isDisabled']=True;active=True;changed=True
                            elif active and a.get('$type','').endswith('HideColor'):a['_isDisabled']=True;active=False
                exclusions[f]=['/assets/resources/ui/uiimage/guide/bg_stardust_haredi.ab']
                patches.append(dict(file=f,basis='PC source hides background at the Haredi demonstration passage',change='retain existing C-layer black fill instead of requesting missing Haredi image'))
            if changed:graphs['lesson'+f]=g;assets.append(write_graph(z,f,g))
    result=dict(assets=assets,patches=patches,graphs=graphs,excluded_dependencies=exclusions,unresolved=failures)
    (ROOT/'evidence/pc_graph_repairs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8');print('Patched graphs',len(graphs),'changes',len(patches),'unresolved',failures)
if __name__=='__main__':main()
