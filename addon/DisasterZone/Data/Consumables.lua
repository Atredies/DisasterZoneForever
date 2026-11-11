if DisasterZoneBoot and DisasterZoneBoot.Run("Data/Consumables.lua", ...) then return end -- DisasterZone: Data/Consumables.lua
-- The consumables kit per spec (My BiS > Consumables, Core/Kit.lua) for WoW Forever's level-60 raids: for each slot of
-- the kit the best pick (prog nights) and a budget pick (farm nights). A budget of "same" means the cheap way is the
-- same thing, false means skip it (skip = why). The usual level-60 raid consumables; every item id checked against
-- Wowhead's Forever item database (dev/tests/forever/test_forever_content.py). Forever renamed some (Elixir of Giants is
-- Elixir of Greater Strength). Forever changes (unverified, beta notes): one battle and one guardian elixir at a
-- time, a flask instead of both; healing potions made with First Aid.
-- The TBC kit: dev/fixtures/tbc/Data/Consumables.lua.
local _, ns = ...
ns.Data = ns.Data or {}

local C = {}
ns.Data.Consumables = C

-- item -> { name, short name (for an elixir pair), what it does, kind }
-- kinds: flask, battle, guardian (elixirs), food, stone, oil, potion, scroll, rune (runes, Thistle Tea)
C.ITEMS = {
  -- flasks
  [13510] = { "Flask of the Titans", "Titans", "+1200 health", "flask" },
  [13511] = { "Flask of Distilled Wisdom", "Distilled Wisdom", "+2000 mana", "flask" },
  [13512] = { "Flask of Supreme Power", "Supreme Power", "+150 spell damage", "flask" },
  [13513] = { "Flask of Chromatic Resistance", "Chromatic Resistance", "+25 all resistances", "flask" },
  -- battle elixirs
  [13452] = { "Elixir of the Mongoose", "Mongoose", "+25 Agility, +2% crit", "battle" },
  [9206] = { "Elixir of Greater Strength", "Greater Strength", "+25 Strength", "battle" },
  [13454] = { "Greater Arcane Elixir", "Greater Arcane", "+35 spell damage", "battle" },
  [9264] = { "Elixir of Shadow Power", "Shadow Power", "+40 shadow damage", "battle" },
  [17708] = { "Elixir of Frost Power", "Frost Power", "+15 frost damage", "battle" },
  -- guardian elixirs
  [3825] = { "Elixir of Lesser Fortitude", "Lesser Fortitude", "+120 health", "guardian" },
  [13445] = { "Elixir of Greater Defense", "Greater Defense", "+450 armor", "guardian" },
  [20007] = { "Mageblood Elixir", "Mageblood", "+12 mana per 5 sec", "guardian" },
  [9179] = { "Elixir of Greater Intellect", "Greater Intellect", "+25 Intellect", "guardian" },
  [13447] = { "Elixir of the Sages", "Sages", "+18 Intellect, +18 Spirit", "guardian" },
  -- food
  [20452] = { "Smoked Desert Dumplings", nil, "+20 Strength", "food" },
  [13928] = { "Grilled Squid", nil, "+10 Agility", "food" },
  [18254] = { "Runn Tum Tuber Surprise", nil, "+10 Intellect", "food" },
  [13931] = { "Nightfin Soup", nil, "+8 mana per 5 sec", "food" },
  [21217] = { "Sagefish Delight", nil, "+6 mana per 5 sec", "food" },
  [21023] = { "Dirge's Kickin' Chimaerok Chops", nil, "+25 Stamina", "food" },
  [12218] = { "Monster Omelet", nil, "+12 Stamina, +12 Spirit", "food" },
  -- weapon stones and oils
  [18262] = { "Elemental Sharpening Stone", nil, "+2% crit", "stone" },
  [12404] = { "Dense Sharpening Stone", nil, "+8 weapon damage", "stone" },
  [12643] = { "Dense Weightstone", nil, "+8 weapon damage", "stone" },
  [20749] = { "Brilliant Wizard Oil", nil, "+36 spell dmg, +1% crit", "oil" },
  [20750] = { "Wizard Oil", nil, "+24 spell damage", "oil" },
  [20748] = { "Brilliant Mana Oil", nil, "+12 mp5, +25 healing", "oil" },
  [20747] = { "Lesser Mana Oil", nil, "+8 mana per 5 sec", "oil" },
  -- potions
  [13444] = { "Major Mana Potion", nil, "1350 to 2250 mana", "potion" },
  [13446] = { "Major Healing Potion", nil, "1050 to 1750 health", "potion" },
  [13442] = { "Mighty Rage Potion", nil, "45 to 75 rage, +60 Strength", "potion" },
  [13455] = { "Greater Stoneshield Potion", nil, "+2000 armor for 2 min", "potion" },
  [5634] = { "Free Action Potion", nil, "Immune to stuns and roots", "potion" },
  -- scrolls
  [10310] = { "Scroll of Strength IV", "Strength", "+17 Strength", "scroll" },
  [10309] = { "Scroll of Agility IV", "Agility", "+17 Agility", "scroll" },
  [10305] = { "Scroll of Protection IV", "Protection", "+240 armor", "scroll" },
  [10308] = { "Scroll of Intellect IV", "Intellect", "+16 Intellect", "scroll" },
  [10306] = { "Scroll of Spirit IV", "Spirit", "+15 Spirit", "scroll" },
  [10307] = { "Scroll of Stamina IV", "Stamina", "+16 Stamina", "scroll" },
  -- runes and the like (their own shared 2 minute timer)
  [12662] = { "Demonic Rune", nil, "900 to 1500 mana", "rune" },
  [20520] = { "Dark Rune", nil, "900 to 1500 mana", "rune" },
  [7676] = { "Thistle Tea", nil, "+100 energy", "rune" },
}

