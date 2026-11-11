-- DZ Probe: records what the WoW Forever client lets an addon do, for the DisasterZoneForever port.
--
-- Two parts:
--   * a one-shot "static" run 5 s after login (and on /dzprobe run): build info, which APIs and events exist,
--     loadstring, SavedVariables timing, guild/roster/loot/tooltip/item facts, an addon-message burst, a /roll.
--   * a passive logger: on every combat, encounter, zone and addon-restriction change it takes a "sample"
--     (can we send addon messages, are unit/aura/cast/threat values secret, is chat locked down) and adds it to
--     a matrix keyed by the context. It never stores a secret value, only whether it was secret.
--
-- Nothing is visible to other players: addon messages go to our own prefix only, the /roll runs only when solo.
-- Read the results with dev/probe/read_probe.py after a /reload or logout.

local ADDON, P = ...
local PREFIX = "DZProbe"
local VERSION = 2 -- round 2 (group/raid): bumping clears round-1 data, which is saved in dev/probe/results/
local MAX_LOG = 1500

local svAtFileLoad = DZProbeDB ~= nil   -- true on a 2nd+ login only if LoadSavedVariablesFirst works

local DB
local now = GetTimePreciseSec or GetTime

------------------------------------------------------------------------------------------------ helpers

local function pack(...) return { n = select("#", ...), ... } end

local function issec(v)
    if type(issecretvalue) ~= "function" then return false end
    local ok, r = pcall(issecretvalue, v)
    return ok and r == true
end

