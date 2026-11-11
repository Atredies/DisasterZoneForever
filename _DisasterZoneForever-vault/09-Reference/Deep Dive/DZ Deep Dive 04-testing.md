# 04 - DisasterZone test system, end to end (and how it runs on Linux)

Clone: upstream `dz-dev` at `e21d5a9` (Release notes 1.6.0). All paths below are relative to the clone unless absolute.
Legend: **VERIFIED** = read in code or reproduced on this machine; **UNVERIFIED** = inferred, not proven.

## Summary

- The test system is four layers: (1) `dev/tools/check.py`, a static checker that compiles every addon file with real
  Lua 5.1 (lupa) and walks the bytecode for global reads/writes, unknown API fields, Lua limits, layer violations and
  a "uniformity" design lint; (2) `dev/tools/harness.py` + `dev/tools/wowmock/*.lua`, a simulated WoW client where each
  player is its own Lua 5.1 runtime and a Python `World` owns the clock, the addon-message bus, chat, guild, raid,
  loot, `/roll` and SavedVariables across relogs; (3) ~283 scenario suites (`dev/tests/<area>/test_*.py`, 67 areas
  with test files; the README still says 209/50) that boot the REAL addon on 2-60 mock clients and assert on state,
  traffic and UI; (4) `dev/tf_e/run_all.py`, a parallel runner with dependency-based test selection (`testmap*.py`),
  longest-first scheduling, shards, machine-wide slots and (on POSIX) fork-per-case via `forkrun.py`. VERIFIED.
- It runs on our Linux box with almost no friction. lupa 2.8 installs as a prebuilt `cp314` manylinux wheel on
  Python 3.14 (no build, no uv needed). VERIFIED.
- Results on Linux, `run_all.py --all -j 12`: **300 suite runs, 282 passed, 18 failed, 308 s wall** (5 m 08 s real,
  ~51 CPU-min). Summed cases from summary lines: 2,987 cases, 2,915 passed, 72 failed. After fixing the environment
  (no clone edits) the 18 failing runs drop to **5 suites / 9 cases**, all of which look like genuine state of the
  repo at this commit or missing private data, not Linux problems. VERIFIED.
- `test_harness_selftest.py`: 13/13 pass in 0.7 s. `check.py`: exit 1 at HEAD (1 real global write + 41 uniformity
  errors in new files; repo drift, not Linux). VERIFIED.
- The mock is kept faithful by evidence, not by an in-game probe: (a) globals/fields/events read by 20 installed
  reference addons (`known_globals.json`), (b) ports of Blizzard UI code from `Gethe/wow-ui-source` branch
  `classic_anniversary`, (c) a hand-written API cheat sheet `dev/docs/research/api.md`. `tests/probe` is about 3D
  model files and `tests/conformance` is about internal code rules; **neither probes the real client API**. VERIFIED.
- Biggest Forever deltas for the mock (checked against Blizzard UI source 1.60.1.70862, Gethe `wow-ui-source` branch `forever`):
  Forever runs the **Mainline** UI, so the loot window is the retail ScrollBox `LootFrame` (no `LootButton1-4` /
  `LootFrame_UpdateButton`), tooltips go through `TooltipDataProcessor` (no `OnTooltipSetItem` anywhere in the source),
  `C_Seasons` is gone, and 91 namespaces exist that Anniversary lacks (`C_TooltipInfo`, `C_LootFrame`, `C_LootHistory`,
  `C_Bank`, `C_SwingTimer`, `C_ClassTalents`, ...). The core comms/party/guild/item/container namespaces are present on
  both with the same shapes. VERIFIED (source); behaviour in the live client UNVERIFIED.

## Architecture of the harness + mock

### Python side: `dev/tools/harness.py` (2,869 lines)

- `World` (realm "Thunderstrike", guild "Casual Disaster", ranks GM/Officer/Raider/Member/Initiate) owns one virtual
  clock. `tick(seconds, step=0.05)`: per step deliver due messages, then per client run deferred events, internal
  timers, `C_Timer`, `OnUpdate(elapsed)` of visible frames, animations. `run_until(pred)`. VERIFIED (harness.py:894).
- `Client` = one `lua51.LuaRuntime(unpack_returned_tuples=True, register_eval=False, register_builtins=False)` per
  player (harness.py:1872). The mock chunk is called as `M = chunk(cfg, PY, sources)`: `cfg` is identity + flags,
  `PY` is a table of Python callbacks (`send_addon`, `send_chat`, `give_master_loot`, `item_lookup`, `random_roll`,
  `invite`, `guild_invite`, `load_lod`, ...), so every cross-player effect goes through Python and the World routes it.
  VERIFIED.
