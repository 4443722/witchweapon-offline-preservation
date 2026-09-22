import os,sys,zipfile,json
sys.path.insert(0,'tools/python')
import UnityPy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
z=zipfile.ZipFile(Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk')))
e=UnityPy.load(z.read('assets/bin/Data/globalgamemanagers'))
f=next(iter(e.files.values()))
idx=json.loads(Path('evidence/resources_index.json').read_text('utf8'))['m_Container']
for key,p in idx:
 if key not in ['animations/ohw','animations/thw','animations/axe']:continue
 ext=f.externals[p['m_FileID']-1].path
 print(key,ext)
 raw=z.read('assets/bin/Data/'+ext.split('/')[-1]);env=UnityPy.load(raw)
 for o in env.objects:
  if o.type.name in ['AnimatorController','AnimatorOverrideController']:
   tree=o.read_typetree();Path('evidence/'+key.split('/')[-1]+'_controller.json').write_text(json.dumps(tree),'utf8')
   print(o.type.name,tree.keys(),str(tree)[:1500])
