---
title: "Talents on Forever's class talent trees"
tags: [task]
status: 1 - In progress
priority: p2
effort: M
updated: 2026-11-11
---

# Talents on Forever's class talent trees

Forever has no `GetTalentTabInfo` / `GetTalentInfo` / `GetNumTalentTabs`; talents are `C_ClassTalents` / `C_Traits`
trees (Blizzard_PlayerSpells/Camelot). DisasterZone reads talents for role guesses (ClassKit, MyLog, Professions),
BiS export, Blessings, WarriorSwing and the Sim. All callers check first, so today they just see "no talents". Map the
trait tree to "points per tree" in Compat (or a new helper) so role detection works again.

## Done when

Role/spec detection gives the right answer for a Forever character in the harness and in game.

## Done 2026-11-09 (PR #37)

In game: `GetSpecializationInfo(1)` = `1491 Warrior 626008 DAMAGER 4 0 nil 0 true` (one spec per class, named
after the class, 0 points). Compat reads the trait-node groups as points per tree (`TalentTabPoints`,
`NumTalentTabs`, `Talents`, `TalentRank`, `SpecRole`); every reader uses them; `ClassKit:MyRole()`. The mock matches.

## Left: in-game checks

`C_Traits.GetGroupDisplayInfoByTreeID` names the groups Arms / Fury / Protection ...;
`C_Traits.GetGroupCurrencyInfo(...).currencyInfos[1].spent` is the points per tree; the spec role of other classes.
