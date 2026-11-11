---
title: "Compat layer and Forever TOC"
tags: [task]
status: 1 - In progress
priority: p1
effort: L
updated: 2026-11-11
---

# Compat layer and Forever TOC

`Core/Compat.lua` + `## Interface: 16001`. Raise sync-validator limits (`MAX_ITEM_ID`, phases) before the first release, since they can only grow.

**Input from the probe (2026-11-08):** the replacement table, the name-normalisation point and the Comm encounter
queue in [[Probe Findings 2026-11-08]].

## State 2026-11-08

First pass on branch `feat/forever-compat`:
- `Core/Compat.lua` (3rd file in the TOC): ~30 old globals rebuilt from C_ replacements only when missing;
  `Compat:CanUseCombatLog()` (false on Forever); `Compat:InChatLockdown()`.
- `ns:RegisterEvent` (Core/Init.lua) and `StrategyLive` refuse COMBAT_LOG_EVENT_UNFILTERED on Forever (covers
  CombatLog, RaidLog, EventSensors, Bingo).
- `Core/Comm.lua` holds messages during the lockdown (max 300, live-only classes dropped), flushes on
  ADDON_RESTRICTION_STATE_CHANGED / ENCOUNTER_END / a 1 s ticker.
- All TOCs at Interface 16001. `dev/tests/compat/` 6/6 (mutation-checked). `dev/install_forever.sh`.

Left on purpose (callers already check for them): old talent tabs, trade skill/craft windows, GetNumBankSlots.
Not yet held during lockdown: direct senders in Patch.lua, ClassPlanner.lua, BossMod.lua, ReserveLR.lua.
Still to do: name normalisation for names with spaces (waits on probe round 2), raise sync-validator limits.
**Next check:** load it in game with Lua errors shown; fix what appears.

## Done when

The addon boots in the real Forever client with no Lua errors and syncs between two characters.
