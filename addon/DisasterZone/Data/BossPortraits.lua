if DisasterZoneBoot and DisasterZoneBoot.Run("Data/BossPortraits.lua", ...) then return end -- DisasterZone Data/BossPortraits.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/BossPortraits.lua (the tests' TBC clients run
-- it); Forever's boss creatures are not known yet.
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.BossPortraits = {}
