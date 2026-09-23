---
type: task
status: review
area: gameplay
priority: medium
---

# task-449: Grapple tracks display names, not identity

**Filed:** 2026-09-22
**Related:** task-446 (id-first node identity), `engine/grapple.py`,
`routes/player_ops.py`

## Problem (functional)

`engine/grapple.py` identifies held targets by **display name**, not identity:

- `_grappling_targets(grappler_name)` (`:145`) and `_grappler_of(target_name)`
  (`:162`) return `node.name` — the anchor node's **display name**.
- `_add_edge` / `_remove_edge` (`:187`, `:196`) take names and run them through
  `get_player_node_id(name)`.
- `routes/player_ops.py:597` passes `player.name` into `_remove_edge`.

With two characters sharing a name, `players.get(display_name)` and
`node_id_for(display_name)` resolve to the **primary**, so grabbing, holding,
releasing, or the desync repair (`sync()`, `:209`) can hit the **wrong**
same-named character. Not exercised yet (no duplicate names in data), but it is
the one *functional* duplicate-name bug left after task-446.

## Fix

- Add a reverse lookup on `PlayerManager` — `key_for_node_id(node_id)` (maintain a
  `node_id → key` index in `add_player`/`reindex`).
- Make `_grappling_targets` / `_grappler_of` return **keys** (map the edge's node
  id back through that lookup, falling back to `node.name` only if unknown).
- `_add_edge` / `_remove_edge` / `release` / `_release_target` accept keys.
- Update callers to pass the key (e.g. `routes/player_ops.py` should use the
  player's registry key, not `.name`).

## Also (cosmetic, same theme)

A few log strings print the registry key for a duplicated character. Use
`p.name`:
- `engine/npc_behaviors.py:146` (`[NPC] {pname} wanders…`), `:175` (flees)
- `engine/tick_manager.py:433` (`[{pname}] GAME OVER…`), `:668` (`[{pname}] gained the {trait}`)

## Acceptance

- Two same-named characters: grappling one records/holds/releases **only** that
  one; `sync()` repairs the right body; a test asserts distinct holds.
- Log lines show the display name for duplicates.
- Full suite green apart from the known pre-existing failures.

## Implemented (2026-09-22)

- `PlayerManager`: added `_players_by_node_id` (maintained in `add_player` and
  `reindex`) and `key_for_node_id(node_id)` — the reverse of
  `get_player_node_id`, with a case-insensitive fallback.
- `engine/grapple.py`: `_grappling_targets` and `_grappler_of` now resolve each
  edge endpoint back to its identity key, falling back to `node.name` only for an
  unknown node. `_add_edge` / `_remove_edge` already route refs through
  `get_player_node_id`, so keys work end to end.
- `routes/player_ops.py`: the "remove_condition grappled" cleanup uses the
  player's registry key instead of `.name`.
- Log label leaks fixed: `engine/npc_behaviors.py` (wander/flee msgs) and
  `engine/tick_manager.py` (GAME OVER / trait-gained msgs) print the display name.
- Tests: `tests/test_grapple.py::TestGrappleIdentity` (3) — grab targets the
  right same-named body, release only affects that identity, and `sync()` repairs
  the right body.
- Regression: full suite unchanged (same 60 pre-existing failures; no new).

