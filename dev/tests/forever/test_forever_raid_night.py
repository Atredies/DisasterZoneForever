"""A raid night on WoW Forever (the retail 12.x engine, vanilla raids Barrow Deeps 10, Hyjal Summit 20, Onyxia's
Lair 40): what a raid leader and the loot council see and send.

  - Item tooltips: Forever has no OnTooltipSetItem script (probe: hasOnTooltipSetItem false), so UI/Tooltip.lua runs
    through TooltipDataProcessor's Item post-call there (and only for its own tooltips); the TBC path is unchanged.
  - Sends during a boss pull: Forever refuses every addon message from ENCOUNTER_START to ENCOUNTER_END
    (AddOnMessageLockdown). BossMod's DBM / BigWigs break, ClassPlanner, ReserveLR (LootReserve) and Patch sent on
    their own; they now go through Core/Comm.lua's hold (Comm:SendOrHold) and leave, in order, when the pull ends.
  - The raid session crest (Core/SessionInfo.lua, UI/SessionDrawer.lua): Forever's raids have no encounter ids or
    instance ids in the data yet, so the raid is found by its name and the bosses are matched to kills by name;
    the fight clock runs when the encounter's payload is secret; Hyjal's 13 boss faces wrap in the drawer.
  - Master loot exists on Forever (Enum.LootMethod.Masterlooter, C_PartyInfo.SetLootMethod, GiveMasterLoot: Forever
    UI source + probe), so the hand-out keeps working with a 40-player raid.

Run: luaenv/bin/python tests/forever/test_forever_raid_night.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors, strip_codes  # noqa: E402
from harness import World, Client  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"
SEAL = "Launcher\\seal"
HYJAL_NAMES = ["Bandalar", "Ancient of Decay", "Time-Lost Battalion"]


def as_list(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v)]
    return list(v or [])


def raid_world(n=20, forever=True, leader_name="Arakis War"):
    """The GM leads a raid of n on Forever (the others without DisasterZone, as extra members)."""
    w = World(realm=REALM)
    w.auto_session = False
    gm = Client(w, leader_name, class_file="WARRIOR", guild_rank=0, level=60, forever=forever)
    gm.load_addon()
    w.tick(5)
    extra = ["Raider%d" % i for i in range(1, n)]
    w.make_raid([gm], leader=gm, extra_members=extra)
    w.tick(3)
    return w, gm


def lock(c, on=True):
    """The Forever mock's chat lockdown, as a boss pull switches it (Enum.AddOnRestrictionType.Chat)."""
    c.eval("__MOCK.set_restriction(Enum.AddOnRestrictionType.Chat, ...)", on)


def txt(e):
    t = e["text"]
    return t.decode("latin-1") if isinstance(t, (bytes, bytearray)) else t


def sent(w, who, prefix, since=0):
    return [e for e in w.addon_log[since:] if e["sender"] == who.full_name and e["prefix"] == prefix]


# ---------------------------------------------------------------------------------------------------------------------
# 1. Item tooltips through TooltipDataProcessor
# ---------------------------------------------------------------------------------------------------------------------

def forever_item(c):
    """An item the Forever data knows (any boss / dungeon drop with an item record), for a BiS pick."""
    return c.eval("""
      for _, raid in ipairs(ns.ItemDB:GetRaids() or {}) do
        for _, b in ipairs(raid.bosses or {}) do
          for _, it in ipairs(b.items or {}) do
            local id = type(it) == 'table' and (it.itemID or it.id or it[1]) or it
            if type(id) == 'number' and ns.ItemDB:GetItem(id) then return id end
          end
        end
      end""")


