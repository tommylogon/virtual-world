# Task 341 — Single-source room perception invariants (agent path + panel path)

**Status:** In Review — implemented 2026-08-24, full suite 1129 passed.
Went slightly beyond the filed proposal: item visibility, people
enumeration, and area resolution are single-sourced too, not just the
three invariants. Browser E2E pending.

## Implementation notes (2026-08-24)

New module `engine/room_perception.py` owns the shared invariants:

- `resolve_area_node(graph, area_name)` — name-based (normalized:
  lowercase, apostrophes dropped, `_`/`-` as spaces), canonical
  constructed id as validated fallback (bug-26).
- `normalize_requires(value)` — none/nothing/no → "" (bug-24).
- `way_visible_to(player, player_manager, viewer_name, way_node,
  area_name, direction)` — hidden ways: slasher or `(area, direction)`
  in `discovered_exits` (bug-23). Viewer is a parameter: the agent path
  passes active_player, the panel passes the viewing character.
- `visible_area_items(graph, area_id, include_hidden)` — the hidden-item
  filter both paths duplicated.
- `characters_in_area(graph, area_id, exclude_name)` — people enumeration.

Consumers rewired:

- `scene_snapshot.py` — area resolution, items loop, people loop, hidden
  way rule, requires normalization all delegate now.
- `area_description.py` — `get_current_area_id`, `get_area_items`,
  `build_exits_for_area` area resolution + hidden rule delegate. Output
  shapes untouched (prose identical, exits dict identical).
- `movement.py` — both requires reads (passage gate + traversal-only
  open/close refusal) use `normalize_requires`.

Contract test `tests/test_room_perception_contract.py`: one fixture world
(non-canonical apostrophe ids, undiscovered + discovered hidden ways,
requires:"none" way, hidden item) asserting the agent path
(`get_area_items` + `build_exits_for_area`) and the panel path
(`build_scene`) return the SAME visible item set and way set. Plus unit
tests for `resolve_area_node` / `normalize_requires`.

AGENTS.md architecture section now names room_perception.py as the
canonical home with the "presentation is the only difference" rule.

## Why

Two renderers answer "what does this character perceive in this room":

- **Agent path**: `engine/area_description.py` (prose) + prompt-builder
- **Panel path**: `engine/scene_snapshot.py` (`/api/scene/<player>`, JSON chips)

The panel legitimately needs structured data (available_actions, per-way
discovered state, YOU strip) — this is NOT a "merge the renderers" task.
The problem is the *invariants* get re-implemented in the panel path and
drift. Four incidents, one root cause:

| Incident | Agent path had | Panel path lacked |
|---|---|---|
| task-333 fix | name-based area lookup | constructed-id lookup (500 crash) |
| bug-23 | `look` filters hidden ways | hidden-way filter (leak) |
| bug-24 | movement normalizes `requires:"none"` | normalization (Go disabled) |
| bug-26 | name-based area resolution | id validation (empty panel) |

## Proposal

Extract the drifting invariants into one small module (e.g.
`engine/room_perception.py`) and make BOTH paths call it:

1. `resolve_area_node(graph, area_name)` — name-based lookup with
   constructed-id fallback (bug-26 fix, already proven in scene_snapshot).
2. `way_visible_to(player, way_node, area_name, direction)` — the hidden
   way rule: slasher sees all, else `(area, direction)` in
   discovered_exits (bug-23; mirror of build_exits_for_area).
3. `normalize_requires(value)` — none/nothing/no → `""` (bug-24).

Consumers: `scene_snapshot.py`, `area_description.py`
(`build_exits_for_area`), and `movement.py` (requires gate reads the
normalized value). Keep each renderer's OUTPUT shape untouched — no
prompt prose changes, no panel payload changes.

## Contract test

A test that builds one fixture world (apostrophe area ids, hidden way,
requires:"none", unmet stranger) and asserts the two paths AGREE:
same visible item set, same way set, same people masking. Drift then
fails CI instead of surfacing in Tommy's playtests.

## Verification

- Full pytest suite green; existing behavior-pinning tests unchanged.
- Browser: men's restroom panel populated (bug-26), hidden ways still
  hidden until searched, "requires none" doors go/open normally.
