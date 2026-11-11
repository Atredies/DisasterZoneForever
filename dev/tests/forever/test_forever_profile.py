"""The mock client's WoW Forever profile (Client(..., forever=True), tools/wowmock/forever.lua + forever_facts.lua,
generated from a DZProbe run by dev/probe/mock_facts.py), and DisasterZone booting on it.

Run: luaenv/bin/python tests/forever/test_forever_profile.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors  # noqa: E402


def forever(**kw):
    return solo("Arakis", class_file="WARRIOR", guild_rank=0, level=17, forever=True, **kw)


def as_list(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v)]
    return list(v or [])


@case
def test_addon_boots_on_forever():
    w, c = forever()
    assert c.eval("return select(4, GetBuildInfo())") == 16001
    assert c.eval("return (GetBuildInfo())") == "1.60.1"
    assert c.eval("return ns.Compat.isForever") is True
    assert c.eval("return ns.Compat:CanUseCombatLog()") is False
    shimmed = as_list(c.eval_py("return ns.Compat.shimmed"))
    for n in ("GetItemInfo", "GetSpellInfo", "UnitBuff", "GetContainerItemInfo", "InviteUnit"):
        assert n in shimmed, (n, shimmed)
    assert not c.eval_py("return __MOCK.forbidden")
    no_errors(w)


@case
def test_old_globals_gone_new_ones_there():
    w, c = forever(load=False)
    for n in ("GetSpellInfo", "UnitBuff", "UnitAura", "GetItemInfo", "GetTalentInfo", "InviteUnit",
              "CombatLogGetCurrentEventInfo"):
        assert c.eval("return %s == nil" % n), n
    for n in ("C_Spell.GetSpellInfo", "C_Spell.GetSpellCooldown", "C_UnitAuras.GetAuraDataByIndex",
              "C_Item.GetItemInfo", "C_PartyInfo.InviteUnit", "C_Container.GetContainerItemInfo",
              "C_RestrictedActions.IsAddOnRestrictionActive", "TooltipDataProcessor.AddTooltipPostCall"):
        assert c.eval("return type(%s) == 'function'" % n), n
    assert c.eval("return WOW_PROJECT_ID") == 18
    assert c.eval("return GetMaxPlayerLevel()") == 60
    assert c.eval("return Enum.LootMethod.Masterlooter") == 2
    assert c.eval("return C_EventUtils.IsEventValid('CRAFT_SHOW')") is False


@case
def test_combat_log_registration_is_forbidden():
    w, c = forever(load=False)
    c.eval("CreateFrame('Frame'):RegisterEvent('COMBAT_LOG_EVENT_UNFILTERED')")
    errs = w.errors()
    assert any("ADDON_ACTION_FORBIDDEN" in e for e in errs), errs
    assert len(c.eval_py("return __MOCK.forbidden")) == 1


@case
def test_boss_pull_locks_addon_messages():
    w, c = forever(load=False)
    c.eval(r"""
      __seen = {}
      local f = CreateFrame('Frame')
      f:RegisterEvent('ENCOUNTER_START'); f:RegisterEvent('ENCOUNTER_END')
      f:RegisterEvent('ADDON_RESTRICTION_STATE_CHANGED')
      f:SetScript('OnEvent', function(_, ev, a, b)
        __seen[#__seen + 1] = ev .. ':' .. tostring(a) .. ':' .. tostring(b) .. ':'
          .. tostring(C_ChatInfo.InChatMessagingLockdown())
      end)
      C_ChatInfo.RegisterAddonMessagePrefix('ZZ')""")
    assert c.eval("return C_ChatInfo.SendAddonMessage('ZZ', 'hi', 'GUILD')") == 0
    c.fire("ENCOUNTER_START", 2741, "Rhahk'Zor", 1, 5)
    assert c.eval("return C_ChatInfo.InChatMessagingLockdown()") is True
    assert c.eval("return C_ChatInfo.SendAddonMessage('ZZ', 'hi', 'GUILD')") == 11
    assert c.eval("return C_RestrictedActions.IsAddOnRestrictionActive(Enum.AddOnRestrictionType.Encounter)") is True
    c.fire("ENCOUNTER_END", 2741, "Rhahk'Zor", 1, 5, 1)
    assert c.eval("return C_ChatInfo.SendAddonMessage('ZZ', 'hi', 'GUILD')") == 0
    assert c.eval("return __MOCK.lockdown_refused") == 1
    # the client's order: the pull reaches addons before the lockdown; the lockdown lifts before the end does
    assert as_list(c.eval_py("return __seen")) == [
        "ENCOUNTER_START:2741:Rhahk'Zor:false",
        "ADDON_RESTRICTION_STATE_CHANGED:1:1:false",
        "ADDON_RESTRICTION_STATE_CHANGED:5:1:true",
        "ADDON_RESTRICTION_STATE_CHANGED:1:0:true",
        "ADDON_RESTRICTION_STATE_CHANGED:5:0:false",
        "ENCOUNTER_END:2741:Rhahk'Zor:false",
    ]


@case
def test_unit_values_are_secret():
    w, c = forever(load=False)
    assert c.eval("return issecretvalue(UnitHealth('player'))") is True
    assert c.eval("return issecretvalue(UnitPower('player'))") is True
    assert c.eval("return issecretvalue(UnitName('player'))") is False
    assert c.eval("return (pcall(function() return UnitHealth('player') / UnitHealthMax('player') end))") is False
    assert c.eval("return (pcall(function() return UnitHealth('player') > 0 end))") is False
    assert c.eval("return issecretvalue('hp: ' .. UnitHealth('player'))") is True


@case
def test_auras_refused_in_combat():
    w, c = forever(load=False)
    c.eval("__MOCK.player_auras = { { 'Battle Shout', 6673 } }")
    assert c.eval("return C_UnitAuras.GetAuraDataByIndex('player', 1, 'HELPFUL').name") == "Battle Shout"
    c.set_combat(True)
    assert c.eval("return (pcall(C_UnitAuras.GetAuraDataByIndex, 'player', 1, 'HELPFUL'))") is False
    c.set_combat(False)
    assert c.eval("return C_UnitAuras.GetAuraDataByIndex('player', 1, 'HELPFUL').spellId") == 6673


@case
def test_tooltips_use_tooltip_data_processor():
    w, c = forever(load=False)
    assert c.eval("return GameTooltip:HasScript('OnTooltipSetItem')") is False
    c.eval("""__tt = nil
      TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tt, data) __tt = data.id end)
      GameTooltip:SetOwner(UIParent, 'ANCHOR_NONE'); GameTooltip:SetItemByID(19019)""")
    assert c.eval("return __tt") == 19019


if __name__ == "__main__":
    run_all()