@case
def test_forever_item_tooltip_shows_the_lines_via_tooltip_data_processor():
    w, c = solo("Arakis War", class_file="WARRIOR", guild_rank=0, level=60, forever=True)
    assert c.eval("return GameTooltip:HasScript('OnTooltipSetItem')") is False
    assert c.eval("return ns.Tooltip:HookTooltip(GameTooltip)") is False     # (already hooked at login)
    # (Forever's raid loot is not known before 9 Dec, so no item has wanters yet: the block's content is stubbed; what
    # it holds is tests/boot-ui/test_tooltip.py's business, this is about the hook)
    item = 16800
    c.eval("""
      __asked = {}
      local seal = '|TInterface\\\\AddOns\\\\DisasterZone\\\\Media\\\\Launcher\\\\seal:0|t'
      ns.Tooltip.BlockLines = function(_, id) __asked[#__asked + 1] = id
        return { { l = seal .. ' Wanted by Gina, Victhar' } }, false end""")
    lines = [strip_codes(l) for l, _ in c.show_tooltip_item(item) if SEAL in (l or "")]
    assert lines == [" Wanted by Gina, Victhar"] or lines == ["Wanted by Gina, Victhar"], c.show_tooltip_item(item)
    assert as_list(c.eval_py("return __asked")) == [item]
    # ItemRefTooltip (a clicked link) gets them too
    c.eval("ItemRefTooltip:SetOwner(UIParent, 'ANCHOR_NONE'); ItemRefTooltip:SetHyperlink('item:16800')")
    ref = c.eval_py("local o = {} for i = 1, ItemRefTooltip:NumLines() do local fs = _G['ItemRefTooltipTextLeft' .. i]"
                    " o[#o + 1] = fs and fs:GetText() or '' end return o")
    assert any(SEAL in (l or "") for l in as_list(ref)), ref
    # one post-call registered however many tooltips use it; lines are not added twice on a repeated set
    assert len(as_list(c.eval_py("return __MOCK.tooltip_post_calls[Enum.TooltipDataType.Item]"))) == 1
    c.eval("__MOCK.tooltip_item_post_calls(GameTooltip, ...)", item)
    again = [l for l, _ in c.show_tooltip_item(item) if SEAL in (l or "")]
    assert len(again) == len(lines), again
    no_errors(w)


@case
def test_forever_post_call_ignores_other_tooltips_and_secret_data():
    w, c = solo("Arakis War", class_file="WARRIOR", guild_rank=0, level=60, forever=True)
    c.eval("ns.BiS:SetSlot(1, 8, 'main', 16800)")
    # a tooltip DisasterZone never hooked (an embedded one): the post-call leaves it alone
    n = c.eval("""
      local tt = CreateFrame('GameTooltip', 'DZTestEmbeddedTooltip', UIParent, 'GameTooltipTemplate')
      tt:SetOwner(UIParent, 'ANCHOR_NONE'); tt:SetItemByID(16800)
      return tt:NumLines()""")
    lines = c.eval_py("""
      local out = {}
      for i = 1, DZTestEmbeddedTooltip:NumLines() do
        local fs = _G['DZTestEmbeddedTooltipTextLeft' .. i]; out[#out + 1] = fs and fs:GetText() or ''
      end
      return out""")
    assert not any(SEAL in (l or "") for l in as_list(lines)), lines
    # secret tooltip data (no link, a secret id): nothing added, no error
    c.eval("""
      GameTooltip:SetOwner(UIParent, 'ANCHOR_NONE'); GameTooltip:ClearLines()
      for _, fn in ipairs(__MOCK.tooltip_post_calls[Enum.TooltipDataType.Item]) do
        fn(GameTooltip, { type = 0, id = secretwrap(16800) })
      end""")
    assert c.eval("return GameTooltip:NumLines()") == 0
    no_errors(w)


@case
def test_tbc_item_tooltip_keeps_on_tooltip_set_item():
    w, c = solo("Alice", guild_rank=3)
    assert c.eval("return GameTooltip:HasScript('OnTooltipSetItem')") is True
    assert c.eval("return TooltipDataProcessor == nil") is True
    no_errors(w)


# ---------------------------------------------------------------------------------------------------------------------
# 2. Direct sends held through a boss pull
# ---------------------------------------------------------------------------------------------------------------------

@case
def test_break_timer_for_dbm_and_bigwigs_waits_for_the_pull_to_end():
    w, gm = raid_world(10)
    n0 = len(w.addon_log)
    lock(gm, True)
    assert gm.eval("return ns.Comm:InLockdown()") is True
    assert gm.eval("return ns.BossMod:SendBreak(5)") is True
    w.tick(2)
    assert sent(w, gm, "D5", n0) == [] and sent(w, gm, "BigWigs", n0) == []
    assert gm.eval("return __MOCK.lockdown_refused_by['D5']") is None      # held, never refused
    assert gm.eval("return ns.Comm:GetLockHeldCount()") >= 1
    lock(gm, False)
    w.tick(2)
    d5, bw = sent(w, gm, "D5", n0), sent(w, gm, "BigWigs", n0)
    assert len(d5) == 1 and "\tBT\t300" in txt(d5[0]), d5
    assert len(bw) == 1 and txt(bw[0]) == "P^Break^300", bw
    assert gm.eval("return ns.Comm:GetLockHeldCount()") == 0
    no_errors(w)


