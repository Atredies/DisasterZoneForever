"""The class tools on WoW Forever: spec and role from the trait tree, the TBC-only spells gone, the tools load.

Forever has one spec per class named after the class, with no points (seen in game 2026-11-09:
C_SpecializationInfo.GetSpecializationInfo(1) printed "1491 Warrior 626008 DAMAGER 4 0 nil 0 true"); the vanilla
trees are trait-node groups (Core/Compat.lua: Compat.TalentTabPoints / Talents / TalentRank / SpecRole). TBC spells
checked against Wowhead's Forever spell database (2026-11-09): no Heroism / Bloodlust, Seal of Blood / the Martyr,
Crusader Strike, Steady Shot, Kill Command, Rampage; Earth Shield and Aspect of the Viper exist.

Run: luaenv/bin/python tests/forever/test_forever_class_tools.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors  # noqa: E402


def forever(class_file, talents=(0, 0, 0), **kw):
    return solo("Arakis", class_file=class_file, guild_rank=0, level=60, talents=talents, forever=True, **kw)


def specs(c):
    """ns.ClassKit:MySpecs() as a Python list."""
    r = c.eval("local t = ns.ClassKit:MySpecs(); return table.concat(t, ',')")
    return r.split(",") if r else []


@case
def test_mock_spec_matches_the_client():
    w, c = forever("WARRIOR", talents=(31, 20, 0))
    r = c.eval("return C_SpecializationInfo.GetSpecializationInfo(1)")
    assert r == (1491, "Warrior", "", 626008, "DAMAGER", 4, 0, None, 0, True), r
    assert c.eval("return GetTalentTabInfo == nil and GetNumTalentTabs == nil and GetTalentInfo == nil") is True
    no_errors(w)


@case
def test_warrior_spec_and_role_from_the_trait_tree():
    w, c = forever("WARRIOR", talents=(31, 20, 0))
    assert c.eval("return ns.Compat.NumTalentTabs()") == 3
    assert [c.eval("return ns.Compat.TalentTabPoints(%d)" % t) for t in (1, 2, 3)] == [31, 20, 0]
    assert c.eval("return ns.ClassKit:MyTab()") == 1
    assert specs(c) == ["Arms"]
    assert c.eval("return ns.BiS:DetectSpec()") == "Arms"
    assert c.eval("return ns.ClassKit:MyRole()") == "dps"
    assert c.eval("return ns.Compat.SpecRole()") == "DAMAGER"
    assert c.eval("return ns.ClassKit:IsMine('war')") is True
    c.set_talents((5, 0, 46))
    c.eval("ns.Compat.TalentsChanged()")
    assert specs(c) == ["Protection"]
    assert c.eval("return ns.ClassKit:MyRole()") == "tank"
    assert c.eval("return ns.ClassKit:IsMine('war')") is False
    no_errors(w)


@case
def test_no_points_falls_back_to_stance_then_spec_role():
    w, c = forever("WARRIOR")
    assert c.eval("return ns.ClassKit:MyTab()") is None
    assert c.eval("return ns.BiS:DetectSpec()") == ""
    assert c.eval("return ns.ClassKit:MyRole()") == "dps"           # the spec's role (DAMAGER)
    c.eval("GetShapeshiftForm = function() return 2 end")            # Defensive Stance
    assert c.eval("return ns.ClassKit:MyRole()") == "tank"
    assert c.eval("return ns.ClassKit:IsMine('war')") is True        # (its fallback: every warrior)
    no_errors(w)


@case
def test_paladin_shaman_hunter_specs():
    for cls, pts, spec, role in (("PALADIN", (0, 0, 31), "Retribution", "dps"),
                                 ("PALADIN", (31, 0, 0), "Holy", "healer"),
                                 ("SHAMAN", (0, 0, 31), "Restoration", "healer"),
                                 ("SHAMAN", (0, 31, 0), "Enhancement", "dps"),
                                 ("HUNTER", (0, 31, 0), "Marksmanship", "dps")):
        w, c = forever(cls, talents=pts)
        assert specs(c) == [spec], (cls, pts)
        assert c.eval("return ns.ClassKit:MyRole()") == role, (cls, pts)
        no_errors(w)
    w, c = forever("PALADIN", talents=(0, 0, 31))
    assert c.eval("return ns.ClassKit:IsMine('swing')") is True
    w, c = forever("HUNTER")
    assert c.eval("return ns.ClassKit:IsMine('shot')") is True


@case
def test_talent_ranks_from_trait_nodes():
    w, c = forever("WARRIOR", talents=(31, 20, 0))
    c.eval("__MOCK.trait_talents = { { spellID = 12295, tab = 1, rank = 3, max = 5 }, "
           "{ spellID = 12319, tab = 2, rank = 0, max = 5 } }")
    c.eval("ns.Compat.TalentsChanged()")
    assert c.eval("return ns.Compat.TalentRank(12295)") == 3
    assert c.eval("return ns.Compat.TalentRank(12319)") == 0
    assert c.eval("return ns.Compat.TalentRank(99999)") == 0
    assert c.eval("return ns.WarriorSwing.TacticalMastery()") == 3
    assert c.eval("return ns.BiSExport and ns.BiSExport:TalentString() or ''") == ""
    no_errors(w)


@case
def test_professions_reads_talents():
    w, c = forever("WARRIOR", talents=(31, 20, 0))
    assert c.eval("return ns.Compat.TalentTabPoints(1, 1)") == 31
    assert c.eval("return ns.Compat.TalentTabPoints(1, 2)") is None    # (no second spec group)
    no_errors(w)


@case
def test_shaman_has_no_heroism_but_earth_shield():
    w, c = forever("SHAMAN", talents=(0, 0, 31))
    D = "ns.ClassData.SHAMAN"
    assert c.eval("return %s.HEROISM == nil and %s.BLOODLUST == nil and #%s.HERO_WHEN == 0" % (D, D, D)) is True
    assert c.eval("return %s.EARTH_SHIELD" % D) == 974
    assert c.eval("return ns.Totems:HasHero()") is False
    assert c.eval("return ns.Totems:HeroSpell()") is None
    assert c.eval("return ns.Totems:SetHero(ns.Totems:Me(), 'pull')") is False
    # the planner's raid falls back to the first Forever raid, not Serpentshrine Cavern
    key = c.eval("return ns.Totems:RaidKey()")
    assert key == c.eval("return ns.Data.Raids[1].key") and key != "SerpentshrineCavern", key
    # the planner and the bar, in demo mode (a raid of shamans): no Heroism column, no hero plan, no Lua error
    c.eval("ns.ClassKit:SetOn('totems', true)")
    c.slash("/dz demo")
    w.tick(1)
    c.eval("ns.TotemsUI:Open()")
    w.tick(0.5)
    plan = c.eval("local p = ns.Totems:AutoPlan(); local n = 0; for _ in pairs(p.hero) do n = n + 1 end; "
                  "local h = 0; for _, v in pairs(p.hero) do if v ~= 'none' then h = h + 1 end end; return h")
    assert plan == 0, plan
    assert not any("DZHERO" in (l or "") for l in [str(x) for x in c.eval_py("return ns.Totems:ReportLines()")])
    c.eval("ns.TotemBar:Update()")
    w.tick(0.5)
    assert c.eval("return DisasterZoneTotem_hero == nil or not DisasterZoneTotem_hero:IsShown()") is True
    no_errors(w)


@case
def test_paladin_plain_swing_timer_from_player_swing():
    w, c = forever("PALADIN", talents=(0, 0, 31))
    assert c.eval("return ns.SwingTimer.twist") is False
    assert c.eval("return ns.SwingTimer.IDS.sob == nil and ns.SwingTimer.IDS.cs == nil") is True
    assert c.eval("return ns.SwingTimer.NameOf('sob')") is None
    c.eval("ns.ClassKit:SetOn('swing', true); ns.DB:SetSetting('swing.idle', true)")
    w.tick(0.5)
    assert c.eval("return ns.SwingTimer.active") is True
    c.eval("__MOCK.player_swing(0, 3.6)")
    w.tick(0.2)
    assert c.eval("return ns.SwingTimer.state.last ~= nil") is True
    assert c.eval("local cur = ns.SwingTimer:Current(); return cur ~= nil and #cur.plan.steps") == 0
    for _ in range(10):
        c.eval("ns.SwingTimerHUD:Update()")
        w.tick(0.3)
    c.slash("/dz swing practice")
    w.tick(0.2)
    assert c.eval("return DisasterZoneSwingPractice == nil or not DisasterZoneSwingPractice:IsShown()") is True
    no_errors(w)


@case
def test_warrior_swing_ids_and_player_swing():
    w, c = forever("WARRIOR", talents=(31, 20, 0))
    ids = c.eval_py("local I = ns.WarriorSwing.IDS; return { I.hs, I.bt, I.ms, I.sweep, I.slam, I.rampage or 0 }")
    assert ids == [25286, 23894, 21553, 12292, 11605, 0], ids
    c.eval("ns.ClassKit:SetOn('war', true); ns.DB:SetSetting('war.idle', true)")
    w.tick(0.5)
    assert c.eval("return ns.WarriorSwing.active") is True
    c.eval("__MOCK.player_swing(0, 2.6)")
    c.eval("__MOCK.player_swing(1, 2.6)")
    w.tick(0.1)
    assert c.eval("return ns.WarriorSwing.state.mhLast ~= nil and ns.WarriorSwing.state.ohLast ~= nil") is True
    c.set_combat(True)
    w.tick(1)
    assert c.eval("local ok = pcall(function() return ns.WarriorSwing:Current() end); return ok") is True
    c.set_combat(False)
    no_errors(w)


@case
def test_hunter_aimed_shot_in_place_of_steady():
    w, c = forever("HUNTER", talents=(0, 31, 0))
    assert c.eval("return ns.ShotTimer.IDS.steady == nil and ns.ShotTimer.IDS.kc == nil") is True
    assert c.eval("return ns.ShotTimer.LEARN") == "aimed"
    # the rotation from a known state: a 3.0 s shot, Aimed Shot (2 s) fits before the next windup, then the shared
    # cooldown keeps Multi-Shot out; Arcane Shot fills
    steps = c.eval("""
        local ST = ns.ShotTimer
        local snap = { now = 10, nextStart = 13, lastShot = 9.6, speed = 3, cycle = 3, haste = 1, windup = 0.5,
          buffer = 0.5, ct = { aimed = 2.0, volley = 6 }, lat = 0.05, kind = 'single', sit = {}, left = {},
          react = 0, gcdReady = 10, busyUntil = 10, gcd = 1.5, cd = { multi = 6, aimed = 6, arcane = 6 },
          ready = { multi = 10, arcane = 10, aimed = 10, volley = 99, etrap = 99, conc = 99, vsting = 99, ssting = 99 },
          kc = false, mana = 100, use = { steady = false, aimedRot = true, multi = true, arcane = true } }
        local out = {}
        for i, st in ipairs(ST.Run(snap)) do out[i] = st.key end
        return table.concat(out, ' ')
    """)
    first = steps.split()
    assert first[0] == "aimed", steps
    assert "multi" not in first[:2], steps          # (shares Aimed Shot's cooldown)
    c.eval("ns.ClassKit:SetOn('shot', true)")
    w.tick(0.5)
    # Auto Shot on and a shot: the timer runs (mana is secret on Forever: no aspect hints, no error)
    c.eval("__MOCK.fire('START_AUTOREPEAT_SPELL')")
    c.eval("__MOCK.fire('UNIT_SPELLCAST_SUCCEEDED', 'player', 'cast-1', 75)")
    w.tick(0.2)
    assert c.eval("local cur = ns.ShotTimer:Current(); return cur ~= nil") is True
    assert c.eval("return ns.ShotTimer:Current().snap.use.aspect") is False
    no_errors(w)


@case
def test_raid_comp_and_resource_drop_tbc_spells():
    w, c = forever("WARRIOR", talents=(31, 20, 0))
    for k in ("heroism", "wrathofair", "totemofwrath", "misery", "coe", "bloodfrenzy", "vampirictouch",
              "ferocious", "exposeweakness"):
        assert c.eval("return ns.RaidComp:GetBuff(...) == nil", k) is True, k
    for k in ("windfury", "unleashedrage", "battleshout", "sunder", "trueshot"):
        assert c.eval("return ns.RaidComp:GetBuff(...) ~= nil", k) is True, k
    assert c.eval("return ns.RaidComp:AirTotem({ { key = 'a', c = 'SHAMAN', sp = 3 } })") is None
    keys = c.eval_py("local o = {} for _, p in ipairs(ns.ClassData.RESOURCE.PRESSES.WARRIOR) do o[#o + 1] = p.key end "
                     "return o")
    assert "rampage" not in keys and "bt" in keys, keys
    ids = c.eval_py("local o = {} for _, p in ipairs(ns.ClassData.RESOURCE.PRESSES.HUNTER) do o[p.key] = p.id end "
                    "return o")
    assert "steady" not in ids and "kc" not in ids and ids["aimed"] == 19434, ids
    no_errors(w)


@case
def test_class_tool_settings_build_on_forever():
    for cls, pts in (("PALADIN", (0, 0, 31)), ("HUNTER", (0, 31, 0)), ("WARRIOR", (31, 20, 0)),
                     ("SHAMAN", (0, 31, 0))):
        w, c = forever(cls, talents=pts)
        c.slash("/dz settings")
        w.tick(0.5)
        c.eval("ns.SettingsUI:SelectSection('classtools')")
        w.tick(0.3)
        c.eval("ns.SettingsUI:Search('timer')")
        w.tick(0.3)
        no_errors(w)


if __name__ == "__main__":
    run_all()
