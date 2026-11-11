"""Secret values on WoW Forever: every place that reads health, power or a mob's GUID / name must survive a secret
(Core/Compat.lua: Compat.Plain / Pct / HealthPct / PowerPct / GUID). On Forever UnitHealth, UnitHealthMax and UnitPower
are secret everywhere; inside an instance an NPC's UnitName and UnitGUID are too (Probe Findings 2026-11-08). The
mock's secrets are tables, so a comparison, arithmetic or (here) a table key on one raises.

Run: luaenv/bin/python tests/forever/test_forever_secrets.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors  # noqa: E402

DEADMINES = dict(name="The Deadmines", instance_id=36, instance_type="party", max_players=5, difficulty_id=1)


def in_dungeon(class_file="WARRIOR"):
    """A Forever client inside the Deadmines, targeting an NPC (secret name and GUID) with a nameplate."""
    w, c = solo("Arakis", class_file=class_file, guild_rank=0, level=60, forever=True)
    mob = w.spawn_npc(644, "Rhahk'Zor")
    w.enter_instance(**DEADMINES)
    c.eval("__MOCK.set_npc_target(...)", mob)
    c.eval("__MOCK.add_nameplate(...)", mob)
    w.tick(1)
    return w, c


def ok(c, lua):
    """Runs lua in a pcall; returns (ok, first result or the error)."""
    return c.eval("local ok, r = pcall(function() %s end); return ok, ok and r or tostring(r)" % lua)


@case
def test_compat_helpers():
    w, c = in_dungeon()
    assert c.eval("return issecretvalue(UnitGUID('target'))") is True
    assert c.eval("return ns.Compat.HealthPct('player')") is None
    assert c.eval("return ns.Compat.PowerPct('player')") is None
    assert c.eval("return ns.Compat.GUID('target')") is None
    assert c.eval("return ns.Compat.GUID('player') ~= nil") is True
    assert c.eval("return ns.Compat.Plain(UnitHealth('player'))") is None
    assert c.eval("return ns.Compat.Plain(5)") == 5
    assert c.eval("return ns.Compat.Pct(25, 50)") == 50
    assert c.eval("return ns.Compat.Pct(25, 0)") is None
    no_errors(w)


@case
def test_boss_mod_and_learn_skip_secrets():
    w, c = in_dungeon()
    assert c.eval("return ns.BossMod.NpcOf(UnitGUID('target'))") is None
    for u in ("target", "nameplate1", "boss1"):
        assert ok(c, "ns.BossMod.CheckHealth('%s')" % u)[0], u
    no_errors(w)


@case
def test_warrior_rotation_reads_no_secrets():
    w, c = in_dungeon()
    c.set_combat(True)
    w.tick(1)
    assert ok(c, "return ns.WarriorSwing:Snapshot()")[0]
    c.set_combat(False)
    no_errors(w)


@case
def test_unit_frames_and_plates_read_hidden_health():
    w, c = in_dungeon()
    r = c.eval("local d = ns.LookUnits.Data('target'); return d.hp, d.hpMax, d.hpHidden, d.name == nil, d.guid == nil")
    assert r == (1, 1, True, True, True), r
    r = c.eval("local d = ns.LookUnits.Data('player'); return d.hpHidden, d.name ~= nil")
    assert r == (True, True), r
    assert ok(c, "local p = {}; ns.Plates:Read('nameplate1', p); return p.hpTarget") == (True, 1)
    no_errors(w)


@case
def test_combat_text_low_health_is_quiet():
    w, c = in_dungeon()
    assert ok(c, "ns.CombatText:CheckLow('player'); ns.CombatText:CheckLow('player', true)")[0]
    no_errors(w)


@case
def test_fight_events_raise_nothing():
    w, c = in_dungeon("PALADIN")
    c.set_combat(True)
    for _ in range(3):
        c._fire("UNIT_HEALTH", "player")
        c._fire("UNIT_HEALTH", "target")
        c._fire("UNIT_POWER_UPDATE", "player", "MANA")
        c._fire("PLAYER_TARGET_CHANGED")
        w.tick(0.5)
    c.set_combat(False)
    w.tick(2)
    no_errors(w)


if __name__ == "__main__":
    run_all(globals())
