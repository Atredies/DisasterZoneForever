"""WoW Forever: TBC text players still saw (final scan 2026-11-09, branch fix/forever-tbc-text).

Covers: the Groups board's quest / other art is an old-world loading screen (not Outland's); the raid leaders' recruit
notice says the level cap (60); the lineup name hint names a Forever raid size; Interface > Looks has no Boss mods or
Meters page and /dz threat, /dz meter and /dz mylog are not registered (no combat log); the Reserves and Bingo demos
name Forever's raids; My BiS says Enchants (Forever has no gems) and its Badge of Justice / Sunmote / Heroic source
words are TBC-only; TBC's Hyjal Summit entrance (534, Caverns of Time) is not pinned on the Forever guild map. The TBC
client keeps its words (checked here once).

Run: luaenv/bin/python tests/forever/test_forever_text.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors, printed_since, install_helpers  # noqa: E402


def as_list(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v)]
    return list(v or [])


def help_text(w, c):
    n0 = len(c.chat_frame)
    c.slash("/dz help")
    w.tick(0.2)
    return "\n".join(printed_since(c, n0))


def part_tiles(w, c):
    install_helpers(c)
    c.slash("/dz settings")
    w.tick(0.5)
    c.eval("ns.SettingsUI:SelectSection('looks')")
    w.tick(0.3)
    return as_list(c.eval_py("local o = {} for _, t in ipairs(ns.SettingsUI.looksSec.partTiles) do"
                             " o[#o + 1] = t.part end return o"))


@case
def test_groups_art_is_old_world_on_forever():
    w, c = solo(level=60, forever=True)
    art = c.eval_py("local a = ns.Data.GroupKinds.art return { a.quest.screen, a.other.screen }")
    assert art == [131848, 131839], art          # (Kalimdor, Eastern Kingdoms; not Outland 131860)
    no_errors(w)


@case
def test_recruit_team_notice_says_level_60_on_forever():
    w, c = solo(level=60, forever=True)
    desc = c.eval("return ns.Notify:GetKind('recruitTeam').desc")
    assert "hit 60" in desc and "70" not in desc, desc
    no_errors(w)


@case
def test_lineup_hint_names_a_forever_size():
    w, c = solo(level=60, forever=True)
    c.eval("ns.MainFrame:Open('raids')")
    w.tick(0.5)
    text = c.eval("local d = ns.Popup.dialogs['DISASTERZONE_LINEUP_NAME'] return d and d.text")
    assert text is not None
    assert "25-man" not in text and "40-man" in text, text
    no_errors(w)


@case
def test_no_combat_log_parts_or_commands_on_forever():
    w, c = solo(level=60, forever=True)
    tiles = part_tiles(w, c)
    assert "bossmods" not in tiles and "meters" not in tiles, tiles
    assert "plates" in tiles and "timers" in tiles, tiles
    text = help_text(w, c)
    for gone in ("/dz threat", "/dz meter", "/dz mylog"):
        assert gone not in text, (gone, text)
    assert "/dz settings" in text, text
    no_errors(w)


@case
def test_no_boss_mod_or_meter_preview_is_reachable_on_forever():
    """The Looks previews of boss mods and meters (a made-up Gruul pull, the meter panels) have no way in on Forever:
    no Looks page, no Combat card, no search result, no demo part; a link to their card (the meter window's and the
    boss pages' "settings" buttons, which Forever never shows) lands on General instead of an empty page."""
    w, c = solo(level=60, forever=True)
    tiles = part_tiles(w, c)
    assert "bossmods" not in tiles and "meters" not in tiles, tiles
    c.eval("T_TRIED = 0 if ns.BossModUI then local real = ns.BossModUI.TryIt "
           "ns.BossModUI.TryIt = function(...) T_TRIED = T_TRIED + 1 return real(...) end end")
    for key in ("meters", "bossmods", "look:bossmods", "look:meters", "mylog", "strategy"):
        c.eval("ns.SettingsUI:SelectSection(...)", key)
        w.tick(0.2)
        got = c.eval_py("local s = ns.SettingsUI return { section = s.section, part = s.part }")
        assert got.get("section") not in ("meters", "bossmods", "mylog", "strategy"), (key, got)
        assert got.get("part") not in ("meters", "bossmods"), (key, got)
    for q in ("boss mod", "meter", "gruul"):
        c.eval("ns.SettingsUI:Search(...)", q)
        w.tick(0.2)
        hits = c.eval_py("local o = {} for k, card in pairs(ns.SettingsUI.cards) do o[#o + 1] = k end return o")
        assert "meters" not in hits and "bossmods" not in hits, (q, hits)
    c.eval("ns.SettingsUI:Search('')")
    keys = as_list(c.eval_py("local o = {} for _, d in ipairs(ns.Demo:Parts('screen')) do o[#o + 1] = d.key end "
                             "return o"))
    assert "bossmods" not in keys and "meters" not in keys, keys
    assert c.eval("return T_TRIED") == 0
    no_errors(w)


@case
def test_demos_name_forever_raids():
    w, c = solo(level=60, forever=True)
    # (Core/Reserves.lua's demo list is for Hyjal Summit: the demo's boss is one of its bosses)
    assert c.eval("for _, b in ipairs(ns.Reserves:Bosses('HyjalForever')) do"
                  " if b.key == 'NythusTheDreambound' then return true end end return false") is True
    src = os.path.join(os.environ.get("DISASTERZONE_ADDON_DIR", os.path.join(TESTS, "..", "..", "addon",
                                                                             "DisasterZone")))
    with open(os.path.join(src, "..", "DisasterZone_Bingo", "Bingo.lua"), encoding="utf-8") as f:
        bingo = f.read()
    assert 'forever and "hyjal" or "ssc"' in bingo and 'forever and "Onyxia" or "Lady Vashj"' in bingo
    no_errors(w)


@case
def test_item_source_words_on_forever():
    w, c = solo(level=60, forever=True)
    assert c.eval("return ns.Data.GemGuides and next(ns.Data.GemGuides) == nil") is True   # (no gem guides)
    # Hyjal Summit on Forever is on Mount Hyjal, not TBC's Caverns of Time entrance (534)
    assert c.eval("return ns.GuildMap:GetEntrance(534)") is None
    assert c.eval("return ns.GuildMap:GetEntrance(249)") is not None      # (Onyxia's Lair stays)
    # the dormant TBC source words are gated (no such items in Forever's data yet: checked in the files)
    src = os.path.join(os.environ.get("DISASTERZONE_ADDON_DIR", os.path.join(TESTS, "..", "..", "addon",
                                                                             "DisasterZone")))
    for rel, needle in (("Core/ItemDB.lua", 'FOREVER and name or (name .. " (Badge of Justice)")'),
                        ("Core/ItemDB.lua", "if FOREVER then heroic = nil end"),
                        ("UI/Tooltip.lua", 'upgrade = "via upgrade"'),
                        ("UI/MyBiS.lua", '"vendors", "Token vendors"')):
        with open(os.path.join(src, rel), encoding="utf-8", newline="") as f:
            assert needle in f.read(), (rel, needle)
    no_errors(w)


@case
def test_tbc_hyjal_entrance_kept():
    w, c = solo(level=70)
    assert c.eval("return ns.GuildMap:GetEntrance(534)") is not None
    no_errors(w)


@case
def test_forever_shamans_do_not_dual_wield():
    w, c = solo("Arakis", class_file="SHAMAN", level=60, forever=True)
    assert c.eval("return ns.DUAL_WIELD.SHAMAN") is None
    assert c.eval("return ns.DUAL_WIELD.WARRIOR") is True
    no_errors(w)


@case
def test_tbc_keeps_its_words():
    w, c = solo(level=70)
    assert c.eval("return ns.DUAL_WIELD.SHAMAN") is True
    assert c.eval("return ns.Data.GroupKinds.art.other.screen") == 131860
    assert "hit 70" in c.eval("return ns.Notify:GetKind('recruitTeam').desc")
    tiles = part_tiles(w, c)
    assert "bossmods" in tiles and "meters" in tiles, tiles
    text = help_text(w, c)
    assert "/dz threat" in text and "/dz meter" in text, text
    no_errors(w)


if __name__ == "__main__":
    run_all(globals())
