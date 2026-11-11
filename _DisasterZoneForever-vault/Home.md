---
tags: [meta]
updated: 2026-11-11
---

# DisasterZoneForever

> The <Casual Disaster> guild addon, ported from TBC Anniversary to **WoW Forever** (1.60.1, Interface 16001).
> A fork of [tsumilo/DisasterZone-dev](https://github.com/tsumilo/DisasterZone-dev). These notes cover the addon,
> its dev tooling and its tests.

## Overview

- [[Project Overview]]: what the addon does and how the port works
- [[Deep Dive Synthesis]]: how the original works and what Forever changes
- [[How Sync Works]]: how the addons share data, and why messages wait during a boss pull
- [[Probe Findings 2026-11-08]]: what the real Forever client does, recorded by the probe addon

## Architecture

- [[Architecture Overview]]: the layers and the deep-dive report for each

## Roadmap

- Board: [[Work.base|Work]] (cards in `04-Roadmap/Tasks/`)
- [[Multi-player Test Plan]]: the in-game test with several players

## Operations

- [[Developer Guide]]: repo layout, everyday commands, tests, making a change, releasing
- [[Linux Dev Setup]]: one-time setup of the Python/Lua test environment
- [[Testing with Forever Data]]: the mock client's Forever profile and the replays
- [[Adding a Feature]] · [[Adding a Forever Raid]]

## Log and code

- [[Changelog]] · [[Decision Log]]
- [[Code Map]]: where each part of the code lives

## Reference

- [[Forever Client Facts]] · [[Forever Client Facts - Round 2]] · [[Forever Content Facts]]
- [[Duplicate Drops Fix]]
- Deep-dive reports in `09-Reference/Deep Dive/`: [[DZ Deep Dive 01-core-framework|01 core framework]] ·
  [[DZ Deep Dive 02-roles-and-leadership|02 roles and leadership]] ·
  [[DZ Deep Dive 03-game-data-and-content|03 game data and content]] · [[DZ Deep Dive 04-testing|04 testing]] ·
  [[DZ Deep Dive 07-ui-and-api-surface|07 UI and API surface]]
- [[Source Documents]]

## Running the tests

Set up the test environment once with [[Linux Dev Setup]], then from `dev/` run `tools/check.py -q` and
`tf_e/run_all.py`. The [[Developer Guide]] lists every command; [[Testing with Forever Data]] explains the Forever
profile.
