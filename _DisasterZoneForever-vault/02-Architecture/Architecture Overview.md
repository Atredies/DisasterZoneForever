---
tags: [architecture]
updated: 2026-11-11
---

# Architecture Overview

The original's architecture carries over. Read the deep-dive reports (`09-Reference/Deep Dive/`) for detail:

| Layer | Report | Upstream docs |
|---|---|---|
| Boot, modules, persistence, comms protocol | `DZ Deep Dive 01-core-framework` | `dev/docs/SPEC.md`, `MODULES.md`, `ARCHITECTURE_PLAN.md` |
| Roles and leader features | `DZ Deep Dive 02-roles-and-leadership` | `SPEC_ADDENDUM_*`, `groups/`, `reserves/`, `EVENTS.md` |
| Game data and generators | `DZ Deep Dive 03-game-data-and-content` | `dev/generators/` |
| Test harness, mock client, run_all | `DZ Deep Dive 04-testing` | `dev/tools/README.md` |
| In-game updates | (no report) | `dev/docs/HOTPATCH.md` |
| UI framework and the WoW API surface | `DZ Deep Dive 07-ui-and-api-surface` | `dev/docs/research/api.md` |

## Forever-specific architecture (planned)

- `Core/Compat.lua`: capability flags, same-shape wrappers for both clients, secret-safe reads, a send queue that holds
  addon messages during lockdown, per-client Blizzard frame-name lists.
- A Forever TOC with `## Interface: 16001`.
- Combat features rebuilt on `C_DamageMeter`, `C_EncounterTimeline`, `C_SwingTimer`, or dropped.
- Mock client (`dev/tools/wowmock`) gains a 1.60.1 profile: retail loot list, `TooltipDataProcessor`, `C_EditMode`,
  the lockdown send result, secret values.
