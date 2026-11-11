---
tags: [reference, loot, reserves, ledger]
updated: 2026-11-11
---

# Duplicate Drops Fix (2026-11-09)

Branch `fix/duplicate-drops`. A report from the original TBC addon: when a boss drops the same item twice
(for example two "Gloves of the Fallen Defender" tokens), the item seemed to be rolled once, as if it were one item.

## For the officers (plain English)

The addon already ran **two separate rolls** for two copies of an item: one card per copy in the drop panel, one roll
after the other with "Roll all", and an award for each. Two things around those rolls still treated the copies as one
item. Both are fixed.

1. **Soft reserves.** With reserves as the loot method, every copy was handed to the same reservers again.
   - One player reserved the item: copy 1 went to them ("goes to X: the only reserve") and so did copy 2. Copy 2 was
     never rolled for the raid.
   - Two players reserved it: copy 2 was rolled among both reservers again, including whoever already won copy 1.

   Now each copy uses up one reservation. Whoever got (or is about to get) copy 1 is no longer a reserver for copy 2.
   - One reserver: they get copy 1, copy 2 is **up for grabs** (everyone rolls, the reserver may roll too).
   - Two reservers: the top roller gets copy 1, the other reserver gets copy 2 ("the only reserve").
   - Three or more: copy 2 is rolled among the reservers who did not get copy 1.
   - An item the guild holds stays a council decision for every copy, as before.
   A player can reserve an item only once (the list stores one entry per player and item), so nobody can claim two
   copies through reserves.

2. **The loot log.** When one player got **both** copies within two minutes, the loot log showed one award, and "won
   N items tonight" counted one. The log hides entries that look like the same award written down by several council
   members, and it took the second copy for such a duplicate. Now the log tells them apart: two roll awards, two
   awards by the same officer from the Award menu, or two loot lines are two awards. The same award written by several
   council members still shows once. Voiding one copy's loot line no longer voids the other copy's.

Nothing changes for an item that drops once.

## Technical

### The bug in the original (DisasterZone 1.5.5 commit 1bb205ee, unchanged in upstream 1.6.0)

Line numbers are those of 1.5.5 (identical in this repo's `main` before the fix).

**Reserves.**
- `Core/Reserves.lua:280-288` `Reserves:Decide(itemID)`: takes only the item id. It returns "s" plus every reserver
  in the group, whatever copy is asked about.
- `Core/Roll.lua:176-183` `ReserveDecision(ses)` calls `R:Decide(ses.i)` without the copy; `Core/Roll.lua:637-648`
  `OpenLocal` puts the result into the session (`rv` / `rk`, sent in RS). Every copy of a drop therefore opens with the
  same reserver list.
- `UI/DropPanel.lua:2835-2836` the card preview before a roll calls `Decide(itemID)` the same way.
- How it failed (reproduced in the mock): one reserver, two copies, "Roll all": copy 1 "goes to Dave: the only
  reserve", copy 2 also `rv = "s", rk = {Dave}` (a second "only reserve" line, no roll). Two reservers (Bob 70,
  Yuri 40): copy 2 opened with `rk = {Bob, Yuri}`, and Bob, copy 1's winner, rolled again.
- `SiblingWinners` (Roll.lua:838) only demoted copy 1's winner in council suggestions, and only once copy 1 was
  awarded; reserves rolls are plain, so it did not help.

**Loot log (Core/Ledger.lua).**
- `:28` `SAME_KIND_WINDOW = 120` and `BuildView` `:371-388`: within each (winner, item) group, a manual entry within
  120 s of the last kept manual entry, or an auto entry within 120 s of the last kept auto entry, is hidden. Two roll
  awards of the two copies to one player (ids `m<session1>-Erin`, `m<session2>-Erin`) became one.
- `:389-401`: one kept manual entry hid **every** auto entry from 10 min before to 6 h after it. Copy 1 awarded by
  roll and copy 2 simply handed to the same player: one award.
- `:495-496` `RecordAuto`: the id `"a" .. ts .. winner .. item` is the same for two loot lines of the same winner and
  item in the same server second; the second line returned the first entry.
- `:473-481` `CancelAutoFor`: a peer's entry cancelled **all** my pending broadcasts of that winner and item within
  120 s, so copy 1's entry from a peer could stop my copy 2 entry from going out.
- `:666-676` `AutoCluster`: voiding (or changing the reason of) one auto entry also voided every auto entry of that
  winner and item within 120 s, so both copies.

### The fix

**Reserves (Core/Roll.lua, Core/Reserves.lua, UI/DropPanel.lua).**
- `Reserves:Decide(itemID, taken)`: optional `taken = { [key] = true }`; those players are removed from the reservers.
  No reserver left: "o" (up for grabs). A held item is still "g" first.
- `Roll.lua` `ClaimsOf(itemID, s, c, demo)` / `CopyClaims(ses)` / public `Roll:CopyClaims(itemID, s, c)`: for a drop
  with an identity (`s ~= ""`), the players holding the other copies: the winner of each awarded sibling session, the
  single suggested player of a closed but not yet awarded sibling (a reserves roll names its reserver at once and the
  award follows; with "Roll all" copy 2 opens before anyone awards copy 1; a tie claims nobody), and the loot log's
  awards of the item for that drop (`Ledger:AwardsForDrop`, the Award menu).
