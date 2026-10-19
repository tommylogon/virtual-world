---
type: task
status: todo
area: world
priority: high
wiki: "[[World Building/World Building Overview]]"
---

# task-694: HTC fixture world: a tiny scenario authored to exercise every turn-panel surface

**Filed:** 2026-10-04
**Related:** task-677,task-448,bug-23,bug-521,task-679

## What

TODO

## Acceptance

A small world (10-20 areas) authored ONCE so the harness (task-693) can exercise
everything the human turn panel does. Content before instrumentation — the fixture
is what makes the checks real.

- [ ] Painted `cell` + `world_scope_id` on every area, so the minimap lattice draws
      (mansion cannot — see task-677's UNMET note).
- [ ] TWO characters sharing a display name in one area, and two sharing a
      nickname across areas — exercises the engine's `__suffix` uniquing, the
      duplicate-import path (bug-521) and task-448's chooser.
- [ ] One hidden way behind a false wall, one locked door, one blocked way —
      exercises bug-23's negative and the way-knowledge gate.
- [ ] One scripted simple NPC with the zombie's behavior shapes (message, damage on
      enter, go-toward-noise) and one human-controlled character with
      preconceived knowledge.
- [ ] At least one item with a flavor trigger and one grapple-ready prop.
- [ ] The harness boots into it and the turn panel opens on the human's slot
      without authoring errors (`tools/tasks.py validate`-equivalent: scenario
      integrity checks green).

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

Intended UI home: load the dedicated HTC fixture through the task-693 harness → open the Human Turn panel on the human-controlled character's slot → exercise the scene, people, ways, item, and grapple surfaces from this one world.

Current availability: the card requires a once-authored 10–20-area fixture with painted cells/scopes, duplicate names/nicknames, a hidden false-wall way, locked/blocked ways, a scripted NPC, preconceived human knowledge, a flavor trigger, and a grapple-ready prop. The fixture is not claimed as authored here.

Live steps when available:
1. Start the fixture with the harness and open the human's turn panel.
   - expected: the minimap lattice draws from every area's `cell` and `world_scope_id`; the panel opens on the human slot with no scenario-integrity errors.
2. Inspect the two same-name characters in one area and the shared nickname across areas; open the person chooser.
   - expected: each character remains separately selectable by its unique node ID and the chooser resolves the right person despite duplicate labels/nicknames.
3. Read WAYS OUT at the false wall and inspect the locked door and blocked way through the panel.
   - expected: the undiscovered hidden way stays absent; the locked and blocked ways expose only the actions/knowledge their states allow.
4. Trigger the scripted NPC's enter damage/noise behavior, use the flavor-trigger item, and grapple with the prop.
   - expected: each event is visible once in the event stream with the correct actor/target; the NPC behavior and grapple use the normal action surfaces.

This section is not a claim that the fixture has been authored or that every turn-panel surface is covered today.
