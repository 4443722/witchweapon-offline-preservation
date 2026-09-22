"""Read inert Godot RSRC character data; never instantiate scripts.
Reference: godotengine/godot core/io/resource_format_binary.cpp.
"""
from pathlib import Path
import struct,re,json,sys
ROOT=Path(__file__).resolve().parent
class Reader:
    def __init__(self,data):self.data=data;self.pos=0;self.strings=[]
    def read(self,fmt):
        v=struct.unpack_from('<'+fmt,self.data,self.pos);self.pos+=struct.calcsize('<'+fmt);return v[0] if len(v)==1 else list(v)
    def string(self):
        n=self.read('I');v=self.data[self.pos:self.pos+n].decode('utf8').rstrip('\0');self.pos+=n;return v
    def name(self):
        i=self.read('I')
        if i&0x80000000:
            n=i&0x7fffffff;v=self.data[self.pos:self.pos+n].decode().rstrip('\0');self.pos+=n;return v
        return self.strings[i]
    def variant(self):
        t=self.read('I')
        if t==1:return None
        if t in (2,3,23):return self.read('i')
        if t==40:return self.read('q')
        if t==4:return self.read('f')
        if t==41:return self.read('d')
        if t in (5,44):return self.string()
        if t in (10,11,12,13,14,15,16,17,18,20):return self.read('f'*{10:2,11:4,12:3,13:4,14:4,15:6,16:9,17:12,18:6,20:4}[t])
        if t==22:
            n=self.read('H');s=self.read('H');return dict(node_path=[self.name() for _ in range(n+(s&32767))])
        if t==24:
            kind=self.read('I');return None if kind==0 else dict(refkind=kind,index=self.read('I'))
        if t==26:
            out={}
            for _ in range(self.read('I')&0x7fffffff):
                k=self.variant();v=self.variant();out[k]=v
            return out
        if t==30:return [self.variant() for _ in range(self.read('I')&0x7fffffff)]
        if t in (32,33):
            n=self.read('I');return [self.read('i' if t==32 else 'f') for _ in range(n)]
        if t==34:return [self.string() for _ in range(self.read('I'))]
        raise ValueError((t,self.pos))

def scene(name):
    source=ROOT/'pc_story_source'
    remap=(source/f'scenes/character/{name}.tscn.remap').read_text('utf8');path=re.search('res://([^"\n]+)',remap).group(1)
    r=Reader((source/path).read_bytes());assert r.data[:4]==b'RSRC';r.pos=4
    assert r.read('I')==0;r.read('4I');kind=r.string();r.read('Q');flags=r.read('I');r.read('Q');assert flags==3
    r.read('11I');r.strings=[r.string() for _ in range(r.read('I'))];external=[]
    for _ in range(r.read('I')):external.append(dict(type=r.string(),path=r.string(),uid=r.read('Q')))
    internal=[]
    for _ in range(r.read('I')):internal.append((r.string(),r.read('Q')))
    objects=[]
    for path,offset in internal:
        r.pos=offset;typ=r.string();props={}
        for _ in range(r.read('I')):
            key=r.name();props[key]=r.variant()
        objects.append(dict(path=path,type=typ,props=props))
    return dict(external=external,objects=objects)

def character_nodes(name):
    s=scene(name);bundle=next(o['props']['_bundled'] for o in s['objects'] if o['type']=='PackedScene');n=bundle['nodes'];pos=0;out={}
    for _ in range(bundle['node_count']):
        parent,owner,typ,nm,ins,count=n[pos:pos+6];pos+=6;props={}
        for i in range(count):
            k,v=n[pos:pos+2];pos+=2;value=bundle['variants'][v]
            if isinstance(value,dict) and value.get('refkind')==3:value=s['external'][value['index']]['path']
            props[bundle['names'][k&0x3fffffff]]=value
        groups=n[pos];pos+=1+groups;out[bundle['names'][nm&0x3fffffff]]=props
    return out

if __name__=='__main__':print(json.dumps(scene(sys.argv[1]),ensure_ascii=False,indent=2))
