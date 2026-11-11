if DisasterZoneBoot and DisasterZoneBoot.Run("Data/ForeverRaids.lua", ...) then return end -- DisasterZone Data/ForeverRaids.lua
-- The raids the raid planner offers on WoW Forever (client 1.60.1): the ONE place to add a raid.
--
-- Loaded on Forever only (Core/Compat.lua's isForever); on the TBC client the planner keeps its raids from
-- Data/Items.lua + Data/Raids.lua. Every guild member must have the same list: the sync refuses a raid whose key it does
-- not know. So a new raid goes in here and ships to everyone in one release (or a signed in-game update).
--
-- Adding a raid when Blizzard releases one:
--   1. Someone zones in once with DisasterZone on: `/dz raiddata` prints the entry it learned (name, instance id,
--      size, the bosses pulled). The group finder's raid activities are listed there too.
--   2. Paste it into `raids` below, give it a short key (lower case, never changed later: saved raids and the sync use
--      it) and a short name, then release.
--
-- Fields of a raid:
--   key         the planner key (saved raids, the sync). Never rename one that shipped.
--   name        as the game names the instance
--   short       the short name the UI shows ("Barrow")
--   size        players (10, 20 or 40 on Forever; fixed sizes)
--   level       the minimum level the New raid window asks for
--   instanceID  GetInstanceInfo()'s 8th value; nil until someone has zoned in (`/dz raiddata`)
--   bosses      boss count (informational until the encounter ids are learned)
--   opens       the release date, "YYYY-MM-DD" (informational)
-- Sources 2026-11-08: Blizzard's announcements as reported by method.gg, timesaver.gg, mmonster.co (sizes and boss
-- counts agree); Onyxia's Lair keeps its classic instance id 249.
local addonName, ns = ...
ns.Data = ns.Data or {}
if not (ns.Compat and ns.Compat.isForever) then return end

ns.Data.PlannerRaids = {
    level = 60,                 -- the level cap (GetMaxPlayerLevel() wins if the client says more)
    sizes = { 10, 20, 40 },     -- the raid sizes a team or a raid may have
    other = 40,                 -- the size of an "Other" raid
    raids = {
        { key = "barrow", name = "Barrow Deeps", short = "Barrow", size = 10, level = 60, instanceID = nil, bosses = 8,
          opens = "2026-12-09" },
        { key = "hyjal", name = "Hyjal Summit", short = "Hyjal", size = 20, level = 60, instanceID = nil, bosses = 13,
          opens = "2026-12-09" },
        { key = "ony", name = "Onyxia's Lair", short = "Ony", size = 40, level = 60, instanceID = 249, bosses = 1,
          opens = "2026-12-09" },
    },
}
