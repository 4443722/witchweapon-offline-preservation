import json,zipfile,sys,os
sys.path.insert(0,'tools/python');import UnityPy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
z=zipfile.ZipFile(Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk')));d=json.load(open('evidence/weapon_controllers.json'));out={}
for k,v in d.items():
 if not k.startswith('animations/') or k.endswith('/bone'):continue
 env=UnityPy.load(z.read('assets/bin/Data/'+v['file']));f=next(iter(env.files.values()));names=[]
 for p in v['tree'].get('m_AnimationClips',[]):
  if not p['m_PathID']:continue
  if p['m_FileID']:
   nf=f.externals[p['m_FileID']-1].path.split('/')[-1];e=UnityPy.load(z.read('assets/bin/Data/'+nf));objs=e.objects
  else:objs=env.objects
  for o in objs:
   if o.path_id==p['m_PathID']:names.append(o.read_typetree().get('m_Name'));break
 out[k]=names
 print(k, names[:7])
Path('evidence/controller_clip_names.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
