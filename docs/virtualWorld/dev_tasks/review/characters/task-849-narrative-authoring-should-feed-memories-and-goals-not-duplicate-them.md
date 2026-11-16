---
type: task
status: todo
area: characters
priority: medium
related: ['task-404', 'task-704', 'task-725', 'task-733', 'task-734', 'task-822', 'task-829']
wiki: "[[Characters/Persona]]"
---

# task-849: Narrative authoring should feed memories and goals, not duplicate them

**Filed:** 2026-10-16
**Related:** 

<!-- deps:start -->
**Related:** [[task-404-character-life-experience-generator]], [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-725-memories-carry-nothing-about-death-vitals-travel-perception-or-resurrection]], [[task-733-character-sheet-a-full-page-worldgraph-style-person-form-that-compiles-into-viwo-primitives]], [[task-734-knowledge-is-memory-fold-known-recipes-known-places-into-one-prose-data-record-with-episodic-vs-semantic-kinds]], [[task-822-gimp-goal-data-reason-carrying-refs-achievement-predicates-and-auto-reached]], [[task-829-growth-wiring-for-persona-fields-via-items-triggers-and-consumers]]
<!-- deps:end -->

## What

Resolve the narrative/biography/arc vs memories/goals overlap: authored narrative seeds or links runtime memory and goal entries through existing systems, with one store per fact.

## Why

TODO

## How

TODO

## Browser UI and intended live verification

Intended UI home: Character Inspector -> Mind -> Memories and Goals panels.

Current availability: Planned; narrative authoring feeds runtime memory and goal records via single-store architecture.

Live steps when available:
1. Open Character Inspector -> Mind for a character with authored narrative backstory.
   - expected: Backstory milestones appear as linked memory records without duplicating standalone narrative text blocks.
2. Inspect the Goals tab.
   - expected: Long-term character motivations link directly to active goal nodes.
3. Edit a narrative milestone in the editor and save.
   - expected: The underlying memory or goal record updates in place without orphaned duplicates.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