- Messaging: addon messages are hex-encoded across the bridge (binary safe), delivered after `latency` (0.1 s),
  routed by chat type (GUILD = online guild incl. sender, OFFICER = rank <= officer_rank, RAID/PARTY by group and
  subgroup, WHISPER by `Name`/`Name-Realm`), with real limits (prefix > 16 chars or text > 255 bytes raise) and a
  per-prefix throttle (10 burst, +1/s, dropped with `AddonMessageThrottle`). `world.addon_fault` injects loss/corruption.
  VERIFIED (README section 3, harness `_route_addon`/`_recipients`).
- Guild: roster built from all clients + `add_offline_member`, empty until the first `GUILD_ROSTER_UPDATE` (0.5 s after
  login), 17 return values, officer notes gated by rank, 31-byte notes, 500-byte guild info text. VERIFIED (README).
- Raid/loot: `make_raid(clients, master_looter=...)` fires `GROUP_ROSTER_UPDATE` (+`PARTY_LOOT_METHOD_CHANGED`),
  `ExtraMember` = raid members with no runtime (people without the addon). `client.open_loot([(itemID, quality)])`
  fires `LOOT_READY`/`LOOT_OPENED`; `GiveMasterLoot` is a request: 0.1 s later the slot clears, 0.2 s later everyone
  gets `CHAT_MSG_LOOT`; `set_ml_refusal` simulates `ERR_LOOT_MASTER_INV_FULL` etc. `start_loot_roll` drives
  `GroupLootFrameN`. `world.encounter(id, name)` fires `ENCOUNTER_START/END` + `BOSS_KILL`. VERIFIED.
- `/roll`: `world.player_roll(who, value=None, lo, hi)` sends `CHAT_MSG_SYSTEM "Name rolls N (lo-hi)"` to every group
  client after `latency`; value from a seeded `random.Random(4242)` when not given; Lua `RandomRoll()` calls it through
  `PY.random_roll`. VERIFIED (harness.py:1570).
