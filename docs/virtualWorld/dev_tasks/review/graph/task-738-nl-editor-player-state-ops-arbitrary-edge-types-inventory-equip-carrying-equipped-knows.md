---
type: task
status: review
area: graph
priority: high
---

# task-738: NL editor: Player-state ops + arbitrary edge types (inventory, equip, carrying/equipped/knows)

**Filed:** 2026-10-08
**Related:** 

## Goal

The editor's op model is graph-shaped; it cannot touch Player state. Add staged ops for inventory add/remove, equip/unequip, and the real edge vocabulary (carrying, equipped, knows, owns, faction) instead of the spatial-only in/on/under/behind/beside/at enum. Route player_* ops to routes/player_ops.py on Apply. See docs/design/nl-editor-full-authoring.md.

## Acceptance

- TODO

## Landed (2026-10-08) — edge vocabulary / inventory / equip

- `attach` and `spawn_library_item` relation enums now include `carrying` and
  `equipped` (`static/js/nl-editor/tools.ts`), with descriptions telling the agent
  "carrying" = inventory, "equipped" = worn/wielded. The server `attach` already
  writes `edge.type = relation`, and `EDGE_CARRYING`/`EDGE_EQUIPPED` are exactly those
  strings (`graph.py:840-841`), so no server change was needed.
- **Verified live** (second copy, `VW_PORT=4445`): create an item + `attach
  {relation: carrying}` → it appears in the character's `you.carrying`; `detach` removes
  it; `attach {relation: equipped, properties:{slot}}` → it appears in `you.wearing`.
- Known limit: equipping via a raw edge sets the `EDGE_EQUIPPED` edge the engine reads,
  but bypasses the equipment system's slot-conflict / auto-unequip handling, so the agent
  can stage a double-booked slot. Guard or route through the equipment path if that bites.

## Landed (2026-10-08) — Player-state ops (`update_player`)

- New staged op **`update_player`** with a validated `patch` of exactly the non-edge
  Player fields:
  - `memories` — append entries via `Player.add_memory`
  - `relationship` — `{target, closeness}` written through
    `engine.relationships.apply_relationship_delta` (whose docstring: it is "the only
    writer of closeness"; cause recorded as `nl_editor`)
  - `remove_relationship` — drop a relationship by resolved key
  - `emotion` — `{name, delta}` via `Player.spike_emotion`
- Validator (`engine/nl_editor_validation.py`): `update_player` in `KNOWN_OP_TYPES`,
  `PLAYER_PATCH_KEYS` whitelist, character must resolve, non-empty patch, memory
  `text` required, relationship `target` required and `closeness` numeric, and the
  emotion **name must be a real dimension** — an unknown dim is silently ignored by
  `emotion.spike`, so it is an error here.
- Apply (`routes/graph_ops.py`): `_apply_batch_op` branch + `_BATCH_PHASE['update_player'] = 1`
  + `_resolve_player` (registry key, `player_<name>` node id, or display name).
- Tool (`static/js/nl-editor/tools.ts`): `update_player` definition + executor, staged
  like `attach`. Tool count 30 → 31.
- Tests: `tests/test_nl_editor_player_ops.py` (**5 passed**) — memory append, relationship
  adjust/remove, emotion pulse, unknown character, and the validator's accept/reject set.

## Closed

- The goal note's "knows/owns/faction" is wrong: there are no such edge types. Ownership
  is a property and relationships are Player state, so the edge vocabulary is spatial +
  carrying/equipped + triggers + connection — all reachable, and the non-edge Player
  state now has `update_player`.

**Live-verified 2026-10-09** against a second server copy on :4445 (camp loaded):
`POST /api/graph/batch {strict_validation:true}` with an `update_player` op applied —
`{applied:{emotion:"afraid"}, player:"Arix"}` — and Arix's `afraid` affect dimension
moved to `12.0` in the next `GET /api/state`. The gate is live too: the same batch
with `emotion:{name:"not_a_dim"}` returned **422** with *"Unknown emotion dimension
'not_a_dim' …"*. Not yet exercised: the editor **staging** the op through the agent
loop (needs the model) — the editor UI itself was served but not scripted.

