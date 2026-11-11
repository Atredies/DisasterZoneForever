"""Authority holes, round 3 (2026-11-09, after test_forever_authority.py and test_forever_authority2.py): every case is
a guild member sending a hand-made message, every other client refusing it, and the legitimate flow still working.

  1. Events and polls "by the GM" through the give path (EVG / PLG): a calendar event, a library event or a poll new to
     a client is taken only from its writer or from who holds the role (a reviewer, an asker); a plain member's copy is
     held back and asked for from the writer (or a role holder) online, so a real one still arrives and a made-up one
     never shows, nor spreads.
  2. Poll answers: one is taken only from the member who gave it or an asker; a relayed poll waits for its asker (or
     another asker) to be online.
  3. Guild council list: a council member's relay of a newer list "by the GM" no longer changes it; the GM's own
     copy does (a relay only confirms the list a client holds).
  4. Members' own records relayed: an event sign-up, a result, a title; a strategy "by" its owner.
  5. The "newer version" notice counts only Forever builds (their HELLO says iface = 16001): an upstream TBC copy
     (1.5.6) no longer tells every 0.x player to update.

Run: luaenv/bin/python tests/forever/test_forever_authority3.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))
sys.path.insert(0, os.path.join(TESTS, "raidplan"))
sys.path.insert(0, os.path.join(TESTS, "loot-roll"))

from _common import case, run_all, no_errors, printed_since  # noqa: E402
from harness import World, Client  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"
REALM_KEY = "CAMWOWEU4Realm4PvP"
GM = "Arakis War"


def key(name):
    return "%s-%s" % (name, REALM_KEY)


GMK, MISSY, AUREL, NALA = key(GM), key("Missy Badshot"), key("Aurel Namahs"), key("Nala Brook")


def guild():
    """The guild on Forever (as the rounds before): Arakis War = GM, Missy = officer (rank 1), Aurel = rank 2,
    Nala = rank 3."""
    w = World(realm=REALM)
    cs = {}
    for name, cls, rank in ((GM, "WARRIOR", 0), ("Missy Badshot", "HUNTER", 1), ("Aurel Namahs", "MAGE", 2),
                            ("Nala Brook", "PRIEST", 3)):
        c = Client(w, name, class_file=cls, guild_rank=rank, level=60, forever=True)
        c.load_addon()
        cs[name.split()[0]] = c
    w.tick(5)
    return w, cs


# ------------------------------------------------------------------------------------------------------------------
# helpers: a record in a client's store, a record passed on by hand
# ------------------------------------------------------------------------------------------------------------------
def has(cl, bucket, kind, rid):
    return cl.eval("local b, k, id = ...; local r = ns.DB:GuildBucket(b, false); "
                   "return (r and r[k] and r[k][id] ~= nil and not r[k][id].del) or false", bucket, kind, rid)


def drop(cl, bucket, kind, rid):
    cl.eval("local b, k, id = ...; local r = ns.DB:GuildBucket(b, false); if r and r[k] then r[k][id] = nil end",
            bucket, kind, rid)


def relay(frm, t, bucket, kind, rid, to):
    """frm passes on its own stored copy of a record (a give, t = EVG / PLG / SBG) to `to`."""
    frm.eval("local t, b, k, id, to = ...; local r = ns.DB:GuildBucket(b, false); "
             "ns.Comm:Send({ t = t, k = k, r = r[k][id] }, 'WHISPER', to, 'data')", t, bucket, kind, rid, to)


# ------------------------------------------------------------------------------------------------------------------
# 1. Events and polls "by the GM" through the give path
# ------------------------------------------------------------------------------------------------------------------
FORGE_EVENT = """
local gm, to = ...
local now = GetServerTime()
local d = ns.EventBlocks:Starter()
d.id, d.by, d.rev, d.at, d.name = 'eforged', gm, now, now, 'Guild Master cup'
local o = { id = 'oforged', by = gm, h = gm, rev = now, def = d, dk = 'eforged', dr = now, at = now + 7200,
            where = 'Stormwind' }
