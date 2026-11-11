-- Offline test of DZProbe under plain Lua 5.1 with a minimal fake Forever client.
-- Run from the repo root: lua5.1 dev/probe/test_probe.lua
-- It checks the probe boots, runs its static pass, samples in normal and restricted states, never stores a
-- secret value, survives missing APIs, and leaves DZProbeDB in the shape read_probe.py expects.

local dir = arg[0]:match("^(.*)/") or "."
local failures, passes = 0, 0
local realprint = print
local function check(cond, msg)
    local print = realprint
    if cond then passes = passes + 1 else failures = failures + 1; print("FAIL: " .. msg) end
end

------------------------------------------------------------------ fake client
local clock = 1000
local timers = {}
local frames = {}
local sent = {}
local restricted = {}          -- AddOnRestrictionType value -> true
local inCombat = false
local secretMode = false

local SECRET_MT = {
    __add = function() error("attempt to perform arithmetic on a secret value") end,
    __concat = function() error("attempt to concatenate a secret value") end,
    __eq = function() error("attempt to compare a secret value") end,
}
local secrets = setmetatable({}, { __mode = "k" })
local function secret()
    local s = setmetatable({}, SECRET_MT); secrets[s] = true; return s
end

_G.issecretvalue = function(v) return secrets[v] == true end
_G.GetTimePreciseSec = function() return clock end
_G.GetTime = GetTimePreciseSec
_G.time = os.time
_G.date = os.date
_G.GetBuildInfo = function() return "1.60.1", "70862", "Nov 1 2026", 16001 end
_G.WOW_PROJECT_ID = 99
_G.WOW_PROJECT_MAINLINE = 1
_G.GetExpansionLevel = function() return 0 end
_G.GetMaxLevelForPlayerExpansion = function() return 60 end
_G.UnitClass = function() return "Warrior", "WARRIOR" end
_G.UnitRace = function() return "Human", "Human" end
_G.UnitLevel = function() return 23 end
_G.UnitFactionGroup = function() return "Alliance" end
_G.GetRealmName = function() return "Testrealm" end
_G.GetLocale = function() return "enUS" end
_G.UnitName = function(u) if u == "player" then return "Jimtank" end return secretMode and secret() or "Boar" end
_G.UnitFullName = function() return "Jimtank", "Testrealm" end
_G.UnitHealth = function(u) return secretMode and u ~= "player" and secret() or 100 end
_G.UnitHealthMax = function() return secretMode and secret() or 100 end
_G.UnitPower = function() return 10 end
_G.UnitGUID = function() return secretMode and secret() or "Creature-0-1" end
_G.UnitCastingInfo = function() return nil end
_G.UnitThreatSituation = function() return secretMode and secret() or 0 end
_G.IsInInstance = function() return restricted[1] and true or false, restricted[1] and "raid" or "none" end
_G.InCombatLockdown = function() return inCombat end
_G.IsInGuild = function() return true end
_G.IsInGroup = function() return false end
_G.IsInRaid = function() return false end
_G.GetNumGroupMembers = function() return 0 end
_G.GetGuildInfo = function() return "Casual Disaster", "Guild Master", 0, "Testrealm" end
_G.IsGuildLeader = function() return true end
_G.GuildControlGetNumRanks = function() return 2 end
_G.GuildControlGetRankName = function(i) return ({ "Guild Master", "Officer" })[i] end
_G.GetNumGuildMembers = function() return 2, 1, 1 end
_G.GetGuildRosterInfo = function(i)
    if i == 1 then return "Jimtank-Testrealm", "Guild Master", 0, 23, "Warrior", "Elwynn", "", "main tank", true, 0, "WARRIOR" end
    return "Other-Testrealm", "Officer", 1, 20, "Mage", "Goldshire", "", "", false, 0, "MAGE"
end
_G.GetInventoryItemID = function() return 1234, 0 end
_G.GetCVar = function() return "1" end
_G.RANDOM_ROLL_RESULT = "%s rolls %d (%d-%d)"
_G.RandomRoll = function(lo, hi)
    for _, fr in ipairs(frames) do
        if fr.events.CHAT_MSG_SYSTEM then fr.script(fr, "CHAT_MSG_SYSTEM", "Jimtank rolls 42 (1-100)") end
    end
