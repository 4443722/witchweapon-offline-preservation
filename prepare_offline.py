from pathlib import Path
import os,sys,json,zipfile,hashlib,subprocess,struct,csv,io,re

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/python'))
import UnityPy
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM,CS_ARCH_ARM64,CS_MODE_ARM

OVERRIDES=ROOT/'overrides'
SOURCE_APK=Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk'))

def write(name,data):
    p=OVERRIDES/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)

def patch_lua_bundle(name, changes):
    env=UnityPy.load(str(ROOT/'original_parts'/name))
    patched=[]
    for obj in env.objects:
        if obj.type.name!='TextAsset':continue
        tree=obj.read_typetree()
        if tree['m_Name'] not in changes:continue
        script=tree['m_Script']
        was_bytes=isinstance(script,bytes)
        if was_bytes:script=script.decode('utf8')
        script=changes[tree['m_Name']](script)
        tree['m_Script']=script.encode('utf8') if was_bytes else script
        obj.save_typetree(tree);patched.append(tree['m_Name'])
    assert set(patched)==set(changes),(name,patched)
    write(name,env.file.save(packer='original'))

def main():
    from offline_story import prepare as prepare_story
    prepare_story()
    from offline_maze import prepare as prepare_maze
    prepare_maze()
    from offline_progression import prepare as prepare_progression
    prepare_progression()
    from offline_skills import prepare_templates
    prepare_templates()
    rooturl='http://127.0.0.1:19876'
    original=ROOT/'original_parts/assets/assetbundle/config/xmlconf/accconf.ab'
    env=UnityPy.load(str(original))
    for obj in env.objects:
        if obj.type.name!='MonoBehaviour':continue
        tree=obj.read_typetree();raw=bytes(tree['bytes'])
        import re
        txt=bytes(x^255 for x in raw).decode('utf-8-sig')
        txt=re.sub(r'url="[^"]*"','url="'+rooturl+'"',txt)
        tree['bytes']=list(bytes(x^255 for x in ('\ufeff'+txt).encode('utf8')))
        obj.save_typetree(tree)
    write('assets/assetbundle/config/xmlconf/accconf.ab',env.file.save(packer='original'))
    patch_lua_bundle('assets/assetbundle/lua/lua_projx_model.ab',{
        'ActivityModel.lua':lambda s:s.replace('ActivityModel = {}','ActivityModel = {ServerData = {}, ServerDataAll = {}}',1)
    })
    patch_lua_bundle('assets/assetbundle/lua/lua_projx_ui.ab',{
        'MainScenePanelAdd.lua':lambda s:s.replace('data999.CanReceive','(data999 and data999.CanReceive)',2).replace('function MainScenePanelAdd.showOnNewDay( ... )','function MainScenePanelAdd.showOnNewDay( ... )\n\tdo return end')
    })
    def local_init(s):
        start=s.index('local opName = VideoManager.GetOPName()')
        end=s.index('local isPrint',start)
        s=s[:start]+'VideoManager.ClosePVToLoginFormal()\n\n'+s[end:]
        from offline_maze_round import lua_rosters
        s+='\n'+(ROOT/'offline_maze_ui.lua').read_text('utf8').replace('local rosters = {}','local rosters = '+lua_rosters())
        s+='\n'+(ROOT/'offline_maze_carry.lua').read_text('utf8')
        s+='\n'+(ROOT/'offline_supply.lua').read_text('utf8')
        s+='\n'+(ROOT/'offline_inventory.lua').read_text('utf8')
        s+='\n'+(ROOT/'offline_summons.lua').read_text('utf8')
        if '--debug' in sys.argv:
            s+='''
-- Temporary development hook, excluded from release preparation.
-- The command file is looked up next to the game's own sandbox so the same
-- script works whether the external files dir is writable by adb or not.
do
    local nextCheck = 0
    local paths = {
        UnityEngine.Application.persistentDataPath..'/offline_command.lua',
        '/data/data/com.codex.witchweapon.local/files/offline_command.lua',
    }
    local function offlineTick()
        local now = UnityEngine.Time.realtimeSinceStartup
        if now < nextCheck then return end
        nextCheck = now + 1
        local code = nil
        for _, path in ipairs(paths) do
            local f = io.open(path, 'r')
            if f then
                code = f:read('*a'); f:close(); os.remove(path)
                if code and #code > 0 then break end
                code = nil
            end
        end
        if not code then return end
        local fn, err = loadstring(code, 'offline_command')
        if fn then
            local ok, result = xpcall(fn, debug.traceback)
            UnityEngine.Debug.LogError('OFFLINE_COMMAND '..tostring(ok)..' '..tostring(result))
        else UnityEngine.Debug.LogError('OFFLINE_COMMAND syntax '..tostring(err)) end
    end
    UpdateBeat:Add(offlineTick)
end
'''
        if '--selftest' in sys.argv:
            s+='\n'+(ROOT/'build/lua/probe_draw.lua').read_text('utf8')
        return s
    patch_lua_bundle('assets/assetbundle/lua/lua.ab',{'init.lua':local_init})
    # Main tutorial quests are marked completed in the seed. Remove the separate
    # first-chapter forced control hints; the original story entries stay intact.
    name='assets/assetbundle/config/clientexel/lessontrigger.ab'
    env=UnityPy.load(str(ROOT/'original_parts'/name))
    for obj in env.objects:
        if obj.type.name!='MonoBehaviour':continue
        tree=obj.read_typetree();txt=bytes(b^255 for b in tree['bytes']).decode('utf-8-sig')
        rows=list(csv.reader(io.StringIO(txt)))
        removed=set(range(200,218))|{220}
        rows=[r for r in rows if not r or not r[0].isdigit() or int(r[0]) not in removed]
        stream=io.StringIO();csv.writer(stream,lineterminator='\r\n').writerows(rows)
        tree['bytes']=list(b^255 for b in ('\ufeff'+stream.getvalue()).encode('utf8'))
        obj.save_typetree(tree)
    write(name,env.file.save(packer='original'))
    patches=[]
    for bits,abi in [(32,'armeabi-v7a'),(64,'arm64-v8a')]:
        source=ROOT/f'original_parts/lib/{abi}/libil2cpp.so';data=bytearray(source.read_bytes())
        script=json.loads((ROOT/f'decoded/il2cpp{bits}/script.json').read_text(encoding='utf-8-sig'))
        method=next(m for m in script['ScriptMethod'] if m['Name']=='UnityEngine.Application$$get_internetReachability')
        address=method['Address']
        with source.open('rb') as f:
            elf=ELFFile(f);seg=next(s for s in elf.iter_segments() if s['p_vaddr']<=address<s['p_vaddr']+s['p_filesz'])
            offset=seg['p_offset']+address-seg['p_vaddr']
        # The local HTTP service is reachable when Wi-Fi/mobile data are off.
        patch=bytes.fromhex('0200a0e31eff2fe1' if bits==32 else '40008052c0035fd6')
        instructions=[i.mnemonic+' '+i.op_str for i in Cs(CS_ARCH_ARM if bits==32 else CS_ARCH_ARM64,CS_MODE_ARM).disasm(patch,address)]
        assert len(instructions)==2
        before=bytes(data[offset:offset+len(patch)]);data[offset:offset+len(patch)]=patch
        write(f'lib/{abi}/libil2cpp.so',data)
        patches.append({'abi':abi,'method':method['Name'],'address':hex(address),'offset':offset,'before':before.hex(),'after':patch.hex(),'disassembly':instructions})
        # NOTE (round 3): the test emulator runs this game on the 32-bit
        # armeabi-v7a ABIs -- the game log reports "arch: arm / ARMv7 VFPv3" --
        # so 64-bit arm64-v8a patches to this method never execute. The two
        # field-offset patches previously applied here have been removed: they
        # were dead code, and the premise was wrong anyway, because loop A
        # indexes lotteryLootDataList ([$this+0xC0]) and connectStarList
        # ([$this+0xC8]), not starSelectEffectList. See the round-3 report.
        for address,before_word,after_word in []:
            if bits!=64:
                continue
            with source.open('rb') as f:
                elf=ELFFile(f);seg=next(s for s in elf.iter_segments() if s['p_vaddr']<=address<s['p_vaddr']+s['p_filesz'])
                offset=seg['p_offset']+address-seg['p_vaddr']
            original=bytes(data[offset:offset+4])
            expected=struct.pack('<I',before_word)
            patched=struct.pack('<I',after_word)
            # Hard assertion: abort the build rather than write a wrong offset.
            assert original in (expected,patched),(
                f'star-map patch site {address:#x}: expected {expected.hex()} '
                f'or {patched.hex()}, found {original.hex()}')
            data[offset:offset+4]=patched
            write(f'lib/{abi}/libil2cpp.so',data)
            instructions=[i.mnemonic+' '+i.op_str for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(patched,address)]
            patches.append({'abi':abi,'method':'WaterBell.ProjX.View.Panel.LotteryUniverse.<ShowResult>c__Iterator0$$MoveNext','address':hex(address),'offset':offset,'before':original.hex(),'after':patched.hex(),'disassembly':instructions})
            print(f'  star-map field patch {address:#x}: {original.hex()} -> {patched.hex()}  ({instructions})')
        # The standalone shop offers one free supply box per click. Original
        # quantity calculation divides currency by price and SIGFPEs at zero.
        method=next(m for m in script['ScriptMethod'] if m['Name']=='ShopItemInfo$$GetMaxNumber')
        address=method['Address']
        with source.open('rb') as f:
            elf=ELFFile(f);seg=next(s for s in elf.iter_segments() if s['p_vaddr']<=address<s['p_vaddr']+s['p_filesz'])
            offset=seg['p_offset']+address-seg['p_vaddr']
        # this.maxNumber = 1; return (field offsets verified in both dumps).
        words=[0xe3a01001,0xe5801170,0xe12fff1e] if bits==32 else [0x52800021,0xb9000001 | ((0x2a4//4)<<10),0xd65f03c0]
        patch=b''.join(struct.pack('<I',w) for w in words)
        instructions=[i.mnemonic+' '+i.op_str for i in Cs(CS_ARCH_ARM if bits==32 else CS_ARCH_ARM64,CS_MODE_ARM).disasm(patch,address)]
        before=bytes(data[offset:offset+len(patch)]);data[offset:offset+len(patch)]=patch
        write(f'lib/{abi}/libil2cpp.so',data)
        patches.append({'abi':abi,'method':method['Name'],'address':hex(address),'offset':offset,'before':before.hex(),'after':patch.hex(),'disassembly':instructions})
    (ROOT/'evidence/native_patches.json').write_text(json.dumps(patches,indent=2),encoding='utf8')
    endpoint=lambda body,kind='text/plain; charset=utf-8':{'body':body,'type':kind}
    envxml='<config><tag name="offline">'+''.join('<'+n+' url="'+rooturl+'/"/>' for n in ['account','notice','talking','cdn','asbd','apk'])+'</tag></config>'
    mapping='<config><mapping><item name="offline"><versions><version code="2.0.1"/></versions></item></mapping></config>'
    responses={'*.env':endpoint(envxml,'application/xml'),'*.mapping':endpoint(mapping,'application/xml'),'/getversion':endpoint('2.0.1.20043076\r\n'),'/m.version':endpoint('2.0.1.20043076\r\n')}
    config=ROOT/'offline_responses.json'
    if not config.exists():config.write_text(json.dumps(responses,ensure_ascii=False,indent=2),encoding='utf8')
    write('assets/offline_responses.json',config.read_bytes())
    with zipfile.ZipFile(SOURCE_APK) as z:
        lines=z.read('assets/m.assets_list.txt').decode('utf8').splitlines();modified=[]
        for line in lines:
            digest,item=line.split('=',1);name,size=item.rsplit(':',1)
            override=OVERRIDES/'assets/assetbundle'/name.lstrip('/')
            if override.is_file():
                data=override.read_bytes();line=hashlib.md5(data).hexdigest()+'='+name+':'+str(len(data))
            modified.append(line)
        indexed={line.split('=',1)[1].rsplit(':',1)[0] for line in modified}
        for path in sorted((OVERRIDES/'assets/assetbundle').rglob('*.ab')):
            name='/'+path.relative_to(OVERRIDES/'assets/assetbundle').as_posix()
            if name not in indexed:
                data=path.read_bytes();modified.append(hashlib.md5(data).hexdigest()+'='+name+':'+str(len(data)))
        write('assets/m.assets_list.txt',('\n'.join(modified)+'\n').encode('utf8'))
    sdk=Path(os.environ.get('WW_ANDROID_SDK',Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData'/'Local'))/'Android'/'Sdk'))
    java=Path(os.environ.get('WW_JAVA_BIN',Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Microsoft'/'jdk-17.0.11.9-hotspot'/'bin'))
    classes=ROOT/'build/java';classes.mkdir(parents=True,exist_ok=True);dex=ROOT/'build/java_dex';dex.mkdir(exist_ok=True)
    subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','--release','8','-classpath',str(sdk/'platforms/android-34/android.jar'),'-d',str(classes)]+[str(ROOT/n) for n in ['OfflineApplication.java','LocalSave.java','LocalEconomy.java','ProtoWire.java']],check=True)
    subprocess.run([str(java/'java.exe'),'-cp',str(sdk/'build-tools/36.1.0/lib/d8.jar'),'com.android.tools.r8.D8','--min-api','21','--lib',str(sdk/'platforms/android-34/android.jar'),'--output',str(dex)]+[str(p) for p in classes.rglob('*.class')],check=True)
    write('classes2.dex',(dex/'classes.dex').read_bytes())
    print('Offline bootstrap prepared; native patches',len(patches))

if __name__=='__main__':main()
