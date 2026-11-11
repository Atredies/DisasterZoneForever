"""WoW Forever only content: what a Forever client shows instead of TBC's (one raid phase, the Classic Atlas without the
era switch, Forever's 35 dungeons with no heroics, raid / PvP / other group kinds without arenas, Outland or
attunements). The TBC client keeps its own lists (the upstream suites cover it).

Seen in game 2026-11-08/09 before this: My BiS had P1-P5 (Karazhan to Sunwell), the Atlas opened on TBC, the Groups
board offered the Outland 5-mans with Heroic, arenas and Halaa.

Run: luaenv/bin/python tests/forever/test_forever_content.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"
PAGES = ["home", "raids", "council", "lootrules", "mybis", "consumables", "wardrobe", "atlas", "members", "map",
         "events", "polls", "recruit", "audit", "games", "dungeons", "settings", "changelog", "feedback"]


def world(forever=True):
    w = World(realm=REALM)
    gm = Client(w, "Arakis War", class_file="WARRIOR", guild_rank=0, level=60, forever=forever)
    gm.load_addon()
    w.tick(5)
    return w, gm


def as_list(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v)]
    return list(v or [])


@case
def test_one_raid_phase():
    w, gm = world()
    assert as_list(gm.eval_py("return ns.PHASES")) == [1]
    assert as_list(gm.eval_py("return ns.LIST_PHASES")) == [0, 1]
    assert gm.eval("return ns.MAX_PHASE") == 1
    assert "Onyxia" in gm.eval("return ns.PHASE_INFO[1].raids")
    assert gm.eval("return ns.PhaseLabel(1)") == "S1"
    assert gm.eval("return ns.PHASE_INFO[1].name") == "Season 1"
    assert "Badges" not in gm.eval("return ns.PHASE_INFO[0].raids")
    # a list made by a later release (a phase 2) is still stored, not refused
    assert gm.eval("return ns.WIRE_MAX_PHASE") == 5
    no_errors(w)


@case
def test_atlas_is_classic_only():
    w, gm = world()
    assert gm.eval("return ns.Atlas:HasEra('tbc')") is False
    assert gm.eval("return ns.Atlas:HasEraSwitch()") is False
    assert gm.eval("return ns.Atlas:GetEra()") == "classic"
    names = as_list(gm.eval_py("local o = {} for _, c in ipairs(ns.Atlas:GetCategories()) do"
                               " for _, s in ipairs(c.sources) do o[#o + 1] = s.name end end return o"))
    # (the raids have no loot yet, so the tree starts with the dungeons: Forever's, then crafting, reputation, PvP)
    assert "Hall of Thanes" in names and "Ragefire Chasm" in names and "Karazhan" not in names, names[:20]
    assert "Molten Core" not in names and "Hellfire Ramparts" not in names, names
    no_errors(w)


@case
def test_dungeons_are_forevers_without_heroics():
    w, gm = world()
    keys = as_list(gm.eval_py("return ns.DungeonRuns:GetDungeonKeys()"))
    assert len(keys) == 35, keys
    for k in ("Deadmines", "HallOfThanes", "BlackmawHold", "ShapersTerrace", "StratholmeUndead"):
        assert k in keys, k
    assert "HellfireRamparts" not in keys
    assert gm.eval("return ns.DungeonRuns.HAS_HEROICS") is False
    assert gm.eval("return ns.DungeonRuns:GetBlocker('Scholomance', true)") is None
    no_errors(w)


@case
def test_group_kinds_are_forevers():
    w, gm = world()
    pvp = as_list(gm.eval_py("local o = {} for _, p in ipairs(ns.Data.GroupKinds.pvp) do o[#o + 1] = p.key end return o"))
    assert pvp == ["wsg", "ab", "av", "darkspear"], pvp
    raids = as_list(gm.eval_py("local o = {} for _, r in ipairs(ns.Data.GroupKinds.raids) do o[#o + 1] = r.key end return o"))
    assert raids == ["BarrowDeeps", "HyjalForever", "Onyxia"], raids
    other = as_list(gm.eval_py("local o = {} for _, r in ipairs(ns.Data.GroupKinds.other) do o[#o + 1] = r.key end return o"))
    assert "attune" not in other, other
    no_errors(w)


@case
def test_recruit_milestones_are_40_and_60():
    w, gm = world()
    assert gm.eval("return ns.Recruit.MILESTONE_LEVEL[58]") == 40
    assert gm.eval("return ns.Recruit.MILESTONE_LEVEL[70]") == 60
    assert gm.eval("return ns.Recruit.MAX_LEVEL") == 60
    assert "Outland" not in gm.eval("return ns.Recruit.MILESTONE_TEXT[58]")
    no_errors(w)


@case
def test_no_jewelcrafting():
    w, gm = world()
    names = as_list(gm.eval_py("local o = {} for _, d in ipairs(ns.Professions:GetProfessions()) do o[#o + 1] = d.name end"
                               " return o"))
    assert "Jewelcrafting" not in names and "Blacksmithing" in names, names
    no_errors(w)


@case
def test_item_data_is_forevers():
    w, gm = world()
    raids = as_list(gm.eval_py("local o = {} for _, r in ipairs(ns.Data.Raids) do o[#o + 1] = r.key .. ':' .. r.size end"
                               " return o"))
    assert raids == ["Onyxia:40", "BarrowDeeps:10", "HyjalForever:20"], raids
    dkeys = as_list(gm.eval_py("local o = {} for _, d in ipairs(ns.Data.Dungeons) do o[#o + 1] = d.key end return o"))
    assert sorted(dkeys) == sorted(as_list(gm.eval_py("return ns.DungeonRuns:GetDungeonKeys()"))), dkeys
    # every dungeon has bosses; the old-world ones have loot; no heroic lists, no TBC items (ids 24000-35000; 24101 Book of
    # Ferocious Bite V is a level-60 UBRS drop)
    bad = gm.eval_py("local o = {} for _, d in ipairs(ns.Data.Dungeons) do for _, b in ipairs(d.bosses) do"
                     " if b.heroicItems then o[#o + 1] = d.key end"
                     " for _, i in ipairs(b.items) do if i >= 24000 and i < 35000 and i ~= 24101 then o[#o + 1] = d.key .. ':' .. i end end"
                     " end end return o")
    assert not as_list(bad), bad
    assert gm.eval("return #ns.ItemDB:GetBossRefs('all') > 300") is True
    assert gm.eval("return next(ns.Data.Badges) == nil and next(ns.Data.Tokens) == nil") is True
    assert gm.eval("return ns.Data.Sockets and next(ns.Data.Sockets) == nil") is True
    assert gm.eval("return ns.Data.BiSLists == nil") is True
    no_errors(w)


@case
def test_hidden_pages_and_totems():
    w, gm = world()
    assert gm.eval("return ns.FOREVER_HIDDEN.gearsim and ns.FOREVER_HIDDEN.mylog and ns.FOREVER_HIDDEN.strategies") is True
    keys = as_list(gm.eval_py("local o = {} for _, l in ipairs(ns.ClassData.SHAMAN.TOTEMS) do for _, t in ipairs(l) do"
                              " o[#o + 1] = t.key end end return o"))
    for k in ("tow", "woa", "earthele", "fireele"):
        assert k not in keys, k
    assert "wf" in keys and "manatide" in keys
    pal = gm.eval_py("local D = ns.ClassData.PALADIN local o = {} for _, b in ipairs(D.BLESSINGS) do"
                     " o[#o + 1] = b.key .. ':' .. #b.ranks end return { o = o, d = D.DURATION, g = D.GDURATION,"
                     " sym = D.SYMBOL_OF_KINGS or 0 }")
    ranks = dict(x.split(":") for x in as_list(pal["o"]))
    assert ranks["salvation"] == "0" and ranks["light"] == "0" and ranks["sanctuary"] == "0", ranks
    assert int(ranks["might"]) == 7 and pal["d"] == 3600 and pal["g"] == 3600 and pal["sym"] == 0, pal
    games = as_list(gm.eval_py("local o = {} for _, g in ipairs(ns.Games.CATALOG) do o[#o + 1] = g.id end return o"))
    assert games == ["bingo", "azeromon", "chess", "holdtheline"], games   # (no Illidan, no Raid Trainer)
    no_errors(w)


@case
def test_consumables_are_level_60():
    w, gm = world()
    ids = as_list(gm.eval_py("local o = {} for id in pairs(ns.Data.Consumables.ITEMS) do o[#o + 1] = id end return o"))
    assert 13510 in ids and 22854 not in ids, ids      # Flask of the Titans, not Relentless Assault
    assert gm.eval("return ns.Data.Consumables.KITS['WARRIOR:Fury'] ~= nil") is True
    no_errors(w)


@case
def test_crafts_and_names_are_forevers():
    """Data/Atlas.lua on Forever: no TBC tree, crafts / recipes / names from AtlasLoot Forever's Classic tables."""
    w, gm = world()
    assert gm.eval("return #ns.Data.Atlas") == 0
    assert gm.eval("return next(ns.Data.AtlasCosts) == nil") is True
    # Flask of the Titans: Alchemy, Stonescale Oil / Black Lotus / ... ; broken down, Stonescale Oil becomes its eel
    craft = gm.eval_py("local c = ns.Atlas:GetCraft(13510) return c and { item = c.item, n = #c.reagents }")
    assert craft and craft["item"] == 13510 and craft["n"] >= 3, craft
    mats = as_list(gm.eval_py("local l = ns.Atlas:GetMaterials(13510, 1, 2) local o = {} for _, e in ipairs(l) do"
                              " o[#o + 1] = e.id end return o"))
    assert 13468 in mats, mats                                  # Black Lotus
    # a recipe teaches its craft; an enchant (a craft that makes no item) has a name
    assert gm.eval("return ns.Data.AtlasRecipes[13517]") == 13503      # Recipe: Alchemist's Stone
    assert gm.eval("return ns.Atlas:GetName(13503)") == "Alchemist's Stone"
    # no TBC crafts (Fel Iron, Adamantite, Primal ... are TBC ids 24000+ as created items; 23684 Crystal Infused
    # Bandage is a vanilla First Aid recipe Forever has)
    tbc = gm.eval("local n = 0 for sp, v in pairs(ns.Data.AtlasCrafts) do local item = tonumber(v:match('^(%d+)'))"
                  " if item and item >= 24000 and item < 35000 then n = n + 1 end end return n")
    assert tbc == 0, tbc
    no_errors(w)


