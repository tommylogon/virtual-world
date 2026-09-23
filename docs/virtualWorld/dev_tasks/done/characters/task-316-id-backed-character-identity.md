# task-316 — ID-backed character identity (same-name support)

**Status**: Done — identity delivered under task-446 Slice A; fresh character
spawns completed 2026-09-23.

## Outcome

Most of this design landed as **task-446 Slice A** (id-first identity), which
cites task-316 as the source of the opaque `Player.id`:

- `Player.id` (opaque, persisted, never shown to agents); registry is
  identity-keyed with name lookup (`PlayerManager._unique_key` /
  `_players_by_id` / `relationship_key` / `resolve` / `find_by_name`).
- Duplicate display names coexist end-to-end: distinct registry keys, distinct
  anchor nodes, separate relationship records (task-446,
  `tests/test_player_identity.py`).
- `graph.add_node` suffixes duplicate `character` ids rather than overwriting
  (graph.py).
- Save/load persists and restores `Player.id` with a legacy fallback
  (`engine/serialization.py`).

**Completed here (2026-09-23):** `spawn_character` is now always *fresh* —
`_hydrate_character(..., always_fresh=True)` builds a new `Player`/identity per
call (mirroring `spawn_item`), and `handle_spawn_character` places the new
entity by its registry key rather than its display name (which would resolve to
the primary for a duplicate). A trigger can now produce 100 distinct same-named
zombies. Covered by `test_spawn_character_is_fresh_per_call`, plus a
strengthened id-stability assertion in the save round-trip test.

Remaining follow-ups live elsewhere: disambiguation UX (**task-448**), character
alters (**task-447**), grapple identity (**task-449**), and location-by-id
(**task-439**).

## Goal

Give every character a stable, opaque backend id so same-named entities are distinct
(e.g. 100 zombies all named "zombie", two characters both named "Violet"), while the
display name remains the human/LLM addressing surface.

## Background / motivation

Library = templates, world = instances. Items already spawn as unique fresh copies
(`always_fresh`, `library_id` stamped — done 2026-08-19 in effects.py). Characters do
not: `_hydrate_character` dedupes by `char_id`, `player_manager.players` is keyed by
display name, relationships are keyed by the other character's display name, and the
frontend agent engine addresses agents by `worldState.players[charName]`.

Consequences today:
- Second spawn of the same character returns the first one (effects.py:537-542).
- Two same-named characters silently overwrite each other in the registry
  (player_manager.py:36) and merge into one relationship slot (player.py:779).
- `graph.add_node` raises on duplicate area ids but only suffixes item/door/logic_trigger
  ids — characters collide and overwrite (graph.py:74).

## Design (confirmed with user)

- **Stable backend `Player.id`** (opaque, unique, never shown to agents/LLM).
- **Display name stays the addressing surface**: commands target by name, alias, or
  descriptive/spatial qualifiers ("attack the ugly one", "attack the zombie at the door").
  No new targeting needed — matching (aliases, descriptions, spatial position) already
  exists.
- With 100 identical zombies and no qualifier, first-match is correct — any zombie is a
  valid target.
- **Registry keyed by id internally**, with name → id resolution for the command surface.
- **Relationships keyed by id**, so two Violets don't share a relationship slot.
- **Serialization**: write `players` keyed by id; migrate name-keyed autosaves.
- **Spawn/give stay fresh** (`always_fresh`) so a trigger can produce 100 unique zombies.

## Scope

Backend:
- `Player.id` field (constructor + from_library hydration path)
- `player_manager` registry keyed by id, name→id resolution helper
- relationships keyed by id (player.py, combat.py, area_description.py)
- serialization (write by id + migration for name-keyed saves)
- action route player resolution (routes/action.py)

Frontend:
- agent engine + prompt builder must keep using display names only (no id leakage)
- world-sync / library match remains name/slug/library_id based (works as-is)

Supporting:
- `graph.add_node`: include character nodes in the unique-suffix branch (or rely on
  id generation in player_manager) so a duplicate player id can never silently overwrite.

## Verification

- Unit tests: spawn two same-named characters → 2 distinct players, 2 distinct nodes,
  separate relationship slots.
- Autosave round-trip keeps ids stable; old name-keyed save still loads.
- E2E: 100 zombie spawns exist as unique entities; `attack zombie at the door` /
  `attack the ugly one` resolve; agent output never shows an id.
