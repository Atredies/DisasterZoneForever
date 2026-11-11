---
tags: [log]
updated: 2026-11-11
---

# Changelog

Newest first.

## 2026-11-11 - Addon: one bot key per guild (draft)
`Core/Bridge.lua` now reads `ns.BridgeKeys[guildKey]` (keyed like `Guild:GetGuildKey()`, "Guild Name-Realm"), so the
PvP and PvE guilds each trust only their own bot's signed records; a record signed for another guild is ignored, not
marked refused. The single legacy `ns.BridgeKey` is still read. `test_bridge.py`: two new cases, suite 23/23; patch
suite 15/15.

## 2026-11-10 - 0.2.2: why 0.2.0 players "don't sync", sync says so now; attunements card
Guildmates on 0.2.0 did not sync with 0.2.1. Two causes. (1) 0.2.1 was built but **never
published**: GitHub's Latest was still 0.2.0, so everyone downloading got 0.2.0. (2) `Store:ValidateData` refuses a
player's **whole** BiS record when any item id (pick, obtained or **equipped**) is above its cap; 0.2.0's cap is
200000 and Forever's new items are 280000+, so a 0.2.0 council drops the list of anyone wearing new gear, with only a
debug line. Same wire protocol (1), no version gate in Sync: old clients can only be fixed by updating.
0.2.2 from `main`: `Store:Put` prints "Couldn't take X's BiS list (...). If they run a newer
DisasterZone than you (/dz version), please update." once per player per session; plus the recruitment fixes
(PRs #61, #62) and the pug-rolls idea card. Test: `test_a_list_this_client_cannot_read_is_said_once`. Version in the
six TOCs, What's New, README, `dev/releases/0.2.2.md`. New card [[attunements-on-forever]] (the Forever raid list
dropped the TBC attunement hint, but Onyxia needs the Drakefire Amulet).

## 2026-11-10 - Idea: pug-friendly rolls
Idea, documented only (no code): when we raid with pugs, `/dz roll` should link the item in raid chat, gather
every roll (addon or not) in one sorted list, and show what each roller would replace. New card
[[pug-friendly-rolls]] (Later, p3). Most of the first two already exist in `Core/Roll.lua`; the real gap is pug gear
(inspect), and the first step is a test with a pug.

## 2026-11-10 - Recruitment message: channels get it without raid icons
A Trade post showed "{rt1}" as text at both ends. Cause (Forever UI source,
`Blizzard_ChatFrameBase/Mainline/ChatFrameOverrides.lua:581`): each chat line carries a server flag (CHAT_MSG arg17)
telling clients not to draw raid icons, and Trade got it, so no addon can show icons there. Fix
(`Core/RecruitMessage.lua`): `Compose(noIcons)` leaves out icon parts and takes `{rt1}` / `{star}`-style codes out of
the words (unknown `{words}` stay); channel places get that text, Say and Yell keep the icons. A message of icons only
is skipped in channels with "only icons, and channels don't show them". The icon part's tooltip and the addon README
say so. Test: `channels_get_the_message_without_icons`.
**Verified in game (2026-11-10):** the Trade post arrives without `{rt1}`. Whether Say and Yell draw the icons on
Forever is unverified (the flag is the server's).

## 2026-11-10 - Recruitment message: GuildRecruitment off by default, and a hint when you're not in it
Post now went to Trade but printed "Not posted: GuildRecruitment: you're not in
GuildRecruitment". Cause: GuildRecruitment was one of the two places on by default, and a guilded character isn't in
that channel (the game puts guildless players in it), so every officer got that line. Fix (`Core/RecruitMessage.lua`):
new setups start with GuildRecruitment listed but **off**, and the skip line says what to do: "GuildRecruitment:
you're not in it, type /join GuildRecruitment". Setups saved before keep their places (an officer unticks it or
joins). Test: `test_recruit_message.py` (defaults, the new line).

## 2026-11-10 - 0.2.1: fixes from the first guild test
Version 0.2.1 in the six TOCs, What's New entry (`Data/Changelog.lua`), release notes `dev/releases/0.2.1.md`, README
zip name. Ships PR #57 (Dungeon tiles fit) and PR #58 (item ids 280000+). Player guide: the Groups tiles' short names
and how officers set up the recruitment message (Message / Posting tabs, posting needs a click).

## 2026-11-10 - Forever's new items (ids 280000+) work in rolls, My BiS and loot
Found in the first live test (GM + one member): `/dz roll [item]` printed its usage line and some items in the new
dungeons' "Loot (boss not confirmed)" lists would not go into My BiS. Cause: every item check kept the TBC cap of item
id 200000, and Forever's new items are 280000-287068. The cap is now 1000000 in BiS, BiSImport, Store, ItemDB, Roll,
Loot, Ledger, Loon, LootLog and DropPanel; the two tests that used 300000 / 999999 as an "invalid" id now use 2000000.
Test: `test_forever_new_items_above_200000_are_valid`. Both players need the new build: a 0.2.0 client still drops
these ids from what it receives (synced BiS lists, rolls).

