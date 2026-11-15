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


@case
def a_whisper_keeps_a_forever_surname():
    """Util.Whisper hands the whole "First Last" name to Blizzard's SendTell (typing "/w Arakis War " in parsed at the
    first space: a whisper to "Arakis" saying "War"). Every Whisper button and menu uses it."""
    w, gm, zed = guild_of_two_realms()
    gm.eval("_G.__tells = {}; ChatFrameUtil = ChatFrameUtil or {}; "
            "ChatFrameUtil.SendTellWithMessage = function(name, text) table.insert(__tells, name .. '|' .. text) end")
    gm.eval("ns.Util.Whisper('Arakis War-Thunderstrike')")
    gm.eval("ns.Util.Whisper('Zed-OtherRealm', 'hi ')")
    assert gm.eval_py("return __tells") in (["Arakis War|", "Zed-OtherRealm|hi "], {1: "Arakis War|", 2: "Zed-OtherRealm|hi "}), \
        gm.eval_py("return __tells")
    w.assert_no_errors()


if __name__ == "__main__":
    run_all("forever / connected realms")
