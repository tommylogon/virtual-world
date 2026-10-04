---
type: task
status: review
area: prompting
priority: high
related: [task-693, task-409, task-702]
---

# task-700: Grounded plan contract: the LLM plan phase emits typed steps validated against world facts

**Filed:** 2026-10-04
**Related:** task-693,task-409

## Goal

Change the plan phase from {'steps': ['prose']} to typed steps in the primitive vocabulary ({act, item/target, area, until, duration}) and validate them against the graph before acceptance. Motivation (live evidence 2026-10-04): Vekka planned 'use hanging meat' against flavor text and resolved to the failure - poetry plans hallucinate affordances. A planner composing from facts cannot. The typed step format must be the SAME artifact the plan executor (see GOSP executor task) can run for simple NPCs - one contract, three consumers: LLM shopping list, engine executor, condition-leaf validator. Keep the freeform plan prompt as fallback when grounding rejects a step: rejection returns the failed preconditions so the LLM re-composes.

## Acceptance
- [x] The plan phase responds with typed steps (act/item/target/area/until/
      duration) instead of prose; the decide prompt consumes the plan via
      PlanTracker's (CURRENT) marker exactly as today (grounded steps render to
      canonical strings: `take dried meat (in Food Storage)`).
- [x] A grounding validator (agent/plan-grounding) checks every step against
      the prompt's facts before acceptance; rejected steps return their failed
      preconditions plus the fact list to the LLM exactly once for
      re-composition; whatever still does not ground is dropped, never
      executed.
- [x] The Vekka regression: "use hanging meat" is REJECTED at plan time
      (unit test: `tools/unit/test_plan_grounding.js`, flavor-only step). Live
      stream confirmation lands with task-702's mechanical execution.
- [ ] A plan whose steps all ground is executed without the decide phase for
      mechanical steps - deliberately deferred to task-702 (the executor);
      this wedge keeps the decide phase as the actor.
- [x] The typed step format is the contract task-702 consumes (rendered form
      locked by unit test; the executor lifts the structure into PlanTracker).
- [x] Fallback preserved: legacy prose contract accepted when the LLM emits
      strings, and the whole grounding layer degrades to the old path if the
      module is unavailable.

## Implementation (2026-10-04)

- `static/js/agent/plan-grounding.ts` (new) - pure fact-side validator:
  collectFacts (prompt-shaped: area items, carried, people, exits, known
  areas), groundStep per act, lenient word-overlap matching in the spirit of
  the action target matcher, canonical render. Unknown acts fail closed.
- `static/js/agent/plan-manager.ts` - typed plan contract in the prompt; parse
  typed steps; ground; ONE bounded re-composition with a
  `=== GROUNDING REJECTIONS ===` block; rejections logged to the stream
  (system-msg); legacy prose contract accepted as fallback; legacy parse kept
  for the no-grounding path.
- Script tag after agent-state/vital-thresholds, before plan-tracker.
- Gate green (`tools/ts_convert.py check`), 11 new unit tests.

## Live run 2026-10-04 (kraktooth_goblin_camp, Rikka) — three defects found and fixed

The user's exported turn 4 shows the contract working on a REAL LLM: typed
compliance, three hallucinated steps caught ("examine collapse", "search
debris", "take edible item" — all invented from room prose "partially
collapsed tunnels"), rejections logged with the fact list, and a grounded
re-composition. Three defects surfaced by that run:

1. **max_tokens 300 truncated the re-composition mid-JSON** ("note": "Listen
   for dripping") — parse failed, the turn ran PLANLESS. Fixed: 560 (the
   decide cap), plus `_salvageTypedSteps()` keeps the complete step objects out
   of a half-written response instead of losing the whole plan.
2. **The act list was missing engine verbs** — no escape/dash/approach/fumble,
   so a character being held (Rikka) could not plan an escape. Fixed: ACTS now
   carries the engine's own verb list (task-491's single source of truth), with
   grounding rules for dash (like go), approach (people/paths/area), drop/stow/
   wear/remove/combine/split (carried), lead/steal (people). 5 new unit tests
   incl. a verb-coverage guard.
3. **Pre-existing, unrelated to the plan layer:** `worldSync.refresh()` was
   never implemented — area-view called it unguarded (live stream: "Scope
   change failed: window.worldSync.refresh is not a function" x3 after a scope
   change that had SUCCEEDED) while graph-manager, structures and worldpainter
   guarded it and silently did nothing. Fixed: `refresh()` implemented
   (re-read + re-render, no modal), `open()` now delegates to it. Filed as
   bug-522.

### Salvage reads the RAW response, not `repairJSON`

The first salvage attempt salvaged from `response` AFTER `repairJSON`. That
cannot work: on truncated JSON `repairJSON` strips quotes, turning
`{"act": "escape"` into `{"act":,"escape"`, so the salvaged chunks are no
longer parseable and salvage returns `[]` — the whole plan is lost anyway.
`_salvageTypedSteps(response || '')` reads the raw string.

Measured live 2026-10-04 in the browser (Thrazz, Mine Access), stubbed
`llmClient.chat` to return a response cut off mid-third-step:

```
truncated in:  {"steps":[{"act":"go","target":"upward tunnel"},{"act":"look"},{"act":"search","item":"rack
llm calls:     1  (no retry — both salvaged steps grounded)
steps out:     ["go upward tunnel", "look"]
```

Two complete steps survive where the turn previously ran PLANLESS. With the
repairJSON input the same stub returned `[]`.

Live fallback gap, still open: a model that answers in the legacy prose format
is accepted ungrounded (the documented fallback). The retry nudge gets typed
compliance on this model; a prose-locked model would need a prose-anchoring
rule — deferred.
