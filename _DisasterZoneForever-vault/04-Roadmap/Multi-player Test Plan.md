---
tags: [roadmap, test]
updated: 2026-11-11
---

# Multi-player Test Plan (0.2.0)

First real test with guildmates. About an hour. Roles: **GM** (the guild's Guild Master),
**Officer** (one tester with an officer rank), **Members** (one or two testers with a plain rank). If only two testers
come, the GM plays the officer part too. Release: https://github.com/Atredies/DisasterZoneForever/releases/tag/v0.2.0

## Before the session

**GM**
- [ ] Settings > Guild > Officers: tick the ranks that count as officers (default ranks 0-1). Make sure the Officer
  tester's rank is ticked and the Members' rank is not.
- [ ] Send everyone the release link.

**Everyone (GM, Officer, Members)**
- [ ] Close the game. Delete old `DisasterZone*` folders in `World of Warcraft\_forever_\Interface\AddOns`, unzip
  `DisasterZone-0.2.0.zip` there, start the game. DisasterZone ticked under AddOns on the character screen.
- [ ] In game: `/dz version` shows 0.2.0.

## The session

| # | Who | Does | Expected |
|---|---|---|---|
| 1 | Everyone | Log in, `/dz version` | Everyone listed on 0.2.0 |
| 2 | Everyone | Open Members | Everyone sees the others online |
| 3 | Officer | Raids page: create an event and a raid (Onyxia 40 is fine) | Everyone sees both within about a minute |
| 4 | Members | Sign up to the event and the raid | Officer and GM see each sign-up |
| 5 | Member | Try to edit the Officer's event | Refused (not allowed) |
| 6 | Officer | Start a poll | Everyone votes; everyone sees the same result |
| 7 | Everyone | My BiS: add a few items | Officer / GM see them in the loot council view |
| 8 | One Member | Log out; Officer changes the event; Member logs back in | The change is there without /reload |
| 9 | GM or Officer | Invite through DisasterZone until it becomes a raid; start a raid session | Party turns into a raid; the raid bar shows |
| 10 | GM or Officer (master looter) | Start a roll on any item (two identical items in one loot is the best case) | Everyone gets the roll window; each copy its own roll and winner |
| 11 | One Member | `/reload` while a roll is open | The roll window comes back with the time left; the roll counts |
| 12 | Everyone (optional) | A dungeon boss pull while people chat / whisper / sign up | No DisasterZone error; messages arrive after the pull |

## While testing

- **Everyone:** something wrong: `/dz bug` straight away, and say what you were doing. Note the time.
- **GM:** watch for "passed on by X, not confirmed" labels, and for anything that takes long to appear (we have
  never measured Forever's real send limit).

## Afterwards (GM)

- [ ] Note which rows worked and which didn't.
- [ ] Log out once so the saved data is written; the reports and errors are in
  `WTF/Account/*/SavedVariables/DisasterZone.lua` (`feedbackErrors`, Feedback).
- [ ] Solo checks if time allows: item tooltip "who wants this" lines; What's New shows 0.2.0; Groups cards show old
  world pictures; swing / shot / totem timers in a fight; Escape in Hold the Line / Azeromon in combat.
