if DisasterZoneBoot and DisasterZoneBoot.Run("Core/BridgeKey.lua", ...) then return end -- DisasterZone: public keys Discord bridge records are verified with (written by dz-server keygen).
-- The private halves live only with each guild's bot. Core/Bridge.lua explains the scheme.
local addonName, ns = ...

ns.BridgeKeys = ns.BridgeKeys or {}

-- Casual Disaster-CAMWOWEU4Realm4PvP
ns.BridgeKeys["Casual Disaster-CAMWOWEU4Realm4PvP"] = {
    seed = "d247fce6fbe5422710890df701a51bdb",
    root = "5e5a40487755f8d5d1416643488bbe611810850cbb00710a8ca1b06af076d4b5",
    h = 16,
}
