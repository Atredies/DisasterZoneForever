if DisasterZoneBoot and DisasterZoneBoot.Run("Data/StarterStrategies.lua", ...) then return end -- DisasterZone Data/StarterStrategies.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/StarterStrategies.lua (the tests' TBC clients run
-- it); the strategy boards are hidden on Forever until the Forever raids have maps.
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.StarterStrategies = {}
