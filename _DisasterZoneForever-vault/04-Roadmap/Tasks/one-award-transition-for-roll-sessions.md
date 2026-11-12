---
title: "One award transition for roll sessions"
tags: [task]
status: "5 - Done"
completed: 2026-11-12
priority: p3
effort: M
updated: 2026-11-12
---

# One award transition for roll sessions

## Context

A loot roll session (`Core/Roll.lua`) is one item put up for loot council or a plain roll. It lives in the in-memory `sessions` table and is created by `NewSession :325` (remote, `open`) and `NewLocalSession :342` (mine, `queued`). States: queued, open, closed, awarded, cancelled. Once awarded, sub-flags record the hand-out: `winner, given, via, looted, lootPrev, lootOther, awardedBy, awardedAt, awardTs, reason, final`.

It reaches `awarded` three ways:
- my own award: `Finish :1895-1996`, from `Award`, `ConfirmAward` and `MarkAwardedExternally`
- a loot chat line names who got the item: `MarkAwarded :2200-2221`, called from `OnItemLooted :2370`
- another council member's or the master looter's award arrives as RW: `OnRollWin :2700-2785`

Awards feed the council ledger, so they decide who got which item.

## What was found

Each of the three paths writes the award fields by hand, and each writes a different subset:

| Field | Finish (`:1948-1958`) | MarkAwarded (`:2210-2218`) | OnRollWin (`:2764-2774`) |
|---|---|---|---|
| `via` | nil | `via` ("loot") | nil |
| `looted` | kept or set | `via == "loot"` | untouched (true only if loot-marked) |
| `lootPrev` | nil | previous state | nil |
| `awardedBy` | me | **nil** | sender |
| `awardTs` | server time | **nil** | the sender's `at` (may be nil) |
| `reason` | computed | **untouched** | from the message |
| `prized` | cleared (`:1921`) | untouched | untouched |
| `final` | rebuilt at the end (`:1993`) | rebuilt | rebuilt |
| `closedAt` / `endsAt` | via `CloseSession` | set inline | via `CloseSession` |

Some differences are intentional: a loot mark is provisional, so it has no `awardedBy`. Others are accidental: `reason` and `prized` survive a loot mark or a remote award. Concrete scenario: my client has a pending prized-item override (`ses.prized` set by `PrizedGate`). A remote RW awards the item, and `prized` stays on the session. A later local upgrade of a loot mark then logs a stale "override: ..." note.

Impact: no wrong award or ledger entry was found. The risk is maintenance. A new award field, or a fix to crossed-award resolution (`AwardBeats`, which reads `given`, `awardTs` and `awardedAt`), has to be made three times. Likelihood is low today. **Priority lowered from medium (p2) to low (p3) on re-verification:** no live defect, only duplication.

## How it was found

State-machine audit 2026-11-12 (prompt: 'Find all the implicit state machines in my app'), read-only code trace from ~/claude-code. I listed every `ses.state = ...` assignment in `Core/Roll.lua` (`grep -n 'state = "' addon/DisasterZone/Core/Roll.lua`) and compared the field writes of the three award paths, giving the table above.

Code reading only, not reproduced. To confirm the field drift, add a harness case to `dev/tests/loot-roll/test_award.py` that awards one session each way (Alice's `MarkAwardedExternally`, a loot message through `w.broadcast_loot_received(...)` (as in `test_roll_close_core.py`), Bob's award arriving as RW) and dumps the award fields for comparison. Run it with `dev/luaenv/bin/python dev/tests/loot-roll/test_award.py -k <name>` and `DISASTERZONE_ADDON_DIR=addon/DisasterZone`.

## Best fix

Add one local `SetAwarded(ses, key, src)` in `Core/Roll.lua`, where `src = { kind = "mine"|"loot"|"remote", given, via, by, ts, reason }`. It:
- closes or dequeues according to the previous state (`CloseSession` if open, `RemoveFromQueue` if queued) and sets `lootPrev` for the loot kind only
- sets `state = "awarded"`, `winner`, `given`, `via`, `looted`, `awardedBy`, `awardedAt`, `awardTs` and `reason` from `src`
- clears `prized`, `final` and `lootOther` unless they are carried over on purpose
- rebuilds `final` and calls `Updated`

