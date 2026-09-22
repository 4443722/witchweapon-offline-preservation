-- UIChest.Open(14, id) in this client only logs "item". Complete its
-- fixed-gift preview with the original widgets and native claim callback.
do
    require 'tolua.reflection';tolua.loadassembly('Assembly-CSharp')
    local chestType=typeof('UIChest')
    local function method(name,types)
        return tolua.gettypemethod(chestType,name,65535,System.Type.DefaultBinder,types,nil)
    end
    local nextCheck,last=0,nil
    local function field(name,ui)return tolua.getfield(chestType,name,65535):Get(ui)end
    local function update()
        local now=UnityEngine.Time.realtimeSinceStartup
        if now<nextCheck then return end;nextCheck=now+0.25
        -- Native loot changes the selected label before the asynchronous full
        -- inventory refresh. Keep it bound to the refreshed original model.
        local detailType=typeof('ItemInfoView')
        local detail=UnityEngine.Object.FindObjectOfType(detailType)
        if detail and tolua.getfield(detailType,'itemContainer',65535):Get(detail).gameObject.activeInHierarchy then
            tolua.gettypemethod(detailType,'ReSetNumber',65535):Call(detail)
        end
        local ui=UnityEngine.Object.FindObjectOfType(chestType)
        if not ui or ui:Equals(nil) then last=nil;return end
        if ui==last or tonumber(field('dataType',ui))~=14 then return end
        field('chooseOneWidget',ui).gameObject:SetActive(false)
        field('itemWdiget',ui).gameObject:SetActive(true)
        field('itemBg',ui).gameObject:SetActive(true)
        field('chestItemGetAwardBtn',ui).gameObject:SetActive(true)
        field('closeBtn',ui).gameObject:SetActive(true)
        field('cannelBtn',ui).gameObject:SetActive(true)
        local name,desc='物品礼包','获得物品说明中的全部奖励。'
        if detail and tostring(tolua.getfield(detailType,'itemId',65535):Get(detail))==tostring(field('dataID',ui)) then
            name=tolua.getfield(detailType,'itemName',65535):Get(detail).text
            desc=tolua.getfield(detailType,'descItemText',65535):Get(detail).text
            if desc=='' then desc=tolua.getfield(detailType,'item_descText',65535):Get(detail).text end
        end
        local rewards=method('GetChestItemDatas',{typeof('System.Int64')}):Call(ui,field('dataID',ui))
        local entries=rewards:GetEnumerator()
        if entries:MoveNext() then method('CreateItem',{typeof('LotteryLootData')}):Call(ui,entries.Current) end
        field('itemName',ui).text='奖励预览'
        local text=field('chestItemText',ui)
        text.fontSize=22
        text.text='使用1个，获得全部奖励：\n'..desc
        last=ui
    end
    UpdateBeat:Add(function()
        local ok,err=pcall(update)
        if not ok then UnityEngine.Debug.LogError('OFFLINE_INVENTORY '..tostring(err));nextCheck=UnityEngine.Time.realtimeSinceStartup+10 end
    end)
end
