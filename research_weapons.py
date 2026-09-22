import csv,json,sys
from offline_seed import table,POOL
D={r['ID']:r['content_chinese'] for r in csv.DictReader(open('decoded/config/clientexel/Dictionary.txt',encoding='utf-8-sig'),delimiter='\t')}
S={r['ID']:r for r in table('Spell')}
ws={r['ID']:r for r in table('ServantWeapon') if r['channel_group'] in ('','0','25') and r['can_see']!='0'}
lines=[]
for w in ws.values():
 if not w['servant_id']:continue
 s=S.get(w['spell_weapon1'],{})
 desc={k:D.get(v,v) for k,v in s.items() if 'name' in k or 'desc' in k}
 lines.append({'id':w['ID'],'name':D.get(w['weapon_name']), 'type':w['weapon_type'],'normal':w['normal_attack1'],'spell':w['spell_weapon1'],'desc':desc})
open('evidence/weapon_original_descriptions.json','w',encoding='utf-8-sig').write(json.dumps(lines,ensure_ascii=False,indent=2))
for typ in ('combatmod.TriggerInfo','combatmod.Basket'):
 try:
  d=POOL.FindMessageTypeByName(typ);print(typ,[(f.name,f.message_type and f.message_type.full_name) for f in d.fields])
 except Exception as e:print(e)
a=json.load(open('evidence/choice_before.json',encoding='utf-8-sig'));b=json.load(open('evidence/choice_after.json',encoding='utf-8-sig'))
print('item delta',[(k,v-a['items'].get(k,0)) for k,v in b['items'].items() if v!=a['items'].get(k)])
print('other changed',[(k,v) for k,v in b.items() if k not in ('items','requestCache') and a.get(k)!=v])
print('current images',[(s['ServantCardID'],s.get('Images')) for s in b['servants']])
