---
title: "In-game check of every page"
tags: [task]
status: 1 - In progress
priority: p1
effort: S
updated: 2026-11-11
---

# In-game check of every page

Open each DisasterZone page on the live Forever client and screenshot it (Print Screen; the files land in
`_forever_/Screenshots`); the addon's own error log is read from
`WTF/Account/*/SavedVariables/DisasterZone.lua` after a `/reload`.

## Checked 2026-11-08 (no DisasterZone errors)

| Page | Result |
|---|---|
| Tour, Home (calendar, your loot) | works |
| Raids > Upcoming, filters | works; raid list is TBC (card "Forever content data") |
| Gear > BiS, slot picker | works, 3D model renders; TBC phases, picker finds no items (content data) |
| Groups | works |
| Guild > Roster, a member's Professions | works, spaced names shown; showed the GM twice (fixed: surnames) |

## Surname fix confirmed in game 2026-11-08

- `RegionalUniqueNamesEnabled()` true; `UnitName` / `UnitNameUnmodified` / `UnitFullName("player")` second value is
  the surname; `GetUnitName("player", false)` is "Name Surname".
- Running addon: `Util.PlayerKey()` and `Guild:GetGM()` both `Name Surname-Realm`, `IsGM` true;
  `Guild:GetMembers()` has the GM once and no first-name-only entry.
- Note: a `/reload` saves the session that is ending, so data saved right after installing a new build was written by
  the old code. Check fixes with `/run` against the global `DisasterZone` (the addon's namespace) instead.
- Old saved data under the first-name-only key (professions, char data, a self "peer") is left in place: only the
  GM's copy has it, it is not a roster member; it will be overwritten or age out.

## Confirmed in game 2026-11-09

- Recipes: Blacksmithing 31, Mining 4, Cooking 9, First Aid 5 shared after opening the windows.

- `/dz raiddata` runs (listed Upper Blackrock Spire; now labelled `[Dungeons]` and not flagged).

## Fixed, to re-check in game (2026-11-08)

- Raids: the filter and New raid list Barrow Deeps / Hyjal Summit / Onyxia's Lair / Other; sizes 10/20/40; "Level 60
  only". `/dz raiddata` prints the data-file entries.

## Still to check

- The DisasterZone roster page itself after the fix (screenshot), and the GM/officer controls it offers.
- Raids > Teams, Strategies; loot council and loot rules pages.
- Every Gear and Guild menu entry (My Log, Gear sim, Consumables, Wardrobe, Atlas; Map, Events, Polls, Recruit, Audit).
- Guild > Recipes: did not fill after opening Blacksmithing (seen 2026-11-08). Fixed for Forever's window (C_TradeSkillUI);
  re-check in game: open Blacksmithing, then Guild > Roster > own Professions shows recipes.
- Settings, `/dz perf`, one item tooltip (expected missing: card "Item tooltip on TooltipDataProcessor").

## 2026-11-09 (Forever-only build)
Confirmed: build running, no Hall of Thanes error,
raid creation (after PR #29).
