-- wowmock/forever.lua : the WoW Forever profile (client 1.60.1, Interface 16001: vanilla content on the retail engine).
-- Loaded after game.lua only for a client made with forever=True (tools/harness.py). It turns the TBC Anniversary
-- mock into the client DZProbe measured (dev/probe/, vault: 01-Overview/Probe Findings 2026-11-08.md). The numbers
-- come from forever_facts.lua, generated from a probe run by dev/probe/mock_facts.py.
--
-- What changes:
--  * identity: GetBuildInfo 1.60.1 / 16001, WOW_PROJECT_ID 18 (CAMELOT), expansion 0, level cap 60
--  * ~45 old globals removed (GetSpellInfo, UnitBuff, GetItemInfo, ...); their C_ replacements present
--  * two events gone (CRAFT_SHOW, LEARNED_SPELL_IN_TAB): registering them errors like the real client
--  * no addon combat log: registering COMBAT_LOG_EVENT_UNFILTERED is ADDON_ACTION_FORBIDDEN (recorded as an error,
--    the real client shows Blizzard's "blocked" popup)
--  * addon restrictions (C_RestrictedActions, ADDON_RESTRICTION_STATE_CHANGED): Combat while in combat, Map inside
--    an instance, Encounter + Chat for a boss pull. In the order the probe logged them: ENCOUNTER_START is delivered
--    first, then Encounter and Chat switch on; at the end both switch off, then ENCOUNTER_END is delivered.
--  * chat lockdown: while Chat is on, C_ChatInfo.InChatMessagingLockdown() is true and every SendAddonMessage
--    returns AddOnMessageLockdown (11) and sends nothing (M.lockdown_refused counts them); CHAT_MSG_* payloads
--    (and READY_CHECK, GUILD_MOTD, the countdowns) arrive secret
--  * globals the UI source shows gone (ConvertToRaid, GuildInvite, officer notes, PickupSpell, ...): C_ names only
--  * PARTY_KILL / UNIT_DIED / LEARNED_SPELL_IN_SKILL_LINE exist (M.party_kill, M.unit_died)
--  * secret values: UnitHealth / UnitHealthMax / UnitPower always; UnitName / UnitGUID of an NPC target inside an
--    instance. A secret can be passed around and concatenated, not compared or used in arithmetic.
--  * auras: C_UnitAuras.GetAuraDataByIndex errors in combat ("cannot be accessed when secret while tainted")
--  * tooltips: no OnTooltipSetItem script; TooltipDataProcessor.AddTooltipPostCall instead
local M, cfg, PY = ...
local F = M.forever_facts
local type, pairs, ipairs, error = type, pairs, ipairs, error

M.forever = true

---------------------------------------------------------------------------------------------------
-- identity
---------------------------------------------------------------------------------------------------
local B = F.build
function GetBuildInfo() return B.version, B.build, B.date, B.interface end
for k, v in pairs(F.projects) do _G[k] = v end
WOW_PROJECT_ID = F.projectId
function GetExpansionLevel() return F.expansion end
function GetServerExpansionLevel() return F.expansion end
function GetMaxPlayerLevel() return F.maxLevel end
function GetMaxLevelForPlayerExpansion() return F.maxLevel end
for k, v in pairs(F.raidMax) do _G[k] = v end
Enum.LootMethod = {}
for k, v in pairs(F.lootMethods) do Enum.LootMethod[k] = v end
Enum.LootStyle = {}
for k, v in pairs(F.lootStyles) do Enum.LootStyle[k] = v end
C_Loot = C_Loot or {}
C_Loot.GetLootStyle = function() return Enum.LootStyle[F.lootStyle] end
Enum.SendAddonMessageResult = {}
for k, v in pairs(F.sendResults) do Enum.SendAddonMessageResult[k] = v end
Enum.AddOnRestrictionType, Enum.AddOnRestrictionState = {}, {}
for k, v in pairs(F.restrictionTypes) do Enum.AddOnRestrictionType[k] = v end
for k, v in pairs(F.restrictionStates) do Enum.AddOnRestrictionState[k] = v end

---------------------------------------------------------------------------------------------------
-- secret values
---------------------------------------------------------------------------------------------------
local secrets = setmetatable({}, { __mode = "k" })
local function refuse(what) return function() error("attempt to " .. what .. " a secret value", 2) end end
local secret_mt = {
  __add = refuse("perform arithmetic on"), __sub = refuse("perform arithmetic on"),
  __mul = refuse("perform arithmetic on"), __div = refuse("perform arithmetic on"),
  __mod = refuse("perform arithmetic on"), __pow = refuse("perform arithmetic on"),
  __unm = refuse("perform arithmetic on"), __lt = refuse("compare"), __le = refuse("compare"),
  __len = refuse("get the length of"), __index = refuse("index"), __newindex = refuse("index"),
  __call = refuse("call"), __tostring = function() return "<secret>" end,
}
local function secret_concat(a, b)
  return M.secret("")
end
secret_mt.__concat = secret_concat

-- A secret wrapper of v (nil stays nil, like the client). In the client a secret keeps its Lua type ("a secret number
-- value"): type() says "number" and tonumber() hands it back, so `tonumber(UnitPower("player")) or 0` is still secret
-- and the arithmetic after it fails (seen in game 2026-11-08, Core/Resource.lua). The mock's secrets are tables, so the
-- global type / tonumber below answer for them like the client.
local secret_kind = setmetatable({}, { __mode = "k" })
function M.secret(v)
  if v == nil then return nil end
  local s = setmetatable({}, secret_mt)
  secrets[s] = true
  secret_kind[s] = type(v)
  return s
end
do
  local raw_type, raw_tonumber = type, tonumber
  _G.type = function(v)
    local k = secret_kind[v]
    if k then return k end
    return raw_type(v)
  end
  _G.tonumber = function(v, base)
    if secret_kind[v] == "number" then return v end
    if base == nil then return raw_tonumber(v) end
    return raw_tonumber(v, base)
  end
end
function issecretvalue(v) return secrets[v] == true end
function canaccessvalue(v) return secrets[v] ~= true end
function canaccessallvalues(...)
  for i = 1, select("#", ...) do
    if secrets[(select(i, ...))] then return false end
  end
  return true
end
function scrubsecretvalues(...)
  local n = select("#", ...)
  local t = { ... }
  for i = 1, n do if secrets[t[i]] then t[i] = nil end end
  return unpack(t, 1, n)
end
function secretwrap(...)
  local n = select("#", ...)
  local t = { ... }
  for i = 1, n do t[i] = M.secret(t[i]) end
  return unpack(t, 1, n)
end

local function always_secret(name)
  local base = _G[name]
  _G[name] = function(...) return M.secret(base(...)) end
end
always_secret("UnitHealth")
always_secret("UnitHealthMax")
always_secret("UnitPower")
-- (seen in game 2026-11-08: DisasterZone's shot timer compared UnitRangedDamage's speed and hit a secret number)
do
  local base = UnitRangedDamage
  UnitRangedDamage = function(...)
    local r = { base(...) }
    r[1] = M.secret(r[1])
    return unpack(r, 1, 6)
  end
end

-- an NPC target inside an instance: its name and GUID are secret (players stay readable)
local function npc_unit_in_instance(unit)
  if not M.W.instance or type(unit) ~= "string" then return false end
  local m = M.unit_rec(unit)
  return m ~= nil and m.npc == true
end
for _, name in ipairs({ "UnitName", "UnitGUID", "UnitNameUnmodified", "GetUnitName" }) do
  local base = _G[name]
  if base then
    _G[name] = function(unit, ...)
      if npc_unit_in_instance(unit) then return M.secret((base(unit, ...))) end
      return base(unit, ...)
    end
  end
end

---------------------------------------------------------------------------------------------------
-- names: regionally unique, first name + surname ("Arakis War")
-- Measured 2026-11-08 on the GM: UnitName("player") / UnitFullName("player") "Arakis", GetUnitName("player", true)
-- "Arakis War", guild roster "Arakis War" (no realm). Blizzard_FrameXMLUtil/Camelot/NameUtil.lua: UnitName returns
-- name, surname. A harness client named "Arakis War" is such a character; a one-word name has no surname.
---------------------------------------------------------------------------------------------------
function RegionalUniqueNamesEnabled() return true end
Constants = Constants or {}
Constants.CharacterNameSeparatorConsts = { CHARACTERNAME_SURNAME_SEPARATOR = " ", CHARACTERNAME_REALMNAME_SEPARATOR = "-" }
C_PlayerInfo = C_PlayerInfo or {}
C_PlayerInfo.ShouldDisplaySurname = function() return true end

local whole_name = UnitName                        -- the mock's: the whole name (+ realm for another realm)
local function name_parts(unit)
  local n = whole_name(unit)
  if type(n) ~= "string" then return n end         -- (nil, or a secret NPC name in an instance)
  local first, surname = n:match("^(%S+) (.+)$")
  if first then return first, surname end
  return n, nil
end
UnitName = name_parts
UnitNameUnmodified = name_parts
UnitFullName = name_parts
function GetUnitName(unit) return (whole_name(unit)) end   -- (Camelot NameUtil: name + surname, no realm)

local roster_info = GetGuildRosterInfo
function GetGuildRosterInfo(i)
  local r = { roster_info(i) }
  if type(r[1]) == "string" then
    local own = "-" .. M.norm_realm(M.W.realm)
    if r[1]:sub(-#own) == own then r[1] = r[1]:sub(1, -#own - 1) end
  end
  return unpack(r, 1, 17)
end

---------------------------------------------------------------------------------------------------
-- addon restrictions
---------------------------------------------------------------------------------------------------
local RT, RS = Enum.AddOnRestrictionType, Enum.AddOnRestrictionState
M.restrictions = {}                                -- type number -> state number (absent = Inactive)
M.restriction_log = {}                             -- { {t, type, state} } for the tests

local function set_restriction(rtype, on)
  local state = on and RS.Activating or RS.Inactive
  if (M.restrictions[rtype] or RS.Inactive) == state then return end
  M.restrictions[rtype] = on and state or nil
  M.restriction_log[#M.restriction_log + 1] = { t = M.now, type = rtype, state = state }
  M.fire("ADDON_RESTRICTION_STATE_CHANGED", rtype, state)
end
M.set_restriction = set_restriction

local function active(rtype) return M.restrictions[rtype] ~= nil end
M.restriction_active = active

C_RestrictedActions = {
  IsAddOnRestrictionActive = function(rtype) return active(rtype) end,
  GetAddOnRestrictionState = function(rtype) return M.restrictions[rtype] or RS.Inactive end,
}

-- the client's own order (probe log): ENCOUNTER_START reaches addons before Encounter/Chat switch on; at the end
-- both switch off before ENCOUNTER_END goes out. Combat follows the regen events; Map follows being in an instance.
local fire_before = M.fire
function M.fire(event, ...)
  if event == "ENCOUNTER_END" then
    set_restriction(RT.Encounter, false)
    set_restriction(RT.Chat, false)
    return fire_before(event, ...)
  end
  if event == "PLAYER_REGEN_ENABLED" then set_restriction(RT.Combat, false) end
  local r = fire_before(event, ...)
  if event == "ENCOUNTER_START" then
    set_restriction(RT.Encounter, true)
    set_restriction(RT.Chat, true)
  elseif event == "PLAYER_REGEN_DISABLED" then
    set_restriction(RT.Combat, true)
  elseif event == "PLAYER_ENTERING_WORLD" or event == "ZONE_CHANGED_NEW_AREA" then
    set_restriction(RT.Map, M.W.instance ~= nil)
  end
  return r
end

---------------------------------------------------------------------------------------------------
-- chat lockdown: addon messages refused for the whole of a boss pull
---------------------------------------------------------------------------------------------------
M.lockdown_refused = 0
M.lockdown_refused_by = {}                         -- prefix -> count
local LOCKDOWN = Enum.SendAddonMessageResult.AddOnMessageLockdown
local CI = C_ChatInfo
CI.InChatMessagingLockdown = function() return active(RT.Chat) end
for _, fname in ipairs({ "SendAddonMessage", "SendAddonMessageLogged" }) do
  local base = CI[fname]
  CI[fname] = function(prefix, text, chatType, target)
    if active(RT.Chat) then
      M.lockdown_refused = M.lockdown_refused + 1
      M.lockdown_refused_by[prefix] = (M.lockdown_refused_by[prefix] or 0) + 1
      return LOCKDOWN
    end
    return base(prefix, text, chatType, target)
  end
end
-- chat payloads: while Chat is on, the CHAT_MSG_* events (not CHAT_MSG_ADDON) and a few others reach addons with a
-- secret payload (SecretInChatMessagingLockdown in Blizzard_APIDocumentationGenerated). M.chat_secret_fired counts.
local LOCKDOWN_SECRET = { READY_CHECK = true, GUILD_MOTD = true, START_PLAYER_COUNTDOWN = true,
                          CANCEL_PLAYER_COUNTDOWN = true }
M.chat_secret_fired = 0
local fire_plain = M.fire
function M.fire(event, ...)
  if active(RT.Chat) and type(event) == "string" and select("#", ...) > 0
      and (LOCKDOWN_SECRET[event] or (event:sub(1, 9) == "CHAT_MSG_" and event:sub(1, 14) ~= "CHAT_MSG_ADDON")) then
    M.chat_secret_fired = M.chat_secret_fired + 1
    return fire_plain(event, secretwrap(...))
  end
  return fire_plain(event, ...)
end

---------------------------------------------------------------------------------------------------
-- C_ replacements the TBC mock lacks, built from the old globals before those go
---------------------------------------------------------------------------------------------------
local old = {}
for _, n in ipairs(F.removedGlobals) do
  if type(_G[n]) == "function" then old[n] = _G[n] end
end

C_UnitAuras = C_UnitAuras or {}
if not C_UnitAuras.GetAuraDataByIndex and old.UnitAura then
  local UnitAura = old.UnitAura
  C_UnitAuras.GetAuraDataByIndex = function(unit, index, filter)
    if active(RT.Combat) then
      error("GetAuraDataByIndex(): Auras cannot be accessed when secret while tainted by 'DisasterZone'", 2)
    end
    local name, icon, count, dispel, duration, expires, source, steal, npShow, spellId = UnitAura(unit, index, filter)
    if not name then return nil end
    return { name = name, icon = icon, applications = count, dispelName = dispel, duration = duration,
      expirationTime = expires, sourceUnit = source, isStealable = steal, nameplateShowPersonal = npShow,
      spellId = spellId, points = {} }
  end
end
C_Spell = C_Spell or {}
if not C_Spell.GetSpellCooldown and old.GetSpellCooldown then
  local get = old.GetSpellCooldown
  C_Spell.GetSpellCooldown = function(spell)
    local s, d, e, m = get(spell)
    if s == nil then return nil end
    return { startTime = s, duration = d, isEnabled = e == 1 or e == true, modRate = m or 1 }
  end
end
if not C_Spell.GetSpellLink and old.GetSpellLink then C_Spell.GetSpellLink = old.GetSpellLink end
if not C_Spell.IsSpellUsable and old.IsUsableSpell then C_Spell.IsSpellUsable = old.IsUsableSpell end
if not C_Spell.IsCurrentSpell and old.IsCurrentSpell then C_Spell.IsCurrentSpell = old.IsCurrentSpell end
if not C_Spell.IsSpellInRange and old.IsSpellInRange then
  local get = old.IsSpellInRange
  C_Spell.IsSpellInRange = function(spell, unit)
    local r = get(spell, unit)
    if r == nil then return nil end
    return r == 1 or r == true
  end
end
C_PartyInfo = C_PartyInfo or {}
-- (game.lua's C_PartyInfo.InviteUnit calls the global by name: once InviteUnit is gone, an addon's own global
-- InviteUnit that calls C_PartyInfo.InviteUnit (Core/Compat.lua) would recurse. The C_ one takes the old function.)
if old.InviteUnit then C_PartyInfo.InviteUnit = old.InviteUnit end

-- Globals the probe did not list but the Forever UI source shows gone (Final Scan 2026-11-09: Blizzard's own code
-- calls only the C_ name; Blizzard_DeprecatedGuildScript sets GuildInvite only with loadDeprecationFallbacks).
-- Their C_ replacements (signatures from Blizzard_APIDocumentationGenerated), then the old names go below.
local UI_SOURCE_REMOVED = { "ConvertToRaid", "GuildInvite", "CanEditOfficerNote", "GuildRosterSetOfficerNote",
  "PickupSpell", "IsAutoRepeatSpell", "GetNumQuestWatches", "GetZonePVPInfo", "OffhandHasWeapon" }
for _, n in ipairs(UI_SOURCE_REMOVED) do
  if type(_G[n]) == "function" then old[n] = _G[n] end
end
M.forever_converted = 0
if old.ConvertToRaid then
  local convert = old.ConvertToRaid
  C_PartyInfo.ConvertToRaid = function() M.forever_converted = M.forever_converted + 1; return convert() end
end
C_GuildInfo = C_GuildInfo or {}
C_GuildInfo.Invite = old.GuildInvite or function() end
-- SetNote(guid, note, isPublic): the member by the GUID GetGuildRosterInfo returns 17th
M.forever_set_notes = {}
C_GuildInfo.SetNote = function(guid, note, isPublic)
  if type(guid) ~= "string" or type(note) ~= "string" or type(isPublic) ~= "boolean" then
    error("Usage: C_GuildInfo.SetNote(guid, note, isPublic)", 2)
  end
  if not isPublic and not C_GuildInfo.CanEditOfficerNote() then
    M.warn("C_GuildInfo.SetNote (officer) without permission: ignored")
    return
  end
  for i = 1, (GetNumGuildMembers()) do
    local r = { roster_info(i) }                   -- (the TBC mock's row: the full name with the realm)
    if r[17] == guid then
      M.forever_set_notes[#M.forever_set_notes + 1] = { guid = guid, note = note, public = isPublic }
      PY.set_note(r[1], isPublic and "public" or "officer", M.hex(note))
      return
    end
  end
end
M.forever_picked = {}
C_Spell.PickupSpell = function(spell) M.forever_picked[#M.forever_picked + 1] = spell; if old.PickupSpell then return old.PickupSpell(spell) end end
C_Spell.IsAutoRepeatSpell = function(spell)
  if old.IsAutoRepeatSpell then return old.IsAutoRepeatSpell(spell) and true or false end
  return M.auto_repeat == true
end
C_QuestLog = C_QuestLog or {}
C_QuestLog.GetNumQuestWatches = old.GetNumQuestWatches or function() return M.quest_watches or 0 end
C_PvP = C_PvP or {}
if old.GetZonePVPInfo then C_PvP.GetZonePVPInfo = old.GetZonePVPInfo end
C_PaperDollInfo = C_PaperDollInfo or {}
if old.OffhandHasWeapon then C_PaperDollInfo.OffhandHasWeapon = old.OffhandHasWeapon end
C_Container = C_Container or {}
if not C_Container.GetContainerItemInfo and old.GetContainerItemInfo then
  local get = old.GetContainerItemInfo
  C_Container.GetContainerItemInfo = function(bag, slot)
    local tex, count, locked, quality, readable, lootable, link, filtered, noValue, itemID, bound = get(bag, slot)
    if tex == nil and itemID == nil then return nil end
    return { iconFileID = tex, stackCount = count, isLocked = locked, quality = quality, isReadable = readable,
      hasLoot = lootable, hyperlink = link, isFiltered = filtered, hasNoValue = noValue, itemID = itemID,
      isBound = bound }
  end
end
C_Reputation = C_Reputation or {}
if not C_Reputation.GetFactionDataByID and old.GetFactionInfoByID then
  local get = old.GetFactionInfoByID
  C_Reputation.GetFactionDataByID = function(id)
    local name, desc, reaction, lo, hi, cur, atWar, canWar, isHeader, collapsed, hasRep, watched, child, fid = get(id)
    if not name then return nil end
    return { name = name, description = desc, reaction = reaction, currentReactionThreshold = lo,
      nextReactionThreshold = hi, currentStanding = cur, atWarWith = atWar, canToggleAtWar = canWar,
      isHeader = isHeader, isCollapsed = collapsed, isHeaderWithRep = hasRep, isWatched = watched, isChild = child,
      factionID = fid or id }
  end
end

-- skills: C_SkillInfo (SkillInfoDocumentation.lua: GetSkillLineInfo(index) -> SkillLineAttributes)
C_SkillInfo = C_SkillInfo or {}
if not C_SkillInfo.GetSkillLineInfo and old.GetSkillLineInfo then
  local get = old.GetSkillLineInfo
  C_SkillInfo.GetNumSkillLines = old.GetNumSkillLines
  C_SkillInfo.ExpandSkillHeader = old.ExpandSkillHeader
  C_SkillInfo.GetSkillLineInfo = function(index)
    local name, isHeader, isExpanded, rank, temp, mod, maxRank, abandon, step, cost, minLevel, costType, desc = get(index)
    if not name then return nil end
    return { skillID = 0, name = name, isHeader = isHeader == true, isCollapsed = isHeader == true and not isExpanded,
      rank = rank or 0, tempPoints = temp or 0, modifier = mod or 0, maxRank = maxRank or 0, isAbandonable = abandon == true,
      stepCost = step or 0, rankCost = cost or 0, minLevel = minLevel or 0, costType = costType or 0,
      parentSkillLineID = 0, skillLineCategoryID = 0, description = desc or "" }
  end
end

-- the profession window: the retail C_TradeSkillUI (measured 2026-11-08: GetAllRecipeIDs, GetFilteredRecipeIDs,
-- IsTradeSkillLinked, GetRecipeOutputItemData present; 507 recipe ids for Blacksmithing, learned or not).
-- Driven by the same M.tradeskill the TBC profile uses: rows { name, spell, item [, learned = false] }. There is no
-- separate craft window on Forever (Enchanting opens in the same one).
C_TradeSkillUI = C_TradeSkillUI or {}
local function ts_rows()
  local t = M.tradeskill
  local out = {}
  if t then for _, r in ipairs(t.rows or {}) do if r.spell then out[#out + 1] = r end end end
  return out
end
local function ts_row(id)
  for _, r in ipairs(ts_rows()) do if r.spell == id then return r end end
end
C_TradeSkillUI.GetAllRecipeIDs = function()
  local ids = {}
  for _, r in ipairs(ts_rows()) do ids[#ids + 1] = r.spell end
  return ids
end
C_TradeSkillUI.GetFilteredRecipeIDs = C_TradeSkillUI.GetAllRecipeIDs
C_TradeSkillUI.GetRecipeInfo = function(id)
  local r = ts_row(id)
  if not r then return nil end
  return { recipeID = id, name = r.name, learned = r.learned ~= false, categoryID = 0, maxTrivialLevel = 0, itemLevel = 0,
    numSkillUps = 1, canSkillUp = false, firstCraft = false, disabled = false, favorite = false,
    supportsQualities = false, craftable = true, skillLineAbilityID = 0, supportsCraftingStats = false }
end
C_TradeSkillUI.GetRecipeOutputItemData = function(id)
  local r = ts_row(id)
  if not r then return nil end
  return { icon = 136243, itemID = r.item, hyperlink = r.item and M.item_link and M.item_link(r.item) or nil }
end
C_TradeSkillUI.GetBaseProfessionInfo = function()
  local t = M.tradeskill
  if not t then return { professionID = 0, professionName = "", skillLevel = 0, maxSkillLevel = 0, skillModifier = 0,
    isPrimaryProfession = false, sourceCounter = 0, expansionName = "" } end
  return { professionID = 0, professionName = t.name, skillLevel = t.rank or 0, maxSkillLevel = t.max or 0,
    skillModifier = 0, isPrimaryProfession = true, sourceCounter = 0, expansionName = "" }
end
C_TradeSkillUI.IsTradeSkillLinked = function() return M.tradeskill ~= nil and M.tradeskill.linked ~= nil end
C_TradeSkillUI.IsTradeSkillGuild = function() return false end
C_TradeSkillUI.IsNPCCrafting = function() return false end

-- the old names go (only real client functions: the probe's list also caught local names, e.g. "Cell")
M.forever_removed = {}
for n in pairs(old) do
  _G[n] = nil
  M.forever_removed[#M.forever_removed + 1] = n
end
table.sort(M.forever_removed)
-- deprecation-gated globals the TBC mock adds with legacy_globals=True are gone on Forever too
for _, n in ipairs(F.removedGlobals) do M.legacy[n] = nil end
for _, n in ipairs(UI_SOURCE_REMOVED) do M.legacy[n] = nil end

---------------------------------------------------------------------------------------------------
-- events: two removed ones, and no addon combat log
---------------------------------------------------------------------------------------------------
M.removed_events = {}
for _, e in ipairs(F.removedEvents) do
  M.removed_events[e] = true
  M.known_events[e] = nil
end
local IsEventValid = C_EventUtils.IsEventValid
C_EventUtils.IsEventValid = function(e)
  if M.removed_events[e] then return false end
  return IsEventValid(e)
end

M.forbidden = {}                                   -- { {event, where} }: ADDON_ACTION_FORBIDDEN raised
local Frame = M.Methods.Frame
local RegisterEvent = Frame.RegisterEvent
Frame.RegisterEvent = function(self, ev)
  if M.removed_events[ev] then
    error("Attempt to register unknown event \"" .. tostring(ev) .. "\"", 2)
  end
  if ev == "COMBAT_LOG_EVENT_UNFILTERED" and F.combatLogForbidden then
    local where = debugstack and debugstack(2, 1, 0) or "?"
    M.forbidden[#M.forbidden + 1] = { event = ev, where = where }
    M.record_error("ADDON_ACTION_FORBIDDEN: an addon registered COMBAT_LOG_EVENT_UNFILTERED (Blizzard UI only on "
      .. "WoW Forever; the client shows the 'blocked' popup)", "RegisterEvent(COMBAT_LOG_EVENT_UNFILTERED)")
    M.after(0, function() M.fire("ADDON_ACTION_FORBIDDEN", "DisasterZone", "UNKNOWN()") end, "ADDON_ACTION_FORBIDDEN")
    return
  end
  return RegisterEvent(self, ev)
end
-- Frame:SetPropagateKeyboardInput is protected in combat (seen in game 2026-11-09: ADDON_ACTION_BLOCKED, Atlas page
-- open in a fight): blocked and recorded as an error, like the protected calls game.lua blocks.
M.blocked = M.blocked or {}
local SetPropagate = Frame.SetPropagateKeyboardInput
Frame.SetPropagateKeyboardInput = function(self, v)
  if M.combat then
    M.blocked[#M.blocked + 1] = "SetPropagateKeyboardInput"
    M.record_error("ADDON_ACTION_BLOCKED: AddOn 'DisasterZone' tried to call the protected function "
      .. "'Frame:SetPropagateKeyboardInput()' (in combat)", "SetPropagateKeyboardInput")
    return
  end
  return SetPropagate(self, v)
end
M.known_events.ADDON_RESTRICTION_STATE_CHANGED = true
M.known_events.ADDON_ACTION_FORBIDDEN = true
-- retail-engine events (Blizzard_APIDocumentationGenerated): LEARNED_SPELL_IN_SKILL_LINE (spellID, skillLineIndex,
-- isGuildPerkSpell) replaces LEARNED_SPELL_IN_TAB; PARTY_KILL (attackerGUID, targetGUID) and UNIT_DIED (unitGUID)
-- stand in for the combat log's subevents, their GUIDs secret when unit identity is restricted (the mock: inside an
-- instance, M.party_kill / M.unit_died below)
M.known_events.LEARNED_SPELL_IN_SKILL_LINE = true
M.known_events.PARTY_KILL = true
M.known_events.UNIT_DIED = true
local function identity(guid)
  if M.W.instance then return M.secret(guid) end
  return guid
end
function M.party_kill(attackerGUID, targetGUID) M.fire("PARTY_KILL", identity(attackerGUID), identity(targetGUID)) end
function M.unit_died(unitGUID) M.fire("UNIT_DIED", identity(unitGUID)) end

---------------------------------------------------------------------------------------------------
-- swings: C_SwingTimer's PLAYER_SWING (swingDuration, swingType 0 main hand / 1 off hand / 2 ranged), the only swing
-- feed an addon has without the combat log (Blizzard_APIDocumentationGenerated/SwingTimerDocumentation.lua; the
-- Blizzard_SwingTimer addon registers it). UNVERIFIED in game that an addon frame receives it.
---------------------------------------------------------------------------------------------------
M.known_events.PLAYER_SWING = true
M.known_events.TRAIT_CONFIG_UPDATED = true          -- (SharedTraitsDocumentation.lua: a talent change)
Enum.PlayerSwingType = { MainHand = 0, OffHand = 1, Ranged = 2 }
function M.player_swing(swingType, duration)
  M.fire("PLAYER_SWING", tonumber(duration) or 2.6, tonumber(swingType) or 0)
end

---------------------------------------------------------------------------------------------------
-- talents: one spec per class, named after the class, with no points (seen in game 2026-11-09 on a warrior:
-- C_SpecializationInfo.GetSpecializationInfo(1) printed "1491 Warrior 626008 DAMAGER 4 0 nil 0 true"). The vanilla
-- trees are trait-node groups of the spec's trait tree (Blizzard_PlayerSpells/Camelot/ClassTalents: the tree headers
-- are C_Traits.GetGroupDisplayInfoByTreeID + C_Traits.GetGroupCurrencyInfo(...).currencyInfos[1].spent). The mock's
-- groups are the TBC mock's three tabs with M.talents / M.talents2 as their points; M.trait_talents (set by a test)
-- lists talents as trait nodes: { spellID =, icon =, tab =, rank =, rank2 =, max = } (names: the spell's).
-- UNVERIFIED: the group display names (assumed the vanilla tree names) and the role of each class's spec (DAMAGER
-- is only seen on a warrior); the spec ids are Blizzard_ClassTalentUtil.lua's SpecializationVisuals.
---------------------------------------------------------------------------------------------------
local SPEC_ID = { MAGE = 1482, DRUID = 1484, HUNTER = 1485, PALADIN = 1486, PRIEST = 1487, ROGUE = 1488,
                  SHAMAN = 1489, WARLOCK = 1490, WARRIOR = 1491 }
local SPEC_ICON = { WARRIOR = 626008 }
local SPEC_STAT = { WARRIOR = 4 }
local TREE_OF = {}                                  -- treeID -> class file
for cls, id in pairs(SPEC_ID) do TREE_OF[id + 10000] = cls end
local function me_class() return (M.W.self and M.W.self.class) or "WARRIOR" end
local GetTabInfo = M.tbc_tab_info                   -- (game.lua's tab table, kept before the global went)
C_SpecializationInfo = {
  GetSpecialization = function() return 1 end,
  GetActiveSpecGroup = function() return M.forever_spec_group or 1 end,
  GetNumSpecializationsForClassID = function() return 1 end,
  GetSpecializationInfo = function(index)
    if tonumber(index) ~= 1 then return 0, nil, nil, nil, nil, nil, 0, nil, 0, true end
    local cls = me_class()
    local name = (LOCALIZED_CLASS_NAMES_MALE and LOCALIZED_CLASS_NAMES_MALE[cls]) or cls
    return SPEC_ID[cls] or 0, name, "", SPEC_ICON[cls] or 135000, M.forever_spec_role or "DAMAGER",
      SPEC_STAT[cls] or 4, 0, nil, 0, true
  end,
  GetCombatConfigIDForSpecGroup = function(group)
    group = tonumber(group) or 1
    if group == 2 and not M.talents2 then return nil end
    return group
  end,
}
C_ClassTalents = {
  GetActiveConfigID = function() return M.forever_spec_group or 1 end,
  GetTraitTreeForSpec = function(specID)
    for _, id in pairs(SPEC_ID) do if id == specID then return id + 10000 end end
    return nil
  end,
}
local function groups_of(treeID)
  local cls = TREE_OF[tonumber(treeID) or 0]
  if not cls then return {} end
  local out = {}
  for tab = 1, 3 do
    local name = GetTabInfo(cls, tab)
    out[tab] = { groupID = treeID * 10 + tab, treeID = treeID, skillLineID = 0, orderIndex = tab - 1,
                 displayName = name or ("Tree " .. tab), icon = 136243 + tab }
  end
  return out
end
local function talents_of(configID) return (tonumber(configID) == 2 and M.talents2) or M.talents end
C_Traits = {
  GetGroupDisplayInfoByTreeID = function(treeID) return groups_of(treeID) end,
  GetGroupCurrencyInfo = function(configID, groupIDs)
    local pts = talents_of(configID) or {}
    local out = {}
    for _, gid in ipairs(groupIDs or {}) do
      local tab = gid % 10
      out[#out + 1] = { traitNodeGroupID = gid,
                        currencyInfos = { { traitCurrencyID = 1, quantity = 0, spent = tonumber(pts[tab]) or 0 } } }
    end
    return out
  end,
  -- talent nodes: node id = tree * 100 + i, entry = node + 50000, definition = entry + 50000
  GetTreeNodes = function(treeID)
    local out = {}
    if not TREE_OF[tonumber(treeID) or 0] then return out end
    for i in ipairs(M.trait_talents or {}) do out[i] = treeID * 100 + i end
    return out
  end,
  GetNodeInfo = function(configID, nodeID)
    local i = nodeID % 100
    local t = (M.trait_talents or {})[i]
    if not t then return { ID = nodeID, entryIDs = {}, activeRank = 0, currentRank = 0, ranksPurchased = 0, groupIDs = {} } end
    local tree = math.floor(nodeID / 100)
    local entry = nodeID + 50000
    local rank = (tonumber(configID) == 2 and t.rank2) or t.rank or 0
    return { ID = nodeID, entryIDs = { entry }, activeRank = rank, currentRank = rank, ranksPurchased = rank,
             maxRanks = t.max or 5, isVisible = true, groupIDs = { tree * 10 + (t.tab or 1) },
             activeEntry = rank > 0 and { entryID = entry, rank = rank } or nil }
  end,
  GetEntryInfo = function(configID, entryID)
    return { definitionID = entryID + 50000, type = 1, maxRanks = 5, isAvailable = true, conditionIDs = {} }
  end,
  GetDefinitionInfo = function(definitionID)
    local i = (definitionID - 100000) % 100
    local t = (M.trait_talents or {})[i] or {}
    return { spellID = t.spellID, overrideName = t.overrideName, overrideIcon = t.icon }
  end,
}

---------------------------------------------------------------------------------------------------
-- tooltips: TooltipDataProcessor, no OnTooltipSetItem
---------------------------------------------------------------------------------------------------
Enum.TooltipDataType = Enum.TooltipDataType or { Item = 0, Spell = 1, Unit = 2 }
M.tooltip_post_calls = {}
TooltipDataProcessor = {
  AddTooltipPostCall = function(dataType, fn)
    local l = M.tooltip_post_calls[dataType]
    if not l then l = {}; M.tooltip_post_calls[dataType] = l end
    l[#l + 1] = fn
  end,
}
-- (the GameTooltip script list loses OnTooltipSetItem: HasScript says false, SetScript / HookScript error like the
-- client; ui.lua's item tooltips call the Item post-calls instead)
if not F.onTooltipSetItem then M.SCRIPTS.GameTooltip.OnTooltipSetItem = nil end
-- (the retail engine has no OnTooltipSetUnit / OnTooltipSetSpell either: hooking them errors, as in game 2026-11-12,
-- GameTooltip:HasScript("OnTooltipSetUnit") = false; the Unit and Spell post-calls run instead, M.tooltip_post_calls_of)
if not F.onTooltipSetUnit then M.SCRIPTS.GameTooltip.OnTooltipSetUnit = nil end
if not F.onTooltipSetSpell then M.SCRIPTS.GameTooltip.OnTooltipSetSpell = nil end
function M.tooltip_post_calls_of(kind, tooltip, data)
  local t = Enum.TooltipDataType[kind]
  local l = t ~= nil and M.tooltip_post_calls[t]
  if not l then return end
  for i = 1, #l do M.safecall("TooltipDataProcessor " .. kind .. " post-call", l[i], tooltip, data) end
end
function M.tooltip_item_post_calls(tooltip, itemID)
  local l = M.tooltip_post_calls[Enum.TooltipDataType.Item]
  if not l then return end
  for i = 1, #l do M.safecall("TooltipDataProcessor Item post-call", l[i], tooltip, { type = 0, id = itemID }) end
end

---------------------------------------------------------------------------------------------------
-- combat secrets: the values Blizzard's API docs mark secret while a restriction is on (Blizzard_APIDocumentationGenerated:
-- SecretWhenCooldownsRestricted, SecretWhenUnitStatsRestricted, SecretWhenUnitSpellCastRestricted,
-- SecretWhenUnitThreatValuesRestricted, SecretWhenUnitComparisonRestricted, SecretWhenUnitIdentityRestricted,
-- SecretWhenUnitPowerRestricted, SecretWhenTotemSlotSecret; GetRaidTargetIndex SecretReturns). When each restriction
-- switches on in the real client is UNVERIFIED; the mock takes the strict reading:
--  * in combat: spell cooldowns (startTime / duration; isActive and isOnGCD never), UnitAttackSpeed, GetUnitSpeed,
--    threat (UnitDetailedThreatSituation, UnitThreatSituation), GetComboPoints, GetTotemInfo
--  * a non-player unit in combat or inside an instance: its casts (UnitCastingInfo / UnitChannelInfo: name, times,
--    spell), and UnitIsUnit with it; inside an instance its UnitClass / UnitClassBase / UnitCreatureType too
--  * always: GetRaidTargetIndex
-- M.combat_secrets = false switches this block off (a test of the plain path on the Forever profile).
---------------------------------------------------------------------------------------------------
M.combat_secrets = true
local function in_combat() return M.combat_secrets ~= false and M.combat == true end
local function npc_restricted(unit)
  if M.combat_secrets == false or type(unit) ~= "string" then return false end
  local m = M.unit_rec(unit)
  if not (m and m.npc) then return false end
  return M.combat == true or M.W.instance ~= nil
end
local function npc_in_instance(unit)
  return M.combat_secrets ~= false and npc_unit_in_instance(unit)
end
local function pack(...) return { ... }, select("#", ...) end
local function wrap(name, when, which)              -- which: return positions made secret (nil: all)
  local base = _G[name]
  if type(base) ~= "function" then return end
  _G[name] = function(...)
    local r, n = pack(base(...))
    if not when(...) then return unpack(r, 1, n) end
    if which then
      for _, i in ipairs(which) do r[i] = M.secret(r[i]) end
    else
      for i = 1, n do r[i] = M.secret(r[i]) end
    end
    return unpack(r, 1, n)
  end
end

do
  local get = C_Spell.GetSpellCooldown
  C_Spell.GetSpellCooldown = function(spell)
    local info = get(spell)
    if info == nil then return nil end
    local s, d = tonumber(info.startTime) or 0, tonumber(info.duration) or 0
    info.isActive = info.isEnabled ~= false and s > 0 and d > 0
    info.isOnGCD = info.isActive and d <= 1.5 or false
    if in_combat() then info.startTime, info.duration = M.secret(s), M.secret(d) end
    return info
  end
end
wrap("UnitAttackSpeed", in_combat)
wrap("GetUnitSpeed", in_combat)
wrap("UnitDetailedThreatSituation", in_combat)
wrap("UnitThreatSituation", in_combat)
wrap("GetComboPoints", in_combat)
wrap("GetTotemInfo", in_combat)
wrap("UnitCastingInfo", npc_restricted, { 1, 2, 3, 4, 5, 9 })
wrap("UnitChannelInfo", npc_restricted, { 1, 2, 3, 4, 5, 8 })
wrap("UnitClass", npc_in_instance)
wrap("UnitClassBase", npc_in_instance)
wrap("UnitCreatureType", npc_in_instance)
wrap("UnitIsUnit", function(a, b) return npc_restricted(a) or npc_restricted(b) end)
wrap("GetRaidTargetIndex", function() return M.combat_secrets ~= false end)
-- (a widget takes a secret: FontString:SetText with a secret string draws it, and its measured width is secret too)
do
  local FS = M.Methods.FontString
  local secret_text = setmetatable({}, { __mode = "k" })
  local set, w, uw = FS.SetText, FS.GetStringWidth, FS.GetUnboundedStringWidth
  FS.SetText = function(self, v, ...)
    if issecretvalue(v) then secret_text[self] = true; return set(self, "?", ...) end
    secret_text[self] = nil
    return set(self, v, ...)
  end
  FS.GetStringWidth = function(self)
    if secret_text[self] then return M.secret(w(self)) end
    return w(self)
  end
  if uw then
    FS.GetUnboundedStringWidth = function(self)
      if secret_text[self] then return M.secret(uw(self)) end
      return uw(self)
    end
  end
end
