"""Go-live readiness, scenario 3: load and throttling with a full 40-man raid on DisasterZone 0.1.0 (WoW Forever).

Forty Forever clients: the GM has the guild's week planned (six raids, three events, two polls) before a raid-night
login wave of 39 members within a minute. Then everyone signs up, votes and edits their BiS list (the council caches
every list), the raid forms from the sign-ups, a pull holds every raider's message, and five drops are rolled and
handed out. The numbers are printed (wire messages and bytes per prefix and channel, deliveries, server-throttled
sends, the busiest sender's peak, game time to settle, wall time); the checks are on the outcome: everything arrives
everywhere (every member holds all the GM's records once the login wave settled, without a /reload), nothing is
refused by the lockdown, nothing is dropped for good.

Forever's send limit: DZProbe's burst of 40 GUILD messages let 9 out (AddonMessageThrottle for the rest). The mock
throttles every prefix to a burst of 10 and one message a second (the retail rule the probe agrees with). Whether
Forever counts per prefix or for all of an addon's prefixes together is not known, so the night runs twice: with the
per-prefix limit, and with one shared bucket of 9 (the strictest reading of the probe). ChatThrottleLib (v32) holds a
refused message and sends it again, so a refusal costs time, not the message.

Run: luaenv/bin/python tests/golive/test_golive_load.py [-k name]
"""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl_common import (case, run_all, no_errors, new_world, roster, make_clients, by_name, key, login_staggered,  # noqa: E402
                       quiet, online, wire_stats, fmt_stats, note, stopwatch, gm_pick, throttled, lockdown_refused,
                       comm_stats, diverging, state, CDL, REALM)
import gl_raid as RN  # noqa: E402

SIZE = 40
STRICT = "__MOCK.throttle_global = true; __MOCK.throttle_burst = 9; __MOCK.throttle_regen = 1"


def peak_per_second(w, mark, who=None):
    """The most messages one client put on the wire within one second (any prefix), and who."""
    per = defaultdict(list)
    for e in w.addon_log[mark:]:
        if e["prefix"] in CDL and (who is None or e["sender"] == who):
            per[e["sender"]].append(e["time"])
    best, by = 0, None
    for s, ts in per.items():
        j = 0
        for i in range(len(ts)):
            while ts[i] - ts[j] >= 1.0:
                j += 1
            if i - j + 1 > best:
                best, by = i - j + 1, s
    return best, by


