"""Read back real emulator state; replay only its already-completed settlement."""
import base64,json
from pathlib import Path
from urllib.parse import urlencode
from emulator import run,pull,ROOT,PACKAGE,SHARED
from offline_seed import message

def request(path,args=None):
    body=urlencode(args or {}).encode()
    raw=(f'POST {path} HTTP/1.1\r\nHost: 127.0.0.1:19876\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n').encode()+body
    (SHARED/'Misc'/'witch_verify_http.bin').write_bytes(raw)
    response=base64.b64decode(run('cat /mnt/shared/Misc/witch_verify_http.bin | toybox nc -w 5 -W 5 127.0.0.1 19876 | base64'))
    head,data=response.split(b'\r\n\r\n',1)
    assert head.startswith(b'HTTP/1.1 200 '),head
    return data

def parse(name,data):
    m=message(name);m.ParseFromString(data);return m

if __name__=='__main__':
    before=pull('/data/data/'+PACKAGE+'/files/offline_save_v1.json')
    state=json.loads(before);assert state['wins']>0
    result=request('/level/pushMainLineProgress',state['lastBattle'])
    assert result==base64.b64decode(state['battleResponse'])
    assert pull('/data/data/'+PACKAGE+'/files/offline_save_v1.json')==before,'Replay changed save'
    role=parse('rolemod.ComplexRole',request('/role/role')).roleInstanceProto
    assert role.Gold==state['gold'] and role.Exp==state['exp']
    chaps=parse('levelmod.Chaps',request('/level/getAllProgress'))
    level=next(l for c in chaps.Data for l in c.Levels if l.ID==3110001002)
    assert level.Pass and level.Stars==(state['stars']==3)
    report=dict(gold=role.Gold,exp=role.Exp,wins=state['wins'],all_stars=level.Stars,
                settlement_replay_unchanged=True,progress_protocol_matches_save=True)
    (ROOT/'evidence/save_protocol_verification.json').write_text(json.dumps(report,indent=2),'utf8')
    print(json.dumps(report))
