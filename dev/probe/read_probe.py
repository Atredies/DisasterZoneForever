#!/usr/bin/env python3
"""Read DZProbe's SavedVariables and write the Forever client facts.

  python3 dev/probe/read_probe.py                      # finds the Forever WTF folder on this machine
  python3 dev/probe/read_probe.py path/to/DZProbe.lua  # or read a copied file

Writes:
  dev/probe/results/DZProbe-<date>.json                       the raw data
  _DisasterZoneForever-vault/09-Reference/Forever Client Facts.md   the answers, for the port

Standard library only: SavedVariables use a small Lua subset, parsed here directly.
"""
import datetime
import glob
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
WOW_GLOBS = [
    os.path.expanduser("~/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_forever_/WTF/Account/*/SavedVariables/DZProbe.lua"),
    "C:/Program Files (x86)/World of Warcraft/_forever_/WTF/Account/*/SavedVariables/DZProbe.lua",
    "C:/World of Warcraft/_forever_/WTF/Account/*/SavedVariables/DZProbe.lua",
]


# ----------------------------------------------------------------------------------------- Lua subset parser
class LuaParser:
    TOKEN = re.compile(r"""
        \s+|--\[(=*)\[.*?\]\1\]|--[^\n]*            # whitespace, comments
        |(?P<str>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
        |(?P<num>-?(?:0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|inf|nan))
        |(?P<name>[A-Za-z_][A-Za-z0-9_]*)
        |(?P<sym>[{}\[\]=,;])
    """, re.S | re.X)

    def __init__(self, text):
        self.toks = []
        pos = 0
        while pos < len(text):
            m = self.TOKEN.match(text, pos)
            if not m:
                raise ValueError(f"unexpected text at {pos}: {text[pos:pos + 30]!r}")
            pos = m.end()
            for kind in ("str", "num", "name", "sym"):
                if m.group(kind) is not None:
                    self.toks.append((kind, m.group(kind)))
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self, value=None):
        tok = self.peek()
        if value is not None and tok[1] != value:
            raise ValueError(f"expected {value!r}, got {tok!r}")
        self.i += 1
        return tok

    def assignments(self):
        out = {}
        while self.i < len(self.toks):
            _, name = self.take()
            self.take("=")
            out[name] = self.value()
        return out

    @staticmethod
    def unquote(s):
        body = s[1:-1]
        return re.sub(r"\\(\d{1,3}|.)", lambda m: chr(int(m.group(1))) if m.group(1).isdigit()
                      else {"n": "\n", "t": "\t", "r": "\r"}.get(m.group(1), m.group(1)), body)

    def value(self):
        kind, v = self.take()
        if kind == "str":
            return self.unquote(v)
        if kind == "num":
            if v in ("inf", "-inf", "nan"):
                return v
            return int(v, 16) if v.lower().startswith(("0x", "-0x")) else (float(v) if re.search(r"[.eE]", v) else int(v))
        if kind == "name":
            return {"true": True, "false": False, "nil": None}.get(v, v)
        if v == "{":
            return self.table()
        raise ValueError(f"unexpected {v!r}")

    def table(self):
        arr, d = [], {}
        while self.peek()[1] != "}":
            if self.peek()[1] == "[":
                self.take("[")
                k = self.value()
                self.take("]")
                self.take("=")
                d[k] = self.value()
            elif self.peek()[0] == "name" and self.i + 1 < len(self.toks) and self.toks[self.i + 1][1] == "=":
                k = self.take()[1]
                self.take("=")
                d[k] = self.value()
            else:
                arr.append(self.value())
            if self.peek()[1] in (",", ";"):
                self.take()
        self.take("}")
        if not d:
            return arr
        for n, v in enumerate(arr, 1):
            d[n] = v
        # tables keyed 1..n only -> list
        if d and all(isinstance(k, int) for k in d) and sorted(d) == list(range(1, len(d) + 1)):
            return [d[k] for k in sorted(d)]
        return {str(k): v for k, v in d.items()}


# ----------------------------------------------------------------------------------------- report
def yn(v):
    return {True: "✅ yes", False: "⛔ no", None: "❔ unknown"}.get(v, f"`{v}`")


def g(d, *path, default=None):
    for p in path:
        if isinstance(d, dict) and p in d:
            d = d[p]
        elif isinstance(d, list) and isinstance(p, int) and 0 <= p - 1 < len(d):
            d = d[p - 1]
        else:
            return default
    return d