-- How many of a kind one night takes (a three hour raid): a flask lasts 2 hours, an elixir 1, food, stones, oils and
-- scrolls 30 minutes; a potion or rune per boss you use it on.
C.NIGHT = { flask = 2, battle = 3, guardian = 3, food = 6, stone = 6, oil = 6, potion = 5, scroll = 6, rune = 4 }

-- The kit's slots, in the order shown; why = the line under the slot's name (a spec can override it).
C.SLOTS = {
  { key = "flask", title = "FLASK", why = "Or two elixirs, never both." },
  { key = "food", title = "FOOD", why = "Well Fed lasts 15 minutes." },
  { key = "weapon", title = "WEAPON", why = "On the weapon for 30 minutes." },
  { key = "potion", title = "POTION", why = "One per fight." },
  { key = "scroll", title = "SCROLLS", why = "Useless if a buff gives the same stat." },
  { key = "extra", title = "EXTRA", why = "Its own timer, apart from potions." },
}

-- A sharpening stone on a blunt weapon is the weightstone.
C.BLUNT = { [12404] = 12643 }

-- The gear sim is not part of WoW Forever (no Forever ruleset): nothing to hand it.
C.SIM_IMBUE, C.SIM_SCROLL, C.SIM_RUNE = {}, {}, {}

local SKIP_RUNE = "Farm bosses die before you run dry."
local WF_WHY = "Windfury Totem replaces it."
local SAME = "Cheap enough for every night."

-- shared rows
local MELEE_STONE = { best = { 18262 }, budget = { 12404 }, why = WF_WHY }
local SCROLLS_PHYS = { best = { 10310, 10309 }, budget = "same", sameWhy = SAME }
local SCROLL_AGI = { best = { 10309 }, budget = "same", sameWhy = SAME }
local MELEE_POT = { best = { 13442 }, budget = { 13446 } }
local CASTER_FOOD = { best = { 18254 }, budget = { 13931 } }
local CASTER_OIL = { best = { 20749 }, budget = { 20750 } }
local CASTER_POT = { best = { 13444 }, budget = "same", sameWhy = "Mana keeps you casting." }
local CASTER_RUNE = { best = { 12662 }, budget = false, skip = SKIP_RUNE }
local HEAL_FOOD = { best = { 13931 }, budget = { 21217 } }
local HEAL_OIL = { best = { 20748 }, budget = { 20747 } }
local HEAL_POT = { best = { 13444 }, budget = "same", sameWhy = "Mana is the fight for a healer." }
local HEAL_RUNE = { best = { 12662 }, budget = "same", sameWhy = "Mana is the fight for a healer." }
local TANK_FOOD = { best = { 21023 }, budget = { 12218 } }
local TANK_POT = { best = { 13455 }, budget = { 13446 } }
local TANK_SCROLL = { best = { 10305, 10309 }, budget = "same", sameWhy = SAME }
local AGI_FOOD = { best = { 13928 }, budget = "same", sameWhy = "Cheap to cook." }
local STR_FOOD = { best = { 20452 }, budget = { 12218 } }

