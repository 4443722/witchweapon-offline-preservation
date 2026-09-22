"""Playable local reconstructions for the remaining bundled servant roster.

Preserve each servant's own summon presentation. Server-only graph parameters
are replaced by explicit local effects, described in the generated manifest.
The five separately reconstructed skills remain unchanged.
"""
import copy,json
import xml.etree.ElementTree as ET
from offline_seed import ROOT,table

DETAILED={100,101,102,103,112}
SHIELD={105,109,121,133,143}
CONTROL={107,108,111,113,115,129,137,142}
SUMMON={116,122,125,131}

def roster():
    clients={r['ID']:r for r in table('ServantClient')}
    return [(int(clients[r['client_id']]['serial']),r) for r in
        {r['ID']:r for r in table('Servant') if r['channel_group'] in ('','0','25') and r['can_see']=='1'}.values()]

def modes(unit,root):
    graphs=[n for n in root if n.get('TempletID','').startswith(f'Servant{unit}_ActiveSkill')]
    tags={n.tag for g in graphs for n in g.iter()}
    out=[]
    if unit in SHIELD:out.append('shield')
    if 'CreateHealPack' in tags:out.append('heal')
    if 'CreateDamagePack' in tags or unit in SUMMON:out.append('damage')
    if unit in CONTROL:out.append('control')
    if not out:out.append('damage')
    return out

def extend(unit_data):
    root=ET.parse(ROOT/'decoded/config/xmlconf/skill/Spells.xml').getroot()
    manifest=[]
    for unit,row in roster():
        if unit in DETAILED:continue
        active=int(row['spell_active']);inner=90510000+unit;agent=90610000+unit
        features=modes(unit,root)
        for sid,template in [(active,f'Offline_Roster{unit}_Summon'),(inner,f'Offline_Roster{unit}_Effect')]:
            unit_data['SpellInfos'].append(dict(ID=sid,Level=5,SpellTempletId=template,
                SpellPriority=10,SpellType=2,SpellTypeTag=2,TargetTypeTrue=1,
                TargetTypeTrue1=2,TargetTypeNominal=2,TargetArgu4=3,
                MaxDistance=3000,MaxDistanceCast=3000,DriveByAnimation=0,
                ChannelTime=4500 if unit in SUMMON else 1800,SpellD=300,SpellEffectArgu=sid))
        unit_data['EffectArgumentInfos'].append(dict(ID=active,Argument1=agent))
        unit_data['EffectArgumentInfos'].append(dict(ID=inner,Argument1=90700000+unit,
            Argument2=90800000+unit))
        unit_data['AgentInfos'].append(dict(ID=agent,Level=5,
            Prefab=f'characters/unit_{unit}/servant/servant_{unit}',SpawnType=0,
            SpawnAction='',DeadAction='disappear',MotionId='MOVEMENT_TYPE_STAY',
            LifeTime=5500 if unit in SUMMON else 4000,PositionType=1,CenterType=1,
            Radius=0,OrientationType=1,TargetType=1,TargetArgu4=3,
            SpellCastSpawn=inner,CombatConstType=1))
        for feature,bid,kind,args in [('shield',90700000+unit,22,dict(Argument4=3,Argument5=10000,Argument6=650,Argument7=90)),
                                      ('control',90800000+unit,4,dict(Argument4=5,Argument8=10000))]:
            if feature not in features:continue
            unit_data['BuffInfos'].append(dict(ID=bid,Level=5,Layer=1,BuffType=kind,
                BuffGroup="3" if kind==22 else "",IsPositive=int(feature=='shield'),MaxDuration=8000 if feature=='shield' else 2000,
                MaxStack=1,AddCondition=448,ReplaceType=0,StackType=1,BuffEffectArgu=bid))
            unit_data['EffectArgumentInfos'].append(dict(ID=bid,**args))
        manifest.append(dict(servant=int(row['ID']),unit=unit,active=active,effects=['summon'] if unit in SUMMON else features,
            original_presentation=True,local_reconstruction=True,
            simplifications=['server parameters replaced','linked agents flattened',
                'real allied summon; local hp/attack/lifetime' if unit in SUMMON else 'local radius and timing']))
    from offline_summons import extend as extend_summons
    extend_summons(unit_data)
    (ROOT/'evidence/roster_local_reconstruction.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')

