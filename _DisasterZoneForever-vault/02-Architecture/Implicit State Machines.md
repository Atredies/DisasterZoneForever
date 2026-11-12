---
tags: [architecture, state-machines]
updated: 2026-11-12
---

# Implicit State Machines

The addon has no transition tables: every lifecycle is a status string or a flag on a record, moved by local
functions and by addon messages from other clients. That said, the important ones are well guarded. Almost every
transition checks the current state first (`if ses.state ~= "open" then return end`), remote writers are checked by role,
and wire records merge by revision. Some states are derived on read instead of stored (event occurrences, polls, raid
sign-up blocks), which is the safest way to do it. The real risks are not illegal jumps but **the same transition
written in several places** that have already drifted apart, and **side processes that do not follow their parent's
lifecycle** (Invite & sort outliving a cancelled raid, an event handover that drops the host role even when the message
did not go out). Twelve machines were found in our own code. Scope: `addon/` (Core, UI, Chess), not `dev/thirdparty`,
libraries or the launcher.

| Machine | Lives in | States | Issues |
|---|---|---|---|
| Loot roll session | `Core/Roll.lua:325-355` | queued, open, closed, awarded, cancelled (+ given / looted / via / lootPrev / lootOther) | Award transition written 3 times (medium); demo toggle bypasses cancel (low); awarded can go back (by design) |
| Event run | `Core/EventEngine.lua:98, 1760-1846` | ready, live, done, cancelled | None: each transition is guarded |
| Live event host role | `Core/EventLive.lua:558-640, 1122-1170, 1406-1425` | hosting, watching (seen), handed over, taken over, forgotten | HandOver drops the role without checking the send (medium) |
| Event occurrence | `Core/Events.lua:1046-1056` (derived) | planned, live, done, cancelled, missed | 6 h cut-off copied in 15 places (low) |
| Raid (planner record) | `Core/RaidPlan.lua:1198-1240, 3830-3870` | scheduled, cancelled (x), restored, deleted (del), series stopped (u), series cancelled | Invite & sort not stopped on cancel / remote delete (medium); series cancel hides past weeks too (low) |
| Raid sign-up | `Core/RaidPlan.lua:148, 2399-2416, 3989-4152` | A, T, B, X; overlays declined (rj), removed (rm, by rev), lock / request, blacklist, level, guest | SignUp and SignUpFor duplicate the guard chain and have drifted (medium) |
| Invite & sort run | `Core/RaidInvite.lua:233-300, 340-401, 464-476` | idle, inviting, sorting, waiting for combat; persisted across /reload | Follows group and session, not the raid's own state (see Raid) |
| Reserves list | `Core/Reserves.lua:331-380, 598-628, 657, 720-768` | none, open (o), closed (o = false, cl), cleared, foreign mirror | Former host still accepted as writer (low) |
| Chess game | `DisasterZone_Chess/Chess.lua:10, 232, 411-700, 724-739` | invited, asked, active, over | Ladder result and "resign" result accepted from one side unchecked (low) |
| Feedback item | `Core/Feedback.lua:67-68, 962-993, 1307-1335` | open, planned, done, exists, notnow, dup, removed | Any-to-any by staff (fine); changelog forces done over removed (low) |
| Patch download slot / Boot | `Core/Patch.lua:729-736, 840-960`; `Core/Boot.lua:146-244` | open, verifying, done (reset on blame); Boot: none, off, base, bad, malformed, rejected, applied, safemode, dormant | None: `dl ~= mine` guards every async job, Boot is set once per load |
| Poll | `Core/Polls.lua:606` (derived) | open, closed (by `cl` time), removed (del) | None |

## Loot roll session

`state` on the session table, created at `Core/Roll.lua:330` (remote, `open`) and `:351` (mine, `queued`). Transitions:
queue advance opens (`:660`), timer or RE closes (`CloseSession :567`), clash or RE x cancels (`CancelSession :578`,
`:2562`), award (`Finish :1948`, loot message `MarkAwarded :2210`, remote RW `OnRollWin :2764`), and a backward edge
awarded to closed / queued when a loot message is reclaimed by an explicit award (`ReclaimLoot :1845-1863`). Triggers:
the starter, the council / master looter (role-checked on every message), the loot chat line, group changes (`:2831`),
the demo toggle (`:2807`).

