if DisasterZoneBoot and DisasterZoneBoot.Run("Data/BossJournal.lua", ...) then return end -- DisasterZone Data/BossJournal.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/BossJournal.lua (the tests' TBC clients run
-- it); Forever's boss art is not known yet.
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.BossJournal = {}
