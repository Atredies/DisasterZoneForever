---
title: "Port the mock client to 1.60.1"
tags: [task]
status: 5 - Done
completed: 2026-11-08
priority: p1
effort: L
updated: 2026-11-08
---

# Port the mock client to 1.60.1

`dev/tools/wowmock`: Forever profile with GetBuildInfo 1.60.1/16001, retail loot list, `TooltipDataProcessor`, `C_EditMode`, lockdown send result, secret values, removed classic functions. Driven by the probe results.

## Done when

Harness self-test and a Forever-profile boot test pass.

## Done 2026-11-08

`Client(..., forever=True)` loads `dev/tools/wowmock/forever.lua` with facts generated from the probe run
(`dev/probe/mock_facts.py`). Harness self-test 13/13; `dev/tests/forever/test_forever_profile.py` 7/7 (boot on
Forever, removed globals, forbidden combat log, pull lockdown in the client's order, secret values, auras in combat,
`TooltipDataProcessor`). Not modelled yet: names with spaces / the spaced realm, Map-restriction effects, battlegrounds.
