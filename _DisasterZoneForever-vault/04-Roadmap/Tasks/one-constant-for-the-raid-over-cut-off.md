---
title: "One constant for the raid-over cut-off"
tags: [task]
status: 3 - To do
priority: p3
effort: S
updated: 2026-11-12
---

# One constant for the raid-over cut-off

## Context

A planned raid (`Core/RaidPlan.lua`) is open for sign-ups until 6 hours after its start time. After that it counts as over: no answers, shown dimmed as "past", left out of upcoming lists. The core holds the rule as `SIGNUP_CLOSE = 6 * 3600` (`Core/RaidPlan.lua:62`) and uses it in `SignUp` (`:4105`), `SignUpFor` (`:4059`), the live sign-ups sent at login (`:2654`, `:2726`) and the series end checks (`:4210-4213`). Who moves the state: nobody. It is derived from the clock on every read.

## What was found

The UI repeats the rule as a literal `6 * 3600` 13 times in `UI/RaidPlanUI.lua` (`:212, 234, 247, 282, 481, 534, 594, 661, 817, 1066, 1768, 2177, 2803`). It decides there whether a raid is listed, shown as past, and whether the answer buttons are live. If someone changes `SIGNUP_CLOSE` (say to 3 h), the core refuses sign-ups at 3 h while the UI still offers the buttons until 6 h, and the user gets "This raid is over." from a button the UI showed as open.

Impact: none today, because the values agree. It is a trap for the next change. Low.

Corrected during re-verification: the audit note first counted `Core/Events.lua:1054` (guild events: "missed" 6 h after start) as the same rule. It is a separate machine (guild event occurrences, not raids) and is left out here. `Core/GuestBook.lua:47` (`NEXT_RAID_SLACK`, also 6 h) is a related but separately named rule for guests. Leave it, or tie it to the same constant if the owner wants guests to follow the sign-up close.

## How it was found

State-machine audit 2026-11-12 (prompt: 'Find all the implicit state machines in my app'), read-only code trace from ~/claude-code. Found with `grep -rn '6 \* 3600' --include=*.lua addon/DisasterZone` plus a check of each hit's meaning. Code reading only. Nothing to reproduce while the values agree.

## Best fix

- Expose the rule from the core: `RaidPlan.SIGNUP_CLOSE = SIGNUP_CLOSE` and a method `RaidPlan:IsOver(v, now)` (`v.t < (now or Now()) - SIGNUP_CLOSE`).
- Replace the 13 UI literals with `RP():IsOver(v)`, or `RP().SIGNUP_CLOSE` for the list queries at `:534` and `:2803`.
- Use `IsOver` in the core's own checks (`:4059`, `:4105`) too, so there is one definition.
- No migration.

Test: `dev/tests/raidplan/test_raidplan_page.py` gains `past_cut_off_follows_the_core_constant`. It patches `ns.RaidPlan.SIGNUP_CLOSE` to 3 h in one client, opens a raid 4 h after its start, and asserts that the answer buttons are hidden and `SignUp` refuses.

## Why this approach

- **Alternative: a shared `local SIX_HOURS` in the UI file.** That removes the duplication inside the UI but not between UI and core, which is where drift would hurt.
- A method rather than only the constant keeps the comparison (`<` vs `<=`, the `now` source) in one place. The UI already calls `RP()` for everything else about a raid.

## Done when

- `grep -n '6 \* 3600' addon/DisasterZone/UI/RaidPlanUI.lua` finds nothing.
- `past_cut_off_follows_the_core_constant` passes, and all of `dev/tests/raidplan/` passes.

## Related

- [[Implicit State Machines]]
- [[one-sign-up-path-for-game-and-discord]]
