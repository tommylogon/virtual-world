---
type: feature
feature_id: 29
status: unwired
section: in-game
tags: [status/unwired, surface/in-game, system/gameplay]
---

# Per-agent knowledge (fog of war)

**What you can do:** Per-character known set; a map that only shows what you have found

## How it works

- [[Per-Agent Knowledge (Fog of War)]]

## Where it lives

- Registry: `engine/fog.py` (`Known`, `reveal_area`, `reveal_examined`, `reveal_sightline`, `teach_from_map`)
- Walk writer: `engine/movement.py` arrival
- Examine and charted-map writer: `engine/items/examine_actions.py`, `engine/items/use_actions.py`
- Sightline writer: `engine/area_description.py` via `beyond_visibility.sightline_run`
- Hearsay writer: `engine/speech.py` (a spoken direction naming an area)
- Perception gate: `engine/room_perception.py` (`way_visible_to`, `visible_area_items`)
- Route bridge: `engine/spatial_memory.py` (`known_route_areas`), read by `routes/memories.py` and `routes/action_handlers.py`

> [!note] Wiring 2026-10-23
> The `known` registry now grows on a walk, an examine, reading or using a
> charted map, looking down an open or see-through corridor, and hearing a
> direction that names a place. The fog/map view (`fog_view`) still has no
> caller, so this row stays `unwired` until task-677 provides that surface.

## Connected

- Feature Map: [[Feature Map|row 29]] (In a game)
- Sibling features: [[look-around]], [[examine]], [[move]], [[open-close]], [[take-drop-give]], [[use-use-on]]
- All features: [[Features Overview]]

> [!note] Status — `unwired`
> Recorded from [[Feature Map|the Feature Map]] on 2026-10-05. This page is an entry point; the
> deep documentation is linked under **How it works**.