- Relog: `client.relog()` fires `PLAYER_LEAVING_WORLD`/`PLAYER_LOGOUT`, serializes SavedVariables to Lua source
  (nested tables, binary strings, `%.17g` floats, inf/nan; recursive tables are an error), builds a **fresh** runtime
  and loads the addon with `PLAYER_ENTERING_WORLD(false,true)`. `relog(reload=False)` = logout (guild sees "has gone
  offline") + login. SavedVariables are assigned before the first file when the TOC says
  `## LoadSavedVariablesFirst: 1`, else just before `ADDON_LOADED`. VERIFIED (harness.py:2426).
- Errors are never swallowed: every dispatch runs in `xpcall` + `debug.traceback` and is recorded; tests end with
  `w.assert_no_errors()`. Reports: unknown template fields/methods, missing globals, unknown events. VERIFIED.
- `Client.eval(code, *args)` runs Lua with `ns` (the addon namespace) in scope; `eval_py` deep-converts to Python
  (`EmptyTable` for `{}`). This is how almost every assertion reads addon state. VERIFIED.
- Packs: the six game packs (`addon/DisasterZone_<Game>`) and `DisasterZone_Rooms` (load-on-demand 3D data) are found
  next to the addon folder and loaded with their own namespace. VERIFIED (harness.py:69-110).

### Lua side: `dev/tools/wowmock/` (plain Lua 5.1, ~7.5k lines + item data)

| File | Holds |
|---|---|
| `mock.lua` | Entry point; loads the modules, known-event list, legacy-global gate, control API for Python (`M.step`, `M.set_time`, ...) |
| `core.lua` | Error capture, WoW Lua extensions (`strsplit`, `format("%2$s")`, degree `sin`, `bit.*`, `wipe`), time, `C_Timer`, event registry; removes `io`, `require`, ... |
| `objects.lua` | Widget types and methods; scripts fire on state change; `SetScript` of a script the type lacks errors like WoW; unknown `Set*/Get*/Is*` methods absorbed and reported |
| `ui.lua` | Templates with modelled children (BackdropTemplate, UIPanelButton, ScrollBox/DataProvider, Settings, MenuUtil, StaticPopup, GameTooltip, LootFrame/LootButton1-4, GroupLootFrame1-4, ...) |
| `game.lua` | Game APIs: `C_Item`, `C_Container`, `C_ChatInfo`, `C_PartyInfo`, `C_GuildInfo`, `C_AddOns`, `C_Map`, `C_Spell`, `C_LFGList`, units, talents, bags/bank, `GetBuildInfo() -> "2.5.6","69795",...,20506`, `WOW_PROJECT_ID = 5` |
| `items.lua` / `items_fallback.json` | 1,434 addon items + 23,576 other TBC items (generated by `gen_items.py` from Questie/LBIS/AtlasLoot data) |

Deprecated globals (`GetItemInfo`, `GetContainer*`, `GuildRoster`, `GetLootMethod`, ...) live in `M.legacy` and are
only installed with `Client(legacy_globals=True)`, mirroring the real `loadDeprecationFallbacks` CVar gate. VERIFIED
(mock.lua, game.lua:1772).

### Speed tricks inside the harness

- **Bytecode cache**: every addon file is compiled once (`loadstring` + `string.dump` in a private runtime) and
  clients load the bytecode; on disk in `dev/.luacache/` keyed by sha1(chunkname + source). VERIFIED (harness.py:150).
- **Native cache** (`NATIVE_DIR`, POSIX only, default `/var/cache/dz-bc`, override `DZ_NATIVE_CACHE`): per path,
  mtime, size and coverage flag, made for WSL's slow 9P mount. Writes fail silently if the dir is not writable.
  VERIFIED. Warning: with `DZ_NATIVE_CACHE` pointed at a folder, one `--all` run grew it to **3.1 GB** (patch suites
  stage trees at new temp paths, so every staged copy is a new key); it filled the `/tmp` quota and broke a later run.
  On Linux leave it unset or prune it. VERIFIED.
- **Pre-loaded templates** (`build_templates`, `DZ_TEMPLATES=n`): runtimes in which the addon's ~390 files already ran,
  handed to `Client.load_addon` when nothing would differ (`_template_mismatch`). Used by `tools/testserver.py`.

### How the mock is kept faithful (and its admitted gaps)

1. `known_globals.json`: 2,693 globals, 773 namespace fields, 381 events read by 20 reference addons that target the
   same client (LootReserve, WeakAuras, DBM-Core, Questie, Details, ...). Own-prefix globals and globals an addon also
   writes are excluded. Used by `check.py` and by the mock's unknown-event report. VERIFIED.
2. Blizzard source ports: `StaticPopup_EscapePressed`, `HandleModifiedItemClick` (classic_anniversary),
   `LootFrame_Update`/`LootFrame_UpdateButton`. `tests/client-api/fetch.sh` pulls files from
   `Gethe/wow-ui-source/classic_anniversary`; `dump_globals.py` lists every global/field the addon reads with how many
   reference addons read it (`globals.txt`, `deprecated_globals.txt`, `tree.txt`). VERIFIED.
3. `dev/docs/research/api.md` (470 lines): verified 2.5.6 notes with file:line evidence from installed addons, a "things
   that break naive retail-11.x or 2.4.3 code" table and an "open uncertainties" list. VERIFIED.
4. The README "Assumptions" and "Known limitations" lists: no layout engine (`GetStringWidth = #text*6`), no
   combat/aura simulation, synthetic item quality/icons, `RegisterEvent` never errors, no taint. VERIFIED.

There is **no in-game probe addon** that dumps real API shapes back to compare with the mock. VERIFIED (grep for
`GetBuildInfo`/dump/probe in addon + tests).

## Static checks

- `check.py` (668 lines): per file `loadstring(src, "@rel")` in lupa, `string.dump`, parse the Lua 5.1 bytecode in
  Python (`luabc.py`), walk nested prototypes: `GETGLOBAL`/`SETGLOBAL` names, a constant-key `GETTABLE`/`SELF` after a
  namespace read (also through `local C_Item = C_Item` aliases) = field access. Outputs `ERROR syntax`, `ERROR global
  write`, `WARN UNKNOWN GLOBAL/FIELD/EVENT`, `WARN DEPRECATED` (a hand list: `GetItemInfo`, `GetContainer*`,
  `GuildRoster`, `GetLootMethod`, `SendAddonMessage`, `EasyMenu`, `InterfaceOptions_*`, ...), `NOT IN WOW` (`io`,
  `require`, ...), `LIMIT` (locals 200 / upvalues 60 per function, warned from 170/45), `LAYERS`, `UNIFORMITY`. Exit 1
  on any ERROR. Uniformity is now strict by default (`--uniformity-strict` kept for old command lines). VERIFIED.
- `known_globals.json` is a cache; `--rebuild-known` re-harvests from `C:\World of Warcraft\...\AddOns` (Windows path,
  reference addons not in the repo, so we cannot rebuild it; we use the committed cache). VERIFIED.
- `uniformity.py` + `uniformity_baseline.json`: counts literal style-token colours, copied local helpers, numeric
  `SetFont` sizes and raid tables per file; only counts above the baseline report. `test_uniformity.py` = self-test.
- `layers.py` + `layers.json` (`layers`, `prefixes`, `files`, `features`, `feature_order`, `kit`, `wire`) +
  `layers_allow.json`: a dependency map from `ns.X` references and the lint for `up`/`kit`/`order` violations; the
  allowlist only shrinks (`--prune`). `test_layers.py` = self-test. `modules_doc.py` = module contract headers.
- `dev/find_multiret.py`: lists `tonumber(<call>)` sites where a multi-return call would feed `tonumber`'s base (the
  `GetInventoryItemID` crash class). Hard-coded `C:\` path. A copy with the path fixed
  listed 270 sites (informational). VERIFIED.
- `ui_audit.py` / `ui_audit_states.py` / `ui_audit_bossmods.py`: boot the addon, open every view (STATES) and compute
  text rectangles with a Segoe UI proxy font calibrated to Friz Quadrata (`K_FRIZ = 1.0855`), reporting TRUNC /
  WRAPCUT / SPILL / OUTSIDE / OVERLAP / COVERED with PNGs; `look_diff.py` diffs renders. Several suites import it.

## Test selection & speed tricks

- `run_all.py [out] [filters] [-j N] [--all] [--dry-run] [-x] [--windows]` globs `tests/*/test_*.py`, runs each as
  its own Python process (`PY = dev/luaenv/Scripts/python.exe`), writes `tf_e/<out>/<task>.txt`, prints the last
  `-- ... passed` line, exits 1 on any failure. VERIFIED.
- **Dependency-based selection** (`testmap.py`, `testmap_rec.py`, `testmap_lua.py`): `tools/covsite/sitecustomize.py`
  is put on `PYTHONPATH`; with `DZ_COVER` set it loads `testmap_rec`, which records every dev/ or addon file opened,
  directories listed, Lua chunks loaded and **addon functions called** (the harness instruments each function body
  with `__DZC_<tag>[line]=true` when `DZ_COVER` is set). Each process writes a `.part`; `testmap.finish` merges them into
  `dev/.testmap/cov/<task>.json` with the exit code. Next run, a suite reruns only if a file it read changed, a folder
  it listed changed, or the own code of a function it called changed (diffed against the exact source kept in
  `.testmap/src/<sha1>.lua`), or a data table it read changed. Moves/splits are recognised (`moves.json`, by content,
  and a whole-program identity check in `testmap_lua.py`). A failed suite with unchanged inputs is reported failed
  again without running. VERIFIED: right after our full run, `--dry-run` selects 29 of 300 (the ones with no
  record, see below), in 0.5 s.
- **Longest first**: `tf_e/timings.json` records durations; the next run starts the slowest first. `-x` starts last
  run's failures first and stops starting new suites after the first failure.
- **Shards**: `testmap.SHARDS` splits 9 long suites into n processes (`DZ_SHARD="i/n"`, `harness.in_shard(pos)` keeps
  every n-th case).
- **RELEASE_ONLY**: `scale/test_raid_night.py` (60 members through a raid night) runs only with `--all` or a filter
  naming it.
- **Machine-wide slots**: lock files (`msvcrt` on Windows, `fcntl.flock` elsewhere) in `%LOCALAPPDATA%\DisasterZone\
  test-slots` (falls back to `~/DisasterZone/test-slots`, override `DZ_SLOT_DIR`); default
  `SLOTS = max(2, min(12, cpu_count - 8))`. A memory gate (`MIN_FREE_MB = 1500`) is Windows-only (`GlobalMemoryStatusEx`).
- **forkrun.py** (POSIX): reads each case's source, takes its leading simple statements (`r = setup()`, ...) as the
  set-up, groups cases with identical set-up, runs it once in a zygote and forks one process per case, so cases are
  isolated and set-up is shared. `DZ_FORK=0` or Windows = sequential. Write tests with shared world-building first.
- **WSL path** (`tools/wsl/`): on Windows, run_all sends suites into an Ubuntu WSL distro (`/opt/dzenv`), through one
  `testserver.py` per run that imports the harness once, pre-loads 16 template clients and forks per suite.
  `WINDOWS_ONLY = patch/, launcher/, scale/, sync/test_mixed_versions.py`. **On native Linux, run_all skips all of
  this** (`wsl_ready()` returns False when `os.name != "nt"`): suites run as plain processes, forkrun is on, the test
  server and templates are not used. VERIFIED.
- **patched_run.py**: builds a "shadow" release whose files are only guard lines + `error("the disk copy ran")`, stores
  the real source as an in-game update (`DisasterZonePatchDB`) and reruns run_all against it, proving the addon behaves
  the same when loaded through the update path.

## How to write a test (example)

Every suite is a standalone script: register cases with a decorator, finish with a runner that prints
`PASS/FAIL <case>` and a final `-- <file>: N case(s), P passed, F failed` line (what run_all parses), exit 1 on failure.
Area helpers build the world (`tests/boot-ui/_common.py`: `case`/`run_all`; `tests/loot-roll/lr_common.py`: `Runner`,
`Raid`; `tests/sync/common.py`: `new_world`, `settle`, traffic helpers). Three representative suites:

1. `tests/loot-roll/test_rolls.py` (raid rolls end to end; 7 addon users + people rolling by hand). Excerpt:

```python
R = Runner("loot-roll / rolls")

def setup(items=None, **kw):
    r = Raid(**kw)                       # 7 clients load the addon, council set, raid with ML, synced
    r["Alice"].open_loot(items or [(RUBY_DRAPE, 4), (THOUSAND_MARKS, 4)])
    r.w.tick(2)
    return r

@R.case
def roll_basic_flow_raid_wide():
    r = setup(); w = r.w
    log0, chat0 = len(w.addon_log), len(w.chat_log)
    panel_start(r["Alice"], RUBY_DRAPE)            # Alice.eval("ns.DropPanel:StartRoll(...)", item, 1)
    w.tick(1)
    RS = msgs_of_type(w, "RS", log0)               # decode addon traffic from world.addon_log
    assert len(RS) == 1 and RS[0]["_chat_type"] == "RAID"
    click_roll(r, "Bob", 54); click_pass(r, "Carol")
    w.player_roll("Zed", 95)                       # no addon: types /roll
    w.player_roll("Gina", 49, 1, 50)               # wrong range: shown, never suggested
    w.tick(30)                                     # roll closes by itself
    assert set(states(r, sid).values()) == {"closed"}
    w.assert_no_errors()
```

2. `tests/sync/test_sync_hostile.py`: injects forged/malformed AceComm traffic with Lua helpers
   (`LibDeflate:EncodeForWoWAddonChannel(LibSerialize:Serialize(msg))` sent through `ns.Comm`) and asserts nothing is
   accepted and nothing raises. Shows protocol-level testing through `eval`.
3. `tests/boot-ui/test_boot.py`: load / relog / migration / corrupt SavedVariables (`set_saved_variable` before
   `load_addon`, `relog()` three times, compare `eval_py("return DisasterZoneDB")`). Shows persistence testing.

`dev/tools/example_scenario.py` is the copy-me template: 3 guild members + 1 offline, `load_addon()`, `make_raid`
with ML, `enter_instance("Karazhan", 532)`, `encounter(652, "Attumen")`, `open_loot`, `GiveMasterLoot(1, 2)`,
`bob.relog()`, `tick(15)`, print `w.report()`, `assert_no_errors()`. Runs in ~1 s here. VERIFIED.
`dev/tools/test_harness_selftest.py` proves the harness with a temp addon folder holding only DisasterZone's `Libs/`
(13 tests: AceComm multipart over WHISPER/GUILD through ChatThrottleLib, raw routing/limits/throttle, timers, events,
widgets, ScrollBox/menus/popups/Settings, TOC + relog persistence, loot/ML/rolls, items/guild/group/bank/talents/
tooltip hooks, LibDBIcon/LibCustomGlow, chat/slash, misc). Extending the mock = edit `game.lua`/`ui.lua`/`objects.lua`
in plain 5.1 and rerun the self-test.

## Our Linux run (exact commands + results)

Machine: Arch Linux, Python 3.14.8, 24 CPUs, 30 GB RAM. All in the clone's `dev/`.

```bash
cd dz-dev/dev
python3 -m venv luaenv
luaenv/bin/pip install -r requirements.txt                 # lupa 2.8: wheel cp314-cp314-manylinux_2_17_x86_64, no build
luaenv/bin/pip install numpy==2.5.3 pillow==12.3.0 shapely==2.1.2   # what tools/wsl/setup.sh adds; some suites need them
mkdir -p luaenv/Scripts && ln -s ../bin/python luaenv/Scripts/python.exe   # run_all hard-codes this Windows path
export DISASTERZONE_ADDON_DIR=$PWD/../addon/DisasterZone   # default is C:\World of Warcraft\...
export DZ_SLOT_DIR=$PWD/.slots                              # else ~/DisasterZone/test-slots
luaenv/bin/python tools/test_harness_selftest.py
luaenv/bin/python tools/check.py -q
luaenv/bin/python tf_e/run_all.py linux1 --all -j 12
```

`lua5.1`/`luajit` from the system are not used: everything goes through lupa's bundled Lua 5.1. `dev/luaenv/`,
`dev/.luacache/`, `dev/.testmap/` and `dev/tf_e/*/` are git-ignored; the clone stays clean. VERIFIED.

| What | Result | Time |
|---|---|---|
| `test_harness_selftest.py` | 13/13 pass | 0.7 s |
| `example_scenario.py` | rc 0, no Lua errors | ~1 s |
| `check.py -q` | rc 1: 405 files, 0 syntax, **1 global write** (`UI/CombatTextLooks.lua:68`, `_, cls = UnitClass(...)` without `local`), **41 uniformity errors** (new `UI/Look*.lua`, `Plates`, `RingFace`, ... not in the Oct 17 baseline), 274 warnings | 12 s |
| `test_uniformity.py` | pass | ~2 s |
| `test_move.py` | pass | |
| `test_layers.py` | 1 fail: `layers.json` does not map 32 new UI files (repo drift) | |
| `test_testmap.py` | 44 pass, 2 fail: `Core/DevPlan.lua: missing` (TOC lists a gitignored private file); first attempt failed on a full `/tmp` quota | 11 s |
| `run_all.py --all -j 12` | **300 runs, 282 pass, 18 fail**; 2,987 cases / 2,915 pass / 72 fail | **308 s wall**, 3,069 s summed |

Slowest: `games/test_naxx` 251 s, `scale/test_raid_night` shards 124-155 s, `strategy/test_standins_gen.s2of3` 132 s.

### The 18 failures, triaged

| Suites | Cause | Linux-specific? | Fixed by |
|---|---|---|---|
| `patch/test_patch_boot` x3, `test_patch_net` x4, `test_release_tool` x2 (39 cases) | `FileExistsError: .../basesrc_1`: `_patchkit._unique()` uses an in-process counter; forked sibling cases get the same name. These suites are `WINDOWS_ONLY` upstream, so they never ran under fork | **Yes** (fork) | `DZ_FORK=0 run_all.py ... patch/ --all`: **12/12 runs pass**, 37 s. VERIFIED |
| `events/test_edge_tab`, `events/test_kinds_ui_qa` (26 cases) | `OSError: cannot open resource`: `ui_audit.py` loads `/mnt/c/Windows/Fonts/segoeui.ttf` on non-Windows | **Yes** (font path) | a wrapper that swaps in Noto Sans: edge_tab 16/16, kinds_ui_qa 37/39 (2 left: metrics differ or genuine, UNVERIFIED) |
| `groups/test_groups_core` (1) | `git show release-1.4.6:...`: shallow clone | No (clone depth) | `git fetch --unshallow --tags`: 9/9 pass. VERIFIED |
| `sync/test_mixed_versions` (6) | needs tag `release-1.4.0`, not on the public remote | No | 3 of 6 fixed by unshallow; 3 need the missing tag |
| `boot-ui/test_changelog` (1) | a 1.6.0 changelog line is > 90 chars | No, repo content (HEAD is literally "...within 90 characters") | - |
| `boot-ui/test_boot` (1) | relog idempotency: a `launcher` key appears after the first relog | No (same with `DZ_FORK=0`) | - (genuine or test drift, UNVERIFIED on Windows) |
| `games/test_azeromon_craft`, `test_azeromon_fix_side` (1+1) | trainer dialogue / `ns.Azero.pending` nil | No (same with `DZ_FORK=0`) | - (pack code mid-change at HEAD, UNVERIFIED) |
| `games/test_naxx` (1) | `n_sapphiron not slain in frost` (deterministic on rerun) | UNVERIFIED | - |

### Every Windows-only assumption we hit

1. `PY = dev/luaenv/Scripts/python.exe` in `run_all.py` (and `test_testmap.py`): fixed with a symlink, no edit.
2. Default addon path `C:\World of Warcraft\_anniversary_\Interface\AddOns\DisasterZone` in `harness.py`, `check.py`,
   `testmap_rec.py`, `find_multiret.py`, `tests/client-api/dump_globals.py`: set `DISASTERZONE_ADDON_DIR` (forgetting it
   makes every `--dry-run` say "changed" for everything, because record keys no longer resolve). `find_multiret.py`
   has no env override: patched copy.
3. `ROOMS_DIR` default is computed with `os.path.dirname(os.path.normpath(r"C:\..."))`, which on Linux yields a bare
   relative `DisasterZone_Rooms`; harmless when packs sit next to the addon folder, as in the clone. VERIFIED (code).
4. `ui_audit.py` fonts at `/mnt/c/Windows/Fonts` (WSL path); `ui_look.py`, `readme_art.py`, `preview_reminder.py`
   use `C:/Windows/Fonts`.
5. Slot dir under `%LOCALAPPDATA%`, memory gate via `GlobalMemoryStatusEx` (no-op off Windows).
6. Patch suites assume sequential cases (only safe because they are `WINDOWS_ONLY`).
7. `NATIVE_DIR=/var/cache/dz-bc` assumes root in WSL; unwritable on a normal Linux user (silently skipped).
8. `check.py --rebuild-known` and `tests/probe` need the installed client and reference addons under `C:\`.
9. The README's commands use backslash paths and `luaenv\Scripts\python.exe`.

## Forever deltas

Evidence base: Blizzard UI source for both clients, Gethe `wow-ui-source` branches `forever`
(`version.txt` = `1.60.1.70862`) and `classic_anniversary` (`2.5.6.70577`), indexed by API doc namespaces, documented
globals, events and templates. Namespace/function existence below is VERIFIED against those docs; live-client behaviour is UNVERIFIED.

### Version identity

- `GetBuildInfo()` must return `"1.60.1", "70862", <date>, 16001` (mock: `"2.5.6","69795",...,20506`). Interface 16001
  comes from the brief (UNVERIFIED here: the Blizzard TOCs in the dump say `## Interface: 0`).
