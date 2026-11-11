---
title: "Item tooltip on TooltipDataProcessor"
tags: [task]
status: 5 - Done
completed: 2026-11-09
priority: p2
effort: S
updated: 2026-11-08
---

# Item tooltip on TooltipDataProcessor

`UI/Tooltip.lua` hooks `OnTooltipSetItem` and returns early when the tooltip lacks it. Forever has no such script
(probe: `hasOnTooltipSetItem` false), so the "who wants this item" lines are silently off. Use
`TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, ...)` when present. The mock's Forever profile
supports it (`dev/tests/forever/test_forever_profile.py`, tooltip case).

## Done when

A Forever-profile test shows DisasterZone's lines on an item tooltip.
