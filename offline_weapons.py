"""Native weapon triggers, reconstructed from the shipped descriptions/graphs.

This is deliberately an explicit per-weapon registry. Unmapped weapons stay in
the pending manifest instead of silently receiving another weapon's passive.
Server-only flat amounts use named local balance; documented ratios are kept.
"""
import copy,json,csv
import xml.etree.ElementTree as ET
from offline_seed import ROOT,table

# These controllers contain the matching numbered character clips. General
# controls remain unchanged until their animation family is positively mapped.
CONTROLLERS={109:'ubla',116:'ed',117:'hook',118:'glnc',119:'scl',120:'es',
             121:'wand',123:'gbld',124:'scsr',125:'ktr',127:'ktna',128:'axe',
             129:'mitt',130:'prte',137:'wand',138:'ghi',139:'fnl',140:'dr',
             142:'ktna'}
CONTROLLER_OVERRIDES={1701040102:'dr',1701110101:'pike',1701110102:'shld',
                      1701180102:'csp',1701410101:'wand'}

def profiles():
    # Trigger events: 12 = damage, 11 = hit, 3 = weapon on/off.
    # typeTag 1 is a normal attack; passive packets use 4, so cannot recurse.
    result = {
      1701000101:dict(name='不死者契约',kind='heal',event='hurt',rate=3000,
          template='Servant100_WeaponSkill_01',args={4:1500,5:10000,6:20},self=True),
      1701010101:dict(name='八方杀阵',kind='switch_burst',event='off',
          template='Servant101_WeaponSkill_03',args={4:10000,5:104000,6:10000,9:400}),
      1701020101:dict(name='内脏暴击',kind='critical_pure',event='normal',
          template='Servant102_WeaponSkill_02',args={4:22800},
          local_rules=['outgoing crit EventTrigger never counts; original Skill_02 extra sits on the cloned normal']),
      1701030101:dict(name='壳体震荡',kind='defense_pure',event='normal',
          template='Servant103_WeaponSkill_03',args={4:7400,5:21000,6:10000},
          local_rules=['outgoing Attack EventTrigger never counts; original Skill_03 extra sits on the cloned normal']),
      1701030102:dict(name='齿轮碾压',kind='max_hp_pure',event='normal',
          template='Servant103_WeaponSkill_02',args={4:200,5:43000},
          local_rules=['outgoing Attack EventTrigger never counts; original Skill_02 extra sits on the cloned normal']),
      1701040101:dict(name='精灵战技',kind='defense_exchange',event='attack',rate=3000,
          template='Servant104_WeaponSkill_01',args={}),
      1701040102:dict(name='幻色流光',kind='dodge_heal',event='dodge',
          template='Servant104_WeaponSkill_02',args={4:300,5:10000,6:10},self=True),
      1701050101:dict(name='重低音',kind='counter_area',event='hurt',times=6,
          damage=37000,magic=True,radius=2000,max_targets=5),
      1701070101:dict(name='王者光环',kind='attack_aura',event='aura'),
      1701110101:dict(name='神圣',kind='life_steal',event='aura'),
      1701160101:dict(name='防御壁垒',kind='stack_defense',event='hurt',self=True),
      1701160102:dict(name='Magma附加攻击',kind='damage',event='normal',damage=4200,frequency=1.6,
          local_rules=['EventTrigger cannot see outgoing hits; extra pack is on the cloned normal']),
      1701180101:dict(name='天蝎鳌刺',kind='damage',event='normal',damage=12000,magic=True,
          local_rules=['4m splash omitted; extra magic pack is on the cloned normal']),
      1701180102:dict(name='蓄力',kind='damage',event='normal',damage=48000,magic=True,frequency=0.7,
          local_rules=['EventTrigger cannot see outgoing hits; extra pack is on the cloned normal']),
      1701200101:dict(name='行刑',kind='current_hp_pure',event='attack',
          template='Servant120_WeaponSkill',args={4:160,5:6500,6:19500}),
      1701270101:dict(name='虎狼之势',kind='enemy_attack_pure',event='attack',
          template='Servant127_WeaponSkill_01',args={4:8000,9:32000,10:5500}),
      1701330101:dict(name='晦月临江',kind='defense_aura',event='aura'),
      1701350101:dict(name='刻骨',kind='damage',event='normal',damage=7000,
          local_rules=['original 75% proc omitted; extra physical pack is on every cloned-normal hit']),
    }
    from offline_weapon_rules import profiles as extra_profiles
    result.update(extra_profiles())
    return result

