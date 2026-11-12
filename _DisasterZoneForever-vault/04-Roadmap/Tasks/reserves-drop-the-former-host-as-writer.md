---
title: "Reserves: drop the former host as writer"
tags: [task]
status: 3 - To do
priority: p3
effort: S
updated: 2026-11-12
---

# Reserves: drop the former host as writer

## Context

Soft reserves (`Core/Reserves.lua`) are a raid's list of who reserved which item. When a reserved item drops, `Roll` asks `Reserves:Decide` who rolls on it (`:276`). The list is the module-local `cur` with these states:
- none
- open (`o = true`, `Open :331`)
- closed (`o = false`, `cl`; `Close :358`, by hand or at the first pull, `OnPull :760`)
- cleared (`Clear :370`, or RVS with `x`)
- a read-only LootReserve mirror (`foreign`, `Mirror :657`)
- dropped 10 s after leaving the raid (`:748`)

Only the raid's loot authority (`GroupRules:GetAuthority`) writes the list. It broadcasts the whole list as RVS on RAID. Members ask for changes with RVR, and a new authority adopts the last list it saw (`MaybeAdopt :687-694`, which sets `by` to itself).

## What was found

`OnList` (`:598-628`) accepts an RVS from the current authority **or from `cur.by`**, the host named in the list I already hold (`:606`). That second clause exists for the moment the authority changes, but it never expires.

1. Alice is the loot authority and hosts the list (`by = Alice`).
2. The raid lead (and authority) passes to Bob. Bob does not run DisasterZone, or has no list, so nobody runs `MaybeAdopt` and clients keep `cur.by = Alice`.
3. Alice is now an ordinary raider. Her own client stops sending (`SendNow` checks `AmHost()`), but any RVS from her, hand-made or from a client with a stale view of the authority, is still taken by every client that holds her list, including the council member who starts the rolls.
4. She can rewrite who reserved what, and that decides who rolls on the next drop.

Impact: low. It needs a demoted host to forge messages, and a new authority that never adopted the list. It is the same class of hole as the "any assist can replace reserves" one closed in [[fix-the-authority-holes]].

## How it was found

State-machine audit 2026-11-12 (prompt: 'Find all the implicit state machines in my app'), read-only code trace from ~/claude-code. I traced the writer checks in `OnList`, `MaybeAdopt` and `SendNow`. Code reading only, not reproduced. To confirm, add a case to `dev/tests/reserves/` in which Alice opens reserves, the raid lead moves to an `ExtraMember` without the addon (`w.make_raid(..., leader=<extra>)`), and Alice sends a crafted `Comm:Send({ t = "RVS", ... by = Alice, v = cur.v + 1 ... }, "RAID")`. Then check Bob's `Reserves:Get()`. Run it with `dev/luaenv/bin/python` and `DISASTERZONE_ADDON_DIR=addon/DisasterZone`.

## Best fix

In `OnList` (`Core/Reserves.lua:606`), take `cur.by` as a writer only while it still has a right to write. Either:
- (preferred) `cur.by == sender and (auth == nil or GroupRules says sender is still leader / ML)`: the former host is accepted only while the authority is not yet known (the post-/reload window the comment describes) and while it still holds a loot role; or
- a short grace: remember when the authority last changed (`GROUP_RULES_CHANGED`) and accept `cur.by` only within N seconds of it.

No migration: the list is per raid and expires after 12 h (`KEEP_SAVED`).

Test: `dev/tests/reserves/` gains `former_host_cannot_rewrite_after_the_authority_moves` (the scenario above): Bob's list is unchanged. The existing reload and handover cases must still pass, notably the new authority adopting the list.

## Why this approach

- **Alternative: drop the `cur.by` clause entirely.** That breaks the case it was written for: right after a /reload a client does not know the authority yet, and the list from the real host would be held and then lost (see the `pendingList` comment, `:603-606`).
- **Alternative: sign lists.** Out of scope for raid-local data, and the rest of the addon trusts the raid's roles, not signatures, for loot (see `Roll`'s `IsRealCouncil` / `IsMasterLooter` checks).
- Tying the clause to a current role matches how `fix-the-authority-holes` closed the assist hole.

## Done when

- `former_host_cannot_rewrite_after_the_authority_moves` passes, and all of `dev/tests/reserves/` passes.

## Related

- [[Implicit State Machines]]
- [[fix-the-authority-holes]]
