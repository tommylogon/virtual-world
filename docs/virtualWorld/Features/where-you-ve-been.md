---
type: feature
feature_id: 43
status: wired
section: in-game
tags: [status/wired, surface/in-game, system/gameplay]
---

# Where you've been

**What you can do:** A map of the cells your character has actually walked, per scope, with what they last observed there and a mark on ways you know are blocked

## How it works

- [[Turn Queue & Human Turns]]
- [[Grid Line of Sight & Charted Memory]]

## Where it lives

- `engine/world_grid.py` - viewshed slope-sweep and 2.5D raycast line of sight
- `player.py` / `engine/character_record.py` - `player.charted_cells` persistent memory
- `engine/spatial_memory.py` - `recall` action and charted A* pathfinding
- `static/js/agent/turn-minimap.ts` - 4-tier fog of war lattice rendering
- `static/js/agent/prompt-builder/room-context.ts` - bounded horizon context injection

## Connected

- Feature Map: [[Feature Map|row 43]] (In a game)
- Sibling features: [[look-around]], [[examine]], [[move]], [[open-close]], [[take-drop-give]], [[use-use-on]]
- All features: [[Features Overview]]

> [!note] Status — `wired`
> Recorded from [[Feature Map|the Feature Map]] on 2026-10-05. This page is an entry point; the
> deep documentation is linked under **How it works**.
