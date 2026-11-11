---
tags: [reference, forever, probe]
updated: 2026-11-11
---

# Forever Client Facts

> Measured in the real WoW Forever client by the DZProbe addon (`dev/probe/`). Regenerate with `python3 dev/probe/read_probe.py` after playing with the probe installed. Raw data: `dev/probe/results/` (not kept in the repo).

- Probe run: 2026-11-10 15:32:48 · runs recorded: 28 · source: `DZProbe.lua`
- Character: Human WARRIOR level 21, Alliance, realm Realm Name PvP, locale enUS

## Key answers for the port

| Question | Answer | Matters for |
|---|---|---|
| Build / Interface | `['1.60.1', '70862', 'Nov  6 2026', 16001]` | TOC, mock `GetBuildInfo` |
| `WOW_PROJECT_ID` | `18` (known: {'WOW_PROJECT_ID': 18, 'WOW_PROJECT_CLASSIC': 2, 'WOW_PROJECT_CAMELOT': 18, 'WOW_PROJECT_MAINLINE': 1}) | flavor checks |
| Max level | `60` | level gates (TBC used 70) |
| `loadstring` runs | ✅ yes · setfenv ✅ yes | in-game updates (hotpatch) |
| `LoadSavedVariablesFirst` honoured | ✅ yes (per login: [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]) | hotpatch boot (Core/Boot.lua) |
| TOC `X-` fields readable | ✅ yes | `X-CDL-Protocol` |
| `loadDeprecationFallbacks` CVar | `1` | old global aliases |
| Master loot in the loot enum | ✅ yes · `SetLootMethod` ✅ yes · `GiveMasterLoot` ✅ yes · style `Vanilla` · now `Group` | loot council hand-out |
| Raid size constants | `{'NUM_RAID_GROUPS': 8, 'MAX_RAID_MEMBERS': 40, 'MEMBERS_PER_RAID_GROUP': 5}` | 10/20/40 raids |
| `GetGuildRosterInfo` | ✅ yes · own row returns `None` · rows readable `8` of `[8, 3]` | roles (Core/Guild.lua) |
| Guild rank index (probe character) | `0` `Guild Master` · leader ✅ yes · ranks `['Guild Master', 'Officer', 'Veteran', 'Member', 'Initiate']` | GM / officer detection |
| Officer note readable | type `None` · can view ✅ yes · can edit ✅ yes | mains/alts, officer notes |
| Item tooltip hook | `OnTooltipSetItem` exists ⛔ no, fired `0` · `TooltipDataProcessor` fired `81024` | BiS tooltip lines |
| Combat log | register forbidden ✅ yes · events seen `0` · `C_DamageMeter` ✅ yes · `C_EncounterTimeline` ✅ yes · `C_SwingTimer` ✅ yes | meters, boss mods, timers |
| Addon-message burst (40 on `GUILD`) | results `{'Success': 9, 'AddonMessageThrottle': 31}` · echoed back `9` | Comm throttle |
| `/roll` line | `{'message': {'t': 'string', 'v': 'Name Surname rolls 86 (1-100)', 'secret': False}, 'parsedWithRANDOM_ROLL_RESULT': True}` | loot rolls |
| `GetInventoryItemID` returns | `1` | mock fidelity |
| Item cache | Hearthstone `{'t': 'string', 'v': 'Hearthstone', 'secret': False}` · Thunderfury first `{'t': 'nil', 'secret': False}`, after load `{'info': {'t': 'string', 'v': 'Thunderfury, Blessed Blade of the Windseeker', 'secret': False}, 'success': True, 'after': 0.009264799999073148}` | Atlas / BiS |
| Talents | `{'activeConfig': 481773, 'GetNumTalentTabs': False, 'GetTalentInfo': False, 'C_Traits': True, 'C_ClassTalents': True}` | class planner, role detection |
| Static checks that errored | `none` · sample errors `0` | probe health |
| Secret-value helpers | `{'scrubsecretvalues': True, 'secretwrap': True, 'canaccessvalue': True, 'issecretvalue': True}` | Compat.lua |
| Own name forms | `{'GetRealmName': 'Realm Name PvP', 'UnitFullName': ['Name', 'Surname'], 'AmbiguateFull': 'Name-Surname', 'UnitName': ['Name', 'Surname'], 'playerFullName': 'Name-Surname', 'GetUnitNameTrue': 'Name Surname', 'GetNormalizedRealmName': 'RealmNamePvP'}` | name keys (Name-Realm) |
| Roster name shapes | `{'space|0hyphen': 8}` · self row matched by `None` | name keys |
| Other addons' messages received | `{'GUILD': 5614, 'PARTY': 6518, 'RAID': 97, 'WHISPER': 113}` | Comm receive |

