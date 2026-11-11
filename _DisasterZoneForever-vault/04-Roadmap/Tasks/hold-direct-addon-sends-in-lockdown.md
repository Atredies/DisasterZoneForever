---
title: "Hold the direct addon sends during a pull"
tags: [task]
status: 5 - Done
completed: 2026-11-09
priority: p2
effort: S
updated: 2026-11-08
---

# Hold the direct addon sends during a pull

`Core/Comm.lua` now holds messages through the encounter chat lockdown, but four places send without Comm:
`Core/Patch.lua` (in-game update chunks), `Core/ClassPlanner.lua`, `Core/BossMod.lua` (DBM/BigWigs break timer),
`Core/ReserveLR.lua` (LootReserve compatibility). During a pull their messages are refused. Route them through the
same hold, or skip and retry after the pull.

## Done when

None of the four loses a message sent during a simulated lockdown (dev/tests/compat).
