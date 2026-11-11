#!/usr/bin/env python3
"""
Generator for DisasterZone's WoW Forever loot data (client 1.60.1, Interface 16001):

  addon/DisasterZone/Data/Items.lua     ns.Data.Raids: Onyxia's Lair, Barrow Deeps, Hyjal Summit (bosses; loot as known)
                                        + the empty TBC-only tables (Tokens, Upgrades, arena exchanges, tier classes)
  addon/DisasterZone/Data/Dungeons.lua  ns.Data.Dungeons: the 35 Forever dungeons, bosses, npc ids and loot

Inputs:
  * AtlasLoot Classic Forever (GPLv2, CurseForge 1422985), unpacked; DZ_ADDONS or --atlasloot points at the folder
    holding AtlasLootClassic_DungeonsAndRaids. Its data.lua is RUN (lupa, a stub of the AtlasLoot API), so the tables
    are exactly what AtlasLoot builds in game.
  * dev/generators/data/forever_dungeon_loot_extra.json: boss loot AtlasLoot does not have yet, gathered by hand
    from public Forever databases (each dungeon lists its sources); merged after AtlasLoot's rows.
  * Item names + "is it in Forever": forever_names.py (cache, then Wowhead's Forever tooltip API with --fetch). An
    item Forever does not know is left out (AtlasLoot's Classic tables still carry Season of Discovery and later
    raid ids).

Raids: AtlasLoot has their boss lists but no loot yet ("Loot will be updated asap"); the bosses ship without items
until the loot is known (re-run after AtlasLoot updates). Raid keys: Onyxia, BarrowDeeps, HyjalForever (not TBC's
HyjalSummit: a different raid; saved data and the wire know the TBC key).

Usage (from dev/):  DZ_ADDONS=<unpacked AtlasLoot> luaenv/bin/python generators/gen_forever_data.py [--fetch]
"""
import argparse
import json
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import forever_names as FN  # noqa: E402
from lupa import lua51  # noqa: E402

DEV = os.path.dirname(HERE)
ADDON = os.path.normpath(os.path.join(DEV, "..", "addon", "DisasterZone"))
EXTRA = os.path.join(HERE, "data", "forever_dungeon_loot_extra.json")
REPORT = os.path.join(HERE, "gen_forever_data_report.json")

