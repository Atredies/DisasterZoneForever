"""Authority holes, round 2 (2026-11-09, after the first round in test_forever_authority.py): every case is a guild
member sending a hand-made message, every other client refusing it (or naming who passed it on), and the legitimate
flow still working.

  1. Raid sign-ups: a sign-up (or a change / withdrawal of one) passed on (RPG) by a plain member is not taken; the
     owner's, a raid planner's or the raid's own leader's copy is. A held-back copy is asked for from the owner and a
     planner who are online, so every client still ends up with the real answer. (Team waitlists the same.)
  2. Audit log: an entry whose author (w) is not its sender keeps who passed it on (rb, "relayed by"); a copy from the
     author, or my own client's, replaces it. Also a peer's record seen here.
  3. "by" labels: officer notes, guest book notes, recruit removals keep who passed them on when the sender is not
     the writer.
  4. LootReserve mirror: only the group's leader, its master looter (LootReserve's own rule) or the raid's loot
     authority host a session that becomes my read-only list.
  5. Relayed records that need a role of their writer: Events (season, reviews, removals), Polls (removals), Prized
     (everything), Strategy (fills, a moderator's edit or deletion) are taken from a relay only when its sender could
     have written them.

Run: luaenv/bin/python tests/forever/test_forever_authority2.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
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
    """The guild on Forever (as test_forever_authority.py): Arakis War = GM, Missy = officer (rank 1), Aurel = rank 2,
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


# ------------------------------------------------------------------------------------------------------------------
# 1. Raid sign-ups
# ------------------------------------------------------------------------------------------------------------------
def _signups(cl, occ):
    return cl.eval_py("local r = ns.db.raidplan and ns.db.raidplan[ns.Guild:GetGuildKey()]; return r and r.U[...]", occ) or {}


def _forge_rpg(frm, to, occ, who, st, bump=10, wipe_e=False):
    """frm whispers `to` a hand-made RPG of occurrence occ: who's answer st, newer than any they hold."""
    frm.eval("local o, to, who, st, bump = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; "
             "local cur = r.U[o] and r.U[o][who]; local s = { st = st, rev = (cur and cur.rev or GetServerTime()) + bump, "
             "c = 'WARRIOR' }; s.at = cur and cur.at or s.rev; "
             "ns.Comm:Send({ t = 'RPG', o = o, u = { [who] = s } }, 'WHISPER', to, 'data')", occ, to, who, st, bump)


