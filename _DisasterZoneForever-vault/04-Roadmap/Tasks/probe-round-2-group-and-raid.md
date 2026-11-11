---
title: "Probe round 2: group and raid"
tags: [task]
status: 2 - Next up
priority: p2
effort: S
updated: 2026-11-11
---

# Probe round 2: group and raid

Questions the solo run could not answer: master loot handing out an item, whether `GetRaidRosterInfo` /
`UnitName("raidN")` are secret inside a raid instance, the raw `GetGuildRosterInfo` name format (names have spaces),
and battleground (PvPMatch) behaviour. Add a raw roster-name log line and a raid-roster sample to the probe, then run
it during a guild group or raid. See [[Probe Findings 2026-11-08]].

**Built 2026-11-08** (probe version 2, installed): raid roster readability per field, master-loot candidates,
loot-method changes, roll items, own name forms, roster name shapes. Steps in `dev/probe/README.md`. **Waiting on:**
a session with a group (party -> raid, master loot hand-out, a group-loot roll).

## Done when

Each of the four questions has a measured answer in [[Forever Client Facts]].
