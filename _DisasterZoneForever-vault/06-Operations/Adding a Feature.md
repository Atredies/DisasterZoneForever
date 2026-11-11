---
tags: [operations, how-to, forever]
updated: 2026-11-11
---

# Adding a Feature

How to add a feature to DisasterZone for WoW Forever, from the first idea to the release, with one worked example:
**who in the guild is already saved (IDed) to a raid**, like Nova Instance Tracker shows it. Read [[How Sync Works]] and
[[Forever Client Facts]] first.

## The recipe

1. **Check what already exists.** The addon is large (about 460 files): grep before you build. Many "new" features
   are half there already (the worked example below is). [[Code Map]] lists the main files.
2. **Find the game data and check it on Forever.** Forever is the retail 12.x engine with vanilla content, so TBC
   and Classic Era answers are often wrong:
   - grep the Forever UI source (Gethe `wow-ui-source`, branch `forever`; `git clone --depth 1 --branch forever`) for
     the function or event, including `Blizzard_APIDocumentationGenerated` (it marks secret return values);
   - values can be **secret** (health, power, cooldowns, an NPC's name / GUID in instances, raid marks, chat text
     during a boss pull): read them through `Core/Compat.lua` (`Plain`, `IsSecret`, `CanAccess` and the helpers);
   - an old global that Forever renamed gets a shim in `Compat.lua` (SHIMS), not a second code path;
   - anything not confirmed in the real client is marked UNVERIFIED and checked in game before release.
3. **Decide where it lives.** A module is one file in `Core/` (data and logic) plus, if it has a screen, one in `UI/`.
   Create it with `ns:NewModule("Name")` and use `OnInit` / `OnLogin`; list the file in `DisasterZone.toc` (load order
   matters: after `Core/Compat.lua`, `Core/Constants.lua`). Events go through `ns:RegisterEvent` (errors land in the
   Feedback sheet, not on screen; unknown events are skipped), never through a frame of your own unless you must.
4. **Decide whether it syncs, and who may write it.**
   - Only on my client: SavedVariables (`ns.db`), nothing else.
   - Shared with the guild: a message type over `Core/Comm.lua` (pick the prefix by kind of traffic; a small
     per-member status rides along on an existing hello / profile message, see the example). Records many members
     need to agree on use `Core/DigestSync.lua` (revisions, tombstones, digest catch-up).
   - **Security rule:** a receiver believes only the actual sender, never a name inside the payload. A record a member
     writes about themselves is accepted only from them; a record that needs a role (officer, raid planner, council,
     GM) is accepted only from a sender who holds that role right now (`Guild:IsOfficer`, `Guild:IsRaidPlanner` and friends). Add a
     hostile test (a forged message is refused); see `dev/tests/forever/test_forever_authority*.py`.
   - Forever refuses addon messages during a boss pull: send through `Comm` (it holds them) or `Comm:SendOrHold`.
   - Lists sent as indexes (the n-th raid) need the same list on every client: **only ever append** to them.
5. **UI.** Reuse the shared toolkit (`ns.UI`, `ns.Style` colours and type scale): `tools/check.py` flags literal
   colours, font sizes and home-made helpers. Players' names come from `Util.UnitNameRealm` (Forever names have a
   surname).
6. **Tests.** Every feature gets a suite in `dev/tests/` driven by the mock client (`dev/tools/wowmock`, Forever
   profile `forever=True`). Multi-member features use a `World` with several `Client`s; go-live style scenarios live
   in `dev/tests/golive/`. Run `tools/check.py -q` and `tf_e/run_all.py --all` ([[Linux Dev Setup]]).
7. **Ship.** Feature branch, PR, merge to `main` after the full run. Update the vault (Changelog, Decision Log, Code
   Map, the board card). Players get it with the next zip (`release.py full`, see [[Developer Guide]] > Releasing).

## Worked example: who is saved to a raid

