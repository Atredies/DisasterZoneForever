#!/usr/bin/env python
"""Loot-roll area: a boss drops the same item twice (two "Gloves of the Fallen Defender" tokens).

Each copy is its own roll and its own award. Covered here (2026-11-09 fix, vault 09-Reference/Duplicate Drops Fix):
  - reserves: each copy uses up one reservation. Copy 2 does not go to copy 1's only reserver again (it is up for
    grabs), and it is not rolled among the same reservers again with copy 1's winner still in;
  - the loot log: one player getting both copies within two minutes is two awards (roll awards, Award menu, loot
    lines, also two loot lines in the same server second), while the same award recorded by several council members
    still shows once; voiding one copy's loot line leaves the other.

Run: luaenv/bin/python tests/loot-roll/test_duplicate_items.py   [-k substring]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reserves"))

from lr_common import *  # noqa: F401,F403,E402
from rv_common import (reserve_raid, open_reserves, roll_kind, results_rv, raid_lines, whisper,  # noqa: E402
                       decide)

R = Runner("loot-roll / duplicate items")

COUNCIL = ("Alice", "Bob")


def wait_session(r, pred, by="Alice", seconds=20):
    """Ticks until by's active session satisfies pred (or seconds pass); returns it (or the last one seen)."""
    s = None
    for _ in range(int(seconds * 4)):
        s = active_session(r[by])
        if s and pred(s):
            r.w.tick(1)   # (the RS reaches the raid)
            return s
        r.w.tick(0.25)
    return s


def award(r, sid, name, by="Alice"):
    """Awards session sid to name through the confirm popup (the loot window is closed: no master-loot hand-out)."""
    r[by].eval("ns.Roll:Award(...)", sid, key(name))
    r.w.tick(0.2)
    r[by].accept_popup("DISASTERZONE_CONFIRM_AWARD")
    r.w.tick(1)


def visible(r, name, item=None):
    return [e for e in ledger_visible(r[name]) if item is None or e["i"] == item]


def count_since(c, name, since=0):
    return c.eval("return ns.Ledger:CountSince(...)", key(name), since)


# ------------------------------------------------------------------------------------------------------------------
# Reserves
# ------------------------------------------------------------------------------------------------------------------
@R.case
def reserves_one_reserver_two_copies_second_is_up_for_grabs():
    r = reserve_raid()
    w = r.w
    open_reserves(r, n=1)
    r["Dave"].eval("ns.Reserves:Reserve(...)", THOUSAND_MARKS)
    w.tick(2)
    r["Alice"].open_loot([(THOUSAND_MARKS, 4), (THOUSAND_MARKS, 4)])
    w.tick(2)
    c0 = len(w.chat_log)
    r["Alice"].eval("ns.DropPanel:RollAll()")
    w.tick(1)
    s1 = active_session(r["Alice"])
    assert s1 and s1["c"] == 1, s1
    assert roll_kind(r["Alice"], s1["id"]) == {"k": "s", "keys": [key("Dave")]}
    # copy 1 names Dave and closes by itself; copy 2 opens without anyone awarding copy 1 yet
    s2 = wait_session(r, lambda s: s["c"] == 2)
    assert s2 and s2["c"] == 2 and s2["id"] != s1["id"], s2
    for n in ("Alice", "Bob", "Carol"):
        k = roll_kind(r[n], s2["id"])
        assert k["k"] == "o", "copy 2 must be up for grabs on %s, not Dave's again: %r" % (n, k)
    lines = [t for _, t in raid_lines(r, c0)]
    assert sum(1 for t in lines if "goes to Dave: the only reserve" in t) == 1, lines
    assert any("up for grabs" in t for t in lines), lines
    w.player_roll("Yuri", 81)
    w.player_roll("Dave", 99)          # Dave's reservation went to copy 1: he can still roll on the spare copy
    w.tick(1)
    res = results_rv(r["Alice"], s2["id"])
    assert [x for x in res if x["suggested"]][0]["key"] == key("Dave"), res
    w.assert_no_errors()


@R.case
def reserves_one_reserver_copy_one_awarded_first():
    r = reserve_raid()
    w = r.w
    open_reserves(r, n=1)
    r["Dave"].eval("ns.Reserves:Reserve(...)", THOUSAND_MARKS)
    w.tick(2)
    r["Alice"].open_loot([(THOUSAND_MARKS, 4), (THOUSAND_MARKS, 4)])
    w.tick(2)
    r["Alice"].close_loot()
    w.tick(0.5)
    r["Alice"].eval("ns.DropPanel:StartRoll(...)", THOUSAND_MARKS, 1)
    w.tick(1)
    s1 = active_session(r["Alice"])
    w.tick(6)
    award(r, s1["id"], "Dave")
    r["Alice"].eval("ns.DropPanel:StartRoll(...)", THOUSAND_MARKS, 2)
    s2 = wait_session(r, lambda s: s["c"] == 2)
    assert s2 and s2["c"] == 2, s2
    assert roll_kind(r["Bob"], s2["id"])["k"] == "o", roll_kind(r["Bob"], s2["id"])
    w.assert_no_errors()


