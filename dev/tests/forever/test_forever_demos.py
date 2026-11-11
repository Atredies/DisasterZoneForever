"""WoW Forever: the demos and their art show Forever's world, not TBC's. On a Forever client no demo names a TBC raid,
zone or system (Karazhan ... Outland, arenas, Badge of Justice runs), every demo item is a Forever item (the Wowhead
Forever cache, dev/generators/data/forever_items.json), the combat demos whose features Forever hides (meters,
threat, boss mods) aren't offered, and the nav cards, window header and raid art use vanilla loading screens.

Run: luaenv/bin/python tests/forever/test_forever_demos.py [-k name]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
DEV = os.path.dirname(TESTS)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"
TBC_WORDS = ["Karazhan", "Gruul", "Magtheridon", "Serpentshrine", "Tempest Keep", "Black Temple", "Shattrath",
             "Nagrand", "Outland", "Terokkar", "Hellfire", "Zangarmarsh", "Netherstorm", "Illidan", "Vashj",
             "Maulgar", "Void Reaver", "Hydross", "Sunwell", "Badge of Justice", "badge run"]
# (arena: the bracket game; heroic: the dungeon mode, not Heroic Strike)
TBC_RE = re.compile("|".join(re.escape(w) for w in TBC_WORDS) + r"|\barenas?\b|\bheroics?\b(?! strike)",
                    re.IGNORECASE)
# the TBC loading screens (FileDataIDs, wowdev community listfile): Auchindoun, Black Temple, Blade's Edge Arena,
# Coilfang, Gruul's Lair, Hellfire Citadel (3), Karazhan, Nagrand Arena, Netherstorm BG, Outland, Ruins of Lordaeron
# arena, Sunwell (2), Tempest Keep
TBC_SCREENS = {131821, 131826, 131828, 131832, 131842, 131844, 131845, 131846, 131849, 131853, 131855, 131860,
               131867, 131873, 131874, 131875}

# Every string value (not key) under the tables the given Lua expressions return.
SCAN = """
local seen, out = {}, {}
local function scan(v, d)
    if type(v) == "string" then out[#out + 1] = v
    elseif type(v) == "table" and not seen[v] and d < 14 and not v.GetObjectType then
        seen[v] = true
        for _, x in pairs(v) do scan(x, d + 1) end
    end
end
for _, fn in ipairs(__dzScan) do
    local ok, v = pcall(fn)
    if ok then scan(v, 0) else out[#out + 1] = "SCAN ERROR " .. tostring(v) end
end
return out
"""


def forever_items():
    with open(os.path.join(DEV, "generators", "data", "forever_items.json"), encoding="utf-8") as f:
        return {int(k) for k, v in json.load(f).items() if v}


def world(forever=True):
    w = World(realm=REALM)
    gm = Client(w, "Arakis War", class_file="PALADIN", guild_rank=0, level=60, forever=forever)
    gm.load_addon()
    w.tick(5)
    gm.eval("ns.Demo:SetEnabled(true)")
    w.tick(1)
    return w, gm


def as_list(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v)]
    return list(v or [])


def scan(gm, exprs):
    gm.eval("__dzScan = {} " + " ".join("__dzScan[#__dzScan + 1] = function() return %s end" % e for e in exprs))
    return as_list(gm.eval_py(SCAN))


def tbc_hits(texts):
    return sorted({t for t in texts if isinstance(t, str) and TBC_RE.search(t)})


@case
def test_demo_texts_name_no_tbc_content():
    w, gm = world()
    texts = scan(gm, [
        "ns.DungeonRuns:GetRuns()",
        "ns.GuildMap:GetEntries()",
        "ns.Polls:BuildDemo()",
        "{ ns.RecruitMessage:GetMessages(), ns.RecruitMessage:GetParts() }",
        "ns.Blessings.planner.buildDemo()",
        "(function() ns.Profiles:SetDemo(true) return ns.Profiles.demo end)()",
        "ns.Wardrobe:DemoList()",
        "ns.Prized:BuildDemo()",
        "ns.Feedback:DemoStore()",
        "ns.FeedbackPlan:DemoStore()",
        "{ ns.Recruit:Live('Kaelthorn-x'), ns.Recruit:Live('Aurelith-x'), ns.Recruit:Live('Bramble-x') }",
        "ns.GroupPvP:GetTeams()",
        "ns.Events:BuildDemo()",
        "ns.EventBlocks:Examples()",
        "{ ns.EventBlocks:Blank(), ns.EventBlocks.ART }",
        "{ ns.Demo:Parts('screen'), ns.Demo:Parts('moment') }",
        "{ ns.LookUnits.Fake('target'), ns.LookUnits.Fake('focus'), ns.LookUnits.Fake('tot') }",
        "ns.Tour:Get('welcome').chapters",
    ])
    errors = [t for t in texts if t.startswith("SCAN ERROR")]
    assert not errors, errors
    assert len(texts) > 300, len(texts)
    hits = tbc_hits(texts)
    assert not hits, hits
    joined = " | ".join(texts)
    for forever in ("Scholomance", "Barrow Deeps", "Onyxia", "Tanaris", "Stormwind"):
        assert forever in joined, forever
    no_errors(w)


@case
def test_demo_items_are_forever_items():
    w, gm = world()
    ids = as_list(gm.eval_py("""
        local o = {}
        for _, id in pairs(ns.Wardrobe.DEMO_WORN) do if id then o[#o + 1] = id end end
        for _, out in ipairs(ns.Wardrobe:DemoList()) do
            for _, s in pairs(out.slots) do if type(s) == 'table' and s.id then o[#o + 1] = s.id end end
        end
        for _, it in pairs(ns.Prized:BuildDemo().I) do
            for _, id in ipairs(it.ids or {}) do o[#o + 1] = tonumber(id) end
        end
        return o
    """))
    assert len(ids) > 30, ids
    known = forever_items()
    bad = sorted({i for i in ids if i not in known})
    assert not bad, bad
    no_errors(w)


@case
def test_hidden_combat_demos_and_level_60():
    w, gm = world()
    keys = as_list(gm.eval_py("local o = {} for _, d in ipairs(ns.Demo:Parts('screen')) do o[#o + 1] = d.key end return o"))
    for k in ("meters", "threat", "bossmods"):
        assert k not in keys, (k, keys)
    assert "plates" in keys and "sct" in keys, keys
    assert gm.eval("return next(ns.GroupPvP:GetTeams()) == nil") is True
    levels = as_list(gm.eval_py("local o = {} for _, m in ipairs(ns.Blessings.planner.buildDemo().roster) do"
                                " o[#o + 1] = m.level end return o"))
    assert levels and set(levels) == {60}, levels
    assert gm.eval("return #ns.Blessings.planner.buildDemo().roster") == 20
    # no Salvation / Light / Sanctuary handed out (Forever has none)
    gone = gm.eval("local n = 0 for _, row in pairs(ns.Blessings.planner.buildDemo().store.assign) do"
                   " for _, bi in pairs(row) do if bi == 4 or bi == 5 or bi == 6 then n = n + 1 end end end return n")
    assert gone == 0, gone
    # the Welcome tour skips the hidden Strategies step
    skip = gm.eval("for _, ch in ipairs(ns.Tour:Get('welcome').chapters) do for _, s in ipairs(ch.steps) do"
                   " if s.title == 'Strategies' then return s.skip and s.skip() end end end return 'missing'")
    assert skip is True, skip
    no_errors(w)


@case
def test_art_is_vanilla():
    w, gm = world()
    arts = as_list(gm.eval_py("local o = {} for k, i in pairs(ns.NavMenu.INFO) do o[#o + 1] = i.art end return o"))
    assert all(isinstance(a, (int, float)) for a in arts), arts
    assert not (set(int(a) for a in arts) & TBC_SCREENS), arts
    raid = as_list(gm.eval_py("local o = {} for k, m in pairs(ns.Data.RaidMeta) do o[#o + 1] = m.art[1] end"
                              " o[#o + 1] = ns.Data.RaidMetaOther.art[1] return o"))
    assert not (set(int(a) for a in raid) & TBC_SCREENS), raid
    ev = as_list(gm.eval_py("local o = {} for _, a in ipairs(ns.EventBlocks.ART) do o[#o + 1] = a[1] end return o"))
    for k in ("nagrand", "blades", "ruins", "eots", "outland"):
        assert k not in ev, (k, ev)
    # every page and the demo open on these (art and demo data)
    for page in ("home", "mybis", "wardrobe", "events", "dungeons", "map", "changelog", "feedback", "settings"):
        gm.eval("ns.MainFrame:Open(...)", page)
        w.tick(0.4)
    no_errors(w)


@case
def test_leftover_texts_follow_forever():
    """Branch fix/forever-leftovers: the class-tool demo lines, the combat-text pull, Azeromon's raid rares."""
    w, gm = world()
    parts = {d[0]: d[1] for d in as_list(gm.eval_py(
        "local o = {} for _, d in ipairs(ns.Demo:Parts('screen', 'class')) do o[#o + 1] = { d.key, d.label .. ': '"
        " .. (d.desc or '') } end return o"))}
    assert "Aimed Shot" in parts["shot"] and "Steady" not in parts["shot"], parts["shot"]
    assert "twist" not in parts["swing"].lower() and "Seal of Command" not in parts["swing"], parts["swing"]
    # the combat text pull: no shaman's Windfury on a paladin
    gm.eval("ns.CombatTextUI:QueuePull(false)")
    spells = as_list(gm.eval_py("local o = {} for _, q in ipairs(ns.CombatTextUI.st.queue) do"
                                " o[#o + 1] = (q.ev.spell or '') .. '|' .. (q.ev.gname or '') end return o"))
    assert spells and not any("Windfury" in s for s in spells), spells
    assert any("Hand of Justice" in s for s in spells), spells
    # Azeromon's raid rares: their words name Forever's raids, not TBC's
    rares = as_list(gm.eval_py("local o = {} for _, r in ipairs(ns.AzeroData.raidRares) do local s ="
                               " ns.AzeroData.species[r.sp] o[#o + 1] = s.name .. ': ' .. s.desc end return o"))
    assert len(rares) >= 9, rares
    hits = tbc_hits(rares)
    assert not hits, hits
    assert not any("Al'ar" in r or "Nightbane" in r for r in rares), rares
    assert gm.eval("return ns.AzeroData.species.nightbane.name") == "Onyxian Whelpling"
    no_errors(w)


@case
def test_tbc_client_keeps_its_demos():
    w, gm = world(forever=False)
    keys = as_list(gm.eval_py("local o = {} for _, d in ipairs(ns.Demo:Parts('screen')) do o[#o + 1] = d.key end return o"))
    assert "meters" in keys and "bossmods" in keys, keys
    texts = scan(gm, ["ns.Polls:BuildDemo()", "ns.EventBlocks:Examples()"])
    assert any("Karazhan" in t for t in texts) and any("Nagrand" in t for t in texts)
    assert gm.eval("return ns.Wardrobe.DEMO_WORN[1]") == 29073
    no_errors(w)


if __name__ == "__main__":
    run_all(globals())
