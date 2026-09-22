"""Audit original story assets and prepare strictly complete offline story entries."""
from pathlib import Path
import os,csv,io,json,zipfile,hashlib
from offline_seed import ROOT,table,proto
SOURCE=Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk'))

def audit():
    with zipfile.ZipFile(SOURCE) as z:names=set(z.namelist())
    recovery=ROOT/'evidence/pc_story_restored_assets.json'
    recovered=set()
    restored_roles={}
    if recovery.exists():
        for asset in json.loads(recovery.read_text('utf8'))['assets']:
            file=ROOT/'overrides'/asset['bundle']
            assert file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==asset['sha256']
            assert asset['pixel_roundtrip_exact']
            recovered.add(asset['bundle'])
            if asset.get('reconstructed_ngui'):restored_roles[asset['role']]=asset
    graphs=json.loads((ROOT/'evidence/original_lesson_graphs.json').read_text('utf8')) if restored_roles else {}
    exclusions={};converted={}
    for filename in ['pc_graph_repairs.json','pc_converted_lessons.json']:
        path=ROOT/'evidence'/filename
        if not path.exists():continue
        data=json.loads(path.read_text('utf8'))
        for asset in data['assets']:
            file=ROOT/'overrides'/asset['bundle']
            assert file.exists() and hashlib.sha256(file.read_bytes()).hexdigest()==asset['sha256']
            recovered.add(asset['bundle'])
        graphs.update(data.get('graphs',{}));exclusions.update(data.get('excluded_dependencies',{}));converted.update(data.get('lessons',{}))
    builtin={x[0] for x in json.loads((ROOT/'evidence/resources_index.json').read_text('utf8'))['m_Container']}
    cuts={}
    for r in list(csv.DictReader((ROOT/'decoded/config/clientexel/AssetsCutInfo.csv').open(encoding='utf-8-sig')))[2:]:
        if r.get('key'):cuts.setdefault(r['key'],[]).append(r)
    rows={r['ID']:r for r in table('Story') if r['channel_group'] in ('','0','25')}
    titles={r['ID']:r['content_chinese'] for r in list(csv.DictReader((ROOT/'decoded/config/clientexel/Dictionary.txt').open(encoding='utf-8-sig'),delimiter='\t'))[2:]}
    result=[]
    for sid,r in rows.items():
        f=r['file'];lesson=f'assets/assetbundle/assets/resources/guide/lesson/lesson{f}.ab';text=f'assets/assetbundle/config/lesson/sentence_{f}.ab'
        if f in converted:
            r=dict(r,isWrite='1');rows[sid]=r
        missing=[x['path'] for x in cuts.get(f,[]) if x['path'] not in exclusions.get(f,[]) and 'assets/assetbundle'+x['path'] not in names|recovered and x['path'].removeprefix('/assets/resources/').removesuffix('.ab') not in builtin]
        for dependency in converted.get(f,{}).get('dependencies',[]):
            if dependency not in names|recovered and dependency.removeprefix('assets/assetbundle/assets/resources/').removesuffix('.ab') not in builtin:missing.append(dependency)
        missing_faces=[]
        graph=graphs.get('lesson'+f,{})
        roles=graph.get('derivedData',{}).get('claimInfo',{}).get('role',[])
        for node in graph.get('nodes',[]):
            for commands in node.get('_roundInfo',{}).values():
                if not isinstance(commands,dict):continue
                for action in commands.get('actions',[]):
                    if action.get('_isDisabled') or not action.get('$type','').endswith('C_roleSpeak'):continue
                    idx=action.get('_roleIdx',0);face=action.get('faceStr','')
                    if idx>=len(roles):continue
                    sn=roles[idx].get('roleSN');asset=restored_roles.get(sn)
                    if asset and asset['has_faces'] and face and face not in asset['faces']:
                        missing_faces.append(sn+':'+face)
        missing_faces=sorted(set(missing_faces))
        okay=lesson in names|recovered and text in names|recovered and not missing and not missing_faces and r['isWrite']=='1'
        result.append(dict(id=sid,title=titles.get(r['name'],sid),name_id=r['name'],group=r['story_group'],file=f,visible=r['can_see'],written=r['isWrite'],lesson_present=lesson in names|recovered,text_present=text in names|recovered,missing_dependencies=missing,missing_expressions=missing_faces,playable=okay))
    (ROOT/'evidence/story_inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    return result,rows

def prepare():
    import UnityPy
    entries,rows=audit();available={x['id'] for x in entries if x['playable']}
    visible_count=sum(x['playable'] and x['visible']=='1' for x in entries)
    groups={}
    for sid,r in rows.items():
        group=groups.setdefault(int(r['story_group']),dict(Unlock=True,SequenceStory=[],SeparatedStory={}))
        node=dict(StoryID=int(sid),Unlock=sid in available,CanUnlock=sid in available)
        if int(r['serial'] or 0):group['SequenceStory'].append(node)
        else:group['SeparatedStory'][int(sid)]=node
    for group in groups.values():group['SequenceStory'].sort(key=lambda n:int(rows[str(n['StoryID'])]['serial']))
    responses=json.loads((ROOT/'offline_responses.json').read_text('utf8'))
    responses['/story/get']=proto('storymod.Story',StoryGroup=groups,Version=5)
    (ROOT/'offline_responses.json').write_text(json.dumps(responses,ensure_ascii=False,indent=2),'utf8')
    unavailable_names={x['name_id'] for x in entries if not x['playable']}
    for filename in ['dictionary','dictionarystatic']:
        name=f'assets/assetbundle/config/clientexel/{filename}.ab'
        env=UnityPy.load(str(ROOT/'original_parts'/name))
        changed=0
        for obj in env.objects:
            if obj.type.name!='MonoBehaviour':continue
            tree=obj.read_typetree()
            if 'bytes' not in tree:continue
            raw=bytes(tree['bytes']);decoded=bytes(b^255 for b in raw) if tree.get('isEncrypt') else raw
            records=list(csv.reader(io.StringIO(decoded.decode('utf-8-sig')),delimiter='\t'))
            for r in records[3:]:
                if filename=='dictionary' and r and r[0] in unavailable_names:
                    r[1]='【缺原版资源】'+r[1];changed+=1
                if filename=='dictionarystatic' and r and r[0]=='UISTORY_HELP':
                    r[1]=f'离线剧情说明\\n共 {visible_count} 篇剧情已免费开放，可反复观看，无等级、剧情券或时间限制。\\n已从电脑剧情程序补回背景、人物立绘和表情，使用原游戏播放器，缺失篇章已按电脑程序补回。\\n其他剧情仍缺原版剧本或演出资源，已标为【缺原版资源】并锁定。';changed+=1
            buf=io.StringIO();csv.writer(buf,delimiter='\t',lineterminator='\r\n').writerows(records)
            out=('\ufeff'+buf.getvalue()).encode('utf8')
            tree['bytes']=list(bytes(b^255 for b in out) if tree.get('isEncrypt') else out)
            obj.save_typetree(tree)
        assert changed>0,(filename,changed)
        dest=ROOT/'overrides'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(env.file.save(packer='original'))
    print('Story originals available:',len(available),'/',len(entries))

if __name__=='__main__':
    entries,_=audit();print('Complete original stories:',[(x['id'],x['title']) for x in entries if x['playable']])
