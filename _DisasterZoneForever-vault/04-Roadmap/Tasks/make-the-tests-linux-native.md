---
title: "Make the tests Linux-native"
tags: [task]
status: 3 - To do
priority: p2
effort: M
updated: 2026-11-15
---

# Make the tests Linux-native

Remove the Windows assumptions found in the deep dive (`luaenv/Scripts/python.exe`, `C:\` addon path, Segoe UI fonts, patch suites under fork). Add a GitHub Actions workflow running `check.py` + `run_all.py` on Ubuntu.

## Done when

`run_all.py --all` green in CI on every PR, no env workarounds.

## Progress (2026-11-15)

`run_all --all` is green on Linux (327 suites): the UI-audit font falls back to Liberation Sans / Noto Sans
(`tools/ui_audit.py`, or `DZ_PROXY_FONT`), `test_mixed_versions` uses the "Release 1.4.0" commit when the tag is
missing, the time-of-day Azeromon cases pin noon. Left: the `luaenv/Scripts/python.exe` symlink and a GitHub Actions
workflow.
