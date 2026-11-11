if DisasterZoneBoot and DisasterZoneBoot.Run("Core/AuditDemo.lua", ...) then return end -- DisasterZone: demo mode's audit log.
-- A made-up month of the demo guild (Core/Demo.lua's members) for the audit log page, in memory only: tonight's
-- changes in full (one of each kind, several big ones, things to put back), then a seeded month around the raid
-- nights (Thursday Gruul + Magtheridon, Sunday Serpentshrine, Tuesday Karazhan; on Forever: Barrow Deeps, Hyjal Summit,
-- Onyxia). Never saved or sent.
local addonName, ns = ...

local AuditDemo = {}
ns.AuditDemo = AuditDemo

local Util = ns.Util
local floor = math.floor
-- WoW Forever: the same month on Forever's raids (Thursday Barrow Deeps, Sunday Hyjal Summit, Tuesday Onyxia) with
-- level-60 dungeon items (the raids' loot isn't known before they open); no strategy boards (hidden on Forever).
-- F(tbc, forever) picks the client's text; the TBC month stays exactly as it was (its tests read it).
local FOREVER = ns.Compat and ns.Compat.isForever
local function F(tbc, forever) if FOREVER then return forever end return tbc end
local DAY = 86400

local seed = 1017
local function R()                          -- (own sequence: math.random is the rolls' and the games')
    seed = (seed * 1103515245 + 12345) % 2147483648
    return seed / 2147483648
end
local function ri(a, b) return a + floor(R() * (b - a + 1)) end
local function pick(t) return t[floor(R() * #t) + 1] end

local function K(name) return Util.NormalizeName(name) or name end
local function P(name) return "@" .. K(name) end

local CLS = { Aldrin = "WARRIOR", Brakka = "WARRIOR", Caelith = "PALADIN", Dornoth = "PALADIN", Elowen = "HUNTER",
    Faelar = "HUNTER", Grimtusk = "ROGUE", Halvard = "ROGUE", Isolde = "PRIEST", Jorvik = "PRIEST", Kaelyn = "SHAMAN",
    Lorvane = "SHAMAN", Mirabel = "MAGE", Nortok = "MAGE", Orinel = "WARLOCK", Pyria = "WARLOCK", Quillon = "DRUID",
    Rhosyn = "DRUID" }
local RAIDERS = { "Aldrin", "Brakka", "Caelith", "Dornoth", "Elowen", "Faelar", "Grimtusk", "Halvard", "Isolde",
    "Jorvik", "Kaelyn", "Lorvane", "Mirabel", "Nortok", "Orinel", "Pyria", "Quillon", "Rhosyn" }
local TOKEN = { WARRIOR = "Defender", PRIEST = "Defender", DRUID = "Defender", PALADIN = "Champion", ROGUE = "Champion",
    SHAMAN = "Champion", HUNTER = "Hero", MAGE = "Hero", WARLOCK = "Hero" }

local function Day(t) return date("%a ", t) .. tonumber(date("%d", t)) end
local function Start(t) return date("%a ", t) .. tonumber(date("%d", t)) .. date(" %b, %H:%M", t) end

-- Fills store (Audit's demo bucket: { since, e, seen }).
function AuditDemo:Fill(store)
    local Audit = ns.Audit
    local me = Util.PlayerKey() or "You"
    local now = Util.Now()
    local d0 = date("*t", now)
    d0.hour, d0.min, d0.sec = 0, 0, 0
    local midnight = time(d0) or (now - now % DAY)
    seed = 1017
    local list = {}
    local function at(d, h, m) return midnight - d * DAY + h * 3600 + (m or 0) end
    local function add(e)
        if e.t > now then e.t = now - 60 * (#list + 1) end
        list[#list + 1] = e
        return e
    end
    -- the raids this week
    local sun = 0
    while date("*t", now + sun * DAY).wday ~= 1 do sun = sun + 1 end
    local ssc = { o = "rp:O:demossc", n = F("Serpentshrine Cavern", "Hyjal Summit") .. " · " .. Day(midnight + sun * DAY),
                  x = F("raid:ssc", "raid:hyjal") }
    local thu = 0
    while date("*t", now - thu * DAY).wday ~= 5 do thu = thu + 1 end
    local gm = { o = "rp:O:demogm", n = F("Gruul + Mag", "Barrow Deeps") .. " · " .. Day(midnight - thu * DAY),
                 x = F("raid:gruul", "raid:barrow") }

    add({ a = "raids", v = "add", w = K("Caelith"), o = ssc.o, n = ssc.n, k = "rp.E", x = ssc.x, t = at(5, 18, 2),
          c = "planned {o}", f = { { l = "Raid", v = F("Serpentshrine Cavern", "Hyjal Summit") }, { l = "Start", v = "19:30" },
          { l = "Leader", v = P("Aldrin") }, { l = "Note", v = "Flasks and food." } } })
    -- today
    add({ a = "raids", v = "chg", w = K("Aldrin"), o = ssc.o, n = ssc.n, k = "rp.E", x = ssc.x, t = at(0, 20, 4),
          f = { { l = "Start", a = "19:30", b = "20:00" }, { l = "Note", ta = "Flasks and food.", tb = F("Flasks and food. Nature resistance for Hydross.", "Flasks and food. Nature resistance for the Wild King.") } } })
    add({ a = "raids", v = "chg", w = K("Aldrin"), o = ssc.o, n = ssc.n, k = "rp.E", x = ssc.x, t = at(0, 19, 58), sk = "g",
          f = { { l = "Groups", mv = { { K("Mirabel"), "Group 4", "Bench" }, { K("Nortok"), "Not placed", "Group 4" },
                { K("Isolde"), "Group 3", "Group 2" }, { K("Jorvik"), "Group 2", "Group 3" } } } } })
    if not FOREVER then add({ a = "raids", v = "chg", w = K("Caelith"), o = ssc.o, n = ssc.n, k = "sb.F", x = ssc.x, t = at(0, 19, 42), sk = "f",
          c = "changed the strategies for {o}", f = { { l = "The Lurker Below", a = "The Lurker Below", b = "Lurker: spout and adds" } } })
    add({ a = "strat", v = "add", w = K("Caelith"), o = "sb:demolurker", n = "Lurker: spout and adds", k = "sb.B", x = "raid:ssc",
          t = at(0, 19, 41), c = "made the strategy {o}", f = { { l = "Boss", v = "The Lurker Below" }, { l = "Pages", v = "Spout · Adds · Positions" } } }) end
    for i, name in ipairs({ "Nortok", "Faelar", "Rhosyn", "Jorvik", "Lorvane", "Kaelyn", "Quillon", "Elowen" }) do
        add({ a = "raids", v = "add", w = K(name), o = ssc.o, n = ssc.n, k = "rp.U", x = ssc.x, t = at(0, 19, 12 + i), sk = K(name),
              c = "signed up for {o}", f = { { l = "Answer", v = i == 3 and "Tentative" or "Coming" } } })
    end
    add({ a = "guests", v = "rem", w = K("Isolde"), o = "bl:" .. K("Dartmoon"), n = "Dartmoon", k = "rp.BL", x = "class:HUNTER",
          t = at(0, 18, 20), b = "black", c = "took {o} off the blacklist", s = "“Talked it out, paid the guild back.”",
          f = { { l = "Blacklisted for", was = F("Ninja-looted two T4 tokens in Gruul's Lair (July)", "Ninja-looted a Royal Tribunal Cloak in Stratholme") } }, p = { r = F("Ninja-looted two T4 tokens in Gruul's Lair (July)", "Ninja-looted a Royal Tribunal Cloak in Stratholme") } })
    add({ a = "roles", v = "chg", w = me, o = "gd:lootrules", n = "the loot rules", k = "gd.RL", x = "g:crown", t = at(0, 17, 5),
          b = "rules", sk = "lr", f = { { l = "Then, among them", a = "Highest roll", b = "Driest first" } } })
    add({ a = "members", v = "chg", w = K("Isolde"), o = "on:" .. K("Brakka"), n = "Brakka", k = "on.N", x = "class:WARRIOR",
          t = at(0, 15, 12), c = "changed the officer note on {o}",
          f = { { l = "Officer note", ta = F("Trial until next week. Good on Maulgar, slow on interrupts.", "Trial until next week. Good on Gandling, slow on interrupts."),
                tb = F("Raider from next week. Good on Maulgar, interrupts fixed.", "Raider from next week. Good on Gandling, interrupts fixed.") } } })
    add({ a = "loot", v = "chg", w = K("Mirabel"), o = "bis:" .. K("Mirabel"), n = "their BiS list", k = "bis.L", x = "class:MAGE",
          t = at(0, 14, 40), f = { { l = F("Neck · Phase 2", "Back · Season 1"), a = F("#28762", "#13376"), b = F("#28530", "#280062") } } })
    add({ a = "events", v = "add", w = K("Caelith"), o = "pl:demo2", n = "Second raid night: Tue or Wed?", k = "pl.P", x = "g:ballot",
          t = at(0, 13, 30), c = "started the poll {o}", f = { { l = "Answers", v = "Tuesday · Wednesday" }, { l = "Closes", v = Start(at(-2, 21)) } } })
    if not FOREVER then add({ a = "strat", v = "rem", w = K("Aldrin"), o = "sb:demohyd", n = "Hydross (old)", k = "sb.B", x = "raid:ssc",
          t = at(0, 12, 2), b = "rem", c = "removed the strategy {o}", f = { { l = "Boss", v = "Hydross the Unstable" }, { l = "Pages", v = "Phases · Marks · Adds · Tanks" } },
          p = { n = "Hydross (old)" } }) end

    -- yesterday
    add({ a = "addon", v = "add", w = me, o = "pt:demo", n = F("1.5.5 update 2", "0.1.0 update 2"), k = "pt.U", x = "seal", t = at(1, 22, 15),
          b = "update", c = "sent {o} to the guild", f = { { l = "Files", v = 4 } } })
    add({ a = "raids", v = "chg", w = K("Aldrin"), o = "rp:O:demokara", n = F("Karazhan", "Onyxia's Lair") .. " · " .. Day(at(-3, 19)), k = "rp.E", x = F("raid:kara", "raid:ony"),
          t = at(1, 21, 30), f = { { l = "Guests", ad = { P("Holymolly") } } } })
    add({ a = "guests", v = "add", w = K("Aldrin"), o = "gb:" .. K("Holymolly"), n = "Holymolly", k = "gb.N", x = "class:PALADIN",
          t = at(1, 20, 47), c = "added {o} to the guest book", f = { { l = "Class", v = "Paladin" }, { l = "Note", v = "Great healer, ask again." } } })
    add({ a = "roles", v = "chg", w = me, o = "gd:leaders", n = "the raid leaders", k = "gd.RL", x = "g:crown", t = at(1, 18, 30),
          b = "rights", sk = "m", f = { { l = "Raid leaders", ad = { P("Caelith") } } } })
    add({ a = "raids", v = "add", w = K("Caelith"), o = "rp:O:demokara", n = F("Karazhan", "Onyxia's Lair") .. " · " .. Day(at(-3, 19)), k = "rp.E", x = F("raid:kara", "raid:ony"),
          t = at(1, 17, 55), c = "planned {o}", f = { { l = "Raid", v = F("Karazhan", "Onyxia's Lair") }, { l = "Start", v = Start(at(-3, 19, 45)) }, { l = "Leader", v = P("Caelith") } } })
    add({ a = "loot", v = "add", w = K("Aldrin"), o = "lg:demobmb2", n = "#" .. F(28802, 13957), k = "lg.A", x = "item:" .. F(28802, 13957), t = at(1, 12, 11), sk = "a",
          c = "gave {o} to " .. P("Nortok"), f = { { l = "Award", aw = { { F(28802, 13957), K("Nortok"), "bis" } } } } })
    add({ a = "loot", v = "rem", w = K("Aldrin"), o = "lg:demobmb1", n = "#" .. F(28802, 13957), k = "lg.A", x = "item:" .. F(28802, 13957), t = at(1, 12, 10), sk = "v",
          b = "void", c = "took back {o} from " .. P("Mirabel"), s = "“Wrong name clicked, it went to Nortok”",
          f = { { l = "Award", aw = { { F(28802, 13957), K("Mirabel"), "bis" } } } }, p = { id = "demobmb1" } })
    add({ a = "members", v = "chg", w = K("Isolde"), o = "rl:demogm", n = gm.n, k = "at.D", x = "class:SHAMAN", t = at(1, 10, 5),
          sk = "dc:" .. K("Kaelyn"), c = "decided the attendance of " .. P("Kaelyn") .. " for {o}",
          f = { { l = "Attendance", a = "Not decided", b = "Excused" }, { l = "Note", v = "Disconnected, was in Discord the whole time." } } })
    add({ a = "recruit", v = "chg", w = K("Isolde"), o = "rc:" .. K("Lumifae"), n = "Lumifae", k = "rc.P", x = "class:MAGE", t = at(1, 9, 40),
          f = { { l = "Stage", a = "Talking", b = "Joined" }, { l = "Note", v = F("Mage 70, Kara geared, free Thu and Sun.", "Mage 60, dungeon geared, free Thu and Sun.") } } })

    -- the raid night (Thursday) and older days: seeded
    local LOOT = F({ { "gruul", 28830, 28802 }, { "mag", 28789 }, { "kara", 28770, 28762, 28772 } },
        { { "barrow", 280063, 16672, 16695 }, { "hyjal", 13969, 16701, 14024 }, { "ony", 18727, 13376, 280064 } })
    local function lootOf(zone)
        for _, z in ipairs(LOOT) do
            if z[1] == zone then return z end
        end
        return {}
    end
    local function awards(o, n, x, who, d, h, m, zone, count)
        for i = 1, count do
            local name = pick(RAIDERS)
            local z = lootOf(zone)
            local item = z[i + 1] or (FOREVER and #z > 1 and z[(i - 1) % (#z - 1) + 2]) or nil
            local tok = (zone == "mag" and "Chestguard" or zone == "kara" and "Helm" or (i % 2 == 0 and "Pauldrons" or "Leggings"))
                .. " of the Fallen " .. TOKEN[CLS[name]]
            add({ a = "loot", v = "add", w = K(who), o = "lg:demo" .. d .. zone .. i, n = item and ("#" .. item) or tok, k = "lg.A",
                  x = item and ("item:" .. item) or x, t = at(d, h, m + i), sk = "a", c = "gave {o} to " .. P(name),
                  f = { { l = "Award", aw = { { item or 0, K(name), R() < 0.85 and "bis" or "os", tok } } } } })
        end
    end
    local nights = 0
    for d = 2, 29 do
        local t = at(d, 12)
        local wd = date("*t", t).wday
        local function raid(key, label, inst, zones, leader)
            nights = nights + 1
            local o = (d == thu and key == "gm") and gm.o or ("rp:O:demo" .. key .. d)
            local n = label .. " · " .. Day(t)
            local x = "raid:" .. inst
            add({ a = "raids", v = "add", w = K("Caelith"), o = o, n = n, k = "rp.E", x = x, t = at(math.min(d + 5, 29), 18, 2),
                  c = "planned {o}", f = { { l = "Raid", v = label }, { l = "Start", v = Start(at(d, 19, 30)) }, { l = "Leader", v = P(leader) } } })
            local pool = {}
            for _, r in ipairs(RAIDERS) do pool[#pool + 1] = r end
            for i = 1, ri(8, 14) do
                local j = ri(i, #pool)
                pool[i], pool[j] = pool[j], pool[i]
                add({ a = "raids", v = "add", w = K(pool[i]), o = o, n = n, k = "rp.U", x = x, t = at(math.min(d + ri(1, 4), 29), 20, i),
                      sk = K(pool[i]), c = "signed up for {o}", f = { { l = "Answer", v = "Coming" } } })
            end
            add({ a = "raids", v = "chg", w = K(leader), o = o, n = n, k = "rp.E", x = x, t = at(d, 18, 48), sk = "g",
                  f = { { l = "Groups", mv = { { K(pool[2]), "Bench", "Group 5" }, { K(pool[3]), "Group 5", "Bench" } } } } })
            add({ a = "raids", v = "add", w = K(leader), o = "rl:" .. o, n = n, k = "rl.R", x = x, t = at(d, 19, 31), sk = "start", c = "started {o}" })
            for zi, z in ipairs(zones) do awards(o, n, x, zi == 1 and "Caelith" or "Aldrin", d, 21 + zi, 30, z, z == "gruul" and ri(4, 6) or ri(2, 4)) end
            add({ a = "raids", v = "chg", w = K(leader), o = "rl:" .. o, n = n, k = "rl.E", x = x, t = at(d, 23, 25), sk = "end", c = "ended {o}",
                  f = { { l = "Attended", v = ri(18, 25) } } })
        end
        if FOREVER then
            if wd == 5 then raid("gm", "Barrow Deeps", "barrow", { "barrow" }, "Aldrin")
            elseif wd == 1 then raid("ssc", "Hyjal Summit", "hyjal", { "hyjal" }, "Aldrin")
            elseif wd == 3 then raid("kara", "Onyxia's Lair", "ony", { "ony" }, "Caelith")
            end
        elseif wd == 5 then raid("gm", "Gruul + Mag", "gruul", { "gruul", "mag" }, "Aldrin")
        elseif wd == 1 then raid("ssc", "Serpentshrine Cavern", "ssc", { "ssc" }, "Aldrin")
        elseif wd == 3 then raid("kara", "Karazhan", "kara", { "kara" }, "Caelith")
        end
        for _ = 1, ri(1, 3) do
            local r = R()
            local who = pick({ "Aldrin", "Caelith", "Isolde" })
            if r < 0.25 then
                local name = pick(RAIDERS)
                add({ a = "members", v = "chg", w = K(who), o = "on:" .. K(name), n = name, k = "on.N", x = "class:" .. CLS[name],
                      t = at(d, ri(10, 22), ri(0, 59)), c = "changed the officer note on {o}",
                      f = { { l = "Officer note", ta = "Trial.", tb = F("Raider. Steady on Gruul.", "Raider. Steady on Onyxia.") } } })
            elseif r < 0.5 and not FOREVER then
                local boards = { "High King Maulgar: kill order", "Magtheridon: cube clickers", "Gruul: shatter spread", "Prince Malchezaar: infernals" }
                local b = pick(boards)
                add({ a = "strat", v = "chg", w = K(pick({ "Quillon", "Caelith", "Aldrin" })), o = "sb:demo" .. b:sub(1, 6), n = b, k = "sb.B",
                      x = "raid:" .. (b:find("Prince") and "kara" or b:find("Magth") and "mag" or "gruul"), t = at(d, ri(11, 23), ri(0, 59)),
                      f = { { l = "Pages changed", v = "Positions" } } })
            elseif r < 0.75 then
                local name = pick(RAIDERS)
                add({ a = "loot", v = "chg", w = K(name), o = "bis:" .. K(name), n = "their BiS list", k = "bis.L", x = "class:" .. CLS[name],
                      t = at(d, ri(9, 23), ri(0, 59)), f = { { l = F("Trinket 1 · Phase 2", "Back · Season 1"), a = F("#28830", "#13376"), b = F("#28789", "#280062") } } })
            elseif r < 0.9 then
                add({ a = "members", v = "chg", w = K("Isolde"), o = "rl:demofix" .. d, n = F("Gruul + Mag", "Barrow Deeps") .. " · " .. Day(at(d + 1, 12)), k = "at.D",
                      x = "class:SHAMAN", t = at(d, 10, ri(0, 59)), sk = "dc:x", c = "decided the attendance of " .. P(pick(RAIDERS)) .. " for {o}",
                      f = { { l = "Attendance", a = "Not decided", b = "Counts" } } })
            elseif not FOREVER then
                add({ a = "strat", v = "rem", w = K(who), o = "sb:democopy" .. d, n = "Gruul: shatter spread (copy)", k = "sb.B", x = "raid:gruul",
                      t = at(d, ri(12, 22), ri(0, 59)), b = "rem", c = "removed the strategy {o}", p = { n = "copy" } })
            end
        end
    end
    for _, e in ipairs(list) do
        local c = Audit._Clean(e, false, 16000)
        if c then store.e[c.id] = c end
    end
    store.since = midnight - 29 * DAY
    store.seen[me] = at(2, 23, 40)
end
