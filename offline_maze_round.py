"""Twelve distinct local encounters, reconstructed from the JP maze notes.

Enemy identities/ranks come from the APK roster. Waves follow observed order;
missing exact times, HP thresholds, coordinates and server stats are local rules.
The first implementation uses the accepted outlets arena for all encounters.
"""
import base64
import copy
import json
from offline_seed import ROOT, table, message

ENTRY=3110001003
# Enemy numbers refer to each original InstanceMobList row, starting at 1.
# A tuple after a wave supplies its reinforcement condition for the NEXT wave.
ROUNDS=[
    (26,1,'金属与玫瑰',[[4],([2,3],'KillCount','1'),[5]*5,[2,1],[5]*5]),
    (21,4,'执行人与守护者',[[4],[2,3],[5,4],([1,3],'KillCount','1'),[4]]),
    (8,5,'双首领防线',[[1,3,2],[5],[4,5,5],([3,1],'KillCount','1'),[4]]),
    # Identity 1 (忍镰娘) also opens the floor so leftover Skill_02 is observable
    # without waiting for later waves. Later Time spawn of 117 is unchanged.
    (12,6,'冰霜与驱魔',[[1,4,2,3],[5,5],[5,4],([1,3],'Time','12'),[5,5]]),
    (13,7,'黑暗中的伏击',[[1,3],[4]*5,([2,5,3],'Time','6'),[4]*4,[5],([1],'Time','10'),([3],'Time','8'),[4]*4]),
    (27,8,'天照的反击',[[3,4,5],[2,4,3,5],[4,4],([3],'Time','10'),[1]]),
    (9,9,'歌声与灵体',[[1,3],[4,5],([2],'Time','12'),[3],[4],([2],'Time','10'),([1,4],'KillCount','1'),[5]]),
    (28,10,'召唤者之庭',[[1,3],[4]*4,([2,3],'Time','12'),[5]*4,[4,4],([1,3],'Time','12'),[5]*5]),
    (3,11,'骑士与召唤者',[[5,5],[2],([3],'Time','12'),[5],[1],([4,5],'Time','10'),[5]]),
    (5,13,'长枪与暗月', [([2],'Time','10'),([3],'Time','8'),[5,4,4,4],([1],'Time','10'),[3],[4]*5,[2]]),
    (22,14,'医疗防线',[[4,4],([2,3],'KillCount','1'),[4,4],[5]*4,([3,2],'Time','12'),[1]]),
    (25,17,'三重灵体',[[4],([2,3],'Time','12'),[5]*5,([2,3],'Time','10'),([1],'Time','10'),[5]*4]),
]

def lua_rosters():
    rows={r['ID']:r for r in table('InstanceMobList')}
    groups=[]
    for core,*_ in ROUNDS:
        row=rows[str(3130001000+core)]
        groups.append('{'+','.join('{'+row[f'mob{i}']+','+row[f'mob{i}_type']+'}' for i in range(1,6))+'}')
    return '{'+','.join(groups)+'}'


