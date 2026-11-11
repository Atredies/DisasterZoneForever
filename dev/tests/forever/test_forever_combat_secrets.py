"""Combat secrets on WoW Forever: the values Blizzard's API docs mark secret while a restriction is on (spell cooldowns,
attack / ranged / movement speed, enemy casts, threat, raid marks, UnitIsUnit, an NPC's name / class / GUID). The
mock (tools/wowmock/forever.lua, "combat secrets") hands them out as secrets in combat and inside an instance; every
reader goes through Core/Compat.lua (SpellCooldown, AttackSpeed, RangedSpeed, UnitSpeed, RaidMark, SameUnit, Name,
Plain) and degrades (last known value, no bar, no mark) instead of raising. Nothing secret may reach SavedVariables.

Run: luaenv/bin/python tests/forever/test_forever_combat_secrets.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors  # noqa: E402

DEADMINES = dict(name="The Deadmines", instance_id=36, instance_type="party", max_players=5, difficulty_id=1)

# (a recursive look through every saved table for a secret value, key or value)
NO_SECRETS = """
local seen = {}
local function walk(t, path)
    if seen[t] then return nil end
    seen[t] = true
    for k, v in pairs(t) do
        if issecretvalue(k) then return path .. "[<secret key>]" end
        if issecretvalue(v) then return path .. "." .. tostring(k) end
        if type(v) == "table" then
            local bad = walk(v, path .. "." .. tostring(k))
            if bad then return bad end
        end
    end
end
for _, n in ipairs({ "DisasterZoneDB", "DisasterZoneLogDB", "DisasterZoneMeterDB", "DisasterZoneBossLearnDB" }) do
    local t = _G[n]
    if type(t) == "table" then
        local bad = walk(t, n)
        if bad then return bad end
    end