## Group roster readability (round 2)

Counts of value kinds per field; `secret` means the addon cannot read it there.

| Context | Rows | GetRaidRosterInfo fields | raidN / partyN unit calls |
|---|---|---|---|
| `none|calm|noenc|unrestricted` | 2049 | `{'subgroup': {'number': 2049}, 'zone': {'string': 2049}, 'class': {'string': 2049}, 'fileName': {'string': 2049}, 'combatRole': {'string': 2049}, 'online': {'boolean': 2049}, 'name': {'string': 2049}, 'isDead': {'boolean': 2049}, 'role': {'nil': 2049}, 'level': {'number': 2049}, 'isML': {'boolean': 2049}, 'rank': {'number': 2049}}` | `{'UnitIsConnected': {'boolean': 2049}, 'UnitGUID': {'string': 2049}, 'UnitName': {'string': 2049}, 'UnitIsGroupLeader': {'boolean': 2049}, 'UnitClass': {'string': 2049}}` |
| `none|combat|noenc|Combat` | 3724 | `{'subgroup': {'number': 3724}, 'zone': {'string': 3724}, 'class': {'string': 3724}, 'fileName': {'string': 3724}, 'name': {'string': 3724}, 'online': {'boolean': 3724}, 'combatRole': {'string': 3724}, 'isDead': {'boolean': 3724}, 'role': {'nil': 3724}, 'level': {'number': 3724}, 'isML': {'boolean': 3724}, 'rank': {'number': 3724}}` | `{'UnitIsConnected': {'boolean': 3724}, 'UnitGUID': {'string': 3724}, 'UnitName': {'string': 3724}, 'UnitClass': {'string': 3724}, 'UnitIsGroupLeader': {'boolean': 3724}}` |
| `party|calm|encounter|Chat+Encounter+Map` | 130 | `{'subgroup': {'number': 130}, 'zone': {'string': 130}, 'class': {'string': 130}, 'fileName': {'string': 130}, 'combatRole': {'string': 130}, 'online': {'boolean': 130}, 'name': {'string': 130}, 'isDead': {'boolean': 130}, 'role': {'nil': 130}, 'level': {'number': 130}, 'isML': {'boolean': 130}, 'rank': {'number': 130}}` | `{'UnitIsConnected': {'boolean': 130}, 'UnitGUID': {'string': 130}, 'UnitName': {'string': 130}, 'UnitIsGroupLeader': {'boolean': 130}, 'UnitClass': {'string': 130}}` |
| `party|calm|noenc|Map` | 5589 | `{'subgroup': {'number': 5589}, 'zone': {'string': 5589}, 'class': {'string': 5589}, 'fileName': {'string': 5589}, 'name': {'string': 5589}, 'online': {'boolean': 5589}, 'combatRole': {'string': 5589}, 'isDead': {'boolean': 5589}, 'role': {'nil': 5589}, 'level': {'number': 5589}, 'isML': {'boolean': 5589}, 'rank': {'number': 5589}}` | `{'UnitIsConnected': {'boolean': 5589}, 'UnitGUID': {'string': 5589}, 'UnitName': {'string': 5589}, 'UnitClass': {'string': 5589}, 'UnitIsGroupLeader': {'boolean': 5589}}` |
| `party|combat|encounter|Chat+Combat+Encounter+Map` | 840 | `{'subgroup': {'number': 840}, 'zone': {'string': 840}, 'class': {'string': 840}, 'fileName': {'string': 840}, 'name': {'string': 840}, 'online': {'boolean': 840}, 'combatRole': {'string': 840}, 'isDead': {'boolean': 840}, 'role': {'nil': 840}, 'level': {'number': 840}, 'isML': {'boolean': 840}, 'rank': {'number': 840}}` | `{'UnitIsConnected': {'boolean': 840}, 'UnitGUID': {'string': 840}, 'UnitName': {'string': 840}, 'UnitClass': {'string': 840}, 'UnitIsGroupLeader': {'boolean': 840}}` |
| `party|combat|noenc|Combat+Map` | 4445 | `{'subgroup': {'number': 4445}, 'zone': {'string': 4445}, 'class': {'string': 4445}, 'fileName': {'string': 4445}, 'name': {'string': 4445}, 'online': {'boolean': 4445}, 'combatRole': {'string': 4445}, 'isDead': {'boolean': 4445}, 'role': {'nil': 4445}, 'level': {'number': 4445}, 'isML': {'boolean': 4445}, 'rank': {'number': 4445}}` | `{'UnitIsConnected': {'boolean': 4445}, 'UnitGUID': {'string': 4445}, 'UnitName': {'string': 4445}, 'UnitClass': {'string': 4445}, 'UnitIsGroupLeader': {'boolean': 4445}}` |

