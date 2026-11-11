if DisasterZoneBoot and DisasterZoneBoot.Run("Data/SimAPL.lua", ...) then return end -- DisasterZone Data/SimAPL.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/SimAPL.lua (the tests' TBC clients run
-- it); the gear sim is hidden on Forever.
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.SimAPL = {}
