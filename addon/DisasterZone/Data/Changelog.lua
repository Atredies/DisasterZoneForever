if DisasterZoneBoot and DisasterZoneBoot.Run("Data/Changelog.lua", ...) then return end -- DisasterZone: Data/Changelog.lua
-- The release notes shown in the Changelog tab and the What's New pop-up, newest release first (DisasterZone for WoW
-- Forever). Versions restarted at 0.1.0 for Forever: test builds are 0.x, go-live is 1.0.0, and 1.5.5 is never used
-- (Util.PRE_FOREVER_VERSION). To add a release: put a new table at the top with the version it ships as. A version
-- newer than the installed one is shown as "In testing" until the TOC version catches up. Sections group the changes;
-- one short line per change, in plain words, saying what players notice. (The TBC original's notes describe TBC and
-- stay out of the game: dev/fixtures/tbc/Data/Changelog.lua and the git history.)
local addonName, ns = ...

ns.CHANGELOG = {
    { version = "0.2.3", date = "12 November 2026", title = "Updates in game, and the guild's Discord",
      sections = {
          { heading = "Updates in game", area = "other", kind = "new", hi = true,
            lead = "This is the last version you install from a zip.", lines = {
              "New versions now reach you in game from your guildmates.",
              "Once one is downloaded, type /dz update to install it (the interface reloads).",
              "/dz update also asks the guild for the newest update at any time.",
          } },
          { heading = "Discord", area = "other", kind = "new", lines = {
              "The guild's Discord bot works with Forever: raids, sign-ups and BiS lists.",
              "Sign-ups and BiS changes made in Discord reach your game, launcher or not.",
          } },
      } },
    { version = "0.2.2", date = "10 November 2026", title = "Sync you can see, cleaner recruitment posts",
      sections = {
          { heading = "Sync", area = "other", kind = "fixed", hi = true,
            lead = "When your copy can't read someone's BiS list, it says so.", lines = {
              "Before, it was dropped without a word (a 0.2.0 copy and Forever's new items).",
              "It names the player; update if they run a newer version (/dz version).",
          } },
          { heading = "Recruitment message", area = "other", kind = "fixed", lines = {
              "Channels like Trade get it without raid icons (the game doesn't draw them there).",
              "Say and Yell keep the icons.",
              "GuildRecruitment is off by default; the skip line tells you to /join GuildRecruitment.",
          } },
      } },
    { version = "0.2.1", date = "10 November 2026", title = "Fixes from the first guild test",
      sections = {
          { heading = "Forever's new items", area = "raids", kind = "fixed", hi = true,
            lead = "Items from Forever's new dungeons work everywhere now.", lines = {
              "/dz roll takes them (it printed its help line instead).",
              "My BiS takes them, including the \"Loot (boss not confirmed)\" lists.",
              "Loot log, council and sync keep them instead of dropping them.",
          } },
          { heading = "List a group", area = "raids", kind = "fixed", lines = {
              "Dungeon tiles fit the window: six per level band, none past the edge.",
              "Long names are shortened (LBRS, DM: East...); the tooltip shows the full name.",
              "Every level band has its picture again.",
          } },
      } },
    { version = "0.2.0", date = "10 November 2026", title = "Second test build: playing together",
      sections = {
          { heading = "Test it together", area = "other", kind = "new", hi = true,
            lead = "This build is for testing with two or three guildmates.", lines = {
              "/dz version shows which version everyone runs.",
              "Anything wrong: /dz bug right away, and say what you were doing.",
          } },
          { heading = "The guild's data is safer", area = "guild", kind = "changed", hi = true,
            lead = "Shared records only change when someone allowed to change them did it.", lines = {
              "Events, sign-ups, polls, raid plans and council lists can't be forged.",
              "The Guild Master picks which ranks are officers: Settings > Guild > Officers.",
              "Records passed on by someone else say who passed them on, until confirmed.",
          } },
          { heading = "Loot", area = "raids", kind = "changed", lines = {
              "Two identical drops: under soft reserves each copy goes to another reserver.",
              "The loot log keeps both copies when one player wins two of the same item.",
              "Reload during a roll: the roll window comes back with the time that is left.",
              "Items for one class only are treated that way in loot decisions.",
              "The \"who wants this\" lines are back on item tooltips.",
          } },
          { heading = "Sync and raid night", area = "raids", kind = "changed", lines = {
              "After a big login everyone gets every event, sign-up and list, no /reload.",
              "Pull and break timers, class planner and LootReserve messages wait out a pull.",
              "The raid bar finds Forever's raids and their bosses.",
          } },
          { heading = "Forever, not TBC", area = "other", kind = "changed", lines = {
              "Azeromon's Guild Hall has wings for Onyxia, Barrow Deeps and Hyjal Summit.",
              "Shamans don't dual wield on Forever: no off-hand weapons offered to them.",
          } },
      } },
    { version = "0.1.0", date = "9 November 2026", title = "First test build for WoW Forever",
      sections = {
          { heading = "First test build", area = "other", kind = "new", hi = true,
            lead = "<Casual Disaster>'s addon for WoW Forever, in its first test build.", lines = {
              "Expect rough edges, and tell us what breaks: type /dz bug in game.",
              "Versions start again at 0.1.0; 1.0.0 comes when Forever goes live.",
              "In-game updates are off for now: each new version is a download from GitHub.",
          } },
          { heading = "What works", area = "raids", kind = "new", hi = true,
            lead = "Raid plans, loot council, members and games run on Forever's data.", lines = {
              "Raid planner: Barrow Deeps (10), Hyjal Summit (20) and Onyxia's Lair (40), level 60.",
              "Gear tiers are seasons: Pre-raid and Season 1 on My BiS, the council and Settings.",
              "Names with surnames work everywhere: the roster, raids, loot and the guild master.",
              "Messages wait out a boss pull (Forever holds them while you fight) and arrive after.",
          } },
          { heading = "Items and the Atlas", area = "gear", kind = "changed", open = "atlas",
            lead = "Every item list is Forever's, checked against Forever's item database.", lines = {
              "The Atlas lists Forever's 35 dungeons, then crafting, reputation and PvP.",
              "New dungeons with no recorded drops yet: one list, \"Loot (boss not confirmed)\".",
              "The raids' loot comes once they open on 9 December.",
              "The item picker finds dungeon, crafted, reputation and PvP gear; no badge vendors.",
              "Gems and enchants: no sockets on Forever, so only enchants.",
              "Consumables: a level-60 kit per spec (flasks, elixirs, food, stones and oils).",
          } },
          { heading = "Groups", area = "raids", kind = "changed", open = "dungeons",
            lead = "The Groups board knows Forever.", lines = {
              "Dungeons by level band, the new ones included; no heroics, keys or dailies.",
              "PvP: Warsong Gulch, Arathi Basin, Alterac Valley and Darkspear Islands.",
          } },
          { heading = "Class tools", area = "class", kind = "changed", lines = {
              "Paladins: Forever's blessings, an hour each; no Salvation, Light or Sanctuary.",
              "Greater Blessings need no Symbol of Kings.",
              "Shamans: no Totem of Wrath, Wrath of Air or elementals in the totem planner.",
          } },
          { heading = "Hidden on Forever (for now)", area = "other", kind = "changed",
            lead = "Some pages wait for Forever data, or for what Forever lets addons see.", lines = {
              "Gear sim, My Log and the strategy boards are hidden for now.",
              "Boss mods stay quiet: Forever gives addons no combat log.",
              "Games: The Binding of Illidan and the Raid Trainer are gone.",
              "Bingo, Chess, Azeromon and Hold the Line stay.",
          } },
          { heading = "Something wrong? Tell us", area = "other", kind = "new", open = "feedback",
            lead = "Report bugs and ideas in game: Feedback carries them through the guild.", lines = {
              "Something broke? Type /dz bug: the last Lua error goes with your report.",
              "/dz idea sends an idea; /dz feedback opens every report and its answers.",
              "DisasterZone's own Lua errors report themselves (Settings > Alerts turns it off).",
              "Say what you were doing and where: it is a test build, every report helps.",
          } },
      } },
}
