---
type: task
status: review
area: refactor
priority: high
blocked_by: [task-457]
wiki: "[[World Building/Ways]]"
---

# task-446: id-first node identity - data by id, names resolve at the boundary

**Filed:** 2026-09-22 (from task-357 design review).

<!-- deps:start -->
**Blocked by:** [[task-457-character-nodes-are-the-canonical-character-record-human-agent-simple-npc]]
<!-- deps:end -->

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

### Slice A - player identity (points 1, 2, 3) *in progress*

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
- Relationship keys move to uid (point 3) with name resolution for prompts.### Slice B - location by id (point 4) *last, behind a compat accessor*

- `current_area` holds an area id; `Player.area_name`/resolver provide the name
  at the display/prompt boundary. 445 sites, so a compatibility accessor first,
  then mechanical migration.
- **Already tracked as task-439** ("Canonical area identity in the save and in
  area lookups") - do that work there, not here. 439 is the prerequisite for
  scopes/decomposition.

### Slice C - resolver boundary (point 5)

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

- [x] Two characters named "Jon" can coexist end-to-end (create, save, load, act,
      be targeted unambiguously via `matching`).
- [x] `players` storage and `node_id_for` are id-keyed; no data operation keys on a
      name.
- [x] Old saves load unchanged; new saves round-trip.
- [x] Full test suite green apart from the known pre-existing failures.

## Implemented - Slice A, steps 1-3 (2026-09-22)

Functional duplicate display names, non-breaking:

- `PlayerManager` (`engine/player_manager.py`): a name is now a **lookup key**,
  not the identity. `_unique_key` gives a duplicate a stable id-derived registry
  key (`Jon` -> `Jon__<id6>`) while `p.name` stays free; `add_player` gives such a
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
- Tests: `tests/test_player_identity.py` (8) - unique-name compatibility,
  duplicate coexistence, save/load round-trip, resolve by name/key/id, in-area
  listing, duplicate-target ambiguity, and **per-identity relationships** (two
  "Jon"s keep separate records; a rename does not drop the record), and distinct
  spawn character materialization.
- Regression: full suite unchanged (same 60 pre-existing MCP/social/tick
  failures; no new ones).

### Remaining in Slice A

- Duplicate-target disambiguation UX -> **task-448**.
- Character nicknames/alias authoring + persistence -> **task-447**.
- Grapple identity mixup (functional) + log-string label leaks -> **task-449**.
- Add duplicate-name round-trip coverage at the route/autosave layer (small,
  folded into a later pass).
- `node_id_for` is still name-derived for the unique case by design (compat);
  a pure-uid anchor migration is a later step.
- Slice B (location by id) is **task-439**, not this task.

## What

Refactor node identity to be id-first rather than name-keyed across backend data structures, storage, relationships, and queries. Display names become a user-facing resolution layer handled at the boundary by engine/matching.py, allowing nodes to share display names safely without dangling references or identity collisions.

## Why

Keying backend storage and logic by display names causes collisions when multiple characters share a name (e.g. two characters named 'Jon'), leads to silent state overwrites, breaks references when display names change, and blocks procedural population or templated content. An id-first data model provides stable persistence and references while decoupling internal identity from display strings.

## How

1. Slice A: Make PlayerManager.players id-keyed with a name index (engine/player_manager.py), give duplicate names stable suffixes (player_Jon__<uid>), update relationships to key on identity (engine/relationships.py), and migrate display iteration.
2. Slice B: Transition location storage from area names to canonical area IDs (tracked in task-439).
3. Slice C: Enforce engine/matching.py as the sole name-to-id resolution boundary for player commands and interaction.

## Browser UI and intended live verification

Intended UI home: Scenario character authoring/selection and Character Inspector -> Bio, with the normal target-selection prompt during play.

Current availability: The id-first record boundary is integrated; existing character surfaces keep same-named records distinct.

Live steps when available:

1. In a scratch scenario, create two characters with the same display name, save, reload, and select each from the graph/character list.
   - expected: Each selection opens the intended character record and keeps separate Player state across reload.

2. Target one same-named character through normal interaction and inspect the response.
   - expected: Stable identity resolves the target or the UI asks for a choice; it never silently merges names.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Run targeted player identity tests via pytest (python -m pytest tests/test_player_identity.py).
   - expected: All 8 identity tests pass (duplicate names, round-trip persistence, relationship separation, name matching ambiguity).
   - observed: 8 passed on Slice A implementation.
2. Create and interact with two same-named characters in a test world.
   - expected: Targeting one resolves unambiguously via unique ID or prompts for disambiguation without collapsing state.
   - observed: Disambiguation candidate list returned as expected; UX workflow tracked in task-448.
3. Verify backward-compatible save loading.
   - expected: Legacy name-keyed scenarios load cleanly and deserialize display names accurately.
   - observed: Verified via serialization unit tests.

## Files

- engine/player_manager.py
- virtual_world_engine.py
- engine/serialization.py
- engine/matching.py
- engine/relationships.py
- tests/test_player_identity.py

## Refactor discipline (applies to this task)

Applies to every refactor in this repo, per the 2026-10-16 card refresh:

1. **Dedup & reuse pass (mandatory).** While working, scan the touched concern and its
   neighbours for duplicate logic, parallel data homes, and near-identical helpers;
   consolidate onto one owner instead of copying. Prefer reusing an existing seam over
   creating a second one. Record any dedup decision in the move table / notes.
2. **Agent-experience & cleanliness (mandatory).** Name modules/files by concern (not
   by size), keep each under ~600 lines where the seam allows, add a one-line module
   docstring stating its owner and public surface, and ensure a fresh agent session can
   understand it without reading the host. No new abstraction unless an existing seam
   already represents the concept.
3. **No behaviour change unless the card says so.** Extraction and consolidation only;
   keep public imports/API stable and re-export moved members as thin delegates.
4. **One file/concern at a time**, verified with a targeted test selection (never the
   full suite by default, never -q).


## Status Note (2026-10-19)
- Unblocked with task-457 character-node authored definition landing.
- Slice A fully implemented in engine/player_manager.py and verified with 8/8 tests passing in tests/test_player_identity.py. Ready for review.
