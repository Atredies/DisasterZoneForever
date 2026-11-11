#!/usr/bin/env python3
"""
Writes addon/DisasterZone/Data/Atlas.lua for WoW Forever: the craft, recipe and name tables the Atlas tab, the
shopping list and the materials breakdown read (Core/Atlas.lua, Core/Materials.lua, Core/ShoppingList.lua). The
browse tree itself is empty on Forever: Forever's raids and dungeons come from Data/Items.lua / Data/Dungeons.lua and
its other pages from Data/AtlasClassic.lua (gen_atlas_classic.py with DZ_FOREVER=1).

Same table shapes as gen_atlas.py (its header documents them), built from AtlasLoot Classic Forever's CLASSIC tables
only (what a Forever client has; GPL v2):
  * AtlasLootClassic/Data/Profession.lua  PROFESSION_DATA.CLASSIC: spell -> created item, skill, reagents, number made
  * AtlasLootClassic/Data/Recipe.lua      RECIPE_DATA.CLASSIC: recipe item -> craft spell
A craft is kept when Forever's item database (forever_names.py, Wowhead's Forever tooltip API, cached) has its
created item (if any) and every reagent; a recipe when it has the recipe item and its craft is kept.
AtlasCosts is empty: AtlasLoot has no Forever prices (its vanilla table is empty, the TBC one's marks are TBC's), so
the addon uses the prices its players' vendors show (Core/Currency.lua).
AtlasNames: every item id the Atlas can list or a craft uses (Data/Items.lua, Dungeons.lua, Sources.lua,
AtlasClassic.lua, the crafts' items and reagents, the recipes), and the names of crafts that create no item.

Usage (from dev/):  DZ_ADDONS=<unpacked AtlasLoot Classic Forever> luaenv/bin/python generators/gen_forever_atlas.py
"""
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_atlas as A  # noqa: E402
from gen_atlas import S  # noqa: E402
import forever_names as FN  # noqa: E402

DEV = os.path.dirname(HERE)
DATA = os.path.normpath(os.path.join(DEV, "..", "addon", "DisasterZone", "Data"))
OUT = os.path.join(DATA, "Atlas.lua")


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def shipped_ids():
    """Every positive item id the other Forever data files list (their `[id]`/`id =`/bare list entries)."""
    ids = set()
    for f in ("Items.lua", "Dungeons.lua", "Sources.lua", "AtlasClassic.lua"):
        text = open(os.path.join(DATA, f), encoding="utf-8").read()
        text = re.sub(r"--[^\n]*", "", text)
        ids |= {int(x) for x in re.findall(r"(?<![\w.])(\d{2,6})(?![\w.])", text) if 10 <= int(x) < 400000}
    return ids


