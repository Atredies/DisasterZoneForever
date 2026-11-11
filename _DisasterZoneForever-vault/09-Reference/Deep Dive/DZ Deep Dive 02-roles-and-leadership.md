# 02 - Roles, permissions and leadership features (DisasterZone 1.5.5, TBC Anniversary)

Scope: the role model and every guild-management / raid-leader / loot-council / officer feature.
All paths are relative to `addon/DisasterZone/` in the read-only clone unless they start with `dev/`.
Line numbers are from the clone as read on 2026-11-08.

---

## 1. Summary

- **There is no central role server.** Every client computes every role locally from three inputs: the live guild
  roster (`GetGuildRosterInfo` rank index), the live raid roster (`GetRaidRosterInfo` rank and `isML`), and a few
  small signed-by-sender lists that are synced over addon messages (`Core/Guild.lua:1-7`).
- **Roles come from four places:**
  1. **Guild rank.** Rank 0 = Guild Master. Rank 0 and 1 = officer (`OFFICER_RANK = 1`, hard-coded,
     `Core/Guild.lua:996`, `Core/Guild.lua:1393-1404`). Officer notes and guild rank permissions are not read.
  2. **GM-picked lists.** The guild council list (CG, `Core/Guild.lua:2162`) plus the GM-only rules (loot,
     attendance, recruitment, Discord) that ride on the raid leaders record (RLL, `Core/Guild.lua:1603-1670`).
  3. **Officer-picked list.** The raid leaders list (RLL, any officer can set it, `Core/Guild.lua:1615`).
  4. **Live group state.** The raid leader (rank 2) is always loot council for their own raid, together with the
     raid list that leader picks (CR, `Core/Guild.lua:836-880`). The master looter joins the council while the raid
     session runs the loot council (`Core/Guild.lua:461-469`, `568-579`). The raid session "authority"
     (GroupRules) is the raid leader, else the ML, else an assistant who holds the raid log (`Core/GroupRules.lua:280-345`).
- **Accounts.** Alts share their main's roles through "vouches" (ACB). A vouch only counts when heard from the vouching
  character itself or passed on by someone who holds every role that character has (`Core/Guild.lua:1014-1131`).
- **Enforcement** is receiver-side: the game names the sender of an addon message, and every handler re-checks that
  sender's role against its own local view before it applies anything (`Core/Comm.lua:445-480`). Comm also gates
  GUILD/WHISPER traffic to guild members and RAID/PARTY traffic to real group members before decoding.
- **Main Forever risks:** (a) Forever's client is a modern engine with the Midnight-style addon restrictions
  (`Enum.AddOnRestrictionType` Combat/Encounter/ChallengeMode/PvPMatch/Map, secret values, `C_ChatInfo.InChatMessagingLockdown`),
  so addon messages and chat-line parsing (`/roll`, loot lines) may be blocked or secret during boss fights. (b) Master
  loot may not exist. (c) Raid sizes are hard-coded to 10/25 and level 70 / TBC phases.

---

## 2. Role model + capability matrix

### 2.1 How each role is decided

| Role | Decided by | Stored | Synced by | Code |
|---|---|---|---|---|
| **Guild Master** | Roster row with rankIndex 0 (lowest key on ties). If hidden (offline rows hidden) the last GM seen in this guild is kept. Alts the GM vouches for count as GM (`IsGMKey`). | `db.council.gm = {key, g}` (cache only) | Nothing: read from the roster | `Core/Guild.lua:282-299`, `301-353`, `1123-1131`, `2082-2086` |
| **Officer** | rankIndex <= 1 (GM + the rank below), or an alt vouched by such a character | Nothing | Nothing | `Core/Guild.lua:996`, `1393-1404` |
| **Guild council** (guild-wide loot council) | The GM's list, only once *confirmed* (received straight from the GM or saved by the GM). A "tofu" list (trust on first use, relayed) names nobody. Member must also be in the roster. Alts inherit. | `db.council.guild = {rev, members, phase, by, recvAt, g, src, de, bank}`; other guilds parked in `db.council.otherGuilds` | `CG` (GUILD/WHISPER, ctrl) and `CQ` query; GM reshare when someone holds a different rev; `cg` rev rides in HELLO/STATE | `Core/Guild.lua:356-391`, `520-553`, `651-810`, `2162-2180`, `2275-2319` |
| **Listed raid leader** | Officers' list. Alts inherit. | `db.raidLeaders[guildKey] = {rev, m, by, ar, arBy, lr, lrBy, dc, dcBy, rc, rcBy}` | `RLL` (GUILD/WHISPER), `rlr` rev in HELLO + `RLQ` query (DigestSync RevList) | `Core/Guild.lua:1001-1012`, `1411-1422`, `1603-1670`, `1839-1865` |
| **Raid planner** | GM or listed raid leader | derived | - | `Core/Guild.lua:1424-1426` |
| **Raid log member** | Raid planner or guild council | derived | - | `Core/Guild.lua:1433-1436` |
| **Attendance reviewer** | GM, officer or guild council | derived | - | `Core/Guild.lua:1440-1443` |
| **Raid log reader** | Raid log member or attendance reviewer | derived | - | `Core/Guild.lua:1448-1450` |
| **Raid leader (live)** | `GetRaidRosterInfo` rank == 2. Counts as council of that raid only if they are in my guild (pugs never). | memory | - | `Core/Guild.lua:404-425`, `555-559`, `568-579` |
| **Raid council (raid list)** | The live raid leader's own saved "raid list", shared with the raid. Members must be in my guild and in the raid. | Leader: `db.council.myRaidList`; others: memory only for that raid | `CR` (RAID, only from rank 2) / `CRQ` | `Core/Guild.lua:393-399`, `836-891`, `2220-2238` |
| **Master looter** | `GetRaidRosterInfo` isML (or party ML via `C_PartyInfo.GetLootMethod`). Council source `"ml"` only while the raid session runs the loot council and the ML is in my guild. | memory | `PARTY_LOOT_METHOD_CHANGED` re-reads | `Core/Guild.lua:427-446`, `461-469`, `1902-1905`; `Core/Util.lua:569-578`, `665-672`, `708-731` |
| **Raid session authority** | GroupRules: raid leader > ML > guild assistant with the raid log (alphabetical) > last session keeper; pugs skipped; must "speak" DZ (sent GS/GQ). Party: leader if guild council or dungeon mode on, else a guild council member. | memory + `db.groupFeatures` | `GS` / `GQ` / `GSQ` / `GSA` (RAID/PARTY) | `Core/GroupRules.lua:1-47`, `280-372`, `823-937` |
| **Raid's own leader** (planned raid) | Named on the raid record (`rl`) by the GM or a listed raid leader (`rlb`) | `db.raidplan[guildKey]` | RaidPlan digest sync | `Core/RaidPlan.lua:25-30`, `210-245` |
| **Roster manager** (guests, blacklist, guest book) | Raid planner or officer | derived | - | `Core/RaidPlan.lua:200-208` |
| **Recruiter** | GM; officers unless the GM's rules turn it off (`wk.o`); listed raid leaders if `wk.l` | derived | - | `Core/Recruit.lua:85-97` |
| **Discord host** | Named by the GM (`dc.h`) | on the RLL record | RLL | `Core/Guild.lua:1789-1793` |
| **Developer / feedback staff** | A hard-coded developer character name (+ its vouched alts); staff = dev + officers | constant | - | `Core/Feedback.lua:50`, `139-186`; debug roles `Core/Guild.lua:494-518` |
| **Debug role** | `/dz role gm|officer|council|raidleader|raider`, only on the developer character; changes only my own UI, never what others accept (`real` flag) | `db.debugRole` | never | `Core/Guild.lua:494-518`, `1867-1890` |

