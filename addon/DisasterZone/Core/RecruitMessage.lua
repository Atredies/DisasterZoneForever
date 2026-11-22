if DisasterZoneBoot and DisasterZoneBoot.Run("Core/RecruitMessage.lua", ...) then return end -- DisasterZone: Core/RecruitMessage.lua
-- Recruitment > Message (1.6): the guild's recruitment message, built by the officers from parts (like the LFG
-- message), and where it goes.
--   Parts, in their order, each on or off: the officers' own words, and helpers that only fill in facts: the guild's
--   name, the classes a team's comp still needs (one team or every team; as specs, short names or classes; any of them
--   left out),
--   a team's raid nights, a raid icon ({rt1}: Say and Yell draw it; channels get the message without icons). Nothing is written for them: the message starts empty. The parts are joined with a space
--   (or " - ", ", ", " / "); one chat line, 255 bytes at most.
--   Places: Say, Yell, or a chat channel by name (Trade, LookingForGroup, GuildRecruitment, General, LocalDefense, or
--   any channel I'm in), each with its own interval (30 seconds to 12 hours) and an optional "major cities only" tick.
-- Posting needs a click or a key (the game sends to channels, Say and Yell only inside a hardware event): Post now
-- sends it to every place that's on (and allowed where I stand); with Reminders on, a place that is due (its interval
-- since the last post there, by any officer) brings a toast whose click posts to every place that is due; the bound
-- key (Key Bindings > AddOns) does the same. Posts are told to the recruiters online (RCP, with the place), so
-- officers take turns per place instead of posting twice.
-- Saved (per guild): db.recruitMsg[guildKey] = { v = 3, parts = { { id, k = "text" | "tag" | "need" | "nights" |
-- "icon", t, team, by = "spec" | "short" | "class", m (an icon part's raid icon 1..8), skip = { [entry] = true }, off },
-- ... }, nid, sep, rep, places = { { id, kind = "SAY" | "YELL" | "CHANNEL", name, every = seconds, u = "s" | "m", on,
-- city }, ... }, posts = { [place id] = { at, ... } } }.
-- Saved messages (1.5.5, feedback #51): msgs = { { id, name, parts, sep }, ... } in the order made, cur = the id in
-- use. The one in use keeps its parts and separator at the top (parts, sep: everything above works on those); the
-- others hold their own (parts, sep) until they're put in use. Places and posts belong to the guild, not a message.
-- 0.2.6: each place sends its own message (place.msg = a message id; nil = the one in use). An icon part has a text
-- marker (tx: ">>", "~*~" ...) sent where the game doesn't draw icons: chat channels, and every chat on WoW Forever.
-- The messages and places are shared by the recruiters (the GM, the officers, the raid leaders the rules allow):
-- rev / by on the store; RCM { v, by, d = the messages and places } to the recruiters online on a change, RCMQ { v }
-- at login (whoever has newer answers with RCM; newer rev wins, the same rev keeps the larger by). Posts (RCP) and
-- the reminders switch stay as they were. Someone who whispers a recruiter within 2 hours of a recruitment post is
-- added to Recruitment (Talking, "Whispers", their first words kept).
local addonName, ns = ...

local Msg = ns:NewModule("RecruitMessage")
local Util = ns.Util

local floor, max, min = math.floor, math.max, math.min
local tconcat, tsort = table.concat, table.sort

local MAX_LEN = 255
local MAX_PLACES = 12
local MAX_PARTS = 24
local MAX_WORDS = 200
local MAX_MESSAGES, MAX_NAME = 8, 24
local MIN_EVERY, MAX_EVERY = 30, 12 * 3600   -- seconds
local DAY = 86400
Msg.MAX_LEN = MAX_LEN
Msg.MAX_PARTS = MAX_PARTS
Msg.MAX_MESSAGES, Msg.MAX_NAME = MAX_MESSAGES, MAX_NAME
Msg.MIN_EVERY, Msg.MAX_EVERY = MIN_EVERY, MAX_EVERY

-- What joins the parts.
Msg.SEPS = { { key = " ", label = "Space" }, { key = " - ", label = "-" }, { key = ", ", label = "," },
             { key = " / ", label = "/" } }
local SEP_OK = {}
for _, s in ipairs(Msg.SEPS) do SEP_OK[s.key] = true end

-- The kinds of parts, for the "+ Add" menu and the chips.
Msg.KINDS = {
    text = { label = "Your words", tip = "Anything you want to say, in your own words." },
    tag = { label = "Guild name", tip = "The guild's name in < >." },
    need = { label = "Classes we need", tip = "What a team's comp still has open: specs or classes, filled in as the "
        .. "comp changes. Leave any of them out." },
    nights = { label = "Raid nights", tip = "A team's raid nights and their start time, e.g. Thu + Sun 19:30." },
    icon = { label = "Raid icon", tip = "A raid target icon (star, skull...). Shown in Say and Yell; left out in Trade "
        .. "and other channels, where the game doesn't draw icons." },
}

-- The raid target icons, as chat writes them: {rt1} .. {rt8} (5 bytes, any client language; {star} etc. work too).
Msg.ICONS = { { m = 1, name = "Star" }, { m = 2, name = "Circle" }, { m = 3, name = "Diamond" },
              { m = 4, name = "Triangle" }, { m = 5, name = "Moon" }, { m = 6, name = "Square" },
              { m = 7, name = "Cross" }, { m = 8, name = "Skull" } }
local ICON_BY_NAME = { x = 7, rt1 = 1, rt2 = 2, rt3 = 3, rt4 = 4, rt5 = 5, rt6 = 6, rt7 = 7, rt8 = 8 }
for _, i in ipairs(Msg.ICONS) do ICON_BY_NAME[i.name:lower()] = i.m end

-- What an icon part sends where icons aren't drawn (a plain-text marker the officers pick; "|" can't be sent).
Msg.MARKERS = { ">>", "<<", "~*~", "**", "<>", "::", "=>", "<=", "-=", "=-" }
Msg.DEFAULT_MARKER = ">>"
local MARKER_OK = {}
for _, m in ipairs(Msg.MARKERS) do MARKER_OK[m] = true end
-- WoW Forever draws no raid icons in chat at all (the server's arg17 also in Say and Yell, owner 2026-11-15).
local NO_ICONS_ANYWHERE = (ns.Compat and ns.Compat.isForever) and true or false
Msg.NO_ICONS_ANYWHERE = NO_ICONS_ANYWHERE

function Msg:IconTexture(m) return "Interface\\TargetingFrame\\UI-RaidTargetingIcon_" .. m end
function Msg:IconCode(m) return "{rt" .. m .. "}" end

-- The text as chat shows it: the icon codes ({rt1}, {star}, ...) drawn as the icons (size: the icons' height).
function Msg:Render(text, size)
    if not text then return text end
    size = size or 14
    return (text:gsub("{([%w]+)}", function(word)
        local m = ICON_BY_NAME[word:lower()]
        return m and ("|T" .. self:IconTexture(m) .. ":" .. size .. ":" .. size .. "|t") or nil
    end))
end

-- The places offered in "Add a place" (custom channels I'm in are added to the menu as they are).
Msg.SUGGESTED = {
    { kind = "CHANNEL", name = "Trade" }, { kind = "CHANNEL", name = "LookingForGroup" },
    { kind = "CHANNEL", name = "GuildRecruitment" }, { kind = "CHANNEL", name = "General" },
    { kind = "CHANNEL", name = "LocalDefense" }, { kind = "YELL", name = "Yell" }, { kind = "SAY", name = "Say" },
}

-- The capitals (uiMapID, and the zone name as a fallback): Stormwind, Ironforge, Darnassus, The Exodar, Orgrimmar,
-- Thunder Bluff, Undercity, Silvermoon, Shattrath.
local CITY_MAPS = { [1453] = true, [1455] = true, [1457] = true, [1947] = true, [1454] = true, [1456] = true,
                    [1458] = true, [1954] = true, [1955] = true }
local CITY_NAMES = { ["Stormwind City"] = true, ["Ironforge"] = true, ["Darnassus"] = true, ["The Exodar"] = true,
                     ["Orgrimmar"] = true, ["Thunder Bluff"] = true, ["Undercity"] = true, ["Silvermoon City"] = true,
                     ["Shattrath City"] = true }

local DAY_SHORT = { "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun" }

-- "Short": the names chat uses, to save the budget (by spec, in ns.SPECS order; a class alone).
Msg.SHORT_SPEC = {
    WARRIOR = { "Arms War", "Fury War", "Prot War" }, PALADIN = { "Holy Pala", "Prot Pala", "Ret Pala" },
    HUNTER = { "BM Hunter", "MM Hunter", "Surv Hunter" }, ROGUE = { "Assa Rogue", "Combat Rogue", "Sub Rogue" },
    PRIEST = { "Disc Priest", "Holy Priest", "Shadow Priest" }, SHAMAN = { "Ele Sham", "Enh Sham", "Resto Sham" },
    MAGE = { "Arcane Mage", "Fire Mage", "Frost Mage" }, WARLOCK = { "Affli Lock", "Demo Lock", "Destro Lock" },
    DRUID = { "Boomkin", "Cat Druid", "Bear Druid", "Resto Druid" },
}
Msg.SHORT_CLASS = { WARRIOR = "War", PALADIN = "Pala", HUNTER = "Hunter", ROGUE = "Rogue", PRIEST = "Priest",
                    SHAMAN = "Sham", MAGE = "Mage", WARLOCK = "Lock", DRUID = "Druid" }

local function R() return ns.Recruit end
local Now = Util.Now

local function PlaceId(kind, name) return kind == "CHANNEL" and ("ch:" .. tostring(name):lower()) or kind:lower() end

local function DefaultPlaces()
    return { { id = "ch:trade", kind = "CHANNEL", name = "Trade", every = 3600, u = "m", on = true, city = true },
             { id = "ch:guildrecruitment", kind = "CHANNEL", name = "GuildRecruitment", every = 3600, u = "m", on = false,
               city = true } }   -- (off at first: a character in a guild isn't put in GuildRecruitment by the game)
end

local function Words(s)
    s = tostring(s or ""):gsub("[\r\n]+", " "):gsub("[%c|]", "")
    return s:sub(1, MAX_WORDS)
end

local demoStore
local function DemoStore()
    local now = Now()
    return { v = 3, nid = 8, sep = " ",
        parts = { { id = 8, k = "icon", m = 8 }, { id = 1, k = "tag" }, { id = 2, k = "text", t = "chill guild for new, returning and raiding players." },
                  { id = 3, k = "text", t = (ns.Compat and ns.Compat.isForever) and "Hyjal/Barrow on" or "SSC/TK on" }, { id = 4, k = "nights", team = "demo-main" },
                  { id = 5, k = "text", t = "- looking for" }, { id = 6, k = "need", team = "demo-main", by = "spec" },
                  { id = 7, k = "text", t = "/w me for a chat!" } },
        cur = 1, mid = 3,
        msgs = { { id = 1, name = (ns.Compat and ns.Compat.isForever) and "Raiders for Hyjal/Barrow" or "Raiders for SSC/TK" },
                 { id = 2, name = "Levellers welcome", sep = " ",
                   parts = { { id = 9, k = "tag" }, { id = 10, k = "text", t = "is a friendly guild for levellers and returning players." },
                             { id = 11, k = "text", t = "Dungeon groups most nights, help with quests. /w me!" } } },
                 { id = 3, name = "Weekend pugs", sep = " - ",
                   parts = { { id = 12, k = "icon", m = 1 }, { id = 13, k = "text", t = (ns.Compat and ns.Compat.isForever) and "Onyxia pug Sunday" or "Karazhan pug Sunday" },
                             { id = 14, k = "nights", team = "demo-main" }, { id = 15, k = "text", t = "/w for a spot" } } } },
        places = { { id = "ch:trade", kind = "CHANNEL", name = "Trade", every = 3600, u = "m", on = true, city = true },
                   { id = "ch:guildrecruitment", kind = "CHANNEL", name = "GuildRecruitment", every = 1800, u = "m",
                     on = true, city = true },
                   { id = "yell", kind = "YELL", name = "Yell", every = 90, u = "s", on = false, city = true } },
        posts = { ["ch:trade"] = { now - 2400, now - 2 * DAY - 1800 }, ["ch:guildrecruitment"] = { now - 4 * DAY - 600 } } }
end

local function DB()
    local d
    if Util.DemoOn() then
        demoStore = demoStore or DemoStore()
        d = demoStore
    else
        d = ns.DB:GuildBucket("recruitMsg", true) or {}
    end
    if d.v == 2 then                       -- (1.6 beta: one text, minutes) -> parts, seconds
        local text = Util.Trim(Words(d.text)) or ""
        d.parts = text ~= "" and { { id = 1, k = "text", t = text } } or {}
        d.nid = #d.parts
        d.text = nil
        for _, p in ipairs(type(d.places) == "table" and d.places or {}) do
            p.every, p.u = (tonumber(p.every) or 60) * 60, "m"
        end
        d.v = 3
    elseif d.v ~= 3 then                   -- (the first, block-built message: started over)
        for k in pairs(d) do d[k] = nil end
        d.v = 3
    end
    if type(d.parts) ~= "table" then d.parts = {} end
    if type(d.nid) ~= "number" then d.nid = 0 end
    if not SEP_OK[d.sep] then d.sep = " " end
    if type(d.places) ~= "table" then d.places = DefaultPlaces() end
    if type(d.posts) ~= "table" then d.posts = {} end
    -- (saved messages: the one there was before is the first)
    if type(d.msgs) ~= "table" or #d.msgs == 0 then d.msgs, d.cur, d.mid = { { id = 1, name = "Message 1" } }, 1, 1 end
    if type(d.mid) ~= "number" then d.mid = #d.msgs end
    local found = false
    for _, m in ipairs(d.msgs) do if m.id == d.cur then found = true end end
    if not found then d.cur = d.msgs[1].id; d.msgs[1].parts, d.msgs[1].sep = nil, nil end
    return d
end

-- A change to what the recruiters share (messages, places): a new rev, sent to the recruiters online (soon, once).
local function Changed()
    if not Util.DemoOn() then
        local d = DB()
        d.rev = max((tonumber(d.rev) or 0) + 1, Now())
        d.by = Util.PlayerKey()
        if Msg.ScheduleShare then Msg:ScheduleShare() end
    end
    ns:Fire("RECRUIT_MSG_CHANGED")
end

---------------------------------------------------------------------------
-- Saved messages (feedback #51): several, one in use
---------------------------------------------------------------------------

local function Named(s)
    s = Util.Trim(Words(s)) or ""
    if #s > MAX_NAME then s = s:sub(1, MAX_NAME) end
    return s ~= "" and s or nil
end

local function FindMsg(d, id)
    for i, m in ipairs(d.msgs) do if m.id == id then return m, i end end
end

-- The saved messages in their order: { { id, name, cur (in use), n (parts), text (what it says now) }, ... }.
function Msg:GetMessages()
    local d = DB()
    local out = {}
    for _, m in ipairs(d.msgs) do
        local cur = m.id == d.cur
        local parts = cur and d.parts or m.parts or {}
        local bits = {}
        for _, p in ipairs(parts) do
            if not p.off then
                local t = self:PartText(p)
                if t and t ~= "" then bits[#bits + 1] = t end
            end
        end
        out[#out + 1] = { id = m.id, name = m.name, cur = cur, n = #parts,
                          text = tconcat(bits, (cur and d.sep) or m.sep or " ") }
    end
    return out
end

-- The message in use: id, name.
function Msg:Current()
    local d = DB()
    local m = FindMsg(d, d.cur)
    return d.cur, m and m.name or ""
end

-- Puts another saved message in use (the one in use keeps what it has). Returns ok.
function Msg:Use(id)
    local d = DB()
    local to = FindMsg(d, id)
    if not to then return false end
    if id == d.cur then return true end
    local from = FindMsg(d, d.cur)
    if from then from.parts, from.sep = d.parts, d.sep end
    d.parts, d.sep = to.parts or {}, SEP_OK[to.sep] and to.sep or " "
    to.parts, to.sep = nil, nil
    d.cur = id
    ns:Fire("RECRUIT_MSG_CHANGED")
    return true
end

-- A new message (copy: starting from the one in use, else empty), put in use. Returns ok, id | why.
function Msg:NewMessage(name, copy)
    local d = DB()
    if #d.msgs >= MAX_MESSAGES then return false, "that's " .. MAX_MESSAGES .. " messages: delete one first" end
    name = Named(name)
    if not name then return false, "give it a name" end
    d.mid = d.mid + 1
    local m = { id = d.mid, name = name, sep = copy and d.sep or " ", parts = {} }
    if copy then
        for _, p in ipairs(d.parts) do
            local q = Util.CopyTable(p)
            d.nid = d.nid + 1
            q.id = d.nid
            m.parts[#m.parts + 1] = q
        end
    end
    d.msgs[#d.msgs + 1] = m
    self:Use(m.id)
    Changed()
    return true, m.id
end

function Msg:RenameMessage(id, name)
    local m = FindMsg(DB(), id)
    name = Named(name)
    if not m then return false, "no such message" end
    if not name then return false, "give it a name" end
    m.name = name
    Changed()
    return true
end

-- Deletes a saved message (never the last one); deleting the one in use puts the next in use.
function Msg:DeleteMessage(id)
    local d = DB()
    local m, i = FindMsg(d, id)
    if not m then return false, "no such message" end
    if #d.msgs <= 1 then return false, "it's the only message" end
    if id == d.cur then
        local next = d.msgs[i + 1] or d.msgs[i - 1]
        self:Use(next.id)
    end
    table.remove(d.msgs, (select(2, FindMsg(d, id))))
    for _, p in ipairs(d.places) do if p.msg == id then p.msg = nil end end
    Changed()
    return true
end

---------------------------------------------------------------------------
-- The helpers' facts
---------------------------------------------------------------------------

local function HM(w)
    local m = floor(w) % 1440
    return ("%d:%02d"):format(floor(m / 60), m % 60)
end

-- A team's nights: "Thu + Sun 19:30" (one start time), "Thu 19:30 + Sun 20:00" (more); nil without nights.
function Msg:NightsText(team)
    local list = {}
    for _, n in ipairs(team and team.nights or {}) do
        local w = tonumber(n.w)
        if w and w >= 0 and w < 7 * 1440 then list[#list + 1] = w end
    end
    if #list == 0 then return nil end
    tsort(list)
    local same = true
    for _, w in ipairs(list) do if HM(w) ~= HM(list[1]) then same = false end end
    local out = {}
    for _, w in ipairs(list) do
        local d = DAY_SHORT[floor(w / 1440) + 1]
        out[#out + 1] = same and d or (d .. " " .. HM(w))
    end
    return tconcat(out, " + ") .. (same and (" " .. HM(list[1])) or "")
end

local function SlotName(o, by)
    if o.c and by == "short" then
        local name = o.sp and Msg.SHORT_SPEC[o.c] and Msg.SHORT_SPEC[o.c][o.sp] or Msg.SHORT_CLASS[o.c] or o.c
        return name, o.c .. ":" .. (o.sp or 0)
    end
    if o.c then
        local cls = ns.ClassName(o.c) or o.c
        local spec = by ~= "class" and o.sp and ns.SPECS[o.c] and ns.SPECS[o.c][o.sp]
        return spec and (spec.label .. " " .. cls) or cls, by == "class" and o.c or (o.c .. ":" .. (o.sp or 0))
    end
    local role = o.role and tostring(o.role) or nil
    if not role then return nil end
    return role:sub(1, 1):upper() .. role:sub(2), "role:" .. role
end

-- The open places of one team ("all": every team, each once): { { key, name, c, sp, skip }, ... } in comp order.
function Msg:NeedList(part)
    local teams = {}
    if part.team == "all" then
        teams = R():GetTeams()
    else
        local t = R():GetTeam(part.team)
        if t then teams[1] = t end
    end
    local out, seen = {}, {}
    local RP = ns.RaidPlan
    for _, team in ipairs(teams) do
        local open = team.demoOpen or (RP and RP.GetTeamOpenSlots and (RP:GetTeamOpenSlots(team))) or {}
        for _, o in ipairs(open) do
            local name, key = SlotName(o, part.by)
            if name and not seen[key] then
                seen[key] = true
                out[#out + 1] = { key = key, name = name, c = o.c, sp = o.sp,
                                  skip = (part.skip and part.skip[key]) and true or false }
            end
        end
    end
    return out
end

local function GuildName()
    if Util.DemoOn() then return "Casual Disaster" end
    local name = GetGuildInfo and GetGuildInfo("player")
    return name
end

-- What one part says now (nil: nothing, e.g. a team without nights or without open places). plain: where icons aren't
-- drawn (an icon part says its text marker).
function Msg:PartText(p, plain)
    if p.k == "text" then
        local t = Util.Trim(p.t or "")
        return (t and t ~= "") and t or nil
    elseif p.k == "tag" then
        local g = GuildName()
        return g and ("<" .. g .. ">") or nil
    elseif p.k == "icon" then
        if plain then return MARKER_OK[p.tx] and p.tx or Msg.DEFAULT_MARKER end
        return self:IconCode(p.m or 1)
    elseif p.k == "nights" then
        return self:NightsText(R():GetTeam(p.team))
    elseif p.k == "need" then
        local names = {}
        for _, e in ipairs(self:NeedList(p)) do if not e.skip then names[#names + 1] = e.name end end
        return #names > 0 and tconcat(names, ", ") or nil
    end
end

-- The team a part is about, by name ("every team" / nil).
function Msg:PartTeamName(p)
    if p.team == "all" then return "every team" end
    local t = p.team and R():GetTeam(p.team)
    return t and t.name or nil
end

---------------------------------------------------------------------------
-- The parts
---------------------------------------------------------------------------

-- The parts in their order (copies, with label and what they say now).
function Msg:GetParts()
    local out = {}
    for _, p in ipairs(DB().parts) do
        local skip = {}
        for k in pairs(p.skip or {}) do skip[k] = true end
        out[#out + 1] = { id = p.id, k = p.k, t = p.t, m = p.m, tx = MARKER_OK[p.tx] and p.tx or Msg.DEFAULT_MARKER,
                          team = p.team, by = p.by or "spec", skip = skip,
                          on = not p.off, label = Msg.KINDS[p.k] and Msg.KINDS[p.k].label or p.k,
                          teamName = self:PartTeamName(p), text = self:PartText(p) }
    end
    return out
end

function Msg:GetPart(id)
    for i, p in ipairs(DB().parts) do if p.id == id then return p, i end end
end

-- Adds a part (kind: "text" | "tag" | "need" | "nights" | "icon"; opts: t, team, by, m (icon 1..8), after (a part's
-- id: put it right after that one)). Returns ok, id | why.
function Msg:AddPart(kind, opts)
    if not Msg.KINDS[kind] then return false, "not a part" end
    local d = DB()
    if #d.parts >= MAX_PARTS then return false, "that's enough parts" end
    opts = opts or {}
    local p = { k = kind }
    if kind == "text" then p.t = Words(opts.t)
    elseif kind == "icon" then
        p.m = Util.IsInt(opts.m, 1, 8) and opts.m or 1
        p.tx = MARKER_OK[opts.tx] and opts.tx or nil
    elseif kind == "need" or kind == "nights" then
        local team = opts.team
        if kind == "need" and team == "all" then p.team = "all"
        elseif team and R():GetTeam(team) then p.team = team
        else
            local first = R():GetTeams()[1]
            if not first then return false, "no team yet: make one in Raids > Teams" end
            p.team = first.id
        end
        if kind == "need" then p.by = (opts.by == "class" or opts.by == "short") and opts.by or "spec" end
    end
    d.nid = d.nid + 1
    p.id = d.nid
    local at
    if opts.after then at = select(2, self:GetPart(opts.after)) end
    table.insert(d.parts, at and (at + 1) or (#d.parts + 1), p)
    Changed()
    return true, p.id
end

-- Changes a part: t (words), m (an icon's 1..8), tx (an icon's text marker, Msg.MARKERS), team, by, on, skip = entry
-- (switches that entry).
function Msg:SetPart(id, f)
    local p = self:GetPart(id)
    if not p then return false end
    if f.t ~= nil and p.k == "text" then p.t = Words(f.t) end
    if f.m ~= nil and p.k == "icon" and Util.IsInt(f.m, 1, 8) then p.m = f.m end
    if f.tx ~= nil and p.k == "icon" and MARKER_OK[f.tx] then p.tx = f.tx ~= Msg.DEFAULT_MARKER and f.tx or nil end
    if f.team ~= nil and (p.k == "need" or p.k == "nights") then
        if (f.team == "all" and p.k == "need") or R():GetTeam(f.team) then
            if p.team ~= f.team then p.skip = nil end
            p.team = f.team
        end
    end
    if f.by ~= nil and p.k == "need" then
        local by = (f.by == "class" or f.by == "short") and f.by or "spec"
        if (by == "class") ~= (p.by == "class") then p.skip = nil end      -- (specs and short share what's left out)
        p.by = by
    end
    if f.on ~= nil then p.off = (not f.on) or nil end
    if f.skip ~= nil and p.k == "need" then
        p.skip = p.skip or {}
        p.skip[f.skip] = (not p.skip[f.skip]) or nil
        if not next(p.skip) then p.skip = nil end
    end
    Changed()
    return true
end

function Msg:RemovePart(id)
    local _, i = self:GetPart(id)
    if not i then return false end
    table.remove(DB().parts, i)
    Changed()
    return true
end

-- Moves a part to position `to` (1 = first).
function Msg:MovePart(id, to)
    local d = DB()
    local p, i = self:GetPart(id)
    if not p then return false end
    table.remove(d.parts, i)
    to = max(1, min(#d.parts + 1, floor(tonumber(to) or i)))
    table.insert(d.parts, to, p)
    Changed()
    return true
end

function Msg:GetSep() return DB().sep end
function Msg:SetSep(sep)
    if not SEP_OK[sep] then return false end
    DB().sep = sep
    Changed()
    return true
end

-- The text without its raid icon codes ({rt1}, {star}, ...; unknown {words} stay), spaces tidied; nil when empty.
local function NoIcons(text)
    text = text:gsub("{([%w]+)}", function(word) if ICON_BY_NAME[word:lower()] then return "" end end)
    return Util.Trim((text:gsub("  +", " "))) or nil
end

-- The parts and separator of a saved message (nil or the one in use: the parts being edited).
local function PartsOf(d, msgId)
    if msgId == nil or msgId == d.cur then return d.parts, d.sep end
    local m = FindMsg(d, msgId)
    if not m then return d.parts, d.sep end
    return m.parts or {}, SEP_OK[m.sep] and m.sep or " "
end

-- The message: text (nil when nothing is said), its length in bytes, too long? noIcons: where the game draws no raid
-- icons (icon parts say their text marker, codes are taken out of the words): chat channels, where the server tells
-- every client not to draw them (Blizzard's ChatFrameOverrides.lua, CHAT_MSG arg17), and all chat on Forever. msgId:
-- a saved message (nil: the one in use).
function Msg:Compose(noIcons, msgId)
    local parts, sep = PartsOf(DB(), msgId)
    local bits = {}
    for _, p in ipairs(parts) do
        if not p.off then
            local t = self:PartText(p, noIcons)
            if t and noIcons and p.k ~= "icon" then t = NoIcons(t) end
            if t and t ~= "" then bits[#bits + 1] = t end
        end
    end
    if #bits == 0 then return nil, 0, false end
    local text = tconcat(bits, sep)
    return text, #text, #text > MAX_LEN
end

---------------------------------------------------------------------------
-- Places
---------------------------------------------------------------------------

-- The places, in their order (copies).
function Msg:GetPlaces()
    local out = {}
    for _, p in ipairs(DB().places) do
        local m = p.msg and FindMsg(DB(), p.msg)
        out[#out + 1] = { id = p.id, kind = p.kind, name = p.name, every = p.every, u = p.u or "m",
                          on = p.on and true or false, city = p.city and true or false,
                          msg = m and p.msg or nil, msgName = m and m.name or nil }
    end
    return out
end

function Msg:GetPlace(id)
    for _, p in ipairs(DB().places) do if p.id == id then return p end end
end

-- Seconds, kept between 30 seconds and 12 hours.
function Msg:CleanEvery(v)
    v = floor(tonumber(v) or 3600)
    return min(MAX_EVERY, max(MIN_EVERY, v))
end

-- Adds a place (kind "SAY" | "YELL" | "CHANNEL" and a channel's name; every in seconds). Returns ok, err / id.
function Msg:AddPlace(kind, name, every)
    if kind ~= "SAY" and kind ~= "YELL" and kind ~= "CHANNEL" then return false, "not a place" end
    if kind == "CHANNEL" then
        name = Util.Trim((tostring(name or ""):gsub("[%c|]", ""))) or ""
        if name == "" or #name > 32 then return false, "a channel needs a name" end
    else
        name = kind == "YELL" and "Yell" or "Say"
    end
    local d = DB()
    local id = PlaceId(kind, name)
    if self:GetPlace(id) then return false, "already in the list" end
    if #d.places >= MAX_PLACES then return false, "that's enough places" end
    local lower = name:lower()
    every = self:CleanEvery(every or 3600)
    d.places[#d.places + 1] = { id = id, kind = kind, name = name, every = every, u = every % 60 == 0 and "m" or "s",
                                on = true, city = kind ~= "CHANNEL" or lower == "trade" or lower == "guildrecruitment" }
    Changed()
    return true, id
end

function Msg:RemovePlace(id)
    local d = DB()
    for i, p in ipairs(d.places) do
        if p.id == id then
            table.remove(d.places, i)
            Changed()
            return true
        end
    end
    return false
end

-- Changes a place: fields on, city, every (seconds), u (the unit it's shown in: "s" | "m"), msg (the saved message
-- it sends: an id, or false = the one in use).
function Msg:SetPlace(id, f)
    local p = self:GetPlace(id)
    if not p then return false end
    if f.on ~= nil then p.on = f.on and true or false end
    if f.city ~= nil then p.city = f.city and true or false end
    if f.every ~= nil then p.every = self:CleanEvery(f.every) end
    if f.u == "s" or f.u == "m" then p.u = f.u end
    if f.msg == false then p.msg = nil
    elseif f.msg ~= nil then
        if not FindMsg(DB(), f.msg) then return false end
        p.msg = f.msg
    end
    Changed()
    return true
end

-- The channels I'm in now (for "Add a place"): their names, without the numbers.
function Msg:JoinedChannels()
    local out = {}
    if not GetChannelList then return out end
    local list = { GetChannelList() }
    for i = 1, #list, 3 do
        local name = list[i + 1]
        if type(name) == "string" and name ~= "" then out[#out + 1] = (name:gsub(" %- .*$", "")) end
    end
    return out
end

function Msg:InMajorCity()
    if Util.DemoOn() then return true end
    local map = C_Map and C_Map.GetBestMapForUnit and C_Map.GetBestMapForUnit("player")
    if map and CITY_MAPS[map] then return true end
    local z = GetRealZoneText and GetRealZoneText()
    return (z and CITY_NAMES[z]) and true or false
end

-- Why I can't post there now ("only in major cities", "you're not in it, type /join <channel>"), or nil.
function Msg:Blocker(p)
    if p.city and not self:InMajorCity() then return "only in major cities" end
    if p.kind == "CHANNEL" and not Util.DemoOn() then
        local id = GetChannelName and tonumber((GetChannelName(p.name)))
        if not (id and id > 0) then return "you're not in it, type /join " .. p.name end
    end
    return nil
end

---------------------------------------------------------------------------
-- Posting, turns, reminders
---------------------------------------------------------------------------

function Msg:LastPost(id)
    local best
    for _, at in ipairs(DB().posts[id] or {}) do if not best or at > best then best = at end end
    return best
end

function Msg:NextDue(id)
    local p = self:GetPlace(id)
    if not p then return nil end
    local last = self:LastPost(id)
    return last and (last + p.every) or Now()
end

function Msg:Record(id, at)
    local d = DB()
    local list = d.posts[id] or {}
    list[#list + 1] = at
    tsort(list, function(a, b) return a > b end)
    for i = #list, 1, -1 do
        if i > 60 or list[i] < Now() - 14 * DAY then table.remove(list, i) end
    end
    d.posts[id] = list
    ns:Fire("RECRUIT_MSG_CHANGED")
end

-- The places that are on, due now and allowed where I stand (ids).
function Msg:DuePlaces()
    local out = {}
    for _, p in ipairs(DB().places) do
        if p.on and Now() >= (self:NextDue(p.id) or 0) and not self:Blocker(p) then out[#out + 1] = p.id end
    end
    return out
end

-- The next place to come due (that is on): its place and when; nil when none is on.
function Msg:NextUp()
    local best, at
    for _, p in ipairs(DB().places) do
        if p.on then
            local due = self:NextDue(p.id)
            if not at or due < at then best, at = p, due end
        end
    end
    return best, at
end

-- What a place gets: its message, with text markers for the icons in channels (see Compose) and everywhere on
-- Forever; Say and Yell elsewhere draw the icons. Returns the text, too long?
function Msg:TextFor(p)
    local text, _, long = self:Compose(NO_ICONS_ANYWHERE or p.kind == "CHANNEL", p.msg)
    return text, long
end

local function SendTo(p, text)
    if not text then return end
    if p.kind == "CHANNEL" then
        local id = GetChannelName and tonumber((GetChannelName(p.name)))
        if id and id > 0 then SendChatMessage(text, "CHANNEL", nil, id) end
        return
    end
    SendChatMessage(text, p.kind)
end

-- Posts (from a click or a key) to the places given (ids), or to every place that is on. Returns ok, why | the places'
-- names, the ones skipped ("Trade: only in major cities").
function Msg:Post(ids)
    if not (R() and R():CanUse()) then return false, "only the Guild Master and officers post it" end
    local want = {}
    for _, id in ipairs(ids or {}) do want[id] = true end
    local sent, skipped = {}, {}
    for _, p in ipairs(DB().places) do
        if (ids and want[p.id]) or (not ids and p.on) then
            local why = self:Blocker(p)
            local out, long
            if not why then out, long = self:TextFor(p) end
            if not why and not out then why = "its message is empty" end
            if not why and long then why = "its message is longer than 255: shorten it" end
            if why then
                skipped[#skipped + 1] = p.name .. ": " .. why
            else
                if Util.DemoOn() then ns:Print("Demo mode, not sent to %s: %s", p.name, out) else SendTo(p, out) end
                sent[#sent + 1] = p
            end
        end
    end
    if #sent == 0 then return false, #skipped > 0 and tconcat(skipped, "; ") or "No place is on." end
    local at = Now()
    local names = {}
    for _, p in ipairs(sent) do
        self:Record(p.id, at)
        names[#names + 1] = p.name
    end
    self.ready, self.readyKey = nil, nil
    if not Util.DemoOn() then
        local G = ns.Guild
        for _, k in ipairs(G and G.GetOnlineMembers and G:GetOnlineMembers() or {}) do
            if not Util.IsMe(k) and R():IsRecruiter(k) then
                for _, p in ipairs(sent) do ns.Comm:Send({ t = "RCP", at = at, p = p.id }, "WHISPER", k, "data") end
            end
        end
    end
    ns:Fire("RECRUIT_MSG_POSTED")
    return true, names, skipped
end

-- The key binding's post: the places that are due; with the reminders off, every place that is on. Returns as Post,
-- or false, "nothing is due ..." while the reminders are on and nothing is due.
function Msg:PostByKey()
    if not (R() and R():CanUse()) then return false, "only the Guild Master and officers post it" end
    if not self:IsRepeating() then return self:Post() end
    local due = self:Ready() or self:DuePlaces()
    if #due == 0 then
        local p, at = self:NextUp()
        if not p then return false, "No place is on." end
        return false, ("Nothing is due yet: %s in %d s."):format(p.name, max(1, at - Now()))
    end
    return self:Post(due)
end

function Msg:IsRepeating() return DB().rep == true end
function Msg:SetRepeat(on)
    DB().rep = on and true or nil
    self.ready, self.readyKey = nil, nil
    ns:Fire("RECRUIT_MSG_CHANGED")
end
-- The places waiting for a click (the toast's), or nil.
function Msg:Ready() return self.ready end

local function OnPost(sender, msg, dist)
    if dist ~= "WHISPER" or not (R() and R():IsRecruiter(sender) and R():CanUse()) then return end
    local at = tonumber(msg.at)
    if not Util.IsInt(at, Now() - DAY, Now() + 60) or type(msg.p) ~= "string" or #msg.p > 40 then return end
    Msg:Record(msg.p, at)
end

local function Tick()
    if not Msg:IsRepeating() or not (R() and R():CanUse()) then return end
    local due = Msg:DuePlaces()
    if #due == 0 then
        Msg.ready, Msg.readyKey = nil, nil
        return
    end
    local key = tconcat(due, ",")
    if Msg.readyKey ~= key then
        Msg.ready, Msg.readyKey = due, key
        ns:Fire("RECRUIT_MSG_READY", due)
    end
end

-- Lately: posts this week (every place), and the people who whispered within 2 hours of a post.
function Msg:Lately()
    local all = {}
    for _, list in pairs(DB().posts) do for _, at in ipairs(list) do all[#all + 1] = at end end
    tsort(all, function(a, b) return a > b end)
    local week = 0
    for _, at in ipairs(all) do if at >= Now() - 7 * DAY then week = week + 1 end end
    local came, joined = {}, 0
    for _, r in ipairs(R():GetPeople()) do
        if (r.src == "whisper" or r.src == "trade") and r.at then
            for _, at in ipairs(all) do
                if r.at >= at and r.at <= at + 7200 then
                    came[#came + 1] = r
                    if r.st == "joined" or r.st == "gone" then joined = joined + 1 end
                    break
                end
            end
        end
    end
    tsort(came, function(a, b) return a.at > b.at end)
    return { week = week, last = all[1], came = came, joined = joined }
end

---------------------------------------------------------------------------
-- Shared by the recruiters (0.2.6): the messages and the places
---------------------------------------------------------------------------

local SHARE_DELAY, LOGIN_ASK = 2, 35        -- seconds: a burst of edits goes out once; the login ask waits for the roster
local PART_KINDS = { text = true, tag = true, need = true, nights = true, icon = true }
local NEED_BY = { spec = true, short = true, class = true }

local function CleanPart(p)
    if type(p) ~= "table" or not PART_KINDS[p.k] or not Util.IsInt(p.id, 1, 1e6) then return nil end
    local q = { id = p.id, k = p.k, off = p.off and true or nil }
    if p.k == "text" then q.t = Words(p.t)
    elseif p.k == "icon" then
        q.m = Util.IsInt(p.m, 1, 8) and p.m or 1
        q.tx = MARKER_OK[p.tx] and p.tx or nil
    elseif p.k == "need" or p.k == "nights" then
        if type(p.team) ~= "string" or #p.team > 40 then return nil end
        q.team = p.team
        if p.k == "need" then
            q.by = NEED_BY[p.by] and p.by or "spec"
            if type(p.skip) == "table" then
                local n = 0
                for k, v in pairs(p.skip) do
                    if type(k) == "string" and #k <= 40 and v == true and n < 40 then
                        q.skip = q.skip or {}
                        q.skip[k], n = true, n + 1
                    end
                end
            end
        end
    end
    return q
end

local function CleanParts(list)
    local out = {}
    for _, p in ipairs(type(list) == "table" and list or {}) do
        local q = #out < MAX_PARTS and CleanPart(p)
        if q then out[#out + 1] = q end
    end
    return out
end

-- What the recruiters share, from my store: { msgs = { { id, name, sep, parts } ... }, places, mid, nid } (the one in
-- use with the parts being edited).
local function ShareDoc(d)
    local msgs = {}
    for _, m in ipairs(d.msgs) do
        local parts, sep = PartsOf(d, m.id)
        msgs[#msgs + 1] = { id = m.id, name = m.name, sep = sep, parts = parts }
    end
    local places = {}
    for _, p in ipairs(d.places) do
        places[#places + 1] = { id = p.id, kind = p.kind, name = p.name, every = p.every, u = p.u, on = p.on,
                                city = p.city, msg = p.msg }
    end
    return { msgs = msgs, places = places, mid = d.mid, nid = d.nid }
end

-- A shared doc made safe (nil: unusable).
local function CleanDoc(doc)
    if type(doc) ~= "table" or type(doc.msgs) ~= "table" or type(doc.places) ~= "table" then return nil end
    local out = { msgs = {}, places = {}, mid = 0, nid = 0 }
    local ids = {}
    for _, m in ipairs(doc.msgs) do
        if type(m) == "table" and Util.IsInt(m.id, 1, 1e6) and not ids[m.id] and #out.msgs < MAX_MESSAGES then
            local name = Named(m.name)
            if name then
                ids[m.id] = true
                local parts = CleanParts(m.parts)
                for _, q in ipairs(parts) do out.nid = max(out.nid, q.id) end
                out.msgs[#out.msgs + 1] = { id = m.id, name = name, sep = SEP_OK[m.sep] and m.sep or " ", parts = parts }
                out.mid = max(out.mid, m.id)
            end
        end
    end
    if #out.msgs == 0 then return nil end
    local seen = {}
    for _, p in ipairs(doc.places) do
        if type(p) == "table" and (p.kind == "SAY" or p.kind == "YELL" or p.kind == "CHANNEL") and #out.places < MAX_PLACES then
            local name = p.kind == "CHANNEL" and Util.Trim((tostring(p.name or ""):gsub("[%c|]", ""))) or
                (p.kind == "YELL" and "Yell" or "Say")
            local id = name and name ~= "" and #name <= 32 and PlaceId(p.kind, name)
            if id and not seen[id] then
                seen[id] = true
                out.places[#out.places + 1] = { id = id, kind = p.kind, name = name, every = Msg:CleanEvery(p.every),
                    u = p.u == "s" and "s" or "m", on = p.on and true or false, city = p.city and true or false,
                    msg = (Util.IsInt(p.msg, 1, 1e6) and ids[p.msg]) and p.msg or nil }
            end
        end
    end
    out.mid = max(out.mid, Util.IsInt(doc.mid, 0, 1e6) and doc.mid or 0)
    out.nid = max(out.nid, Util.IsInt(doc.nid, 0, 1e6) and doc.nid or 0)
    return out
end

-- Takes a shared doc into my store (my message in use stays in use when it's still there; posts are mine).
local function ApplyDoc(d, doc, rev, by)
    -- (a store never shared before keeps its own messages that have words: added after the shared ones, room allowing)
    local keep = {}
    if not d.rev then
        for _, m in ipairs(d.msgs) do
            local parts = PartsOf(d, m.id)
            if #parts > 0 then keep[#keep + 1] = { name = m.name, sep = (select(2, PartsOf(d, m.id))), parts = parts } end
        end
    end
    local cur = d.cur
    d.msgs, d.places, d.mid, d.nid = doc.msgs, doc.places, max(d.mid or 0, doc.mid), max(d.nid or 0, doc.nid)
    local mine = false
    for _, k in ipairs(keep) do
        local same = false
        for _, m in ipairs(d.msgs) do
            if Util.Hash(m.parts) == Util.Hash(CleanParts(k.parts)) then same = true end
        end
        if not same and #d.msgs < MAX_MESSAGES then
            d.mid = d.mid + 1
            local parts = CleanParts(k.parts)
            for _, q in ipairs(parts) do d.nid = d.nid + 1; q.id = d.nid end
            d.msgs[#d.msgs + 1] = { id = d.mid, name = Named(k.name .. " (mine)") or k.name, sep = k.sep, parts = parts }
            mine = true
        end
    end
    local found = FindMsg(d, cur) and cur or d.msgs[1].id
    local m = FindMsg(d, found)
    d.cur, d.parts, d.sep = found, m.parts or {}, SEP_OK[m.sep] and m.sep or " "
    m.parts, m.sep = nil, nil
    d.rev, d.by = rev, by
    if mine then Changed() else ns:Fire("RECRUIT_MSG_CHANGED") end
end

-- Am I really a recruiter (not a pretend role from /dz role, which stays on this PC)?
local function RealRecruiter()
    return R() and R():CanUse() and R():IsRecruiter(Util.PlayerKey()) and not Util.DemoOn()
end

local function Recruiters()
    local out = {}
    local G = ns.Guild
    for _, k in ipairs(G and G.GetOnlineMembers and G:GetOnlineMembers() or {}) do
        if not Util.IsMe(k) and R():IsRecruiter(k) then out[#out + 1] = k end
    end
    return out
end

local function SendDoc(to)
    local d = DB()
    if not d.rev then return end
    local msg = { t = "RCM", v = d.rev, by = d.by, d = ShareDoc(d) }
    for _, k in ipairs(to) do ns.Comm:Send(msg, "WHISPER", k, "data") end
end

function Msg:ScheduleShare()
    if self.sharePending or not (ns.Comm and ns.Comm.Send) then return end
    self.sharePending = true
    Util.After(SHARE_DELAY, function()
        Msg.sharePending = nil
        if RealRecruiter() then SendDoc(Recruiters()) end
    end)
end

-- Is (v, by) newer than what I have?
local function Newer(d, v, by)
    local mine = tonumber(d.rev) or 0
    if v ~= mine then return v > mine end
    return tostring(by or "") > tostring(d.by or "")
end

local function OnDoc(sender, msg, dist)
    if dist ~= "WHISPER" or not (RealRecruiter() and R():IsRecruiter(sender)) then return end
    local v = tonumber(msg.v)
    if not Util.IsInt(v, 1, Now() + 86400 * 365) or type(msg.by) ~= "string" or #msg.by > 64 then return end
    local d = DB()
    if not Newer(d, v, msg.by) then return end
    local doc = CleanDoc(msg.d)
    if doc then ApplyDoc(d, doc, v, msg.by) end
end

local function OnAsk(sender, msg, dist)
    if dist ~= "WHISPER" or not (RealRecruiter() and R():IsRecruiter(sender)) then return end
    local d = DB()
    local v = tonumber(msg.v) or 0
    local mine = tonumber(d.rev) or 0
    if mine > v then SendDoc({ sender })
    elseif v > mine and not msg.r then ns.Comm:Send({ t = "RCMQ", v = mine, r = true }, "WHISPER", sender, "data") end
end

-- (login) asks the recruiters online whether anyone has newer messages.
function Msg:AskShared()
    if not RealRecruiter() then return end
    local v = tonumber(DB().rev) or 0
    for _, k in ipairs(Recruiters()) do ns.Comm:Send({ t = "RCMQ", v = v }, "WHISPER", k, "data") end
end

---------------------------------------------------------------------------
-- Whispers after a post: into Recruitment (0.2.6)
---------------------------------------------------------------------------

local WHISPER_WINDOW = 2 * 3600

function Msg:LastAnyPost()
    local best
    for _, list in pairs(DB().posts) do
        for _, at in ipairs(list) do if not best or at > best then best = at end end
    end
    return best
end

-- Is a whisper about the guild? Only those add the sender: a recruiter who runs dungeons gets whispered for groups
-- too ("inv", "can I join?"), and those stay out of Recruitment (owner, 2026-11-16). The words: guild, recruit,
-- apply / application, ginv / g inv / gi, or the guild's name.
local GUILD_WORDS = { "guild", "recruit", "apply", "applica", "ginv", "g inv", "g%-inv", "%f[%a]gi%f[%A]" }
function Msg.IsAboutGuild(text)
    if type(text) ~= "string" then return false end
    local t = " " .. text:lower() .. " "
    for _, w in ipairs(GUILD_WORDS) do
        if t:find(w) then return true end
    end
    local name = GetGuildInfo and GetGuildInfo("player")
    if type(name) == "string" and name ~= "" and t:find(name:lower(), 1, true) then return true end
    return false
end

-- A whisper to me about the guild (IsAboutGuild): someone outside the guild, within 2 hours of a recruitment post
-- (by any recruiter), not in Recruitment yet -> added, talking with me, their first words kept. Returns the key
-- added, or nil.
function Msg:OnWhisper(text, sender)
    local C = ns.Compat
    if C and C.IsSecret and (C.IsSecret(text) or C.IsSecret(sender)) then return nil end
    if type(sender) ~= "string" or sender == "" or Util.DemoOn() then return nil end
    if not (R() and R():CanUse()) then return nil end
    local last = self:LastAnyPost()
    if not last or Now() - last > WHISPER_WINDOW then return nil end
    if not Msg.IsAboutGuild(text) then return nil end
    local key = Util.NormalizeName(sender)
    if not key or Util.IsMe(key) then return nil end
    local G = ns.Guild
    if G and G.IsInGuild and G:IsInGuild(key, true) then return nil end
    if R():Get(key) then return nil end
    local ok = R():Add(key, { src = "whisper" })
    if not ok then return nil end
    local said = type(text) == "string" and Util.Trim((text:gsub("|", ""))) or nil
    if said and said ~= "" and R().Update then R():Update(key, { said = said }) end
    ns:Print("%s whispered after a recruitment post: added to Guild > People > Talking.", Util.ShortName(key) or key)
    ns:Fire("RECRUIT_WHISPER_ADDED", key)
    return key
end

function Msg:OnInit()
    if ns.Comm and ns.Comm.Register then ns.Comm:Register("RCP", OnPost) end
    if ns.Comm and ns.Comm.Register then
        ns.Comm:Register("RCM", OnDoc)
        ns.Comm:Register("RCMQ", OnAsk)
        -- (a raid leader may be a recruiter: the whole set of messages passes the members' size cap)
        if ns.Comm.AllowLarge then ns.Comm:AllowLarge("RCM", "data") end
    end
    ns:RegisterEvent("CHAT_MSG_WHISPER", function(_, text, sender) Msg:OnWhisper(text, sender) end)
    if C_Timer and C_Timer.NewTicker then C_Timer.NewTicker(1, Tick) end
    ns:On("DEMO_TOGGLED", function() demoStore = nil; Msg.ready, Msg.readyKey = nil, nil end)
end

function Msg:OnLogin()
    Util.After(LOGIN_ASK, function() Msg:AskShared() end)
end

-- (tests) check now
function Msg:_Tick() Tick() end
