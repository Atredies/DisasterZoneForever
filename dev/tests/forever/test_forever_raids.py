"""The raid planner on WoW Forever: its raids (Barrow Deeps 10, Hyjal Summit 20, Onyxia's Lair 40; Data/ForeverRaids.lua),
raid sizes 10 / 20 / 40, the level-60 cap, and `/dz raiddata` (Core/RaidLearn.lua), which records raids and bosses the
game shows so a new raid can be pasted into the data file.

Seen in game 2026-11-08 before this: the Raids filter listed Karazhan to Sunwell and a new raid said "This raid is for
level 70 characters".

Run: luaenv/bin/python tests/forever/test_forever_raids.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"


def gm_world(forever=True):
    w = World(realm=REALM)
    gm = Client(w, "Arakis War", class_file="WARRIOR", guild_rank=0, level=60, forever=forever)
    gm.load_addon()
    w.tick(5)
    return w, gm


def as_list(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v)]
    return list(v or [])


def create(cl, **f):
    return cl.eval_py("local f = ...; local ok, r = ns.RaidPlan:CreateRaid(f); return { ok = ok, r = r }", f)


@case
def test_the_planner_offers_the_forever_raids():
    w, gm = gm_world()
    rows = as_list(gm.eval_py("local o = {} for _, i in ipairs(ns.RaidPlan:GetInstances()) do"
                              " o[#o + 1] = { key = i.key, name = i.name, size = i.size } end return o"))
    assert [(r["key"], r["name"], r["size"]) for r in rows] == [
        ("barrow", "Barrow Deeps", 10), ("hyjal", "Hyjal Summit", 20), ("ony", "Onyxia's Lair", 40),
        ("other", "Other", 40)], rows
    assert as_list(gm.eval_py("return ns.RaidPlan:GetSizes()")) == [10, 20, 40]
    assert gm.eval("return ns.RaidPlan:GetMaxLevel()") == 60
    no_errors(w)


@case
def test_a_raid_takes_its_size_and_level_60():
    w, gm = gm_world()
    t = gm.eval("return GetServerTime() + 86400")
    for key, size in (("barrow", 10), ("hyjal", 20), ("ony", 40)):
        res = create(gm, i=key, t=t, ml=60)
        assert res["ok"] is True, (key, res)
        v = gm.eval_py("local v = ns.RaidPlan:GetRaid(...); return { sz = v.sz, ml = v.ml }", res["r"])
        assert v == {"sz": size, "ml": 60}, (key, v)
    # 25 is a TBC size; 70 is past the cap
    assert create(gm, i="ony", t=t, sz=25)["ok"] is False
    bad = create(gm, i="ony", t=t, ml=70)
    assert bad["ok"] is False and "60" in str(bad["r"]), bad
    no_errors(w)


@case
def test_the_new_raid_window_creates_the_raid_you_pick():
    """In game 2026-11-09: New raid > Hyjal Summit > Create raid said "Pick a raid." (the window started on the TBC
    "kara", hidden on Forever, so Hyjal became the night's second raid)."""
    w, gm = gm_world()
    for key, size in (("hyjal", 20), ("ony", 40), ("barrow", 10)):
        res = gm.eval_py("""
            local P, key, default = ns.RaidPlanUI, ...
            P:OpenEditor()
            if key ~= default then P:ToggleEditorRaid(default) P:ToggleEditorRaid(key) end
            local before = #ns.RaidPlan:GetRaids()
            local ok = P:SaveEditor()
            local list = ns.RaidPlan:GetRaids()
            local v = list[#list]
            return { ok = ok and true or false, n = #list - before, i = v and v.i, sz = v and v.sz }
        """, key, "barrow")
        assert res == {"ok": True, "n": 1, "i": key, "sz": size}, (key, res)
    no_errors(w)


@case
def test_forty_players_make_eight_groups():
    w, gm = gm_world()
    assert gm.eval("return ns.RaidComp:GroupCount(40)") == 8
    assert gm.eval("return ns.RaidComp:GroupCount(20)") == 4
    assert gm.eval("return ns.RaidComp:GroupCount(10)") == 2
    sizes = as_list(gm.eval_py("local o = {} for _, p in ipairs(ns.RaidComp.PRESETS) do o[#o + 1] = p.size end return o"))
    assert sorted(sizes) == [10, 20, 40], sizes
    for p in as_list(gm.eval_py("local o = {} for _, p in ipairs(ns.RaidComp.PRESETS) do"
                                " o[#o + 1] = { size = p.size, n = ns.RaidComp:CompSize(p.cp) } end return o")):
        assert p["n"] == p["size"], p
    no_errors(w)


@case
def test_tbc_client_keeps_its_raids():
    w, gm = gm_world(forever=False)
    keys = as_list(gm.eval_py("local o = {} for _, i in ipairs(ns.RaidPlan:GetInstances()) do o[#o + 1] = i.key end return o"))
    assert keys[0] == "kara" and "swp" in keys and "barrow" not in keys, keys
    assert as_list(gm.eval_py("return ns.RaidPlan:GetSizes()")) == [10, 25]
    assert gm.eval("return ns.RaidPlan:GetMaxLevel()") == 70
    no_errors(w)


@case
def test_raiddata_learns_a_new_raid_and_its_bosses():
    w, gm = gm_world()
    w.enter_instance(name="Barrow Deeps", instance_id=2900, instance_type="raid", max_players=10, difficulty_id=3)
    gm.fire("ENCOUNTER_START", 3101, "Barrow Wight", 3, 10)
    gm.fire("ENCOUNTER_END", 3101, "Barrow Wight", 3, 10, 1)
    w.enter_instance(name="Onyxia's Lair", instance_id=249, instance_type="raid", max_players=40, difficulty_id=9)
    # a raid Blizzard adds later, not in Data/ForeverRaids.lua
    w.enter_instance(name="Molten Core", instance_id=409, instance_type="raid", max_players=40, difficulty_id=9)
    gm.fire("ENCOUNTER_START", 663, "Lucifron", 9, 40)
    text = "\n".join(as_list(gm.eval_py("return ns.RaidLearn:Report()")))
    assert '-- (in the list: set its instanceID) { key = "?", name = "Barrow Deeps"' in text, text
    assert "instanceID = 2900" in text and "3101 Barrow Wight" in text, text
    assert '-- (in the list) { key = "?", name = "Onyxia\'s Lair"' in text, text
    assert 'NEW { key = "?", name = "Molten Core", short = "?", size = 40, level = 60, instanceID = 409' in text, text
    assert "663 Lucifron" in text, text
    # the group finder: its raid category flagged, a 10-player dungeon only listed
    gm.eval("""__MOCK.lfg_activities[1401] = { fullName = 'Upper Blackrock Spire', categoryID = 2, maxNumPlayers = 10,
      minLevel = 0, mapID = 229, isPvpActivity = false, isRatedPvpActivity = false }""")
    gm.eval("SlashCmdList.DISASTERZONE('raiddata')")      # (what /dz raiddata runs: records the group finder too)
    text = "\n".join(as_list(gm.eval_py("return ns.RaidLearn:Report()")))
    assert "Upper Blackrock Spire [Dungeons], 10 players, level 0, map 229\n" in text + "\n", text
    assert "Karazhan [Raids], 10 players" in text and "map 532  (not in the list)" in text, text
    no_errors(w)


if __name__ == "__main__":
    run_all()
