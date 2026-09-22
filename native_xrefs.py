"""Read-only direct AArch64 call/branch references in the original IL2CPP image."""
from pathlib import Path
import sys, json, re, bisect

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/python'))
import numpy as np
from elftools.elf.elffile import ELFFile

def references(pattern):
    rows=json.loads((ROOT/'decoded/il2cpp64/script.json').read_text('utf-8-sig'))['ScriptMethod']
    names={r['Address']:r['Name'] for r in rows}
    addresses=sorted(names)
    targets={r['Address']:r['Name'] for r in rows if re.search(pattern,r['Name'])}
    with (ROOT/'original_parts/lib/arm64-v8a/libil2cpp.so').open('rb') as f:
        elf=ELFFile(f)
        for section in elf.iter_sections():
            if not section['sh_flags']&4 or section['sh_type']!='SHT_PROGBITS':continue
            words=np.frombuffer(section.data(),dtype='<u4')
            indices=np.flatnonzero((words&0x7c000000)==0x14000000)
            offsets=(words[indices]&0x03ffffff).astype(np.int64)
            offsets[offsets>=0x02000000]-=0x04000000
            sources=indices*4+section['sh_addr'];destinations=sources+offsets*4
            for target,name in targets.items():
                for pos in np.flatnonzero(destinations==target):
                    source=int(sources[pos]);index=bisect.bisect_right(addresses,source)-1
                    print(f'{source:#x} {names[addresses[index]]} -> {name}')

if __name__=='__main__':references(sys.argv[1])
