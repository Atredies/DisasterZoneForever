---
title: "Replay real Forever sessions in the tests"
tags: [task]
status: 1 - In progress
priority: p1
effort: M
updated: 2026-11-08
---

# Replay real Forever sessions in the tests

Probe logs -> `dev/probe/export_replay.py` -> `dev/tests/forever/fixtures/*.json` -> replayed through a group of
Forever mock clients.

## State 2026-11-08

- Deadmines clear (9 pulls) replayed by `dev/tests/forever/test_deadmines_replay.py`, 5/5: restrictions match the
  recording, nothing on the wire during a pull, every message arrives after it, no errors, no forbidden actions.
- It found the ChatThrottleLib loss during pulls (fixed in `Core/Comm.lua`).

## Next

- Loot rolls from the recording (`loot-roll` events are in the fixture; replay ignores them for now).
- A raid session once probe round 2 has run with a group (roster secrets, master loot), then replay it.
- Run the ported raid-leader features (sign-ups, attendance, council) through the replay as they land.
