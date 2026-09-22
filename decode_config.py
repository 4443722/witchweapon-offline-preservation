from pathlib import Path
import json, base64, re
from google.protobuf.descriptor_pb2 import FileDescriptorProto

ROOT = Path(__file__).resolve().parent

def main():
    records = []
    for p in (ROOT / 'decoded/objects/config').rglob('*.json'):
        tree = json.loads(p.read_text(encoding='utf-8'))
        raw = bytes(tree['bytes'])
        data = bytes(x ^ 255 for x in raw) if tree['isEncrypt'] else raw
        try: text = data.decode('utf-8-sig')
        except UnicodeDecodeError: text = None
        suffix = '.xml' if text and text.lstrip().startswith('<') else '.csv' if text and ',' in text.splitlines()[0] else '.txt' if text else '.bin'
        out = ROOT / 'decoded/config' / p.relative_to(ROOT / 'decoded/objects/config').parent / (tree['m_Name'] + suffix)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        assert (bytes(x ^ 255 for x in data) if tree['isEncrypt'] else data) == raw
        records.append({'name':str(out.relative_to(ROOT)), 'bytes':len(data), 'encrypted':tree['isEncrypt']})
    protos = []
    literals = json.loads((ROOT / 'decoded/metadata_literals.json').read_text(encoding='utf-8'))
    for index, first_text in enumerate(literals):
        if len(first_text) < 8 or not re.fullmatch('[A-Za-z0-9+/]+={0,2}', first_text): continue
        try:
            first = base64.b64decode(first_text, validate=True)
            length = first[1]
            if first[0] != 10 or length > len(first)-2 or not first[2:length+2].endswith(b'.proto'): continue
        except Exception: continue
        text = ''
        for stop in range(index, min(len(literals), index+1200)):
            if not re.fullmatch('[A-Za-z0-9+/]+={0,2}', literals[stop]): break
            text += literals[stop]
            try:
                data = base64.b64decode(text, validate=True)
                descriptor = FileDescriptorProto()
                descriptor.ParseFromString(data)
                if not (descriptor.message_type or descriptor.enum_type) or not descriptor.syntax: continue
            except Exception: continue
            out = ROOT / 'decoded/proto_descriptors' / descriptor.name
            assert out.resolve().is_relative_to((ROOT / 'decoded/proto_descriptors').resolve())
            out.parent.mkdir(parents=True, exist_ok=True)
            out.with_suffix('.pb').write_bytes(data)
            out.with_suffix('.txt').write_text(str(descriptor), encoding='utf-8')
            protos.append({'name':descriptor.name, 'package':descriptor.package, 'messages':[m.name for m in descriptor.message_type], 'chunks':stop-index+1})
            break
    (ROOT / 'evidence/config_inventory.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'evidence/protobuf_inventory.json').write_text(json.dumps(protos, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'configs':len(records), 'protobuf':protos}, ensure_ascii=False))

if __name__ == '__main__': main()
