-- Скрипт вставляется в зону Global в Tabletop Simulator

local ZONE_GUID = "fc6f55" -- GUID зоны для броска кубика
local diceResults = {}
local zone = nil
local errorShown = false
local sessionActive = false

function onLoad()
    zone = getObjectFromGUID(ZONE_GUID)
    if zone and zone.type == "ScriptingTrigger" then
        print("Zone loaded successfully: " .. ZONE_GUID)
    else
        print("Error: Could not find or invalid zone with GUID " .. ZONE_GUID)
        zone = nil
    end
end

function onObjectRandomize(obj, player_color)
    if not zone then return end
    if isDiceInZone(obj, zone) then
        local player = Player[player_color].steam_name
        local function checkDiceStopped()
            if obj.getVelocity().x == 0 and obj.getVelocity().y == 0 and obj.getVelocity().z == 0 then
                local result = obj.getValue()
                diceResults[obj.getGUID()] = result

                local diceInZone = getDiceInZone(zone)
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
                    sendResults(player, diceInZone)
                end
            else
                Wait.frames(checkDiceStopped, 10)
            end
        end
        Wait.frames(checkDiceStopped, 30)
    end
end

function isDiceInZone(dice, zone)
    local objects = zone.getObjects()
    for _, obj in ipairs(objects) do
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
    if not sessionActive then
        print("Error: No active session! Please start a session with 'start'.")
        diceResults = {}
        errorShown = false
        return
    end
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
    WebRequest.post(
        "https://relieved-firm-titmouse.ngrok-free.app/roll",
        jsonData,
        function(response)
            if response.is_error then
                print("Error: " .. response.error)
            else
                print(player .. " rolled a total of " .. total)
            end
        end,
        { ["Content-Type"] = "application/json" }
    )
    diceResults = {}
    errorShown = false
end

function onChat(message, player)
    if message:lower() == "start" and player.host then
        print("Starting new session...")
        WebRequest.post(
            "https://relieved-firm-titmouse.ngrok-free.app/start_session",
            "{}",
            function(response)
                if response.is_error then
                    print("Error starting session: " .. response.error)
                else
                    sessionActive = true
                    print("New session started!")
                end
            end,
            { ["Content-Type"] = "application/json" }
        )
    end
end