end
return nil
"""


def fight(class_file="WARRIOR", cast=True):
    """A Forever client in the Deadmines, in combat with an NPC target (secret name, GUID, cast, mark) on a plate."""
    w, c = solo("Arakis", class_file=class_file, guild_rank=0, level=60, forever=True)
    mob = w.spawn_npc(644, "Rhahk'Zor")
    w.enter_instance(**DEADMINES)
    c.eval("__MOCK.set_npc_target(...)", mob)
    c.eval("__MOCK.add_nameplate(...)", mob)
    if cast:
        c.eval("__MOCK.npc_casts = { [...] = "
               "{ 'Shadow Bolt', GetTime() * 1000 - 500, GetTime() * 1000 + 1500, 686, false } }", mob)
    w.tick(1)
    c.set_combat(True)
    w.tick(0.5)
    return w, c


def ok(c, lua):
    """Runs lua in a pcall; returns (ok, first result or the error)."""
    return c.eval("local ok, r = pcall(function() %s end); return ok, ok and r or tostring(r)" % lua)


def must(c, lua):
    r = ok(c, lua)
    assert r[0], r[1]
    return r[1]


@case
def test_mock_hands_out_combat_secrets():
    w, c = fight()
    mob = c.eval("return __MOCK.target_npc")
    assert c.eval("return issecretvalue(C_Spell.GetSpellCooldown(6673).startTime)") is True
    assert c.eval("return C_Spell.GetSpellCooldown(6673).isActive") is True
    assert c.eval("return issecretvalue((UnitAttackSpeed('player')))") is True
    assert c.eval("return issecretvalue((GetUnitSpeed('player')))") is True
    assert c.eval("return issecretvalue((UnitCastingInfo('target')))") is True
    assert c.eval("return issecretvalue(UnitIsUnit('target', 'nameplate1'))") is True
    c.eval("__MOCK.marks[...] = 8", mob)
    assert c.eval("return issecretvalue(GetRaidTargetIndex('target'))") is True
    c.set_combat(False)
    no_errors(w)


@case
def test_compat_combat_helpers():
    w, c = fight()
    r = c.eval("return ns.Compat.SpellCooldown(6673)")
    assert r == (None, None, True), r
    c.eval("__MOCK.spell_cd = { [6673] = { 0, 0 } }")
    assert c.eval("return ns.Compat.SpellCooldown(6673)") == (0, 0, True)
    assert c.eval("return ns.Compat.CooldownLeft(6673)") == 0
    assert c.eval("return ns.Compat.SpellCooldown(nil)") == (None, None, False)
    assert c.eval("return ns.Compat.AttackSpeed('player')") is None
    assert c.eval("return ns.Compat.UnitSpeed('player')") is None
    assert c.eval("return ns.Compat.RangedSpeed('player')") is None
    assert c.eval("return ns.Compat.RaidMark('target')") is None
    assert c.eval("return ns.Compat.Name('target')") is None
    assert c.eval("return ns.Compat.Name('player')") == "Arakis"
    assert c.eval("return ns.Compat.SameUnit('target', 'nameplate1')") is False
    assert c.eval("return ns.Compat.SameUnit('player', 'player')") is True
    c.set_combat(False)
    w.tick(0.5)
    # out of combat (a cooldown is plain again, in the instance too)
    assert c.eval("return ns.Compat.SpellCooldown(6673)") == (0, 0, True)
    assert c.eval("return ns.Compat.AttackSpeed('player') ~= nil") is True
    no_errors(w)


@case
def test_warrior_swing_timer_in_combat():
    w, c = fight("WARRIOR")
    must(c, "ns.WarriorSwing.active = true; ns.WarriorSwing:MarkDirty(); return true")
    for _ in range(5):
        c.eval("__MOCK.player_swing(0, 2.6)")
        w.tick(0.6)
        must(c, "return ns.WarriorSwing:Snapshot() ~= nil")
        if c.eval("return ns.WarriorSwing.Plan ~= nil"):
            must(c, "ns.WarriorSwing:Plan(); return true")
    c.set_combat(False)
    w.tick(1)
    assert c.eval(NO_SECRETS) is None
    no_errors(w)


@case
def test_paladin_swing_timer_in_combat():
    w, c = fight("PALADIN")
    must(c, "ns.SwingTimer.active = true; ns.SwingTimer.twist = true; return true")
    c.set_combat(False)
    w.tick(0.2)
    c.set_combat(True)                                  # (StartFight: the target's name, secret here)
    for _ in range(6):
        c.eval("__MOCK.player_swing(0, 3.5)")
        w.tick(0.7)
        must(c, "return ns.SwingTimer:Snapshot() ~= nil")
    must(c, "ns.SwingTimer:MarkDirty(); return true")
    c.set_combat(False)
    w.tick(1)
    for rep in c.eval_py("return ns.SwingTimer:Reports()") or []:
        assert rep.get("target") is None, rep
    assert c.eval(NO_SECRETS) is None
    no_errors(w)


@case
def test_hunter_shot_timer_in_combat():
    w, c = fight("HUNTER")
    must(c, "ns.ShotTimer.active = true; return true")
    c.set_combat(False)
    w.tick(0.2)
    c.set_combat(True)
    for _ in range(5):
        c._fire("START_AUTOREPEAT_SPELL")
        w.tick(0.5)
        must(c, "return ns.ShotTimer:NextStart() ~= nil")
        if c.eval("return ns.ShotTimer.Snapshot ~= nil"):
            must(c, "ns.ShotTimer:Snapshot(); return true")
    c.set_combat(False)
    w.tick(1)
    assert c.eval(NO_SECRETS) is None
    no_errors(w)


@case
def test_swing_practice_and_my_log_read_no_secrets():
    w, c = fight("PALADIN")
    if c.eval("return ns.SwingPractice ~= nil and ns.SwingPractice.Start ~= nil"):
        ok(c, "ns.SwingPractice:Start(); return true")
        w.tick(1)
        must(c, "if ns.SwingPractice.Stop then ns.SwingPractice:Stop() end; return true")
    c.eval("__MOCK.casting = { 'Holy Light', GetTime() * 1000, GetTime() * 1000 + 2500, 635 }")
    c._fire("UNIT_SPELLCAST_START", "player", "cast-1", 635)
    c._fire("UNIT_SPELLCAST_SUCCEEDED", "player", "cast-1", 635)
    w.tick(1)
    c.set_combat(False)
    w.tick(1)
    assert c.eval(NO_SECRETS) is None
    no_errors(w)


@case
def test_combat_text_alerts_and_totem_bar():
    w, c = fight("SHAMAN")
    must(c, "ns.CombatText:CheckAlerts(); return true")
    c.eval("__MOCK.totems = { [1] = { 'Searing Totem', GetTime(), 60, 135825 } }")
    must(c, "return ns.Totems:MyTotem(2) == nil")
    if c.eval("return ns.TotemBar ~= nil and ns.TotemBar.Refresh ~= nil"):
        ok(c, "ns.TotemBar:Refresh(); return true")
    c.set_combat(False)
    w.tick(0.5)
    assert c.eval("return (ns.Totems:MyTotem(2))") == "Searing Totem"
    no_errors(w)


@case
def test_cast_bars_and_plates_skip_a_secret_cast():
    w, c = fight()
    # the looks' cast bar: no bar for a cast whose times are secret
    if c.eval("return ns.LookCast ~= nil and ns.LookCast.Start ~= nil"):
        must(c, "local f = { unit = 'target', name = { SetText = function() end }, icon = { SetTexture = function() end },"
                " IsShown = function() return false end, Hide = function() end }; ns.LookCast:Start(f); return true")
    assert c.eval("local p = {}; ns.Plates:Read('nameplate1', p); return issecretvalue(p.name) or issecretvalue(p.mark)") \
        is False
    assert c.eval("local p = {}; ns.Plates:Read('nameplate1', p); return p.castInfo == nil, p.mark == nil, p.target") \
        == (True, True, False)
    # the plate looks' raid mark and the pen's text width with a secret name
    must(c, "ns.CTPen.W(nil, 'Friz', 11, UnitName('target'), 1); return true")
    no_errors(w)


@case
def test_threat_scan_and_aggro_read_no_secrets():
    w, c = fight()
    c.eval("__MOCK.threat = { Arakis = { true, 3, 100, 100, 5000 } }")
    r = c.eval("local st = ns.Threat:Scan(); return #st.rows, st.name == nil, st.guid == nil, st.me ~= nil")
    assert r == (0, True, True, False), r                 # (threat secret in combat: no rows, no error)
    c.set_combat(False)
    w.tick(0.5)
    r = c.eval("local st = ns.Threat:Scan(); return #st.rows, st.name == nil, st.me ~= nil")
    assert r == (1, True, True), r                        # (out of combat: my row; the name stays secret)
    must(c, "return ns.LookAggro == nil or ns.LookAggro.Read == nil or ns.LookAggro.Read('player') ~= nil")
    c.set_combat(False)
    no_errors(w)


@case
def test_wardrobe_never_stores_a_secret_target():
    w, c = fight()
    must(c, "ns.Wardrobe:CheckTarget(); ns.Wardrobe:CheckBossDead(); return true")
    c.set_combat(False)
    w.tick(0.5)
    assert c.eval(NO_SECRETS) is None
    no_errors(w)


@case
def test_unit_frames_tanks_and_strategy_marks():
    w, c = fight()
    r = c.eval("local d = ns.LookUnits.Data('target'); return d.raidIcon == nil, d.selected, d.class == nil")
    assert r == (True, False, True), r
    must(c, "ns.LookUnits.MarkTarget(); return true")
    must(c, "return ns.Util.UnitNameRealm('target') == nil")
    must(c, "return ns.Util.IsPlayerMasterLooter() ~= nil")
    must(c, "return ns.Situation:TargetPlayer() == nil")
    c.set_combat(False)
    no_errors(w)


@case
def test_bingo_detect_group_guids():
    w, c = fight()
    if c.eval("return ns.BingoDetect ~= nil"):
        must(c, "ns.BingoDetect:OnConnection('party1', false); ns.BingoDetect:OnTick(); return true")
    c.set_combat(False)
    no_errors(w)


if __name__ == "__main__":
    run_all(globals())
