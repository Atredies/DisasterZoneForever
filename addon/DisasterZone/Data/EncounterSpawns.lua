if DisasterZoneBoot and DisasterZoneBoot.Run("Data/EncounterSpawns.lua", ...) then return end -- DisasterZone Data/EncounterSpawns.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/EncounterSpawns.lua (the tests' TBC clients run
-- it); the strategy boards are hidden on Forever.
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.EncounterSpawns = {}
