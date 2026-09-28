---
type: task
status: review
area: world
priority: high
---

# task-575: Painter guidance: preflight blockers, a per-mode checklist, and hint coverage

**Filed:** 2026-09-28
**Related:** task-521,task-496,task-535,task-560,task-563

## Goal

Make the WorldPainter say why a scope cannot be compiled, and what to paint next,
before the author presses Generate.

**Filed from a real session.** An author made a 30×20 town grid, and the painter
offered no sequence, no per-mode guidance, and — when they pressed the button —
a red line saying only "Generate failed". Two conditions were involved and
neither was discoverable from the UI:

- The scope had `paint_policy: "baked"` because it was made with
  **🪜 Make this a scope…**, which *promotes* areas the author had already
  written. A promoted scope is authored rather than painted, carries no paint, and
  can never be compiled — yet nothing displayed the field, and
  `compile_grid`'s message ("compile it once then author by hand") is advice a
  promoted scope **cannot follow**, since it is precisely how it ended up with no
  paint.
- The scope sat on world cell (17,3), where the parent's paint has a gap. A
  gateway needs a compiled region on that cell, so `_gateway` skipped it and
  **no gateway was ever minted** — no error, no warning, just an unreachable
  scope.

## Acceptance

- [x] `engine.world_compile.preflight(manifest, scope_id)` returns
      `[{code, severity, text, remedy}]` and `_grid_payload` ships it as
      `blockers`, alongside `paint_policy` on the scope block.
- [x] Every `block` is a condition `compile_grid` refuses, or one it starts
      refusing once the remedy is carried out. The two are held together by a
      test rather than by convention.
- [x] The refusals in `compile_grid` say the **remedy**, not the rule.
- [x] The editor renders `blockers` beside **⚙ Generate**, and a blocked
      condition appears in the button's own tooltip.
- [x] A per-mode checklist in the editor, with progress **derived from the
      payload** rather than remembered in `localStorage`.
- [x] `data-help` hooks on the in-editor controls, with matching HelpCenter tips
      under a `WorldPainter` group and a `paint-a-town` tour (task-521's first
      gap; its other gaps are untouched).
- [x] `tools/unit/test_help_center.js` guards the registry, including that every
      `data-help` key the app emits has a tip behind it.
- [x] The area estimate in the `node-cap` warning reuses `_regions`, so it
      follows the merge switch and the per-kind merge rules.
- [x] The `unnamed` warning is scoped to `town`/`interior` (or a partly-named
      scope) so a wilderness map is not nagged for scenery cells.
- [x] Documented in `docs/design/worldpainter-knowledge-and-fog.md`.

## Notes

- **The tip layer alone would not have helped.** A coach card explains what a
  control *is*; it cannot say that *this* scope is un-generatable, or that *this*
  placement is on a hole. Preflight had to come first, and it is the layer that
  turns a silent failure into a stated one.
- The registry guard found a live defect immediately: the **❓ Help button** in
  `templates/index.html` carried `data-help="help"` with no tip behind it, so the
  entry point to the whole help layer explained nothing. Now tipped.
- Every pre-existing tour was unreferenced from its own steps, so the Help index
  listed four chains nothing linked to. Every step tip now names its tour, and the
  guard holds that invariant.
- The dead-hook check matches `data-help="…"` attributes **and** the painter's
  `_help(el, '…')` helper, and reconstructs the tool rail's eight `wp-tool-*`
  keys from the `TOOLS` table, which are built at runtime as `'wp-tool-' + id`.
  The closing paren in the helper pattern is load-bearing: without it the prefix
  matches as a whole key and the guard fails on itself.
- **Left for a follow-up:** `world_grid.normalise_grid` rebuilds every placement
  keeping only `x, y, area_id, area_name`, so one paint click silently drops
  `entry_phrase` (task-529), `sides` (task-563) and `gateway_from` (task-535).
  That is a data-loss bug, not a guidance gap, and it is why
  "paint first, generate last" is advice in the `wp-generate` tip.
