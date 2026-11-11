"""Recipes on WoW Forever: the profession window is the retail one (C_TradeSkillUI). GetTradeSkillLine and the craft
window are gone, so DisasterZone read no recipes at all ("Open your Blacksmithing window once" stayed up after
opening it, seen in game 2026-11-08). C_TradeSkillUI.GetAllRecipeIDs lists every recipe of the profession, learned
or not (507 for Blacksmithing, measured): only the learned ones are the character's.

Run: luaenv/bin/python tests/forever/test_forever_professions.py [-k name]
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
BLACKSMITHING = 164
# (name, spell, item, learned): what Arakis War's window lists (he knows the first three)
RECIPES = [("Rough Sharpening Stone", 2660, 2862, True), ("Copper Chain Pants", 2662, 2852, True),
           ("Runed Copper Belt", 2666, 2857, True), ("Golden Rod", 14379, 11128, False),
           ("Heavy Copper Maul", 7408, 6214, False)]
SKILLS = [("Blacksmithing", 74, 150), ("Mining", 91, 150), ("Cooking", 61, 150), ("First Aid", 79, 150)]


def key(name):
    return "%s-%s" % (name, REALM_KEY)


def setup(cl):
    for name, spell, _, _ in RECIPES:
        cl.eval("__MOCK.SPELL_NAMES[...] = select(2, ...)", spell, name)
    cl.eval("""
      local list = ...
      local out = { { name = "Professions", header = true } }
      for _, s in ipairs(list) do out[#out + 1] = { name = s[1], rank = s[2], max = s[3] } end
      out[#out + 1] = { name = "Weapon Skills", header = true }
      out[#out + 1] = { name = "Swords", rank = 90, max = 90 }
      __MOCK.skills = out""", [list(s) for s in SKILLS])
    cl.fire("SKILL_LINES_CHANGED")


def open_window(cl, linked=None):
    rows = [{"name": "Recipes", "header": True}]
    for name, spell, item, learned in RECIPES:
        rows.append({"name": name, "spell": spell, "item": item, "learned": learned})
    cl.eval("local rows, linked = ...; __MOCK.tradeskill = { name = 'Blacksmithing', rank = 74, max = 150, rows = rows,"
            " linked = linked }", rows, linked)
    cl.fire("TRADE_SKILL_SHOW")
    cl.fire("TRADE_SKILL_LIST_UPDATE")


def guild():
    w = World(realm=REALM)
    gm = Client(w, "Arakis War", class_file="WARRIOR", guild_rank=0, level=18, forever=True)
    missy = Client(w, "Missy Badshot", class_file="HUNTER", guild_rank=3, level=24, forever=True)
    for c in (gm, missy):
        c.load_addon()
        setup(c)
    w.tick(5)
    return w, gm, missy


def recipes(cl, who):
    rows = cl.eval_py("local o = {} for _, r in ipairs(ns.Professions:GetMemberRecipes(...)) do o[#o + 1] = r.spell or"
                      " r.id end return o", key(who), BLACKSMITHING) or {}
    rows = [rows[k] for k in sorted(rows)] if isinstance(rows, dict) else list(rows)
    return sorted(int(x) for x in rows)


@case
def test_skills_are_read_on_forever():
    w, gm, missy = guild()
    rows = gm.eval_py("local o = {} for _, r in ipairs(ns.Professions:GetMember(...) or {}) do o[r.id] = r.rank end"
                      " return o", key("Arakis War")) or {}
    assert rows.get(BLACKSMITHING) == 74, rows
    no_errors(w)


@case
def test_opening_the_window_reads_the_learned_recipes():
    w, gm, missy = guild()
    assert recipes(gm, "Arakis War") == []
    open_window(gm)
    w.tick(2)
    assert recipes(gm, "Arakis War") == [2660, 2662, 2666], recipes(gm, "Arakis War")
    no_errors(w)


@case
def test_the_guild_sees_them():
    w, gm, missy = guild()
    open_window(gm)
    w.tick(240)
    assert recipes(missy, "Arakis War") == [2660, 2662, 2666], recipes(missy, "Arakis War")
    no_errors(w)


@case
def test_someone_elses_linked_profession_is_not_mine():
    w, gm, missy = guild()
    open_window(gm, linked="Missy Badshot")
    w.tick(2)
    assert recipes(gm, "Arakis War") == []
    no_errors(w)


if __name__ == "__main__":
    run_all()
