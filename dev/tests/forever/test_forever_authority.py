"""Authority holes (owner decisions 2026-11-09, before the guild's first multi-player test): every case is a guild
member sending a hand-made message, and every other client refusing it.

  1. GM rules: an officer's RLL that names the GM as author (lrb / arb / dcb / rcb) no longer changes the loot,
     attendance, Discord or recruitment rules; a GMR is taken only from the Guild Master (rank 0) as its sender.
  2. Reserves: a raid assistant's RVS no longer replaces the raid's soft-reserve list (only the authority, or whoever
     holds the list I have).
  3. Raid plans: a raid record passed on (RPG) by a plain member, "by" a raid leader, no longer shows on a client that
     never had it; a raid planner's copy does.
  4. Officers: the GM picks the officer ranks (default 0-1), the pick syncs from the GM only, and a rank the addon
     can't read (secret on Forever) is no officer.
  5. Developer: the owner's character "Arakis War" on the guild's realm only, never the old name and never the same
     name on another realm.

Run: luaenv/bin/python tests/forever/test_forever_authority.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))
sys.path.insert(0, os.path.join(TESTS, "raidplan"))
sys.path.insert(0, os.path.join(TESTS, "reserves"))

from _common import case, run_all, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"
REALM_KEY = "CAMWOWEU4Realm4PvP"
GM = "Arakis War"


def key(name):
    return "%s-%s" % (name, REALM_KEY)


def guild():
    """The guild on Forever: Arakis War = GM (and the developer), Missy = officer (rank 1), Aurel = rank 2,
    Nala = rank 3."""
    w = World(realm=REALM)
    cs = {}
    for name, cls, rank in ((GM, "WARRIOR", 0), ("Missy Badshot", "HUNTER", 1), ("Aurel Namahs", "MAGE", 2),
                            ("Nala Brook", "PRIEST", 3)):
        c = Client(w, name, class_file=cls, guild_rank=rank, level=60, forever=True)
        c.load_addon()
        cs[name.split()[0]] = c
    w.tick(5)
    return w, cs


def rules(c):
    return c.eval_py("return { lr = ns.Guild:GetLootRules(), ar = ns.Guild:GetAttendanceRules(), "
                     "dc = ns.Guild:GetDiscord().host, rc = ns.Guild:GetRecruitRules().uc }")


# ------------------------------------------------------------------------------------------------------------------
# 1. GM rules
# ------------------------------------------------------------------------------------------------------------------
@case
def test_an_officer_cannot_forge_the_gms_rules():
    w, c = guild()
    gm, missy, nala = c["Arakis"], c["Missy"], c["Nala"]
    before = rules(nala)
    # an officer's raid leaders list (legitimate: officers keep it) carrying "the GM's" rules
    missy.eval("local me, gm = ...; ns.Comm:Send({ t = 'RLL', rev = GetServerTime() + 5, m = { me }, by = me, "
               "ar = { o = 1, d = 1 }, arb = gm, lr = { f = 90, s = 'p', l = 'r', w = 'd', y = 'a', o = 0, q = 's' }, "
               "lrb = gm, dc = { h = me }, dcb = gm, rc = { uc = 29 }, rcb = gm }, 'GUILD', nil, 'ctrl')",
               key("Missy Badshot"), key(GM))
    w.tick(3)
    assert nala.eval_py("return ns.Guild:GetRaidLeadersInfo().members") == [key("Missy Badshot")]
    assert rules(nala) == before, rules(nala)
    # the GM's own record, sent by an officer (or a member): refused too
    for forger in (missy, nala):
        forger.eval("ns.Comm:Send({ t = 'GMR', v = GetServerTime() + 30, ar = { o = 2, d = 2 }, dc = { h = ... }, "
                    "ok = { 0, 1, 2, 3 } }, 'GUILD', nil, 'ctrl')", key(forger.name))
        w.tick(3)
        assert rules(nala) == before, rules(nala)
        assert nala.eval("return ns.Guild:IsOfficer(...)", key("Nala Brook")) is False
    assert missy.eval("return (ns.Guild:SetLootRules({ f = 50, s = 'r', l = 'l', w = 'r', y = 'n' }))") is False
    # the GM's change reaches everyone, and an officer's later list keeps it
    assert gm.eval("return (ns.Guild:SetAttendanceRules(12, 20))") is True
    assert gm.eval("return (ns.Guild:SetDiscord({ host = ... }))", key("Aurel Namahs")) is True
    w.tick(3)
    assert nala.eval_py("return ns.Guild:GetAttendanceRules()") == {"o": 12, "d": 20}
    assert nala.eval("return ns.Guild:GetDiscord().host") == key("Aurel Namahs")
    missy.eval("local nala, me, gm = ...; ns.Comm:Send({ t = 'RLL', rev = GetServerTime() + 50, m = { nala }, by = me, "
               "dc = { h = me }, dcb = gm }, 'GUILD', nil, 'ctrl')", key("Nala Brook"), key("Missy Badshot"), key(GM))
    w.tick(3)
    assert nala.eval("return ns.Guild:GetDiscord().host") == key("Aurel Namahs")
    assert nala.eval("return ns.Guild:IsDiscordHost(...)", key("Missy Badshot")) is False
    no_errors(w)


@case
def test_a_member_who_missed_the_gm_gets_the_rules_from_the_gm_only():
    w, c = guild()
    gm, missy, nala = c["Arakis"], c["Missy"], c["Nala"]
    nala.logout()
    assert gm.eval("return (ns.Guild:SetAttendanceRules(7, 9))") is True
    w.tick(3)
    gm.logout()
    nala.login()
    w.tick(60)
    # only the officer was online: the GM's rules can't be vouched for by anybody else
    assert nala.eval_py("return ns.Guild:GetAttendanceRules()") == {"o": 5, "d": 10}
    gm.login()
    w.tick(60)
    assert nala.eval_py("return ns.Guild:GetAttendanceRules()") == {"o": 7, "d": 9}
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 4. Officer ranks
# ------------------------------------------------------------------------------------------------------------------
@case
def test_the_gm_picks_the_officer_ranks_and_only_the_gm():
    w, c = guild()
    gm, missy, aurel, nala = c["Arakis"], c["Missy"], c["Aurel"], c["Nala"]

    def officers(cl):
        return [n for n in (GM, "Missy Badshot", "Aurel Namahs", "Nala Brook")
                if cl.eval("return ns.Guild:IsOfficer(..., true)", key(n))]

    # the default: ranks 0 and 1
    for cl in c.values():
        assert officers(cl) == [GM, "Missy Badshot"], (cl.name, officers(cl))
    assert nala.eval_py("return { ns.Guild:GetOfficerRanks() }") == [[0, 1], False]
    # an officer (or anyone but the GM) can't pick them
    res = missy.eval_py("local ok, e = ns.Guild:SetOfficerRanks({ 0, 1, 3 }); return { ok = ok, e = e }")
    assert res["ok"] is False, res
    missy.eval("ns.Comm:Send({ t = 'GMR', v = GetServerTime() + 30, ok = { 0, 1, 3 } }, 'GUILD', nil, 'ctrl')")
    w.tick(3)
    assert officers(aurel) == [GM, "Missy Badshot"], officers(aurel)
    # the GM: rank 2 instead of rank 1, for everyone
    assert gm.eval("return (ns.Guild:SetOfficerRanks({ [0] = true, [2] = true }))") is True
    w.tick(3)
    for cl in c.values():
        assert officers(cl) == [GM, "Aurel Namahs"], (cl.name, officers(cl))
    assert nala.eval_py("return { ns.Guild:GetOfficerRanks() }") == [[0, 2], True]
    ranks = nala.eval_py("return ns.Guild:GetRanks()")
    assert [r["index"] for r in ranks if r["officer"]] == [0, 2], ranks
    # the old officer lost the rights that come with it (the raid leaders list)
    assert missy.eval("return ns.Guild:CanEditRaidLeaders()") is False
    assert aurel.eval("return ns.Guild:CanEditRaidLeaders()") is True
    no_errors(w)


@case
def test_the_officers_card_lets_the_gm_tick_ranks_and_shows_others_read_only():
    w, c = guild()
    gm, nala = c["Arakis"], c["Nala"]

    def rows(cl):
        cl.slash("/dz settings")
        w.tick(0.5)
        cl.eval("ns.SettingsUI:SelectSection('officers')")
        w.tick(0.5)
        return cl.eval_py("local out = {}; for _, r in ipairs(ns.SettingsUI.ofc.rows) do if r.rank and r:IsShown() then "
                          "out[#out + 1] = { r.rank, r.title:GetText(), r.readOnly or false } end end; return out")

    got = rows(gm)
    # one row per rank the guild has below the GM, under the guild's own rank names
    names = gm.eval_py("local o = {}; for i = 2, GuildControlGetNumRanks() do o[#o + 1] = GuildControlGetRankName(i) end; "
                       "return o")
    assert [r[0] for r in got] == list(range(1, len(names) + 1)) and [r[1] for r in got] == names, got
    assert not any(r[2] for r in got), got
    assert all(r[2] for r in rows(nala)), rows(nala)
    # a click on the GM's rank 3 switch makes rank 3 officers for everyone
    gm.eval("for _, r in ipairs(ns.SettingsUI.ofc.rows) do if r.rank == 3 then r.control:Click() end end")
    w.tick(3)
    assert nala.eval("return ns.Guild:IsOfficer(..., true)", key("Nala Brook")) is True
    no_errors(w)


@case
def test_a_secret_guild_rank_is_no_officer():
    w, c = guild()
    nala = c["Nala"]
    assert nala.eval("return ns.Guild:IsOfficer(..., true)", key("Missy Badshot")) is True
    nala.eval("local base = GetGuildRosterInfo; GetGuildRosterInfo = function(i) local r = { base(i) }; "
              "r[3] = __MOCK.secret(r[3]); return unpack(r, 1, 17) end")
    nala.fire("GUILD_ROSTER_UPDATE", True)
    w.tick(70)
    assert nala.eval("return ns.Guild:IsOfficer(..., true)", key("Missy Badshot")) is False
    assert nala.eval("return ns.Guild:IsGM(...)", key(GM)) is False
    # the GM's record can't come from a sender whose rank I can't read
    c["Arakis"].eval("ns.Guild:SetAttendanceRules(3, 4)")
    w.tick(3)
    assert nala.eval_py("return ns.Guild:GetAttendanceRules()") == {"o": 5, "d": 10}
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 5. Developer
# ------------------------------------------------------------------------------------------------------------------
@case
def test_the_developer_is_arakis_war_on_the_guilds_realm_only():
    w, c = guild()
    gm, nala = c["Arakis"], c["Nala"]
    assert gm.eval("return ns.Feedback:AmIDev()") is True
    assert gm.eval("return ns.Perf:IsDev()") is True
    assert nala.eval("return ns.Feedback:IsDev(...)", key(GM)) is True
    assert nala.eval("return ns.Feedback:AmIDev()") is False
    for k in ("Arakis War-Thunderstrike", "Tsumil-" + REALM_KEY, "Tsumil-Thunderstrike", "Arakis-" + REALM_KEY):
        assert nala.eval("return ns.Feedback:IsDev(...)", k) is False, k
    # a dev number (feedback "n" record) "by" a made-up developer is not taken
    assert nala.eval("return ns.Feedback:IsStaff(...)", "Arakis War-Thunderstrike") is False
    # /dz role is the developer's only
    nala.slash("/dz role gm")
    assert nala.eval("return ns.db.debugRole") is None
    no_errors(w)


@case
def test_the_same_name_on_another_realm_is_not_the_developer():
    w = World(realm="Thunderstrike")
    c = Client(w, GM, class_file="WARRIOR", guild_rank=3, level=60, forever=True)
    other = Client(w, "Tsumil", class_file="WARRIOR", guild_rank=3, level=60)
    c.load_addon()
    other.load_addon()
    w.tick(3)
    assert c.eval("return ns.Util.PlayerKey()") == "Arakis War-Thunderstrike"
    for cl in (c, other):
        assert cl.eval("return ns.Feedback:AmIDev()") is False, cl.name
        assert cl.eval("return ns.Perf:IsDev()") is False, cl.name
        cl.slash("/dz role gm")
        assert cl.eval("return ns.db.debugRole") is None, cl.name
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 3. Raid plans: a relayed record new to me
# ------------------------------------------------------------------------------------------------------------------
@case
def test_a_relayed_raid_by_a_raid_leader_is_not_taken_from_a_plain_member():
    from rp_common import world as rp_world, create, now, DAY, K  # noqa: E402
    w, c = rp_world()
    bob, lee, sam = c["Bob"], c["Lee"], c["Sam"]           # Bob: council + raid leader; Lee, Sam: members
    occ = create(bob, i="kara", t=now(bob) + DAY, no="the real note")
    w.tick(3)

    def stored(cl):
        return cl.eval_py("local o = ...; local r = ns.db.raidplan and ns.db.raidplan[ns.Guild:GetGuildKey()]; "
                          "return r and r.E[o]", occ)

    assert stored(sam)["no"] == "the real note"
    # Lee loses the raid (a fresh install); Sam passes on a made-up newer version "by" Bob
    lee.eval("local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; r.E[...] = nil; r.OK = {}", occ)
    sam.eval("local o, to = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; local e = {}; "
             "for k, v in pairs(r.E[o]) do e[k] = v end; e.no = 'forged'; e.rev = e.rev + 1; "
             "ns.Comm:Send({ t = 'RPG', o = o, e = e }, 'WHISPER', to, 'data')", occ, K("Lee"))
    w.tick(1)
    assert stored(lee) is None, stored(lee)
    # Lee asks a raid planner (Bob) and takes Bob's copy
    w.tick(6)
    s = stored(lee)
    assert s and s["no"] == "the real note", s
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 2. Reserves
# ------------------------------------------------------------------------------------------------------------------
@case
def test_a_raid_assistant_cannot_replace_the_reserves():
    from rv_common import reserve_raid, open_reserves, key as rkey  # noqa: E402
    r = reserve_raid()
    open_reserves(r, n=1)
    w = r.w
    w.make_raid(list(r.c.values()), master_looter=r["Alice"], leader=r["Alice"], assistants=[r["Frank"]],
                extra_members=r.extra)
    w.tick(2)

    def host(cl):
        return cl.eval_py("local L = ns.Reserves:Get(); return L and { by = L.by, id = L.id }")

    assert host(r["Carol"])["by"] == rkey("Alice")
    r["Frank"].eval("ns.Comm:Send({ t = 'RVS', id = 'forged', by = ..., v = 99, at = GetServerTime(), rk = 'Karazhan', "
                    "n = 3, o = 1, h = {}, r = { [(...)] = '28766:d' } }, 'RAID', nil, 'ctrl')", rkey("Frank"))
    w.tick(2)
    for n in ("Bob", "Carol", "Gina"):
        h = host(r[n])
        assert h["by"] == rkey("Alice") and h["id"] != "forged", (n, h)
    # nor wipe it
    r["Frank"].eval("local L = ...; ns.Comm:Send({ t = 'RVS', id = L, x = true }, 'RAID', nil, 'ctrl')",
                    host(r["Carol"])["id"])
    w.tick(2)
    assert host(r["Carol"]) is not None
    w.assert_no_errors()


if __name__ == "__main__":
    run_all()
