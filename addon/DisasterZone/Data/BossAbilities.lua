if DisasterZoneBoot and DisasterZoneBoot.Run("Data/BossAbilities.lua", ...) then return end -- DisasterZone Data/BossAbilities.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/BossAbilities.lua (the tests' TBC clients run
-- it); Forever's boss abilities are not known yet (the raids open 2026-12-09).
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.BossAbilities = {}
