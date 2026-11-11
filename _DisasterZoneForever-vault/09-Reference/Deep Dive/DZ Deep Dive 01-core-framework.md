# 01 - DisasterZone core framework and networking

Scope: repo layout, boot sequence, namespace/module system, event and message bus, persistence, addon-to-addon comms,
game packs and the Lua conventions a WoW Forever port must keep. All paths are relative to the clone root
`dz-dev/` unless they start with `Core/`, `Libs/` etc., which are under `addon/DisasterZone/`. Read-only study; nothing
in the clone was changed.

## Summary

- DisasterZone (v1.5.5, `## Interface: 20506`, `addon/DisasterZone/DisasterZone.toc:1-5`) is a single large addon
  (~514k lines of Lua across all folders, ~325 Lua files in the main TOC) plus six optional **game packs** and one
  load-on-demand data addon (`DisasterZone_Rooms`). There is no XML; every frame is built in Lua (`dev/docs/SPEC.md:65`).
- The framework is home-grown, not Ace3-addon based: `Core/Init.lua` gives a module registry with `OnInit`/`OnLogin`
  lifecycle in TOC order, one event frame with copy-on-write handler lists, an internal pub/sub bus (`ns:On/Off/Fire`)
  with a declared message catalogue, slash routing and a full error-capture system. Only the comms libraries are Ace
  (AceComm-3.0 + ChatThrottleLib, LibSerialize, LibDeflate).
- A distinctive layer is the **in-game hot-patch boot loader** (`Core/BuildInfo.lua`, `Core/Boot.lua` first;
  `Core/Outbox.lua`, `Core/BootEnd.lua` last). Every other Lua file starts with a line-1 guard that lets a signed patch
  stored in `DisasterZonePatchDB` replace the file's text at load time. This depends on `## LoadSavedVariablesFirst: 1`
  and on `loadstring`.
- Persistence: one main account-wide table `DisasterZoneDB` (schema 2, deep default fill, numbered migrations, per-guild
  buckets) plus five side tables (patch, My Log, meters, boss learning, Discord bridge).
- Comms: 16 own AceComm prefixes `CDLc/CDLd/CDLa/...` (one per traffic class, one CTL priority each), payload =
  `"1"` + LibDeflate-encoded(Deflate(LibSerialize(table))), every message a table with a type field `t`. ~150 message
  types. Sender identity always comes from the transport and is gated on guild/group membership before decoding.
  Convergence uses three patterns: (1) owner-rev BiS lists via HELLO/STATE/MANIFEST/WANT/LIST/RELAY between members and
  the loot council, (2) a generic digest/want/give engine (`DigestSync`) keyed on hashes advertised in the guild HELLO,
  (3) rev-handshake lists (`DigestSync.RevList`). Patches have their own plain-text gossip protocol on `CDLp1..4`.
- For Forever, the transport code is already written against the modern API (`C_ChatInfo.*`, `C_AddOns.*`,
  `C_EventUtils.IsEventValid`, `Enum.SendAddonMessageResult`), so the networking core should port almost unchanged. The
  main risks are TOC directives (`LoadSavedVariablesFirst`), the server's addon-message throttle, and TBC-specific
  constants and data that leak into validators (for example `MAX_ITEM_ID = 200000`).

## Structure map (folder -> purpose)

### Top level

