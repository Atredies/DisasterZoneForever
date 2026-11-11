"""WoW Forever's regionally unique names: a character is "Arakis War", first name + surname, on the realm
"CAMWOW EU4 Realm 4 PvP". UnitName("player") gives the parts ("Arakis", "War"); the guild roster, chat and
addon-message senders the whole name (measured in game 2026-11-08; Blizzard_FrameXMLUtil/Camelot/NameUtil.lua).

Before the fix DisasterZone keyed itself "Arakis-<realm>" while the roster said "Arakis War": the Guild Master was not
the Guild Master to his own addon, his own messages came back as another player's, and he showed twice on the
Members page. These cases use the guild's real names.

Run: luaenv/bin/python tests/forever/test_forever_names.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"
REALM_KEY = "CAMWOWEU4Realm4PvP"
GM = "Arakis War"


def guild(names=((GM, "WARRIOR", 0), ("Missy Badshot", "HUNTER", 1), ("Aurel Namahs", "MAGE", 3))):
    w = World(realm=REALM)
    cs = []
    for name, cls, rank in names:
        c = Client(w, name, class_file=cls, guild_rank=rank, level=18, forever=True)
        c.load_addon()
        cs.append(c)
    w.tick(5)
    return w, cs


def key(name):
    return "%s-%s" % (name, REALM_KEY)


@case
def test_the_client_splits_names_like_forever():
    w, (gm, missy, aurel) = guild()
    assert gm.eval("return (UnitName('player'))") == "Arakis"
    assert gm.eval("return select(2, UnitName('player'))") == "War"
    assert gm.eval("return GetUnitName('player', true)") == GM
    rows = [gm.eval("return (GetGuildRosterInfo(%d))" % i) for i in range(1, 4)]
    assert GM in rows, rows


@case
def test_i_am_myself_with_a_surname():
    w, (gm, missy, aurel) = guild()
    assert gm.eval("return ns.Util.PlayerKey()") == key(GM)
    assert gm.eval("return ns.Util.IsMe(...)", key(GM)) is True
    assert missy.eval("return ns.Util.PlayerKey()") == key("Missy Badshot")
    no_errors(w)


@case
def test_the_guild_master_is_the_guild_master():
    w, (gm, missy, aurel) = guild()
    assert gm.eval("return ns.Guild:GetGM()") == key(GM)
    assert gm.eval("return ns.Guild:IsGM(ns.Util.PlayerKey())") is True
    assert missy.eval("return ns.Guild:IsGM(...)", key(GM)) is True
    assert missy.eval("return ns.Guild:IsOfficer(ns.Util.PlayerKey(), true)") is True
    assert aurel.eval("return ns.Guild:IsGM(ns.Util.PlayerKey())") is False
    no_errors(w)


@case
def test_my_own_messages_are_mine():
    w, (gm, missy, aurel) = guild()
    w.tick(30)
    peers = gm.eval_py("return ns.db.peers") or {}
    assert key(GM) not in peers, "the GM's addon took its own messages for another player's: %s" % list(peers)
    assert missy.eval("return ns.Sync:GetPeer(...) ~= nil", key(GM)) is True
    no_errors(w)


@case
def test_party_units_key_with_the_surname():
    w, (gm, missy, aurel) = guild()
    w.make_party([gm, missy])
    w.tick(2)
    assert gm.eval("return ns.Util.UnitKey('party1')") == key("Missy Badshot")
    assert gm.eval("return ns.Util.GetPartyUnit(...)", key("Missy Badshot")) == "party1"
    no_errors(w)


if __name__ == "__main__":
    run_all()