def round_seeds(base, make_basket):
    """make_basket(stage, round_index) returns a native Basket and identities."""
    stage_rows={r['ID']:r for r in table('InstanceMobList')}
    output={}; report=[]
    for number,(core,wiki,title,composition) in enumerate(ROUNDS,1):
        stage=stage_rows[str(3130001000+core)]
        basket,identities=make_basket(stage,number)
        level=json.loads(base['/combat/mob/json']['body'])
        level['QuestInfo']['sec']=600
        level['QuestInfo']['Triggers'][1]['param']=['600']
        level['MapInfo']['sceneName']='map_1026_outlets'
        level['EnemyLayer'].update(levelID=str(ENTRY),lvMin=5,lvMax=5)
        zone=level['EnemyLayer']['areas'][0]['zones'][0]
        zone.update(entryPR=[3.8,0,-8,0,0,0],navP=[3.8,0,-3.8])
        zone['triggers'][0]['PRS']=[3.8,-6,0,5]
        positions=[(3.8,-3.8),(6.2,-4.6),(1.4,-4.6),(5.4,-1.8),(2.2,-1.8),(7,-2)]
        waves=[]
        for wi,entry in enumerate(composition):
            indices,kind,param=entry if isinstance(entry,tuple) else (entry,'WaveClear','')
            if kind=='Time':kind='TimeLimit'
            mobs=[]
            for ni,index in enumerate(indices):
                item=identities[index-1];x,z=positions[ni%len(positions)]
                mobs.append(dict(name=f'Round{number}_W{wi}_{ni}',opName=item['model'],
                    givenName=item['label'],statID=f"{item['id']}-{item['rank']}-5",
                    appearType=0,PRS=[x,z,180,1],groupID=101,
                    ai_config=dict(taunt_list_index=0,can_be_taunt=True,follow_target=''),tag=''))
            waves.append(dict(name=f'Wave_{wi}',showMode=0,spawnDelay=0.6,sec=0,kill=999,
                NextWaveTriggers=[dict(type=kind,param=param)],SubWaves=[],monsters=mobs))
        zone['waves']=waves
        output[f'/combat/mob/info#{ENTRY}@{number}']=dict(type='application/octet-stream',
            base64=base64.b64encode(basket.SerializeToString()).decode())
        output[f'/combat/mob/json#{ENTRY}@{number}']=dict(type='application/json',
            body=json.dumps(level,ensure_ascii=False,separators=(',',':')))
        report.append(dict(round=number,title=title,wiki_entry=wiki,apk_source=int(stage['ID']),
            enemy_count=sum(len(w['monsters']) for w in waves),waves=waves,identities=identities))
    (ROOT/'evidence/maze_round_config.json').write_text(json.dumps(dict(
        source='https://anywhere.coresv.net/mobile/wiki/witchs_weapon/doku.php?id=結界迷宮',
        local_rules=['single accepted arena','spawn coordinates','stats','reinforcement timers',
                     'HP-threshold reinforcements temporarily timed','two-area paths flattened'],
        rounds=report),ensure_ascii=False,indent=2),'utf8')
    return output


def make_basket_factory(base):
    """Share the accepted native data shape; enemy skill enrichment is separate."""
    original=message('combatmod.Basket')
    original.ParseFromString(base64.b64decode(base['/combat/mob/info']['base64']))
    mobs={r['ID']:r for r in table('Mob')}
    def make(stage,number):
        basket=message('combatmod.Basket'); identities=[]
        for i in range(1,6):
            mid=int(stage['mob'+str(i)]);rank=int(stage['mob'+str(i)+'_type'])
            row=mobs[str(mid)];skill=2020900000+number*10+i;treeid=8040901000+number*10+i
            mob=basket.MobInfos.add();mob.CopyFrom(original.MobInfos[0])
            mob.ID=mid;mob.CurType=rank;mob.Level=5;mob.Model=row['model']
            mob.MobTypeInfoNormal=mid;mob.MobTypeInfoElite=mid;mob.MobTypeInfoBoss=mid
            mob.Hp={1:1800,2:7000,3:16000}[rank]
            mob.PhysicalAttack=mob.MagicalAttack={1:25,2:42,3:65}[rank]
            typ=basket.MobTypeInfos.add();typ.CopyFrom(original.MobTypeInfos[0])
            typ.ID=mid;typ.BehaviorTreeId=treeid;typ.MobSpell1=skill
            tree=basket.BehaviorTreeArgumentInfos.add();tree.CopyFrom(original.BehaviorTreeArgumentInfos[0])
            tree.ID=treeid;tree.Argument0=skill
            spell=basket.SpellInfos.add();spell.CopyFrom(original.SpellInfos[0])
            spell.ID=skill;spell.SpellEffectArgu=skill
            effect=basket.EffectArgumentInfos.add();effect.CopyFrom(original.EffectArgumentInfos[0]);effect.ID=skill
            identities.append(dict(id=mid,rank=rank,model=row['model'],label=row['developer_name']))
        from offline_enemies import enrich
        enrich(basket)
        return basket,identities
    return make
