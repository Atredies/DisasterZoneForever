#!/usr/bin/env python
"""Loot-roll area: an open roll comes back after a /reload (DisasterZone Forever 0.2).

Sessions live in memory only, so a raider who /reloads mid-roll lost the roll window. Now the client asks the group
for open rolls after a login / reload (RQ) and the starter sends its RS again with the time left (re = 1):
  * a raider /reloads mid-roll: the roll and its window come back with the remaining time, the Roll button works and
    the roll closes and is awarded on the raider like everywhere else;
  * clients that already know the roll ignore the re-sent RS: no second session, no second ROLL_STARTED, a raider
    who passed does not get the window again;
  * two raiders reloading together get one answer;
  * a roll that closed before the reload (or before the RQ) is not reopened, and nothing is re-sent for it.

Run: luaenv/bin/python tests/loot-roll/test_roll_reload.py   [-k substring]
"""
from lr_common import *  # noqa: F401,F403

R = Runner("loot-roll / roll after /reload")

ADDON_USERS = ("Alice", "Bob", "Carol", "Dave", "Erin", "Frank", "Gina")

STARTED_PROBE = r"""
__RLD = { started = 0 }
ns:On("ROLL_STARTED", function() __RLD.started = __RLD.started + 1 end)
"""


class FixedRng:
    def __init__(self, value):
        self.value = value

    def randint(self, lo, hi):
        return self.value


def setup():
    r = Raid()
    r["Alice"].open_loot([(RUBY_DRAPE, 4), (THOUSAND_MARKS, 4)])
    r.w.tick(2)
    return r


def start(r, item=RUBY_DRAPE):
    r["Alice"].eval("ns.DropPanel:StartRoll(...)", item, 1)
    r.w.tick(1)
    s = active_session(r["Alice"])
    assert s and s["i"] == item, s
    return s["id"]


def click_roll(r, name, value):
    c = r[name]
    assert c.eval("return ns.RollFrame.frame:IsShown() and ns.RollFrame.frame.roll:IsShown()"), \
        "%s: Roll button not visible (%r)" % (name, rollframe_state(c))
    r.w._roll_rng = FixedRng(value)
    c.click(c.eval("return ns.RollFrame.frame.roll"))
    del r.w._roll_rng


def reload(r, name):
    r[name].relog()
    install_probes([r[name]])


def resent(r, mark):
    return [m for m in msgs_of_type(r.w, "RS", mark) if m.get("re") == 1]


@R.case
def raider_reload_gets_the_window_back():
    r = setup()
    w = r.w
    sid = start(r)
    w.tick(4)
    mark = len(w.addon_log)
    reload(r, "Dave")
    assert r["Dave"].eval("return ns.Roll:Get(...) == nil", sid)
    w.tick(10, 0.25)
    rq = msgs_of_type(w, "RQ", mark)
    assert [m["_sender"] for m in rq] == [r["Dave"].full_name], rq
    rs = resent(r, mark)
    assert len(rs) == 1 and rs[0]["id"] == sid and rs[0]["_sender"] == r["Alice"].full_name, rs
    info = session_info(r["Dave"], sid)
    assert info and info["state"] == "open" and info["starter"] == key("Alice"), info
    left = r["Dave"].eval("return ns.Roll:GetTimeLeft(...)", sid)
    alice_left = r["Alice"].eval("return ns.Roll:GetTimeLeft(...)", sid)
    assert 0 < left <= alice_left <= 30 - 14, (left, alice_left)
    rf = rollframe_state(r["Dave"])
    assert rf["shown"] and rf["id"] == sid and rf["rollShown"], rf
    click_roll(r, "Dave", 77)
    w.tick(1)
    d = [x for x in results(r["Alice"], sid) if x["key"] == key("Dave")]
    assert d and d[0]["roll"] == 77, results(r["Alice"], sid)
    # it closes on the raider with everyone else's, and the award reaches it
    w.tick(20)
    assert session_info(r["Dave"], sid)["state"] == "closed", session_info(r["Dave"], sid)
    r["Alice"].eval("ns.DropPanel:AwardRoll(...)", sid, key("Dave"))
    w.tick(0.3)
    r["Alice"].accept_popup("DISASTERZONE_GIVE_ITEM")
    w.tick(3)
    for n in ADDON_USERS:
        info = session_info(r[n], sid)
        assert info["state"] == "awarded" and info["winner"] == key("Dave"), (n, info)
    w.assert_no_errors()


