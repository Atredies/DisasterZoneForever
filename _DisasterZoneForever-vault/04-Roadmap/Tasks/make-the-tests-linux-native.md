---
title: "Make the tests Linux-native"
tags: [task]
status: 3 - To do
priority: p2
effort: M
updated: 2026-11-08
---

# Make the tests Linux-native

Remove the Windows assumptions found in the deep dive (`luaenv/Scripts/python.exe`, `C:\` addon path, Segoe UI fonts, patch suites under fork). Add a GitHub Actions workflow running `check.py` + `run_all.py` on Ubuntu.

## Done when

`run_all.py --all` green in CI on every PR, no env workarounds.
