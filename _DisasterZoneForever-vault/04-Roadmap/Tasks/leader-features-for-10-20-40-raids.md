---
title: "Leader features for 10/20/40 raids"
tags: [task]
status: 1 - In progress
due: 2026-11-12
priority: p1
effort: L
updated: 2026-11-12
---

# Leader features for 10/20/40 raids

Council, reserves, raid plans, sign-ups, attendance, audit, polls, recruit with Forever raid sizes, level 60 and phases. Redesign the hand-out if master loot does not exist.

## Must include: the raid session crest

TBC raid leaders use it (for example: "Zul'Aman · Regular ZA Team 2 · T2: Lag Spike · 7 of 11 here",
the loot council / rolls / BiS lock switches and one-click **Start raid**). Code: `UI/SessionBar.lua` (crest + line),
`UI/SessionDrawer.lua` (bosses with Strategy / Pull 10 / Break 5, loot, council, attendance, link, End raid),
`Core/SessionInfo.lua` (the one table both draw from). Setting `sessionBar.show`: auto / always / lead / never.

Forever checks:
- Boss beads (killed / being fought) come from encounter events: the probe logs whether `ENCOUNTER_START` / `ENCOUNTER_END`
  payloads are secret on Forever.
- "x of N here" needs the raid roster + zone; N must allow 10 / 20 / 40.
- Pull 10 / Break 5 and the drawer's council and loot actions send addon messages: hold them through a lockdown
  (`AddOnMessageLockdown`) instead of dropping them.
- In a boss fight the crest shows the boss and fight time: check the timer still works if encounter values are secret.

Not urgent, but part of this card's scope.

## Done when

Used in a first guild raid on or after 9 Dec 2026.
