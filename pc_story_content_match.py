"""Match original lessons to actual PC script content, independently of menu labels."""
from pathlib import Path
import json,re,collections
from pc_script_inspect import read_script,ROOT
from pc_story_match import norm,strings

def main():
    source=ROOT/'pc_story_source';config=json.loads((source/'scripts/set/story_config.json').read_text('utf8'))
    files={}
    for group in config.values():
        for title,e in group['episodes'].items():
            path=e['scripts']['zh'].removeprefix('res://').removesuffix('.gd')+'.gdc'
            files[path]=dict(group=group['title'],title=title)
    for p in (source/'scripts/story').rglob('*.gdc'):
        if re.search(r'_ep\d+\.gdc$',p.name):files.setdefault(p.relative_to(source).as_posix(),dict(group=p.parent.name,title='not in menu'))
    inverted=collections.defaultdict(set);pc={}
    for path,meta in files.items():
        text,_,_=read_script(source/path);lines=[]
        for line in text.splitlines():
            if re.search(r'PERIOD (?:show_dialog|show_text_only) PARENTHESIS_OPEN',line):
                values=strings(line)
                if values:lines.append(norm(values[0]))
        pc[path]=dict(meta,dialog_count=len(lines),lines=lines)
        for line in set(lines):
            if len(line)>=8:inverted[line].add(path)
    sentences=json.loads((ROOT/'evidence/original_sentence_tables.json').read_text('utf8'));result={}
    for name,rows in sentences.items():
        original={norm(row[2]) for row in rows if len(row)>2 and row[0].isdigit() and len(norm(row[2]))>=8};counts=collections.Counter();weights=collections.Counter()
        for line in original:
            for path in inverted.get(line,[]):counts[path]+=1;weights[path]+=len(line)
        ranked=sorted(counts,key=lambda p:(weights[p],counts[p]),reverse=True)[:4]
        if ranked:result[name.removeprefix('sentence_')]=dict(original_lines=len(original),candidates=[dict(path=p,count=counts[p],characters=weights[p],coverage=round(counts[p]/max(1,len(original)),4),group=pc[p]['group'],title=pc[p]['title']) for p in ranked])
    (ROOT/'evidence/pc_content_matches.json').write_text(json.dumps(dict(lessons=result,pc_scripts={p:{k:v for k,v in d.items() if k!='lines'} for p,d in pc.items()}),ensure_ascii=False,indent=2),'utf8')
    print('PC scripts',len(pc),'matched lessons',len(result))
    for f in ['30013','30021','30212','30318','30319']:
        print(f,result.get(f))
if __name__=='__main__':main()
