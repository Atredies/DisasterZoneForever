---
tags: [reference, forever, content]
updated: 2026-11-11
---

# Forever Content Facts

> Game content of WoW Forever as researched on 2026-11-09, for the content data DisasterZone needs. VERIFIED = Blizzard,
> or two independent guides agree; UNVERIFIED = one guide, a datamine or a beta report. Client facts measured by the
> probe are in [[Forever Client Facts]].

## Release shape

- Live since 2026-11-04. Raids open **2026-12-09**, weekly reset. VERIFIED (Blizzard raid post
  `news.blizzard.com/en-gb/article/24303009`).
- **Seasons, not Classic phases.** Spring 2027: a 10- and a 20-player raid, two dungeons, a new area, a legendary
  questline. Summer 2027: another raid plus one revamped Classic raid (not named). VERIFIED (Method, Icy Veins).
- MC, BWL, ZG, AQ, Naxx: not announced. UNVERIFIED datamine lists them with Nightmare Grove, Scarlet Enclave, Storm
  Cliffs, The Crystal Vale, The Tainted Scar.

## Raids (DisasterZone keys in `Data/ForeverRaids.lua`)

| Raid | Size | Bosses (AtlasLoot Forever 1.3.4 order) |
|---|---|---|
| Barrow Deeps (`barrow`) | 10 | Deepscar Matriarch, Khalith the Dreadspinner, Elder Tangleclaw, Well of Sorrow, Amethrax, Del'lynar Songwood, Ravus and Darlissa, Sonya Darkhallow |
| Hyjal Summit (`hyjal`) | 20 | Bandalar, Ancient of Decay, Time-Lost Battalion, Sylvestris Dusksong, Old Gloomlurker, Gharalis the Abyssal, Kathris the Haunted, Elder Minderel, Anara Chillwind, Tracker Stillwind, Council of Thorns, The Wild King, Nythus the Dreambound |
| Onyxia's Lair (`ony`) | 40 | Onyxia (Drakefire Amulet in the bags of every raider, VERIFIED) |

Boss names UNVERIFIED by Blizzard but the same in Method and AtlasLoot. Raid loot: unknown until release (AtlasLoot:
"Loot will be updated asap"). Tier sets appear to be crafted (Malleable Essence of Nature from disenchanting raid
loot; Guardians of Hyjal reputation unlocks the 2-piece; a faction "The Watchers" tied to Barrow Deeps). UNVERIFIED.

## Dungeons (35, one difficulty, no heroics: VERIFIED)

Levels and zones from ForeverDungeonJournal 1.6.6 (Blizzard's ranges for the new ones are a little narrower).

| Band | Dungeons |
|---|---|
| 13-30 | Ragefire Chasm 13-18, **Hall of Thanes** 13-20 (under Ironforge), Wailing Caverns 15-24, **Ruins of Lordaeron** 15-22, The Deadmines 17-26, Shadowfang Keep 20-30 |
| 24-38 | The Stockade 24-32, Blackfathom Deeps 24-32, **Excavation Site: Wetlands** 26-33, **City of Dalaran** 28-33 (Alterac Mts, attunement quest), Gnomeregan 29-38, Razorfen Kraul 29-38 |
| 30-46 | SM Graveyard 30-38, Library 33-41, Armory 34-42, Cathedral 36-45, **The Drowned City** 35-40 (Stranglethorn), Razorfen Downs 37-46 |
| 38-56 | Uldaman 38-48, **Krol'dok Stronghold** 40-45 (Riverglades), Zul'Farrak 43-50, Maraudon 45-52, **Alcaz Prison** 48-53 (Dustwallow), Sunken Temple 49-56 |
| 52-60 | Blackrock Depths 52-60, Lower and Upper Blackrock Spire 55-60, Dire Maul East 55-60, West and North 57-60 |
| 60 | **Blackmaw Hold** 55-60 (Azshara), Scholomance 58-60, Stratholme Living and Undead 58-60, **Shaper's Terrace** 58-60 (Un'Goro) |

## PvP

- Battlegrounds: Warsong Gulch 10, Arathi Basin 15, Alterac Valley 40, **Darkspear Islands** 15 v 15 (new, levels
  30-60; reputations Darkspear Raiders / Theramore Expeditionary Force). VERIFIED for Darkspear (Blizzard).
- Honor (buys PvP sets) + Rank Points (ranks 1-14, weekly cap); Emboldened Seals upgrade blue PvP gear. VERIFIED.
- Arenas: none announced. World PvP objectives: none found.

## Classes and professions

- Paladins and shamans on both factions (Undead paladins, Dwarf shamans). New race Skyborne (Windshaper, Horde;
  High-Order, Alliance). Classic three talent trees. Enhancement shaman can tank. VERIFIED (Warcraft Tavern).
- 9 primary professions, no Jewelcrafting, cap 300. VERIFIED.
- Legacy System replaces achievements (three point trees). VERIFIED.
- Consumables: one battle + one guardian elixir; flasks exclusive with elixirs; new level-60 flasks; healing potions
  moved to First Aid. UNVERIFIED.

## Data sources for generators

| Source | What | Licence |
|---|---|---|
| AtlasLoot Classic Forever 1.3.4 (CurseForge 1422985, file 9520898) | vanilla loot, the new dungeons (partly), raid boss lists, BiS tooltips | GPLv2 |
| ForeverDungeonJournal 1.6.6 (installed in the client) | 35 dungeons: levels, zones, bosses, loot, quests | none stated: facts only until the author agrees |
| Questie (Forever DB, installed) | NPCs, quests, items for the old world and new zones | GPLv3 |
| Wowhead Forever tooltip API `nether.wowhead.com/forever/tooltip/item/<id>` | item names / stats | lookup |
| DBM, BigWigs, Details | have 1.60.1 builds (CurseForge API, 2026-11-09) | per addon |