@case
def test_class_planner_messages_wait_for_the_pull_to_end():
    w, gm = raid_world(10)
    mod =gm.eval("for _, n in ipairs({ 'Blessings', 'Totems' }) do local m = ns[n]; "
                  "if m and m.planner and m.SendRaw then return n end end")
    assert mod, "no class planner module"
    pfx = gm.eval("return ns[...].planner.prefix", mod)
    gm.eval("ns[...].IsDemo = function() return false end", mod)
    n0 = len(w.addon_log)
    lock(gm, True)
    assert gm.eval("return ns[...]:SendRaw('HELLO')", mod) is True
    w.tick(2)
    assert sent(w, gm, pfx, n0) == []
    assert gm.eval("return __MOCK.lockdown_refused_by[...]", pfx) is None
    lock(gm, False)
    w.tick(3)
    assert [txt(e) for e in sent(w, gm, pfx, n0)] == ["HELLO"], sent(w, gm, pfx, n0)
    no_errors(w)


@case
def test_no_patch_traffic_while_updates_are_off():
    # 0.1.0 ships with no update key (Core/PatchKey.lua empty): no announce before, during or after a pull. (The
    # hold of the patch send path itself is exercised in dev/tests/patch once we have our own key.)
    w = World(realm=REALM)
    gm = Client(w, "Arakis War", class_file="WARRIOR", guild_rank=0, level=60, forever=True)
    gm.load_addon()
    assert gm.eval("return ns.Patch._Key()") is None
    lock(gm, True)
    w.tick(40)
    assert sent(w, gm, "CDLp1") == []
    assert gm.eval("return __MOCK.lockdown_refused_by['CDLp1']") is None
    lock(gm, False)
    w.tick(3)
    assert sent(w, gm, "CDLp1") == []
    no_errors(w)


@case
def test_lootreserve_session_info_waits_for_the_pull_to_end():
    # (the reserves suite's raid: Alice hosts; the lockdown is simulated as tests/compat does, on the mock's TBC
    # client, since the suite's raid runs Karazhan)
    sys.path.insert(0, os.path.join(TESTS, "reserves"))
    from rv_common import reserve_raid, open_reserves  # noqa: E402
    r = reserve_raid()
    alice = r["Alice"]
    alice.eval("__LOCK = true; ns.Compat.InChatLockdown = function() return __LOCK end")
    n0 = len(r.w.addon_log)
    open_reserves(r, n=1, tick=4)            # (SessionInfo for LootReserve goes out 1 s after the opening)
    lr = [e for e in r.w.addon_log[n0:] if e["sender"] == alice.full_name and e["prefix"].startswith("LootReserve")]
    assert lr == [], lr
    assert alice.eval("return ns.Comm:GetLockHeldCount()") >= 1
    alice.eval("__LOCK = false")
    r.w.tick(3)
    lr = [e for e in r.w.addon_log[n0:] if e["sender"] == alice.full_name and e["prefix"].startswith("LootReserve")]
    assert lr, "LootReserve's SessionInfo never went out"
    assert alice.eval("return ns.Comm:GetLockHeldCount()") == 0
    no_errors(r.w)


@case
def test_comm_send_or_hold_keeps_order_with_comm_messages():
    w, gm = raid_world(10)
    lock(gm, True)
    gm.eval("""
      __order = {}
      ns.Comm:SendOrHold(function(a, b) __order[#__order + 1] = a .. b end, 'x', 1)
      ns.Comm:SendOrHold(function() __order[#__order + 1] = 'y' end)""")
    assert as_list(gm.eval_py("return __order")) == []
    lock(gm, False)
    w.tick(2)
    assert as_list(gm.eval_py("return __order")) == ["x1", "y"]
    # outside a lockdown it runs at once
    assert gm.eval("local ran; local now = ns.Comm:SendOrHold(function() ran = true end); return now and ran") is True
    no_errors(w)


# ---------------------------------------------------------------------------------------------------------------------
# 3. The raid session crest at Forever sizes
# ---------------------------------------------------------------------------------------------------------------------

def session_info(c):
    return c.eval_py("""
      local i = ns.SessionInfo:Get()
      if not i then return nil end
      local b = {}
      for k, x in ipairs(i.bosses or {}) do b[k] = { name = x.name, killed = x.killed, enc = x.enc } end
      return { zone = i.zone, raidKey = i.raidKey, kills = i.kills, total = i.total, bosses = b,
               fight = i.fight and { i = i.fight.i, name = i.fight.name, since = i.fight.since } or nil }""")


