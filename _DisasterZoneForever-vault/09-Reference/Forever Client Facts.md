---
tags: [reference, forever, probe]
updated: 2026-11-11
---

# Forever Client Facts

> Measured in the real WoW Forever client by the DZProbe addon (`dev/probe/`). Regenerate with `python3 dev/probe/read_probe.py` after playing with the probe installed. Raw data: `dev/probe/results/` (not kept in the repo).

- Probe run: 2026-11-08 18:47:31 · runs recorded: 4 · source: `DZProbe.lua`
- Character: Human WARRIOR level 17, Alliance, realm Realm Name PvP, locale enUS

## Key answers for the port

| Question | Answer | Matters for |
|---|---|---|
| Build / Interface | `['1.60.1', '70862', 'Nov  6 2026', 16001]` | TOC, mock `GetBuildInfo` |
| `WOW_PROJECT_ID` | `18` (known: {'WOW_PROJECT_ID': 18, 'WOW_PROJECT_CLASSIC': 2, 'WOW_PROJECT_CAMELOT': 18, 'WOW_PROJECT_MAINLINE': 1}) | flavor checks |
| Max level | `60` | level gates (TBC used 70) |
| `loadstring` runs | ✅ yes · setfenv ✅ yes | in-game updates (hotpatch) |
| `LoadSavedVariablesFirst` honoured | ✅ yes (per login: [False, True, True, True]) | hotpatch boot (Core/Boot.lua) |
| TOC `X-` fields readable | ✅ yes | `X-CDL-Protocol` |
| `loadDeprecationFallbacks` CVar | `1` | old global aliases |
| Master loot in the loot enum | ✅ yes · `SetLootMethod` ✅ yes · `GiveMasterLoot` ✅ yes · style `Vanilla` · now `Group` | loot council hand-out |
| Raid size constants | `{'NUM_RAID_GROUPS': 8, 'MAX_RAID_MEMBERS': 40, 'MEMBERS_PER_RAID_GROUP': 5}` | 10/20/40 raids |
| `GetGuildRosterInfo` | ✅ yes · own row returns `None` · rows readable `4` of `[4, 2]` | roles (Core/Guild.lua) |
| Guild rank index (probe character) | `0` `Guild Master` · leader ✅ yes · ranks `['Guild Master', 'Officer', 'Veteran', 'Member', 'Initiate']` | GM / officer detection |
| Officer note readable | type `None` · can view ✅ yes · can edit ✅ yes | mains/alts, officer notes |
| Item tooltip hook | `OnTooltipSetItem` exists ⛔ no, fired `0` · `TooltipDataProcessor` fired `29781` | BiS tooltip lines |
| Combat log | register forbidden ✅ yes · events seen `0` · `C_DamageMeter` ✅ yes · `C_EncounterTimeline` ✅ yes · `C_SwingTimer` ✅ yes | meters, boss mods, timers |
| Addon-message burst (40 on `GUILD`) | results `{'Success': 9, 'AddonMessageThrottle': 31}` · echoed back `9` | Comm throttle |
| `/roll` line | `{'message': {'t': 'string', 'v': 'Name Surname rolls 29 (1-100)', 'secret': False}, 'parsedWithRANDOM_ROLL_RESULT': True}` | loot rolls |
| `GetInventoryItemID` returns | `1` | mock fidelity |
| Item cache | Hearthstone `{'t': 'string', 'v': 'Hearthstone', 'secret': False}` · Thunderfury first `{'t': 'string', 'v': 'Thunderfury, Blessed Blade of the Windseeker', 'secret': False}`, after load `None` | Atlas / BiS |
| Talents | `{'activeConfig': 481773, 'GetNumTalentTabs': False, 'GetTalentInfo': False, 'C_Traits': True, 'C_ClassTalents': True}` | class planner, role detection |
| Static checks that errored | `none` · sample errors `0` | probe health |
| Secret-value helpers | `{'scrubsecretvalues': True, 'secretwrap': True, 'canaccessvalue': True, 'issecretvalue': True}` | Compat.lua |

## API surface the addon uses

Present: `{'EV': 122, 'C': 77, 'G': 252}`

**Missing C_ functions (0):** none

