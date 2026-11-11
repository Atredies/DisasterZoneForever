---
tags: [overview]
updated: 2026-11-11
---

# Project Overview

**Goal:** everything DisasterZone does for <Casual Disaster> on TBC, working on WoW Forever, ready for the first raids
on 9 Dec 2026. That covers loot council, soft reserves, raid plans and sign-ups, attendance, audit, roles, polls,
recruitment, strategy boards, boss mods, meters, Atlas/BiS and the games. The repo also holds a Rust desktop launcher
and a Discord bot server (`launcher/`); these notes cover the addon.

**Who uses it:** the guild. The GM configures council and rules; officers manage raid leaders; raid leaders run
raids and per-raid council; members keep BiS lists and sign up.

**How:** fork the original 1-to-1, add a Forever compatibility layer (`Core/Compat.lua`) and an Interface 16001 TOC,
port the mock client to 1.60.1, swap the TBC content data for Forever data, and rebuild the combat features on
Forever's own APIs (`C_DamageMeter`, `C_EncounterTimeline`, `C_SwingTimer`), because addons get no combat log there.

Full picture: [[Deep Dive Synthesis]].
