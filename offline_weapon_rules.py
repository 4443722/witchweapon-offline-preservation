"""Additional, explicit weapon mechanics. No catch-all damage substitute.

Ratios/thresholds come from the shipped Chinese descriptions; missing flat
values and periodic scheduling are documented local choices. Original XML is
used where it already expresses the relevant calculation.
"""
import copy
import xml.etree.ElementTree as ET


def profiles():
    return {
        1701050102:dict(name='放课后LIVE',kind='resource_support',event='attack',
            template='Servant105_WeaponSkill_04',args={4:340,5:28},self=True,
            local_rules=['magic uses the local 10000-point sharpness scale']),
        1701080102:dict(name='噩梦之棘',kind='pure_counter',event='hurt',magic=True,damage=24000),
        1701100101:dict(name='青金石刻印',kind='stack_extra',event='attack'),
        1701120101:dict(name='闪电链',kind='damage',event='normal',
            magic=True,damage=13000,
            local_rules=['chain/3-hit gate omitted; extra magic pack is on the cloned normal']),
        1701020102:dict(name='核子狂欢',kind='damage',event='normal',damage=44000,
            local_rules=['jump-smash fan omitted; extra physical pack is on the cloned normal']),
        1701060102:dict(name='超合金HomeRun',kind='damage',event='normal',damage=8000,
            local_rules=['3-bounce delayed ball omitted; extra physical pack is on the cloned normal']),
        1701400101:dict(name='哉生既死',kind='damage',event='normal',magic=True,damage=10000,
            local_rules=['combo 3/5/7 forced crit omitted; extra magic pack is on the cloned normal']),
        1701430101:dict(name='红龙',kind='damage',event='normal',damage=6000,
            local_rules=['nearby-enemy switch stacks omitted; extra physical pack is on the cloned normal']),
        1701140102:dict(name='剑气流星',kind='stored_burst',event='attack',
            local_rules=['three stored layers discharge on a two-second native timer']),
        1701220102:dict(name='合金撬棍',kind='normal_armor',event='normal',
            local_rules=['missing flat attack bonus is 30']),
        1701240101:dict(name='赤月血霞',kind='normal_critical',event='normal'),
        1701240102:dict(name='高频电刃',kind='low_hp',event='normal',
            template='Servant124_WeaponSkill_01',args={4:30,5:5,6:1,7:15,8:2},
            local_rules=['Skill_01 missing-HP pack is inside the cloned-normal hit EffectList; Argument6=1 so bufflayer is 0-10000 across missing HP; Skill_02 low-HP aura stays on its timer']),
        1701250102:dict(name='背刺',kind='backstab',event='attack',
            template='Servant125_WeaponSkill_06',args={4:10000,5:25000,6:0,7:0}),
        1701290101:dict(name='AMG-79',kind='normal_pure',event='normal'),
        1701290102:dict(name='孤敌增伤',kind='crowd_pure',event='attack',
            template='Servant129_WeaponSkill_01',args={4:4000,5:2000,6:200,7:25},
            local_rules=['missing flat pure damage is 200 + 25 per skill level']),
        1701300102:dict(name='暴击迸射',kind='critical_area',event='critical',
            template='Servant130_WeaponSkill_04',args={4:10000,5:7000,6:0,7:0,8:300}),
        1701310101:dict(name='流血',kind='dot',event='normal',damage=10000,period=1500,duration=3000,
            local_rules=['DOT is applied by the cloned dual-wield normal, not EventTrigger; Attack/Hit/Damage delegates stay on the defender']),
        1701320101:dict(name='毒素',kind='dot',event='normal',damage=10500,magic=True,period=1500,duration=3000,
            local_rules=['same cloned-normal CreateBuffPack path as 流血, using the one-hand graph']),
        1701150102:dict(name='天国玫瑰',kind='damage',event='normal',magic=True,damage=5800,
            local_rules=['silence splash is omitted until a silence sample exists; extra hit is on the cloned normal']),
        1701230101:dict(name='冰结棱镜',kind='critical_area',event='critical',
            template='Servant130_WeaponSkill_04',args={4:10000,5:8500,6:0,7:0,8:500},
            local_rules=['original 3 shards cap 2 per target; local rule reuses the verified crit-area graph at 5m']),
        # Remaining exclusives reuse the shipped ServantXXX_WeaponSkill graphs.
        # Extra-on-normal packs stay only where the original extra sits on the
        # dual-wield/one-hand normal (EventTrigger cannot see those hits).
        1701000102:dict(name='水银波纹',kind='native',event='native',
            buffs=[dict(type=10,args={4:-6000,9:-6000,14:-6000,19:0,20:0,22:943},duration=750)],
            parts=[dict(template='Servant100_WeaponSkill',event='aura',self_cast=True,args={1:'$buff'})],
            local_rules=['ranged-only gate is not in the 100 graph; 60% uses BuffType 10 with cap 943']),
        1701010102:dict(name='红髓勾玉',kind='native',event='native',
            buffs=[dict(type=22,args={4:3,5:10000,6:458,7:78},duration=5000,stack=3)],
            normal_extra=dict(magic=True,damage=13500,flat=90,convert_magic=True),
            parts=[dict(template='Servant101_WeaponSkill',event='attack',rate=7500,args={4:13500,5:10000,6:10,7:16,1:'$buff'})],
            local_rules=['75% extra uses combatRate; death-to-shield waits on kill event Argument, shield buff is applied with the extra hit']),
        1701010103:dict(name='铃音溢散',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=5000,positive=False,stack=1)],
            parts=[
                dict(template='Servant101_WeaponSkill_02',event='attack',args={1:'$buff'}),
                dict(template='Servant101_WeaponSkill_07',event='aura',suffix='_Pulse',
                     args={4:8000,5:10000,6:6,7:14,8:300},trigger_extra=dict(TimerTime=1000)),
                dict(template='Servant101_WeaponSkill_07',event='attack',times=3,suffix='_Third',
                     args={4:8000,5:10000,6:6,7:14,8:300}),
            ]),
        1701060101:dict(name='布偶转化',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=8000,positive=False)],
            parts=[
                dict(template='Servant106_WeaponSkill_05',event='attack',args={1:'$buff'}),
                dict(template='Servant106_WeaponSkill_03',event='attack',rate=3400,suffix='_Bear',
                     args={1:'$mob'}),
            ]),
        1701070102:dict(name='生命火焰',kind='native',event='native',
            parts=[
                dict(template='Servant107_WeaponSkill_05',event='aura',
                     args={4:200,5:10000,6:40,7:24,8:300,9:250000,10:750000},
                     trigger_extra=dict(TimerTime=500)),
                dict(template='Servant107_WeaponSkill_04',event='aura',suffix='_Pet',
                     args={1:'$buff',2:'$buff'},trigger_extra=dict(TimerTime=500)),
            ],
            buffs=[dict(type=99,args={},duration=750)]),
        1701080101:dict(name='极黑法球',kind='native',event='native',
            parts=[
                dict(template='Servant108_WeaponSkill_01',event='attack',times=4,args={1:'$buff'}),
                dict(template='Servant108_WeaponSkill_02',event='aura',suffix='_Orb',
                     args={4:10500,5:10000,6:-4,7:7,8:180},trigger_extra=dict(TimerTime=500)),
            ],
            buffs=[dict(type=99,args={},duration=5000)]),
        1701090101:dict(name='禁断领域',kind='native',event='native',
            buffs=[dict(type=4,args={4:5,8:10000},duration=4000,positive=False)],
            parts=[dict(template='Servant109_WeaponSkill_01',event='hurt',rate=7500,
                        args={1:'$buff',4:36000,5:10000,6:29,7:30,8:3500,9:400})]),
        1701090102:dict(name='水痕格挡',kind='native',event='native',
            buffs=[dict(type=10,args={4:-2000,9:-2000,14:-2000,19:0,20:0,22:316},duration=750)],
            parts=[dict(template='Servant109_WeaponSkill',event='hurt',self_cast=True,args={1:'$buff'})],
            local_rules=['melee-only is not a separate 109 graph; BuffType 10 cap is Spell.csv 261+11*5']),
        1701100102:dict(name='荣光虔诚',kind='native',event='native',
            buffs=[
                dict(slot=0,type=99,args={},duration=600000,stack=40),
                dict(slot=1,type=99,args={},duration=600000,stack=40),
            ],
            parts=[
                dict(template='Servant110_WeaponSkill_02',event='attack',args={1:'$buff',2:'$buff1'}),
                dict(template='Servant110_WeaponSkill_04',event='hurt',suffix='_Piety',args={1:'$buff1',2:'$buff'}),
                dict(template='Servant110_WeaponSkill_05',event='off',suffix='_Switch',
                     args={1:'$buff',2:'$buff1',4:4000,5:10000,6:21,7:16,8:90,9:10000,10:352,11:2}),
            ]),
        1701100103:dict(name='汐焰',kind='native',event='native',
            buffs=[
                dict(slot=0,type=99,args={},duration=2000,stack=20),
                dict(slot=1,type=99,args={},duration=600000,stack=20),
            ],
            parts=[
                dict(template='Servant110_WeaponSkill_07',event='attack',times=3,args={1:'$buff'}),
                dict(template='Servant110_WeaponSkill_10',event='aura',suffix='_Ring',
                     args={1:'$buff',4:7800,5:10000,6:21,7:16},trigger_extra=dict(TimerTime=500)),
                dict(template='Servant110_WeaponSkill_08',event='off',suffix='_Gem',args={1:'$buff',2:'$buff1',3:'$buff1'}),
            ]),
        1701110102:dict(name='不屈信仰',kind='native',event='native',
            buffs=[
                dict(slot=0,type=10,args={4:-6000,9:-6000,14:-6000,19:0,20:0,22:2200},duration=750,stack=1),
                dict(slot=1,type=4,args={4:5,8:10000},duration=5000,positive=False),
                dict(slot=2,type=99,args={},duration=600000,stack=3),
            ],
            parts=[
                dict(template='Servant111_WeaponSkill_01',event='on',self_cast=True,
                     args={1:'$buff',2:'$buff1',3:'$buff2'}),
                dict(template='Servant111_WeaponSkill_02',event='on',suffix='_Taunt',args={}),
                dict(template='Servant111_WeaponSkill_04',event='hurt',times=2,suffix='_Ring',self_cast=True,args={1:'$buff2'}),
                dict(template='Servant111_WeaponSkill_03',event='off',suffix='_Burst',
                     args={1:'$buff2',2:'$buff1',3:'$buff1',4:6000,5:1200,6:400}),
            ]),
        1701120102:dict(name='脉冲雷霆',kind='native',event='native',
            buffs=[dict(type=3,args={4:1,5:15,8:2000},duration=600000,stack=99)],
            parts=[
                dict(template='Servant112_WeaponSkill_04',event='attack',self_cast=True,args={1:'$buff',4:3}),
                dict(template='Servant112_WeaponSkill_01',event='global_attack',suffix='_Spend',self_cast=True,args={1:'$buff'}),
                dict(template='Servant112_WeaponSkill',event='attack',suffix='_Slow',args={1:'$buff'}),
            ]),
        1701130101:dict(name='时计星辉',kind='native',event='native',
            buffs=[dict(type=3,args={4:1,5:17,8:2000,13:18,16:2000},duration=600000,stack=99)],
            parts=[
                dict(template='Servant113_WeaponSkill_02',event='sheathed',self_cast=True,
                     args={1:'$buff',4:2000,5:10000,6:3500,7:20,8:39,9:10000},
                     trigger_extra=dict(TimerTime=2000)),
            ]),
        1701140101:dict(name='狂血',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=750,stack=20)],
            normal_extra=dict(magic=True,damage=4500,flat=8),
            parts=[
                dict(template='Servant114_WeaponSkill_01',event='attack',self_cast=True,args={4:3,5:1}),
                dict(template='Servant114_WeaponSkill_03',event='aura',self_cast=True,args={1:'$buff',4:500}),
            ]),
        1701150101:dict(name='神之戒律',kind='native',event='native',
            buffs=[dict(type=4,args={4:5,8:10000},duration=4000,positive=False)],
            parts=[
                dict(template='Servant115_WeaponSkill_02',event='hurt',
                     args={4:50000,5:10000,6:22,7:25}),
                dict(template='Servant115_WeaponSkill',event='hurt',suffix='_Silence',
                     args={1:'$buff'}),
            ]),
        1701170101:dict(name='裂解程式',kind='native',event='native',
            buffs=[dict(type=1,args={4:7500,5:10000,14:1,15:1,16:4,17:1},duration=4000,stack=5,positive=False,
                        buff_extra=dict(PeriodicTime=2000,BuffGroup='7'))],
            parts=[
                dict(template='Servant117_WeaponSkill',event='attack',times=3,args={1:'$buff'}),
                dict(template='Servant117_WeaponSkill_01',event='off',suffix='_Blast',
                     args={1:'$buff',4:12000,5:10000,6:25,7:18,8:500}),
            ]),
        1701190101:dict(name='暗灵冰弹',kind='native',event='native',
            parts=[
                dict(template='Servant119_WeaponSkill',event='on',args={1:'$mob'}),
                dict(template='Servant119_WeaponSkill_02',event='attack',suffix='_Bolt',args={1:'$mob'}),
            ]),
        1701190102:dict(name='血之契约',kind='native',event='native',
            buffs=[dict(type=9,args={10:8000,13:1},duration=3000)],
            parts=[dict(template='Servant119_WeaponSkill_03',event='hurt',self_cast=True,args={1:'$buff'})]),
        1701200102:dict(name='尸弹馈赠',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=600000,stack=4,positive=False)],
            parts=[
                dict(template='Servant120_WeaponSkill_02',event='attack',times=4,args={1:'$buff',4:18000,5:10000,6:20,7:15}),
                dict(template='Servant120_WeaponSkill_03',event='global_attack',suffix='_Bomb',
                     args={1:'$buff',4:8500,5:10000,6:26,7:18}),
            ]),
        1701210101:dict(name='金色追想',kind='native',event='native',
            buffs=[dict(type=3,args={4:1,5:17,8:2000,13:18,16:2000},duration=600000,stack=99)],
            parts=[
                dict(template='Servant121_WeaponSkill',event='attack',self_cast=True,args={1:'$buff',4:3}),
                dict(template='Servant121_WeaponSkill_01',event='global_attack',suffix='_Hold',self_cast=True,args={1:'$buff',4:0}),
            ]),
        1701210102:dict(name='星辰灌注',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=600000,stack=99)],
            parts=[
                dict(template='Servant121_WeaponSkill',event='attack',self_cast=True,args={1:'$buff',4:2}),
                dict(template='Servant121_WeaponSkill_03',event='off',suffix='_Heal',self_cast=True,args={1:'$buff'}),
                dict(template='Servant121_WeaponSkill_04',event='off',suffix='_Shard',args={4:500,5:10,6:2}),
            ]),
        1701220101:dict(name='战术指导',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=600000,positive=False)],
            parts=[
                dict(template='Servant122_WeaponSkill_01',event='attack',times=3,args={1:'$buff'}),
                dict(template='Servant122_WeaponSkill_02',event='aura',suffix='_Taunt',args={}),
                dict(template='Servant122_WeaponSkill_05',event='hurt',suffix='_MarkDmg',args={4:98,5:72}),
            ]),
        1701230102:dict(name='拉普拉斯风切',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=600000,stack=10)],
            parts=[
                dict(template='Servant123_WeaponSkill_01',event='attack',self_cast=True,args={1:'$buff'}),
                dict(template='Servant123_WeaponSkill_06',event='attack',suffix='_Cut',
                     args={4:3600,5:10000,6:21,7:15}),
                dict(template='Servant123_WeaponSkill_07',event='attack',times=3,suffix='_Storm',
                     args={4:3600,5:10000,6:21,7:15}),
                dict(template='Servant123_WeaponSkill_08',event='attack',times=10,suffix='_Repel',args={4:300}),
            ]),
        1701250101:dict(name='幽冥骑士',kind='native',event='native',
            parts=[dict(template='Servant125_WeaponSkill_01',event='on',args={1:'$mob',4:10000,5:10000})]),
        1701280101:dict(name='潮汐赐福',kind='native',event='native',
            buffs=[
                dict(slot=0,type=3,args={4:1,5:25,8:6000,13:26,16:6000},duration=600000,stack=8),
                dict(slot=1,type=99,args={},duration=750),
            ],
            parts=[
                dict(template='Servant128_WeaponSkill_01',event='attack',self_cast=True,args={1:'$buff',2:'$buff1'}),
                dict(template='Servant128_WeaponSkill_02',event='on',self_cast=True,suffix='_Active',args={1:'$buff',2:'$buff',3:'$buff1'}),
                dict(template='Servant128_WeaponSkill_06',event='off',self_cast=True,suffix='_Clear',args={1:'$buff'}),
            ]),
        1701280102:dict(name='潮汐保龄',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=10000,positive=False)],
            parts=[
                dict(template='Servant128_WeaponSkill_11',event='attack',args={1:'$buff'}),
                dict(template='Servant128_WeaponSkill_12',event='aura',suffix='_Puddle',
                     args={1:'$buff',4:2000,5:10000,6:2,7:11},trigger_extra=dict(TimerTime=500)),
            ]),
        1701300101:dict(name='伟业远征',kind='native',event='native',
            buffs=[
                dict(slot=0,type=99,args={},duration=600000,stack=4),
                dict(slot=1,type=99,args={},duration=600000,stack=4),
            ],
            parts=[
                dict(template='Servant130_WeaponSkill_01',event='hurt',self_cast=True,args={1:'$buff',2:'$buff1'}),
                dict(template='Servant130_WeaponSkill_03',event='off',self_cast=True,suffix='_Heal',
                     args={1:'$buff',2:'$buff1',4:1500}),
            ]),
        1701320102:dict(name='灾疫爆发',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=600000,stack=3)],
            parts=[
                dict(template='Servant132_WeaponSkill_04',event='hurt',self_cast=True,args={1:'$buff',4:80}),
                dict(template='Servant132_WeaponSkill_04',event='on',self_cast=True,suffix='_Spawn',args={1:'$buff',4:80}),
                dict(template='Servant132_WeaponSkill_05',event='attack',args={1:'$buff',4:19000,5:10000,6:7,7:14,8:-80}),
            ]),
        1701370101:dict(name='星屑贮存',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=600000,stack=120)],
            parts=[
                dict(template='Servant137_WeaponSkill_01',event='attack',self_cast=True,args={1:'$buff',2:'$buff'}),
                dict(template='Servant137_WeaponSkill_02',event='aura',suffix='_Fire',
                     args={1:'$buff',2:'$buff',3:'$buff',4:300,5:800,6:0},trigger_extra=dict(TimerTime=500)),
            ]),
        1701380101:dict(name='五芒星阵',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=8000,positive=False)],
            parts=[
                dict(template='Servant138_WeaponSkill_01',event='attack',times=3,args={1:'$buff',4:92000,5:10000,6:9,7:15}),
                dict(template='Servant138_WeaponSkill_02',event='attack',times=5,suffix='_Cross',
                     args={1:'$buff',4:46000,5:10000,6:9,7:16}),
            ]),
        1701390101:dict(name='捕食者',kind='native',event='native',
            buffs=[dict(type=99,args={},duration=600000,stack=4)],
            parts=[
                dict(template='Servant139_WeaponSkill_01',event='on',self_cast=True,args={1:'$buff'}),
                dict(template='Servant139_WeaponSkill_02',event='attack',args={1:'$mob',2:'$mob',3:'$buff',4:0}),
            ]),
        1701410101:dict(name='死者之荣光',kind='native',event='native',
            buffs=[
                dict(slot=0,type=3,args={4:1,5:25,8:340,13:26,16:340},duration=600000,stack=20),
                dict(slot=1,type=99,args={},duration=600000,stack=20),
            ],
            parts=[
                dict(template='Servant141_WeaponSkill_02',event='global_attack',
                     args={1:'$buff1',4:1,5:4,6:8}),
                dict(template='Servant141_WeaponSkill_03',event='on',self_cast=True,suffix='_Hold',
                     args={1:'$buff',2:'$buff1'}),
            ]),
        1701410102:dict(name='死者之怒火',kind='native',event='native',
            buffs=[
                dict(slot=0,type=99,args={},duration=600000,stack=20,positive=False),
                dict(slot=1,type=3,args={4:1,5:25,8:170,13:26,16:170},duration=10000,stack=20),
            ],
            parts=[
                dict(template='Servant141_WeaponSkill_04',event='attack',args={1:'$buff',2:'$buff1',4:1,5:4,6:8}),
                dict(template='Servant141_WeaponSkill_03',event='off',self_cast=True,suffix='_Dump',
                     args={1:'$buff1',2:'$buff'}),
            ]),
        1701420101:dict(name='圣十字斩',kind='native',event='native',
            parts=[
                dict(template='Servant142_WeaponSkill_01',event='attack',
                     args={1:0,6:14000,7:10000,8:6,9:14}),
            ]),
    }


