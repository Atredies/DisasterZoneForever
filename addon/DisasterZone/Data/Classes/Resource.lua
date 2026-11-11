if DisasterZoneBoot and DisasterZoneBoot.Run("Data/Classes/Resource.lua", ...) then return end -- DisasterZone: resource bar spells.
-- Spell data for the resource bar (Core/Resource.lua, feedback #26): the presses a player can pick a mark for, per
-- class, by spell id (TBC's top rank; a lower rank counts as known by name, names come from the client in any
-- language). `cost` is the base rage / energy cost for when the client gives none (talents then do not count); mana
-- costs come from the client only. `form` limits a druid press to the form whose power it spends.
local addonName, ns = ...

ns.ClassData = ns.ClassData or {}

ns.ClassData.RESOURCE = {
    PRESSES = {
        WARRIOR = {
            { key = "hs", id = 29707, cost = 15 }, { key = "cleave", id = 25231, cost = 20 },
            { key = "bt", id = 30335, cost = 30 }, { key = "ms", id = 30330, cost = 30 },
            { key = "ww", id = 1680, cost = 25 }, { key = "slam", id = 25242, cost = 15 },
            { key = "exe", id = 25236, cost = 15 }, { key = "rampage", id = 30033, cost = 20 },
            { key = "shout", id = 2048, cost = 10 }, { key = "ham", id = 25212, cost = 10 },
            { key = "op", id = 11585, cost = 5 }, { key = "pummel", id = 6554, cost = 10 },
            { key = "bash", id = 29704, cost = 10 }, { key = "intercept", id = 25275, cost = 10 },
            { key = "sunder", id = 25225, cost = 15 }, { key = "revenge", id = 30357, cost = 5 },
            { key = "slamshield", id = 30356, cost = 20 }, { key = "tclap", id = 25264, cost = 20 },
            { key = "demo", id = 25203, cost = 10 },
        },
        ROGUE = {
            { key = "ss", id = 26862, cost = 45 }, { key = "bs", id = 26863, cost = 60 },
            { key = "hemo", id = 26864, cost = 35 }, { key = "muti", id = 34413, cost = 60 },
            { key = "snd", id = 6774, cost = 25 }, { key = "evis", id = 26865, cost = 35 },
            { key = "rupture", id = 26867, cost = 25 }, { key = "envenom", id = 32684, cost = 35 },
            { key = "expose", id = 26866, cost = 25 }, { key = "kick", id = 38768, cost = 25 },
            { key = "gouge", id = 38764, cost = 45 }, { key = "shiv", id = 5938, cost = 20 },
            { key = "feint", id = 27448, cost = 20 },
        },
        DRUID = {
            { key = "shred", id = 27002, cost = 60, form = "energy" }, { key = "mangle_cat", id = 33983, cost = 45, form = "energy" },
            { key = "rip", id = 27008, cost = 30, form = "energy" }, { key = "fb", id = 24248, cost = 35, form = "energy" },
            { key = "rake", id = 27003, cost = 40, form = "energy" }, { key = "claw", id = 27000, cost = 45, form = "energy" },
            { key = "maul", id = 26996, cost = 15, form = "rage" }, { key = "mangle_bear", id = 33987, cost = 20, form = "rage" },
            { key = "swipe", id = 26997, cost = 20, form = "rage" }, { key = "lacerate", id = 33745, cost = 15, form = "rage" },
            { key = "roar", id = 26998, cost = 10, form = "rage" },
            { key = "ht", id = 26979, form = "mana" }, { key = "rejuv", id = 26982, form = "mana" },
            { key = "regrowth", id = 26980, form = "mana" }, { key = "lifebloom", id = 33763, form = "mana" },
            { key = "wrath", id = 26985, form = "mana" }, { key = "starfire", id = 26986, form = "mana" },
            { key = "moonfire", id = 26988, form = "mana" },
        },
        PALADIN = {
            { key = "hl", id = 27136 }, { key = "fol", id = 27137 }, { key = "shock", id = 33072 },
            { key = "cs", id = 35395 }, { key = "judge", id = 20271 }, { key = "cons", id = 27173 },
            { key = "exo", id = 27138 }, { key = "how", id = 27180 }, { key = "avenger", id = 32700 },
            { key = "hshield", id = 27179 },
        },
        PRIEST = {
            { key = "gheal", id = 25213 }, { key = "flash", id = 25235 }, { key = "poh", id = 25316 },
            { key = "renew", id = 25222 }, { key = "coh", id = 34866 }, { key = "pom", id = 33076 },
            { key = "shield", id = 25218 }, { key = "bheal", id = 32546 }, { key = "blast", id = 25375 },
            { key = "swp", id = 25368 }, { key = "smite", id = 25364 },
        },
        SHAMAN = {
            { key = "hw", id = 25396 }, { key = "lhw", id = 25420 }, { key = "ch", id = 25423 },
            { key = "lb", id = 25449 }, { key = "cl", id = 25442 }, { key = "es", id = 25454 },
            { key = "ss", id = 17364 },
        },
        MAGE = {
            { key = "fireball", id = 27070 }, { key = "frostbolt", id = 27072 }, { key = "ablast", id = 30451 },
            { key = "scorch", id = 27074 }, { key = "fblast", id = 27079 }, { key = "pyro", id = 33938 },
            { key = "lance", id = 30455 }, { key = "aexp", id = 27082 }, { key = "blizzard", id = 27085 },
        },
        WARLOCK = {
            { key = "sbolt", id = 27209 }, { key = "incin", id = 32231 }, { key = "immo", id = 27215 },
            { key = "corr", id = 27216 }, { key = "agony", id = 27218 }, { key = "ua", id = 30405 },
            { key = "seed", id = 27243 }, { key = "pain", id = 30459 }, { key = "burn", id = 30546 },
        },
        HUNTER = {
            { key = "steady", id = 34120 }, { key = "multi", id = 27021 }, { key = "arcane", id = 27019 },
            { key = "aimed", id = 27065 }, { key = "serpent", id = 27016 }, { key = "kc", id = 34026 },
            { key = "raptor", id = 27014 }, { key = "volley", id = 27022 },
        },
    },
    -- Druid forms whose shift a mana mark counts (Cat Form; Dire Bear Form, Bear Form below 40)
    SHIFTS = { 768, 9634, 5487 },
    ADRENALINE_RUSH = 13750,        -- energy comes twice as fast while it runs
}

-- WoW Forever (every id checked against Wowhead's Forever spell database, 2026-11-09): the TBC top ranks are not in the
-- game, so each press is its rank 1 there (a higher rank counts as known by name); the presses Forever does not have
-- go (Rampage, Mangle, Lacerate, Lifebloom, Envenom, Crusader Strike, Avenger's Shield, Circle of Healing, Prayer of
-- Mending, Binding Heal, Arcane Blast, Ice Lance, Incinerate, Unstable Affliction, Seed of Corruption, Steady Shot,
-- Kill Command; Shiv needs level 70 there). Mutilate and Holy Shock are there.
if ns.Compat and ns.Compat.isForever then
    local FOREVER_IDS = {
        WARRIOR = { hs = 78, cleave = 845, bt = 23881, ms = 12294, ww = 1680, slam = 1464, exe = 5308, shout = 6673,
                    ham = 1715, op = 7384, pummel = 6552, bash = 72, intercept = 20252, sunder = 7386, revenge = 6572,
                    slamshield = 23922, tclap = 6343, demo = 1160 },
        ROGUE = { ss = 1752, bs = 53, hemo = 16511, muti = 1329, snd = 5171, evis = 2098, rupture = 1943, expose = 8647,
                  kick = 1766, gouge = 1776, feint = 1966 },
        DRUID = { shred = 5221, rip = 1079, fb = 22568, rake = 1822, claw = 1082, maul = 6807, swipe = 779, roar = 99,
                  ht = 5185, rejuv = 774, regrowth = 8936, wrath = 5176, starfire = 2912, moonfire = 8921 },
        PALADIN = { hl = 635, fol = 19750, shock = 20473, judge = 20271, cons = 26573, exo = 879, how = 24275,
                    hshield = 20925 },
        PRIEST = { gheal = 2060, flash = 2061, poh = 596, renew = 139, shield = 17, blast = 8092, swp = 589, smite = 585 },
        SHAMAN = { hw = 331, lhw = 8004, ch = 1064, lb = 403, cl = 421, es = 8042, ss = 17364 },
        MAGE = { fireball = 133, frostbolt = 116, scorch = 2948, fblast = 2136, pyro = 11366, aexp = 1449, blizzard = 10 },
        WARLOCK = { sbolt = 686, immo = 348, corr = 172, agony = 980, pain = 5676, burn = 17877 },
        HUNTER = { multi = 2643, arcane = 3044, aimed = 19434, serpent = 1978, raptor = 2973, volley = 1510 },
    }
    local P = ns.ClassData.RESOURCE.PRESSES
    for cls, list in pairs(P) do
        local ids = FOREVER_IDS[cls] or {}
        for i = #list, 1, -1 do
            local id = ids[list[i].key]
            if id then list[i].id = id else table.remove(list, i) end
        end
    end
end