**Missing globals (96):** `All`, `Always`, `Atlas`, `BugGrabber`, `C`, `Cell`, `Characters`, `CloseBankFrame`, `CombatLogGetCurrentEventInfo`, `ExpandSkillHeader`, `Format`, `GetCoinTextureString`, `GetContainerItemInfo`, `GetCraftDisplaySkillLine`, `GetCraftInfo`, `GetCraftItemLink`, `GetCraftRecipeLink`, `GetFactionInfoByID`, `GetItemCount`, `GetItemGem`, `GetItemIcon`, `GetItemInfo`, `GetMerchantItemInfo`, `GetNumBankSlots`, `GetNumCrafts`, `GetNumSkillLines`, `GetNumSpellTabs`, `GetNumTalentGroups`, `GetNumTalentTabs`, `GetNumTalents`, `GetNumTradeSkills`, `GetSkillLineInfo`, `GetSpellBookItemName`, `GetSpellCooldown`, `GetSpellInfo`, `GetSpellLink`, `GetSpellSubtext`, `GetSpellTabInfo`, `GetSpellTexture`, `GetTalentInfo`, `GetTalentTabInfo`, `GetTradeSkillInfo`, `GetTradeSkillItemLink`, `GetTradeSkillLine`, `GetTradeSkillRecipeLink`, `GetWatchedFactionInfo`, `Host`, `InviteUnit`, `IsCurrentSpell`, `IsEquippableItem`, `IsItemInRange`, `IsSpellInRange`, `IsTradeSkillLinked`, `IsUsableSpell`, `L`, `Locked`, `None`, `Professions`, `UnitAura`, `UnitBuff`, `UnitDebuff`, `alpha`, `b`, `backdrop`, `circle`, `classID`, `debug`, `default`, `export`, `flag`, `frame`, `from`, `g`, `height`, `iconSize`, `io`, `item`, `itemID`, `l`, `me`, `name`, `os`, `player`, `r`, `rank`, `spell`, `t`, `text`, `texture`, `top`, `tsort`, `unit`, `used`, `value`, `x`, `y`

**Missing events (20):** `CRAFT_SHOW`, `ENVIRONMENTAL_DAMAGE`, `LEARNED_SPELL_IN_TAB`, `RANGE_DAMAGE`, `RANGE_MISSED`, `SPELL_AURA_APPLIED`, `SPELL_AURA_APPLIED_DOSE`, `SPELL_AURA_REFRESH`, `SPELL_AURA_REMOVED`, `SPELL_CAST_SUCCESS`, `SPELL_DAMAGE`, `SPELL_DISPEL`, `SPELL_EXTRA_ATTACKS`, `SPELL_HEAL`, `SPELL_INTERRUPT`, `SPELL_MISSED`, `SPELL_PERIODIC_DAMAGE`, `SPELL_SUMMON`, `SWING_DAMAGE`, `SWING_MISSED`

## What works where (passive samples)

Context = instance type | combat | encounter | active addon restrictions.

| Context | Samples | Addon sends | Chat lockdown | Secret values |
|---|---|---|---|---|
| `none|calm|noenc|unrestricted` | 74 | PARTY: {'Success': 46, 'GeneralError': 7}; WHISPER-self: {'Success': 67, 'GeneralError': 7}; GUILD: {'Success': 66, 'AddonMessageThrottle': 1} | false | UnitHealthMax(target), UnitHealth(target), UnitPower(player), UnitHealth(player) |
| `none|combat|noenc|Combat` | 21 | PARTY: {'Success': 21}; WHISPER-self: {'Success': 21}; GUILD: {'Success': 21} | false | UnitCastingInfo(target), UnitHealthMax(target), UnitHealth(target), UnitHealth(player), UnitPower(player) |
| `party|calm|encounter|Chat+Encounter+Map` | 51 | PARTY: {'AddOnMessageLockdown': 51}; WHISPER-self: {'AddOnMessageLockdown': 51}; GUILD: {'AddOnMessageLockdown': 51} | true | UnitCastingInfo(target), UnitHealthMax(target), UnitHealth(target), UnitGUID(target), UnitHealth(player), UnitPower(player), UnitName(target) |
| `party|calm|noenc|Map` | 798 | GUILD: {'Success': 784, 'AddonMessageThrottle': 9}; WHISPER-self: {'AddonMessageThrottle': 23, 'Success': 770, 'GeneralError': 5}; PARTY: {'AddonMessageThrottle': 35, 'Success': 758, 'GeneralError': 5} | false | UnitCastingInfo(target), UnitHealthMax(target), UnitHealth(target), UnitGUID(target), UnitHealth(player), UnitPower(player), UnitName(target) |
| `party|combat|encounter|Chat+Combat+Encounter+Map` | 134 | PARTY: {'AddOnMessageLockdown': 134}; WHISPER-self: {'AddOnMessageLockdown': 134}; GUILD: {'AddOnMessageLockdown': 134} | true | UnitHealthMax(target), UnitHealth(target), UnitGUID(target), UnitHealth(player), UnitPower(player), UnitName(target) |
| `party|combat|noenc|Combat+Map` | 617 | PARTY: {'Success': 558, 'AddonMessageThrottle': 59}; WHISPER-self: {'Success': 578, 'AddonMessageThrottle': 39}; GUILD: {'Success': 610, 'AddonMessageThrottle': 7} | false | UnitCastingInfo(target), UnitHealthMax(target), UnitHealth(target), UnitGUID(target), UnitHealth(player), UnitPower(player), UnitName(target) |

## Event log summary