def report(db, src):
    s = db.get("static", {})
    lines = []
    w = lines.append
    today = datetime.date.today().isoformat()
    build = s.get("build", {})
    if isinstance(build, dict):
        build = [build.get(str(i)) for i in range(1, 5)]
    w("---\ntags: [reference, forever, probe]\nupdated: %s\n---\n" % today)
    w("# Forever Client Facts\n")
    w("> Measured in the real WoW Forever client by the DZProbe addon (`dev/probe/`). Regenerate with "
      "`python3 dev/probe/read_probe.py` after playing with the probe installed. Raw data: `dev/probe/results/`.\n")
    w(f"- Probe run: {s.get('when')} · runs recorded: {db.get('runs')} · source: `{os.path.basename(src)}`")
    w(f"- Character: {g(s, 'player', 'race')} {g(s, 'player', 'class')} level {g(s, 'player', 'level')}, "
      f"{g(s, 'player', 'faction')}, realm {g(s, 'player', 'realm')}, locale {s.get('locale')}\n")

    w("## Key answers for the port\n")
    w("| Question | Answer | Matters for |")
    w("|---|---|---|")
    w(f"| Build / Interface | `{build}` | TOC, mock `GetBuildInfo` |")
    w(f"| `WOW_PROJECT_ID` | `{s.get('WOW_PROJECT_ID')}` (known: {s.get('projects')}) | flavor checks |")
    w(f"| Max level | `{s.get('maxLevel')}` | level gates (TBC used 70) |")
    w(f"| `loadstring` runs | {yn(g(s, 'lua', 'loadstringRuns'))} · setfenv {yn(g(s, 'lua', 'setfenv'))} | in-game updates (hotpatch) |")
    hist = db.get("svAtFileLoadHistory", [])
    lsvf = True if any(h is True for h in hist[1:]) else (False if len(hist) > 1 else None)
    w(f"| `LoadSavedVariablesFirst` honoured | {yn(lsvf)} (per login: {hist}) | hotpatch boot (Core/Boot.lua) |")
    w(f"| TOC `X-` fields readable | {yn(g(s, 'toc', 'xField') == 'metadata-ok')} | `X-CDL-Protocol` |")
    w(f"| `loadDeprecationFallbacks` CVar | `{g(s, 'toc', 'deprecationFallbacks')}` | old global aliases |")
    w(f"| Master loot in the loot enum | {yn('Masterlooter' in (g(s, 'loot', 'methods') or {}))} · "
      f"`SetLootMethod` {yn(g(s, 'loot', 'SetLootMethod'))} · `GiveMasterLoot` {yn(g(s, 'loot', 'GiveMasterLoot'))} · "
      f"style `{g(s, 'loot', 'style')}` · now `{g(s, 'loot', 'current', 'method')}` | loot council hand-out |")
    w(f"| Raid size constants | `{g(s, 'loot', 'raidMax')}` | 10/20/40 raids |")
    w(f"| `GetGuildRosterInfo` | {yn(g(s, 'guild', 'GetGuildRosterInfo'))} · own row returns "
      f"`{g(s, 'guild', 'selfRow', 'returns')}` · rows readable `{g(s, 'guild', 'rosterRowsReadable')}` of "
      f"`{g(s, 'guild', 'numMembers')}` | roles (Core/Guild.lua) |")
    w(f"| Guild rank index (us) | `{g(s, 'guild', 'rankIndex')}` `{g(s, 'guild', 'rankName')}` · leader "
      f"{yn(g(s, 'guild', 'isLeader'))} · ranks `{g(s, 'guild', 'ranks')}` | GM / officer detection |")
    w(f"| Officer note readable | type `{g(s, 'guild', 'selfRow', 'officerNoteType')}` · can view "
      f"{yn(g(s, 'guild', 'canViewOfficerNote'))} · can edit {yn(g(s, 'guild', 'canEditOfficerNote'))} | mains/alts, officer notes |")
    w(f"| Item tooltip hook | `OnTooltipSetItem` exists {yn(g(s, 'tooltip', 'hasOnTooltipSetItem'))}, fired "
      f"`{db.get('counters', {}).get('ttLegacy', 0)}` · `TooltipDataProcessor` fired `{db.get('counters', {}).get('ttData', 0)}` | BiS tooltip lines |")
    w(f"| Combat log | register forbidden {yn(g(s, 'combatLog', 'registerForbidden'))} · "
      f"events seen `{db.get('counters', {}).get('clog', 0)}` · `C_DamageMeter` {yn(g(s, 'combatLog', 'C_DamageMeter'))} · "
      f"`C_EncounterTimeline` {yn(g(s, 'combatLog', 'C_EncounterTimeline'))} · `C_SwingTimer` {yn(g(s, 'combatLog', 'C_SwingTimer'))} | meters, boss mods, timers |")
    w(f"| Addon-message burst (40 on `{g(s, 'burst', 'channel')}`) | results `{g(s, 'burst', 'results')}` · echoed back "
      f"`{db.get('counters', {}).get('burstRecv')}` | Comm throttle |")
    w(f"| `/roll` line | `{g(s, 'roll')}` | loot rolls |")
    w(f"| `GetInventoryItemID` returns | `{g(s, 'items', 'invItemIdReturns')}` | mock fidelity |")
    w(f"| Item cache | Hearthstone `{g(s, 'items', 'hearthstone')}` · Thunderfury first `{g(s, 'items', 'thunderfury')}`, "
      f"after load `{g(s, 'items', 'thunderfuryLoaded')}` | Atlas / BiS |")
    w(f"| Talents | `{s.get('talents')}` | class planner, role detection |")
    w(f"| Static checks that errored | `{s.get('errors') or 'none'}` · sample errors `{db.get('counters', {}).get('sampleErrors', 0)}` | probe health |")
    w(f"| Secret-value helpers | `{g(s, 'restrictions', 'helpers')}` | Compat.lua |")
    if s.get("names"):
        w(f"| Own name forms | `{s.get('names')}` | name keys (Name-Realm) |")
        w(f"| Roster name shapes | `{g(s, 'guild', 'nameShapes')}` · self row matched by `{g(s, 'guild', 'selfRow', 'matchedBy')}` | name keys |")
    others = db.get("counters", {}).get("othersByChannel")
    if others:
        w(f"| Other addons' messages received | `{others}` | Comm receive |")
    w("")

    rost = [(ctx, m["roster"]) for ctx, m in sorted((db.get("matrix") or {}).items()) if m.get("roster")]
    if rost:
        w("## Group roster readability (round 2)\n")
        w("Counts of value kinds per field; `secret` means the addon cannot read it there.\n")
        w("| Context | Rows | GetRaidRosterInfo fields | raidN / partyN unit calls |")
        w("|---|---|---|---|")
        for ctx, r in rost:
            w(f"| `{ctx}` | {r.get('rows')} | `{r.get('fields')}` | `{r.get('units')}` |")
        w("")

    api = s.get("api", {})
    w("## API surface the addon uses\n")
    w(f"Present: `{api.get('present')}`\n")
    for key, label in (("C", "C_ functions"), ("G", "globals"), ("EV", "events")):
        miss = g(api, "missing", key) or []
        w(f"**Missing {label} ({len(miss)}):** " + (", ".join(f"`{m}`" for m in miss) if miss else "none") + "\n")

    w("## What works where (passive samples)\n")
    w("Context = instance type | combat | encounter | active addon restrictions.\n")
    w("| Context | Samples | Addon sends | Chat lockdown | Secret values |")
    w("|---|---|---|---|---|")
    for ctx, m in sorted((db.get("matrix") or {}).items()):
        secrets = [k for k, v in (m.get("values") or {}).items() if isinstance(v, dict) and v.get("secret")]
        sends = "; ".join(f"{ch}: {res}" for ch, res in (m.get("sends") or {}).items())
        w(f"| `{ctx}` | {m.get('samples')} | {sends} | {m.get('chatLockdown')} | {', '.join(secrets) or 'none'} |")
    w("")

    log = db.get("log") or []
    kinds = {}
    for e in log:
        kinds[e.get("k")] = kinds.get(e.get("k"), 0) + 1
    w("## Event log summary\n")
    w(f"Entries: {len(log)} · by kind: `{kinds}` · handler errors: `{db.get('counters', {}).get('handlerErrors', 0)}`\n")
    restr = [e for e in log if e.get("k") == "restriction"][:40]
    if restr:
        w("| When | Restriction | State | Context |")
        w("|---|---|---|---|")
        for e in restr:
            when = datetime.datetime.fromtimestamp(e.get("t", 0)).strftime("%m-%d %H:%M:%S")
            w(f"| {when} | {e.get('type')} | {e.get('state')} | `{e.get('ctx')}` |")
        w("")
    for kind in ("action-blocked", "action-forbidden", "handler-error", "clog-first", "loot", "encounter-start",
                 "group", "loot-method-changed", "loot-opened", "master-loot-list", "loot-slot-cleared", "loot-roll"):
        hits = [e for e in log if e.get("k") == kind][:5]
        if hits:
            w(f"**{kind}:** " + "; ".join(f"`{ {k: v for k, v in e.items() if k not in ('k', 't')} }`" for e in hits) + "\n")
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) > 1:
        src = sys.argv[1]
    else:
        found = [p for pat in WOW_GLOBS for p in glob.glob(pat)]
        if not found:
            sys.exit("No DZProbe.lua SavedVariables found. Install the probe, log in, /reload, then run again.")
        src = max(found, key=os.path.getmtime)
    data = LuaParser(pathlib.Path(src).read_text(encoding="utf-8", errors="replace")).assignments()
    db = data.get("DZProbeDB") or {}
    override = os.environ.get("DZPROBE_OUT_DIR")          # tests write somewhere else
    out = pathlib.Path(override) if override else ROOT / "dev" / "probe" / "results"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    (out / f"DZProbe-{stamp}.json").write_text(json.dumps(db, indent=1, sort_keys=True, default=str), encoding="utf-8")
    # each probe round (DZProbeDB.version) gets its own note, so a later round never overwrites an earlier one
    rnd = int(db.get("version") or 1)
    name = "Forever Client Facts.md" if rnd == 1 else f"Forever Client Facts - Round {rnd}.md"
    facts = (out if override else ROOT / "_DisasterZoneForever-vault" / "09-Reference") / name
    facts.write_text(report(db, src), encoding="utf-8")
    print(f"read {src}\nwrote {out / f'DZProbe-{stamp}.json'}\nwrote {facts}")


if __name__ == "__main__":
    main()