- **Medium: the award transition exists three times.** `Finish`, `MarkAwarded` and `OnRollWin` each write
  `state, winner, given, via, looted, lootPrev, awardedBy, awardedAt, awardTs, final` by hand, and each writes a
  different subset (MarkAwarded clears `awardedBy`, OnRollWin leaves `looted` alone unless loot-marked, Finish computes
  `final` later). Any new award field must be added in three places, and the crossed-award resolution in OnRollWin
  depends on those fields being consistent.
- Low: `OnDemoToggled` (`:2807-2826`) sets `cancelled` directly, without `CancelSession` and without an RE, so a roll I
  started stays open on everyone else's screen until their own timeout.
- Low: sessions are memory-only. A closed roll that was never awarded is gone after a /reload (the ledger is the record;
  only the "award now" moment is lost).

## Event run

`st.phase` on the run (`Core/EventEngine.lua:98`): `ready` to `live` (`Run:Start :1760`), `live` to `done`
(`Run:End :1827`), `ready` or `live` to `cancelled` (`Run:Cancel :1837`). Every transition checks the phase first and
`Wrap` closes asks and timers. A calendar cancel or removal while I host it cancels the run (`Core/EventLive.lua:2112`).
No issues.

## Live event host role

Who runs a live event is a role spread over clients: `hosting[occId]` (I run it) and `seen[occId]` (someone else does).
Transitions: start, `Resume` after a takeover or reload (`:558`), `HandOver` (`:617`), a newer state from another host
(`OnState :1122-1150`, with a race rule: `StateNewer`), takeover by entrants after silence in name order
(`CheckTakeover :1406`), forgotten 10 minutes after the end (`:1369`).

- **Medium: `HandOver` ignores whether its EVS went out.** It clears `hosting[occId]` and writes `seen` for the new host
  right after `Send(...)` (`:627-630`) without checking the return value. `Send` returns false in demo mode, when the
  guild is not known yet after a /reload, or when the state is too large. Then nobody hosts the run: the named player
  never learns it, and the event waits for the takeover timer, which resumes from an older state.

## Event occurrence

Derived on read by `Events:OccState` (`Core/Events.lua:1046`): `cancel` flag, else a saved result (done or cancelled),
else live per EventLive, else missed after 6 h, else planned. Nothing stores it, so it cannot go stale.

- Low: "over 6 hours after the start" is a literal in 15 places: `Events.lua:1054`, `RaidPlan.lua:62`
  (`SIGNUP_CLOSE`, the only named one) and 13 times in `UI/RaidPlanUI.lua` (`:212, 234, 247, 282, 481, 534, 594, 661,
  817, 1066, 1768, 2177, 2803`). Changing the rule in one place leaves the others behind.

## Raid (planner record)

A raid view is built from the series (S) and its override (E): `cancelled` from `x` (`Core/RaidPlan.lua:1205, 1234`),
deleted as an E tombstone with `del` (`:3851`), a series ends at `u` (`StopRepeating :3860`), and a series with `x` is
dropped entirely (`ViewOccurrence :1213`). Cancel can be undone by an edit with `x = false` (`:3778, :3825`). Writers
are checked by `Trusted` on merge.

- **Medium: Invite & sort does not follow the raid.** `DeleteRaid` stops a run for that raid (`:3856`), but
  `CancelRaid` (`:3830`) does not, and neither does a cancel or delete that arrives from another planner through the
  sync. The run keeps inviting and sorting the planned layout until the group or session ends or MAX_AGE passes
  (`Core/RaidInvite.lua:247-273`).
- Low: cancelling a series (`s.x`) removes past weeks from the list too, so it looks like a delete; `DeleteRaid` with
  scope series is in fact implemented as that cancel (`:3850`).

## Raid sign-up

Stored per character as `U[occId][key] = { st = A|T|B|X, rev, ... }`; the effective status is derived:
`GetSignupBlock` (`:2399`) layers blacklist, declined (`rj`), lock (a request to join), level, and `rm` (removed: an
answer is ignored until a newer rev). Organizer transitions: `DeclineSignup :3989`, `ApproveRequest :4003`,
`RemoveSignup :4016`, `RestoreSignup :4032`. Member transitions: `SignUp :4090` (in game) and `SignUpFor :4052`
(Discord, via `Core/Bridge.lua:703`).

