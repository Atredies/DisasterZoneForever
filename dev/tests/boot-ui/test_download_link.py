"""The download link, easy to copy and paste to others: /dz download (and /dz link) print it and open a box with it
selected; Settings > About has a "Copy link" button for the same box; the game hub's "Get the game" shows the same
address (Core/Util.lua DOWNLOAD_URL, UI/Settings.lua).

Run: luaenv/bin/python tests/boot-ui/test_download_link.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _common import case, run_all, World, Client, printed_since  # noqa: E402

URL = "https://github.com/Atredies/DisasterZoneForever/releases/latest"


def one():
    w = World()
    c = Client(w, "Gina", guild_rank=3)
    c.load_addon()
    w.tick(3)
    return w, c


@case
def the_slash_commands_print_it_and_open_the_box():
    w, c = one()
    assert c.eval("return ns.Util.DOWNLOAD_URL") == URL
    for line in ("/dz download", "/dz link"):
        n0 = len(c.chat_frame)
        assert c.slash(line), line
        w.tick(1)
        out = printed_since(c, n0)
        assert any(URL in str(m) for m in out), (line, out[-3:])
        assert c.eval("return ns.Popup:IsShown()") is True
        c.eval("ns.Popup:Hide('DISASTERZONE_DOWNLOAD_LINK')")
    w.assert_no_errors()


@case
def the_box_holds_the_link_and_typing_cannot_change_it():
    w, c = one()
    d = "local d = ns.Popup:Show('DISASTERZONE_DOWNLOAD_LINK') "
    assert c.eval(d + "return d.editBox:GetText()") == URL
    c.eval(d + "d.editBox:SetText('something else') local s = d.editBox:GetScript('OnTextChanged') "
           "if s then s(d.editBox, true) end")
    assert c.eval(d + "return d.editBox:GetText()") == URL
    w.assert_no_errors()


@case
def the_game_hub_shows_the_same_address():
    w, c = one()
    assert c.eval("return ns.Games.RELEASES") == URL
    w.assert_no_errors()


if __name__ == "__main__":
    run_all()
