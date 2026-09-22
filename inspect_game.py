"""Read the original APK and save independent, reproducible static evidence."""
from pathlib import Path
import os, sys, zipfile, json, hashlib, collections, struct

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/python'))
import UnityPy
from loguru import logger
logger.remove()
from androguard.core.axml import AXMLPrinter
from lxml import etree

SOURCE = Path(os.environ.get('WW_SOURCE_APK', ROOT / 'inputs' / '20240516161158_mnbq.apk'))

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    entries, objects, failures = [], [], []
    with SOURCE.open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    with zipfile.ZipFile(SOURCE) as z:
        for i in z.infolist():
            entries.append({'name':i.filename, 'size':i.file_size, 'compressed':i.compress_size, 'crc32':i.CRC})
            n = i.filename
            core = n in {'AndroidManifest.xml', 'resources.arsc', 'classes.dex', 'classes2.dex',
                         'assets/bin/Data/Managed/Metadata/global-metadata.dat',
                         'assets/bin/Data/globalgamemanagers', 'assets/bin/Data/boot.config'} or n.startswith('lib/')
            chosen = n.endswith('.ab') and (n.startswith('assets/assetbundle/lua/') or n.startswith('assets/assetbundle/config/'))
            if core or chosen:
                p = ROOT / 'original_parts' / n
                assert p.resolve().is_relative_to((ROOT / 'original_parts').resolve())
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists(): p.write_bytes(z.read(n))
            if not chosen: continue
            try:
                env = UnityPy.load(z.read(n))
                for obj in env.objects:
                    if obj.type.name not in ('TextAsset', 'MonoBehaviour'): continue
                    rec = {'bundle':n, 'path_id':obj.path_id, 'type':obj.type.name}
                    try:
                        tree = obj.read_typetree()
                        rec['name'] = tree.get('m_Name', '')
                        rec['fields'] = list(tree)
                        out = ROOT / 'decoded' / 'objects' / n.removeprefix('assets/assetbundle/')
                        save_json(out.with_suffix(f'.{obj.path_id}.json'), tree)
                        if obj.type.name == 'TextAsset':
                            text = obj.read().m_Script
                            data = text if isinstance(text, bytes) else text.encode('utf-8', 'surrogateescape')
                            dest = ROOT / 'decoded' / 'text' / n.removeprefix('assets/assetbundle/').removesuffix('.ab') / rec['name']
                            assert dest.resolve().is_relative_to((ROOT / 'decoded/text').resolve())
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(data)
                            rec['bytes'] = len(data)
                    except Exception as e:
                        rec['error'] = repr(e)
                        raw = obj.get_raw_data()
                        out = ROOT / 'decoded/raw' / n.removeprefix('assets/assetbundle/')
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.with_suffix(f'.{obj.path_id}.bin').write_bytes(raw)
                    objects.append(rec)
            except Exception as e: failures.append({'name':n, 'error':repr(e)})
        root = AXMLPrinter(z.read('AndroidManifest.xml')).get_xml_obj()
        (ROOT / 'evidence/AndroidManifest.xml').write_bytes(etree.tostring(root, pretty_print=True, encoding='utf-8'))
        b = z.read('assets/bin/Data/Managed/Metadata/global-metadata.dat')
        h = struct.unpack_from('<8I', b)
        strings = [x.decode('utf8', 'replace') for x in b[h[6]:h[6]+h[7]].split(b'\0')]
        literals = []
        for off in range(h[2], h[2]+h[3], 8):
            length, index = struct.unpack_from('<II', b, off)
            literals.append(b[h[4]+index:h[4]+index+length].decode('utf8', 'replace'))
        save_json(ROOT / 'decoded/metadata_literals.json', literals)
        (ROOT / 'decoded/metadata_strings.txt').write_text('\n'.join(strings), encoding='utf-8')
    save_json(ROOT / 'evidence/source.json', {'source':str(SOURCE), 'size':SOURCE.stat().st_size, 'sha256':sha, 'unitypy':UnityPy.__version__})
    save_json(ROOT / 'evidence/zip_inventory.json', entries)
    save_json(ROOT / 'evidence/object_inventory.json', objects)
    save_json(ROOT / 'evidence/parse_failures.json', failures)
    print(json.dumps({'sha256':sha, 'entries':len(entries), 'objects':len(objects), 'types':dict(collections.Counter(x['type'] for x in objects)), 'object_errors':sum('error' in x for x in objects), 'bundle_failures':failures[:8]}, ensure_ascii=False))

if __name__ == '__main__': main()
