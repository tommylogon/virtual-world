---
type: task
status: todo
area: crafting
priority: medium
related: [task-831, task-840, task-734, task-691]
---

# task-841: Known recipes live in the Mind panel

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-840-crafting-runtime-who-crafts-activities-backsim-abort]], [[task-734-knowledge-is-memory-fold-known-recipes-known-places-into-one-prose-data-record-with-episodic-vs-semantic-kinds]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]]
<!-- deps:end -->

## What

Known recipes are character knowledge — procedural memory — so they render
in the Mind panel (`static/js/inspector/mind-view.ts`), not in an
inspector action list and never as a craft-execution surface.

Content: `player.crafting_known` names + skill-gated recipes (skill at
level >= 1) + recipes carried on items (`properties.recipe` on a cookbook
or note in inventory). Each row: recipe name, source tag (global / taught
/ discovered / cookbook / skill), skill + DC, duration. Clicking a row
opens the library entry (read-only here). A `Make` button MAY appear on
the row for the controlled character — it emits the same turn-modal
`Make X` command, it does not execute anything inline.

No execution in this panel. The Mind panel reads knowledge; the turn
system performs actions. That separation is the invariant from task-840.

## Why

Task-734 folds known-recipes into the unified memory record as procedural
knowledge; the Mind panel already renders a `procedural` category color
(`mind-view.ts` CAT_COLORS). This card puts the separated store
(`crafting_known`) where the unified model says it belongs.

## How

1. Mind panel `procedural` section gains a Recipes group reading
   `worldState.players[name].crafting_known` + derived skill/carried
   sources (backend exposes one `known_recipes` list per character —
   no new stores, just a projection).
2. Row action (controlled character only): emit `Make X` to the turn
   system. Read-only for everyone else.

## Steps to verify

1. Teach a character a recipe, open Mind.
   - expected: recipe listed under procedural with its source tag.
   - observed: TODO
2. Click Make as the controlled character.
   - expected: identical to typing `Make X` in the turn modal (Activity
     starts or fail-closed missing list).
   - observed: TODO

## Acceptance

- [ ] Known recipes render under procedural in the Mind panel with source.
- [ ] Make emits the turn command; panel executes nothing itself.
- [ ] Read-only for non-controlled characters.

## Files

- `static/js/inspector/mind-view.ts` — Recipes group
- Backend: `known_recipes` projection per character

## Browser UI and intended live verification

Intended UI home: character → Mind panel → procedural → Recipes.

Current availability: card only.

Live steps when available:
1. Open Mind for a cook who knows pottage.
   - expected: pottage listed with source + skill/DC/duration; Make
     behaves exactly like the turn-modal command.
