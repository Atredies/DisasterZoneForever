"""Errors in normal play on WoW Forever (Final Scan 2026-11-09, Forever API risks 1-3, 8-10):

  * chat payloads are secret during a boss pull (SecretInChatMessagingLockdown): DisasterZone skips a CHAT_MSG_*
    event (and READY_CHECK, GUILD_MOTD, the countdowns) whose payload it may not read, in the Core/Init.lua dispatcher
    and in the two direct frames of Core/Recruit.lua and Core/RecruitIntro.lua
  * globals gone on the retail engine, rebuilt by Core/Compat.lua from their C_ names: ConvertToRaid, GuildInvite,
    CanEditOfficerNote, GuildRosterSetOfficerNote (C_GuildInfo.SetNote by GUID), PickupSpell, IsAutoRepeatSpell,
    GetNumQuestWatches, GetZonePVPInfo, OffhandHasWeapon
  * LEARNED_SPELL_IN_TAB is LEARNED_SPELL_IN_SKILL_LINE; kills come from PARTY_KILL / UNIT_DIED (no combat log)
  * the game packs' Escape key must not call the protected SetPropagateKeyboardInput in combat
  * Forever is still recognised by the interface number when WOW_PROJECT_ID is missing

Run: luaenv/bin/python tests/forever/test_forever_api_shims.py [-k name]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "boot-ui"))

from _common import case, run_all, solo, no_errors  # noqa: E402
from harness import World, Client  # noqa: E402

SHIMMED = ["CanEditOfficerNote", "ConvertToRaid", "GetNumQuestWatches", "GetZonePVPInfo", "GuildInvite",
           "GuildRosterSetOfficerNote", "IsAutoRepeatSpell", "OffhandHasWeapon", "PickupSpell"]


def gm(**kw):
    return solo("Arakis", class_file="WARRIOR", guild_rank=0, level=60, forever=True,
                members=[("Bobby", "MAGE", 4)], **kw)


def pull(c):
    c.fire("ENCOUNTER_START", 2741, "Rhahk'Zor", 1, 5)
    assert c.eval("return C_ChatInfo.InChatMessagingLockdown()") is True


def end_pull(c):
    c.fire("ENCOUNTER_END", 2741, "Rhahk'Zor", 1, 5, 1)


@case
def test_removed_globals_are_rebuilt_from_c_names():
    w, c = gm()
    shimmed = c.eval_py("return ns.Compat.shimmed")
    for name in SHIMMED:
        assert name in shimmed, (name, shimmed)
    assert c.eval("return ConvertToRaid == C_PartyInfo.ConvertToRaid") is True
    assert c.eval("return GuildInvite == C_GuildInfo.Invite") is True
    assert c.eval("return CanEditOfficerNote == C_GuildInfo.CanEditOfficerNote") is True
    assert c.eval("return PickupSpell == C_Spell.PickupSpell") is True
    assert c.eval("return GetZonePVPInfo()") == "sanctuary"
    assert c.eval("return OffhandHasWeapon()") is False
    assert c.eval("return GetNumQuestWatches()") == 0
    assert c.eval("return IsAutoRepeatSpell('Shoot')") is False
    no_errors(w)


@case
def test_tbc_keeps_its_own_globals():
    w, c = solo("Arakis", class_file="WARRIOR", guild_rank=0)
    shimmed = c.eval_py("return ns.Compat.shimmed") or []
    for name in ("ConvertToRaid", "GuildInvite", "CanEditOfficerNote", "GuildRosterSetOfficerNote", "GetZonePVPInfo",
                 "OffhandHasWeapon"):
        assert name not in shimmed, name
    assert c.eval("return ns.Compat.isForever") is False
    no_errors(w)


@case
def test_forever_detected_by_interface_number():
    w = World()
    c = Client(w, "Arakis", class_file="WARRIOR", guild_rank=0, level=60, forever=True)
    c.eval("WOW_PROJECT_ID = nil")
    c.load_addon()
    w.tick(2)
    assert c.eval("return ns.Compat.isForever") is True
    no_errors(w)


@case
def test_convert_to_raid_uses_c_party_info():
    w, c = gm()
    c.eval("ConvertToRaid()")
    assert c.eval("return __MOCK.forever_converted") == 1
    no_errors(w)


@case
def test_guild_invite_and_officer_note():
    w, c = gm()
    c.eval("GuildInvite('Bobby')")
    w.tick(1)
    log = getattr(w, "guild_invite_log", [])
    assert log and log[-1]["target"] == "Bobby", log
    i = c.eval("""
      for i = 1, GetNumGuildMembers() do
        if (GetGuildRosterInfo(i)) == 'Bobby' then return i end
      end""")
    assert i, "Bobby not on the roster"
    c.eval("GuildRosterSetOfficerNote(...)", i, "Recruit 2026")
    w.tick(1)
    notes = c.eval_py("return __MOCK.forever_set_notes")
    assert notes and notes[-1]["note"] == "Recruit 2026" and notes[-1]["public"] is False, notes
    assert c.eval("return (select(8, GetGuildRosterInfo(...)))", i) == "Recruit 2026"
    no_errors(w)


@case
def test_chat_payloads_secret_in_a_pull_are_skipped():
    w, c = gm()
    c.eval("""
      __seen = {}
      ns:RegisterEvent('CHAT_MSG_SYSTEM', function(_, text) __seen[#__seen + 1] = text:upper() end)
    """)
    pull(c)
    for ev, args in (("CHAT_MSG_SYSTEM", ("Bobby has joined the guild.",)),
                     ("CHAT_MSG_SYSTEM", ("Bobby declines your guild invitation.",)),
                     ("CHAT_MSG_WHISPER", ("res pls", "Bobby-Realm", "", "", "Bobby")),
                     ("CHAT_MSG_RAID", ("+ reserve", "Bobby-Realm")),
                     ("CHAT_MSG_RAID_LEADER", ("hi", "Arakis")),
                     ("CHAT_MSG_MONSTER_YELL", ("Ugh!", "Rhahk'Zor")),
                     ("CHAT_MSG_RAID_BOSS_EMOTE", ("%s goes into a frenzy!", "Rhahk'Zor")),
                     ("CHAT_MSG_LOOT", ("You receive loot: [Linen Cloth].",)),
                     ("READY_CHECK", ("Arakis", 30))):
        c.fire(ev, *args)
        w.tick(0.1)
    assert c.eval("return __MOCK.chat_secret_fired") >= 9
    assert c.eval("return #__seen") == 0
    end_pull(c)
    c.fire("CHAT_MSG_SYSTEM", "Bobby has joined the guild.")
    w.tick(0.5)
    assert c.eval("return __seen[1]") == "BOBBY HAS JOINED THE GUILD."
    no_errors(w)


@case
def test_learned_spell_uses_the_skill_line_event():
    w, c = gm()
    c.eval("""
      __learned = 0
      ns:RegisterEvent('LEARNED_SPELL_IN_SKILL_LINE', function() __learned = __learned + 1 end)
    """)
    c.fire("LEARNED_SPELL_IN_SKILL_LINE", 6343, 2, False)
    w.tick(1)
    assert c.eval("return __learned") == 1
    no_errors(w)


@case
def test_kills_without_a_combat_log():
    w, c = gm()
    me = c.eval("return UnitGUID('player')")
    # out in the world: plain GUIDs; in an instance: secret (nothing counted, nothing raised)
    c.eval("__MOCK.party_kill(...)", me, "Creature-0-0-0-0-38-0000000001")
    c.eval("__MOCK.unit_died(...)", "Creature-0-0-0-0-38-0000000001")
    w.enter_instance(name="The Deadmines", instance_id=36, instance_type="party", max_players=5, difficulty_id=1)
    w.tick(1)
    c.eval("__MOCK.party_kill(...)", me, "Creature-0-0-0-0-644-0000000002")
    c.eval("__MOCK.unit_died(...)", "Creature-0-0-0-0-644-0000000002")
    w.tick(1)
    assert not c.eval_py("return __MOCK.forbidden"), "the combat log was registered"
    no_errors(w)


@case
def test_pack_escape_in_combat_is_not_blocked():
    w, c = solo("Alice", class_file="PALADIN", forever=True)
    c.eval("ns.Games:Open('holdtheline')")
    w.tick(1.0)
    c.set_combat(True)
    c.eval("ns.HTLUI._Key('ESCAPE')")
    assert not c.eval_py("return __MOCK.blocked"), c.eval_py("return __MOCK.blocked")
    c.set_combat(False)
    w.tick(0.2)
    c.eval("ns.Games:Open('azeromon')")
    w.tick(1.0)
    c.set_combat(True)
    c.eval("local r = ns.AzeroUI._Root() if r then r:GetScript('OnKeyDown')(r, 'ESCAPE') end")
    assert not c.eval_py("return __MOCK.blocked"), c.eval_py("return __MOCK.blocked")
    c.set_combat(False)
    w.tick(0.5)
    no_errors(w)


if __name__ == "__main__":
    run_all(globals())
