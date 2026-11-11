# DisasterZone for WoW Forever

The guild addon of **&lt;Casual Disaster&gt;** on **WoW Forever** (client 1.60.1, Interface 16001).

- Every player keeps a best-in-slot (BiS) list: a Pre-raid list and a Season 1 list, with a main and an alt pick per
  slot, plus an optional off-spec list.
- The Loot Council sees everyone's lists. When a boss is looted, the council sees who has each drop on their list.
- Raiders get a Roll / Pass popup. Council members can vote. DisasterZone suggests a winner, the council confirms it,
  and the award goes into a shared loot log with a reason (BiS, Alt, Offspec, Disenchant, ...).
- Raid sign-ups, teams and groups, guests, attendance, soft reserves, the guild's dungeon groups, members and
  recipes, polls, recruitment, and a few games to play together.

DisasterZone only suggests. The council makes the loot decision.

DisasterZone was written by tsumilo for TBC Anniversary. This is the Forever version: Forever's raids, dungeons, items
and seasons, and only the features that work on Forever. See [What is not on Forever (yet)](#what-is-not-on-forever-yet).

---

## Contents

1. [Install and update](#install-and-update)
2. [Opening DisasterZone](#opening-disasterzone)
3. [Forever in DisasterZone](#forever-in-disasterzone)
4. [Before the first raid](#before-the-first-raid)
5. [Raider: My BiS](#raider-my-bis)
6. [The Atlas](#the-atlas)
7. [Raids: sign-ups, teams and the raid night](#raids-sign-ups-teams-and-the-raid-night)
8. [Groups, Members and the other guild pages](#groups-members-and-the-other-guild-pages)
9. [Loot Council](#loot-council)
10. [Raid leader](#raid-leader)
11. [Guild Master](#guild-master)
12. [How rolls pick a suggested winner](#how-rolls-pick-a-suggested-winner)
13. [Settings](#settings)
14. [Demo mode](#demo-mode)
15. [What is not on Forever (yet)](#what-is-not-on-forever-yet)
16. [Slash commands](#slash-commands)
17. [FAQ and troubleshooting](#faq-and-troubleshooting)
18. [How it syncs, and privacy](#how-it-syncs-and-privacy)

---

## Install and update

**Requirements:** the WoW Forever client. Every library DisasterZone uses is built in, so no other addon is needed.

### Install
1. Download `DisasterZone-<version>.zip` from <https://github.com/Atredies/DisasterZoneForever/releases> and close
   the game.
2. Unzip it into `World of Warcraft\_forever_\Interface\AddOns\` (or copy the `DisasterZone` folder there).
   The result must be `...\_forever_\Interface\AddOns\DisasterZone\DisasterZone.toc`.
   The folder must be named exactly `DisasterZone`. Names such as `DisasterZone-main` or a folder nested inside
   another `DisasterZone` folder won't load.
3. The games are optional addon folders next to it: `DisasterZone_Bingo`, `DisasterZone_Chess` (with
   `DisasterZone_Rooms`), `DisasterZone_Azeromon` and `DisasterZone_HoldTheLine`. Copy the ones you want.
4. Start the game. On the character screen, open **AddOns** and make sure DisasterZone is ticked.
5. In game, type `/dz` to check that it loaded.

### Update
1. Close the game.
2. Delete the old `Interface\AddOns\DisasterZone` folder, then copy the new one in. Replacing the whole folder makes
   sure no old files are left behind.
3. Start the game and check the version with `/dz version`. The first line shows your own version.

Your data is safe when you update. Lists, settings and the loot log are stored in
`_forever_\WTF\Account\<ACCOUNT>\SavedVariables\DisasterZone.lua`, not in the addon folder. That file is shared by
every character on the account; each character still keeps its own BiS list.

**In-game updates.** DisasterZone can receive signed updates over the guild's addon channel (a popup then asks you to
reload). The Forever version has no signing keys yet, so in-game updates are off and every update is a new zip from
the releases page, unzipped by hand. Test builds are 0.x (0.1.0 is the first); 1.0.0 comes when Forever goes live.

Everyone should run the same version. See [Mixed versions](#mixed-versions).

---

## Opening DisasterZone

| How | What it does |
|---|---|
| `/dz` or `/disasterzone` | Opens or closes the window (it opens on Home) |
| Minimap button | Left-click opens the window. Right-click opens Settings. Shift-click opens the boss drop panel. |

The top of the window holds the pages. Some are grouped under one tab; rest the mouse on it to see its pages.

| Tab | Pages |
|---|---|
| **Home** | What needs you now: the next raids (sign up in one click), your BiS picks that can drop there, players asking to join your group, a newer DisasterZone, what's new |
| **Raids** | **Raids** (sign-ups, teams, guests, raid log), **Council** (loot council members), **Loot rules** (how the council decides; for everyone) |
| **Gear** | **My BiS**, **Consumables** (a level-60 kit per spec), **Wardrobe** (outfits you swap in one click), **Atlas** |
| **Guild** | **Members**, **Map**, **Events** (beta), **Polls**, **Recruitment**, **Audit log** (guild council and GM), **Games** |
| **Groups** | The guild's dungeon, raid, PvP and other groups |
| **Settings**, **Changelog**, **Feedback** | Settings, what changed in each version, and reporting a bug or an idea |

The bell next to the tabs collects notifications. The mark at the top right shows your list's sharing status. See
[Sync status](#what-does-the-sync-status-mean).

---

## Forever in DisasterZone

| | On Forever |
|---|---|
| Level cap | 60 |
| Raids | **Barrow Deeps** (10 players), **Hyjal Summit** (20) and **Onyxia's Lair** (40). All three open on 9 December 2026. |
| Gear tiers | **Seasons**. My BiS has a **Pre-raid** list and **Season 1** (S1). Where the TBC addon said "Phase", Forever says "Season". |
| Dungeons | 35 dungeons, normal only: no heroics, keys or dailies |
| Battlegrounds | Warsong Gulch, Arathi Basin, Alterac Valley and Darkspear Islands. No arena. |
| Items | Every item is checked against Forever's item database. No gems, sockets, Jewelcrafting, badges or tier tokens. |
| Names | Forever names are first name and surname ("Name Surname"). DisasterZone keys players by the full name. |
| Addon messages | Forever holds addon messages during a boss pull. DisasterZone queues them and sends them when the pull ends. |

Raid loot is empty until the raids open: DisasterZone never shows an item it isn't sure drops there. New dungeons whose
drops nobody has recorded yet show one list, "Loot (boss not confirmed)".

---

## Before the first raid

- [ ] **Everyone** runs the same DisasterZone version. The raid leader checks with `/dz version`.
- [ ] **Everyone** has filled in their My BiS list for Season 1, and the status says "Shared with council".
- [ ] **Guild Master** has picked the guild council (see [Guild Master](#guild-master)).
- [ ] **Raid leader** has set the group loot rules and, if wanted, extra raid council members (see [Raid leader](#raid-leader)).
- [ ] **Master looter** has set the loot method to Master Looter if DisasterZone should hand items out.
- [ ] **Everyone** knows how to report a Lua error (see [Reporting a Lua error](#reporting-a-lua-error)).

---

## Raider: My BiS

Open it with **Gear > My BiS** or `/dz bis`.

### Build your list

The top bar:

- **Pre-raid** / **S1**: which list you are editing. Pre-raid is for dungeons, reputation, crafting and PvP gear; only
  you see it. Season 1 is the raid list the council sees.
- **Main spec** / **Off spec**: which of your two lists the page shows. See [Off-spec list](#off-spec-list).
- **Spec**: pick your spec, or **Auto-detect**.
- **Copy from**: copy the other list into this one (fill empty slots, or overwrite).
- **Suggest** is empty on Forever: there are no reliable Forever BiS guides yet, so you build your list by hand.
- **More (...)**: **Import**, **Export** and **Clear**.
  - **Import** takes a That's My BiS CSV ("Just Wishlists"), a Sixty Upgrades export, or item links, item numbers or
    item names, one per line. The preview shows what fits and what doesn't.
  - **Export** gives your list or your worn gear as text. The WoWSims and Wowhead formats there still point at the TBC
    sites; don't rely on them on Forever.

Below the bar is a paper doll. Each slot has a **main** pick (the large icon) and an **alt** pick (the small icon).

- **Click a slot** to open the item picker. **Click the small square** to choose an alt.
- **Drag an item from your bags onto a slot** to use any item, including items the picker doesn't list.
- **Shift-click** an icon to link the item in chat.
- **Right-click a slot** for: choose main / alt, swap main and alt, mark obtained or not obtained, clear, link,
  and disable the slot.

A **disabled** slot (for example the off hand when you use a two-hander) turns grey and is left out of your progress,
the council's need counts and drop alerts. Your pick is kept.

### The item picker

- **Search** matches item names, bosses, professions, factions and vendors.
- **Sources**: Raids, 5-man dungeons, Crafted, Reputation and PvP. The default is Raids + 5-man dungeons.
  PvP items and faction-only reputation items are shown for your own faction only.
- **Usable by my class** and **My armor type only** are on by default.
- Each row shows where the item comes from, for example "Blacksmithing (300)" or a faction and standing.
  "Main" or "Alt" on the right means it is already on your list; "owned" means you have it.

### Obtained detection

A pick is marked obtained on its own when you wear it, carry it, or have it in your bank (the bank is only read while
its window is open, so visit it once). **Mark obtained** sets it by hand.

### Sharing

You don't need to do anything. Changes go to online council members about 8 seconds after your last edit, or when you
close the window. The status shows at the top right of the window and on the My BiS card.

### Off-spec list

Next to your main list you can keep one **off-spec** list, for example tank gear as a Fury warrior.

- Click **+ Off spec** in the top bar, choose the spec, and pick items as usual.
- Off-spec wanters are listed **after** everyone who has the item on their main list, with an **[OS]** badge.
- In a roll, an off-spec pick ranks after main-spec BiS and alt picks, but before players who don't list the item.
- An item won through your off-spec list is recorded as **Offspec** and doesn't count as loot received.
- To delete the list, choose **Remove off-spec list...** in the off spec's **Spec** dropdown.

Alts: every character has its own list. Log in on the alt and fill in its My BiS.

### When loot drops

- **Toast:** "On your BiS list!" with the item, the slot and whether it's your main or alt pick.
- **Chat line** and a **Yours** badge with a glow in the loot window.

### The roll popup

When the council starts a roll, a popup shows the item, your status for it, what you wear in that slot and a
countdown. **Roll** does a normal `/roll` (1-100); **Pass** passes.

- Typing `/roll` in chat counts too, so players without DisasterZone can still roll.
- Only a 1-100 roll counts, and only your **first** roll.
- One item is rolled at a time. The others wait in a queue.

### Tooltips

Item tooltips show your own status ("Your S1 BiS (main) - Head", "obtained"), and who in the guild can craft the item.

### When lists are locked

During a raid the raid leader can lock everyone's lists. My BiS then shows "BiS lists locked by *name*", and you can't
change picks, spec or disabled slots. Obtained items still update and sync.

---

## The Atlas

**Gear > Atlas** is a loot browser, like AtlasLoot, built in.

- **Left**: the sources: **Raids**, **Dungeons** (Forever's 35), **Crafting**, **Reputation**, **PvP**, **World
  Events** and **Sets**. Raid loot fills in once the raids open.
- **Middle**: the bosses or lists of the source you picked.
- **Right**: the items, with slot and armor or weapon type; crafting shows the skill needed. Under a pattern, plan or
  formula, an indented row shows what it makes.
- **Search** (top left) looks through every item at once, by name or item number.
- **Show**: all items, **My class**, or your spec (it also hides gear whose stats don't suit it).
- **Shopping list** collects what you still need and what it takes to make it.

Item rows: hover for the tooltip, Shift-click to link, Ctrl-click to try it on, right-click to **Add to my BiS list**
(Pre-raid or S1, as best or as alt). Marks on the right show what is on your list and what you have. Loot Council
members also see **N want**.

---

## Raids: sign-ups, teams and the raid night

Open **Raids** or type `/dz raids`.

### Signing up (everyone)
1. **Upcoming** lists this week's raids, next week's and later. Raids you still have to answer show "you: not answered".
2. Pick a raid. Under **Your answer**, click **Accept**, **Tentative**, **Bench** or **Absent**.
3. Pick your **spec** (it is remembered) and, if you like, a short **Note**.
4. You can change your answer until 6 hours after the raid started.

When you log in, DisasterZone reminds you in chat of your teams' raids in the next 7 days that you haven't answered.

### Who can do what
| | Plan raids | Build teams | A raid's groups, Invite & sort | Pick raid leaders |
|---|---|---|---|---|
| Guild Master | yes | yes | yes | yes |
| Officers (the rank below the GM) | - | - | - | yes |
| Guild council | - | yes | yes | - |
| Raid leaders | yes | - | yes | - |

With nobody on the raid leaders list, only the Guild Master plans raids. Officers name raid leaders in **Raids > Teams
> Raid leaders**. Raid leaders see the Raid log (attendance, bench, no-shows) but get no loot council access outside the
raid they lead.

### Planning raids
- **Teams**: **New team**, a name, the members, **Save**. A player can be on several teams.
- **New raid**: pick the raid (Barrow Deeps, Hyjal Summit, Onyxia's Lair or Other), size (10, 20 or 40), day and time,
  the teams it is for (none = everyone), an optional title and note. **Repeat weekly** keeps the next two weeks planned.
- **Edit**, **Cancel...** and the red **delete** button change, cancel or remove a raid. For a weekly raid you choose
  this week only or every week.
- **Locked**: only the raid's teams and invited players can sign up and see it.
- **Invite** adds players outside the teams.

### Groups and Invite & sort
- A team's groups: drag names into groups, or **Auto-fill**. The icons under each group show the buffs it gets; greyed
  icons mean nobody on the team brings it.
- A raid's **Groups** tab starts from its team's groups and fills empty seats from the sign-ups.
- As raid leader or assistant, **Invite & sort** invites everyone placed in a group, turns the party into a raid and
  moves each player into their group as they join. **Re-sort** moves everyone back. Nothing moves during combat.

### Guests and the blacklist
For the Guild Master, officers, the guild council and raid leaders:

- **Guests** are players outside the guild. Add one with **Add players** at the top right of a raid. A pug who joins
  the raid group of a planned raid becomes its guest by themselves.
- **Raids > Guests** opens the **guest book** (every pug who raided with us: raids, kills, items, no-shows, notes, a
  Recruit mark) and the **blacklist** (players who can't sign up, be added or be invited).
- Tooltips and the right-click menu on players show what the guest book and blacklist know.

### Starting the raid (raid leader)
In a raid, the loot council and rolls stay off until the raid leader starts the raid.

- **Start raid** is on the bar that appears when the leader enters a raid instance, and on the Raids tab.
- Choose what to run: **Loot council**, **Rolls**, and **Lock everyone's BiS lists**. Attendance, boss kills and the
  loot handed out are always logged.
- **Rolls without the loot council** (pugs, loot handled outside the addon): a plain roll panel, highest roll suggested.
- **Options** changes it during the raid. **End raid** switches everything off.
- `/dz raid start` starts with your last choices; `/dz raid options` opens the window.

### Raid log and attendance
- **Start raid** links the raid log to the planned raid (the one you ran Invite & sort for, or the one most of the raid
  signed up for). At **End raid** the sign-ups are saved with it: bench counts as bench, and accepted players who
  didn't come show as no-shows.
- The council, the Guild Master and raid leaders see the **Raid log** and the players' attendance. Members see their
  own on their Members card. `/dz attendance` opens the right view.

### Soft reserves
`/dz reserves` opens the reserves window: each player reserves items from the raid's loot, the host sees every reserve,
and the wrap-up lists the night's reserve rolls. The host can import from softres.it, Gargul or LootReserve.
`/dz reserves demo` shows it with made-up data.

---

## Groups, Members and the other guild pages

### Groups (`/dz lfg`)
The guild's groups as cards: **dungeons** by level band, **raids**, **PvP** (the four battlegrounds) and **other**
(world bosses, farming, reputation, anything else). Switch on **I'm up for a run** with your roles, or **List a run**:
pick the dungeon (long names are shortened on the tiles, e.g. LBRS; hover for the full name), when, a note and
your role. **Join** asks the leader. Your run can also be listed in Blizzard's
Group Finder.

### Members (`/dz members`)
- **Roster**: every guild member with online status, level, main and off spec, and professions with skill. Click a
  member for their characters and recipes.
- **Your recipes**: recipes are read only while a profession window is open, so **open each of your profession windows
  once** (and again after learning new ones).
- **Recipes**: type a name to see who can craft it, online first. **Whisper** opens a message with the item linked.
- **Alts**: log in once on each character, then pick your main with **Change** on your own entry.
- **Officer notes** (Guild Master and the rank below): a private note per member, sent only between officers.

### Other pages
- **Loot rules** (`/dz lootrules`): how the council's suggestion is made, and the prized items. For everyone.
- **Polls** (`/dz polls`): questions from the officers. Answer and see the results.
- **Events** (beta): guild events and cups.
- **Recruitment** (`/dz recruit`): the people you talk to about joining, and the team each one fits.
  Officers also build the guild's **recruitment message** here (**Message** tab: **+ Add a part** for your own words,
  the guild name, raid icons, and once raid teams exist the classes they need and their nights; one chat line, 255
  characters at most) and pick where it goes (**Posting** tab: Trade, GuildRecruitment or any channel, Say or Yell,
  each with its own interval and "cities only"). Raid icons show in Say and Yell only: the game doesn't draw them in
  Trade or other channels, so those get the message without them. GuildRecruitment starts off: a character in a guild
  has to `/join GuildRecruitment` first. The game only lets addons post from a click: **Post now**, the reminder toast, or a
  key bound under Key Bindings > AddOns. Officers share one timer per channel, so nobody posts twice.
- **Audit log** (`/dz audit`, guild council and GM): every change in the addon, who made it, before and after.
- **Map** (`/dz map`): where guildmates who share their position are.
- **Games** (`/dz play`): Council Bingo, Karazhan Chess, Azeromon and Hold the Line, each an optional addon folder.
- **Consumables**: the flask, elixirs, food and potions for your spec at level 60, with a budget pick for farm nights.
- **Wardrobe** (`/dz wardrobe`): outfits you swap with one click, or by a rule.

---

## Loot Council

You are on the council if the Guild Master put you on the guild council, you are the Guild Master, you lead the raid
you're in, or the raid leader put you on this raid's council (only inside that raid). **Settings > Guild > Council**
tells you whether you are on it, and why.

### Council tab
Views: **Roster**, **Items**, **Loot log**, **Loot council** and **Rules**. The toolbar has **Drops** (the drop
panel), a name search, class and role filters, **In my raid only**, **Hide obtained** and **Off-spec lists**.

- **Roster**: one row per member: presence dot, name, spec, **Need** count, a cell per slot (check = obtained, star =
  awarded, "-" = disabled) and the list's **Age** (orange after 7 days). Click a cell to see that item's boss; click the
  name for the member's list.
- **Items**: the raids and bosses with demand counts, and each item with its wanters (main picks first). Click an item
  for **Announce to raid** and **Record award to**.
- The footer's **Request sync** asks online members for newer lists and awards.

### Drop panel
The drop panel opens on its own when someone in the raid who runs DisasterZone loots a boss. Reopen it with **Drops**,
Shift-click on the minimap button, or `/dz drops`.

- It lists epic items by default (the group's minimum quality). Disenchanting, lockboxes, fishing and trade goods are
  ignored.
- Each item shows how many want it and its candidates: **[BiS]** or **[Alt]**, "can't use", "won N" tonight, what they
  wear in that slot, "not in raid", and a warning when their list changed during a lock.
- **Announce** posts one line to raid chat. **Award...** records the award (BiS, Alt, Offspec, another raid member,
  someone not in the raid, the disenchanter or the guild bank). It doesn't hand the item out.
- **Roll** starts a roll. **DE** and **Bank** give the item to the disenchanter or guild bank character in one click.
- In roll mode each row shows the roll and the suggested winner. **Votes**: every council member in the raid has one
  vote per item; click the vote column of a row. **End roll & award to**, **Award to**, **Re-roll** and **Cancel roll**
  finish it.

During a boss pull Forever holds addon messages, so drops, rolls and votes sent in the pull arrive when it ends.

### Loot log
**Council > Loot log** or `/dz log`.

- **Automatic entries** come from "X receives loot: [item]" inside a raid (or a dungeon in dungeon mode).
- **Manual entries**: awards from the drop panel, or **Add award...**.
- **Reasons**:

  | Reason | Counts as loot received ("won N") | Marks the item as awarded on the winner's list |
  |---|---|---|
  | **BiS**, **Alt**, **Upgrade** | yes | yes |
  | **Offspec** | no | yes |
  | **Disenchant**, **Guild bank** | no | no |

- Right-click an entry to change the reason, void or restore it. The log is shared between council members.

### Council tooltips
Item tooltips add "wanted by N (M in raid)" and the names. Hold **Shift** for every name and what each one wears in
that slot.

---

## Raid leader

While you lead a raid you are on the council for that raid.

### Group loot rules
**Settings > Loot > Group rules**. They are sent to everyone in the group:

| Setting | Values |
|---|---|
| Roll duration | 15 / 20 / 30 / 45 / 60 seconds (default 30) |
| Minimum quality | Epic (default) or Rare |
| Raid season | Follow the guild, or a season |
| Dungeon mode (5-man parties) and its minimum quality | See [Dungeon mode](#dungeon-mode) |

Others see "Set by *your name* for this group". `/dz rules` prints the rules in effect. The group's loot leader is the
raid leader (or the master looter when the leader doesn't run DisasterZone); in a party, the party leader if they are
on the council or turned dungeon mode on.

### Raid council
**Council > Loot council > This raid's council**: add players who count as council inside your raid only. The same
section has **Disenchanter** and **Guild bank** buttons; your pick replaces the guild's in your raids.

### Lock and unlock BiS lists
`/dz lock` and `/dz unlock`, or the buttons in Settings, the Council toolbar and the drop panel. Only the raid's loot
leader can lock. A list that changes anyway is flagged "changed during lock" and is never the suggested winner. The
lock ends on unlock, when the raid disbands, when the lead changes or when the raid turns into a party.

### Rolls and master loot
Council members, the master looter and the raid leader or assistants can start rolls: **Roll** or **Roll all** in the
drop panel, or `/dz roll [item link]`.

To have DisasterZone hand items out: set the loot method to Master Looter, keep the boss loot window open as master
looter, and click **Award to** *name*. A popup asks first; the award is recorded once the server has handed the item
over. If it can't be given (full bags, out of range, loot window closed), DisasterZone says why and offers to record
the award anyway.

Forever has master loot. The hand-out has not been tested in a real Forever raid yet: if it fails, hand the item out
yourself and record it with **Award...**.

### Dungeon mode
Dungeon mode shares boss drops and rolls in a 5-man party the way they work in a raid.

- `/dz dungeon on` (as party leader, for the whole party), `/dz dungeon off`, `/dz dungeon status`.
- Minimum quality is Rare by default: `/dz dungeon epic` or `/dz dungeon rare`.
- Awards are tagged "(dungeon)" in the loot log and don't count towards "won N".

---

## Guild Master

The Guild Master is always on the council.

### Pick the guild council
1. **Council > Loot council > Guild council** (or **Settings > Guild > Council**).
2. Add guild members with the search box. **Show offline members** lists everyone.
3. Set the **guild season** (Season 1 for now).
4. Optional: pick the **Disenchanter** and the **Guild bank** character.
5. Click **Save & share**.

The list reaches online members at once and later log-ins within about a minute. Your client only trusts the list you
saved yourself, on that PC: if you play the GM on another PC, save it once there too.

### Seasons
| Season | Set by | Applies to |
|---|---|---|
| Guild season | the GM, with the guild council | everyone: the default My BiS list, council views, tooltips and alerts |
| Raid season | the raid leader, in Group rules | that raid only |
| View season | each player, in Settings | only that player's own views |

With one season so far, all three are Season 1.

---

## How rolls pick a suggested winner

In a raid started without the **Loot council**, rolls are plain: the highest valid roll is suggested.

With the loot council:

**Council votes come first.** Once any council member has voted on an item, the player with the most votes is
suggested. Ties are decided by the groups below, then by the roll.

**Without votes**, everyone who rolled is sorted into four groups:

1. **BiS main**, not obtained yet
2. **BiS alt**, not obtained yet
3. **Off-spec list**, not obtained yet
4. **Everyone else**: not on their list, already obtained, slot disabled, "can't use", or "won a copy" of this drop

The highest roll in the best group is suggested. A roll outside 1-100, a second roll, or a roll more than 2 seconds
late doesn't count. Players flagged "changed during lock", "can't use", "won a copy" or who left the group are never
suggested, but the council can still award them. Ties are marked "tie": pick one or **Re-roll**.

The council always confirms the award. Nothing is given away without a click and a confirmation.

---

## Settings

Open **Settings** (`/dz settings`, or right-click the minimap button). The groups on the left:

| Group | What is in it |
|---|---|
| General | The window, item tooltip lines, the season you look at |
| Alerts | When to stay quiet, and what reaches you (popup, sound, chat) |
| Loot | Raid session, drop panel, rolls, group rules |
| Combat | Class tools (see below) |
| Interface | Looks and layout |
| Guild | The council, attendance, Discord, recruitment, guild setup (most are the Guild Master's) |
| Help | Tutorials, demo mode, version and about |

**Class tools** are per class: for example the paladin blessing planner (Forever's blessings, an hour each) and the
shaman totem planner. They start off. Forever hides health, power and some other values from addons during combat,
so tools that read them show less than they would on other clients.

---

## Demo mode

Try the addon solo with made-up data: `/dz demo` opens the Demo page, `/dz demo on` and `/dz demo off` switch it.
Demo mode adds fake guild members with lists, a pretend raid, and the Council tab. **Simulate a boss drop** (or
`/dz test`) opens the drop panel; **Demo a roll** gives you a roll popup with fake raiders. Nothing is saved or sent:
announces print only in your own chat as "[demo, not sent]".

---

## What is not on Forever (yet)

Forever gives addons no combat log, and some content has no Forever data yet. These parts of the original are hidden
or gone:

| Part | State |
|---|---|
| Gear sim | Hidden. It simulated TBC fights. |
| My Log (your own boss pulls) | Hidden. It needs the combat log. |
| Raids > Strategies (strategy boards) | Hidden. It has only TBC raid maps and rooms. |
| Meters and boss mods | Hidden. They need the combat log; Forever's own replacements are being looked at. |
| My BiS > Suggest | Empty until there are reliable Forever BiS lists. |
| Raid loot | Fills in after the raids open on 9 December 2026. |
| Raid Trainer, The Binding of Illidan | Removed (TBC bosses and rooms). |
| Arena, badges, gems, Jewelcrafting, heroics, Outland | Not in Forever. |

A few labels and pictures still come from the TBC addon (for example "P1" in places where Forever means Season 1, or
TBC loading-screen art). They are being replaced.

---

## Slash commands

`/dz` and `/disasterzone` work the same way. `/dz help` lists every command.

| Command | What it does | Who |
|---|---|---|
| `/dz` | Opens or closes the window | everyone |
| `/dz home`, `/dz bis`, `/dz raids`, `/dz members`, `/dz polls`, `/dz map`, `/dz changelog` | Opens that page | everyone |
| `/dz lfg` | Opens Groups | everyone |
| `/dz settings` | Opens Settings | everyone |
| `/dz plan` | Lists the planned raids and your answers in chat | everyone |
| `/dz version` | Your version and the versions seen in the guild | everyone |
| `/dz sync` | Asks the guild and council to sync lists now | everyone |
| `/dz demo [on\|off]` | The Demo page, or demo mode on / off | everyone |
| `/dz test` | Simulates a boss drop on your own screen. Nothing is sent. | everyone |
| `/dz bug`, `/dz idea`, `/dz feedback` | Report a bug (the last Lua error goes with it), an idea, or other feedback | everyone |
| `/dz council`, `/dz log` | Opens the Council tab or its loot log | council |
| `/dz drops` | The drop panel with tonight's drops | council, master looter |
| `/dz drop <item links>` | Announces a drop to the raid by hand | council, master looter |
| `/dz roll <item link>` / `/dz roll end` | Starts a roll / ends the running roll | council, master looter, raid leader / assistants |
| `/dz rules` | The group loot rules in effect and who set them | everyone |
| `/dz lock` / `/dz unlock` | Locks or unlocks every BiS list in the raid | raid loot leader |
| `/dz raid start\|options\|end\|status` | The raid session | raid leader |
| `/dz reserves` | The soft reserves window | everyone (host: raid leader) |
| `/dz attendance` | Attendance: the raid log, or your own | everyone |
| `/dz dungeon [on\|off\|rare\|epic\|status]` | Dungeon mode for 5-man parties | party leader / council |
| `/dz raiddata` | Prints what DisasterZone learned about the raids you entered (for whoever maintains the addon) | anyone asked to |
| `/dz debug` | Debug messages in chat | only when asked to |

---

## FAQ and troubleshooting

### What does the sync status mean?

| Status | Meaning | What to do |
|---|---|---|
| **Shared with council** | A council member has your current list. | Nothing |
| **Changes pending** | You edited your list recently. It is sent about 8 s after the last edit. | Wait, or close the window |
| **Sharing with council** | A council member is online but hasn't confirmed your version yet. | Wait a minute |
| **Not shared yet: no council member online** | Your list is sent when a council member logs in. | Nothing, or `/dz sync` later |
| **Waiting for guild roster** | The guild roster hasn't loaded yet. | Wait a moment |
| **Not in a guild** | Sharing is off. My BiS, tooltips and your own alerts still work. | - |

A list with no picks at all is never sent.

### The Council tab is missing
Only council members see it. Ask the Guild Master to add you. To look around anyway, use [demo mode](#demo-mode).

### The drop panel didn't open
It needs all of these: you are on the council (or lead a party in dungeon mode); the drop panel is on in Settings;
someone in the raid who runs DisasterZone opened the boss loot window (under master loot: the master looter, the raid
leader, an assistant or a council member); an item met the minimum quality. Reopen it with **Drops** or `/dz drops`,
or announce a drop by hand with `/dz drop [item]`.

If it was during a pull, wait for the pull to end: Forever holds addon messages until then.

### My roll wasn't counted
Only `/roll` 1-100 counts, only your first roll, and only before the timer ends (or up to 2 seconds after).

### A council member has a newer copy of my list
DisasterZone asks whether to restore it. **Restore** takes their copy (after a reinstall or lost SavedVariables).
**Keep mine** keeps yours and sends it as the newest.

### Mixed versions
Everyone, and above all council members, the raid leader and the master looter, should run the **same** version.
`/dz version` shows who runs what. If DisasterZone prints "X uses an incompatible DisasterZone version", messages
between you and X are dropped until one of you updates.

### Something looks stuck
`/reload` rebuilds the windows. Rolls in progress live in memory only: avoid `/reload` on the client that started a
roll until it is awarded. If DisasterZone fails mid-raid, hand the item out the normal way and record it afterwards
with **Council > Loot log > Add award...**.

### Reporting a Lua error
1. Type `/console scriptErrors 1` to see the game's own error window, or use an error-catching addon if you have one.
2. `/dz bug` opens the bug form with the last error attached. **Feedback** shows what you sent.
3. Say what you were doing, whether you were solo, in a party or in a raid, your role there, and whether demo mode
   was on.

---

## How it syncs, and privacy

- **Your BiS list goes only to the council, by whisper**: your picks, disabled slots, class, spec, which listed items
  you own and what you wear. Guild council members and the GM get it; the raid leader and raid council only while you
  are in their raid. Regular raiders never receive other players' lists.
- **The guild channel carries small status messages**: list revision numbers and versions, which lists council members
  hold, and the guild council list from the GM. The guild can see who has a list, not what is on it.
- **The raid or party channel carries loot events**: drops, rolls, votes, group rules, the raid council and the lock.
- **The loot log is council only**, shared by whisper.
- **Everything stays inside the game.** Council members keep copies of other players' lists in their SavedVariables.
- **It is not cryptographic.** Checksums catch damaged or old data, not forgery. DisasterZone refuses the known ways a
  modified client could interfere with others, but treat it as a helper for an honest guild, not a security system.

---

Third-party libraries, data sources and credits: see [NOTICE.md](NOTICE.md).