**Who grants / revokes:**
- GM is changed only in-game (guild leadership transfer). DZ follows the roster.
- Officers are changed only by guild rank (in-game promote/demote).
- Guild council: the GM only (`CanEditGuildCouncil`, `Core/Guild.lua:2155-2157`). Revoking = saving a list without them.
- Raid leaders list: any officer, including the GM (`CanEditRaidLeaders`, `Core/Guild.lua:1406-1408`).
- Raid list: each player's own (only used while they lead a raid), `Core/Guild.lua:2220`.
- Raid's own leader: GM or listed raid leaders (`Core/RaidPlan.lua:210-212`).
- Alts: the player via automatic vouch at login and `/dz account forget <name>` (`Core/Guild.lua:1347-1383`).

### 2.2 Role -> capability matrix

Legend: Y = yes, R = read only, own = own records only, raid = only for the raid they are in / lead.

| Capability | GM | Officer | Guild council | Listed raid leader | Live raid leader (guild) | Raid list pick | Master looter (guild) | Raider | Code |
|---|---|---|---|---|---|---|---|---|---|
| Pick guild council, guild phase, guild DE/bank targets | Y | - | - | - | - | - | - | - | `Core/Guild.lua:2155-2180` |
| Pick raid leaders list | Y | Y | - | - | - | - | - | - | `Core/Guild.lua:1406`, `1615` |
| Loot rules, attendance rules, recruitment rules, Discord set-up | Y | R (recruit) | R | R | R | R | R | R | `Core/Guild.lua:1685`, `1719-1745`, `1755-1777`, `1795-1837` |
| Loot council member (see BiS lists, vote, award) | Y | - | Y | - | raid | raid | raid (loot council on) | - | `Core/Guild.lua:568-612`, `2090-2096` |
| Start a roll in a raid | Y (in raid) | - | Y | - | Y | Y | Y (always, even plain) | - | `Core/Roll.lua:2421-2431`, `1273` |
| End / award a council roll | Y | - | Y | - | Y | Y | Y while loot council on (as council) | - | `Core/Roll.lua:196-207`, `2560-2570`, `2601-2640` |
| End / award a plain roll (no loot council) | Y | - | Y | - | Y | Y | Y | - | `Core/Roll.lua:196-207` |
| Hand out with master loot | - | - | - | - | - | - | Y (game rule) | - | `Core/Loot.lua:1321-1380` |
| Award log (Ledger) full sync | Y | - | Y | - | single awards of the last 12 h | same | - | - | `Core/Ledger.lua:144-162`, `1050-1100` |
| Run raid session (start/end, features loot/rolls/lock/reserve, roll duration, quality, phase) | if authority | if authority | if authority | if authority | Y (authority) | - | fallback authority | - | `Core/GroupRules.lua:280-372` |
| Lock BiS lists | via session | | | | Y | | | - | `Core/GroupRules.lua:20-26` |
| Host soft reserves (RVS) | authority | | | | Y | | fallback | request own (RVR) | `Core/Reserves.lua:12-17`, `593-643` |
| Plan raids (series, events, cancel, delete) | Y | - | - | Y | raid's own leader for that raid | - | - | sign up own | `Core/RaidPlan.lua:180-290` |
| Teams (members, specs, nights) | Y | - | Y | - | - | - | - | R | `Core/RaidPlan.lua:190-193` |
| Raid group layout | Y | - | Y (raids without own leader) | Y | raid's own leader | - | - | R | `Core/RaidPlan.lua:195-198`, `253-258` |
| Strategy picks / assignments on a raid | Y | - | - | Y (no own leader) | raid's own leader | - | - | R | `Core/RaidPlan.lua:262-269` |
| Guests, decline/remove answers, blacklist, guest book notes | Y | Y | - | Y | raid's own leader | - | - | - | `Core/RaidPlan.lua:200-208`; `Core/GuestBook.lua:1-12` |
| Invite & sort | needs game lead/assist | | | | Y | | | - | `Core/RaidInvite.lua:1-8`, `30-34` |
| Raid log read / sync | Y | attendance pages only | Y | Y | - | - | - | own attendance (ATQ) | `Core/RaidLog.lua:45-60`; `Core/Guild.lua:1433-1456` |
| Raid log linking, bench marks, deleting | Y | - | Y | Y | - | - | - | - | `Core/Guild.lua:1445-1448` |
| Attendance marks during the raid (bench, swap, removed, officers decide) | if authority | | | | Y (authority, ATM) | | | own reason (ATY) | `Core/Attendance.lua:1433-1445`, `1519-1540` |
| Attendance review decisions (Excuse / Counts) | Y | Y | Y | - | - | - | - | - | `Core/Attendance.lua:89-94`, `1128-1129` |
| Dry streaks view | Y | - | Y | - | - | - | - | - | `Core/Attendance.lua:996-1000` |
| Audit log (see, keep, sync, Put back) | Y | - | Y | - | - | - | - | - | `Core/Audit.lua:1-9`, `69-90` |
| Officer notes (DZ long notes) | Y | Y | - | - | - | - | - | - | `Core/OfficerNotes.lua:1-12`, `146-151` |
| Polls: ask | Y | Y | Y | - | - | - | - | answer if asked | `Core/Polls.lua:129-136` |
| Polls: close/extend/remove any | Y | own | own | - | - | - | - | - | `Core/Polls.lua:153-161` |
| Events: review/rank, remove anyone's | Y | Y | Y | - | - | - | - | build own, sign up | `Core/Events.lua:157-170` |
| Events: season (moderate) | Y | Y | - | - | - | - | - | - | `Core/Events.lua:150-155` |
| Prized items rules | Y | - | Y | - | - | - | - | R | `Core/Prized.lua:125-131` |
| Record a prized hand-out | Y | - | Y | Y (raid log) | Y (council) | Y | Y | - | `Core/Prized.lua:135-141` |
| Recruitment records, guild invite, officer-note write | Y | Y (if `wk.o`) | - | if `wk.l` | - | - | - | introduce friends (if `it`) | `Core/Recruit.lua:85-97`, `1005-1056`; `Core/RecruitIntro.lua:1-14` |
| Feedback: answer, status, merge | Y | Y | - | - | - | - | - | post, me-too | `Core/Feedback.lua:160-186` |
| Main tank order (MTO) | - | - | - | - | Y | - | - | assistants too | `Core/Tanks.lua:1-12`, `110-116` |
| Discord sign-ups for others (RPH) | - | - | - | - | - | - | - | Discord host only | `Core/RaidPlan.lua:1355-1372` |
| Large addon messages (24 KB wire, 200 KB inflated) | Y | - | Y | Y | raid | raid | raid | 4 KB / 16 KB | `Core/Comm.lua:47-60`, `320-332` |

