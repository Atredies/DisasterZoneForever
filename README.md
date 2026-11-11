# DisasterZone for WoW Forever

The guild addon of **&lt;Casual Disaster&gt;** for **WoW Forever** (client 1.60.1). It handles raid sign-ups,
polls, BiS lists, loot council and rolls, the guild roster, and a few small guild games.

## Download

**[Download the latest release](https://github.com/Atredies/DisasterZoneForever/releases/latest)**: under *Assets*,
click **`DisasterZone-<version>.zip`** (today that is `DisasterZone-0.2.3.zip`).

Older versions are on the [Releases page](https://github.com/Atredies/DisasterZoneForever/releases).
Don't use GitHub's green "Code > Download ZIP" button: that gives you the source code, not the addon.

## Install

1. **Close the game.**
2. Open your WoW folder and go to `World of Warcraft\_forever_\Interface\AddOns`.
   (If `AddOns` doesn't exist yet, create it.)
3. Unzip the zip into `AddOns`. The folders must sit **directly** in `AddOns`, like this:

   ```
   AddOns\
     DisasterZone\               <- the addon (required)
       DisasterZone.toc
     DisasterZone_Rooms\         <- needed by Chess
     DisasterZone_Bingo\         <- optional game
     DisasterZone_Azeromon\      <- optional game
     DisasterZone_HoldTheLine\   <- optional game
     DisasterZone_Chess\         <- optional game
   ```

   If you end up with `AddOns\DisasterZone-0.2.3\DisasterZone\...` (an extra folder level), move the inner folders up one level.
4. **Start the game.** On the character screen, click **AddOns** and make sure DisasterZone is ticked.
5. In game, type `/dz` to open it. `/dz version` shows which version you and your guildmates run.

## Update to a new version

**From 0.2.3 on, updates come in game.** When a guildmate who has a newer update is online, it downloads in the
background and DisasterZone tells you. Type **`/dz update`**: it installs it (your interface reloads). You can also
type `/dz update` any time to ask the guild for the newest one. Updates are signed: your copy only takes the ones
signed with this project's key.

A new zip is only needed when an update brings new art or new folders (the release notes say so), or to go from
0.2.2 or older to 0.2.3:

1. Close the game.
2. Delete the old `DisasterZone*` folders from `AddOns`.
3. Unzip the new zip there, the same way as above, and start the game.

Your settings and game progress are kept: they live in your saved variables, not in these folders.

## Discord (optional)

The guild's Discord bot shows raids, sign-ups and BiS lists, and lets you sign up or change your list from Discord.
**You don't need anything for that to reach the guild's game:** what people do in Discord reaches everyone's addon
through any guildmate who runs the launcher. To link your own game:

1. Install the **DisasterZone Forever Launcher** from the release page (Windows: the `-setup.exe`. Windows warns
   that the publisher is unknown: **More info > Run anyway**. Linux: the `.AppImage`).
2. In the launcher's **Settings**, pick your World of Warcraft folder (the one that holds `_forever_`).
3. In the guild's Discord, type `/launcher` and paste the code it gives you under **Link this launcher**.
4. Once: `/character` in Discord to add your character (or just press a raid's sign-up button).

The launcher then syncs in the background while you play (every couple of minutes, and after each `/reload`).

## Something wrong?

- Type `/dz bug` in game straight away and say what you were doing. The report is saved with your settings.
- Or tell an officer in guild chat or Discord.
- Not loading at all? Check that `DisasterZone.toc` sits at `AddOns\DisasterZone\DisasterZone.toc`, and that you
  restarted the game (a `/reload` doesn't pick up new folders).

Versions 0.x are test builds. 1.0.0 comes when we go live.

## More reading

The project's notes live in the Obsidian vault in [`_DisasterZoneForever-vault/`](_DisasterZoneForever-vault/Home.md). You can read them on
GitHub, or open the folder as a vault in [Obsidian](https://obsidian.md). Useful starting points:

**Players**

| Read this | For |
|---|---|
| [Player guide](addon/DisasterZone/README.md) | Every page and slash command in the addon |
| [Changelog](_DisasterZoneForever-vault/07-Log/Changelog.md) | What changed in each version (release notes per version: [`dev/releases/`](dev/releases/)) |
| [How Sync Works](_DisasterZoneForever-vault/01-Overview/How%20Sync%20Works.md) | Why a new event or sign-up takes up to a minute to show for everyone, and why messages wait during a boss pull |
| [Multi-player Test Plan](_DisasterZoneForever-vault/04-Roadmap/Multi-player%20Test%20Plan.md) | The guild test session: who does what, and what to look out for |
| [Forever Content Facts](_DisasterZoneForever-vault/09-Reference/Forever%20Content%20Facts.md) | The Forever raids, dungeons and content the addon knows about |

**Project**

| Read this | For |
|---|---|
| [Home](_DisasterZoneForever-vault/Home.md) | Index of the notes |
| [Project Overview](_DisasterZoneForever-vault/01-Overview/Project%20Overview.md) | What DisasterZone does and who uses it |
| [Decision Log](_DisasterZoneForever-vault/07-Log/Decision%20Log.md) | Why things are the way they are |

**Developers**

| Read this | For |
|---|---|
| [Developer Guide](_DisasterZoneForever-vault/06-Operations/Developer%20Guide.md) | Repo layout, everyday commands, tests, making a change, releasing |
| [Linux Dev Setup](_DisasterZoneForever-vault/06-Operations/Linux%20Dev%20Setup.md) | One-time setup of the Python/Lua test environment |
| [Adding a Feature](_DisasterZoneForever-vault/06-Operations/Adding%20a%20Feature.md) · [Testing with Forever Data](_DisasterZoneForever-vault/06-Operations/Testing%20with%20Forever%20Data.md) | Adding a feature; how the offline mock client and Forever replays work |
| [Adding a Forever Raid](_DisasterZoneForever-vault/06-Operations/Adding%20a%20Forever%20Raid.md) | Filling in a new raid's data once it opens |
| [Code Map](_DisasterZoneForever-vault/08-Code-Map/Code%20Map.md) | Where each part of the code lives |

## Credits

DisasterZone was written by **tsumilo** for &lt;Casual Disaster&gt; on TBC Anniversary; this is a fork of
[tsumilo/DisasterZone-dev](https://github.com/tsumilo/DisasterZone-dev) for WoW Forever. The launcher in `launcher/`
is MIT (`launcher/LICENSE`). The item data is generated from **AtlasLoot Classic** (GPL v2). Libraries, data sources
and art credits: [`addon/DisasterZone/NOTICE.md`](addon/DisasterZone/NOTICE.md). World of Warcraft names, IDs and game
art belong to Blizzard Entertainment.
