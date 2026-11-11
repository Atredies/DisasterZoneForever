---
tags: [log]
updated: 2026-11-12
---

# Decision Log

| Date | Decision | Why |
|---|---|---|
| 2026-11-08 | Fork `tsumilo/DisasterZone-dev` 1-to-1 with full history | Attribution kept: upstream history, `upstream` remote, `addon/DisasterZone/NOTICE.md` (GPLv2 AtlasLoot-derived data, library licenses) |
| 2026-11-08 | Public repo named `DisasterZoneForever` | Same naming convention |
| 2026-11-08 | Keep signed in-game updates (hotpatch) | It is how the original runs. Fix the load-time check (Adler-32 only) |
| 2026-11-08 | Addon stays Lua | WoW runs only Lua |
| 2026-11-08 | Keep the original internal names (`DisasterZone` folder, `/dz`, `DisasterZoneDB`, prefixes) | Flavors have separate AddOns/WTF folders, so no clash; upstream merges stay clean; guildmates know the commands |
| 2026-11-08 | Probe is a solo passive logger | Two-character checks (party/raid messages, setting master loot) wait for a group |
| 2026-11-08 | Raid-leader features before the full test pipeline | First raids 9 Dec 2026; compat + council/reserves/sign-ups/attendance/roles first, content and combat later |
| 2026-11-09 | Forever shamans cannot dual wield: `ns.DUAL_WIELD.SHAMAN` is nil on Forever | Blizzard's class overview never lists it; zockify, wow.gg, lfcarry and dtgre guides say no |
| 2026-11-09 | During a boss pull, skip `CHAT_MSG_*` (and other secret-payload events) whose payload cannot be read | Payloads are secret in chat lockdown; same check as Blizzard's ChatFrameFilters |
| 2026-11-09 | Secret cooldowns / speeds: keep the last plain value seen instead of erroring | A frozen timer is better than a Lua error; verify in game |
| 2026-11-09 | Distribution for go-live: a zip on this repo's GitHub Releases page | Simplest path while in-game updates stay off |
| 2026-11-09 | Version numbering restarts for Forever: 0.x.x before go-live, starting at 0.1.0; go-live is 1.0.0 | 0.x.x marks builds before go-live |
| 2026-11-10 | Skip publishing 0.2.1; publish 0.2.2 from `main` instead (0.2.1's fixes + recruitment fixes + a visible "couldn't take X's list" notice) | 0.2.1's zip predates PRs #61/#62; one update for the guild instead of two |
| 2026-11-10 | Attunements are a feature on Forever (own card), not a TBC leftover to drop | Onyxia needs the Drakefire Amulet; the old hint only checked my own quest |
| 2026-11-10 | Player zips go out as full releases marked Latest (0.2.0 switched from pre-release); the README links `/releases/latest` and keeps the rest of the docs in the vault | Guildmates get one link that never goes stale; the README stays short |
| 2026-11-10 | Recruitment message places: GuildRecruitment off by default (Trade stays on); skip line names `/join <channel>` | A guilded character is not put in GuildRecruitment, so it was skipped on every post |
| 2026-11-10 | Recruitment message: strip raid icons from channel posts, keep them for Say / Yell | Forever's server flags channel lines so clients don't draw icons; they showed as "{rt1}" |
| 2026-11-12 | In-game updates on from 0.2.3: the project's own update key ships in `Core/PatchKey.lua`; members install later versions with `/dz update` | 0.2.3 is the last zip members need; later code changes travel in game, signed, and only this key's updates are taken |
| 2026-11-12 | Forever bots name the season, not TBC's phases (`/bis`: Pre-raid + Season 1) | Forever has one season so far; the addon says Season |
| 2026-11-09 | Launch zip = DisasterZone + all game packs (Bingo, Azeromon, Hold the Line, Chess); no Bridge | Bridge needs the launcher and the Discord bot |
| 2026-11-09 | Officer ranks: the GM picks them in Settings (synced, GM-owned); default ranks 0-1 | Replaces the hard-coded rank <= 1 |
| 2026-11-09 | GM rules move to their own GM-only record; relayed raid plans only from writer / planner | Closes forging by officers and members; trade-off: members need the GM / a planner online once |
| 2026-11-09 | Release zips ship with in-game updates off (empty PatchKey); upstream keys always refused | No keys of our own yet; upstream could otherwise sign code for our guild |
| 2026-11-09 | Soft reserves: each copy of a duplicate drop uses up one reservation | Fixes the original's duplicate-drop bug |
| 2026-11-09 | Loot log: another council member's entry of a loot line within 120 s is the same line; the same recorder's second entry is a second item; a council award hides one loot line (its hand-out), not all of them for 6 h | Two copies won by one player showed as one (original 1.5.5 / 1.6.0). The old rule assumed one client could log one hand-out twice, which it cannot |

## 2026-11-08 - Comm queues during encounters
Addon messages return `AddOnMessageLockdown` for the whole of a boss pull on Forever (measured). Comm will queue
while `C_ChatInfo.InChatMessagingLockdown()` is true and flush when the Chat restriction ends, rather than dropping
or retrying blindly. Raid-leader flows (council, attendance, sign-ups) run between pulls and need no other change.

## 2026-11-08 - Old API names come back as global shims
About 30 old global functions are missing on Forever and are called from ~60 files. Rebuilding each old global from
its C_ replacement (only when missing, in `Core/Compat.lua`) keeps the code 1-to-1 with upstream and merges clean,
instead of editing every call site. Trade-off: other addons see these globals too; they are the client's own names
with the client's old behaviour, so that is acceptable. Functions with no faithful replacement (old talent tabs,
trade skill windows) are left missing, because every caller already checks for them.

