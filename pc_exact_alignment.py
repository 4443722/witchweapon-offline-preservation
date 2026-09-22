"""Align complete dialogue sequences to recover short lines and silent expressions."""
import json,re,collections,difflib
from pathlib import Path
from pc_script_inspect import read_script,ROOT
from pc_story_match import norm,strings

def pc_dialogs(path,characters):
    text,_,_=read_script(path);state={};dialogs=[];active=0;music=None;background=None
    for line in text.splitlines():
        m=re.search(r'novel_interface PERIOD (\w+) PARENTHESIS_OPEN',line)
        if not m:continue
        method=m[1];args=strings(line);slot=2 if '3rd' in method else 1 if '2nd' in method else 0
        if method=='change_music' and args:music=args[0]
        elif method=='stop_music':music=None
        if method in ['change_background','show_background'] and args:background=args[0]
        elif method in ['hide_background','hide_background_with_fade']:background=None
        if method in ['show_character','show_2nd_character','show_3rd_character'] and args:
            ch=args[0];state[slot]=[ch,args[1] if len(args)>1 and args[1] else characters.get(ch,{}).get('current_expression','')];active=slot
        elif ('expression' in method or 'move' in method or 'light' in method and 'dark' not in method) and args and slot in state:state[slot][1]=args[-1]
        if 'light' in method and 'dark' not in method:active=slot
        if method in ['hide_character','hide_2nd_character','hide_3rd_character']:state.pop(slot,None)
        elif method=='hide_all_characters':state={}
        if method in ['show_dialog','show_text_only'] and args:
            speaker=args[1] if len(args)>1 else '';matches=[v for v in state.values() if norm(characters.get(v[0],{}).get('display_name',''))==norm(speaker)]
            chosen=matches[0] if len(matches)==1 else state.get(active) if method=='show_dialog' else None
            dialogs.append(dict(text=args[0],norm=norm(args[0]),speaker=speaker,chosen=chosen[:] if chosen else None,state=[v[:] for v in state.values()],line=line,music=music,background=background))
    return dialogs

def actions_ordered(graph,all_actions=False):
    nodes={n['$id']:n for n in graph['nodes']};links=collections.defaultdict(list)
    for c in graph['connections']:links[c['_sourceNode']['$ref']].append(c['_targetNode']['$ref'])
    current=graph['primeNode']['$ref'];seen=set();ordered=[]
    while current not in seen:
        seen.add(current);node=nodes[current]
        for key in ['_b4cmdActionList','_a4cmdActionList']:
            ordered.extend(a for a in node.get('_roundInfo',{}).get(key,{}).get('actions',[]) if (all_actions or 'sentenceIdx' in a) and not a.get('_isDisabled'))
        if not links[current]:break
        if len(links[current])!=1:raise ValueError('branch '+current)
        current=links[current][0]
    return ordered

def main():
    e=json.loads((ROOT/'evidence/pc_role_mapping_evidence.json').read_text('utf8'));g=json.loads((ROOT/'evidence/original_lesson_graphs.json').read_text('utf8'));s=json.loads((ROOT/'evidence/original_sentence_tables.json').read_text('utf8'));m=json.loads((ROOT/'evidence/pc_content_matches.json').read_text('utf8'))['lessons'];observations=[];stats=[];asset_observations=[]
    for f,match in m.items():
        if 'lesson'+f not in g:continue
        best=match['candidates'][0]
        if best['count']<3:continue
        graph=g['lesson'+f];roles=graph['derivedData'].get('claimInfo',{}).get('role',[])
        try:actions=actions_ordered(graph)
        except (ValueError,KeyError):continue
        music=graph['derivedData'].get('claimInfo',{}).get('defaultBGM');bg=None;action_assets={}
        for action in actions_ordered(graph,True):
            kind=action.get('$type','').split('.')[-1]
            if kind=='PlayBGM':music=str(action.get('sndID'))
            elif kind=='StopBGM':music=None
            if kind=='C_changeBG':bg=action.get('picName')
            if 'sentenceIdx' in action:action_assets[id(action)]=(music,bg)
        rows={int(r[0])-1:r[2] for r in s.get('sentence_'+f,[]) if len(r)>2 and r[0].isdigit()}
        original=[norm(rows.get(a['sentenceIdx'],a.get('wordStr',''))) for a in actions];pc=pc_dialogs(ROOT/'pc_story_source'/best['path'],e['characters'])
        matcher=difflib.SequenceMatcher(None,original,[x['norm'] for x in pc],autojunk=False);aligned=0
        for block in matcher.get_matching_blocks():
            for j in range(block.size):
                i,k=block.a+j,block.b+j;a=actions[i];d=pc[k];aligned+=1
                asset_observations.append(dict(file=f,sentence=a['sentenceIdx'],original_music=action_assets.get(id(a),(None,None))[0],original_background=action_assets.get(id(a),(None,None))[1],pc_music=d['music'],pc_background=d['background']))
                if not a.get('$type','').endswith('C_roleSpeak') or not d['chosen']:continue
                if block.size<3 and len(original[i])<8:continue
                idx=a.get('_roleIdx',0)
                if idx>=len(roles):continue
                role=roles[idx];ch,ex=d['chosen'];observations.append(dict(file=f,sentence=a['sentenceIdx'],role=role.get('roleSN'),face=a.get('faceStr',''),character=ch,expression=ex,matching_block=block.size,text=rows.get(a['sentenceIdx'],a.get('wordStr','')),pc_line=d['line']))
        stats.append(dict(file=f,actions=len(actions),pc_dialogs=len(pc),aligned=aligned,path=best['path']))
    (ROOT/'evidence/pc_exact_alignment.json').write_text(json.dumps(dict(observations=observations,stats=stats,asset_observations=asset_observations),ensure_ascii=False,indent=2),'utf8');print('Aligned',len(observations),'role expressions across',len(stats),'lessons')
if __name__=='__main__':main()
