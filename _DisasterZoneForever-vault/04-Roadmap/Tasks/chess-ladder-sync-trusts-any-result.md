---
title: "Chess: ladder sync trusts any result"
tags: [task]
status: 3 - To do
priority: p3
effort: S
updated: 2026-11-12
---

# Chess: ladder sync trusts any result

## Context

Found while fixing [[chess-results-need-both-sides]] (2026-11-12). The Chess ladder catches up at login: CHQ (digest on GUILD) -> CHN (I have more) -> CHY (send me yours) -> CHZ (whispered result lists). `handlers.CHZ` (`DisasterZone_Chess/Chess.lua`) calls `AddResult` for every entry, from any sender, with no check that the sender played the game or concedes it.

## What was found

Bob whispers `CHZ { list = { { "forged-2", "Bob-...", "Alice-...", "1-0", <now>, 40 } } }` to each guild member (or answers a CHY with it). Every receiver adds a Bob win over Alice. The CHL "concede, not claim" rule does not cover this path, so rating farming is still possible, just less direct.

## Best fix

Options, from simplest:
- Take CHZ only as an answer to my own CHY (remember whom I asked, accept from that sender once, for a short window). Limits who can push, does not stop a lying answerer.
- Keep a result from CHZ only if it agrees with what I can check (I played it, or a CHL from the loser already named it). Bystanders cannot check most results, so this mostly drops catch-up.
- Accept the residual risk (a fun ladder, no loot) and document it.

Needs a call on how much catch-up the ladder should keep.

## Done when

- A CHZ entry from a sender I did not ask is ignored (test in `dev/tests/games/test_chess.py`), and `someone_offline_catches_up_on_the_ladder_at_login` still passes; or the decision to accept the risk is in `07-Log/Decision Log.md`.

## Related

- [[chess-results-need-both-sides]]
- [[Implicit State Machines]]
