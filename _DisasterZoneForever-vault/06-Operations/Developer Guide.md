---
tags: [operations, dev]
updated: 2026-11-11
---

# Developer Guide

Moved here from the root README on 2026-11-10, so the README stays a short install guide for players. Background on
Forever: Forever runs vanilla content at level 60 on the modern retail (12.x) engine. Addons there get no combat log,
see secret (unreadable) health, power and instance mob names, and cannot send addon messages during a boss pull. Do not
assume TBC or Classic Era behaviour. Upstream: a full-history fork of
[tsumilo/DisasterZone-dev](https://github.com/tsumilo/DisasterZone-dev) (TBC Anniversary, Interface 20506); its design
docs in `dev/docs/` still describe that original.

Related: [[Linux Dev Setup]] · [[Testing with Forever Data]] · [[Adding a Feature]] · [[Adding a Forever Raid]] ·
[[Code Map]]

## What the addon covers

DisasterZone is Forever-only. The shipped addon has only Forever data: dungeon, crafted, reputation and PvP items,
consumables, paladin blessings and shaman totems, seasons instead of TBC phases, and the three raids that open on
9 December 2026 (Barrow Deeps 10, Hyjal Summit 20, Onyxia's Lair 40). Pages without Forever data are hidden for now:
the gear sim, My Log, Raids > Strategies, meters and boss mods. Open work is on the board ([[Work.base|Work]]).

## Layout

```
addon/DisasterZone/          the addon (Lua 5.1); README.md is the player guide
addon/DisasterZone_Rooms/    3D room data, load on demand (Karazhan Chess uses it)
addon/DisasterZone_<Game>/   game packs: Azeromon, Bingo, Chess, HoldTheLine (dev/docs/GAME_PACKS.md)
dev/
  tools/       check.py (static checker), harness.py + wowmock/ (the Lua 5.1 mock client, with a Forever
               profile), release.py + patchlib.py (releases and signed in-game updates), README.md
  tests/       the test suites: tests/<area>/test_*.py; tests/forever/ runs against the Forever profile
  tf_e/        run_all.py (runs the suites in parallel; output in tf_e/<name>/, git-ignored)
  generators/  the data generators; gen_forever_*.py build the shipped Forever data
  fixtures/tbc/  the upstream TBC data, used only by the upstream tests
  probe/       DZProbe, the small addon that records what the real Forever client does
  docs/        upstream design docs (TBC original): SPEC.md and addenda, HOTPATCH.md, GAME_PACKS.md, research/
  install_forever.sh   copies the working copy into the Forever client
launcher/      the DisasterZone Launcher and the Discord bot server (Rust, Tauri); see launcher/README.md
_DisasterZoneForever-vault/   project docs (Obsidian)
```

## Setup on Linux (once, or after deleting `dev/luaenv`)

The vault note `06-Operations/Linux Dev Setup.md` is the source of truth. In short, from `dev/`:

```bash
python3 -m venv luaenv
luaenv/bin/pip install -r requirements.txt                          # lupa 2.8 (real Lua 5.1 inside Python)
luaenv/bin/pip install numpy==2.5.3 pillow==12.3.0 shapely==2.1.2   # some suites need these
mkdir -p luaenv/Scripts && ln -s ../bin/python luaenv/Scripts/python.exe   # run_all expects this path
export DISASTERZONE_ADDON_DIR=$PWD/../addon/DisasterZone
export DZ_SLOT_DIR=$PWD/.slots
```

Set the two variables in every shell you run tests from. Never point `DZ_NATIVE_CACHE` at `/tmp`: it can grow to
several GB.

### Windows

Upstream was built on Windows: `addon/DisasterZone` was a directory junction into the game's AddOns folder, the venv
was run as `luaenv\Scripts\python.exe`, and `run_all` forked its suites inside WSL (`dev/tools/wsl/README.md`). That
still works in principle, with the junctions pointing into `_forever_\Interface\AddOns`. We have not tested it on
Windows. If you use junctions, delete one only with `rmdir` (never a recursive delete, which can follow the junction
and delete the real addon).

## Everyday commands

Run from `dev/`, with the variables above set:

| What | Command |
|---|---|
| Static check (syntax, stray globals, unknown APIs) | `luaenv/bin/python tools/check.py -q` |
| Test suites (only what your change can affect) | `luaenv/bin/python tf_e/run_all.py` |
| What that would run, and why | `luaenv/bin/python tf_e/run_all.py --dry-run` |
| Every suite, no skipping | `luaenv/bin/python tf_e/run_all.py --all -j 12` |
| Patch suites (they cannot fork) | `DZ_FORK=0 luaenv/bin/python tf_e/run_all.py patch/ --all` |
| Fail fast while fixing | `luaenv/bin/python tf_e/run_all.py -x` |
| One suite | `luaenv/bin/python tests/forever/test_forever_raids.py` (add `-k name` for matching cases) |
| The Forever suites | `luaenv/bin/python tests/forever/test_<name>.py` (profile, Deadmines replay, names, professions, raids, keys, secrets, content) |
| Harness self-test | `luaenv/bin/python tools/test_harness_selftest.py` |
| Install into the Forever client | `./install_forever.sh` (add pack names, e.g. `Bingo Chess`; `--remove` takes them out; `WOW_DIR` sets the client) |

`dev/tools/README.md` documents the mock client (World / Client, the guild and raid simulation, loot, `/roll`,
relogs). A Forever client is `Client(w, name, forever=True)`: see the vault note `06-Operations/Testing with Forever
Data.md` for how the profile and the replays come from real client sessions.

### Tests today

- `dev/tests/` holds 288 suite files in 69 areas; 8 of them, in `tests/forever/`, run against the Forever profile.
- `run_all --all` runs 306 suites (the longest are split into shards). 17 fail; all 17 are known upstream or
  environment failures, listed in the Linux Dev Setup note. More than that is a regression.
- Most upstream suites still use TBC data as their fixtures (`dev/fixtures/tbc/`): they test the engines (council,
  BiS, raid plans), not the content.

### How run_all stays fast

- **Only what changed.** Each suite records what it read (files and the addon functions its clients called) in
  `dev/.testmap/` (git-ignored). `run_all.py` skips a suite when none of that changed since its last run. An edit
  inside a function reruns the suites that called it; top-level code reruns every suite that loaded the file, so keep
  load-time code to table set-up. Use `--all` before a release.
- **Fork per case.** Suites that share a set-up (`r = setup()`) build it once and fork a clean process per case
  (`tools/forkrun.py`). Put shared world-building first in a case and per-case tweaks after it.
- **Bytecode cache.** The harness compiles each addon file once (`dev/.luacache/`); `DISASTERZONE_NO_BCCACHE=1` turns
  it off.
- **Scheduling.** Longest suites first (`tf_e/timings.json`), long ones split into shards, and one shared pool of
  worker slots for every `run_all` on the machine (`DZ_TEST_SLOTS`, default 8).

## Making a change

1. Work on a feature branch (never commit straight to `main`). Edit the addon under `addon/DisasterZone/`.
2. Run `tools/check.py` and `tf_e/run_all.py`. Add a test for any bug you fix; Forever behaviour goes in a
   `forever=True` suite.
3. Install with `dev/install_forever.sh` and test in game. Code changes need `/reload`; a TOC change needs a full
   client restart.
4. A new Lua file needs the line-1 guard: `tools/release.py guards add`.
5. Open a PR and merge to `main` once checks pass. Update the vault (changelog, decisions, board, code map).

**Mock fidelity.** When the real client disagrees with the mock, fix the mock first, then the addon. On Forever, check
the API against Blizzard's UI source (Gethe `wow-ui-source`, branch `forever`) or the real client, not against TBC.

## Releasing

The tools are upstream's and work the same way: `release.py full` builds a release zip, `release.py patch` makes a
signed in-game update (Lua files only; `dev/docs/HOTPATCH.md`).

What is different today:

- **Releases are zips on this repo's GitHub Releases.** `release.py full` writes `dist/DisasterZone-<version>.zip`
  (the addon, `DisasterZone_Rooms` and the game packs; never `DisasterZone_Bridge`) and checks it. Attach it to a
  GitHub release with the notes from `dev/releases/<version>.md`, as a full release marked **Latest** (not a
  pre-release): the README's download link is `/releases/latest`, which skips pre-releases. Versions restarted at 0.1.0 (test builds 0.x,
  go-live 1.0.0); never use 1.5.5 (`Util.PRE_FOREVER_VERSION`, the label of every pre-0.1.0 Forever copy).
  `dev/releases/` holds only our records; the TBC original's (0.10.0 ... 1.5.5, its update and publish logs) are kept
  for reference in `dev/fixtures/tbc/releases/`. `full` refuses a version that already has a record.
- **In-game updates are off.** `Core/PatchKey.lua` holds no key, so releases ship with in-game updates off. The addon
  and `release.py` refuse the TBC original's keys.
- Before any release: `tf_e/run_all.py --all`, plus the patch suites with `DZ_FORK=0`.

## Launcher

`launcher/` holds the desktop launcher (Tauri 2, Rust) and the Discord bot server; these notes do not cover them.
Rust tests: `cargo test` in `launcher/proto`, `launcher/server` and `launcher/src-tauri`.

