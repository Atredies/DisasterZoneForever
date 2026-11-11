if DisasterZoneBoot and DisasterZoneBoot.Run("Data/GroupQuests.lua", ...) then return end -- DisasterZone Data/GroupQuests.lua
-- WoW Forever: no data yet. The TBC data this file held is in dev/fixtures/tbc/Data/GroupQuests.lua (the tests' TBC clients run
-- it); the TBC file listed Outland's group quests; Forever's are not generated yet, so the Groups board has no
-- Quest kind on Forever (Data/GroupKinds.lua).
local _, ns = ...
ns.Data = ns.Data or {}
ns.Data.GroupQuests = { zones = {}, quests = {} }