def family_of(wid):
    from offline_seed import table
    row=next(r for r in table('ServantWeapon') if int(r['ID'])==wid)
    return {'1':'TH','2':'DW','3':'SH'}[row['weapon_type']]


WEAPON_MOBS={
    1701060101:dict(id=332010380601,model='mob_405',count=2,hp=1200,attack=90,life=12000,hit=48000,flat=74),
    1701190101:dict(id=332010381001,model='summonS_810',count=1,hp=99999,attack=160,life=600000,hit=14500,flat=84),
    1701250101:dict(id=332010343301,model='mob_434',count=2,hp=99999,attack=130,life=600000,hit=21000,flat=90),
    1701390101:dict(id=332010380901,model='mob_405',count=4,hp=800,attack=90,life=600000,hit=16000,flat=96),
}


def clone_normals(unit,sv,sid,wid,mutate=None):
    source=next(s for s in unit['SpellInfos'] if s['ID']==sv['RoleNormalAtkIDs'][0])
    effect=next(e for e in unit['EffectArgumentInfos'] if e['ID']==source['SpellEffectArgu'])
    normal=95000000+(sid-91000000)
    for n in (normal,normal+1):
        s=copy.deepcopy(source);s.update(ID=n,SpellEffectArgu=n,SpellTempletId='Offline_Normal_'+str(wid))
        e=copy.deepcopy(effect);e['ID']=n
        if mutate:mutate(e)
        unit['SpellInfos'].append(s);unit['EffectArgumentInfos'].append(e)
    sv['RoleNormalAtkIDs']=[normal]*3;sv['RoleDashAtkID']=normal+1
    return source['SpellTempletId']


