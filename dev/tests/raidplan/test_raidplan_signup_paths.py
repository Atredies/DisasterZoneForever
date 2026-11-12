"""One sign-up path for the game and Discord (2026-11-12, state-machine audit): RaidPlan:SignUp (a member in game)
and RaidPlan:SignUpFor (the same member's answer given in Discord, run by every client that takes the bot's record)
share one set of rules (BuildSignup in Core/RaidPlan.lua).

Covers, through both paths: a cancelled raid, a raid over, the blacklist, a member taken off (declined), a locked raid
(the one deliberate difference: in game the answer becomes a request to join, Discord refuses), the level minimum, an
answer the organizers removed (the new one wins), a note over 40 characters (refused on both; before, Discord dropped
the stored note silently) and note = false (clears it).

Run: luaenv\\Scripts\\python.exe tests\\raidplan\\test_raidplan_signup_paths.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rp_common import World, Client, gm_pick, set_raid_leaders, K, DAY, now, team, create, signup, signups, call  # noqa: E402
from _common import case, run_all  # noqa: E402

LONG = "x" * 60


def world():
    """Gina = GM, Bob = council + raid leader; Lee / Rita members; Sam a level 60 member."""
    w = World()
    c = {}
    for name, rank, cls, lv in (("Gina", 0, "PALADIN", 70), ("Bob", 1, "MAGE", 70), ("Lee", 3, "WARRIOR", 70),
                                ("Rita", 3, "PRIEST", 70), ("Sam", 3, "ROGUE", 60)):
        c[name] = Client(w, name, guild_rank=rank, class_file=cls, level=lv)
    for x in c.values():
        x.load_addon()
    w.tick(3)
    gm_pick(w, c["Gina"], ["Bob"])
    set_raid_leaders(w, c["Gina"], ["Bob"])
    w.tick(2)
    return w, c


def game(cl, occ, st, sp=None, note=None):
    return signup(cl, occ, st, sp, note)


def discord(cl, occ, st, sp=None, note=None):
    """The Discord path, run on the member's own client (every client runs it the same way)."""
    return cl.eval_py("local o, k, st, sp, n = ...; local ok, e = ns.RaidPlan:SignUpFor(o, k, st, sp, n);"
                      " return { ok = ok, e = e }", occ, K(cl.name), st, sp, note)


PATHS = (("game", game), ("discord", discord))


def both(cl, occ, st, note=None):
    return {name: fn(cl, occ, st, None, note) for name, fn in PATHS}


def refused_alike(res, err):
    for name, r in res.items():
        assert r["ok"] is False and r["e"] == err, (name, r)


@case
def both_paths_apply_the_same_rules():
    w, c = world()
    bob, lee, rita, sam = c["Bob"], c["Lee"], c["Rita"], c["Sam"]
    t0 = now(bob)

    # cancelled
    occ = create(bob, i="kara", t=t0 + DAY)
    w.tick(2)
    assert call(bob, "CancelRaid", occ, "one")["ok"] is True
    w.tick(2)
    refused_alike(both(lee, occ, "A"), "This raid was cancelled.")

    # the level minimum
    occ = create(bob, i="kara", t=t0 + DAY, ml=70)
    w.tick(2)
    refused_alike(both(sam, occ, "A"), "This raid is for level 70 characters.")

    # declined (taken off by an organizer)
    occ = create(bob, i="kara", t=t0 + DAY)
    w.tick(2)
    assert game(lee, occ, "A")["ok"] is True
    w.tick(2)
    assert call(bob, "DeclineSignup", occ, K("Lee"))["ok"] is True
    w.tick(2)
    refused_alike(both(lee, occ, "A"), "You were taken off this raid.")

    # the blacklist
    assert call(bob, "SetBlacklisted", "Sam", "left mid-raid twice")["ok"] is True
    w.tick(3)
    refused_alike(both(sam, occ, "A"), "You can't sign up for raids. Contact an officer.")

    # a locked raid: the deliberate difference (in game a request to join, Discord refuses)
    tid = team(bob, "Kara A", ["Rita", "Gina"])
    occ = create(bob, i="kara", t=t0 + DAY, tm=[tid], lk=True)
    w.tick(2)
    res = both(lee, occ, "A")
    assert res["game"]["ok"] is True, res
    assert res["discord"] == {"ok": False, "e": "This raid is locked to its teams and invited players."}, res
    reqs = lee.eval_py("return ns.RaidPlan:GetRequests(...)", occ)
    assert [r["key"] for r in reqs] == [K("Lee")], reqs

    # removed by an organizer: a new answer, from either path, is newer than the removal
    for name, fn in PATHS:
        occ = create(bob, i="kara", t=t0 + DAY)
        w.tick(2)
        assert game(rita, occ, "A")["ok"] is True
        w.tick(2)
        assert call(bob, "RemoveSignup", occ, K("Rita"))["ok"] is True
        w.tick(2)
        assert K("Rita") not in signups(bob, occ), name
        assert fn(rita, occ, "T")["ok"] is True, name
        w.tick(3)
        # (the Discord path broadcasts nothing: every client runs it; read it where it ran)
        assert (signups(rita, occ) or {}).get(K("Rita"), {}).get("st") == "T", (name, signups(rita, occ))

    # notes: too long is refused and the stored note stays; false clears it
    for name, fn in PATHS:
        occ = create(bob, i="kara", t=t0 + DAY)
        w.tick(2)
        assert game(rita, occ, "A", None, "late 15")["ok"] is True
        r = fn(rita, occ, "T", None, LONG)
        assert r == {"ok": False, "e": "Notes are at most 40 characters."}, (name, r)
        su = signups(rita, occ)[K("Rita")]
        assert su["st"] == "A" and su["n"] == "late 15", (name, su)
        assert fn(rita, occ, "T", None, False)["ok"] is True, name
        su = signups(rita, occ)[K("Rita")]
        assert su["st"] == "T" and su.get("n") is None, (name, su)

    # over: 6 hours after the start (the server clock moved on)
    occ = create(bob, i="kara", t=t0 + 3600)
    w.tick(2)
    lee.eval("local base = GetServerTime; GetServerTime = function() return base() + 8 * 3600 end")
    refused_alike(both(lee, occ, "A"), "This raid is over.")
    w.assert_no_errors()


@case
def a_discord_answer_is_marked_and_keeps_the_note_when_none_is_given():
    w, c = world()
    bob, rita = c["Bob"], c["Rita"]
    occ = create(bob, i="kara", t=now(bob) + DAY)
    w.tick(2)
    assert game(rita, occ, "A", None, "late 15")["ok"] is True
    w.tick(2)
    # (another client takes the record: the answer is still Rita's)
    r = bob.eval_py("local o, k = ...; local ok, e = ns.RaidPlan:SignUpFor(o, k, 'T'); return { ok = ok, e = e }",
                    occ, K("Rita"))
    assert r["ok"] is True, r
    su = signups(bob, occ)[K("Rita")]
    assert su["st"] == "T" and su["n"] == "late 15" and su.get("dc") == 1, su
    w.assert_no_errors()


if __name__ == "__main__":
    run_all()
