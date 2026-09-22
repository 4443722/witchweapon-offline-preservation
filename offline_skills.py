"""Original initial-servant skill graphs, with explicit local server parameters.

No production combat parameter table survived. Templates and advertised skill
effects are from the APK; numerical configuration is a local reconstruction.
"""

def initial_skills():
    spells, effects, agents, buffs = [], [], [], []

    def effect(sid, **args):
        effects.append(dict(ID=sid, **{'Argument'+str(k[1:]):v for k,v in args.items()}))

    def spell(sid, template, **extra):
        spells.append(dict(ID=sid, Level=5, SpellTempletId=template,
            SpellPriority=10, SpellType=2, SpellTypeTag=2,
            TargetTypeTrue=1, TargetTypeTrue1=2, TargetTypeNominal=2,
            TargetArgu4=3, MaxDistance=3000, MaxDistanceCast=3000,
            DriveByAnimation=0, ChannelTime=1800, SpellD=300,
            SpellEffectArgu=sid, **extra))

    def buff(bid, kind, duration, template='', positive=True, **args):
        buffs.append(dict(ID=bid, Level=5, Layer=1, BuffType=kind,
            IsPositive=int(positive), MaxDuration=duration, MaxStack=1, AddCondition=448,
            ReplaceType=0, StackType=1, BuffEffectArgu=bid,
            BuffTempletId=template,BuffGroup="3" if kind==22 else ""))
        effect(bid, **args)

    # Type 22 is the native finite all-damage shield. Legacy type 12 only
    # processes physical damage in this client. Disable per-second decay.
    # BuffState Argument4 stun, Argument7 immunity bits. 16 = stun immunity.
    buff(90100001, 22, 8000, 'Servant100_ActiveSkill_Buff', a4=3, a5=10000, a6=458, a7=78)
    buff(90100002, 4, 8000, a7=16)
    buff(90103001, 4, 2000, positive=False, a4=5, a8=10000)
    # Emily's linked hit buff only marks impact; damage comes from the spell.
    buff(90102001, 99, 300, positive=False)
    effect(90102002, a1=90102001)
    spell(90102002, 'Player_CV_hit')

    for unit in range(100,104):
        active=2010310002+(unit-100)*100
        inner=90110000+unit
        agent=90210000+unit
        spell(active, f'Servant{unit}_ActiveSkill', SpellAgent1=agent)
        effect(active, a1=agent)
        extras={}
        if unit==102: extras['LinkSpell1']=90102002
        spell(inner, f'Offline_Servant{unit}_ActiveSkill_01', **extras)
        agents.append(dict(ID=agent, Level=5,
            Prefab=f'characters/unit_{unit}/servant/servant_{unit}',
            SpawnType=0, SpawnAction='', DeadAction='disappear',
            MotionId='MOVEMENT_TYPE_STAY', LifeTime=4000,
            PositionType=1, CenterType=1, Radius=0,
            OrientationType=1, TargetType=1, TargetArgu4=3,
            SpellCastSpawn=inner, CombatConstType=1))
        if unit==100:
            effect(inner, a1=90100001, a2=90100002)
        elif unit==101:
            # Native template expanding wave, total 550% magical attack;
            # center 1.3x, outer edge 1x, range 30 game units.
            effect(inner, a4=400, a5=100, a6=6, a7=1500,
                   a8=13000, a9=10000, a10=55000, a11=10000,
                   a12=-2, a13=35, a14=1100)
        elif unit==102:
            effect(inner, a4=500, a5=100, a6=1, a7=3000,
                   a8=360, a9=0, a10=78000, a11=10000, a12=4, a13=33)
        else:
            effect(inner, a1=90103001, a4=500, a5=6000)
    # Tina: original summon and ice impact visuals, with a local area release
    # instead of the missing server-configured projectile agent.
    active,inner,agent,freeze=2010311202,90110112,90210112,90112001
    spell(active,'Servant112_ActiveSkill',SpellAgent1=agent)
    effect(active,a1=agent)
    spell(inner,'Offline_Servant112_ActiveSkill_01')
    effect(inner,a1=freeze,a4=10000,a5=40000,a6=300,a7=40)
    buff(freeze,4,2500,'Servant112_ActiveSkill_Buff',positive=False,a4=5,a8=10000)
    agents.append(dict(ID=agent,Level=5,Prefab='characters/unit_112/servant/servant_112',
        SpawnType=0,SpawnAction='',DeadAction='disappear',MotionId='MOVEMENT_TYPE_STAY',
        LifeTime=4000,PositionType=1,CenterType=1,Radius=0,OrientationType=1,
        TargetType=1,TargetArgu4=3,SpellCastSpawn=inner,CombatConstType=1))
    return dict(SpellInfos=spells, EffectArgumentInfos=effects,
                AgentInfos=agents, BuffInfos=buffs)


