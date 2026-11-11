"""Go-live readiness, scenario 4: what goes wrong on a real raid night, on WoW Forever with DisasterZone 0.1.0.

  * a raider /reloads mid-raid (between pulls, with a roll open): the session, the council and the roll come back,
    and the raider still rolls;
  * a raider disconnects during a roll after rolling, and another before: the roll ends and is awarded without
    them; the one who left gets the result when back;
  * the raid leader changes mid-raid (the lead passes to an officer): the raid session goes on under the new leader;
  * the master looter leaves the raid during the loot: a new master looter takes over and hands out the rest;
  * two officers edit the same raid plan at the same moment, and two officers save the raid leaders list at once:
    every client ends up with the same version.
Every client: no Lua error.

Run: luaenv/bin/python tests/golive/test_golive_resilience.py [-k name]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl_common import case, run_all, no_errors, note, key, quiet, state, online, diverging  # noqa: E402
from gl_raid import (form_raid, run_loot, active, results, ledger, PROBE, ONY_GUID, ITEMS,  # noqa: E402
                     SAPPHIRON_DRAPE, RING_OF_BINDING, NETHERWIND_CROWN, LEADER)

BARROW = {"name": "Barrow Deeps", "id": 9102}
BOSS_GUID = "Creature-0-1-2-3-30001-000AAA"


def small_raid(size=10, seed=21):
    n = form_raid(size, "barrow", BARROW, seed=seed)
    return n


def open_roll(n, item, by=LEADER):
    ml = n["by"][by]
    ml.open_loot([(item, 4)], source_guid=BOSS_GUID)
    n["w"].tick(2)
    ml.eval("ns.DropPanel:StartRoll(...)", item, 1)
    n["w"].tick(1.5)
    s = active(ml)
    assert s and s["i"] == item, s
    return s


def award(n, sid, winner, by=LEADER):
    ml = n["by"][by]
    ml.eval("ns.Roll:End(...)", sid)
    n["w"].tick(1)
    ml.eval("ns.DropPanel:AwardRoll(...)", sid, winner)
    n["w"].tick(0.3)
    if "DISASTERZONE_GIVE_ITEM" in ml.popups():
        ml.accept_popup("DISASTERZONE_GIVE_ITEM")
    elif "DISASTERZONE_CONFIRM_AWARD" in ml.popups():
        ml.accept_popup("DISASTERZONE_CONFIRM_AWARD")
    n["w"].tick(3)


def roll_state(c, sid):
    return c.eval_py("local s = ns.Roll:Get(...); return s and { state = s.state, winner = s.winner } or nil", sid)


# ---------------------------------------------------------------------------------------------------------------------
@case
def test_reload_mid_raid_with_a_roll_open():
    n = small_raid()
    w, by = n["w"], n["by"]
    me = by["Megumin Chan"]
    s = open_roll(n, SAPPHIRON_DRAPE)
    me.relog()                             # /reload while the roll is open
    w.tick(10, 0.25)
    me.eval(PROBE)
    # the session and the council are back
    assert me.eval("return ns.GroupRules:GetSession() ~= nil") is True
    assert me.eval("return ns.Guild:IsCouncil(...)", key("Missy Badshot")) is True
    # Forever 0.2: the reloaded raider asks for open rolls (RQ) and the starter sends its RS again with the time
    # left, so the roll and its window come back (before 0.2 the raider saw no window until the next drop)
    got = me.eval_py("local s = ns.Roll:Get(...); return s and { state = s.state } or nil", s["id"])
    assert got == {"state": "open"}, got
    left = me.eval("return ns.Roll:GetTimeLeft(...)", s["id"])
    assert left and 0 < left <= 30 - 10, left
    assert me.eval("return ns.RollFrame.frame ~= nil and ns.RollFrame.frame:IsShown()") is True
    w.player_roll("Megumin Chan", 97)
    w.player_roll("Tobin Greyhill", 40)
    w.tick(2)
    res = results(by[LEADER], s["id"])
    assert res and res[0]["key"] == key("Megumin Chan"), res
    award(n, s["id"], key("Megumin Chan"))
    for name in ("Arakis War", "Missy Badshot", "Tobin Greyhill"):
        assert roll_state(by[name], s["id"]) == {"state": "awarded", "winner": key("Megumin Chan")}, (
            name, roll_state(by[name], s["id"]))
    # the next drop reaches the reloaded raider as usual
    s2 = open_roll(n, RING_OF_BINDING)
    assert s2 and s2["id"] != s["id"], s2
    assert me.eval_py("local s = ns.Roll:Get(...); return s and s.state", s2["id"]) == "open"
    no_errors(w)


@case
def test_reload_during_a_boss_pull():
    """A /reload in the middle of a pull: the client comes back while the chat lockdown is still on (it lasts until
    ENCOUNTER_END), so its login traffic (HELLO, the raid's questions) must wait for the end of the pull."""
    n = small_raid(seed=26)
    w, by = n["w"], n["by"]
    me = by["Megumin Chan"]
    group = [c for c in n["cs"] if c.loaded]
    for c in group:
        c._fire("ENCOUNTER_START", 3201, "Deepscar Matriarch", 9, 10)
        c.set_combat(True)
    w.tick(3)
    me.preload_lua = ("__MOCK.set_restriction(Enum.AddOnRestrictionType.Encounter, true);"
                      " __MOCK.set_restriction(Enum.AddOnRestrictionType.Chat, true); __MOCK.combat = true")
    me.relog()
    me.preload_lua = None
    mark = len(w.addon_log)
    w.tick(25, 0.25)
    during = [e for e in w.addon_log[mark:] if e["sender"] == me.full_name]
    held = me.eval("return ns.Comm:GetLockHeldCount()")
    refused = me.eval("return __MOCK.lockdown_refused or 0")
    for c in group:
        c._fire("ENCOUNTER_END", 3201, "Deepscar Matriarch", 9, 10, 1)
        c.set_combat(False)
    w.tick(10, 0.25)
    after = [e for e in w.addon_log[mark:] if e["sender"] == me.full_name]
    note("reloaded mid-pull: %d sends held during the pull, %d refused, %d on the wire after it" % (
        held, refused, len(after)))
    assert during == [] and refused == 0, (len(during), refused)
    assert held > 0 and len(after) > 0, (held, len(after))
    assert me.eval("return ns.GroupRules:GetSession() ~= nil") is True
    no_errors(w)


@case
def test_disconnect_during_a_roll():
    n = small_raid(seed=22)
    w, by = n["w"], n["by"]
    s = open_roll(n, RING_OF_BINDING)
    w.player_roll("Tobin Greyhill", 99)
    w.tick(1)
    by["Tobin Greyhill"].logout()            # rolled, then disconnected
    by["Elra Northwind"].logout()            # disconnected before rolling
    w.player_roll("Garrick Underbough", 60)
    w.tick(3)
    res = results(by[LEADER], s["id"])
    assert [r["key"] for r in res][:2] == [key("Tobin Greyhill"), key("Garrick Underbough")], res
    # the leader gives it to the best roller still here (master loot can't hand an item to someone offline)
    award(n, s["id"], key("Garrick Underbough"))
    assert roll_state(by["Missy Badshot"], s["id"])["winner"] == key("Garrick Underbough")
    # back online: no error, and the raid's council still has the award in the loot log
    by["Tobin Greyhill"].login()
    by["Elra Northwind"].login()
    w.tick(30, 0.25)
    for name in ("Arakis War", "Missy Badshot", "Aurel Namahs"):
        got = [(e["i"], e["w"]) for e in ledger(by[name]) if e["i"] in ITEMS]
        assert got == [(RING_OF_BINDING, key("Garrick Underbough"))], (name, got)
    no_errors(w)


@case
def test_raid_leader_changes_mid_raid():
    n = small_raid(seed=23)
    w, by = n["w"], n["by"]
    missy = by["Missy Badshot"]
    sess0 = by["Megumin Chan"].eval("local s = ns.GroupRules:GetSession(); return s and s.id")
    assert sess0
    w.promote(by[LEADER], "Missy Badshot")
    w.tick(20, 0.25)
    assert missy.eval("return UnitIsGroupLeader('player')") is True
    # the session goes on: the new leader is its authority, every raider still sees one
    for c in online(n["cs"]):
        assert c.eval("return ns.GroupRules:GetSession() ~= nil") is True, c.name
    assert missy.eval("return ns.GroupRules:IsAuthority()") is True
    sess1 = by["Megumin Chan"].eval("local s = ns.GroupRules:GetSession(); return s and s.id")
    note("raid session id before / after the lead passed: %s / %s" % (sess0, sess1))
    # the new leader runs a roll; the old leader (still the master looter) hands it out
    missy.open_loot([(NETHERWIND_CROWN, 4)], source_guid=BOSS_GUID)
    w.tick(1)
    missy.eval("ns.DropPanel:StartRoll(...)", NETHERWIND_CROWN, 1)
    w.tick(1.5)
    s = active(missy)
    assert s and s["i"] == NETHERWIND_CROWN, s
    w.player_roll("Aurel Namahs", 88)
    w.tick(2)
    award(n, s["id"], key("Aurel Namahs"), by="Missy Badshot")
    assert roll_state(by["Megumin Chan"], s["id"]) == {"state": "awarded", "winner": key("Aurel Namahs")}
    no_errors(w)


@case
def test_master_looter_leaves_during_the_loot():
    n = small_raid(seed=24)
    w, by = n["w"], n["by"]
    blu, missy = by[LEADER], by["Missy Badshot"]
    blu.open_loot([(SAPPHIRON_DRAPE, 4), (RING_OF_BINDING, 4)], source_guid=BOSS_GUID)
    w.tick(2)
    blu.eval("ns.DropPanel:StartRoll(...)", SAPPHIRON_DRAPE, 1)
    w.tick(1.5)
    s1 = active(blu)
    w.player_roll("Tobin Greyhill", 70)
    w.tick(2)
    award(n, s1["id"], key("Tobin Greyhill"))
    # the master looter (and leader) has to go: the lead and master loot pass to Missy, Blu leaves the group
    w.promote(blu, "Missy Badshot")
    w.tick(2)
    w.uninvite(missy, LEADER)
    w.set_master_looter(missy)
    w.tick(20, 0.25)
    assert missy.eval("return ns.Util.IsPlayerMasterLooter()") is True
    for c in online(n["cs"]):
        if c is not blu:
            assert c.eval("return ns.GroupRules:GetSession() ~= nil") is True, c.name
    # the rest of the loot: the new master looter loots the boss again and hands out the ring
    missy.open_loot([(RING_OF_BINDING, 4)], source_guid=BOSS_GUID)
    w.tick(2)
    missy.eval("ns.DropPanel:StartRoll(...)", RING_OF_BINDING, 1)
    w.tick(1.5)
    s2 = active(missy)
    assert s2 and s2["i"] == RING_OF_BINDING, s2
    w.player_roll("Elra Northwind", 91)
    w.tick(2)
    missy.eval("__GL.gives = {}")
    award(n, s2["id"], key("Elra Northwind"), by="Missy Badshot")
    gives = missy.eval_py("return __GL.gives") or []
    assert [g["name"] for g in gives] == ["Elra Northwind"], gives
    for name in ("Arakis War", "Aurel Namahs"):
        got = sorted((e["i"], e["w"]) for e in ledger(by[name]) if e["i"] in ITEMS)
        assert got == sorted([(SAPPHIRON_DRAPE, key("Tobin Greyhill")), (RING_OF_BINDING, key("Elra Northwind"))]), (
            name, got)
    no_errors(w)


@case
def test_two_officers_edit_the_same_raid_at_once():
    n = small_raid(seed=25)
    w, by, occ = n["w"], n["by"], n["occ"]
    missy, aurel, gm = by["Missy Badshot"], by["Aurel Namahs"], by["Arakis War"]
    # both officers on the raid leaders list (the GM saves it)
    res = gm.eval_py("local ok, e = ns.Guild:SetRaidLeaders(...); return { ok = ok, e = e }",
                     [key(LEADER), key("Missy Badshot"), key("Aurel Namahs")])
    assert res["ok"] is True, res
    quiet(w, idle=5)
    a = missy.eval_py("local o = ...; local ok, e = ns.RaidPlan:EditRaid(o, { no = 'Missy: bring flasks' }); "
                      "return { ok = ok, e = e }", occ)
    b = aurel.eval_py("local o = ...; local ok, e = ns.RaidPlan:EditRaid(o, { no = 'Aurel: bring pots' }); "
                      "return { ok = ok, e = e }", occ)
    note("simultaneous raid edits: Missy %r, Aurel %r" % (a, b))
    assert a["ok"] is True or b["ok"] is True, (a, b)
    quiet(w, idle=10)
    notes = {c.name: c.eval("return ns.RaidPlan:GetRaid(...).no", occ) for c in online(n["cs"])}
    assert len(set(notes.values())) == 1, notes
    assert notes["Arakis War"] in ("Missy: bring flasks", "Aurel: bring pots"), notes
    note("every client settled on %r" % notes["Arakis War"])
    # two officers save the raid leaders list at the same moment (different lists)
    r1 = missy.eval_py("local ok, e = ns.Guild:SetRaidLeaders(...); return { ok = ok, e = e }",
                       [key(LEADER), key("Missy Badshot")])
    r2 = aurel.eval_py("local ok, e = ns.Guild:SetRaidLeaders(...); return { ok = ok, e = e }",
                       [key(LEADER), key("Aurel Namahs")])
    assert r1["ok"] is True and r2["ok"] is True, (r1, r2)
    quiet(w, idle=10)
    d = diverging(n["cs"], ("rp", "leaders"))
    assert not d, d
    note("raid leaders list everyone settled on: %s" % state(gm)["leaders"])
    no_errors(w)


if __name__ == "__main__":
    run_all()
