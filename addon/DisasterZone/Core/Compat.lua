if DisasterZoneBoot and DisasterZoneBoot.Run("Core/Compat.lua", ...) then return end
-- DisasterZone (Forever): the client compatibility layer. Loads right after the boot loader, before everything else.
--
-- WoW Forever (client 1.60.1, Interface 16001) runs vanilla content on the current retail engine. Measured by the
-- DZProbe addon (dev/probe/, vault: 01-Overview/Probe Findings 2026-11-08.md):
--  * about 30 global functions the TBC client still had are gone; each has a C_ replacement. Shims below rebuild the
--    old global with the old return order, ONLY when the global is missing, so on a client that still has it (the
--    test harness, TBC) nothing changes. Functions with no safe one-to-one replacement (old talent tabs, trade skill
--    and craft windows, GetNumBankSlots) stay missing: every DisasterZone caller already checks for them first. The
--    talents are read through Compat.TalentTabPoints / Talents / TalentRank / SpecRole (Forever's trait tree).
--  * there is no addon combat log: registering COMBAT_LOG_EVENT_UNFILTERED raises ADDON_ACTION_FORBIDDEN and the
--    "only available to the Blizzard UI" popup. Compat.combatLog is false there and every place that registers it
--    asks Compat:CanUseCombatLog() first.
--  * addon messages are refused (AddOnMessageLockdown) for the whole of a boss pull. Compat:InChatLockdown() says
--    when; Core/Comm.lua holds messages until it ends.
local addonName, ns = ...
local _G = _G
local type, pcall = type, pcall

local Compat = {}
ns.Compat = Compat

Compat.projectId = _G.WOW_PROJECT_ID
Compat.isForever = _G.WOW_PROJECT_ID ~= nil and _G.WOW_PROJECT_ID == (_G.WOW_PROJECT_CAMELOT or 18)
-- (fallback: the interface number, should the project id ever change or go missing)
if not Compat.isForever and type(_G.GetBuildInfo) == "function" then
    local ok, _, _, _, interface = pcall(_G.GetBuildInfo)
    Compat.isForever = ok and tonumber(interface) == 16001
end
-- the secret-values era (the Midnight engine) has no addon combat log, Forever included
Compat.secrets = type(_G.issecretvalue) == "function"
Compat.combatLog = not (Compat.isForever or Compat.secrets)

function Compat:CanUseCombatLog() return self.combatLog end

-- True while the client refuses addon messages (a boss pull on Forever). False where the API does not exist.
function Compat:InChatLockdown()
    local C = _G.C_ChatInfo
    if C and C.InChatMessagingLockdown then
        local ok, locked = pcall(C.InChatMessagingLockdown)
        return ok and locked == true
    end
    return false
end

-- Plain value or a secret one the addon may not read (Forever's secret values; always false elsewhere).
function Compat.IsSecret(v)
    local f = _G.issecretvalue
    return f ~= nil and f(v) == true
end

-- True when the addon may read every value given (an event's payload). During a boss pull on Forever the CHAT_MSG_*
-- payloads are secret (SecretInChatMessagingLockdown); Blizzard's chat filters skip them the same way
-- (Blizzard_ChatFrameBase/Shared/ChatFrameFilters.lua: canaccessvalue). Always true where secrets don't exist.
function Compat.CanAccess(...)
    if select("#", ...) == 0 then return true end
    local all = _G.canaccessallvalues
    if all then return all(...) == true end
    local one, sec = _G.canaccessvalue, _G.issecretvalue
    for i = 1, select("#", ...) do
        local v = select(i, ...)
        if one then
            if one(v) ~= true then return false end
        elseif sec and sec(v) == true then
            return false
        end
    end
    return true
end

-- v, or nil when it is a secret value. On Forever UnitHealth / UnitHealthMax / UnitPower / UnitPowerMax are secret
-- everywhere, and UnitGUID / UnitName of a non-player unit inside an instance (Probe Findings 2026-11-08): a secret
-- may be handed to a widget but never compared, used in arithmetic or used as a table key.
function Compat.Plain(v)
    if Compat.IsSecret(v) then return nil end
    return v
end

-- cur / max * 100 when both are plain numbers and max > 0, else nil (secret or unknown).
function Compat.Pct(cur, max)
    cur, max = Compat.Plain(cur), Compat.Plain(max)
    if type(cur) ~= "number" or type(max) ~= "number" or max <= 0 then return nil end
    return cur / max * 100
end

-- A unit's health in % (0-100), or nil when the client keeps it secret (always on Forever).
function Compat.HealthPct(unit)
    local h, m = _G.UnitHealth, _G.UnitHealthMax
    if not (h and m) then return nil end
    return Compat.Pct(h(unit), m(unit))
end

-- A unit's power in % (0-100) of powerType (nil: its current one), or nil when secret.
function Compat.PowerPct(unit, powerType)
    local p, m = _G.UnitPower, _G.UnitPowerMax
    if not (p and m) then return nil end
    return Compat.Pct(p(unit, powerType), m(unit, powerType))
end

-- UnitGUID(unit), or nil when there is none or it is secret.
function Compat.GUID(unit)
    local g = _G.UnitGUID
    return g and Compat.Plain(g(unit)) or nil
end

---------------------------------------------------------------------------
-- Talents: points per tree, talent ranks, the spec's role
---------------------------------------------------------------------------
-- TBC 2.5.6: three talent tabs; C_SpecializationInfo.GetSpecializationInfo(tab) has the tab's points as its 7th
-- return (GetTalentTabInfo is the older alias, points 5th; the 2.4 order had them 3rd), GetTalentInfo the talents.
-- WoW Forever: ONE spec per class, named after the class, pointsSpent 0 (seen in game 2026-11-09 on a warrior:
-- "1491 Warrior 626008 DAMAGER 4 0 nil 0 true"), and none of the old talent globals. The vanilla trees are trait-node
-- groups of the spec's trait tree (Blizzard_PlayerSpells/Camelot/ClassTalents/Blizzard_ClassTalentsFrame.lua, the
-- tree headers): C_Traits.GetGroupDisplayInfoByTreeID(treeID) gives each tree's displayName and orderIndex,
-- C_Traits.GetGroupCurrencyInfo(configID, groupIDs)[i].currencyInfos[1].spent its points. The tree comes from
-- C_ClassTalents.GetTraitTreeForSpec(specID), the config from C_ClassTalents.GetActiveConfigID() (a spec group:
-- C_SpecializationInfo.GetCombatConfigIDForSpecGroup). UNVERIFIED in game: that the group names are the vanilla tree
-- names (a tab is matched to ns.SPECS by name, else by order).
local talentCache = {}                       -- [group or 0] = { at, trees }

local function SpecsOfMyClass()
    local _, cls = _G.UnitClass and _G.UnitClass("player")
    return cls and ns.SPECS and ns.SPECS[cls] or nil
end

-- The tab number (ns.SPECS' tab) of a Forever trait group: by its name ("Feral Combat" -> the Feral specs' tab),
-- else by its place.
local function TabOfGroup(displayName, place)
    local specs = SpecsOfMyClass()
    if specs and type(displayName) == "string" then
        local first = displayName:match("^(%S+)")
        for _, s in ipairs(specs) do
            if s.label == displayName or (first and s.label:match("^(%S+)") == first) then return s.tab end
        end
    end
    return place
end

-- Forever: { treeID, configID, groups = { { id, tab, name, points } } } of talent group `group` (nil: the active
-- one), or nil when the client can't tell. Cached for a second (role checks run often; a respec shows next second).
local function ForeverTrees(group)
    local key = group or 0
    local now = _G.GetTime and _G.GetTime() or 0
    local c = talentCache[key]
    if c and now - c.at < 1 then return c.trees end
    local CS, CT, TR = _G.C_SpecializationInfo, _G.C_ClassTalents, _G.C_Traits
    local trees
    if CS and CT and TR and CS.GetSpecializationInfo and CT.GetTraitTreeForSpec and TR.GetGroupDisplayInfoByTreeID
        and TR.GetGroupCurrencyInfo then
        local ok, res = pcall(function()
            local index = CS.GetSpecialization and CS.GetSpecialization() or 1
            local specID = CS.GetSpecializationInfo(index or 1)
            local treeID = specID and CT.GetTraitTreeForSpec(specID)
            if not treeID then return nil end
            local configID
            if group and CS.GetCombatConfigIDForSpecGroup then configID = CS.GetCombatConfigIDForSpecGroup(group)
            elseif not group and CT.GetActiveConfigID then configID = CT.GetActiveConfigID() end
            if not configID then return nil end
            local displays = TR.GetGroupDisplayInfoByTreeID(treeID) or {}
            local sorted = {}
            for _, d in ipairs(displays) do sorted[#sorted + 1] = d end
            table.sort(sorted, function(a, b) return (a.orderIndex or 0) < (b.orderIndex or 0) end)
            local ids = {}
            for i, d in ipairs(sorted) do ids[i] = d.groupID end
            local spent = {}
            for _, g in ipairs(TR.GetGroupCurrencyInfo(configID, ids) or {}) do
                local cur = g.currencyInfos and g.currencyInfos[1]
                spent[g.traitNodeGroupID] = cur and tonumber(Compat.Plain(cur.spent)) or 0
            end
            local out = { treeID = treeID, configID = configID, groups = {} }
            for i, d in ipairs(sorted) do
                out.groups[i] = { id = d.groupID, tab = TabOfGroup(d.displayName, i), name = d.displayName,
                                  points = spent[d.groupID] or 0 }
            end
            return out
        end)
        trees = ok and res or nil
    end
    talentCache[key] = { at = now, trees = trees }
    return trees
end

-- Forgets what was read (a respec): the next question asks the client again.
function Compat.TalentsChanged() for k in pairs(talentCache) do talentCache[k] = nil end end

-- Talent trees the class has (3; Forever: its trait groups). Never 0, so a loop over the tabs always runs.
function Compat.NumTalentTabs()
    if Compat.isForever then
        local t = ForeverTrees()
        return t and #t.groups > 0 and #t.groups or 3
    end
    return (_G.GetNumTalentTabs and tonumber(_G.GetNumTalentTabs())) or 3
end

-- Points spent in talent tab `tab` (ns.SPECS' numbering) of talent group `group` (nil: the active one); nil when
-- the client can't tell.
function Compat.TalentTabPoints(tab, group)
    if Compat.isForever then
        local t = ForeverTrees(group)
        if not t then return nil end
        for _, g in ipairs(t.groups) do
            if g.tab == tab then return g.points end
        end
        return 0
    end
    local CS = _G.C_SpecializationInfo
    if CS and CS.GetSpecializationInfo then
        local ok, _, _, _, _, _, _, points = pcall(CS.GetSpecializationInfo, tab, false, false, nil, nil, group)
        if ok and tonumber(points) then return tonumber(points) end
    end
    if _G.GetTalentTabInfo then
        local ok, r1, _, r3, _, r5 = pcall(_G.GetTalentTabInfo, tab, false, false, group)
        if ok then return (type(r1) == "string") and tonumber(r3) or tonumber(r5) end
    end
    return nil
end

-- Every talent of the active group: { { name, icon, rank, maxRank, tab, spellID, tier, column } } (tier / column
-- only where the client has them: not on Forever). nil when the client can't tell.
function Compat.Talents()
    if Compat.isForever then
        local t = ForeverTrees()
        local TR, CSp = _G.C_Traits, _G.C_Spell
        if not (t and TR and TR.GetTreeNodes and TR.GetNodeInfo and TR.GetEntryInfo and TR.GetDefinitionInfo) then
            return nil
        end
        local tabOf = {}
        for _, g in ipairs(t.groups) do tabOf[g.id] = g.tab end
        local ok, list = pcall(function()
            local out = {}
            for _, nodeID in ipairs(TR.GetTreeNodes(t.treeID) or {}) do
                local node = TR.GetNodeInfo(t.configID, nodeID)
                local entryID = node and ((node.activeEntry and node.activeEntry.entryID) or (node.entryIDs and node.entryIDs[1]))
                local entry = entryID and TR.GetEntryInfo(t.configID, entryID)
                local def = entry and entry.definitionID and TR.GetDefinitionInfo(entry.definitionID)
                if def then
                    local sid = def.spellID
                    local name = def.overrideName or (sid and CSp and CSp.GetSpellName and CSp.GetSpellName(sid))
                    local icon = def.overrideIcon or (sid and CSp and CSp.GetSpellTexture and CSp.GetSpellTexture(sid))
                    local tab
                    for _, gid in ipairs(node.groupIDs or {}) do tab = tab or tabOf[gid] end
                    out[#out + 1] = { name = name, icon = icon, spellID = sid, tab = tab,
                                      rank = tonumber(node.activeRank) or tonumber(node.ranksPurchased) or 0,
                                      maxRank = tonumber(node.maxRanks) or tonumber(entry.maxRanks) or 0 }
                end
            end
            return out
        end)
        return ok and list or nil
    end
    if not (_G.GetNumTalentTabs and _G.GetNumTalents and _G.GetTalentInfo) then return nil end
    local out = {}
    for tab = 1, tonumber(_G.GetNumTalentTabs()) or 0 do
        for i = 1, tonumber(_G.GetNumTalents(tab)) or 0 do
            local name, icon, tier, column, rank, maxRank, _, available = _G.GetTalentInfo(tab, i)
            if name then
                out[#out + 1] = { name = name, icon = icon, tab = tab, tier = tonumber(tier), column = tonumber(column),
                                  rank = tonumber(rank) or 0, maxRank = tonumber(maxRank) or 0,
                                  available = available }
            end
        end
    end
    return out
end

-- Points in one talent, by its spell id or name (0: not taken or not found; nil: the client can't tell).
function Compat.TalentRank(spell)
    local list = Compat.Talents()
    if not list then return nil end
    local want = spell
    if type(spell) == "number" then
        local GSI = _G.GetSpellInfo
        want = GSI and GSI(spell) or nil
    end
    for _, t in ipairs(list) do
        if (type(spell) == "number" and t.spellID == spell) or (want and t.name == want) then return t.rank end
    end
    return 0
end

-- The role the client gives the spec: "TANK" | "HEALER" | "DAMAGER", or nil. On Forever every class has one spec
-- and a fixed role (a warrior is DAMAGER, seen in game), so it is the last guess, not the first.
function Compat.SpecRole()
    local CS = _G.C_SpecializationInfo
    if not (CS and CS.GetSpecialization and CS.GetSpecializationInfo) then return nil end
    local ok, role = pcall(function()
        local index = CS.GetSpecialization()
        if not index then return nil end
        return select(5, CS.GetSpecializationInfo(index))
    end)
    if ok and (role == "TANK" or role == "HEALER" or role == "DAMAGER") then return role end
    return nil
end

---------------------------------------------------------------------------
-- Global shims: old name -> builder returning the replacement (nil when the replacement is missing too)
---------------------------------------------------------------------------

local function ns_(name) local t = _G[name]; return type(t) == "table" and t or nil end
local C_Item, C_Spell, C_SpellBook, C_UnitAuras = ns_("C_Item"), ns_("C_Spell"), ns_("C_SpellBook"), ns_("C_UnitAuras")
local C_Container, C_CurrencyInfo, C_PartyInfo = ns_("C_Container"), ns_("C_CurrencyInfo"), ns_("C_PartyInfo")
local C_Reputation, C_SkillInfo, C_MerchantFrame, C_Bank = ns_("C_Reputation"), ns_("C_SkillInfo"),
    ns_("C_MerchantFrame"), ns_("C_Bank")
local C_GuildInfo, C_QuestLog, C_PvP, C_PaperDollInfo = ns_("C_GuildInfo"), ns_("C_QuestLog"), ns_("C_PvP"),
    ns_("C_PaperDollInfo")

local function from(t, key) return t and t[key] end

local function unpackAura(a)
    if not a then return nil end
    local AU = _G.AuraUtil
    if AU and AU.UnpackAuraData then return AU.UnpackAuraData(a) end
    return a.name, a.icon, a.applications, a.dispelName, a.duration, a.expirationTime, a.sourceUnit, a.isStealable,
        a.nameplateShowPersonal, a.spellId
end

-- (WoW Forever refuses auras to an addon in combat: GetAuraDataByIndex raises "Auras cannot be accessed when secret
-- while tainted" (DZProbe 2026-11-08). The old globals then answer "no aura", as when the unit has none.)
local function auraBy(filterBase)
    local get = from(C_UnitAuras, "GetAuraDataByIndex")
    if not get then return nil end
    return function(unit, index, filter)
        local f = filterBase
        if filter and filter ~= "" then f = f and (f .. "|" .. filter) or filter end
        local ok, a = pcall(get, unit, index, f)
        if not ok then return nil end
        return unpackAura(a)
    end
end

local SHIMS = {
    -- items
    GetItemInfo = function() return from(C_Item, "GetItemInfo") end,
    GetItemIcon = function() return from(C_Item, "GetItemIconByID") end,
    GetItemCount = function() return from(C_Item, "GetItemCount") end,
    IsEquippableItem = function() return from(C_Item, "IsEquippableItem") end,
    GetItemGem = function() return from(C_Item, "GetItemGem") end,
    IsItemInRange = function() return from(C_Item, "IsItemInRange") end,
    -- spells: name, rank, icon, castTime, minRange, maxRange, spellID, originalIcon
    GetSpellInfo = function()
        local get = from(C_Spell, "GetSpellInfo")
        return get and function(spell)
            if spell == nil then return nil end
            local i = get(spell)
            if i then return i.name, nil, i.iconID, i.castTime, i.minRange, i.maxRange, i.spellID, i.originalIconID end
        end
    end,
    GetSpellLink = function() return from(C_Spell, "GetSpellLink") end,
    GetSpellTexture = function() return from(C_Spell, "GetSpellTexture") end,
    GetSpellSubtext = function() return from(C_Spell, "GetSpellSubtext") end,
    -- start, duration, enabled (1/0), modRate
    GetSpellCooldown = function()
        local get = from(C_Spell, "GetSpellCooldown")
        return get and function(spell)
            local c = get(spell)
            if c then return c.startTime, c.duration, c.isEnabled and 1 or 0, c.modRate end
        end
    end,
    IsUsableSpell = function() return from(C_Spell, "IsSpellUsable") end,
    IsCurrentSpell = function() return from(C_Spell, "IsCurrentSpell") end,
    -- 1 in range, 0 out of range, nil when it cannot tell (the old numeric answer)
    IsSpellInRange = function()
        local get = from(C_Spell, "IsSpellInRange")
        return get and function(spell, unit)
            local r = get(spell, unit)
            if r == nil then return nil end
            return r and 1 or 0
        end
    end,
    -- spell book tabs: name, texture, offset, numSlots, isGuild, offSpecID
    GetNumSpellTabs = function() return from(C_SpellBook, "GetNumSpellBookSkillLines") end,
    GetSpellTabInfo = function()
        local get = from(C_SpellBook, "GetSpellBookSkillLineInfo")
        return get and function(tab)
            local t = get(tab)
            if t then return t.name, t.iconID, t.itemIndexOffset, t.numSpellBookItems, t.isGuild, t.offSpecID end
        end
    end,
    GetSpellBookItemName = function()
        local get = from(C_SpellBook, "GetSpellBookItemName")
        local bank = _G.Enum and _G.Enum.SpellBookSpellBank
        return get and bank and function(index, bookType)
            return get(index, (bookType == "pet" or bookType == _G.BOOKTYPE_PET) and bank.Pet or bank.Player)
        end
    end,
    -- auras in the old unpacked order
    UnitAura = function() return auraBy(nil) end,
    UnitBuff = function() return auraBy("HELPFUL") end,
    UnitDebuff = function() return auraBy("HARMFUL") end,
    -- bags: texture, count, locked, quality, readable, lootable, link, isFiltered, noValue, itemID, isBound
    GetContainerItemInfo = function()
        local get = from(C_Container, "GetContainerItemInfo")
        return get and function(bag, slot)
            local i = get(bag, slot)
            if i then
                return i.iconFileID, i.stackCount, i.isLocked, i.quality, i.isReadable, i.hasLoot, i.hyperlink,
                    i.isFiltered, i.hasNoValue, i.itemID, i.isBound
            end
        end
    end,
    GetCoinTextureString = function() return from(C_CurrencyInfo, "GetCoinTextureString") end,
    InviteUnit = function() return from(C_PartyInfo, "InviteUnit") end,
    ConvertToRaid = function() return from(C_PartyInfo, "ConvertToRaid") end,
    -- spells (PickupSpell / IsAutoRepeatSpell take a name or an id, like the old globals)
    PickupSpell = function() return from(C_Spell, "PickupSpell") end,
    IsAutoRepeatSpell = function() return from(C_Spell, "IsAutoRepeatSpell") end,
    GetNumQuestWatches = function() return from(C_QuestLog, "GetNumQuestWatches") end,
    -- pvpType, isSubZonePvP, factionName
    GetZonePVPInfo = function() return from(C_PvP, "GetZonePVPInfo") end,
    OffhandHasWeapon = function() return from(C_PaperDollInfo, "OffhandHasWeapon") end,
    -- guild: invite by name; the officer note of roster row i (C_GuildInfo.SetNote takes the member's GUID, the
    -- 17th return of GetGuildRosterInfo)
    GuildInvite = function() return from(C_GuildInfo, "Invite") end,
    CanEditOfficerNote = function() return from(C_GuildInfo, "CanEditOfficerNote") end,
    GuildRosterSetOfficerNote = function()
        local set, roster = from(C_GuildInfo, "SetNote"), _G.GetGuildRosterInfo
        return set and roster and function(index, note)
            local guid = Compat.Plain((select(17, roster(index))))
            if type(guid) ~= "string" or guid == "" then return end
            set(guid, tostring(note or ""), false)
        end
    end,
    -- reputation: name, description, standingID, barMin, barMax, barValue, atWar, canToggleAtWar, isHeader,
    -- isCollapsed, hasRep, isWatched, isChild, factionID, hasBonusRepGain, canSetInactive
    GetFactionInfoByID = function()
        local get = from(C_Reputation, "GetFactionDataByID")
        return get and function(id)
            local d = get(id)
            if d then
                return d.name, d.description, d.reaction, d.currentReactionThreshold, d.nextReactionThreshold,
                    d.currentStanding, d.atWarWith, d.canToggleAtWar, d.isHeader, d.isCollapsed, d.isHeaderWithRep,
                    d.isWatched, d.isChild, d.factionID, d.hasBonusRepGain, d.canSetInactive
            end
        end
    end,
    -- name, standingID, barMin, barMax, barValue, factionID
    GetWatchedFactionInfo = function()
        local get = from(C_Reputation, "GetWatchedFactionData")
        return get and function()
            local d = get()
            if d then
                return d.name, d.reaction, d.currentReactionThreshold, d.nextReactionThreshold, d.currentStanding,
                    d.factionID
            end
        end
    end,
    -- skills: name, isHeader, isExpanded, rank, tempPoints, modifier, maxRank, isAbandonable, stepCost, rankCost,
    -- minLevel, costType, description
    GetNumSkillLines = function() return from(C_SkillInfo, "GetNumSkillLines") end,
    GetSkillLineInfo = function()
        local get = from(C_SkillInfo, "GetSkillLineInfo")
        return get and function(index)
            local s = get(index)
            if s then
                return s.name, s.isHeader, not s.isCollapsed, s.rank, s.tempPoints, s.modifier, s.maxRank,
                    s.isAbandonable, s.stepCost, s.rankCost, s.minLevel, s.costType, s.description
            end
        end
    end,
    ExpandSkillHeader = function() return from(C_SkillInfo, "ExpandSkillHeader") end,
    -- merchant: name, texture, price, stackCount, numAvailable, isPurchasable, isUsable, extendedCost
    GetMerchantItemInfo = function()
        local get = from(C_MerchantFrame, "GetItemInfo")
        return get and function(index)
            local m = get(index)
            if m then
                return m.name, m.texture, m.price, m.stackCount, m.numAvailable, m.isPurchasable, m.isUsable,
                    m.hasExtendedCost
            end
        end
    end,
    CloseBankFrame = function() return from(C_Bank, "CloseBankFrame") end,
}

-- Fills each missing global from its replacement. Written through a table key on purpose: these are the client's
-- own names, rebuilt once, never DisasterZone state. Compat.shimmed lists what was filled (the Performance page and
-- the tests read it).
Compat.shimmed = {}
for name, build in pairs(SHIMS) do
    if _G[name] == nil then
        local fn = build()
        if type(fn) == "function" then
            _G[name] = fn
            Compat.shimmed[#Compat.shimmed + 1] = name
        end
    end
end
table.sort(Compat.shimmed)

---------------------------------------------------------------------------
-- Combat-restricted reads (WoW Forever): spell cooldowns, attack / ranged speed, movement speed, raid marks
---------------------------------------------------------------------------
-- The retail engine hands addons these as secret values while the matching restriction is on (Blizzard's API docs:
-- C_Spell.GetSpellCooldown SecretWhenCooldownsRestricted; UnitAttackSpeed, UnitRangedDamage and GetUnitSpeed
-- SecretWhenUnitStatsRestricted; GetRaidTargetIndex SecretReturns). Each helper below answers plain numbers, or nil
-- where the client keeps the value secret, so a caller keeps its last known value (or hides its bar) instead of
-- raising. On TBC nothing is secret and they return what the old globals return. UNVERIFIED in game: exactly when
-- Forever switches each restriction on (assumed: in combat, and inside an instance).

-- A spell's cooldown: start, duration, found. start / duration are plain numbers, or nil when the client keeps them
-- secret; found is false when the client does not know the spell (nil spell, not in the spellbook). A cooldown that
-- is not running answers 0, 0 even while restricted (SpellCooldownInfo.isActive is never secret).
function Compat.SpellCooldown(spell)
    if spell == nil then return nil, nil, false end
    local C = _G.C_Spell
    local get = C and C.GetSpellCooldown
    if get and (Compat.secrets or Compat.isForever or not _G.GetSpellCooldown) then
        local ok, info = pcall(get, spell)
        if not ok then return nil, nil, false end
        if Compat.IsSecret(info) then return nil, nil, true end
        if info == nil then return nil, nil, false end
        if type(info) ~= "table" then return nil, nil, false end
        local s, d = Compat.Plain(info.startTime), Compat.Plain(info.duration)
        if s == nil or d == nil then
            if info.isActive == false then return 0, 0, true end
            return nil, nil, true
        end
        return tonumber(s) or 0, tonumber(d) or 0, true
    end
    local g = _G.GetSpellCooldown
    if not g then return nil, nil, false end
    local s, d = g(spell)
    if s == nil and d == nil then return nil, nil, false end
    s, d = Compat.Plain(s), Compat.Plain(d)
    if s == nil or d == nil then return nil, nil, true end
    return tonumber(s) or 0, tonumber(d) or 0, true
end

-- Seconds left on a spell's cooldown at now (GetTime()), or nil when unknown (no such spell, or secret).
function Compat.CooldownLeft(spell, now)
    local s, d = Compat.SpellCooldown(spell)
    if s == nil then return nil end
    if s == 0 or d == 0 then return 0 end
    now = now or (_G.GetTime and _G.GetTime()) or 0
    local left = s + d - now
    return left > 0 and left or 0
end

-- UnitAttackSpeed(unit): main hand, off hand (plain numbers, each nil when absent or secret).
function Compat.AttackSpeed(unit)
    local f = _G.UnitAttackSpeed
    if not f then return nil, nil end
    local mh, oh = f(unit or "player")
    return Compat.Plain(mh), Compat.Plain(oh)
end

-- UnitRangedDamage(unit)'s speed (the first return), or nil when absent or secret.
function Compat.RangedSpeed(unit)
    local f = _G.UnitRangedDamage
    if not f then return nil end
    return Compat.Plain((f(unit or "player")))
end

-- GetUnitSpeed(unit): current, run, flight, swim speed (yards / s), each nil when absent or secret.
function Compat.UnitSpeed(unit)
    local f = _G.GetUnitSpeed
    if not f then return nil end
    local cur, run, flight, swim = f(unit or "player")
    return Compat.Plain(cur), Compat.Plain(run), Compat.Plain(flight), Compat.Plain(swim)
end

-- GetRaidTargetIndex(unit) as a plain 1-8, or nil (no mark, or secret: the docs mark its return always secret).
function Compat.RaidMark(unit)
    local f = _G.GetRaidTargetIndex
    if not f then return nil end
    local i = Compat.Plain(f(unit))
    return type(i) == "number" and i or nil
end

-- UnitIsUnit(a, b) as a plain boolean. While the client keeps the answer secret (SecretWhenUnitComparisonRestricted)
-- the two GUIDs decide when both are plain (players), else false. UNVERIFIED: whether a secret boolean raises when
-- tested (it is never tested here).
function Compat.SameUnit(a, b)
    local f = _G.UnitIsUnit
    if not f then return false end
    local r = f(a, b)
    if Compat.IsSecret(r) then
        local ga, gb = Compat.GUID(a), Compat.GUID(b)
        return ga ~= nil and ga == gb
    end
    return r and true or false
end

-- UnitName(unit) as a plain string, or nil (no unit, or a secret name: an NPC inside an instance on Forever).
function Compat.Name(unit)
    local f = _G.UnitName
    if not f then return nil end
    local n = Compat.Plain((f(unit)))
    return type(n) == "string" and n or nil
end