# AtlasLoot key -> (DisasterZone key, name, instance id or None). Keys match Core/DungeonRuns.lua's Forever list.
DUNGEONS = OrderedDict([
    ("Ragefire", ("Ragefire", "Ragefire Chasm", 389)),
    ("TheHallOfThanes", ("HallOfThanes", "Hall of Thanes", None)),
    ("WailingCaverns", ("WailingCaverns", "Wailing Caverns", 43)),
    ("TheRuinsOfLordaeron", ("RuinsOfLordaeron", "Ruins of Lordaeron", None)),
    ("TheDeadmines", ("Deadmines", "The Deadmines", 36)),
    ("ShadowfangKeep", ("ShadowfangKeep", "Shadowfang Keep", 33)),
    ("TheStockade", ("Stockade", "The Stockade", 34)),
    ("BlackfathomDeeps", ("BlackfathomDeeps", "Blackfathom Deeps", 48)),
    ("ExcavationSiteWetlands", ("ExcavationSite", "Excavation Site: Wetlands", None)),
    ("TheCityOfDalaran", ("CityOfDalaran", "City of Dalaran", None)),
    ("Gnomeregan", ("Gnomeregan", "Gnomeregan", 90)),
    ("RazorfenKraul", ("RazorfenKraul", "Razorfen Kraul", 47)),
    ("ScarletMonasteryGraveyard", ("SMGraveyard", "Scarlet Monastery: Graveyard", 189)),
    ("ScarletMonasteryLibrary", ("SMLibrary", "Scarlet Monastery: Library", 189)),
    ("ScarletMonasteryArmory", ("SMArmory", "Scarlet Monastery: Armory", 189)),
    ("ScarletMonasteryCathedral", ("SMCathedral", "Scarlet Monastery: Cathedral", 189)),
    ("TheDrownedCity", ("DrownedCity", "The Drowned City", None)),
    ("RazorfenDowns", ("RazorfenDowns", "Razorfen Downs", 129)),
    ("Uldaman", ("Uldaman", "Uldaman", 70)),
    ("KroldokStronghold", ("KroldokStronghold", "Krol'dok Stronghold", None)),
    ("Zul'Farrak", ("ZulFarrak", "Zul'Farrak", 209)),
    ("Maraudon", ("Maraudon", "Maraudon", 349)),
    ("AlcazPrison", ("AlcazPrison", "Alcaz Prison", None)),
    ("TheTempleOfAtal'Hakkar", ("SunkenTemple", "Sunken Temple", 109)),
    ("BlackrockDepths", ("BlackrockDepths", "Blackrock Depths", 230)),
    ("LowerBlackrockSpire", ("LBRS", "Lower Blackrock Spire", 229)),
    ("UpperBlackrockSpire", ("UBRS", "Upper Blackrock Spire", 229)),
    ("DireMaulEast", ("DireMaulEast", "Dire Maul: East", 429)),
    ("DireMaulWest", ("DireMaulWest", "Dire Maul: West", 429)),
    ("DireMaulNorth", ("DireMaulNorth", "Dire Maul: North", 429)),
    ("BlackmawHold", ("BlackmawHold", "Blackmaw Hold", None)),
    ("Scholomance", ("Scholomance", "Scholomance", 289)),
    ("Stratholme", (None, None, 329)),                      # split below into Living / Undead
    ("ShapersTerrace", ("ShapersTerrace", "Shaper's Terrace", None)),
])
STRAT = {"Living": ("StratholmeLive", "Stratholme: Living"), "Undead": ("StratholmeUndead", "Stratholme: Undead")}
# The Undead side (Service Gate); every other Stratholme boss is the Living side (Main Gate).
STRAT_UNDEAD = {"Magistrate Barthilas", "Stonespine", "Baroness Anastari", "Nerub'enkan", "Maleki the Pallid",
                "Ramstein the Gorger", "Baron Rivendare", "Black Guard Swordsmith", "Postmaster Malown"}

# Sources.lua (the item picker's crafted / reputation / PvP sources). Crafted: the gear professions' tables, crafts at
# skill >= CRAFT_MIN_SKILL whose result Forever has; sub-tables that are not gear are left out by name.
CRAFT_PROFS = OrderedDict([("Blacksmithing", 2), ("Leatherworking", 3), ("Tailoring", 8), ("Engineering", 9)])
CRAFT_MIN_SKILL = 225
NOT_GEAR = ("misc", "bag", "enhancement", "reagent", "consum", "explosive", "material", "parts", "firework",
            "item enhancement", "ammo", "pet", "toy", "smelt")
RECIPE_PREFIX = ("Pattern:", "Plans:", "Formula:", "Recipe:", "Schematic:", "Manual:", "Design:", "Book:")
FACTIONS = OrderedDict([
    ("ArgentDawn", "Argent Dawn"), ("Timbermaw", "Timbermaw Hold"), ("ThoriumBrotherhood", "Thorium Brotherhood"),
    ("CenarionCircle", "Cenarion Circle"), ("ZandalarTribe", "Zandalar Tribe"), ("BroodOfNozdormu", "Brood of Nozdormu"),
    ("HydraxianWaterlords", "Hydraxian Waterlords"), ("BloodsailBuccaneers", "Bloodsail Buccaneers"),
    ("WintersaberTrainers", "Wintersaber Trainers"),
])
STANDINGS = ("Exalted", "Revered", "Honored", "Friendly", "Neutral")
PVP = OrderedDict([
    ("AlteracValley", ("AlteracValley", "Alterac Valley")), ("WarsongGulch", ("WarsongGulch", "Warsong Gulch")),
    ("ArathiBasin", ("ArathiBasin", "Arathi Basin")), ("Armor", ("Armor", "Rank armor")),
    ("Weapons", ("Weapons", "Rank weapons")), ("Insignia", ("Insignia", "Insignia")),
])