@case
def test_the_demo_guild_raids_on_forever():
    w, gm = world()
    gm.eval("ns.Demo:SetEnabled(true)")
    w.tick(1)
    log = gm.eval_py("local o = {} for _, r in ipairs(ns.Demo:GetRaidLog()) do"
                     " o[#o + 1] = { z = r.zone, b = #r.bosses, a = #(r.demoAwards or {}) } end return o")
    zones = {r["z"] for r in as_list(log)}
    assert zones == {"Hyjal Summit", "Barrow Deeps", "Onyxia's Lair"}, zones
    assert all(r["b"] > 0 for r in as_list(log)) and sum(r["a"] for r in as_list(log)) > 0, log
    assert gm.eval("local r = ns.Demo:GetRoster() local _, m = next(r) return m.level") == 60
    # the audit month: Forever raid nights, no TBC raid or boss names, no strategy boards
    texts = gm.eval_py("local st = { e = {}, seen = {} } ns.AuditDemo:Fill(st) local o = {} for _, e in pairs(st.e) do"
                       " o[#o + 1] = (e.n or '') .. ' ' .. (e.a or '') end return o")
    joined = " | ".join(as_list(texts))
    for tbc in ("Karazhan", "Gruul", "Serpentshrine", "Maulgar", "Hydross", "Lurker"):
        assert tbc not in joined, tbc
    assert "Barrow Deeps" in joined and "Onyxia's Lair" in joined
    assert " strat" not in joined
    # council scenarios without the token / longest-use cases; reserves work on a dungeon (UBRS)
    keys = as_list(gm.eval_py("local o = {} for _, s in ipairs(ns.Demo.SCENARIOS) do o[#o + 1] = s.key end return o"))
    assert "class" not in keys and "longest" not in keys and "split" in keys, keys
    assert gm.eval("return ns.Reserves:RaidLoot('UBRS')[16688]") == "GeneralDrakkisath"
    # the session crest's made-up night (the owner's screenshot showed "Thursday SSC", 23 of 25)
    for moment in ("idle", "between", "pull", "loot", "done"):
        info = gm.eval_py("local i = ns.SessionInfo:Demo(...) return { zone = i.zone, lt = i.lineup and i.lineup.title,"
                          " total = i.addon and i.addon.total }", moment)
        assert info["zone"] == "Hyjal Summit" and info["total"] == 20, (moment, info)
        assert moment != "idle" or info["lt"] == "Thursday Hyjal", info
    gm.eval("ns.Demo:SetEnabled(false)")
    no_errors(w)


