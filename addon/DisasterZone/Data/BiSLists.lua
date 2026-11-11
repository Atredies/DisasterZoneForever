if DisasterZoneBoot and DisasterZoneBoot.Run("Data/BiSLists.lua", ...) then return end -- DisasterZone suggested BiS lists per class guide and phase (My BiS > Suggest).
-- WoW Forever: no suggested lists yet. AtlasLoot Forever's BiS module has no items yet and Wowhead's Forever BiS
-- guides call themselves speculative (most items were hidden at launch), so My BiS > Suggest is off
-- (Core/Loon.lua: no ns.Data.BiSLists) and players build their lists by hand. When a source settles, generate
-- [guide] = { [phase 0..1] = "slot:item,..." } here (the TBC lists: dev/fixtures/tbc/Data/BiSLists.lua).
local addonName, ns = ...
ns.Data = ns.Data or {}
