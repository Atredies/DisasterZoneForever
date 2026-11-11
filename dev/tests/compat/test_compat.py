"""The WoW Forever compatibility layer (Core/Compat.lua) and what leans on it: the old global names rebuilt from their
C_ replacements only where the client lacks them, no addon combat log on Forever (ns:RegisterEvent and the strategy
board refuse COMBAT_LOG_EVENT_UNFILTERED, so Blizzard's "blocked" popup never shows), and Core/Comm.lua holding
addon messages through a boss pull's chat lockdown and sending them, in order, once it ends.

The "Forever client" here is the mock with the facts DZProbe measured (dev/probe/, vault: Probe Findings 2026-11-08)
put in before the addon loads: WOW_PROJECT_ID 18, issecretvalue, the old globals removed, C_ replacements present.

Run: luaenv\\Scripts\\python.exe tests\\compat\\test_compat.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

FOREVER = r"""
WOW_PROJECT_ID = 18
WOW_PROJECT_CAMELOT = 18
issecretvalue = function() return false end
GetSpellInfo, GetSpellCooldown, UnitBuff, GetContainerItemInfo, InviteUnit = nil, nil, nil, nil, nil
C_Spell = C_Spell or {}
C_Spell.GetSpellInfo = function(id)
  if id == 133 then return { name = "Fireball", iconID = 135812, castTime = 3500, minRange = 0, maxRange = 35,
    spellID = 133, originalIconID = 135812 } end
end
C_Spell.GetSpellCooldown = function() return { startTime = 10, duration = 1.5, isEnabled = true, modRate = 1 } end
C_UnitAuras = C_UnitAuras or {}
C_UnitAuras.GetAuraDataByIndex = function(unit, i, filter)
  __lastFilter = filter
  if i == 1 then return { name = "Battle Shout", icon = 132333, applications = 0, duration = 120,
    expirationTime = 200, sourceUnit = "player", spellId = 6673, points = {} } end
end
C_Container = C_Container or {}
C_Container.GetContainerItemInfo = function() return { iconFileID = 1, stackCount = 5, isLocked = false, quality = 2,
  hyperlink = "|Hitem:915|h[Red Silk Bandana]|h", itemID = 915, isBound = true } end
