---
title: "Forever content data"
tags: [task]
status: 1 - In progress
priority: p2
effort: L
updated: 2026-11-11
---

# Forever content data

Regenerate `Data/` from AtlasLoot Classic Forever + Wowhead Forever: raids (new key for Forever Hyjal), dungeons, BiS. Drop TBC-only systems (gems, badges, arena, heroic keys, attunements).

## Done when

Atlas and My BiS show Forever raids and items.

## Seen in game 2026-11-08

The first DisasterZone session on Forever shows the TBC data: the Raids filter lists Karazhan to Sunwell (no Barrow
Deeps, Hyjal Summit, Onyxia), My BiS has Pre-raid and P1-P5 and the home banner says "Pick your Phase 1 BiS", and the
item picker finds no items (TBC item ids are not in Forever's item database).

## Done 2026-11-08: the raid planner's raids

`Data/ForeverRaids.lua` (Barrow Deeps 10, Hyjal Summit 20, Onyxia's Lair 40, level 60) drives the raid planner on
Forever; see [[Adding a Forever Raid]]. Still TBC: item/loot data (`Data/Items.lua`), BiS lists and phases, Atlas,
boss journal and boss mods, raid art for the new raids.

## Done 2026-11-09: Forever-only pass (no new loot data yet)

One raid phase, Classic-only Atlas, Forever's 35 dungeons on the Groups board (no heroics), Forever group kinds, recruit
milestones 40/60, no Jewelcrafting ([[Changelog]]). Facts: [[Forever Content Facts]].

## Done 2026-11-09 (later): Forever item data

Items / Dungeons / Sources / Raids / Gems / Consumables are Forever's; BiS suggestions off; TBC data in
`dev/fixtures/tbc/` ([[Changelog]]). Loot still missing: the three raids (opens 2026-12-09), boss-by-boss for 5 new
dungeons.

## Next (old list, items 1 and 4 mostly done)

1. Item data for Forever (`ns.Data.Raids` / `Dungeons` / `RaidMeta` on Forever): generate from AtlasLoot Classic
   Forever (download by script): vanilla dungeons + Onyxia + the new dungeons' partial
   loot, the two new raids as boss lists with no loot until 2026-12-09. This feeds the BiS picker, council, Atlas raids
   and raid art/icons (raid groups have no art today).
2. Pre-raid BiS lists from AtlasLoot Forever's BiS data (replaces LoonBestInSlot).
3. Loading screens for the 9 new dungeons (FileDataIDs from wago.tools / the client).
4. Consumables kit, currencies (honor / rank points, no badges / arena), Paladin and Shaman class data (vanilla ranks,
   Forever's totem changes).

## Next (2026-11-09)

1. ~~Remove the Raid Trainer pack~~ (done 2026-11-09). `DisasterZone_Rooms`: keep only what Chess needs (the
   Karazhan room) in Forever releases.
2. ~~Regenerate AtlasClassic~~ (done 2026-11-09). ~~`Data/Atlas.lua`~~ (done: `gen_forever_atlas.py`) (TBC tree, still shipped because its crafts / recipes / names tables feed the shopping list and
   materials): regenerate the crafts and recipes from AtlasLoot Forever's Profession.lua / Recipe.lua, then drop the
   TBC tree. Regenerate `Data/AtlasClassic.lua` from AtlasLoot Forever (`gen_atlas_classic.py` needs the Forever
   table keys and the Wowhead name check) so crafting / reputation / PvP pages list only Forever items.
3. Full vanilla enchant list (27 today), ~~Paladin data~~ (done), Currency (honor / rank
   points; no badges / arena), demo data and the in-addon changelog (TBC examples).
4. Raid loot once known; boss-by-boss loot for Krol'dok, Drowned City, Alcaz, Blackmaw, Shaper's Terrace.
5. ~~Demo mode's sample guild~~ (done 2026-11-09; MyLogDemo / MeterDemo stay TBC: their features are hidden) (Core/Demo.lua, AuditDemo, ReserveDemo, MyLogDemo, MeterDemo) on Forever raids and items.

## 2026-11-09: TBC sweep

Demos, art, wording, packs and class data moved to Forever (PRs #35-#38, [[Changelog]]). Still
open: raid loot after 2026-12-09; Azeromon hall art for the Forever raids; Bingo raid pools for Forever (need
something other than the combat log); Barrow Deeps has no loading screen of its own (Eastern Kingdoms placeholder).
