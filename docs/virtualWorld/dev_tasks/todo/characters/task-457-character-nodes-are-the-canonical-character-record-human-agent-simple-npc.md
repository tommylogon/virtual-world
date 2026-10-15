---
type: task
status: todo
area: characters
priority: high
related: [task-316, task-446, bug-549]
wiki: "[[Characters Overview]]"
---

# task-457: Character nodes own authored definition; Player owns runtime state

**Filed:** 2026-09-22

**Reframed:** 2026-10-15

<!-- deps:start -->
**Related:** [[task-316-id-backed-character-identity]], [[task-446-id-first-node-identity]], [[bug-549-character-definition-is-blank-on-the-live-player-after-a-scenario-load]]
<!-- deps:end -->

## What

Make each character graph node the persisted home for that character's authored
definition, while keeping Player as the character's runtime model. Existing
prompts and UI may read a Player-shaped projection of node-owned definition, but
the saved character definition has one source of truth.

This is the model boundary that task-446 needs. This card owns authored-field
storage and projection. Task-446 owns id-first player identity, duplicate-name
resolution, and relationship identity. Do not fold that migration into this
card.

## Ownership boundary

| Data | Authoritative home |
|---|---|
| Authored personality, base_description/description prose, authored tags, and authored traits | Character node properties |
| Private character data, including GIMP goals and motivations, MOSIAC schedules and obligations, memories, emotion, vitals, plans, pursuits, activities, perception, and mutable behavior state | Player |
| Physical location, equipment, and containment | Existing graph edges and their current contracts |
| Derived state and lookup indexes | Computed from their existing source; never copied onto the node as a second record |

Where an existing Player field mixes authored data with mutable behavior state,
the implementation must map those meanings explicitly before writing either
value. It must not mirror one mutable field in both places or move the
character's private mind onto a world node.

If the current description is composed from authored prose and equipment or
state, preserve the authored base on the node and keep the composed current
description as a Player/runtime projection. Never write derived prose back over
the authored base.

## Acceptance

- [ ] engine/character_record.py defines a field ownership map that separates
      node-owned authored definition, Player-owned private/runtime data,
      edge-backed state, and derived values. Mutable fields such as vitals,
      memories, emotion, goals, schedules, plans, and activities are not
      classified as node definition.
- [ ] Creating a human, agent, or simple NPC gives its existing character node
      the authored definition properties. The node remains linked to its
      Player through the existing identity seam; id-first registry changes
      remain in task-446.
- [ ] On load, existing node properties win over conflicting legacy values in
      the players block. For a legacy character whose authored definition exists
      only in the players block, load migrates those missing properties onto
      the node and hydrates the Player projection from the resulting node.
- [ ] Persisted scenario and savegame data stores authored definition on the
      character node only, with no second authored copy in that character's
      players-block record. The live /api/state payload may expose the Player
      projection for existing prompt and UI consumers.
- [ ] Goals, schedules, motivations, intentions, obligations, memories, vitals,
      emotion, plans, pursuits, activities, perception, and mutable behavior
      state remain on Player; equipment and location remain edge-backed.
- [ ] Authored tags/traits and mutable behavior tags/traits have an explicit
      mapping. Loading or updating one cannot silently overwrite the other.
- [ ] A targeted scenario fixture proves the same ownership and projection path
      for a human, an agent, and a simple NPC, without adding a second character
      node or a new character-state store.
- [ ] Mechanism tests assert which value was read when node properties and a
      legacy players block disagree, and which migration branch ran when node
      properties are absent.

## Why

PlayerManager.add_player and the scenario loader currently create bare
character nodes. engine/character_record.py is a read-only drift audit, and its
current field list classifies mutable mind and runtime state as if it should
move to the node. Meanwhile, serialization already reads authored prose from
node properties for the live payload and strips it from the saved scenario's
players block. Without a writer and a precise ownership boundary, scenario
loads can leave the live Player blank, as reported by bug-549, or lose authored
values on a later save.

