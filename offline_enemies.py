"""Reconnect native enemy spell graphs and AI. Missing magnitudes are local balance."""
import copy
from offline_seed import table

SPECIALS={
    'mob_100':('Mob100_Skill_01',{1:90300000,2:90300016,3:0},1800),
    'mob_103':('Mob103_Skill_01',{1:90300032,2:90300016,4:500,5:10000,6:16000,7:0,8:0},1800),
    'mob_104':('Mob104_Skill_01',{1:90300016,4:0,5:1000,6:3,7:1500,8:10000,9:50000,10:200,11:0},4500),
    'mob_119':('Mob119_Skill_01',{4:10000,5:10000,6:0,7:0,8:3,9:650},2600),
    # Native control/movement graphs, locally chosen magnitudes and timings.
    'mob_107':('Mob107_Skill_01',{2:90300016,3:90300016,4:500,5:600,6:10000,7:12000,8:0,9:0,10:650,11:250,12:3,13:700,14:350},2200),
    'mob_108':('Mob108_Skill_01',{1:90300032,2:90300016,4:650,5:1300,6:800,8:500,9:800,10:10000,11:18000,12:0,13:0},2200),
    'mob_111':('Mob111_Skill_01',{1:90300032,2:90300032,3:90300016,4:500,5:500,6:10000,7:12000,8:0,9:0},3000),
    'mob_118':('Mob118_Skill_01',{1:90300032,2:90300016,4:10000,5:10000,6:0,7:0,8:3,9:600,10:650,11:900,12:400,13:200},3000),
    'mob_431':('Mob431_Skill_01',{1:90300016,2:90300016,4:10000,5:22000,6:0,7:0},1500),
    # Maze leftover: native 117 Skill_02 is a hostile pack plus optional buffs.
    # Magnitudes are local 10000-point percents; stun reuses the shared 90300032.
    'mob_117':('Mob117_Skill_02',{1:90300032,4:10000,5:10000,6:80,7:0,8:500,9:0},1800),
    # Floor 8/9 leftover: native taunt circle. Radius 2000 is local.
    'mob_122':('Mob122_Skill_02',{4:8000},1800),
    # Floor 6 leftover: native sharpness drain on the current weapon.
    'mob_442':('Mob442_Skill_01',{4:-2000},1500),
    # Floor 6 leftover: native magic pack; CreateAgent graph stays unused.
    'mob_436':('Mob436_Skill_02',{4:10000,5:10000,6:80,7:0},1800),
    # Floor 3 leftover: native self shield plus casting protection. Magnitudes
    # reuse the shared 90300000/90300016 packets.
    'mob_403':('Mob403_Skill_01',{1:90300000,2:90300016},1800),
    # Floor 3/8 leftover: native self defense pack. Attr 32/33 +3000 is local.
    'mob_116':('Mob116_Skill_01',{1:90300080},1800),
    # Floor 7 leftover: original Skill_01 CreateAgent; inner circle is Skill_01_01.
    # Skill_03 lock-on pack stays attached as a second phase so the accepted
    # magic hit is not dropped.
    'mob_105':('Mob105_Skill_01',{2:90300016,4:10000,5:10000,6:80,7:0},1800),
    'mob_109':('Mob109_Skill_01',{},1800),
}

# Outer CreateAgent graphs. Argument1 is filled with the AgentInfo ID.
AGENTS={
    'mob_105':dict(prefab='characters/unit_105/effects/105_m_e_skill',
                   inner='Mob105_Skill_01_01',inner_args={1:90300032,4:800},life=2500),
    'mob_109':dict(prefab='characters/unit_109/effects/109_m_e_buff',
                   inner='Mob109_Skill_01_01',inner_args={1:90300032,4:500},life=2500),
}

# Native CreateMob leftovers, keyed to the servant summon reconstructions.
SUMMONS={
    'mob_116':116,
    'mob_122':122,
}