def extend_rule(unit,sv,p,sid,tid,bid,spell,buff,trigger,args):
    kind=p['kind'];wid=sv['SvWeaponCardID']
    if kind=='native':
        for spec in p.get('buffs',[]):
            slot=spec.get('slot',0)
            extra=dict(spec.get('buff_extra',{}))
            buff(bid+slot,spec['type'],spec.get('args',{}),
                 duration=spec.get('duration',5000),stack=spec.get('stack',1),
                 positive=spec.get('positive',True),**extra)
        if wid in WEAPON_MOBS:
            pet=WEAPON_MOBS[wid];mid=pet['id']
            if not any(m.get('ID')==mid for m in unit.get('MobInfos',[])):
                unit.setdefault('MobInfos',[]).append(dict(
                    ID=mid,CurType=1,Level=5,Camp=0,Model=pet['model'],
                    MobKind=1,MobType=2,MobTypeInfoNormal=mid,MobTypeInfoElite=mid,
                    MobTypeInfoBoss=mid,BehaviorPatterns=1,Protogenesis=0,
                    Shadow=1,BeSelected=1,CanMove=1,CanTurn=1,FollowMaster=1,
                    FollowDistance=500,CollideWithAgent=1,LifeTime=pet['life'],
                    Hp=pet['hp'],PhysicalAttack=pet['attack'],MagicalAttack=pet['attack'],
                    PhysicalDefense=40,MagicalDefense=40,Hit=10000,
                    PhysicalCriticalMulti=15000,MagicalCriticalMulti=15000,CombatConstType=1))
                tree=90921000+(wid%1000);msp=90911000+(wid%1000)
                unit.setdefault('MobTypeInfos',[]).append(dict(
                    ID=mid,AttributeTypeHp=1,AttributeTypeAttack=1,AttributeTypeDefense=1,
                    MultiHp=10000,MultiAttack=10000,BehaviorTreeId=tree,MobSpell1=msp,
                    FirstAttackIntervalLower=1,FirstAttackIntervalUpper=1,
                    AttackIntervalLower=1,AttackIntervalUpper=2))
                unit.setdefault('BehaviorTreeArgumentInfos',[]).append(dict(
                    ID=tree,Name='normal_attack',Argument0=msp,Argument11=1,Argument12=3,Argument13=4,Argument14=5))
                unit['SpellInfos'].append(dict(
                    ID=msp,Level=5,SpellTempletId='Offline_Summon_Attack',SpellPriority=1,
                    SpellType=1,SpellTypeTag=1,TargetTypeTrue=1,TargetTypeTrue1=1,
                    TargetTypeNominal=1,TargetArgu4=2,MaxDistance=350,MaxDistanceCast=350,
                    FacetoTarget=1,DriveByAnimation=0,ChannelTime=900,SpellD=600,
                    ChannelPrefabStart='attack',SpellEffectArgu=msp))
                unit['EffectArgumentInfos'].append(dict(ID=msp,Argument4=pet.get('hit',16000),Argument5=10000,Argument6=pet.get('flat',90)))
        if p.get('normal_extra'):
            ne=p['normal_extra']
            def extra(e):
                e['Argument20']=ne['damage'];e['Argument21']=10000;e['Argument22']=ne.get('flat',0)
                if ne.get('convert_magic'):e['Argument19']=2
            p['normal_source']=clone_normals(unit,sv,sid,wid,extra)
        for i,part in enumerate(p.get('parts',[])):
            a={}
            for k,v in part.get('args',{}).items():
                if v=='$buff':a[k]=bid
                elif v=='$buff1':a[k]=bid+1
                elif v=='$buff2':a[k]=bid+2
                elif v=='$mob':a[k]=WEAPON_MOBS.get(wid,{}).get('id',0)
                else:a[k]=v
            suffix=part.get('suffix','' if i==0 else '_'+str(i))
            spell(sid+i,'Offline_Weapon_'+str(wid)+suffix,a)
            if part.get('self_cast'):
                unit['SpellInfos'][-1]['TargetArgu4']=3
                unit['SpellInfos'][-1]['TargetTypeTrue']=1
            trigger(wid,tid+i,sid+i,part['event'],part.get('rate',0),part.get('times',1),**part.get('trigger_extra',{}))
            sv.setdefault('TriggerList',[]).append(tid+i)
        return
    if kind.startswith('normal_'):
        p['normal_source']=clone_normals(unit,sv,sid,wid)
    elif kind=='dot':
        # Native BuffDamage: 4/8 = physical/magical ratios, 5/9 = source
        # attack factor, 14 = damage multiplier, 15 = damage kind, 16 = tag.
        a={14:1,15:2 if p.get('magic') else 1,16:4,17:1}
        a.update({8:p['damage'],9:10000} if p.get('magic') else {4:p['damage'],5:10000})
        buff(bid,1,a,duration=p['duration'],stack=5,positive=False,PeriodicTime=p['period'],BuffGroup='7')
        p['normal_source']=clone_normals(unit,sv,sid,wid,lambda e:e.__setitem__('Argument1',bid))
    elif kind=='damage' and p.get('event')=='normal':
        def extra(e):
            e['Argument20']=p['damage'];e['Argument21']=10000
            e['Argument22']=p.get('flat',0)
            if p.get('crit'):e['Argument23']=p['crit']
        p['normal_source']=clone_normals(unit,sv,sid,wid,extra)
    elif kind in ('stack_extra','stored_burst'):
        buff(bid,99,{},duration=600000,stack=10 if kind=='stack_extra' else 3)
        args[1]=bid
        spell(sid+1,'Offline_Weapon_'+str(wid)+'_Secondary',{1:bid})
        if kind=='stack_extra':
            trigger(wid,tid+1,sid+1,'attack',TriggerConditionArgu2=0)
        else:
            trigger(wid,tid+1,sid+1,'aura',TimerTime=2000)
        sv.setdefault('TriggerList',[]).append(tid+1)
    elif kind=='low_hp':
        buff(bid,3,{4:1,5:18,8:1500,13:19,16:1500},duration=750)
        spell(sid+1,'Offline_Weapon_'+str(wid)+'_LowHP',{1:bid,4:2500,5:1000})
        trigger(wid,tid+1,sid+1,'aura');sv.setdefault('TriggerList',[]).append(tid+1)
        def copy_args(e):
            # Native Skill_01 uses Argument4-8; those slots are the cloned
            # SH normal's SPP coefficients, so the missing-HP pack is 20-24.
            a=p.get('args',{})
            e['Argument20']=a.get(4,30);e['Argument21']=a.get(5,5)
            e['Argument22']=a.get(6,1);e['Argument23']=a.get(7,15);e['Argument24']=a.get(8,2)
        p['normal_source']=clone_normals(unit,sv,sid,wid,copy_args)
    elif kind in ('critical_pure','defense_pure','max_hp_pure'):
        def copy_args(e):
            for k,v in p.get('args',{}).items():e['Argument'+str(k)]=v
        p['normal_source']=clone_normals(unit,sv,sid,wid,copy_args)
    elif kind=='crowd_pure':
        buff(bid,99,{},duration=100,positive=False);args[1]=bid


