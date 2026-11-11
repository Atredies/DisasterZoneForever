"""WoW Forever: My BiS Import / Export without the TBC sites (Core/BiSExport.lua, Core/BiSImport.lua,
UI/ImportExport.lua, UI/MyBiS.lua).

WoWSims has no Forever sim and the link format of Wowhead's Forever gear planner (wowhead.com/forever/gear-planner)
is not known, so on a Forever client: the export window offers only DisasterZone's own JSON (its "wowsims" key, the
text Import reads back), no Bulk list and no Wowhead link (Exp:WowheadLink makes none); Import's texts don't name
WoWSims or Wowhead's planner, a pasted gear planner link is refused with a hint, our own export is labelled
"DisasterZone export"; no window or menu text says wowsims.com/tbc or wowhead.com/tbc. The TBC client keeps all
three formats (checked once here; tests/bisimport covers the rest).

Run: luaenv/bin/python tests/forever/test_forever_export.py [-k name]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors, install_helpers, menu_texts, strip_codes  # noqa: E402

LAWBRINGER_HELM = 16854   # Lawbringer Helm (paladin T1, on Forever)

# Every FontString text under a frame, and every tooltip line its help links add.
TEXTS = """
local out = {}
for _, f in ipairs(T_desc(..., function(f, st) return st.kind == "FontString" end)) do
  local t = f:GetText()
  if type(t) == "string" then out[#out + 1] = t end
end
return out
"""
TBC_SITES = ("wowsims", "wowhead.com/tbc", "gear planner", "gear-planner", "Bulk")


def setup(forever=True):
    w, c = solo("Alice", class_file="PALADIN", guild_rank=3, tick=4, council=[], forever=forever, level=60)
    install_helpers(c)
    return w, c


def as_list(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v)]
    return list(v or [])


def window_texts(c, tab):
    c.eval("ns.ImportExport:Open(...)", tab)
    return as_list(c.eval_py(TEXTS, c.eval("return ns.ImportExport:GetFrame()")))


def site_hits(texts):
    return sorted({t for t in texts if any(s.lower() in t.lower() for s in TBC_SITES)})


@case
def test_export_is_only_our_own_json_on_forever():
    w, c = setup()
    assert c.eval("return ns.BiSExport:WowheadLink(ns.BiSExport:EquippedSpecs())") == ""
    c.eval("ns.ImportExport:Open('export')")
    w.tick(0.1)
    # Bulk / Wowhead can't be chosen: the format stays our JSON
    for fmt in ("bulk", "wowhead"):
        c.eval("ns.ImportExport:SetExport(nil, ...)", fmt)
        assert c.eval("return ns.ImportExport:GetImportState().format") == "wowsims", fmt
    c.eval("ns.ImportExport:SetExport('gear')")
    text = c.eval("return ns.ImportExport:GetExportText()")
    doc = json.loads(text)
    assert doc["version"].startswith("DisasterZone") and doc["class"] == "paladin" and doc["level"] == 60, doc
    assert doc["talents"] == "", doc["talents"]
    help_text = c.eval("return ns.ImportExport:GetFrame().export.help:GetText()")
    assert "guildmate" in help_text and "wowsims" not in help_text.lower(), help_text
    texts = window_texts(c, "export")
    assert len(texts) > 10 and "DisasterZone text" in texts, texts
    assert "Your gear or a BiS phase as text a guildmate can import." in texts, texts   # (the banner)
    hits = site_hits(texts)
    assert not hits, hits
    no_errors(w)


@case
def test_import_reads_our_export_and_refuses_a_planner_link_on_forever():
    w, c = setup()
    doc = {"version": "DisasterZone 1", "class": "paladin", "gear": {"items": [{"id": LAWBRINGER_HELM}]}}
    p = c.eval_py("local p, e = ns.BiSImport:Parse(...); return { p and p.label or '', e or '' }", json.dumps(doc))
    assert p == ["DisasterZone export", ""], p
    p = c.eval_py("local p, e = ns.BiSImport:Parse(...); return { p and p.label or '', e or '' }",
                  "https://www.wowhead.com/forever/gear-planner/paladin/human/AwA")
    assert p[0] == "" and "can't be read on WoW Forever" in p[1], p
    nothing = c.eval_py("local p, e = ns.BiSImport:Parse(...); return e", "nothing here at all")
    assert "WoWSims" not in nothing and "gear planner" not in nothing, nothing
    hits = site_hits(window_texts(c, "import"))
    assert not hits, hits
    no_errors(w)


@case
def test_my_bis_texts_name_no_tbc_sites_on_forever():
    w, c = setup()
    c.eval("ns.MainFrame:Open('mybis')")
    w.tick(0.3)
    more = c.eval("return ns.MainFrame:GetPanel('mybis').moreBtn")
    assert "WoWSims" not in c.eval("local b = ...; return b.tipText or ''", more)
    c.click(more)
    entries = [strip_codes(e[2] or "") for e in menu_texts(c.last_menu())]
    assert "Export" in " ".join(entries), entries
    c.eval("ns.ImportExport:Open('export')")
    w.tick(0.1)
    no_errors(w)


@case
def test_tbc_client_keeps_wowsims_and_wowhead():
    w, c = setup(forever=False)
    assert c.eval("return ns.BiSExport:WowheadLink({})").startswith("https://www.wowhead.com/tbc/gear-planner/")
    c.eval("ns.ImportExport:Open('export')")
    w.tick(0.1)
    c.eval("ns.ImportExport:SetExport('bis', 'bulk')")
    assert c.eval("return ns.ImportExport:GetImportState().format") == "bulk"
    assert "WoWSims Bulk" in window_texts(c, "export")
    assert c.eval("return ns.BiSImport.FORMAT_LABELS.wowsims") == "WoWSims"
    no_errors(w)


if __name__ == "__main__":
    run_all()
