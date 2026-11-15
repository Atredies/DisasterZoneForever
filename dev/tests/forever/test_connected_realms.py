"""Connected realms: a member whose character is from another realm of the group computes the same guild key as the
rest of the guild (Core/Guild.lua takes the realm from GetGuildInfo's 4th return), keeps their own realm in their
player key, and takes the guild bot's records (Core/Bridge.lua looks the bot's key up by the guild key).

Run: luaenv/bin/python tests/forever/test_connected_realms.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "boot-ui"))

from _common import case, run_all, World, Client  # noqa: E402


def guild_of_two_realms():
    w = World()
    gm = Client(w, "Gina", guild_rank=0)
    zed = Client(w, "Zed", realm="Other Realm", guild_rank=3)
    for c in (gm, zed):
        c.load_addon()
    w.tick(5)
    return w, gm, zed


@case
def a_member_from_another_realm_has_the_guilds_key():
    w, gm, zed = guild_of_two_realms()
    key = gm.eval("return ns.Guild:GetGuildKey()")
    assert key == "Casual Disaster-Thunderstrike", key
    assert zed.eval("return ns.Guild:GetGuildKey()") == key
    # their own key keeps their realm
    assert zed.eval("return ns.Util.PlayerKey()") == "Zed-OtherRealm"
    w.assert_no_errors()


if __name__ == "__main__":
    run_all("forever / connected realms")