def night(strict):
    sw = stopwatch()
    w = new_world()
    w.auto_session = False
    cs = make_clients(w, roster(SIZE - 4))
    if strict:
        for c in cs:
            c.preload_lua = STRICT
    by = by_name(cs)
    gm, missy, blu = by["Arakis War"], by["Missy Badshot"], by[RN.LEADER]
    phases = {}

    def phase(name, mark, t0):
        phases[name] = dict(wire_stats(w, mark), game=w.now - t0)

    # the GM plans the week alone
    gm.login()
    w.tick(5)
    RN.define_items(w)
    gm_pick(w, gm, ["Missy Badshot", "Aurel Namahs"], realm=REALM)
    res = gm.eval_py("local ok, e = ns.Guild:SetRaidLeaders(...); return { ok = ok, e = e }", [key(RN.LEADER)])
    assert res["ok"] is True, res
    week = gm.eval_py("""
        local out = { raids = {}, events = {}, polls = {} }
        local now = GetServerTime()
        for d = 0, 1 do
          for i, k in ipairs({ 'ony', 'hyjal', 'barrow' }) do
            local ok, r = ns.RaidPlan:CreateRaid({ i = k, t = now + 1200 + d * 7 * 86400 + i * 86400, ml = 60 })
            out.raids[#out.raids + 1] = ok and r or ('ERR ' .. tostring(r))
          end
        end
        local d = ns.Events:NewDef(true)
        ns.Events:SaveDef(d)
        for i = 1, 3 do out.events[i] = ns.Events:Schedule(d.id, now + i * 86400) end
        for i = 1, 2 do
          out.polls[i] = ns.Polls:Create({ q = 'Question ' .. i, k = 'one', o = { 'A', 'B', 'C' }, a = { { 'g' } },
                                           cl = now + 2 * 86400, rv = 'vote', ch = true })
        end
        return out""")
    assert all(not str(r).startswith("ERR") for r in week["raids"]), week
    occ = week["raids"][0]
    w.tick(5)
    # the login wave
    mark, t0 = len(w.addon_log), w.now
    login_staggered(w, cs[1:], 60, seed=11)
    last = quiet(w, idle=30, timeout=1800)
    # who still lacks some of the GM's records once the wave went quiet; then, without anyone's /reload, the rechecks
    # (Core/DigestSync.lua) until every member holds them (or the deadline)
    lag_quiet = lagging(cs, gm)
    deadline = w.now + 1200
    while lagging(cs, gm) and w.now < deadline:
        w.tick(5, 0.25)
    converged = w.now - t0
    last = max(last, quiet(w, idle=30, timeout=1800))
    phase("login wave", mark, t0)
    settle_login = last - t0
    lag = lagging(cs, gm)
    # everyone answers: a sign-up, both polls, a BiS pick
    mark, t0 = len(w.addon_log), w.now
    for i, c in enumerate(cs):
        if c is not blu:
            r = c.eval_py("local o = ...; local ok, e = ns.RaidPlan:SignUp(o, 'A'); return { ok = ok, e = e }", occ)
            assert r["ok"] is True, (c.name, r)
        for pid in week["polls"]:
            v = c.eval_py("return { ns.Polls:Vote(...) }", pid, [1 + i % 3])
            assert v[0] is True, (c.name, v)
        item = c.eval(RN_BIS, i)
        assert item, c.name
        c.eval("ns.BiS:Commit()")
        w.tick(0.5, 0.1)
    last = quiet(w, idle=30, timeout=1800)
    phase("answers", mark, t0)
    settle_answers = last - t0
    # the raid
    mark, t0 = len(w.addon_log), w.now
    plan = {key(c.name): i // 5 + 1 for i, c in enumerate(cs)}
    res = blu.eval_py("local o, p = ...; local ok, e = ns.RaidInvite:Start(o, p, 'Onyxia'); return { ok = ok, e = e }",
                      occ, plan)
    assert res["ok"] is True, res
    for _ in range(60):
        w.tick(1, 0.25)
        if w.group and w.group["kind"] == "raid" and len(w.group["members"]) == SIZE:
            break
    assert w.group and len(w.group["members"]) == SIZE
    for c in cs:
        c.eval(RN.PROBE)
    res = blu.eval_py("local ok, e = ns.GroupRules:SetSession(true, nil, { loot = true, rolls = true, lock = false });"
                      " return { ok = ok, e = e }")
    assert res["ok"] is True, res
    w.set_master_looter(blu)
    w.tick(3)
    w.enter_instance(name="Onyxia's Lair", instance_id=249, max_players=SIZE, difficulty_id=9)
    w.tick(3)
    n = {"w": w, "cs": cs, "by": by, "size": SIZE}
    p = RN.pull(n, 1084, "Onyxia", RN.ONY_GUID, RN.ONY_NPC, seconds=15)
    awarded = RN.run_loot(n, RN.ONY_DROPS, RN.ONY_GUID)
    quiet(w, idle=20)
    phase("raid + pull + loot", mark, t0)
    got_pull = {c.name: sorted(x["n"] for x in (c.eval_py("return __GL.got") or [])) for c in cs}
    lag_end = lagging(cs, gm)
    out = {"w": w, "cs": cs, "by": by, "week": week, "occ": occ, "pull": p, "awarded": awarded, "phases": phases,
           "settle_login": settle_login, "settle_answers": settle_answers, "wall": sw(), "strict": strict,
           "lag_quiet": lag_quiet, "lag": lag, "lag_end": lag_end, "converged": converged, "got_pull": got_pull,
           "throttled": {c.name: throttled(c) for c in cs},
           "throttled_by": Counter(),
           "dropped": sum(comm_stats(c)["dropped"] for c in cs),
           "backlog": max(comm_stats(c)["backlog"] for c in cs),
           "total": wire_stats(w, 0), "peak": peak_per_second(w, 0)}
    for c in cs:
        for pfx, k in (c.eval_py("return __MOCK.throttledBy or {}") or {}).items():
            out["throttled_by"][pfx] += k
    report(out)
    return out


def lagging(cs, ref, fields=("ev", "po", "rp", "pz", "sd")):
    """{field: [names]} of the online members whose digest differs from ref's (the GM, who made every record).

    Go-live test 2026-11-09: after a login wave 32 of 40 members (36 under the strict limit) lacked events until their
    next login. A newcomer syncs with the first member who answers its HELLO (Core/DigestSync.lua: one answer per
    round, a claim keeps the others quiet), and in a wave that was often a member who held only part of the data
    itself (the GM's live changes it heard after its login, a catch-up from another such member). Fixed with the
    recheck (DigestSync: once a catch-up settled, the digest goes out again until nobody holds anything more)."""
    want = state(ref)
    out = {}
    for c in online(cs):
        s = state(c)
        for f in fields:
            if s[f] != want[f]:
                out.setdefault(f, []).append(c.name)
    return out


RN_BIS = r"""
local i = ...
local picks = { { 4, 17078 }, { 11, 18813 }, { 13, 17067 }, { 1, 16963 }, { 1, 16914 }, { 1, 16921 } }
for k = 0, #picks - 1 do
  local p = picks[(i + k) % #picks + 1]
  if ns.BiS:SetSlot(1, p[1], 'main', p[2]) then return p[2] end
end
return nil
"""


def report(o):
    label = "STRICT (one shared bucket of 9, 1/s)" if o["strict"] else "per prefix (10 burst, 1/s)"
    note("== load night, send limit %s: %.0f game-seconds, %.1f s wall" % (label, o["w"].now, o["wall"]))
    for name, s in o["phases"].items():
        note("%-20s %5.0f s game | %s" % (name, s["game"], fmt_stats(s)))
    t = o["total"]
    thr = o["throttled"]
    note("total: %d wire msgs / %.1f KB, %d deliveries; server-throttled sends (ChatThrottleLib retried them): %d "
         "(max %d on one client: %s), by prefix %s" % (
             t["wire"], t["bytes"] / 1024.0, t["deliveries"], sum(thr.values()), max(thr.values()),
             max(thr, key=thr.get), dict(o["throttled_by"])))
    note("peak: %d msgs in one second from %s; login wave settled after %.0f s, answers after %.0f s; "
         "messages dropped by receivers: %d; largest send backlog left: %d bytes" % (
             o["peak"][0], (o["peak"][1] or "-").split("-")[0], o["settle_login"], o["settle_answers"], o["dropped"],
             o["backlog"]))
    note("members lacking some of the GM's records when the wave first went quiet: %s; after the rechecks "
         "(no /reload): %s, every member converged %.0f s after the wave began; at the end of the night: %s" % (
             {f: len(v) for f, v in o["lag_quiet"].items()}, {f: len(v) for f, v in o["lag"].items()},
             o["converged"], {f: len(v) for f, v in o["lag_end"].items()}))


_RUNS = {}


def run(strict):
    if strict not in _RUNS:
        _RUNS[strict] = night(strict)
    return _RUNS[strict]


def check_outcome(o):
    cs, by, occ = o["cs"], o["by"], o["occ"]
    # everyone holds the same events, polls, raid plans, prized items and strategies as the GM once the login wave
    # settled, without a /reload (lagging(): the recheck), and still at the end of the night
    assert not o["lag"], o["lag"]
    assert not o["lag_end"], o["lag_end"]
    d = diverging(cs, ("ev", "po", "rp", "pz", "sd", "leaders", "council"))
    assert not d, d
    for c in cs:
        n = c.eval("local n = 0 for _ in pairs(ns.RaidPlan:GetSignups(...)) do n = n + 1 end return n", occ)
        assert n == SIZE - 1, (c.name, n)
        for pid in o["week"]["polls"]:
            r = c.eval_py("local p = ns.Polls:GetPoll(...); local r = ns.Polls:Results(p); return { a = r.answered }",
                          pid)
            assert r["a"] == SIZE, (c.name, pid, r)
    # the council has every member's list at its current revision
    for council in ("Arakis War", "Missy Badshot", "Aurel Namahs"):
        cc = by[council]
        missing = []
        for owner in cs:
            if owner is cc:
                continue
            mine = owner.eval_py("local r = ns.BiS:GetRecord(); return { rev = r.rev, hash = r.hash }")
            got = cc.eval_py("local r = ns.Store:GetCached(...); return r and { rev = r.rev, hash = r.hash } or nil",
                             owner.full_name)
            if got != mine:
                missing.append(owner.name)
        assert not missing, (council, missing)
    # the pull and the loot
    p = o["pull"]
    assert p["on_wire"] == [] and p["refused"] == 0, p
    for c in cs:
        got = o["got_pull"][c.name]
        want = sorted(i for i in p["sent"] if cs[i] is not c)
        assert got == want, (c.name, got, want)
    assert sorted(i for i, _, _ in o["awarded"]) == sorted(RN.ONY_DROPS), o["awarded"]
    for name in ("Arakis War", "Missy Badshot", "Aurel Namahs", RN.LEADER):
        got = sorted((e["i"], e["w"]) for e in RN.ledger(by[name]) if e["i"] in RN.ITEMS)
        assert got == sorted((i, k) for i, _, k in o["awarded"]), (name, got)
    assert o["dropped"] == 0, o["dropped"]
    no_errors(o["w"])


@case
def test_forty_clients_per_prefix_limit_everything_arrives():
    check_outcome(run(False))


@case
def test_forty_clients_strict_shared_limit_everything_arrives():
    o = run(True)
    check_outcome(o)
    # the strict limit costs time, not messages: refused sends go out again; nobody ever put more on the wire in one
    # second than the server lets through; the login wave still settles (per prefix it took ~5 min, strict ~12 min)
    assert o["peak"][0] <= 9, o["peak"]
    assert o["settle_login"] < 1200, o["settle_login"]


if __name__ == "__main__":
    run_all()
