"""WoW Forever hides the realm from addons since build 1.60.1.71037 (2026-11-20): GetRealmName() and
GetNormalizedRealmName() return "", GetRealmID() 0, GetGuildInfo("player") no realm (measured in game 2026-11-22).

Before the fix every key lost its realm: "Arakis War-CAMWOWEU4Realm4PvP" became "Arakis War" and the guild
"Casual Disaster-CAMWOWEU4Realm4PvP" became "Casual Disaster-", so the saved members, professions, raids and recruits
were out of reach and the Professions page came up empty. The guild's realm now stands in (Util.HIDDEN_REALM).

Run: luaenv/bin/python tests/forever/test_forever_hidden_realm.py [-k name]
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

# The client as measured on build 71037: no realm anywhere.
HIDE_REALM = """
GetRealmName = function() return "" end
GetNormalizedRealmName = function() return "" end
GetRealmID = function() return 0 end
local gi = GetGuildInfo
GetGuildInfo = function(unit)
  local name, rank, index = gi(unit)
  return name, rank, index, nil
end
"""


def guild(names=((GM, "WARRIOR", 0), ("Missy Badshot", "HUNTER", 1), ("Aurel Namahs", "MAGE", 3))):
    w = World(realm=REALM)
    cs = []
    for name, cls, rank in names:
        c = Client(w, name, class_file=cls, guild_rank=rank, level=18, forever=True, preload_lua=HIDE_REALM)
        c.load_addon()
        cs.append(c)
    w.tick(5)
    return w, cs


def key(name):
    return "%s-%s" % (name, REALM_KEY)


@case
def test_the_client_hides_the_realm():
    w, (gm, missy, aurel) = guild()
    assert gm.eval("return GetRealmName()") == ""
    assert gm.eval("return GetNormalizedRealmName()") == ""


@case
def test_keys_keep_the_guilds_realm():
    w, (gm, missy, aurel) = guild()
    assert gm.eval("return ns.Util.PlayerKey()") == key(GM)
    assert gm.eval("return ns.Util.NormalizeName('Missy Badshot')") == key("Missy Badshot")
    assert gm.eval("return ns.Guild:GetGuildKey()") == "Casual Disaster-" + REALM_KEY
    no_errors(w)


@case
def test_the_guild_still_sees_itself():
    w, (gm, missy, aurel) = guild()
    w.tick(30)
    assert gm.eval("return ns.Guild:GetGM()") == key(GM)
    assert missy.eval("return ns.Guild:IsGM(...)", key(GM)) is True
    assert missy.eval("return ns.Sync:GetPeer(...) ~= nil", key(GM)) is True
    assert gm.eval("return ns.Sync:GetPeer(...) ~= nil", key("Aurel Namahs")) is True
    peers = gm.eval_py("return ns.db.peers") or {}
    assert key(GM) not in peers and GM not in peers, list(peers)
    no_errors(w)


@case
def test_the_developer_is_still_the_developer():
    w, (gm, missy, aurel) = guild()
    assert gm.eval("return ns.Util.IsDevKey(ns.Util.PlayerKey())") is True
    assert gm.eval("return ns.Perf:IsDev()") is True
    assert missy.eval("return ns.Perf:IsDev()") is False
    no_errors(w)


if __name__ == "__main__":
    run_all()
