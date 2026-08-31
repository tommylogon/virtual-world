-- PZ Bridge: Lua mod with embedded HTTP server (listens on localhost port 8742)
-- Runs on dedicated server or single-player; exposes /snapshot and /act endpoints.
-- The server uses Java's ServerSocket via luajava (available in any PZ mod).
local ServerSocket = luajava.bindClass('java.net.ServerSocket')
local Socket = luajava.bindClass('java.net.Socket')
local PrintWriter = luajava.bindClass('java.io.PrintWriter')
local BufferedReader = luajava.bindClass('java.io.BufferedReader')
local String = luajava.bindClass('java.lang.String')

local bridgeMod = {}
bridgeMod.name = 'PZBridge'
bridgeMod.author = 'viwo-adapter'
bridgeMod.version = '0.1.0'
bridgeMod.port = 8742
bridgeMod.running = false

-- Start the HTTP listener thread
function bridgeMod:startServer()
    if self.running then return end
    self.running = true
    local thread = luajava.startThread(function()
        local server = ServerSocket:new(self.port)
        print(string.format('[PZBridge] HTTP server listening on :%d', self.port))
        while self.running do
            local conn = server:accept()
            local in = BufferedReader:new(conn:getInputStream())
            local out = PrintWriter:new(conn:getOutputStream(), true)
            -- Read first line (request line)
            local line = in:readLine()
            if not line then conn:close(); continue end
            -- Parse method + path: e.g. GET /snapshot HTTP/1.1
            local method, path = line:match('^([A-Z]+)%s+(%S+)')
            if not method then
                out:println('HTTP/1.1 400 Bad Request')
                out:println('Content-Type: text/plain')
                out:println('Connection: close')
                out:println()
                out:println('Unknown request')
                out:flush()
                conn:close()
                goto continue
            end
            if path == '/snapshot' then
                -- Return JSON: {"zone":"...","players":[{...}],"items":[...],"zombies":[...]}
                local snap = self:buildSnapshot()
                out:println('HTTP/1.1 200 OK')
                out:println('Content-Type: application/json')
                out:println('Connection: close')
                out:println()
                out:println(snap)
                out:flush()
            elseif path == '/act' then
                -- Read body: {"npc":"...","action":"move_to","params":{"x":10,"y":20}}
                local body = ''
                while true do
                    local l = in:readLine()
                    if not l or l == '' then break end
                    body = body .. l
                end
                local ok, parsed = pcall(function() return json.decode(body) end)
                if ok and parsed then
                    local resp = self:handleAction(parsed.npc, parsed.action, parsed.params or {})
                    out:println('HTTP/1.1 200 OK')
                    out:println('Content-Type: application/json')
                    out:println('Connection: close')
                    out:println()
                    out:println(resp)
                    out:flush()
                else
                    out:println('HTTP/1.1 400 Bad Request')
                    out:println('Content-Type: text/plain')
                    out:println('Connection: close')
                    out:println()
                    out:println('Invalid JSON body')
                    out:flush()
                end
            else
                out:println('HTTP/1.1 404 Not Found')
                out:println('Content-Type: text/plain')
                out:println('Connection: close')
                out:println()
                out:println('Not found: ' .. path)
                out:flush()
            end
            conn:close()
            ::continue::
        end
        server:close()
    end)
    return thread
end

-- Build a snapshot of the current world state from PZ's Lua globals
-- In a real mod you'd read from IsoWorld / IsoPlayer / IsoObject APIs
function bridgeMod:buildSnapshot()
    local player = getPlayer():getName()
    local sq = getCell():getGridSquare(getPlayer():getX(), getPlayer():getY(), getPlayer():getZ())
    local zone = sq:getDescription()
    local items = {}
    local zombies = {}
    -- Very rough: list items on this square
    for i, item in ipairs(sq:getObjects()) do
        table.insert(items, {name=item:getType(), x=sq:getX(), y=sq:getY(), z=sq:getZ()})
    end
    -- List zombies (this may not exist in all PZ versions)
    local zombieCount = 0
    if sq:getZombies then
        for z in sq:getZombies() do
            zombieCount = zombieCount + 1
        end
    end
    return string.format('{"zone":"%s","player":"%s","x":%d,"y":%d,"z":%d,"items":%s,"zombieCount":%d}', 
        zone or 'unknown', player, sq:getX(), sq:getY(), sq:getZ(), 
        table.concat(items, ','), zombieCount)
end

-- Dispatch action: move_to / say / attack / loot
-- In a real mod these call PZ API: move IsoPlayer, say, attack, takeItem
function bridgeMod:handleAction(npc, action, params)
    if action == 'move_to' then
        -- params = {x, y, z}
        local x = params.x or 0
        local y = params.y or 0
        local z = params.z or getPlayer():getZ()
        -- Move the named NPC (or the player if npc==player name)
        -- Placeholder: log intent
        print(string.format('[PZBridge] NPC %s wants to move to x=%d y=%d z=%d', tostring(npc), x, y, z))
        return string.format('{"status":"accepted","action":"move_to","target_x":%d,"target_y":%d}', x, y)
    elseif action == 'say' then
        local text = params.text or ''
        print(string.format('[PZBridge] NPC %s says: %s', tostring(npc), text))
        return string.format('{"status":"ok","action":"say","text":"%s"}', text:gsub('"', '\\"' ))
    elseif action == 'attack' then
        -- params = {target_type, target_name}
        local t = params.target_type or 'zombie'
        local n = params.target_name or ''
        print(string.format('[PZBridge] NPC %s attacking %s %s', tostring(npc), t, tostring(n)))
        return string.format('{"status":"accepted","action":"attack","target_type":"%s","target_name":"%s"}', t, n)
    elseif action == 'loot' then
        local item = params.item or ''
        print(string.format('[PZBridge] NPC %s looting %s', tostring(npc), item))
        return string.format('{"status":"accepted","action":"loot","item":"%s"}', item:gsub('"', '\\"' ))
    else
        return string.format('{"status":"error","message":"unknown action:%s"}', action)
    end
end

-- Called when the mod is loaded
function bridgeMod:onLoad()
    self:startServer()
    print(string.format('[PZBridge] %s v%s loaded', self.name, self.version))
end

return bridgeMod