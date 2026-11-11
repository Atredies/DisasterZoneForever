---
title: "Raid lockouts: who is saved"
tags: [task]
status: 3 - To do
priority: p2
effort: M
updated: 2026-11-11
---

# Raid lockouts: who is saved

Show who in the guild is already saved (IDed) to each raid, like Nova Instance Tracker,
including alts and boss progress, in the raid planner and on the Groups board. Most of the plumbing exists
(`Core/DungeonRuns.lua` `ScanSaved`, the `DRP` field `rs`). Plan and steps: [[Adding a Feature]] > Worked example.

Blocked in part until 2026-12-09: Barrow Deeps and Hyjal Summit instance ids come from `/dz raiddata` in each raid.

## Done when
A member saved to a raid shows as saved (with boss count and reset day) next to their sign-up in every other
member's raid planner, alts included, with a mock test and a hostile test.