## API surface the addon uses

Present: `{'EV': 122, 'C': 77, 'G': 282}`

**Missing C_ functions (0):** none

**Missing globals (66):** `All`, `Always`, `Atlas`, `BugGrabber`, `C`, `Cell`, `Characters`, `CombatLogGetCurrentEventInfo`, `Format`, `GetCraftDisplaySkillLine`, `GetCraftInfo`, `GetCraftItemLink`, `GetCraftRecipeLink`, `GetNumBankSlots`, `GetNumCrafts`, `GetNumTalentGroups`, `GetNumTalentTabs`, `GetNumTalents`, `GetNumTradeSkills`, `GetTalentInfo`, `GetTalentTabInfo`, `GetTradeSkillInfo`, `GetTradeSkillItemLink`, `GetTradeSkillLine`, `GetTradeSkillRecipeLink`, `Host`, `IsTradeSkillLinked`, `L`, `Locked`, `None`, `Professions`, `alpha`, `b`, `backdrop`, `circle`, `classID`, `debug`, `default`, `export`, `flag`, `frame`, `from`, `g`, `height`, `iconSize`, `io`, `item`, `itemID`, `l`, `me`, `name`, `os`, `player`, `r`, `rank`, `spell`, `t`, `text`, `texture`, `top`, `tsort`, `unit`, `used`, `value`, `x`, `y`

**Missing events (20):** `CRAFT_SHOW`, `ENVIRONMENTAL_DAMAGE`, `LEARNED_SPELL_IN_TAB`, `RANGE_DAMAGE`, `RANGE_MISSED`, `SPELL_AURA_APPLIED`, `SPELL_AURA_APPLIED_DOSE`, `SPELL_AURA_REFRESH`, `SPELL_AURA_REMOVED`, `SPELL_CAST_SUCCESS`, `SPELL_DAMAGE`, `SPELL_DISPEL`, `SPELL_EXTRA_ATTACKS`, `SPELL_HEAL`, `SPELL_INTERRUPT`, `SPELL_MISSED`, `SPELL_PERIODIC_DAMAGE`, `SPELL_SUMMON`, `SWING_DAMAGE`, `SWING_MISSED`

## What works where (passive samples)

Context = instance type | combat | encounter | active addon restrictions.

