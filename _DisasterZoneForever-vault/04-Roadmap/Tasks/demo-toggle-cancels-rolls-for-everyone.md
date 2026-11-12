---
title: "Demo toggle cancels rolls for everyone"
tags: [task]
status: 3 - To do
priority: p3
effort: S
updated: 2026-11-12
---

# Demo toggle cancels rolls for everyone

## Context

Loot roll sessions (`Core/Roll.lua`) go queued, open, closed, awarded or cancelled. Every client holds its own copy of a session. The starter's RS opens it everywhere, and the starter's RE closes it (or cancels it, with `x`) everywhere (`OnRollEnd :2629-2642`). The normal way to cancel is `CancelSession` (`:578-590`), which also fires `OnSessionFinished` so the queue advances. Demo mode (`Core/Demo.lua:257`, `Demo:SetEnabled`) is a local practice mode. Turning it on fires `DEMO_TOGGLED`, which `Roll`'s `OnDemoToggled` (`:2807-2826`) handles.

## What was found

1. Alice, the master looter, has a real roll open for Ruby Drape. Every raider sees it open.
2. Alice turns demo mode on (or off).
3. `OnDemoToggled` sets `ses.state = "cancelled"` directly on her open and queued sessions (`:2815`). It does not go through `CancelSession` and sends no RE: in demo mode `Send` is off, and the handler does not send before switching.
4. On every other client the roll stays open until their own timer, then closes as a normal roll (`closed`, awardable). On Alice's client it is `cancelled`.

The states disagree for good: a council member can award a roll the master looter's client calls cancelled, and Alice gets no "give item" flow for it. Impact: low. It takes a master looter switching demo mode during a live roll, but the result is confusing loot handling at the moment it matters.

## How it was found

State-machine audit 2026-11-12 (prompt: 'Find all the implicit state machines in my app'), read-only code trace from ~/claude-code. I traced which state changes in `Core/Roll.lua` bypass `CloseSession` and `CancelSession`.

**Reproduced** with the repo's harness from a scratch script outside the repo (`smrepro/repro_demo.py`, built on `dev/tests/loot-roll/test_rolls.py`'s `setup` and `panel_start`):
- Alice turns demo on during an open roll. Alice is `cancelled`, the other six clients are `open`, and Alice sent 0 addon messages.
- +40 s: the others are `closed`. Alice is still `cancelled`.
- Bob (council) awards it (`MarkAwardedExternally`): the six others show `awarded`, Alice stays `cancelled`. The award did reach the ledger on both.

## Best fix

In `OnDemoToggled` (`Core/Roll.lua:2807`), for each real (non-demo) session I started (`ses.isLocal`) that is open, send `Send({ t = "RE", id = ses.id, x = true }, true)`. The file's `Send` already takes `real = true` to go out while demo mode is on (`:222-223`; `DEMO_TOGGLED` fires after the flag flips, `Core/Demo.lua:267-268`). Then cancel through `CancelSession(ses)` instead of writing `state` directly. Remote sessions I did not start: leave the wire alone. Demo mode only hides them locally, and they are someone else's. No migration: sessions are memory-only.

Test to add in `dev/tests/loot-roll/test_rolls.py`: `demo_toggle_mid_roll_cancels_it_everywhere`. Alice starts a roll and turns demo on. All seven clients show `cancelled` within 1 s.

## Why this approach

- **Alternative: keep the roll open across the demo toggle.** Demo mode replaces the roll UI with made-up sessions, so the master looter could not see or award the real roll. Cancelling is right; it only needs to be done for everyone.
- **Alternative: refuse to toggle demo mode during an open roll.** Simple, but it blocks an innocent action with a popup. The cancel path already exists, so using it is the smaller change.
- Using `CancelSession` and RE x matches how every other cancel in the file works (`Preempt :612-629`).

## Done when

- `demo_toggle_mid_roll_cancels_it_everywhere` passes, and all of `dev/tests/loot-roll/` passes.
- `repro_demo.py` shows every client `cancelled` right after the toggle.

## Related

- [[Implicit State Machines]]
- [[one-award-transition-for-roll-sessions]]
