---
type: task
status: review
area: characters
priority: medium
related: ["'task-253'", 'task-253']
wiki: "[[Characters/Persona]]"
---

# task-851: Authorable starting injuries, missing parts and prosthetics

**Filed:** 2026-10-16
**Related:** 

<!-- deps:start -->
**Related:** [[task-253-body-part-targeted-injuries]]
<!-- deps:end -->

## What

Let authors create characters with wounds, missing limbs, hooks: seed the same injured/bleeding condition instances combat makes; represent absent parts and prosthetics (mods cover hook) without a parallel injury store.

## Why

Withholding injury authoring was the wrong call (corrected on review): a broken leg
or a hook hand is legitimate character creation. But the mechanics stay single — a
seeded wound must heal, ache, and slow exactly like a dealt one, so authoring seeds
the same instances instead of inventing a parallel injury model. A hook itself is an
appearance modification (exists); absence is the new `missing` condition.

## How

- `PUT /body` grows `injuries[]` (`{region, level 1..3, bleeding, source?=authored}`)
  and `missing[]`, validated against the catalog. Wounds call
  `player.add_condition` exactly as `combat._apply_region_injury` does — speed
  (`level_speed_mult`), symptoms, `ends_on: heal/medicine` all work untouched.
- New `data/library/conditions/missing.json`: permanent (`ends_on: cure`),
  body_part-scoped, symptoms with `{body_part}`. No stat mods in v1 — a missing leg
  does not yet slow travel; that integration is filed below, not silently omitted.
- UI: ✖ badge on doll slots, ✖ chip in 🩺 modal + Persona side rows (all three read
  `conditions.missing`, same store).
- Prose: left to the author (mods/hook lines). The endpoint seeds state, never touches
  the record — layers stay clean.

## Browser UI and intended live verification

Intended UI home: TODO — name the page, panel, tab, or control where this behavior belongs. If no browser UI is appropriate, write 'Not applicable' here, explain why below, and give an observable alternative.

Current availability: TODO — for example, planned/not implemented, present but not live-checked, or live-checked with date and evidence.

Live steps when available:
1. TODO — describe how to reach the surface and the interaction to perform.
   - expected: TODO — describe what the user can see or do.

Why no browser UI: (only when Intended UI home is Not applicable) TODO — explain why browser interaction is not appropriate.

Alternative verification steps: (only when Intended UI home is Not applicable)
1. TODO — describe an observable alternative.
   - expected: TODO — describe the result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Seed a broken leg + missing hand via `PUT /body`, read the doll.
   - expected: injured Lv2 slows (speed_mult), ✖ shows on slot + side row; prose untouched.
   - observed: backend 8/8 green incl. same-instance + rejection tests; UI chips verified in code + ts gate (live doll check needs restart — route is new).
2. `python -m pytest tests/test_body_baseline.py tests/test_body_parts.py tests/test_pleasure_system.py tests/test_equipment_system.py`.
   - expected: all green.
   - observed: 113 passed 2026-10-16.
3. `python tools/ts_convert.py check`.
   - expected: green (modal chip restore included).
   - observed: green; also repaired an edit that dropped the 🩺 injured line.

## Acceptance

- [x] Starting wounds are the same instances combat makes (speed/symptoms/healing work).
- [x] Missing parts are a condition, not a second model; shown in all three body views.
- [x] Bad regions/levels are 400s that write nothing.
- [x] Prosthetics stay mods; prose stays the author's.
- [ ] Follow-up (not this card): missing-limb travel/movement integration.

## Files

- routes/player_ops.py (`handle_set_body_baseline` grows injuries/missing)
- data/library/conditions/missing.json (new)
- tests/test_body_baseline.py (4 → 8 tests)
- static/js/inspector/paperdoll-view.ts (✖ badges, modal chip)
- static/js/inspector/mind-view.ts (✖ side chip)