| Context | Samples | Addon sends | Chat lockdown | Secret values |
|---|---|---|---|---|
| `none|calm|noenc|unrestricted` | 1094 | RAID: {'Success': 14}; PARTY: {'AddonMessageThrottle': 5, 'Success': 681, 'GeneralError': 8}; WHISPER-self: {'Success': 1084, 'GeneralError': 10}; GUILD: {'Success': 1066, 'AddonMessageThrottle': 18} | false | UnitCastingInfo(target), UnitHealthMax(target), UnitHealth(target), UnitPower(player), UnitHealth(player) |
| `none|combat|noenc|Combat` | 1782 | GUILD: {'Success': 1782}; WHISPER-self: {'Success': 1782}; PARTY: {'Success': 1450} | false | UnitCastingInfo(target), UnitHealthMax(target), UnitHealth(target), UnitHealth(player), UnitPower(player) |
| `party|calm|encounter|Chat+Encounter+Map` | 26 | PARTY: {'AddOnMessageLockdown': 26}; WHISPER-self: {'AddOnMessageLockdown': 26}; GUILD: {'AddOnMessageLockdown': 26} | true | UnitHealthMax(target), UnitHealth(target), UnitGUID(target), UnitHealth(player), UnitPower(player), UnitName(target) |
| `party|calm|noenc|Map` | 1211 | GUILD: {'Success': 1195, 'AddonMessageThrottle': 8}; WHISPER-self: {'AddonMessageThrottle': 18, 'Success': 1185, 'GeneralError': 8}; PARTY: {'AddonMessageThrottle': 40, 'Success': 1074, 'GeneralError': 6} | false | UnitHealthMax(target), UnitHealth(target), UnitGUID(target), UnitHealth(player), UnitName(target), UnitPower(player) |
| `party|combat|encounter|Chat+Combat+Encounter+Map` | 168 | GUILD: {'AddOnMessageLockdown': 168}; WHISPER-self: {'AddOnMessageLockdown': 168}; PARTY: {'AddOnMessageLockdown': 168} | true | UnitCastingInfo(target), UnitHealthMax(target), UnitHealth(target), UnitGUID(target), UnitName(target), UnitHealth(player), UnitPower(player) |
| `party|combat|noenc|Combat+Map` | 889 | GUILD: {'Success': 874, 'AddonMessageThrottle': 15}; WHISPER-self: {'Success': 839, 'AddonMessageThrottle': 50}; PARTY: {'Success': 800, 'AddonMessageThrottle': 89} | false | UnitCastingInfo(target), UnitHealthMax(target), UnitHealth(target), UnitGUID(target), UnitName(target), UnitHealth(player), UnitPower(player) |

## Event log summary

Entries: 1500 · by kind: `{'loot-opened': 141, 'loot': 282, 'loot-slot-cleared': 235, 'restriction': 315, 'combat-end': 136, 'combat-start': 135, 'group': 156, 'loot-method-changed': 13, 'zone': 38, 'static': 6, 'loot-roll': 27, 'encounter-start': 8, 'encounter-end': 8}` · handler errors: `0`

| When | Restriction | State | Context |
|---|---|---|---|
| 11-09 19:52:09 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:52:29 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:52:59 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:53:29 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:53:37 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:54:14 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:55:11 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:55:12 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:55:39 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:55:40 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:55:50 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:56:23 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:56:39 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:57:18 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:57:31 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:57:53 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:59:16 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 19:59:33 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 19:59:51 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:00:11 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:00:34 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:00:40 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:01:00 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:01:09 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:02:44 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:02:49 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:03:54 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:21:43 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:21:48 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:25:05 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:25:23 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:25:29 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:26:35 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:27:07 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:27:27 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:27:29 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:27:50 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:27:54 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-09 20:28:27 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-09 20:28:33 | Combat | Activating | `none|calm|noenc|unrestricted` |

**loot:** `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'nil', 'secret': False}, 'ctx': 'none|combat|noenc|Combat', 'method': 'Group'}`; `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'nil', 'secret': False}, 'ctx': 'none|combat|noenc|Combat', 'method': 'Group'}`; `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'nil', 'secret': False}, 'ctx': 'none|combat|noenc|Combat', 'method': 'Group'}`; `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'nil', 'secret': False}, 'ctx': 'none|combat|noenc|Combat', 'method': 'Group'}`; `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'nil', 'secret': False}, 'ctx': 'none|combat|noenc|Combat', 'method': 'Group'}`

