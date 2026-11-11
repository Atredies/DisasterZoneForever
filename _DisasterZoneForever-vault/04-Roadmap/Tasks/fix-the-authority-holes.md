---
title: "Fix the authority holes"
tags: [task]
status: 5 - Done
completed: 2026-11-09
priority: p1
effort: M
updated: 2026-11-08
---

# Fix the authority holes

Officer can forge GM rules (`Core/Guild.lua:1647-1663`); any assist can replace reserves (`Core/Reserves.lua:603-608`); first-seen raid plan trusts its author; officer hard-coded to rank <= 1; dev recognised by name. Each with a hostile test.

## Done when

Hostile tests for all five pass.
