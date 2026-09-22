import os,sys,zipfile,json
from pathlib import Path
sys.path.insert(0,'tools/python')
import UnityPy
ROOT=Path(__file__).resolve().parent
z=zipfile.ZipFile(Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk')))
for unit in [100,101,102,103]:
 n=f'assets/assetbundle/assets/resources/characters/unit_{unit}/builds/3_b_wr.ab'
 e=UnityPy.load(z.read(n))
 for o in e.objects:
  if o.type.name=='MonoBehaviour':
   try:
    t=o.read_typetree()
    if 'controller' in t:print(unit,t)
   except Exception as ex:print(str(ex)[:100])