**Goal:** in the raid planner and on the Groups board, see which members (and which of their characters) are already
saved to Onyxia's Lair, Hyjal Summit or Barrow Deeps this week, and when the lockout resets. Nova Instance Tracker
does this per character for one account; we want it per guild.

**What exists already (2026-11-09):**
- `Core/DungeonRuns.lua` `ScanSaved` (around line 619) reads the player's lockouts with `GetNumSavedInstances` /
  `GetSavedInstanceInfo` on `UPDATE_INSTANCE_INFO` and asks for fresh data with `RequestRaidInfo` (around line 3255).
  It keeps raid lockouts in `GK.saved[raidKey] = { untilT, done, total }`.
- Each member's Groups profile message (`DRP`, sent on the guild channel, prefix "run") already carries `rs`: the
  indexes (into `GK.raids`) of the raids the sender is saved to. The Groups board uses it.
- The Forever raid list of the Groups board is `Data/GroupKinds.lua` (`BarrowDeeps`, `HyjalForever`, `Onyxia`).
- The Forever client has all three functions (they are old globals, used by Blizzard's own `RaidFrame.lua` /
  `RaidInfoFrameSocialView.lua` on Forever); `UPDATE_INSTANCE_INFO` is in the generated API docs.

**What is missing:**
1. **Matching a lockout to a Forever raid.** `ScanSaved` maps the lockout's instance id to a raid key through
   `ItemDB:ItemKeyOf(instanceId)`. Barrow Deeps and Hyjal Summit have no known instance id yet (they open 2026-12-09;
   [[Adding a Forever Raid]] explains `/dz raiddata`). Once the ids are in `Data/ForeverRaids.lua`, check the item
   data's raid meta maps them; else match by `ForeverRaids` instance id first, then by name (as the dungeon branch of
   `ScanSaved` already does with `SAVED_WORDS`). UNVERIFIED: whether Onyxia's Forever instance id is still 249.
2. **Alts.** Nova shows every character of the account. DisasterZone knows a member's alts (Members: main / alt
   link). Each character reports its own lockouts when it logs in; keep the last report per character with its reset
   time (`untilT`) so an alt that is offline still shows as saved until the reset. Store reports per character key in
   the Groups peer data (it already keeps `peer.saved` / `savedUntil` for dungeons) and drop them after `untilT`.
3. **Boss progress.** `GetSavedInstanceInfo` also returns `numEncounters` and `encounterProgress`, and
   "saved, 3 of 8 bosses" is more useful for a raid leader than "saved". Send `done` / `total` with `rs` (a new
   optional field in `DRP`; older clients ignore it). Per-boss detail (`GetSavedInstanceEncounterInfo` on other
   clients) is not in the Forever UI source: UNVERIFIED, probe it in game before relying on it.
4. **Showing it.**
   - Raid planner (`UI/RaidPlanUI.lua`): next to each sign-up, a small "Saved (3/8)" tag when that character is
     saved to this raid and the raid's date is before the reset.
   - Groups board: already shows "Saved"; add the count and the reset day.
   - Optional: a "Lockouts" view listing members by raid (Nova's main window), one row per character.
5. **Security.** A member reports only their own lockouts, so a `DRP` is believed only for its sender (it already is:
   the profile is keyed by the sender). Never accept lockouts "for" another player.
6. **Forever specifics.** Lockout data is not a combat value and not secret. `RequestRaidInfo` is safe out of combat;
   call it on login, after an encounter ends and when the raid planner opens, debounced. Sending happens with the
   existing debounced profile (`SendProfile`), so no extra traffic.
7. **Tests.** The mock already has `GetSavedInstanceInfo` / `RequestRaidInfo` (`dev/tools/wowmock/game.lua`); give
   each client its own lockouts, then a suite: a member saved to Onyxia shows as saved in another member's raid planner; an alt's lockout
   persists while the alt is offline until the reset; a forged `DRP` for someone else changes nothing; the lockout
   disappears after the reset time.

Board card: [[raid-lockouts-who-is-saved|Raid lockouts: who is saved]].