RAIDS = OrderedDict([
    ("OnyxiasLairNew", ("Onyxia", "Onyxia's Lair", 40, 249)),
    ("BarrowDeepsRaid", ("BarrowDeeps", "Barrow Deeps", 10, None)),
    ("MountHyjal", ("HyjalForever", "Hyjal Summit", 20, None)),
])

STUB = r"""
local function new_data()
  local d, n = {}, 0
  local mt = { __index = {} }
  local function id(kind) n = n + 1; return kind .. n end
  function mt.__index:AddDifficulty(name) return "D:" .. tostring(name) end
  function mt.__index:AddContentType(name) return "C:" .. tostring(name) end
  function mt.__index:AddItemTableType() return id("T") end
  function mt.__index:AddExtraItemTableType() return id("X") end
  return setmetatable(d, mt)
end
DATA = nil
AtlasLoot = {
  CLASSIC_VERSION_NUM = 1, BC_VERSION_NUM = 2, WRATH_VERSION_NUM = 3,
  ItemDB = { Add = function() DATA = new_data(); return DATA end },
  Locales = setmetatable({}, { __index = function(_, k) return k end }),
  IngameLocales = setmetatable({}, { __index = function(_, k) return k end }),
  ReturnForGameVersion = function(classic) return classic end,
  GameVersion_GE = function() return false end, GameVersion_LT = function() return true end,
  GameVersion_EQ = function() return false end,
  -- (any other AtlasLoot module a data file asks for: methods that return nothing)
  Data = setmetatable({ ContentPhase = { GetActivePhase = function() return 1 end },
           Profession = { GetColorSkillRankNoSpell = function() return "" end } },
           { __index = function() return setmetatable({}, { __index = function() return function() end end }) end }),
  GUI = { frame = {} },
}
C_Map = { GetAreaInfo = function(id) return "Area " .. id end }
C_Seasons = nil
UnitFactionGroup = function() return "Alliance" end
FACTION_HORDE, FACTION_ALLIANCE = "Horde", "Alliance"
RAID_CLASS_COLORS = setmetatable({}, { __index = function() return { colorStr = "ffffffff" } end })
ATLASLOOT_IT_HORDE, ATLASLOOT_IT_ALLIANCE = "IT_HORDE", "IT_ALLIANCE"
setmetatable(_G, { __index = function(_, k) if type(k) == "string" and k:match("^ATLASLOOT_") then return k end end })
CreateFrame = function() return setmetatable({}, { __index = function() return function() end end }) end
hooksecurefunc = function() end
"""


def load_atlasloot(path, module="AtlasLootClassic_DungeonsAndRaids"):
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUB)
    src = open(path, encoding="utf-8", errors="replace").read()
    fn = lua.eval("function(s, name) local f, e = loadstring(s, name); if not f then error(e) end; return f end")(
        src, "=" + os.path.basename(path))
    fn(module, lua.table())
    return lua, lua.globals().DATA


def lua_items(rows, report, where):
    """Item ids of one difficulty's rows: numbers, and both sides of a faction row; headers / hidden rows out."""
    out = []
    if rows is None:
        return out
    for _, row in sorted(rows.items(), key=lambda kv: kv[0]):
        if lua51.lua_type(row) != "table":
            continue
        pos = row[1]
        if pos == 0:
            report["hidden rows"] = report.get("hidden rows", 0) + 1
            continue
        ids = []
        v = row[2]
        if isinstance(v, (int, float)) and v > 0:
            ids.append(int(v))
        for k in ("IT_ALLIANCE", "IT_HORDE"):
            if row[k] and isinstance(row[k], (int, float)):
                ids.append(int(row[k]))
        for i in ids:
            if i not in out:
                out.append(i)
    return out


