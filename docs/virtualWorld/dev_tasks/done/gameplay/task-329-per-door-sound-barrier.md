# Task-329: Per-Door Sound Barrier Property

**Status**: In Review — implemented + committed 2026-08-23 (`100b7cc3`), moved to
review/. Renumbered from 327: another session claimed 327/328 for prompting tasks
without bumping `dev_Task_sequence.md`. Engine (`get_way_barrier` custom-property
branch), way inspector 🔇 Sound Barrier field, library refresh maps (both
`_refresh_way` dict + prop_map), save/refresh payloads + diff sections, AI-improve
PROPERTIES doc line. Tests: `tests/test_sound.py` `TestWayBarrier` +5 cases (custom
on closed/locked/blocked; ignored open/hidden; invalid falls back; overrides
see_through on solid states) — 31 passed. Live-verified all 6 scenario ways render
the field. Follow-up fix in same task: `_renderUnifiedPassage` now returns a lit
TemplateResult, but `showWay` still wrapped it in `unsafeHTML()` → every way
inspector crashed ("unsafeHTML() called with a non-string value"). Fixed by direct
interpolation (`${passageHtml}`); all ways verified rendering after.

## Summary

Ways get an optional `sound_barrier` float property. When set, it replaces the
state-derived barrier while the door is in a solid state (`closed`, `blocked`,
`locked`). Unset → existing behavior unchanged (per-state Engine Config defaults,
`sound.way_closed`=1 etc.). Open (0.5), hidden (2), and see_through (0.75) paths
are untouched; see_through still wins over state lookup as today (sound.py:83).

Single value per door — no separate closed/locked/blocked overrides on the node.
Falls back to the task-304 config chain so Engine Config remains the global tuner.

## Motivation

Hidden/solid doors currently block even shouts (barrier 2 ≥ shout penetration 2).
Designers need doors with different acoustic mass (vault door vs thin wooden door)
without editing global config per scenario.

## Implementation

1. `engine/sound.py` — `get_way_barrier()`: read `properties.sound_barrier`
   (float-coerced) before the see_through/state lookup, only for solid states.
   Absent/invalid → exact current behavior (zero regression when unused).
2. `static/js/inspector/way-view.js` — number input in the passage settings block
   (next to Max size / Edge Length): blank = default, saves float or clears.
3. `routes/library_routes.py` — add `sound_barrier` to way library prop maps
   (full-refresh dict + section map) so library round-trips preserve it.
4. Way-view save/refresh-from-library payloads + diff sections: include the key.
5. AI improve prompt PROPERTIES doc line: mention the new optional key.

## Verification plan

- Unit test(s) in the existing sound test file: custom value honored for
  closed/blocked/locked; ignored for open/hidden; absent property → unchanged
  defaults; see_through precedence preserved.
- `pytest` sound suite + guard suites.
- Live: way inspector field renders, saves via api.updateNode, propagation
  reflects the custom value.