@case
def test_secret_nameplate_guids_are_never_table_keys():
    """In game 2026-11-09, Hall of Thanes: UI/CombatText.lua:376 "attempted to index a table that cannot be indexed with
    secret keys" (and the same on assignment): a nameplate's GUID is secret in an instance and was used as a key."""
    w, gm = world()
    gm.eval("__realGUID = UnitGUID UnitGUID = function() return UnitHealth('player') end")   # (a mock secret)
    assert gm.eval("return issecretvalue(UnitGUID('nameplate1'))") is True
    gm.fire("NAME_PLATE_UNIT_ADDED", "nameplate1")      # (the client errors right here: a secret table key)
    bad = gm.eval_py("""
        local out = {}
        for k in pairs(ns.CombatTextUI and ns.CombatTextUI.plates or {}) do
            if issecretvalue(k) then out[#out + 1] = tostring(k) end
        end
        if ns.StrategyLive and ns.StrategyLive.OnUnit then ns.StrategyLive:OnUnit("nameplate1") end
        UnitGUID = __realGUID
        return out
    """)
    gm.fire("NAME_PLATE_UNIT_REMOVED", "nameplate1")
    assert not as_list(bad), bad
    no_errors(w)


@case
def test_changelog_is_forevers():
    w, gm = world()
    log = gm.eval_py("local o = {} for _, e in ipairs(ns.CHANGELOG) do for _, s in ipairs(e.sections) do"
                     " o[#o + 1] = s.lead or '' for _, l in ipairs(s.lines) do o[#o + 1] = type(l) == 'table' and l[1] or l end"
                     " end end return { v = ns.CHANGELOG[1].version, lines = o }")
    assert log["v"] == gm.eval("return ns.version") == gm.eval("return ns.CHANGELOG[1].version"), log["v"]  # (versions restarted for Forever)
    # the TBC original's history stays out of the game: Forever's notes begin at 0.1.0
    assert gm.eval("return ns.CHANGELOG[#ns.CHANGELOG].version") == "0.1.0"
    for line in as_list(log["lines"]):
        assert len(line) <= 90, line                       # (the Changelog tab's rule, tests/boot-ui/test_changelog.py)
        assert "Karazhan" not in line and "Outland" not in line, line
    no_errors(w)