def bosses_of(tbl, diffs, report, where):
    out = []
    items = tbl["items"]
    if lua51.lua_type(items) != "table":
        return out
    for _, b in sorted(items.items(), key=lambda kv: kv[0]):
        if lua51.lua_type(b) != "table" or b["ExtraList"] or b["IgnoreAsSource"]:
            continue
        name = b["name"]
        if not isinstance(name, str):
            continue
        rows = None
        for d in diffs:
            rows = b[d]
            if rows is not None:
                break
        npc = b["npcID"]
        npcs = []
        if isinstance(npc, (int, float)):
            npcs = [int(npc)]
        elif lua51.lua_type(npc) == "table":
            npcs = [int(x) for x in npc.values() if isinstance(x, (int, float))]
        out.append({"name": name.split("|")[0].strip(), "npcIDs": npcs,
                    "items": lua_items(rows, report, where + "/" + name),
                    "trash": bool(b["specialType"] == "trash" or name.lower().startswith("trash"))})
    return out


def professions(path):
    """{craft spell: (created item, AtlasLoot profession, min skill)} from Profession.lua's CLASSIC table."""
    out = {}
    text = open(path, encoding="utf-8", errors="replace").read()
    i, j = text.find("PROFESSION_DATA.CLASSIC = {"), text.find("PROFESSION_DATA.BCC")
    for m in re.finditer(r"\[(\d+)\]\s*=\s*\{\s*(\d+|nil)\s*,\s*(\d+)\s*,\s*(\d+)", text[i:j]):
        if m.group(2) != "nil":
            out[int(m.group(1))] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return out


def side_rows(entry):
    """[(side or None, rows)] of a boss / page entry: the normal list, or the Alliance and Horde ones."""
    out = []
    for d, side in (("D:NORMAL", None), ("D:Normal", None), ("D:Alliance", "Alliance"), ("D:Horde", "Horde")):
        if entry[d] is not None:
            out.append((side, entry[d]))
    return out


def build_sources(al, names, keep, report):
    """Forever's ns.Data.Crafted / Reputation / PvP from AtlasLoot's crafting, faction and PvP tables."""
    prof = professions(os.path.join(al, "AtlasLootClassic", "Data", "Profession.lua"))
    _, craft = load_atlasloot(os.path.join(al, "AtlasLootClassic_Crafting", "data.lua"), "AtlasLootClassic_Crafting")
    crafted = []
    for key, pid in CRAFT_PROFS.items():
        tbl, items, seen = craft[key], [], set()
        for _, sub in sorted(tbl["items"].items(), key=lambda kv: kv[0]):
            if lua51.lua_type(sub) != "table" or not isinstance(sub["name"], str):
                continue
            if any(w in sub["name"].lower() for w in NOT_GEAR):
                continue
            for _, rows in side_rows(sub):
                for spell in lua_items(rows, report, key):
                    p = prof.get(spell)
                    if not p or p[2] < CRAFT_MIN_SKILL or p[0] in seen:
                        continue
                    seen.add(p[0])
                    if keep([p[0]], "crafted/" + key):
                        items.append({"id": p[0], "skill": p[2], "spell": spell})
        crafted.append({"key": key, "name": key, "pid": pid, "items": items})
    _, fac = load_atlasloot(os.path.join(al, "AtlasLootClassic_Factions", "data.lua"), "AtlasLootClassic_Factions")
    reputation = []
    for key, name in FACTIONS.items():
        tbl = fac[key]
        if tbl is None:
            continue
        items, seen = [], set()
        for _, sub in sorted(tbl["items"].items(), key=lambda kv: kv[0]):
            if lua51.lua_type(sub) != "table" or sub["name"] not in STANDINGS:
                continue
            for side, rows in side_rows(sub):
                for i in keep(lua_items(rows, report, key), "rep/" + key):
                    nm = names.get(i) or ""
                    if i in seen or nm.startswith(RECIPE_PREFIX):
                        continue
                    seen.add(i)
                    items.append({"id": i, "standing": sub["name"]})
        reputation.append({"key": key, "name": name, "fid": int(tbl["FactionID"] or 0), "items": items})
    _, pvp = load_atlasloot(os.path.join(al, "AtlasLootClassic_PvP", "data.lua"), "AtlasLootClassic_PvP")
    pvp_out = []
    for al_key, (key, name) in PVP.items():
        tbl = pvp[al_key]
        if tbl is None:
            continue
        items, seen = [], {}
        for _, sub in sorted(tbl["items"].items(), key=lambda kv: kv[0]):
            if lua51.lua_type(sub) != "table":
                continue
            for side, rows in side_rows(sub):
                for i in keep(lua_items(rows, report, al_key), "pvp/" + al_key):
                    if i in seen:
                        if seen[i] != side:
                            seen[i] = None
                        continue
                    seen[i] = side
                    items.append(i)
        pvp_out.append({"key": key, "name": name, "items": [(i, seen[i]) for i in items]})
    return crafted, reputation, pvp_out


