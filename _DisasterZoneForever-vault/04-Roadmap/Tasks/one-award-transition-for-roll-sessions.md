---
title: "One award transition for roll sessions"
tags: [task]
status: 3 - To do
priority: p2
effort: M
updated: 2026-11-12
---

# One award transition for roll sessions

A roll session becomes `awarded` in three places that each write the award fields by hand, and each writes a different subset: `Finish` (`Core/Roll.lua:1948`), `MarkAwarded` (`:2210`, loot message) and `OnRollWin` (`:2764`, remote award). Fold them into one helper that sets `state, winner, given, via, looted, lootPrev, awardedBy, awardedAt, awardTs, reason, final` with the source (mine, loot, remote) as a parameter. See `02-Architecture/Implicit State Machines.md`.

## Done when

`ses.state = "awarded"` appears once in `Core/Roll.lua`, and the existing roll suites (award, crossed awards, loot conflict, reclaim) pass unchanged.