`Finish`, `MarkAwarded` and `OnRollWin` keep their checks and side effects (ledger, announce, prized record, RW send) and call `SetAwarded` for the state change. No data migration: sessions are memory-only.

Tests: run the existing `dev/tests/loot-roll/` suites (`test_award.py`, `test_rolls.py`, `test_bag_loot.py`, `test_duplicate_items.py`, `test_ledger_auto.py`) unchanged. Add `award_fields_are_the_same_whichever_way_it_was_awarded` (the case above), asserting the documented field set for each `kind`.

## Why this approach

- **Alternative: a full transition table (`state x event -> state`) for sessions.** The guards in this file are already correct and well tested. A table would rewrite all of them for no behaviour gain. Only the award write is duplicated.
- **Alternative: leave it and add comments.** Comments do not stop drift. The table above shows two accidental differences already.
- One setter per transition matches the file's own pattern for close and cancel: `CloseSession` and `CancelSession` are single functions every path calls.

## Done when

- `grep -c 'state = "awarded"' addon/DisasterZone/Core/Roll.lua` returns 1.
- `award_fields_are_the_same_whichever_way_it_was_awarded` passes, as do all of `dev/tests/loot-roll/`.

## Fix (2026-11-12)

Done as the card's best fix with two corrections found while re-reading the code, branch `fix/state-machines`.

- **What changed:** `Core/Roll.lua` gains one local `SetAwarded(ses, key, src)` (`src.kind` = "mine" / "loot" / "remote"), the only `state = "awarded"` in the file (`grep -c` gives 1). It closes an open session (CloseSession; a loot mark closes inline as before), dequeues a queued one, and sets `winner, given, via, looted, lootPrev, awardedBy, awardedAt, awardTs, reason, final` per kind. `Finish`, `MarkAwarded` and `OnRollWin` keep their guards and side effects (ledger, prized record, RW, announce, loot conflict) and call it.
- **Behaviour change:** a loot mark now clears `reason` (it is provisional: no reason, like no `awardedBy`). Everything else each path wrote is unchanged.
- **Corrections to the card:**
  - `prized` is **not** cleared by a loot mark or a remote RW. It is not stale there: my own master-loot hand-out sets it in `PrizedGate`, the loot message arrives first (`MarkAwarded`), and the hand-out callback then calls `Finish`, which reads it for `Prized:RecordGiven`. Same after a crossed RW, when my physical hand-out wins (`ConfirmGive`). `Finish` still clears it.
  - `lootOther` is left alone: no path cleared it before, and `FlagLootConflict` sets it after the award.
  - `Updated` stays with the callers, because each fires it at a different point (Finish and OnRollWin after the ledger).
- **Protocol:** no message changed.
- **Test added** (`dev/tests/loot-roll/test_award.py`): `award_fields_are_the_same_whichever_way_it_was_awarded`. My award (`MarkAwardedExternally`) and the RW another client receives leave identical fields; a loot mark leaves the loot fields with no reason even when one was left on the session. Fails on the old code (stale `reason`), passes now.
- **Side-effect audit:** `Finish` callers: Award / ConfirmGive / ConfirmAward / MarkAwardedExternally and the demo award. `MarkAwarded` caller: `OnItemLooted`. `OnRollWin`: the RW handler. Readers of the fields (`AwardBeats`, `LootMarked`, `MarkGiven`, the drop panel, the award log) see the same values as before except `reason` on loot marks, which the drop panel does not show for loot marks, and `MarkGiven` only sends for non-loot awards.
- **Checks:** all of `dev/tests/loot-roll/`, `rollclose/`, `prized/` and `council/` pass (17 suites); full harness run listed in the PR.

## Related

- [[Implicit State Machines]]
- [[demo-toggle-cancels-rolls-for-everyone]]
- [[pug-friendly-rolls]]