-- Describe a value without keeping it if it is secret.
local function describe(v)
    local d = { secret = issec(v) }
    local okT, t = pcall(type, v)
    d.t = okT and t or "type-error"
    if d.secret then
        d.math = pcall(function() return v + 0 end)
        d.cmp = pcall(function() return v == v end)
        d.concat = pcall(function() return "" .. v end)
    elseif t == "number" or t == "boolean" or (t == "string" and #v <= 120) then
        d.v = v
    elseif t == "string" then
        d.len = #v
    end
    return d
end

local function resolve(path)
    local cur = _G
    for part in string.gmatch(path, "[^%.]+") do
        if type(cur) ~= "table" then return nil end
        local ok, nxt = pcall(function() return cur[part] end)
        if not ok then return nil end
        cur = nxt
    end
    return cur
end

local function log(kind, data)
    local e = data or {}
    e.k = kind
    e.t = time()
    e.ctx = P.ContextKey and P.ContextKey() or nil
    local l = DB.log
    l[#l + 1] = e
    if #l > MAX_LOG then table.remove(l, 1) end
end

local function enumNames(enumTable)
    local out = {}
    if type(enumTable) ~= "table" then return nil end
    for k, v in pairs(enumTable) do out[tostring(k)] = v end
    return out
end

local function enumName(enumTable, value)
    if type(enumTable) == "table" then
        for k, v in pairs(enumTable) do if v == value then return k end end
    end
    return tostring(value)
end

------------------------------------------------------------------------------------------------ context

local RESTRICTIONS = {}   -- name -> enum value, filled at login

local function restrictionList()
    local active = {}
    local cra = C_RestrictedActions
    if cra and cra.IsAddOnRestrictionActive then
        for name, v in pairs(RESTRICTIONS) do
            local ok, on = pcall(cra.IsAddOnRestrictionActive, v)
            if ok and on then active[#active + 1] = name end
        end
    end
    table.sort(active)
    return active
end

function P.ContextKey()
    local okI, inInst, instType = pcall(IsInInstance)
    local combat = (InCombatLockdown and InCombatLockdown()) and "combat" or "calm"
    local enc = "noenc"
    if C_InstanceEncounter and C_InstanceEncounter.IsEncounterInProgress then
        local ok, r = pcall(C_InstanceEncounter.IsEncounterInProgress)
        if ok and r then enc = "encounter" end
    end
    local r = restrictionList()
    return table.concat({ okI and (instType or "none") or "?", combat, enc,
        #r > 0 and table.concat(r, "+") or "unrestricted" }, "|")
end

------------------------------------------------------------------------------------------------ addon messages

local pendingSends = {}   -- token -> sent time

local function sendTest(channel, target, tag)
    local token = tag .. ":" .. string.format("%.3f", now())
    pendingSends[token] = now()
    local send = C_ChatInfo and C_ChatInfo.SendAddonMessage
    if not send then return "no-C_ChatInfo.SendAddonMessage" end
    local ok, res = pcall(send, PREFIX, token, channel, target)
    if not ok then return "error:" .. tostring(res) end
    return enumName(Enum and Enum.SendAddonMessageResult, res)
end

local function playerFullName()
    local name, realm = UnitFullName("player")
    if realm and realm ~= "" then return name .. "-" .. realm end
    return name
end

------------------------------------------------------------------------------------------------ samples (passive)

local UNIT_PROBES = {
    { "UnitHealth(player)", function() return UnitHealth("player") end },
    { "UnitHealth(target)", function() return UnitHealth("target") end },
    { "UnitHealthMax(target)", function() return UnitHealthMax("target") end },
    { "UnitPower(player)", function() return UnitPower("player") end },
    { "UnitName(target)", function() return UnitName("target") end },
    { "UnitGUID(target)", function() return UnitGUID("target") end },
    { "UnitCastingInfo(target)", function() return UnitCastingInfo("target") end },
    { "UnitThreatSituation", function() return UnitThreatSituation("player", "target") end },
    { "AuraData(player,1).spellId", function()
        local a = C_UnitAuras and C_UnitAuras.GetAuraDataByIndex and C_UnitAuras.GetAuraDataByIndex("player", 1)
        return a and a.spellId
    end },
    { "AuraData(target,1).expirationTime", function()
        local a = C_UnitAuras and C_UnitAuras.GetAuraDataByIndex and C_UnitAuras.GetAuraDataByIndex("target", 1, "HARMFUL")
        return a and a.expirationTime
    end },
}

local function takeSampleRaw(reason)
    local key = P.ContextKey()
    local m = DB.matrix[key]
    if not m then
        m = { samples = 0, sends = {}, values = {}, first = time(), reasons = {} }
        DB.matrix[key] = m
    end
    m.samples = m.samples + 1
    m.last = time()
    m.reasons[reason] = (m.reasons[reason] or 0) + 1

    local function count(ch, res)
        m.sends[ch] = m.sends[ch] or {}
        m.sends[ch][res] = (m.sends[ch][res] or 0) + 1
    end
    if IsInGuild() then count("GUILD", sendTest("GUILD", nil, "s")) end
    count("WHISPER-self", sendTest("WHISPER", playerFullName(), "s"))
    if IsInRaid() then count("RAID", sendTest("RAID", nil, "s"))
    elseif IsInGroup() then count("PARTY", sendTest("PARTY", nil, "s")) end

    if C_ChatInfo and C_ChatInfo.InChatMessagingLockdown then
        local ok, r = pcall(C_ChatInfo.InChatMessagingLockdown)
        m.chatLockdown = ok and tostring(r) or "error"
    end

    if IsInGroup() then
        -- which GetRaidRosterInfo fields and raidN/partyN unit values are readable here (counts, never values)
        local RF = { "name", "rank", "subgroup", "level", "class", "fileName", "zone", "online", "isDead", "role",
            "isML", "combatRole" }
        local roster = m.roster or { rows = 0, fields = {}, units = {} }
        m.roster = roster
        local raid = IsInRaid()
        for i = 1, math.min(GetNumGroupMembers() or 0, 40) do
            local r = pack(pcall(GetRaidRosterInfo, i))
            if r[1] then
                roster.rows = roster.rows + 1
                for fi, fname in ipairs(RF) do
                    local v = r[fi + 1]
                    local k = issec(v) and "secret" or type(v)
                    local slot = roster.fields[fname] or {}
                    roster.fields[fname] = slot
                    slot[k] = (slot[k] or 0) + 1
                end
            end
            local unit = raid and ("raid" .. i) or (i == 1 and "player" or ("party" .. (i - 1)))
            for _, probe in ipairs({ { "UnitName", UnitName }, { "UnitGUID", UnitGUID }, { "UnitClass", UnitClass },
                { "UnitIsGroupLeader", UnitIsGroupLeader }, { "UnitIsConnected", UnitIsConnected } }) do
                local ok, v = pcall(probe[2], unit)
                local k = (not ok and "error") or (issec(v) and "secret") or type(v)
                local slot = roster.units[probe[1]] or {}
                roster.units[probe[1]] = slot
                slot[k] = (slot[k] or 0) + 1
            end
        end
    end

    for _, p in ipairs(UNIT_PROBES) do
        local ok, v = pcall(p[2])
        local slot = m.values[p[1]] or {}
        m.values[p[1]] = slot
        if not ok then
            slot.err = (slot.err or 0) + 1
            slot.lastErr = tostring(v):sub(1, 160)
        elseif v ~= nil or issec(v) then
            local d = describe(v)
            local s = d.secret and "secret" or d.t
            slot[s] = (slot[s] or 0) + 1
            if d.secret then slot.math, slot.cmp, slot.concat = d.math, d.cmp, d.concat end
        else
            slot["nil"] = (slot["nil"] or 0) + 1
        end
    end
end

local function takeSample(reason)
    local ok, err = pcall(takeSampleRaw, reason)
    if not ok then
        DB.counters.sampleErrors = (DB.counters.sampleErrors or 0) + 1
        if DB.counters.sampleErrors <= 20 then log("sample-error", { err = tostring(err):sub(1, 200) }) end
    end
end

------------------------------------------------------------------------------------------------ static run

-- Guild and roles: DisasterZone derives every role from these calls (Core/Guild.lua)
function P.GuildFacts()
    local g = { inGuild = IsInGuild() }
    if g.inGuild then
        local gi = pack(GetGuildInfo("player"))
        g.guildInfoReturns = gi.n
        g.guildName = gi[1]
        g.rankName = gi[2]
        g.rankIndex = gi[3]
        g.isLeader = IsGuildLeader and IsGuildLeader() or nil
        g.isOfficer = C_GuildInfo and C_GuildInfo.IsGuildOfficer and C_GuildInfo.IsGuildOfficer() or nil
        g.canEditOfficerNote = C_GuildInfo and C_GuildInfo.CanEditOfficerNote and C_GuildInfo.CanEditOfficerNote() or nil
        g.canViewOfficerNote = (C_GuildInfo and C_GuildInfo.CanViewOfficerNote and C_GuildInfo.CanViewOfficerNote())
            or (CanViewOfficerNote and CanViewOfficerNote()) or nil
        g.numRanks = GuildControlGetNumRanks and GuildControlGetNumRanks() or nil
        if g.numRanks then
            g.ranks = {}
            for i = 1, g.numRanks do g.ranks[i] = GuildControlGetRankName(i) end
        end
        g.numMembers = { GetNumGuildMembers() }
        g.GetGuildRosterInfo = type(GetGuildRosterInfo) == "function"
        if g.GetGuildRosterInfo then
            local me = UnitName("player")
            local full = playerFullName()
            local total = GetNumGuildMembers() or 0
            g.rosterRowsReadable = 0
            g.nameShapes = {}
            for i = 1, total do
                local r = pack(pcall(GetGuildRosterInfo, i))
                if r[1] and r[2] then
                    g.rosterRowsReadable = g.rosterRowsReadable + 1
                    local raw = tostring(r[2])
                    -- shape only, never other members' names (results are committed to a public repo)
                    local shape = (raw:find(" ", 1, true) and "space" or "nospace") .. "|"
                        .. select(2, raw:gsub("%-", "")) .. "hyphen"
                    g.nameShapes[shape] = (g.nameShapes[shape] or 0) + 1
                    local name = raw:match("^[^-]+")
                    if raw == full or raw == me or name == me then
                        g.selfRow = { returns = r.n - 1, name = r[2], rank = r[3], rankIndex = r[4], level = r[5],
                            class = r[6], noteType = type(r[8]), officerNoteType = type(r[9]),
                            officerNoteLen = type(r[9]) == "string" and #r[9] or nil, online = r[10], classFile = r[12],
                            guid = r[18] and "present" or nil,
                            matchedBy = (raw == full and "fullName") or (raw == me and "UnitName") or "beforeHyphen" }
                    end
                end
            end
        end
        g.SetOfficerNote = type(GuildRosterSetOfficerNote) == "function" or type(resolve("C_GuildInfo.SetNote")) == "function"
        g.C_Club_guildClubId = C_Club and C_Club.GetGuildClubId and C_Club.GetGuildClubId() and "present" or nil
    end
    return g
end

-- Our own name in every form the addon might key by (own character only)
function P.NameFacts()
    local n = {}
    n.UnitName = { UnitName("player") }
    n.UnitFullName = { UnitFullName("player") }
    n.GetUnitNameTrue = GetUnitName and GetUnitName("player", true) or nil
    n.GetRealmName = GetRealmName and GetRealmName() or nil
    n.GetNormalizedRealmName = GetNormalizedRealmName and GetNormalizedRealmName() or nil
    n.playerFullName = playerFullName()
    n.AmbiguateFull = Ambiguate and Ambiguate(playerFullName(), "none") or nil
    return n
end


local function staticRun()
    local s = {}
    DB.static = s
    s.errors = {}
    local valid = C_EventUtils and C_EventUtils.IsEventValid
    local function section(name, fn)
        local ok, err = pcall(fn)
        if not ok then s.errors[name] = tostring(err):sub(1, 200) end
    end
    section("basics", function()
        s.when = date("%Y-%m-%d %H:%M:%S")
        s.probeVersion = VERSION
        s.build = pack(GetBuildInfo())
        s.WOW_PROJECT_ID = WOW_PROJECT_ID
        local projects = {}
        for k, v in pairs(_G) do
            if type(k) == "string" and k:match("^WOW_PROJECT_") and type(v) == "number" then projects[k] = v end
        end
        s.projects = projects
        s.expansion = GetExpansionLevel and GetExpansionLevel()
        s.maxLevel = (GetMaxLevelForPlayerExpansion and GetMaxLevelForPlayerExpansion())
            or (GetMaxPlayerLevel and GetMaxPlayerLevel())
        s.player = { class = select(2, UnitClass("player")), race = select(2, UnitRace("player")),
            level = UnitLevel("player"), faction = UnitFactionGroup("player"), realm = GetRealmName() }
        s.locale = GetLocale()
    end)

    section("lua", function()
        -- Lua environment (in-game updates need loadstring + setfenv)
        local lua = {}
        lua.loadstring = type(loadstring) == "function"
        if lua.loadstring then
            local ok, fn = pcall(loadstring, "return 1 + 1")
            lua.loadstringRuns = ok and type(fn) == "function" and fn() == 2
        end
        lua.load = type(load) == "function"
        lua.setfenv = type(setfenv) == "function"
        lua.getfenv = type(getfenv) == "function"
        lua.newproxy = type(newproxy) == "function"
        lua.debugTraceback = type(debug) == "table" and type(debug.traceback) == "function"
        lua.bit = type(bit) == "table"
        lua.strsplit = type(strsplit) == "function"
        lua.version = _VERSION
        s.lua = lua
    end)

    section("toc", function()
        -- TOC + SavedVariables
        local meta = C_AddOns and C_AddOns.GetAddOnMetadata
        s.toc = {
            svAtFileLoad = svAtFileLoad,
            runs = DB.runs,
            xField = meta and meta(ADDON, "X-Probe") or nil,
            interface = meta and meta(ADDON, "Interface") or nil,
            deprecationFallbacks = GetCVar and GetCVar("loadDeprecationFallbacks") or nil,
        }
    end)

    section("api", function()
        -- API surface the DisasterZone addon uses
        local missing = { C = {}, G = {}, EV = {} }
        local present = { C = 0, G = 0, EV = 0 }
        for _, name in ipairs(P.API_C or {}) do
            if type(resolve(name)) == "function" then present.C = present.C + 1 else missing.C[#missing.C + 1] = name end
        end
        for _, name in ipairs(P.API_G or {}) do
            if _G[name] ~= nil then present.G = present.G + 1 else missing.G[#missing.G + 1] = name end
        end
        for _, ev in ipairs(P.API_EV or {}) do
            local ok, r = true, true
            if valid then ok, r = pcall(valid, ev) end
            if ok and r then present.EV = present.EV + 1 else missing.EV[#missing.EV + 1] = ev end
        end
        s.api = { present = present, missing = missing }
    end)

    section("restrictions", function()
        -- Restriction system and secret-value helpers
        s.restrictions = {
            types = enumNames(Enum and Enum.AddOnRestrictionType),
            states = enumNames(Enum and Enum.AddOnRestrictionState),
            activeNow = restrictionList(),
            helpers = {
                issecretvalue = type(issecretvalue) == "function",
                canaccessvalue = type(canaccessvalue) == "function",
                secretwrap = type(secretwrap) == "function",
                scrubsecretvalues = type(scrubsecretvalues) == "function",
            },
            sendResults = enumNames(Enum and Enum.SendAddonMessageResult),
        }
    end)

    section("combatLog", function()
        -- Combat log
        local cl = {}
        cl.C_CombatLog = type(C_CombatLog) == "table"
        cl.GetCurrentEventInfo = type(resolve("C_CombatLog.GetCurrentEventInfo")) == "function"
        cl.CombatLogGetCurrentEventInfo = type(CombatLogGetCurrentEventInfo) == "function"
        cl.eventValid = valid and select(2, pcall(valid, "COMBAT_LOG_EVENT_UNFILTERED")) or nil
        cl.registerForbidden = true -- known from the 2026-11-08 in-game run, no longer attempted
        cl.eventsSeen = DB.counters.clog or 0
        cl.C_DamageMeter = type(C_DamageMeter) == "table"
        cl.C_EncounterTimeline = type(C_EncounterTimeline) == "table"
        cl.C_SwingTimer = type(C_SwingTimer) == "table"
        s.combatLog = cl
    end)

    section("loot", function()
        -- Loot
        local loot = {}
        loot.methods = enumNames(Enum and Enum.LootMethod)
        loot.styles = enumNames(Enum and Enum.LootMethodStyles)
        loot.legacyGetLootMethod = type(GetLootMethod) == "function"
        loot.SetLootMethod = type(resolve("C_PartyInfo.SetLootMethod")) == "function"
        if C_PartyInfo and C_PartyInfo.GetLootMethod then
            local r = pack(pcall(C_PartyInfo.GetLootMethod))
            loot.current = { ok = r[1], method = enumName(Enum and Enum.LootMethod, r[2]), mlParty = r[3], mlRaid = r[4] }
        end
        if C_PartyInfo and C_PartyInfo.GetLootMethodStyle then
            local ok, st = pcall(C_PartyInfo.GetLootMethodStyle)
            loot.style = ok and enumName(Enum and Enum.LootMethodStyles, st) or "error"
        end
        loot.GiveMasterLoot = type(GiveMasterLoot) == "function"
        loot.GetMasterLootCandidate = type(GetMasterLootCandidate) == "function"
        loot.RollOnLoot = type(RollOnLoot) == "function"
        loot.C_LootHistory = type(C_LootHistory) == "table"
        loot.raidMax = { MAX_RAID_MEMBERS = MAX_RAID_MEMBERS, MEMBERS_PER_RAID_GROUP = MEMBERS_PER_RAID_GROUP,
            NUM_RAID_GROUPS = NUM_RAID_GROUPS }
        s.loot = loot

    end)

    section("names", function() s.names = P.NameFacts() end)

    section("guild", function() s.guild = P.GuildFacts() end)

    section("group", function()
        -- Group / roll
        s.group = { inGroup = IsInGroup(), inRaid = IsInRaid(), members = GetNumGroupMembers(),
            RANDOM_ROLL_RESULT = RANDOM_ROLL_RESULT, RandomRoll = type(RandomRoll) == "function"
                or type(resolve("C_RandomRoll.Roll")) == "function" }
    end)

    section("items", function()
        -- Items and inventory (the upstream "mock fidelity lesson": GetInventoryItemID returns 2 values)
        local it = {}
        it.invItemIdReturns = pack(GetInventoryItemID("player", 16)).n
        it.hearthstone = describe(C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(6948))
        it.thunderfury = describe(C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(19019))
        it.getItemInfoReturns = pack(C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(6948)).n
        it.bag0Slots = C_Container and C_Container.GetContainerNumSlots and C_Container.GetContainerNumSlots(0)
        if C_Item and C_Item.RequestLoadItemDataByID then
            P.itemRequestedAt = now()
            pcall(C_Item.RequestLoadItemDataByID, 19019)
        end
        s.items = it
    end)

    section("tooltip", function()
        -- Tooltips
        s.tooltip = {
            hasOnTooltipSetItem = GameTooltip and GameTooltip.HasScript and GameTooltip:HasScript("OnTooltipSetItem") or false,
            TooltipDataProcessor = type(TooltipDataProcessor) == "table",
            seenOnTooltipSetItem = DB.counters.ttLegacy or 0,
            seenTooltipDataProcessor = DB.counters.ttData or 0,
        }
    end)

    section("talents", function()
        -- Talents / specs / edit mode
        s.talents = {
            GetTalentInfo = type(GetTalentInfo) == "function",
            GetNumTalentTabs = type(GetNumTalentTabs) == "function",
            C_ClassTalents = type(C_ClassTalents) == "table",
            C_Traits = type(C_Traits) == "table",
            activeConfig = C_ClassTalents and C_ClassTalents.GetActiveConfigID and C_ClassTalents.GetActiveConfigID() or nil,
            GetSpecialization = type(GetSpecialization) == "function" and GetSpecialization() or nil,
        }
        s.editModeSystems = enumNames(Enum and Enum.EditModeSystem)
    end)

    section("burst", function()
        -- Addon-message burst: how many of 40 quick GUILD/self messages are accepted
        local burst = { sent = 0, results = {} }
        local ch, target = "WHISPER", playerFullName()
        if IsInGuild() then ch, target = "GUILD", nil end
        burst.channel = ch
        P.burstStart = now()
        DB.counters.burstRecv = 0
        for i = 1, 40 do
            local r = sendTest(ch, target, "b")
            burst.results[r] = (burst.results[r] or 0) + 1
            burst.sent = i
        end
        s.burst = burst
        s.prefixRegistered = C_ChatInfo and C_ChatInfo.IsAddonMessagePrefixRegistered
            and C_ChatInfo.IsAddonMessagePrefixRegistered(PREFIX) or nil
    end)

    section("roll", function()
        -- /roll capture, solo only (in a group the roll line is visible to others)
        if not IsInGroup() and RandomRoll then
            P.rollWaitUntil = now() + 3
            RandomRoll(1, 100)
        end
    end)

    log("static", { note = "static run done" })
    print("|cffff8000DZ Probe|r: static run done. Play normally; /reload or log out to save. /dzprobe for a summary.")
end

------------------------------------------------------------------------------------------------ events

local f = CreateFrame("Frame")
local handlers = {}

local function reg(ev)
    local valid = C_EventUtils and C_EventUtils.IsEventValid
    if valid then
        local ok, r = pcall(valid, ev)
        if ok and not r then return false end
    end
    return pcall(f.RegisterEvent, f, ev)
end

function handlers.ADDON_LOADED(name)
    if name ~= ADDON then return end
    DZProbeDB = DZProbeDB or {}
    DB = DZProbeDB
    if DB.version ~= VERSION then
        for k in pairs(DB) do DB[k] = nil end
        DB.version = VERSION
    end
    DB.runs = (DB.runs or 0) + 1
    DB.log = DB.log or {}
    DB.matrix = DB.matrix or {}
    DB.counters = DB.counters or {}
    DB.svAtFileLoadHistory = DB.svAtFileLoadHistory or {}
    table.insert(DB.svAtFileLoadHistory, svAtFileLoad)
    if Enum and Enum.AddOnRestrictionType then
        for k, v in pairs(Enum.AddOnRestrictionType) do RESTRICTIONS[k] = v end
    end
    if C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix then
        local ok, r = pcall(C_ChatInfo.RegisterAddonMessagePrefix, PREFIX)
        DB.prefixRegisterResult = ok and enumName(Enum and Enum.RegisterAddonMessagePrefixResult, r) or ("error:" .. tostring(r))
    end
    -- Not registering COMBAT_LOG_EVENT_UNFILTERED on purpose: on Forever 1.60.1 the call
    -- returns without a Lua error but the client raises ADDON_ACTION_FORBIDDEN ("UNKNOWN()")
    -- and shows the "blocked from an action only available to the Blizzard UI" popup on
    -- every load. Observed in game 2026-11-08; recorded as a known fact in the static run.
end

function handlers.PLAYER_LOGIN()
    if GameTooltip and GameTooltip.HasScript and GameTooltip:HasScript("OnTooltipSetItem") then
        GameTooltip:HookScript("OnTooltipSetItem", function() DB.counters.ttLegacy = (DB.counters.ttLegacy or 0) + 1 end)
    end
    if TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall and Enum and Enum.TooltipDataType then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function()
            DB.counters.ttData = (DB.counters.ttData or 0) + 1
        end)
    end
    if C_GuildInfo and C_GuildInfo.GuildRoster then pcall(C_GuildInfo.GuildRoster) end
    C_Timer.After(5, staticRun)
    -- passive sampler: every 5 s while anything interesting is going on, every 60 s otherwise
    local last = 0
    C_Timer.NewTicker(5, function()
        local key = P.ContextKey()
        local busy = not key:find("calm|noenc|unrestricted", 1, true)
        if busy or now() - last >= 60 then
            last = now()
            takeSample(busy and "tick-busy" or "tick-idle")
        end
    end)
end

function handlers.ADDON_RESTRICTION_STATE_CHANGED(rtype, state)
    log("restriction", { type = enumName(Enum and Enum.AddOnRestrictionType, rtype),
        state = enumName(Enum and Enum.AddOnRestrictionState, state) })
    C_Timer.After(0.2, function() takeSample("restriction") end)
end

function handlers.PLAYER_REGEN_DISABLED() log("combat-start"); C_Timer.After(1, function() takeSample("combat") end) end
function handlers.PLAYER_REGEN_ENABLED() log("combat-end"); C_Timer.After(1, function() takeSample("after-combat") end) end

function handlers.ENCOUNTER_START(id, name, difficulty, size)
    log("encounter-start", { id = describe(id), name = describe(name), difficulty = describe(difficulty), size = describe(size) })
    C_Timer.After(2, function() takeSample("encounter") end)
end

function handlers.ENCOUNTER_END(id, name, difficulty, size, success)
    log("encounter-end", { id = describe(id), success = describe(success) })
    C_Timer.After(1, function() takeSample("after-encounter") end)
end

function handlers.ZONE_CHANGED_NEW_AREA()
    local _, instType = IsInInstance()
    log("zone", { instType = instType, zone = GetRealZoneText() })
    C_Timer.After(2, function() takeSample("zone") end)
end

function handlers.CHAT_MSG_ADDON(prefix, msg, channel, sender)
    if prefix ~= PREFIX then
        local c = DB.counters.othersByChannel or {}
        DB.counters.othersByChannel = c
        local k = tostring(channel) .. (issec(msg) and "-secret" or "")
        c[k] = (c[k] or 0) + 1
        return
    end
    local secret = issec(msg)
    DB.counters.recv = (DB.counters.recv or 0) + 1
    if secret then DB.counters.recvSecret = (DB.counters.recvSecret or 0) + 1; return end
    local sent = pendingSends[msg]
    if msg:sub(1, 2) == "b:" then DB.counters.burstRecv = (DB.counters.burstRecv or 0) + 1 end
    if sent then
        local lat = now() - sent
        pendingSends[msg] = nil
        local ch = DB.counters.latency or {}
        DB.counters.latency = ch
        local slot = ch[channel] or { n = 0, max = 0, sum = 0 }
        ch[channel] = slot
        slot.n, slot.sum = slot.n + 1, slot.sum + lat
        if lat > slot.max then slot.max = lat end
    end
end

function handlers.CHAT_MSG_SYSTEM(msg)
    if not P.rollWaitUntil or now() > P.rollWaitUntil then return end
    local d = describe(msg)
    local parsed = false
    if not d.secret and type(RANDOM_ROLL_RESULT) == "string" then
        local fmt = RANDOM_ROLL_RESULT:gsub("%%%d+%$", "%%")                 -- "%1$s" -> "%s"
        local pattern = fmt:gsub("([%(%)%.%-%+%*%?%[%]%^%$])", "%%%1")       -- escape magic characters
        pattern = pattern:gsub("%%s", "(.+)"):gsub("%%d", "(%%d+)")
        parsed = msg:match("^" .. pattern .. "$") ~= nil
    end
    DB.static.roll = { message = d, parsedWithRANDOM_ROLL_RESULT = parsed }
    P.rollWaitUntil = nil
end

function handlers.COMBAT_LOG_EVENT_UNFILTERED()
    DB.counters.clog = (DB.counters.clog or 0) + 1
    if DB.counters.clog == 1 then
        local fn = resolve("C_CombatLog.GetCurrentEventInfo") or CombatLogGetCurrentEventInfo
        local r = fn and pack(pcall(fn)) or { n = 0 }
        log("clog-first", { callable = fn ~= nil, ok = r[1], returns = r.n - 1,
            subevent = r[3] and describe(r[3]) or nil })
    end
end

function handlers.GET_ITEM_INFO_RECEIVED(itemID, success)
    if itemID == 19019 and P.itemRequestedAt then
        DB.static.items.thunderfuryLoaded = { success = success, after = now() - P.itemRequestedAt,
            info = describe(C_Item.GetItemInfo(19019)) }
        P.itemRequestedAt = nil
    end
end

function handlers.LOOT_READY()
    local r = C_PartyInfo and C_PartyInfo.GetLootMethod and pack(pcall(C_PartyInfo.GetLootMethod)) or {}
    local n = GetNumLootItems and GetNumLootItems()
    log("loot", { method = enumName(Enum and Enum.LootMethod, r[2]), items = describe(n),
        link1 = n and n > 0 and GetLootSlotLink and describe(GetLootSlotLink(1)) or nil })
end

local function lootMethod()
    local r = C_PartyInfo and C_PartyInfo.GetLootMethod and pack(pcall(C_PartyInfo.GetLootMethod)) or {}
    return enumName(Enum and Enum.LootMethod, r[2]), r[3], r[4]
end

function handlers.LOOT_OPENED()
    local method, mlParty, mlRaid = lootMethod()
    local e = { method = method, mlParty = describe(mlParty), mlRaid = describe(mlRaid),
        GetMasterLootCandidate = type(GetMasterLootCandidate) == "function",
        GiveMasterLoot = type(GiveMasterLoot) == "function" }
    if e.GetMasterLootCandidate and (GetNumLootItems() or 0) > 0 then
        local c = { readable = 0, secret = 0, nils = 0 }
        for i = 1, 40 do
            local ok, v = pcall(GetMasterLootCandidate, 1, i)
            if not ok then c.err = tostring(v):sub(1, 120); break end
            if issec(v) then c.secret = c.secret + 1 elseif v then c.readable = c.readable + 1 else c.nils = c.nils + 1 end
        end
        e.candidatesSlot1 = c
    end
    log("loot-opened", e)
end

function handlers.OPEN_MASTER_LOOT_LIST() log("master-loot-list", { method = (lootMethod()) }) end
function handlers.LOOT_SLOT_CLEARED(slot) log("loot-slot-cleared", { slot = describe(slot), method = (lootMethod()) }) end
function handlers.PARTY_LOOT_METHOD_CHANGED() log("loot-method-changed", { method = (lootMethod()) }) end

function handlers.START_LOOT_ROLL(rollID)
    local e = { rollID = describe(rollID) }
    if GetLootRollItemInfo then
        local r = pack(pcall(GetLootRollItemInfo, rollID))
        e.ok = r[1]
        e.name = describe(r[3])
        e.quality = describe(r[5])
        e.canNeed = describe(r[7])
    end
    if GetLootRollItemLink then e.link = describe(GetLootRollItemLink(rollID)) end
    log("loot-roll", e)
end

function handlers.CHAT_MSG_LOOT(msg)
    DB.counters.lootMsgs = (DB.counters.lootMsgs or 0) + 1
    if DB.counters.lootMsgs <= 5 then log("loot-msg", { msg = { secret = issec(msg), t = type(msg) } }) end
end

function handlers.ADDON_ACTION_BLOCKED(addon, fn) log("action-blocked", { addon = addon, fn = fn }) end
function handlers.ADDON_ACTION_FORBIDDEN(addon, fn) log("action-forbidden", { addon = addon, fn = fn }) end
function handlers.GUILD_ROSTER_UPDATE()
    if DB.static and DB.static.guild and not P.guildRefreshed then
        P.guildRefreshed = true
        DB.static.guild = P.GuildFacts()
        DB.static.guild.refreshedOnRosterUpdate = true
    end
end

function handlers.GROUP_ROSTER_UPDATE()
    log("group", { inRaid = IsInRaid(), n = GetNumGroupMembers(), leader = UnitIsGroupLeader("player"),
        method = (lootMethod()) })
    if not P.groupSamplePending then   -- roster updates come in bursts; one sample per burst
        P.groupSamplePending = true
        C_Timer.After(2, function() P.groupSamplePending = nil; takeSample("group") end)
    end
end

for _, ev in ipairs({ "ADDON_LOADED", "PLAYER_LOGIN" }) do f:RegisterEvent(ev) end
for ev in pairs(handlers) do
    if ev ~= "ADDON_LOADED" and ev ~= "PLAYER_LOGIN" and ev ~= "COMBAT_LOG_EVENT_UNFILTERED" then reg(ev) end
end
f:SetScript("OnEvent", function(_, ev, ...)
    local h = handlers[ev]
    if not h or (not DB and ev ~= "ADDON_LOADED") then return end
    local ok, err = pcall(h, ...)
    if not ok and DB then
        DB.counters.handlerErrors = (DB.counters.handlerErrors or 0) + 1
        log("handler-error", { ev = ev, err = tostring(err):sub(1, 200) })
    end
end)

------------------------------------------------------------------------------------------------ slash command

SLASH_DZPROBE1 = "/dzprobe"
SlashCmdList.DZPROBE = function(arg)
    arg = (arg or ""):lower()
    if arg == "run" then
        staticRun()
    elseif arg == "sample" then
        takeSample("manual"); print("|cffff8000DZ Probe|r: sample taken in " .. P.ContextKey())
    elseif arg == "reset" then
        for k in pairs(DZProbeDB) do DZProbeDB[k] = nil end
        print("|cffff8000DZ Probe|r: cleared. /reload to start fresh.")
    else
        local s = DB.static or {}
        local contexts = 0
        for _ in pairs(DB.matrix) do contexts = contexts + 1 end
        print(("|cffff8000DZ Probe|r: runs %d, log %d entries, %d contexts sampled, %d handler errors."):format(
            DB.runs or 0, #DB.log, contexts, DB.counters.handlerErrors or 0))
        if s.api then
            print(("  APIs present: C_ %d, globals %d, events %d. Missing: %d / %d / %d"):format(
                s.api.present.C, s.api.present.G, s.api.present.EV, #s.api.missing.C, #s.api.missing.G, #s.api.missing.EV))
        end
        print("  Now: " .. P.ContextKey() .. ". Commands: /dzprobe run | sample | reset")
    end
end