def prepare_templates():
    """Preserve original skill graphs, with explicit local millisecond timing.

    The native timeline is constructed before OnStart installs the live skill
    namespace. Bake scheduling parameters only; damage expressions stay native.
    A zero-frame inner effect runs before the summoned entity finishes setup.
    """
    import copy
    import xml.etree.ElementTree as ET
    import UnityPy
    from offline_seed import ROOT
    root = ET.parse(ROOT/'decoded/config/xmlconf/skill/Spells.xml').getroot()
    timing = {100:[('500','1')],
              101:[('{400 + 100 * (@SKILL_EFFECT_POINT_COUNT_LIST - 1)}','6'),('1100','1')],
              102:[('500','1')],103:[('350','1')]}
    for unit, phases in timing.items():
        original=next(n for n in root if n.get('TempletID')==f'Servant{unit}_ActiveSkill_01')
        node=copy.deepcopy(original)
        node.set('TempletID',f'Offline_Servant{unit}_ActiveSkill_01')
        effects=[n for n in node if n.get('PointType')=='OnEffectPoint']
        assert len(effects)==len(phases)
        for effect,(delay,repeat) in zip(effects,phases):
            effect.set('Delay',delay);effect.set('RepeatNum',repeat)
        if unit==100:
            # The summon uses a positional release target. Select the allied
            # player explicitly; a zero-radius locked-target range is empty.
            for select in node.iter('RangeSelect'):
                select.set('RangeType','3');select.set('RangeArgu1','3000')
            # Submit the independent effects in separate timeline packets.
            # This client retains only the final buff from the combined pack.
            second=copy.deepcopy(effects[0])
            second.set('Delay','600')
            for pack in effects[0].iter('CreateBuffPack'):
                pack.set('BuffID2','0')
            for pack in second.iter('CreateBuffPack'):
                pack.set('BuffID1','@ARGUMENT2');pack.set('BuffID2','0')
            node.append(second)
        root.append(node)
    # Keep the original summon cut-in, voice and particles. Resolve the ice
    # impact directly after setup; original remote projectile data is absent.
    visual=next(n for n in root if n.get('TempletID')=='Servant112_ActiveSkill_01')
    hit=next(n for n in root if n.get('TempletID')=='Servant112_ActiveSkill_02')
    node=ET.Element('SpellEffect',TempletID='Offline_Servant112_ActiveSkill_01')
    for n in visual:
        if n.get('PointType')=='OnStartPoint':node.append(copy.deepcopy(n))
    phase=copy.deepcopy(next(n for n in hit if n.get('PointType')=='OnEffectPoint'))
    phase.set('Delay','650')
    for select in phase.iter('RangeSelect'):
        select.set('RangeType','3');select.set('RangeArgu1','1500')
    for pack in phase.iter('CreateBuffPack'):pack.set('BuffID1','@ARGUMENT1')
    node.append(phase);root.append(node)
    from offline_enemies import append_templates
    append_templates(root)
    from offline_roster import append_templates as append_roster_templates
    append_roster_templates(root)
    from offline_weapons import append_templates as append_weapon_templates
    append_weapon_templates(root)
    name='assets/assetbundle/config/xmlconf/skill/spells.ab'
    env=UnityPy.load(str(ROOT/'original_parts'/name))
    for obj in env.objects:
        if obj.type.name!='MonoBehaviour':continue
        tree=obj.read_typetree()
        if 'bytes' not in tree:continue
        raw=ET.tostring(root,encoding='utf-8',xml_declaration=True)
        tree['bytes']=list(bytes(b^255 for b in raw) if tree.get('isEncrypt') else raw)
        obj.save_typetree(tree)
    dest=ROOT/'overrides'/name;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(env.file.save(packer='original'))
