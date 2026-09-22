-- The native MobInfo loader ignores LifeTime. Use its normal death/AI cleanup
-- when an allied summon reaches its local lifetime; never touch enemy mobs.
do
    require 'tolua.reflection';tolua.loadassembly('Assembly-CSharp')
    local kind=typeof('unit.MonsterEntity');local voType=typeof('MonsterVO')
    local voField=tolua.getfield(kind,'monsterVO',65535)
    local idField=tolua.getfield(voType,'ID',65535)
    local master=tolua.getproperty(typeof('Entity'),'Master',65535)
    local die=tolua.gettypemethod(kind,'ExecDeath',65535)
    local ttl={['332010380501']=18,['332010381501']=20,['332010381701']=25,['332010340501']=16}
    local seen,nextCheck={},0
    local function tick()
        local now=UnityEngine.Time.time
        if now<nextCheck then return end;nextCheck=now+0.25
        local arr=UnityEngine.Object.FindObjectsOfType(kind);local live={}
        for i=0,arr.Length-1 do
            local entity=arr[i];local vo=voField:Get(entity)
            local duration=vo and ttl[tostring(idField:Get(vo))]
            if duration and master:Get(entity,nil) then
                local id=entity:GetInstanceID();live[id]=true
                local entry=seen[id]
                if not entry then entry={born=now,expired=false};seen[id]=entry end
                if not entry.expired and now-entry.born>=duration then
                    entry.expired=true;die:Call(entity)
                end
            end
        end
        for id in pairs(seen) do if not live[id] then seen[id]=nil end end
    end
    UpdateBeat:Add(function()
        local ok,err=pcall(tick)
        if not ok then UnityEngine.Debug.LogError('OFFLINE_SUMMON '..tostring(err));nextCheck=UnityEngine.Time.time+10 end
    end)
end
