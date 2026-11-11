---
title: "Startup error after in-game update 0.2.4 (HookScript)"
tags: [task]
status: "5 - Done"
completed: 2026-11-13
priority: p1
effort: M
updated: 2026-11-12
---

# Startup error after in-game update 0.2.4 (HookScript)

**On hold until 2026-11-13** (fresh eyes). The in-game update itself works end to end: signed, sent over the guild
channel, downloaded, installed with `/dz update`, rolled back with `/dzpatch rollback`. Only this error is open; update
#1 stays live for testing.

A tester who installed in-game update #1 (0.2.4 on top of 0.2.3, `/dz update`) gets the boot loader's "had 1 error
while starting" popup at every login. Not seen on 0.2.3 (checked by rolling back with `/dzpatch rollback`): it comes
with the update. The update only changes `Core/Sync.lua`, `UI/Members.lua` and `Data/Changelog.lua`.

The error (scriptErrors on):

```
bad argument #2 to '?' (Usage: local success = self:HookScript(scriptTypeName, script [, bindingType]))
[C]: in function 'xpcall'
Core/Init.lua:62  (SafeCall)
Core/Init.lua:503 (the event dispatcher)
```

An EVENT handler calls `HookScript` with a nil script; its own frame is not in the stack (a tail call or a C function),
so the source isn't named.

What is known:
- The update applies with 0 errors in the harness, with the real 0.2.3 zip and the real signed update, also for a
  member on another connected realm (the tester's home realm differs from the guild's).
- None of the three changed files calls `HookScript` at startup; the new code (`SendVersionTo`) uses `Util.After`
  (`C_Timer`); `UI/Changelog.lua`'s only hook takes an inline function.
- The publisher's own copy (a development copy: updates never apply) does not show it.
- The tester runs Windows, the publisher Linux (Proton): not expected to matter (same client and Lua; an applied
  update runs from saved variables, not disk). What differs: release zip + update through the boot loader vs the
  development copy from disk; the tester's other addons; their realm.

Next:
1. The tester's addon list, and BugSack/BugGrabber for a fuller trace.
2. Reproduce on a client running the 0.2.3 release zip that takes the update with `/dz update` (not the development
   copy), BugSack on.
3. Fix, a test for it, and a new signed update.

## Cause found (2026-11-12, reproduced in a stricter mock)

Not the update's code: `UI/GuestBook.lua:1486` (`GuestUI:OnInit`) calls
`GameTooltip:HookScript("OnTooltipSetUnit", OnTooltipSetUnit)` unguarded; Forever's retail-engine GameTooltip has no
`OnTooltipSetUnit` script, so the call fails on EVERY login, 0.2.3 too. Startup errors are only counted (and the popup
shown) while an in-game update is applied (`Core/Init.lua:408`, `Core/Boot.lua:467`); otherwise they are caught
quietly. Side effect today: `GuestUI:OnInit` stops before `Menu.ModifyMenu`, so the guest-book entries in the player
right-click menu are likely missing for everyone. The mock missed it: its Forever profile still has
`OnTooltipSetUnit` / `OnTooltipSetSpell` (`dev/tools/wowmock/forever.lua`). Confirm in game:
`/dump GameTooltip:HasScript("OnTooltipSetUnit")` -> false.

Fix: the guard `UI/Tooltip.lua:898` already has (`HasScript`, else TooltipDataProcessor's Unit post-call, unit read
with `Compat.Plain`), shipped as update #2. Tests: the mock's Forever GameTooltip without those scripts (and running
TooltipDataProcessor's Unit callbacks); a patch test asserting 0 startup errors after an update; a check that a
Forever login has no caught OnInit/OnLogin error.

## Done when

A client on the 0.2.3 zip takes the fixed update and starts with no error.
