---
title: "Raid times in server or local time, busy days in pages, other raiders' Bingo cards"
tags: [task]
status: "1 - In progress"
priority: p2
effort: M
updated: 2026-11-15
---

# Raid times in server or local time, busy days in pages, other raiders' Bingo cards

## Context

Three owner requests (2026-11-15):

1. Raid days and times: a switch between server (realm) time and local time.
2. A calendar day with several raids showed two and "+2 more", which could not be clicked: hard to see every raid
   and pick the one to sign up for.
3. Council Bingo: players should see the other players' cards.

## What was done

- `Util.Date` / `Util.Time` / `Util.RealmOffset` / `Util.ServerClock` (`Core/Util.lua`), setting `serverClock`
  (`Core/DB.lua`, off). The raid screens shadow `date` / `time` with them. `UI:CreateClockSwitch` on the calendar
  header, the Raids toolbar, and a Settings switch. Team nights follow it (`RaidNights:ShownOffset`).
- Calendar: the picked day's raids in pages (`< 1/2 >`, mouse wheel), `UI/Dashboard.lua`.
- Bingo: a click on a race row shows that raider's card read-only (`DisasterZone_Bingo/UI.lua`).
- Tests in `test_dashboard`, `test_bingo`, `test_boot`. See the 2026-11-15 changelog entry.

## Done when

- [x] Code and tests merged.
- [ ] In game: the switch on a client whose clock differs from the realm's (the tooltip shows both times), a day
  with 3+ raids turns pages, and in a Bingo game a click on another raider shows their card.
- [ ] Out to the guild (the next release or in-game update).
