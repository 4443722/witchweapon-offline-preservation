import json,zipfile,sys,os
sys.path.insert(0,'tools/python')
import UnityPy
from offline_seed import table,ROOT
z=zipfile.ZipFile(Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk')))
ws={r['ID']:r for r in table('ServantWeapon') if r['channel_group'] in ('','0','25') and r['can_see']!='0'}
rows=[]
for w in ws.values():
 if not w['servant_id']:continue
 serial=(int(w['servant_id'])//100)%1000
 name=f"assets/assetbundle/assets/resources/characters/unit_{serial}/{w['weapon_prefab']}/{w['weapon_type']}_b_wr.ab"
 try:
  env=UnityPy.load(z.read(name))
  for o in env.objects:
   if o.type.name=='MonoBehaviour':
    t=o.read_typetree()
    if 'controller' in t:
     rows.append(dict(id=w['ID'],asset=name,builder=t));print(w['ID'],t.get('controller'),t.get('overrideController'),t.get('animationClips'))
 except KeyError:print('missing',name)
(ROOT/'evidence/weapon_builder_original.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf8')