**encounter-start:** `{'difficulty': {'t': 'number', 'secret': False, 'v': 1}, 'name': {'t': 'string', 'secret': False, 'v': "Rhahk'Zor"}, 'id': {'t': 'number', 'secret': False, 'v': 2741}, 'ctx': 'party|calm|noenc|Map', 'size': {'t': 'number', 'secret': False, 'v': 5}}`; `{'difficulty': {'t': 'number', 'secret': False, 'v': 1}, 'name': {'t': 'string', 'secret': False, 'v': 'Sneed'}, 'id': {'t': 'number', 'secret': False, 'v': 2742}, 'ctx': 'party|combat|noenc|Combat+Map', 'size': {'t': 'number', 'secret': False, 'v': 5}}`; `{'difficulty': {'t': 'number', 'secret': False, 'v': 1}, 'name': {'t': 'string', 'secret': False, 'v': 'Gilnid'}, 'id': {'t': 'number', 'secret': False, 'v': 2743}, 'ctx': 'party|combat|noenc|Combat+Map', 'size': {'t': 'number', 'secret': False, 'v': 5}}`; `{'difficulty': {'t': 'number', 'secret': False, 'v': 1}, 'name': {'t': 'string', 'secret': False, 'v': 'Mr. Smite'}, 'id': {'t': 'number', 'secret': False, 'v': 2745}, 'ctx': 'party|calm|noenc|Map', 'size': {'t': 'number', 'secret': False, 'v': 5}}`; `{'difficulty': {'t': 'number', 'secret': False, 'v': 1}, 'name': {'t': 'string', 'secret': False, 'v': 'Captain Greenskin'}, 'id': {'t': 'number', 'secret': False, 'v': 2744}, 'ctx': 'party|calm|noenc|Map', 'size': {'t': 'number', 'secret': False, 'v': 5}}`

**group:** `{'inRaid': False, 'method': 'Group', 'ctx': 'none|combat|noenc|Combat', 'leader': False, 'n': 0}`; `{'inRaid': False, 'method': 'Group', 'ctx': 'none|calm|noenc|unrestricted', 'leader': False, 'n': 2}`; `{'inRaid': False, 'method': 'Group', 'ctx': 'none|combat|noenc|Combat', 'leader': False, 'n': 2}`; `{'inRaid': False, 'method': 'Group', 'ctx': 'none|calm|noenc|unrestricted', 'leader': False, 'n': 2}`; `{'inRaid': False, 'method': 'Group', 'ctx': 'none|calm|noenc|unrestricted', 'leader': False, 'n': 2}`

**loot-method-changed:** `{'ctx': 'none|calm|noenc|unrestricted', 'method': 'Group'}`; `{'method': 'Group', 'ctx': 'none|calm|noenc|unrestricted'}`; `{'method': 'Freeforall', 'ctx': 'none|calm|noenc|unrestricted'}`; `{'method': 'Group', 'ctx': 'none|combat|noenc|Combat'}`; `{'method': 'Group', 'ctx': 'none|calm|noenc|unrestricted'}`

**loot-opened:** `{'GetMasterLootCandidate': True, 'method': 'Group', 'mlRaid': {'t': 'nil', 'secret': False}, 'GiveMasterLoot': True, 'mlParty': {'t': 'nil', 'secret': False}, 'candidatesSlot1': {'nils': 40, 'readable': 0, 'secret': 0}, 'ctx': 'none|combat|noenc|Combat'}`; `{'GetMasterLootCandidate': True, 'method': 'Group', 'mlRaid': {'t': 'nil', 'secret': False}, 'GiveMasterLoot': True, 'mlParty': {'t': 'nil', 'secret': False}, 'candidatesSlot1': {'nils': 40, 'readable': 0, 'secret': 0}, 'ctx': 'none|combat|noenc|Combat'}`; `{'GetMasterLootCandidate': True, 'method': 'Group', 'mlRaid': {'t': 'nil', 'secret': False}, 'GiveMasterLoot': True, 'mlParty': {'t': 'nil', 'secret': False}, 'candidatesSlot1': {'nils': 40, 'readable': 0, 'secret': 0}, 'ctx': 'none|combat|noenc|Combat'}`; `{'GetMasterLootCandidate': True, 'method': 'Group', 'mlRaid': {'t': 'nil', 'secret': False}, 'GiveMasterLoot': True, 'mlParty': {'t': 'nil', 'secret': False}, 'candidatesSlot1': {'nils': 40, 'readable': 0, 'secret': 0}, 'ctx': 'none|combat|noenc|Combat'}`; `{'GetMasterLootCandidate': True, 'method': 'Group', 'mlRaid': {'t': 'nil', 'secret': False}, 'GiveMasterLoot': True, 'mlParty': {'t': 'nil', 'secret': False}, 'candidatesSlot1': {'nils': 40, 'readable': 0, 'secret': 0}, 'ctx': 'none|combat|noenc|Combat'}`