C_PartyInfo = C_PartyInfo or {}
C_PartyInfo.InviteUnit = function(name) __invited = name end
__LOCK = false
C_ChatInfo.InChatMessagingLockdown = function() return __LOCK == true end
"""


def forever(name="Alice", **kw):
    return solo(name, preload_lua=FOREVER, **kw)


@case
def test_tbc_client_untouched():
    w, c = solo()
    assert c.eval("return ns.Compat.combatLog") is True
    # (the mock is a TBC Anniversary client: it already lacks a few old names, e.g. GetItemInfo; nothing it has is
    # replaced)
    shimmed = c.eval_py("return ns.Compat.shimmed") or []
    for n in ("GetSpellInfo", "GetSpellCooldown", "UnitBuff", "InviteUnit"):
        assert n not in shimmed, (n, shimmed)
    assert c.eval("return GetSpellInfo == ns.Compat.__none") is False
    no_errors(w)


@case
def test_forever_shims_old_return_order():
    w, c = forever()
    assert c.eval("return ns.Compat.isForever") is True
    shimmed = c.eval_py("return ns.Compat.shimmed")
    shimmed = list(shimmed.values()) if isinstance(shimmed, dict) else list(shimmed)
    for n in ("GetSpellInfo", "GetSpellCooldown", "UnitBuff", "GetContainerItemInfo", "InviteUnit"):
        assert n in shimmed, (n, shimmed)
    r = c.eval_py("return { GetSpellInfo(133) }")
    r = [r.get(i) for i in range(1, 8)] if isinstance(r, dict) else r
    assert r[0] == "Fireball" and r[1] is None and r[2] == 135812 and r[3] == 3500 and r[6] == 133, r
    assert c.eval("return select('#', GetSpellInfo(999))") == 0
    cd = c.eval_py("return { GetSpellCooldown(133) }")
    assert cd[0] == 10 and cd[1] == 1.5 and cd[2] == 1, cd
    assert c.eval("return (UnitBuff('player', 1))") == "Battle Shout"
    assert c.eval("UnitBuff('player', 1, 'PLAYER'); return __lastFilter") == "HELPFUL|PLAYER"
    assert c.eval("return (select(10, GetContainerItemInfo(0, 1)))") == 915
    c.eval("InviteUnit('Bob')")
    assert c.eval("return __invited") == "Bob"
    no_errors(w)


@case
def test_forever_never_registers_combat_log():
    w, c = forever()
    assert c.eval("return ns.Compat:CanUseCombatLog()") is False
    ok = c.eval("return ns:RegisterEvent('COMBAT_LOG_EVENT_UNFILTERED', function() end)")
    assert ok is False
    # nothing in the addon got the event registered on any frame (Blizzard's popup would show)
    hit = c.eval("""
      for _, f in ipairs(__MOCK.allFrames or {}) do
        if f.IsEventRegistered and f:IsEventRegistered('COMBAT_LOG_EVENT_UNFILTERED') then return true end
      end
      return false""")
    assert not hit
    no_errors(w)


def two_forever():
    w = World()
    a = Client(w, "Alice", guild_rank=0, preload_lua=FOREVER)
    b = Client(w, "Bob", guild_rank=3, preload_lua=FOREVER)
    a.load_addon()
    b.load_addon()
    w.tick(3)
    return w, a, b


def sent_by(w, who, since, prefix="CDLc"):
    return [e for e in w.addon_log[since:] if e["sender"].startswith(who) and e["prefix"] == prefix]


@case
def test_messages_wait_out_a_boss_pull():
    w, a, b = two_forever()
    n0 = len(w.addon_log)
    a.eval("__LOCK = true")
    assert a.eval("return ns.Comm:Send({ t = 'ZZTEST', n = 1 }, 'GUILD')") is True
    assert a.eval("return ns.Comm:Send({ t = 'ZZTEST', n = 2 }, 'GUILD')") is True
    w.tick(3)
    assert sent_by(w, "Alice", n0) == [], "nothing may leave during the lockdown"
    held = a.eval("return ns.Comm:GetLockHeldCount()")
    assert held >= 2, held          # ours, plus any sync traffic the addon sent meanwhile
    a.eval("__LOCK = false")
    w.tick(2)
    out = sent_by(w, "Alice", n0)
    assert len(out) >= 2, out
    assert len({e["time"] for e in out[:2]}) == 1, "held messages leave together when the lockdown ends"
    assert a.eval("return ns.Comm:GetLockHeldCount()") == 0
    assert a.eval("return ns.Comm.stats.lockFlushed") == held
    no_errors(w)


@case
def test_live_traffic_dropped_not_held():
    w, a, b = two_forever()
    n0 = len(w.addon_log)
    a.eval("__LOCK = true")
    a.eval("ns.Comm:Send({ t = 'ZZWALK' }, 'GUILD', nil, 'walk')")
    assert a.eval("return ns.Comm:GetLockHeldCount()") == 0
    assert a.eval("return ns.Comm.stats.lockDropped") == 1
    a.eval("__LOCK = false")
    w.tick(2)
    assert sent_by(w, "Alice", n0, "CDLw") == []
    no_errors(w)


@case
def test_flush_on_encounter_end_event():
    w, a, b = two_forever()
    n0 = len(w.addon_log)
    a.eval("__LOCK = true")
    a.eval("ns.Comm:Send({ t = 'ZZTEST' }, 'GUILD')")
    a.eval("__LOCK = false")
    a.fire("ENCOUNTER_END", 2745, "Mr. Smite", 1, 5, 1)
    w.tick(0.3)
    assert len(sent_by(w, "Alice", n0)) == 1
    no_errors(w)


if __name__ == "__main__":
    run_all()