def append_templates(root):
    originals=list(root)
    for unit,row in roster():
        if unit in DETAILED:continue
        features=modes(unit,originals)
        outer=ET.Element('SpellEffect',TempletID=f'Offline_Roster{unit}_Summon')
        phase=ET.SubElement(outer,'FuncDef',PointType='OnEffectPoint',Delay='0',RepeatNum='1')
        ET.SubElement(ET.SubElement(phase,'RangeList'),'RangeSelect',RangeType='1',RangeArgu1='0')
        ET.SubElement(phase,'TargetSelect',TargetType='1',TargetArgu4='3')
        ET.SubElement(ET.SubElement(phase,'EffectList'),'CreateAgent',AgentMaxNum='1',AgentID='@ARGUMENT1')
        root.append(outer)
        node=ET.Element('SpellEffect',TempletID=f'Offline_Roster{unit}_Effect')
        start=ET.SubElement(node,'FuncDef',PointType='OnStartPoint')
        ET.SubElement(start,'Declare',ID='pref',Value='0')
        ET.SubElement(start,'GetSettingPlayAnimation',Variable='pref')
        yes=ET.SubElement(start,'Condition',Type='==',Value1='$pref',Value2='1')
        ET.SubElement(yes,'PlayAction',TargetType='1',ActionName='skill')
        # Read the actual cut-in name from this servant's original graph.
        animations=[n.get('AnimationName') for g in originals if g.get('TempletID','').startswith(f'Servant{unit}_ActiveSkill')
                    for n in g.iter('PlaySpecialAnimation') if n.get('AnimationName')]
        if animations:ET.SubElement(yes,'PlaySpecialAnimation',AnimationName=animations[0])
        no=ET.SubElement(start,'Condition',Type='==',Value1='$pref',Value2='0')
        ET.SubElement(no,'PlayAction',TargetType='1',ActionName='appear')
        ET.SubElement(no,'PlayCV',ServantId=str(unit),IsDelay='1')
        if unit in SUMMON:
            from offline_summons import append_spawn
            append_spawn(node,unit)
        for index,feature in enumerate([] if unit in SUMMON else features):
            phase=ET.SubElement(node,'FuncDef',PointType='OnEffectPoint',Delay=str(650+index*100),RepeatNum='1')
            if feature=='damage' and unit in SUMMON:
                phase.set('Delay','{650 + 1000 * (@SKILL_EFFECT_POINT_COUNT_LIST - 1)}');phase.set('RepeatNum','4')
            ET.SubElement(ET.SubElement(phase,'RangeList'),'RangeSelect',RangeType='3',RangeArgu1='1500')
            ET.SubElement(phase,'TargetSelect',TargetType='1',TargetArgu4='3' if feature in ('heal','shield') else '2')
            effects=ET.SubElement(phase,'EffectList')
            if feature=='damage':
                ratio='15000' if unit in SUMMON else '50000'
                ET.SubElement(effects,'CreateDamagePack',DamageTag=str(unit),DamageType='2',DamageModulus='1',
                    SPMDmgP='10000',SPMAP=ratio,SPMAV='{200 + 40 * @SKILL_LEVEL}',Combine='0')
            elif feature=='heal':
                ET.SubElement(effects,'CreateHealPack',HealModulus='1',SPHealP='10000',SPMHP='35000',SPMHV='{250 + 50 * @SKILL_LEVEL}')
            else:
                ET.SubElement(effects,'CreateBuffPack',BuffID1='@ARGUMENT1' if feature=='shield' else '@ARGUMENT2',BuffLayer1='1')
        root.append(node)
    from offline_summons import append_templates as append_summon_templates
    append_summon_templates(root)
