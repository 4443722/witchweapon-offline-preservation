"""Local economy catalog, using APK identities and progression costs."""
import base64,json
from offline_seed import ROOT,table,proto,message

MUTATIONS=['/servant/exp','/servant/rank','/servant/star','/servant/starpoint',
 '/servant/spell','/servant/image/change','/servant/compose','/servant/equip',
 '/servant/weapon','/servant/weapon/compose','/servant/weapon/promote',
 '/servant/weapon/spell/promote','/servant/weapon/skin/change','/servant/favor/exp',
 '/backpack/item/use','/resource/sell/gold','/role/board/change','/role/rename','/fashion/compose','/fashion/runes/update']

def prepare():
    from offline_maze import patch_table
    def free_draw(rows):
        columns={name:i for i,name in enumerate(rows[0])}
        for row in rows[3:]:
            if row and row[0] in {'DRAW_COST_SINGLE_GOLD','DRAW_COST_MULTI_GOLD_FIVE',
                    'DRAW_COST_MULTI_GOLD_TEN','DRAW_COST_SINGLE_DIAMOND',
                    'DRAW_COST_MULTI_DIAMOND','DRAW_COOLDOWN_GOLD'}:
                row[columns['value3']]='0'
            elif row and row[0]=='PROMOTE_UNLOCK_RANK':row[columns['value3']]='1'
    patch_table('constant',free_draw)
    def supply_text(rows):
        labels={'14135000401':'离线补给箱','14503012401':'离线补给箱',
            '14700000101':'免费补给','14700000102':'离线补给商店',
            '14135000404':'免费领取后立即将全部材料与装备储备补至9999，并获得100万金币。可反复领取，无需在背包拆开。'}
        for row in rows:
            if row and row[0] in labels:row[1]=labels[row[0]]
    patch_table('dictionary',supply_text,'\t',use_override=True)
    def supply_item(rows):
        c={name:i for i,name in enumerate(rows[0])}
        for row in rows[3:]:
            # Legacy display-only chest subtypes 5/8 are filtered by the
            # current PackagePanelController. Subtype 14 uses its original
            # fixed-reward UIChest path, with exactly the same reward columns.
            if row and row[c['item_type']]=='9' and row[c['item_sub_type']] in ('5','8'):
                row[c['item_sub_type']]='14'
            if row and row[0]=='40350004':
                row[c['item_set_type1']]='13'
                row[c['item_set_id1']]=''
                row[c['item_set_num1']]='1000000'
    patch_table('item',supply_item)
    def supply_structure(rows):
        c={name:i for i,name in enumerate(rows[0])}
        for row in rows[3:]:
            if row and row[c['channel_group']]=='25':
                row[c['name']]='离线补给商店'
                row[c['structure']]='14700000101|47000001'
    patch_table('shopstructure',supply_structure)
    def supply_tabs(rows):
        c={name:i for i,name in enumerate(rows[0])}
        for row in rows[3:]:
            if row and row[c['channel_group']]=='25':
                row[c['format']]='4'
                for i in range(1,11):row[c['shop_set'+str(i)]]='44000001' if i==1 else ''
    patch_table('shopbigset',supply_tabs)
    def supply_stock(rows):
        c={name:i for i,name in enumerate(rows[0])}
        for row in rows[3:]:
            if row and row[0]=='4501010003':row[c['max_total_num']]='999999'
    patch_table('shop',supply_stock)
    p=ROOT/'offline_responses.json';responses=json.loads(p.read_text('utf8'))
    role=message('rolemod.ComplexRole')
    role.ParseFromString(base64.b64decode(responses['/role/role']['base64']))
    fashions={r['ID']:r for r in table('Fashion') if r['channel_group'] in ('','0','25')}
    role.ClearField('FashionInstances')
    for fid in fashions:
        fashion=role.FashionInstances.add(FashionCardID=int(fid),RoleID=1,Own=True)
        fashion.FashionRunes.Runes.extend([0]*9)
    # These original lobby interactions and display characters have no
    # expiring server gates in the standalone edition.
    for field,tablename in [('Action','Interaction'),('Board','Kanban')]:
        role.roleInstanceProto.ClearField(field)
        unlocked={int(r['ID']) for r in table(tablename)
            if r['channel_group'] in ('','0','25')}
        # ObservablePlayer reads a 1-based indexed flag array, not IDs.
        getattr(role.roleInstanceProto,field).extend(
            1 if index in unlocked else 0 for index in range(1,max(unlocked)+1))
    role.roleInstanceProto.CurBoard=1
    responses['/role/role']={'type':'application/octet-stream','base64':base64.b64encode(role.SerializeToString()).decode()}
    responses['/game/role/role']=responses['/role/role']
    svs={r['ID']:r for r in table('Servant') if r['channel_group'] in ('','0','25') and r['can_see']=='1'}
    weapons={r['ID']:r for r in table('ServantWeapon') if r['channel_group'] in ('','0','25') and r['can_see']!='0'}
    spells={r['ID']:r for r in table('Spell')}
    achievements={r['ID']:r for r in table('Achievement')}
    favor_quests={r['favorability_quest']:dict(servant=int(sid),
        amount=50*max(0,int(r['favorability_level'] or 3)-1))
        for sid,r in svs.items() if r.get('favorability_quest') in achievements}
    def local_favor_conditions(rows):
        c={name:i for i,name in enumerate(rows[0])}
        for row in rows[3:]:
            if row and row[0] in favor_quests:
                row[c['achievement_type']]='082'
                row[c['achievement_argu1']]='1'
                row[c['achievement_argu3']]=str(favor_quests[row[0]]['servant'])
                row[c['attachment_value1']]=str(favor_quests[row[0]]['amount'])
    patch_table('achievement',local_favor_conditions)
    favor_text_ids={achievements[q][k] for q in favor_quests
        for k in ('achievement_name','achievement_desc','achievement_tips') if achievements[q].get(k)}
    def local_favor_text(rows):
        for row in rows:
            if row and row[0] in favor_text_ids:row[1]='拥有该魔女即可领取离线羁绊奖励'
    patch_table('dictionary',local_favor_text,'\t',use_override=True)
    templates={}
    for sid,row in svs.items():
        ws=[dict(WeaponCardID=int(wid),RoleID=1,WeaponSpellPromoteLv=1,Skins=1,CurSkin=1)
            for wid,w in weapons.items() if w['servant_id']==sid]
        templates[sid]=proto('svmod.ServantInstanceProto',ServantCardID=int(sid),RoleID=1,
            Level=5,Rank=1,Star=1,SpellLv=[1]*5,FavorLevel=1,Images=1,CurImage=1,
            ImagesForFavor=1,WeaponLv=5,Weapons=ws,Skins=1)['base64']
    items={r['ID']:{k:int(r.get(k) or 0) for k in ['servant_exp','weapon_value','favorability_value','stamina','act_stamina','item_type','item_sub_type','sell_price','max_stack']}
        for r in table('Item')}
    for row in table('Item'):
        items[row['ID']]['rewards']=[dict(type=int(row['item_set_type'+str(i)]),
            id=int(row['item_set_id'+str(i)] or 0),
            value=int(row['item_set_value'+str(i)] or 0),
            count=int(row['item_set_num'+str(i)] or 0))
            for i in range(1,16) if row.get('item_set_type'+str(i))]
    levels={r['ID']:int(r['levelup_exp'] or 0) for r in table('ServantLevelInfo')}
    # The original growth controller dereferences every servant's favor quest
    # before setting level/weapon fields, even when that quest is not unlocked.
    # Offline favor conditions are permanent; LocalEconomy overlays each saved
    # claim state. Tutorial completion remains separate from bond rewards.
    tasks=message('achievemod.Result')
    tasks.ParseFromString(base64.b64decode(responses['/task/all']['base64']))
    job_ids={j.ID for j in tasks.Jobs}
    for r in svs.values():
        q=int(r.get('favorability_quest') or 0)
        if q and q not in job_ids:
            tasks.Jobs.add(ID=q,Status=0,Valid=1,Guide=False,TypeID='82');job_ids.add(q)
    for job in tasks.Jobs:
        if str(job.ID) in favor_quests:job.Status=0;job.Valid=1;job.TypeID='82'
    known_metas={m.JobID for m in tasks.Metas}
    for q in favor_quests:
        if int(q) not in known_metas:tasks.Metas.add(TorD=8,TypeID='82',JobID=int(q),Meta=1)
    responses['/task/all']={'type':'application/octet-stream','base64':base64.b64encode(tasks.SerializeToString()).decode()}
    responses['/game/task/all']=responses['/task/all']
    responses['_catalog']=dict(servants=templates,items=items,levels=levels,
        favorQuests=favor_quests,
        favorCaps={sid:int(r['favorability_level'] or 3) for sid,r in svs.items()},
        favorAttrs={sid:[dict(level=int(a['ID'][-2:]),type=int(a['attribute_type']),value=int(a['attribute_value']))
            for a in table('ServantFavorability') if a['ID'].startswith(r['favorability_info'])]
            for sid,r in svs.items()},
        weaponLevels={sid:{str(int(r['ID'][-3:])):int(r['levelup_exp'] or 0)
            for r in table('ServantWeaponAttr') if r['ID'].startswith(row['weapon_info'])}
            for sid,row in svs.items()},
        weaponMods={sid:{str(int(r['ID'][-3:])):int(r['weapon_attack_modulus'] or 10000)
            for r in table('ServantWeaponAttr') if r['ID'].startswith(row['weapon_info'])}
            for sid,row in svs.items()},
        ranks={sid:{str(int(r['rank'])):dict(minLevel=int(r['min_level']),
            equips=[int(r['equipment'+str(i)] or 0) for i in range(1,7)])
            for r in table('ServantRankInfo') if r['ID'].startswith(row['rank_info'])}
            for sid,row in svs.items()},
        stars={sid:{r['star']:dict(gold=int(r['cost'] or 0),
            item=int(r['levelup_item_id'] or 0),count=int(r['levelup_item_num'] or 0))
            for r in table('ServantStarInfo') if r['ID'].startswith(row['star_info'])}
            for sid,row in svs.items()},
        fashions={fid:int(r['serial']) for fid,r in fashions.items()},
        fashionAttrs={str(fid):[
            dict(type=int(sp.get('attribute_type'+str(i)) or 0),
                 value=int(sp.get('attribute_init_value'+str(i)) or 0))
            for i in (1,2,3)
            if int(sp.get('attribute_type'+str(i)) or 0) and int(sp.get('attribute_init_value'+str(i)) or 0)]
            for fid,r in fashions.items()
            for sp in [spells.get((r.get('spell') or '').strip(), {})]
            if (sp.get('is_attribute_type') or '0')=='1'},
        boards=sorted({int(r['ID']) for r in table('Kanban') if r['channel_group'] in ('','0','25')}),
        roleLevels={r['ID']:int(r['levelup_exp'] or 0) for r in table('CharacterLevelInfo')},
        equips={r['ID']:{k:int(r[k] or 0) for k in ('weapon_value','sell_price')} for r in table('ServantEquip')},
        weapons={wid:{'servant':int(w['servant_id']),'rare':int(w['weapon_rare'] or 1),
            'awakenGold':int(w['promote1_gold'] or 0),
            'awakenItems':[[int(w['promote1_item'+str(i)] or 0),int(w['promote1_item_num'+str(i)] or 0)] for i in (1,2,3)],
            'physical':[int(w['weapon_physical_attack'+str(i)] or 0) for i in (1,2)],
            'magical':[int(w['weapon_magical_attack'+str(i)] or 0) for i in (1,2)]}
            for wid,w in weapons.items()})
    for route in MUTATIONS:
        responses[route]=proto('actionmod.CommonInfo',Result='ok')
        responses['/game'+route]=responses[route]
    responses['/task/update']=proto('lootmod.LootResult')
    responses['/game/task/update']=responses['/task/update']
    for route in ['/draw/gold/single','/draw/gold/ten','/draw/rmb/single',
                  '/draw/rmb/ten','/draw/activity','/draw/activity/special','/guide/draw']:
        responses[route]=proto('lootmod.LootResult')
        responses['/game'+route]=responses[route]
    responses['/draw/rate/get']=proto('ratemod.RateInfos')
    responses['/game/draw/rate/get']=responses['/draw/rate/get']
    # Original shop UI, permanent free supply item. No payment/order SDK path.
    supply_set=dict(SetID=44000001,Open=True,AutoRefresh=False,ManualRefresh=False,
        Shops=[dict(ShopID=4501010003,Visible=True,Number=999999,
            Items=[dict(ID=45030124,Price=0,Number=999999,Discount=100)])])
    for route in ['/shop/allShopSet','/shop/getSetData']:
        responses[route]=proto('shopmod.AllSets',Data=[supply_set],CanPay=False)
        responses['/game'+route]=responses[route]
    responses['/shop/buy']=proto('shopmod.BuyResult',Result='ok')
    responses['/game/shop/buy']=responses['/shop/buy']
    p.write_text(json.dumps(responses,ensure_ascii=False,indent=2),'utf8')
    print('Local progression catalog',len(templates),'servants',len(items),'items')
