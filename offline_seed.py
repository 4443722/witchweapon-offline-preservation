"""Build local protocol fixtures from descriptors recovered from this APK.

This generates seeds, not real account/server data. Runtime mutations and the
save file are handled by OfflineApplication in the independent test package.
"""
from pathlib import Path
import base64, csv, json, time
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

ROOT = Path(__file__).resolve().parent
POOL = descriptor_pool.DescriptorPool()
FILES = [descriptor_pb2.FileDescriptorProto.FromString(p.read_bytes())
         for p in (ROOT/'decoded/proto_descriptors').glob('*.pb')]
todo = FILES[:]
while todo:
    count = len(todo)
    for fd in todo[:]:
        try: POOL.Add(fd)
        except Exception: continue
        todo.remove(fd)
    if len(todo) == count:
        raise RuntimeError('Unresolved descriptors: '+str([f.name for f in todo]))

def message(name, **data):
    desc = POOL.FindMessageTypeByName(name)
    obj = message_factory.GetMessageClass(desc)()
    for key, val in data.items():
        field = desc.fields_by_name[key]
        target = getattr(obj, key)
        if field.is_repeated:
            if field.message_type and field.message_type.GetOptions().map_entry:
                value_field=field.message_type.fields_by_name['value']
                if value_field.message_type:
                    for k,v in val.items():target[k].CopyFrom(message(value_field.message_type.full_name,**v))
                else:target.update(val)
            elif field.message_type:
                for item in val: target.add().CopyFrom(message(field.message_type.full_name, **item))
            else: target.extend(val)
        elif field.message_type:
            target.CopyFrom(message(field.message_type.full_name, **val))
        else: setattr(obj, key, val)
    return obj

def proto(name, **data):
    return {'type':'application/octet-stream','base64':base64.b64encode(message(name,**data).SerializeToString()).decode()}

def table(name):
    rows=list(csv.DictReader((ROOT/'decoded/config/clientexel'/f'{name}.csv').open(encoding='utf-8-sig')))
    return [r for r in rows[2:] if (r.get('ID') or r.get('recID') or '').lstrip('-').isdigit()]

