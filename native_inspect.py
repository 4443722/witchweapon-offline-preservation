"""Small static class/method browser. Never executes game code."""
from pathlib import Path
import sys, re, json, bisect, os

ROOT = Path(__file__).resolve().parent
BITS=int(os.environ.get("WW_NATIVE_BITS","64"))
ABI="arm64-v8a" if BITS==64 else "armeabi-v7a"
sys.path.insert(0, str(ROOT / 'tools/python'))

def classes(pattern):
    text = (ROOT / f'decoded/il2cpp{BITS}/dump.cs').read_text(encoding='utf-8-sig')
    for block in text.split('// Namespace:'):
        heading = block[:block.find('\n{')]
        if re.search(pattern, heading): print('// Namespace:' + block)

def disasm(pattern, limit=400):
    from elftools.elf.elffile import ELFFile
    from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM
    script = json.loads((ROOT / f'decoded/il2cpp{BITS}/script.json').read_text(encoding='utf-8-sig'))
    methods = script['ScriptMethod']
    byaddr = {m['Address']:m['Name'] for m in methods}
    addresses = sorted(byaddr)
    labels = {}
    for key in ['ScriptMetadata', 'ScriptMetadataMethod', 'ScriptString']:
        for row in script.get(key, []): labels[row['Address']] = str(row.get('Name', row.get('Value', '')))
    with (ROOT / f'original_parts/lib/{ABI}/libil2cpp.so').open('rb') as f:
        elf = ELFFile(f)
        segments = [(p['p_vaddr'], p['p_offset'], p['p_filesz']) for p in elf.iter_segments() if p['p_type']=='PT_LOAD']
        rels = {}
        for section in elf.iter_sections():
            if section['sh_type'] in ('SHT_RELA', 'SHT_REL'):
                for rel in section.iter_relocations():
                    if rel['r_info_type'] == 1027: rels[rel['r_offset']] = rel['r_addend']
        for m in methods:
            if not re.search(pattern, m['Name']): continue
            start = m['Address']; endidx = bisect.bisect_right(addresses, start)
            end = addresses[endidx] if endidx < len(addresses) else start+1024
            print('\nMETHOD',m['Name'],m.get('Signature',''),hex(start),'bytes',end-start)
            off = next((o+start-v for v,o,n in segments if v<=start<v+n), None)
            if off is None: continue
            f.seek(off); data = f.read(min(end-start, limit*4))
            pages = {}
            for i in Cs(CS_ARCH_ARM64 if BITS==64 else CS_ARCH_ARM, CS_MODE_ARM).disasm(data, start):
                note=''
                if i.mnemonic in ('b', 'bl') and i.op_str.startswith('#'):
                    dest=int(i.op_str[1:],16);note=byaddr.get(dest,'')
                if i.mnemonic == 'adrp':
                    reg, val=i.op_str.split(', ');pages[reg]=int(val.lstrip('#'),16)
                match=re.match(r'([^,]+), \[([^,\]]+)(?:, #(0x[0-9a-f]+|[0-9]+))?\]',i.op_str)
                if i.mnemonic in ('ldr', 'ldrb', 'str') and match:
                    reg, base, delta = match.groups()
                    if base in pages:
                        pointer=pages[base]+int(delta or '0',0)
                        note += ' @'+hex(pointer)+' '+labels.get(pointer,labels.get(rels.get(pointer),'') or '')
                    if i.mnemonic.startswith('ld'): pages.pop(reg, None)
                elif i.mnemonic not in ('adrp','b','bl','cbz','cbnz','tbz','tbnz','cmp','tst','ret','str','strb','stp'):
                    pages.pop(i.op_str.split(',')[0], None)
                print(f'{i.address:08x}  {i.mnemonic:8} {i.op_str:42} {note}')

if __name__ == '__main__':
    if sys.argv[1]=='class': classes(sys.argv[2])
    else: disasm(sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 400)
