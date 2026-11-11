if DisasterZoneBoot and DisasterZoneBoot.Run("Core/RaidLearn.lua", ...) then return end -- DisasterZone: Core/RaidLearn.lua
-- Learns the raids the game shows, so adding a new one to Data/ForeverRaids.lua is a paste (WoW Forever).
--
-- Forever's client has no raid list to read (measured 2026-11-08: the Encounter Journal is empty, EJ_GetNumTiers() 0;
-- the group finder lists only activities already released). And the planner's raid list must be the same for the
-- whole guild (the sync refuses unknown keys), so nothing learned here changes it by itself. Instead this records:
--   * each raid instance someone zones into: name, instance id, size (GetInstanceInfo)
--   * the bosses pulled there: encounter id and name (ENCOUNTER_START)
--   * the group finder's raid-size PvE activities (C_LFGList: name, size, level, map id)
-- and `/dz raiddata` prints them as Data/ForeverRaids.lua entries, marking the ones the file does not have yet.
-- Saved in db.raidLearn (account-wide, a few hundred bytes).
local addonName, ns = ...

local RL = ns:NewModule("RaidLearn")

local pairs, ipairs, type, tonumber, tostring = pairs, ipairs, type, tonumber, tostring
local tsort, tconcat = table.sort, table.concat
local strformat = string.format

local MAX_BOSSES = 30            -- per raid kept (a raid has at most ~13)

local function Store()
    local db = ns.db
    if not db then return nil end
    if type(db.raidLearn) ~= "table" then db.raidLearn = { raids = {}, lfg = {} } end
    local s = db.raidLearn
    s.raids = type(s.raids) == "table" and s.raids or {}
    s.lfg = type(s.lfg) == "table" and s.lfg or {}
    return s
end

-- The planner's known raids by instance id and by name (Data/ForeverRaids.lua, or the TBC list).
local function Known()
    local byId, byName = {}, {}
    local RP = ns.RaidPlan
    for _, inst in ipairs(RP and RP:GetInstances() or {}) do
        if inst.instID then byId[inst.instID] = inst end
        if inst.name then byName[inst.name] = inst end
    end
    return byId, byName
end

local current                    -- the raid instance I am in: its db record

local function SeeInstance()
    current = nil
    local inInstance, kind = IsInInstance()
    if not inInstance or kind ~= "raid" then return end
    local name, _, difficulty, _, maxPlayers, _, _, instanceID = GetInstanceInfo()
    instanceID = tonumber(instanceID)
    if type(name) ~= "string" or name == "" or not instanceID then return end
    local s = Store()
    if not s then return end
    local r = s.raids[instanceID]
    if type(r) ~= "table" then r = { bosses = {} }; s.raids[instanceID] = r end
    r.name, r.size, r.difficulty, r.seen = name, tonumber(maxPlayers), tonumber(difficulty), GetServerTime()
    r.bosses = type(r.bosses) == "table" and r.bosses or {}
    current = r
end

local function SeeEncounter(_, encounterID, encounterName)
    if not current then SeeInstance() end
    local r = current
    encounterID = tonumber(encounterID)
    if not r or not encounterID or type(encounterName) ~= "string" then return end
    for _, b in ipairs(r.bosses) do
        if b.id == encounterID then return end
    end
    if #r.bosses >= MAX_BOSSES then return end
    r.bosses[#r.bosses + 1] = { id = encounterID, name = encounterName }
end

-- The group finder's raid-size PvE activities (an unreleased raid is not listed yet).
local function SeeGroupFinder()
    local L = C_LFGList
    if not (L and L.GetAvailableActivities and L.GetActivityInfoTable) then return end
    local s = Store()
    if not s then return end
    local ok, ids = pcall(L.GetAvailableActivities)
    if not ok or type(ids) ~= "table" then return end
    for _, id in ipairs(ids) do
        local a = L.GetActivityInfoTable(id)
        if type(a) == "table" and (tonumber(a.maxNumPlayers) or 0) > 5 and not a.isPvpActivity and not a.isRatedPvpActivity then
            local cat = L.GetLfgCategoryInfo and L.GetLfgCategoryInfo(a.categoryID)
            s.lfg[id] = { name = a.fullName, size = a.maxNumPlayers, level = a.minLevel, map = a.mapID,
                cat = type(cat) == "table" and cat.name or nil }
        end
    end
end

-- Lines for the chat window (and the tests): one Data/ForeverRaids.lua entry per learned raid, then the group finder.
function RL:Report()
    local s = Store()
    local out = {}
    if not s then return out end
    local byId, byName = Known()
    local ids = {}
    for id in pairs(s.raids) do ids[#ids + 1] = id end
    tsort(ids)
    for _, id in ipairs(ids) do
        local r = s.raids[id]
        local known = byId[id] or byName[r.name]
        local bosses = {}
        for _, b in ipairs(r.bosses or {}) do bosses[#bosses + 1] = strformat("%d %s", b.id, b.name) end
        local mark = "NEW"
        if known then mark = known.instID and "-- (in the list)" or "-- (in the list: set its instanceID)" end
        out[#out + 1] = strformat('%s { key = "?", name = %q, short = "?", size = %s, level = 60, instanceID = %d, bosses = %d },',
            mark, r.name or "?", tostring(r.size or "?"), id, #bosses)
        if #bosses > 0 then out[#out + 1] = "    -- bosses pulled: " .. tconcat(bosses, ", ") end
    end
    local lfg = {}
    for id, a in pairs(s.lfg) do
        -- (a 10-player dungeon like Upper Blackrock Spire is listed too: flag only the group finder's raid category,
        -- or every activity when the client gives no category)
        local raid = a.cat == nil or tostring(a.cat):lower():find("raid", 1, true) ~= nil
        local flag = (raid and not byName[a.name]) and "  (not in the list)" or ""
        lfg[#lfg + 1] = strformat("    group finder %d: %s [%s], %s players, level %s, map %s%s", id, tostring(a.name),
            tostring(a.cat or "?"), tostring(a.size), tostring(a.level), tostring(a.map), flag)
    end
    tsort(lfg)
    for _, l in ipairs(lfg) do out[#out + 1] = l end
    if #out == 0 then out[1] = "No raid seen yet: zone into a raid (or open the group finder) and try again." end
    return out
end

function RL:OnInit()
    ns:RegisterEvent("PLAYER_ENTERING_WORLD", SeeInstance)
    ns:RegisterEvent("ZONE_CHANGED_NEW_AREA", SeeInstance)
    ns:RegisterEvent("ENCOUNTER_START", SeeEncounter)
    ns:RegisterSlash("raiddata", function()
        SeeInstance()
        SeeGroupFinder()
        ns:Print("Raids the game has shown (paste NEW ones into Data/ForeverRaids.lua):")
        for _, line in ipairs(RL:Report()) do ns:Print("%s", line) end
    end, "raids and bosses seen in game, as Data/ForeverRaids.lua entries")
end

function RL:OnLogin()
    SeeGroupFinder()
end