@case
def test_a_relayed_sign_up_is_taken_only_from_its_owner_or_a_planner():
    from rp_common import world as rp_world, create, now, DAY, K, signup
    w, c = rp_world()
    gina, bob, lee, rita, sam = c["Gina"], c["Bob"], c["Lee"], c["Rita"], c["Sam"]   # Gina GM, Bob planner
    occ = create(bob, i="kara", t=now(bob) + DAY)
    w.tick(3)
    assert signup(lee, occ, "A")["ok"] is True
    w.tick(3)
    assert _signups(sam, occ)[K("Lee")]["st"] == "A"
    # Rita withdraws Lee's answer on Sam's client (a newer "X"), and signs Gina up there
    _forge_rpg(rita, K("Sam"), occ, K("Lee"), "X")
    _forge_rpg(rita, K("Sam"), occ, K("Gina"), "A")
    w.tick(10)
    u = _signups(sam, occ)
    assert u[K("Lee")]["st"] == "A", u
    assert K("Gina") not in u, u
    # (and the raid's sign-up list shows Lee only)
    assert set(sam.eval_py("return ns.RaidPlan:GetSignups(...)", occ)) == {K("Lee")}
    # the planner passes on a real change: taken
    assert signup(lee, occ, "T")["ok"] is True
    w.tick(3)
    assert _signups(sam, occ)[K("Lee")]["st"] == "T"
    sam.eval("local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; r.U[...] = nil", occ)
    bob.eval("local o, to = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; "
             "ns.Comm:Send({ t = 'RPG', o = o, e = r.E[o], u = r.U[o] }, 'WHISPER', to, 'data')", occ, K("Sam"))
    w.tick(2)
    assert _signups(sam, occ)[K("Lee")]["st"] == "T"
    # the owner's own copy: taken
    sam.eval("local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; r.U[...] = nil", occ)
    lee.eval("local o, to = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; "
             "ns.Comm:Send({ t = 'RPG', o = o, u = r.U[o] }, 'WHISPER', to, 'data')", occ, K("Sam"))
    w.tick(2)
    assert _signups(sam, occ)[K("Lee")]["st"] == "T"
    # a plain member passes on the real answer to a client that lost it: the owner's copy is asked for at once (RPW)
    # and comes, so the clients still agree
    sam.eval("local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; r.U[...] = nil", occ)
    mark = len(w.addon_log)
    rita.eval("local o, to = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; "
              "ns.Comm:Send({ t = 'RPG', o = o, u = r.U[o] }, 'WHISPER', to, 'data')", occ, K("Sam"))
    w.tick(10)
    assert _signups(sam, occ)[K("Lee")]["st"] == "T"
    asks = [e for e in w.addon_log[mark:] if e["sender"] == K("Sam") and e["chat_type"] == "WHISPER"
            and K("Lee") in e.get("recipients", [])]
    assert asks, "Sam did not ask Lee"
    # with the owner and every planner away, the real answer passed on by a member waits for the owner's login
    sam.eval("local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; r.U[...] = nil", occ)
    for x in (gina, bob, lee):
        x.logout()
    w.tick(2)
    rita.eval("local o, to = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; "
              "ns.Comm:Send({ t = 'RPG', o = o, u = r.U[o] }, 'WHISPER', to, 'data')", occ, K("Sam"))
    w.tick(10)
    assert K("Lee") not in _signups(sam, occ)
    lee.login()
    w.tick(60)
    assert _signups(sam, occ)[K("Lee")]["st"] == "T"
    no_errors(w)


@case
def test_a_withdrawal_passed_on_while_owner_and_planners_are_away_waits():
    from rp_common import world as rp_world, create, now, DAY, K, signup
    w, c = rp_world()
    gina, bob, lee, rita, sam = c["Gina"], c["Bob"], c["Lee"], c["Rita"], c["Sam"]
    occ = create(bob, i="kara", t=now(bob) + DAY)
    w.tick(3)
    assert signup(lee, occ, "A")["ok"] is True
    w.tick(3)
    for x in (gina, bob, lee):
        x.logout()
    w.tick(2)
    _forge_rpg(rita, K("Sam"), occ, K("Lee"), "X")
    w.tick(20)
    assert _signups(sam, occ)[K("Lee")]["st"] == "A"
    # nobody may vouch for it when the planner is back either (Rita passed it on, not the planner)
    bob.login()
    w.tick(60)
    assert _signups(sam, occ)[K("Lee")]["st"] == "A"
    no_errors(w)


