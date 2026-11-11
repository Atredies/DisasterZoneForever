"""Go-live readiness, scenario 1: a guild day on WoW Forever with ~15 members running DisasterZone 0.1.0.

Fifteen Forever clients (forever=True) log in at staggered times: the GM, two officers, a raid leader and members,
plus one member on an old copy (the TBC original, which reports 1.5.5: the only "older" DisasterZone that exists,
since the Forever versions restarted at 0.1.0). The HELLO + DigestSync catch-up runs as in game. Through the day:
  * the GM picks the officer ranks (Veteran becomes an officer rank) and the guild council; an officer names the
    raid leaders;
  * an officer puts two events on the calendar, asks a poll and plans Onyxia's Lair (40) and Hyjal Summit (20);
  * members sign up to the raids and the event, vote and edit their BiS lists (the council caches them);
  * a member logs out in the morning and back in in the evening, and catches up on everything;
  * a member's illegitimate edits are refused everywhere (someone else's raid / event / poll, the officer ranks, a
    forged live update on the wire).
Every client (the old copy aside) ends up with the same events, polls, raid plans, officer ranks, raid leaders and
council list, and no client raises a Lua error.

Run: luaenv/bin/python tests/golive/test_golive_guild_day.py [-k name]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl_common import (case, run_all, no_errors, new_world, roster, make_clients, by_name, key, login_staggered,  # noqa: E402
                       quiet, online, state, diverging, assert_converged, wire_stats, fmt_stats, note, stopwatch,
                       gm_pick, Client, REALM)

N_MEMBERS = 11          # + GM, 2 officers, raid leader = 15 on 0.1.0, + 1 old copy
LATE = "Kesha Frostmane"    # logs out in the morning, back in the evening
SNEAK = "Lorn Mossy"        # tries edits that are not theirs
OLD = "Oldy Copper"
HOUR = 3600

_DAY = {}


def sp(c, code, *args):
    return c.eval_py(code, *args)


def organize(w, by):
    """The GM picks the officer ranks and the council; an officer names the raid leaders."""
    gm, missy = by["Arakis War"], by["Missy Badshot"]
    res = sp(gm, "local ok, e = ns.Guild:SetOfficerRanks({ 0, 1, 2 }); return { ok = ok, e = e }")
    assert res["ok"] is True, res
    w.tick(3)
    gm_pick(w, gm, ["Missy Badshot", "Aurel Namahs"], realm=REALM)
    w.tick(2)
    res = sp(missy, "local ok, e = ns.Guild:SetRaidLeaders(...); return { ok = ok, e = e }",
             [key("Missy Badshot"), key("Blu Skydagger")])
    assert res["ok"] is True, res
    w.tick(3)


def plan_day(w, by):
    """Officer Aurel: two events + a poll; officer / raid leader Missy: Onyxia 40 and Hyjal 20."""
    aurel, missy = by["Aurel Namahs"], by["Missy Badshot"]
    ev = sp(aurel, """
        local d = ns.Events:NewDef(true)
        assert(ns.Events:SaveDef(d), "save")
        local a = ns.Events:Schedule(d.id, GetServerTime() + 6 * 3600, { where = 'Ironforge' })
        local b = ns.Events:Schedule(d.id, GetServerTime() + 30 * 3600, { where = 'Orgrimmar' })
        return { def = d.id, a = a, b = b }""")
    assert ev["a"] and ev["b"], ev
    w.tick(2)
    poll = aurel.eval("""
        local id, why = ns.Polls:Create({ q = 'Which night for Onyxia?', k = 'one', o = { 'Wednesday', 'Thursday',
          'Sunday' }, a = { { 'g' } }, cl = GetServerTime() + 20 * 3600, rv = 'vote', ch = true })
        return id or ('ERR ' .. tostring(why))""")
    assert poll and not poll.startswith("ERR"), poll
    w.tick(2)
    t = missy.eval("return GetServerTime() + 8 * 3600")
    ony = sp(missy, "local f = ...; local ok, r = ns.RaidPlan:CreateRaid(f); return { ok = ok, r = r }",
             {"i": "ony", "t": t, "ml": 60, "no": "Bring fire resistance"})
    hyj = sp(missy, "local f = ...; local ok, r = ns.RaidPlan:CreateRaid(f); return { ok = ok, r = r }",
             {"i": "hyjal", "t": t + 2 * 86400, "ml": 60})
    assert ony["ok"] is True and hyj["ok"] is True, (ony, hyj)
    # (the records leave through ChatThrottleLib on the data prefix: a few seconds until everyone has them)
    quiet(w, idle=10)
    return {"ev": ev, "poll": poll, "ony": ony["r"], "hyj": hyj["r"]}


def members_answer(w, cs, plan):
    """Every member on 0.1.0 answers: raid sign-ups, the event, the poll, a BiS pick."""
    out = {"signed": {}, "voted": 0, "bis": {}}
    for i, c in enumerate(cs):
        st = ("A", "A", "T", "B")[i % 4]
        res = sp(c, "local o, s = ...; local ok, e = ns.RaidPlan:SignUp(o, s); return { ok = ok, e = e }",
                 plan["ony"], st)
        assert res["ok"] is True, (c.name, res)
        out["signed"][key(c.name)] = st
        if i % 2 == 0:
            res = sp(c, "local o = ...; local ok, e = ns.RaidPlan:SignUp(o, 'A'); return { ok = ok, e = e }",
                     plan["hyj"])
            assert res["ok"] is True, (c.name, res)
        if i % 3 == 0 and not c.eval("return ns.Events:IsSignedUp(...)", plan["ev"]["a"]):
            ok = sp(c, "return { ns.Events:SignUp(...) }", plan["ev"]["a"], True)
            assert ok[0] is True, (c.name, ok)
        v = sp(c, "return { ns.Polls:Vote(...) }", plan["poll"], [1 + i % 3])
        assert v[0] is True, (c.name, v)
        out["voted"] += 1
        item = bis_pick(c, i)
        if item:
            out["bis"][c.name] = item
        w.tick(1.5, 0.25)
    for c in cs:
        c.eval("ns.BiS:Commit()")
    return out


# (Forever's raid loot is not in the data before 9 Dec 2026, so ItemDB:GetCandidates offers nothing yet: members pick
# Onyxia items the client knows by id, as they would from a link)
BIS_PICK = r"""
local i = ...
local picks = { { 4, 17078 }, { 11, 18813 }, { 13, 17067 }, { 1, 16963 }, { 1, 16914 }, { 1, 16921 } }
for k = 0, #picks - 1 do
  local p = picks[(i + k) % #picks + 1]
  if ns.BiS:SetSlot(1, p[1], 'main', p[2]) then return p[2] end
end
return nil
"""


def bis_pick(c, i):
    return c.eval(BIS_PICK, i)


def day():
    """One guild day, shared by the checks below."""
    if _DAY:
        return _DAY
    sw = stopwatch()
    w = new_world()
    cs = make_clients(w, roster(N_MEMBERS))
    old = Client(w, OLD, class_file="PALADIN", guild_rank=3, level=60, forever=False, online=False)
    by = by_name(cs + [old])
    # morning: the GM first, then everyone over ten minutes (the old copy among them)
    by["Arakis War"].login()
    w.tick(5)
    login_staggered(w, [c for c in cs if c.name != "Arakis War"] + [old], 600, seed=7)
    quiet(w, idle=25)
    organize(w, by)
    # the late member leaves for the day before anything is planned
    by[LATE].logout()
    w.tick(5)
    mark = len(w.addon_log)
    plan = plan_day(w, by)
    on = [c for c in online(cs) if c.name not in (LATE,)]
    answers = members_answer(w, on, plan)
    quiet(w, idle=25)
    day_traffic = wire_stats(w, mark)
    # the sneak tries what is not theirs
    sneak = sneak_attempts(w, by, plan)
    quiet(w, idle=20)
    # evening: the late member is back and catches up
    mark2 = len(w.addon_log)
    t_login = w.now
    by[LATE].login()
    caught = None
    for _ in range(240):
        w.tick(0.5, 0.25)
        # the daily Prune runs 20-40 s after a login, often while the catch-up still arrives (one record a second):
        # running it all along must not drop sign-ups whose calendar event is still on its way
        if by[LATE].loaded:
            by[LATE].eval("ns.Events:Prune()")
        if not diverging([by[LATE], by["Arakis War"]], ("ev", "po", "rp", "ranks", "leaders", "council")):
            caught = w.now - t_login
            break
    quiet(w, idle=25)
    catchup = wire_stats(w, mark2)
    _DAY.update(w=w, cs=cs, old=old, by=by, plan=plan, answers=answers, sneak=sneak, caught=caught,
                traffic=day_traffic, catchup=catchup, wall=sw())
    note("guild day: %d clients, %.0f game-seconds, %.1f s wall" % (len(cs) + 1, w.now, _DAY["wall"]))
    note("day traffic: " + fmt_stats(day_traffic))
    note("evening catch-up of %s: %s s; %s" % (LATE, caught, fmt_stats(catchup)))
    return _DAY


# ---------------------------------------------------------------------------------------------------------------------
# a member's illegitimate edits
# ---------------------------------------------------------------------------------------------------------------------
def sneak_attempts(w, by, plan):
    s = by[SNEAK]
    out = {}
    out["edit_raid"] = sp(s, "local o = ...; local ok, e = ns.RaidPlan:EditRaid(o, { no = 'free loot' }); "
                          "return { ok = ok, e = e }", plan["ony"])
    out["create_raid"] = sp(s, "local ok, e = ns.RaidPlan:CreateRaid({ i = 'ony', t = GetServerTime() + 7200 }); "
                            "return { ok = ok, e = e }")
    out["poll"] = s.eval("local id, why = ns.Polls:Create({ q = 'x', k = 'yn', a = { { 'g' } }, "
                         "cl = GetServerTime() + 3600, rv = 'vote' }); return id or ('ERR ' .. tostring(why))")
    out["ranks"] = sp(s, "local ok, e = ns.Guild:SetOfficerRanks({ 0, 1, 2, 3 }); return { ok = ok, e = e }")
    out["edit_occ"] = s.eval("return ns.Events:EditOcc(..., GetServerTime() + 60, 'nowhere')", plan["ev"]["a"])
    out["cancel_occ"] = s.eval("return ns.Events:CancelOcc(...)", plan["ev"]["a"])
    # forged live updates on the wire: the raid and the event moved by the sneak (by = the sneak, so the sender check
    # passes; the merge's authority check must refuse them), and the GM's officer ranks
    s.eval("""
        local occ, evOcc = ...
        local r = ns.RaidPlan:GetRaid(occ)
        local rec = { id = occ, by = ns.Util.PlayerKey(), rev = GetServerTime() + 5, i = 'ony',
                      t = GetServerTime() + 60, no = 'forged' }
        ns.Comm:Send({ t = 'RPU', k = 'E', r = rec }, 'GUILD', nil, 'data')
        local o = ns.Events:GetOcc(evOcc)
        local f = {}
        for k, v in pairs(o) do f[k] = v end
        f.by = ns.Util.PlayerKey(); f.rev = (o.rev or 0) + 100; f.where = 'forged'; f.at = GetServerTime() + 60
        ns.Comm:Send({ t = 'EVU', k = 'O', r = f }, 'GUILD')
        ns.Comm:Send({ t = 'GMR', v = GetServerTime(), ok = { 0, 1, 2, 3, 4 } }, 'GUILD')
    """, plan["ony"], plan["ev"]["a"])
    w.tick(3)
    return out


# ---------------------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------------------
@case
def test_everyone_on_010_converges_to_the_same_data():
    d = day()
    cs = d["cs"]
    assert all(c.online for c in cs), [c.name for c in cs if not c.online]
    assert_converged(cs)
    st = state(d["by"]["Arakis War"])
    assert st["ranks"] == "0,1,2", st
    assert st["leaders"] == ",".join(sorted([key("Missy Badshot"), key("Blu Skydagger")])), st
    assert st["ev"] != "0" and st["po"] != "0" and st["rp"] != "0", st
    no_errors(d["w"])


@case
def test_officer_ranks_and_council_reach_everyone():
    d = day()
    for c in d["cs"]:
        assert c.eval("return ns.Guild:IsOfficer(...)", key("Blu Skydagger")) is True, c.name
        assert c.eval("return ns.Guild:IsOfficer(...)", key(SNEAK)) is False, c.name
        assert c.eval("return ns.Guild:IsCouncil(...)", key("Aurel Namahs")) is True, c.name
    no_errors(d["w"])


@case
def test_sign_ups_votes_and_event_reach_everyone():
    d = day()
    plan, ans = d["plan"], d["answers"]
    for c in d["cs"]:
        su = c.eval_py("local o = ...; local out = {} for k, s in pairs(ns.RaidPlan:GetSignups(o)) do"
                       " out[k] = s.st end return out", plan["ony"]) or {}
        mine = {k: v for k, v in su.items() if k in ans["signed"]}
        assert mine == ans["signed"], (c.name, len(mine), len(ans["signed"]))
        n_hyj = c.eval("local n = 0 for _ in pairs(ns.RaidPlan:GetSignups(...)) do n = n + 1 end return n", plan["hyj"])
        assert n_hyj == (len(ans["signed"]) + 1) // 2, (c.name, n_hyj)
        r = c.eval_py("local p = ns.Polls:GetPoll(...); local r = ns.Polls:Results(p); return { a = r.answered, t = r.total }",
                      plan["poll"])
        assert r["a"] == ans["voted"], (c.name, r)
        n_ev = c.eval("return #ns.Events:GetSignups(...)", plan["ev"]["a"])
        assert n_ev >= 1 + len([1 for i in range(len(ans["signed"])) if i % 3 == 0]) - 1, (c.name, n_ev)
    no_errors(d["w"])


@case
def test_bis_lists_reach_the_council():
    d = day()
    by = d["by"]
    assert len(d["answers"]["bis"]) >= len(d["answers"]["signed"]) // 2, d["answers"]["bis"]
    for council in ("Arakis War", "Missy Badshot", "Aurel Namahs"):
        c = by[council]
        for owner in d["answers"]["bis"]:
            o = by[owner]
            if o is c:
                continue
            mine = o.eval_py("local r = ns.BiS:GetRecord(); return { rev = r.rev, hash = r.hash }")
            got = c.eval_py("local r = ns.Store:GetCached(...); return r and { rev = r.rev, hash = r.hash } or nil",
                            key(owner))
            assert got == mine, (council, owner, got, mine)
    no_errors(d["w"])


@case
def test_late_member_catches_up_in_the_evening():
    d = day()
    late = d["by"][LATE]
    assert d["caught"] is not None and d["caught"] < 90, d["caught"]
    plan = d["plan"]
    assert late.eval("return ns.RaidPlan:GetRaid(...) ~= nil", plan["ony"]) is True
    assert late.eval("return ns.Polls:GetPoll(...) ~= nil", plan["poll"]) is True
    assert late.eval("return ns.Events:GetOcc(...) ~= nil", plan["ev"]["b"]) is True
    # and can still answer
    res = late.eval_py("local o = ...; local ok, e = ns.RaidPlan:SignUp(o, 'T'); return { ok = ok, e = e }", plan["ony"])
    assert res["ok"] is True, res
    quiet(d["w"], idle=10)
    assert d["by"]["Missy Badshot"].eval("local o, k = ...; local s = ns.RaidPlan:GetSignups(o)[k]; return s and s.st",
                                        plan["ony"], key(LATE)) == "T"
    no_errors(d["w"])


@case
def test_illegitimate_edits_are_refused_everywhere():
    d = day()
    s, plan = d["sneak"], d["plan"]
    assert s["edit_raid"]["ok"] is False, s
    assert s["create_raid"]["ok"] is False, s
    assert s["poll"].startswith("ERR"), s
    assert s["ranks"]["ok"] is False, s
    assert not s["edit_occ"] and not s["cancel_occ"], s
    for c in d["cs"]:
        v = c.eval_py("local v = ns.RaidPlan:GetRaid(...); return { no = v.no, t = v.t, by = v.by }", plan["ony"])
        assert v["no"] == "Bring fire resistance" and v["by"] == key("Missy Badshot"), (c.name, v)
        o = c.eval_py("local o = ns.Events:GetOcc(...); return { where = o.where, h = o.h, cancel = o.cancel }",
                      plan["ev"]["a"])
        assert o["where"] == "Ironforge" and o["h"] == key("Aurel Namahs") and o.get("cancel") is None, (c.name, o)
        assert c.eval("return table.concat((ns.Guild:GetOfficerRanks()), ',')") == "0,1,2", c.name
    no_errors(d["w"])


@case
def test_old_copy_does_not_disturb_the_guild():
    d = day()
    w, old = d["w"], d["old"]
    assert old.eval("return ns.version") == "1.5.5"
    # the old copy knows none of the Forever raids: it keeps out of them, and 0.1.0 clients are unaffected
    nags = [c.name for c in d["cs"]
            if any("newer DisasterZone version" in str(x) and "1.5.5" in str(x) for x in c.chat_frame)]
    note("clients told 'a newer DisasterZone version (1.5.5) is in use' by the old copy: %d of %d" % (
        len(nags), len(d["cs"])))
    _DAY["nags"] = nags
    assert not nags, "0.1.0 clients ask their players to 'update' to the old TBC copy: %s" % nags
    no_errors(w)


if __name__ == "__main__":
    run_all()
