---
type: task
status: review
area: ui
priority: medium
wiki: "[[Characters/Persona]]"
---

# task-847: Persona tab: embedded body paperdoll navigator for appearance schema

**Filed:** 2026-10-16
**Related:** 

## What

Embed the paperdoll as a region navigator beside the appearance schema fields: clicking a body region shows the linked schema fields plus live summary in a side panel; schema record stays the sole source of truth.

## Why

The schema describes a body in prose while the paperdoll models one
mechanically, and they never met: appearance fields were a wall of text
inputs with no body to hang on. Clicking a bodypart now reads both —
live status plus what the sheet says — without duplicating an editor.

## How

Embedded, not copied: the navigator reads the paperdoll's own
`AREA_TO_REGIONS` (exposed as `InspectorPaperdoll.AREA_TO_REGIONS`,
one map two readers) and renders region chips atop the Appearance fold.

## Browser UI and intended live verification

Intended UI home: Mind dashboard → Persona tab → Appearance fold → "🩺 body — click to read" navigator.

Current availability: live-checked 2026-10-16 on :4444 (Kiala scratch block, reverted after).

Live steps when available:
1. Mind → Persona → Appearance, click torso.
   - expected: region rows (Torso/Breasts/Nipples + sens + healthy) + chest value + markings; the jump arrow scrolls the chest input into view.
   - observed: exact — "small, little more than training muscle" + "thin scar across left ribs" rendered; jump landed (input in viewport y=607/805); viewport screenshot taken.

Why no browser UI: (only when Intended UI home is Not applicable) TODO — explain why browser interaction is not appropriate.

Alternative verification steps: (only when Intended UI home is Not applicable)
1. TODO — describe an observable alternative.
   - expected: TODO — describe the result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Mind → Persona → Appearance, click a body chip; click the jump arrow.
   - expected: live region status + linked schema summary in place; jump scrolls the real input into view.
   - observed: 2026-10-16 live on Kiala — torso showed sens rows + chest + markings; jump landed; screenshot taken.
2. Click a chip, then type in a schema input without saving, then click another chip.
   - expected: panel updates in place; unsaved typing survives (no full re-render).
   - observed: in-place `#mind-persona-bodynav` update by construction; full `_personaHtml` re-render untouched by chip clicks.
3. `python tools/ts_convert.py check`.
   - expected: build/typecheck/lint/module/unit all green.
   - observed: green 2026-10-16. No JS unit — live pass is the wiring proof. Kiala scratch reverted (DELETE /record, prose-only confirmed).

## Acceptance

- [x] Region chips render atop Appearance from the paperdoll's own map (no second vocabulary).
- [x] Click shows live status + linked schema summary + markings, in place.
- [x] Empty-but-mapped fields read as empty; unmapped areas say so honestly.
- [x] Jump arrows reach the real inputs; no duplicate editors; unsaved typing survives.
- [x] Scratch state reverted; world clean.

## Files

- static/js/inspector/paperdoll-view.ts (expose AREA_TO_REGIONS)
- static/js/inspector/mind-view.ts (navigator, side panel, jumps, pane null-guard)