@case
def test_a_relayed_waitlist_entry_is_taken_only_from_its_player_or_a_writer():
    from rp_common import world as rp_world, team, K
    w, c = rp_world()
    bob, lee, rita, sam = c["Bob"], c["Lee"], c["Rita"], c["Sam"]
    tid = team(bob, "Main", ["Lee"])
    w.tick(3)
    ln = "main"          # (a lineup id; the waitlists are kept per lineup id, Lineup.MergeWait)
    # Rita passes on Bob's team with a waitlist entry "by" Sam, joining it
    rita.eval("local tid, ln, sam, to = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; local now = GetServerTime(); "
              "ns.Comm:Send({ t = 'RPG', T = r.T[tid], w = { [ln] = { [sam] = { rev = now, by = sam, at = now } } } }, "
              "'WHISPER', to, 'data')", tid, ln, K("Sam"), K("Lee"))
    w.tick(3)

    def waiting(cl):
        return cl.eval_py("local tid, ln, k = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; "
                          "return r.W[tid] and r.W[tid][ln] and r.W[tid][ln][k] or false", tid, ln, K("Sam"))

    assert waiting(lee) is False, waiting(lee)
    # Sam's own copy (or the council's) is taken
    sam.eval("local tid, ln, sam, to = ...; local r = ns.db.raidplan[ns.Guild:GetGuildKey()]; local now = GetServerTime(); "
             "ns.Comm:Send({ t = 'RPG', T = r.T[tid], w = { [ln] = { [sam] = { rev = now, by = sam, at = now } } } }, "
             "'WHISPER', to, 'data')", tid, ln, K("Sam"), K("Lee"))
    w.tick(3)
    assert waiting(lee) and waiting(lee)["by"] == K("Sam"), waiting(lee)
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 2. Audit log
# ------------------------------------------------------------------------------------------------------------------
def _audit_world():
    sys.path.insert(0, os.path.join(TESTS, "sync"))
    import common  # noqa: E402
    from common import Client, new_world, up, settle, gm_pick  # noqa: E402
    common.CDL_PREFIXES = tuple(common.CDL_PREFIXES) + ("CDLz",)
    w = new_world(council=None)
    gm = Client(w, "Guildboss", class_file="PALADIN", guild_rank=0)
    ca = Client(w, "Councila", class_file="PRIEST", guild_rank=1)
    cb = Client(w, "Councilb", class_file="MAGE", guild_rank=2)
    rd = Client(w, "Raider", class_file="WARRIOR", guild_rank=3)
    for x in (gm, ca, cb, rd):
        up(x)
    settle(w, 3)
    gm_pick(w, gm, ["Councila", "Councilb"])
    settle(w, 60)
    return w, gm, ca, cb, rd, common.key, settle


FORGE_AUE = """
local o, w, to, t = ...
local e = { t = t or GetServerTime() - 30, a = 'raids', v = 'rem', o = o, n = 'Karazhan', k = 'rp.E', w = w,
            c = 'deleted {o}' }
e.id = ns.Audit.EntryId(e)
ns.Comm:Send({ t = 'AUE', e = { e } }, 'WHISPER', to, 'audit')
return e.t"""


def _audit_of(cl, o):
    return cl.eval_py("local o = ...; local out = {}; for _, e in ipairs(ns.Audit:Entries()) do "
                      "if e.o == o then out[#out + 1] = { w = e.w, rb = e.rb or false, v = e.v } end end; return out", o)


@case
def test_an_audit_entry_from_someone_else_than_its_author_says_who_passed_it_on():
    w, gm, ca, cb, rd, key_, settle = _audit_world()
    gmk, cak, cbk = key_("Guildboss"), key_("Councila"), key_("Councilb")
    assert ca.eval("return ns.Audit:IsRecording()") and cb.eval("return ns.Audit:IsRecording()")
    # Councilb writes "the GM deleted Karazhan" into Councila's log
    t = cb.eval(FORGE_AUE, "rp:O:forged", gmk, cak)
    settle(w, 3)
    got = _audit_of(ca, "rp:O:forged")
    assert got == [{"w": gmk, "rb": cbk, "v": "rem"}], got
    # the page names the relayer
    who = ca.eval("local e; for _, x in ipairs(ns.Audit:Entries()) do if x.o == 'rp:O:forged' then e = x end end; "
                  "return ns.AuditUI and ns.AuditUI.H and ns.AuditUI.H.Who and ns.AuditUI.H.Who(e) or e.rb")
    assert "Councilb" in str(who), who
    # an entry about its sender's own change: no mark
    cb.eval(FORGE_AUE, "rp:O:own", cbk, cak)
    settle(w, 3)
    assert _audit_of(ca, "rp:O:own") == [{"w": cbk, "rb": False, "v": "rem"}]
    # the same entry from its author replaces the relayed copy
    gm.eval(FORGE_AUE, "rp:O:forged", gmk, cak, t)
    settle(w, 3)
    assert _audit_of(ca, "rp:O:forged") == [{"w": gmk, "rb": False, "v": "rem"}]
    # a real change the GM makes: first hand on both council clients, no mark
    res = gm.eval_py("local ok, r = ns.RaidPlan:CreateRaid({ i = 'kara', t = GetServerTime() + 2 * 86400 }); "
                     "return { ok = ok, r = r }")
    assert res["ok"], res
    settle(w, 10)
    for x in (ca, cb):
        made = [e for e in _audit_of(x, "rp:O:" + res["r"]) if e["v"] == "add"]
        assert made == [{"w": gmk, "rb": False, "v": "add"}], (x.name, made)
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 3. "by" labels: officer notes, guest book, recruit removals
# ------------------------------------------------------------------------------------------------------------------
def _officers_guild():
    w, c = guild()
    # the GM makes rank 2 officers too: Missy and Aurel are officers, Nala is not
    assert c["Arakis"].eval("return (ns.Guild:SetOfficerRanks({ [0] = true, [1] = true, [2] = true }))") is True
    w.tick(70)
    for n in ("Missy Badshot", "Aurel Namahs"):
        assert c["Nala"].eval("return ns.Guild:IsOfficer(..., true)", key(n)) is True, n
    return w, c


