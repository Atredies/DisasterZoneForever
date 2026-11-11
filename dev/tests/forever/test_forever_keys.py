"""Keyboard handlers in combat on WoW Forever: Frame:SetPropagateKeyboardInput is protected in combat. In game
(2026-11-09) DisasterZone got ADDON_ACTION_BLOCKED for it with the Atlas page open in a fight. Every call now goes
through Util.SetPropagateKeys, which does nothing in combat. The mock's Forever profile blocks the raw call in combat.

The sweep opens every page of the main window, enters combat and presses keys on every frame that has an OnKeyDown
script, then checks nothing was blocked.

Run: luaenv/bin/python tests/forever/test_forever_keys.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"
PAGES = ["home", "raids", "mybis", "gearsim", "consumables", "wardrobe", "atlas", "members", "map", "events", "polls",
         "recruit", "audit", "games", "council", "lootrules", "mylog"]

PRESS_ALL = r"""
local key = ...
local n = 0
for _, f in ipairs(__MOCK.all_objects) do
  local st = __MOCK.OBJ[f]
  local fn = st and st.scripts and st.scripts.OnKeyDown
  if fn and f.IsVisible and f:IsVisible() then
    n = n + 1
    __MOCK.safecall("OnKeyDown", fn, f, key)
  end
end
return n
"""


def gm():
    w = World(realm=REALM)
    c = Client(w, "Arakis War", class_file="WARRIOR", guild_rank=0, level=18, forever=True)
    c.load_addon()
    w.tick(5)
    return w, c


@case
def test_the_raw_call_is_blocked_in_combat():
    w, c = gm()
    c.eval("__f = CreateFrame('Frame'); __f:SetPropagateKeyboardInput(true)")
    assert not any("ADDON_ACTION_BLOCKED" in e for e in w.errors())
    c.set_combat(True)
    c.eval("__f:SetPropagateKeyboardInput(false)")
    assert any("SetPropagateKeyboardInput" in e for e in w.errors())


@case
def test_the_helper_waits_out_combat():
    w, c = gm()
    c.eval("__f = CreateFrame('Frame')")
    assert c.eval("return ns.Util.SetPropagateKeys(__f, true)") is True
    c.set_combat(True)
    assert c.eval("return ns.Util.SetPropagateKeys(__f, false)") is False
    assert c.eval("return __MOCK.OBJ[__f].propagate") is True          # (not changed in combat)
    c.set_combat(False)
    assert c.eval("return __MOCK.OBJ[__f].propagate") is False         # applied when combat ended
    assert c.eval("return ns.Util.SetPropagateKeys(__f, true)") is True
    no_errors(w)


@case
def test_pages_first_opened_in_combat():
    """The in-game case: the Atlas page built for the first time during a fight (its set-up called the protected
    function)."""
    w, c = gm()
    c.set_combat(True)
    for page in PAGES:
        c.eval("ns.MainFrame:Open(...)", page)
        w.tick(0.3)
    assert not c.eval_py("return __MOCK.blocked"), c.eval_py("return __MOCK.blocked")
    no_errors(w)


@case
def test_keys_on_every_page_in_combat():
    w, c = gm()
    pressed = 0
    for page in PAGES:
        c.eval("ns.MainFrame:Open(...)", page)
        w.tick(0.5)
        c.set_combat(True)
        for key in ("A", "ESCAPE", "ENTER", "LEFT"):
            pressed += c.eval(PRESS_ALL, key)
        c.set_combat(False)
        w.tick(0.2)
    assert pressed > 0, "no key handler was reached"
    assert not c.eval_py("return __MOCK.blocked"), c.eval_py("return __MOCK.blocked")
    no_errors(w)


if __name__ == "__main__":
    run_all()
