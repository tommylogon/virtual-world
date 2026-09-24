---
type: task
status: todo
area: items
priority: medium
---

# task-514: Item provenance and acquisition history

**Filed:** 2026-09-24
**Related:** task-408, task-403

## Goal

Give items an acquisition record so gear carries history — Mikka's wrench
stolen from a human wagon, Gribba's apron taken from an abandoned farm, Vekka's
mirror traded from a scout, Krikka's favourite coin found in a dead dwarf's
boot — and surface it on examine and in prompts.

## Context

- The item schema has no origin/history field (`data/library/items/cleaver.json`,
  `rope.json`). `library_id` is a template link (task-392), not a story.
- Paths that would need to record it:
  - `routes/library_ops.py:_spawn_library_item_node` (line 110),
  - the `give_item` effect (`engine/effect_handlers/spawn.py:141`),
  - character inventory load (`routes/library_ops.py:540-579`),
  - transfers (`engine/items/transfer_actions.py`, give line 16 / steal line 96).
- Node identity is id-first (task-446); the record belongs on the instance, not
  the template.

## Proposal

- Optional `provenance` on item nodes, e.g. `{text, source, area, tick}` (or a
  short bounded list). A library template may define a default; an instance
  overrides/attaches it on spawn, loot or steal.
- Set it at authoring (the matrix's "How they acquired it" column), on spawn
  effects, on take-from-container, and on steal (new acquisition).
- Surface on `examine` and in the agent prompt as one bounded line so it stays
  flavor rather than a log dump.

## Open questions

- One `text` string versus an event list.
- Does `steal` rewrite provenance (new owner) or append?
- Do we reveal provenance to non-owners on examine?
- Stacking: `engine/items/stacking.py` keys identity on `library_id`/name plus
  identity fields — decide whether provenance participates (per-instance
  provenance would block stacking of otherwise identical items).

## Acceptance

- An item node can carry acquisition provenance; library authoring can set it.
- Spawn/loot/steal can record it without breaking stack identity (decision
  documented).
- `examine` renders it and the prompt includes a bounded form.
- The record lives on the instance, not the shared template.
- Covered by a test.

## Non-goals

- A general history/event-log UI (task-340 is the unrelated event stream).
- Changing `library_id` semantics.

## Verification

- Unit test: author/spawn with provenance → examine shows it; steal updates it.
- Document stacking behaviour in the test or task notes.
