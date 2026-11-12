---
title: "Event handover checks the send"
tags: [task]
status: 3 - To do
priority: p2
effort: S
updated: 2026-11-12
---

# Event handover checks the send

## Context

A live guild event (a duel cup, a race and so on) is run by exactly one client, the host. Everyone else watches. The role lives in two module tables in `Core/EventLive.lua`: `hosting[occId]` (I run it) and `seen[occId]` (someone else does, with their last state). How the role moves:
- start (`Live:Start :519`)
- the host hands it to an online member (`Live:HandOver :617`)
- a newer state from another host replaces mine (`OnState :1122-1150`)
- if the host goes silent, the entrants take over one at a time in name order (`CheckTakeover :1406`, `Resume :558`)

The run's state is broadcast as EVS on GUILD. While nobody hosts, nothing advances: no matches are decided and no stages move. Guild members are standing in a live event waiting.

## What was found

1. Gina hosts a live cup and hands it to Cora (`HandOver`, from the Live panel).
2. `HandOver` (`Core/EventLive.lua:617-631`) calls `Send({ t = "EVS", ... }, "GUILD")` and ignores the result. It then sets `seen[occId]` with Cora as host and clears `hosting[occId]`.
3. `Send` (`:101-105`) returns false when `Comm:Send` refuses the message: demo mode, `ns.loggedIn` not set, not in a guild yet after a /reload, an encode error, or a state too large to send (`Core/Comm.lua:326-344`).
4. Result: Gina no longer hosts, Cora never heard she should, and the event has no host. After the silence timeout the first entrant in name order takes over from the last state they saw. That is not the person Gina chose, and the takeover may lose the latest changes.

Impact: a live event stalls for about 90 seconds, then continues under the wrong host. `HandOver` returns true, so the UI tells Gina it worked. The trigger is uncommon: most handovers happen in a healthy session. But a large state (many entrants and moments) is exactly when a refusal for size can happen.

## How it was found

State-machine audit 2026-11-12 (prompt: 'Find all the implicit state machines in my app'), read-only code trace from ~/claude-code. I traced the host role's transitions in `Core/EventLive.lua` and which of them check `Send`'s result. `SendState` does (`h.dirty = not Send(...)`, `:604`); `HandOver` does not.

**Reproduced** with the repo's harness from a scratch script outside the repo (`smrepro/repro_handover.py`, built on `dev/tests/events/test_edge_live.py`'s `guild` and `cup` helpers). On Gina's client, `Comm:Send` was stubbed to refuse EVS once, simulating any of the refusal causes above, and then `HandOver(occ, 'Cora-Thunderstrike')` was called:
- `HandOver` returned `true`, with 1 EVS refused.
- +3 s to +60 s: no client hosts. Gina's and Cora's `IsHosting` are both false.
- +90 s: Bert hosts (takeover by name order), not Cora.

Not reproduced: a real refusal cause, as opposed to the stub. Confirm one with a test that fills a cup past the GUILD size cap and hands it over, or calls `HandOver` in the first second after a /reload.

## Best fix

In `Live:HandOver` (`Core/EventLive.lua:617`):

```lua
local ok = Send({ t = "EVS", o = occId, h = key, s = Outgoing(h.run), c = chain }, "GUILD")
if not ok then
    h.run.st.host = Me()          -- undo the host change on my run
    return false, "Could not reach the guild: you still host it."
end
-- only now: seen[occId] = ..., hosting[occId] = nil
```

Set `h.run.st.host = key` only after a successful send, or restore it on failure as above. The UI caller already shows `HandOver`'s error string (see `handover_needs_someone_online` in `test_edge_live.py`).

Test to add in `dev/tests/events/test_edge_live.py`: `handover_keeps_the_host_when_the_state_cannot_go_out`. Stub `Comm:Send` on the host to refuse EVS, call `HandOver`, and assert `[False, <reason>]`, `IsHosting` still true on the host, and `hosts_of(...) == [host]` after 120 s.

## Why this approach

- **Alternative: hand over, then wait for an ack from the new host before dropping the role.** That is more robust (it also covers a message that was sent but lost), but it needs a new message type and a timeout state, and the handover is rare. The EVS that the new host broadcasts when it resumes already acts as an implicit ack, and `OnState` (`:1138-1150`) resolves any overlap.
- **Alternative: retry the send.** A refusal for size or for "not in guild" will not fix itself in a second, and a retry loop adds another state.
- Checking the return value matches how `SendState` (`:604`) already handles the same `Send`.

## Done when

- `handover_keeps_the_host_when_the_state_cannot_go_out` and the existing `handover_needs_someone_online` pass.
- `repro_handover.py` shows `HandOver` returning false and Gina still hosting.

## Related

- [[Implicit State Machines]]
- [[hold-direct-addon-sends-in-lockdown]] (the send hold during a pull, done)
