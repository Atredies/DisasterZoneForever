"""WoW Forever: TBC leftovers in user-facing words and defaults (sweep 2026-11-09, branch fix/forever-quick-fixes).

Covers: the events' "Max level" sign-up compares with Forever's cap (60), not 70, and says the real level; phase words
go through ns.PhaseLabel / ns.PHASE_WORD ("S1", "Season"); the Atlas currency bar pins Honor only; the guild map and
the event builder's zone list have no Outland; new raid team lineups take the planner's default size and the team
themes are Forever's raids; the recruit milestones name levels 40 and 60; a new event's art is Warsong Gulch. The TBC
client keeps its words (checked here once, the upstream suites cover the rest).

Run: luaenv/bin/python tests/forever/test_forever_quick_fixes.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import World, Client, case, run_all, solo, no_errors, menu_texts, install_helpers  # noqa: E402

# (as tests/boot-ui/test_settings.py: importing it would run its cases here too)
DD_LIST = r"""
function T_settings() return ns.MainFrame:GetPanel("settings") end
function T_dropdowns(root)
  local out = {}
  for _, f in ipairs(T_dropdown_list(root)) do
    local m = T_menu(f)
    local first = m and m.children[1] and m.children[1].text or ""
    out[#out + 1] = { f, first }
  end
  return out
end
function T_dd_by_first(root, first)
  for _, e in ipairs(T_dropdowns(root)) do if e[2] == first then return e[1] end end
end
"""


def settings_client(**kw):
    w, c = solo("Alice", tick=3, **kw)
    install_helpers(c)
    c.eval(DD_LIST)
    c.slash("/dz settings")
    w.tick(0.5)
    return w, c


def as_list(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v)]
    return list(v or [])


def guild(levels, forever=True):
    """One guild: the first name is the GM (rank 0), the rest members (rank 3); levels = [(name, level)]."""
    w = World()
    cs = []
    for i, (name, level) in enumerate(levels):
        cs.append(Client(w, name, guild_rank=0 if i == 0 else 3, class_file="WARRIOR", level=level, forever=forever))
    for c in cs:
        c.load_addon()
    w.tick(50)
    return w, cs


@case
def test_max_level_sign_up_takes_level_60_on_forever():
    w, (g, cap, low) = guild([("Gina", 60), ("Cappy", 60), ("Lowbie", 55)])
    assert g.eval("return ns.Events:MaxLevel()") == 60
    assert g.eval("return ns.EventBlocks.SMART.signup.settings[3].label") == "Max level"
    assert g.eval("return ns.EventBlocks.SMART.signup.settings[3].key") == "lvl70"   # (saved and sent: kept)
    occ = g.eval("local d = ns.Events:NewDef(true); ns.Events:SaveDef(d)"
                 " return ns.Events:Schedule(d.id, GetServerTime() + 3600)")
    w.tick(6)
    assert g.eval("return ns.Events:Needs70(ns.Events:GetOcc(...).def)", occ) is True
    # a level 60 character is at the cap on Forever (it was refused while the check said 70)
    assert cap.eval("return (ns.Events:SignUp(..., true))", occ) is True
    got = low.eval_py("return { ns.Events:SignUp(..., true) }", occ)
    assert got == [False, "This one is for level 60 characters."], got
    no_errors(w)


@case
def test_tbc_sign_up_still_asks_level_70():
    w, c = solo(level=70)
    assert c.eval("return ns.Events:MaxLevel()") == 70
    assert c.eval("return ns.EventBlocks.DEFAULT_ART") == "nagrand"
    assert c.eval("return ns.Currency.PINNED[2]") == "c1900"
    assert as_list(c.eval_py("local o = {} for _, x in ipairs(ns.GuildMap.CONTINENTS) do o[#o + 1] = x.id end"
                             " return o")) == [1414, 1415, 1945]
    no_errors(w)


@case
def test_phase_words_are_seasons_on_forever():
    w, c = settings_client(guild_rank=3, level=60, forever=True)
    assert c.eval("return ns.PhaseLabel(1)") == "S1"
    assert c.eval("return ns.PHASE_WORD") == "Season"
    # Settings: the view phase menu ("Follow guild (S1)", "S1 · Onyxia, ...")
    vp = c.eval("return T_dd_by_first(T_settings(), 'Follow guild (S1)')")
    assert vp is not None, c.eval_py("local o = {} for i, e in ipairs(T_dropdowns(T_settings())) do o[i] = e[2] end"
                                     " return o")
    c.eval("ns.SettingsUI:Reveal(...)", vp)
    texts = [e[2] for e in menu_texts(c.dropdown_menu(vp))]
    assert texts == ["Follow guild (S1)", "S1 · Onyxia, Barrow Deeps, Hyjal"], texts
    src = os.path.join(os.environ.get("DISASTERZONE_ADDON_DIR", os.path.join(TESTS, "..", "..", "addon",
                                                                             "DisasterZone")))
    # no hard-coded "P%d" / "Phase " .. p is left in the files this sweep fixed
    for rel in ("UI/Council.lua", "UI/DropPanel.lua", "UI/Dashboard.lua", "UI/GroupsSheet.lua", "UI/AtlasNav.lua",
                "UI/Settings.lua", "UI/Atlas.lua"):
        with open(os.path.join(src, rel), encoding="utf-8") as f:
            text = f.read()
        for bad in ('P%d', '"Phase " ..', '("P" ..', '"P" .. p'):
            assert bad not in text, (rel, bad)
    no_errors(w)


@case
def test_forever_lists_and_defaults():
    w, c = solo(level=60, forever=True)
    # the Atlas currency bar: Honor only (no Arena Points, no Badge of Justice)
    assert as_list(c.eval_py("return ns.Currency.PINNED")) == ["c1901"]
    # the guild map: Kalimdor and the Eastern Kingdoms, no Outland
    assert as_list(c.eval_py("local o = {} for _, x in ipairs(ns.GuildMap.CONTINENTS) do o[#o + 1] = x.id end"
                             " return o")) == [1414, 1415]
    assert c.eval("return ns.GuildMap.DEFAULT_CONTINENT") == 1415
    # a new event: Warsong Gulch art; the art picker has no Outland or arena screens
    assert c.eval("return ns.EventBlocks:Blank().art") == "wsg"
    arts = as_list(c.eval_py("local o = {} for _, a in ipairs(ns.EventBlocks.ART) do o[#o + 1] = a[1] end return o"))
    assert "nagrand" not in arts and "outland" not in arts and "eots" not in arts, arts
    art = c.eval("return ns.EventBlocks:ArtPath('nope')")      # (WSG: a FileDataID on Forever, else the path)
    assert art == 131883 or str(art).endswith("LoadScreenWarsongGulch"), art
    # the recruit milestones name Forever's levels
    assert c.eval("return ns.Recruit.MILESTONE_LEVEL[70]") == 60
    # the planner's default size is a Forever raid size (not 25)
    assert c.eval("return ns.RaidPlan:GetDefaultSize()") in (10, 20, 40)
    no_errors(w)


@case
def test_pvp_sheet_opens_on_battlegrounds_on_forever():
    w, c = solo(level=60, forever=True)
    c.eval("ns.MainFrame:Open('dungeons')")
    w.tick(1)
    c.eval("ns.DungeonsUI:SetTab('pvp')")
    c.eval("ns.DungeonsUI:OpenSheet()")
    w.tick(0.5)
    s = c.eval_py("local s = ns.DungeonsUI:GetSheetState(); return { s.kind, s.pm, s.pa }")
    assert s == ["pvp", "bg", "wsg"], s
    # one mode tile (no Arena, no World PvP)
    shown = c.eval("local n = 0 for _, t in ipairs(ns.DungeonsUI:GetPanel().sheet.pvpTiles) do"
                   " if t:IsShown() then n = n + 1 end end return n")
    assert shown == 1, shown
    no_errors(w)


@case
def test_dungeon_sheet_tiles_fit_on_forever():
    """Forever's bands hold six dungeons: the tiles share the row (they ran off the sheet at 4 x 130 px), the labels fit
    their tile (short names; the tooltip has the full one), and a band opening on a new dungeon still has a picture."""
    w, c = solo(level=60, forever=True)
    c.eval("ns.MainFrame:Open('dungeons')")
    w.tick(1)
    c.eval("ns.DungeonsUI:OpenSheet()")
    w.tick(0.5)
    rows = c.eval_py("""local sh = ns.DungeonsUI:GetPanel().sheet; local out = {}
      for _, r in ipairs(sh.rows) do if r:IsShown() then
        local tiles = {}
        for _, t in ipairs(r.tiles) do if t:IsShown() then
          tiles[#tiles + 1] = { t.name:GetText(), t:GetWidth(), t.name:GetStringWidth() } end end
        out[#out + 1] = { r:GetWidth(), r.art.tex:GetTexture() ~= nil, tiles } end end
      return out""")
    assert len(rows) == 6, rows
    for row_w, has_art, tiles in rows:
        assert has_art, (row_w, tiles)
        assert len(tiles) >= 5, tiles
        tile_w = tiles[0][1]
        assert 180 + len(tiles) * tile_w + (len(tiles) - 1) * 5 <= row_w - 8, (row_w, tile_w, len(tiles))
        for name, tw, sw in tiles:
            assert sw <= tw - 18, (name, tw, sw)
    names = [t[0] for r in rows for t in r[2]]
    assert "LBRS" in names and "Strat: UD" in names, names
    tip = c.eval_py("return ns.DungeonRuns:GetDungeon('UBRS').name")
    assert tip == "Upper Blackrock Spire", tip
    no_errors(w)


@case
def test_forever_new_items_above_200000_are_valid():
    """Forever's new items have ids 280000+ (Blackmaw Hold's Cloak of the Fleshborer: 280062). The TBC cap of 200000
    refused them: /dz roll printed its usage line for their link and My BiS would not take them (live test
    2026-11-10)."""
    w, c = solo(level=60, forever=True)
    c.eval("__MOCK.ITEMS[280062] = { name = 'Cloak of the Fleshborer', quality = 3, loc = 'INVTYPE_CLOAK', cls = 4,"
           " sub = 1, icon = 133762, ilvl = 60, minlvl = 55, bind = 1, stack = 1 }")
    got = c.eval_py("""local sid
      for i, s in ipairs(ns.SLOTS) do if s.invTypes and s.invTypes.INVTYPE_CLOAK then sid = i end end
      local ok = ns.BiS:SetSlot(0, sid, 'main', 280062)
      return { ok, ns.BiS:GetData() ~= nil }""")
    assert got[0] is True, got
    n = len(c.chat_frame)
    c.slash("/dz roll |cff0070dd|Hitem:280062::::::::60:::::|h[Cloak of the Fleshborer]|h|r")
    said = c.chat_frame[n:]
    assert said and "Usage" not in said[0] and "master looter" in said[0], said
    no_errors(w)


@case
def test_a_list_this_client_cannot_read_is_said_once():
    """0.2.2: a 0.2.0 council refused a 0.2.1 member's whole BiS list (an item id above its cap) with only a debug
    line, and the owner saw "people on 0.2.0 don't sync". Store:Put now prints why, once per player per session."""
    w, c = solo("Cou", guild_rank=1, tick=3, council=["Cou"], phase=3, members=[("Bob", "MAGE", 3)], forever=True)
    n = len(c.chat_frame)
    put = """local d = { v = 1, cl = 'MAGE', sp = '', ph = { [1] = { [1] = { 5000000, 0 } } }, ob = {}, eq = {} }
      return ns.Store:Put('Bob-Thunderstrike', { r = %d, ts = GetServerTime(), h = ns.Util.Hash(d), d = d }, 'direct')"""
    assert c.eval(put % 1) is False
    assert c.eval(put % 2) is False
    said = [l for l in c.chat_frame[n:] if "Couldn't take" in l]
    assert len(said) == 1 and "Bob" in said[0] and "/dz version" in said[0], c.chat_frame[n:]
    no_errors(w)


if __name__ == "__main__":
    run_all(globals())