def write_sources(path, head, crafted, reputation, pvp, names):
    L = ['if DisasterZoneBoot and DisasterZoneBoot.Run("Data/Sources.lua", ...) then return end '
         '-- DisasterZone crafted / reputation / PvP item database (WoW Forever, Interface 16001)', head.rstrip("\n"),
         "-- ns.Data.Crafted    = { { key, name, professionID, items = { { id, skill, phase, spell } } } }: gear crafts",
         "--   at skill >= %d of Blacksmithing, Leatherworking, Tailoring, Engineering (AtlasLoot Profession.lua)." % CRAFT_MIN_SKILL,
         "-- ns.Data.Reputation = { { key, name, factionID, items = { { id, standing, phase } } } }: no recipes. Forever's",
         "--   new factions (Guardians of Hyjal, The Watchers, Darkspear Raiders, ...) are not in AtlasLoot yet.",
         "-- ns.Data.Badges     = {} (no Badge of Justice on Forever)",
         "-- ns.Data.PvP        = { { key, name, phase, items = { { id, faction?, phase } } } }: battlegrounds, rank gear.",
         "local _, ns = ...", "ns.Data = ns.Data or {}", "", "ns.Data.Crafted = {"]
    for c in crafted:
        L.append('  { key = %s, name = %s, professionID = %d, items = {' % (lua_str(c["key"]), lua_str(c["name"]), c["pid"]))
        for it in c["items"]:
            L.append('    { id = %d, skill = %d, phase = 1, spell = %d }, -- %s' % (it["id"], it["skill"], it["spell"],
                                                                                 names.get(it["id"]) or "?"))
        L.append("  } },")
    L += ["}", "", "ns.Data.Reputation = {"]
    for r in reputation:
        L.append('  { key = %s, name = %s, factionID = %d, items = {' % (lua_str(r["key"]), lua_str(r["name"]), r["fid"]))
        for it in r["items"]:
            L.append('    { id = %d, standing = %s, phase = 1 }, -- %s' % (it["id"], lua_str(it["standing"]),
                                                                          names.get(it["id"]) or "?"))
        L.append("  } },")
    L += ["}", "", "ns.Data.Badges = {}", "", "ns.Data.PvP = {"]
    for g in pvp:
        L.append('  { key = %s, name = %s, phase = 1, items = {' % (lua_str(g["key"]), lua_str(g["name"])))
        for i, side in g["items"]:
            L.append('    { id = %d%s, phase = 1 }, -- %s' % (i, ", faction = %s" % lua_str(side) if side else "",
                                                             names.get(i) or "?"))
        L.append("  } },")
    L += ["}", ""]
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(L))


