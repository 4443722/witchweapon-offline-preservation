"""Recover descriptor chunks reused by IL2CPP's string literal deduplication.

Consumes annotated static AArch64 disassembly, following only literal loads and
array stores until Convert.FromBase64String. Does not execute the native code.
"""
from pathlib import Path
import re,base64
from google.protobuf import descriptor_pb2,text_format
ROOT=Path(__file__).resolve().parent
for block in (ROOT/'evidence/missing_proto_cctors.txt').read_text('utf8').split('METHOD ')[1:]:
    regs={};arrays={}
    for line in block.splitlines()[1:]:
        if 'System.Convert$$FromBase64String' in line:break
        m=re.match(r'[0-9a-f]+\s+(\w+)\s+(.*)',line)
        if not m:continue
        op,tail=m.groups();args=tail.split('  ')[0].strip()
        if op=='ldr':
            p=re.match(r'(\w+), \[(\w+)(?:, #(0x[0-9a-f]+|\d+))?\]',args)
            if not p:continue
            dst,src,off=p.groups();literal=re.search(r'@[0-9a-fx]+ ([A-Za-z0-9+/=]+)\s*$',tail)
            if literal:regs[dst]=('pointer',literal[1])
            elif not off and src in regs and regs[src][0]=='pointer':regs[dst]=('string',regs[src][1])
            else:regs.pop(dst,None)
        elif op=='str':
            p=re.match(r'(\w+), \[(\w+), #(0x[0-9a-f]+|\d+)\]',args)
            if p and regs.get(p[1],('?',))[0]=='string':arrays.setdefault(p[2],{})[int(p[3],0)]=regs[p[1]][1]
        elif op=='mov':
            dst,src=args.split(', ',1)
            if src in regs:regs[dst]=regs[src]
            else:regs.pop(dst,None)
        elif op in ('adrp','add','sub'):regs.pop(args.split(',')[0],None)
    valid=False
    for arr in arrays.values():
        encoded=''.join(arr[k] for k in sorted(arr))
        try:
            raw=base64.b64decode(encoded,validate=True);fd=descriptor_pb2.FileDescriptorProto.FromString(raw)
            assert fd.name.endswith('.proto') and fd.syntax=='proto3'
        except Exception:continue
        path=ROOT/'decoded/proto_descriptors'/fd.name.replace('.proto','.pb')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        path.with_suffix('.txt').write_text(text_format.MessageToString(fd),'utf8')
        print(fd.name,len(raw),len(fd.message_type),'messages');valid=True
    if not valid:raise RuntimeError('Descriptor reconstruction failed: '+block.splitlines()[0])
