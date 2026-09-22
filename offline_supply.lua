-- Refresh the original observable models after a committed inventory transaction.
-- Native callbacks still show their original loot and sale dialogs.
do
    local nextCheck,lastRevision,pending,lastCollection,collectionPending=0,nil,nil,nil,false
    local function supplyRefresh()
        local now=UnityEngine.Time.realtimeSinceStartup
        if now<nextCheck then return end
        nextCheck=now+1
        require 'tolua.reflection';tolua.loadassembly('Assembly-CSharp')
        local shopType=typeof('NewShopPanelControl')
        local shop=UnityEngine.Object.FindObjectOfType(shopType)
        if shop then
            for _,name in ipairs({'buyWidget','FreshView'}) do
                local widget=tolua.getfield(shopType,name,65535):Get(shop)
                if widget then widget.gameObject:SetActive(false) end
            end
        end
        local f=io.open('/data/data/com.codex.witchweapon.local/files/offline_save_v1.json','r')
        if not f then return end
        local text=f:read('*a');f:close()
        local player=WaterBell.ProjX.Data.Entity.UserInfo.GetInstance():GetPlayer()
        if not player then return end
        -- ActivityPlay's constructor/setContent clear this balance on seasonal
        -- initialization. Offline supplies persist across those lifecycle resets.
        local activityStamina=tonumber(text:match('"activityStamina"%s*:%s*(%d+)')) or 200
        if player.ActivityStamina~=activityStamina then player.ActivityStamina=activityStamina end
        local revision=tonumber(text:match('"inventoryRevision"%s*:%s*(%d+)')) or 0
        local collection=tonumber(text:match('"collectionRevision"%s*:%s*(%d+)')) or 0
        if lastCollection==nil then lastCollection=collection end
        if collection~=lastCollection then lastCollection=collection;collectionPending=true;pending=now+1 end
        if lastRevision==nil then lastRevision=revision end
        if revision~=lastRevision then lastRevision=revision;pending=now+1 end
        if not pending or now<pending then return end
        require 'tolua.reflection';tolua.loadassembly('Assembly-CSharp')
        for _,name in ipairs({'BackpackGetAllItemsLogic','BackpackGetAllEquipsLogic'}) do
            local msg=tolua.createinstance(typeof('WaterBell.ProjX.Data.NetIO.'..name))
            tolua.gettypemethod(typeof('WaterBell.ProjX.Data.NetIO.NetMsgBase'),'SendMsg',65535):Call(msg)
        end
        if collectionPending then
            for _,name in ipairs({'GetServantListLogic','RoleGetRoleInfoLogic'}) do
                local msg=tolua.createinstance(typeof('WaterBell.ProjX.Data.NetIO.'..name))
                tolua.gettypemethod(typeof('WaterBell.ProjX.Data.NetIO.NetMsgBase'),'SendMsg',65535):Call(msg)
            end
            collectionPending=false
        end
        player.Gold=tonumber(text:match('"gold"%s*:%s*(%d+)'))
        -- The generated Lua wrapper exposes only Diamond's getter.
        local diamonds=tonumber(text:match('"rmb"%s*:%s*(%d+)')) or 100000
        tolua.getproperty(typeof('WaterBell.ProjX.Data.Entity.ObservablePlayer'),'Diamond',65535):Set(player,int64.new(diamonds),nil)
        player.Stamina=tonumber(text:match('"stamina"%s*:%s*(%d+)')) or 200
        pending=nil
    end
    UpdateBeat:Add(function()
        local ok,err=pcall(supplyRefresh)
        if not ok then UnityEngine.Debug.LogError('OFFLINE_SUPPLY '..tostring(err));nextCheck=UnityEngine.Time.realtimeSinceStartup+10 end
    end)
end
