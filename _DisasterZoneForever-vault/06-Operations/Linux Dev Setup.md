---
tags: [operations]
updated: 2026-11-11
---

# Linux Dev Setup

Verified 2026-11-08 on Arch Linux, Python 3.14. Upstream assumes Windows; these steps need no source edits.

```bash
cd dev
python3 -m venv luaenv
luaenv/bin/pip install -r requirements.txt                       # lupa 2.8 ships a cp314 wheel
luaenv/bin/pip install numpy==2.5.3 pillow==12.3.0 shapely==2.1.2   # some suites need these
mkdir -p luaenv/Scripts && ln -s ../bin/python luaenv/Scripts/python.exe   # run_all hard-codes this path
export DISASTERZONE_ADDON_DIR=$PWD/../addon/DisasterZone           # default is C:\World of Warcraft\...
export DZ_SLOT_DIR=$PWD/.slots
luaenv/bin/python tools/test_harness_selftest.py                 # 13/13
luaenv/bin/python tools/check.py -q
luaenv/bin/python tf_e/run_all.py --all -j 12                    # ~5 min
DZ_FORK=0 luaenv/bin/python tf_e/run_all.py patch/ --all        # patch suites cannot fork
luaenv/bin/python tests/forever/test_forever_profile.py           # Forever mock profile, 7/7
luaenv/bin/python tests/forever/test_deadmines_replay.py          # Deadmines replay, 5/5 (~2 s)
luaenv/bin/python tests/forever/test_forever_names.py             # surnames, 5/5
luaenv/bin/python tests/forever/test_forever_professions.py       # recipes, 4/4
luaenv/bin/python tests/forever/test_forever_raids.py             # raid planner, 5/5
luaenv/bin/python tests/forever/test_forever_keys.py              # keyboard in combat, 4/4
luaenv/bin/python tests/forever/test_forever_secrets.py           # secret health / power / GUIDs, 6/6
luaenv/bin/python tests/forever/test_forever_quick_fixes.py       # sign-up level, phase words, PvP, 5/5
luaenv/bin/python tests/forever/test_forever_packs.py             # Rooms, Chess, Bingo, Azeromon, 5/5
luaenv/bin/python tests/forever/test_forever_class_tools.py       # specs, roles, class spells, 12/12
luaenv/bin/python tests/forever/test_forever_demos.py             # no TBC in demos, 5/5
```

- ⚠️ Never set `DZ_NATIVE_CACHE` under `/tmp`: it grew to 3.1 GB in one run.
- Two UI-audit suites load Segoe UI from a Windows path; substitute Noto Sans (card "Make the tests Linux-native").
- Known upstream failures at e21d5a9 (not Linux): `boot-ui/test_changelog`, `boot-ui/test_boot`, two Azeromon suites,
  `games/test_naxx`, 3 cases of `sync/test_mixed_versions` (missing private tag `release-1.4.0`), `test_testmap`
  (gitignored `Core/DevPlan.lua` listed in the TOC).

- Baseline 2026-11-08 (after PR #9): `run_all --all` = 307 suites, 17 failed, all the known ones above plus the
  `events` UI-QA suites (Segoe UI font) and the `patch/` suites under forking (run them with `DZ_FORK=0`: 2 left).
  More than that is a regression. Testing on Forever data: [[Testing with Forever Data]].

## Not in git

- `dev/luaenv/` (recreate above)