- **Medium: the member transition is written twice and has drifted.** SignUp and SignUpFor each re-implement the
  checks (cancelled, over, status, block) and the rev rules (beat `rm`, beat the other characters). They already
  differ: SignUpFor refuses a locked raid outright where SignUp turns it into a request, SignUpFor links characters with
  `Linked(key)` and SignUp with `GetMyCharacters()`, and an over-long note is cut by one and refused by the other. A
  future rule (a new block, a sign-up cut-off) will land in one path only.
- By design: a removed answer is soft (the member can answer again at once); a declined one is sticky.

## Invite & sort run

`active` in `Core/RaidInvite.lua`, saved to `db.raidInvite` and resumed after a /reload (`:464`). Inviting vs sorting
only (`inviting`), `waitCombat` while in combat. Stops: Stop button, leaving the group, the raid session ending (with a
grace), MAX_AGE, or `DeleteRaid`. Its gap is listed under Raid above.

## Reserves list

`cur` with `o` (open) and `cl` (closed at) in `Core/Reserves.lua`. Open (`:331`), close by hand or at the first pull
(`:358`, `:760`), clear (`:370`, RVS x), a LootReserve mirror (`:657`), dropped 10 s after leaving the raid (`:748`). Only
the host writes; others ask with RVR.

- Low: `OnList` (`:607`) accepts a list from the raid's authority or from `cur.by`, the host of the list I hold. After
  the authority moves, the former host is still a valid writer on clients that hold its list, so two writers are
  possible until those clients take the new authority's list (a different id replaces it regardless of version).

## Chess game

`g.status` in `DisasterZone_Chess/Chess.lua`: `invited` (they asked me) or `asked` (I asked), `active`, `over`
(`Finish :232`, guarded). `asked` is promoted to `active` by any move, ack or sync from the opponent, a sensible
recovery for a lost accept.

- Low: the ladder takes a result from either player (`CHL :734-739`) with no game behind it, and a whole-game sync
  (`CHG`, `Merge :535-540`) lets the opponent end my game as "resign" with any result. It is a fun ladder, so this is
  low impact.

## Feedback item

Status records (`k = "s"`) merged last-writer-wins by `rv` (`Core/Feedback.lua:1307-1335`); staff move any state to any
state, `nil` reopens. The changelog naming the item's number forces `done` on read (`:986-992`), even over `removed`.
Low.

## Patch download slot and Boot

Slots go `open` to `verifying` to `done`, and back to `open` on a failed check (`Blame` / `ResetSlot`,
`Core/Patch.lua:733-757`). Every async verify job checks `dl ~= mine` before it writes. `Boot.state` is set once per
load. No issues found.

## Worth fixing

1. **Medium: one award helper for roll sessions.** Fold the three award writes in `Core/Roll.lua` (`:1948`, `:2210`,
   `:2764`) into one function that sets every award field, with a parameter for the source (mine, loot message,
   remote). Card: `04-Roadmap/Tasks/one-award-transition-for-roll-sessions.md`.
2. **Medium: Invite & sort stops when its raid is cancelled or deleted**, locally or by sync
   (`Core/RaidPlan.lua:3830`, `Core/RaidInvite.lua:247`). Card:
   `04-Roadmap/Tasks/invite-and-sort-follows-the-raid.md`.
3. **Medium: one sign-up path for in-game and Discord answers** (`Core/RaidPlan.lua:4052` and `:4090`). Card:
   `04-Roadmap/Tasks/one-sign-up-path-for-game-and-discord.md`.
4. **Medium: HandOver keeps the host role until its state went out** (`Core/EventLive.lua:617-631`). Card:
   `04-Roadmap/Tasks/event-handover-checks-the-send.md`.
5. Low: one constant for the 6 h "over" cut-off (`Events.lua:1054`, `RaidPlan.lua:62`, 13 literals in `UI/RaidPlanUI.lua`).
6. Low: the demo toggle cancels my open roll through `CancelSession` and sends RE (`Core/Roll.lua:2807`).
7. Low: Reserves stops accepting the former host once the authority changed (`Core/Reserves.lua:607`).
8. Low: the chess ladder takes a result only with a game both sides hold (`Chess.lua:734`).
