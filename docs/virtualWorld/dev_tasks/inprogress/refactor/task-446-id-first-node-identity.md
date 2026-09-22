---
type: task
status: inprogress
area: refactor
priority: high
---

# task-446: id-first node identity — data by id, names resolve at the boundary

**Filed:** 2026-09-22 (from task-357 design review).

## Principle

Backend data operations on nodes are keyed by **id**. Names are user-facing: a
matcher resolves user text ("steal from Jon", "take the knife") to an id, and
the id is what every data operation consumes. Ids are stable across renames, so a
rename never dangles a reference and two nodes may share a display name.

`engine/matching.py` is the name→id seam. Storage must not use names as identity.

## Measured blast radius (2026-09-22, non-test)

| Violation | Sites |
|---|---|
| `players` dict keyed by name | 24 direct `players[...]` + 69 `.items()/.values()/.keys()` |
| `Player.node_id_for(name)` anchor id from name | 192 (`node_id_for`/`player_node_id`) |
| `relationships` keyed by name | 6 |
| `current_area` stores an area **name** | 445 |
| `find_item_node` / exit resolution by name as identity | small (mostly `matching.py`) |

## Slices

### Slice A — player identity (points 1, 2, 3) *in progress*

- `Player.uid` is the stable identity (existing opaque `Player.id`, task-316).
- `PlayerManager.players` becomes **id-keyed**, with a name index. Duplicate
  display names are allowed; ambiguous name lookups return candidates and the
  resolver picks.
- Anchor node ids stay `player_<slug(name)>` for a **unique** name (saves and
  tests keep working) and get a stable suffix from the uid when the name is
  duplicated (`player_jon__<uid>`).
- Save format: `players` written keyed by id with `name` inside; **read** accepts
  legacy name-keyed files (key falls back to the payload's `name`).
- Migrate the ~93 access sites: iteration for display uses `p.name`; identity
  uses the key/uid.
- Relationship keys move to uid (point 3) with name resolution for prompts.### Slice B — location by id (point 4) *last, behind a compat accessor*

- `current_area` holds an area id; `Player.area_name`/resolver provide the name
  at the display/prompt boundary. 445 sites, so a compatibility accessor first,
  then mechanical migration.
- **Already tracked as task-439** ("Canonical area identity in the save and in
  area lookups") — do that work there, not here. 439 is the prerequisite for
  scopes/decomposition.

### Slice C — resolver boundary (point 5)

- Formalize `matching.py` as the only name→id seam; no engine code consumes a
  name as a key. Mostly a cleanup once A/B land.

## Why this order

A is the core of the stated goal (500 "Jon"s; template population). B is the
widest change, so it goes last. C is cleanup. A+B+C in one pass would leave the
tree half-migrated and break the suite; each slice must keep the suite green.

## Compatibility / migration rules

- Never break a name-keyed save: read old, write new.
- A unique name keeps its derived anchor id (no churn on existing worlds).
- `players[name]` continues to work for a unique name; ambiguous access logs /
  returns the primary candidate and the resolver surfaces the alternatives.
- Rename must remain reference-safe: only the display name changes.

## Acceptance

- Two characters named "Jon" can coexist end-to-end (create, save, load, act,
  be targeted unambiguously via `matching`).
- `players` storage and `node_id_for` are id-keyed; no data operation keys on a
  name.
- Old saves load unchanged; new saves round-trip.
- Full test suite green apart from the known pre-existing failures.

## Implemented — Slice A, steps 1–3 (2026-09-22)

Functional duplicate display names, non-breaking:

- `PlayerManager` (`engine/player_manager.py`): a name is now a **lookup key**,
  not the identity. `_unique_key` gives a duplicate a stable id-derived registry
  key (`Jon` → `Jon__<id6>`) while `p.name` stays free; `add_player` gives such a
  player a unique anchor (`player_Jon__<id6>`). Unique names keep the exact legacy
  key and anchor, so existing worlds/saves do not churn. Added `uid_of`,
  `get_by_id`, `find_by_name`, `resolve`, `reindex`, `relationship_key`,
  `display_name_of`; `get_player` / `get_player_node_id` / `set_active_player`
  accept key, name or id; `get_players_in_area` / `get_all_*_players` report
  `p.name` (display). Registered players are given a `player_manager`
  back-reference so identity can be resolved from anywhere.
- `virtual_world_engine.py`: `player_node_id` / `_player_node_id` delegate to
  `PlayerManager.get_player_node_id`, so a registry key resolves to its own anchor.
- `engine/serialization.py`: `_deserialize_player` restores `p.name` from the
  payload (fixes a latent bug that would set the display name to the key), and
  `load_from_dict` calls `reindex()` so duplicate keys get unique anchors.
- `engine/matching.py` (`_match_character_name`): name tiers compare the
  **display** name, so two characters named "Jon" return an **ambiguous**
  candidate list (keys) instead of silently resolving to the first.
- **Relationships keyed by identity (point 3).** `engine/relationships.py` gains
  `resolve_key` / `display_name` / `get_relationship`; every writer and reader
  (`ensure_relationship`, `apply_relationship_delta`, `apply_symmetric_delta`,
  `describe`, and the migrated reads in `derive`, `area_description`,
  `background_social`, `grapple`, `pleasure_actions`, `movement`, `player_ops`)
  resolves the other party to the unique key. Records carry a denormalized
  `name` for prose/prompts; `Player._rel_key` backs `has_met` / `knows_name` /
  `learn_name` / `register_first_meeting`; `_relationships_to_dict` emits display
  names. For a unique name the key IS the name, so nothing churns.
- **Display-name usage in iteration (step 4).** Label sites that printed or
  matched the loop key as a name now use the display name: `narration.py`
  character listing, `logging_events.py` debug export, `routes/settings.py`
  player dump, `routes/player_ops.py` player lists + target candidates + learned
  list, `engine/autocomplete.py` character suggestions, `engine/movement.py`
  feared-room check, `engine/effects.py` / `engine/triggers/evaluation.py`
  target resolution. Sites where the key is genuinely an identity (edge/condition
  keys, notification keys, counts, hash keys) were left as-is.
- Tests: `tests/test_player_identity.py` (7) — unique-name compatibility,
  duplicate coexistence, save/load round-trip, resolve by name/key/id, in-area
  listing, duplicate-target ambiguity, and **per-identity relationships** (two
  "Jon"s keep separate records; a rename does not drop the record).
- Regression: full suite unchanged (same 60 pre-existing MCP/social/tick
  failures; no new ones).

### Remaining in Slice A

- Duplicate-target disambiguation UX → **task-448**.
- Character nicknames/alias authoring + persistence → **task-447**.
- Grapple identity mixup (functional) + log-string label leaks → **task-449**.
- Add duplicate-name round-trip coverage at the route/autosave layer (small,
  folded into a later pass).
- `node_id_for` is still name-derived for the unique case by design (compat);
  a pure-uid anchor migration is a later step.
- Slice B (location by id) is **task-439**, not this task.

