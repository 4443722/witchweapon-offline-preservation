import json,re
from pathlib import Path
from offline_seed import ROOT
ps=json.loads((ROOT/'evidence/weapon_original_descriptions.json').read_text('utf-8-sig'))
for p in ps:
 if p['id'] in ['1701240102','1701250101','1701250102']:
  print(p['id'],p['name'],re.sub(r'\[[^\]]+\]|#\{[^}]+\}','',p['desc']['spell_desc_floor']))
