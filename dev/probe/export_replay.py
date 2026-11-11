#!/usr/bin/env python3
"""Cut a replayable session out of a DZProbe run: the timeline of zones, group size, combat, boss pulls, loot rolls
and the addon-restriction changes the client made, with times in seconds from the start.

  python3 dev/probe/export_replay.py RUN.json OUT.json [--name NAME]

The Deadmines fixture (dev/tests/forever/fixtures/deadmines-2026-11-08.json) was made with:
  python3 dev/probe/export_replay.py dev/probe/results/DZProbe-2026-11-08_2106.json \\
      dev/tests/forever/fixtures/deadmines-2026-11-08.json --name "Deadmines full clear, 2026-11-08"

dev/tests/forever/test_deadmines_replay.py plays it through a party of Forever clients. Standard library only.
"""
import argparse
import json
import os

KEEP = {"zone", "group", "combat-start", "combat-end", "encounter-start", "encounter-end", "loot-roll", "restriction"}


def val(d):
    """A probe-described value ({secret, t, v}) as plain data; None if it was secret or nil."""
    if isinstance(d, dict) and "t" in d:
        return None if d.get("secret") else d.get("v")
    return d


def export(run, name):
    log = [e for e in run["log"] if e["k"] in KEEP]
    t0 = log[0]["t"]
    out = []
    for e in log:
        r = {"t": e["t"] - t0, "k": e["k"]}
        k = e["k"]
        if k == "zone":
            r["zone"], r["instType"] = e["zone"], e.get("instType")
        elif k == "group":
            r["n"], r["inRaid"] = e["n"], bool(e.get("inRaid"))
        elif k == "encounter-start":
            r.update(id=val(e["id"]), name=val(e["name"]), difficulty=val(e["difficulty"]), size=val(e["size"]))
        elif k == "encounter-end":
            r.update(id=val(e["id"]), success=val(e["success"]))
        elif k == "loot-roll":
            r["rollID"] = val(e["rollID"])
        elif k == "restriction":
            r["type"], r["state"] = e["type"], e["state"]
        out.append(r)
    s = run["static"]
    return {
        "name": name,
        "source": "DZProbe run %s" % s.get("when", "?"),
        "player": s["player"],
        "build": s["build"]["1"],
        "events": out,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("out")
    ap.add_argument("--name", default="DZProbe session")
    a = ap.parse_args()
    with open(a.run, encoding="utf-8") as f:
        run = json.load(f)
    data = export(run, a.name)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=0, sort_keys=True)
        f.write("\n")
    n = sum(1 for e in data["events"] if e["k"] == "encounter-start")
    print("wrote %s: %d events, %d boss pulls" % (a.out, len(data["events"]), n))


if __name__ == "__main__":
    main()
