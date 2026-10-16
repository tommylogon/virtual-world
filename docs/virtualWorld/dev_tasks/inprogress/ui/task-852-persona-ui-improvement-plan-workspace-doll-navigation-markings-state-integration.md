---
type: task
status: inprogress
area: ui
priority: medium
wiki: "[[Characters/Persona]]"
---

# task-852: Persona UI improvement plan: workspace, doll navigation, markings, state integration

**Filed:** 2026-10-16
**Related:** 

## What

Deliver the Persona improvement plan P1-P5: workspace redesign, paperdoll navigation with front/back views, region-linked markings, body-state integration, personality/narrative polish — no duplicate truth, no readerless fields.

## Why

The Persona tab read as a database form: a 720px max-width column of
bordered inputs. The user's review (2026-10-16) asked for a polished,
cohesive authoring workspace where the doll is central and the body is
super useful AND stunning — real hierarchy, state clarity, region
navigation, and markings — without duplicating systems or inventing
readerless fields.

## How

Blueprint: user-provided Persona UI Improvement Plan (P1-P5). Order:
workspace layout → doll navigation (front/back, keyboard, no artwork
required) → region-linked markings (multiple per region, canonical
store) → body-state integration (sensitivity verified end-to-end,
injuries/bleeding/coverage read-only, task-851 seeded wounds wired) →
personality/narrative polish → regression.

Non-goals (hard): no second doll/region catalog, no duplicate editors
in the region panel, no fields without consumers, sensitivity never
compiles to prose, no pregnancy/identity work (846/850 stay out).

## Browser UI and intended live verification

Intended UI home: Mind dashboard → Persona tab.

Current availability: P1 (workspace layout) in progress — pane width
720px → full width live; header + state chips built, not yet shipped.

Live steps when available:
1. Mind → Persona. 
   - expected: wide workspace, character header (name, one-liner, badges),
     ✓ saved / ● unsaved / ⚠ uncompiled state, actions on the right.
   - observed: partial — full-width pane + header live on :4444; one-liner
     source fixed to base_description (was reading equipment prose); state
     chips render. NOT shipped (dirty/stale wiring + polish pending).

Why no browser UI: (only when Intended UI home is Not applicable) TODO — explain why browser interaction is not appropriate.

Alternative verification steps: (only when Intended UI home is Not applicable)
1. TODO — describe an observable alternative.
   - expected: TODO — describe the result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Live path above (Mind → Persona).
   - expected: wide workspace + header + state chips.
   - observed: partial (1.0 of done): pane is full-width, header renders with
     one-liner (base_description) and badges. Dirty/stale toggling + final
     layout polish are unimplemented — card parked at inprogress.
2. `python tools/ts_convert.py check`.
   - expected: green.
   - observed: green 2026-10-16 after header/width edits (build/typecheck/lint/module/unit).
3. Live region/navigation acceptance (pending figure asset).

## Acceptance

- [ ] (PARTIAL, parked at inprogress) Full-width pane — live verified.
- [ ] (PARTIAL, parked at inprogress) Character header: name, one-liner, badges — live verified; source = base_description.
- [ ] (PARTIAL, parked at inprogress) State chips render — saved/unsaved/stale toggling not finished.
- [ ] Paperdoll navigation front/back + region selection polish (P2).
- [ ] Region-linked markings, multiple per region (P3).
- [ ] Body-state integration incl. task-851 wiring (P4).
- [ ] Personality/narrative polish (P5).
- [ ] Regression + responsive pass.

## Files

- static/js/inspector/mind-view.ts (pane width, header, state chips, one-liner source)
- static/css/style.css (header/states styles)
