---
title: "Invite & sort follows the raid"
tags: [task]
status: 3 - To do
priority: p2
effort: S
updated: 2026-11-12
---

# Invite & sort follows the raid

`DeleteRaid` stops a running Invite & sort for that raid (`Core/RaidPlan.lua:3856`), but `CancelRaid` (`:3830`) does not, and a cancel or delete that arrives from another planner through the sync never stops it. The run keeps inviting and sorting the planned layout (`Core/RaidInvite.lua:247-273`). Have `Pump` check the raid itself (gone or cancelled: stop, and say why). See `02-Architecture/Implicit State Machines.md`.

## Done when

A test cancels the raid locally, and another one merges a remote cancel and a remote delete, while a run is active: in each case `RaidInvite:IsActive()` is false after the next pump and no further invite goes out.
