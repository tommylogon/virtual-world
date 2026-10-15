---
type: task
status: todo
area: crafting
priority: high
related: [task-831, task-703, task-131, task-399, task-466]
---

# task-840: Crafting runtime — who crafts, activities, backsim, abort

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]], [[task-131-stateful-actions-over-time]], [[task-399-background-character-simulation-and-reactivation]], [[task-466-interrupt-relevance-evaluator-shared-by-timeskip-fidelity-soak]]
<!-- deps:end -->

## What

One card for the five actor questions — they share one mechanism (the
Activity), so splitting them makes five cards touching one dispatch.

**Q1 — agents, NPCs, humans:** same verb, three doors. Human: turn modal /
command line `Make X` → requirement check → timed cooking Activity.
LLM agent: `make <recipe>` as a turn action; prompt builder lists
craftable-now recipes as guidance (backend resolves leniently, per the
established `contextual-actions.ts` pattern). Simple NPC / backsim: never
emits verbs — the background tier picks a recipe the camp can afford and
opens the same Activity via `_begin_task` (`background_simulation.py:345`).
No second code path.

**Q2 — Activity:** yes. Every recipe with `duration_min > 0` starts a
`cooking` Activity (new `data/library/activities/cooking.json`:
interruptible, blocks turns, binds station). Instant recipes resolve
immediately through today's `craft()`. Completion rechecks conditions,
rolls the tier, spawns outputs. Interruption never spawns outputs.

**Q3 — backsim while humans craft:** yes, unchanged. `process_due` skips
anyone mid-activity; `tick_activity` advances the cook. A human mid-pottage
is exactly like a human asleep. Attention tiers (task-411/418) schedule
cooking NPCs — no crafting-specific scheduling.

**Q4 — abort:** three ways, all existing machinery. Any other action
interrupts (nothing consumed, no outputs, "the pot waits"). Explicit
`stop` → `stop_activity()`. Involuntary (damage/noise/hostile via
`interrupts.py`) ends it like sleep. No partial progress — restart from
scratch (documented, avoids partial-state modeling).

**Q5 — minigame:** hook, not build. Tier roll becomes one
`resolve_craft_tier(recipe, player)` call the Activity completion invokes;
a future minigame replaces the single roll with staged rolls feeding the
same four tiers. No minigame UI here.

**Q6 — no crafting via editor/inspector:** invariant. The inspector edits
data, never performs world actions. Library tab browses/authors;
Mind panel shows known recipes; neither executes a craft.

## Why

Five questions, one mechanism. The Activity system already does timed +
visible + interruptible + backsim-skipped — crafting rides it instead of
rebuilding it.

## How

1. New `data/library/activities/cooking.json` (interruptible,
   blocks_turns, binds station, ticks-remaining via `activity_description`).
2. `craft()` split: check (fail-closed missing list) → start Activity
   (reserve inputs) → on completion: recheck → `resolve_craft_tier` →
   consume + spawn.
3. Prompt builder: craftable-now recipes in contextual actions (guidance).
4. Backsim: recipe selection in `_act`, Activities via `_begin_task`.

## Steps to verify

1. Start pottage, act otherwise mid-cook.
   - expected: activity ends, nothing consumed or spawned, "the pot waits".
   - observed: TODO
2. Backsim a hungry camp holding pottage inputs.
   - expected: NPC starts cooking Activity; completion spawns pottage.
   - observed: TODO

## Acceptance

- [ ] `Make X` starts a visible interruptible cooking Activity (timed) or
      resolves instantly (untimed).
- [ ] Abort never consumes or spawns; restart from scratch.
- [ ] One dispatch for agents, NPCs, humans; prompt guidance only.
- [ ] `resolve_craft_tier` seam exists; no minigame built.
- [ ] No craft execution in inspector, library, or painter.

## Files

- `data/library/activities/cooking.json` — new
- `engine/crafting.py` — check/reserve/complete + tier seam
- `engine/background_simulation.py` — recipe selection in `_act`
- `static/js/agent/prompt-builder/contextual-actions.ts` — listing

## Browser UI and intended live verification

Intended UI home: turn modal → Make pottage → activity banner with
ticks-remaining + Stop → completion toast with tier flavor.

Current availability: card only; timed cooking not yet implemented.

Live steps when available:
1. Make pottage at a lit fire, then Stop mid-cook.
   - expected: abort with nothing consumed; re-make completes with tiered
     outputs in inventory.
