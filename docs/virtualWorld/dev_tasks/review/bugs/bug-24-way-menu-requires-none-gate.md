# Bug 24 — Way menu gates Go/Open on requires:"none" (panel-only)

**Status:** In Review — fixed 2026-08-24, backend normalization + frontend
hardening, 1 new unit test, full suite 1121 passed. Browser E2E pending.

## Found

2026-08-24 taco_bell playtest: the men's restroom door menu showed only
Examine + a DISABLED "Go men's restroom → … — requires none". No Open
entry. Typed `go men's restroom` worked fine the whole time.

## Why

Legacy data stores the literal string `"none"` in a way's `requires`
field. The engine special-cases it (`movement.py:228`
`if requires and requires != "none"`), but `scene_snapshot.py` passed it
through verbatim and `turn-scene-view.js` treats any truthy `requires` as
a gate: Go disabled ("requires none"), Open/Close suppressed
(`!way.requires` fails), ⛰ marker + hover text shown.

## Fix

- `engine/scene_snapshot.py`: normalize none-like requires
  ("none"/"nothing"/"no", case-insensitive) to `""` in the ways payload.
- `static/js/agent/turn-scene-view.js`: new `requiresGate()` helper used
  by buildWayMenu, the exit hover card, and the ⛰ marker — same
  normalization client-side (defense in depth for stale payloads).

## Tests

`tests/test_scene_snapshot.py::test_requires_none_is_not_a_gate` — a way
with `requires: "none"` ships `"requires": ""` in the scene payload.

## Verification

- pytest full suite 1121 passed
- Browser: reload panel → restroom door menu must show enabled Go + Open;
  no "requires none" reason text, no ⛰ marker.
