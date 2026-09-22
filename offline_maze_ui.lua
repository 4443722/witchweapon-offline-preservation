-- Persistent twelve-encounter expedition label; no development command hook.
do
    require 'tolua.reflection'
    tolua.loadassembly('Assembly-CSharp')
    tolua.loadassembly('Assembly-CSharp-firstpass')
    local nextCheck = 0
    local detailType = typeof('WaterBell.ProjX.View.Panel.SelectLevelDetail')
    local fields = nil
    local rosters = {}
    local lastPanel,lastRound=nil,nil
    local function refreshMazeLabel()
        local now = UnityEngine.Time.realtimeSinceStartup
        if now < nextCheck then return end
        nextCheck = now + 0.5
        local mapType=typeof('WaterBell.ProjX.View.Panel.MapPanelControl')
        local map=UnityEngine.Object.FindObjectOfType(mapType)
        if map then
            local function mf(name)return tolua.getfield(mapType,name,65535):Get(map)end
            for name,text in pairs({chapterNameLabel='单人作战',chapterNameLabel_EN='Training & Labyrinth',en_chapterNameLabel='Training & Labyrinth',chapterIndexLabel='01'}) do
                local l=mf(name);if l then l.text=text end
            end
            for _,name in ipairs({'prevChapterButton','nextChapterButton','butonDiffContainer','portalButtons'}) do
                local obj=mf(name);if obj then obj:SetActive(false) end
            end
            local icons=mf('levelIconDict')
            if icons then
                local e=icons:GetEnumerator()
                while e:MoveNext() do
                    local id=tonumber(tostring(e.Current.Key));local icon=e.Current.Value
                    local supported=id==3110001002 or id==3110001003
                    icon.gameObject:SetActive(supported)
                    if supported then
                        local label=tolua.getfield(typeof('WaterBell.ProjX.View.Panel.BMLevelIcon'),'indexLabel',65535):Get(icon)
                        if label then label.text=id==3110001002 and '训练营' or '迷宫' end
                    end
                end
            end
        end
        local settleType=typeof('WaterBell.ProjX.View.Panel.SettlementUI')
        local settle=UnityEngine.Object.FindObjectOfType(settleType)
        if settle then
            local sid=tonumber(tostring(tolua.getfield(settleType,'instanceId',65535):Get(settle)))
            if sid==3110001002 or sid==3110001003 then
                local l=tolua.getfield(settleType,'instanceIndexLabel',65535):Get(settle)
                if l then l.text=sid==3110001002 and '训练营' or '迷宫' end
            end
        end
        local panel = UnityEngine.Object.FindObjectOfType(detailType)
        if not panel then return end
        if not fields then
            require 'tolua.reflection'
            tolua.loadassembly('Assembly-CSharp')
            fields = {}
            for _, name in ipairs({'instanceId','chapterNameLabel','chapterNameENLabel','EnchapterName','taskName','taskDescLabel'}) do
                fields[name] = tolua.getfield(detailType, name, 65535)
            end
        end
        local id=tonumber(tostring(fields.instanceId:Get(panel)))
        if id~=3110001003 and id~=3110001002 then return end
        local function label(name, text)
            local component = fields[name]:Get(panel)
            if component and component.text ~= text then component.text = text end
        end
        if id==3110001002 then
            label('chapterNameLabel','训练营')
            label('chapterNameENLabel','Training Camp')
            label('EnchapterName','Training Camp')
            label('taskName','自由战斗训练')
            label('taskDescLabel','练习移动、切换武器和召唤技能\n不消耗体力，可反复进入')
            return
        end
        local round=1
        local f=io.open('/data/data/com.codex.witchweapon.local/files/offline_save_v1.json','r')
        if f then local raw=f:read('*a');f:close();round=tonumber(raw:match('"mazeRound"%s*:%s*(%d+)')) or 1 end
        local titles={'金属与玫瑰','执行人与守护者','双首领防线','冰霜与驱魔','黑暗中的伏击','天照的反击',
            '歌声与灵体','召唤者之庭','骑士与召唤者','长枪与暗月','医疗防线','三重灵体'}
        local shown=math.min(round,12)
        if rosters[shown] and (lastPanel~=panel or lastRound~=shown) then
            local mob=tolua.getfield(detailType,'mobData',65535):Get(panel)
            if mob then
                for i,pair in ipairs(rosters[shown]) do
                    tolua.getfield(typeof('TypeCsvInstanceMobList'),'mob'..i,65535):Set(mob,pair[1])
                    tolua.getfield(typeof('TypeCsvInstanceMobList'),'mob'..i..'_type',65535):Set(mob,pair[2])
                    tolua.getfield(typeof('TypeCsvInstanceMobList'),'mob'..i..'_lv',65535):Set(mob,5)
                end
                tolua.gettypemethod(detailType,'SetEnemyAndAllies',65535):Call(panel)
                lastPanel,lastRound=panel,shown
            end
        end
        label('chapterNameLabel',titles[shown])
        label('chapterNameENLabel','Labyrinth')
        label('EnchapterName','Labyrinth')
        label('taskName',round>12 and '本轮通关' or ('迷宫 '..shown..'/12'))
        label('taskDescLabel',round>12 and '十二关已完成！\n再次出击开始新一轮' or '剩余生命、能量带入下一关\n每三关回复30%生命、300能量\n另获1万金币，失败可重试')
    end
    UpdateBeat:Add(function()
        local ok,err=pcall(refreshMazeLabel)
        if not ok then UnityEngine.Debug.LogError('LOCAL_MAZE_UI '..tostring(err)) end
    end)
end
