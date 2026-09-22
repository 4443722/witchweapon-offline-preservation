"""Build and sign a separate test package; never overwrite the user's APK."""
from pathlib import Path
import os, sys, ast, copy, struct, json, hashlib, zlib, subprocess, zipfile
from patch_manifest import patch_manifest

ROOT=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk'))
BUILD=ROOT/'build'
BUILD.mkdir(exist_ok=True)
JAVA=Path(os.environ.get('WW_JAVA_BIN',Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Microsoft'/'jdk-17.0.11.9-hotspot'/'bin'))
BT=Path(os.environ.get('WW_ANDROID_BUILD_TOOLS',Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData'/'Local'))/'Android'/'Sdk'/'build-tools'/'36.1.0'))

def copy_compressed_entry(src, dst, info):
    assert info.file_size<0xffffffff and info.compress_size<0xffffffff
    src.fp.seek(info.header_offset); header=src.fp.read(30)
    assert header[:4]==b'PK\x03\x04'
    names,extra=struct.unpack_from('<HH',header,26)
    size=30+names+extra+info.compress_size
    if info.flag_bits&8:
        src.fp.seek(info.header_offset+size)
        size+=16 if src.fp.read(4)==b'PK\x07\x08' else 12
    destinfo=copy.copy(info);dst.fp.seek(dst.start_dir);destinfo.header_offset=dst.fp.tell()
    dst._writecheck(destinfo);dst._didModify=True;src.fp.seek(info.header_offset)
    remaining=size
    while remaining:
        block=src.fp.read(min(1024*1024,remaining))
        if not block:raise ValueError('Truncated input ZIP')
        dst.fp.write(block);remaining-=len(block)
    dst.start_dir=dst.fp.tell();dst.filelist.append(destinfo);dst.NameToInfo[destinfo.filename]=destinfo

def patch_dex(data):
    from loguru import logger
    logger.remove()
    from androguard.core.dex import DEX
    d=DEX(data);out=bytearray(data);patched=[]
    for cls in d.get_classes():
        if cls.get_name()!='Lcom/shuiqinling/ww/android/Util/LebianHelper;':continue
        for m in cls.get_methods():
            if m.get_name()=='queryUpdate':
                assert m.get_descriptor().endswith(')V')
                item=m.get_code_off();off=item+16
                size=m.get_code().get_insns_size()*2
                patched.append({'class':cls.get_name(),'method':m.get_name(),'offset':off,'before':out[off:off+2].hex(),'after':'0e00'})
                out[off:off+size]=b'\x0e\x00'+b'\x00'*(size-2)
                struct.pack_into('<H',out,item+6,0)  # No exception regions remain.
                struct.pack_into('<I',out,item+8,0)  # Drop obsolete debug offsets.
    assert len(patched)==1,patched
    out[12:32]=hashlib.sha1(out[32:]).digest()
    struct.pack_into('<I',out,8,zlib.adler32(out[12:])&0xffffffff)
    (ROOT/'evidence/dex_patch.json').write_text(json.dumps(patched,indent=2),encoding='utf8')
    return bytes(out)

def patch_resources(data):
    out=bytearray(data);pos=struct.unpack_from('<H',out,2)[0];found=0
    while pos<len(out):
        kind,header,size=struct.unpack_from('<HHI',out,pos)
        assert size>=header and pos+size<=len(out)
        if kind==0x200:
            old=bytes(out[pos+12:pos+268]).decode('utf-16le').split('\0',1)[0]
            assert old=='com.shuiqinling.ww.android.cn00',old
            out[pos+12:pos+268]='com.codex.witchweapon.local'.encode('utf-16le').ljust(256,b'\0')
            found+=1
        pos+=size
    assert found==1
    return bytes(out)

def main():
    expected=json.loads((ROOT/'evidence/source.json').read_text(encoding='utf8'))
    with SOURCE.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==expected['sha256']
    unsigned=BUILD/'stage1-unsigned.apk';aligned=BUILD/'stage1-aligned.apk';output=BUILD/'witchweapon-stage1-test.apk'
    replacements={}
    with zipfile.ZipFile(SOURCE) as src:
        replacements['AndroidManifest.xml'],removed=patch_manifest(src.read('AndroidManifest.xml'))
        replacements['classes.dex']=patch_dex(src.read('classes.dex'))
        replacements['resources.arsc']=patch_resources(src.read('resources.arsc'))
        overrides=ROOT/'overrides'
        if overrides.exists():
            for p in overrides.rglob('*'):
                if p.is_file():replacements[p.relative_to(overrides).as_posix()]=p.read_bytes()
        with zipfile.ZipFile(unsigned,'w',allowZip64=True) as dst:
            for info in src.infolist():
                upper=info.filename.upper()
                if upper.startswith('META-INF/') and (upper.endswith(('.SF','.RSA','.DSA','.EC')) or upper=='META-INF/MANIFEST.MF'):continue
                if info.filename in replacements:
                    dst.writestr(copy.copy(info),replacements.pop(info.filename))
                else:copy_compressed_entry(src,dst,info)
            for n,d in replacements.items():dst.writestr(n,d,compress_type=zipfile.ZIP_DEFLATED)
    subprocess.run([str(BT/'zipalign.exe'),'-f','-p','4',str(unsigned),str(aligned)],check=True)
    unsigned.unlink(missing_ok=True)
    key=BUILD/'local-test-key.jks'
    if not key.exists():
        subprocess.run([str(JAVA/'keytool.exe'),'-genkeypair','-keystore',str(key),'-storepass','local-stage1','-keypass','local-stage1','-alias','local','-keyalg','RSA','-keysize','2048','-validity','10000','-dname','CN=WitchWeapon Local Test'],check=True)
    signer=[str(JAVA/'java.exe'),'-jar',str(BT/'lib/apksigner.jar')]
    subprocess.run(signer+['sign','--ks',str(key),'--ks-pass','pass:local-stage1','--key-pass','pass:local-stage1','--out',str(output),str(aligned)],check=True)
    aligned.unlink(missing_ok=True)
    result=subprocess.run(signer+['verify','--verbose',str(output)],check=True,capture_output=True,text=True)
    print(result.stdout)
    with zipfile.ZipFile(output) as z:
        from loguru import logger
        logger.remove()
        from androguard.core.axml import AXMLPrinter
        root=AXMLPrinter(z.read('AndroidManifest.xml')).get_xml_obj()
        assert root.get('package')=='com.codex.witchweapon.local'
        assert z.testzip() is None
    with output.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest()
    (ROOT/'evidence/build.json').write_text(json.dumps({'source_sha256':expected['sha256'],'output':str(output),'sha256':sha,'size':output.stat().st_size,'removed_manifest_entries':removed,'apksigner':result.stdout},ensure_ascii=False,indent=2),encoding='utf8')
    print(str(output),sha)

if __name__=='__main__':main()
