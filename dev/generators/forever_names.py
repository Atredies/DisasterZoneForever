#!/usr/bin/env python3
"""
English item names for the WoW Forever data generators, and the test "is this item in WoW Forever at all".

Order of sources, first hit wins:
  1. dev/generators/data/forever_items.json  (cache of earlier answers, committed: {id: name} or {id: null} = not in
     Forever's item database)
  2. names the addon already ships for the TBC client (Data/AtlasClassic.lua, Data/Atlas.lua: AtlasNames,
     AtlasClassicNames): an old-world item keeps its name; dev/fixtures/tbc/ when the addon's files are Forever's
  3. AtlasLoot's row comments ("{ 17, 273289 }, -- {FOREVER} Ogre Loincloth"), read with comments_from()
  4. Wowhead's Forever tooltip API, https://nether.wowhead.com/forever/tooltip/item/<id> (JSON; "Entity not found"
     means Forever has no such item). Only with fetch=True; answers go into the cache.

Usage from a generator:
    import forever_names as FN
    names = FN.Names(fetch=True)
    names.add_comments(FN.comments_from(path_to_atlasloot_data_lua))
    names.get(12345) -> "Rockslicer" | None
    names.save()
"""
import json
import os
import re
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.dirname(HERE)
ADDON = os.path.normpath(os.path.join(DEV, "..", "addon", "DisasterZone"))
TBC_FIXTURES = os.path.join(DEV, "fixtures", "tbc")
CACHE = os.path.join(HERE, "data", "forever_items.json")
TOOLTIP = "https://nether.wowhead.com/forever/tooltip/item/%d"
UA = "DisasterZoneForever-datagen/1.0 (guild addon data generator)"

ROW_RX = re.compile(r"\{\s*\d+\s*,\s*(\d{2,7})\s*[,}][^\n]*?--\s*(?:\{[A-Z]+\}\s*)?([^\n]+?)\s*$", re.M)
NAME_RX = re.compile(r"^\s*\[(\d+)\]\s*=\s*\"((?:[^\"\\]|\\.)*)\"", re.M)


def comments_from(path):
    """{id: name} from AtlasLoot loot rows that carry the item's name as a trailing comment."""
    out = {}
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return out
    for m in ROW_RX.finditer(text):
        name = m.group(2).strip()
        name = re.sub(r"\s*\(.*\)\s*$", "", name)          # "(neck)", "(main hand, dagger)"
        if name and not name.startswith(("TODO", "?")) and len(name) < 80:
            out.setdefault(int(m.group(1)), name)
    return out


def _shipped_names():
    out = {}
    for base in (TBC_FIXTURES, ADDON):
        for rel in ("Data/AtlasClassic.lua", "Data/Atlas.lua"):
            p = os.path.join(base, rel)
            if not os.path.exists(p):
                continue
            text = open(p, encoding="utf-8", errors="replace").read()
            for tbl in ("AtlasNames", "AtlasClassicNames"):
                i = text.find("ns.Data.%s = {" % tbl)
                if i < 0:
                    continue
                j = text.find("\n}", i)
                for m in NAME_RX.finditer(text[i:j]):
                    out.setdefault(int(m.group(1)), m.group(2).encode().decode("unicode_escape"))
    return out


class Names:
    def __init__(self, fetch=False, verify_all=False):
        self.fetch, self.verify_all = fetch, verify_all
        self.cache = {}
        if os.path.exists(CACHE):
            self.cache = {int(k): v for k, v in json.load(open(CACHE, encoding="utf-8")).items()}
        self.shipped = _shipped_names()
        self.comments = {}
        self.fetched = 0

    def add_comments(self, d):
        for k, v in d.items():
            self.comments.setdefault(k, v)

    def _wowhead(self, i):
        req = urllib.request.Request(TOOLTIP % i, headers={"User-Agent": UA})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = json.loads(r.read().decode("utf-8"))
                break
            except Exception as e:                       # (HTTP 404 = not found too)
                if getattr(e, "code", None) == 404:
                    return None
                time.sleep(1 + attempt)
        else:
            raise RuntimeError("Wowhead tooltip API unreachable for item %d" % i)
        if data.get("error") or not data.get("name"):
            return None
        return data["name"]

    def get(self, i):
        """The item's name, or None when Forever has no such item (or nothing knows it and fetching is off)."""
        if i in self.cache:
            return self.cache[i]
        if not self.verify_all:
            nm = self.shipped.get(i) or self.comments.get(i)
            if nm and i < 200000:                        # (old-world ids: unchanged in Forever)
                return nm
        if not self.fetch:
            return self.shipped.get(i) or self.comments.get(i)
        nm = self._wowhead(i)
        self.cache[i] = nm
        self.fetched += 1
        if self.fetched % 100 == 0:
            self.save()
        time.sleep(0.15)
        return nm

    def prefetch(self, ids, workers=8):
        """Ask Wowhead about every id the cache does not know yet, `workers` at a time (fetch=True only)."""
        if not self.fetch:
            return
        from concurrent.futures import ThreadPoolExecutor
        todo = sorted({int(i) for i in ids if int(i) > 0 and int(i) not in self.cache})

        def one(i):
            return i, self._wowhead(i)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for n, (i, nm) in enumerate(ex.map(one, todo), 1):
                self.cache[i] = nm
                self.fetched += 1
                if n % 200 == 0:
                    self.save()
                    print("  wowhead: %d / %d" % (n, len(todo)), flush=True)
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump({str(k): v for k, v in sorted(self.cache.items())}, fh, indent=0, ensure_ascii=False)
            fh.write("\n")
