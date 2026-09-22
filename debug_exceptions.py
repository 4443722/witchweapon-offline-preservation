"""Expand reflection diagnostics in development libraries, removed for release."""
from prepare_offline import ROOT, ELFFile, Cs, CS_ARCH_ARM, CS_MODE_ARM
import json,struct
for bits,abi in [(32,'armeabi-v7a'),(64,'arm64-v8a')]:
    path=ROOT/f'overrides/lib/{abi}/libil2cpp.so'
    data=bytearray(path.read_bytes())
    script=json.loads((ROOT/f'decoded/il2cpp{bits}/script.json').read_text('utf-8-sig'))
    m=next(m for m in script['ScriptMethod'] if m['Name']=='LuaInterface.LuaDLL$$toluaL_exception')
    with path.open('rb') as f:
        elf=ELFFile(f);seg=next(s for s in elf.iter_segments() if s['p_vaddr']<=m['Address']<s['p_vaddr']+s['p_filesz'])
        offset=seg['p_offset']+m['Address']-seg['p_vaddr']
    if bits==32:
        for delta,old,new in [(0x54,0xe59020e4,0xe59020cc),(0x58,0xe59010e8,0xe59010d0),
                              (0xc4,0xe59020e4,0xe59020cc),(0xc8,0xe59010e8,0xe59010d0)]:
            at=offset+delta
            assert struct.unpack_from('<I',data,at)[0] in (old,new)
            struct.pack_into('<I',data,at,new)
    else:
        for delta in [0x50,0xb0]:
            at=offset+delta;old=struct.unpack_from('<I',data,at)[0]
            # ldp x9,x1,[x8,#0x170] -> ToString's slot at 0x140.
            assert ((old>>15)&127) in (0x170//8,0x140//8)
            struct.pack_into('<I',data,at,(old&~(127<<15))|((0x140//8)<<15))
    path.write_bytes(data)
    print('Reflection diagnostics expanded',abi)
