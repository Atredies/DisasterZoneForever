---
title: "Event handover checks the send"
tags: [task]
status: 3 - To do
priority: p2
effort: S
updated: 2026-11-12
---

# Event handover checks the send

`Live:HandOver` (`Core/EventLive.lua:617-631`) clears `hosting[occId]` right after sending the EVS, without checking `Send`'s return value. If the message does not go out (guild not known yet after a /reload, state too large, demo), nobody hosts the live event, the named player never hears of it, and the run waits for the takeover timer. Keep hosting and report the failure when the send fails. See `02-Architecture/Implicit State Machines.md`.

## Done when

A test with a failing `Comm:Send` shows `HandOver` returning false with a reason and `Live:IsHosting(occId)` still true. The normal handover test still passes.
