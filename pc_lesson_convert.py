"""Convert an EXE-authored linear episode to native Android GuideLessonTree commands."""
from pathlib import Path
import os,sys,json,re,hashlib,zipfile,collections,copy,csv,io
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/python'))
import UnityPy
from pc_script_inspect import read_script
from pc_story_match import strings,norm
from pc_role_restore import build_role
from offline_seed import table
SOURCE=Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk'))
T='NodeCanvas.Tasks.Actions.'
def command(kind,**kwargs):return dict(kwargs,**{'$type':T+kind})

def save_bundle(z,old,new,transform):
    env=UnityPy.load(z.read(old));oldstem=Path(old).stem;newstem=Path(new).stem
    for o in env.objects:
        t=o.read_typetree()
        if o.type.name=='MonoBehaviour':t=transform(t);t['m_Name']=newstem
        elif o.type.name=='AssetBundle':
            for key in ['m_Name','m_AssetBundleName']:t[key]=t[key].replace(oldstem,newstem)
            t['m_Container']=[(k.replace(oldstem,newstem),v) for k,v in t['m_Container']]
        o.save_typetree(t)
    key=next(iter(env.file.files));env.file.files['CAB-'+hashlib.md5(new.encode()).hexdigest()]=env.file.files.pop(key)
    blob=env.file.save(packer='original');target=ROOT/'overrides'/new;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
    return dict(bundle=new,sha256=hashlib.sha256(blob).hexdigest())

