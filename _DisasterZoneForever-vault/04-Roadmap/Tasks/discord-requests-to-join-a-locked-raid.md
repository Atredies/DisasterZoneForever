---
title: "Discord: requests to join a locked raid"
tags: [task]
status: 4 - Later
priority: p3
effort: S
updated: 2026-11-12
---

# Discord: requests to join a locked raid

## Context

Split out of [[one-sign-up-path-for-game-and-discord]] (2026-11-12). Both sign-up paths now share `BuildSignup` in `Core/RaidPlan.lua`. One difference is kept on purpose until it is decided: a member outside a locked (not private) raid who answers **in game** files a request to join (`opts.request = true`); the same answer **from Discord** is refused with "This raid is locked to its teams and invited players.".

## Blocked on

An owner decision: should a Discord answer to a locked raid also become a request to join (like the game), or keep being refused?

## Best fix

If requests: pass `request = true` in `SignUpFor`'s `opts`, and flip the lock row of `both_paths_apply_the_same_rules` (`dev/tests/raidplan/test_raidplan_signup_paths.py`) to expect a request on both paths. The bot would then want to tell the member "asked to join" instead of "signed up". If refused: nothing to do but close this card.

## Done when

- The decision is recorded in `07-Log/Decision Log.md` and the test's lock row asserts it.

## Related

- [[one-sign-up-path-for-game-and-discord]]
- [[Implicit State Machines]]
