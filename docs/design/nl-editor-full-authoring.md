# NL editor — full authoring (the "everything" scope)

**Status:** design / backlog. Captured 2026-10-08 from a user request to let the NL
editor do "crud on all entities, edge crud, full trigger and behaviour creation,
handle issues from the Issues tab via NL, add/remove inventory and equipment —
everything". This doc scopes that, not promises it.

## Principle

The NL editor's tools are thin wrappers over the app's own authoring APIs
(`graph_ops`, `player_ops`, the trigger compiler, the validator). So "everything"
means one thing concretely:

> **Every authoring mutation the app can perform, the NL editor can stage** —
> with validation on Apply, a ghost/preview where it makes sense, and one undo
> snapshot per Apply.

Today it covers the graph *shape* (areas, items, ways, tags, traits, bulk
patches, library archetypes) and half of characters. It is blind to **Player
state**, **behaviours**, and the **Issues tab**. Those are the entire second half.

## What a character is: the node half and the Player half

Two different things share the word "character", and that is the source of most of
the confusion here — and of `bug-527`:

- **The character graph node** (`player_<name>`, `type: "character"`, minted by
  `PlayerManager.add_player`) — the *identity / definition* half. Today it is thin:
  `name` + `node_id`, plus authored prose (`personality` / `description` /
  `base_description`) where a scenario writes it. Task-457 is the migration to make
  this node the single source of truth for the definition; it is **in progress**.
- **The `Player` object** — the *runtime* half, one per character (NPC, background
  citizen, or the human avatar alike). It holds nearly everything today: identity
  prose, `stats`, `skills`, `traits`, `vitals`, `emotion`, `conditions`,
  `relationships`, `memories`, `behaviors`, `tags`, `activity`, `facing` …
- **Edges** carry a few fields directly: `equipped` (`EDGE_EQUIPPED`) and
  `current_area` (`in` / spatial edges). `state` (dead / prone) is **derived** from
  the conditions, stored nowhere.

`engine/character_record.py` is the canonical audit of this split —
`DEFINITION_FIELDS` tags every field `node` / `player` / `edges` / `derived`, and
`definition_drift` measures how far a character is from the node being canonical.

"Player" is **not** "the active character": `active_player` is a single pointer at
whichever character currently holds the turn. Every character has a `Player`.

Consequence for the editor: a `character` op targets the one entity — authored
fields route to node `properties`, runtime fields route to the `Player` API.
Creating a character therefore means `add_player`, which mints **both** halves; that
is the fix for `bug-527`.

## The architectural crux: one op model, three state domains

`static/js/nl-editor/staging.ts` is **graph-op shaped** (`create_node`,
`update_node`, `attach`, `detach`, `connect_areas`, …). Everything requested
falls into three domains, only one of which fits that shape:

| Domain | Examples | Fits the current op model? |
|---|---|---|
| **Graph** | nodes, edges, tags, traits, ways | yes |
| **Player** | inventory, equipment, memories, relationships, emotion, skills, plans | **no** — these live on the `Player`, keyed by id, not on node properties |
| **Behaviour** | triggers, conditions, effects | **no** — compiled + validated by a separate pipeline (`engine/triggers`, `shared/trigger-graph`) |

**Decision needed first.** Either:
- **(A)** extend the staging op set with `player_*` and `behavior_*` op kinds against
  the *same* buffer (one tray, one undo, each op routed to the right API on Apply);
  or
- **(B)** a second buffer per domain.

Recommend **(A)**. The user's mental model is a single "staged changes" tray, and
the atomic undo already assumes one batch. The cost is teaching `staging.ts` +
`ghosts.ts` + the Apply validator about the new op kinds.

### Corrected model (2026-10-08)

There is **one entity** (a character) and **one op surface** — not three domains:

- **Authored** fields live on the character node's `properties` (`personality`,
  `description`, `base_description`, authored `tags`/`traits`).