end
_G.GetRealZoneText = function() return "Elwynn Forest" end
_G.SlashCmdList = {}
_G.print = function() end

_G.Enum = {
    AddOnRestrictionType = { Combat = 0, Encounter = 1, ChallengeMode = 2, PvPMatch = 3, Map = 4, Chat = 5 },
    AddOnRestrictionState = { Inactive = 0, Activating = 1, Active = 2 },
    SendAddonMessageResult = { Success = 0, AddOnMessageLockdown = 11 },
    RegisterAddonMessagePrefixResult = { Success = 0 },
    LootMethod = { Freeforall = 0, Roundrobin = 1, Masterlooter = 2, Group = 3, Needbeforegreed = 4, Personal = 5 },
    LootMethodStyles = { Mainline = 0, Vanilla = 1 },
    TooltipDataType = { Item = 0 },
    EditModeSystem = { ActionBar = 0 },
}
_G.C_RestrictedActions = { IsAddOnRestrictionActive = function(t) return restricted[t] == true end }
_G.C_InstanceEncounter = { IsEncounterInProgress = function() return restricted[1] == true end }
_G.C_EventUtils = { IsEventValid = function(ev) return ev ~= "COMBAT_LOG_EVENT_UNFILTERED" end }
_G.C_ChatInfo = {
    RegisterAddonMessagePrefix = function() return 0 end,
    IsAddonMessagePrefixRegistered = function() return true end,
    InChatMessagingLockdown = function() return restricted[5] == true end,
    SendAddonMessage = function(prefix, msg, ch, target)
        if restricted[5] or restricted[1] then return 11 end
        sent[#sent + 1] = { prefix, msg, ch, target }
        return 0
    end,
}
_G.C_PartyInfo = { GetLootMethod = function() return 0 end, GetLootMethodStyle = function() return 1 end,
    SetLootMethod = function() end }
_G.C_GuildInfo = { IsGuildOfficer = function() return true end, CanEditOfficerNote = function() return true end,
    GuildRoster = function() end }
_G.C_AddOns = { GetAddOnMetadata = function(_, f) return f == "X-Probe" and "metadata-ok" or "16001" end }
_G.C_Item = { GetItemInfo = function(id) if id == 6948 then return "Hearthstone" end end,
    RequestLoadItemDataByID = function() end }
_G.C_Container = { GetContainerNumSlots = function() return 16 end }
_G.C_UnitAuras = { GetAuraDataByIndex = function() return secretMode and { spellId = secret() } or { spellId = 6673 } end }
_G.C_Timer = {
    After = function(d, fn) timers[#timers + 1] = { at = clock + d, fn = fn } end,
    NewTicker = function(d, fn) timers[#timers + 1] = { at = clock + d, fn = fn, every = d } end,
}
_G.GameTooltip = { HasScript = function() return false end }
_G.TooltipDataProcessor = { AddTooltipPostCall = function(_, fn) _G.__ttHook = fn end }
_G.CreateFrame = function()
    local fr = { events = {} }
    function fr:RegisterEvent(ev)
        if ev == "COMBAT_LOG_EVENT_UNFILTERED" then _G.__clogAttempted = true end
        self.events[ev] = true
    end
    function fr:SetScript(_, fn) self.script = fn end
    frames[#frames + 1] = fr
    return fr
end

local function fire(ev, ...)
    for _, fr in ipairs(frames) do if fr.events[ev] and fr.script then fr.script(fr, ev, ...) end end
end
local function advance(sec)
    local target = clock + sec
    while true do
        table.sort(timers, function(a, b) return a.at < b.at end)
        local t = timers[1]
        if not t or t.at > target then break end
        table.remove(timers, 1)
        clock = t.at
        t.fn()
        if t.every then timers[#timers + 1] = { at = clock + t.every, fn = t.fn, every = t.every } end
    end
    clock = target
end

------------------------------------------------------------------ load the addon
local P = {}
for _, file in ipairs({ "ApiList.lua", "Probe.lua" }) do
    local chunk = assert(loadfile(dir .. "/DZProbe/" .. file))
    chunk("DZProbe", P)
end

fire("ADDON_LOADED", "DZProbe")
fire("PLAYER_LOGIN")
advance(6)                                   -- static run at +5 s
-- echo the burst back as CHAT_MSG_ADDON, as the server would
for _, m in ipairs(sent) do fire("CHAT_MSG_ADDON", m[1], m[2], m[3], "Jimtank-Testrealm") end

local DB = DZProbeDB
check(DB and DB.static, "static run stored")
local s = DB.static
check(s.build[4] == 16001 and s.build.n == 4, "build info packed with 4 returns")
check(s.lua.loadstringRuns == true, "loadstring detected as working")
check(s.toc.xField == "metadata-ok", "TOC X- field read")
check(s.toc.svAtFileLoad == false, "first run: SavedVariables absent at file load")
check(not _G.__clogAttempted and s.combatLog.registerForbidden == true, "never registers the combat log (forbidden popup on Forever)")
check(s.loot.current.method == "Freeforall" and s.loot.style == "Vanilla", "loot method + style named")
check(s.loot.methods.Masterlooter == 2, "loot method enum recorded")
check(s.guild.isLeader == true and s.guild.rankIndex == 0, "guild leader + rank index")
check(s.guild.selfRow and s.guild.selfRow.returns == 11, "own roster row found with its return count")
check(s.names and s.names.playerFullName == "Jimtank-Testrealm" and s.names.GetRealmName == "Testrealm", "own name forms recorded")
check(s.guild.nameShapes and next(s.guild.nameShapes) and s.guild.selfRow.matchedBy, "roster name shapes only, self row match method")
check(s.guild.selfRow.officerNoteLen == 9 and s.guild.selfRow.officerNote == nil, "officer note length only, not text")
check(s.burst.sent == 40 and s.burst.results.Success == 40, "burst: 40 accepted")
check(DB.counters.burstRecv == 40, "burst: 40 echoed back")
check(s.roll and s.roll.parsedWithRANDOM_ROLL_RESULT == true, "roll line parsed with RANDOM_ROLL_RESULT")
check(s.items.invItemIdReturns == 2, "GetInventoryItemID return count")
check(s.api.present.C > 0 and type(s.api.missing.C) == "table", "API surface counted")
check(s.tooltip.TooltipDataProcessor == true, "TooltipDataProcessor detected")

-- restricted encounter state with secret values
restricted[0], restricted[1] = true, true
inCombat, secretMode = true, true
fire("ADDON_RESTRICTION_STATE_CHANGED", 1, 2)
fire("ENCOUNTER_START", secret(), secret(), 3, 20)
advance(3)
local key
for k in pairs(DB.matrix) do if k:find("raid|combat|encounter", 1, true) then key = k end end
check(key ~= nil, "restricted context sampled: " .. tostring(key))
local m = key and DB.matrix[key]
check(m and m.sends.GUILD and (m.sends.GUILD.AddOnMessageLockdown or 0) >= 1, "lockdown send result counted")
local hp = m and m.values["UnitHealth(target)"]
check(hp and (hp.secret or 0) >= 1 and hp.math == false, "secret health recorded as secret, math blocked")

-- passive ticker keeps sampling while busy
advance(11)
check(m and m.samples >= 3, "busy ticker samples every 5 s (got " .. tostring(m and m.samples) .. ")")

-- nothing secret was stored anywhere
local function scan(t, path, seen)
    seen = seen or {}
    if seen[t] then return end
    seen[t] = true
    for k, v in pairs(t) do
        if secrets[v] or secrets[k] then check(false, "secret stored at " .. path .. "." .. tostring(k)) end
        if type(v) == "table" then scan(v, path .. "." .. tostring(k), seen) end
    end
end
scan(DB, "DZProbeDB")
local enc
for _, e in ipairs(DB.log) do if e.k == "encounter-start" then enc = e end end
check(enc and enc.name.secret == true and enc.name.v == nil and enc.size.v == 20, "encounter log keeps flags, not secrets")

-- round 2: a raid group with secret roster names, master loot and a need/greed roll
local keepG = { IsInGroup = IsInGroup, IsInRaid = IsInRaid, GetNumGroupMembers = GetNumGroupMembers }
_G.IsInGroup, _G.IsInRaid, _G.GetNumGroupMembers = function() return true end, function() return true end, function() return 3 end
_G.GetRaidRosterInfo = function(i) return secret(), 0, 1, 17, "Warrior", "WARRIOR", "The Deadmines", true, false, nil, i == 1 end
_G.UnitIsGroupLeader = function(u) return u == "player" end
_G.UnitIsConnected = function() return true end
_G.UnitClass = _G.UnitClass or function() return "Warrior", "WARRIOR" end
_G.GetNumLootItems = function() return 1 end
_G.GetMasterLootCandidate = function(slot, i) if i <= 3 then return secret() end end
_G.GiveMasterLoot = function() end
_G.GetLootRollItemInfo = function() return "tex", secret(), 1, 3, true, true end
_G.GetLootRollItemLink = function() return "|Hitem:915|h[Red Silk Bandana]|h" end
fire("GROUP_ROSTER_UPDATE"); fire("GROUP_ROSTER_UPDATE")
advance(3)
fire("LOOT_OPENED")
fire("START_LOOT_ROLL", 7)
local rm
for k, v in pairs(DB.matrix) do if v.roster then rm = v.roster end end
check(rm and rm.rows >= 3 and rm.fields.name.secret >= 3 and rm.fields.isML.boolean >= 3, "raid roster fields counted by kind")
check(rm and rm.units.UnitName and (rm.units.UnitName.secret or 0) >= 1, "raidN unit names counted as secret")
local lo, lr
for _, e in ipairs(DB.log) do if e.k == "loot-opened" then lo = e elseif e.k == "loot-roll" then lr = e end end
check(lo and lo.candidatesSlot1 and lo.candidatesSlot1.secret == 3 and lo.GiveMasterLoot == true, "master loot candidates counted")
check(lr and lr.name.secret == true and lr.link.v ~= nil, "roll item: secret name flagged, link kept")
for k, v in pairs(keepG) do _G[k] = v end
scan(DB, "DZProbeDB")

-- slash command runs
SlashCmdList.DZPROBE("")
SlashCmdList.DZPROBE("sample")
check((DB.counters.handlerErrors or 0) == 0, "no handler errors (" .. tostring(DB.counters.handlerErrors) .. ")")

-- a client missing functions: sections fail alone, the rest still runs, samples keep working
local keep = { GetGuildInfo = GetGuildInfo, IsInRaid = IsInRaid, GetInventoryItemID = GetInventoryItemID }
_G.GetGuildInfo, _G.IsInRaid, _G.GetInventoryItemID = nil, nil, nil
SlashCmdList.DZPROBE("run")
local s2 = DZProbeDB.static
check(s2.errors.guild and s2.errors.items, "missing APIs recorded per section")
check(s2.lua and s2.lua.loadstringRuns and s2.burst and s2.loot, "other sections still ran")
local before = DZProbeDB.counters.sampleErrors or 0
SlashCmdList.DZPROBE("sample")
check((DZProbeDB.counters.sampleErrors or 0) == before + 1, "sample error caught and counted")
for k, v in pairs(keep) do _G[k] = v end
SlashCmdList.DZPROBE("run")
check(next(DZProbeDB.static.errors) == nil, "full client: no section errors")

-- write DZProbeDB the way the client does, for read_probe.py (optional 1st argument = output file)
if arg[1] then
    local function ser(v, ind)
        local t = type(v)
        if t == "string" then return string.format("%q", v) end
        if t == "number" or t == "boolean" then return tostring(v) end
        if t ~= "table" then return "nil" end
        local out = { "{\n" }
        for k, x in pairs(v) do
            local key = type(k) == "number" and ("[" .. k .. "]") or ("[" .. string.format("%q", tostring(k)) .. "]")
            out[#out + 1] = ind .. "\t" .. key .. " = " .. ser(x, ind .. "\t") .. ",\n"
        end
        out[#out + 1] = ind .. "}"
        return table.concat(out)
    end
    local fh = assert(io.open(arg[1], "w"))
    fh:write("\nDZProbeDB = " .. ser(DZProbeDB, "") .. "\n")
    fh:close()
end

realprint(("test_probe: %d passed, %d failed"):format(passes, failures))
os.exit(failures == 0 and 0 or 1)
