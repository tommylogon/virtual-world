---
type: bug
status: review
area: characters
priority: high
related: [task-724, task-447, task-463]
---

# bug-524: Inspector shows personality as "undefined" and descriptions blank because it reads them from the Player while they live on the character node

**Filed:** 2026-10-07
**Related:** task-724 (owner of the root cause), task-447, task-463

## Symptom (verified live 2026-10-07)

Character inspector, Bio tab: the Personality textarea shows the literal word
`undefined`; Base Description and Current Description are blank. A value typed in
and blurred does not survive a refresh.

## What is and is not true

The character **has the data**. It is on the character **node**, not the Player:

```
GET /api/state → graph.nodes.player_Belne.properties
  personality      = "You are Belne, a banished goblin from a savage tribe…"
  description      = "A quiet, hardened goblin traveler with wary eyes."
  base_description = "Female goblin wanderer. Smaller than average, scarred, wary…"

GET /api/state → players.Belne
  no `personality` key, no `description` key, no `base_description` key

GET /api/players/Belne/record
  {"appearance":{},"personality":{},"prose":"","record":{}} → the record prose is empty
```

The authored source agrees with the node: `data/library/characters/Belne.json` and
`data/scenarios/kraktooth_goblin_camp.json` both carry the prose under the
character node properties.

## Cause

A read-path split, already documented in **task-724** (same finding, verified with
`Rikka`):

- The **node** (`properties`) owns the authored prose: `base_description`,
  `description`, `personality` (plus `expressions`, `profile_image`, `tags`,
  `traits`, `x`, `y`). This is the node's "node-level definition" role.
- The **Player** never receives it on load. `player.py:186` declares
  `self.personality` and `to_dict` publishes it, but the live world creates the
  Player with no value copied from the node, so `_serialize_player`
  (`engine/serialization.py:150`) — which does not emit the field at all — is a
  co-factor, not the whole story.
- The **inspector reads the Player**: `agent-view.ts:832` `${player.personality}`,
  `:839` `${player.base_description}`, `:841` `${player.description}`. So it reads
  the empty home. The same is true of the LLM prompt (`room-context.ts`
  `player.personality` / `player.description`) — personality and appearance are
  silently absent from every prompt, which is the other half of task-724.

Note the internal inconsistency, which is the giveaway: the inspector already
reads `expressions` / `profile_image` **from the node**, but personality and the
descriptions **from the Player**. The node carries all of them.

## Secondary defect (independent, fixable now)

`agent-view.ts:832` interpolates `${player.personality}` with **no** `|| ''`
guard, so a missing field renders the string `undefined`. Lines 839 and 841 use
`|| ''`, which is why the descriptions are blank rather than `undefined`. The
guard is worth fixing regardless of which home wins.

## Fix — blocked on task-724's decision, not on implementation effort

task-724 lists the two options and owns the choice:

1. **Node stays authoritative for authored prose** → readers (inspector, prompt)
   read `node.properties.personality` / `.description` / `.base_description`,
   matching how the inspector already reads `expressions` / `profile_image`.
2. **Player stays authoritative** → hydrate the prose onto the Player at load
   (node → Player) and publish it in `_serialize_player`.

Do not do both, and do not add a third copy.

## Acceptance

- [ ] Whichever home task-724 picks, the Bio tab shows Belne's real personality
      and both descriptions, and an edit round-trips across a refresh.
- [ ] The personality interpolation is guarded (`|| ''`) so a missing field is
      empty, never the literal `undefined`.
- [ ] The LLM prompt contains the "You are <name>. Personality: …" preamble again
      (task-724's acceptance), proving the prompt path reads the same home.
- [ ] No new copy of the data is introduced.
- [ ] `node tools/unit/run.cjs` and `npm run build:ts` pass.

## Fix landed (2026-10-07) — awaiting restart verification

Decision recorded in task-724: the character node is the persisted home for
authored definition; the Player reads it. First landing:

- `engine/serialization.py::_serialize_player` now publishes `personality`,
  `base_description`, `description` on the live read payload, sourced from the
  character node (`personality`/`base_description` node-first, `description`
  Player-first so an equipment-derived current description still wins).
- `engine/serialization.py::to_scenario_dict` strips the three from the players
  block, so a saved file keeps them only on the node (single home).
- `routes/player_ops.py::handle_update_player` mirrors a definition edit onto
  the node, so an inspector save lands on the persisted home.
- `static/js/inspector/agent-view.ts:832` guards `${player.personality || ''}`.

Gates: `npm run build:ts` clean, `node tools/unit/run.cjs` 618 passed,
`python -m py_compile` clean. **Verified live 2026-10-07** after a server
restart: the personality and both descriptions display and round-trip in the
Bio tab. Location and tags/traits de-duplication (task-724) remain open.

## Note on the duplication

This bug is the UI-visible face of task-724's `personality`/`description`
finding. It is filed separately only because it is a concrete, reproducible
defect (screenshot + live payload). If task-724 is actioned first, close this
against it rather than fixing twice.