- `WOW_PROJECT_ID`: the mock sets 5 (BCC). Forever's value is UNVERIFIED; read it from the Forever source/client.
- Every `20506` literal (README, api.md, check.py messages, release tooling) becomes 16001.

### Namespaces (mock vs Forever docs)

- Present on both and already mocked, same function names: `C_Item` (Forever 121 functions), `C_Container` (47),
  `C_ChatInfo` (45), `C_PartyInfo` (55), `C_GuildInfo` (39), `C_AddOns` (29), `C_Map`, `C_Spell`, `C_Timer`,
  `C_CVar`, `C_DateAndTime`, `C_CurrencyInfo`, `C_NamePlate`, `C_LFGList`, `C_EditMode` (12 functions on both; the addon
  calls `GetLayouts`/`SaveLayouts`/`SetActiveLayout`, the mock does not define `C_EditMode` at all, so add it).
- `C_PartyInfo.GetLootMethod` returns `method, masterLootPartyID, masterLooterRaidID` with the same `Enum.LootMethod`
  (0 FFA .. 2 Masterlooter .. 5 Personal) on both. `C_ChatInfo.SendAddonMessage` signature identical.
- In Anniversary, gone in Forever: `C_Seasons` (mocked: drop it), `C_Engraving`, `C_QuestChoice`, `C_Reforge`,
  `C_TableUtil`.