local function caster(battle, extra)
  return { flask = { best = { 13512 }, budget = { battle, 9179 } }, food = CASTER_FOOD,
    weapon = CASTER_OIL, potion = CASTER_POT, extra = extra or CASTER_RUNE }
end

local function healer()
  return { flask = { best = { 13511 }, budget = { 20007, 13447 }, budgetWhy = "Mageblood and the Sages." },
    food = HEAL_FOOD, weapon = HEAL_OIL, potion = HEAL_POT, extra = HEAL_RUNE }
end

local function tank()
  return { flask = { best = { 13510 }, budget = { 13452, 13445 } }, food = TANK_FOOD,
    weapon = { best = { 12404 }, budget = "same", sameWhy = "Cheap, and it is threat." },
    potion = TANK_POT, scroll = TANK_SCROLL }
end

local ROGUE = {
  flask = { best = { 13510 }, budget = { 13452, 3825 } },
  food = AGI_FOOD, weapon = MELEE_STONE,
  potion = { best = { 13446 }, budget = "same", sameWhy = "For the bad pull." }, scroll = SCROLLS_PHYS,
  extra = { best = { 7676 }, budget = "same", sameWhy = "You make it yourself (Cooking)." },
}
local HUNTER = {
  flask = { best = { 13510 }, budget = { 13452, 3825 } },
  food = AGI_FOOD, potion = CASTER_POT, scroll = SCROLL_AGI,
  extra = { best = { 12662 }, budget = false, skip = SKIP_RUNE },
}
local MELEE = {
  flask = { best = { 13510 }, budget = { 9206, 3825 } },
  food = STR_FOOD, weapon = MELEE_STONE, potion = MELEE_POT, scroll = SCROLLS_PHYS,
}

C.KITS = {
  ["PALADIN:Retribution"] = {
    flask = { best = { 13510 }, budget = { 9206, 9179 } },
    food = STR_FOOD, weapon = MELEE_STONE,
    potion = { best = { 13444 }, budget = { 13446 } }, scroll = SCROLLS_PHYS,
    extra = { best = { 12662 }, budget = false, skip = SKIP_RUNE, why = "Mana when you run dry." },
  },
  ["PALADIN:Holy"] = healer(),
  ["PALADIN:Protection"] = tank(),
  ["WARRIOR:Arms"] = MELEE,
  ["WARRIOR:Fury"] = MELEE,
  ["WARRIOR:Protection"] = tank(),
  ["SHAMAN:Enhancement"] = {
    flask = { best = { 13510 }, budget = { 9206, 9179 } },
    food = STR_FOOD, potion = { best = { 13444 }, budget = { 13446 } }, scroll = SCROLLS_PHYS,
    extra = { best = { 12662 }, budget = false, skip = SKIP_RUNE },
  },
  ["SHAMAN:Elemental"] = caster(13454),
  ["SHAMAN:Restoration"] = healer(),
  ["ROGUE:Assassination"] = ROGUE,
  ["ROGUE:Combat"] = ROGUE,
  ["ROGUE:Subtlety"] = ROGUE,
  ["HUNTER:Beast Mastery"] = HUNTER,
  ["HUNTER:Marksmanship"] = HUNTER,
  ["HUNTER:Survival"] = HUNTER,
  ["DRUID:Balance"] = caster(13454),
  ["DRUID:Feral"] = {
    flask = { best = { 13510 }, budget = { 13452, 13445 } },
    food = AGI_FOOD, potion = MELEE_POT, scroll = SCROLLS_PHYS,
  },
  ["DRUID:Restoration"] = healer(),
  ["PRIEST:Shadow"] = caster(9264),
  ["PRIEST:Holy"] = healer(),
  ["PRIEST:Discipline"] = healer(),
  ["MAGE:Arcane"] = caster(13454),
  ["MAGE:Fire"] = caster(13454),
  ["MAGE:Frost"] = caster(17708),
  ["WARLOCK:Affliction"] = caster(9264),
  ["WARLOCK:Demonology"] = caster(9264),
  ["WARLOCK:Destruction"] = caster(9264),
}