Entries: 729 · by kind: `{'action-forbidden': 3, 'zone': 14, 'static': 4, 'group': 69, 'combat-start': 97, 'restriction': 240, 'combat-end': 97, 'loot': 161, 'loot-msg': 5, 'encounter-start': 9, 'encounter-end': 9, 'loot-roll': 21}` · handler errors: `0`

| When | Restriction | State | Context |
|---|---|---|---|
| 11-08 19:03:50 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-08 19:04:19 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-08 19:06:00 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-08 19:06:26 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-08 19:06:33 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-08 19:06:56 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-08 19:07:02 | Map | Activating | `none|calm|noenc|unrestricted` |
| 11-08 19:07:53 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:08:02 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:08:04 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:08:16 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:08:23 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:09:00 | Combat | Inactive | `none|calm|noenc|Map` |
| 11-08 19:09:00 | Map | Inactive | `none|calm|noenc|unrestricted` |
| 11-08 19:09:02 | Combat | Activating | `none|calm|noenc|unrestricted` |
| 11-08 19:09:03 | Combat | Inactive | `none|calm|noenc|unrestricted` |
| 11-08 19:09:08 | Map | Activating | `none|calm|noenc|unrestricted` |
| 11-08 19:09:09 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:09:36 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:10:08 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:10:38 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:11:31 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:11:36 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:11:47 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:11:54 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:11:58 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:12:03 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:12:05 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:12:19 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:12:22 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:12:34 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:12:38 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:13:04 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:13:20 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:13:38 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:13:44 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:13:55 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:13:58 | Combat | Activating | `party|calm|noenc|Map` |
| 11-08 19:14:18 | Combat | Inactive | `party|calm|noenc|Map` |
| 11-08 19:14:25 | Combat | Activating | `party|calm|noenc|Map` |

**action-forbidden:** `{'addon': 'DZProbe', 'ctx': 'none|calm|noenc|unrestricted', 'fn': 'UNKNOWN()'}`; `{'addon': 'DZProbe', 'ctx': 'none|calm|noenc|unrestricted', 'fn': 'UNKNOWN()'}`; `{'addon': 'DZProbe', 'ctx': 'none|calm|noenc|unrestricted', 'fn': 'UNKNOWN()'}`

**loot:** `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'nil', 'secret': False}, 'ctx': 'none|calm|noenc|unrestricted', 'method': 'Group'}`; `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'nil', 'secret': False}, 'ctx': 'none|calm|noenc|unrestricted', 'method': 'Group'}`; `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'string', 'v': '|cnIQ1:|Hitem:915::::::::17:1491:::::::::|h[Red Silk Bandana]|h|r', 'secret': False}, 'ctx': 'party|calm|noenc|Map', 'method': 'Group'}`; `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'string', 'v': '|cnIQ1:|Hitem:915::::::::17:1491:::::::::|h[Red Silk Bandana]|h|r', 'secret': False}, 'ctx': 'party|calm|noenc|Map', 'method': 'Group'}`; `{'items': {'t': 'number', 'v': 2, 'secret': False}, 'link1': {'t': 'string', 'v': '|cnIQ1:|Hitem:915::::::::17:1491:::::::::|h[Red Silk Bandana]|h|r', 'secret': False}, 'ctx': 'party|calm|noenc|Map', 'method': 'Group'}`

**encounter-start:** `{'difficulty': {'t': 'number', 'v': 1, 'secret': False}, 'name': {'t': 'string', 'v': "Rhahk'Zor", 'secret': False}, 'id': {'t': 'number', 'v': 2741, 'secret': False}, 'ctx': 'party|calm|noenc|Map', 'size': {'t': 'number', 'v': 5, 'secret': False}}`; `{'difficulty': {'t': 'number', 'v': 1, 'secret': False}, 'name': {'t': 'string', 'v': 'Sneed', 'secret': False}, 'id': {'t': 'number', 'v': 2742, 'secret': False}, 'ctx': 'party|calm|noenc|Map', 'size': {'t': 'number', 'v': 5, 'secret': False}}`; `{'difficulty': {'t': 'number', 'v': 1, 'secret': False}, 'name': {'t': 'string', 'v': 'Gilnid', 'secret': False}, 'id': {'t': 'number', 'v': 2743, 'secret': False}, 'ctx': 'party|combat|noenc|Combat+Map', 'size': {'t': 'number', 'v': 5, 'secret': False}}`; `{'difficulty': {'t': 'number', 'v': 1, 'secret': False}, 'name': {'t': 'string', 'v': 'Mr. Smite', 'secret': False}, 'id': {'t': 'number', 'v': 2745, 'secret': False}, 'ctx': 'party|calm|noenc|Map', 'size': {'t': 'number', 'v': 5, 'secret': False}}`; `{'difficulty': {'t': 'number', 'v': 1, 'secret': False}, 'name': {'t': 'string', 'v': 'Mr. Smite', 'secret': False}, 'id': {'t': 'number', 'v': 2745, 'secret': False}, 'ctx': 'party|calm|noenc|Map', 'size': {'t': 'number', 'v': 5, 'secret': False}}`