- **Runtime** fields live on the `Player` object (`vitals`, `stats`, `skills`,
  `equipped`, `inventory`, `memories`, `relationships`, `emotion`) — serialized with
  the world, **not** node properties.

So a `character` op is one op the Apply router splits by field: authored → node
properties, runtime → the Player API. **Triggers are graph data** — a `logic_trigger`
node + a `triggers` edge, the same props written to both
(`engine/triggers/materialize.py`: "no parallel trigger format"); a *behaviour* is the
compiled projection, derived not authored. **Undo already covers both**:
`_push_undo_snapshot` (`routes/saveload.py:27`) snapshots the whole world (graph +
players), so one-undo-per-Apply holds across node, player and trigger changes. The
domain table above is the older framing and should be read as *storage layers*, not
domains.

## Workstreams

- **A. Entity CRUD parity** — fix character create (`bug-527`, already filed); add
  **duplicate** (the app has `handle_duplicate_node`, task-377; the editor has no
  tool); rename; reparent (move between areas) as one atomic op.
- **B. Edge CRUD** — the current relation enum is spatial only
  (`in/on/under/behind/beside/at`, `tools.ts:658,749`). Expose the real edge
  vocabulary the graph supports: `carrying`, `equipped`, `knows`, `owns`,
  `faction`, … plus per-edge properties.
- **C. Player state** — inventory add/remove, equip/unequip, **memories**,
  **relationships**, emotion, skills, plans. Id-keyed, `Player`-backed
  (`PlayerManager`, `routes/player_ops.py`). This is what makes "give Jane a sword"
  and "Jane remembers the fire" work.
- **D. Behaviours** — full trigger authoring: expose the condition/effect schema
  and the graph→behaviour compile (`shared/trigger-graph.ts`,
  `compileToBehaviorsWithIssues`) so the editor can create *and validate* a
  trigger's logic, not just mint an empty `logic_trigger` node. Reuse the existing
  machinery; do not invent a second trigger format.
- **E. Issues → NL** — a `list_world_issues` read tool over
  `GET /api/triggers/validate` (`validator-panel.ts:84`), then stage fixes with the
  existing tools and **re-validate**. This is the cheapest, highest-value slice:
  the issue list is already a machine-readable `{code, node, message, severity}`.
- **F. Scopes / ownership** — `world_scopes` hierarchy, ownership, gateways
  (task-397, task-583). Currently zero tooling.
- **G. Library parity** — `spawn_library_character` (items-only today), and
  refresh/link parity so a template change reaches spawned nodes.

## Explicitly NOT in scope (another surface owns it)

Dialogue content, the WorldPainter map (`get_background_map` is read-only by
design), time / calendar / weather / forecast, fog + lighting config, and the
world-lore editor. Folding these in would build a second home for each.

## Phases

- **P0** — `bug-527` (character CRUD) · edge vocabulary + `carrying`/`equipped` ·
  inventory/equip player ops · `list_world_issues`.
- **P1** — behaviours (trigger authoring + validate) · duplicate · rename/reparent ·
  bulk delete (`delete_matching_nodes`).
- **P2** — memories / relationships / emotion · `spawn_library_character` · scopes.
- **P3** — world-lore / time / fog, if wanted.

## Reuse (do not rebuild)

`engine/triggers/*` + `shared/trigger-graph.ts` (behaviour compile + validate) ·
`routes/player_ops.py` (players, inventory, equip) · `GET /api/triggers/validate`
(issues) · `handle_duplicate_node` (task-377) · `PlayerManager` and its `player_*`
nodes · `tools/way_properties.py` (the way-property vocabulary the editor is not
taught today).

## Guardrails

- Every new op kind validates on Apply — extend the task-461 gate.
- Ghost preview for the new *graph/edge* ops; state ops (player/behaviour) get an
  explicit "no preview" rather than silently nothing.
- One undo snapshot per Apply stays true.
- The editor must be able to run the validator *on the world after Apply*, so the
  Issues flow can confirm a fix landed.