ns.Comm:Send({ t = 'EVG', k = 'D', r = d }, 'WHISPER', to, 'data')
ns.Comm:Send({ t = 'EVG', k = 'O', r = o }, 'WHISPER', to, 'data')"""


@case
def test_a_member_cannot_give_an_event_by_the_gm_to_a_client_that_never_had_it():
    w, c = guild()
    gm, missy, aurel, nala = c["Arakis"], c["Missy"], c["Aurel"], c["Nala"]
    nala.eval(FORGE_EVENT, GMK, AUREL)
    w.tick(10)
    assert not has(aurel, "events", "O", "oforged") and not has(aurel, "events", "D", "eforged")
    # (held back and asked for from the GM, who has no such event: it never shows)
    assert aurel.eval_py("local o = ns.Events:GetOcc('oforged'); return o ~= nil") is False
    # nor does it spread: a newcomer's sync from Aurel carries nothing of it
    missy.logout()
    w.tick(2)
    missy.login()
    w.tick(50)
    assert not has(missy, "events", "O", "oforged")
    # the GM's real event reaches everyone (live)
    occ = gm.eval_py("local d = ns.Events:NewDef(true); assert(ns.Events:SaveDef(d)); "
                     "return { d.id, ns.Events:Schedule(d.id, GetServerTime() + 3600) }")
    w.tick(3)
    for x in (missy, aurel, nala):
        assert has(x, "events", "O", occ[1]), x.name
    # a client that lost it: a plain member's copy is held back and the writer's asked for (it comes)
    drop(aurel, "events", "O", occ[1])
    relay(nala, "EVG", "events", "O", occ[1], AUREL)
    w.tick(1)
    assert not has(aurel, "events", "O", occ[1])
    w.tick(8)
    assert has(aurel, "events", "O", occ[1])
    # an officer's copy (a reviewer: their store holds only vouched copies) is taken at once
    drop(aurel, "events", "O", occ[1])
    relay(missy, "EVG", "events", "O", occ[1], AUREL)
    w.tick(1)
    assert has(aurel, "events", "O", occ[1])
    # the GM's own copy too
    drop(aurel, "events", "D", occ[0])
    relay(gm, "EVG", "events", "D", occ[0], AUREL)
    w.tick(1)
    assert has(aurel, "events", "D", occ[0])
    no_errors(w)


FORGE_POLL = """
local gm, me, to = ...
local now = GetServerTime()
ns.Comm:Send({ t = 'PLG', k = 'P', r = { id = 'pforged', by = gm, rev = now, at = now, q = 'Disband the guild?',
    k = 'yn', o = { 'Yes', 'No' }, cl = now + 3600, rv = 'live', a = { { 'g' } }, m = { me, to } } },
    'WHISPER', to, 'data')"""


def make_poll(gm, targets):
    pid = gm.eval("local t = ...; local id, why = ns.Polls:Create({ q = 'Raid on Sunday?', k = 'yn', a = t, "
                  "cl = GetServerTime() + 3600, rv = 'live', ch = true }); return id or ('ERR ' .. tostring(why))",
                  targets)
    assert pid.startswith("p"), pid
    return pid


@case
def test_a_member_cannot_give_a_poll_by_the_gm_or_another_members_answer():
    w, c = guild()
    gm, missy, aurel, nala = c["Arakis"], c["Missy"], c["Aurel"], c["Nala"]
    nala.eval(FORGE_POLL, GMK, NALA, AUREL)
    w.tick(10)
    assert not has(aurel, "polls", "P", "pforged")
    assert aurel.eval("return ns.Polls:GetPoll('pforged') ~= nil") is False
    # a real poll asking Aurel and Nala; Nala forges Aurel's answer onto the GM's and Missy's clients
    pid = make_poll(gm, [["p", AUREL], ["p", NALA]])
    w.tick(3)
    assert has(aurel, "polls", "P", pid)
    forge = ("local pid, who, to = ...; ns.Comm:Send({ t = 'PLG', k = 'V', r = { id = pid .. '/' .. who, by = who, "
             "rev = GetServerTime(), c = { 2 } } }, 'WHISPER', to, 'data')")
    for to in (GMK, MISSY):
        nala.eval(forge, pid, AUREL, to)
    w.tick(10)
    for x in (gm, missy):
        assert not has(x, "polls", "V", pid + "/" + AUREL), x.name
    # Aurel's own answer reaches everyone (live)
    assert aurel.eval_py("return { ns.Polls:Vote(...) }", pid, [1])[0] is True
    w.tick(3)
    assert has(missy, "polls", "V", pid + "/" + AUREL)
    # a client that lost it: Nala's copy is held back and Aurel's own asked for
    vid = pid + "/" + AUREL
    drop(missy, "polls", "V", vid)
    relay(nala, "PLG", "polls", "V", vid, MISSY)
    w.tick(1)
    assert not has(missy, "polls", "V", vid)
    w.tick(8)
    assert has(missy, "polls", "V", vid)
    assert missy.eval_py("return ns.DB:GuildBucket('polls', false).V[...].c", vid) == [1]
    # an asker's copy (the GM's) is taken at once
    drop(missy, "polls", "V", vid)
    relay(gm, "PLG", "polls", "V", vid, MISSY)
    w.tick(1)
    assert has(missy, "polls", "V", vid)
    no_errors(w)


@case
def test_a_poll_passed_on_by_a_member_waits_for_its_asker():
    w, c = guild()
    gm, missy, aurel, nala = c["Arakis"], c["Missy"], c["Aurel"], c["Nala"]
    pid = make_poll(gm, [["p", AUREL], ["p", NALA]])
    w.tick(3)
    drop(aurel, "polls", "P", pid)
    for x in (gm, missy):            # the asker and the other asker (an officer) are away
        x.logout()
    w.tick(2)
    relay(nala, "PLG", "polls", "P", pid, AUREL)
    w.tick(10)
    assert not has(aurel, "polls", "P", pid)
    # the asker logs in: Aurel asks for it and gets it from them
    gm.login()
    w.tick(30)
    assert has(aurel, "polls", "P", pid)
    assert aurel.eval("return ns.Polls:AsksMe(ns.Polls:GetPoll(...))", pid) is True
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 3. Guild council list
# ------------------------------------------------------------------------------------------------------------------
def pick(gm, keys):
    res = gm.eval_py("local keys = ...; local set = {}; for _, k in ipairs(keys) do set[k] = true end; "
                     "local ok, err = ns.Guild:SetGuildCouncil(set); return { ok = ok, err = err }", keys)
    assert res.get("ok") is True, res
    return gm.eval("return ns.Guild:GetGuildCouncilRev()")


@case
def test_a_council_member_cannot_rewrite_the_gms_council_list():
    import lr_common as lr
    w, c = guild()
    gm, missy, aurel, nala = c["Arakis"], c["Missy"], c["Aurel"], c["Nala"]
    rev = pick(gm, [MISSY, AUREL])
    w.tick(3)
    for x in (missy, aurel, nala):
        assert x.eval("return ns.Guild:GetGuildCouncilRev()") == rev, x.name
        assert x.eval("return ns.Guild:IsGuildCouncil(...)", AUREL) is True, x.name
    # Missy, on the list, relays a newer list "by the GM": Aurel off it, Nala on it
    mark = len(w.addon_log)
    forge = ("local rev, m, gm = ...; ns.Comm:Send({ t = 'CG', rev = rev, m = m, ph = 1, by = gm }, 'GUILD', nil, "
             "'ctrl')")
    missy.eval(forge, rev + 5, [MISSY, NALA], GMK)

    def unchanged():
        for x in (aurel, nala):
            assert x.eval("return ns.Guild:GetGuildCouncilRev()") == rev, x.name
            assert x.eval("return ns.Guild:IsGuildCouncil(...)", NALA) is False, x.name
            assert x.eval("return ns.Guild:IsGuildCouncil(...)", AUREL) is True, x.name

    w.tick(1)
    unchanged()                     # (before: taken at once, until the GM's client shared its own list again)
    w.tick(5)
    unchanged()
    # (they ask the GM instead)
    cq = [m for m in lr.msgs_of_type(w, "CQ", mark) if m["_chat_type"] == "WHISPER"]
    assert cq, "nobody asked the GM"
    # with the GM away it does not stand either
    gm.logout()
    w.tick(2)
    missy.eval(forge, rev + 7, [MISSY, NALA], GMK)
    w.tick(10)
    unchanged()
    gm.login()
    w.tick(30)
    # the same list it holds, relayed: still taken as a confirmation (no change)
    missy.eval("local rev, m, gm = ...; ns.Comm:Send({ t = 'CG', rev = rev, m = m, ph = 1, by = gm }, 'GUILD', nil, "
               "'ctrl')", rev, [MISSY, AUREL], GMK)
    w.tick(3)
    assert nala.eval("return ns.Guild:GetGuildCouncilRev()") == rev
    # the GM's own new list is taken at once
    rev2 = pick(gm, [MISSY, NALA])
    w.tick(3)
    for x in (missy, aurel, nala):
        assert x.eval("return ns.Guild:GetGuildCouncilRev()") == rev2, x.name
        assert x.eval("return ns.Guild:IsGuildCouncil(...)", NALA) is True, x.name
        assert x.eval("return ns.Guild:IsGuildCouncil(...)", AUREL) is False, x.name
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 4. Members' own records relayed
# ------------------------------------------------------------------------------------------------------------------
@case
def test_a_members_sign_up_result_or_title_passed_on_by_someone_else_is_not_taken():
    w, c = guild()
    gm, missy, aurel, nala = c["Arakis"], c["Missy"], c["Aurel"], c["Nala"]
    d, occ = gm.eval_py("local d = ns.Events:NewDef(true); assert(ns.Events:SaveDef(d)); "
                        "return { d.id, ns.Events:Schedule(d.id, GetServerTime() + 3600) }")
    w.tick(3)
    jid = occ + "/" + AUREL
    # Nala signs Aurel up on Missy's and the GM's clients, gives herself a title "by" Aurel, writes a result "by" the GM
    forge = """
