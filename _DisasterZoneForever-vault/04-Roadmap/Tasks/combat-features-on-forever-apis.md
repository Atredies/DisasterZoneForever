---
title: "Combat features on Forever APIs"
tags: [task]
status: 1 - In progress
priority: p2
effort: L
updated: 2026-11-09
---

# Combat features on Forever APIs

Meters, boss mods, My Log, combat text, swing/shot timers rebuilt on `C_DamageMeter`, `C_EncounterTimeline`, `C_SwingTimer`, or dropped.

## Done when

Each combat feature either works in a Forever raid or is removed with a changelog line.

## Secret values, state 2026-11-09

On Forever `UnitHealth`, `UnitHealthMax`, `UnitPower` and `UnitRangedDamage` are secret numbers: an addon may hand
them to a widget but not compare them or do arithmetic (see [[Probe Findings 2026-11-08]]).
- Fixed after in-game errors: `Core/Resource.lua` (bar off on Forever, tick tracking skips secrets),
  `Core/ShotTimer.lua` (ranged speed from casts).
- ~~Still reading these values (13 files, 28 calls)~~ **Guarded 2026-11-09** through `Compat.Plain` / `HealthPct` /
  `PowerPct` / `GUID` (Changelog, `tests/forever/test_forever_secrets.py`): no Lua error, but the features that need
  the numbers go quiet (HP alerts, execute phase, low health) and bars show full without numbers.
- **Next:** real bars by handing the secret straight to a StatusBar (`SetMinMaxValues(0, UnitHealthMax(u))`,
  `SetValue(UnitHealth(u))`; check the Forever UI source for `UnitHealthPercent` and curve objects), then each combat
  feature on `C_DamageMeter` / `C_EncounterTimeline` or removed. UNVERIFIED: whether `UnitInRange`,
  `UnitThreatSituation`, `UnitGetIncomingHeals` and aura fields are secret too (guarded anyway).

## 2026-11-09: secret table keys
Besides arithmetic and comparisons, a secret may not be a **table key** (index or assignment): seen in game with
nameplate GUIDs (UI/CombatText.lua, fixed; Core/StrategyLive.lua, fixed). Any `t[UnitGUID(unit)]` on a non-player
unit inside an instance must check `Compat.IsSecret` first. The mock can't raise this one (its secrets are tables).

## 2026-11-09: swings from PLAYER_SWING

The paladin / warrior swing timers take swings from `C_SwingTimer`'s `PLAYER_SWING` on Forever (PR #37); UNVERIFIED
that it reaches an addon. Council Bingo polls deaths from the group instead of the combat log (PR #36).