Notes:
- "Guild council" in practice always includes the GM: `GuildSource` returns `"gm"` first (`Core/Guild.lua:527-553`).
- A raid leader is **not** loot council by being on the raid leaders list. Listed raid leaders get the raid log, not
  loot data (`dev/tests/raidplan/test_raidplan_leaders.py` docstring). They only become loot council while they
  actually lead a raid (rank 2).
- Raid assistants have **no** loot rights (1.3 decision, `Core/Roll.lua:14-16`, `Core/Loot.lua:345-349`).

---

## 3. Feature flows

### 3.1 Loot council decision (raid, loot council on)

1. **Session.** The authority starts a raid session (`GS rs/rsAt rf="lrk"`, RAID). Until then drops, votes and awards are
   off in a raid (`Core/GroupRules.lua:34-38`). Starting also locks BiS lists (`rf` k).
2. **BiS lists reach the council.** Guild council holds everyone's lists all the time (Sync H/S/M/W/L/R). A raid-scope
   council member (raid leader / raid list / ML) receives raiders' lists only while that session runs with the loot
   council, and drops them afterwards (`Core/Sync.lua:1-9`).
3. **Drop.** Loot window scan, then `D` on RAID (`Core/Loot.lua:323-337`). Under master loot only the ML or a council
   member may announce (`TrustedDropSender`, `Core/Loot.lua:345-357`). Receivers dedupe by source key.
4. **Roll.** A council member or the ML sends `RS {id,i,s,b,d,ts,c,pl,rv,rk}` on RAID (`Core/Roll.lua:2421-2460`).
   Reserves decide who may roll (`ReserveDecision`, `Core/Roll.lua:177-186`). Raiders answer `RR` (roll/pass) and type
   `/roll`, parsed from `CHAT_MSG_SYSTEM` (`RANDOM_ROLL_RESULT`, `Core/Roll.lua:60`).
5. **Tiers and votes.** Each council client whispers `RT` (BiS tier per candidate, lock flags) to council members who
   lack the data (`Core/Roll.lua:2378-2420`). Council members vote with `RV` on RAID, one vote each, names visible
   (`Core/Roll.lua:2689-2701`). The suggestion = most votes, ties by BiS tier then roll, shaped by the GM's loot rules
   (`Guild.LOOT_RULES`, `Core/Guild.lua:1490-1527`) and prized-item gates (`PrizedGate`, `Core/Roll.lua:2012`).
