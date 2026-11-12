---
title: "Chess results need both sides"
tags: [task]
status: 3 - To do
priority: p3
effort: S
updated: 2026-11-12
---

# Chess results need both sides

## Context

Karazhan Chess (`DisasterZone_Chess/Chess.lua`) has guild games between two members over whispers and a guild ladder of results. A game's state is `g.status`: `invited` (they asked me) or `asked` (I asked them), then `active`, then `over`. `Finish :232-248` sets `result` and `reason` and records the game on the ladder. Who moves it: the two players (invite, accept, move, resign, draw), the opponent's messages (CHA, CHM, CHK, CHP, CHG, CHR, CHD, CHX; handlers `:553-683`), and checkmate or other end conditions (`CheckEnd`). The ladder is a guild-wide set of results (`AddResult`), spread by CHL on GUILD (`Record :724-732`, `handlers.CHL :734-739`). Ratings are computed from it on every client.

## What was found

Two ways for one player to write a result the other never agreed to:

1. **A ladder result with no game.** Bob sends `CHL { id = "forged-1", w = Bob, b = Alice, r = "1-0", n = 40 }` on GUILD. `handlers.CHL` (`:734-739`) only checks that the sender is one of the two players, then calls `AddResult`. Every client now has a Bob win over Alice that was never played, and ratings shift.
2. **"You resigned".** In a real game (`active`), Bob whispers `CHG { id, ms = <current moves>, r = "0-1", why = "resign" }`. `Merge` (`:522-547`) takes any result whose reason is `resign` or `agreed` (`:536-537`) and calls `Finish`. Alice's game ends as a loss by resignation she never made, and her client then broadcasts that loss to the ladder itself.

Impact: low. It is a fun ladder with no loot or rank attached, and it needs a hand-made message. But it lets one member farm rating or end someone else's game.

## How it was found

State-machine audit 2026-11-12 (prompt: 'Find all the implicit state machines in my app'), read-only code trace from ~/claude-code. I traced the game status transitions and which remote messages can reach `Finish` and `AddResult`.

**Reproduced** with the repo's harness from a scratch script outside the repo (`smrepro/repro_chess.py`, built like `dev/tests/games/test_chess.py`, with clients Alice, Bob and Carol):
- After Bob's forged CHL, Alice and Carol both list `['Bob=1216', 'Alice=1184']`, with no game played.
- In a real game (e2e4 e7e5), after Bob's forged CHG, Alice's game is `over 0-1 resign` and her result is `loss`.

## Best fix

1. **CHG (`Merge`)**: a `resign` result is taken only if it is a resignation **by the sender**, i.e. the result is a win for me: `result == (g.me == 1 and "1-0" or "0-1")`. An `agreed` draw is taken only if I offered or accepted a draw (`g.drawFrom` set, or a pending accept of mine). Anything else is ignored, and the game continues to sync by moves.
2. **CHL**: a result is added only if (a) it is the sender's loss or a draw (a player can concede, not claim), or (b) both players have reported the same id and result: keep a pending map `id -> first report` and add on the second. Option (a) is one line and stops rating farming. Option (b) is stricter and needs the opponent online at some point. Pick (a) unless the owner wants (b).
3. Backfill: results already on the ladder cannot be told apart from real ones. Leave them, or offer an officer "remove result" if forged ones turn up.

Tests in `dev/tests/games/test_chess.py`:
- `a_forged_ladder_win_is_ignored`: Bob's CHL claiming a win over Alice leaves the ratings unchanged on Alice and Carol.
- `the_opponent_cannot_resign_for_me`: Bob's CHG with `0-1 resign` leaves Alice's game `active`.

The existing `resigning_and_draws_end_the_game_for_both_and_the_ladder_agrees` must still pass.

## Why this approach

- **Alternative: verify that the game exists on the receiver.** Bystanders (Carol) never hold the game, so they cannot check it. The "concede, not claim" rule works on every client with no extra state.
- **Alternative: a co-signed result.** There is no key infrastructure for chess, and that is far too heavy for a fun ladder.
- The move-level checks already work this way: illegal or out-of-turn moves from the wire are refused (see `a_guild_game_plays_over_whispers_on_both_clients` in `test_chess.py`). This extends the same distrust to results.

## Done when

- `a_forged_ladder_win_is_ignored` and `the_opponent_cannot_resign_for_me` pass, and all of `dev/tests/games/test_chess.py` passes.
- `repro_chess.py` shows unchanged ratings and an `active` game.

## Related

- [[Implicit State Machines]]
