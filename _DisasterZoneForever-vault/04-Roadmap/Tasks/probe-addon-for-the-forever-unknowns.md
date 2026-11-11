---
title: "Probe addon for the Forever unknowns"
tags: [task]
status: 5 - Done
completed: 2026-11-08
priority: p1
effort: M
updated: 2026-11-11
---

# Probe addon for the Forever unknowns

A tiny Forever addon that records, to SavedVariables: `GetBuildInfo`, `WOW_PROJECT_ID`, `loadstring`, `LoadSavedVariablesFirst`, master loot / `GetLootMethod`, `GetGuildRosterInfo` + officer notes, `OnTooltipSetItem` vs `TooltipDataProcessor`, combat-log registration, `C_ChatInfo.SendAddonMessage` result codes in and out of combat / boss fights / battlegrounds, secret values in the open world. A script turns the output into mock facts.

## State

Built and installed in the Forever AddOns folder (`dev/probe/`, see its README). Offline test 27/27 on Lua 5.1 and LuaJIT.
Solo passive logger: no second character, so party/raid messages and setting master loot wait for a
group. To run it: log in, `/reload` once, play (ideally one dungeon boss and one battleground), then
`python3 dev/probe/read_probe.py`.

**First in-game run, 2026-11-08 (Stormwind, open world):** 0 handler errors; all 77 C_ present, 252/348
globals, 122/142 events. Registering `COMBAT_LOG_EVENT_UNFILTERED` raises ADDON_ACTION_FORBIDDEN and the
"Blizzard UI only" popup on every load, so the probe no longer tries (PR #4). Guild roster rows readable, GM
detected, officer notes viewable and editable. Addon messages GUILD/WHISPER work (~0.3 s). Old talent API gone,
C_Traits/C_ClassTalents present.

**Full run done 2026-11-08** (~4 h, full Deadmines clear). No `action-forbidden` after the PR #4 fix. Conclusions in
[[Probe Findings 2026-11-08]], numbers in [[Forever Client Facts]]. Group-only questions moved to
[[probe-round-2-group-and-raid]].

## Done when

Probe run once in the real client; results written into `09-Reference/Forever Client Facts.md`.