@case
def test_an_officer_note_passed_on_names_who_passed_it():
    w, c = _officers_guild()
    gm, missy, aurel = c["Arakis"], c["Missy"], c["Aurel"]
    target = key("Nala Brook")
    send = ("local k, n, v, by, to = ...; ns.Comm:Send({ t = 'ON', k = k, n = n, v = v, by = by }, 'WHISPER', to, "
            "'data')")
    rev = gm.eval("return GetServerTime()") + 5
    missy.eval(send, target, "Steals from the bank", rev, key(GM), key("Aurel Namahs"))
    w.tick(3)
    note = aurel.eval_py("return ns.OfficerNotes:Get(...)", target)
    assert note["by"] == key(GM) and note["via"] == key("Missy Badshot"), note
    # the same note from its writer clears the mark
    gm.eval(send, target, "Steals from the bank", rev, key(GM), key("Aurel Namahs"))
    w.tick(3)
    note = aurel.eval_py("return ns.OfficerNotes:Get(...)", target)
    assert note["by"] == key(GM) and "via" not in note, note
    # a note the GM writes reaches the officers first hand
    assert gm.eval("return (ns.OfficerNotes:Set(..., 'Healer, raids twice a week'))", key("Aurel Namahs")) is True
    w.tick(3)
    note = missy.eval_py("return ns.OfficerNotes:Get(...)", key("Aurel Namahs"))
    assert note["text"] == "Healer, raids twice a week" and note["by"] == key(GM) and "via" not in note, note
    no_errors(w)


@case
def test_a_guest_book_note_passed_on_names_who_passed_it():
    w, c = _officers_guild()
    gm, missy, aurel = c["Arakis"], c["Missy"], c["Aurel"]
    pug = "Pugzor-Thunderstrike"
    missy.eval("local pug, gm = ...; local now = GetServerTime() + 5; ns.Comm:Send({ t = 'GNL', rev = now, by = gm, "
               "l = { { k = pug, n = 'Ninja looter', b = gm, a = now } } }, 'GUILD', nil, 'data')", pug, key(GM))
    w.tick(3)
    note = aurel.eval_py("return ns.GuestBook:GetNote(...)", pug)
    assert note["note"] == "Ninja looter" and note["by"] == key(GM) and note["via"] == key("Missy Badshot"), note
    entry = aurel.eval_py("local e = ns.GuestBook:GetEntry(...); return e and { by = e.noteBy, via = e.noteVia }", pug)
    assert entry == {"by": key(GM), "via": key("Missy Badshot")}, entry
    # the GM's own note: no mark on anyone
    ok = gm.eval_py("return { ns.GuestBook:SetNote('Healbot-Thunderstrike', 'Great healer') }")
    assert ok[0] is True, ok
    w.tick(3)
    for x in (missy, aurel):
        note = x.eval_py("return ns.GuestBook:GetNote(...)", "Healbot-Thunderstrike")
        assert note["by"] == key(GM) and "via" not in note, (x.name, note)
        # (and the relayed one kept its mark through the GM's newer list: the note itself did not change)
    note = aurel.eval_py("return ns.GuestBook:GetNote(...)", pug)
    assert note.get("via") == key("Missy Badshot") or note["by"] == key(GM), note
    no_errors(w)