6. **Close / award.** A manager sends `RE` then `RW {id,w,g,at,n,r}` (`Core/Roll.lua:1998-2100`, `2601-2680`).
   The ML hands the item out with `GiveMasterLoot` (`Core/Loot.lua:1164-1190`, `1321-1380`); under Free for All the
   holder trades it (bag loot, `Core/Loot.lua:595-620`). Clashing awards resolve deterministically
   (`AwardBeats`, `Core/Roll.lua:2575-2582`).
7. **Ledger.** Every council client records the award (`Ledger:RecordRollAward`, `Core/Ledger.lua:571`). Single awards
   travel as `A` whispers between council members (`Core/Ledger.lua:1050-1068`); the full log syncs by per-day digest
   (`LW`/`LG`) between guild-wide council only. Disenchant / bank hand-outs by an ML outside the council use `LT`
   (`Core/Loot.lua:1386-1410`, `Core/Ledger.lua:618`).

**Authoritative:** the roll starter for the session id; the manager (council / ML) for the award; the ML's hand-out
beats a recorded award. No single client owns the ledger: it is a merge (CRDT-like) across council clients.

### 3.2 Soft reserve

1. The raid session's `reserve` feature (`GS rv=1`, `Core/GroupRules.lua:127-175`) makes reserves the loot method.
2. The **host = the session authority** (`AmHost`, `Core/Reserves.lua:72-77`) holds the list
   `{id, by, v, rk, n, o, h, r, cl}` (`Core/Reserves.lua:2-21`), saved for 12 h (`KEEP_SAVED`).
3. Inputs: host UI; `RVR` from DZ raiders (RAID, own reserve/cancel, `Core/Reserves.lua:630-643`); `!sr` whispers and
   raid lines (`Core/ReserveChat.lua`); LootReserve clients on LootReserve's own prefixes `LootReserve`,
   `LootReserve1..40` (`Core/ReserveLR.lua:1-25`); CSV / softres.it / Gargul imports (`Core/ReserveIO.lua`).
4. Output: the whole list as `RVS` on RAID; joiners ask `RVQ` (`Core/Reserves.lua:593-628`). If another player hosts
   LootReserve, DZ mirrors it read-only (`Reserves:Mirror`, `Core/Reserves.lua` ~650).
5. On a drop `Reserves:Decide(itemID)` returns `"s"` + reservers, `"g"` (guild hard reserve: loot council among guild
   members) or `"o"` (up for grabs) (`Core/Reserves.lua:279-287`); Roll carries it in RS.

**Authoritative:** the host. Receivers accept RVS from the authority, from the holder of the current list, or from any
raid leader/assistant (`Core/Reserves.lua:603-608`).

### 3.3 Raid sign-up

1. Raid planners write series `S` and events `E`; GM/guild council write teams `T` (`Core/RaidPlan.lua:1-6`).
   Live edits go out as `RPU` on GUILD with `r.by == sender` enforced (`Core/RaidPlan.lua:1312-1317`).
2. Each character writes only its own sign-up (`RPS`, GUILD, `Core/RaidPlan.lua:1319-1335`); alts of the same account
   via `RPA` (`SameAccount` check, `1337-1355`); Discord answers via `RPH` from the GM-named Discord host only
   (`1355-1372`).
3. Lock / invite-only, minimum level (`ml`, default 70, `MAX_LEVEL = 70`, `Core/RaidPlan.lua:88`), guests `gu`,
   declined `rj`, removed `rm` live on the raid record (`Core/RaidPlan.lua:8-24`). Blacklist `BLL` from roster
   managers only (`Core/RaidPlan.lua:1816-1860`).
4. Login sync: HELLO carries a plan hash (`pd`); digests `RPD`, wants `RPW`, items `RPG` one per message (DigestSync,
   `Core/RaidPlan.lua:36-42`, `386`). Records merge by rev then hash. Trust marks per record version
   (`Trusted`/`Entitled`, `Core/RaidPlan.lua:271-312`).
5. On raid night: Invite & sort invites the group layout (`Core/RaidInvite.lua`), RaidLink links the running session to
   the planned raid (`Core/RaidLink.lua:1-9`), riding on `GS rp/rpAt`.

**Authoritative:** each record's writer (`by`) as checked against current roles; sign-ups by their owner.

### 3.4 Attendance

1. **Recording.** Every client in the raid records the session locally into `db.raids` (no single recorder): zone, kills
   (`RLK` from any raider, `Core/RaidLog.lua:451-470`), presence pieces per player every 60 s
   (`Core/RaidLog.lua:1-45`). The record closes when the authority ends the session.
2. **Expected list** snapshot from the planned raid: the lineup's grouped players or Accept answers
   (`Att:Snapshot`, `Core/Attendance.lua:159`).
3. **Live marks** from the authority only: `ATM` on RAID (bench, swap in, removed, officers decide)
   (`Core/Attendance.lua:1433-1445`). A leaving player gets a prompt and whispers their reason `ATY` to raid log readers
   (`Core/Attendance.lua:1484`, `1519-1540`).
4. **Credit** = time there / time expected after the GM's margins (`o` on-time minutes, `d` disconnect minutes,
   defaults 5/10, `Core/Guild.lua:1671-1700`). Server trouble gaps are excused.
5. **Reviews.** Early leaves / reasons open a review; GM, officers or guild council decide (`Att:Decide`,
   `Core/Attendance.lua:1128`). Decisions `dc` merge with the record.
