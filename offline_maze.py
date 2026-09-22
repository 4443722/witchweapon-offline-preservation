"""One playable maze encounter, using a labelled temporary campaign entry.

JP player observations supply waves; the APK supplies map and enemy identities.
Stats, positions and rewards are local balance. Special enemy skills are not
claimed restored. This does not implement the twelve-stage expedition system.
"""
import base64
import copy
import csv
import io
import json
from offline_seed import ROOT, table, message, proto
from offline_combat import combat_seeds

ENTRY = 3110001003
SOURCE = 3130001026
WIKI = 'https://anywhere.coresv.net/mobile/wiki/witchs_weapon/doku.php?id=結界迷宮'


def decode(seed, name):
    obj = message(name)
    obj.ParseFromString(base64.b64decode(seed['base64']))
    return obj


def maze_seeds(base):
    stage = next(r for r in table('InstanceMobList') if r['ID'] == str(SOURCE))
    mobs = {r['ID']: r for r in table('Mob')}
    basket = decode(base['/combat/mob/info'], 'combatmod.Basket')
    original_mob = copy.deepcopy(basket.MobInfos[0])
    original_type = copy.deepcopy(basket.MobTypeInfos[0])
    original_tree = copy.deepcopy(basket.BehaviorTreeArgumentInfos[0])
    original_spell = copy.deepcopy(basket.SpellInfos[0])
    original_effect = copy.deepcopy(basket.EffectArgumentInfos[0])
    basket.Clear()
    # Short, approachable first sample. These are not original server values.
    names = ['液态金属人形', '玫瑰少女', '灵体·爱丽丝', '暴走族', '忍者喵']
    stats = [(18000,65), (6500,40), (8000,50), (2200,25), (1200,30)]
    identities = []
    for i in range(1,6):
        mid = int(stage['mob'+str(i)])
        rank = int(stage['mob'+str(i)+'_type'])
        row = mobs[str(mid)]
        skill, treeid = 2020100000+i, 8040900000+i
        mob = basket.MobInfos.add(); mob.CopyFrom(original_mob)
        mob.ID=mid; mob.CurType=rank; mob.Level=5; mob.Model=row['model']
        mob.MobTypeInfoNormal=mid; mob.MobTypeInfoElite=mid; mob.MobTypeInfoBoss=mid
        mob.Hp=stats[i-1][0]; mob.PhysicalAttack=stats[i-1][1]; mob.MagicalAttack=stats[i-1][1]
        typ=basket.MobTypeInfos.add(); typ.CopyFrom(original_type)
        typ.ID=mid; typ.BehaviorTreeId=treeid; typ.MobSpell1=skill
        tree=basket.BehaviorTreeArgumentInfos.add(); tree.CopyFrom(original_tree)
        tree.ID=treeid; tree.Argument0=skill
        spell=basket.SpellInfos.add(); spell.CopyFrom(original_spell)
        spell.ID=skill; spell.SpellEffectArgu=skill
        effect=basket.EffectArgumentInfos.add(); effect.CopyFrom(original_effect); effect.ID=skill
        identities.append(dict(id=mid,rank=rank,model=row['model'],label=names[i-1]))
    from offline_enemies import enrich
    enrich(basket)

    # 1: biker; 2: rose+Alice, kill either; 3: five ninjas;
    # 4: rose+metal boss; 5: five ninjas. Exactly fifteen enemies overall.
    composition = [[3], [1,2], [4]*5, [1,0], [4]*5]
    positions = [(3.8,-3.8),(6.2,-4.6),(1.4,-4.6),(5.4,-1.8),(2.2,-1.8)]
    waves=[]
    for wi, enemies in enumerate(composition):
        monsters=[]
        for ni,index in enumerate(enemies):
            item=identities[index]; x,z=positions[ni]
            monsters.append(dict(name=f'Maze_W{wi+1}_{ni+1}',opName=item['model'],givenName=item['label'],
                statID=f"{item['id']}-{item['rank']}-5",appearType=0,PRS=[x,z,180,1],groupID=101,
                ai_config=dict(taunt_list_index=0,can_be_taunt=True,follow_target=''),tag=''))
        trigger=dict(type='KillCount',param='1') if wi==1 else dict(type='WaveClear',param='')
        waves.append(dict(name=f'Wave_{wi}',showMode=0,spawnDelay=0.6,sec=0,kill=999,
                          NextWaveTriggers=[trigger],SubWaves=[],monsters=monsters))
    level=json.loads(base['/combat/mob/json']['body'])
    level['QuestInfo']['sec']=600
    level['QuestInfo']['Triggers'][1]['param']=['600']
    level['MapInfo']['sceneName']='map_1026_outlets'
    level['EnemyLayer'].update(levelID=str(ENTRY),lvMin=5,lvMax=5)
    zone=level['EnemyLayer']['areas'][0]['zones'][0]
    zone.update(entryPR=[3.8,0,-8,0,0,0],navP=[3.8,0,-3.8],waves=waves)
    zone['triggers'][0]['PRS']=[3.8,-6,0,5]
    seeds={f'/combat/mob/info#{ENTRY}':dict(type='application/octet-stream',base64=base64.b64encode(basket.SerializeToString()).decode()),
           f'/combat/mob/json#{ENTRY}':dict(type='application/json',body=json.dumps(level,ensure_ascii=False,separators=(',',':')))}
    evidence=dict(source=WIKI,wiki_entry=1,apk_maze_id=SOURCE,temporary_entry=ENTRY,
                  map=level['MapInfo']['sceneName'],enemies=identities,waves=waves,
                  restored=['map resource','enemy identities and ranks','wave order and counts','kill-one reinforcement'],
                  local=['spawn positions','level 5','HP/attack/defense','600-second limit','1000 gold and 5 XP'],
                  missing=['original special skills including rose reflection','original stat scaling','12-stage maze system'])
    (ROOT/'evidence/maze_trial_config.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),'utf8')
    return seeds


def patch_table(filename, callback, delimiter=',', use_override=False):
    import UnityPy
    name=f'assets/assetbundle/config/clientexel/{filename}.ab'
    src=ROOT/'overrides'/name if use_override else ROOT/'original_parts'/name
    env=UnityPy.load(str(src))
    for obj in env.objects:
        if obj.type.name!='MonoBehaviour':continue
        tree=obj.read_typetree()
        if 'bytes' not in tree:continue
        raw=bytes(tree['bytes'])
        if tree.get('isEncrypt'):raw=bytes(b^255 for b in raw)
        rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig')),delimiter=delimiter))
        callback(rows)
        buf=io.StringIO();csv.writer(buf,delimiter=delimiter,lineterminator='\r\n').writerows(rows)
        raw=('\ufeff'+buf.getvalue()).encode('utf8')
        tree['bytes']=list(bytes(b^255 for b in raw) if tree.get('isEncrypt') else raw)
        obj.save_typetree(tree)
    dest=ROOT/'overrides'/name;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(env.file.save(packer='original'))


def prepare():
    base=combat_seeds()
    path=ROOT/'offline_responses.json';responses=json.loads(path.read_text('utf8'))
    responses.update(base);responses.update(maze_seeds(base))
    from offline_maze_round import round_seeds,make_basket_factory
    responses.update(round_seeds(base,make_basket_factory(base)))
    for route in ['/level/getAllProgress','/game/level/getAllProgress']:
        progress=decode(responses[route],'levelmod.Chaps')
        for chapter in progress.Data:
            for level in chapter.Levels:
                if level.ID==ENTRY:level.Status=True
        responses[route]=dict(type='application/octet-stream',base64=base64.b64encode(progress.SerializeToString()).decode())
    path.write_text(json.dumps(responses,ensure_ascii=False,indent=2),'utf8')

    def instance(rows):
        cols={name:i for i,name in enumerate(rows[0])}
        row=next(r for r in rows if r and r[0]==str(ENTRY))
        for key,value in dict(instance_time_limit='600000',instance_stamina_enter='0',instance_stamina_victory='0',
                              instance_power='0',instance_repeatable='1',instance_mob_config='core_26').items():row[cols[key]]=value
        for key in cols:
            if key.startswith(('instance_loot_','reward_type','reward_id','reward_value','reward_num')):row[cols[key]]=''
    patch_table('instance',instance)
    def mob_list(rows):
        source=next(r for r in rows if r and r[0]==str(SOURCE))
        cols={name:i for i,name in enumerate(rows[0])}
        for i,r in enumerate(rows):
            if r and r[0]==str(ENTRY):
                rows[i]=[str(ENTRY)]+source[1:]
                rows[i][cols['time']]='600'
                for n in range(1,6):rows[i][cols[f'mob{n}_lv']]='5'
    patch_table('instancemoblist',mob_list)
    def dictionary(rows):
        for row in rows:
            if row and row[0]=='1311000100301':row[1]='十二关迷宫'
            if row and row[0]=='1311000100302':row[1]='连续十二关，生命与能量继承。每三关自动补给，通关后可开始新一轮。'
    # Preserve story labels generated immediately before this preparation step.
    patch_table('dictionary',dictionary,'\t',use_override=True)
    # The campaign detail screen displays chapter text rather than instance_name.
    # Label this temporary entry explicitly without renaming the whole chapter.
    from prepare_offline import patch_lua_bundle
    def detail_patch(script):
        anchor='    field:Destroy()\n    PatchModel.SelectLevelDetail_ActivityDataFloor = nil'
        assert anchor in script
        extra=r'''    field:Destroy()
    if tonumber(tostring(instanceId)) == 3110001003 then
        local root = 'Center/LevelDetailPanel/InfoBox/Container/'
        local function label(path, text)
            local node = obj.transform:Find(root .. path)
            if node then node:GetComponent('UILabel').text = text end
        end
        label('LevelInfo/Label_ChapterName', '迷宫试玩·金属与玫瑰')
        label('LevelInfo/Label_ChapterName_EN', 'Maze Trial')
        label('LevelInfo/En_Label_ChapterName', 'Maze Trial')
        label('Label_TaskName', '迷宫试玩')
        label('Task/Target/Label_TaskDesc', '击败五波敌人\\n数值为本地设定，特殊技能暂简化')
    end
    PatchModel.SelectLevelDetail_ActivityDataFloor = nil'''
        return script.replace(anchor,extra,1)
    patch_lua_bundle('assets/assetbundle/lua/lua_projx_patch.ab',{'SelectLevelDetailPatch.lua':detail_patch})
    print('Maze trial prepared:',ENTRY,'<-',SOURCE,'5 waves, 15 enemies')


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT/'tools/python'))
    prepare()
