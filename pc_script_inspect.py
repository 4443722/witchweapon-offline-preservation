"""Decode Godot token buffers as inert data, without executing GDScript.
Format reference: godotengine/godot modules/gdscript/gdscript_tokenizer_buffer.cpp.
"""
from pathlib import Path
import sys,struct,json,re
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/python'))
import zstandard

def read_script(path):
    b=Path(path).read_bytes();assert b[:4]==b'GDSC'
    d=zstandard.ZstdDecompressor().decompress(b[12:]) if struct.unpack_from('<I',b,8)[0] else b[12:]
    ni,nc,nl,nt=struct.unpack_from('<4I',d);pos=16;ids=[];constants=[]
    def u32():
        nonlocal pos
        v=struct.unpack_from('<I',d,pos)[0];pos+=4;return v
    for _ in range(ni):
        n=u32();ids.append(bytes(x^182 for x in d[pos:pos+4*n]).decode('utf-32le').rstrip('\0'));pos+=4*n
    for _ in range(nc):
        typeflags=u32();t=typeflags&0xffff
        if t==0:v=None
        elif t in (1,2,3):
            fmt=('<q' if t==2 else '<d') if typeflags&65536 else ('<f' if t==3 else '<i')
            v=struct.unpack_from(fmt,d,pos)[0];pos+=struct.calcsize(fmt)
        elif t in (4,21):
            n=u32();v=d[pos:pos+n].decode('utf8');pos+=(n+3)//4*4
        else:raise ValueError((str(path),t,pos))
        constants.append(v)
    pos+=nl*16;lines={}
    enum=(ROOT/'evidence/gdscript_tokenizer.h').read_text().split('enum Type {',1)[1].split('};',1)[0]
    names=[re.sub(r'//.*','',x).strip().split('=')[0].strip() for x in enum.split(',')];names=[x for x in names if x]
    for _ in range(nt):
        if d[pos]&128:token=u32()
        else:token=d[pos];pos+=1
        line=u32();typ=token&127;value=token>>8
        name=names[typ]
        out=ids[value] if name in ('IDENTIFIER','ANNOTATION') else json.dumps(constants[value],ensure_ascii=False) if name=='LITERAL' else name
        lines.setdefault(line,[]).append(out)
    assert pos==len(d),(pos,len(d))
    return '\n'.join(str(k)+': '+' '.join(v) for k,v in lines.items()),ids,constants

if __name__=='__main__':
    text,_,_=read_script(sys.argv[1]);print(text)
