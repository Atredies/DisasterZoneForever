if DisasterZoneBoot and DisasterZoneBoot.Run("Data/BossMods/Forever.lua", ...) then return end -- DisasterZone: boss mods (format: dev/docs/bossmods/DATA_FORMAT.md)
-- WoW Forever: no boss mods. Addons get no combat log on Forever, and nobody has timers for the new raids yet; the
-- boss mod runner stays idle. The TBC raids' mods are in dev/fixtures/tbc/Data/BossMods/ (the tests' TBC clients
-- run them in place of this file). B["Raid:Boss"] entries for Forever's raids go here when they exist.
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.BossMods = ns.Data.BossMods or {}
