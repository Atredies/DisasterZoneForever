"""Raid-night helpers of the go-live suites (dev/tests/golive): a guild raid formed from sign-ups on WoW Forever, a
boss pull under Forever's lockdowns, and loot rolled, awarded and handed out through master loot. Not a test file:
test_golive_raid_night.py, test_golive_load.py and test_golive_resilience.py use it."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl_common import (no_errors, new_world, roster, make_clients, by_name, key, login_staggered,  # noqa: E402,F401
                       quiet, online, wire_stats, fmt_stats, note, stopwatch, gm_pick, strip_codes, throttled,
                       lockdown_refused, comm_stats, REALM)

ONY_NPC, ONY_GUID = 10184, "Creature-0-1-2-3-10184-000ABC"
HYJAL_BOSS_GUID = "Creature-0-1-2-3-17767-000DEF"
HELM_OF_WRATH = 16963       # (the duplicate on the Onyxia night)
NETHERWIND_CROWN = 16914
SAPPHIRON_DRAPE = 17078
RING_OF_BINDING = 18813
CORNERSTONE = 17067
ONY_DROPS = [HELM_OF_WRATH, HELM_OF_WRATH, NETHERWIND_CROWN, SAPPHIRON_DRAPE, RING_OF_BINDING]
# Hyjal's loot is not in the data before 9 Dec 2026: the reserve night uses classic items the client knows by id
HYJAL_DUP = CORNERSTONE
HYJAL_DROPS = [CORNERSTONE, CORNERSTONE, RING_OF_BINDING]
ITEMS = {HELM_OF_WRATH: ("Helm of Wrath", "INVTYPE_HEAD", 4, 4),
         NETHERWIND_CROWN: ("Netherwind Crown", "INVTYPE_HEAD", 4, 1),
         SAPPHIRON_DRAPE: ("Sapphiron Drape", "INVTYPE_CLOAK", 4, 1),
         RING_OF_BINDING: ("Ring of Binding", "INVTYPE_FINGER", 4, 0),
         CORNERSTONE: ("Ancient Cornerstone Grimoire", "INVTYPE_TRINKET", 4, 0)}
COUNCIL = ("Arakis War", "Missy Badshot", "Aurel Namahs")
LEADER = "Blu Skydagger"

PROBE = r"""
__GL = __GL or { got = {} }
ns.Comm:Register("ZZPULL", function(sender, msg) __GL.got[#__GL.got + 1] = { from = sender, n = msg.n } end)
local orig = GiveMasterLoot
__GL.gives = {}
GiveMasterLoot = function(slot, idx)
  __GL.gives[#__GL.gives + 1] = { slot = slot, name = GetMasterLootCandidate(slot, idx), link = GetLootSlotLink(slot) }
  return orig(slot, idx)
end
"""


def define_items(w):
    for iid, (name, loc, q, sub) in ITEMS.items():
        w.define_item(iid, name, quality=q, equip_loc=loc, class_id=4, subclass_id=sub, ilvl=76, min_level=60)


# ---------------------------------------------------------------------------------------------------------------------
# the night up to the pull
# ---------------------------------------------------------------------------------------------------------------------
def form_raid(size, raid_key, inst, seed=3):
    """A guild of `size`, all online on Forever: the raid leader plans the raid, everyone signs up, Invite & sort forms
    it, the session starts, master loot on the leader, everyone zones in. Returns a dict."""
    sw = stopwatch()
    w = new_world()
    w.auto_session = False
    cs = make_clients(w, roster(size - 4))
    by = by_name(cs)
    gm, missy, blu = by["Arakis War"], by["Missy Badshot"], by[LEADER]
    gm.login()
    w.tick(3)
    login_staggered(w, cs[1:], 90, seed=seed)
    quiet(w, idle=15)
    define_items(w)
    gm_pick(w, gm, ["Missy Badshot", "Aurel Namahs"], realm=REALM)
    res = missy.eval_py("local ok, e = ns.Guild:SetRaidLeaders(...); return { ok = ok, e = e }", [key(LEADER)])
    assert res["ok"] is True, res
    quiet(w, idle=5)
    t = blu.eval("return GetServerTime() + 900")
    res = blu.eval_py("local f = ...; local ok, r = ns.RaidPlan:CreateRaid(f); return { ok = ok, r = r }",
                      {"i": raid_key, "t": t, "ml": 60})
    assert res["ok"] is True, res
    occ = res["r"]
    quiet(w, idle=5)
    for c in cs:
        if c is blu:
            continue
        r = c.eval_py("local o = ...; local ok, e = ns.RaidPlan:SignUp(o, 'A'); return { ok = ok, e = e }", occ)
        assert r["ok"] is True, (c.name, r)
        w.tick(0.3, 0.1)
    quiet(w, idle=8)
    signed = blu.eval("local n = 0 for _ in pairs(ns.RaidPlan:GetSignups(...)) do n = n + 1 end return n", occ)
    assert signed == size - 1, signed
    # the raid from the sign-ups: everyone in a group of five, in sign-up order
    plan = {key(c.name): i // 5 + 1 for i, c in enumerate(cs)}
    res = blu.eval_py("local o, p, n = ...; local ok, e = ns.RaidInvite:Start(o, p, n); return { ok = ok, e = e }",
                      occ, plan, inst["name"])
    assert res["ok"] is True, res
    for _ in range(60):
        w.tick(1, 0.25)
        if w.group and w.group["kind"] == "raid" and len(w.group["members"]) == size:
            break
    assert w.group and w.group["kind"] == "raid" and len(w.group["members"]) == size, w.group and len(w.group["members"])
    converted = blu.eval("return __MOCK.forever_converted")
    w.tick(3)
    status = blu.eval_py("local s = ns.RaidInvite:GetStatus(); return s and { planned = s.planned, inRaid = s.inRaid,"
                         " sorted = s.sorted } or nil")
    for c in cs:
        c.eval(PROBE)
    res = blu.eval_py("local ok, e = ns.GroupRules:SetSession(true, nil, { loot = true, rolls = true, lock = false });"
                      " return { ok = ok, e = e }")
    assert res["ok"] is True, res
    w.set_master_looter(blu)
    w.tick(3)
    w.enter_instance(name=inst["name"], instance_id=inst["id"], max_players=size, difficulty_id=9)
    w.tick(3)
    return {"w": w, "cs": cs, "by": by, "occ": occ, "converted": converted, "status": status, "size": size,
            "sw": sw}


def session_info(c):
    return c.eval_py("local i = ns.SessionInfo:Get(); if not i then return nil end"
                     " return { raidKey = i.raidKey, total = i.total, kills = i.kills }")


# ---------------------------------------------------------------------------------------------------------------------
# the pull
# ---------------------------------------------------------------------------------------------------------------------
def fight_events(c):
    token = {"WARRIOR": "RAGE", "ROGUE": "ENERGY"}.get(c.class_file, "MANA")
    for _ in range(2):
        c._fire("UNIT_POWER_FREQUENT", "player", token)
        c._fire("UNIT_HEALTH", "player")
        c._fire("UNIT_HEALTH", "target")
        c._fire("UNIT_AURA", "player")
        c._fire("UNIT_SPELLCAST_SUCCEEDED", "player", "Cast-1", 78)
        c._fire("SPELL_UPDATE_COOLDOWN")
    c._fire("PLAYER_TARGET_CHANGED")
    c._fire("RAID_TARGET_UPDATE")


SECRETS_LUA = r"""
local out = {}
out.health = issecretvalue(UnitHealth('player'))
out.power = issecretvalue(UnitPower('player'))
local cd = C_Spell.GetSpellCooldown(78)
out.cooldown = cd ~= nil and issecretvalue(cd.duration)
out.mark = issecretvalue(GetRaidTargetIndex('target'))
out.npcName = issecretvalue((UnitName('target')))
out.npcGuid = issecretvalue(UnitGUID('target'))
return out
"""


def pull(n, boss_id, boss_name, guid, npc_id, seconds=20):
    """A pull: ENCOUNTER_START on every raider (the mock switches Encounter + Chat on), a fight of `seconds` with
    combat events, guild and raid chat (secret payloads), addon traffic from many raiders (held), then a kill."""
    w, cs = n["w"], n["cs"]
    group = [c for c in cs if c.loaded]
    npc = w.spawn_npc(npc_id, boss_name)
    for c in group:
        c.target_npc(npc)
    w.set_raid_target(n["by"][LEADER], npc, 8)
    mark = len(w.addon_log)
    sent_during = []
    for c in group:
        c._fire("ENCOUNTER_START", boss_id, boss_name, 9, n["size"])
    for c in group:
        c.set_combat(True)
    secrets = n["by"]["Megumin Chan"].eval_py(SECRETS_LUA)
    for i, c in enumerate(group):
        # addon traffic during the pull: every fifth raider sends something (it waits for the end of the pull)
        if i % 5 == 0:
            assert c.eval("return ns.Comm:Send({ t = 'ZZPULL', n = ... }, 'RAID')", i) is True
            sent_during.append(i)
    lead_hold = n["by"][LEADER].eval("return ns.Comm:GetLockHeldCount()")
    t0 = w.now
    while w.now - t0 < seconds:
        for c in group:
            fight_events(c)
        # guild chat, a raid line, a whisper and a guildmate logging on, while chat is locked down
        for c in group[:10]:
            c._fire("CHAT_MSG_GUILD", "pull timer?", key("Garrick Underbough"), "", "", "Garrick Underbough", "", 0, 0,
                    "", 0, 77, "Player-1-00000001", 0, False, False, False, False)
            c._fire("CHAT_MSG_RAID", "dps!", key(LEADER), "", "", LEADER, "", 0, 0, "", 0, 78, "Player-1-00000002", 0,
                    False, False, False, False)
            c._fire("CHAT_MSG_WHISPER", "inv pls", key("Orla Ashford"), "", "", "Orla Ashford", "", 0, 0, "", 0, 79,
                    "Player-1-00000003", 0, False, False, False, False)
            c._fire("CHAT_MSG_SYSTEM", "|Hplayer:Orla Ashford|h[Orla Ashford]|h has come online.")
        w.tick(1, 0.1)
    on_wire = [e for e in w.addon_log[mark:] if e["sender"] in {c.full_name for c in group}]
    secret_fired = sum(c.eval("return __MOCK.chat_secret_fired or 0") for c in group)
    for c in group:
        c._fire("ENCOUNTER_END", boss_id, boss_name, 9, n["size"], 1)
        c._fire("BOSS_KILL", boss_id, boss_name)
    for c in group:
        c.set_combat(False)
    w.tick(1)
    quiet(w, idle=8)
    return {"on_wire": on_wire, "sent": sent_during, "secrets": secrets, "lead_hold": lead_hold,
            "secret_fired": secret_fired, "refused": sum(lockdown_refused(c) for c in group)}


# ---------------------------------------------------------------------------------------------------------------------
# loot
# ---------------------------------------------------------------------------------------------------------------------
def active(c):
    return c.eval_py("local s = ns.Roll:GetActive(); return s and { id = s.id, i = s.i, c = s.c, state = s.state }")


def results(c, sid):
    return c.eval_py(r"""
        local out = {}
        for i, r in ipairs(ns.Roll:GetResults(...)) do out[i] = { key = r.key, roll = r.roll, suggested = r.suggested } end
        return out""", sid) or []


def run_loot(n, drops, source_guid, winners_for=None, roll_names=None, seconds=8):
    """The master looter opens the loot window and rolls every drop; raiders /roll; the leader ends each roll and
    awards it (the suggested winner) through master loot. Returns [(item, copy, winner key)]."""
    w, by = n["w"], n["by"]
    ml = by[LEADER]
    ml.open_loot([(i, 4) for i in drops], source_guid=source_guid)
    w.tick(2)
    ml.eval("ns.DropPanel:RollAll()")
    w.tick(1)
    awarded, seen = [], set()
    names = roll_names or [c.name for c in n["cs"]]
    for _ in range(len(drops) * 3):
        s = None
        for _ in range(int(seconds * 8)):
            s = active(ml)
            if s and s["id"] not in seen:
                break
            w.tick(0.25)
        if not s or s["id"] in seen:
            break
        seen.add(s["id"])
        w.tick(1)
        rollers = (winners_for or {}).get((s["i"], s["c"])) or names[(len(seen) * 3) % len(names):][:6]
        for j, nm in enumerate(rollers):
            w.player_roll(nm, 90 - j * 7)
        w.tick(2)
        ml.eval("ns.Roll:End(...)", s["id"])
        w.tick(1)
        res = results(ml, s["id"])
        pick = next((r for r in res if r.get("suggested")), res[0] if res else None)
        assert pick, (s, res)
        ml.eval("ns.DropPanel:AwardRoll(...)", s["id"], pick["key"])
        w.tick(0.3)
        ml.accept_popup("DISASTERZONE_GIVE_ITEM")
        w.tick(3)
        awarded.append((s["i"], s["c"], pick["key"]))
    quiet(w, idle=8)
    return awarded


def ledger(c):
    return c.eval_py(r"""
        local out = {}
        for i, e in ipairs(ns.Ledger:GetEntries({})) do out[i] = { i = e.i, w = e.w, s = e.s } end
        return out""") or []