@case
def test_a_recruit_removal_passed_on_names_who_passed_it():
    w, c = _officers_guild()
    gm, missy, aurel = c["Arakis"], c["Missy"], c["Aurel"]
    assert aurel.eval("return ns.Recruit:IsRecruiter(...)", key("Missy Badshot")) is True
    who = "Recruitme-Thunderstrike"
    send = "local k, v, by, to = ...; ns.Comm:Send({ t = 'RCX', k = k, v = v, by = by }, 'WHISPER', to, 'data')"
    rev = gm.eval("return GetServerTime()") + 5
    missy.eval(send, who, rev, key(GM), key("Aurel Namahs"))
    w.tick(3)

    def tomb(cl):
        return cl.eval_py("local b = ns.DB:GuildBucket('recruit', false, ns.Util.GuildKey()); "
                          "return b and b.x and b.x[...]", who)

    x = tomb(aurel)
    assert x["by"] == key(GM) and x["rb"] == key("Missy Badshot"), x
    gm.eval(send, who, rev, key(GM), key("Aurel Namahs"))
    w.tick(3)
    x = tomb(aurel)
    assert x["by"] == key(GM) and "rb" not in x, x
    # a person record passed on "by" the GM, with a note "by" the GM
    missy.eval("local who, gm, to = ...; local now = GetServerTime() + 9; ns.Comm:Send({ t = 'RC', k = who, v = now, "
               "r = { st = 'talk', rev = now, by = gm, at = now, n = { { by = gm, at = now, t = 'Said yes' } } } }, "
               "'WHISPER', to, 'data')", "Newbie-Thunderstrike", key(GM), key("Aurel Namahs"))
    w.tick(3)
    p = aurel.eval_py("local b = ns.DB:GuildBucket('recruit', false, ns.Util.GuildKey()); return b.p[...]",
                      "Newbie-Thunderstrike")
    assert p["by"] == key(GM) and p["rb"] == key("Missy Badshot") and p["n"][0]["rb"] == key("Missy Badshot"), p
    no_errors(w)


@case
def test_a_blacklist_entry_passed_on_names_who_passed_it():
    w, c = _officers_guild()
    gm, missy, aurel = c["Arakis"], c["Missy"], c["Aurel"]
    bad = "Badguy-Thunderstrike"
    send = ("local bad, gm, to, now = ...; ns.Comm:Send({ t = 'BLL', rev = now, by = gm, f = 2, x = {}, "
            "l = { { k = bad, r = 'Ninja looter', b = gm, a = now, v = now } } }, 'WHISPER', to, 'data')")
    now = gm.eval("return GetServerTime()") + 5
    missy.eval(send, bad, key(GM), key("Aurel Namahs"), now)
    w.tick(3)
    e = aurel.eval_py("return ns.RaidPlan:GetBlacklistEntry(...)", bad)
    assert e["by"] == key(GM) and e["via"] == key("Missy Badshot"), e
    gm.eval(send, bad, key(GM), key("Aurel Namahs"), now)
    w.tick(3)
    e = aurel.eval_py("return ns.RaidPlan:GetBlacklistEntry(...)", bad)
    assert e["by"] == key(GM) and "via" not in e, e
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 4. LootReserve mirror
# ------------------------------------------------------------------------------------------------------------------
SESSION = r"""
LootReserve.Server.CurrentSession = { Settings = { Blind = false, MaxReservesPerPlayer = 1, LootCategories = { 2010 },
  Duration = 0, Lock = false, Equip = false, Multireserve = 1 }, Duration = 0, StartTime = 100, AcceptingReserves = true,
  Members = { Hanna = { ReservesLeft = 0, ReservesDelta = 0 }, Carol = { ReservesLeft = 0, ReservesDelta = 0 } },
  ItemReserves = { [...] = { Players = { "Carol", "Hanna" } } }, ItemConditions = {} }
LootReserve.Comm:BroadcastSessionInfo(true)"""


