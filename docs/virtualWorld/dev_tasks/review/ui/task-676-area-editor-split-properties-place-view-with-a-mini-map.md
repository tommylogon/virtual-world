---
type: task
status: todo
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-676: Area editor: split properties/place view with a mini-map

**Filed:** 2026-10-02
**Related:** task-240, task-246, task-237

## What

Phase 4 of docs/design/full-entity-editors.md. The area editor has 14 sections in a 379px column with no map, and its inherently spatial sections (exits, agents present, item visibility, area event log) are stranded as text lists. Build a split view in the full-surface editor: left column properties (name, description, tags, aliases; environment light/temp/air/smell/noise plus weather, wind, humidity and the presets scope picker; floor, scope, graph physics), right column place (mini-map of the area and its ways, exits list, agents present, items visible, area event log read-only and scroll-locked). Note the way view already offers a VISIBLE ITEMS IN <AREA> selector with 207 options, which is the signal that visibility is spatial and should be shown next to a map. Also record that the area view currently has zero input[type=range], so the environment controls are text/number/select and are not the sliders the docs describe. NOTE the open dependency: whether below 900px is a real target is undecided, so confirm the responsive story before building a stacked variant. Depends on the phase 1 frame being verified in a browser first.

## Acceptance

- TODO

## Browser UI and intended live verification

Intended UI home: Select an area → inspector peek → expand to the full-surface Area Editor. Its Properties column owns authored settings; its Place column keeps the mini-map beside exits, occupants, visible items, and the area event log.

Current availability: The card records 14 area sections in a 379px column and no map; the split view is planned and depends on the task-673 frame being browser-verified. The below-900px layout target is still undecided.

Live steps when available:
1. Open a populated area in the full-surface editor at 1200px or wider.
   - expected: left Properties shows name/description/tags/aliases, environment, presets, floor, scope, and physics; right Place shows that area's map and ways, exits, agents present, visible items, and a read-only scroll-locked event log.
2. Select an exit on the mini-map and compare it with the Exits list; inspect the existing “Visible items in <area>” choice.
   - expected: the selected map way and exit row identify the same connected area, and visible items correspond to the selected area rather than the whole scope.
3. Change the area light or temperature setting and save; inspect the Properties controls again.
   - expected: text/number/select controls display the saved values; the UI does not present the existing environment fields as sliders unless real range inputs were added.
4. Test the confirmed width breakpoint and record the result below it.
   - expected: both columns remain usable at the agreed width; do not accept a stacked layout until the under-900px target is decided.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
