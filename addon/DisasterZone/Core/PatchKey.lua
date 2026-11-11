if DisasterZoneBoot and DisasterZoneBoot.Run("Core/PatchKey.lua", ...) then return end -- DisasterZone: public key in-game updates are verified with (written by dev/tools/release.py keygen).
-- The private half lives only on the publisher's machine. Core/Patch.lua explains the scheme.
local addonName, ns = ...

ns.PatchKey = {
    seed = "c9682bcd18b702279932b068e9d94489",
    root = "a084ad6fdb3ecbf55309cf0160669754e36c9ee3f12e147bc93b98b04f3d463e",
    h = 10,
}