@case
def test_crest_finds_hyjal_by_name_and_counts_kills_by_boss_name():
    w, gm = raid_world(20)
    w.enter_instance(name="Hyjal Summit", instance_id=9101, max_players=20, difficulty_id=9)
    w.tick(1)
    gm.eval("ns.GroupRules:SetSession(true, nil, { loot = true, rolls = true, lock = false })")
    w.tick(2)
    i = session_info(gm)
    assert i and i["raidKey"] == "HyjalForever", i
    bosses = as_list(i["bosses"])
    assert len(bosses) == 13 and [b["name"] for b in bosses[:3]] == HYJAL_NAMES, bosses
    assert i["total"] == 13
    # a pull: the fight shows the boss (matched by name: the data has no encounter ids)
    gm.fire("ENCOUNTER_START", 3101, "Bandalar", 9, 20)
    i = session_info(gm)
    assert i["fight"] and i["fight"]["i"] == 1 and i["fight"]["name"] == "Bandalar", i
    gm.fire("ENCOUNTER_END", 3101, "Bandalar", 9, 20, 1)
    w.tick(2)
    i = session_info(gm)
    assert i.get("fight") is None
    assert as_list(i["bosses"])[0]["killed"] is True, i
    assert i["kills"] == 1, i
    no_errors(w)


@case
def test_crest_fight_clock_runs_with_a_secret_encounter():
    w, gm = raid_world(10)
    w.enter_instance(name="Barrow Deeps", instance_id=9102, max_players=10, difficulty_id=9)
    w.tick(1)
    gm.eval("ns.GroupRules:SetSession(true, nil, { loot = true, rolls = true, lock = false })")
    w.tick(1)
    gm.eval("__MOCK.fire('ENCOUNTER_START', secretwrap(3201, 'Deepscar Matriarch', 9, 10))")
    i = session_info(gm)
    assert i["fight"] is not None and i["fight"]["since"] is not None, i
    assert i["fight"].get("i") is None and i["fight"].get("name") is None
    w.tick(5)
    clock = gm.eval("local i = ns.SessionInfo:Get(); return ns.SessionInfo:Clock(GetTime() - i.fight.since, true)")
    assert clock == "0:05", clock
    gm.fire("ENCOUNTER_END", 3201, "Deepscar Matriarch", 9, 10, 0)
    no_errors(w)


@case
def test_crest_onyxia_40_and_the_drawer_wraps_hyjal_faces():
    w, gm = raid_world(40)
    assert gm.eval("return GetNumGroupMembers()") == 40
    w.enter_instance(name="Onyxia's Lair", instance_id=249, max_players=40, difficulty_id=9)
    w.tick(1)
    gm.eval("ns.GroupRules:SetSession(true, nil, { loot = true, rolls = true, lock = false })")
    w.tick(2)
    i = session_info(gm)
    assert i["raidKey"] == "Onyxia" and i["total"] == 1 and as_list(i["bosses"])[0]["name"] == "Onyxia", i
    # Hyjal's 13 faces in the drawer stay inside it (the demo night is Hyjal on Forever)
    d = gm.eval_py("""
      local info = ns.SessionInfo:Demo('between')
      local f = ns.SessionDrawer:Show({ line = UIParent }, info,
        { state = 'session', aud = 'lead', name = function(k) return k end })
      local xs, w = {}, f:GetWidth()
      for _, c in ipairs({ f:GetChildren() }) do
        if c:IsShown() then
          local p, rel, rp, x, y = c:GetPoint(1)
          if p == 'TOP' and rp == 'TOPLEFT' then xs[#xs + 1] = { x = x, y = y } end
        end
      end
      return { n = #info.bosses, w = w, xs = xs }""")
    faces = as_list(d["xs"])
    assert d["n"] == 13 and len(faces) == 13, d
    assert all(0 < f["x"] < d["w"] for f in faces), faces
    assert len({f["y"] for f in faces}) == 2, faces       # two rows
    no_errors(w)


@case
def test_demo_night_has_no_tbc_items():
    w, c = solo("Arakis War", class_file="WARRIOR", guild_rank=0, level=60, forever=True)
    ids = c.eval_py("""
      local out = {}
      for _, m in ipairs({ 'loot', 'done' }) do
        local i = ns.SessionInfo:Demo(m)
        for _, d in ipairs(i.drops or {}) do out[#out + 1] = d.itemID end
        for _, t in ipairs(i.trades or {}) do out[#out + 1] = t.itemID end
      end
      return out""")
    ids = as_list(ids)
    assert ids and all(i < 25000 for i in ids), ids      # (TBC items are 25000 and up)
    no_errors(w)


# ---------------------------------------------------------------------------------------------------------------------
# 4. Master loot on Forever
# ---------------------------------------------------------------------------------------------------------------------

@case
def test_master_loot_is_recognised_in_a_forever_raid():
    w, gm = raid_world(40)
    assert gm.eval("return Enum.LootMethod.Masterlooter") == 2
    assert gm.eval("return ns.Util.IsPlayerMasterLooter()") is False
    w.set_master_looter(gm)
    w.tick(1)
    assert gm.eval("return ns.Util.IsPlayerMasterLooter()") is True
    no_errors(w)


if __name__ == "__main__":
    run_all()
