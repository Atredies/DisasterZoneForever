if DisasterZoneBoot and DisasterZoneBoot.Run("Data/SimItems.lua", ...) then return end -- DisasterZone Data/SimItems.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/SimItems.lua (the tests' TBC clients run
-- it); the gear sim (WoWSims TBC rules) is hidden on Forever (Core/Constants.lua FOREVER_HIDDEN).
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.SimItems, ns.Data.SimConsumables, ns.Data.SimOnUse, ns.Data.SimProcs, ns.Data.SimSuffixes = {}, {}, {}, {}, {}
