--[[
PZBridge v2 — HTTP bridge mod for Project Zomboid
Endpoints: GET /snapshot, POST /act, POST/GET /npc, GET /npc/{name}, GET /zone
Includes NPC vitals, inventory, personality/traits, full character sheet.
]]

local ServerSocket     = luajava.bindClass('java.net.ServerSocket')
local Socket           = luajava.bindClass('java.net.Socket')
local PrintWriter      = luajava.bindClass('java.io.PrintWriter')
local BufferedReader   = luajava.bindClass('java.io.BufferedReader')
local InputStreamReader= luajava.bindClass('java.io.InputStreamReader')
local StringBuilder    = luajava.bindClass('java.lang.StringBuilder')
local JSON = luajava.bindClass('zombie.core.raknet.Json')

local PZBridge = {name="PZBridge",version="2.0.0",port=8742,running=false,server=nil,spawned_npcs={}}

-- ─── JSON encoder (handles nested tables) ──────────────────────────
local function esc(s) return (tostring(s):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r')) end
local function enc(v)
    local t = type(v)
    if t=="string" then return '"'..esc(v)..'"'
    elseif t=="number" or t=="boolean" then return tostring(v)
    elseif t=="nil" then return "null"
    elseif t=="table" then
        local is_arr=true; local mx=0
        for k in pairs(v) do
            if type(k)~="number" or k<1 or math.floor(k)~=k then is_arr=false end
            if k>mx then mx=k end
        end
        if is_arr and mx==#v then
            local p={}; for i=1,#v do p[i]=enc(v[i]) end; return '['..table.concat(p,',')..']'
        else
            local p={}; for k,va in pairs(v) do p[#p+1]='"'..esc(tostring(k))..'":'..enc(va) end; return '{'..table.concat(p,',')..'}'
        end
    else return '"'..esc(tostring(v))..'"' end
end
local function to_json(tbl)
    local ok,out=pcall(function() return JSON:encode(tbl) end)
    if ok and out then return out end
    return enc(tbl)
end
local function safe(v,d) return v~=nil and v or (d or "") end

-- ─── Vitals reader ─────────────────────────────────────────────────
local function readVitals(p)
    local st = p:getStats()
    if not st then return {hp=100,max_hp=100} end
    local function sf(f) local o,v=pcall(f); if o then return v end; return nil end
    local v = {
        hp = sf(function() return p:getHealth() end) or 100,
        max_hp = sf(function() return p:getMaxHealth() end) or 100,
        hunger = sf(function() return (st:getHunger() or 0)*100 end) or 0,
        thirst = sf(function() return (st:getThirst() or 0)*100 end) or 0,
        fatigue = sf(function() return (st:getFatigue() or 0)*100 end) or 0,
        endurance = sf(function() return (st:getEndurance() or 0) end) or 0,
        stress = sf(function() return (st:getStress() or 0)*100 end) or 0,
        boredom = sf(function() return (st:getBoredom() or 0)*100 end) or 0,
        morale = sf(function() return (st:getMorale() or 0)*100 end) or 0,
        temperature = sf(function() return (p:getBodyTemperature() or 37) end) or 37,
    }
    local bd = p:getBodyDamage()
    if bd then
        v.bleeding = bd:getBleeding()
        v.numBodyParts = bd:getNumBodyParts()
        local mp=0
        for i=1,(bd:getNumBodyParts() or 0) do
            local bp=bd:getBodyPart(i)
            if bp then local pt=bp:getPain() or 0; if pt>mp then mp=pt end end
        end
        v.pain = mp
    end
    return v
end

-- ─── Inventory reader ──────────────────────────────────────────────
local function readInventory(p)
    local inv = p:getInventory()
    if not inv then return {} end
    local items = {}
    local ok,list = pcall(function() return inv:getItems() end)
    if ok and list then
        for i=0,list:size()-1 do
            local it=list:get(i)
            if it then
                local function sf(f) local o,v=pcall(f); if o then return v end; return nil end
                items[#items+1] = {
                    type = sf(function() return it:getType() end) or "unknown",
                    name = sf(function() return it:getName() end) or "unknown",
                    count = sf(function() return it:getCount() end) or 1,
                    condition = sf(function() return it:getCondition() end) or -1,
                    weight = sf(function() return it:getWeight() end) or 0.1,
                    category = sf(function() return it:getCategory() end) or "Misc"
                }
            end
        end
    end
    return items
end

-- ─── Build character sheet for one NPC ─────────────────────────────
function PZBridge:buildNPCSheet(name)
    local nd = self.spawned_npcs[name]
    if not nd then return to_json({status="error",message="NPC not found: "..tostring(name)}) end
    local p = nd.survivor and nd.survivor:getPlayer()
    if not p then return to_json({status="error",message="NPC survivor object missing"}) end
    local vit=readVitals(p); local inv=readInventory(p)
    return to_json({status="ok",name=name,x=p:getX(),y=p:getY(),z=p:getZ(),hp=vit.hp,
        npc_state=nd.npc_state or "idle",personality=nd.personality or "none",traits=nd.traits or {},
        vitals=vit,inventory=inv,numItems=#inv})
end

-- ─── Build world snapshot ──────────────────────────────────────────
function PZBridge:buildSnapshot()
    local player = getPlayer()
    if not player then return to_json({status="offline",error="No player object"}) end
    local sq = getCell() and getCell():getGridSquare(player:getX(),player:getY(),player:getZ())
    local zone = "outdoors"
    if sq then local rm=sq:getRoom(); if rm then zone=safe(rm:getName(),"outdoors") end end
    local items={}
    if sq then
        local objs=sq:getObjects()
        if objs then for i=0,objs:size()-1 do
            local o=objs:get(i); local nm="unknown"
            if o then local sp=o:getSprite(); if sp then nm=safe(sp:getName(),"unknown") end end
            items[#items+1]={name=nm,x=sq:getX(),y=sq:getY(),z=sq:getZ()}
        end end
        local inv=sq:getItems()
        if inv then for i=0,inv:size()-1 do
            local it=inv:get(i); if it then items[#items+1]={name=safe(it:getType()),x=sq:getX(),y=sq:getY(),z=sq:getZ()} end
        end end
    end
    local zombieCount=0
    for dx=-15,15 do for dy=-15,15 do
        local chk=getCell() and getCell():getGridSquare(player:getX()+dx,player:getY()+dy,player:getZ())
        if chk and chk:getZombieCount then zombieCount=zombieCount+(chk:getZombieCount() or 0) end
    end end
    local time={}; local gt=getGameTime()
    if gt then time={hour=gt:getHour(),minute=gt:getMinutes(),day=gt:getDay(),month=gt:getMonth(),year=gt:getYear()} end
    local weather={}; local cm=getClimateManager()
    if cm and cm:getWeatherPeriod then local r=cm:getWeatherPeriod()
        if r then weather={temperature=r:getCurrentTemperature(),raining=r:isRaining()} end end
    local pv=readVitals(player); local pi=readInventory(player)
    local npcs={}
    for nm,nd in pairs(self.spawned_npcs) do
        local p=nd.survivor and nd.survivor:getPlayer()
        if p then
            local v=readVitals(p)
            local ic=0; local ok2,iv2=pcall(function() return p:getInventory():getItems():size() end)
            if ok2 then ic=iv2 or 0 end
            npcs[#npcs+1]={name=nm,x=p:getX(),y=p:getY(),z=p:getZ(),hp=v.hp,state="alive",
                npc_state=nd.npc_state or "idle",personality=nd.personality or "none",traits=nd.traits or {},
                vitals=v,numItems=ic}
        end
    end
    return to_json({status="ok",player=safe(player:getUsername()),x=player:getX(),y=player:getY(),z=player:getZ(),
        zone=zone,items=items,zombieCount=zombieCount,time=time,weather=weather,
        playerInventory=pi,playerNumItems=#pi,playerVitals=pv,npcs=npcs,npcCount=#npcs})
end

-- ─── Action dispatch ───────────────────────────────────────────────
function PZBridge:handleAction(npcName,action,params)
    local nd=self.spawned_npcs[npcName]
    if not nd then return to_json({status="error",message="NPC not found: "..tostring(npcName)}) end
    local p=nd.survivor and nd.survivor:getPlayer()
    if not p then return to_json({status="error",message="NPC survivor missing"}) end
    params=params or {}
    if action=="move_to" then
        p:setX(params.x or p:getX()); p:setY(params.y or p:getY()); p:setZ(params.z or p:getZ())
        nd.npc_state="moving"
        return to_json({status="ok",action="move_to",x=params.x or p:getX(),y=params.y or p:getY(),z=params.z or p:getZ()})
    end
    if action=="walk_to" then
        local x=params.x or p:getX(); local y=params.y or p:getY(); local z=params.z or p:getZ()
        if p:getPathFindBehavior then p:getPathFindBehavior():pathTo(x,y,z) end
        nd.npc_state="walking"; return to_json({status="ok",action="walk_to",x=x,y=y,z=z})
    end
    if action=="say" then p:say(params.text or ""); return to_json({status="ok",action="say",text=params.text or ""}) end
    if action=="attack" then
        local tgt=params.target_type or "zombie"
        if tgt=="zombie" then
            local sq=getCell() and getCell():getGridSquare(p:getX(),p:getY(),p:getZ())
            if sq and sq:getZombies then local zeds=sq:getZombies()
                if zeds and zeds:size()>0 then
                    if p:attack then p:attack(zeds:get(0)) end
                    return to_json({status="ok",action="attack",target="zombie"}) end end
            return to_json({status="ok",action="attack",message="No zombies nearby"}) end
        return to_json({status="error",message="Unknown target: "..tostring(tgt)}) end
    if action=="loot" then
        local sq=getCell() and getCell():getGridSquare(p:getX(),p:getY(),p:getZ())
        if sq and sq:getItems then local its=sq:getItems()
            if its and its:size()>0 then local ti=its:get(0)
                if p:getInventory then p:getInventory():AddItem(ti) end
                return to_json({status="ok",action="loot",item=params.item or ""}) end end
        return to_json({status="ok",action="loot",message="Nothing to loot"}) end
    if action=="set_personality" then
        nd.personality=params.text or nd.personality; nd.traits=params.traits or nd.traits or {}
        return to_json({status="ok",action="set_personality",personality=nd.personality,traits=nd.traits}) end
    if action=="set_state" then nd.npc_state=params.state or "idle"; return to_json({status="ok",action="set_state",state=nd.npc_state}) end
    if action=="follow" then
        nd.follow_target=params.target or (getPlayer() and getPlayer():getUsername())
        nd.npc_state="following"; return to_json({status="ok",action="follow",target=nd.follow_target}) end
    if action=="stop" then nd.follow_target=nil; nd.npc_state="idle"; return to_json({status="ok",action="stop"}) end
    return to_json({status="error",message="Unknown action: "..tostring(action)})
end

-- ─── Spawn NPC ─────────────────────────────────────────────────────
function PZBridge:spawnNPC(name,skin,x,y,z,personality,traits)
    name=tostring(name or ""); if name=="" then name="Survivor_"..tostring(math.random(10000,99999)) end
    if self.spawned_npcs[name] then return to_json({status="error",message="NPC already exists: "..name}) end
    local cell=getCell(); if not cell then return to_json({status="error",message="No cell"}) end
    local sq=cell:getGridSquare(x,y,z); if not sq then return to_json({status="error",message="Bad location"}) end
    local surv=nil
    local ok,SF=pcall(function() return luajava.bindClass('zombie.survivor.SurvivorFactory') end)
    if ok and SF and SF:createSurvivor then surv=SF:createSurvivor(name,sq) end
    if not surv then
        ok,surv=pcall(function()
            local IP=luajava.bindClass('zombie.iso.IsoPlayer')
            local pp=IP:new(cell,sq,name); pp:setUsername(name); return pp end)
        if not ok then surv=nil end end
    if not surv then return to_json({status="error",message="Failed to create NPC"}) end
    self.spawned_npcs[name]={survivor=surv,npc_state="idle",follow_target=nil,personality=personality or "",
        traits=traits or {}}
    return to_json({status="ok",action="spawn",name=name,x=x,y=y,z=z,personality=personality or "",traits=traits or {}})
end

-- ─── Read request body ─────────────────────────────────────────────
local function readBody(instream)
    local body=StringBuilder:new()
    local line=instream:readLine()
    while line~=nil do body:append(line); body:append("\n"); line=instream:readLine() end
    return body:toString()
end

-- ─── Route one connection ──────────────────────────────────────────
function PZBridge:handleConnection(conn)
    local instream = BufferedReader:new(InputStreamReader:new(conn:getInputStream()))
    local out      = PrintWriter:new(conn:getOutputStream(),true)
    local cors     = "Access-Control-Allow-Origin: *\r\n"
    local reqLine = instream:readLine()
    if reqLine then
        local method,path = reqLine:match('^([A-Z]+)%s+(%S+)')
        if method and path then
            local h=instream:readLine()
            while h~=nil and h~="" do h=instream:readLine() end
            local body=""
            if method=="POST" then body=readBody(instream) end
            local status,payload
            -- Route: /npc/{name} (must be checked before /npc GET or POST)
            local npcName = path:match('^/npc/(.+)$')
            if npcName and method=="GET" then
                status,payload = "HTTP/1.1 200 OK\r\n", self:buildNPCSheet(npcName)
            elseif path == "/snapshot" and method == "GET" then
                status,payload = "HTTP/1.1 200 OK\r\n", self:buildSnapshot()
            elseif path == "/act" and method == "POST" then
                local ok,parsed=pcall(function() return JSON:decode(body) end)
                if not ok or not parsed then status,payload = "HTTP/1.1 400 Bad Request\r\n", to_json({status="error",message="Invalid JSON"})
                else status,payload = "HTTP/1.1 200 OK\r\n", self:handleAction(parsed.npc,parsed.action,parsed.params) end
            elseif path == "/npc" and method == "POST" then
                local ok,parsed=pcall(function() return JSON:decode(body) end)
                if not ok or not parsed then status,payload = "HTTP/1.1 400 Bad Request\r\n", to_json({status="error",message="Invalid JSON"})
                else status,payload = "HTTP/1.1 200 OK\r\n", self:spawnNPC(parsed.name,parsed.skin,parsed.x or 0,parsed.y or 0,parsed.z or 0,parsed.personality,parsed.traits) end
            elseif path == "/npc" and method == "GET" then
                status,payload = "HTTP/1.1 200 OK\r\n", to_json({npcs=self.spawned_npcs})
            elseif path == "/zone" and method == "GET" then
                local player=getPlayer()
                local sq=player and getCell() and getCell():getGridSquare(player:getX(),player:getY(),player:getZ())
                local zone,room="unknown",nil
                if sq then room=sq:getRoom(); zone=safe(room and room:getName(),"outdoors") end
                local zd={}; if room then zd={name=safe(room:getName()),x=room:getX(),y=room:getY(),w=room:getW(),h=room:getH(),z=room:getZ()} end
                status,payload = "HTTP/1.1 200 OK\r\n", to_json({zone=zone,data=zd})
            else
                status,payload = "HTTP/1.1 404 Not Found\r\n", to_json({status="error",message="Not found: "..path})
            end
            out:write(status)
            out:write("Content-Type: application/json\r\n")
            out:write(cors)
            out:write("Connection: close\r\n")
            out:write("\r\n")
            out:write(payload)
            out:flush()
        end
    end
    conn:close()
end

-- ─── Server lifecycle ──────────────────────────────────────────────
function PZBridge:startServer()
    if self.running then return end
    self.running=true
    print("[PZBridge] Starting on port "..tostring(self.port).." ...")
    luajava.createThread(function()
        local ok,sv=pcall(function() return ServerSocket:new(self.port) end)
        if not ok or not sv then print("[PZBridge] Port "..tostring(self.port).." in use?"); self.running=false; return end
        self.server=sv; print("[PZBridge] http://127.0.0.1:"..tostring(self.port).."/")
        while self.running do
            local ok2,cn=pcall(function() return sv:accept() end)
            if ok2 and cn then self:handleConnection(cn) end
        end
        sv:close(); print("[PZBridge] Stopped")
    end)
end
function PZBridge:stopServer()
    self.running=false; if self.server then self.server:close(); self.server=nil end
end

-- ─── Event hooks ───────────────────────────────────────────────────
local function OnStart() if isServer() or not isClient() then PZBridge:startServer() end end
local function OnGame() if not isServer() then PZBridge:startServer() end end
local function OnTick()
    for _,nd in pairs(PZBridge.spawned_npcs) do
        if nd.npc_state=="following" and nd.follow_target then
            local tgt=getPlayer()
            if tgt and nd.survivor and nd.survivor:getPlayer then
                local npc=nd.survivor:getPlayer()
                if npc and npc:getX and tgt:getX then
                    local dx=tgt:getX()-npc:getX(); local dy=tgt:getY()-npc:getY()
                    if math.abs(dx)>2 or math.abs(dy)>2 then
                        if npc:getPathFindBehavior then npc:getPathFindBehavior():pathTo(tgt:getX(),tgt:getY(),tgt:getZ()) end
                    end
                end
            end
        end
    end
end
Events.OnServerStarted.Add(OnStart)
Events.OnGameStart.Add(OnGame)
Events.OnGameTimeUpdate.Add(OnTick)
print("[PZBridge] v"..PZBridge.version.." loaded")
return PZBridge