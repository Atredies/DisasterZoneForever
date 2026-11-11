if DisasterZoneBoot and DisasterZoneBoot.Run("Data/ModelIndex.lua", ...) then return end -- DisasterZone Data/ModelIndex.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/ModelIndex.lua (the tests' TBC clients run
-- it); the 3D boards are hidden on Forever.
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.ModelIndex = {}