## How

1. Correct the field map in engine/character_record.py to match the ownership
   boundary above; do not create a blanket Player-to-node copier.
2. Write authored properties at the existing character creation seam. During
   legacy load, seed only missing node properties from the old players block;
   when both copies exist, the node wins.
3. Hydrate the Player's existing runtime-facing projection from the node-owned
   authored properties before prompt, dressing, and UI consumers read it.
4. Serialize the authored definition once on the node. Keep private GIMP/MOSIAC
   data on Player and physical relationships on their existing edges.
5. Keep id-first keying and display-name resolution in task-446.

## Steps to verify

1. Run python -m pytest tests/test_character_record.py.
   - expected: the ownership map excludes Player-private, runtime,
     edge-backed, and derived fields from node definition drift.
   - observed: not run; task remains open.
2. Run python -m pytest tests/test_serialization.py.
   - expected: a conflicting node value wins; a legacy Player-only definition
     migrates to the node; scenario and savegame files contain one authored
     copy.
   - observed: not run; task remains open.
3. Add a focused scenario test covering human, agent, and simple-NPC creation
   and load.
   - expected: each resolves through the existing Player/node mapping; prompt
     and UI payloads receive the authored projection; private mind/runtime data
     stays on Player; no duplicate character node is added.
   - observed: not run; task remains open.

## Browser UI and intended live verification

Intended UI home: Character Inspector → Bio for authored definition and
**🧠 Mind** for private runtime state, on the same selected character.

Current availability: Bio and Mind surfaces exist; the canonical node writer
and load projection are not implemented.

Live steps when available:

The existing Character Inspector is the author-facing surface for this
boundary: authored definition belongs in **Bio**; private runtime state belongs
in **🧠 Mind**. Keep both on the same inspected character. Do not add a second
character record or a separate mind panel.

1. Open a scratch scenario containing one human, one agent, and one simple NPC;
   select each character in turn and open the Inspector's **Bio** tab.
   - expected: authored personality, description, and authored traits are
     visible on the character being inspected.
2. Open **🧠 Mind** for the same character and inspect goals, memories, vitals,
   plan/pursuit, and activity where present.
   - expected: private/runtime values appear in the existing Mind sections and
     remain distinct from the authored Bio fields.
3. Use the top menu's **Export Scenario File…**, then inspect the exported
   character node and Player record for each character.
   - expected: authored definition is stored once on the node; private mind
     state is stored on Player; no duplicate character node or second authored
     copy is introduced.
4. Reload the scratch scenario and revisit the same Bio and Mind surfaces.
   - expected: the node-owned definition hydrates the same Player projection,
     and existing UI consumers still show the character correctly.
5. Compare the panels with the corresponding values in **/api/state**.
   - expected: API projection agrees with the node source of truth and the
     Player-owned private state.

These browser steps define intended access and live acceptance; they are not a
claim the implementation works today. No browser run is recorded for this
updated card. An API-only implementation is not complete if the existing
Inspector surfaces fail to show the correct fields.

## Files

- engine/character_record.py
- engine/player_manager.py
- engine/serialization.py
- tests/test_character_record.py
- tests/test_serialization.py
- A focused character-definition projection test if the existing tests do not
  cover the end-to-end path.

## Related work

- task-446 is blocked on this model boundary and owns id-first identity
  migration, including duplicate display names and relationship keys.
- task-316 established stable character IDs.
- bug-549 is the scenario-load symptom of missing node-to-Player hydration;
  its fix must use this same source-of-truth path.

## Measured state (2026-10-15)

- engine/player_manager.py:add_player creates a character node without
  definition properties.
- engine/serialization.py also creates a bare character node in the scenario
  load path.
- No node-definition writer or Player hydration helper is currently wired.
- The earlier proposal to move vitals, memories, emotion, and the whole private
  mind onto the graph node is superseded by the ownership boundary above.
