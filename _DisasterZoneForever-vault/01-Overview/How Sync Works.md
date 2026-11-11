---
tags: [overview]
updated: 2026-11-11
---

# How Sync Works

How every member's DisasterZone keeps the same events, polls, raid plans and BiS lists. Plain-English summary of
`DZ Deep Dive 01-core-framework` > "Comms protocol" (09-Reference), with what Forever changes.

## No server: the addons talk to each other

Each copy talks to the others over WoW's hidden addon-message channels (GUILD, RAID, PARTY, WHISPER), through
`Core/Comm.lua` (AceComm + ChatThrottleLib). Messages are serialized, compressed and split across about 16 prefixes,
one per kind of traffic, so one busy kind cannot starve the others. A message from someone outside the guild or group
is dropped before it is even decoded.

## The sequence

1. **Hello.** 8-20 s after login each client sends one small HELLO on GUILD: its version, its own BiS list revision,
   and a short fingerprint (hash) of each shared dataset (events, polls, raid plans, prized items, raid leaders,
   blacklist, guest notes, Discord links...).
2. **Catching up.** A member whose fingerprint differs answers after a random delay (so 30 people don't reply at once).
   The newcomer gets the list of what exists, asks by whisper for only the records it lacks, and receives them. After
   that, edits are pushed live.
3. **Conflicts.** Every record carries a revision; the higher one wins. A tie goes to a fixed hash rule every client
   computes the same way, so all copies agree. Deletions are kept as tombstones for a while, so an event deleted
   while someone was offline doesn't come back from their copy.
4. **Owned data.** A BiS list has one writer: its owner. The loot council caches copies and swaps them among
   themselves every 10 minutes; nobody else can overwrite it. Small lists kept by a few writers (raid leaders,
   blacklist) travel as one revision number in the HELLO.
5. **Trust.** Nobody is "the server". Each client works out roles itself (guild rank 0 = GM, officers by rank, raid
   leader and master looter from the live roster, plus the synced council and raid-leader lists) and checks the
   sender's role on everything it receives.
6. **Addon version.** Upstream could stream a signed in-game update to everyone online (patch gossip on `CDLp1..4`).
   In this fork in-game updates are off, so everyone installs the release zip by hand.

## What Forever changes

- **No addon messages during a boss pull** (`AddOnMessageLockdown`): `Comm` holds outgoing messages and flushes them
  when the pull ends (`Compat:InChatLockdown()`), see [[Probe Findings 2026-11-08]].
- **Tighter send limit:** in a burst of 40 GUILD messages only 9 went out; ChatThrottleLib's pacing handles it.
- **Open question:** whether guild / raid roster names are secret inside a raid instance. If they are, role checks on
  received messages could fail in raids. Probe round 2 with a group, before 2026-12-09.

## Not the same thing: the Discord bridge

`DisasterZone_Bridge` (with the launcher and the bot server in `launcher/`) links the addon to Discord. That is a
separate path, not how players sync with each other in game.