def main():
    path = ROOT/'offline_responses.json'
    responses = json.loads(path.read_text('utf8'))
    for key, response in responses.items():
        if not key.startswith('/account/') or not response.get('body'): continue
        obj = json.loads(response['body'])
        if isinstance(obj.get('Value'), dict) and 'UID' in obj['Value']:
            obj['Value']['OnlineStep'] = 5
            obj['Value']['OnlineTime'] = 86400000
            response['body'] = json.dumps(obj,ensure_ascii=False)
    stamp = int(time.time())
    sync = dict(Time=stamp, Stamina=200,StaminaTime=stamp,ActivityStamina=200,
                ActivityStaminaTime=stamp, RoleTimeInstance=dict(TimeZone=8,TimePoint5=stamp,TimePoint0=stamp))
    # Optional online systems start empty. Required character data is explicit below.
    for r in json.loads((ROOT/'evidence/protocol_routes.json').read_text('utf8')):
        if len(r['types']) == 1:
            responses.setdefault(r['route'],proto(r['types'][0]))
    weapons=table('ServantWeapon')
    servants=[]
    for sid in [10010001,10010101,10010201,10010301]:
        row=next(r for r in table('Servant') if int(r['ID'])==sid)
        candidates={int(w['ID']):w for w in weapons if int(w['servant_id'] or 0)==sid and w['channel_group'] in ('','0','25')}
        ws=[dict(WeaponCardID=wid,RoleID=1,WeaponPromoteLv=0,WeaponSpellPromoteLv=1,Skins=1,CurSkin=1)
            for wid in candidates]
        servants.append(dict(ServantCardID=sid,RoleID=1,Level=5,Rank=1,Star=1,SpellLv=[1,1,1,1,1],
            FavorLevel=1,Images=1,CurImage=1,ImagesForFavor=1,WeaponLv=5,Weapons=ws,Skins=1))
    tutorial_jobs=sorted({int(row[key]) for row in table('LessonTrigger') if int(row['recID'])<100
                          for key in ['quest1','quest2','quest3'] if int(row[key] or -1)>0})
    role=dict(RoleID=1,UserID=1,Name='本地玩家',Level=5,Gold=1000000,Rmb=100000,Stamina=200,
              StaminaTime=stamp,ActivityStamina=200,ActivityStaminaTime=stamp,FirstDraws=7,
              Head=[1],HeadBox=[1],CurHead=1,CurHeadBox=1,MonthCardDays=[0,0],MonthCardSend=[False,False],
              PlatForm=2,Hack={},BindIdentity=1,StoryCurrency=1000,DrawCurrency=1000)
    chaps={}
    for row in table('Instance'):
        if row['instance_type'] not in ('1','2'):continue
        cid=int(row['instance_set_attached'] or 0)
        if not cid:continue
        chaps.setdefault(cid,[]).append(dict(ID=int(row['ID']),Status=row['ID'] in ('3110001002','3110001003')))
    stories={}
    for row in {r['ID']:r for r in table('Story') if r['channel_group'] in ('','0','25')}.values():
        gid=int(row['story_group'] or 0)
        if not gid:continue
        group=stories.setdefault(gid,dict(Unlock=True,SequenceStory=[],SeparatedStory={}))
        node=dict(StoryID=int(row['ID']),Unlock=True,CanUnlock=True)
        if int(row['serial'] or 0):group['SequenceStory'].append(node)
        else:group['SeparatedStory'][int(row['ID'])]=node
    seeds = {
        '/test/ok': {'body':'ok','type':'text/plain'},
        '/hello': {'body':'ok','type':'text/plain'},
        '/role/create': proto('api.CreateLoginResp', RoleID=1,Time=sync),
        '/role/userlogin': proto('api.CreateLoginResp', RoleID=1,Time=sync),
        '/role/login': proto('timermod.SyncTime',**sync),
        '/role/role':proto('rolemod.ComplexRole',roleInstanceProto=role,roleTimeInstance=sync['RoleTimeInstance'],
                          FashionInstances=[dict(FashionCardID=70000001,RoleID=1,Own=True,FashionRunes=dict(Runes=[0]*9))],PreRoleLevel=5),
        '/servant/servants':proto('svmod.ServantInstancesProto',servantInstanceProto=servants),
        '/task/all':proto('achievemod.Result',Jobs=[dict(ID=n,Status=1,Valid=1,Guide=True) for n in tutorial_jobs]),
        '/story/get':proto('storymod.Story',StoryGroup=stories,Version=1),
        '/level/getAllProgress':proto('levelmod.Chaps',Data=[dict(ID=k,Levels=v,Version=1) for k,v in chaps.items()]),
        '/evnInfo/get':proto('actionmod.Environment',CallbackIP='127.0.0.1',TimeZone=8,extraInfo={}),
        '/login/complete':proto('actionmod.CommonInfo',Result='ok',extraInfo={}),
        '/level/startBattle':proto('actionmod.CommonInfo',Result='ok',extraInfo={}),
        '/level/rebattle':proto('actionmod.CommonInfo',Result='ok',extraInfo={}),
        '/time/sync':proto('timermod.SyncTime',**sync),
        '/timer/sync':proto('timermod.Timer',second=stamp),
        '/guild/getUserGuild':proto('guildmod.GuildInfo',UserInfo={},Result='ok',ExtraInfo={}),
        '/ap/instance/get':proto('apmod.ActivityGameInstance',AccSet={},MercenaryInfo={},extraInfo={}),
        '/ap/getRank':proto('apmod.RankDatas'),
        '/csc/GetRank':proto('apmod.RankDatas'),
        '/resource/recycle/get':proto('resourcemod.RecycleInstance'),
    }
    for key, value in seeds.items():
        responses[key]=value
        responses['/game'+key]=value
    path.write_text(json.dumps(responses,ensure_ascii=False,indent=2),'utf8')
    inventory={}
    for fd in FILES:
        for m in fd.message_type:
            name=fd.package+'.'+m.name
            inventory[name]={f.name:{'number':f.number,'type':f.type,'label':f.label,'message':f.type_name} for f in m.field}
    (ROOT/'evidence/proto_schema.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),'utf8')
    print('Seed routes',len(responses),'protocol messages',len(inventory))

if __name__=='__main__':main()
