---
title: "Invite & sort follows the raid"
tags: [task]
status: "5 - Done"
completed: 2026-11-12
priority: p2
effort: S
updated: 2026-11-12
---

# Invite & sort follows the raid

## Context

Invite & sort (`Core/RaidInvite.lua`) is the raid leader's button that invites everyone placed in a planned raid's group layout and sorts them into their groups, then keeps sorting late joiners. Its state is the module-local `active` table (`Core/RaidInvite.lua:340-354`), saved to `db.raidInvite` and resumed after a /reload (`:464-476`). States: idle (`active = nil`), inviting (`active.inviting`), sorting only, waiting for combat (`active.waitCombat`). It is started by the leader (`RaidInvite:Start :356`, `Resort :369`) and stopped by `Stop` (`:233`): the Stop button (`UI/RaidPlanUI.lua:1687`), leaving the group, the raid session ending, MAX_AGE (`Pump :247-273`), or `RaidPlan:DeleteRaid` (`Core/RaidPlan.lua:3856`).

The raid it serves has its own lifecycle in the planner (`Core/RaidPlan.lua`): scheduled, cancelled (`x`, `CancelRaid :3830`), deleted (`del` tombstone, `DeleteRaid :3847`), written by the GM, the raid leaders and the raid's own leader, and spread to every client by the guild sync.

## What was found

The run does not follow the raid's lifecycle.

1. Bob (raid leader) runs Invite & sort for Friday's Karazhan. Lock is offline, so he is listed as missing.
2. The raid is cancelled, either by Bob (`CancelRaid`) or by the GM Gina on her own client (the cancel reaches Bob through the sync). Gina could also delete it.
3. `CancelRaid` (`Core/RaidPlan.lua:3830-3842`) never calls `RaidInvite:Stop`, and the merge of a remote cancel or delete does not either. Only a local `DeleteRaid` does (`:3856`).
4. Lock logs in. The next `Pump` (on `GROUP_ROSTER_UPDATE`) still has `active` and invites him into the raid group of a raid that no longer exists.

Impact: players are invited and moved for a cancelled raid, and the leader's panel still shows a running Invite & sort. It is user-visible and confusing, but no data is lost. It is likely whenever a raid is cancelled at short notice while the leader is already forming the group, which is when cancels happen.

## How it was found

State-machine audit 2026-11-12 (prompt: 'Find all the implicit state machines in my app'), read-only code trace from ~/claude-code. I traced every caller of `RaidInvite:Stop` and `Stop` (`grep -rn 'RaidInvite:Stop' addon/`) against the raid's cancel and delete paths.

**Reproduced** with the repo's own harness, run from a scratch script outside the repo (`smrepro/repro_invite.py` in the audit's scratch space, run with `dev/luaenv/bin/python` and `DISASTERZONE_ADDON_DIR=addon/DisasterZone`), built on `dev/tests/raidplan/test_raidplan_invite.py`'s `setup`:

| Who ends the raid | `RaidInvite:IsActive()` after | Lock invited after logging in |
|---|---|---|
| Bob, `CancelRaid` (local) | true | yes |
| Gina, `CancelRaid` (remote, via sync) | true | yes |
| Gina, `DeleteRaid` (remote) | true | yes |
| Bob, `DeleteRaid` (local) | false | no |

Not checked: the UI side (the Groups tab's run line) after a remote cancel.

## Best fix

Make the run check its raid every time it acts, instead of relying on every writer to remember to stop it:

- In `Pump` (`Core/RaidInvite.lua:247`), right after the MAX_AGE check, look up the raid: `local v = ns.RaidPlan:GetRaid(active.occ)`. If `not v` (deleted or gone) or `v.cancelled`, `return Stop("Invite & sort stopped: the raid was cancelled.")` (or "deleted").
- Also `SchedulePump` on `RAIDPLAN_CHANGED` (fired by `RaidPlan`'s `Changed()`, `Core/RaidPlan.lua:406-409`) while `active`, so a synced cancel stops the run without waiting for a roster event.
- Keep the explicit `RaidInvite:Stop()` in `DeleteRaid`. It is now redundant but harmless.
- No data migration: `active` lives only in memory and in `db.raidInvite`, and a stale saved run hits the new check on its first pump after login.

Tests to add in `dev/tests/raidplan/test_raidplan_invite.py`:
- `the_run_stops_when_the_raid_is_cancelled`: the local cancel case above.
- `the_run_stops_when_another_planner_cancels_or_deletes_the_raid`: Gina cancels on her client, and in a second world deletes it. `IsActive()` is false within a few ticks, and a member who logs in afterwards is not invited.

## Why this approach

- **Alternative: call `RaidInvite:Stop()` from `CancelRaid` and from the sync merge.** That patches today's writers but leaves the same hole for the next one (an edit that moves the raid, a series stop, a leader change). The repo already prefers derived checks over pushed notifications for this kind of thing: `Pump` already re-reads the group and the raid session on every pass (`:255-273`).
- **Alternative: stop the run only at the UI.** It would not cover a /reload resume (`:464`) or a leader who has the panel closed.
- The check costs one table lookup per pump, which is negligible.

## Done when

- `the_run_stops_when_the_raid_is_cancelled` and `the_run_stops_when_another_planner_cancels_or_deletes_the_raid` pass, with the rest of `test_raidplan_invite.py`.
- Running `repro_invite.py` gives `IsActive() == false` and no invite after cancel or delete in all four rows.

## Fix (2026-11-12)

Done as the card's best fix, branch `fix/state-machines`.

- **What changed:** `Core/RaidPlan.lua` gains `RaidPlan:RaidStatus(occId)` ("on", "cancelled", "gone", or nil while the guild's plan is not known yet). `Core/RaidInvite.lua`: `Pump` checks it right after the MAX_AGE check and stops with "the raid was cancelled" / "the raid was deleted"; a `RAIDPLAN_CHANGED` listener schedules a pump while a run is active, so a synced cancel stops it without waiting for a roster event. The explicit `RaidInvite:Stop()` in `DeleteRaid` stays.
- **Why `RaidStatus` and not `GetRaid` in `Pump`:** `GetRaid` also returns nil when there is no guild key yet (the first seconds after a /reload, when `OnLogin` resumes a saved run). Treating that as "deleted" would have stopped every resumed run. `RaidStatus` returns nil (unknown) in that window and the run continues.
- **Protocol:** no message changed. Old clients still keep inviting for a cancelled raid; new clients stop.
- **Tests added** (`dev/tests/raidplan/test_raidplan_invite.py`): `the_run_stops_when_the_raid_is_cancelled`, `the_run_stops_when_another_planner_cancels_or_deletes_the_raid` (Gina cancels, then in a second world deletes; Lock logs in afterwards and is not invited). Both fail on the old code, pass now.
- **Side-effect audit:** `Pump` is called by Start, Resort, UpdatePlan, the login resume, roster / regen / group-rules events and now RAIDPLAN_CHANGED. All of them now stop on a cancelled or deleted raid, which is the intent. RAIDPLAN_CHANGED fires on every plan merge, so an active run pumps a little more often; the pump is debounced (0.5 s) and invites are tracked in `active.invited`, so nothing is sent twice. `RaidStatus` is new and has no other caller. A raid that is merely past its start is not affected.
- **Checks:** `test_raidplan_invite.py` 10/10; full harness run listed in the PR.

## Related

- [[Implicit State Machines]]
- [[one-sign-up-path-for-game-and-discord]]