- New in Forever (91), the ones a guild/loot addon is likely to touch: `C_TooltipInfo`, `C_LootFrame` (`TryAutoLoot`),
  `C_LootHistory`, `C_Bank`, `C_SwingTimer` (`EnableRangeCheck`, `IsTargetWithinSwingRange`: relevant to DZ's swing
  timers), `C_ClassTalents`, `C_SkillInfo`, `C_Trainer`, `C_SuperTrack`, `C_VignetteInfo`, `C_AutoLoot`, `C_NameUtil`.
  Each needs a stub or model only if our addon calls it.
- Globals: Forever's API docs no longer document global `GetItemInfo` (Anniversary does): keep the mock's
  `legacy_globals` gate and treat `GetItemInfo` as deprecated/absent by default. Many globals the mock needs
  (`GetGuildRosterInfo`, `GiveMasterLoot`, `GetMasterLootCandidate`, `GetRaidRosterInfo`) are undocumented C functions
  on both, so their absence from the docs proves nothing; verify in-client.

### UI framework (the biggest change)

- Forever ships the **Mainline** UI tree (`Blizzard_UIPanels_Game/Mainline/`; Anniversary uses `.../Classic/` and
  `.../TBC/`). VERIFIED.
- Loot window: `Mainline/LootFrame.lua` is the retail ScrollBox LootFrame; there is no `LootFrame_UpdateButton` or
  `LootButton1-4` in the Forever source. The mock's LootFrame model (README section 3) and api.md section 2 must be
  rebuilt around `LootFrame.ScrollBox` element frames. Group rolls live in `Mainline/GroupLootFrame.lua`. VERIFIED.
