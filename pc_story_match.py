"""Collect evidence for original role/expression to PC character mappings."""
from pathlib import Path
import json,re,collections,difflib,csv
from pc_script_inspect import read_script,ROOT
from offline_seed import table

def norm(s):
    s=re.sub(r'\\u([0-9a-fA-F]{4})',lambda m:chr(int(m[1],16)),s)
    s=s.replace('瑟蕾莎','瑟雷莎').replace('伦伯特','兰伯特')
    s=s.replace('[%rolename%]','').replace('\\n','').replace('\\r','')
    return ''.join(c.lower() for c in s if c.isalnum())

def strings(line):return [json.loads(x) for x in re.findall(r'"(?:[^"\\]|\\.)*"',line)]

def main():
    source=ROOT/'pc_story_source';chars={};failures=[]
    for file in (source/'scripts/character').glob('*.gdc'):
        try:text,_,_=read_script(file)
        except Exception as e:failures.append((str(file),str(e)));continue
        info={}
        for line in text.splitlines():
            for key in ['character_name','display_name','current_expression','expression_list']:
                if key+' EQUAL ' in line:
                    vals=strings(line);info[key]=vals if key=='expression_list' else vals[0] if vals else ''
        if 'character_name' in info:chars[info['character_name']]=info
    config=json.loads((source/'scripts/set/story_config.json').read_text('utf8'))
    dictionary={r['ID']:r['content_chinese'] for r in list(csv.DictReader((ROOT/'decoded/config/clientexel/Dictionary.txt').open(encoding='utf-8-sig'),delimiter='\t'))[2:]}
    group_names={r['ID']:norm(dictionary.get(r['name'],'')) for r in table('StoryGroup')}
    group_names['6010004']=norm('深潜症')
    pc_titles={}
    for chap,group in config.items():
        for title,e in group['episodes'].items():pc_titles[(norm(group['title']),title)]=(chap,Path(e['scene']).stem)
    graphs=json.loads((ROOT/'evidence/original_lesson_graphs.json').read_text('utf8'))
    sentences=json.loads((ROOT/'evidence/original_sentence_tables.json').read_text('utf8'))
    inventory=json.loads((ROOT/'evidence/story_inventory_before_pc_restore.json').read_text('utf8'))
    content=json.loads((ROOT/'evidence/pc_content_matches.json').read_text('utf8'))['lessons']
    observations=[];rolecounts=collections.defaultdict(collections.Counter);facecounts=collections.defaultdict(collections.Counter)
    for story in inventory:
        key=pc_titles.get((group_names.get(story['group'],''),story['title']));g=graphs.get('lesson'+story['file'])
        candidates=content.get(story['file'],{}).get('candidates',[])
        if candidates and candidates[0]['count']>=3:
            p=Path(candidates[0]['path']);key=(p.parent.name,p.stem)
        if not key or not g:continue
        dialogs=[]
        for lang,suffix in [(2,''),(3,'_tc'),(6,'_en')]:
            file=source/'scripts/story'/key[0]/(key[1]+suffix+'.gdc')
            if not file.exists():continue
            try:text,_,_=read_script(file)
            except Exception as e:failures.append((str(file),str(e)));continue
            state={}
            for line in text.splitlines():
                m=re.search(r'novel_interface PERIOD (\w+) PARENTHESIS_OPEN',line)
                if not m:continue
                method=m[1];args=strings(line);slot=2 if '3rd' in method else 1 if '2nd' in method else 0
                if method in ['show_character','show_2nd_character','show_3rd_character'] and args:
                    ch=args[0];state[slot]=[ch,args[1] if len(args)>1 else chars.get(ch,{}).get('current_expression','')]
                elif ('expression' in method or 'move' in method or 'light' in method and 'dark' not in method) and args and slot in state:state[slot][1]=args[-1]
                elif method in ['hide_character','hide_2nd_character','hide_3rd_character']:state.pop(slot,None)
                elif method=='hide_all_characters':state={}
                if method in ['show_dialog','show_text_only'] and args:dialogs.append(dict(lang=lang,text=norm(args[0]),state=[x[:] for x in state.values()],line=line,speaker=args[1] if len(args)>1 else ''))
        roles=g.get('derivedData',{}).get('claimInfo',{}).get('role',[])
        actions=[]
        for node in g.get('nodes',[]):
            for commands in node.get('_roundInfo',{}).values():
                if isinstance(commands,dict):actions.extend(commands.get('actions',[]))
        for action in actions:
            if not action.get('$type','').endswith('C_roleSpeak'):continue
            idx=action.get('_roleIdx',0)
            if idx>=len(roles):continue
            role=roles[idx];sn=role.get('roleSN');original=norm(action.get('wordStr',''))
            localized={2:original}
            for row in sentences.get('sentence_'+story['file'],[]):
                if row and row[0]==str(action.get('sentenceIdx',-2)+1):
                    localized.update({i:norm(row[i]) for i in [2,3,6] if i<len(row) and row[i]});break
            candidates=[]
            for dialog in dialogs:
                original=localized.get(dialog['lang'],'')
                if len(original)<8 or not dialog['text']:continue
                if abs(len(original)-len(dialog['text'])) > max(len(original),len(dialog['text']))*.2:continue
                score=1.0 if original==dialog['text'] else difflib.SequenceMatcher(None,original,dialog['text'],autojunk=False).ratio()
                if score<.9:continue
                matching=[(ch,ex) for ch,ex in dialog['state'] if norm(chars.get(ch,{}).get('display_name',''))==norm(role.get('name',''))]
                if not matching and len(dialog['state'])==1 and norm(dialog.get('speaker',''))==norm(role.get('name','')):matching=[tuple(dialog['state'][0])]
                if len(matching)==1:candidates.append((score,matching[0],dialog))
            if not candidates:continue
            score,(ch,ex),dialog=max(candidates,key=lambda x:x[0]);face=action.get('faceStr','')
            rolecounts[sn][ch]+=1
            if face.isdigit() and ex:facecounts[(sn,face)][(ch,ex)]+=1
            observations.append(dict(story=story['id'],role=sn,face=face,character=ch,expression=ex,score=score,original=localized.get(dialog['lang'],''),pc=dialog['text'],lang=dialog['lang']))
    result=dict(characters=chars,role_votes={k:dict(v) for k,v in rolecounts.items()},face_votes={k+'_'+f:{ch+':'+ex:n for (ch,ex),n in v.items()} for (k,f),v in facecounts.items()},observations=observations,failures=failures)
    (ROOT/'evidence/pc_role_mapping_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print('Characters',len(chars),'role mappings',len(rolecounts),'expression mappings',len(facecounts),'observations',len(observations),'parse failures',len(failures))
    print(json.dumps(result['role_votes'],ensure_ascii=False))

if __name__=='__main__':main()
