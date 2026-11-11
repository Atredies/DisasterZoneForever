"""Go-live readiness, scenario 2: raid nights on WoW Forever with every raider on DisasterZone 0.1.0.

  * Onyxia's Lair, 40 players, a loot-council night: the raid leader plans the raid, 39 guildmates sign up, Invite &
    sort forms the raid from the sign-ups (party -> raid through Forever's C_PartyInfo.ConvertToRaid), the raid
    session starts (the session crest finds Onyxia), master loot. The pull: Forever's addon-message lockdown and chat
    lockdown (CHAT_MSG_* payloads secret) for the whole encounter, secret unit values in combat (health, power,
    cooldowns, raid marks, the boss's name and GUID inside the instance). Messages sent during the pull arrive after
    it. Then the loot window with five drops, two of them identical (two Helms of Wrath): every drop rolled, awarded
    by the council and handed out through master loot; the loot log shows every award on every council client (the
    duplicate twice); the raid log records who attended.
  * Hyjal Summit, 20 players, a soft-reserve night: reserves opened, members reserve (two of them the same item),
    the boss drops that item twice: each copy goes to one reserver, through master loot, logged on the council.

Every client: no Lua error, nothing refused by the lockdown (AddOnMessageLockdown), nothing lost.

Run: luaenv/bin/python tests/golive/test_golive_raid_night.py [-k name]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl_common import case, run_all, no_errors, note, key, quiet, wire_stats, fmt_stats  # noqa: E402
from gl_raid import (form_raid, session_info, pull, run_loot, ledger, ONY_GUID, ONY_NPC, ONY_DROPS,  # noqa: E402
                     HELM_OF_WRATH, HYJAL_BOSS_GUID, HYJAL_DROPS, HYJAL_DUP, RING_OF_BINDING, ITEMS, COUNCIL, LEADER)


# ---------------------------------------------------------------------------------------------------------------------
# Onyxia, 40, loot council
# ---------------------------------------------------------------------------------------------------------------------
_ONY = {}


def onyxia():
    if _ONY:
        return _ONY
    n = form_raid(40, "ony", {"name": "Onyxia's Lair", "id": 249})
    n["crest"] = session_info(n["by"]["Megumin Chan"])
    n["pull"] = pull(n, 1084, "Onyxia", ONY_GUID, ONY_NPC)
    n["crest_after"] = session_info(n["by"]["Megumin Chan"])
    mark = len(n["w"].addon_log)
    n["awarded"] = run_loot(n, ONY_DROPS, ONY_GUID)
    n["loot_traffic"] = wire_stats(n["w"], mark)
    n["wall"] = n["sw"]()
    _ONY.update(n)
    note("Onyxia 40: %.0f game-seconds, %.1f s wall; awards %s" % (n["w"].now, n["wall"],
                                                                  [(i, c, k.split("-")[0]) for i, c, k in n["awarded"]]))
    note("loot traffic: " + fmt_stats(n["loot_traffic"]))
    return _ONY


@case
def test_ony_raid_formed_from_sign_ups_through_the_forever_convert():
    n = onyxia()
    assert n["converted"] >= 1, n["converted"]        # C_PartyInfo.ConvertToRaid (Forever has no global)
    assert n["status"] == {"planned": 40, "inRaid": 40, "sorted": 40}, n["status"]
    no_errors(n["w"])


@case
def test_ony_crest_shows_onyxia_and_counts_the_kill():
    n = onyxia()
    assert n["crest"] and n["crest"]["raidKey"] == "Onyxia" and n["crest"]["total"] == 1, n["crest"]
    assert n["crest_after"]["kills"] == 1, n["crest_after"]
    no_errors(n["w"])


@case
def test_ony_pull_holds_messages_and_delivers_them_after():
    n = onyxia()
    p = n["pull"]
    assert p["on_wire"] == [], [(e["sender"], e["prefix"]) for e in p["on_wire"]][:10]
    assert p["refused"] == 0, p["refused"]                  # nothing refused by AddOnMessageLockdown
    assert p["secret_fired"] > 0, p                         # chat payloads arrived secret
    assert all(p["secrets"].values()), p["secrets"]         # secret values in combat were really present
    # every message sent during the pull reached every other raider afterwards
    for c in n["cs"]:
        got = sorted(x["n"] for x in (c.eval_py("return __GL.got") or []))
        want = sorted(i for i in p["sent"] if n["cs"][i] is not c)
        assert got == want, (c.name, got, want)
    no_errors(n["w"])


@case
def test_ony_every_drop_awarded_and_handed_out_through_master_loot():
    n = onyxia()
    items = sorted(i for i, _, _ in n["awarded"])
    assert items == sorted(ONY_DROPS), n["awarded"]
    copies = sorted(c for i, c, _ in n["awarded"] if i == HELM_OF_WRATH)
    assert copies == [1, 2], n["awarded"]
    gives = n["by"][LEADER].eval_py("return __GL.gives") or []
    assert len(gives) == len(ONY_DROPS), gives
    no_errors(n["w"])


@case
def test_ony_loot_log_on_every_council_client():
    n = onyxia()
    want = sorted((i, k) for i, _, k in n["awarded"])
    for name in COUNCIL + (LEADER,):
        got = sorted((e["i"], e["w"]) for e in ledger(n["by"][name]) if e["i"] in ITEMS)
        assert got == want, (name, got, want)
    no_errors(n["w"])


@case
def test_ony_attendance_recorded():
    n = onyxia()
    for name in COUNCIL + (LEADER,):
        # (att: who was there; ex: who the planned raid expected, its sign-ups; pl: the planned raid)
        rec = n["by"][name].eval_py("local r = ns.RaidLog:GetOpenRecord(); if not r then return nil end"
                                   " local m, x = 0, 0 for _ in pairs(r.att or {}) do m = m + 1 end"
                                   " for _ in pairs(r.ex or {}) do x = x + 1 end"
                                   " local b = 0 for _ in pairs(r.bosses or {}) do b = b + 1 end"
                                   " return { m = m, x = x, pl = r.pl, bosses = b }")
        note("raid log on %s: %r" % (name, rec))
        assert rec is not None and rec["m"] == 40 and rec["x"] == 39 and rec["pl"] == n["occ"], (name, rec)
        assert rec["bosses"] == 1, (name, rec)                 # the Onyxia kill
    no_errors(n["w"])


# ---------------------------------------------------------------------------------------------------------------------
# Hyjal, 20, soft reserves
# ---------------------------------------------------------------------------------------------------------------------
_HYJ = {}
RESERVERS = ("Megumin Chan", "Tobin Greyhill")


def hyjal():
    if _HYJ:
        return _HYJ
    n = form_raid(20, "hyjal", {"name": "Hyjal Summit", "id": 9101}, seed=5)
    w, by = n["w"], n["by"]
    blu = by[LEADER]
    res = blu.eval_py("local ok, e = ns.GroupRules:SetSessionFeatures(...); return { ok = ok, e = e }",
                      {"loot": True, "rolls": True, "lock": False, "reserve": True})
    assert res["ok"] is True, res
    w.tick(3)
    res = blu.eval_py("local ok, e = ns.Reserves:Open(...); return { ok = ok, e = e }",
                      {"n": 1, "hr": [], "rk": "HyjalForever"})
    assert res["ok"] is True, res
    quiet(w, idle=5)
    n["reserve_answers"] = {}
    for nm in RESERVERS:
        n["reserve_answers"][nm] = by[nm].eval_py("return { ns.Reserves:Reserve(...) }", HYJAL_DUP)
    n["reserve_answers"]["Elra Northwind"] = by["Elra Northwind"].eval_py("return { ns.Reserves:Reserve(...) }",
                                                                            RING_OF_BINDING)
    quiet(w, idle=5)
    n["reservers"] = sorted(blu.eval_py("return ns.Reserves:Reservers(...)", HYJAL_DUP) or [])
    n["pull"] = pull(n, 3101, "Bandalar", HYJAL_BOSS_GUID, 17767, seconds=10)
    n["awarded"] = run_loot(n, HYJAL_DROPS, HYJAL_BOSS_GUID)
    _HYJ.update(n)
    note("Hyjal 20: awards %s" % [(i, c, k.split("-")[0]) for i, c, k in n["awarded"]])
    return _HYJ


@case
def test_hyjal_reserves_reach_the_host():
    n = hyjal()
    assert n["reservers"] == sorted(key(x) for x in RESERVERS), (n["reservers"], n["reserve_answers"])
    no_errors(n["w"])


@case
def test_hyjal_two_identical_drops_go_one_to_each_reserver():
    n = hyjal()
    dup = sorted(k for i, _, k in n["awarded"] if i == HYJAL_DUP)
    assert dup == sorted(key(x) for x in RESERVERS), n["awarded"]
    ring = [k for i, _, k in n["awarded"] if i == RING_OF_BINDING]
    assert ring == [key("Elra Northwind")], n["awarded"]
    for name in COUNCIL + (LEADER,):
        got = sorted((e["i"], e["w"]) for e in ledger(n["by"][name]) if e["i"] in ITEMS)
        assert got == sorted((i, k) for i, _, k in n["awarded"]), (name, got)
    no_errors(n["w"])


@case
def test_hyjal_pull_no_message_refused():
    n = hyjal()
    assert n["pull"]["on_wire"] == [] and n["pull"]["refused"] == 0, n["pull"]
    no_errors(n["w"])


if __name__ == "__main__":
    run_all()
