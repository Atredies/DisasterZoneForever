if DisasterZoneBoot and DisasterZoneBoot.Run("Data/RaidMaps.lua", ...) then return end -- DisasterZone Data/RaidMaps.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/RaidMaps.lua (the tests' TBC clients run
-- it); the strategy boards are hidden on Forever.
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.RaidMaps = {}
