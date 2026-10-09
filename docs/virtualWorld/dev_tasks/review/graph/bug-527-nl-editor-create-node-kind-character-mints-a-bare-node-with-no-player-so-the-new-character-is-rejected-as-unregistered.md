---
type: bug
status: review
area: graph
priority: high
---

# bug-527: NL editor create_node kind=character mints a bare node with no Player, so the new character is rejected as unregistered

**Filed:** 2026-10-08
**Related:** 

## Goal

Repro (live 2026-10-08): NL editor 'add Zoe Mercer to the foyer' stages create_node {kind:character} -> handle_create_node (routes/graph_ops.py:123) writes a bare character_* node; attach succeeds; the inspector then rejects it (inspector.ts:294, 'has no player state ... not a registered player'). Characters are Player-backed; the canonical creation path is PlayerManager.add_player (engine/player_manager.py:182), exposed by handle_create_player (routes/player_ops.py:381), which mints a player_<name> type=character node. The NL editor bypasses it. Fix: register a Player (a create_character op applied via handle_create_player, then attach the player_<name> node to the area), drop character from create_node's kind enum, and guard that the editor never creates a character_* node. Verify: add Zoe Mercer -> she appears in the inspector WITH player state and is present in the foyer.

## Acceptance

- TODO

## Landed (2026-10-08)

A character is now created as a **Player**, not a bare graph node.

- **Server** (`routes/graph_ops.py`): new batch op `create_character` (phase 0) registers a
  Player via `player_manager.add_player` — which mints the canonical `player_<name>` node —
  then writes authored prose (`personality` / `description` / `base_description`) onto the
  node. Restores `active_player` like the duplicate path. `_BATCH_PHASE` updated.
- **Validation** (`engine/nl_editor_validation.py`): `create_character` added to
  `KNOWN_OP_TYPES` with a name + id-collision check (slug warning skipped — `player_<Name>`
  ids are mixed case by convention).
- **Front end**: `tools.ts` `create_node` branches `kind === 'character'` to a
  `create_character` op carrying the canonical `player_<name>` id (so a following `attach`
  resolves); `staging.ts` adds the op to the create phase + per-op fallback (`POST
  /api/players`) + `getStagedCreations`; `ghosts.ts` / `diff.ts` recognise the op.
- **Verified live** (second app copy, `VW_PORT=4445`): `POST /api/graph/batch` with a
  `create_character` op → player registered **and** node `player_Fix_Probe`
  (`type=character`) present with `properties.personality`/`description`; `DELETE
  /api/players/...` removed the node too. No `character_*` bare node.
- Not changed: `handle_create_node` (`/api/graph/node`) keeps its low-level "add a node"
  semantics — the inspector, triggers and items still use it unchanged.
- Note: `tags` land on the Player (per `character_record.py`), not the node, so node-tag
  bulk selectors still don't see characters — that is the task-457 migration, tracked there.

