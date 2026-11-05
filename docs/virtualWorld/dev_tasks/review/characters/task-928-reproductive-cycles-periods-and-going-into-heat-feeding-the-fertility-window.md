---
type: task
status: review
area: characters
priority: medium
wiki: "[[Characters/Persona]]"
---

# task-928: Reproductive cycles: periods and going into heat, feeding the fertility window

**Filed:** 2026-11-04
**Completed:** 2026-11-04
**Related:** task-846

<!-- deps:start -->
**Related:** [[task-846-pregnancy-gestation-and-birth]]
<!-- deps:end -->

## What

Add a reproductive cycle to characters: periods (menstrual cycle) for species that have one, and heat (estrus) for species that have one. The cycle is a bounded per-character record advanced by the sim clock. It produces a fertile window that task-846's conception check reads, plus visible phases and conditions (for example menstruating, in_heat) that prompts, the Mind panel and the Bio tab can show. Species decide which pattern applies (none, monthly cycle, seasonal or periodic heat).

## Why

task-846 gates conception on life stage and willingness only, so every adult is equally fertile at every tick. That is a flat model: it has no timing, no way for a character to be aware of their body's state, and no seasonal or periodic breeding for animals and goblins. This is deliberately NOT part of task-846. Pregnancy is a one-shot state machine (conceive, gestate, birth). A cycle is a separate recurring system with its own state, its own species table, its own conditions and its own content and consent surface, and it applies to characters who never become pregnant. It feeds 846 through one narrow seam (the fertility check) and should not widen 846.

## How

- Cycle state is one bounded dict on the Player (species pattern, phase, day in cycle, next-phase tick), advanced in lifecycle.on_clock beside pregnancy. No event store.
- A species table in one place (like SPECIES_LIFESPAN) declares the pattern: none, cycle (length, fertile window), or heat (period and duration, optionally seasonal via the calendar).
- Phases surface as conditions through the existing conditions system (no new status mechanism). Prompt text goes through the existing state context, not a new prompt lane.
- engine/pregnancy.is_fertile reads the cycle: fertile only inside the window for cycling or in-heat characters; species with no pattern keep today's stage-only rule so existing scenarios do not change.
- Pregnancy suspends the cycle and birth resumes it.
- Heat may raise willingness-adjacent drives (arousal conditions from task-210) but must never override the willingness and boundary gate. Consent stays the explicit gate.
- Authored data: a species entry and a trait or tag opt-out (infertile, sterile) stay honoured.
- Mature-content framing follows the existing matureContent setting: the cycle is a simulation state, not explicit content.

## Browser UI and intended live verification

Intended UI home: Character Inspector, Mind panel and Bio tab: current cycle phase and conditions.

Current availability: Implemented. `mind-view.ts` and `persona-view.ts` render reproductive cycle and pregnancy badges and details. Condition chips `menstruating`, `ovulating`, and `in_heat` render in `agent-view.ts`.

Live steps:
1. Select a cycling adult, advance time past a phase boundary, and read the phase in Mind or Bio.
2. Check the condition chips appear and clear at the phase edges.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Mind view displays reproductive cycle badge/status and condition chips cycle with sim time.
   - observed: Condition definitions created in `data/library/conditions/`, integrated with `mind-view.ts`, `persona-view.ts`, and `agent-view.ts`.
2. Record the browser surface and interaction actually used.
   - expected: Character Inspector Mind/Persona/Agent tabs inspect character conditions and lifecycle state.
   - observed: Inspecting Mind view surfaces cycle phase, day, length, and fertile window badge.
3. Run the targeted regression test for the mechanism.
   - expected: pytest tests/test_reproductive_cycle.py passes all 8 test cases.
   - observed: 8 passed in 0.95s; tests/test_pregnancy.py 7 passed; tests/test_background_social.py 29 passed.

## Acceptance

- [x] A species table declares none, cycle or heat per species in one place.
- [x] Cycle state is one bounded dict on the Player and persists across save and reload.
- [x] The fertile window gates engine/pregnancy.is_fertile for characters with a pattern, and species without one are unchanged.
- [x] Phases surface through the existing conditions system and the Mind or Bio view, with no new status mechanism.
- [x] Pregnancy suspends the cycle and birth resumes it.
- [x] Heat never bypasses the willingness and boundary gate.
- [x] At least one authored character per pattern exists so the mechanic is exercised by content, not only by a test.

## Files

- `engine/reproductive_cycle.py` (new)
- `engine/lifecycle.py` - advance the cycle in on_clock
- `engine/pregnancy.py` - is_fertile reads the window, sex compatibility check
- `engine/serialization.py` - persist the cycle dict
- `data/library/conditions/` - menstruating.json, ovulating.json, in_heat.json
- `static/js/inspector/mind-view.ts` - mind tab cycle display
- `static/js/inspector/persona-view.ts` - header cycle badge
- `static/js/inspector/agent-view.ts` - condition chip colors
- `tests/test_reproductive_cycle.py` (new)