@R.case
def reserves_two_reservers_two_copies_each_gets_one():
    r = reserve_raid()
    w = r.w
    open_reserves(r, n=1)
    whisper(r, "Yuri", "!sr Ruby Drape")
    r["Bob"].eval("ns.Reserves:Reserve(...)", RUBY_DRAPE)
    w.tick(2)
    r["Alice"].open_loot([(RUBY_DRAPE, 4), (RUBY_DRAPE, 4)])
    w.tick(2)
    r["Alice"].eval("ns.DropPanel:RollAll()")
    w.tick(1)
    s1 = active_session(r["Alice"])
    assert s1 and s1["c"] == 1, s1
    assert roll_kind(r["Alice"], s1["id"]) == {"k": "s", "keys": [key("Bob"), key("Yuri")]}
    w.player_roll("Yuri", 40)
    w.player_roll("Bob", 70)
    c0 = len(w.chat_log)
    # copy 2 opens once copy 1 closed (not awarded yet): Bob, copy 1's winner, is not a reserver of copy 2
    s2 = wait_session(r, lambda s: s["c"] == 2, seconds=60)
    assert s2 and s2["c"] == 2, s2
    for n in ("Alice", "Bob", "Carol"):
        k = roll_kind(r[n], s2["id"])
        assert k == {"k": "s", "keys": [key("Yuri")]}, "copy 2 on %s: %r" % (n, k)
    assert any("goes to Yuri: the only reserve" in t for _, t in raid_lines(r, c0)), raid_lines(r, c0)
    w.assert_no_errors()


@R.case
def reserves_two_reservers_copy_one_awarded_to_the_low_roller():
    """The council awards copy 1 to someone other than the top roller: copy 2's reservers are the rest."""
    r = reserve_raid()
    w = r.w
    open_reserves(r, n=1)
    whisper(r, "Yuri", "!sr Ruby Drape")
    r["Bob"].eval("ns.Reserves:Reserve(...)", RUBY_DRAPE)
    r["Dave"].eval("ns.Reserves:Reserve(...)", RUBY_DRAPE)
    w.tick(2)
    r["Alice"].open_loot([(RUBY_DRAPE, 4), (RUBY_DRAPE, 4)])
    w.tick(2)
    r["Alice"].close_loot()
    w.tick(0.5)
    r["Alice"].eval("ns.DropPanel:StartRoll(...)", RUBY_DRAPE, 1)
    w.tick(1)
    s1 = active_session(r["Alice"])
    w.player_roll("Yuri", 40)
    w.player_roll("Bob", 70)
    w.player_roll("Dave", 20)
    w.tick(31)
    award(r, s1["id"], "Yuri")
    r["Alice"].eval("ns.DropPanel:StartRoll(...)", RUBY_DRAPE, 2)
    s2 = wait_session(r, lambda s: s["c"] == 2)
    k = roll_kind(r["Carol"], s2["id"])
    assert k == {"k": "s", "keys": [key("Bob"), key("Dave")]}, k
    w.assert_no_errors()


@R.case
def reserves_held_item_two_copies_both_for_the_guild():
    r = reserve_raid()
    w = r.w
    open_reserves(r, n=1, held=[RUBY_DRAPE])
    r["Alice"].open_loot([(RUBY_DRAPE, 4), (RUBY_DRAPE, 4)])
    w.tick(2)
    r["Alice"].eval("ns.DropPanel:RollAll()")
    w.tick(1)
    s1 = active_session(r["Alice"])
    assert roll_kind(r["Bob"], s1["id"])["k"] == "g"
    r["Alice"].eval("ns.Roll:End(...)", s1["id"])
    s2 = wait_session(r, lambda s: s["c"] == 2)
    assert s2 and s2["c"] == 2 and roll_kind(r["Bob"], s2["id"])["k"] == "g", s2
    w.assert_no_errors()


@R.case
def reserves_single_copy_unchanged():
    r = reserve_raid()
    w = r.w
    open_reserves(r, n=1)
    r["Dave"].eval("ns.Reserves:Reserve(...)", THOUSAND_MARKS)
    w.tick(2)
    assert decide(r["Alice"], THOUSAND_MARKS) == {"k": "s", "keys": [key("Dave")]}
    r["Alice"].open_loot([(THOUSAND_MARKS, 4)])
    w.tick(2)
    r["Alice"].eval("ns.DropPanel:StartRoll(...)", THOUSAND_MARKS, 1)
    w.tick(1)
    s1 = active_session(r["Alice"])
    assert roll_kind(r["Bob"], s1["id"]) == {"k": "s", "keys": [key("Dave")]}
    w.assert_no_errors()