- Tooltips: no `OnTooltipSetItem` anywhere in the Forever source; it uses `TooltipDataProcessor.AddTooltipPostCall`
  with `C_TooltipInfo` data. The mock's `show_tooltip_item` + `OnTooltipSetItem` hook path must become a
  TooltipDataProcessor model (api.md section 11 says the opposite for 20506). VERIFIED.
- `StaticPopup_EscapePressed` still exists (`Blizzard_StaticPopup/StaticPopup.lua:846`), but re-port from the Forever
  file. Re-check every other port (`HandleModifiedItemClick`, Settings, MenuUtil, templates) against the Forever tree.
- Templates: Forever has 3,659 named templates vs 2,337; the mock's template list (`ui.lua`) should be regenerated or
  at least checked against `idx_forever.json` `TPL`.
- Events: 1,816 vs 1,483 documented events; rebuild the mock's known-event list and check.py's event set from Forever.

### Return values and behaviour to re-verify (UNVERIFIED until checked in-client)

- `C_Item.GetItemInfo` 17 returns, `C_Container.GetContainerItemInfo` returning a table, `GetTalentTabInfo` order
  (`id, name, desc, icon, pointsSpent, ...`; Forever also has `C_ClassTalents`, so talents may be a different system),
  `GetGuildRosterInfo` count, `GetRaidRosterInfo` 12 values, `CHAT_MSG_ADDON` 5th arg, `CHAT_MSG_LOOT` args, the
  addon-message throttle numbers (10 / 1 per s), whether master loot exists in practice on Forever realms.
