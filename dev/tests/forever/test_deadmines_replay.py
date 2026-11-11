"""A real WoW Forever session, played back through DisasterZone: the full Deadmines clear of 2026-11-08 as DZProbe
recorded it (9 boss pulls, 3 of them wipes; fixtures/deadmines-2026-11-08.json, cut by dev/probe/export_replay.py).

A party of five Forever clients (the mock's forever=True profile, wowmock/forever.lua) goes through the recorded
zones, combat and pulls in order, with long quiet gaps shortened. Around every pull the guild talks: the leader sends
a multi-part message the instant the boss is pulled, and members send small ones during the fight. Checked:
  * the client's restriction changes match the recording (Encounter + Chat on for each pull, off before ENCOUNTER_END)
  * nothing goes on the wire while a pull's chat lockdown is on, and the client refuses nothing (no message lost to
    AddOnMessageLockdown)
  * every message sent around a pull arrives, whole, after it
  * no Lua errors and no forbidden actions (the combat log stays untouched) on any client

Run: luaenv/bin/python tests/forever/test_deadmines_replay.py [-k name]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "deadmines-2026-11-08.json")
GAP_CAP = 4.0          # quiet stretches longer than this are shortened to it (pulls themselves are short anyway)
STEP = 0.1
DEADMINES = dict(name="The Deadmines", instance_id=36, instance_type="party", max_players=5, difficulty_id=1)
# the guild's real names (first name + surname) and realm: Forever's regionally unique names, test_forever_names.py
REALM = "CAMWOW EU4 Realm 4 PvP"
PARTY = [("Arakis War", "WARRIOR", 0), ("Missy Badshot", "HUNTER", 1), ("Aurel Namahs", "MAGE", 3),
         ("Blu Skydagger", "ROGUE", 3), ("Megumin Chan", "PRIEST", 4)]


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


# a payload that does not compress: several 255-byte parts on the wire
def bulky(seed, n=9000):
    x, out = seed * 7919 + 1, []
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"[x % 62])
    return "".join(out)


RECV_SPY = r"""
__got = {}
local function keep(sender, msg)
  __got[#__got + 1] = { t = msg.t, n = msg.n, len = msg.body and #msg.body or 0, from = sender }
end
ns.Comm:Register("ZZPULLBIG", keep)
ns.Comm:Register("ZZPULLSMALL", keep)
"""


def party():
    w = World(realm=REALM)
    cs = []
    for name, cls, rank in PARTY:
        c = Client(w, name, class_file=cls, guild_rank=rank, level=17, forever=True)
        c.load_addon()
        cs.append(c)
    w.tick(3)
    w.make_party(cs)
    w.tick(2)
    for c in cs:
        c.eval(RECV_SPY)
    return w, cs


class Replay:
    def __init__(self, w, cs, events):
        self.w, self.cs, self.events = w, cs, events
        self.pulls = []                 # [{id, name, start, end, success, sent: [(n, t)]}]
        self.cur = None
        self.in_dm = False

    def run(self):
        last = 0.0
        for e in self.events:
            gap = min(e["t"] - last, GAP_CAP)
            last = e["t"]
            if gap > 0:
                self.w.tick(gap, step=STEP)
            getattr(self, "on_" + e["k"].replace("-", "_"))(e)
        self.w.tick(5, step=STEP)

    # -- recorded events -------------------------------------------------------------------------------------
    def on_zone(self, e):
        dm = e["zone"] == "The Deadmines"
        if dm and not self.in_dm:
            self.w.enter_instance(**DEADMINES)
        elif not dm and self.in_dm:
            self.w.leave_instance()
        self.in_dm = dm

    def on_group(self, e):
        pass                            # (the party is formed up front)

    def on_combat_start(self, e):
        for c in self.cs:
            c.set_combat(True)
            self.fight_events(c)

    # what the client sends during a fight: power and health changes (secret values on Forever), the target
    def fight_events(self, c):
        token = {"WARRIOR": "RAGE", "ROGUE": "ENERGY"}.get(c.class_file, "MANA")
        for _ in range(3):
            c._fire("UNIT_POWER_FREQUENT", "player", token)
            c._fire("UNIT_POWER_UPDATE", "player", token)
            c._fire("UNIT_HEALTH", "player")
            c._fire("UNIT_HEALTH", "target")
            c._fire("UNIT_AURA", "player")
            c._fire("UNIT_SPELLCAST_SUCCEEDED", "player", "Cast-1", 75)
        c._fire("PLAYER_TARGET_CHANGED")

    def on_combat_end(self, e):
        for c in self.cs:
            c.set_combat(False)

    def on_restriction(self, e):
        pass                            # (the mock makes its own; compared after the run)

    def on_loot_roll(self, e):
        pass

    def on_encounter_start(self, e):
        w, lead = self.w, self.cs[0]
        n = len(self.pulls) + 1
        p = {"n": n, "id": e["id"], "name": e["name"], "diff": e["difficulty"], "size": e["size"],
             "start": w.now, "big": n, "small": []}
        # the leader's message goes out as the boss is pulled: ChatThrottleLib is still sending its parts
        assert lead.eval("local n, body = ...; return ns.Comm:Send({ t = 'ZZPULLBIG', n = n, body = body }, 'PARTY')",
                         n, bulky(n)) is True
        for c in self.cs:
            c._fire("ENCOUNTER_START", e["id"], e["name"], e["difficulty"], e["size"])
        # members speak up during the fight
        for i, c in enumerate(self.cs[1:], 1):
            tag = n * 10 + i
            assert c.eval("return ns.Comm:Send({ t = 'ZZPULLSMALL', n = ... }, 'PARTY')", tag) is True
            p["small"].append(tag)
        self.cur = p
        self.pulls.append(p)

    def on_encounter_end(self, e):
        p = self.cur
        assert p and p["id"] == e["id"], (p, e)
        for c in self.cs:
            c._fire("ENCOUNTER_END", e["id"], p["name"], p["diff"], p["size"], e["success"])
        p["end"], p["success"] = self.w.now, e["success"]
        self.cur = None


_RUN = {}


def played():
    """One replay shared by the checks below (it takes a while)."""
    if not _RUN:
        data = load_fixture()
        w, cs = party()
        r = Replay(w, cs, data["events"])
        r.run()
        _RUN.update(w=w, cs=cs, r=r, data=data)
    return _RUN["w"], _RUN["cs"], _RUN["r"], _RUN["data"]


def mock(c, expr):
    return c.eval_py("return " + expr)


@case
def test_fixture_is_the_deadmines_clear():
    data = load_fixture()
    starts = [e for e in data["events"] if e["k"] == "encounter-start"]
    ends = [e for e in data["events"] if e["k"] == "encounter-end"]
    assert [e["name"] for e in starts] == ["Rhahk'Zor", "Sneed", "Gilnid", "Mr. Smite", "Mr. Smite",
                                           "Captain Greenskin", "Edwin VanCleef", "Edwin VanCleef", "Cookie"]
    assert [e["success"] for e in ends] == [1, 1, 1, 0, 1, 1, 0, 1, 0]
    assert data["build"] == "1.60.1"


@case
def test_restrictions_follow_the_recording():
    w, cs, r, data = played()
    want = [(e["type"], e["state"]) for e in data["events"]
            if e["k"] == "restriction" and e["type"] in ("Encounter", "Chat")]
    names = {v: k for k, v in mock(cs[0], "Enum.AddOnRestrictionType").items()}
    states = {v: k for k, v in mock(cs[0], "Enum.AddOnRestrictionState").items()}
    log = mock(cs[0], "__MOCK.restriction_log") or {}
    log = [log[i] for i in sorted(log)] if isinstance(log, dict) else log
    got = [(names[x["type"]], states[x["state"]]) for x in log if names[x["type"]] in ("Encounter", "Chat")]
    assert got == want, (got[:6], want[:6])


@case
def test_nothing_on_the_wire_during_a_pull():
    w, cs, r, data = played()
    assert len(r.pulls) == 9
    for p in r.pulls:
        during = [e for e in w.addon_log if round(p["start"], 3) < e["time"] < round(p["end"], 3)]
        assert during == [], "pull %d (%s): %d message(s) sent during the lockdown" % (p["n"], p["name"], len(during))
    for c in cs:
        refused = c.eval("return __MOCK.lockdown_refused")
        assert refused == 0, "%s: %d send(s) refused with AddOnMessageLockdown: %s" % (
            c.name, refused, mock(c, "__MOCK.lockdown_refused_by"))


@case
def test_every_message_arrives_after_its_pull():
    w, cs, r, data = played()
    for c in cs:
        got = mock(c, "__got") or {}
        got = [got[i] for i in sorted(got)] if isinstance(got, dict) else got
        big = sorted(g["n"] for g in got if g["t"] == "ZZPULLBIG")
        small = sorted(g["n"] for g in got if g["t"] == "ZZPULLSMALL")
        if c is not cs[0]:
            assert big == list(range(1, 10)), "%s got the leader's pull messages %s" % (c.name, big)
            assert all(g["len"] == 9000 for g in got if g["t"] == "ZZPULLBIG"), "a pull message arrived cut short"
        want_small = sorted(t for p in r.pulls for t in p["small"] if t % 10 != cs.index(c))
        assert small == want_small, "%s: small messages %s, want %s" % (c.name, small, want_small)


@case
def test_no_errors_and_no_forbidden_actions():
    w, cs, r, data = played()
    for c in cs:
        assert not mock(c, "__MOCK.forbidden"), c.name
    no_errors(w)


if __name__ == "__main__":
    run_all()
