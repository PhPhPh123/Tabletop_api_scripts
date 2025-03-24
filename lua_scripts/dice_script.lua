-- Скрипт вставляется в зону Global в Tabletop Simulator


local ZONE_GUID = "e84e08" -- GUID твоей зоны (замени на актуальный GUID)
local diceResults = {}
local zone = nil
local errorShown = false
local sessionActive = false

function onLoad()
    print("onLoad: Starting initialization...")
    local attempts = 0
    local maxAttempts = 10
    local function tryLoadZone()
        attempts = attempts + 1
        print("onLoad: Attempt " .. attempts .. " to load zone with GUID: " .. ZONE_GUID)
        zone = getObjectFromGUID(ZONE_GUID)
        if zone then
            print("onLoad: Zone found, type: " .. zone.type)
            if zone.type == "Scripting" then -- Принимаем зону типа Scripting
                print("Zone loaded successfully: " .. ZONE_GUID)
                -- Проверяем, работает ли getObjects()
                local objects = zone.getObjects()
                print("onLoad: Objects in zone: " .. #objects)
                for _, obj in ipairs(objects) do
                    print("onLoad: Object in zone, type: " .. obj.type .. ", GUID: " .. obj.getGUID())
                end
            else
                print("Error: Zone is not a Scripting zone, type: " .. zone.type)
                zone = nil
            end
        else
            if attempts < maxAttempts then
                Wait.time(tryLoadZone, 1) -- Пробуем снова через 1 секунду
            else
                print("Error: Could not find zone with GUID " .. ZONE_GUID .. " after " .. maxAttempts .. " attempts")
                zone = nil
            end
        end
    end
    tryLoadZone()
end

function onObjectRandomize(obj, player_color)
    print("onObjectRandomize: Object randomized, GUID: " .. obj.getGUID())
    if not zone then
        print("onObjectRandomize: Zone is nil, skipping...")
        return
    end
    if isDiceInZone(obj, zone) then
        print("onObjectRandomize: Dice is in zone, player: " .. Player[player_color].steam_name)
        local player = Player[player_color].steam_name
        local function checkDiceStopped()
            if obj.getVelocity().x == 0 and obj.getVelocity().y == 0 and obj.getVelocity().z == 0 then
                local result = obj.getValue()
                diceResults[obj.getGUID()] = result
                print("onObjectRandomize: Dice stopped, result: " .. result)

                local diceInZone = getDiceInZone(zone)
                print("onObjectRandomize: Dice in zone: " .. #diceInZone)
                if #diceInZone ~= 3 then
                    if not errorShown then
                        print("Error: There must be exactly 3 dice in the zone! Found: " .. #diceInZone)
                        errorShown = true
                    end
                    diceResults = {}
                    return
                end

                errorShown = false

                if hasAllDiceStopped(diceInZone) then
                    print("onObjectRandomize: All dice stopped, processing results...")
                    if not sessionActive then
                        print("Warning: Dice rolled without an active session! Please use 'start' to begin a session.")
                        diceResults = {}
                        return
                    end
                    sendResults(player, diceInZone)
                end
            else
                Wait.frames(checkDiceStopped, 10)
            end
        end
        Wait.frames(checkDiceStopped, 30)
    else
        print("onObjectRandomize: Dice not in zone, skipping...")
    end
end

function isDiceInZone(dice, zone)
    local objects = zone.getObjects()
    print("isDiceInZone: Checking if dice is in zone, dice GUID: " .. dice.getGUID())
    for _, obj in ipairs(objects) do
        print("isDiceInZone: Found object in zone, type: " .. obj.type .. ", GUID: " .. obj.getGUID())
        if obj == dice and obj.type == "Dice" then
            return true
        end
    end
    return false
end

function getDiceInZone(zone)
    local dice = {}
    for _, obj in ipairs(zone.getObjects()) do
        if obj.type == "Dice" then
            table.insert(dice, obj)
        end
    end
    return dice
end

function hasAllDiceStopped(diceList)
    for _, dice in ipairs(diceList) do
        if not diceResults[dice.getGUID()] then
            return false
        end
    end
    return true
end

function sendResults(player, diceList)
    local total = 0
    local results = {}
    for _, dice in ipairs(diceList) do
        local result = diceResults[dice.getGUID()]
        total = total + result
        table.insert(results, result)
    end
    local rollData = {
        player = player,
        results = results,
        total = total
    }
    local jsonData = JSON.encode(rollData)
    print("sendResults: Sending data: " .. jsonData)
    WebRequest.post(
        "https://relieved-firm-titmouse.ngrok-free.app/roll",
        jsonData,
        function(response)
            if response.is_error then
                print("sendResults: Error: " .. response.error)
            else
                -- Выводим только итоговый результат в чат
                broadcastToAll(player .. " rolled a total of " .. total, {1, 1, 1})
                print("sendResults: Success: Data sent to server")
            end
        end,
        { ["Content-Type"] = "application/json" }
    )
    diceResults = {}
    errorShown = false
end

function onChat(message, player)
    if message:lower() == "start" and player.host then
        print("onChat: Starting new session...")
        WebRequest.post(
            "https://relieved-firm-titmouse.ngrok-free.app/start_session",
            "{}",
            function(response)
                if response.is_error then
                    print("onChat: Error starting session: " .. response.error)
                else
                    sessionActive = true
                    print("onChat: New session started!")
                end
            end,
            { ["Content-Type"] = "application/json" }
        )
    end
end