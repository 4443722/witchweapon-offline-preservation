"""Operate only LDPlayer instance 6; never address the user's USB phone."""
from pathlib import Path
import os, subprocess, base64, sys, json, shutil

ROOT=Path(__file__).resolve().parent
LD=os.environ.get('WW_LDPLAYER',r'D:\leidian\LDPlayer9\ld.exe')
INDEX=os.environ.get('WW_LD_INDEX','6')
PACKAGE='com.codex.witchweapon.local'
SHARED=Path(os.environ.get('WW_LD_SHARED',str(Path.home()/'Documents'/'leidian9')))

def run(command, timeout=40):
    return subprocess.run([LD,'-s',INDEX,command],check=True,capture_output=True,timeout=timeout).stdout

def pull(remote):
    assert remote.startswith(('/sdcard/','/data/data/'+PACKAGE+'/')) and "'" not in remote
    size=int(run("stat -c %s '"+remote+"'").strip())
    chunks=[]
    for i in range((size+16383)//16384):
        for attempt in range(4):
            try:
                raw=base64.b64decode(run("dd if='"+remote+"' bs=16384 skip="+str(i)+" count=1 2>/dev/null | base64"))
                if len(raw)==min(16384,size-i*16384):chunks.append(raw);break
            except ValueError:pass
        else:raise RuntimeError('Short transfer at chunk '+str(i))
    return b''.join(chunks)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='exec':print(run(sys.argv[2]).decode('utf8','replace').replace('\r',''))
    elif mode=='screen':
        run('screencap -p /sdcard/Pictures/witchweapon_stage1.png')
        raw=(SHARED/'Pictures/witchweapon_stage1.png').read_bytes();assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        dest=ROOT/'evidence'/sys.argv[2];dest.write_bytes(raw);print(dest)
    elif mode=='log':
        raw=run('logcat -d -v threadtime -t '+(sys.argv[3] if len(sys.argv)>3 else '1200'))
        dest=ROOT/'evidence'/sys.argv[2];dest.write_bytes(raw);print(dest)
    elif mode=='launch':
        print(run('am start -W -n '+PACKAGE+'/com.shuiqinling.ww.android.LingGameActivity').decode('utf8','replace'))
    elif mode=='install':
        shared=SHARED/'Applications/witchweapon_stage1.apk'
        shutil.copyfile(ROOT/'build/witchweapon-stage1-test.apk',shared)
        print(run('pm install -r /mnt/shared/Applications/witchweapon_stage1.apk',180).decode('utf8','replace'))
    elif mode=='sync':
        shared=SHARED/'Misc/witchweapon_responses.json'
        shutil.copyfile(ROOT/'offline_responses.json',shared)
        print(run('cp /mnt/shared/Misc/witchweapon_responses.json /data/data/'+PACKAGE+'/files/offline_responses.json').decode('utf8','replace'))
        run('chmod 644 /data/data/'+PACKAGE+'/files/offline_responses.json')
    elif mode=='lua':
        source=Path(sys.argv[2])
        shared=SHARED/'Misc/witchweapon_command.lua'
        shutil.copyfile(source,shared)
        run('cp /mnt/shared/Misc/witchweapon_command.lua /data/data/'+PACKAGE+'/files/offline_command.lua')
        run('chmod 644 /data/data/'+PACKAGE+'/files/offline_command.lua')
    elif mode=='pull':
        dest=ROOT/'evidence'/sys.argv[3];dest.write_bytes(pull(sys.argv[2]));print(dest)
