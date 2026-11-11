"""Shared set-up of the go-live readiness suites (dev/tests/golive): the guild <Casual Disaster> on WoW Forever, every
client on the Forever profile (forever=True: client 1.60.1, Interface 16001, the retail engine with vanilla content;
wowmock/forever.lua), with realistic numbers of members.

Not a test file itself. The suites:
  test_golive_guild_day.py     ~15 members through a guild day (logins, ranks, events, polls, raids, BiS, catch-up)
  test_golive_raid_night.py    a 40-man Onyxia and a 20-man Hyjal night (invites, pulls, loot, reserves, council)
  test_golive_load.py          40 clients in a raid plus guild traffic: message counts, throttling, nothing lost
  test_golive_resilience.py    /reload mid-raid, a disconnect during a roll, leader / master looter changes, conflicts

Run one: luaenv/bin/python tests/golive/test_golive_guild_day.py [-k name]
"""
import os
import random
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
for sub in ("boot-ui", "sync"):
    p = os.path.join(TESTS, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from _common import case, run_all, no_errors, strip_codes  # noqa: E402,F401
from harness import World, Client, ExtraMember, normalize_realm  # noqa: E402,F401
from cdl_council import gm_pick  # noqa: E402

REALM = "CAMWOW EU4 Realm 4 PvP"
GUILD = "Casual Disaster"
CDL = ("CDLc", "CDLd", "CDLa", "CDLg", "CDLm", "CDLl", "CDLw", "CDLr", "CDLe", "CDLf", "CDLq", "CDLx", "CDLy",
       "CDLb", "CDLk", "CDLz")

# The guild, Forever style (first name + surname). Rank 0 GM, 1 Officer, 2 Veteran, 3 Member, 4 Initiate.
GM = ("Arakis War", "WARRIOR", 0)
OFFICERS = [("Missy Badshot", "HUNTER", 1), ("Aurel Namahs", "MAGE", 1)]
RAID_LEADER = ("Blu Skydagger", "ROGUE", 2)
FIRST = ["Megumin", "Tobin", "Elra", "Garrick", "Sefa", "Holt", "Ivy", "Jorun", "Kesha", "Lorn", "Mira", "Nedd",
         "Orla", "Pike", "Quill", "Rhea", "Soren", "Tamsin", "Ulric", "Vala", "Wynn", "Xera", "Yorik", "Zinna",
         "Brannoc", "Cedra", "Dagny", "Eamon", "Fenna", "Gisla", "Hakon", "Iselda", "Jory", "Kael", "Liri", "Morn",
         "Nyssa", "Osric", "Pella", "Rook", "Sable", "Thane", "Una", "Vex", "Wren"]
SURNAMES = ["Chan", "Ashford", "Brightwater", "Coldiron", "Dunmore", "Emberly", "Frostmane", "Greyhill", "Hollow",
            "Ironleaf", "Jadeborn", "Kettle", "Longstride", "Mossy", "Northwind", "Oakhart", "Pebble", "Quickfoot",
            "Redfern", "Stonebrook", "Thistle", "Underbough", "Vale", "Whitlock", "Yarrow"]
CLASSES = ["PRIEST", "WARRIOR", "DRUID", "HUNTER", "ROGUE", "PALADIN", "MAGE", "WARLOCK", "SHAMAN"]


def member_names(n):
    return ["%s %s" % (FIRST[i % len(FIRST)], SURNAMES[(i * 7) % len(SURNAMES)]) for i in range(n)]


def key(name):
    return "%s-%s" % (name, normalize_realm(REALM))


def roster(n_members):
    """[(name, class, rank)]: GM, two officers, the raid leader, then n_members members (ranks 3 and 4)."""
    out = [GM] + list(OFFICERS) + [RAID_LEADER]
    for i, nm in enumerate(member_names(n_members)):
        out.append((nm, CLASSES[i % len(CLASSES)], 3 if i % 3 else 4))
    return out


def new_world(**kw):
    kw.setdefault("realm", REALM)
    return World(**kw)


def make_clients(w, rows, online=False, forever=True, level=60):
    return [Client(w, n, class_file=cls, guild_rank=rank, level=level, forever=forever, online=online)
            for n, cls, rank in rows]


def by_name(clients):
    return {c.name: c for c in clients}


# ---------------------------------------------------------------------------------------------------------------------
# time
# ---------------------------------------------------------------------------------------------------------------------
def quiet(w, prefixes=CDL, idle=20.0, timeout=900.0, step=0.25):
    """Tick until none of `prefixes` was sent for `idle` seconds (and nothing is queued in the mock). Returns the
    time of the last such message."""
    start = w.now
    n0 = len(w.addon_log)
    last = start
    while w.now - start < timeout:
        w.tick(step, step)
        for e in w.addon_log[n0:]:
            if e["prefix"] in prefixes:
                last = max(last, e["time"])
        n0 = len(w.addon_log)
        if w.now - last >= idle:
            return last
    raise TimeoutError("traffic did not settle within %ss" % timeout)


def login_staggered(w, clients, spread, seed=1, step=0.25):
    """Log the clients in one after another over `spread` seconds (shuffled, deterministic)."""
    order = list(clients)
    random.Random(seed).shuffle(order)
    gap = spread / max(1, len(order))
    for c in order:
        c.login()
        w.tick(gap, min(gap, step))
    return order


def online(clients):
    return [c for c in clients if c.online and c.runtime is not None and c.loaded]


# ---------------------------------------------------------------------------------------------------------------------
# what a client holds (for convergence)
# ---------------------------------------------------------------------------------------------------------------------
STATE_LUA = r"""
local G = ns.Guild
local ranks = G:GetOfficerRanks()
local leaders = G.GetRaidLeaders and G:GetRaidLeaders() or {}
local l2 = {}
for _, k in ipairs(leaders) do l2[#l2 + 1] = k end
table.sort(l2)
local function h(m) return m and m.GetDigestHash and m:GetDigestHash() or "-" end
return { ev = h(ns.Events), po = h(ns.Polls), rp = h(ns.RaidPlan), pz = h(ns.Prized), sd = h(ns.Strategy),
         ranks = table.concat(ranks, ","), leaders = table.concat(l2, ","),
         council = G.GetGuildCouncilRev and G:GetGuildCouncilRev() or 0 }
"""


def state(c):
    return c.eval_py(STATE_LUA)


def states(clients):
    return {c.name: state(c) for c in online(clients)}


def diverging(clients, fields=("ev", "po", "rp", "ranks", "leaders", "council")):
    """{field: {value: [names]}} for every field on which the online clients do not all agree."""
    st = states(clients)
    out = {}
    for f in fields:
        vals = {}
        for n, s in st.items():
            vals.setdefault(str(s.get(f)), []).append(n)
        if len(vals) > 1:
            out[f] = vals
    return out


def assert_converged(clients, fields=("ev", "po", "rp", "ranks", "leaders", "council")):
    d = diverging(clients, fields)
    assert not d, "clients disagree: %r" % (d,)


# ---------------------------------------------------------------------------------------------------------------------
# traffic numbers
# ---------------------------------------------------------------------------------------------------------------------
def throttled(c):
    try:
        return int(c.eval("return __MOCK.throttled or 0") or 0)
    except Exception:  # noqa: BLE001
        return 0


def lockdown_refused(c):
    try:
        return int(c.eval("return __MOCK.lockdown_refused or 0") or 0)
    except Exception:  # noqa: BLE001
        return 0


def comm_stats(c):
    return c.eval_py("local s = ns.Comm.stats; return { sent = s.sent, recv = s.recv, dropped = s.dropped,"
                     " held = s.lockHeld or 0, flushed = s.lockFlushed or 0, lockDropped = s.lockDropped or 0,"
                     " backlog = ns.Comm:Backlog() }")


def wire_stats(w, mark=0, prefixes=CDL):
    """Wire messages / bytes since addon_log[mark], per prefix and chat type; deliveries; lost/dropped entries."""
    wire = [e for e in w.addon_log[mark:] if e["prefix"] in prefixes]
    per, ct, senders = Counter(), Counter(), Counter()
    size = 0
    for e in wire:
        per[e["prefix"]] += 1
        ct[e["chat_type"]] += 1
        senders[e["sender"].split("-")[0]] += 1
        size += len(e["text"])
    deliveries = sum(len(e.get("delivered") or ()) for e in wire)
    dropped = sum(len(e.get("dropped") or ()) for e in wire)
    return {"wire": len(wire), "bytes": size, "per_prefix": dict(per), "per_chat": dict(ct),
            "deliveries": deliveries, "dropped_offline": dropped, "busiest": senders.most_common(3)}


def fmt_stats(s):
    return "%d wire msgs / %.1f KB, %d deliveries, per prefix %s, per channel %s, busiest %s" % (
        s["wire"], s["bytes"] / 1024.0, s["deliveries"], s["per_prefix"], s["per_chat"], s["busiest"])


def note(text):
    print("    " + text)


def stopwatch():
    t0 = time.time()
    return lambda: time.time() - t0