local occ, aurel, gm, to = ...
local now = GetServerTime()
ns.Comm:Send({ t = 'EVG', k = 'J', r = { id = occ .. '/' .. aurel, by = aurel, rev = now, o = occ, on = true, at = now } },
    'WHISPER', to, 'data')
ns.Comm:Send({ t = 'EVG', k = 'T', r = { id = aurel, by = aurel, rev = now, ti = 'the Fool' } }, 'WHISPER', to, 'data')
ns.Comm:Send({ t = 'EVG', k = 'R', r = { id = occ, by = gm, rev = now, name = 'Cup', at = now - 60, t1 = now,
    champ = ns.Util.PlayerKey(), points = { [ns.Util.PlayerKey()] = 100 }, hosts = { gm } } }, 'WHISPER', to, 'data')"""
    for to in (MISSY, GMK):
        nala.eval(forge, occ, AUREL, GMK, to)
    w.tick(10)
    for x in (missy, gm):
        assert not has(x, "events", "J", jid), x.name
        assert not has(x, "events", "T", AUREL), x.name
        assert not has(x, "events", "R", occ), x.name
    # Aurel's real sign-up (live) reaches everyone; passed on by Nala to a client that lost it, Aurel's copy is asked for
    assert aurel.eval("return (ns.Events:SignUp(...))", occ) is True
    w.tick(3)
    assert has(missy, "events", "J", jid)
    drop(missy, "events", "J", jid)
    relay(nala, "EVG", "events", "J", jid, MISSY)
    w.tick(1)
    assert not has(missy, "events", "J", jid)
    w.tick(8)
    assert has(missy, "events", "J", jid)
    no_errors(w)


@case
def test_a_strategy_by_its_owner_passed_on_by_someone_else_is_not_taken():
    sys.path.insert(0, os.path.join(TESTS, "strategy"))
    from st_common import save_council
    from rp_common import world as rp_world, K
    # Gina = GM (a moderator), Bob = guild council (a moderator), Lee / Rita / Sam plain members
    w, c = rp_world(names=(("Gina", 0, "PALADIN"), ("Bob", 2, "MAGE"), ("Lee", 3, "WARRIOR"), ("Rita", 3, "PRIEST"),
                           ("Sam", 3, "HUNTER")), council=("Bob",), planners=())
    gina, bob, lee, rita, sam = c["Gina"], c["Bob"], c["Lee"], c["Rita"], c["Sam"]
    sid = save_council(lee, "Lee's plan")
    w.tick(3)
    assert has(sam, "strategy", "B", sid)
    # Rita passes on Lee's strategy renamed, "by" Lee, newer; and a whole new strategy "by" Lee
    forge = ("local id, lee, to = ...; local r = ns.DB:GuildBucket('strategy', false).B[id]; local c = {}; "
             "for k, v in pairs(r) do c[k] = v end; c.rev, c.by, c.n = r.rev + 5, lee, 'Rita rules'; "
             "ns.Comm:Send({ t = 'SBG', k = 'B', r = c }, 'WHISPER', to, 'data'); "
             "local n = {}; for k, v in pairs(r) do n[k] = v end; n.id, n.rev, n.n = 'sforged', r.rev + 5, 'Forged'; "
             "ns.Comm:Send({ t = 'SBG', k = 'B', r = n }, 'WHISPER', to, 'data')")
    rita.eval(forge, sid, K("Lee"), K("Sam"))
    w.tick(10)
    assert sam.eval("return ns.DB:GuildBucket('strategy', false).B[...].n", sid) == "Lee's plan"
    assert not has(sam, "strategy", "B", "sforged")
    # Lee's own copy of the same is taken; a moderator's too
    lee.eval(forge, sid, K("Lee"), K("Sam"))
    w.tick(2)
    assert sam.eval("return ns.DB:GuildBucket('strategy', false).B[...].n", sid) == "Rita rules"
    assert has(sam, "strategy", "B", "sforged")
    drop(sam, "strategy", "B", sid)
    relay(bob, "SBG", "strategy", "B", sid, K("Sam"))
    w.tick(2)
    assert has(sam, "strategy", "B", sid)
    # a plain member's copy of a real one: held back, Lee's own asked for
    drop(sam, "strategy", "B", sid)
    relay(rita, "SBG", "strategy", "B", sid, K("Sam"))
    w.tick(1)
    assert not has(sam, "strategy", "B", sid)
    w.tick(8)
    assert has(sam, "strategy", "B", sid)
    w.assert_no_errors()


# ------------------------------------------------------------------------------------------------------------------
# 5. The "newer version" notice counts only Forever builds
# ------------------------------------------------------------------------------------------------------------------
@case
def test_an_upstream_version_does_not_tell_forever_players_to_update():
    import lr_common as lr
    w, c = guild()
    aurel, nala = c["Aurel"], c["Nala"]
    # a Forever build's HELLO says so
    mark = len(w.addon_log)
    nala.eval("ns.Sync:SendHello(true)")
    w.tick(2)
    hellos = [m for m in lr.msgs_of_type(w, "H", mark, whole=True) if m["_sender"] == NALA]
    assert hellos and hellos[-1].get("iface") == 16001, hellos
    hello = ("local v, iface = ...; ns.Comm:Send({ t = 'H', r = 0, v = v, n = 7, iface = iface }, 'GUILD', nil, "
             "'ctrl')")

    def newer_noted(n0):
        return any("newer DisasterZone" in line for line in printed_since(nala, n0))

    def notice():
        return nala.eval_py("local N = ns.Notify; local out = {}; for _, e in ipairs(ns.Sync:GetVersions()) do "
                            "if ns.Util.PeerVersionNewer(e.v, e.fi) then out[#out + 1] = e.v end end; return out") or []

    n0 = len(nala.chat_frame)
    # an upstream TBC copy (1.5.6, no iface), then one that names another interface
    aurel.eval(hello, "1.5.6", None)
    w.tick(2)
    assert nala.eval("return ns.Sync:GetPeer(...).v", AUREL) == "1.5.6"
    assert not newer_noted(n0) and notice() == [], (printed_since(nala, n0), notice())
    aurel.eval(hello, "1.5.7", 20505)
    w.tick(2)
    assert not newer_noted(n0) and notice() == []
    # a Forever build that is newer: the notice
    aurel.eval(hello, "9.9.9", 16001)
    w.tick(2)
    assert newer_noted(n0), printed_since(nala, n0)
    assert notice() == ["9.9.9"]
    no_errors(w)


if __name__ == "__main__":
    run_all()