**Live test so far (2026-11-10):** steps 1-10 of [[Multi-player Test Plan]] pass, apart from the roll (this fix).
Raid sign-up waits for level-60 characters (the raid's level limit refuses the leader too; correct).

## 2026-11-10 - Groups sheet: dungeon tiles fit the window
On "List a group" > Dungeon the tiles ran off the sheet's right edge, long names spilled out
of their tiles, and the "Level 60" row had no picture. Causes: the layout reserved room for TBC's four tiles per row
(Forever's level bands hold six) at a fixed 130 px; the Forever data had full names only; the row picture came from
the band's first dungeon (Blackmaw Hold, no loading screen). Fix (`UI/GroupsSheet.lua`, `Core/DungeonRuns.lua`): the
tiles share the row's free width (at most 130 px), labels are short names (field [7]: LBRS, DM: East, Strat: UD...,
truncated if still too long) with the full name in the tooltip, and the row picture is the first dungeon with a
loading screen. Test: `test_dungeon_sheet_tiles_fit_on_forever`.

## 2026-11-10 - 0.2.0 release notes link the README
`dev/releases/0.2.0.md` (and the GitHub release text, updated from it) now points to the README's install guide and
the player guide, with full URLs because relative links don't work on a release page.

## 2026-11-10 - 0.2.0 is the Latest release; README links into the vault
0.2.0 switched from pre-release to a full release marked Latest, so `/releases/latest` opens it. The README's download
link now points there, and its "More reading" section links the vault notes for players, the project and developers.
[[Developer Guide]] says to mark future zips Latest.

## 2026-11-10 - README is now a player install guide
Root `README.md` cut down to download, install, update and bug-report steps for guildmates, linking straight to the
0.2.0 zip (checked: the zip's top-level folders are the six `DisasterZone*` folders). The developer material (layout,
Linux setup, commands, tests, releasing, launcher) moved unchanged to [[Developer Guide]].

## 2026-11-10 - 0.2.0 published; test plan for the guild
0.2.0 published on GitHub Releases (pre-release, tag v0.2.0). [[Multi-player Test Plan]] splits the first guild test (2026-11-11) into GM / Officer / Members steps.

## 2026-11-10 - 0.2.0: sync after a login wave, security passes 3-4, go-live polish
Five branches merged on `integ/round5`; full run 325 suites, the 17 known failures.
- **Sync (fix/sync-login-wave + tuning on integ/round4):** a member whose own catch-up settled sends a recheck digest
  (`XXR`); members holding what it lacks answer; relayers' and planners' digests are remembered so wants and held-copy
  asks go to a role holder that has the items; the GM answers members last during a login wave; no duplicate gives
  (`Comm:Drained`). 40-member login wave: 0 members missing, ~812 s per-prefix, ~811 s strict shared bucket.
- **Security 3 (fix/authority-holes-3):** events and polls (incl. votes) only from their writer or a role holder,
  relays held and fetched; council list only from the GM; members' own records only from them; HELLO carries
  `iface = 16001` and only Forever peers count as "newer".
- **Security 4 (fix/authority-holes-4):** Feedback, EventLive hosting, DungeonRuns owners, Professions (incl. the
  officer-only main link), FeedbackPlan, Ledger `by`: actual sender only; a plain member's relay of someone else's
  record is kept marked "passed on by X" until the owner / an officer confirms it.
- **Polish (fix/golive-polish):** roll window restored after /reload (`RQ`); upstream release records moved to
  `dev/fixtures/tbc/releases/`; Azeromon Guild Hall wings for Forever raids; one-class items from the tooltip's
  "Classes:" line; Looks previews unreachable on Forever; `dev/releases/0.2.0.md`.
- Version 0.2.0 (TOCs, What's New). Open: a member signed up to an event can still take over its live run on a client
  that never saw it; unconfirmed me-toos count; group-run player profiles go by the relayer; role holders can still
  forge "by" someone else (needs signatures).

## 2026-11-09 - Security pass 2 and the multi-player go-live test
- **Security (fix/authority-holes-2):** relayed sign-ups only from their owner, a planner, the raid leader or the
  Discord host (else fetched from the owner); audit-log and note authors from a relayer get a local "relayed by X"
  mark; LootReserve sessions only from the group leader / master looter / loot authority; role-gated records (prized,
  events season / reviews / officer removals, polls edits, strategy fills and edits, team waitlists) need the role.
  Hostile tests: `dev/tests/forever/test_forever_authority2.py`.
- **Go-live tests (test/golive-readiness):** `dev/tests/golive/` (guild day 15 members, Onyxia 40 and Hyjal 20 raid
  nights, 40-client load, resilience): 29 cases pass. Fixed: event sign-ups lost in a catch-up (dependency order in
  DigestSync; prune only sign-ups of deleted events). Verdict: ready with caveats. Open: after a 40-member login wave
  most members miss some events until /reload; events / polls can be forged "by the GM" through the give path; an
  open roll does not survive /reload; the old-version exemption is exactly "1.5.5".
- Full run on the merge: 322 suites, the 17 known failures.

## 2026-11-09 - Guide: adding a feature (worked example: who is saved to a raid)
New [[Adding a Feature]] (06-Operations): the recipe from Forever API checks and secret values to sync, the sender-only
security rule, UI, tests and release, with Nova Instance Tracker-style raid lockouts as the worked example (most of
the plumbing exists in `Core/DungeonRuns.lua`). Board card [[raid-lockouts-who-is-saved|Raid lockouts: who is saved]].

## 2026-11-09 - Go-live round: security, 0.1.0, raid night, duplicate drops
Four branches in parallel, merged on `integ/go-live`, run through `run_all --all`.
- **Security (fix/authority-holes):** GM rules travel in their own GM-only record (`GMR`, sender must be live rank 0);
  reserve lists only from the raid's loot authority; relayed raid plans only from their writer, a planner or (teams)
  the council; one `RankIsOfficer` check with ranks the GM picks (Settings > Guild > Officers, default 0-1; secret or
  unknown rank = no officer); dev powers only for `Util.DEV_KEY` (one character on the guild realm). Hostile tests:
  `dev/tests/forever/test_forever_authority.py`. Still open: relayed sign-ups can be forged; audit-entry author;
  `by` labels from same-role peers; the LootReserve mirror.
- **Release 0.1.0 (release/0.1.0):** versions restart at 0.1.0 (1.0.0 = go-live); a stored "1.5.5" ranks below
  everything on Forever (never ship 1.5.5). `Core/PatchKey.lua` is empty: in-game updates off; upstream's patch and
  bot keys are refused (`Patch.IsUntrustedKey`, also in Bridge). `release.py full` builds the GitHub zip (main +
  Azeromon, Bingo, Chess, Hold the Line, Rooms; never Bridge) and checks it (`verify_zip`). What's New = one 0.1.0
  entry. Notes: `dev/releases/0.1.0.md`. README: install from GitHub Releases.
- **Raid night (fix/forever-raid-night):** item tooltip lines via `TooltipDataProcessor`; `Comm:SendOrHold` holds
  break timers, ClassPlanner, LootReserve and patch sends through a pull; session crest finds Forever raids by name
  and matches bosses by name; Hyjal's 13 bosses wrap; master loot exists on Forever (UI source + probe).
- **Duplicate drops (fix/duplicate-drops):** bug from the original (1.5.5 and 1.6.0): under soft reserves both copies
  went to the same reserver or copy 2 re-rolled among all reservers; the loot log merged two copies won by one
  player. Fixed; [[Duplicate Drops Fix]]; `dev/tests/loot-roll/test_duplicate_items.py` (10 of 12 failed before).

## 2026-11-09 - Final-scan fixes for go-live (PRs #42-#44)
Three branches in parallel, merged together and run through `run_all --all` (313 suites, the 17 known failures).
- **Errors in normal play (PR #42):** `Compat.CanAccess`; the event dispatcher and the Recruit frames skip chat and
  other events whose payload is secret during a boss pull. Shims: `ConvertToRaid`, `GuildInvite`, officer notes,
  `PickupSpell`, `GetNumQuestWatches`, `GetZonePVPInfo`, `OffhandHasWeapon`, `IsAutoRepeatSpell`. Kill goals use
  `PARTY_KILL` / `UNIT_DIED`. Pack Escape keys wait for combat to end. Forever detection falls back to Interface
  16001. The global `_` write is gone.
- **TBC text (PR #43):** Groups art, "hit 60", lineup hint, Looks without Boss mods / Meters, `/dz threat`, `meter`,
  `mylog` not registered on Forever, demos name Forever raids, "Enchants", dormant Sunmote / Badge / Heroic words,
  TBC Hyjal pin removed. Forever shamans cannot dual wield (researched, Decision Log).
- **Combat secrets (PR #44):** `Compat.SpellCooldown`, `AttackSpeed`, `RangedSpeed`, `UnitSpeed`, `RaidMark`,
  `SameUnit`, `Name`; used by the timers, totems, LookCast, Plates, Threat, Wardrobe, StrategyLive, Bingo and fight
  reports. The mock returns these secrets as the API docs say.
- Confirmed in game: `GetMaxPlayerLevel()` = 60.

## 2026-11-09 - Final scan: what is still wrong after the sweep
Read-only: audits (Forever API risks, TBC leftovers), the client's error log, `check.py` and `run_all --all` (17 known failures). Biggest: secret chat payloads during boss pulls and missing globals (ConvertToRaid, GuildInvite).

## 2026-11-09 - TBC sweep: what was still TBC, fixed in six branches
Three read-only sweeps listed what was still TBC; six branches fixed it in
parallel, each branch run through `run_all --all` (the 17 known failures, nothing new) before merging.
- **Docs (PR #34):** root README rewritten for the Forever dev kit; the addon README is a Forever player guide (~600
  lines instead of 1,030); NOTICE.md names the Forever data sources; TOC Notes updated; `dev/docs/SPEC.md` and
  `dev/tools/README.md` say they describe the TBC original.
- **Quick fixes (PR #35):** Events "Max level" sign-up uses the level cap (level-60 players were refused; key `lvl70`
  kept), also the Attendance swap-in filter and Members level column. Atlas currency bar pins Honor only. Phase words
  through `ns.PhaseLabel` / `PHASE_WORD` in Settings, Council, DropPanel, Dashboard, Groups, Atlas. Groups PvP sheet is
  battlegrounds only. Guild map and event zones drop Outland (map opens on Eastern Kingdoms). Raid lineups take the
  planner's default size; team themes are the Forever raids. Recruit milestones 40/60, event default art WSG, My BiS
  enchant wording. Test `test_forever_quick_fixes.py`.
- **Packs + release tools (PR #36):** `DisasterZone_Rooms` ships only the chess hall's room (0.15 MB zipped instead of
  13 MB; the TBC rooms stay in git for the TBC-profile strategy suites, list in
  `dev/fixtures/tbc/DisasterZone_Rooms/DisasterZone_Rooms.toc`). Bingo deals no
  combat-log-only squares on Forever and polls deaths from the group (26 core squares). Azeromon raid rares come loose
  on Onyxia / Hyjal Summit / Barrow Deeps bosses; the hall's TBC wings read as open and empty. Test
  `test_forever_packs.py`.
- **Class tools (PR #37):** spec and role from Forever's trait tree (`Compat.TalentTabPoints`, `NumTalentTabs`,
  `Talents`, `TalentRank`, `SpecRole`; `ClassKit:MyRole`). Shaman: no Heroism / Bloodlust, Earth Shield kept. Paladin
  swing timer is swings only. Hunter rotation: Aimed Shot in Steady Shot's place, then Multi-Shot, then Arcane Shot.
  Warrior: vanilla ranks, no Rampage, Slam on a 15 s cooldown, Sweeping Strikes 12292. Swing timers take swings from
  `PLAYER_SWING`. RaidComp buffs and resource presses drop what Forever lacks. Mock: Forever spec info, `C_Traits`
  groups, `PLAYER_SWING`. Every spell id checked against Wowhead Forever. Test `test_forever_class_tools.py`.
- **Demos + art (PR #38):** on Forever every demo (guild, Groups, Guild Map, polls, recruit, Blessings, profiles,
  wardrobe, prized, feedback, group finder, event examples and library) shows Forever content with Forever item ids;
  meters / threat / boss-mod demos hidden; Looks previews use the Seven of BRD and Onyxia; the tour skips Strategies.
  Nav cards, window header, My BiS, Changelog, Feedback banner and PerfUI use vanilla loading screens (FileDataIDs).
  Test `test_forever_demos.py`.
- **Leftovers (PR #39):** BiS import / export on Forever offers only DisasterZone's own format (WoWSims has no Forever
  sim; Wowhead's Forever gear planner exists but its link format is UNVERIFIED), no Jewelcrafting / Inscription or
  Draenei / Blood Elf in the export maps. Paladin demo is a plain swing timer, hunter's names Aimed / Multi-Shot,
  combat-text preview uses a Hand of Justice swing, Azeromon rares name Forever's raids, guild map share says Tanaris /
  battlegrounds, totem and reserves demos use Hyjal Summit. Test `test_forever_export.py`.
- Still TBC, left on purpose or for later: Looks > Boss mods / Meters previews (features hidden on Forever), the
  Azeromon hall's wings and the Steward's Sunwell line, `Data/ItemClasses.lua` (generator needs the TBC setup),
  Karazhan Chess (themed on purpose).
- New note: [[How Sync Works]].

## 2026-11-09 - Secret values: every remaining reader guarded
- `Core/Compat.lua`: `Compat.Plain` (a value, or nil when secret), `Pct`, `HealthPct`, `PowerPct`, `GUID`. Every file
  card [[combat-features-on-forever-apis|Combat features on Forever APIs]] listed now goes through them: BossMod,
  BossLearn, StrategyLive, Meter, MyLog, CombatText (low health / mana), SwingTimer (consecration mana floor),
  WarriorSwing (rage, execute phase, dodge), Totems, Situation, Threat, Loot, StrategyPractice, UI/LookUnits,
  UI/LookTanks, UI/LookAggro, UI/Plates. `BossMod.NpcOf` refuses a secret GUID, which covers its other callers.
- What the player sees on Forever: HP-% boss alerts, the execute phase and the low-health / low-mana warning stay
  quiet; unit frames, tank frames and nameplates show a full bar with no numbers; a mob's name is blank in instances.
- The `UnitBuff` / `UnitDebuff` / `UnitAura` shims answer "no aura" when Forever refuses auras in combat, instead of
  raising (the warrior rotation's first error once health and rage were fixed).
- Test `tests/forever/test_forever_secrets.py` (6/6; 4 cases fail on the old code). `run_all --all`: the 17 known
  failures; `check.py` unchanged.

## 2026-11-09 - New raid: "Pick a raid." whatever was picked (in game)
- In game: New raid > Hyjal Summit > Create raid said "Pick a raid.". The window started every new raid on the
  TBC planner key "kara" (Karazhan), which has no tile on Forever; clicking Hyjal added it as the night's *second*
  raid, and the first ("kara") was refused. `UI/RaidSheet.lua` now starts on the planner's first raid (Barrow Deeps).
  Test `test_the_new_raid_window_creates_the_raid_you_pick` (fails on the old code). Also confirmed in game: the new
  build runs (`DisasterZone.PHASE_WORD` = Season) and the Hall of Thanes combat-text error is gone.

## 2026-11-09 - Demo text a screenshot caught
- The session crest's demo night (`Core/SessionInfo.lua`: "Thursday SSC", 23 of 25), the demo poll, the recruit
  message and recruit cards still said SSC / TK / Karazhan / level 70. On Forever: "Thursday Hyjal", Hyjal Summit, 20
  players, Forever items; Hyjal / Barrow recruit lines; level from `Recruit.MAX_LEVEL`. Test extended (15/15).

## 2026-11-09 - Secret nameplate GUIDs (in-game error, Hall of Thanes)
- In game (Feedback > Yours): `UI/CombatText.lua:376` "attempted to index a table that cannot be
  indexed with secret keys", and the same on assignment, in Hall of Thanes. In an instance a nameplate's `UnitGUID`
  is a secret value; the combat-text plate tracker used it as a table key. Fixed there and in
  `Core/StrategyLive.lua` (same pattern): secret GUIDs are skipped (`Compat.IsSecret`).
- Mock fidelity note: the mock's secrets are tables, which Lua accepts as keys, so it cannot raise this error; the
  new test `test_secret_nameplate_guids_are_never_table_keys` asserts no secret ever becomes a key instead (fails on
  the old code, passes now).
- The reporting client ran the 2026-11-08 build: none of PRs #20-#26 were in it, which is why the
  reserves demo still showed Serpentshrine Cavern. The other errors in the inbox (resource bar, shot timer, keyboard
  in combat) were fixed in PRs #16 / #19.

## 2026-11-09 - The demo guild raids on Forever
- `Core/Demo.lua`: the demo raid log runs Hyjal Summit / Barrow Deeps / Onyxia nights at level 60; bosses without
  encounter ids get stand-in ids, and awards come from level-60 dungeon loot while raid loot is unknown.
- `Core/AuditDemo.lua`: the month's text on Forever raids, items (Loomguard Armbraces, Royal Tribunal Cloak, Blackmaw
  Hold drops ...) and bosses (Gandling, the Wild King); no strategy-board entries. `F(tbc, forever)` keeps the TBC
  month byte-for-byte for its suites.
- `Core/ReserveDemo.lua`: a pug night in Upper Blackrock Spire, General Drakkisath's loot (Magister's Robes for you,
  the Breastplate of Valor and the Flask of the Titans recipe held for the guild).
- `Core/Reserves.lua`: a reserve list may be for a dungeon too (Forever's 10-player UBRS).
- Council demo scenarios: Loomguard Armbraces and a prized Hand of Justice; no tier-token or longest-use case.
- Demo page: no My Log entry on Forever, Onyxia art.
- Test `test_the_demo_guild_raids_on_forever` (14/14). `run_all --all`: 17 known failures.

## 2026-11-09 - Forever crafts, recipes and names (Data/Atlas.lua)
- New `dev/generators/gen_forever_atlas.py`: Forever's `Data/Atlas.lua` from AtlasLoot Classic Forever's CLASSIC
  Profession.lua / Recipe.lua, every item checked on Wowhead Forever: 2,143 crafts (13 dropped), 762 recipes, 12
  craft-for, 8 conversions, 5,233 names; no browse tree (AtlasClassic.lua has the pages); AtlasCosts empty (AtlasLoot
  has no Forever prices; vendors teach them). The TBC file (14.5K lines) moved to `dev/fixtures/tbc/`.
  `AtlasClassic.lua` regenerated after it (no duplicate names).
- Test: Flask of the Titans' craft and breakdown, a recipe, names (`test_forever_content.py` 13/13). `run_all --all`:
  17 known failures.

## 2026-11-09 - Forever Atlas pages, paladins, changelog, combat settings
- `Data/AtlasClassic.lua` regenerated from AtlasLoot Classic Forever (`DZ_FOREVER=1 gen_atlas_classic.py`, Wowhead
  check through `forever_names.ForeverNames`): crafting 2,109 items (12 professions), reputation 139, PvP 462,
  events 109, sets = PvP rank sets only (Tier 1-3, ZG and AQ sets dropped: their raids are not in Forever). The
  Anniversary version moved to `dev/fixtures/tbc/`. Wowhead cache now ~11,000 ids (parallel prefetch).
- Paladin (Wowhead Forever spell database): no Salvation / Light / Sanctuary / Crusader Aura / Symbol of Kings, no TBC
  ranks, blessings an hour; gone blessings keep their Pally Power index with no ranks; the bar hides the symbol count.
- Changelog tab: one Forever release ("2.0.0 DisasterZone for WoW Forever"); the upstream notes moved to fixtures.
- Settings > Combat on Forever: only Class tools (no Meters, Boss mods, Strategy, My Log cards).
- New Forever tests: every page opens with Forever data, also in demo mode; changelog lines; paladin data
  (`test_forever_content.py` 12/12). `run_all --all`: the 17 known failures only.
- Open: the demo's sample guild is TBC-flavoured (Gruul nights, Karazhan loot); `Data/Atlas.lua` still ships for its
  crafts / recipes / names tables (its TBC tree is unused); Zandalar Tribe and Brood of Nozdormu rewards are listed
  though ZG / AQ are not open (whether Forever has those factions is unverified).

## 2026-11-09 - Raid Trainer pack removed
- Decision: Karazhan Chess stays, the Raid Trainer goes (it only had TBC bosses). Deleted
  `addon/DisasterZone_Trainer`, its logo, hub entries, `tools/render_check.py` / `.lua` and three suites; the hub,
  packs, share and slash tests now use Chess as their example game; two strategy-board checks no longer compare
  against Trainer objects. `DisasterZone_Rooms` stays: Chess draws its 3D board from the Karazhan room (slimming the
  pack to that room is open).
- `run_all --all`: 17 known failures, nothing new.

## 2026-11-09 - Forever item data, Seasons, TBC data out of the addon
- Decisions (2026-11-09): "Season" instead of "Phase"; TBC code and data deleted area by area; Illidan pack
  dropped; ForeverDungeonJournal used for facts only; Onyxia loot empty until known; unconfirmed dungeon loot as one
  list; Karazhan Chess kept, Raid Trainer to be dropped (next PR).
- New `dev/generators/gen_forever_data.py`: runs AtlasLoot Classic Forever 1.3.4's own Lua (stubbed API) and writes
  Forever's `Data/Items.lua` (Onyxia 40, Barrow Deeps 10, Hyjal Summit 20: bosses, no loot yet), `Data/Dungeons.lua`
  (35 dungeons, 1,392 items) and `Data/Sources.lua` (482 crafted, 55 reputation, 402 PvP items, no badges). Every
  item checked against Wowhead's Forever tooltip API (`forever_names.py`, cache `data/forever_items.json`): 257
  AtlasLoot ids Forever does not have are left out. New-dungeon loot AtlasLoot lacks:
  `data/forever_dungeon_loot_extra.json` (foreverchanges.pro observed drops for 4 dungeons; client item blocks for 5,
  listed as "Loot (boss not confirmed)").
- Forever `Data/Raids.lua` (raid meta: Barrow / Hyjal / Ony), `Data/Gems.lua` (no sockets or gems; 27 enchants AtlasLoot
  Forever lists, `gen_forever_gems.py`), `Data/BiSLists.lua` (none: Suggest is off until a source settles),
  `Data/Consumables.lua` (level-60 kit; 5 items renamed by Forever, e.g. Elixir of Giants = Elixir of Greater
  Strength).
- TBC data moved to `dev/fixtures/tbc/Data/` (Items, Dungeons, Raids, Sources, BiSLists, Gems, Consumables, SimItems,
  SimAPL, StarterStrategies, EncounterSpawns, RaidMaps, ModelIndex, BossAbilities, BossJournal, BossPortraits,
  GroupQuests, BossMods/*): the harness runs them for TBC-profile clients (`TBC_FIXTURES`, `TBC_FAN_OUT`), so the
  ~2,900 upstream cases keep their fixtures; the addon ships small Forever stubs.
- Hidden on Forever (`ns.FOREVER_HIDDEN`): Gear sim, My Log (no combat log), Raids > Strategies (TBC maps). Groups:
  no Quest kind. Shaman: Totem of Wrath, Wrath of Air and the elementals gone, role tables re-indexed.
- "Season" wording: `ns.PHASE_WORD` / `ns.PHASE_LETTER` ("S1"), 25 labels routed through them.
- The Binding of Illidan pack, its tools and tests deleted.
- Tests: `test_forever_content.py` 10/10; `run_all --all` 307 suites, 17 failed = the known baseline.

## 2026-11-09 - Forever only: phases, Atlas, dungeons, group kinds, recruit, professions
- Goal: a lot of TBC content was still in the app; get it into shape for WoW Forever only. Online research
  (Blizzard posts, Warcraft Tavern, Method, CurseForge API) plus two installed addons as fact sources
  (ForeverDungeonJournal 1.6.6: the 35 dungeons with levels and zones; AtlasLoot Classic Forever 1.3.4: raid boss
  lists, raid loot still empty). Findings in [[Forever Content Facts]].
- One raid phase on Forever: My BiS / council / Settings show Pre-raid + P1 ("Onyxia · Barrow Deeps · Hyjal Summit").
  Stored and received lists still take phases 1-5 (`ns.WIRE_MAX_PHASE`), so a later phase is not refused.
- Atlas: no TBC tree and no Classic | TBC switch on Forever (`Atlas:HasEraSwitch`); it opens on Classic at any level.
- Groups board: Forever's 35 dungeons in 6 level bands (keys from AtlasLootClassic where the dungeon is the same; the 9
  new ones have no loading screen yet), no Heroic switch, no rep keys, no Shattrath dailies, raid level 60. Raid
  groups list Barrow / Hyjal / Ony; PvP is WSG, AB, AV and Darkspear Islands (no arenas, no Outland world PvP);
  "Attunement" gone from Other, hints are vanilla.
- Recruit milestones keep their stored keys (58 / 70) but mean level 40 and 60 on Forever (`Recruit.MILESTONE_LEVEL`).
- Professions: no Jewelcrafting on Forever. Item picker: no "Badge vendors" source.
- New `dev/tests/forever/test_forever_content.py` (5/5), TBC client keeps its lists.

## 2026-11-09 - Keyboard handling blocked in combat (ADDON_ACTION_BLOCKED)
- In game DisasterZone's feedback inbox had `ADDON_ACTION_BLOCKED ... 'Frame:SetPropagateKeyboardInput()'`, "Atlas
  page open, in combat". The function is protected in combat on the modern engine; the Atlas page's set-up calls it
  when the page is built, i.e. the first time it is opened, and here that was during a fight. (The other two inbox
  entries are the secret-value errors fixed in PR #16, sent before that fix.)
- New `Util.SetPropagateKeys(frame, on)`: in combat it skips the call and applies the last value asked for when
  combat ends. All 38 calls in 16 files go through it (no raw call left).
- Mock Forever profile blocks `SetPropagateKeyboardInput` in combat (`__MOCK.blocked`). New
  `dev/tests/forever/test_forever_keys.py` (4/4): every page first opened in combat (fails on the old code with the
  in-game error), keys pressed on every page in combat, the deferred value applied after combat.

## 2026-11-09 - `/dz raiddata` confirmed in game; group finder categories
- In game `/dz raiddata` listed "Upper Blackrock Spire, 10 players, level 0, map 229 (not in the list)": a 10-player
  dungeon, not a raid. The report now shows each group finder activity's category (`C_LFGList.GetLfgCategoryInfo`)
  and flags only the raid category as missing. Mock: `GetLfgCategoryInfo` (2 Dungeons, 114 Raids).

## 2026-11-09 - Secret values: resource bar and shot timer errors
- In game after the restart: recipes now share (Blacksmithing 31, Mining 4, Cooking 9, First Aid 5). DisasterZone's
  error popup came up: `Core/Resource.lua:167` arithmetic on a secret number (2,693 times in one session: every power
  update, even with the bar switched off) and `Core/ShotTimer.lua:155` comparing a secret number (`UnitRangedDamage`).
- Fixed: the resource bar is not live on Forever (its numbers are secret; rebuild on secret-safe widgets is card
  "Combat features on Forever APIs") and its tick tracking skips secret readings; the shot timer falls back to the
  speed it learns from casts.
- Mock: a secret keeps its Lua type like the client (`type()` "number", `tonumber()` returns it), so
  `tonumber(UnitPower(...)) or 0` stays secret; `UnitRangedDamage` is secret. The Deadmines replay now sends power,
  health, aura and cast events during each fight: it reproduced both in-game errors before the fix (5/5 after).

## 2026-11-08 - Raid planner on Forever: its raids, 10/20/40, level 60
- In game the Raids filter listed Karazhan to Sunwell and a new raid said "for level 70 characters". Measured: no
  raid list in the client (Encounter Journal empty; the group finder lists only Warsong Gulch and Upper Blackrock
  Spire, the raids open 9 Dec), max level 60.
- New `Data/ForeverRaids.lua` (loaded on Forever only): Barrow Deeps 10, Hyjal Summit 20, Onyxia's Lair 40, level 60,
  sizes 10/20/40. `Core/RaidPlan.lua` builds its raids, sizes, default size and level cap from it (TBC unchanged);
  `RaidComp` 20/40 auto-fill layouts, presets Standard 40/20/10, comps up to 40, `GroupCount` = size / 5;
  size menus in `UI/RaidPlanUI.lua`, level in `UI/RaidSheet.lua`, party cards in `UI/GroupsLead.lua`.
- New `Core/RaidLearn.lua` + `/dz raiddata`: records raid instances zoned into (name, instance id, size), bosses
  pulled (encounter id, name) and the group finder's raid activities; prints them as `Data/ForeverRaids.lua` entries.
- New `dev/tests/forever/test_forever_raids.py` (5/5); `test_slash` lists `raiddata`; `layers.json` places RaidLearn.

## 2026-11-08 - Recipes on Forever's profession window
- In game: opening Blacksmithing did not share any recipes ("Open your ... window once" stayed). Forever's window is
  the retail one: `GetTradeSkillLine` / the craft window are gone. Measured: `C_TradeSkillUI.GetAllRecipeIDs` (507 ids
  for Blacksmithing, learned or not), `GetFilteredRecipeIDs`, `IsTradeSkillLinked`, `GetRecipeOutputItemData` present.
- `Core/Professions.lua`: a `C_TradeSkillUI` scan (learned recipes only; skips linked/guild/NPC lists) when the old
  functions are missing; also listens to `TRADE_SKILL_LIST_UPDATE` / `TRADE_SKILL_DATA_SOURCE_CHANGED`.
- Mock Forever profile: `C_TradeSkillUI` and `C_SkillInfo` over the existing `M.tradeskill` / `M.skills` model.
  New `dev/tests/forever/test_forever_professions.py` (4/4; the two recipe cases fail on the old code).
- Seen in game too: the Encounter Journal is empty on Forever (`EJ_GetNumTiers()` 0), the group finder lists 76
  activities, max level 60.

## 2026-11-08 - Surname fix confirmed in game
- On the live client with the new build: `Util.PlayerKey()` = `Guild:GetGM()` (full name with surname and realm),
  `IsGM` true, the GM once in the guild members. Client facts: `RegionalUniqueNamesEnabled()` true, every
  `UnitName` variant's second value is the surname, `GetUnitName(unit, false)` also gives the full name.
  Card "In-game check of every page" updated.

## 2026-11-08 - First in-game session with DisasterZone; surname names fixed
- DisasterZone opened on the live Forever client (tour, Home, Raids, Gear/BiS, Groups, Guild roster):
  no Lua errors in its own error log. Works: calendar, raid list, groups, the 3D model on the BiS page, the guild
  roster with spaced names, professions read from the game. TBC content still shows (raid filter lists Karazhan to
  Sunwell, BiS phases P1-P5, item picker finds nothing): card "Forever content data".
- **Bug found and fixed:** Forever names are first name + surname. `UnitName` returns the two parts,
  the roster and message senders the whole name, so the addon keyed the GM by first name only and did not know he was GM
  (Members page showed him twice; his own messages came back as a peer's). New `Util.UnitNameRealm`, used by every
  place a unit becomes a name key (`Core/Util.lua`, `DungeonRuns`, `EventLive`, `BossLearn`, `BiSExport`,
  `UI/EventTracker`, `UI/LookTanks`, `UI/RaidPlanUI`).
- Mock Forever profile: surnames (`UnitName` parts, roster without realm, `RegionalUniqueNamesEnabled`). New
  `dev/tests/forever/test_forever_names.py` (5/5; 0/5 before the fix) with the guild's real names; the Deadmines replay
  now uses them too. `check.py` knows `RegionalUniqueNamesEnabled`.
- Line endings: PR #9 had turned the CRLF `dev/tools/wowmock/ui.lua` into LF; restored. Edits keep each file's endings.
- Probe Findings corrected: the probe ran on the GM's full name (with surname), not the first name alone.

## 2026-11-08 - Docs: testing with Forever data
- New `06-Operations/Testing with Forever Data.md` (probe -> mock facts -> replays loop, the profile table, fixtures);
  `Linux Dev Setup` lists the Forever suites and the current test baseline; `dev/probe/README.md` covers
  `mock_facts.py` and `export_replay.py`.

## 2026-11-08 - Forever mock profile + Deadmines replay
- `wowmock` has a Forever profile (`Client(..., forever=True)`, `dev/tools/wowmock/forever.lua`), built from the probe
  run by `dev/probe/mock_facts.py` -> `forever_facts.lua`: build 1.60.1/16001, the old globals gone, no addon combat
  log, Encounter/Chat restrictions in the client's order, `AddOnMessageLockdown` during pulls, secret unit values,
  auras refused in combat, `TooltipDataProcessor`.
- `dev/probe/export_replay.py` cut the Deadmines clear (9 pulls) into `dev/tests/forever/fixtures/`;
  `dev/tests/forever/test_deadmines_replay.py` plays it through a party of five Forever clients (5/5),
  `test_forever_profile.py` covers the profile and the addon booting on it (7/7).
- **Bug found and fixed:** a multi-part message still queued in ChatThrottleLib when a boss is pulled lost every
  remaining part (153 refused over the 9 pulls; receivers never got it). `Core/Comm.lua` now pauses ChatThrottleLib's
  despooling while the chat lockdown is on.
- Full suite unchanged otherwise (same 17 known failures as before, all environmental/upstream). Merged branches deleted.

## 2026-11-08 - Forever compat layer, first pass
- New `Core/Compat.lua`, all TOCs at Interface 16001, combat log refused on Forever, Comm holds messages through a
  boss pull. New `dev/tests/compat/` (6/6) and `dev/install_forever.sh`.
- Probe round 2 (group/raid checks) built.

## 2026-11-08 - DZProbe full run: findings
- ~4 h run incl. a full Deadmines clear. Results in `dev/probe/results/`, `09-Reference/Forever Client Facts.md`,
  conclusions in `01-Overview/Probe Findings 2026-11-08.md`. Probe card done; round-2 card for group questions.
- Key facts: hotpatch mechanics work; master loot API present; guild roles readable; **all addon messages are
  blocked for the length of a boss pull** (lift on ENCOUNTER_END); unit health/power always secret, target
  name/GUID secret in instances; no combat log; names can contain spaces.

## 2026-11-08 - DZProbe first in-game run
- Probe ran on the live client: 0 errors, 77/77 C_, 252/348 globals, 122/142 events present.
- Registering the combat log is forbidden on Forever (popup every load); probe stopped asking (PR #4).
- Guild roster, GM detection, officer notes and addon messages all work. Full facts note after the long run.

## 2026-11-08 - DZProbe: measure the real Forever client
- New `dev/probe/`: the DZProbe addon (one-shot checks + passive logger of combat/encounter/restriction states),
  `gen_apilist.py` (the 77 C_ functions, 348 globals and 142 events the addon uses), `read_probe.py` (SavedVariables
  -> `09-Reference/Forever Client Facts.md`), `install.sh`, and an offline test with a fake Forever client (27/27).
- Confirmed from the 1.60.1 UI source: master loot is still in `Enum.LootMethod`; `C_RestrictedActions` has six
  restriction types (Combat, Encounter, ChallengeMode, PvPMatch, Map, Chat); `SendAddonMessage` can return
  `AddOnMessageLockdown` (11); Blizzard's own Forever UI never calls `GetGuildRosterInfo`.

## 2026-11-08 - Repo created, deep dive done
- Forked `tsumilo/DisasterZone-dev` @ e21d5a9 with full history (1,223 commits, 22 tags) into this public repo;
  `upstream` remote is fetch-only.
- Deep dive of the original (core, roles, data, tests, UI/API): [[Deep Dive Synthesis]].
- Ran the upstream test suites on Linux: [[Linux Dev Setup]].
- Vault and board with the port plan.