6. **Sync.** Closed records travel `RLD` (digest) / `RLW` / `RLG` by whisper between guild-council pairs, digests also on
   Sync's H/M (`Core/RaidLog.lua:1494-1545`). Raiders ask their own attendance with `ATQ` -> `ATR`
   (`Core/Attendance.lua:1704-1730`).

**Authoritative:** the session authority for marks and session end; reviewers for decisions; records merge.

### 3.5 Audit

1. Each module calls `ns.AuditSaw(kind, old, new, ctx)` when a shared record changes on this client (own edit
   `ctx.mine`, merged peer version `ctx.via`) (`Core/Audit.lua:7-9`, `265`). `Core/AuditKinds.lua` (1053 lines) turns
   diffs into entries per area: raids, loot, strat, members, guests, events, recruit, roles, addon (`Core/Audit.lua:48`).
   Roles changes are audited at CG store (`Core/Guild.lua:681`) and RLL (`Core/Guild.lua:1594-1601`).
2. Recorded only on GM / confirmed guild council clients, never in demo mode or with a debug role (`Core/Audit.lua:83`),
   and only after `since` (first-sync suppression).
3. Entry id = hash(o, sk, v, t): copies of the same change fold. Kept 90 days, max 6000.
4. Sync on prefix CDLz by whisper, both ends staff: `AUE` entries live, `AUD` per-day digest
   (`Core/Audit.lua:19-22`, `526-575`). "Put back" restores removed records where the kind supports it
   (`Core/Audit.lua:389`).

**Authoritative:** none; union of what every staff client saw.

---

## 4. Admin / GM configuration

GM-only settings (all shared on the RLL record or CG, `Core/Guild.lua:1480-1837`, `2155-2180`):

| Setting | Where in UI | Data | Code |
|---|---|---|---|
| Guild council members (max 40) | Settings > Loot Council (Council tab picker) | CG `m` | `UI/Council.lua:3506-3566`, `Core/Guild.lua:2162` |
| Guild phase (1-5, TBC phases) | same | CG `ph` | `Core/Guild.lua:2168-2171`, `2326-2350` |
| Guild disenchanter / guild bank characters | same | CG `de`/`bk` | `Core/Guild.lua:2243-2260` |
| Loot rules: attendance floor %, vote split (roll / council picks), list-first or roll-only, then highest roll or driest, dry streak counts nights there or any, longest use up to phase 3-5, prized notice or show roll | Council > Rules | RLL `lr` | `Core/Guild.lua:1490-1527`, `1703-1745`; `UI/CouncilRules.lua:600-615` |
| Attendance margins (on-time 0-60, disconnect 0-60 minutes) | Settings > Attendance | RLL `ar` | `Core/Guild.lua:1482-1490`, `1685-1700`; `UI/Settings.lua:4260-4475` |
| Recruitment rules: officers/raid leaders work on recruits, members introduce, unclaimed days, check-ins, milestones (58, 70, first dungeon, first raid), gone-quiet days, not-now days, tell raid leaders at 70, tags, welcome line, officer-note template | Settings > Recruitment | RLL `rc` | `Core/Guild.lua:1551-1589`, `1747-1777`; `UI/Settings.lua:4366-4380` |
| Discord: host character, guild channel, this-week board, loot feed, per-team channels | Settings > Discord | RLL `dc` | `Core/Guild.lua:1529-1549`, `1779-1837`; `UI/Settings.lua:4290-4340` |
| Raid leaders list (also officers) | Raids > Raid leaders | RLL `m` | `UI/RaidLeadersUI.lua:141` |
| Set-up checklist (council, raid leaders, loot rules, attendance, first raid) | Settings > Guild set-up, Home chip | derived | `UI/WelcomeTour.lua:342-390`; `UI/Settings.lua:150-152` |

Raid-leader / authority settings (per group, not guild-wide): roll duration 15-60 s, quality threshold, dungeon mode
and 5-man quality, group phase, features loot/rolls/lock/reserve, reserves per player 1-3
(`Core/GroupRules.lua:56-60`, `127-175`, `380-410`; `UI/SessionDrawer.lua:492`, `561`). Each player's own raid list and
raid DE/bank targets (`Core/Guild.lua:2220-2238`).

---

## 5. Security of authority

### 5.1 What makes it work

- **Sender identity is the game's.** AceComm passes the server-provided sender; DZ normalizes it and gates before decode:
  GUILD/WHISPER only from guild members (unknown senders held up to 60 s while the roster loads), RAID/PARTY only from
  real group members; cross-guild group whispers limited to `RT` (`Core/Comm.lua:309-312`, `401-480`).
- **Every handler re-checks the sender's role on its own client** (examples): CG only from the GM or a confirmed-list
  council member relaying the GM's own list (`Core/Guild.lua:709-780`); CR only from raid rank 2
  (`Core/Guild.lua:859-866`); RLL only from an officer, and its GM-only fields only if sender or the stated author is GM
  (`Core/Guild.lua:1630-1667`); RS from council/ML (`Core/Roll.lua:2427-2434`); RE/RW via `Manages`
  (`Core/Roll.lua:203-207`); RV/RT from council (`Core/Roll.lua:2382-2383`, `2694-2696`); A/LW/LG council pairs
  (`Core/Ledger.lua:1050-1080`); ATM from the authority (`Core/Attendance.lua:1438-1440`); audit, officer notes,
  recruit records both ends checked (`Core/Audit.lua:526-528`, `Core/OfficerNotes.lua:146-151`).
