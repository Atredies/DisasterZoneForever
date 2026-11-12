---
title: "One sign-up path for game and Discord"
tags: [task]
status: 3 - To do
priority: p2
effort: M
updated: 2026-11-12
---

# One sign-up path for game and Discord

`RaidPlan:SignUp` (`Core/RaidPlan.lua:4090`) and `RaidPlan:SignUpFor` (`:4052`, Discord via `Core/Bridge.lua:703`) each re-implement the checks (cancelled, over, status, block) and the rev rules, and have drifted: lock is a request in one and a refusal in the other, alt characters come from `GetMyCharacters()` vs `Linked(key)`, and an over-long note is refused vs cut. Move the checks and rev rules into one shared function. Keep the deliberate differences explicit as parameters. See `02-Architecture/Implicit State Machines.md`.

## Done when

Both functions call one shared validator and rev builder. A table-driven test runs every block (cancelled, over, blacklist, declined, lock, level, removed) through both paths and gets the documented result for each.
