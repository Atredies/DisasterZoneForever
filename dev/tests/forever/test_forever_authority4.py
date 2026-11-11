"""Authority holes, round 4 (2026-11-09, after test_forever_authority.py / 2 / 3): every case is a guild member sending a
hand-made message, the other clients refusing it (or naming who passed it on), and the legitimate flow still working.
A receiver believes only the actual sender, never an author / owner / host named inside the payload.

  1. Feedback (FBN / FBR): items, me-toos and replies are believed from their author or staff. Passed on by anyone
     else, a new one is kept marked with who passed it on (shown on the item), and it never changes or withdraws one
     the receiver holds; the author's copy is asked for and clears the mark.
  2. Live events (EVS): the host is the sender (or a hand-over the host I know sent); a client never goes on hosting
     a run, nor publishes its result, because a message named it.
  3. Group runs (DRS): a run in the board digest is taken from its owner only; a relayed one is asked for from its
     owner, and a run never changes owner.
  4. Professions (PFB / PFR): a member's record (professions, gear, main / alt link) is believed from its owner or an
     officer; the officer-only main link only from an officer. A relayed copy is asked for from them.
  5. Low priority: the developer's feedback plan only from the developer; a council Ledger entry's `by`.

Run: luaenv/bin/python tests/forever/test_forever_authority4.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import World, Client, case, run_all, no_errors, dev_client, DEV_KEY  # noqa: E402

FB_REALM = "Thunderstrike"


def fk(name):
    return DEV_KEY if name == "Tsumil" else "%s-%s" % (name, FB_REALM)


# ------------------------------------------------------------------------------------------------------------------
# 1. Feedback
# ------------------------------------------------------------------------------------------------------------------
def fb_world():
    """Gina the GM, Olaf an officer, Tsumil the developer, Alfa / Bert / Cleo raiders (as tests/feedback)."""
    w = World()
    c = {}
    for name, cls, rank in (("Gina", "PALADIN", 0), ("Olaf", "WARRIOR", 1), ("Tsumil", "PALADIN", 3),
                            ("Alfa", "MAGE", 3), ("Bert", "ROGUE", 3), ("Cleo", "PRIEST", 3)):
        c[name] = (dev_client(w, class_file=cls, guild_rank=rank) if name == "Tsumil"
                   else Client(w, name, class_file=cls, guild_rank=rank))
    for x in c.values():
        x.load_addon()
    w.tick(3)
    w.tick(40, step=0.25)
    return w, c


def fb_item(cl, id_):
    return cl.eval_py("local v = ns.Feedback:Get(...); if not v then return nil end; return { text = v.text, "
                      "gone = v.gone, via = v.via or false, votes = v.voteCount, author = v.author }", id_)


FB_SEND = ("local id, rec, to = ...; ns.Comm:Send({ t = 'FBN', r = { [id] = rec } }, to and 'WHISPER' or 'GUILD', to, "
           "'fb')")


def fb_rec(cl, id_):
    return cl.eval_py("local s = ns.DB:GuildBucket('feedback', false, ns.Util.GuildKey()); return s and s.r[...]", id_)


@case
def test_feedback_an_item_made_up_in_someones_name_is_marked_with_who_passed_it_on():
    w, c = fb_world()
    alfa, bert, gina = c["Alfa"], c["Bert"], c["Gina"]
    now = alfa.eval("return GetServerTime()")
    fid = fk("Alfa") + "#7"
    forged = {"k": "i", "a": fk("Alfa"), "n": 7, "kd": "love", "x": "Bert is the best tank", "t": now, "rv": now}
    alfa.logout()          # (the author away: nobody to confirm it)
    w.tick(2)
    bert.eval(FB_SEND, fid, forged, fk("Gina"))
    w.tick(3)
    got = fb_item(gina, fid)
    assert got and got["via"] == fk("Bert"), got
    no_errors(w)


@case
def test_feedback_a_relayed_withdrawal_or_edit_never_changes_an_item_held():
    w, c = fb_world()
    alfa, bert, gina, olaf, cleo = c["Alfa"], c["Bert"], c["Gina"], c["Olaf"], c["Cleo"]
    fid = alfa.eval("local id = ns.Feedback:Submit('bug', 'The roll popup closes in combat.'); return id")
    assert fid == fk("Alfa") + "#1", fid
    w.tick(5)
    assert fb_item(gina, fid)["via"] is False
    # Bert withdraws it, and rewrites it, on Gina's and Cleo's clients (newer versions "by" Alfa)
    rec = fb_rec(bert, fid)
    gone = {"k": "i", "a": fk("Alfa"), "n": 1, "d": 1, "rv": rec["rv"] + 50}
    bert.eval(FB_SEND, fid, gone, fk("Gina"))
    edit = dict(rec, x="Please remove the roll popup entirely", rv=rec["rv"] + 60)
    bert.eval(FB_SEND, fid, edit, fk("Cleo"))
    w.tick(5)
    for x in (gina, cleo):
        got = fb_item(x, fid)
        assert got and not got["gone"] and got["text"] == "The roll popup closes in combat." and got["via"] is False, \
            (x.name, got)
    # a me-too Gina gave, taken back by Bert in her name: refused
    assert gina.eval("return (ns.Feedback:Vote(...))", fid, True) is True
    w.tick(5)
    assert fb_item(cleo, fid)["votes"] == 1
    vid = fid + "+" + fk("Gina")
    v = fb_rec(bert, vid)
    bert.eval(FB_SEND, vid, dict(v, d=1, rv=v["rv"] + 30), fk("Cleo"))
    w.tick(5)
    assert fb_item(cleo, fid)["votes"] == 1
    # an officer passing on the author's own withdrawal: taken (staff only hold copies vouched for)
    olaf.eval(FB_SEND, fid, gone, fk("Cleo"))
    w.tick(3)
    assert fb_rec(cleo, fid).get("d") == 1 and fb_item(cleo, fid) is None
    # the author's own withdrawal reaches everyone
    assert alfa.eval("return (ns.Feedback:Withdraw(...))", fid) is True
    w.tick(5)
    for x in (gina, bert):
        assert fb_rec(x, fid).get("d") == 1, x.name
    no_errors(w)


@case
def test_feedback_passed_on_by_a_member_reaches_the_developer_marked_until_the_author_confirms():
    w, c = fb_world()
    for n in ("Gina", "Olaf", "Tsumil", "Cleo"):
        c[n].logout()
    w.tick(5)
    alfa, bert, dev = c["Alfa"], c["Bert"], c["Tsumil"]
    fid = alfa.eval("local id = ns.Feedback:Submit('idea', 'Show who still needs a token.'); return id")
    w.tick(5)
    assert fb_item(bert, fid)["via"] is False          # (first hand from Alfa)
    alfa.logout()
    w.tick(3)
    dev.login()
    w.tick(60, step=0.25)
    got = fb_item(dev, fid)
    assert got and got["text"] == "Show who still needs a token." and got["via"] == fk("Bert"), got
    # (the developer numbered it: Bert hears the number)
    assert dev.eval_py("return ns.Feedback:Get(...).no", fid) == 1
    # the author comes back: the developer's client asks them and the mark goes
    alfa.login()
    w.tick(60, step=0.25)
    dev.eval("ns.Feedback:SyncNow(...)", fk("Alfa"))
    w.tick(10, step=0.25)
    got = fb_item(dev, fid)
    assert got["via"] is False, got
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 2. Live events
# ------------------------------------------------------------------------------------------------------------------
def _ev():
    """(guild, cup, state, hosts_of, K) of tests/events/test_edge_live.py without importing its cases."""
    import importlib.util
    path = os.path.join(TESTS, "events", "test_edge_live.py")
    src = open(path, encoding="utf-8").read()
    src = src.replace("@case\n", "")
    mod = type(sys)("ev_live_helpers")
    mod.__file__ = path
    sys.path.insert(0, os.path.join(TESTS, "events"))
    exec(compile(src.replace('if __name__ == "__main__":', "if False:"), path, "exec"), mod.__dict__)
    return mod


EV_STATE = """local occ, host, chain, seqUp = ...
local st = ns.EventBlocks.Copy(ns.EventLive:GetState(occ))
st.seq = st.seq + seqUp; st.host = host
return { t = 'EVS', o = occ, h = host, s = st, c = chain }"""


@case
def test_live_a_member_cannot_name_a_victim_as_host_nor_take_over_a_run_unseen():
    ev = _ev()
    w, cs = ev.guild(["Gina", "Bert", "Cora", "Dain", "Eve", "Fay"])
    g, b, c, d, e, f = cs
    K = ev.K
    # Fay hears nothing of the run (she came online late, the states went past her); Dain still reaches her
    w.addon_fault = lambda entry, rc: (False if rc.full_name == K("Fay") and entry["prefix"] in ("CDLe", "CDLf")
                                       and entry["sender"] != K("Dain") else None)
    occ = ev.cup(w, g, [b, c, e])
    assert f.eval_py("return ns.EventLive:GetState(...)", occ) is None
    # Dain "hands" the run to Fay in a chain from Gina: Fay's client must not go on with it
    d.eval("local msg = (function(...) " + EV_STATE + " end)(...)\nns.Comm:Send(msg, 'WHISPER', select(5, ...), 'event')",
           occ, K("Fay"), [K("Gina"), K("Dain"), K("Fay")], 50, K("Fay"))
    w.tick(3)
    assert not f.eval("return ns.EventLive:IsHostOf(...)", occ)
    assert f.eval_py("return ns.EventLive:GetState(...)", occ) is None
    # Dain (not signed up) goes on with it as its host, on Fay's client: not listened to
    d.eval("local msg = (function(...) " + EV_STATE + " end)(...)\nns.Comm:Send(msg, 'WHISPER', select(5, ...), 'event')",
           occ, K("Dain"), [K("Gina"), K("Dain")], 50, K("Fay"))
    w.tick(3)
    assert f.eval_py("return ns.EventLive:GetState(...)", occ) is None
    # nobody else moved
    assert ev.hosts_of(cs, occ) == ["Gina"]
    for x in (b, c, d, e):
        assert ev.state(x, occ)["host"] == K("Gina"), x.name
    # the event's own host hands it to Fay, who never saw it: she goes on with it
    w.addon_fault = None
    assert g.eval("return ns.EventLive:HandOver(..., 'Fay-Thunderstrike')", occ)
    w.tick(3)
    assert ev.hosts_of(cs, occ) == ["Fay"]
    for x in (b, c, e):
        assert ev.state(x, occ)["host"] == K("Fay"), x.name
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 3. Group runs
# ------------------------------------------------------------------------------------------------------------------
def dr_world():
    w = World()
    c = {}
    for i, (name, cls) in enumerate((("Gina", "PALADIN"), ("Alfa", "PRIEST"), ("Bert", "WARRIOR"), ("Cara", "MAGE"))):
        c[name] = Client(w, name, class_file=cls, guild_rank=0 if i == 0 else 3)
    for x in c.values():
        x.load_addon()
    w.tick(50)
    return w, c


def dr_runs(cl):
    return cl.eval_py("local out = {}; for _, r in ipairs(ns.DungeonRuns:GetRuns()) do out[r.id] = { o = r.o, "
                      "no = r.no or false, rb = r.rb or false, rv = r.rv } end; return out") or {}


def dr_list(cl, d="Botanica", at=0, note=None):
    rid = cl.eval_py("local r, why = ns.DungeonRuns:List({ d = select(1, ...), h = true, role = 'healer', "
                     "at = select(2, ...), no = select(3, ...) }); return r and r.id or why", d, at, note)
    assert isinstance(rid, str) and ":" in rid, rid
    return rid


# a DRS whispered by the sender with one run: id, owner o, note, rv; the sender's own profile first
DR_FORGE = """local id, o, note, rv, to = ...
local now = GetServerTime()
ns.Comm:Send({ t = 'DRS', p = {}, l = { { id = id, o = o, d = 3, h = 1, at = 0, c = now, rv = rv, no = note,
  s = { { o, 2 } } } } }, 'WHISPER', to, 'run')"""


@case
def test_runs_a_run_passed_on_is_believed_only_from_its_owner():
    w, c = dr_world()
    gina, alfa, bert, cara = c["Gina"], c["Alfa"], c["Bert"], c["Cara"]
    rid = dr_list(gina, note="Quick heroic")
    w.tick(3)
    real = dr_runs(cara)[rid]
    assert real["o"] == fk("Gina") and real["no"] == "Quick heroic", real
    # Bert overwrites Gina's run on Cara's client (a newer revision, his note), and lists a made-up one of hers
    bert.eval(DR_FORGE, rid, fk("Gina"), "Selling boosts, whisper Bert", real["rv"] + 100, fk("Cara"))
    bert.eval(DR_FORGE, fk("Gina") + ":1", fk("Gina"), "Gina pays 100g", 5, fk("Cara"))
    w.tick(5)
    got = dr_runs(cara)
    assert got[rid]["no"] == "Quick heroic" and got[rid]["rb"] is False, got
    assert fk("Gina") + ":1" not in got, got
    # nor does a DRL of his own take her run's id
    bert.eval("local id, to, rv = ...; ns.Comm:Send({ t = 'DRL', id = id, d = 3, h = 1, at = 0, c = GetServerTime(), "
              "rv = rv, no = 'mine now', s = { { ns.Util.PlayerKey(), 1 } } }, 'GUILD', nil, 'run')",
              rid, fk("Cara"), real["rv"] + 200)
    w.tick(3)
    got = dr_runs(cara)[rid]
    assert got["o"] == fk("Gina") and got["no"] == "Quick heroic", got
    # a run of an owner who is offline: kept, marked with who passed it on, and gone once she says it isn't hers
    alfa.logout()
    w.tick(3)
    bert.eval(DR_FORGE, fk("Alfa") + ":2", fk("Alfa"), "Alfa says: guild bank is open", 5, fk("Cara"))
    w.tick(3)
    got = dr_runs(cara)
    assert got[fk("Alfa") + ":2"]["rb"] == fk("Bert"), got
    alfa.login()
    w.tick(60)
    assert fk("Alfa") + ":2" not in dr_runs(cara), dr_runs(cara)
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 4. Professions
# ------------------------------------------------------------------------------------------------------------------
def _mb():
    sys.path.insert(0, os.path.join(TESTS, "members"))
    import mb_common
    return mb_common


PF_FORGE = """local key, to, bump, link, sb, tailor = ...
local b = ns.DB:GuildBucket('prof', false, ns.Guild:GetGuildKey())
local rec = b and b[key]
local rev = (rec and rec.rev or GetServerTime()) + bump
local p = tailor and { { 197, 300, 300, 0, rev - 10, 0, 0 } } or {}
ns.Comm:Send({ t = 'PFB', l = { { k = key, v = rev, p = p, a = link, sb = sb } } }, to and 'WHISPER' or 'GUILD', to,
  'member')"""


def _prof_world():
    mb = _mb()
    w, c = mb.guild([("Gina", "PALADIN"), ("Alfa", "MAGE"), ("Bert", "ROGUE"), ("Cara", "PRIEST")])
    mb.set_skills(c["Alfa"], [("Alchemy", 375, 375)])
    w.tick(200)
    return mb, w, c


def _prof_of(cl, key):
    return cl.eval_py("local key = ...; local b = ns.DB:GuildBucket('prof', false, ns.Guild:GetGuildKey()); "
                      "local r = b and b[key]; if not r then return nil end; local p = {}; "
                      "for id in pairs(r.p) do p[#p + 1] = id end; table.sort(p); "
                      "return { p = p, a = r.a or false, sb = r.sb or false, rb = r.rb or false, rev = r.rev }", key)


@case
def test_professions_a_members_record_is_believed_only_from_them_or_an_officer():
    mb, w, c = _prof_world()
    K = mb.K
    gina, alfa, bert, cara = c["Gina"], c["Alfa"], c["Bert"], c["Cara"]
    assert _prof_of(cara, K("Alfa"))["p"] == [171]
    # Bert rewrites Alfa's record on Cara's client: Tailoring, and Alfa an alt of Bert
    bert.eval(PF_FORGE, K("Alfa"), K("Cara"), 100, K("Bert"), None, True)
    w.tick(5)
    got = _prof_of(cara, K("Alfa"))
    assert got["p"] == [171] and got["a"] is False and got["rb"] is False, got
    assert cara.eval("return ns.Professions:GetMain(...)", K("Alfa")) == K("Alfa")
    # the officer-only main link: "set" by a member, or "by" Gina but passed on by Bert
    for sb in (K("Bert"), K("Gina")):
        bert.eval(PF_FORGE, K("Cara"), K("Alfa"), 200, K("Bert"), sb, False)
        w.tick(3)
        assert alfa.eval("return ns.Professions:GetMain(...)", K("Cara")) == K("Cara"), sb
    # Alfa's own change is taken (a skill-up)
    mb.set_skills(alfa, [("Alchemy", 375, 375), ("Herbalism", 300, 375)])
    w.tick(60)
    assert _prof_of(cara, K("Alfa"))["p"] == [171, 182]
    no_errors(w)


@case
def test_professions_an_officers_main_link_is_taken_only_from_an_officer():
    mb, w, c = _prof_world()
    K = mb.K
    gina, alfa, bert, cara = c["Gina"], c["Alfa"], c["Bert"], c["Cara"]
    # Dora and Eli don't run DisasterZone
    Client(w, "Dora", class_file="PRIEST", guild_rank=3)
    Client(w, "Eli", class_file="PRIEST", guild_rank=3)
    for cl in c.values():
        cl.fire("GUILD_ROSTER_UPDATE")
    w.tick(5)
    bert.eval(PF_FORGE, K("Eli"), None, 0, K("Bert"), K("Gina"), False)
    w.tick(5)
    for cl in (alfa, cara):
        assert cl.eval("return ns.Professions:GetMain(...)", K("Eli")) == K("Eli"), cl.name
    assert gina.eval("return ns.Professions:SetMainFor(...)", K("Eli"), K("Dora")) is True
    w.tick(10)
    for cl in (alfa, bert, cara):
        assert cl.eval("return ns.Professions:GetMain(...)", K("Eli")) == K("Dora"), cl.name
    no_errors(w)


@case
def test_professions_a_member_who_was_offline_still_gets_the_guilds_professions():
    mb, w, c = _prof_world()
    K = mb.K
    gina, alfa, bert, cara = c["Gina"], c["Alfa"], c["Bert"], c["Cara"]
    gina.logout()
    alfa.logout()
    w.tick(3)
    evie = mb.join(w, "Evie")
    w.tick(200)
    got = _prof_of(evie, K("Alfa"))
    assert got and got["p"] == [171] and got["rb"] in (K("Bert"), K("Cara")), got
    # the owner back online confirms it: the mark goes
    alfa.login()
    w.tick(200)
    got = _prof_of(evie, K("Alfa"))
    assert got["p"] == [171] and got["rb"] is False, got
    # with the owner away again, an officer's copy confirms it
    alfa.logout()
    eli = mb.join(w, "Eli")
    w.tick(200)
    assert _prof_of(eli, K("Alfa"))["rb"] in (K("Bert"), K("Cara"), K("Evie")), _prof_of(eli, K("Alfa"))
    gina.login()
    w.tick(200)
    got = _prof_of(eli, K("Alfa"))
    assert got["p"] == [171] and got["rb"] is False, got
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 5. Low priority: the developer's feedback plan
# ------------------------------------------------------------------------------------------------------------------
PLAN_FORGE = """local to, bump = ...
local s = ns.DB:GuildBucket('feedbackPlan', false, ns.Util.GuildKey())
local p = ns.EventBlocks.Copy(s.plan)
p.rev = p.rev + bump
for v, r in pairs(p.rel) do r.th = 'Officer Olaf decides now'; r.u = p.rev end
ns.Comm:Send({ t = 'FBP', p = p }, 'WHISPER', to, 'fb')
local c = ns.EventBlocks.Copy(s.coming)
c.rev = c.rev + bump
for _, r in ipairs(c.l) do r.th = 'Officer Olaf decides now' end
ns.Comm:Send({ t = 'FBC', c = c }, 'GUILD', nil, 'fb')"""


def _plan_theme(cl):
    return cl.eval_py("local s = ns.DB:GuildBucket('feedbackPlan', false, ns.Util.GuildKey()); "
                      "local p = s and s.plan; local c = s and s.coming; "
                      "return { p = p and p.rel['1.9.1'] and p.rel['1.9.1'].th or false, "
                      "c = c and c.l[1] and c.l[1].th or false }")


def _set_release(dev, theme):
    r = dev.eval_py("local ok, err = ns.FeedbackPlan:SetRelease('1.9.1', { th = ..., bg = 8, pub = true }); "
                    "return { ok = ok and true or false, err = err or false }", theme)
    assert r["ok"], r


@case
def test_plan_an_officer_cannot_rewrite_the_developers_plan():
    w, c = fb_world()
    dev, gina, olaf, alfa = c["Tsumil"], c["Gina"], c["Olaf"], c["Alfa"]
    _set_release(dev, "Quality of life")
    w.tick(10, step=0.25)
    assert _plan_theme(gina) == {"p": "Quality of life", "c": "Quality of life"}, _plan_theme(gina)
    assert _plan_theme(alfa)["c"] == "Quality of life", _plan_theme(alfa)
    # Olaf (an officer, who holds a copy) sends a newer plan to Gina and a newer Coming next to the guild
    olaf.eval(PLAN_FORGE, fk("Gina"), 100)
    w.tick(5, step=0.25)
    assert _plan_theme(gina) == {"p": "Quality of life", "c": "Quality of life"}, _plan_theme(gina)
    assert _plan_theme(alfa)["c"] == "Quality of life", _plan_theme(alfa)
    # the developer's next change reaches everyone
    _set_release(dev, "Raid night fixes")
    w.tick(10, step=0.25)
    assert _plan_theme(gina) == {"p": "Raid night fixes", "c": "Raid night fixes"}, _plan_theme(gina)
    assert _plan_theme(alfa)["c"] == "Raid night fixes"
    no_errors(w)


# ------------------------------------------------------------------------------------------------------------------
# 5b. Low priority: who recorded a loot council award (Ledger `by`)
# ------------------------------------------------------------------------------------------------------------------
LEDGER_SEND = """local id, by, to, ts = ...
ns.Comm:Send({ t = 'A', e = { id = id, i = 28766, w = to, by = by, ts = ts, s = 'm' } }, 'WHISPER', to, 'data')"""


def _ledger(cl, id_):
    return cl.eval_py("local e = ns.db.ledger and ns.db.ledger[...]; return e and { by = e.by, rb = e.rb or false }",
                      id_)


@case
def test_ledger_an_award_passed_on_says_who_passed_it_on():
    sys.path.insert(0, os.path.join(TESTS, "sync"))
    import common  # noqa: E402
    from common import Client as SClient, new_world, up, settle, gm_pick  # noqa: E402
    w = new_world(council=None)
    gm = SClient(w, "Guildboss", class_file="PALADIN", guild_rank=0)
    ca = SClient(w, "Councila", class_file="PRIEST", guild_rank=1)
    cb = SClient(w, "Councilb", class_file="MAGE", guild_rank=2)
    for x in (gm, ca, cb):
        up(x)
    settle(w, 3)
    gm_pick(w, gm, ["Councila", "Councilb"])
    settle(w, 60)
    key = common.key
    ts = gm.eval("return GetServerTime()") - 60
    # Councilb tells Councila of an award "recorded by" the GM
    cb.eval(LEDGER_SEND, "forged-1", key("Guildboss"), key("Councila"), ts)
    settle(w, 3)
    assert _ledger(ca, "forged-1") == {"by": key("Guildboss"), "rb": key("Councilb")}, _ledger(ca, "forged-1")
    # an award its sender recorded: no mark
    cb.eval(LEDGER_SEND, "own-1", key("Councilb"), key("Councila"), ts)
    settle(w, 3)
    assert _ledger(ca, "own-1") == {"by": key("Councilb"), "rb": False}, _ledger(ca, "own-1")
    # the recorder's own copy puts things right
    gm.eval(LEDGER_SEND, "forged-1", key("Guildboss"), key("Councila"), ts)
    settle(w, 3)
    assert _ledger(ca, "forged-1") == {"by": key("Guildboss"), "rb": False}, _ledger(ca, "forged-1")
    no_errors(w)


if __name__ == "__main__":
    run_all()
