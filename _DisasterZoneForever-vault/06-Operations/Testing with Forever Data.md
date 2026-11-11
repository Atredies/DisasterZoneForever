---
tags: [operations, testing, forever]
updated: 2026-11-11
---

# Testing with Forever Data

How the tests are kept true to the real WoW Forever client. Set-up first: [[Linux Dev Setup]].

## The loop

```
play with DZProbe -> read_probe.py -> results/DZProbe-*.json
                                        |-> mock_facts.py    -> dev/tools/wowmock/forever_facts.lua (mock profile)
                                        |-> export_replay.py -> dev/tests/forever/fixtures/*.json  (replays)
                                                                  -> dev/tests/forever/ suites
```

1. **Record:** `dev/probe/install.sh`, play (a dungeon with boss pulls, later a raid), log out,
   `python3 dev/probe/read_probe.py`. Facts note: [[Forever Client Facts]].
2. **Refresh the mock:** `python3 dev/probe/mock_facts.py` (newest run by default). It rewrites
   `forever_facts.lua`; never edit that file by hand. Behaviour the facts drive lives in `dev/tools/wowmock/forever.lua`.
3. **Cut a replay:** `python3 dev/probe/export_replay.py dev/probe/results/RUN.json dev/tests/forever/fixtures/NAME.json --name "..."`.
4. **Test:** `luaenv/bin/python tests/forever/test_forever_profile.py` and `test_deadmines_replay.py` (or the whole
   `tf_e/run_all.py --all`; `tests/forever/` is picked up automatically). Commit the facts and fixture; the probe
   dumps in `dev/probe/results/` are not kept in the repo.

## The Forever profile (`Client(w, name, forever=True)`)

| Measured on the client | In the mock |
|---|---|
| 1.60.1 / Interface 16001, `WOW_PROJECT_ID` 18, level cap 60 | `GetBuildInfo`, project ids, expansion 0 |
| ~45 old globals missing (`GetSpellInfo`, `UnitBuff`, `GetItemInfo`, talents, trade skills) | removed; C_ replacements present, so `Core/Compat.lua` shims them |
| `CRAFT_SHOW`, `LEARNED_SPELL_IN_TAB` gone | registering errors; `C_EventUtils.IsEventValid` false |
| Combat log forbidden for addons | registering it records an `ADDON_ACTION_FORBIDDEN` error (`__MOCK.forbidden`) |
| Boss pull: `ENCOUNTER_START`, then Encounter + Chat restrictions on; off again before `ENCOUNTER_END` | same order, `ADDON_RESTRICTION_STATE_CHANGED`, `C_RestrictedActions`, `__MOCK.restriction_log` |
| Addon messages refused during a pull (`AddOnMessageLockdown` 11) | `SendAddonMessage` returns 11, sends nothing; `__MOCK.lockdown_refused` |
| `UnitHealth` / `UnitHealthMax` / `UnitPower` / `UnitRangedDamage` secret; NPC target name/GUID secret in instances; a secret keeps its type ("a secret number value") | secret values: no arithmetic, no comparison, concat gives a secret; `issecretvalue`; `type()` / `tonumber()` answer like the client |
| Auras unreadable in combat | `C_UnitAuras.GetAuraDataByIndex` errors while the Combat restriction is on |
| No `OnTooltipSetItem` | `TooltipDataProcessor.AddTooltipPostCall` instead |
| `Frame:SetPropagateKeyboardInput` protected in combat (ADDON_ACTION_BLOCKED) | blocked in combat, recorded (`__MOCK.blocked`) |
| Retail profession window: `C_TradeSkillUI` (`GetAllRecipeIDs` lists learned and unlearned), `C_SkillInfo`; no `GetTradeSkill*` / craft window | both over the mock's `M.tradeskill` / `M.skills`; rows take `learned = false` |
| Names are first name + surname: `UnitName` -> `"Name", "Surname"`, roster `"Name Surname"` (no realm) | a client named "Name Surname" gets the same; `RegionalUniqueNamesEnabled()` true |

Not modelled yet: raid roster secrecy and the name form `GetRaidRosterInfo` returns, master loot
hand-out, battlegrounds (PvPMatch). They wait on probe round 2.

## Replays

| Fixture | Recorded | What it covers | Suite |
|---|---|---|---|
| `deadmines-2026-11-08.json` | 2026-11-08, a level-17 character, full clear | 9 pulls (3 wipes), combat, zoning, Encounter/Chat restrictions | `test_deadmines_replay.py` |

The replay forms a party of five Forever clients, shortens quiet gaps to 4 s, and has the guild talk around every pull
(a message larger than ChatThrottleLib's burst at the pull, small ones during it), and each client gets power, health,
aura and cast events in every fight. Loot rolls are in the fixture but
not replayed yet. Card: [[replay-real-forever-sessions|Replay real Forever sessions]].

## What it has caught

- 2026-11-08: multi-part messages queued in ChatThrottleLib when a pull starts lost their remaining parts (153 over
  the clear). Fixed in `Core/Comm.lua` (ChatThrottleLib paused during the lockdown); see [[Decision Log]].
- 2026-11-08: the first in-game session showed the GM twice on the Members page. Forever's surnames: the addon keyed
  itself from `UnitName` (first name only) while the roster had first name + surname. Fixed with `Util.UnitNameRealm`;
  `test_forever_names.py` uses Forever-style names (0/5 before the fix).
- 2026-11-09: in-game errors from secret numbers (resource bar 2,693x, shot timer). The mock's secrets were tables, so
  `tonumber(secret) or 0` hid them; now they answer `type()` / `tonumber()` like the client and the replay fires
  power/health events: both reproduced, then fixed.
- 2026-11-09: ADDON_ACTION_BLOCKED for `SetPropagateKeyboardInput` with the Atlas page first opened in a fight. The
  mock now blocks it in combat; `test_forever_keys.py` opens every page in combat (fails on the old code).
