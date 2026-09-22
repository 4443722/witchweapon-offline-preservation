"""Real allied MonsterEntity summons using the original models and engine AI.

IDs/models are recovered from the original CreateMob graphs. Missing server
stats, lifetime and attack coefficients are explicit local balance.
"""
import json
import xml.etree.ElementTree as ET
from offline_seed import ROOT

PETS = {
    116: dict(id=332010380501, model='summonS_805', count=1, hp=2800, attack=160, life=18000),
    122: dict(id=332010381501, model='mob_808', count=1, hp=2400, attack=220, life=20000),
    125: dict(id=332010381701, model='summonS_817', count=1, hp=4200, attack=130, life=25000),
    131: dict(id=332010340501, model='mob_405', count=3, hp=1000, attack=90, life=16000),
}


def prefab(pet):
    return f"characters/unit_{pet['model'][-3:]}/mob/{pet['model']}"


def extend(unit):
    for serial, pet in PETS.items():
        mid=pet['id']; spell=90910000+serial; tree=90920000+serial
        # MobType=2 sets MonsterVO.isAsSummonUnit. CreateMob's MobType=1
        # separately selects the normal power rank. Camp is inherited on spawn.
        unit.setdefault('MobInfos', []).append(dict(
            ID=mid, CurType=1, Level=5, Camp=0, Model=pet['model'],
            MobKind=1, MobType=2, MobTypeInfoNormal=mid, MobTypeInfoElite=mid,
            MobTypeInfoBoss=mid, BehaviorPatterns=1, Protogenesis=0,
            Shadow=1, BeSelected=1, CanMove=0 if serial==125 else 1,
            CanTurn=1, FollowMaster=0 if serial==125 else 1,
            FollowDistance=500, CollideWithAgent=1, LifeTime=pet['life'],
            Hp=pet['hp'], PhysicalAttack=pet['attack'], MagicalAttack=pet['attack'],
            PhysicalDefense=40, MagicalDefense=40, Hit=10000,
            PhysicalCriticalMulti=15000, MagicalCriticalMulti=15000,
            CombatConstType=1))
        unit.setdefault('MobTypeInfos', []).append(dict(
            ID=mid, AttributeTypeHp=1, AttributeTypeAttack=1, AttributeTypeDefense=1,
            MultiHp=10000, MultiAttack=10000, BehaviorTreeId=tree, MobSpell1=spell,
            FirstAttackIntervalLower=1, FirstAttackIntervalUpper=1,
            AttackIntervalLower=1, AttackIntervalUpper=2))
        unit.setdefault('BehaviorTreeArgumentInfos', []).append(dict(
            ID=tree, Name='normal_attack', Argument0=spell,
            Argument11=1, Argument12=3, Argument13=4, Argument14=5))
        unit['SpellInfos'].append(dict(
            ID=spell, Level=5, SpellTempletId='Offline_Summon_DollTaunt' if serial==125 else 'Offline_Summon_Attack',
            SpellPriority=1, SpellType=1, SpellTypeTag=1,
            TargetTypeTrue=1, TargetTypeTrue1=1, TargetTypeNominal=1,
            TargetArgu4=2, MaxDistance=1800 if serial==125 else 350,
            MaxDistanceCast=1800 if serial==125 else 350,
            FacetoTarget=1, DriveByAnimation=0, ChannelTime=900, SpellD=600,
            ChannelPrefabStart='' if serial==125 else 'attack', SpellEffectArgu=spell))
        unit['EffectArgumentInfos'].append(dict(ID=spell))
        if serial==125:
            # The original doll model has only spawn/idle/death clips. It stays
            # in place, taunts enemies and returns damage through native buff 7.
            bid=90930000+serial
            unit['MobInfos'][-1]['SpawnBuffs']=[bid]
            unit['BuffInfos'].append(dict(ID=bid,Level=5,Layer=1,BuffType=7,
                BuffGroup='7',IsPositive=1,MaxDuration=pet['life'],MaxStack=1,
                AddCondition=448,ReplaceType=0,StackType=1,BuffEffectArgu=bid))
            unit['EffectArgumentInfos'].append(dict(ID=bid,Argument4=3,
                Argument6=50,Argument16=1,Argument20=2,Argument21=10000))
        for effect in unit['EffectArgumentInfos']:
            if effect['ID']==90510000+serial:effect['Argument1']=mid
    manifest=[dict(servant=10000001+s*100, **p, prefab=prefab(p),
        behavior='stationary taunt and native retaliation' if s==125 else 'native allied summon with independent normal_attack AI',
        balance='local hp/attack/lifetime; scales with saved servant level',
        original_graph=f'Servant{s}_ActiveSkill_01') for s,p in PETS.items()]
    (ROOT/'evidence/summon_reconstruction.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')


def append_spawn(node, serial):
    pet=PETS[serial]
    phase=ET.SubElement(node,'FuncDef',PointType='OnEffectPoint',
        Delay='{650 + 180 * (@SKILL_EFFECT_POINT_COUNT_LIST - 1)}',RepeatNum=str(pet['count']))
    ET.SubElement(ET.SubElement(phase,'RangeList'),'RangeSelect',RangeType='1',RangeArgu1='0')
    ET.SubElement(phase,'TargetSelect',TargetType='1',TargetArgu4='1')
    ET.SubElement(ET.SubElement(phase,'EffectList'),'CreateMob',
        MobMaxNum=str(pet['count']),MobID='@ARGUMENT1',MobType='1',MobPrefab=prefab(pet))


def append_templates(root):
    attack=ET.SubElement(root,'SpellEffect',TempletID='Offline_Summon_Attack')
    phase=ET.SubElement(attack,'FuncDef',PointType='OnEffectPoint',Delay='350',RepeatNum='1')
    ET.SubElement(ET.SubElement(phase,'RangeList'),'RangeSelect',RangeType='1',RangeArgu1='0')
    ET.SubElement(phase,'TargetSelect',TargetType='1',TargetArgu4='2')
    ET.SubElement(ET.SubElement(phase,'EffectList'),'CreateDamagePack',
        DamageTag='131',DamageType='1',DamageModulus='1',SPPDmgP='10000',
        SPPAP='10000',SPPAV='0',Combine='0')
    doll=ET.SubElement(root,'SpellEffect',TempletID='Offline_Summon_DollTaunt')
    phase=ET.SubElement(doll,'FuncDef',PointType='OnEffectPoint',Delay='350',RepeatNum='1')
    ET.SubElement(ET.SubElement(phase,'RangeList'),'RangeSelect',RangeType='3',RangeArgu1='1800')
    ET.SubElement(phase,'TargetSelect',TargetType='1',TargetArgu4='2')
    ET.SubElement(ET.SubElement(phase,'EffectList'),'CreateTauntPack',Target='1')
