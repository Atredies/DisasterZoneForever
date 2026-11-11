if DisasterZoneBoot and DisasterZoneBoot.Run("Core/PatchKey.lua", ...) then return end -- DisasterZone: public key in-game updates are verified with (written by dev/tools/release.py keygen).
-- The private half lives only on the publisher's machine. Core/Patch.lua explains the scheme.
-- No key yet: DisasterZone for WoW Forever has not made its own signing key, so in-game updates are OFF (Core/Patch.lua
-- does nothing without a key, and never trusts the TBC original's). 'release.py keygen', on ONE machine, writes ours here.
local addonName, ns = ...

ns.PatchKey = nil
