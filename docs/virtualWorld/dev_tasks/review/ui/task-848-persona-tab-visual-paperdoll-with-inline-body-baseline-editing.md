---
type: task
status: review
area: ui
priority: medium
wiki: "[[Characters/Persona]]"
---

# task-848: Persona tab: visual paperdoll with inline body baseline editing

**Filed:** 2026-10-16
**Related:** 

## What

One doll, two modes. The equipment paperdoll figure is now a shared
template (`renderPaperdollFigureHtml`, mode `equip`|`navigate`):
Inventory equips through it unchanged, Persona reads through it.
Navigate mode swaps equip actions for selection (slots dispatch
`onNavigate`, never equip), tints slots by live status (hurt/hot),
and rings the selection. The side panel gains per-region sensitivity
sliders writing the new authorable baseline endpoint. Injury stays
unwritable (sim state); schema text still edits in the fold (single
editors — sliders write a different endpoint, so nothing fights).

## Why

The 847 chip row proved the mapping; the doll is the surface the user
actually asked for — see, click, adjust the body's baseline instead of
a database form for everything. A second doll was rejected: two figures
means two places where the left hand lives, and they will drift.

## How

- Engine: `PUT /api/players/<name>/body` (`handle_set_body_baseline`)
  writes `player.body_state[region].sensitivity`, validated against the
  `BODY_REGIONS` catalog (unknown region / non-number / out-of-0..1 =
  400). Same value `pleasure_actions` already reads; persisted via the
  existing ON_PLAYER serialization. No schema change, nothing compiles
  (sensitivity is a number, not prose).
- Template: grid loop extracted verbatim into the figure; equip caller
  passes `{mode:'equip'}` (output unchanged); Persona passes
  `{mode:'navigate', selectedArea}`. `navigateToArea` calls the host's
  `onNavigate` callback — the doll never edits, it names an area.
- Panel: `_refreshBodyNav` re-renders doll + side in place (unsaved
  typing still survives); sliders PUT on release, patch local
  `worldState` player, refresh. Jumps unchanged.
- Pretty: navigate CSS — gradient slots, hover lift + accent glow,
  selection ring, hot tint (sens ≥ .75), hurt red glow. CSS-only, no
  per-frame JS.

## Browser UI and intended live verification

Intended UI home: Mind dashboard → Persona tab → Appearance fold → doll figure + side panel.

Current availability: frontend live-checked 2026-10-16 on :4444; `PUT /body` backend-tested (4 green), live slider write needs a server restart (route is new).

Live steps when available:
1. Mind → Persona → Appearance, click the TORSO slot on the doll.
   - expected: slot rings selected; side shows 5 region rows each with a sensitivity slider + chest summary + jumps.
   - observed: exact — `pd-sel` on torso, 5 sliders, chest "empty, fill it below" (Arix prose-only); viewport screenshot taken.
2. Mind → Inventory tab (equipment surface, regression).
   - expected: unchanged — equip pickers, slot modals, 🩺 buttons, carry bar.
   - observed: equip-mode figure verified via live render (equip picker/modal/🩺 present, `data-mode="equip"`); filled-slot path not exercisable live (nobody currently geared — equipping would dirty the world; branch is verbatim moved code, covered by ts gate).

Why no browser UI: (only when Intended UI home is Not applicable) TODO — explain why browser interaction is not appropriate.

Alternative verification steps: (only when Intended UI home is Not applicable)
1. TODO — describe an observable alternative.
   - expected: TODO — describe the result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Doll click → selection + side panel (live path above).
   - expected: ring + rows + sliders + summary.
   - observed: 2026-10-16 live, confirmed + screenshot.
2. `python -m pytest tests/test_body_baseline.py`.
   - expected: 4 passed (write persists, unknown region 400, range/type 400 without touching state, unknown player 404).
   - observed: 4 passed.
3. `python tools/ts_convert.py check`.
   - expected: all green (refactor must not break equip).
   - observed: green 2026-10-16.

## Acceptance

- [x] One figure, two modes; equip output unchanged (live-verified structure).
- [x] Navigate slots select only; hurt/hot/selection styling live.
- [x] Sensitivity authorable via validated PUT; injury not writable by design.
- [x] No duplicate schema editors; unsaved typing survives refreshes.
- [x] Slider live-write pending server restart (backend proven).

## Files

- routes/player_ops.py (`handle_set_body_baseline`), routes/players.py (`PUT /body`)
- tests/test_body_baseline.py (new, 4 tests)
- static/js/inspector/paperdoll-view.ts (figure extraction, navigate mode, `onNavigate`)
- static/js/inspector/mind-view.ts (doll embed, sliders, in-place refresh)
- static/css/style.css (navigate-mode pretty)