def add_pet(basket, serial, rank=1):
    from offline_summons import PETS, prefab
    pet=PETS[serial]; mid=pet['id']
    if any(m.ID==mid for m in basket.MobInfos):
        return mid
    src_mob=basket.MobInfos[0]; src_typ=basket.MobTypeInfos[0]
    src_tree=basket.BehaviorTreeArgumentInfos[0]; src_spell=basket.SpellInfos[0]
    src_effect=basket.EffectArgumentInfos[0]
    spell_id=90910000+serial; tree_id=90920000+serial
    # One VO. Duplicate ranks fill createMobDic so MobMaxNum=1 never spawns.
    # Enemy CreateMob keys GetMobUUID(id, casterPowerRank, level).
    mob=basket.MobInfos.add(); mob.CopyFrom(src_mob)
    mob.ID=mid; mob.CurType=rank; mob.Level=5; mob.Model=pet['model']
    mob.MobTypeInfoNormal=mid; mob.MobTypeInfoElite=mid; mob.MobTypeInfoBoss=mid
    mob.MobType=2; mob.Camp=1; mob.Hp=pet['hp']
    mob.PhysicalAttack=pet['attack']; mob.MagicalAttack=pet['attack']
    mob.FollowMaster=1; mob.CanMove=1; mob.CanTurn=1; mob.FollowDistance=500
    mob.LifeTime=pet['life']
    typ=basket.MobTypeInfos.add(); typ.CopyFrom(src_typ)
    typ.ID=mid; typ.BehaviorTreeId=tree_id; typ.MobSpell1=spell_id
    typ.MobSpell2=0; typ.MobSpell3=0
    tree=basket.BehaviorTreeArgumentInfos.add(); tree.CopyFrom(src_tree)
    tree.ID=tree_id; tree.Name='normal_attack'; tree.Argument0=spell_id
    tree.Argument1=0
    sp=basket.SpellInfos.add(); sp.CopyFrom(src_spell)
    sp.ID=spell_id; sp.SpellEffectArgu=spell_id
    sp.SpellTempletId='Offline_Summon_Attack'
    sp.SpellType=1; sp.SpellTypeTag=1; sp.TargetTypeTrue=1; sp.TargetArgu4=2
    sp.MaxDistance=350; sp.MaxDistanceCast=350; sp.ChannelTime=900; sp.SpellD=600
    sp.ChannelPrefabStart='attack'
    ef=basket.EffectArgumentInfos.add(); ef.CopyFrom(src_effect); ef.ID=spell_id
    ef.Argument0=''; ef.Argument6=10000; ef.Argument7=10000
    return mid


