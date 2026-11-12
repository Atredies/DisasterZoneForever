---
title: "One sign-up path for game and Discord"
tags: [task]
status: 3 - To do
priority: p2
effort: M
updated: 2026-11-12
---

# One sign-up path for game and Discord

## Context

A raid sign-up is a member's answer to a planned raid: `U[occId][key] = { st, rev, c, sp, n, at, dc }` in the guild's raid plan (`Core/RaidPlan.lua`). The status is A, T, B or X (Accept, Tentative, Bench, Absent; `STATUSES :148`). The effective state is derived by `GetSignupBlock` (`:2399-2408`), which layers the blacklist, declined (`rj`), lock (a request to join), level, and removed (`rm`, ignored until a newer rev) on top of the stored answer.

A member moves it in two ways:
- in game, with `RaidPlan:SignUp` (`:4090-4152`)
- from Discord: the bot signs a record, every game client that receives it runs `Bridge`'s `signup` type (`Core/Bridge.lua:694-703`), which calls `RaidPlan:SignUpFor` (`:4052-4088`)

Organizers move it with Decline, Approve, Remove and Restore (`:3989-4041`). Sign-ups are the raid roster: who is expected, who gets a group seat, who is invited by Invite & sort.

## What was found

The member transition is written twice, and the two copies have drifted. Both re-implement the same guard chain (cancelled, over, status, block) and the same rev rules (beat `rm`, beat the player's other characters), with these differences:

1. **Locked raid.** A member outside a locked raid's teams answers in game: `SignUp` turns it into a request to join (`:4112-4115`, `CanRequest`). The same member answers in Discord: `SignUpFor` refuses with "This raid is locked to its teams and invited players." (`:4064`). Members who use Discord cannot ask to join a locked raid.
2. **Note too long.** Rita is signed up with the note "late 15". She changes her answer with a 60-character note. In game, `SignUp` refuses with "Notes are at most 40 characters." (`:4136-4141`). From Discord, `SignUpFor` (`:4082-4083`) gets `nil` from `CleanText` (which rejects over-long text, `:170-175`) and stores the answer with **no note**: "late 15" is silently lost and the call returns ok.
3. `note = false` (clear the note) is handled by `SignUp` only. `SignUpFor` never receives false today (the Bridge passes a string or nil), so this is latent.

Impact: user-visible but small today. Discord members of locked raids are refused instead of queued, and notes can vanish. The real cost is the next rule: any new block or cut-off has to be added to both copies, and the two already disagree. Likely to bite on the next change to sign-up rules.

Corrected during re-verification: the audit note first said the two paths find a player's other characters differently (`Linked(key)` vs `GetMyCharacters()`). `GetMyCharacters` (`:2750-2755`) is `{ me } + Linked(me)`, so the two are equivalent. That claim was dropped.

## How it was found

State-machine audit 2026-11-12 (prompt: 'Find all the implicit state machines in my app'), read-only code trace from ~/claude-code. I compared `SignUp` and `SignUpFor` line by line and traced `CleanText` and `GetMyCharacters`.

**Reproduced** with the repo's harness from a scratch script outside the repo (`smrepro/repro_signup.py`, built on `dev/tests/raidplan/rp_common.py`: a locked raid whose team is Bob and Rita):
- In game `SignUp` by Lee (outside the team): `{ok: true}`, stored as a request.
- `SignUpFor` for Lee: `{ok: false, e: 'This raid is locked to its teams and invited players.'}`.
- Rita answers "A" with note "late 15". A 60-character note through `SignUp` is refused. The same through `SignUpFor` returns `{ok: true}`, and Rita's stored answer is `{st: 'T', n: nil}`.

Unverified: whether the Discord bot ever sends notes longer than 40 characters, and whether the lock refusal is intended. The Bridge comment (`:690-693`) does not say. Ask the owner before deciding difference 1.

## Best fix

1. Extract one local function in `Core/RaidPlan.lua`, e.g. `BuildSignup(root, occId, key, status, spec, note, opts)`. It returns `clean` or `nil, err` and holds the guard chain, the rev rules (`rm`, other characters), spec defaulting, note handling (nil keeps, false clears, too long refuses) and `CleanSignup`. `opts` carries the deliberate differences:
   - `opts.request`: may a locked-out member ask to join (true for the game; for Discord as the owner decides)
   - `opts.dc`: mark the answer as given in Discord
   - `opts.charCheck`: SameAccount for the game, roster class for Discord
2. `SignUp` = `BuildSignup` + `MergeSignup` + spec memory + broadcast. `SignUpFor` = `BuildSignup` + `MergeSignup` (no broadcast, as now).
3. Make the Discord path refuse an over-long note, which the bot can show, instead of dropping it, or keep the old note. No backfill: notes that were already lost cannot be recovered, and the record is otherwise valid.

Test to add, `dev/tests/raidplan/test_raidplan_signup_paths.py`: `both_paths_apply_the_same_rules`, table-driven over cancelled, over, blacklist, declined, lock, level, removed, a note over 40 characters and `note=false`. It runs each case through `SignUp` and `SignUpFor` and asserts the documented result for each (equal, or the named deliberate difference).

## Why this approach

- **Alternative: make `SignUpFor` call `SignUp`.** `SignUp` reads the logged-in player (`Util.PlayerKey`), checks SameAccount against them and broadcasts. The Discord path runs on every client for someone else's character and must not broadcast (`:4049-4051`). Splitting out the pure part avoids both.
- **Alternative: just patch the two differences.** Cheapest now, but the next rule repeats the problem. This file already went the shared-helper way for the same reason (the `Merge` helper table, `:155-158`).

## Done when

- `both_paths_apply_the_same_rules` passes, and the rest of `dev/tests/raidplan/` and `dev/tests/bridge/` still pass.
- `repro_signup.py` shows the long note refused, or kept, on both paths, and the lock behaviour the owner chose on both.

## Related

- [[Implicit State Machines]]
- [[invite-and-sort-follows-the-raid]]
- [[one-constant-for-the-raid-over-cut-off]]