**loot-slot-cleared:** `{'method': 'Group', 'slot': {'t': 'number', 'v': 1, 'secret': False}, 'ctx': 'none|combat|noenc|Combat'}`; `{'method': 'Group', 'slot': {'t': 'number', 'v': 1, 'secret': False}, 'ctx': 'none|combat|noenc|Combat'}`; `{'method': 'Group', 'slot': {'t': 'number', 'v': 2, 'secret': False}, 'ctx': 'none|combat|noenc|Combat'}`; `{'method': 'Group', 'slot': {'t': 'number', 'v': 1, 'secret': False}, 'ctx': 'none|combat|noenc|Combat'}`; `{'method': 'Group', 'slot': {'t': 'number', 'v': 1, 'secret': False}, 'ctx': 'none|combat|noenc|Combat'}`

**loot-roll:** `{'canNeed': {'t': 'boolean', 'v': True, 'secret': False}, 'rollID': {'t': 'number', 'v': 1, 'secret': False}, 'link': {'t': 'string', 'v': '|cnIQ2:|Hitem:3036::::::::20:1491:::::::::|h[Heavy Shortbow]|h|r', 'secret': False}, 'ctx': 'none|combat|noenc|Combat', 'name': {'t': 'string', 'v': 'Heavy Shortbow', 'secret': False}, 'ok': True, 'quality': {'t': 'number', 'v': 2, 'secret': False}}`; `{'canNeed': {'t': 'boolean', 'secret': False, 'v': True}, 'rollID': {'t': 'number', 'secret': False, 'v': 1}, 'link': {'t': 'string', 'secret': False, 'v': '|cnIQ2:|Hitem:5578::::::::20:1491::1::1:28:5240:::::|h[Plans: Silvered Bronze Breastplate]|h|r'}, 'ctx': 'party|combat|noenc|Combat+Map', 'name': {'t': 'string', 'secret': False, 'v': 'Plans: Silvered Bronze Breastplate'}, 'ok': True, 'quality': {'t': 'number', 'secret': False, 'v': 2}}`; `{'canNeed': {'t': 'boolean', 'secret': False, 'v': True}, 'rollID': {'t': 'number', 'secret': False, 'v': 2}, 'link': {'t': 'string', 'secret': False, 'v': "|cnIQ2:|Hitem:7608::::::::20:1491::1::1:28:5240:::::|h[Seer's Fine Stein]|h|r"}, 'ctx': 'party|combat|noenc|Combat+Map', 'name': {'t': 'string', 'secret': False, 'v': "Seer's Fine Stein"}, 'ok': True, 'quality': {'t': 'number', 'secret': False, 'v': 2}}`; `{'canNeed': {'t': 'boolean', 'secret': False, 'v': True}, 'rollID': {'t': 'number', 'secret': False, 'v': 3}, 'link': {'t': 'string', 'secret': False, 'v': '|cnIQ2:|Hitem:1930::::::::20:1491::1::1:28:5240:::::|h[Stonemason Cloak]|h|r'}, 'ctx': 'party|combat|noenc|Combat+Map', 'name': {'t': 'string', 'secret': False, 'v': 'Stonemason Cloak'}, 'ok': True, 'quality': {'t': 'number', 'secret': False, 'v': 2}}`; `{'canNeed': {'t': 'boolean', 'secret': False, 'v': True}, 'rollID': {'t': 'number', 'secret': False, 'v': 4}, 'link': {'t': 'string', 'secret': False, 'v': '|cnIQ3:|Hitem:872::::::::20:1491::1::1:28:5240:::::|h[Rockslicer]|h|r'}, 'ctx': 'party|calm|noenc|Map', 'name': {'t': 'string', 'secret': False, 'v': 'Rockslicer'}, 'ok': True, 'quality': {'t': 'number', 'secret': False, 'v': 3}}`