- `ReserveDecision` passes `CopyClaims(ses)`. Only the starter decides; receivers take `rv` / `rk` from the RS as
  before (no wire change), so every client agrees. `Core/ReserveLR.lua` (LootReserve compat) uses the session's `rk`,
  so it follows. `Core/ReserveChat.lua` only takes reserves, no drop logic: nothing to change.
- The drop panel preview passes `Roll:CopyClaims(itemID, drop.s, copy)`.

**Loot log (Core/Ledger.lua).** The view still depends only on the entries it holds.
- `DistinctManual(a, b)`: two manual entries are two awards when both are roll awards (`IsRollAwardID`: `^m%D`, two
  different sessions) or both are Award-menu entries of the same recorder. Any other pair within 120 s is one award,
  as before (two council members recording the same award).
- `AutoLines(list)`: auto entries grouped into loot lines. An entry joins the earliest line within 120 s that has no
  entry of its recorder yet, else starts a new line. Every council member records each loot line once, so N lines from
  one recorder are N awards; the other recorders' entries of those lines are hidden. With one entry per recorder this
  is exactly the old rule.
- A kept manual entry hides **one** loot line in its range (the earliest one not hidden yet), not all of them.
- `RecordAuto`: the second loot line of the same winner and item in the same server second gets id `<id>-2` (third
  `-3`...). Every council member that sees both lines in that second derives the same ids; the first line keeps the
  old id, so cross-version de-duplication is unchanged.
- `CancelAutoFor`: a peer's entry cancels only my pending entry of the **same** loot line (`AutoLines` over the
  entries I hold plus the peer's).
- `AutoCluster` (void / reason change): only the entries of the voided entry's own loot line.

Known limits:
- Two officers each awarding one copy to the same player from the Award menu within 2 minutes still show as one
  award (indistinguishable from two officers recording one award). Use the copies' rolls, or one officer.
- When one council client's entry of line 1 and another's of line 2 fall in the same server second they share an id;
  the clients may then show different entries, but the same count.
- Disenchant / bank hand-outs by a non-council master looter (`RecordTargetAward`) of two copies in the same second
  still share one id. They do not count as loot won, so only the log line is missing. Not changed.

### Other places checked (no change needed)
- `Roll.lua` `SpareCopies` / `FlagLootConflict` / `NoteLootConflict`: count copies of the drop minus awarded
  sessions: correct for copies. `OnItemLooted` picks the lowest unresolved copy; `MarkGiven` / `GetOwed` are per
  session.
- `Roll.lua` `WonTonight` -> `Ledger:CountSince`: correct now that the view counts both copies.
- `UI/RollFrame.lua`: popup state is keyed by session id.
- `Core/Loot.lua` `FindLootSlot` skips a slot whose hand-out is in flight, so copy 2 finds the other slot while copy
  1's give is pending; `NoteHandedOut` finishes the first matching watch. `IsGiveInFlight(itemID)` has no callers.
  `ScanLoot` reopening the same corpse: the source is already seen, the drop is not added again.
- `UI/DropPanel.lua` `AnnounceItem` / `HandlePersonal` de-duplicate by item on purpose (one BiS announce / one toast
  per item).

### Tests
`dev/tests/loot-roll/test_duplicate_items.py` (12 cases). Before the fix 10 failed (the two control cases passed):

| Case | Before | After |
|---|---|---|
| reserves_one_reserver_two_copies_second_is_up_for_grabs | FAIL (copy 2 `s {Dave}`) | PASS |
| reserves_one_reserver_copy_one_awarded_first | FAIL | PASS |
| reserves_two_reservers_two_copies_each_gets_one | FAIL (copy 2 `s {Bob, Yuri}`) | PASS |
| reserves_two_reservers_copy_one_awarded_to_the_low_roller | FAIL | PASS |
| reserves_held_item_two_copies_both_for_the_guild | FAIL (test timing, fixed in the test) | PASS |
| reserves_single_copy_unchanged | PASS | PASS |
| ledger_one_player_wins_both_copies_by_roll | FAIL (1 entry) | PASS |
| ledger_one_player_gets_both_copies_from_the_award_menu | FAIL (1 entry) | PASS |
| ledger_two_loot_lines_same_winner_same_second | FAIL (1 entry) | PASS |
| ledger_two_loot_lines_same_winner_seconds_apart_seen_at_different_seconds | FAIL (1 entry) | PASS |
| ledger_one_loot_line_on_two_council_clients_still_one | PASS | PASS |
| ledger_void_one_of_two_loot_lines_keeps_the_other | FAIL (1 entry) | PASS |

Everything above is checked in the `wowmock` mock client only: **UNVERIFIED** in the real Forever client (a boss
dropping two copies with reserves on, and the loot log afterwards). Check it on the next raid where a token drops
twice.