@case
def test_a_pre_forever_copy_never_looks_newer():
    """Versions restarted at 0.1.0 (2026-11-09). Every Forever copy before that said 1.5.5: that label is older than
    any version (Util.PRE_FOREVER_VERSION), so a guildmate's old copy brings no "newer version" nag, and a changelog
    read on an old copy leaves 0.1.0's What's New unread."""
    w, gm = world()
    cmp = gm.eval_py("local C = ns.Util.CompareVersions; return { C('1.5.5', '0.1.0'), C('0.1.0', '1.5.5'),"
                     " C('1.5.5', '0.0.1'), C('1.5.5', '1.5.5'), C('1.5.6', '1.5.4'), C('0.10.0', '0.9.3'),"
                     " C('1.0.0', '0.1.0') }")
    assert as_list(cmp) == [-1, 1, -1, 0, 1, 1, 1], cmp
    old = Client(w, "Oldcopy", class_file="MAGE", level=60, forever=True)
    old.load_addon()
    w.tick(30)
    old.eval("ns.version = '1.5.5'; ns.Sync:SendHello(true)")
    w.tick(5)
    assert not [l for l in gm.chat_frame if "newer DisasterZone version" in l], gm.chat_frame
    old.eval("ns.version = '9.0.0'; ns.Sync:SendHello(true)")      # a real newer build still says so
    w.tick(5)
    assert [l for l in gm.chat_frame if "newer DisasterZone version (9.0.0)" in l], gm.chat_frame
    no_errors(w)