def enrich(basket):
    def effect(id,args):
        e=basket.EffectArgumentInfos.add();e.ID=id;e.Argument0=''
        for k,v in args.items():setattr(e,'Argument'+str(k),v)
    def buff(id,kind,duration,args,positive=True):
        b=basket.BuffInfos.add();b.ID=id;b.Level=5;b.Layer=1;b.BuffType=kind
        b.MaxDuration=duration;b.MaxStack=1;b.StackType=1;b.AddCondition=448
        b.IsPositive=int(positive);b.BuffEffectArgu=id
        b.BuffGroup={7:"7",22:"3",50:"3"}.get(kind,"")
        effect(id,args)
    # Shared shielding, casting protection and interruptible stun.
    buff(90300000,22,6000,{4:3,5:10000,6:1300})
    buff(90300016,4,6000,{7:16})
    buff(90300032,4,1200,{4:5,8:10000},False)
    # Rose: native counterattack flag (damageTag bit 128), fixed damage per hit.
    # Magnitude 18 is local balance; the original server magnitude is unavailable.
    buff(90300070,7,600000,{4:3,6:18,16:1,20:2,21:10000})
    # Native special reduction keeps criticals and converts non-criticals to 1.
    buff(90300071,50,600000,{4:10000})
    # 116 consecutive-defense leftover; indices 32/33 are physical/magical def.
    # SaveBuff treats protocol 0 as positive.
    b=basket.BuffInfos.add();b.ID=90300080;b.Level=5;b.Layer=1;b.BuffType=3
    b.MaxDuration=6000;b.MaxStack=1;b.StackType=1;b.AddCondition=448
    b.IsPositive=0;b.BuffEffectArgu=90300080
    effect(90300080,{4:1,5:32,8:3000,13:33,16:3000})
    original_tree=next(r for r in table('BehaviorTreeArgument') if r['name']=='normal_att+spell')
    # Buffs are prepended to EffectArgumentInfos. Pair each mob with its own
    # normal spell/effect by ID, not by zip position after those buffs.
    normals=list(zip(basket.MobInfos,basket.MobTypeInfos,
                     basket.BehaviorTreeArgumentInfos,list(basket.SpellInfos)))
    effects={e.ID:e for e in basket.EffectArgumentInfos}
    for mob,typ,tree,spell in normals:
        ef=effects.get(spell.ID)
        # Percentages are basis points. The old 100/100 pair produced minimum
        # one-point damage and made enemy attacks ineffective.
        if ef is not None:
            ef.Argument6=10000;ef.Argument7=10000
        if mob.Model=='mob_407':
            mob.SpawnBuffs.append(90300071)
            spell.SpellTempletId='Mob_NormalAttack_Melee_Magical'
        if mob.Model=='mob_406':
            mob.SpawnBuffs.append(90300070)
            spell.SpellTempletId='Mob_NormalAttack_Range_Magical'
            spell.MaxDistance=2000;spell.MaxDistanceCast=2000
            if ef is not None:
                ef.Argument4=10000;ef.Argument5=10000;ef.Argument6=0;ef.Argument7=0
        if mob.Model not in SPECIALS:continue
        template,args,duration=SPECIALS[mob.Model]
        sid=spell.ID+50000
        args=dict(args)
        if mob.Model in AGENTS:
            spec=AGENTS[mob.Model]
            agent_id=90410000+int(mob.Model[-3:])
            inner_id=sid+1
            args[1]=agent_id
            inner=basket.SpellInfos.add();inner.CopyFrom(spell)
            inner.ID=inner_id;inner.SpellEffectArgu=inner_id
            inner.SpellTempletId='Offline_'+spec['inner']
            inner.Level=mob.Level
            inner.TargetTypeTrue=2;inner.TargetTypeTrue1=2;inner.TargetArgu4=3
            inner.SpellType=2;inner.SpellTypeTag=2;inner.SpellPriority=10
            inner.DriveByAnimation=0;inner.ChannelTime=650
            inner.MaxDistance=3000;inner.MaxDistanceCast=3000;inner.SpellD=300
            effect(inner_id,spec['inner_args'])
            agent=basket.AgentInfos.add()
            agent.ID=agent_id;agent.Level=mob.Level
            agent.Prefab=spec['prefab']
            agent.SpawnType=0;agent.SpawnAction='';agent.DeadAction='disappear'
            agent.MotionId='MOVEMENT_TYPE_STAY';agent.LifeTime=spec['life']
            agent.PositionType=1;agent.CenterType=1;agent.Radius=0
            agent.OrientationType=1;agent.TargetType=1;agent.TargetArgu4=3
            agent.SpellCastSpawn=inner_id;agent.CombatConstType=1
        if mob.Model in SUMMONS:
            pet_id=add_pet(basket,SUMMONS[mob.Model], mob.CurType)
            # 116 Skill_01 already uses Argument1 for the defense buff.
            args[2 if mob.Model=='mob_116' else 1]=pet_id
        active=basket.SpellInfos.add();active.CopyFrom(spell)
        active.ID=sid;active.SpellEffectArgu=sid;active.SpellTempletId='Offline_'+template
        active.Level=mob.Level
        if mob.Model in ('mob_103','mob_108','mob_118','mob_122','mob_109','mob_403','mob_116','mob_105'):
            # These graphs exclude the release target from their hostile area.
            # Release from the caster, not the hero, or the only player is filtered out.
            active.TargetTypeTrue=2;active.TargetTypeTrue1=2
        if mob.Model in ('mob_108','mob_122','mob_116','mob_105','mob_109'):
            # Protocol Argu4=2 with True=2 is an empty set. Self-release lets
            # XML TargetSelect pick hostiles, allies, or CreateMob on the caster.
            active.TargetArgu4=3
        if mob.Model in ('mob_436','mob_117'):
            # Native RangeType 1 applies the pack to the locked attack target.
            # TargetTypeTrue=2 made RangeType 1 select the caster, then
            # TargetArgu4=2 filtered that self hit away. 117 already uses this.
            active.TargetTypeTrue=1;active.TargetTypeTrue1=1
        active.SpellType=2;active.SpellTypeTag=2;active.SpellPriority=10
        active.DriveByAnimation=0;active.ChannelTime=duration
        active.ChannelPrefabStart='skill';active.MaxDistance=3000;active.MaxDistanceCast=3000
        active.SpellD=1000
        effect(sid,args)
        typ.MobSpell2=sid
        tree.Name='normal_att+spell'
        for i in range(31):
            if original_tree.get('argument'+str(i)):
                setattr(tree,'Argument'+str(i),int(original_tree['argument'+str(i)]))
        tree.Argument0=spell.ID;tree.Argument1=sid
        # Original AI's first cast delay and subsequent cooldown intervals.
        tree.Argument15=2;tree.Argument16=5;tree.Argument17=8;tree.Argument18=12