def main():
    al = os.environ.get("DZ_ADDONS")
    if not al:
        sys.exit("set DZ_ADDONS to the unpacked AtlasLoot Classic Forever folder")
    S.P_PROFESSION = os.path.join(al, "AtlasLootClassic", "Data", "Profession.lua")
    S.P_RECIPE = os.path.join(al, "AtlasLootClassic", "Data", "Recipe.lua")
    names = FN.Names(fetch=True, verify_all=True)
    names.add_comments(FN.comments_from(S.P_PROFESSION))
    _, comments = A.tokenize(A.read(S.P_PROFESSION))

    # crafts (CLASSIC only), kept when Forever has their items
    crafts, cmts, dropped = OrderedDict(), {}, 0
    t = S.version_table(S.P_PROFESSION, "PROFESSION_DATA", "CLASSIC")
    raw = []
    for sp, v in t.hash.items():
        a = v.array
        if len(a) < 7 or not isinstance(a[5], A.LuaTable) or not isinstance(a[6], A.LuaTable):
            continue
        ids = [A.int_val(x) for x in a[5].array]
        cnt = [A.int_val(x) for x in a[6].array]
        if len(ids) != len(cnt) or not ids or any(not i or i <= 0 for i in ids) or any(not n or n <= 0 for n in cnt):
            continue
        made = A.int_val(a[7]) if len(a) > 7 else None
        raw.append((sp, A.int_val(a[0]) or 0, made if made and made > 0 else 1, list(zip(ids, cnt)),
                    A.int_val(a[2]) or 0, A.int_val(a[1]) or 0))
        c = (comments.get(v.line_start) or "").strip()
        if c:
            cmts[sp] = re.sub(r"\s*/\s*\d+\s*$", "", c).strip()
    every = {r[1] for r in raw if r[1]} | {i for r in raw for i, _ in r[3]}
    names.prefetch(every)
    for sp, item, made, reagents, skill, prof in sorted(raw):
        if (item and not names.get(item)) or any(not names.get(i) for i, _ in reagents):
            dropped += 1
            continue
        crafts[sp] = (item, made, reagents, skill, "CLASSIC", prof)
    conv = A.conversions(crafts)
    craft_for = A.craft_for_items(crafts, conv)

    # recipes (CLASSIC), kept when Forever has the recipe item and its craft is kept
    rt = S.version_table(S.P_RECIPE, "RECIPE_DATA", "CLASSIC")
    rec_raw = {it: v.array[2] for it, v in rt.hash.items() if len(v.array) >= 3 and isinstance(v.array[2], int)}
    names.prefetch(rec_raw.keys())
    recipes = OrderedDict()
    for it, sp in sorted(rec_raw.items()):
        if sp in crafts and names.get(it):
            item = crafts[sp][0]
            recipes[it] = item if item else -sp

    # names
    want = shipped_ids() | {c[0] for c in crafts.values() if c[0]} | {i for c in crafts.values() for i, _ in c[2]} \
        | set(recipes)
    names.prefetch(want)
    out_names = OrderedDict()
    for i in sorted(want):
        nm = names.get(i)
        if nm:
            out_names[i] = nm
    for sp, c in crafts.items():
        if not c[0] and cmts.get(sp):
            out_names[-sp] = cmts[sp]
    names.save()

    L = ['if DisasterZoneBoot and DisasterZoneBoot.Run("Data/Atlas.lua", ...) then return end '
         '-- DisasterZone Atlas browser data (WoW Forever, Interface 16001)',
         "-- AUTO-GENERATED by gen_forever_atlas.py - do not edit by hand; re-run the generator instead.",
         "-- WoW Forever. AtlasLoot Classic Forever's CLASSIC Profession.lua / Recipe.lua (GPL v2); items checked against",
         "-- Wowhead's Forever item database. Shapes as the TBC file documented (dev/fixtures/tbc/Data/Atlas.lua):",
         "-- ns.Data.Atlas: no categories here on Forever (Data/AtlasClassic.lua has the pages).",
         "-- ns.Data.AtlasCosts: empty (no Forever prices in AtlasLoot: vendors teach them, Core/Currency.lua).",
         "-- ns.Data.AtlasNames = { [id] = name } (negative = a craft spell that makes no item);",
         "-- ns.Data.AtlasRecipes = { [recipe item] = created item or -spell };",
         "-- ns.Data.AtlasCrafts = { [spell] = \"created,made,reagent,count,...\" };",
         "-- ns.Data.AtlasCraftFor = { [created item] = spell } (items several crafts make);",
         "-- ns.Data.AtlasConversions = { [spell] = true } (loops a materials breakdown never goes through).",
         "local _, ns = ...", "ns.Data = ns.Data or {}", "", "ns.Data.Atlas = {}", "", "ns.Data.AtlasRecipes = {"]
    for it, v in recipes.items():
        L.append("  [%d] = %d, -- %s -> %s" % (it, v, names.get(it) or "?", out_names.get(v) or "?"))
    L += ["}", "", "ns.Data.AtlasCrafts = {"]
    for sp, (item, made, reagents, _, _, _) in crafts.items():
        L.append('  [%d] = "%s",' % (sp, ",".join(str(x) for x in [item, made] + [y for r in reagents for y in r])))
    L += ["}", "", "ns.Data.AtlasCraftFor = {"]
    for item, sp in craft_for.items():
        L.append("  [%d] = %d, -- %s" % (item, sp, out_names.get(item) or "?"))
    L += ["}", "", "ns.Data.AtlasConversions = {"]
    for sp in sorted(conv):
        L.append("  [%d] = true, -- %s" % (sp, out_names.get(crafts[sp][0]) or "?"))
    L += ["}", "", "ns.Data.AtlasCosts = {}", "", "ns.Data.AtlasNames = {"]
    for i, nm in out_names.items():
        L.append("  [%d] = %s," % (i, lua_str(nm)))
    L += ["}", ""]
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("crafts %d (dropped %d: not in Forever), recipes %d, craft-for %d, conversions %d, names %d" % (
        len(crafts), dropped, len(recipes), len(craft_for), len(conv), len(out_names)))


if __name__ == "__main__":
    main()
