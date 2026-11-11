# 07 - DisasterZone UI layer and WoW API surface vs WoW Forever 1.60.1

Report 7. Scope: part A, the UI layer (`addon/DisasterZone/UI`, 126 files + 7 in `UI/Comp`, about 169K lines). Part B, the WoW client API the whole addon uses, classified against Forever 1.60.1 (Interface 16001). Read-only. Nothing in the clone or the client was changed.

## Sources (how "VERIFIED" is earned)

| Tag | Source |
|---|---|
| **[F-doc]** | `Gethe/wow-ui-source` branch **`forever`**, head commit "1.60.1 (70862)", 2026-11-07, `Blizzard_APIDocumentationGenerated` (643 files). **This is the exact build installed**: `.build.info` lists `1.60.1.70862` for product `wowf`. |
| **[F-src]** | Same branch, only the Lua/XML that the TOCs load for game type `camelot` (resolved with `[Family]`=Mainline, `[Game]`=Camelot, `AllowLoadGameType camelot/mainline`, XML includes followed): 3,505 files. |
| **[A-doc] / [A-src]** | Branch `classic_anniversary`, "2.5.6 (70577)", the same treatment for game type `tbc` (2,040 files). This is the client DisasterZone runs on today. |
| **[F-addon]** | Addons installed on the Forever client that ship a `_Camelot.toc` / `16001` TOC (Details, Questie, DialogueUI, EnhanceQoL). |
| **UNVERIFIED** | An undocumented C function with no call site in Blizzard's own Forever code, or a runtime behaviour the source cannot prove. |

The installed Forever client has no Blizzard Lua on disk (`Interface/` holds only `AddOns/`), so the Gethe branch is the source.

---

## Summary

1. **Forever is not a classic client. It is the retail "Midnight" engine (12.x) running Vanilla content.** The `forever` branch loads Garrison, Covenant, Housing, Delves, `Blizzard_CooldownViewer`, `Blizzard_DamageMeter`, `Blizzard_EncounterTimeline` and the retail `PlayerSpells` talent UI. Its project constant is `WOW_PROJECT_CAMELOT = 18` ([F-src] `Blizzard_ProjectConstants/Camelot/ProjectConstants.lua`), and addons ship it as `*_Camelot.toc`. Details' framework classes it as "AddonApocalypseWow" next to retail 12.x ([F-addon] `Details/Libs/DF/fw.lua:260`).
2. **TBC Anniversary 2.5.6 is already a modern-engine client**, so DisasterZone already calls `C_Item`, `C_Container`, `C_ChatInfo`, `C_Spell`, `C_UnitAuras`, `Settings`, `ScrollBox`, `MenuUtil`-style menus and `C_EditMode`. **All 77 `C_` functions DisasterZone calls exist on Forever** ([F-doc]). The classic "rename into a C_ namespace" work is largely done.
3. **The real deltas are three retail-only systems, not renames:**
   - **No combat log for addons.** `C_CombatLog.GetCurrentEventInfo` is gone from [F-doc]. It is present in [A-doc]. `CombatLogGetCurrentEventInfo` is only a CVar-gated alias to that missing function. The source says "relocated to the secure environment, for which no deprecation is (intentionally) provided" ([F-src] `Blizzard_DeprecatedCombatLog/Deprecated_CombatLog.lua`). **Meters, My Log, Raid log, boss mods, BossLearn, swing timers, combat text, Situation and StrategyLive all read the combat log, so all of them are dead on Forever.**
   - **Secret values.** In combat, encounters, M+, PvP and "restricted maps", unit, aura, cast, threat, health, power and chat payloads come back as *secret* values. Tainted code may pass them on to widgets but may not compare them or do arithmetic on them ([F-doc] `SecretWhen*`, `SecretReturns`, `SecretInChatMessagingLockdown` on `UnitHealth`, `UnitName`, `UnitGUID`, `C_UnitAuras.*`, `UnitCastingInfo`, `UnitDetailedThreatSituation`, `UNIT_AURA`, `UNIT_SPELLCAST_*`, `CHAT_MSG_*`). [A-doc] has none of these attributes.
   - **Addon chat lockdown.** `Enum.SendAddonMessageResult.AddOnMessageLockdown = 11` and `C_ChatInfo.InChatMessagingLockdown()` exist. `AddOnRestrictionType` has six values: Combat, Encounter, ChallengeMode, PvPMatch, Map, Chat ([F-doc] `RestrictedActionsConstantsDocumentation.lua`).
4. **Classic-only globals that are gone for `camelot`:** `UnitAura` / `UnitBuff` / `UnitDebuff`, the classic talent API (`GetTalentInfo`, `GetTalentTabInfo`, `GetNumTalentTabs`, `GetNumTalents`, `GetNumTalentGroups`), the classic spell API (`GetSpellInfo`, `GetSpellCooldown`, `GetSpellTexture`, `GetSpellLink`, `IsUsableSpell`, `IsSpellInRange`, `GetNumSpellTabs`, `GetSpellTabInfo`, `GetSpellBookItemName`), the classic trade skill and craft API, arena teams, the classic `LootFrame_*` functions and the classic `MainMenuBar*` and `MiniMap*` frames. Forever's talents are the retail Traits system (`C_ClassTalents`, `C_Traits`).
5. **DisasterZone is extremely defensive** (`if X then X() end`, `pcall`, `C_X.f or f`). Most removals therefore **degrade silently instead of throwing**: features go blank rather than erroring. The secret-value problem is the exception. Arithmetic or comparison on a secret value throws, and unit frames, nameplates, aggro, tanks, cast bars, Blessings range and threat do exactly that.
6. **The widget framework is portable as it is.** It is self-drawn (textures and fontstrings, its own menus, popups and tooltip skin), uses Blizzard templates sparingly, and uses no XML except `Bindings.xml`. None of the frame methods it calls is missing on Forever ([F-doc] ScriptObject docs: zero DisasterZone-used methods dropped).

---

## UI framework (part A)

### Load order and module pattern