def _append_phase(node, original_name, root, delay='800'):
    source=next(n for n in root if n.get('TempletID')==original_name)
    phase=copy.deepcopy(next(n for n in source if n.get('PointType')=='OnEffectPoint'))
    phase.set('Delay',delay);phase.set('RepeatNum','1')
    node.append(phase)
    return phase


def append_templates(root):
    """Preserve original logic, resolve effect scheduling before OnStart."""
    originals=list(root)
    for model,(name,args,duration) in SPECIALS.items():
        original=next(n for n in originals if n.get('TempletID')==name)
        node=copy.deepcopy(original);node.set('TempletID','Offline_'+name)
        phases=[n for n in node if n.get('PointType')=='OnEffectPoint']
        # Resolve schedules explicitly; preserve distinct phases and repetition.
        schedules={
            'mob_107':[('650','1'),('{700 + 350 * (@SKILL_EFFECT_POINT_COUNT_LIST - 1)}','3')],
            'mob_108':[('650','1'),('1300','1')],
            'mob_111':[('1000','1'),('1000','1'),('2200','1')],
            'mob_118':[('{650 + 600 * (@SKILL_EFFECT_POINT_COUNT_LIST - 1)}','3')],
            'mob_431':[('650','1')],
            'mob_117':[('650','1'),('650','1')],
        }
        schedule=schedules.get(model,[('650','1')]*len(phases))
        assert len(schedule)==len(phases),(model,len(phases))
        for phase,(delay,repeats) in zip(phases,schedule):
            phase.set('Delay',delay);phase.set('RepeatNum',repeats)
        if model=='mob_119':
            phases[0].set('Delay','{650 + 650 * (@SKILL_EFFECT_POINT_COUNT_LIST - 1)}')
            phases[0].set('RepeatNum','3')
        if model=='mob_104':
            phases[0].set('Delay','{2000 + 1000 * (@SKILL_EFFECT_POINT_COUNT_LIST - 1)}')
            phases[0].set('RepeatNum','3')
        if model=='mob_100':
            for select in phases[0].iter('RangeSelect'):
                select.set('RangeType','3');select.set('RangeArgu1','1000')
        if model=='mob_116':
            # Native RangeType 1 + TargetArgu4=1 never attached 90300080. Self range.
            for select in phases[0].iter('RangeSelect'):
                select.set('RangeType','99');select.set('RangeArgu1','0')
            for select in phases[0].iter('TargetSelect'):
                select.set('TargetArgu4','3')
            # Original Skill_02 CreateMob; one AI slot, so it rides the same cast.
            # Argument1 is the defense buff, so the pet id lives on Argument2.
            # Native MobMaxNum=0 / MobType=@SELF_TYPE looks up id-rank-level that
            # is not in the basket (pets are stored as CurType=1).
            phase=_append_phase(node,'Mob116_Skill_02',originals,'900')
            for pack in phase.iter('CreateMob'):
                pack.set('MobID','@ARGUMENT2')
                pack.set('MobType','1')
                pack.set('MobMaxNum','1')
            for select in phase.iter('TargetSelect'):
                select.set('TargetArgu4','3')
        if model=='mob_122':
            # Native Skill_02 taunts hostiles (the player). Camp.csv camp1 vs
            # camp1 is -1, so Argu4=1 never selects 116. Keep the native pack.
            phase=_append_phase(node,'Mob122_Skill_01',originals,'900')
            for pack in phase.iter('CreateMob'):
                pack.set('MobType','1')
                pack.set('MobMaxNum','1')
            for select in phase.iter('TargetSelect'):
                select.set('TargetArgu4','3')
        if model=='mob_105':
            # Keep the accepted Skill_03 lock-on pack on the same special cast.
            extra=_append_phase(node,'Mob105_Skill_03',originals,'900')
            for select in extra.iter('TargetSelect'):
                select.set('TargetArgu4','2')
        root.append(node)
    for spec in AGENTS.values():
        original=next(n for n in originals if n.get('TempletID')==spec['inner'])
        node=copy.deepcopy(original);node.set('TempletID','Offline_'+spec['inner'])
        for phase in node:
            if phase.get('PointType')=='OnEffectPoint':
                phase.set('Delay','0');phase.set('RepeatNum','1')
                for select in phase.iter('TargetSelect'):
                    select.set('TargetArgu4','2')
        root.append(node)
