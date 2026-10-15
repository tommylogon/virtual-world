---
type: task
status: todo
area: world
priority: medium
blocked_by: [task-746, task-745]
---

# task-747: WorldPainter compiler emits terrain hazards (river, cliff, thorn, fall) from the painted layers

**Filed:** 2026-10-09
**Related:** task-496 task-525 task-529 task-745

<!-- deps:start -->
**Blocked by:** [[task-746-a-single-roll-hazard-effect-one-check-branch-forced-move-and-a-sweep-guard-against-cascades]], [[task-745-worldpainter-hazards-a-current-strength-paint-layer-plus-a-hazards-json-category-table]]
<!-- deps:end -->

## What

world_compile emits no triggers today; give it a hazards pass that reads data/worldpainter/hazards.json (task-745) and the painted layers and attaches a compact hazards:[...] descriptor to generated ways/areas (the engine expands it at load, so no trigger-node spam). Rules: a way crossing water with no bridge -> river; a way with requires: jump over water -> fall into the water; a _climb_step rising or falling -> cliff/fall, REPLACING the hard refusal task-525 chose where the author wants a check with a consequence; a thorn/bramble biome -> thorns. Severity from storey_delta (an 89-storey drop is lethal). Direction from the current layer, defaulting to the storey gradient. This also gives the on_fail hook its compiler side, and the hazard reader is what makes trigger-written condition tags (flooded) fire consequences. Depends on task-745 (layer+table) and task-746 (effect).

## Acceptance

- TODO

## Status (2026-10-09)

**Blocked, not started — the dependency recorded is real.** The card says it
"Depends on task-745 (layer+table) and task-746 (effect)". As of 2026-10-09:

- **task-745**: only the registry half is built (`data/worldpainter/hazards.json`,
  `engine/hazards.py`, the gate, the Vocabulary-tab integration). The
  **current/strength paint layer** — which supplies the rules' *direction* and
  part of their *severity* — is **not built**.
- **task-746** (a single-roll hazard effect: one check, branch, forced move, sweep
  guard) is in `todo/triggers` — **not built**. There is **no consumer** for a
  `hazards:[...]` descriptor.

Attaching `way_props["hazards"]` now would produce a field that serializes, looks
functional, and is read by nothing — the exact "exists ≠ wired" anti-pattern this
repo treats as a finding. So this card waits for task-746 (the consumer) and the
task-745 paint layer, then the derivation is a small, testable compiler pass.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: WorldPainter → paint water, bridge, elevation/cliff, and thorn-biome layers → compile the painted world → inspect generated ways/areas in the graph and traverse them in the game view.

Current availability: the card reports that `world_compile` emits no hazard descriptors. Terrain hazard authoring and runtime expansion are planned; no hazard behavior is claimed as implemented.

Live steps when available:
1. Paint a water crossing without a bridge and compile. Inspect the generated way in the graph and then move a character across it.
   - expected: the generated way carries the river hazard descriptor and movement resolves the authored hazard rather than silently treating it as an ordinary safe way.
2. Paint a jump-required crossing over water, compile, and attempt the crossing with a character lacking the required ability.
   - expected: the jump check branches to the authored fall-into-water outcome; the action does not bypass the check.
3. Paint a `_climb_step` with a positive and negative storey delta, then traverse each generated way.
   - expected: the descriptor uses the direction/storey gradient and the selected check consequence; the task-525 hard refusal remains only where the author did not specify a hazard consequence.
4. Paint a thorn biome and test movement through it; also test the large storey-drop severity case.
   - expected: thorn effects and severity follow `hazards.json`; an 89-storey fall uses the authored lethal tier, not a fixed minor penalty.

This section is not a claim that planned UI exists or works today.