def main():
    file='303190';path=ROOT/'pc_story_source/scripts/story/stardustdescends/stardustdescends_ep19.gdc'
    text,_,_=read_script(path);E=json.loads((ROOT/'evidence/pc_role_mapping_evidence.json').read_text('utf8'));characters=E['characters'];manifest=json.loads((ROOT/'evidence/pc_restored_roles.json').read_text('utf8'));role_assets={x['character']:x for x in manifest['assets']};extras=[]
    with zipfile.ZipFile(SOURCE) as z:
        # A distinct sunglasses portrait is used by this episode; do not substitute the ordinary face.
        char='akikounglass';extra=build_role('9001',char,{},characters[char],z.read('assets/assetbundle/assets/resources/ui/prefab/guide/role01.ab'));extras.append(extra);role_assets[char]=extra
        usedchars=sorted(set(re.findall(r'show_(?:2nd_|3rd_)?character PARENTHESIS_OPEN "([^"\n]+)"',text)))
        assert all(ch in role_assets for ch in usedchars)
        claim=[dict(roleSN=role_assets[ch]['role'],name=characters[ch]['display_name']) for ch in usedchars];indices={ch:i for i,ch in enumerate(usedchars)}
        observed=json.loads((ROOT/'evidence/pc_exact_alignment.json').read_text('utf8'))['asset_observations'];votes=collections.defaultdict(collections.Counter)
        for x in observed:
            if x['pc_music'] and x['original_music']:votes[x['pc_music']][x['original_music']]+=1
        music={p:max(v,key=v.get) for p,v in votes.items()};soundrows={r['ID']:r for r in table('Sound')};music_used={}
        bgmapping=json.loads((ROOT/'pc_background_mapping.json').read_text('utf8'));bgreverse={'res://assets/images/bg/'+v+'.png':k for k,v in bgmapping.items()}
        known=set(z.namelist())|{p.relative_to(ROOT/'overrides').as_posix() for p in (ROOT/'overrides/assets/assetbundle').rglob('*.ab')};builtin={x[0] for x in json.loads((ROOT/'evidence/resources_index.json').read_text('utf8'))['m_Container']}
        def background(path):
            dest=bgreverse.get(path,Path(path).stem.lower());bundle='assets/assetbundle/assets/resources/ui/uiimage/guide/'+dest+'.ab'
            assert bundle in known or 'ui/uiimage/guide/'+dest in builtin,(path,bundle)
            return dest
        nodes=[];state={};materialized=set();pending=[command('C_Begin')];lines=[];active=0;bg_black=False;first_music=None;methods=collections.Counter();dependencies=set()
        def emit(actions,after=None,control=False):
            # C_roleOut finishes its task immediately, but StoryRole.Disappear
            # removes the dictionary entry only after its queued animation.
            # Godot's awaited hide must therefore remain a synchronization point.
            actions=[step for action in actions for step in
                     ([action,command('DelayTime',delaytime=0.5)]
                      if action['$type']==T+'C_roleOut' else [action])]
            roundinfo={'_b4cmdActionList':{'actions':actions},'_a4cmdActionList':{'actions':after or []}}
            if control:roundinfo.update(execMode='onlyCMDList',evtType='none',triggerType='Empty')
            nodes.append({'_roundInfo':roundinfo,'_position':{'x':3000.0,'y':float(len(nodes)*80)},'$type':'NodeCanvas.GuideLessonTrees.GuideRoundNode','$id':str(len(nodes)+1)})
        def role_speak(ch,expression,word,index,spname):
            role=role_assets[ch];face='pc_'+expression if role['has_faces'] else ''
            if face:assert face in role['faces'],(ch,face)
            return command('C_roleSpeak',enableSentenceMapping=index>=0,_roleIdx=indices[ch],faceStr=face,wordStr=word,sentenceIdx=index,spRoleName=spname)
        def hide(slot):
            item=state.pop(slot,None)
            if item and item[0] in materialized:pending.append(command('C_roleOut',roleIdx=indices[item[0]]));materialized.discard(item[0])
        for raw in text.splitlines():
            m=re.search(r'novel_interface PERIOD (\w+) PARENTHESIS_OPEN',raw)
            if not m:continue
            method=m[1];methods[method]+=1;args=strings(raw);slot=2 if '3rd' in method else 1 if '2nd' in method else 0
            if method=='change_music':
                snd=music[args[0]];music_used[args[0]]=dict(id=snd,resource=soundrows[snd]['sound_name'],evidence_votes=dict(votes[args[0]]));pending.append(command('PlayBGM',sndID=int(snd)));first_music=first_music or snd
            elif method=='stop_music':pending.append(command('StopBGM'))
            elif method in ['change_background','show_background']:
                bg=background(args[0]);dependencies.add('assets/assetbundle/assets/resources/ui/uiimage/guide/'+bg+'.ab');pending.append(command('C_changeBG',picName=bg))
                if bg_black:pending.append(command('HideColor',layerType='C'));bg_black=False
            elif method in ['hide_background','hide_background_with_fade']:
                pending.append(command('FillColor',layerType='C'));bg_black=True
            elif method in ['show_character','show_2nd_character','show_3rd_character']:
                if slot in state and state[slot][0]!=args[0]:hide(slot)
                state[slot]=[args[0],args[1] if len(args)>1 and args[1] else characters[args[0]].get('current_expression','')];active=slot
            elif method in ['hide_character','hide_2nd_character','hide_3rd_character']:hide(slot)
            elif method=='hide_all_characters':
                for s in list(state):hide(s)
            elif 'expression' in method or 'move' in method or method.endswith('_light'):
                if slot in state and args:state[slot][1]=args[-1]
                if method.endswith('_light'):active=slot
            elif method.endswith('_dark'):pass # Native speaker/asides apply the dialogue focus shading.
            elif method in ['show_dialog','show_text_only']:
                word=args[0].replace('\n','\\n');speaker=args[1] if len(args)>1 else '';index=len(lines);lines.append([str(index+1),speaker or 'N/A']+[word]*5+[''])
                matches=[v for v in state.values() if norm(characters[v[0]]['display_name'])==norm(speaker)]
                chosen=matches[0] if method=='show_dialog' and len(matches)==1 else None
                # PC-aside portraits are introduced in a command-only node so the narration remains an aside.
                silent=[v for v in state.values() if v[0] not in materialized and v!=chosen]
                if silent:
                    emit(pending+[role_speak(ch,ex,'',-1,'role84' if ch=='akikounglass' else '') for ch,ex in silent],control=True);pending=[]
                    materialized.update(ch for ch,ex in silent)
                if chosen:
                    ch,ex=chosen;action=role_speak(ch,ex,word,index,'role84' if ch=='akikounglass' else '');materialized.add(ch)
                else:action=command('C_speakAside',enableSentenceMapping=True,spName=speaker,wordStr=word,sentenceIdx=index)
                emit(pending+[action]);pending=[]
            elif method=='end_story_episode':pass
            else:raise ValueError('Unsupported PC command '+method)
        tail=pending+[command('StopBGM'),command('C_end'),command('EndLesson')]
        nodes[-1]['_roundInfo']['_a4cmdActionList']['actions'].extend(tail)
        graph=dict(version=json.loads((ROOT/'evidence/original_lesson_graphs.json').read_text('utf8'))['lesson10201']['version'],type='NodeCanvas.GuideLessonTrees.GuideLessonTree',translation={'x':0.0,'y':0.0},nodes=nodes,connections=[{'_sourceNode':{'$ref':str(i)},'_targetNode':{'$ref':str(i+1)},'$type':'NodeCanvas.GuideLessonTrees.GLTConnection'} for i in range(1,len(nodes))],primeNode={'$ref':'1'},localBlackboard={'_name':'Local Blackboard','_variables':{}},derivedData={'claimInfo':{'role':claim,'stage':{},'defaultBGM':first_music},'sentenceFName':'sentence_'+file+'.txt','$type':'NodeCanvas.GuideLessonTrees.GuideLessonTree+DerivedSerializationData'})
        def lesson(t):
            if '_serializedGraph' in t:t.update(_serializedGraph=json.dumps(graph,ensure_ascii=False,separators=(',',':')),sentenceFileName='sentence_'+file+'.txt',_defaultBGM=int(first_music),_claimInfo={'defaultBGM':first_music})
            return t
        def sentence(t):
            if 'bytes' in t:
                data=('\ufeff'+'\r\n'.join('\t'.join(row) for row in lines)+'\r\n').encode('utf8');t['bytes']=list(bytes(b^255 for b in data) if t.get('isEncrypt') else data)
            return t
        assets=[save_bundle(z,'assets/assetbundle/assets/resources/guide/lesson/lesson10201.ab','assets/assetbundle/assets/resources/guide/lesson/lesson'+file+'.ab',lesson),save_bundle(z,'assets/assetbundle/config/lesson/sentence_10201.ab','assets/assetbundle/config/lesson/sentence_'+file+'.ab',sentence)]
        def story_table(t):
            if 'bytes' in t:
                raw=bytes(t['bytes']);raw=bytes(b^255 for b in raw) if t.get('isEncrypt') else raw
                rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))));idcol=rows[0].index('ID');flagcol=rows[0].index('isWrite');changed=0
                for row in rows[3:]:
                    if row and row[idcol]=='61300041019' and row[rows[0].index('channel_group')] in ('0','25'):row[flagcol]='1';changed+=1
                assert changed==1
                out=io.StringIO();csv.writer(out,lineterminator='\n').writerows(rows);data=('\ufeff'+out.getvalue()).encode('utf8');t['bytes']=list(bytes(b^255 for b in data) if t.get('isEncrypt') else data)
            return t
        assets.append(save_bundle(z,'assets/assetbundle/config/clientexel/story.ab','assets/assetbundle/config/clientexel/story.ab',story_table))
        assert len(lines)==methods['show_dialog']+methods['show_text_only']
        for ch in usedchars:dependencies.add(role_assets[ch]['bundle'])
        result=dict(assets=assets,extra_roles=extras,graphs={'lesson'+file:graph},lessons={file:dict(source=path.relative_to(ROOT).as_posix(),dialogues=len(lines),nodes=len(nodes),dependencies=sorted(dependencies),music=music_used,pc_commands=dict(methods),presentation='Native Android dialogue layout and transitions, PC text, portraits and per-line expressions; retained all 349 dialogue/asides')})
        (ROOT/'evidence/pc_converted_lessons.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8');print('Converted',file,'dialogues',len(lines),'nodes',len(nodes),'characters',usedchars)
if __name__=='__main__':main()
