---
title: "Connected realms: one guild key for members of every realm"
tags: [task]
status: "5 - Done"
due: 2026-11-12
completed: 2026-11-15
priority: p1
effort: M
updated: 2026-11-15
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

## Done (2026-11-15)

`Core/Guild.lua` builds the key from the guild's realm (GetGuildInfo's 4th return; the player's realm when it is
nil). Member keys were already right: a name without a realm means the viewer's own realm on every client. The mock's
GetGuildInfo now returns the guild's home realm (the world's) for a member of another realm, as the client does;
`tests/cdl_council.py` seeds the council list under that key. Test: `tests/forever/test_connected_realms.py`;
`test_sync_flows` `j_cross_realm_member_sync_and_restore` covers the sync. Ships in 0.2.6. To confirm in game: a Realm 8 member's Discord sign-ups apply, and
their raids and BiS list reach the GM.
