---
title: "Attunements on Forever: who is ready for each raid and dungeon"
tags: [task]
status: 3 - To do
priority: p2
effort: M
updated: 2026-11-11
---

# Attunements on Forever

A feature of its own. Show what each raid (and dungeon) needs before you can enter, and
who in the guild already has it, so the raid leader knows before raid night who still has to do their chain.

## Where the code stands
- The TBC original has an attunement **hint**: `Data/GroupKinds.lua` `raids[].attune = { quest =, name = }`, read by
  `Runs:GetMissingAttunements` (`Core/DungeonRuns.lua`) and shown on the group card ("check your attunement: ...",
  `UI/GroupsCard.lua`). It only checks **my own** completed quest and never blocks a sign-up.
- The Forever branch of `GroupKinds.lua` sets the raids **without** `attune` ("no attunements") and removes the
  "Attunement" kind from Other. **That is wrong for Onyxia**, and maybe for the new content.
- The card [[forever-content-data]] says "drop TBC-only systems (... attunements)": that means TBC's keys, not this.

## What Forever needs (verify each against Wowhead Forever / the real client before coding)
| Content | Requirement | Status |
|---|---|---|
| Onyxia's Lair (`Onyxia`) | Drakefire Amulet (item 16309) in the bags of every raider | VERIFIED that it's required ([[Forever Content Facts]]); item id from Classic, verify |
| Onyxia chain | Alliance: quest "Drakefire Amulet" (6502); Horde: "Blood of the Black Dragon Champion" (6602); both go through UBRS | Classic ids, UNVERIFIED on Forever |
| Upper Blackrock Spire | Seal of Ascension key in Classic | UNVERIFIED on Forever |
| City of Dalaran (dungeon, 28-33) | an attunement quest (Forever Content Facts) | which quest: UNKNOWN |
| Barrow Deeps (10), Hyjal Summit (20) | none known | check at raid release 2026-12-09 |
| Later raids (MC, BWL, Naxx, if they come) | Classic attunements | when announced |

## Steps
1. Fill the table above from Wowhead Forever and one in-game check (the item / quest ids).
2. Forever `GroupKinds.lua` raids get `attune`, with **items** besides quests (`{ item = 16309 }`: the amulet in
   the bags is what the game checks, so `GetItemCount` is the real test). `GetMissingAttunements` reads both.
3. Guild-wide: each member's client sends what it has (a small field in its presence / `DRP` message, like the
   raid lockouts in [[raid-lockouts-who-is-saved]]), and the raid planner and sign-up list show who is missing what.
   An officer view lists, per raid, everyone's state (attuned / missing / unknown = no addon).
4. Bring back the "Attunement" kind under Other on Forever, so people can list "Ony attunement, UBRS run".

## Done when
The raid planner shows, for Onyxia, which signed-up members don't have the Drakefire Amulet (alts too). The group
card warns a member who lacks it. Mock tests cover a member with and without the amulet, plus a hostile test (a
peer that claims attunements for someone else).