- **Trust on first use is contained.** A relayed guild list is stored as `tofu` and names nobody until the GM's own CG
  confirms it; the GM's direct CG outranks any relayed list whatever its rev (`Core/Guild.lua:520-525`, `651-655`,
  `746-757`). Future revs are rejected (`FUTURE_SLACK`, `Core/Guild.lua:727-731`).
- **Account vouches** can only grant roles the relayer could grant its own alt (`CoversRoles`,
  `Core/Guild.lua:1078-1086`).
- **Payload limits.** Non-council senders: 4 KB wire, 16 KB inflated; deflate bombs (ratio > 16) get the sender ignored
  for the session (`Core/Comm.lua:47-60`, `320-345`).
- **Hostile tests** exist (`dev/tests/sync/test_sync_hostile.py`, 14 cases; forged records in polls, prized, raidplan
  trust, accounts, recruit).

### 5.2 Weak spots found (worth fixing in the Forever port)

1. **Any officer can forge GM-only rules.** `OnRaidLeaders` accepts `lr`/`ar`/`dc`/`rc` when the *claimed* author
   `lrb`/`arb`/`dcb`/`rcb` is the GM, from any officer sender (`Core/Guild.lua:1647-1663`). An officer can therefore
   change loot rules, attendance margins, the Discord host (who can then file RPH sign-ups for anyone) and recruit rules
   "as the GM". Revs are also free-form up to now + 60 s, so an officer can overwrite the raid leaders list at will
   (which is intended) but also pin a high rev.
2. **Relayed raid-plan records take `by` at its word** on a client that never had the record (`Core/RaidPlan.lua:40-42`):
   a guild member can seed a fresh client with a raid "by" a raid leader.
3. **RVS accepted from any raid leader or assistant**, not only the authority (`Core/Reserves.lua:603-608`): a raid
   assistant can replace the soft-reserve list on every client.
4. **The live raid leader is automatically loot council for that raid** whoever they are in the guild
   (`Core/Guild.lua:568-579`). Any guild member who forms a raid gets council rights there, by design.
5. **Officer = rank index <= 1, hard-coded** (`Core/Guild.lua:996`). Guild rank permissions (officer chat, edit officer
   note) are ignored. A guild with "Officer" at rank 2 loses those rights; rank 1 alts gain them.
6. **Audit entries carry the author `w` as sent** by a council peer (`Core/Audit.lua:530-546`): a council member can
   insert fabricated entries; nothing is signed.
7. **Developer identity by character name** (`Core/Feedback.lua:50`, `Core/Guild.lua:501`): on another server a
   player with that name gets feedback-staff powers and the debug-role slash command (UI only).

---

## 6. Tests

Python harness running the real addon Lua against a WoW mock (`dev/tools/wowmock/game.lua`, multiple simulated clients;
run with `luaenv\Scripts\python.exe tests\<area>\<file>.py`). Counts are decorated cases per file.