| Path | Purpose |
|---|---|
| `README.md` | Dev-kit README: layout, Windows junction setup, everyday commands, test runner, release flow (`README.md:35-192`). |
| `addon/DisasterZone/` | The live addon (on the author's PC a Windows junction into `Interface\AddOns`). |
| `addon/DisasterZone_Rooms/` | Load-on-demand 3D room data (`## LoadOnDemand: 1`), loaded by `Render3D/Rooms.lua R3.LoadData`. |
| `addon/DisasterZone_{Azeromon,Bingo,Chess,HoldTheLine,Illidan,Trainer}/` | The six game packs (`dev/docs/GAME_PACKS.md`). |
| `dev/` | The workshop: specs, mock client, tests, generators, release tooling. |
| `launcher/` | Tauri desktop launcher (Rust `src-tauri/`, `ui/`), plus `server/` (the guild Discord bot backend) and `proto/` (signed record format shared with `Core/Bridge.lua`). |
| `archive/` | Retired experiments (`delve`, `murloc-defense`). |
| `tf_e/` (root) | Stray UI audit renders (`ui_teams*` PNGs); the real runner lives in `dev/tf_e/`. |
| `.github/readme/` | README art only (no CI workflows here; launcher CI is under `launcher/ci`). |

### Inside `addon/DisasterZone/`

| Folder | Purpose |
|---|---|
| `Core/` | Everything that is not UI: platform (Boot, Init, Util, DB, Comm, Sync), context (Guild, GroupRules, ItemDB) and today all feature logic (Loot, Roll, RaidPlan, Events ...). The planned move to `Logic/`, `Sync/` (`dev/docs/ARCHITECTURE_PLAN.md`, P4) has not happened in this snapshot: the TOC still lists a flat `Core/`. |
| `Data/` | Generated game data (items, raids, dungeons, sources, BiS lists, boss mods, atlas). Written by `dev/generators/*.py`; paths are fixed. |
| `Sim/` | Lua port of WoWSims TBC (gear sim). |
| `Render3D/` | 3D room renderer shared by the strategy board and the Raid Trainer. |
| `UI/` | All windows, kit components (`UI/Comp/*`), HUDs, Edit Mode integration. |
| `Games/` | Only the hub (`Hub.lua`, `HubUI.lua`); the games themselves are packs. |
| `Libs/` | Embedded LibStub, CallbackHandler, AceComm-3.0 (MINOR 14) + ChatThrottleLib (v32), LibSerialize (6), LibDeflate, LDB, LibDBIcon, LibCustomGlow. |
| `Media/` | Core art (`ns.MEDIA`, `Core/Init.lua:8`). |
| `Bindings.xml` | Key bindings (the only XML). |

### Inside `dev/`

| Folder / file | Purpose |
|---|---|
| `docs/` | `SPEC.md` + `SPEC_ADDENDUM_A..J.md` (feature design, numbered sections continue), `ARCHITECTURE_PLAN.md` (layers, hard rules), `MODULES.md` (generated module/API map), `REFACTOR_PLAN/API.md` (UI kit contract), `GAME_PACKS.md`, `HOTPATCH.md`, `research/` (`api.md` = verified 2.5.6 API notes, `sync.md` = original sync design), `impl/` (phase reports), feature folders. |
| `tools/` | `check.py` (static checker: syntax, stray globals, unknown APIs vs `known_globals.json`, `--layers`, uniformity), `harness.py` + `wowmock/` (Lua 5.1 WoW client mock run through lupa), `release.py` + `patchlib.py` (full releases, signed patches, guards), `layers.json` / `layers_allow.json` / `layers.py`, `packs.py`, `testmap*.py` (change-based test selection), `move.py`, `modules_doc.py`, UI audit tools. |
| `tests/` | ~69 area folders of scenario suites (`tests/<area>/test_*.py`). |
| `tf_e/` | `run_all.py` parallel runner; outputs git-ignored. |
| `generators/` | ~106 data/art generators (items, atlas, Azeromon art, rooms, encounter assets). |
| `releases/` | Per-version release manifests (`0.10.0.json` .. `1.5.5.json`, `patches.json`, `published.json`). |
| `thirdparty/` | LootReserve sources (reference for the `ReserveLR` interop). |
| `data/`, `art/`, `render_baseline_v2/` | APL data for the sim, source art, render baselines. |
| `find_multiret.py`, `requirements.txt` | `tonumber(<multi-return>)` hazard scan; `lupa==2.8`. |

### TOC load order (`addon/DisasterZone/DisasterZone.toc`)

1. Header (`:1-11`): `Interface 20506`, `Version 1.5.5`, `X-CDL-Protocol: 1`, six `SavedVariables`,
   `LoadSavedVariablesFirst: 1`, `OptionalDeps: CDLoot, DisasterZone_Bridge`, `IconTexture`, `Category: Raid`.
2. Boot loader (`:13-15`): `Core\BuildInfo.lua`, `Core\Boot.lua`. Must stay first (they never run through a guard).
3. Embedded libraries (`:17-26`).
4. Platform core (`:29-35`): `Init`, `Util`, `Perf`, `Sha256`, `Dungeon`, `GroupRules`, `Constants`.
5. Game data `Data\*.lua` (`:36-72`), then `Core\ItemDB.lua` and `Core\DB.lua` (`:73-74`). DB comes after ItemDB so
   `ns.db` exists before any later module's `OnInit` (`Core/Init.lua:761-762`).
6. Context and sync core (`:75-87`): `Guild`, `BiS`, `Gems`, `Store`, `Notify`, `Comm`, `Layout`, `Profiles`, `Sync`,
   `DigestSync`, `Audit`, `AuditKinds`, `Professions`.
7. Gear sim `Sim\*.lua` (`:89-114`).
8. Feature logic `Core\*.lua` (`:116-216`): Bridge, Patch, Ledger, RaidLog, combat, class tools, raids, events, loot,
   reserves, demo.
9. `Render3D\*` (`:219-224`), `UI\*` (`:227-363`), `Games\Hub*.lua` (`:366-367`).
10. `Core\Outbox.lua`, `Core\BootEnd.lua` (`:370-371`). Must stay last: `BootEnd` runs patch files that were added after
    every disk file (`Core/Boot.lua:283-296`).

Order matters because modules register in TOC order and lifecycle dispatch follows that order
(`Core/Init.lua:378-411`). Files at load time only build tables and register; real work happens in `OnInit`
(at `ADDON_LOADED`) and `OnLogin` (at `PLAYER_LOGIN`).

## Boot and module system

### Boot sequence

1. **`Core/BuildInfo.lua`** (`:7-10`): global `DisasterZoneBuild = { id = "dev", assetPack = 17 }`. `release.py`
   stamps the real build id (and `packs = { [folder] = stamp }`) when packaging. `assetPack` gates code that needs newer
   art (`ns:HasAssets(n)`, `Core/Init.lua:27-29`).
2. **`Core/Boot.lua`** (global `DisasterZoneBoot`, also `ns.Boot`, `:22-24`):
   - Adopts `DisasterZonePatchDB` at file time (`:42-62`); records `Boot.svFirst` = whether saved variables were
     readable before files ran.
   - Goes **dormant** if the old addon CDLoot is loaded (`:64-77`), offering a data import (`:488-587`).
   - `Decide()` (`:152-213`) validates the stored patch: same build id, Adler-32 per file, every file compiled with
     `loadstring` before anything runs. Produces `plan[path] = fn | SKIP`, `extras` (new files before an anchor),
     `tail` and `packTail`.
   - `Boot.Run(path, ...)` (`:261-279`) is what every line-1 guard calls: returns true when the caller must stop (patched
     text ran instead, file deleted, safe mode, dormant, stale game pack).
   - Errors in patched code put the addon in **safe mode** for the session and mark the patch bad (`:234-256`).
   - `/dzpatch` (`:701-704`) works in any state.
3. **`Core/Init.lua`** sets up `ns` (below), registers `ADDON_LOADED` and `PLAYER_LOGIN` (`:806-819`):
   - `ADDON_LOADED(DisasterZone)` -> `RunInit()` -> every module's `OnInit` in order (`:758-771`); if already logged in
     (LoD), also `RunLogin()`.
   - `PLAYER_LOGIN` -> `RunLogin()` -> every module's `OnLogin` (`:773-780`), then `Boot.LifecycleDone()` reports
     startup errors of a running patch.
4. **Game packs** load after DisasterZone; their last file calls `ns:PackLoaded(folder, ns)` which runs `OnInit` /
   `OnLogin` for the modules they added (`:787-804`).
5. **`Core/BootEnd.lua`** (`:3`) calls `DisasterZoneBoot.End(...)`.

### Namespace (`ns`) conventions

- Every file: guard on line 1, then `local addonName, ns = ...` (`Core/Init.lua:1-4`).
- `DisasterZone = ns` is the only debugging global (`Core/Init.lua:6`). Game packs alias their private namespace onto it
  with a metatable (`addon/DisasterZone_Chess/Load.lua:5-9`), so `ns.X` and `ns:NewModule` work identically in packs.
- Fields on `ns`: `name`, `MEDIA`, `version` (patch version if a patch runs, else TOC `Version`), `diskVersion`,
  `assetPack`, `PROTO = 1` (wire major, mirrors `X-CDL-Protocol`), `initialized`, `loggedIn` (`Core/Init.lua:7-17`).
- Plain helper tables (no lifecycle) hang off `ns` directly: `ns.Util`, `ns.Codec`, `ns.Sha256`, `ns.DigestSync`,
  `ns.Style`, `ns.UI`. Lifecycle modules come from `ns:NewModule("Name")`.
- Module names never change (`ARCHITECTURE_PLAN.md`, hard rules): tests and other files call modules, not files.

### Module system

- `ns:NewModule(name)` (`Core/Init.lua:380-391`) creates `ns[name] = { name = name }`, errors on duplicates, appends to
  the ordered list. Optional `M:OnInit()` and `M:OnLogin()` are called through `SafeCall`; a failure while a patch runs
  increments `Boot.startupErrors` (`:402-411`).
- `SafeCall` (`:58-91`) = `xpcall` that forwards varargs without garbage; the handler is resolved per call.
- Error capture (`:94-331`): DisasterZone's own Lua errors never show on screen. They are routed to a sink set by
  `Core/Feedback.lua` (`ns:SetErrorSink`, `:308-311`) that reports them to the developer over comms. Works with or
  without BugGrabber (wraps `seterrorhandler`, or hooks `EventRegistry` "BugGrabber.BugGrabbed").

### Event bus (game events)

- One hidden frame; `ns:RegisterEvent(event, fn)` / `ns:UnregisterEvent` (`Core/Init.lua:417-472`). Handler lists are
  replaced, never mutated, so dispatch can iterate safely. Handler signature: `fn(event, ...)`.
- **Unknown events are skipped, not errors**: `C_EventUtils.IsEventValid` is checked first (`:421-426`) and the
  `RegisterEvent` call is wrapped in `pcall` (`:443`). This is a big help for a port to a client with a different
  event set.
- Dispatch stops completely in safe mode (`:477`).

### Internal message bus

- `ns:On(msg, fn)`, `ns:Off`, `ns:Fire(msg, ...)` (`Core/Init.lua:604-639`), copy-on-write lists, handlers via
  `SafeCall`. ~110 message names are declared in `KNOWN_MESSAGES` (`:491-594`); unknown names only produce a debug note.
- Layering rule: lower layers talk upward only through `ns:Fire` messages, ports (`ns.Ask`, `ns.Nav`) and registries
  (`ARCHITECTURE_PLAN.md`, "Target layers").

### Slash commands, output, trail

- `/dz`, `/disasterzone`, `/cdl`, `/cdloot` (`Core/Init.lua:733-739`); modules add subcommands with
  `ns:RegisterSlash(sub, fn, help)` (`:678-683`).
- `ns:Print`, `ns:Debug` (debug gated on `db.settings.debug`), `ns:Trail` ring of the last 12 user steps for error
  reports (`:647-670`).

### Util (`Core/Util.lua`) and Constants (`Core/Constants.lua`)

- Util: name keys (`NormalizeName` always returns `Name-Realm`, `:39-54`; `PlayerKey`, `IsMe`, `ShortName`), timers
  (`After`, `Debounce`, `RandomDelay` on `C_Timer`, `:189-260`), `Canonical` deterministic serializer + `Hash` =
  Adler-32 of the canonical form as 8 hex (`:328-416`; DigestSync and records use it for cross-client tie breaks), group
  tracking `Util.group` refreshed on `GROUP_ROSTER_UPDATE` etc. and firing `GROUP_UPDATED` (`:563-783`), group channel
  choice (`GetGroupChannel`: RAID, or PARTY with dungeon mode, `:769-773`). Loot method via `C_PartyInfo.GetLootMethod`
  vs `Enum.LootMethod.Masterlooter` (`:569-578`).
- Constants: own slot ids 1..17, phases 1..5 (+ pre-raid 0), TBC class list, specs, roles, professions, TBC armor and
  weapon proficiencies at level 70 (`:337-385`), `ns.MAX_REV`.

### Other platform pieces

- `Core/Perf.lua`: developer performance page; hooks `ns.PerfProbe/PerfNote/PerfNet/PerfComm/PerfTimer` used by Init,
  Util and Comm.
- `Core/Notify.lua`: notification center (registry of kinds and sources).
- `Core/Sha256.lua`: SHA-256 on the client `bit` library; used only for patch authentication.
- `Core/Codec.lua`: **not a wire codec** - JSON / base64 / CSV for BiS import/export of pasted text (`Core/Codec.lua:2-3`).

## Persistence

### SavedVariables (`DisasterZone.toc:7`), all account wide (no `SavedVariablesPerCharacter`)

| Variable | Owner | Shape |
|---|---|---|
| `DisasterZoneDB` | `Core/DB.lua` | Main table, schema 2. Defaults at `Core/DB.lua:14-164`. |
| `DisasterZonePatchDB` | `Core/Boot.lua`, `Core/Patch.lua` | `active` patch (seq, version, base, files, sums, list), `bad`, `off`, `tryOnce`, `lastLoad` (`Core/Boot.lua:152-213`). |
| `DisasterZoneLogDB` | `Core/MyLog.lua` | `{ v = 1, chars = {} }`, own file, never synced (`Core/MyLog.lua:24,100-161`). |
| `DisasterZoneMeterDB` | `Core/Meter.lua` | `{ v = 1, segs, specs }`, reset when `v ~= 1` (`Core/Meter.lua:134-137`). |
| `DisasterZoneBossLearnDB` | `Core/BossLearn.lua` | learned boss timers, account wide (`Core/BossLearn.lua:22,131`). |
| `DisasterZoneBridgeDB` | `Core/Bridge.lua` | `{ applied, loaded, inbox, snap }`, read/written by the launcher between sessions (`Core/Bridge.lua:6,21-23`). |

### `DisasterZoneDB` layout (main keys, `Core/DB.lua:14-164`)

- `schema`, `settings` (alerts, roll, reserves, dungeon, picker sources, meters, class tools `swing/shot/war/power/
  bless`, map sharing, strategy helpers, `windows`, `debug`).
- Per character: `chars[nameKey]` (own BiS record), `raidplanSpec`, `mybisPreRaid`, `gemQuality`, `strategyDraft`,
  `shopping`, `simRuns`.
- Synced caches: `lists` (other players' BiS, council only), `ledger` (awards), `peers`, `council`, `raids` (raid log),
  `raidplan[guildKey]`, `prof[guildKey]`, `games`, `dropHistory`, plus per-guild buckets created lazily by modules
  (`events`, `polls`, `prized`, `strategy`, ...).
- `DB:GuildBucket(key, create, guildKey)` (`Core/DB.lua:384-406`) is the standard "this guild's saved table": keyed by
  `"Guild Name-Realm"`, nil until the guild key is known (fires `GUILD_KEY_READY` later).

### Init, defaults and migrations

- `DB:OnInit` (`Core/DB.lua:239-267`): creates the table, publishes `ns.db` first, deep-fills defaults without
  overwriting (`FillDefaults`, `:217-233`; replaces a non-table where a table is expected), runs `MIGRATIONS[n]` from
  the saved schema up to `SCHEMA = 2` (`:12, :167-177`), warns and leaves data alone when the saved schema is newer, and
  always runs the idempotent `CleanupGuildInfo` (`:191-202`).
- Policy (`ARCHITECTURE_PLAN.md` D8): other migrations stay lazy in the module that owns the data; no new top-level
  saved tables, no reshaping keys.
- Settings access by dotted path: `DB:GetSetting`, `DB:SetSetting` (fires `SETTINGS_CHANGED`), `DB:GetDefault`, and
  `DB:GetEffective` which substitutes the group loot authority's values for the group-rule paths (`:357-373`).

### Store and Profiles

- `Core/Store.lua`: the council cache of other players' BiS lists (`db.lists`), strict validation of incoming list data
  (caps `MAX_ITEM_ID = 200000`, `MAX_NODES = 1500`, `MAX_DEPTH = 4`, rev jump bound, `:14-25`), the
  "who wants item X" index, manifest + manifest hashes for Sync (`:485-517`), lock-change detection, pruning of former
  members after 30 days and of raid-scope copies after a raid session.
- `Core/Profiles.lua`: UI profiles (looks / layout / keys) stored under `db.layouts` via `Core/Layout.lua`; per-character
  and per-spec profile assignment; shared with `LAYQ` / `LAYP` messages (`Core/Layout.lua:995-996`).

## Comms protocol

### Transport (`Core/Comm.lua`)

- AceComm-3.0 embedded into `Comm` (`:13-19`). One prefix per traffic class, one CTL priority per prefix
  (`:37-45`):

| Class | Prefix | Priority | Carries |
|---|---|---|---|
| ctrl | CDLc | NORMAL | HELLO/STATE/WANT, queries, small control |
| data | CDLd | BULK | lists, relays, digests, records |
| alert | CDLa | ALERT | drops, rolls, group rules, raid kills |
| game | CDLg | BULK | minigames |
| member | CDLm | BULK | professions and recipes |
| live | CDLl | NORMAL | strategy presence/edits, digest claims |
| walk | CDLw | NORMAL | 3D room positions (~1/s) |
| run | CDLr | NORMAL | dungeon runs board |
| event | CDLe | NORMAL | live events state |
| eventmsg | CDLf | ALERT | live event banners/sounds |
| map | CDLq | NORMAL | guild map positions |
| craft / craftev | CDLx / CDLy | NORMAL | Disastercraft world / combat |
| fb | CDLb | BULK | feedback and auto error reports |
| boss | CDLk | BULK | boss-learn pulls |
| audit | CDLz | BULK | audit log council <-> GM |

- Other prefixes outside Comm: patches `CDLp1` (control) + `CDLp2..4` (data, plain text, GUILD only,
  `Core/Patch.lua:12-23,43-44`); LootReserve interop `LootReserve` + `LootReserve1..40` (`Core/ReserveLR.lua:25,432-433`);
  Pally Power `PLPWR` (`Core/Blessings.lua:31`) and ShamanPower-style `SHPWR` (`Core/Totems.lua:32`) via CTL directly
  (`Core/ClassPlanner.lua:231-245,337`); DBM `D5` and `BigWigs` for pull/break timers (`Core/BossMod.lua:32,994-997,1092-1096`).
- **Encoding** (`:101-113`): `tostring(ns.PROTO) .. LibDeflate:EncodeForWoWAddonChannel(Deflate(LibSerialize(msg)))`.
  If the payload would inflate more than 16:1 it is padded with an incompressible `_f` field so receivers accept it.
- **Caps**: wire 24000 bytes for council/large senders, 4000 for members; inflated 200000 / 16384; inflate ratio 16 +
  2048 slack (`:48-58`). A sender whose payload trips the inflate cap is ignored for the session (`:333-343`).
- **Routing** (`CheckRoute`, `:185-202`): WHISPER only to a guild member seen online or a real group member; GUILD needs
  `IsInGuild()`, RAID `IsInRaid()`, PARTY `IsInGroup()`. `Comm:SendToCouncil` whispers one encoding to every online
  council peer (`:238-264`). Backlog per class tracked from AceComm's per-part callback (`:157-182`); modules use it to
  let an idle client answer first.
- **Receive** (`OnCommReceived`, `:445-481`): normalize sender, drop own, size check, then the **sender gate before
  decoding**: GUILD/WHISPER need guild membership (else held up to 60 s / 40 messages while the roster loads, ranked
  ctrl > data > other, `:401-443`); cross-guild group whispers allow only `RT` (`:310`); RAID/PARTY need a real group
  member. `Dispatch` (`:317-383`) checks the protocol major (first byte), picks caps by council status or `AllowLarge`,
  decodes in `pcall`, checks the handler and calls `handler(senderKey, msg, distribution)` through `SafeCall`.
- "No player named X" system messages caused by our whispers are filtered and mark that member offline (`:494-506`,
  `:523-530`).
- Rate limiting: `Comm:RateLimit(key, seconds)` (`:294-302`) used everywhere for reply caps; CTL does the bandwidth
  shaping (800 CPS, 4000 burst, `Libs/AceComm-3.0/ChatThrottleLib.lua:60-63`). The research notes record the server
  rule of 10 messages burst then 1/s per prefix for GUILD/RAID/PARTY (`dev/docs/research/api.md:212-216`), which is why
  traffic is split across many prefixes.

### Convergence patterns

1. **BiS lists (Core/Sync.lua)**: the owner is the only writer; a list carries an owner rev, highest rev wins, the owner
   never accepts another copy except an explicit restore (`dev/docs/research/sync.md` summary; `Core/Sync.lua:1-9`).
   Login HELLO on GUILD after 8-20 s (`:931-940`) carries `r` (own rev), `v`, `n` (session nonce), `cg` (council list
   rev) and, for council, `c`, `m` (manifest), `mh` (hashes), `ld` (ledger digest), `rd/rd2` (raid log digests)
   (`:431-461`). Council replies `S` by whisper (queued, `STATE_GAP` 2 s); owners push `L` when the council's rev is
   older; council pairs exchange `M`, pull with `W`, answer with `R` (8 entries each). A 10-minute periodic manifest
   exchange between guild council members (`:988-997`, `:1094-1098`). Raid-scope council gets lists only while a raid
   session runs with loot council (`:105-129`).
2. **DigestSync engine (Core/DigestSync.lua)**, used by Events (`EV`), Polls (`PL`), Prized (`PZ`), RaidPlan (`RP`),
   Strategy (`SB`): each module puts a hash of its digest in the HELLO (`helloField`). A member with a different hash
   answers once per 20 s round after a random delay (later when its data queue is busy): `XXK {to}` claim on `live`,
   then `XXD {to, h, d}` on `data`. The newcomer takes the first digest only, asks `XXW {w}` by whisper and is given
   `XXG` items; live edits go out as `XXU`. Records: higher `rev` wins, equal rev settles on the larger `Util.Hash`
   (`:98-102`). Deletions are tombstones ("graves") kept in the digest for `tombKeep`, then hidden (`:252-335`).
3. **RevList (DigestSync.RevList, `:479-515`)**: a whole list kept by a few writers with one rev in the HELLO; a writer
   with a newer list sends it, a member with an older one asks the writer (`BLQ`, `GNQ`, `RLQ`, `DCQ`).
4. **Bucket digests** (`:520-550`): Ledger by day, raid log by week (`LW/LG`, `RLW/RLG/RLD`).
5. **Patch gossip** (`Core/Patch.lua:12-23`): `A:<seq>:<build>:<n0>` announce, `W:` ranges wanted, `C:` 236-byte chunks;
   one holder streams, everyone listens; trust only via the W-OTS/Merkle signature.

### HELLO field registry (`Sync:RegisterHelloField`, `Core/Sync.lua:418-429`)

| Field | Order | Module |
|---|---|---|
| pd | 10 | RaidPlan digest hash |
| blr | 20 | raid blacklist rev (RevList) |
| gnr | 30 | guest book notes rev (RevList) |
| sd | 40 | Strategy digest hash |
| ed | 50 | Events digest hash |
| od | 60 | Polls digest hash |
| zd | 70 | Prized digest hash |
| rlr | 80 | raid leaders rev (RevList, `Core/Guild.lua:1840`) |
| av | 90 | accounts hash (`Core/Guild.lua:1927`) |
| dcr | 95 | Discord links rev (`Core/Bridge.lua:349`) |

### Message catalogue

Channel/class columns come from the send sites found in the code; "-" means the send site was not on one line or the
handler is generic. Sender gates: see each handler; the global gate in `Comm.lua` always applies first.

| Type(s) | Module (handler site) | Channel / class | Purpose |
|---|---|---|---|
| H | Sync (`Core/Sync.lua:1045`) | GUILD / ctrl | HELLO: rev, version, nonce, council manifest + digests, module hello fields |
| S | Sync (`:1046`) | WHISPER / ctrl | STATE: council's cached rev + hash of your list |
| M | Sync (`:1047`) | WHISPER / ctrl | MANIFEST between council members (+ `q` = answer me) |
| W | Sync (`:1048`) | WHISPER / ctrl | WANT up to 40 names; `{me}` = restore |
| L | Sync (`:1049`) | WHISPER / data | owner's own LIST to a council member |
| R | Sync (`:1050`) | WHISPER / data | RELAY of cached lists (8 per message) |
| CG, CQ, CR, CRQ | Guild (`Core/Guild.lua:1913-1916`) | ctrl (CRQ on RAID) | guild council list / query, raid council list / query |
| RLL, RLQ | Guild (`:1919`, RevList) | ctrl/data | raid leaders list |
| ACB | Guild (`:1920`) | GUILD / ctrl, data | accounts: characters of one player share roles |
| GS, GQ, GSQ, GSA, GSP | GroupRules (`Core/GroupRules.lua:1369-1373`) | RAID/WHISPER / alert | group loot rules, query, session ask/answer, plan request |
| DM | Dungeon (`Core/Dungeon.lua:397`) | PARTY | legacy dungeon mode switch |
| D, LT | Loot (`Core/Loot.lua:1459-1460`) | RAID / alert | DROP broadcast; DE/bank hand-out by a non-council master looter |
| RS, RR, RE, RW, RT, RV | Roll (`Core/Roll.lua:2820-2825`) | RAID (RT WHISPER) / alert | roll start, response, end, win, tiers, council vote |
| A, LW, LG | Ledger (`Core/Ledger.lua:1202-1204`) | WHISPER / ctrl, data | award, ledger want by day, ledger entries |
| RLW, RLG, RLD, RLK | RaidLog (`Core/RaidLog.lua:1603-1606`) | ctrl/data, RLK RAID alert | raid log want/give/digest, boss kill |
| ATM, ATY, ATQ, ATR | Attendance (`Core/Attendance.lua:1758-1761`) | WHISPER ctrl/data | attendance mark, reason, ask, answer |
| RPU/RPD/RPK/RPW/RPG + RPS, RPA, RPH, BLL/BLQ, RTW | RaidPlan (`Core/RaidPlan.lua:386,1888,4251-4255`) | GUILD/WHISPER | raid plan digest engine, sign-ups, alt sign-ups, host sign-ups, blacklist, live lineup |
| EVU/EVD/EVK/EVW/EVG | Events (`Core/Events.lua:103`) | DigestSync | events library/calendar |
| EVS, EVH, EVQ, EVF, EVM | EventLive (`Core/EventLive.lua:2152-2157`) | GUILD/WHISPER, event / eventmsg | live event state (large), heartbeat, query, facts, host messages |
| PLU/PLD/PLK/PLW/PLG, PLN | Polls (`Core/Polls.lua:100,1085`) | DigestSync; PLN GUILD ctrl | polls, nudge |
| PZU/PZD/PZK/PZW/PZG | Prized (`Core/Prized.lua:98`) | DigestSync | prized items rules |
| SBU/SBD/SBK/SBW/SBG | Strategy (`Core/Strategy.lua:305`) | DigestSync, large | strategy boards |
| SBP, SBJ, SBS, SBO, SBC, SWK, SWL | StrategyCollab (`Core/StrategyCollab.lua:1304-1312`) | live / walk | presence, join, snapshot, ops (large), selection, 3D walk |
| GNL, GNQ | GuestBook (`Core/GuestBook.lua:252,896`) | RevList | guest notes |
| RVS, RVQ, RVR | Reserves (`Core/Reserves.lua:766-768`) | RAID / ctrl | soft reserves list, ask, request |
| RC, RCI, RCX, RCR | Recruit (`Core/Recruit.lua:1331-1334`) | - | recruit people, index, remove, team news |
| RCN, RCNA, RCQ, RCT, RCW, RCTA | RecruitIntro (`Core/RecruitIntro.lua:307-312`) | - | recruit intros and Q&A |
| RCP | RecruitMessage (`Core/RecruitMessage.lua:770`) | WHISPER / data | recruit post |
| ON, ONI | OfficerNotes (`Core/OfficerNotes.lua:199-200`) | - | officer notes, index |
| PFB, PFR, PFI, PFW, PMU | Professions (`Core/Professions.lua:1645-1649`) | member | batches, recipes, index, want, unlock |
| MP, MQ, MX | GuildMap (`Core/GuildMap.lua:568-570`) | GUILD / map | position, ask, stop |
| MH | Materials (`Core/Materials.lua:412`) | alert | material holdings |
| MTO | Tanks (`Core/Tanks.lua:213`) | RAID / alert | main tank order |
| LAYQ, LAYP | Layout (`Core/Layout.lua:995-996`) | WHISPER ctrl/data | ask for / send a UI profile |
| DRP, DRQ, DRS, DRL, DRX, DRJ, DRC, DRA, DRH, DRR | DungeonRuns (`Core/DungeonRuns.lua:3067-3076`) | run | dungeon run board |
| AUE, AUD | Audit (`Core/Audit.lua:603-604`) | audit | audit entries, digest |
| BL | BossLearn (`Core/BossLearn.lua:51,1337`) | boss | boss pull data |
| DCL, DCQ, DZR, BDA | Bridge (`Core/Bridge.lua:349,479-485`) | data (large), BDA ctrl | Discord links, signed record relay, BiS ack |
| FBH, FBI, FBQ, FBC, FBP, FBPH | Feedback / FeedbackPlan | fb | feedback items, queries, plan |
| BG, BGQ | Bingo pack (`addon/DisasterZone_Bingo/Bingo.lua:583-584`) | game | bingo |
| CHL, CHQ, ... | Chess pack (`addon/DisasterZone_Chess/Chess.lua:852`) | GUILD / game | chess |
| BIA, BIQ, BIR, ... | Illidan pack (`addon/DisasterZone_Illidan/Board.lua:214`) | GUILD / game | Illidan game board |
| HLA, HLF, HLQ, HLR, ... | HoldTheLine pack (`addon/DisasterZone_HoldTheLine/Social.lua:406`) | GUILD / game | scores and social |
| AZP, AZL, AZS, AZQ, AZN, AZC, AZA, AZG, AZF, AZM, AZW, AZV, AZT, AZK | Azeromon pack (`Net.lua:322`, `GuildBoard.lua:451`, `PvP.lua:568`, `Watch.lua:143`, `Trade.lua:735`, `Chat.lua:201`) | game | presence, board, PvP, watch, trade, chat |
| (patch) A, W, C | Patch (`Core/Patch.lua:12-23`) | CDLp1..4, GUILD, plain text | in-game update gossip |

Note: SPEC's original table (`dev/docs/SPEC.md:401-415`) documents H, S, M, W, L, R, D, A, LW, LG; everything else
was added by addenda and later features. Wire formats are frozen by rule (`ARCHITECTURE_PLAN.md`, hard rules): never
change types, fields, order, 6-hex hashes, tie breaks or the class/prefix of a message.

## Game packs (how a pack plugs in)

From `dev/docs/GAME_PACKS.md` and the Chess pack:
- Separate addon folder `DisasterZone_<Game>` with `## Dependencies: DisasterZone`, `X-DZ-Pack` (game id), `X-DZ-Kind:
  game`, `X-DZ-Build` (release stamp), CRLF TOC (`addon/DisasterZone_Chess/DisasterZone_Chess.toc`).
- `Load.lua` first: metatable onto `DisasterZone` so the pack shares the core namespace, then
  `DisasterZoneBoot.CheckPack(folder)` compares the TOC stamp (read via `C_AddOns.GetAddOnMetadata`) with
  `DisasterZoneBuild.packs` (`Core/Boot.lua:302-327`). A mismatched pack is skipped whole (every guard returns true).
- Game files carry folder-qualified guards (`DisasterZone_Chess/Chess.lua`), make modules with `ns:NewModule`, register
  comms types on the shared `Comm` (class `game`), and register with the hub (`Games:Register`, `Games.CATALOG` in
  `Games/Hub.lua`).
- `Done.lua` last: `DisasterZone:PackLoaded(...)` runs patch tail files for the pack, then `OnInit`/`OnLogin` for its
  modules (`Core/Init.lua:787-804`).
- Not load-on-demand: packs load at login so they can listen on GUILD. The core nil-checks anything a pack provides.

## Conventions

- **Line-1 guard** on every Lua file except the four boot files:
  `if DisasterZoneBoot and DisasterZoneBoot.Run("<path>", ...) then return end` followed by a short description on the
  same line (`dev/tools/release.py:302-304`; `release.py guards check|add`). Pack paths include the folder. The four
  boot files (`BuildInfo`, `Boot`, `Outbox`, `BootEnd`) never move or change.
- After the guard: `local addonName, ns = ...`; header comment (planned module contract header format in
  `ARCHITECTURE_PLAN.md`, "Module contract header"; `MODULES.md` says 0 files have it yet).
- **Lua 5.1 only**: no `goto`, no `//`, `unpack` not `table.unpack`; at most 200 locals per function and 60 upvalues per
  closure, checked on bytecode (`SPEC.md:56`, `ARCHITECTURE_PLAN.md` hard rules).
- **Globals**: only `DisasterZone`, the SavedVariables, `SLASH_*`/`SlashCmdList` fields, `StaticPopupDialogs`
  entries `DISASTERZONE_*`, and frames named `DisasterZone*` (`SPEC.md:57`). `check.py` reports stray globals and
  unknown client APIs, using `dev/tools/known_globals.json` (2693 globals, 773 C_ fields, 381 events harvested from
  20 installed 2.5.6 addons) plus hand-verified `EXTRA_KNOWN*` sets (`dev/tools/check.py:58,128-163`).
- **API rules for 20506** (`SPEC.md:58`, `research/api.md` §11): `C_Item.*`, `C_Container.*`, `C_ChatInfo.SendAddonMessage`
  via AceComm, `C_ChatInfo.SendChatMessage` with fallback, `C_GuildInfo.GuildRoster()`, `C_PartyInfo.GetLootMethod()`,
  `ChatFrameUtil.*`, `Settings.*`, `BackdropTemplate`, `SetResizeBounds`. Never bare `SendAddonMessage` /
  `RegisterAddonMessagePrefix` (another addon defines global shims, `research/api.md:239`).
- **Name keys** are always `Name-Realm` via `Util.NormalizeName`; sender identity only from the transport.
- **No OnUpdate polling** except short animations; use `C_Timer` and `Util.Debounce` (`SPEC.md:62`). Keep load-time code
  to table set-up (test selection reruns every suite for top-level side effects, `README.md` "How run_all stays fast").
- **Layers** (`dev/tools/layers.json`): 0 Platform `Core/`, 1 Game data `Data/`, 2 Context, 3 Feature logic + `Sim/`,
  4 Sync, 5 UI + `Render3D/`, 6 Games + `DisasterZone_*`; per-file overrides for today's flat `Core/` (e.g.
  `Core/Guild.lua` = 2, `Core/Store.lua` = 3, `Core/Comm.lua`/`Sync.lua`/`DigestSync.lua` = 4); a file may call its own
  layer and below; `layers_allow.json` is an allowlist that only shrinks; `"wire"` marks Comm/DigestSync calls for the
  logic-plus-wire report (`layers.json:185-188`).
- **Demo mode** must keep working for every feature: made-up data, nothing sent (`DigestSync` `Engine:Send` returns
  false in demo, `Core/DigestSync.lua:105-110`).
- **Changelog**: user-visible changes get a line in `Data/Changelog.lua`.
- **Mock fidelity**: when client and mock disagree, fix the mock first (`README.md:139`).

## Forever deltas

Status key: **VERIFIED** = confirmed from this codebase (the code already does it, or the fact is in the brief such as
Interface 16001 and C_EditMode existing). **UNVERIFIED** = needs checking on a real 1.60.1 client; nobody in this
analysis had a Forever client. Most client-side facts are therefore UNVERIFIED by design.

### TOC and packaging

| # | Delta | Status |
|---|---|---|
| F1 | `## Interface: 20506` -> `## Interface: 16001` in `DisasterZone.toc:1`, every pack TOC (e.g. `DisasterZone_Chess.toc:1`) and `DisasterZone_Rooms`. The value comes from the brief. | VERIFIED (value), UNVERIFIED (whether Forever also expects a flavor-suffixed TOC name, e.g. `_Vanilla`/`_Classic`; 2.5.6 uses a plain name, `research/api.md:421-426`) |
| F2 | `## LoadSavedVariablesFirst: 1` (`DisasterZone.toc:8`) is required for hot patches: `Boot.lua` must read `DisasterZonePatchDB` at file time (`Core/Boot.lua:7-8,40-48`). If Forever ignores it, the boot loader degrades safely (`Boot.svFirst = false`, `/dzpatch` reports it, `:633-636`) but in-game updates never apply. Its semantics were unverified even on 2.5.6 (`research/api.md:430,467`). | UNVERIFIED |
| F3 | `X-CDL-Protocol`, `X-DZ-Build`, `X-DZ-Pack` are custom `X-` fields read through `C_AddOns.GetAddOnMetadata` (`Core/Boot.lua:302-308`, `Core/Init.lua:12`). Modern clients restrict which metadata fields are readable; `X-` fields have historically been allowed. | UNVERIFIED |
| F4 | `## OptionalDeps: CDLoot, DisasterZone_Bridge` and the whole CDLoot move (`Core/Boot.lua:64-77,485-587`, slash aliases `/cdl`, `/cdloot` at `Core/Init.lua:735-736`) should be dropped: a Forever guild has no CDLoot history. | VERIFIED (code) |
| F5 | `## IconTexture` path and `## Category: Raid` carry over if the client supports them (both modern directives). | UNVERIFIED |
| F6 | New addon identity: decide whether to keep the folder name `DisasterZone` and prefixes `CDL*`. Forever runs on separate realms, so cross-talk with the TBC addon cannot happen; renaming is a product choice, not a technical need. If the SavedVariables names are renamed, every reference must follow (grep shows them in DB, Boot, Patch, MyLog, Meter, BossLearn, Bridge, UI/Settings). | VERIFIED (code) |

### Addon messaging

| # | Delta | Status |
|---|---|---|
| F7 | Sending: all traffic goes through ChatThrottleLib v32, which already calls `_G.C_ChatInfo.SendAddonMessage` and reads `Enum.SendAddonMessageResult` (`Libs/AceComm-3.0/ChatThrottleLib.lua:349-381,640`). Direct sends also use `C_ChatInfo.SendAddonMessage` (`Core/BossMod.lua:994-997`, `Core/ClassPlanner.lua:238-242`). No bare `SendAddonMessage` is called anywhere in our code. A modern client should need no change. | VERIFIED (code), UNVERIFIED (Forever exposes `C_ChatInfo.SendAddonMessage` with the same return enum) |
| F8 | Prefix registration: AceComm calls `C_ChatInfo.RegisterAddonMessagePrefix` when `C_ChatInfo` exists, else the bare global (`Libs/AceComm-3.0/AceComm-3.0.lua:64-68`); BossMod and ClassPlanner call `C_ChatInfo.RegisterAddonMessagePrefix` directly (`Core/BossMod.lua:1092-1094`, `Core/ClassPlanner.lua:337`). Prefix max 16 chars (AceComm `:61`). | VERIFIED (code), UNVERIFIED (Forever) |
| F9 | Prefix count: 16 Comm + 4 Patch + 41 LootReserve + D5, BigWigs, PLPWR, SHPWR = about 65 registered prefixes. Check Forever's per-client prefix limit, and whether LootReserve/Pally Power/ShamanPower-style addons even exist on Forever; if not, drop `ReserveLR` (41 prefixes), `PLPWR`, `SHPWR` interop or re-target it to the Forever versions. | UNVERIFIED |
| F10 | Server throttle: the design assumes 10-message burst then 1/s per prefix on GUILD/RAID/PARTY and unthrottled whispers outside instances (`research/api.md:212-216`; `Core/Patch.lua:40-42`; Sync `STATE_GAP`). All rate constants (Sync `:20-37`, DigestSync `ROUND_WINDOW`, Patch `CHUNK`/`IDLE`) are tuned to it. Measure on Forever before trusting the timings, especially the patch stream and login waves of a full guild. | UNVERIFIED |
| F11 | `CHAT_MSG_ADDON` payload and sender format (`Name-Realm`, `Ambiguate(sender, "none")`). Forever's realm naming (connected realms or not) decides whether `Util.NormalizeName` (`Core/Util.lua:39-54`) and `GetNormalizedRealmName` keys stay stable. | UNVERIFIED |
| F12 | Chat channels used: GUILD, RAID, PARTY, WHISPER (and `INSTANCE_CHAT` in ClassPlanner, `Core/ClassPlanner.lua:225`). A vanilla-setting client should have all; `INSTANCE_CHAT` may not exist without LFG. | UNVERIFIED |
| F13 | "No player named" filter uses `ERR_CHAT_PLAYER_NOT_FOUND_S` and `ChatFrameUtil.AddMessageEventFilter` with fallback `ChatFrame_AddMessageEventFilter` (`Core/Comm.lua:523-530`). Already fallback-safe. | VERIFIED (code) |
| F14 | Keep the wire format as is (protocol major `"1"`, LibSerialize/LibDeflate). Nothing in the encoding is client-specific. The Forever port may reset `ns.PROTO` freely since no old clients exist. | VERIFIED (code) |

### SavedVariables and boot

| # | Delta | Status |
|---|---|---|
| F15 | All six SavedVariables are account wide; DB.lua already keys per-character data by `Name-Realm` and per-guild data by `Guild-Realm` (`Core/DB.lua:132-160,384-406`). No change needed unless Forever shares an account across TBC and Forever WTF folders (it should not: separate client install). | VERIFIED (code), UNVERIFIED (Forever WTF layout) |
| F16 | Start the Forever port at a fresh `SCHEMA` (1 or keep 2 with an empty `MIGRATIONS`), drop `CleanupGuildInfo` (`Core/DB.lua:191-202`) and TBC-only defaults (Retribution swing timer, Hunter Viper/Hawk aspects, Sunmote/arena `VIA_TEXT`, `Core/Constants.lua:14`). Schema/migration machinery itself ports as is. | VERIFIED (code) |
| F17 | Hot patch: `loadstring` must exist (`Core/Boot.lua:164,184`); retail-era clients still have it. The public keys live in `Core/PatchKey.lua` (patches) and `Core/BridgeKey.lua` (Discord bridge); a fork needs its own. Decide whether to keep the hot-patch system at all for v1 of the port. | VERIFIED (code), UNVERIFIED (`loadstring` on 1.60.1) |
| F18 | `C_AddOns.GetAddOnMetadata` is used without a global fallback for the version (`Core/Init.lua:12`): if missing, `ns.version` becomes `"0.0.0"`. `Boot.lua` already falls back for `IsAddOnLoaded`/`DisableAddOn` (`:69,534-538`). | VERIFIED (code), UNVERIFIED (C_AddOns on Forever; likely given a modern client) |
| F19 | Error capture uses `seterrorhandler`, `debugstack`, `debuglocals`, `EventRegistry`, `IsEncounterInProgress` (`Core/Init.lua:189-226,255-294`), all guarded by type checks. | VERIFIED (code, guarded) |
| F20 | `bit` library for SHA-256 (`Core/Sha256.lua:11`). Present on every WoW client so far. | UNVERIFIED |

### Events, timers and other client APIs in the core

| # | Delta | Status |
|---|---|---|
| F21 | Event registration skips events the client does not know via `C_EventUtils.IsEventValid` + `pcall` (`Core/Init.lua:421-448`), so TBC-only events (e.g. `ENCOUNTER_START/END` used by Patch, `Core/Patch.lua:1336-1337`) fail soft. Turn on `/dz debug` on Forever to list skipped events. | VERIFIED (code), UNVERIFIED (which events are missing) |
| F22 | `C_Timer.After/NewTimer/NewTicker`, `GetServerTime`, `Ambiguate`, `IsInGuild/IsInRaid/IsInGroup`, `GetRaidRosterInfo`, `C_PartyInfo.GetLootMethod` + `Enum.LootMethod.Masterlooter` (`Core/Util.lua:569-578`), `C_GuildInfo.GuildRoster` (`Core/Guild.lua:1982-1983`). Master loot is a vanilla mechanic, so the loot council model should still apply. | UNVERIFIED |
| F23 | Edit Mode: `Core/Layout.lua:684-834` writes Blizzard frames through `C_EditMode.GetLayouts/SaveLayouts` and `EditModeManagerFrame`. The brief says C_EditMode exists on Forever. | VERIFIED (exists per brief), UNVERIFIED (same layout schema) |

### TBC constants that leak into validators and sync

| # | Delta | Status |
|---|---|---|
| F24 | `MAX_ITEM_ID = 200000` in `Core/Store.lua:15`, `Core/BiS.lua:30`, `Core/ItemDB.lua:349`. It validates synced lists; any Forever item id above 200000 (new zones and raids) would make a member's list fail validation everywhere. Raise or derive it. | VERIFIED (code), UNVERIFIED (Forever item id range) |
| F25 | Phases 1..5 + pre-raid 0 (`Core/Constants.lua:136-139`), 17 slots incl. relic, TBC proficiencies "at level 70" (`:337-385`), class list without the new race's needs (race does not change classes, but check for any new class). Store validators accept only phases 1..5 (`Core/Constants.lua:132-135`), so Forever's raid tiers must map onto that or the caps must change before the first release (after release the caps may only grow). | VERIFIED (code), UNVERIFIED (Forever tier count) |
| F26 | `dev/tools/known_globals.json` is harvested from 2.5.6 addons. Re-harvest it from a Forever AddOns folder (`check.py --rebuild-known`, `dev/tools/check.py:556`), and update `wowmock/` to the 1.60.1 API before relying on the test suites. | VERIFIED (tooling), UNVERIFIED (Forever API surface) |
| F27 | Interop targets: DBM `D5` / BigWigs pull timers, LootReserve, Pally Power, a ShamanPower-like protocol, Discord bridge launcher. Confirm which of these exist for Forever. | UNVERIFIED |

### What can be copied nearly verbatim

`Core/Init.lua` (minus CDLoot slash aliases), `Core/Util.lua` (minus TBC-specific group helpers if any), `Core/DB.lua`
(new defaults), `Core/Comm.lua`, `Core/Sync.lua`, `Core/DigestSync.lua`, `Core/Sha256.lua`, `Core/Codec.lua`, the
embedded libraries, and the boot loader if hot patches are kept. The DigestSync/RevList/HELLO-field patterns are the
reusable backbone for every guild-shared feature in the port.