# ------------------------------------------------------------------------------------------------------------------
# The loot log
# ------------------------------------------------------------------------------------------------------------------
@R.case
def ledger_one_player_wins_both_copies_by_roll():
    r = Raid()
    w = r.w
    r["Alice"].open_loot([(HELM_CHAMPION, 4), (HELM_CHAMPION, 4)])
    w.tick(2)
    r["Alice"].close_loot()
    w.tick(0.5)
    t0 = r["Alice"].eval("return GetServerTime()")
    r["Alice"].eval("ns.DropPanel:RollAll()")
    w.tick(1)
    s1 = active_session(r["Alice"])
    w.player_roll("Erin", 90)
    w.tick(31)
    award(r, s1["id"], "Erin")
    s2 = wait_session(r, lambda s: s["c"] == 2)
    assert s2 and s2["c"] == 2, s2
    w.player_roll("Erin", 50)
    w.tick(31)
    award(r, s2["id"], "Erin")
    w.tick(3)
    for n in COUNCIL:
        vis = visible(r, n, HELM_CHAMPION)
        assert len(vis) == 2 and all(e["w"] == key("Erin") for e in vis), (n, vis)
        assert count_since(r[n], "Erin", t0) == 2, (n, count_since(r[n], "Erin", t0))
    blocks = [b for b in panel_blocks(r["Bob"]) if b["item"] == HELM_CHAMPION]
    assert len(blocks) == 2 and all("Erin" in strip_codes(b["awarded"]) for b in blocks), blocks
    w.assert_no_errors()


@R.case
def ledger_one_player_gets_both_copies_from_the_award_menu():
    r = Raid()
    w = r.w
    r["Alice"].open_loot([(HELM_CHAMPION, 4), (HELM_CHAMPION, 4)])
    w.tick(2)
    r["Alice"].close_loot()
    w.tick(0.5)
    r["Alice"].eval("ns.DropPanel:Award(%d, 'Erin-Thunderstrike', 'Karazhan:Prince')" % HELM_CHAMPION)
    w.tick(5)
    r["Alice"].eval("ns.DropPanel:Award(%d, 'Erin-Thunderstrike', 'Karazhan:Prince')" % HELM_CHAMPION)
    w.tick(3)
    for n in COUNCIL:
        vis = visible(r, n, HELM_CHAMPION)
        assert len(vis) == 2, (n, vis)
    w.assert_no_errors()


@R.case
def ledger_two_loot_lines_same_winner_same_second():
    r = Raid()
    w = r.w
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION)
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION)
    w.tick(4)
    ids = {}
    for n in COUNCIL:
        vis = visible(r, n, HELM_CHAMPION)
        assert len(vis) == 2, (n, vis, ledger_raw(r[n]))
        ids[n] = sorted(e["id"] for e in vis)
        assert count_since(r[n], "Erin") == 2, n
    assert ids["Alice"] == ids["Bob"], ids
    w.assert_no_errors()


@R.case
def ledger_two_loot_lines_same_winner_seconds_apart_seen_at_different_seconds():
    r = Raid()
    w = r.w
    others = [c for c in r.clients if c.name != "Alice"]
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION, clients=[r["Alice"]])
    w.tick(1.6)
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION, clients=others)      # Bob sees line 1 a second later
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION, clients=[r["Alice"]])
    w.tick(1.6)
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION, clients=others)      # ... and line 2
    w.tick(4)
    # (Bob's entry of line 1 and Alice's of line 2 fall in the same server second and so share an id: the clients may
    # show different entries of the two lines, but both show two awards)
    for n in COUNCIL:
        vis = visible(r, n, HELM_CHAMPION)
        assert len(vis) == 2, (n, vis, ledger_raw(r[n]))
        assert count_since(r[n], "Erin") == 2, n
    w.assert_no_errors()


@R.case
def ledger_one_loot_line_on_two_council_clients_still_one():
    r = Raid()
    w = r.w
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION, clients=[r["Alice"]])
    w.tick(1.6)
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION, clients=[c for c in r.clients if c.name != "Alice"])
    w.tick(4)
    for n in COUNCIL:
        assert len(visible(r, n, HELM_CHAMPION)) == 1, (n, ledger_raw(r[n]))
    w.assert_no_errors()


@R.case
def ledger_void_one_of_two_loot_lines_keeps_the_other():
    r = Raid()
    w = r.w
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION)
    w.tick(1.2)
    w.broadcast_loot_received(r["Erin"], HELM_CHAMPION)
    w.tick(4)
    vis = visible(r, "Alice", HELM_CHAMPION)
    assert len(vis) == 2, (vis, ledger_raw(r["Alice"]))
    r["Alice"].eval("ns.Ledger:Void(...)", vis[0]["id"], True)
    w.tick(3)
    for n in COUNCIL:
        left = visible(r, n, HELM_CHAMPION)
        assert len([e for e in left if not e.get("vd")]) == 1, (n, left)
    w.assert_no_errors()


if __name__ == "__main__":
    main(R)
