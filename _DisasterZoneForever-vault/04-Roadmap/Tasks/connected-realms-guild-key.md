---
title: "Connected realms: one guild key for members of every realm"
tags: [task]
status: "2 - Next up"
due: 2026-11-12
priority: p1
effort: M
updated: 2026-11-12
---

# Connected realms: one guild key for members of every realm

The guild has members whose home realm is another realm of the connected group. `Guild:GetGuildKey()` builds
"Guild Name-Realm" from the PLAYER's realm (`Util.GetPlayerRealm`), so such a member computes a different guild key:
guild data lands in another bucket, and `Core/Bridge.lua` looks up `ns.BridgeKeys[<that key>]`, finds nothing, and
ignores the guild bot's records. Member keys are also inconsistent: the same character shows up under both realms
(peers / dungeon board under the guild's realm, a bug report under their own).

Fix idea: the guild key from the guild's realm (`GetGuildInfo("player")`'s realm return, else the player's realm);
member keys always with the character's own realm. Test with members on two realms of one guild.

## Done when

A member from another realm of the guild computes the same guild key as the GM, and takes the bot's records.