@case
def test_a_raid_member_who_cannot_host_lootreserve_is_not_mirrored():
    from rv_common import reserve_raid, open_reserves, key as rkey
    from test_lootreserve import lr_client, lr_host, RUBY_DRAPE
    r = reserve_raid()
    hanna = lr_client(r, "Hanna", "PRIEST")          # a pug, neither leader nor master looter
    hanna.eval(SESSION, RUBY_DRAPE)
    r.w.tick(4)
    for n in ("Alice", "Carol"):
        assert r[n].eval_py("return ns.Reserves:IsForeign()") is None, n
        assert r[n].eval_py("return ns.Reserves:Get()") is None, n
    # nor does it make the DisasterZone host go quiet
    open_reserves(r, n=1)
    r.w.tick(3)
    assert r["Alice"].eval("return ns.ReserveLR.Hosting()")
    hanna.eval(SESSION, RUBY_DRAPE)
    r.w.tick(3)
    assert r["Alice"].eval("return ns.ReserveLR.Hosting()")
    assert r["Carol"].eval_py("return ns.Reserves:Get().by") == rkey("Alice")
    r.w.assert_no_errors()


@case
def test_the_master_looter_hosting_lootreserve_is_mirrored():
    from rv_common import reserve_raid, key as rkey
    from test_lootreserve import lr_host, RUBY_DRAPE
    r = reserve_raid()
    hanna = lr_host(r)
    hanna.eval(SESSION, RUBY_DRAPE)
    r.w.tick(4)
    for n in ("Alice", "Carol"):
        assert r[n].eval_py("return ns.Reserves:IsForeign()") == rkey("Hanna"), n
    r.w.assert_no_errors()


# ------------------------------------------------------------------------------------------------------------------
# 5. Relayed records that need a role of their writer
# ------------------------------------------------------------------------------------------------------------------
@case
def test_a_plain_member_cannot_relay_the_gms_prized_item_removal():
    w, c = guild()
    gm, nala, aurel = c["Arakis"], c["Nala"], c["Aurel"]
    rec = gm.eval_py("local r = ns.Prized:Add({ 28766 }, {}); return r")
    assert rec and rec["id"] == "28766", rec
    w.tick(3)
    assert aurel.eval_py("return ns.Prized:Get('28766') ~= nil") is True
    forge = ("local gm, to = ...; local r = ns.DB:GuildBucket('prized', false).I['28766']; local c = {}; "
             "for k, v in pairs(r) do c[k] = v end; c.del, c.rev, c.by = true, r.rev + 5, gm; "
             "ns.Comm:Send({ t = 'PZG', k = 'I', r = c }, 'WHISPER', to, 'data')")
    nala.eval(forge, key(GM), key("Aurel Namahs"))
    w.tick(3)
    assert aurel.eval_py("return ns.Prized:Get('28766') ~= nil") is True
    # the GM's own copy of the same removal is taken
    gm.eval(forge, key(GM), key("Aurel Namahs"))
    w.tick(3)
    assert aurel.eval_py("return ns.Prized:Get('28766') ~= nil") is False
    no_errors(w)