- **TOC order:** `Core\BuildInfo`, then `Core\Boot` (the in-game patch loader; every file starts with `if DisasterZoneBoot and DisasterZoneBoot.Run("<path>", ...) then return end`, so a signed patch from `DisasterZonePatchDB` can replace a file's text via `loadstring`), then Libs, Core, Data, then `UI\Style`, `UI\Widgets`, `UI\Comp\*`, `UI\MainFrame`, then the pages.
- **Module pattern:** every file does `local addonName, ns = ...` and `local M = ns:NewModule("Name")`. The lifecycle runs `M:OnInit()` (ADDON_LOADED), then `M:OnLogin()` (PLAYER_LOGIN), both through `ns.SafeCall`.
- **Events:** `ns:RegisterEvent(evt, fn)` runs on one event frame, with `C_EventUtils.IsEventValid` plus `pcall` around `RegisterEvent`.
- **Internal message bus:** `ns:On("MSG", fn)` and `ns:Fire`.
- **Errors:** they go to a feedback sink and never to the screen (BugGrabber-aware, `Core/Init.lua`).

### Design tokens and primitives

- **`UI/Style.lua` (`ns.Style`, aliased `S`):** the single home of colours, type scale, spacing and the page size `PAGE_W x PAGE_H = 790 x 548`. The older `UI.*` and `EUI.*` colour tables are the same table objects.
- **`UI/Widgets.lua` (`ns.UI`, 4.5K lines):** the factory. It covers:
  - Text: `UI:Text`, `UI:SetTextStyle`, `FitText`, `TextWidth`.
  - Paint: `UI:Fill`, `Gradient`, `Rule`, `AddEdges` / `SetEdges` (1 px edges from textures instead of backdrops), `SoftShadow`, `PaintSleek`, `Glow`.
  - Motion: `Tween`, `DropIn`.
  - Windows: `UI:CreateWindow` (the window frame and head, close button, saved position via `SavePosition` / `RestorePosition`).
  - Controls: sleek buttons, icon buttons, edit boxes, search boxes, checkboxes, switches, sleek dropdown, multi dropdown, search dropdown, underline tabs, count badges and dots.
  - Lists: `UI:CreateScrollFrame`, and `UI:CreateScrollList`, which is the only Blizzard ScrollBox use: `WowScrollBoxList` + `CreateScrollBoxListLinearView` + `CreateDataProvider`.
  - Items: item buttons, item text, link and tooltip helpers (`UI:InsertLink` via `ChatFrameUtil.InsertLink`, falling back to `ChatEdit_InsertLink`).
  - Classes: class and role icons (`CLASS_ICON_TCOORDS`, `GetTexCoordsForRole`).
  - Models: the BiS model (`DressUpModel`, falling back to `PlayerModel`).
  - Nav: `UI:CreateNavStrip` (the main window's tab strip).
  - `SetBackdrop` appears only twice, and both calls are guarded (`if not f.SetBackdrop`, or `CreateFrame(..., "BackdropTemplate")`).
- **`UI/Comp/*` (the 1.4 refactor, "phase 2/3"):**
  - `Layouts.lua`: `UI:CreateLayout(kind, parent, opts)`. Five page skeletons own the toolbar (tabs left, filters, a "..." menu, ONE primary action right), margins and empty/notice slots:
    - `board`: toolbar, hero banner, grouped body and an optional side card (Home, Events, Polls, Groups).
    - `listdetail`: list column plus detail, with an optional nav column (Members, Raid log, Loot rules, Atlas).
    - `detail`: hero with back link, tabs, tool row and body (raid page, event page).
    - `rail`: side menu plus body (Settings, Notifications).
    - `tool`: a tool window banner plus body (planners, meter detail, drop panel).
  - `Surfaces.lua`: cards, row looks, empty states, notices.
  - `PageParts.lua`: page banners, back links, section headers.
  - `Controls.lua`: pills, chips, segments, side menu.
  - `Overlays.lua`: sheet, toast, HUD frame.
  - `Themes.lua`: the theme registry for meters and class bars.
  - `MapArt.lua`: zone art tiles from `C_Map.GetMapArtLayers` / `GetMapArtLayerTextures`.

### Shell

- **`UI/MainFrame.lua`:** the main window, 790 x 548 pages created lazily. Its parts:
  - Nav strip: text tabs with "beta" pills.
  - Icon pages on the right: Feedback, Changelog, Settings.
  - Sync status.
  - The launcher: LibDataBroker plus LibDBIcon minimap button; `UI/MinimapArc.lua` fans pinned pages out around it.
  - The page registry: `MainFrame:RegisterTab(key, label, order, createFn, isAvailableFn, opts)`.
  - Three group tabs (`NAV_GROUPS`): Raids, Gear and Guild. Each opens `UI/NavMenu.lua`, a "spotlight" flyout with page art, facts and jump-to views.
- **`UI/Menu.lua`:** every dropdown and context menu, drawn by the addon itself. It reproduces **MenuUtil's builder contract** (`root:CreateButton / CreateCheckbox / CreateRadio / CreateTitle / CreateDivider`, `MenuResponse.*`), so pages are written against the Blizzard API shape but rendered by DisasterZone. `UIDropDownMenu` is not used.
- **`UI/Popup.lua`:** its own confirm and prompt dialogs, using the same contract as `StaticPopupDialogs` (`Register`, `Show`, `OnAccept`, `hasEditBox`, ...).
- **`UI/Tooltip.lua`:** adds BiS and council lines to item tooltips via `HookScript("OnTooltipSetItem")`, guarded by `HasScript`. **`UI/TooltipSkin.lua`** reskins GameTooltip only when DisasterZone code called `SetOwner`, decided by the call site, through `hooksecurefunc(GameTooltip, "SetOwner")`.
- **`UI/Settings.lua` (5K lines):** the in-window Settings page, a rail layout. Groups (General, Alerts, Loot, Combat, Interface, Guild, Help) hold feature tiles, each tile opens a card page, and a search box covers every option. **The Blizzard Settings entry** uses `Settings.RegisterCanvasLayoutCategory` + `RegisterAddOnCategory` (line 707), with no `InterfaceOptions_AddCategory`.
- **`UI/EditMode.lua` (2.2K lines) + `Core/Layout.lua`:** `/dz edit` is DisasterZone's own edit-layout overlay. It moves DisasterZone frames AND Blizzard frames. Blizzard frames move through `C_EditMode.GetLayouts` / `SaveLayouts` / `SetActiveLayout`, `EditModeManagerFrame`, `EditModePresetLayoutManager`, `EditModeSettingDisplayInfoManager` and `Enum.EditModeSystem` (by name, not by number: good, because Forever renumbers `TotemActionBar` from 24 to 25 and adds `RaidWarning`, `MainActionBarEndCap`, `GroupFinder`, `LossOfControl`, `SwingTimer` and `GamepadMainActionBar`). Features declare `Layout:Register(id, def)`.
- **`UI/KeyBinds.lua`:** its own quick-keybind mode (`SetBinding`, `SaveBindings`, `GetBindingKey`, `C_ActionBar.PutActionInSlot`).
- **`UI/Tour.lua` + `UI/WelcomeTour.lua`:** a data-driven tutorial engine (`Data/Tours/*.lua`). It spotlights a control, dims the rest, and advances when the user acts.
- **Notifications** (`Notify`, `NotifySources`), **demo mode** (`DemoBar` / `List` / `Page`: fake data for screenshots and tours), **Share / ShareWindow**, **DatePicker**, **Picker**.
- **`Bindings.xml`:** the only XML. It holds seven bindings under header `DISASTERZONE`:
  - `CLICK DisasterZoneBlessNext:LeftButton`
  - `DisasterZone_ToggleEditLayout`
  - `DisasterZone_ToggleKeyBinds`
  - `DisasterZone_WardrobeNext`
  - `DisasterZone_PostLFG`
  - `DisasterZone_PostRecruit`
  - `DisasterZone_SituationNext`
  The `BINDING_*` globals are set in Lua.

### How a tab is built (the pattern)

1. Module `XUI` with `OnInit` calls `ns.MainFrame:RegisterTab("key", "Label", order, function(parent) return XUI:CreatePanel(parent) end, availableFn, { layout = "board" })`.
2. `CreatePanel(parent)` runs once (memoised). It creates `CreateFrame("Frame", nil, parent)`, calls `UI:CreateLayout(kind, p, opts)`, then fills `L.toolbar`, `L.banner`, `L.body` and `L.side` with Surfaces, Controls and ScrollLists.
3. Data arrives through the bus: `ns:On("RAIDPLAN_CHANGED", ...)` and similar call `RequestRefresh()`, which marks the panel dirty and refreshes on `OnShow` / `OnPanelShown`, or on a throttled `OnUpdate`. Example: `UI/Dashboard.lua:2149-2195`.
4. Slash shortcut: `ns:RegisterSlash("home", ...)`.

---

## Tab map

Tab orders come from `RegisterTab`. Groups come from `MainFrame.NAV_GROUPS`.

| Strip item | Pages (key, order) | Main UI files |
|---|---|---|
| **Home** | `home` 0.5 | `Dashboard.lua` (board: hello, banner with next raid, calendar, loot side card) |
| **Raids** (group 0.8) | `raids` 3.5, `council` 2, `lootrules` 3.51, `mylog` 3.52 | `RaidsTab`, `RaidPlanUI` (7K lines), `RaidSheet`, `RaidGroups`, `RaidLeadersUI`, `AttendanceUI`, `GuestBook`, `Reserves`, `SessionBar` / `SessionDrawer`, the Strategy set (`StrategyBoard`, `StrategyMap`, `StrategyMap3D`, `StrategyBlocks`, `StrategyReminder`, `StrategiesView`); `Council`, `CouncilRules`, `DropPanel` (4K, the loot drop window), `RollFrame`, `LootLog`, `PrizedUI`, `LootRulesUI`; `MyLogUI`, `MyLogDetail`, `MyLogKit`, `MyLogTimeline` |
| **Gear** (group 1) | `mybis` 1, `gearsim` 1.1, `consumables` 1.2, `wardrobe` 1.25, `atlas` 1.5 | `MyBiS` (one panel for three keys), `PaperDoll`, `GemEditor`, `KitView`, the Sim set (`SimPanel`, `SimStage`, `SimNerd`, `SimBuffs`, `SimHistory`), `Wardrobe`, `Atlas`, `AtlasNav`, `AtlasShop` |
| **Groups** | `dungeons` 3.55 | `DungeonsTab`, `GroupsCard`, `GroupsLead`, `GroupsMessage`, `GroupsSheet` |
| **Guild** (group 3.58) | `members` 3.6, `map` 3.61, `events` 3.57, `polls` 3.575, `recruit` 3.577, `audit` 3.578, `games` 3.8 | `Members`, `GuildMapUI`, `EventsTab` (6K), `EventBoard`, `EventBuilder` (7K), `EventPieces`, `EventWidgets`, `EventTracker`, `PollsTab`, `Recruit`, `AuditUI`, `AuditStory`, `Games/HubUI.lua` (+ the `Games/` folder) |
| icon pages | `feedback` 3.85, `changelog` 3.9, `settings` 4; hidden `notify` 3.95, `perf` 3.92 | `Feedback`, `FeedbackPlan`, `FeedbackSheet`, `Changelog`, `Settings`, `ProfilesUI`, `ImportExport`, `PatchUI`, `PerfUI`, `Notify` |
| tool windows | (not tabs) | `BlessingsUI`, `TotemsUI`, `PlannerWindow`, `SwingPracticeUI`, `MeterDetail`, `BossLearnUI`, `BossModSettings` |

---

## Look and HUD modules

**The Look system** (`UI/Look.lua`). Each part of the game UI gets one of these looks: `blizzard` (untouched, the default), `flat`, `halo`, `sigil`, `slate`, `gilded` or `classic` (DisasterZone frames in the game's art). Shared painters: `Look:Panel`, `Look:Bar`, `Look:Gilt`, `Look:Icon`. A part that was replaced needs a reload to hand frames back (`Look:NeedsReload`).

| Part | Method | Blizzard objects touched | Forever risk |
|---|---|---|---|
| **units / group** (`LookUnits`, `LookAggro`, `LookTanks`) | **Replaced** with its own `SecureUnitButtonTemplate` buttons and `SecureGroupHeaderTemplate` headers, built out of combat; it retires PlayerFrame, TargetFrame, FocusFrame, PetFrame, PartyFrame (pool) and the Compact* frames | `UnitHealth/Max`, `UnitPower`, `UnitName`, `UnitClass`, `C_UnitAuras.GetAuraDataByIndex` (falls back to `UnitAura`), `UnitDetailedThreatSituation`, `UnitGetIncomingHeals`, `UnitInRange` | **High.** In combat these return secrets, and the face code does math on them (hp fraction, threat %). Secure templates exist ([F-src]). |
| **cast** (`LookCast`) | **Replaced** (only draws); retires `PlayerCastingBarFrame` and the target/focus spell bars | `UnitCastingInfo` / `UnitChannelInfo`, `UNIT_SPELLCAST_*` | **High.** Secret when spellcast is restricted. Forever offers `UnitCastingDuration` + `StatusBar:SetTimerDuration` ([F-doc]). |
| **bags** (`LookBags`) | **Replaced** windows that host the game's `ContainerFrameItemButtonTemplate`; the bank uses `BankItemButtonGenericTemplate` | `C_Container.*`, `C_NewItems`, `C_Container.SortBags`, bank globals | **Medium.** `BankItemButtonGenericTemplate` is absent on Forever ([F-src]): Forever has the retail bank panel (`C_Bank`) and `ContainerFrameCombinedBags`. The `KeyRingButton` frame exists. |
| **bars** (`LookBars`, `LookDock`, `DockArt`) | **Reskinned**: the secure action buttons stay, with `hooksecurefunc(b, "Update" / "UpdateUsable" / "UpdateState")`; it hides the classic `MainMenuBarTexture0-3`, `EndCap`s and `MaxLevelBar`s; it replaces the XP/rep bar | `MainActionBar`, `MultiBar*`, `StanceBar`, `PetActionBar`, `BagsBar`, `MicroMenuContainer`, `StatusTrackingBarManager`, `GetWatchedFactionInfo`, spellbook globals | **Medium-low.** The modern bar frames exist. The classic art names are nil but iterated defensively. `GetWatchedFactionInfo` and the spellbook globals are gone (use `C_Reputation`, `C_SpellBook`). Forever has its own end caps (`MainActionBarEndCap` system). |
| **minimap** (`LookMinimap`, `MinimapArc`) | **Reskinned** | `Minimap`, `MinimapCluster`, `MinimapBackdrop`, `MinimapCompassTexture`, `GetMinimapShape` override, the HIDE list of the classic `MiniMap*` buttons | **Low.** The classic button names are nil (skipped). Forever has a Camelot minimap override ([F-src] `Blizzard_Minimap/Camelot/Minimap.lua`); re-check the child names in game. |
| **plates** (`Plates`, `PlateLooks`, `CombatTextPen`) | A DisasterZone frame drawn over every plate on `NAME_PLATE_UNIT_ADDED` | `C_NamePlate.GetNamePlateForUnit` / `GetNamePlates`, health, threat, auras, casts, `GetRaidTargetIndex`, CVars `nameplateShowEnemies` / `Friends` / `Motion` | **High** (secrets, as for units). |
| **combat text** (`CombatText`, `CombatTextLooks`) | Reads the combat log | `CombatLogGetCurrentEventInfo`, `floatingCombatText*_v2` CVars | **Dead** (no combat log). |
| **boss mods** (`BossModUI`, `BossModLooks`, `BossModSettings`, `BossLearnUI`) | Bars, warnings, countdown, range | CLEU, `CHAT_MSG_RAID_BOSS_EMOTE` / `MONSTER_YELL`, `C_Item.IsItemInRange` | **Dead or degraded.** No combat log; boss chat is secret in lockdown. Forever has `C_EncounterTimeline` / `EncounterWarnings` built in. |

**HUDs and meters:**

- **Meters** (`MeterWindow`, `MeterPanels` 2.6K, `MeterTheme`, `MeterDetail`): dockable panel stacks fed by `Core/Meter.lua` from CLEU, plus Threat. **Dead on Forever.** The replacement is `C_DamageMeter` (sessions, sources and spells for DamageDone, Dps, HealingDone, Hps, Absorbs, Interrupts, ...; `SecretWhenInCombat`) [F-doc]. Details does this on Forever in `core/parser_nocleu*.lua` [F-addon].
- **Class tools:**
  - `SwingTimerHUD`, `WarriorSwingHUD` and `ShotTimerHUD` share `ns.SwingRing` and `RingFace`. They are driven by `Core/SwingTimer.lua`, `WarriorSwing.lua` and `ShotTimer.lua` (CLEU, `UnitAttackSpeed`, and `UnitBuff` / `UnitDebuff` / `GetSpellCooldown` / `IsUsableSpell` / `IsCurrentSpell`). **Forever ships its own `Blizzard_SwingTimer`** (an Edit Mode system) [F-src].
  - `ResourceBar` / `ResourceFace`: `UnitPower` is secret when restricted. `UnitPowerPercent` exists.
  - `ClassBar`, `BlessingsBar`, `TotemBar` and `BarFace` are secure buttons, using `IsSpellInRange`, `GetSpellCooldown`, `GetTotemInfo` and `OffhandHasWeapon`.

---

## API surface table

Counts:

| What | Count |
|---|---|
| Distinct `_G` reads in non-Lib addon code (bytecode `GETGLOBAL`) | 462 |
| Explicit `_G.X` reads | 71 |
| Blizzard frame names in Look strings | 89 |
| `C_` functions | 77 |
| Events | 180 |
| CVars | 14 |
| Frame types | 9 |
| Templates | 9 |

`used in` gives the main files. "F-calls" means Blizzard's own loaded Forever code calls the function, which proves it exists.

### A. C_ namespaces (all 77 present on Forever)

| api | used in | Forever status | replacement | verified? |
|---|---|---|---|---|
| `C_Timer.After/NewTicker/NewTimer` (154 calls) | everywhere | same | - | VERIFIED [F-doc] |
| `C_Item.GetItemInfo/GetItemInfoInstant/GetItemIconByID/IsItemDataCachedByID/GetItemCount/RequestLoadItemDataByID/GetItemQualityByID/GetItemNameByID/IsEquippableItem/GetItemQualityColor/IsItemInRange` | ItemDB, MyBiS, Atlas, LookBags, BossModUI | same | - | VERIFIED [F-doc] |
| `C_Container.GetContainerItemInfo/NumSlots/ItemLink/ItemCooldown/NumFreeSlots/UseContainerItem/ContainerIDToInventoryID/SortBags` | LookBags, Wardrobe, Loot, SimPanel | same (`SortBags` is new vs anniversary) | - | VERIFIED [F-doc] |
| `C_ChatInfo.SendAddonMessage` / `RegisterAddonMessagePrefix` | Comm (via AceComm/CTL) | **behaviour change**: `SecretArguments=NotAllowed`; new result `AddOnMessageLockdown (11)`; `InChatMessagingLockdown()` | queue and retry after lockdown; check the result enum | VERIFIED [F-doc] |
| `C_ChatInfo.SendChatMessage` / `PerformEmote` | Recruit, GroupsLFG, Loot announce | same (`HasRestrictions` in both) | - | VERIFIED [F-doc] |
| `C_UnitAuras.GetAuraDataByIndex` | LookUnits, LookAggro | **behaviour change**: `SecretWhenUnitAuraRestricted` | `C_UnitAuras.GetUnitAuras`, `GetAuraDuration`; show without math | VERIFIED [F-doc] |
| `C_Spell.GetSpellName/GetSpellTexture/GetSpellLink/RequestLoadSpellData` | ShoppingList, Atlas, Sim | same | - | VERIFIED [F-doc] |
| `C_NamePlate.GetNamePlates/GetNamePlateForUnit` | Plates, CombatText | same API (payload secrets apply) | - | VERIFIED [F-doc] |
| `C_PartyInfo.GetLootMethod/InviteUnit/UninviteUnit/LeaveParty/DoCountdown` | Loot, Recruit, GroupFinder, BossMod | same | - | VERIFIED [F-doc] |
| `C_GuildInfo.GuildRoster/IsGuildOfficer` | Guild | same | - | VERIFIED [F-doc] |
| `C_EditMode.GetLayouts/SaveLayouts/SetActiveLayout` | Layout, EditMode | same; `Enum.EditModeSystem` renumbered after 23 | use names (already done) | VERIFIED [F-doc] |
| `C_Map.*` (13 functions), `C_MapExplorationInfo.GetExploredMapTextures` | GuildMap, StrategyMap, MapArt, EventSensors | same | - | VERIFIED [F-doc] |
| `C_CVar.GetCVar/SetCVar` | Plates, CombatText, EventSensors | same (`SetCVar`: `RequiresValidAndPublicCVar`) | - | VERIFIED [F-doc] |
| `C_AddOns.*`, `C_EventUtils.IsEventValid`, `C_SpecializationInfo.GetSpecializationInfo`, `C_LFGList.*`, `C_LFGInfo.*`, `C_GossipInfo.GetAvailableQuests`, `C_QuestLog.IsOnQuest`, `C_CurrencyInfo.*`, `C_NewItems.*`, `C_ActionBar.PutActionInSlot`, `C_UIFileAsset.IsKnownFile`, `C_FriendList`, `C_UIWidgetManager`, `C_AddOnProfiler` | various | same | - | VERIFIED [F-doc] |

### B. Globals: removed, renamed or changed on Forever

| api | used in | Forever status | replacement | verified? |
|---|---|---|---|---|
| `CombatLogGetCurrentEventInfo` + event `COMBAT_LOG_EVENT_UNFILTERED` | Core/CombatLog (shared reader: Meter, MyLog, RaidLog, BossMod, BossLearn, SwingTimer, WarriorSwing, ShotTimer, CombatText, Situation), StrategyLive:875, EventSensors | **removed for addons**: `C_CombatLog.GetCurrentEventInfo` is not in [F-doc] (it is in [A-doc]); the alias points at nil; CLEU is `HasRestrictions` / `CallbackEvent` | `C_DamageMeter` (meters), `UNIT_SPELLCAST_*` for own casts, `Blizzard_SwingTimer`, `C_EncounterTimeline`, `ENCOUNTER_START/END` | VERIFIED [F-doc][F-src]; runtime register behaviour UNVERIFIED (DisasterZone's `pcall` swallows either outcome) |
| `UnitAura`, `UnitBuff`, `UnitDebuff` | LookUnits:113 (fallback), LookAggro, WarriorSwing, ShotTimer | **removed** (aliases exist only in `Blizzard_Deprecated/Classic/*`, not loaded for camelot) | `C_UnitAuras.GetAuraDataByIndex` / `GetBuffDataByIndex` / `GetDebuffDataByIndex` / `GetPlayerAuraBySpellID` | VERIFIED [F-src] |
| `GetTalentInfo`, `GetTalentTabInfo`, `GetNumTalentTabs`, `GetNumTalents`, `GetNumTalentGroups` | Sim/Runner, WarriorSwing, Professions, MyLog | **removed** (`Blizzard_DeprecatedSpecialization` has `AllowLoadGameType: classic, standard`, not camelot); talents are retail Traits | `C_ClassTalents.GetActiveConfigID` + `C_Traits.GetConfigInfo/GetTreeNodes/GetNodeInfo`; `C_SpecializationInfo.GetTalentInfo` | VERIFIED [F-src] |
| `GetSpellInfo` | TotemBar, SwingTimerHUD, SimNerd (all guarded) | **removed** (0 calls in loaded Forever code vs 9 in anniversary; not in docs) | `C_Spell.GetSpellInfo` (returns a table) / `C_Spell.GetSpellName` | VERIFIED-absent [F-src]; matches retail 11.0 removal |
| `GetSpellCooldown`, `GetSpellTexture`, `GetSpellLink`, `IsUsableSpell`, `IsSpellInRange`, `GetSpellPowerCost`, `GetSpellSubtext`, `IsCurrentSpell`, `IsAutoRepeatSpell`, `PickupSpell` | TotemBar, SwingTimer, WarriorSwing, ShotTimer, BlessingsBar, Resource, LookBars, StrategyMap, Atlas | **removed** | `C_Spell.GetSpellCooldown` (`SecretWhenCooldownsRestricted`), `GetSpellTexture`, `GetSpellLink`, `IsSpellUsable`, `IsSpellInRange`, `GetSpellPowerCost`, `GetSpellSubtext`, `IsCurrentSpell`, `IsAutoRepeatSpell`, `PickupSpell` | VERIFIED replacements [F-doc]; globals absent [F-src] |
| `GetNumSpellTabs`, `GetSpellTabInfo`, `GetSpellBookItemName`, `BOOKTYPE_SPELL` | LookBars:962 | **removed** | `C_SpellBook.GetNumSpellBookSkillLines`, `GetSpellBookSkillLineInfo`, `GetSpellBookItemName`, `Enum.SpellBookSpellBank` | VERIFIED [F-doc] |
| `IsSpellKnown`, `IsPlayerSpell` | class tools | CVar-gated deprecated alias only | `C_SpellBook.IsSpellKnown` / `IsSpellInSpellBook` | VERIFIED [F-src] |
| `GetItemInfo`, `GetItemInfoInstant`, `GetItemIcon`, `GetItemCount`, `IsEquippableItem`, `IsItemInRange`, `GetItemGem` | fallbacks in Wardrobe, LookBags, MyBiS, StrategyMap, Widgets, Sim | **removed** (anniversary had CVar aliases; Forever has none) | `C_Item.*` (already the first choice almost everywhere); `C_Item.GetItemGem` | VERIFIED [F-src] |
| `GetContainerItemInfo` (multi-return), `GetContainerNumSlots`, `UseContainerItem`, `ContainerIDToInventoryID` | fallbacks | removed (already handled) | `C_Container.*` | VERIFIED [F-doc] |
| `GetCoinTextureString`, `GetZonePVPInfo` | LookBags, LookMinimap | removed | `C_CurrencyInfo.GetCoinTextureString`, `C_PvP.GetZonePVPInfo` | VERIFIED [F-doc] |
| `GetInventorySlotInfo` | Wardrobe | CVar-gated alias only | `C_PaperDollInfo.GetInventorySlotInfo` | VERIFIED [F-src] |
| `GetFactionInfoByID`, `GetWatchedFactionInfo` | MyBiS, Atlas, LookBars | removed | `C_Reputation.GetFactionDataByID`, `GetWatchedFactionData` | VERIFIED [F-doc]; globals UNVERIFIED-absent |
| `GetTradeSkillLine/Info/ItemLink/RecipeLink`, `GetNumTradeSkills`, `IsTradeSkillLinked`, `GetCraftInfo/DisplaySkillLine/ItemLink/RecipeLink`, `GetNumCrafts`, `GetSkillLineInfo`, `GetNumSkillLines`, `ExpandSkillHeader`, event `TRADE_SKILL_UPDATE`, `CRAFT_SHOW/UPDATE` | Core/Professions (all guarded) | **removed**: Forever uses retail `Blizzard_Professions` | `C_TradeSkillUI.GetBaseProfessionInfo/GetRecipeInfo/...`, `GetProfessions()` + `GetProfessionInfo` | VERIFIED-absent [F-src]; replacement set partly UNVERIFIED (`C_TradeSkillUI.GetAllRecipeIDs` not in [F-doc]) |
| `GetArenaTeam*`, `ArenaTeamRoster`, `ArenaTeamInviteByName`, `GetNumArenaTeamMembers`, `ARENA_TEAM_*` events | Core/GroupPvP | **removed** (no arena teams in Vanilla content) | drop the feature | VERIFIED [F-src] |
| `LootFrame_UpdateButton`, `LootFrame_Show`, `LootButton_OnClick`, `LOOTFRAME_NUMBUTTONS` | DropPanel:4040, Loot:1278 | **removed**: Forever's `LootFrame` is the retail ScrollBox frame | `LootFrame.ScrollBox` enumerate frames / `LOOT_READY`; for the master loot click, `MasterLooterFrame` (exists) | VERIFIED [F-src]; DisasterZone already falls back to an `OnShow` repaint |
| `GetLootSourceInfo`, `GetLootRollItemLink`, `GetMasterLootCandidate`, `GiveMasterLoot`, `GetLootSlotInfo/Link/Type`, `GetNumLootItems`, `GetLootThreshold`, `IsFishingLoot` | Loot | same (F-calls present for all except `GetLootSourceInfo`) | - | VERIFIED [F-src]; `GetLootSourceInfo` UNVERIFIED |
| `GetGuildRosterInfo`, `GetGuildRosterLastOnline`, `GuildRosterSetOfficerNote`, `CanEditOfficerNote` | Guild, Recruit, OfficerNotes | no call site in Forever Blizzard code (the retail roster is Communities) | `C_GuildInfo.CanEditOfficerNote`, `C_GuildInfo.SetNote(guid, note, isPublic)` | UNVERIFIED (`GetGuildRosterInfo` is used by EnhanceQoL on Forever [F-addon]: likely present) |
| `GetQuestGreenRange`, `GetQuestResetTime`, `GetNumQuestWatches`, `QuestWatchFrame` / `WatchFrame` | Plates:77, DungeonRuns, EventTracker | removed or moved | `UnitQuestTrivialLevelRange`, `C_DateAndTime.GetSecondsUntilDailyReset`, `C_QuestLog.GetNumQuestWatches`, `ObjectiveTrackerFrame` | `C_*` VERIFIED [F-doc]; `QuestWatchFrame` absent VERIFIED [F-src] |
| `GetMouseFocus` | EventSensors:231 (second choice) | removed | `GetMouseFoci` (already the first choice) | VERIFIED [F-src] |
| `ChatEdit_InsertLink`, `ChatFrame_OpenChat`, `ChatFrame_AddMessageEventFilter`, `ChatFrame_SendTell`, `SendChatMessage`, `DoEmote`, `GuildInvite`, `UninviteUnit`, `RaidNotice_AddMessage`, `IsEncounterInProgress`, `HasAction`, `IsActionInRange`, `IsUsableAction`, `GetActionBarPage`, `GetBonusBarOffset`, `GetWeaponEnchantInfo` | many (mostly second choices) | **CVar-gated deprecated aliases only** (`loadDeprecationFallbacks`) | `ChatFrameUtil.*`, `C_ChatInfo.*`, `C_GuildInfo.Invite`, `C_PartyInfo.UninviteUnit`, `C_InstanceEncounter.IsEncounterInProgress`, `C_ActionBar.*`, `RaidWarningFrame` | VERIFIED [F-src] |
| `hooksecurefunc("InviteUnit" / "LeaveParty" / "UninviteUnit")` | Roster hooks | hooking a missing global errors unless guarded | hook `C_PartyInfo` (already done too) | VERIFIED that the globals are absent or alias-only |
| `OnTooltipSetItem` script | Tooltip:787 (guarded by `HasScript`) | **likely removed**: Forever's Blizzard code never uses it; `TooltipDataProcessor` is loaded | `TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, fn)` | `TooltipDataProcessor` VERIFIED [F-src]; script removal UNVERIFIED. Note: `classic_anniversary` now also loads `TooltipDataHandler.lua`, contradicting `dev/docs/research/api.md` section 7 |
| Frames: `MainMenuBarTexture0-3`, `MainMenuBarLeft/RightEndCap`, `MainMenuMaxLevelBar0-3`, `MainMenuBarArtFrame`, `MicroButtonPortrait`, `SocialsMicroButton`, `LFGMicroButton`, `PVPMicroButton`, `WorldMapMicroButton`, `MinimapBorder`, `MinimapZoomIn/Out`, `MinimapNorthTag`, `MinimapToggleButton`, `MinimapZoneTextButton`, `MiniMapTracking`, `MiniMapMailFrame`, `MiniMapWorldMapButton`, `MiniMapBattlefieldFrame`, `LFGMinimapFrame`, `PartyMemberFrame1-4`, `WorldFrame` (as named XML), `ShowLFGParentFrame` / `ToggleLFGParentFrame` | LookBars, LookMinimap, LookUnits, KeyBinds | **absent** (retail equivalents: `PlayerSpellsMicroButton`, `LFDMicroButton`, `PVEFrame`, `PartyFrame.MemberFrameN`) | name lists per flavour | VERIFIED [F-src] (`WorldFrame` is a C-created global, so its absence from XML is not real: UNVERIFIED) |
| Template `BankItemButtonGenericTemplate` | LookBags:325 | absent (retail bank panel) | `C_Bank` + `BankPanel` item buttons | VERIFIED [F-src] |
| `SetPortraitToTexture`, `GetMinimapShape` (a convention, not an API), `OffhandHasWeapon`, `GetMacroSpell`, `GetMacroIndexByName`, `LoadSavedVariablesFirst` TOC directive, `loadstring` (Boot) | SimStage, MeterTheme, LookMinimap, TotemBar, KeyBinds, Boot | unknown | - | UNVERIFIED |

### C. Globals that stay the same (proved by [F-doc] or by Forever Blizzard call sites)

These are present, and those flagged in section D carry secret-return rules.

- **Unit API:** `UnitName`, `UnitNameUnmodified`, `UnitFullName`, `UnitGUID`, `UnitClass`, `UnitClassBase`, `UnitRace`, `UnitSex`, `UnitLevel`, `UnitExists`, `UnitIsUnit`, `UnitIsPlayer`, `UnitIsDead` / `Ghost` / `DeadOrGhost` / `FeignDeath`, `UnitIsConnected`, `UnitIsAFK` / `DND`, `UnitIsGroupLeader` / `Assistant`, `UnitInParty` / `Raid` / `Range`, `UnitIsVisible`, `UnitIsFriend`, `UnitCanAttack`, `UnitReaction`, `UnitFactionGroup`, `UnitCreatureType`, `UnitClassification`, `UnitIsTapDenied`, `UnitPlayerControlled`, `UnitAffectingCombat`, `UnitHealth` / `Max`, `UnitPower` / `Max` / `Type`, `UnitGetIncomingHeals`, `UnitCastingInfo` / `ChannelInfo`, `UnitThreatSituation`, `UnitDetailedThreatSituation`, `UnitGroupRolesAssigned`, `UnitAttackSpeed`, `UnitRangedDamage`, `UnitXP` / `Max`, `UnitPosition`, `UnitDistanceSquared`, `GetUnitSpeed`, `GetComboPoints`.
- **Group and guild:** `IsInGroup`, `IsInRaid`, `IsInGuild`, `GetNumGroupMembers`, `GetNumSubgroupMembers`, `GetRaidRosterInfo`, `SetRaidSubgroup`, `SwapRaidSubgroup`, `GetPartyAssignment`, `GetRaidTargetIndex`, `SetRaidTarget`, `AcceptGroup`, `DeclineGroup`, `GetGuildInfo`, `GetNumGuildMembers`, `CanGuildInvite`, `RequestRaidInfo`, `GetNumSavedInstances`, `GetSavedInstanceInfo`, `GetInstanceInfo`, `ConvertToRaid` (the Forever call site is a Classic XML; `C_PartyInfo.ConvertToRaid` exists).
- **Inventory and merchant:** `GetInventoryItemID` / `Link` / `Texture` / `Quality`, `IsInventoryItemLocked`, `PickupInventoryItem`, `PickupBagFromSlot`, `PutItemInBag`, `GetMerchant*`, `GetRepairAllCost`, `RepairAllItems`, `CanMerchantRepair`, `GetTradePlayerItemInfo` / `Link`, `ClickTradeButton`, `GetMoney`.
- **Bindings, actions and macros:** `GetBinding*`, `SetBinding`, `SaveBindings`, `LoadBindings`, `GetCurrentBindingSet`, `GetActionInfo`, `PickupAction`, `PlaceAction`, `GetPetActionInfo`, `GetShapeshiftForm` / `FormID` / `FormInfo`, `GetMacroInfo`, `GetTotemInfo`.
- **Misc:** `GetTime`, `GetServerTime`, `GetGameTime`, `GetBuildInfo`, `GetLocale`, `GetRealmName`, `GetNormalizedRealmName`, `Ambiguate`, `GetPlayerInfoByGUID`, `GetChannelName` / `List`, `GetCursorInfo` / `Position`, `ClearCursor`, `CursorHasItem`, `ResetCursor`, `SetCursor`, `GetFramerate`, `GetNetStats`, `InCombatLockdown`, `IsModifiedClick`, the modifier-key functions, `IsMounted` / `Flying` / `Swimming` / `Indoors`, `IsXPUserDisabled`, `GetXPExhaustion`, `GetZoneText` / `RealZoneText` / `SubZoneText` / `MinimapZoneText`, `PlaySound` + `SOUNDKIT`, `ReloadUI`, `CreateFrame`, `CreateColor`, `CreateVector2D`, `CreateDataProvider`, `CreateScrollBoxListLinearView`, `ScrollBoxConstants`, `EventRegistry`, `Menu` / `MenuInputContext` / `MenuResponse`, `LinkUtil`, `ChatFrameUtil`, `StaticPopup_*`, `UISpecialFrames`, `RegisterUnitWatch` / `RegisterAttributeDriver`, `SetPortraitTexture`, `SetPortraitTextureFromCreatureDisplayID`, `SetItemButton*`, `CooldownFrame_Set`, `ActionButton_UpdateRangeIndicator`, `MultiActionBar_Update`, `HandleModifiedItemClick`, `DressUpItemLink`, `GameTooltip_SetDefaultAnchor`, `KeybindFrames_InQuickKeybindMode`, `RAID_CLASS_COLORS`, `CLASS_ICON_TCOORDS`, `ITEM_QUALITY_COLORS`, `FACTION_BAR_COLORS`, `LOCALIZED_CLASS_NAMES_MALE`.
- **Frames that still exist:** `UIParent`, `GameTooltip`, `ItemRefTooltip`, `ShoppingTooltip1/2`, `MainActionBar`, `MultiBarBottomLeft` / `Right` / `Left` / `Right`, `MultiBar5-7`, `StanceBar`, `PetActionBar`, `BagsBar`, `MicroMenu(Container)`, `MainMenuBarBackpackButton`, `CharacterBag0-3Slot`, `KeyRingButton`, `StatusTrackingBarManager` + `Main` / `SecondaryStatusTrackingBarContainer`, `PlayerFrame`, `TargetFrame`, `FocusFrame`, `PetFrame`, `PartyFrame`, `CompactPartyFrame`, `CompactRaidFrameManager` / `Container`, `PlayerCastingBarFrame`, `Minimap`, `MinimapCluster`, `MinimapBackdrop`, `MinimapCompassTexture`, `GameTimeFrame`, `TimeManagerClockButton`, `LootFrame`, `MasterLooterFrame`, `GroupLootFrame1`, `BankFrame`, `MerchantFrame`, `WorldMapFrame`, `EditModeManagerFrame`, `SettingsPanel`, `GameMenuFrame`, `AddonList`, `LFGParentFrame`, `RaidWarningFrame`, `UIErrorsFrame`, `DropDownList1`, `QuickKeybindFrame`, `ObjectiveTrackerFrame`. All VERIFIED [F-src].
- **Templates:** `GameTooltipTemplate`, `SecureUnitButtonTemplate`, `SecureActionButtonTemplate`, `SecureGroupHeaderTemplate` (+ Party / Raid), `SecureHandlerStateTemplate`, `CooldownFrameTemplate`, `BackdropTemplate`, `ContainerFrameItemButtonTemplate`, `ModelSceneActorTemplate`, `WowScrollBoxList`. All VERIFIED [F-src].
- **Settings API:** `Settings.RegisterCanvasLayoutCategory`, `RegisterAddOnCategory` (VERIFIED, `Blizzard_Settings` loaded). `InterfaceOptions_AddCategory` is not used.
- **Frame methods:** none of the frame methods DisasterZone calls is in [A-doc] but missing from [F-doc] (1,085 vs 1,193 documented ScriptObject methods). VERIFIED.

### D. Secret-value surface that DisasterZone touches (Forever only, [F-doc])

| api | Forever attribute |
|---|---|
| `UnitHealth`, `UnitGetIncomingHeals`, `UnitInRange`, `GetRaidTargetIndex` | `SecretReturns` |
| `UnitHealthMax` | `SecretWhenUnitHealthMaxRestricted` |
| `UnitPower`, `GetComboPoints` / `UnitPowerMax` | `SecretWhenUnitPowerRestricted` / `...PowerMaxRestricted` |
| `UnitName` | `SecretWhenUnitNameIdentityRestricted` |
| `UnitGUID`, `UnitClass`, `UnitRace`, `UnitSex`, `UnitFullName`, `UnitInRaid`, `UnitIsGroupLeader` / `Assistant`, `UnitGroupRolesAssigned`, `UnitCreatureType` | `SecretWhenUnitIdentityRestricted` |
| `UnitIsUnit` | `SecretWhenUnitComparisonRestricted` |
| `UnitCastingInfo` / `ChannelInfo`, `UNIT_SPELLCAST_*` | `SecretWhenUnitSpellCastRestricted` |
| `UnitThreatSituation` / `UnitDetailedThreatSituation` | `SecretWhenUnitThreatStateRestricted` / `...ThreatValuesRestricted` |
| `UnitAttackSpeed`, `UnitRangedDamage`, `GetUnitSpeed` | `SecretWhenUnitStatsRestricted` |
| `C_UnitAuras.*`, `UNIT_AURA` | `SecretWhenUnitAuraRestricted` / `SecretWhenAurasRestricted` |
| `C_Spell.GetSpellCooldown` | `SecretWhenCooldownsRestricted` |
| `GetTotemInfo` | `SecretWhenTotemSlotSecret` |
| `UnitIsAFK` / `DND`, `READY_CHECK`, `START/CANCEL_PLAYER_COUNTDOWN`, all `CHAT_MSG_*` that DisasterZone listens to (not `CHAT_MSG_LOOT`, not `CHAT_MSG_ADDON`) | `SecretInChatMessagingLockdown` |
| `PARTY_KILL`, `UNIT_DIED` | `SecretWhenUnitIdentityRestricted` |
| `C_DamageMeter.GetCombatSessionFromType` | `SecretWhenInCombat` |

Helpers on Forever: `issecretvalue`, `canaccessvalue`, `issecrettable`, `scrubsecretvalues`, `secretwrap` ([F-doc] `FrameScriptDocumentation.lua`), plus `UnitHealthPercent`, `UnitPowerPercent` (curve-based), `UnitCastingDuration`, `C_UnitAuras.GetAuraDuration` and `StatusBar:SetTimerDuration`, which display secrets without doing math on them. **The exact conditions under which each predicate is active (open world combat vs instance only) are UNVERIFIED.** The enum says "Combat: the player is actively affecting combat", which suggests any combat.

### E. Events and CVars

- **Events:** 173 of the 180 events DisasterZone uses exist in both clients.
  - **Gone:** `ARENA_TEAM_ROSTER_UPDATE`, `ARENA_TEAM_UPDATE`, `CRAFT_SHOW`, `CRAFT_UPDATE`, `TRADE_SKILL_UPDATE`, `PLAYERBANKBAGSLOTS_CHANGED` (VERIFIED [F-doc]).
  - `LEARNED_SPELL_IN_TAB` is in neither doc set (UNVERIFIED).
  - `COMBAT_LOG_EVENT_UNFILTERED` is listed but unusable.
  - Restricted payloads: see section D.
- **CVars:** all exist in Forever Blizzard code, except the following, which are UNVERIFIED (they are not referenced by name in either branch's Lua, which is also true on anniversary): `SpellQueueWindow`, `nameplateShowFriends`, `nameplateMotion`, `floatingCombatTextPetMeleeDamage_v2` / `PetSpellDamage_v2`. The verified ones: `rotateMinimap`, `nameplateShowEnemies`, `timeMgrUseLocalTime`, `ActionButtonUseKeyDown`, `floatingCombatTextCombatDamage_v2` / `CombatLogPeriodicSpells_v2` / `CombatHealing_v2`, `enableFloatingCombatText`, `loadDeprecationFallbacks`.
- **TOC:** `## Interface: 16001`, or a `DisasterZone_Camelot.toc`, or a comma list. Per-file `[AllowLoadGameType camelot]` works, and `WOW_PROJECT_ID == WOW_PROJECT_CAMELOT (18)`. DialogueUI uses `## X-GameType: Camelot [AllowLoadGameType camelot]` [F-addon].

---

## Forever deltas

### What breaks, by module

| Severity | Modules | Why |
|---|---|---|
| **Dead (feature gone, needs a redesign)** | Meters (`Core/Meter`, `MeterPanels`, `MeterDetail`, `MeterTheme`), My Log (`Core/MyLog`, `MyLogUI*`), Raid log combat parts (`Core/RaidLog`), Boss mods and BossLearn (`Core/BossMod`, `BossLearn`, `BossModUI`), combat text (`Core/CombatText`, `CombatText*`), swing / shot / warrior timers (`Core/SwingTimer`, `ShotTimer`, `WarriorSwing` + HUDs, `SwingPracticeUI`), `Core/Situation`, `Core/StrategyLive` (live strategy cues), `Core/EventSensors` combat sensors, death recaps | No combat log. `RegisterEvent` is `pcall`ed, so they likely just never fire. If CLEU does register, `CombatLogGetCurrentEventInfo` is nil and `Core/CombatLog.lua:52` and `StrategyLive.lua:875` throw on every event. |
| **Throws in combat (secret values)** | `LookUnits`, `LookAggro`, `LookTanks`, `Plates` / `PlateLooks`, `LookCast`, `ResourceBar`, `BlessingsBar` / `TotemBar` range and cooldown cells, `Core/Threat`, unit-name comparisons in roster code during lockdown, chat parsers (`CHAT_MSG_*` in Recruit, GroupsLFG, Loot `CHAT_MSG_LOOT` is safe) | Arithmetic or comparison on secret returns. |
| **Silently empty (guarded removals)** | Professions scan (trade skill/craft), arena PvP card, talents in Sim / WarriorSwing / MyLog, spellbook scan in LookBars, item-gem read in Sim, quest-watch tracker anchor, LootFrame per-button decoration, the bank window template, tooltip lines (if `OnTooltipSetItem` is gone), reputation in MyBiS / Atlas / LookBars | `if X then` guards hide the failure. |
| **Comms degraded** | `Core/Comm`, `Outbox`, `DigestSync`, `Bridge` and everything synced | `AddOnMessageLockdown` during encounters / restricted states; payload arguments must not be secret. Needs a "hold until unlocked" outbox. ChatThrottleLib must know result 11 (the CTL in Forever's Questie already checks `issecretvalue` [F-addon]). |
| **Works as is** | MainFrame, NavMenu, Menu, Popup, Widgets, Style, Comp/*, Settings, EditMode (C_EditMode and Enum by name), KeyBinds, Tour, Dashboard and most pages (Raids planning, Council UI, Events, Polls, Members, Recruit, Atlas, MyBiS UI, Games, Changelog, Feedback), LookBars / LookDock / LookMinimap with blank classic-name lists | Self-drawn UI on APIs that exist. **Data content** (TBC raids and items vs Vanilla) is out of my scope. |

### Compat-shim strategy

Use one `Core/Compat.lua`, loaded right after `Boot` and the libs. It exposes `ns.API`, and no file calls a WoW global directly for anything in sections B and D.

1. **Flavour flags:** `ns.IS_FOREVER = WOW_PROJECT_ID == WOW_PROJECT_CAMELOT`, `ns.IS_TBC = WOW_PROJECT_ID == WOW_PROJECT_BURNING_CRUSADE_CLASSIC`, and `ns.HAS_CLEU = C_CombatLog and C_CombatLog.GetCurrentEventInfo ~= nil`. Gate whole features on capabilities, not flavour: `Meter` uses `ns.HAS_CLEU or C_DamageMeter`, the timers use `ns.HAS_CLEU`.
2. **Flat wrappers that return one shape:**
   - `API.SpellName(id)`, `API.SpellIcon(id)`, `API.SpellCooldown(id)` (start, duration, using `C_Spell` tables), `API.SpellUsable`, `API.SpellInRange`.
   - `API.Aura(unit, i, filter)` (the shape `LookUnits` already uses), `API.PlayerBuff(spellId|name)`.
   - `API.Talents()`, which returns `{ [talentKey] = rank }` from `GetTalentInfo` on TBC or `C_Traits` on Forever.
   - `API.Professions()`: the TBC skill lines and trade skill window on TBC, `GetProfessions` / `C_TradeSkillUI` on Forever.
   - `API.WatchedFaction()`, `API.FactionStanding(id)`, `API.CoinText(c)`, `API.QuestResetSeconds()`, `API.NumQuestWatches()`, `API.InventorySlotInfo(name)`.
   - `API.HookItemTooltip(fn)`: `TooltipDataProcessor.AddTooltipPostCall` when present, else `HookScript("OnTooltipSetItem")`.
   - `API.HookLootButtons(fn)`: the classic `LootFrame_UpdateButton` on TBC, `LootFrame.ScrollBox:ForEachFrame` after `LOOT_READY` on Forever.
3. **Secret-safe reads:** `API.Safe(v)` returns `nil` when `issecretvalue and issecretvalue(v)`. `API.HealthFrac(unit)` uses `UnitHealthPercent` on Forever. Faces get a "secret mode" that passes raw values to `StatusBar:SetValue` / `SetMinMaxValues`, uses `UnitCastingDuration` + `SetTimerDuration` for cast bars, and skips threat math. Register `ADDON_RESTRICTION_STATE_CHANGED` and expose `ns.Restricted()`, so expensive or unsafe paths (aggro glow, plate colouring by threat, death recap) pause during restrictions.
4. **Comms:** wrap `C_ChatInfo.SendAddonMessage` in `API.SendAddon(prefix, msg, chan, target)`. It checks `C_ChatInfo.InChatMessagingLockdown()` first, and on result `AddOnMessageLockdown` it queues into the existing Outbox and flushes on `ADDON_RESTRICTION_STATE_CHANGED` with Chat or Encounter inactive.
5. **Frame name tables per flavour:** move the HIDE / retire lists in `LookBars`, `LookMinimap`, `LookUnits` and `KeyBinds` into `Compat.FRAMES[flavour]`. Forever uses the retail names: `PartyFrame.MemberFrameN`, `PlayerSpellsMicroButton`, `LFDMicroButton`, `ObjectiveTrackerFrame`, the bank via `BankPanel`.
6. **Feature replacements on Forever (not shims):**
   - Meters: read `C_DamageMeter` sessions (Details' `parser_nocleu1.lua` is a working reference on this exact client).
   - Swing timer: defer to `Blizzard_SwingTimer` (an Edit Mode system); the existing ForeverMacros addon already toggles it.
   - Boss mods: `C_EncounterTimeline` / `EncounterWarnings` plus `ENCOUNTER_START` / `END`.
   - My Log: `C_DamageMeter` sessions plus `ENCOUNTER_END`.
   - Arena: drop it.
7. **TOC:** ship `DisasterZone_Camelot.toc` (`## Interface: 16001`) next to the TBC TOC, sharing the file list. Use `[AllowLoadGameType camelot]` for Forever-only files (for example a `Meter_DamageMeter.lua`). Confirm in game that `## LoadSavedVariablesFirst` and `loadstring` (the Boot patcher) are still honoured.
8. **Guardrail:** extend `dev/tools/check.py` with a Forever profile. Point `known_globals.json`'s harvest at the Gethe `forever` branch's `[F-doc]` + `[F-src]`, and flag any raw use of a section B name outside `Compat.lua`.

### Still to check in game (UNVERIFIED items worth one `/dump` each)

- Whether `RegisterEvent("COMBAT_LOG_EVENT_UNFILTERED")` errors or silently registers.
- Whether `GameTooltip:HasScript("OnTooltipSetItem")` is true.
- `GetGuildRosterInfo`, `GuildRosterSetOfficerNote`, `GetLootSourceInfo`, `SetPortraitToTexture`, `OffhandHasWeapon`, `GetMacroSpell`.
- The default of `loadDeprecationFallbacks`.
- Which restriction states are active in open world combat vs a dungeon, via `C_RestrictedActions.IsAddOnRestrictionActive(Enum.AddOnRestrictionType.*)`.
