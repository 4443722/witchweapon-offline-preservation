"""Reconstruct a first local encounter using bundled maps, enemies and skill templates.

Server-only numbers and spawn coordinates below are local test balance, not
claimed recovered production values. Original CSVs remain read-only.
"""
from offline_seed import *
import re
from offline_skills import initial_skills

def combat_seeds():
    attrs=['hit_const','dodge_const','ignore_physical_defense_const','ignore_magical_defense_const',
           'physical_critical_const','magical_critical_const','physical_critical_multi_const','magical_critical_multi_const']
    levels=table('CharacterLevelInfo')
    ct=dict(characterLevelInfoProto=[dict(AttrLevelConst=[int(r[a] or 200) for a in attrs]) for r in levels],
        LevelModify=[dict(HitRateLevelModify=0,SpellHitRateLevelModify=0,CriticalRateLevelModify=0) for _ in range(201)],
        combatConstTypeInfo=[dict(ModulusType=i,PhysicalDamageModulus=1,MagicalDamageModulus=1,
                 PhysicalDefenseModulus=1,MagicalDefenseModulus=1,HealModulus=1) for i in range(1,5)],
        # CSV -1 on the diagonal is a placeholder. Runtime ally selection needs
        # relationship 0, including the player and her summoned servants.
        Camp=[dict(Base=int(r['ID']),Target=t,Relationship=max(0,int(r['camp'+str(t)]))) for r in table('Camp') for t in range(3)],
        CommonSpell=[2010100001,2010100002,2010100003,2099000003])
    # Native HitRandom requires a server CombatRate row for every (rate,times)
    # pair. Use independent documented probabilities without escalating odds;
    # a high explicit limit avoids Times=0 becoming guaranteed every hit.
    from offline_weapons import profiles
    rates={p['rate'] for p in profiles().values() if p.get('rate')}
    rates.update(part['rate'] for p in profiles().values() for part in p.get('parts',[]) if part.get('rate'))
    ct['combatRate']=[dict(Rate=r,Times=1000000,RateInit=r/10000,RateIncrease=0) for r in sorted(rates)]
    spells=[];effects=[];servants=[]
    def attack(sid,template,active=False,mob=False):
        # Original skill templates carry visual and damage logic; parameters are
        # conservative local values until server tables can be reconstructed.
        # Animation events spread a combo over 2.5-3.1 seconds instead of
        # firing all phases every 0.7 seconds. Rebalance local damage accordingly.
        effect=dict(ID=sid,Argument0='',Argument4=4500,Argument5=4500,Argument6=0,
                    Argument7=0,Argument8=0,Argument12=0,Argument13=0,Argument18=0)
        if mob:
            effect.update(Argument4=250,Argument5=200,Argument6=100,Argument7=100,Argument8=0)
        # RangeType=1 with zero radius uses the already selected target.
        # TH Argument8 and SH Argument12 otherwise add a forward-offset hit circle.
        # Use the same locked-target rule for both local weapon families.
        effects.append(effect)
        spells.append(dict(ID=sid,Level=1,SpellTempletId=template,SpellPriority=1,
            SpellType=2 if active else 1,SpellCanCastTag=0,SpellTypeTag=1,
            TargetTypeTrue=1,TargetTypeTrue1=1,TargetTypeNominal=1,TargetArgu4=2,
            MaxDistance=300,MaxDistanceCast=300,FacetoTarget=1,
            ChargeTime=0,ChannelTime=700,DriveByAnimation=1,SpellD=500,
            # Player controller state names are case-sensitive; mob controllers use attack.
            ChannelPrefabStart='attack' if mob else 'AttackStandStart0',
            SpellEffectArgu=sid,NormalAttackTimePerHit=700))
    for sid in [2010100001,2010100002,2010100003]:attack(sid,'Player_NormalAttack_SH_01')
    spells.append(dict(ID=2099000003,Level=1,SpellTempletId='Player_CV_hit',SpellType=1,
                       DriveByAnimation=0,SpellD=100,SpellEffectArgu=2099000003))
    effects.append(dict(ID=2099000003))
    roster={int(r['ID']):r for r in table('Servant') if r['channel_group'] in ('','0','25') and r['can_see']=='1'}
    for s,sr in roster.items():
        candidates={int(r['ID']):r for r in table('ServantWeapon') if int(r['servant_id'] or 0)==s and r['channel_group'] in ('','0','25')}
        for wid,w in candidates.items():
            if w['can_see']=='0':continue
            normal=int(w['normal_attack1']);active=int(sr['spell_active']);dash=normal+90000000
            family={'1':'TH','2':'DW','3':'SH'}[w['weapon_type']]
            template=f'Player_NormalAttack_{family}_01'
            for skill,temp in [(normal,template),(dash,template)]:
                if not any(a['ID']==skill for a in spells):attack(skill,temp,skill==active)
            # HeroEntity.LoadBuild overwrites Builder.controller with SvCtrl.
            # Empty SvCtrl removes the Animator controller even though clips exist.
            servants.append(dict(SvCardID=s,SvWeaponCardID=wid,SpaNeedCurTarget=False,
                WeaponPAtk=int(w['weapon_physical_attack1'] or 60),WeaponMAtk=int(w['weapon_magical_attack1'] or 60),
                SvCtrl='animations/'+{'1':'thw','2':'dw','3':'ohw'}[w['weapon_type']],RoleDashAtkID=dash,RoleNormalAtkIDs=[normal]*3,EnergyCombo=[300000,200000,600000,300000],ActiveSpellID=active,
                WeaponSharpInfo=dict(SharpMax=10000,SharpRecovery=100,SharpReduceAttack=20),
                WeaponAttackFrequency=1,CurSkin=1,SpellEnegyType=1))
    unit=initial_skills()
    from offline_roster import extend
    extend(unit)
    unit['SpellInfos']=spells+unit['SpellInfos']
    unit['EffectArgumentInfos']=effects+unit['EffectArgumentInfos']
    from offline_weapons import extend as extend_weapons
    extend_weapons(unit,servants)
    rc=dict(CommonAttr=[1500,100,100,30,30,0.9,0,0,0,0.2,0.2,1.5,1.5],RoleLv=5,FashionSerial=1,
        SvCombatInfo=servants,CombatConst=dict(KillingCD=1500,Char=[1,450,3],WpMDL=[2,1,1.5],DmgPkgMDL=[1]*6,
            TSP=[1000,100,10,1],MobExtraHealModulus=[1]*5),
        Unit=unit,PlayerAttr=[0]*5)
    # Stage 1-2: its map, enemy IDs, ranks, levels, objective and time all come
    # from InstanceMobList.csv. The original server's wave layout is absent.
    stage=next(r for r in table('InstanceMobList') if r['ID']=='3110001002')
    ms=[];types=[];monsters=[];mobspells=[];trees=[];mobeffects=[]
    for i in range(1,6):
        mid=int(stage.get('mob'+str(i)) or 0)
        if not mid:continue
        rank=int(stage['mob'+str(i)+'_type']);lv=int(stage['mob'+str(i)+'_lv'])
        row=next(r for r in table('Mob') if int(r['ID'])==mid)
        spell=2020000000+i;typ=mid;tree=8040800047+i
        types.append(dict(ID=typ,AttributeTypeHp=1,AttributeTypeAttack=1,AttributeTypeDefense=1,
                          MultiHp=10000,MultiAttack=10000,BehaviorTreeId=tree,MobSpell1=spell,
                          FirstAttackIntervalLower=1,FirstAttackIntervalUpper=2,AttackIntervalLower=2,AttackIntervalUpper=3))
        trees.append(dict(ID=tree,Name='normal_attack',Argument0=spell,Argument11=1,Argument12=3,Argument13=4,Argument14=5))
        ms.append(dict(ID=mid,CurType=rank,Level=lv,Camp=1,Model=row['model'],MobKind=3,MobType=1,
                 MobTypeInfoNormal=typ,MobTypeInfoElite=typ,MobTypeInfoBoss=typ,BehaviorPatterns=1,
                 Protogenesis=1,Shadow=1,BeSelected=1,CanMove=1,CanTurn=1,CollideWithAgent=1,
                 Hp=6000 if rank==2 else 4000,PhysicalAttack=40,MagicalAttack=40,PhysicalDefense=10,MagicalDefense=10,
                 Hit=9000,PhysicalCriticalMulti=15000,MagicalCriticalMulti=15000,CombatConstType=1))
        attack(spell,'Mob_NormalAttack_Melee_Physical',mob=True)
        mobspells.append(spells.pop());mobeffects.append(effects.pop())
        monsters.append(dict(name='Enemy_'+str(i),opName=row['model'],givenName='',statID=f'{mid}-{rank}-{lv}',
            appearType=0,PRS=[2.74+(i-1)*2,-1.5,180,1],groupID=101,
            ai_config=dict(taunt_list_index=0,can_be_taunt=True,follow_target=''),tag=''))
    # The original quest evaluator consumes a flattened 3 x 3 OR-of-AND
    # expression. -1 means unused; indices refer to the triggers below.
    level=dict(QuestInfo=dict(code=0,optStr='',sec=300,
            Triggers=[dict(type='AllZoneClear',param=[]),dict(type='TimeLimit',param=['300']),dict(type='HeroPerish',param=[])],
            WinJudgement=[0,-1,-1,-1,-1,-1,-1,-1,-1],LoseJudgement=[1,-1,-1,2,-1,-1,-1,-1,-1],
            BonusType=2,BonusParam=0.5,LevelObjectiveType=6),
        MapInfo=dict(sceneName='map_1004_metroplatform',isForceGuideMap=False,globalBuff=0,servantInitialEnergyRate=10000,levelInitialCameraRotation=''),
        AIInfo=dict(ai_taunt_list_presets=[]),EnemyLayer=dict(levelID='3110001002',lvMin=1,lvMax=1,
            areas=[dict(name='Area_0',zones=[dict(name='Zone_0',entryPR=[2.74,0.17,-5.5,0,0,0],navP=[2.74,0.17,-1.5],walls=[],
                 triggers=[dict(name='Start',opName='ColliderTrigger',PRS=[2.74,-3,0,4],allowSkillPenetration=True,triggerCameraFocusOnFirstMob=False)],
                 waves=[dict(name='Wave_0',showMode=0,spawnDelay=0,sec=0,kill=999,NextWaveTriggers=[],SubWaves=[],monsters=monsters)])])]),
        ItemLayer=[],NPCLayer=[],InteractiveObjLayer=[])
    return {'/combat/table':proto('combatmod.CombatTable',**ct),
            '/combat/role/info':proto('combatmod.RoleCombatInfoProto',**rc),
            '/combat/mob/info':proto('combatmod.Basket',MobInfos=ms,MobTypeInfos=types,SpellInfos=mobspells,
                                     BehaviorTreeArgumentInfos=trees,EffectArgumentInfos=mobeffects),
            '/combat/mob/json':dict(type='application/json',body=json.dumps(level,separators=(',',':')))}

if __name__=='__main__':
    path=ROOT/'offline_responses.json';responses=json.loads(path.read_text('utf8'))
    seeds=combat_seeds();responses.update(seeds)
    path.write_text(json.dumps(responses,ensure_ascii=False,indent=2),'utf8')
    print('Combat fixtures',[(k,len(v.get('base64',v.get('body','')))) for k,v in seeds.items()])
