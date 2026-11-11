"""The game packs and the release on WoW Forever: what the TBC original shipped that a Forever player cannot use.

Covers: the chess hall draws its 3D room from the trimmed DisasterZone_Rooms (its TOC lists only Karazhan:Chess and
the shared stand-in tables, and a release ships only those); Council Bingo deals no square that only the combat log
can fill (Forever gives addons none), still fills the death squares by polling the group, and deals no TBC raid
pool; Azeromon's raid rares come loose on Forever's raid bosses (matched by name: Forever's raid data has no
encounter ids yet) and the guild hall's TBC wings stand open and empty, never "sealed".

Run: luaenv/bin/python tests/forever/test_forever_packs.py [-k name]
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
DEV = os.path.dirname(TESTS)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))
sys.path.insert(0, os.path.join(DEV, "tools"))

from _common import case, run_all, solo, no_errors, World, Client  # noqa: E402
import harness  # noqa: E402
import release  # noqa: E402

ROOMS = os.path.join(os.path.dirname(os.path.normpath(harness.ADDON_DIR)), harness.ROOMS_NAME)
SHIPPED_ROOMS = ["DisasterZone_Rooms.toc", "Load.lua", "Rooms/Karazhan_Chess.lua", "Standins/Gaps.lua",
                 "Standins/Karazhan_Chess.lua", "Standins/Modes.lua"]


# -- the 3D rooms ------------------------------------------------------------------------------------------------

@case
def the_rooms_toc_lists_only_the_chess_hall_and_a_release_ships_only_that():
    headers, files = harness.parse_toc(ROOMS, harness.ROOMS_NAME)
    assert headers.get("interface") == "16001", headers
    assert "raid trainer" not in headers.get("notes", "").lower(), headers.get("notes")
    assert files == SHIPPED_ROOMS[1:], files
    assert release.rooms_files(ROOMS) == SHIPPED_ROOMS
    assert sorted(release.rooms_hashes(harness.ADDON_DIR)) == sorted(SHIPPED_ROOMS)
    # the TBC rooms stay in the folder (the TBC-profile strategy suites), listed by the fixture TOC
    _, tbc = harness.parse_toc(harness.TBC_ROOMS_TOC_DIR, harness.ROOMS_NAME)
    assert "Rooms/BlackTemple_Illidan.lua" in tbc and "Rooms/Karazhan_Chess.lua" in tbc, len(tbc)
    for rel in tbc:
        assert os.path.isfile(os.path.join(ROOMS, rel)), rel
    # stage_tree copies only the listed files next to the staged addon
    tmp = tempfile.mkdtemp(prefix="dz_rooms_")
    try:
        record = release.stage_tree(harness.ADDON_DIR, os.path.join(tmp, "DisasterZone"), lua_only=True,
                                    rooms=True, packs=False)
        staged = []
        rdst = os.path.join(tmp, harness.ROOMS_NAME)
        for root, _, names in os.walk(rdst):
            staged += [os.path.relpath(os.path.join(root, n), rdst).replace("\\", "/") for n in names]
        assert sorted(staged) == sorted(SHIPPED_ROOMS), staged
        assert sorted(record["rooms"]) == sorted(SHIPPED_ROOMS)
        size = sum(os.path.getsize(os.path.join(rdst, f)) for f in staged)
        assert size < 1024 * 1024, size                    # (was ~19 MB with every TBC room)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@case
def the_chess_hall_draws_its_room_from_the_trimmed_rooms_on_forever():
    old = harness.LOAD_ROOMS
    harness.LOAD_ROOMS = True
    try:
        w, c = solo("Alice", forever=True, level=60)
        c.eval("ns.MainFrame:Open('games') ns.GamesUI:Select('chess')")
        w.tick(1)
        assert c.eval("return (C_AddOns.IsAddOnLoaded('DisasterZone_Rooms'))") is True
        st = c.eval_py("return ns.ChessUI:_State()")
        assert st["has3d"] is True, st
        floors = c.eval_py("local o = {} for k in pairs(ns.RoomFloors or {}) do o[#o + 1] = k end table.sort(o) "
                           "return o")
        assert floors == ["Karazhan_Chess"], floors
        assert not [x for x in c.load_warnings if harness.ROOMS_NAME in x], c.load_warnings
        gid = c.eval("local g = ns.Chess:NewAIGame(1, 'apprentice', false) "
                     "g.moves = { 'e2e4', 'd7d5' } ns.ChessUI:OpenGame(g) return g.id")
        w.tick(1)
        assert gid
        assert c.eval("local B = ns.ChessUI._Board3D() local n = 0 for _ in pairs(B.actors) do n = n + 1 end "
                      "return n") == 32
        no_errors(w)
    finally:
        harness.LOAD_ROOMS = old


# -- Council Bingo -----------------------------------------------------------------------------------------------

LOG_ONLY = ("overkill", "one_shot", "big_crit", "crushing", "ankh", "fall_death", "bres", "phoenix", "lust",
            "interrupts", "taunt_resist", "pet_death", "beat_clock", "feign_wipe")


def bingo_raid(forever=True, names=("Lee", "Rita", "Sam", "Bob")):
    w = World()
    c = {n: Client(w, n, guild_rank=3, forever=forever, level=60) for n in names}
    for x in c.values():
        x.load_addon()
    w.tick(3)
    w.make_raid(list(c.values()), leader=c[names[0]])
    w.tick(5)
    return w, c


def hits(cl):
    return set(cl.eval_py("local g = ns.Bingo:GetGame(); if not g then return {} end; "
                          "local t = {}; for id in pairs(g.hits) do t[#t+1] = id end; return t") or [])


@case
def bingo_deals_no_combat_log_square_on_forever():
    w, c = solo("Alice", forever=True, level=60)
    assert c.eval("return ns.Compat:CanUseCombatLog()") is False
    core = c.eval_py("local o = {} for _, sq in ipairs(ns.BingoSquares:Core()) do o[#o + 1] = sq.id end return o")
    assert len(core) >= 24, core                           # (a full card: 24 squares and the free centre)
    assert not set(core) & set(LOG_ONLY), set(core) & set(LOG_ONLY)
    assert not [i for i in core if c.eval("return ns.BingoSquares:NeedsLog(...)", i)], core
    # every card dealt from it, for many players and seeds
    for seed in ("s1", "s2", "s3"):
        for who in ("Alice-X", "Bob-X", "Carol-X", "Dan-X"):
            card = c.eval_py("local s, k = ... return ns.BingoCard.Deal(s, k, ns.BingoSquares:Core(), "
                             "ns.BingoSquares:Pool('kara'))", seed, who)
            ids = [x for x in card if x != "FREE"]
            assert len(ids) == 24 and len(set(ids)) == 24, card
            assert not [i for i in ids if c.eval("return ns.BingoSquares:NeedsLog(...)", i)], ids
    # the TBC raid pools are combat log rules: none is dealt on Forever
    for raid in ("kara", "gruul", "mag", "ssc"):
        assert c.eval("return #ns.BingoSquares:Pool(...)", raid) == 0, raid
        assert c.eval("return ns.BingoSquares:HasPool(...)", raid) is False, raid
    no_errors(w)
    # a TBC client still deals them
    w2, t = solo("Tom")
    assert t.eval("return ns.Compat:CanUseCombatLog()") is True
    tcore = t.eval_py("local o = {} for _, sq in ipairs(ns.BingoSquares:Core()) do o[#o + 1] = sq.id end return o")
    assert set(LOG_ONLY) <= set(tcore)
    assert t.eval("return #ns.BingoSquares:Pool('kara')") > 0


@case
def bingo_counts_deaths_without_a_combat_log():
    w, c = bingo_raid()
    lee = c["Lee"]
    lee.slash("/dz bingo start")
    w.tick(3)
    assert lee.eval("return ns.Bingo:IsActive() and ns.Bingo:IsHost()") is True
    w.set_dead("Bob")                                      # dead before any pull: trash
    w.tick(3)
    assert "death_trash" in hits(lee), hits(lee)
    w.set_dead("Bob", dead=False)
    w.tick(3)
    lee.fire("ENCOUNTER_START", 1084, "Onyxia", 9, 4)
    w.tick(3)
    w.set_dead("Sam")                                      # in the first 30 seconds of the pull
    w.tick(3)
    assert "death_first" in hits(lee), hits(lee)
    lee.fire("ENCOUNTER_END", 1084, "Onyxia", 9, 4, 1)
    w.tick(1)
    h = hits(lee)
    assert "speed_kill" in h and "late_death" in h and "flawless" not in h, h
    no_errors(w)


# -- Azeromon ----------------------------------------------------------------------------------------------------

@case
def azeromon_raid_rares_come_loose_on_forevers_raid_bosses():
    w, c = bingo_raid(names=("Lee", "Rita"))
    lee = c["Lee"]
    rares = lee.eval_py("local o = {} for _, r in ipairs(ns.AzeroData.raidRares) do o[#o + 1] = { r.boss, r.sp } end "
                        "return o")
    tbc = lee.eval_py("local o = {} for _, r in ipairs(ns.AzeroData.raidRaresTBC) do o[r.sp] = true end return o")
    assert {sp for _, sp in rares} == set(tbc), (rares, tbc)   # (every beast still has a way in)
    bosses = lee.eval_py("local o = {} for _, raid in ipairs(ns.Data.Raids) do for _, b in ipairs(raid.bosses) do "
                         "o[b.key] = b.name end end return o")
    for boss, sp in rares:
        assert boss in bosses, (boss, sp)
    w.enter_instance(name="Onyxia's Lair", instance_id=249, instance_type="raid", max_players=40)
    w.tick(1)
    w.encounter(1084, "Onyxia", success=True)
    w.tick(1)
    store = lee.eval_py("local s = ns.Azero:RaidRareStore() local o = {} for k in pairs(s) do o[#o + 1] = k end "
                        "return o")
    assert {"nightbane", "corehound"} <= set(store), store
    assert "midnight" not in store, store
    # the hall (Forever 0.2): Forever's three raids move into the TBC wings whose plinths fit them; the other wings
    # stay roped off as "an unfinished wing", and no banner names a TBC raid
    wings = lee.eval_py("local H = ns.AzeroHideout local o = {} for _, wg in ipairs(H.ART.wings) do "
                        "local n, t = H.WingCount(wg.key) o[wg.key] = { open = H.WingOpen(wg.key), n = n, t = t, "
                        "line = H.WingLine(wg.key) } end return o")
    tbc = ("Karazhan", "Gruul", "Magtheridon", "Serpentshrine", "Tempest", "Black Temple", "Zul'Aman", "Sunwell",
           "Mount Hyjal")
    for k, v in wings.items():
        assert not any(t in v["line"] for t in tbc), (k, v)
    assert wings["Karazhan"]["t"] == 8 and wings["Karazhan"]["line"].startswith("Barrow Deeps: "), wings["Karazhan"]
    assert wings["HyjalSummit"]["t"] == 13 and wings["BlackTemple"]["line"].startswith("Hyjal Summit: "), wings
    for k in ("GruulsLair", "SerpentshrineCavern", "TempestKeep", "ZulAman", "SunwellPlateau"):
        assert wings[k] == {"open": False, "n": 0, "t": 0, "line": "An unfinished wing: no raid of ours fills it yet"}, \
            (k, wings[k])
    # the Onyxia kill above put a trophy on Onyxia's plinth (matched on the boss's name: no encounter ids yet)
    assert wings["MagtheridonsLair"] == {"open": True, "n": 1, "t": 1, "line": "Onyxia's Lair: its trophy stands"}, \
        wings["MagtheridonsLair"]
    plinths = lee.eval_py("local o = {} for _, p in pairs(ns.AzeroMaps.hideout.objects) do "
                          "if p.boss then o[#o + 1] = p.boss.raid .. ':' .. p.boss.name end end return o")
    assert len(plinths) == 1 + 8 + 13 and "HyjalForever:Nythus the Dreambound" in plinths, plinths
    no_errors(w)


if __name__ == "__main__":
    run_all(globals())
