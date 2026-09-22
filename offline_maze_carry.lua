-- Apply the expedition checkpoint once per spawned hero, and capture energy.
do
    require 'tolua.reflection';tolua.loadassembly('Assembly-CSharp')
    local F=65535
    local function field(t,n,o)return tolua.getfield(typeof(t),n,F):Get(o)end
    local function method(t,n,types)
        return tolua.gettypemethod(typeof(t),n,F,System.Type.DefaultBinder,types,nil)
    end
    local getProperty=tolua.gettypemethod(typeof('HeroEntity'),'GetProperty',F)
    local value=method('PropertyValue','GetValue',{typeof('System.Int32')})
    local setHP=method('Entity','SetHP',{typeof('System.Int64'),typeof('System.Boolean')})
    local dir='/data/data/com.codex.witchweapon.local/files/'
    local nextTick=0;local hero=nil;local ready=0;local applied=false
    local function number(raw,key,default)
        return tonumber(raw:match('"'..key..'"%s*:%s*([%d%.%-]+)')) or default
    end
    local function update()
        local now=UnityEngine.Time.realtimeSinceStartup
        if now<nextTick then return end;nextTick=now+0.5
        local h=field('HeroEntity','instance',nil)
        if not h or h:Equals(nil) then hero=nil;applied=false;return end
        if h~=hero then hero=h;ready=now+1.5;applied=false end
        if now<ready then return end
        local file=io.open(dir..'offline_save_v1.json','r');if not file then return end
        local raw=file:read('*a');file:close()
        if number(raw,'activeStage',0)~=3110001003 or not raw:match('"active"%s*:%s*true') then return end
        local ps=field('HeroEntity','powerAndSharp',h);if not ps then return end
        local data=field('BuildPowerAndSharp','powerData',ps);if not data then return end
        if not applied then
            local prop=getProperty:Call(h)
            local max=value:Call(field('PropertiesVO','BHP',prop),0)
            if max<=0 then return end
            setHP:Call(h,math.max(1,math.floor(max*number(raw,'mazeHP',1)+0.5)),false)
            local e=data:GetEnumerator()
            while e:MoveNext() do
                local pd=e.Current.Value;local id=tostring(field('PowerData','servantID',pd))
                tolua.getfield(typeof('PowerData'),'currentPower',F):Set(pd,number(raw,'mazeEnergy_'..id,1000))
            end
            applied=true
            UnityEngine.Debug.Log("LOCAL_MAZE_CHECKPOINT round="..number(raw,"battleMazeRound",1).." hp="..number(raw,"mazeHP",1))
        end
        local key=raw:match('"startKey"%s*:%s*"([%d%-]+)"') or ''
        local parts={'"startKey":"'..key..'"'}
        local e=data:GetEnumerator()
        while e:MoveNext() do
            local pd=e.Current.Value;local id=tostring(field('PowerData','servantID',pd))
            parts[#parts+1]='"mazeEnergy_'..id..'":'..tostring(field('PowerData','currentPower',pd))
        end
        local f=io.open(dir..'offline_battle_energy.tmp','w')
        if f then f:write('{'..table.concat(parts,',')..'}');f:close();os.rename(dir..'offline_battle_energy.tmp',dir..'offline_battle_energy.json') end
    end
    local failed=false
    UpdateBeat:Add(function()
        if failed then return end
        local ok,err=pcall(update)
        if not ok then failed=true;UnityEngine.Debug.LogError('LOCAL_MAZE_CARRY '..tostring(err)) end
    end)
end