@case
def test_every_page_and_the_demo_run_on_forever_data():
    """Every page opens on Forever's data (raids without loot yet, stub data files), then again in demo mode, whose
    sample raids and drops come from the same data."""
    w, gm = world()
    pages = as_list(gm.eval_py("local o = {} for _, d in ipairs(ns.MainFrame.__tabs and ns.MainFrame.__tabs() or {}) do"
                               " o[#o + 1] = d.key end return o")) or PAGES
    for demo in (False, True):
        if demo:
            gm.eval("ns.Demo:SetEnabled(true)")
            w.tick(1)
        for page in pages:
            gm.eval("ns.MainFrame:Open(...)", page)
            w.tick(0.4)
    gm.eval("ns.Demo:SetEnabled(false)")
    w.tick(0.5)
    no_errors(w)


@case
def test_class_restricted_items_come_from_the_tooltip():
    """Data/ItemClasses.lua is the TBC original's list (TBC item ids only) and Forever's item data has no tier or token
    classes: a Forever item's "Classes: ..." tooltip line says who may use it (Forever 0.2)."""
    w, gm = world()
    # no Forever item id is in the TBC list (its ids are 24046-37740, Forever's items are vanilla ids or its own)
    lo, hi = gm.eval_py("local lo, hi for id in pairs(ns.Data.ItemClasses) do lo = math.min(lo or id, id) "
                        "hi = math.max(hi or id, id) end return { lo, hi }")
    assert lo >= 24000 and hi < 38000, (lo, hi)
    w.define_item(16866, "Helm of Might", equip_loc="INVTYPE_HEAD", class_id=4, subclass_id=4, ilvl=66)
    w.define_item(16900, "Stormrage Cover", equip_loc="INVTYPE_HEAD", class_id=4, subclass_id=2, ilvl=76)
    w.define_item(18823, "Aged Core Leather Gloves", equip_loc="INVTYPE_HAND", class_id=4, subclass_id=2, ilvl=63)
    gm.eval("__MOCK.item_rec(16866).classes = { 'Warrior' } __MOCK.item_rec(16900).classes = { 'Druid', 'Rogue' }")
    got = gm.eval_py(r"""
        local DB = ns.ItemDB
        return { warrior = DB:CanClassUse(16866, 'WARRIOR'), mage = DB:CanClassUse(16866, 'MAGE'),
                 usable = DB:IsUsableBy(16866, 'PALADIN'), classes = DB:GetItemClasses(16900),
                 free = DB:CanClassUse(18823, 'ROGUE'), none = DB:GetItemClasses(18823) or false }""")
    assert got == {"warrior": True, "mage": False, "usable": False, "classes": ["DRUID", "ROGUE"], "free": True,
                   "none": False}, got
    # an item the client has not loaded yet is not judged (and asked again once it is)
    w.define_item(16867, "Legplates of Might", equip_loc="INVTYPE_LEGS", class_id=4, subclass_id=4, ilvl=66)
    gm.eval("__MOCK.item_rec(16867).classes = { 'Warrior' } local real = C_Item.IsItemDataCachedByID "
            "T_real_cached = real C_Item.IsItemDataCachedByID = function(id) if id == 16867 then return false end "
            "return real(id) end")
    assert gm.eval("return ns.ItemDB:CanClassUse(16867, 'MAGE')") is True
    gm.eval("C_Item.IsItemDataCachedByID = T_real_cached")
    assert gm.eval("return ns.ItemDB:CanClassUse(16867, 'MAGE')") is False
    no_errors(w)


@case
def test_tbc_client_keeps_its_content():
    w, gm = world(forever=False)
    assert gm.eval("return ns.MAX_PHASE") == 5
    assert gm.eval("return ns.DungeonRuns.HAS_HEROICS") is True
    assert "HellfireRamparts" in as_list(gm.eval_py("return ns.DungeonRuns:GetDungeonKeys()"))
    assert gm.eval("return ns.Recruit.MAX_LEVEL") == 70
    assert gm.eval("return ns.Atlas:HasEraSwitch()") is True
    no_errors(w)


if __name__ == "__main__":
    run_all(globals())