@R.case
def others_ignore_the_resent_start():
    r = setup()
    w = r.w
    for n in ADDON_USERS:
        r[n].eval(STARTED_PROBE)
    sid = start(r)
    r["Carol"].click(r["Carol"].eval("return ns.RollFrame.frame.pass"))
    w.tick(2)
    carol_before = rollframe_state(r["Carol"])
    for n in ADDON_USERS:
        r[n].eval("__RLD.started = 0")   # (the roll's own start counted once everywhere)
    mark = len(w.addon_log)
    reload(r, "Dave")
    r["Dave"].eval(STARTED_PROBE)
    w.tick(10, 0.25)
    assert len(resent(r, mark)) == 1
    for n in ADDON_USERS:
        if n == "Dave":
            continue
        assert r[n].eval("return __RLD.started") == 0, (n, r[n].eval("return __RLD.started"))
        assert session_info(r[n], sid)["state"] == "open", n
    assert r["Dave"].eval("return __RLD.started") == 1
    # Carol passed: her popup is as it was (no second window, she still passed)
    assert rollframe_state(r["Carol"]) == carol_before, (rollframe_state(r["Carol"]), carol_before)
    assert session_info(r["Alice"], sid)["responses"].get(key("Carol")) == "pass"
    w.assert_no_errors()


@R.case
def two_reloads_one_answer():
    r = setup()
    w = r.w
    sid = start(r)
    w.tick(3)
    mark = len(w.addon_log)
    reload(r, "Dave")
    reload(r, "Erin")
    w.tick(10, 0.25)
    assert len(msgs_of_type(w, "RQ", mark)) == 2
    rs = resent(r, mark)
    assert len(rs) == 1 and rs[0]["id"] == sid, rs
    for n in ("Dave", "Erin"):
        assert session_info(r[n], sid)["state"] == "open", n
        assert rollframe_state(r[n])["shown"], (n, rollframe_state(r[n]))
    w.assert_no_errors()


@R.case
def closed_roll_is_not_reopened():
    r = setup()
    w = r.w
    sid = start(r)
    w.tick(2)
    r["Alice"].eval("ns.Roll:End(...)", sid)
    w.tick(1)
    assert session_info(r["Alice"], sid)["state"] == "closed"
    mark = len(w.addon_log)
    reload(r, "Dave")
    w.tick(10, 0.25)
    assert resent(r, mark) == [], resent(r, mark)
    assert r["Dave"].eval("return ns.Roll:Get(...) == nil", sid)
    assert not rollframe_state(r["Dave"])["shown"], rollframe_state(r["Dave"])
    for n in ADDON_USERS:
        if n != "Dave":
            assert session_info(r[n], sid)["state"] == "closed", n
    w.assert_no_errors()


@R.case
def roll_ending_before_the_answer_is_not_resent():
    """The roll is about to end when the raider reloads: nothing comes back with less than 5 s left."""
    r = setup()
    w = r.w
    sid = start(r)
    w.tick(21)          # ~8 s left: the RQ (6-8 s after the reload) finds less than 5 s
    mark = len(w.addon_log)
    reload(r, "Dave")
    w.tick(10, 0.25)
    assert resent(r, mark) == [], resent(r, mark)
    assert r["Dave"].eval("return ns.Roll:Get(...) == nil", sid)
    w.assert_no_errors()


if __name__ == "__main__":
    main(R)