def extend(unit,servants):
    ps=profiles(); manifest=[]
    unit.setdefault('TriggerInfos',[])
    def effect(sid,args):unit['EffectArgumentInfos'].append(dict(ID=sid,Argument0='',**{'Argument'+str(k):v for k,v in args.items()}))
    def spell(sid,name,args):
        unit['SpellInfos'].append(dict(ID=sid,Level=5,SpellTempletId=name,
            SpellType=1,SpellTypeTag=4,SpellPriority=0,TargetTypeTrue=1,
            TargetTypeTrue1=1,TargetTypeNominal=1,TargetArgu4=2,
            DriveByAnimation=0,ChannelTime=0,SpellD=0,SpellEffectArgu=sid))
        effect(sid,args)
    def buff(bid,kind,args,duration=5000,stack=1,positive=True,**extra):
        unit['BuffInfos'].append(dict(ID=bid,Level=5,Layer=1,BuffType=kind,
            # SaveBuff treats protocol value 0 as positive, 1 as negative.
            IsPositive=int(not positive),MaxDuration=duration,MaxStack=stack,
            StackType=1,AddCondition=448,ReplaceType=0,BuffEffectArgu=bid,**extra))
        effect(bid,args)
    def trigger(wid,tid,sid,event,rate=0,times=1,**extra):
        t=dict(ID=tid,Level=5,Type=3,Times=times,Spell=sid,
               ActivateCondition=3,ActivateConditionArgu1=wid,ActivateConditionArgu2=1,
               ActivateCondition1=3,ActivateCondition1Argu1=wid,ActivateCondition1Argu2=3,
               InactivateCondition=3,InactivateConditionArgu1=wid,InactivateConditionArgu2=2)
        if event=='off':
            # The off event must fire before any inactivation; it needs no
            # holding gate because the event itself carries the exact weapon.
            for k in list(t):
                if k.startswith(('Activate','Inactivate')):del t[k]
            t.update(TriggerCondition=3,TriggerConditionArgu1=wid,TriggerConditionArgu2=2)
        elif event=='on':
            t.update(TriggerCondition=3,TriggerConditionArgu1=wid,TriggerConditionArgu2=1)
        elif event=='sheathed':
            t.update(Type=2,TimerTime=2000,TimerTimes=0,
                     TimerStartCondition=3,TimerStartConditionArgu1=wid,TimerStartConditionArgu2=2,
                     ActivateCondition=3,ActivateConditionArgu1=wid,ActivateConditionArgu2=2,
                     ActivateCondition1=3,ActivateCondition1Argu1=wid,ActivateCondition1Argu2=2,
                     InactivateCondition=3,InactivateConditionArgu1=wid,InactivateConditionArgu2=1)
        elif event=='global_attack':
            for k in list(t):
                if k.startswith(('Activate','Inactivate')):del t[k]
            t.update(TriggerCondition=10,TriggerConditionTargetType=1,
                     TriggerConditionArgu1=1,TriggerConditionArgu2=0)
        elif event=='aura':
            # TimeTrigger only starts in response to TimerStartCondition;
            # Activate() alone does not start its clock. Weapon init/on both
            # match arg2=0; off is already excluded by the holding gate.
            t.update(Type=2,TimerTime=500,TimerTimes=0,TimerStartCondition=3,
                     TimerStartConditionArgu1=wid)
        elif event=='dodge':
            t.update(TriggerCondition=11,TriggerConditionTargetType=2,
                TriggerConditionArgu1=3,TriggerConditionArgu2=1,TriggerConditionArgu3=3)
        elif event=='hit':
            # HitDelegate is invoked on DamagePack+0x28 (the defender). Hero
            # outgoing dual-wield never sees HitEvent; AttackDelegate does.
            t.update(TriggerCondition=11,TriggerConditionTargetType=1,
                TriggerConditionArgu1=1,TriggerConditionArgu2=0)
        elif event=='attack':
            # DamagePack.DoAttack posts AttackEvent (type 10) on the attacker.
            # Type 12 DamageEvent is the defender path used by hurt heals.
            t.update(TriggerCondition=10,TriggerConditionTargetType=1,
                TriggerConditionArgu1=1,TriggerConditionArgu2=0)
        else:
            t.update(TriggerCondition=12,TriggerConditionTargetType=2 if event=='hurt' else 1,
                TriggerConditionArgu1=1 if event=='critical' else 3,TriggerConditionArgu2=1)
        if rate:t.update(IsRate=1,RateType=1,Rate=rate,TriggerSureTimes=1000000)
        t.update(extra)
        unit['TriggerInfos'].append(t)
    for index,sv in enumerate(servants):
        wid=sv['SvWeaponCardID'];serial=(sv['SvCardID']//100)%1000
        ctrl=CONTROLLER_OVERRIDES.get(wid,CONTROLLERS.get(serial))
        if ctrl:sv['SvCtrl']='animations/'+ctrl
        record=dict(weapon=wid,controller=sv['SvCtrl'],status='pending')
        if wid not in ps:manifest.append(record);continue
        p=ps[wid];sid=91000000+index*10;tid=92000000+index*10;bid=93000000+index*10
        args=dict(p.get('args',{}));kind=p['kind'];event=p['event']
        from offline_weapon_rules import extend_rule
        extend_rule(unit,sv,p,sid,tid,bid,spell,buff,trigger,args)
        if kind=='defense_exchange':
            # Attribute indices 27/28 are relative physical/magical defense.
            buff(bid,3,{4:1,5:27,8:100,13:28,16:100},stack=3)
            buff(bid+1,3,{4:1,5:27,8:-1900,13:28,16:-1900},stack=3,positive=False)
            args.update({1:bid,2:bid+1})
        elif kind in ('attack_aura','defense_aura','life_steal','stack_defense','hold_reduce','evade_aura','crit_aura'):
            if kind=='attack_aura':
                v=p.get('aura',4200)
                buff(bid,3,{4:1,5:25,8:v,13:26,16:v},duration=750)
            if kind=='defense_aura':buff(bid,3,{4:1,5:32,8:30,13:33,16:30},duration=750)
            if kind=='life_steal':buff(bid,9,{10:p.get('steal',800),13:1},duration=750)
            if kind=='stack_defense':buff(bid,10,{4:-1200,9:-1200,14:-1200,19:0,20:0,22:10000},stack=6)
            if kind=='hold_reduce':
                red=p.get('reduce',-2000)
                buff(bid,10,{4:red,9:red,14:red,19:0,20:0,22:10000},duration=750)
            if kind=='evade_aura':buff(bid,3,{4:1,5:15,8:p.get('dodge',2000)},duration=750)
            if kind=='crit_aura':
                v=p.get('crit',2000)
                buff(bid,3,{4:1,5:17,8:v,13:18,16:v},duration=750)
            args[1]=bid
        if kind=='dodge_heal':
            buff(bid,3,{4:1,5:15,8:3900},duration=750)
            spell(sid+1,'Offline_Weapon_SelfBuff',{1:bid})
            trigger(wid,tid+1,sid+1,'aura');sv.setdefault('TriggerList',[]).append(tid+1)
        if event not in ('normal','native'):
            template='Offline_Weapon_'+str(wid)
            spell(sid,template,args);trigger(wid,tid,sid,event,p.get('rate',0),p.get('times',1),**p.get('trigger_extra',{}))
            if kind=='counter_area':
                # Protocol True=2 + Argu4=2 filters the caster away (empty set).
                # Release on self (Argu4=3); XML TargetSelect Argu4=2 picks hostiles in the circle.
                unit['SpellInfos'][-1]['TargetArgu4']=3
                unit['SpellInfos'][-1]['TargetTypeTrue']=2
                unit['SpellInfos'][-1]['TargetTypeTrue1']=2
            sv.setdefault('TriggerList',[]).append(tid)
        if 'frequency' in p:sv['WeaponAttackFrequency']=p['frequency']
        record.update(status='implemented_pending_runtime',mechanic=kind,name=p['name'],
                      local_flat_balance=True)
        if event=='normal':
            record.update(normal=sv['RoleNormalAtkIDs'][0])
            if kind=='dot':record['buff']=bid
        elif event=='native':
            record.update(spell=sid,trigger=tid)
            if p.get('normal_extra'):record['normal']=sv['RoleNormalAtkIDs'][0]
        else:
            record.update(trigger=tid,spell=sid)
        record['local_rules']=p.get('local_rules',[])
        manifest.append(record)
    (ROOT/'evidence/weapon_reconstruction.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')

def append_templates(root):
    original={n.get('TempletID'):n for n in root}
    def phase(node,allies=False,radius=0,max_targets=0):
        p=ET.SubElement(node,'FuncDef',PointType='OnEffectPoint',Delay='50',RepeatNum='1')
        r=ET.SubElement(p,'RangeList')
        ET.SubElement(r,'RangeSelect',RangeType='99' if allies and not radius else ('3' if radius else '1'),RangeArgu1=str(radius))
        attrs=dict(TargetType='1',TargetArgu4='3' if allies else '2')
        if max_targets:attrs['TargetArgu3']=str(max_targets)
        ET.SubElement(p,'TargetSelect',**attrs)
        return ET.SubElement(p,'EffectList')
    node=ET.Element('SpellEffect',TempletID='Offline_Weapon_SelfBuff')
    ET.SubElement(phase(node,True),'CreateBuffPack',BuffID1='@ARGUMENT1',BuffLayer1='1');root.append(node)
    for wid,p in profiles().items():
        from offline_weapon_rules import make_template
        custom=make_template(wid,p,original,phase)
        if custom is not None:
            root.extend(custom);continue
        if 'template' in p:
            assert p['template'] in original,p['template']
            node=copy.deepcopy(original[p['template']])
            for ph in node:
                if ph.get('PointType')=='OnEffectPoint':ph.set('Delay','50')
            if p.get('self'):
                for select in node.iter('RangeSelect'):select.set('RangeType','99');select.set('RangeArgu1','0')
        else:
            node=ET.Element('SpellEffect')
            if p['kind'] in ('attack_aura','defense_aura','life_steal','stack_defense','hold_reduce','evade_aura','crit_aura'):
                fx=phase(node,True,3000 if p['kind'].endswith('aura') else 0)
                ET.SubElement(fx,'CreateBuffPack',BuffID1='@ARGUMENT1',BuffLayer1='1')
            else:
                fx=phase(node,radius=p.get('radius',0),max_targets=p.get('max_targets',0))
                fields=dict(DamageTag='0',DamageType='2' if p.get('magic') else '1',DamageModulus='1',Combine='1')
                prefix='SPM' if p.get('magic') else 'SPP'
                fields.update({prefix+'DmgP':str(p['damage']),prefix+('AP'):'10000',prefix+'AV':str(p.get('flat',0))})
                ET.SubElement(fx,'CreateDamagePack',**fields)
        node.set('TempletID','Offline_Weapon_'+str(wid));root.append(node)
