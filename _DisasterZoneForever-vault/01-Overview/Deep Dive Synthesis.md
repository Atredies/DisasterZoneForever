---
tags: [incubator, wow, forever, addon, research]
status: phase-1-done
updated: 2026-11-11
source_repo: "github.com/tsumilo/DisasterZone-dev @ e21d5a9 (branch disasterzone)"
---

# Forever Guild Addon - Deep Dive Synthesis

> Phase 1 of building a WoW Forever version of **DisasterZone**, the <Casual Disaster> guild addon for TBC.
> The whole dev kit was read on 2026-11-08; the addon reports are in `09-Reference/Deep Dive/` (01-04 and 07).
> This note is the one-page answer.

## What DisasterZone is, in numbers

| Part | Language | Size | What |
|---|---|---|---|
| `addon/DisasterZone` | Lua 5.1 (WoW addons can only be Lua) | ~360K lines, 320 files | Core (107), UI (133), Data (40, mostly generated), Sim (25), Render3D, embedded libs |
| `addon/DisasterZone_*` | Lua | 7 extra addons | 6 game packs + 3D room data (load on demand) |
| `dev/` | Python 3 + Lua mock | ~28K lines of tools | specs, WoW-client mock, 300 suite runs in ~69 areas, generators, `release.py` |
| `launcher/` | **Rust** (Tauri 2) + HTML/JS | ~10K lines Rust | desktop launcher (`src-tauri`), Discord bot + web API (`server`), shared formats (`proto`) |

The "Rust" part is the launcher and the server. The addon itself stays Lua, because the game runs nothing else.

## How it works (one paragraph per layer)

- **Core** (report 01): home-grown framework (not Ace3). TOC order is load order; modules get `OnInit` / `OnLogin`; an internal bus of ~110 messages. Six account-wide SavedVariables, schema 2 with migrations and per-guild buckets. Comms: 16 AceComm prefixes, every message serialized + compressed + versioned, sender checked against guild/group before decode. BiS lists sync by owner revision; events, polls, prized, raid plans and strategies share one digest/want/give engine with tombstones.
- **Roles** (report 02): no server authority. Each client derives roles locally: guild rank 0 = GM, rank <= 1 = officer, raid leader + master looter from the live roster, plus synced lists (guild council picked by the GM, raid leaders edited by officers, per-raid council picked by that raid's leader). Alts inherit their main's roles. Handlers check the sender's role on receipt.
- **Leader features**: loot council (drop > roll > tiers > votes > award > master-loot hand-out > award log), soft reserves (+ LootReserve interop), raid plans / sign-ups, attendance, audit log, polls, recruitment, group finder, strategy boards, boss mods.
- **Testing** (report 04): each simulated player is its own Lua 5.1 runtime (lupa), a Python `World` routes messages, guild, raid, loot, `/roll` and relogs. Tests boot the real addon. `run_all.py` reruns only suites whose recorded dependencies changed, longest first, sharded, forked per case. `check.py` is the static gate.
- **Release**: `release.py` builds the release zip. In-game update = Lua-only, hash-signed (one-time signatures, 1023 uses), build-id pinned, monotonic sequence, spread over guild chat (`dev/docs/HOTPATCH.md`).

## Running the upstream tests (2026-11-08)

| Check | Result |
|---|---|
| Harness self-test | 13/13 pass |
| `run_all.py --all -j 12` | 282/300 suite runs, 2,915/2,987 cases, 308 s. After env fixes only 5 suites / 9 cases fail, none Linux-related |
| `check.py` | exit 1 on real upstream issues (a missing `local` in `UI/CombatTextLooks.lua:68`, 41 style-baseline hits) |

Linux notes: lupa 2.8 wheel works on Python 3.14; needs a `dev/luaenv/Scripts/python.exe` symlink and `DISASTERZONE_ADDON_DIR`; patch suites need `DZ_FORK=0`; never set `DZ_NATIVE_CACHE` under `/tmp` (grew to 3.1 GB).

## ⚠️ The big difference: Forever is the retail engine

Verified against Blizzard's own UI source for build **1.60.1.70862** (Gethe `wow-ui-source`, `forever` branch). Forever is the modern retail (12.x, Midnight) client running vanilla content, with retail addon restrictions.

| Area | TBC 2.5.6 | Forever 1.60.1 | Impact |
|---|---|---|---|
| `C_` APIs used (77) | present | all present | ✅ ports as-is |
| UI framework (own frames, menus, tooltip skin) | works | works | ✅ ports as-is |
| Addon comms | `C_ChatInfo` | same, plus a new **lockdown** send result | 🟡 add a send queue that flushes after lockdown |
| Combat log for addons | available | **gone** (`C_CombatLog.GetCurrentEventInfo` missing) | ⛔ meters, My Log, boss mods, BossLearn, combat text, swing/shot timers, Situation, StrategyLive must be rebuilt on `C_DamageMeter`, `C_EncounterTimeline`, `C_SwingTimer` or dropped |
| Unit / aura / cast / threat values in combat + instances | readable | **secret values** (display only, math errors) | ⛔ unit frames, plates, aggro, tanks, cast bars, resource bar, blessings/totems need secret-safe reads |
| Classic talent / spellbook / trade-skill / loot-frame / arena functions | present | removed | 🟡 most calls are guarded, so features go blank; talents move to `C_ClassTalents` / `C_Traits` |
| Item tooltip hook | `OnTooltipSetItem` | `TooltipDataProcessor` | 🟡 BiS tooltip lines silently vanish unless switched |
| Item data | all in client | ~80% hidden until seen | 🟡 Atlas/BiS need server-cached item info handling |
| Master loot | exists | **unverified** | ⛔ if absent, the council hand-out flow needs redesign |

## Content differences (report 03)

- **Reusable engines with new data:** Atlas, BiS, ItemDB, raid planner, groups board, boss-mod runner, strategy boards, 3D renderer, class planner.
- **Drop (TBC-only):** gems/sockets/Jewelcrafting, badges, arena, heroic keys, attunements, Outland, P1-P5 phases, Seal of Blood twist, Steady Shot timer, TBC totems.
- **New data needed:** raids Barrow Deeps (10, 8 bosses), Hyjal Summit (20, 13 bosses, a **different** raid from TBC's: new internal key), Onyxia (40); 8 new dungeons; raid sizes 10/20/40 (code hard-codes 10/25); level 60; phases.
- **Sources found:** Wowhead `/forever` (live, tooltips work), AtlasLoot Classic Forever (CurseForge 1422985, GPLv2, 1.60.1), `AtlasClassic.lua` already in DZ covers vanilla raids/dungeons. No DBM/BigWigs/Loon/WoWSims for Forever yet.
- **Gear sim** ports WoWSims TBC: heavy rework, do it last.

## Security holes to fix in our version (report 02)

1. Any officer can push loot/attendance/Discord/recruit rules claiming the GM wrote them (`Core/Guild.lua:1647-1663`).
2. Any raid assistant can replace the soft-reserve list (`Core/Reserves.lua:603-608`).
3. First-seen raid plan records trust their claimed author.
4. Officer is hard-coded to rank index <= 1; the developer is recognised by a hard-coded character name.
5. In-game updates apply on next reload without consent; at load only Adler-32 is re-checked; `PatchKey.lua` can be replaced by an update.

## Licensing

- `launcher/` is **MIT** (tsumilo): fork freely, keep the notice.
- The addon and dev kit have **no license file** upstream.
- `Data/` is generated from GPLv2 AtlasLoot data, so shipped data stays GPLv2.

## What came next

The port's work items are on the board ([[Work.base|Work]]).
