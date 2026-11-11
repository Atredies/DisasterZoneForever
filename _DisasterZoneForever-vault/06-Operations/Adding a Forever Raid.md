---
tags: [operations, forever, raids]
updated: 2026-11-08
---

# Adding a Forever Raid

The raid planner offers the raids in `addon/DisasterZone/Data/ForeverRaids.lua`, and only those: every guild member
must have the same list, because the sync refuses a raid whose key it does not know. The game has no raid list to
read (the Encounter Journal is empty on Forever; the group finder lists a raid only after release).

## When Blizzard adds a raid (or to fill in a missing instance id)

1. Someone with DisasterZone zones into the raid once, ideally pulls a boss, then types `/dz raiddata`. It prints one
   line per raid the game has shown, e.g.
   `NEW { key = "?", name = "Molten Core", short = "?", size = 40, level = 60, instanceID = 409, bosses = 1 },`
   plus the bosses pulled (encounter id and name) and the group finder's raid-size activities with their category
   (`[Raids]` / `[Dungeons]`); only a raid-category one missing from the file is flagged `(not in the list)`.
   Seen 2026-11-09: Upper Blackrock Spire `[Dungeons]`, 10 players, map 229 (a dungeon, ignore it).
   `-- (in the list: set its instanceID)` means the raid is listed but its `instanceID` is still `nil`: copy the number.
2. Paste NEW lines into `raids` in `Data/ForeverRaids.lua`; pick a short lower-case `key` and a `short` name. **Never
   rename a key that shipped** (saved raids and the sync use it).
3. Run `luaenv/bin/python tests/forever/test_forever_raids.py` (update its expected list), release, and every member
   gets the raid with the update.

## Today's list

| Key | Raid | Size | Level | Instance id | Bosses | Opens |
|---|---|---|---|---|---|---|
| `barrow` | Barrow Deeps | 10 | 60 | unknown yet | 8 | 2026-12-09 |
| `hyjal` | Hyjal Summit | 20 | 60 | unknown yet | 13 | 2026-12-09 |
| `ony` | Onyxia's Lair | 40 | 60 | 249 (classic) | 1 | 2026-12-09 |

Sizes and boss counts from Blizzard's announcement as reported by method.gg, timesaver.gg and mmonster.co
(2026-11-08). Loot, BiS and Atlas data for these raids are a separate job: card "Forever content data".