- Item data: `items.lua`/`items_fallback.json` are TBC items from Questie's TBC DB. Forever's item set and quality/
  equipLoc must come from Forever data.

### What check.py needs

- `known_globals.json` is harvested from 20 addons that target Anniversary. For Forever, harvest from addons that
  target 16001 (or seed it from `idx_forever.json` `G`/`NS`/`EV`, which is stronger evidence: the client's own API
  docs). `DEPRECATED` hints and `EXTRA_KNOWN` must be redone for Forever.
- Uniformity/layers/limits are client-independent and carry over unchanged.

### How to verify the mock against the real Forever client

DisasterZone has nothing for this (VERIFIED: `tests/probe` checks generated 3D model files against CASC data,
`tests/conformance` checks internal code rules like one handler per comm type). Proposal:

1. **Static source diff (do first, offline)**: generate a "mock surface" list (every global and `C_*` member the mock
   defines, every template, every event) and diff it against `idx_forever.json`. The quick version above already
   found `C_Seasons` to drop, `C_EditMode` to add, and mock-only helpers that are not real (`C_BattleNet.GetFriendInfo`,
   `C_LFGList.GetAvailableActivities`, `C_ChatInfo.IsValidChatType`: candidates to rename or remove).
2. **In-game probe addon** (`DZProbe`, Interface 16001): a set of probe calls (each API the mock models, with fixed
   arguments: a known item ID, bag 0 slot 1, `"player"`, the guild roster index 1, `C_PartyInfo.GetLootMethod()`, ...)
   that records `select("#", ...)`, each return's `type()` and value, and table key sets, plus `GetBuildInfo()` and a
   `pcall` per call, into SavedVariables. Also an event recorder for a scripted session (loot a corpse, `/roll`,
   whisper an addon message, relog) that logs event names and argument types and counts.
3. **Replay the same probe in the mock**: load `DZProbe` in a harness client (it is just an addon), let it write its
   SavedVariables, and diff the two SV files in a test (`tests/client-api/test_forever_conformance.py`). Any shape
   difference is a mock bug or a client change, caught in CI; rerun the probe after each Forever patch.