## 2026-11-08 - Pause ChatThrottleLib during a pull instead of patching it
A message whose parts are still in ChatThrottleLib's queue when a pull starts loses them: CTL treats
`AddOnMessageLockdown` as a final failure. Rather than edit the bundled CTL (another addon's newer copy would replace
it), `Core/Comm.lua` wraps `ChatThrottleLib.Despool` at login and before each send, and skips despooling while
`C_ChatInfo.InChatMessagingLockdown()` is true. Side effect: other addons' queued messages wait through the pull too,
which only saves them from the same loss.

## 2026-11-08 - Test against recorded Forever sessions
The mock's Forever profile is generated from a probe run (`dev/probe/mock_facts.py`), not hand-written, and real
sessions are replayed from probe logs (`dev/probe/export_replay.py`). Re-run both after each probe run, so the tests
follow what the client actually does.

## 2026-11-08 - Surnames: one helper, not a UnitName override
Forever's `UnitName` returns first name and surname where other clients return name and realm. Overriding the
global `UnitName` would fix every caller at once but taints Blizzard's own code that calls it (and changes it for
every other addon). Instead `Util.UnitNameRealm(unit)` returns the name as the roster writes it (first name and
surname) and is used wherever a unit becomes a name key; display text keeps plain `UnitName` (first name only). New
code that turns a unit into a key must use the helper.

## 2026-11-08 - Forever raids: one shipped list, learned data gets pasted in
The client has no raid list to read (empty Encounter Journal; the group finder lists a raid only once released), and
the sync refuses a raid whose planner key the receiver does not know, so the whole guild must share one list. The
list lives in `Data/ForeverRaids.lua` and ships with a release.
`/dz raiddata` (Core/RaidLearn.lua) records what the game shows (instance ids, bosses, group finder raids) and prints
ready entries, so adding a raid is a paste; it never changes the planner by itself. Planner keys (`barrow`, `hyjal`,
`ony`) are permanent once shipped.

## 2026-11-09 - Protected frame calls go through one helper
`Frame:SetPropagateKeyboardInput` is protected in combat. Instead of guarding 38 call sites one by one (half already
were), every call goes through `Util.SetPropagateKeys`, which skips it in combat and applies the latest value when
combat ends. New code must use the helper; the Forever mock blocks the raw call in combat, so a test catches a miss.

## 2026-11-09 - Forever only; TBC paths stay dead until replaced
DisasterZone targets WoW Forever only. The client only ever runs the Forever branch (`Compat.isForever`),
so every Forever list replaces the TBC one at load time behind that flag, and the TBC data and code stay in the tree,
unused, until each area has Forever data and tests; then they are deleted area by area. This keeps the ~2,900
upstream test cases (TBC profile) running as a regression net, and upstream merges possible, while the guild sees only
Forever content. Wire lists that only Forever clients exchange (dungeons, group kinds) start a fresh order on Forever:
from now on append only.

## 2026-11-09 - Phases: show one, accept five
Forever has one raid tier so far. The UI shows Pre-raid + P1 (`ns.MAX_PHASE = 1`) but stored and received BiS lists
accept phases up to `ns.WIRE_MAX_PHASE` (5), so a list made by a newer release with a second phase is kept, not
refused.