def key_of(name, used):
    k = "".join(ch for ch in name.title() if ch.isalnum())[:24] or "Boss"
    base, n = k, 2
    while k in used:
        k = "%s%d" % (base, n)
        n += 1
    used.add(k)
    return k


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_boss(lines, b, names, indent="    "):
    head = '%s{ key = %s, name = %s' % (indent, lua_str(b["key"]), lua_str(b["name"]))
    if b["npcIDs"]:
        head += ", npcIDs = { %s }" % ", ".join(str(i) for i in b["npcIDs"])
    if b.get("trash"):
        head += ", isTrash = true"
    if not b["items"]:
        lines.append(head + ", items = {} },")
        return
    lines.append(head + ", items = {")
    for i in b["items"]:
        lines.append("%s    %d, -- %s" % (indent, i, names.get(i) or "?"))
    lines.append("%s}}," % indent)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlasloot", default=os.environ.get("DZ_ADDONS"))
    ap.add_argument("--fetch", action="store_true", help="ask Wowhead about ids the cache does not know")
    ap.add_argument("--out-dir", default=os.path.join(ADDON, "Data"))
    args = ap.parse_args()
    if not args.atlasloot:
        sys.exit("set DZ_ADDONS (or --atlasloot) to the unpacked AtlasLoot Classic Forever folder")
    p_data = os.path.join(args.atlasloot, "AtlasLootClassic_DungeonsAndRaids", "data.lua")
    lua, data = load_atlasloot(p_data)
    names = FN.Names(fetch=args.fetch, verify_all=True)
    names.add_comments(FN.comments_from(p_data))
    report = {"atlasloot": args.atlasloot, "dropped_not_in_forever": [], "dungeons": {}, "raids": {}}
    extra = json.load(open(EXTRA, encoding="utf-8")) if os.path.exists(EXTRA) else {}

    if args.fetch:                                        # (every id AtlasLoot lists, asked in parallel first)
        ids = set()
        for sub in ("AtlasLootClassic_DungeonsAndRaids", "AtlasLootClassic_Crafting", "AtlasLootClassic_Factions",
                    "AtlasLootClassic_PvP"):
            text = open(os.path.join(args.atlasloot, sub, "data.lua"), encoding="utf-8", errors="replace").read()
            ids.update(int(m) for m in re.findall(r"\{\s*\d+\s*,\s*(\d{2,6})\s*[,}]", text))
            ids.update(int(m) for m in re.findall(r"ATLASLOOT_IT_(?:HORDE|ALLIANCE)\]\s*=\s*(\d+)", text))
        prof = professions(os.path.join(args.atlasloot, "AtlasLootClassic", "Data", "Profession.lua"))
        ids.update(v[0] for v in prof.values())
        for d in extra.values():
            for b in (d.get("bosses", []) if isinstance(d, dict) else []):
                ids.update(b.get("items", []))
        names.prefetch(ids)

    def keep(ids, where):
        out = []
        for i in ids:
            if names.get(i):
                out.append(i)
            else:
                report["dropped_not_in_forever"].append({"id": i, "where": where})
        return out

    NORMAL = ["D:NORMAL", "D:Alliance", "D:Horde"]
    dungeons = []
    for al_key, (key, name, inst) in DUNGEONS.items():
        tbl = data[al_key]
        if tbl is None:
            report.setdefault("missing_tables", []).append(al_key)
            continue
        bosses = bosses_of(tbl, NORMAL, report, al_key)
        ex = extra.get(al_key) or {}
        if ex.get("replace"):                           # (AtlasLoot has only a placeholder boss)
            bosses = []
        for eb in ex.get("bosses", []):
            hit = next((b for b in bosses if b["name"].lower() == eb["name"].lower()), None)
            if not hit:
                hit = {"name": eb["name"], "npcIDs": [], "items": [], "trash": bool(eb.get("trash"))}
                bosses.append(hit)
            if eb.get("npcID") and eb["npcID"] not in hit["npcIDs"]:
                hit["npcIDs"].append(eb["npcID"])
            for i in eb.get("items", []):
                if i not in hit["items"]:
                    hit["items"].append(i)
        for b in bosses:
            b["items"] = keep(b["items"], al_key + "/" + b["name"])
        if al_key == "Stratholme":
            for side in ("Living", "Undead"):
                part = [b for b in bosses if (b["name"] in STRAT_UNDEAD) == (side == "Undead")]
                dungeons.append({"key": STRAT[side][0], "name": STRAT[side][1], "inst": inst, "bosses": part})
        else:
            dungeons.append({"key": key, "name": name, "inst": inst, "bosses": bosses})
    for d in dungeons:
        used = set()
        for b in d["bosses"]:
            b["key"] = key_of(b["name"], used)
        report["dungeons"][d["key"]] = {"bosses": len(d["bosses"]), "items": sum(len(b["items"]) for b in d["bosses"])}

    raids = []
    for al_key, (key, name, size, inst) in RAIDS.items():
        tbl = data[al_key]
        bosses = bosses_of(tbl, NORMAL + ["D:40RAID", "D:20RAID"], report, al_key)
        used = set()
        for b in bosses:
            b["items"] = keep(b["items"], al_key + "/" + b["name"])
            b["key"] = key_of(b["name"], used)
        raids.append({"key": key, "name": name, "size": size, "inst": inst, "bosses": bosses})
        report["raids"][key] = {"bosses": len(bosses), "items": sum(len(b["items"]) for b in bosses)}
    crafted, reputation, pvp = build_sources(args.atlasloot, names, keep, report)
    report["sources"] = {"crafted": {c["key"]: len(c["items"]) for c in crafted},
                         "reputation": {r["key"]: len(r["items"]) for r in reputation},
                         "pvp": {g["key"]: len(g["items"]) for g in pvp}}
    names.save()

    head = ("-- AUTO-GENERATED by gen_forever_data.py - do not edit by hand; re-run the generator instead.\n"
            "-- WoW Forever (client 1.60.1). Sources: AtlasLoot Classic Forever (GPLv2, its data.lua run as AtlasLoot\n"
            "-- runs it), dev/generators/data/forever_dungeon_loot_extra.json (public Forever databases, sources listed\n"
            "-- there); every item checked against Wowhead's Forever item database (forever_names.py).\n")
    L = ['if DisasterZoneBoot and DisasterZoneBoot.Run("Data/Items.lua", ...) then return end '
         '-- DisasterZone embedded raid-loot database (WoW Forever, Interface 16001)', head.rstrip("\n"),
         "-- Raids: their bosses; loot as it becomes known (none yet before the raids open on 2026-12-09).",
         "-- Boss fields: key, name, npcIDs, isTrash, items. No tier tokens, Sunmote upgrades or arena exchanges on Forever.",
         "local _, ns = ...", "ns.Data = ns.Data or {}", "", "ns.Data.Raids = {"]
    for r in raids:
        L.append('  { key = %s, name = %s, phase = 1, size = %d%s, bosses = {'
                 % (lua_str(r["key"]), lua_str(r["name"]), r["size"],
                    ", instanceID = %d" % r["inst"] if r["inst"] else ""))
        for b in r["bosses"]:
            write_boss(L, b, names)
        L.append("  }},")
    L += ["}", "", "ns.Data.Tokens = {}", "ns.Data.TokenClasses = {}", "ns.Data.Upgrades = {}",
          "ns.Data.TokenArenaExchanges = {}", "ns.Data.TierPieceClass = {}", ""]
    open(os.path.join(args.out_dir, "Items.lua"), "w", encoding="utf-8", newline="\n").write("\n".join(L))

    L = ['if DisasterZoneBoot and DisasterZoneBoot.Run("Data/Dungeons.lua", ...) then return end '
         '-- DisasterZone embedded 5-man dungeon loot database (WoW Forever, Interface 16001)', head.rstrip("\n"),
         "-- Dungeon fields: key (Core/DungeonRuns.lua's), name, phase, instanceID (nil: not known yet), bosses.",
         "-- Boss fields: key, name, npcIDs, isTrash, items. Forever has one difficulty: no heroicItems.",
         "local _, ns = ...", "ns.Data = ns.Data or {}", "", "ns.Data.Dungeons = {"]
    for d in dungeons:
        L.append('  { key = %s, name = %s, phase = 1%s, bosses = {'
                 % (lua_str(d["key"]), lua_str(d["name"]), ", instanceID = %d" % d["inst"] if d["inst"] else ""))
        for b in d["bosses"]:
            write_boss(L, b, names)
        L.append("  }},")
    L += ["}", ""]
    open(os.path.join(args.out_dir, "Dungeons.lua"), "w", encoding="utf-8", newline="\n").write("\n".join(L))

    write_sources(os.path.join(args.out_dir, "Sources.lua"), head, crafted, reputation, pvp, names)
    report["dropped_count"] = len(report["dropped_not_in_forever"])
    json.dump(report, open(REPORT, "w", encoding="utf-8"), indent=1)
    print("dungeons %d (%d items), raids %d, dropped (not in Forever) %d, Wowhead lookups %d" % (
        len(dungeons), sum(v["items"] for v in report["dungeons"].values()), len(raids), report["dropped_count"],
        names.fetched))


if __name__ == "__main__":
    main()
