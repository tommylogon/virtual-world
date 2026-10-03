---
type: task
status: todo
area: ui
priority: medium
---

# task-676: Area editor: split properties/place view with a mini-map

**Filed:** 2026-10-02
**Related:** task-240, task-246, task-237

## Goal

Phase 4 of docs/design/full-entity-editors.md. The area editor has 14 sections in a 379px column with no map, and its inherently spatial sections (exits, agents present, item visibility, area event log) are stranded as text lists. Build a split view in the full-surface editor: left column properties (name, description, tags, aliases; environment light/temp/air/smell/noise plus weather, wind, humidity and the presets scope picker; floor, scope, graph physics), right column place (mini-map of the area and its ways, exits list, agents present, items visible, area event log read-only and scroll-locked). Note the way view already offers a VISIBLE ITEMS IN <AREA> selector with 207 options, which is the signal that visibility is spatial and should be shown next to a map. Also record that the area view currently has zero input[type=range], so the environment controls are text/number/select and are not the sliders the docs describe. NOTE the open dependency: whether below 900px is a real target is undecided, so confirm the responsive story before building a stacked variant. Depends on the phase 1 frame being verified in a browser first.

## Acceptance

- TODO