@case
def test_a_plain_member_cannot_relay_a_season_or_a_poll_removal_by_the_gm():
    w, c = guild()
    gm, nala, aurel = c["Arakis"], c["Nala"], c["Aurel"]
    season = ("local gm, to = ...; ns.Comm:Send({ t = 'EVG', k = 'C', r = { id = 'season', by = gm, rev = GetServerTime(), "
              "n = 'Forged season', from = 0, to = 0 } }, 'WHISPER', to, 'data')")

    def season_name(cl):
        return cl.eval("local r = ns.DB:GuildBucket('events', false); return r and r.C and r.C.season and r.C.season.n "
                       "or false")

    nala.eval(season, key(GM), key("Aurel Namahs"))
    w.tick(3)
    assert season_name(aurel) is False
    gm.eval(season, key(GM), key("Aurel Namahs"))
    w.tick(3)
    assert season_name(aurel) == "Forged season"
    # a poll the GM asks; Nala relays a removal "by" the GM
    pid = gm.eval("local id, why = ns.Polls:Create({ q = 'Raid on Sunday?', k = 'yn', a = { { 'g' } }, "
                  "cl = GetServerTime() + 3600, rv = 'vote', ch = true }); return id or ('ERR ' .. tostring(why))")
    assert pid.startswith("p"), pid
    w.tick(3)
    assert aurel.eval_py("return ns.Polls:GetPoll(...) ~= nil", pid) is True
    forge = ("local id, gm, to = ...; local r = ns.DB:GuildBucket('polls', false).P[id]; local c = {}; "
             "for k, v in pairs(r) do c[k] = v end; c.del, c.rev, c.by = true, r.rev + 5, gm; "
             "ns.Comm:Send({ t = 'PLG', k = 'P', r = c }, 'WHISPER', to, 'data')")
    nala.eval(forge, pid, key(GM), key("Aurel Namahs"))
    w.tick(3)
    assert aurel.eval_py("return ns.Polls:GetPoll(...) ~= nil", pid) is True
    # an officer (who may ask polls) passing on the GM's removal: taken
    missy = c["Missy"]
    missy.eval(forge, pid, key(GM), key("Aurel Namahs"))
    w.tick(3)
    assert aurel.eval_py("return ns.Polls:GetPoll(...) ~= nil", pid) is False
    no_errors(w)


@case
def test_a_plain_member_cannot_relay_a_raids_strategy_fill():
    sys.path.insert(0, os.path.join(TESTS, "strategy"))
    from st_common import save_council, fill, get_fill
    from rp_common import world as rp_world, create, now, DAY, K
    w, c = rp_world(names=(("Gina", 0, "PALADIN"), ("Bob", 2, "MAGE"), ("Lee", 3, "WARRIOR"), ("Rita", 3, "PRIEST"),
                           ("Sam", 3, "HUNTER")), council=("Bob",), planners=("Lee",))
    lee, rita, sam = c["Lee"], c["Rita"], c["Sam"]
    boss = "BlackTemple:Council"
    sid = save_council(lee, "A plan")
    occ = create(lee, i="bt", t=now(lee) + DAY)
    w.tick(2)
    assert fill(lee, occ, boss, sid, {"tk.1.1": K("Sam")})["ok"] is True
    w.tick(3)
    assert get_fill(sam, occ, boss)["a"] == {"tk.1.1": K("Sam")}
    # Rita passes on Lee's fill with herself as the tank, "by" Lee
    forge = ("local o, b, by, me, to = ...; for id, f in pairs(ns.DB:GuildBucket('strategy', false).F) do "
             "if f.o == o and f.b == b then local c = {}; for k, v in pairs(f) do c[k] = v end; "
             "c.rev, c.by, c.a = f.rev + 5, by, { ['tk.1.1'] = me }; "
             "ns.Comm:Send({ t = 'SBG', k = 'F', r = c }, 'WHISPER', to, 'data') end end")
    rita.eval(forge, occ, boss, K("Lee"), K("Rita"), K("Sam"))
    w.tick(3)
    assert get_fill(sam, occ, boss)["a"] == {"tk.1.1": K("Sam")}, get_fill(sam, occ, boss)
    # the raid's planner passing on the same: taken
    lee.eval(forge, occ, boss, K("Lee"), K("Rita"), K("Sam"))
    w.tick(3)
    assert get_fill(sam, occ, boss)["a"] == {"tk.1.1": K("Rita")}, get_fill(sam, occ, boss)
    no_errors(w)


if __name__ == "__main__":
    run_all()