def make_template(wid,p,original,phase):
    kind=p['kind'];nodes=[]
    def node(suffix=''):
        n=ET.Element('SpellEffect',TempletID='Offline_Weapon_'+str(wid)+suffix)
        nodes.append(n);return n
    def attr(parent,var,index,target=1):
        ET.SubElement(parent,'Declare',ID=var)
        ET.SubElement(parent,'GetTargetAttr',Variable=var,TargetType=str(target),
                      AttributeType=str(index),ContainAddValue='0')
    if kind=='native':
        if p.get('normal_extra'):
            ne=p['normal_extra']
            n=copy.deepcopy(original['Player_NormalAttack_'+family_of(wid)+'_01'])
            n.set('TempletID','Offline_Normal_'+str(wid));nodes.append(n)
            prefix='SPM' if ne.get('magic') or ne.get('convert_magic') else 'SPP'
            extra=dict(DamageTag='0',DamageType='2' if (ne.get('magic') or ne.get('convert_magic')) else '1',DamageModulus='1',Combine='1')
            extra[prefix+'DmgP']='@ARGUMENT20';extra[prefix+'AP']='@ARGUMENT21';extra[prefix+'AV']='@ARGUMENT22'
            for pack in list(n.iter('CreateDamagePack')):
                if ne.get('convert_magic'):
                    pack.set('DamageType','2')
                parent=next(x for x in n.iter() if pack in list(x))
                i=list(parent).index(pack)
                parent.insert(i+1,ET.Element('CreateDamagePack',**extra))
        for i,part in enumerate(p.get('parts',[])):
            assert part['template'] in original,part['template']
            n=copy.deepcopy(original[part['template']])
            suffix=part.get('suffix','' if i==0 else '_'+str(i))
            n.set('TempletID','Offline_Weapon_'+str(wid)+suffix)
            for ph in n:
                if ph.get('PointType')=='OnEffectPoint' and ph.get('Delay') in (None,'0'):
                    ph.set('Delay','50')
            nodes.append(n)
    elif kind=='pure_counter':
        n=node();fx=phase(n)
        for var,index in [('base',3),('pct',26),('flat',31)]:attr(fx,var,index)
        ET.SubElement(fx,'CreateDamagePack',DamageTag='0',DamageType='4',DamageModulus='1',
            SPCDmg='{($base * (1+$pct) + $flat) * 2.4}',Combine='1')
    elif kind=='counter_area':
        # Same native pure pack as 108, but a circle around the holder.
        # XML TargetType 2 + Argu1 cap matches Servant143 area graphs; Argu3 is lock-on only.
        n=node();fx=phase(n,radius=p.get('radius',2000),max_targets=p.get('max_targets',5))
        cap=str(p.get('max_targets',5))
        for ts in n.iter('TargetSelect'):
            ts.set('TargetType','2');ts.set('TargetArgu1',cap);ts.set('TargetArgu4','2')
            if 'TargetArgu3' in ts.attrib:del ts.attrib['TargetArgu3']
        for var,index in [('base',3),('pct',26),('flat',31)]:attr(fx,var,index)
        ET.SubElement(fx,'CreateDamagePack',DamageTag='0',DamageType='4',DamageModulus='1',
            SPCDmg='{($base * (1+$pct) + $flat) * 1.8}',Combine='1')
    elif kind=='dot':
        family=family_of(wid)
        n=copy.deepcopy(original['Player_NormalAttack_'+family+'_01'])
        n.set('TempletID','Offline_Normal_'+str(wid));nodes.append(n)
        for pack in list(n.iter('CreateDamagePack')):
            parent=next(x for x in n.iter() if pack in list(x))
            i=list(parent).index(pack)
            parent.insert(i+1,ET.Element('CreateBuffPack',BuffID1='@ARGUMENT1',BuffLayer1='1'))
    elif kind=='damage' and p.get('event')=='normal':
        n=copy.deepcopy(original['Player_NormalAttack_'+family_of(wid)+'_01'])
        n.set('TempletID','Offline_Normal_'+str(wid));nodes.append(n)
        prefix='SPM' if p.get('magic') else 'SPP'
        extra=dict(DamageTag='0',DamageType='2' if p.get('magic') else '1',DamageModulus='1',Combine='1')
        extra[prefix+'DmgP']='@ARGUMENT20';extra[prefix+'AP']='@ARGUMENT21'
        extra[prefix+'AV']='@ARGUMENT22'
        if p.get('crit'):extra[prefix+'CR']='@ARGUMENT23'
        for pack in list(n.iter('CreateDamagePack')):
            parent=next(x for x in n.iter() if pack in list(x))
            i=list(parent).index(pack)
            parent.insert(i+1,ET.Element('CreateDamagePack',**extra))
    elif kind in ('stack_extra','stored_burst'):
        main=node();secondary=node('_Secondary')
        charge=secondary if kind=='stack_extra' else main
        ET.SubElement(phase(charge,True),'CreateBuffPack',BuffID1='@ARGUMENT1',BuffLayer1='1')
        fire=main if kind=='stack_extra' else secondary
        fx=phase(fire,radius=0 if kind=='stack_extra' else 500)
        ET.SubElement(fx,'Declare',ID='layers')
        ET.SubElement(fx,'GetBuffLayer',Variable='layers',TargetType='1',BuffID='@ARGUMENT1')
        cond=ET.SubElement(fx,'Condition',Type='>',Value1='$layers',Value2='0')
        a=dict(DamageTag='0',DamageType='1' if kind=='stack_extra' else '2',DamageModulus='1',Combine='1')
        prefix='SPP' if kind=='stack_extra' else 'SPM'
        a.update({prefix+'DmgP':'{$layers * '+('800' if kind=='stack_extra' else '13000')+'}',prefix+'AP':'10000'})
        ET.SubElement(cond,'CreateDamagePack',**a)
        if kind=='stored_burst':
            # Consume once in a separate self phase, after all selected targets
            # have received the same stack multiplier.
            clear=phase(fire,True);list(fire)[-1].set('Delay','100')
            ET.SubElement(clear,'CreateDispelPack',BuffMaxNum='1',LayerNum='99',BuffID1='@ARGUMENT1',Force='1')
    elif kind in ('low_hp','critical_pure','defense_pure','max_hp_pure'):
        n=copy.deepcopy(original['Player_NormalAttack_'+family_of(wid)+'_01'])
        n.set('TempletID','Offline_Normal_'+str(wid));nodes.append(n)
        extra=copy.deepcopy(original[p['template']])
        host=next(ph for ph in n if ph.get('PointType')=='OnEffectPoint'
                  and any(True for _ in ph.iter('CreateDamagePack')))
        fx=next(el for el in host.iter('EffectList'))
        for ph in extra:
            if ph.get('PointType') not in ('OnStartPoint','OnEffectPoint'):continue
            for child in ph:
                if child.tag in ('RangeList','TargetSelect','EffectList'):
                    for pack in child.iter('CreateDamagePack'):
                        fx.append(copy.deepcopy(pack))
                    for pack in child.iter('CreateBuffPack'):
                        fx.append(copy.deepcopy(pack))
                    continue
                host.insert(list(host).index(fx),copy.deepcopy(child))
        if kind=='low_hp':
            for d in host.iter('Declare'):
                if d.get('ID')=='bufflayer':
                    d.set('Value','{$loseHP / @ARGUMENT22 * 10000}')
            for pack in fx.findall('CreateDamagePack'):
                if pack.get('Damage'):
                    pack.set('Damage','{@ARGUMENT20+@ARGUMENT23 * $bufflayer+(@ARGUMENT21+@ARGUMENT24* $bufflayer)* @SKILL_LEVEL}')
            aura=copy.deepcopy(original['Servant124_WeaponSkill_02'])
            aura.set('TempletID','Offline_Weapon_'+str(wid)+'_LowHP');nodes.append(aura)
            for ph in aura:
                if ph.get('PointType')=='OnEffectPoint':ph.set('Delay','50')
    elif kind.startswith('normal_'):
        family='DW' if wid==1701290101 else ('SH' if wid==1701220102 else 'DW')
        n=copy.deepcopy(original['Player_NormalAttack_'+family+'_01'])
        n.set('TempletID','Offline_Normal_'+str(wid));nodes.append(n)
        for pack in list(n.iter('CreateDamagePack')):
            if kind=='normal_armor':
                pack.set('SPIPDR','6000');pack.set('SPPAV','30')
            elif kind=='normal_critical':
                pack.set('SPPCMV','60000')
                parent=next(x for x in n.iter() if pack in list(x))
                i=list(parent).index(pack)
                # TargetType 3 is the current effect-list target, as in the
                # shipped defense/max-HP pure-damage graphs.
                tmp=ET.Element('temp');attr(tmp,'targetHP',99,3);attr(tmp,'targetMaxHP',1,3)
                for e in reversed(list(tmp)):parent.insert(i,e)
                parent.remove(pack)
                low=ET.SubElement(parent,'Condition',Type='<',Value1='$targetHP',Value2='{$targetMaxHP * 0.3}')
                critical=copy.deepcopy(pack);critical.set('SPPCR','2000');low.append(critical)
                high=ET.SubElement(parent,'Condition',Type='>=',Value1='$targetHP',Value2='{$targetMaxHP * 0.3}');high.append(pack)
            else:
                parent=next(x for x in n.iter() if pack in list(x));i=list(parent).index(pack)
                tmp=ET.Element('temp')
                for var,index in [('base',2),('pct',25),('flat',30)]:attr(tmp,var,index)
                for e in reversed(list(tmp)):parent.insert(i,e)
                tag=pack.get('DamageTag','248');pack.attrib.clear()
                pack.attrib.update(DamageTag=tag,DamageType='4',DamageModulus='1',
                    SPCDmg='{($base * (1+$pct) + $flat) * 2.1}',Combine='1')
    else:return None
    return nodes
