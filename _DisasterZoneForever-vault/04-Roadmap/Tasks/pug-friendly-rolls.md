---
title: "Pug-friendly rolls: link in raid chat, collect every roll, show what it replaces"
tags: [task]
status: 4 - Later
priority: p3
effort: M
updated: 2026-11-11
---

# Pug-friendly rolls

An **add-on to the existing roll flow, not a rewrite**. Our raids will likely take pugs, who
don't run DisasterZone. When we put an item up with `/dz roll <link>`:

1. **Link the item in raid chat** so players without the addon see what is up and type `/roll`.
2. **Collect every roll in one place in the addon**: addon users and pugs alike, highest first, so the
   loot master sees at a glance who rolled highest.
3. **Show what each roller would replace**: the item they wear in that slot now, next to their roll.

## What already exists (check before building)
- `Core/Roll.lua` already announces the start in group chat (`"Roll for <item> now — /roll (30s)"`, setting
  `roll.announce`, default on) and reads every `/roll` from `CHAT_MSG_SYSTEM`, so pug rolls should already land in
  the session. **First step: test this with a pug** (or a guildie with the addon off) and confirm that the item link
  shows in raid chat, that their roll appears in the drop panel and that they can be suggested and awarded. Watch
  for: `r.notGuild` (only applies to guild-only rolls, `rv = "g"`), a raid-warning variant for visibility, and the
  addon-message lockdown during a boss pull (chat lines are not addon messages, but check).
- "What it replaces" (`r.equippedList`, `EquippedFor` -> `Store:GetEquippedList`) comes from gear data that
  members' addons share, so **a pug shows nothing there**. This is the real gap.

## Likely work
- Pug gear: inspect rollers who don't run the addon (`NotifyInspect` + `INSPECT_READY` + `GetInventoryItemLink(unit, slot)`)
  while the roll is open. Inspect needs range and is throttled, so queue the requests one at a time. Cache by GUID
  for the raid. Verify these APIs on the Forever client first (secret values in instances? inspect in combat?).
- Drop panel: one sorted list (roll, name, guild/pug tag, equipped item with item level / tooltip on hover).
- Optional: a "roll summary" line in raid chat at close (`Winner X (87), next Y (72)`) so pugs see the result.

## Done when
A pug's `/roll` for an item started with `/dz roll` shows in the drop panel's sorted list with their equipped item
for that slot (by inspect), the item link was posted in raid chat, and a mock test covers a non-addon roller.