## 2026-11-09 - Decisions on the Forever-only port
| Decision | Why |
|---|---|
| UI says "Season" / "S1", not "Phase" / "P1" | Blizzard runs Forever in seasons |
| TBC code and data deleted area by area (replace, then delete) | No dead TBC paths in the product; each area keeps working while its Forever data lands |
| The Binding of Illidan pack dropped | Black Temple themed |
| ForeverDungeonJournal: facts only (names, levels, zones, bosses) | It has no licence; loot comes from AtlasLoot (GPLv2) and public databases |
| Raid loot (Onyxia included) empty until known | Never show a wrong item; AtlasLoot has none yet |
| New-dungeon loot without observed drops: one "Loot (boss not confirmed)" list | Items are real (client item blocks, Wowhead-verified); boss assignments would be guesses |
| Karazhan Chess kept, Raid Trainer dropped | Chess works anywhere; the Trainer only has TBC bosses and rooms |

## 2026-11-09 - TBC data lives on as test fixtures
"Delete per area" would break ~100 upstream suites that use TBC items and bosses as fixtures for the engines
(council, BiS, raid plans, boss mods). Instead the TBC data files moved to `dev/fixtures/tbc/` and the harness runs
them in place of the addon's files for TBC-profile clients (`forever=False`, the default). The shipped addon has only
Forever data; the engine tests keep their fixtures; Forever suites (`forever=True`) run the shipped files. Where the
addon now has one Forever file and the TBC fixture had several (the boss mods), `TBC_FAN_OUT` maps them.

## 2026-11-09 - Forever specs come from the trait tree
Forever has one spec per class, named after the class (in game: `GetSpecializationInfo(1)` = `1491 Warrior ...
DAMAGER`, 0 points). The three vanilla talent trees are trait-node groups; DisasterZone reads points per group and
matches each group to `ns.SPECS` by name, else by order. The spec role is the last guess (a class's one spec always has
the same role). When the tree can't be read, a spec-restricted class tool shows for the whole class.

## 2026-11-09 - Class tools: rework what vanilla supports, hide what it doesn't
Paladin: no twist on Forever (no Seal of Blood or Crusader Strike, and Judgement does not end the seal), a plain swing
timer. Hunter: reworked around Aimed Shot / Multi-Shot / Arcane Shot. Shaman: Heroism and Bloodlust gated out, Earth
Shield kept (a level-50 baseline spell on Wowhead Forever). Swing timers use `PLAYER_SWING` (no combat log).

## 2026-11-09 - Forever uses Classic uiMap ids
SavedVariables from a Forever client show 1429 Elwynn, 1436 Westfall, 1453 Stormwind: the Classic numbers, not retail's. The
guild map opens on 1415 (Eastern Kingdoms); Kalimdor is 1414.

## 2026-11-09 - Demo art by FileDataID, TBC event art keys still resolve
Vanilla loading screens are referenced by FileDataID (wowdev listfile). On Forever the event art picker offers only
old-world screens, but a saved or received event with a TBC art key still shows its picture.

## 2026-11-09 - The TBC rooms stay in git, out of the release
The Rooms pack's TOC lists only the chess room; the TBC rooms remain in the repo because the TBC-profile strategy
suites draw them (fixture TOC under `dev/fixtures/tbc/`), and `release.py` ships only what the TOC lists.

## 2026-11-09 - A secret reads as "unknown", not as zero
On Forever health and power are secret everywhere, a mob's name and GUID inside instances. Code that needs them for a
decision treats a secret like a missing value (`Compat.Plain` -> nil): health-% alerts and the execute phase do not
fire, a unit frame shows a full bar without numbers (not an empty one, which would read as dead). Showing the real
bar needs the secret handed straight to a StatusBar, which is the rebuild on card "Combat features on Forever APIs".
Aura reads refused in combat answer "no aura" in the shim, so every caller keeps its out-of-combat behaviour.

## 2026-11-09 - Every shipped item id is checked against Wowhead Forever
AtlasLoot Classic Forever still lists Classic, Season of Discovery and later-raid ids (e.g. the Tier 2 bracers) that
Forever does not have. The generators keep an item only when Wowhead's Forever tooltip API knows it; answers are
cached in `dev/generators/data/forever_items.json` (committed) so a re-run is offline and reproducible.

## 2026-11-09 - Paladin: gone blessings keep their Pally Power index
Forever has no Blessing of Salvation, Light or Sanctuary, no Crusader Aura and no Symbol of Kings (Wowhead's Forever
spell database). Pally Power's wire protocol sends blessings by index, so the gone ones keep their place with no
ranks: nobody "knows" them, no menu offers them, and a Pally Power user's numbers still mean the same blessings.
Durations are Forever's hour for both kinds.

## 2026-11-09 - Pages without Forever data are hidden, not emptied
Gear sim, My Log, Raids > Strategies, and the Meters / Boss mods / Strategy / My Log settings cards are hidden on
Forever (`ns.FOREVER_HIDDEN`, Settings' Combat section) rather than shown empty: each needs either the combat log
Forever does not give addons or Forever data nobody has yet. They come back one by one with that data.
