"""Read-only, checksum-verified extraction of the user-supplied Godot pack."""
from pathlib import Path
import os, struct, hashlib, json
ROOT=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get('WW_PC_EXE',ROOT/'inputs'/'Witch Weapon.exe'))
DEST=ROOT/'pc_story_source'

def extract():
    with SOURCE.open('rb') as f:
        f.seek(-12,2);size,magic=struct.unpack('<Q4s',f.read(12));assert magic==b'GDPC'
        start=SOURCE.stat().st_size-12-size
        f.seek(start);header=f.read(112)
        assert header[:4]==b'GDPC' and struct.unpack_from('<I',header,4)[0]==4
        base,directory=struct.unpack_from('<QQ',header,24)
        f.seek(start+directory);count=struct.unpack('<I',f.read(4))[0];entries=[]
        for _ in range(count):
            length=struct.unpack('<I',f.read(4))[0];name=f.read(length).rstrip(b'\0').decode('utf8')
            offset,length=struct.unpack('<QQ',f.read(16));md5=f.read(16).hex();flags=struct.unpack('<I',f.read(4))[0]
            assert not flags and not Path(name).is_absolute() and '..' not in Path(name).parts
            entries.append(dict(path=name,offset=offset,size=length,md5=md5,flags=flags))
        for x in entries:
            f.seek(start+base+x['offset']);data=f.read(x['size']);assert hashlib.md5(data).hexdigest()==x['md5'],x['path']
            target=DEST/x['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (ROOT/'evidence/pc_story_pack_inventory.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),'utf8')
    print('Verified and extracted',count,'files to',DEST)

if __name__=='__main__':extract()