| Area | Files (cases) | Covers |
|---|---|---|
| council | `test_council_picker.py` (17), `test_accounts.py` (5) | GM picks council (CG/CQ, relays, tofu), raid leader + raid list; alts share roles, forged vouches refused |
| sync | `test_council_membership.py` (4), `test_raid_council_lists.py` (2), `test_ledger_sync.py` (10), `test_sync_hostile.py` (14), `test_sync_flows.py`, `test_mixed_versions.py` | membership changes live, raid-scope list access only during the session, ledger digest sync, forged/malformed traffic |
| loot-roll | `test_loot_rights.py` (5), `test_award.py` (17), `test_bag_loot.py` (9), `test_guest_rolls.py` (1), `test_rolls.py`, `test_drops.py`, `test_ledger_auto.py` | 1.3 loot rights (pugs never council, ML joins council), awards, FFA bag loot, guests |
| votes | `test_votes.py` (21), `test_loot_rules.py` (14), `test_demo_scenarios.py` (8) | reasons, RV votes, DE/bank targets, GM loot rules |
| rollclose | `test_rollclose.py` | closing races |
| reserves | `test_reserves.py` (10), `test_edges.py` (5), `test_io.py` (6), `test_lootreserve.py` (5, against LootReserve's real Comm.lua in `dev/thirdparty/LootReserve`), `test_demo.py` (3) | list, rules, sync, whispers, imports, interop |
| grouprules | `test_grouprules.py` (13) (+ `addon02/` old CDLoot copy for mixed versions) | authority resolution, GS rules |
| raidlog | `test_raidlog.py` (21), `test_raid_features.py` (18), `test_raid_link.py` (3), `test_raid_session_edges.py` (3) | sessions, forged GS refused, features, linking |
| attendance | `test_attendance.py` (27), `test_dry_streak.py` (11) | expected list, pieces, margins, reviews |
| audit | `test_audit.py` (11) | who keeps/sees, sync, Put back, demo |
| raidplan | 20 files incl. `test_raidplan_leaders.py` (14), `test_raidplan_trust.py` (8), `test_raidplan_raid_leader.py` (7), `test_guestbook.py` (16), `test_raidplan_invite.py`, `test_raidplan_lock.py`, `test_raidplan_guests.py`, `test_raidplan_groups.py` | raid leaders and who plans, trust of records, raid's own leader, guests/blacklist, invite & sort |
| teamcomp | `test_lineups.py`, `test_nights.py`, `test_teamcomp.py` | lineups, raid nights, comp |
| members | `test_members.py` (17) | roster, alts, officer notes |
| polls | `test_polls.py` (14) | ask/answer, forged poll dropped |
| prized | `test_prized.py` (10), `test_loot_rules_page.py` (4), `test_prized_look.py` (11) | rules, forged records |
| events | 19 files, e.g. `test_events.py` (12), `test_edge_live.py`, `test_kinds_*.py` | library, reviews, live host handover |
| recruit | 6 files: `core` (9), `invite` (9), `members` (6), `message` (10), `page` (6), `settling` (5) | recruiters only, sync, guild invite |
| feedback | `test_feedback.py` (24) + 3 more | staff, dev numbering |
| groups / dungeons | `test_groups_*.py`, `test_dungeon_runs.py`, `test_group_finder.py` | LFG message, Group Finder |

Gap: no test for an officer forging GM-only fields in RLL (5.2 item 1) was found by name.

---

## 7. Forever deltas

Evidence base: the installed Forever addons in
a Forever client's `_forever_/Interface/AddOns` folder (all TOCs `## Interface: 16001`).
They show Forever's project id is `WOW_PROJECT_CAMELOT` ("Camelot", to be renamed "Forever")
(`DialogueUI/Initialization.lua:242-251`, `Questie/Modules/VersionCheck.lua:60`), and that addon authors treat it as
"modern" like retail: "Modern (Standard & Forever) have Secrets" (`DialogueUI/Initialization.lua:250`), Auctionator
maps Camelot to retail (`Auctionator/Source/Constants/Main.lua:56`). VERIFIED = seen in code that targets Forever;
UNVERIFIED = needs an in-game `/dump`.

### 7.1 Guild APIs

| Item | TBC 2.5.6 use | Forever | Status |
|---|---|---|---|
| `GetGuildRosterInfo(i)` returns name, rankName, rankIndex, level, ..., isOnline, status, classFile | `Core/Guild.lua:311` | Still present; EnhanceQoL reads the same 17-return shape incl. guid (`EnhanceQoL/Core/Streams/Stream_Friends.lua:378`). Name likely always `Name-Realm`; `Util.NormalizeName` must keep handling it. | VERIFIED (exists), UNVERIFIED (name format) |
| `C_GuildInfo.GuildRoster()` | `Core/Guild.lua:1982-1984` | Present (`Stream_Friends.lua:303`, Details). | VERIFIED |
| `GUILD_ROSTER_UPDATE(canRequestRosterUpdate)`, `PLAYER_GUILD_UPDATE` | `Core/Guild.lua:1896-1897` | Event exists on all modern clients; arg semantics unverified. | UNVERIFIED |
| Officer by rank index <= 1 | `Core/Guild.lua:996` | Replace with rank permissions: retail-style `C_GuildInfo.IsGuildOfficer()` (self only), `C_GuildInfo.CanEditOfficerNote()`, `GuildControlGetRankFlags`. Keep a configurable "officer ranks" set on the GM record so other clients can judge others. | UNVERIFIED |
| `GuildInvite`, `CanGuildInvite`, `GuildRosterSetOfficerNote`, `CanEditOfficerNote` | `Core/Recruit.lua:1005-1056` | Retail moved some to `C_GuildInfo.Invite` and protected others. | UNVERIFIED |
| `GetGuildInfo("player")` for the guild key | `Core/Guild.lua:255-270` | Present on modern clients (also returns realm). | UNVERIFIED |
| Chat line parsing of "X has joined the guild" | `Core/RecruitIntro.lua:1-6` | Chat messages can be **secret values** on Forever: Questie guards `CHAT_MSG_SYSTEM` with `issecretvalue(message)` (`Questie/Modules/EventHandler/EventHandler.lua:449-454`). | VERIFIED (secrets exist), UNVERIFIED (when) |

### 7.2 Group, loot method, master loot

| Item | TBC use | Forever | Status |
|---|---|---|---|
| `C_PartyInfo.GetLootMethod()` + `Enum.LootMethod.Masterlooter (2)` / `Freeforall (0)` | `Core/Util.lua:569-578`, `Core/Loot.lua:351-353`, `603-605` | The modern API name is the one DZ already uses, but whether Forever offers Master Looter at all is unknown. Retail removed master loot in 8.0. If missing: the "ml" council source, `TrustedDropSender`, `GiveMasterLoot` hand-out, `LT`, and bag-loot logic all go dead, and the loot council must work by trade (bag loot path) or group loot. | UNVERIFIED (critical) |
| `GetRaidRosterInfo` 11th return `isML` | `Core/Guild.lua:427-437`, `Core/Util.lua:714`, `Core/GroupRules.lua:287` | Details reads it on Forever-era code (`Details/functions/coach.lua:561`), but it may always be false. | UNVERIFIED |
| `GiveMasterLoot`, `GetMasterLootCandidate`, `OPEN_MASTER_LOOT_LIST` | `Core/Loot.lua:1113-1190` | Exist only if master loot exists. | UNVERIFIED |
| Group loot (`START_LOOT_ROLL`, need/greed) | `Core/Loot.lua:1449` | Modern group loot adds transmog/disenchant buttons; event exists. | UNVERIFIED |
| `UnitIsGroupLeader`/`UnitIsGroupAssistant`, `C_PartyInfo.InviteUnit`, `LeaveParty`, `UninviteUnit` | many | Present on modern clients (`EnhanceQoL/Submodules/GroupTools_Camelot.lua`). | VERIFIED (group basics) |
| Distribution `RAID` for home raids | everywhere | Fine for normal groups; instance/LFG groups need `INSTANCE_CHAT`. | UNVERIFIED |

### 7.3 Addon message and chat restrictions (biggest risk to loot council and attendance)

- Forever addons reference `Enum.AddOnRestrictionType` {Combat, Encounter, ChallengeMode, PvPMatch, Map},
  `ADDON_RESTRICTION_STATE_CHANGED`, `C_RestrictedActions` and `C_ChatInfo.InChatMessagingLockdown()`
  (`Details/core/parser_nocleu1.lua:154-160`, `EnhanceQoL/Submodules/GroupTools_Camelot.lua:1215`,
  `EnhanceQoL/Core/DataPanel.lua:528`). Details ships a "no CLEU" parser for this client. VERIFIED that these exist in
  Forever-targeted code; UNVERIFIED exactly which addon messages are blocked during an Encounter.
- If `SendAddonMessage` / `CHAT_MSG_ADDON` are locked during boss encounters (as in retail Midnight), then RS/RR/RV/RW
  in the middle of a fight, `RLK` kill reports and `GS` changes queue or fail. Loot happens after the kill, so most
  loot traffic is outside the encounter window, but the code must check `InChatMessagingLockdown()` and the
  `Enum.SendAddonMessageResult` return (Questie's patched ChatThrottleLib already maps results and skips secret
  text, `Questie/Libs/AceComm-3.0/ChatThrottleLib.lua:280-381`). DZ embeds its own CTL/AceComm (`DisasterZone.toc`)
  which must be updated to a modern-aware version.
- `/roll` results come from `CHAT_MSG_SYSTEM` (`Core/Roll.lua:60`, roll parser). If system lines are secret in
  instances, roll parsing breaks: rolls would need an addon-side roll (`RR` with a value) or a `C_` roll API. Same for
  `CHAT_MSG_LOOT` award parsing (`Core/Loot.lua:1448`). UNVERIFIED, test first.
- Raid warning / raid chat announcements (`Core/ReserveChat.lua:44`) may be blocked by messaging lockdown. UNVERIFIED.

### 7.4 Raid sizes, levels, phases (data deltas, VERIFIED in DZ code)

| Hard-coded | Where | Forever change |
|---|---|---|
| Raid/team sizes only 10 or 25 | `Core/RaidPlan.lua:122`, `3264`, `3464`; `UI/RaidPlanUI.lua:3135`, `3278`, `3377-3378` | 10 / 20 / 40 (Barrow Deeps 10, Hyjal 20, Onyxia 40) |
| Group count `size == 10 and 2 or 5`, comp themes for 10/25 | `Core/RaidComp.lua:194-201`, `306`, `702` | `ceil(size / 5)`: 2 / 4 / 8 groups; themes per size |
| Raid min level `MAX_LEVEL = 70` | `Core/RaidPlan.lua:88`, `777`, `2740` | 60 |
| Recruit milestones 58 / 70, "tell raid leaders at 70" | `Core/Guild.lua:1551-1562`; `Core/Recruit.lua:1230` | e.g. 50 / 60 |
| Phases 1-5 (TBC), longest-use counted to phase 3-5 | `Core/Guild.lua:71-75`, `1490-1520` | Forever's own phase plan (Onyxia first) |
| "Never a 10-man player at the 25" attendance rule | `Core/Attendance.lua` (lineup per size) | per 10/20/40 lineup |
| `MAX_COUNCIL = 40`, roster loops to 40 | `Core/Guild.lua:22`, `410` | unchanged (40-man raids fit) |
| Prized defaults (Dragonspine, Warglaives, Thori'dal) | `Core/Prized.lua:1-4` | Forever items (data from another report) |
| LootReserve categories by raid key | `Core/ReserveLR.lua:33-38`, `Data/Raids.lua lr` | LootReserve's Forever categories, if LootReserve supports Forever (installed list says "add if a Forever group uses it") |

### 7.5 PvP-server angle

- Same-faction only: guild and raid are single-faction on a PvP server, so the GUILD/RAID gates already cover it.
  Opposite-faction players cannot join the guild or raid, so they cannot send DZ traffic at all. VERIFIED by design of
  `Core/Comm.lua:445-480` (guild member or group member only); faction rules UNVERIFIED for Forever.
- `PvPMatch` is one of the restriction types (7.3): inside battlegrounds addon messaging may be locked. Guild events
  (EventLive duels, GroupPvP) should not rely on traffic inside a BG. UNVERIFIED.
- World PvP raids (40-man raid groups for world PvP) would start a GroupRules authority and could turn on the raid
  session, the raid log and attendance by mistake; consider a "PvP raid" kind that records no attendance. Design note.
- Officer notes, recruit records and audit stay whisper-only between staff, so enemy players never see them; but on a
  PvP server spies inside the guild are a real concern: the 5.2 weak spots (officer forging GM rules, assistant
  replacing reserves, relayed raid records) matter more there.

### 7.6 Port checklist for roles (short)

1. Replace `OFFICER_RANK = 1` with a GM-set officer-rank set shared on the GM record.
2. Make GM-only fields on RLL accepted only when the **sender** is the GM (drop the `lrb`/`arb`/`dcb`/`rcb` claim path),
   or split them into a GM-only message.
3. Restrict RVS to the authority (and the list holder), not any assistant.
4. Probe master loot in-game (`/dump C_PartyInfo.GetLootMethod(), Enum.LootMethod, GiveMasterLoot`) before porting
   `Core/Loot.lua`; design a trade-based (bag loot) path as the default if ML is absent.
5. Probe addon messaging during an encounter (`C_ChatInfo.InChatMessagingLockdown()`, send results) and whether
   `CHAT_MSG_SYSTEM` `/roll` lines are secret in a raid instance.
6. Re-key sizes 10/20/40, level 60, phases, milestones; rename the dev character constant.
