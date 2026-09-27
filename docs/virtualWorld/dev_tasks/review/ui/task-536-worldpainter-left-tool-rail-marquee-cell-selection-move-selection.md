---
type: task
status: review
area: ui
priority: medium
---

# task-536: WorldPainter: left tool rail, marquee cell selection, move selection

**Filed:** 2026-09-27
**Related:** task-528 task-495 task-496

## Goal

Give the WorldPainter the selection/move ergonomics of a real paint tool (Unity/Blender/Aseprite) instead of four tool buttons in a top row. A vertical left rail holds the tools with keyboard shortcuts and an active state, plus the options that belong to the active tool; a Select tool adds click, shift-click and drag-a-marquee multi-selection of cells (Ctrl+A all, Escape clear), every paint/erase/route operation then acts on the whole selection in one request, and a Move tool (or arrow keys) shifts the selected cells' contents with bounds clamping. Selection is per-scope and survives tool switches. Must not fight the existing paint stroke: drag means marquee in Select mode and stroke in Paint mode, decided by the active tool. task-528's new Area tool goes in the rail from the start rather than the old top row, so the two changes meet in one place.

## Acceptance

## Acceptance

- [x] **A vertical left rail holds the tools**, beside the canvas rather than
      above it, so the tool column and the map it acts on are read together and
      the map gets the width back. `⬚ Select · 🖌 Paint · 🧽 Erase · ✥ Move ·
      🧭 Route · 🏠 Feature · 📍 Area · 🔍 Inspect`, with task-528's Area tool in
      the rail from the start rather than the old top row.
- [x] **One key per tool** (V P E M R F A I), handled in the existing key handler
      rather than a second one, because the interesting cases are combinations
      (Escape with a selection *and* a half-drawn route) and two handlers deciding
      what each does is how a key ends up meaning two things.
- [x] **The active tool is visible** (outline + `aria-pressed`) and the rail also
      shows **the options that belong to the active tool**: the selection panel
      (count, all, clear, invert) under Select, the nudge pad under Move.
- [x] **Select tool: click, shift-click, and a drag-a-marquee** multi-selection.
      A click on an already-selected cell deselects it, so the same gesture that
      made the selection takes it back.
- [x] **Ctrl+A selects all, Escape clears** — and Escape drops the selection
      *before* it resets the tool, peeling off the least-committed thing first.
- [x] **Every paint/erase operation then acts on the whole selection in one
      request**: one `paint_batch` over the selected cells, one undo step.
- [x] **Move tool / arrow keys shift the selected cells' contents** with bounds
      clamping, as one batch: every source cleared and every value written at its
      new home. Clear-then-write, so a value moving one cell east is not erased
      by its own neighbour's clear. Cells pushed past the edge are dropped from
      the move and counted in the status line rather than silently wrapping.
- [x] **Selection is per-scope and survives tool switches** (keyed by scope id),
      and is visible on the canvas: a tinted overlay plus a rubber-band marquee
      drawn into its own layer, so it moves with the map and does not fight the
      cell colours.
- [x] **It does not fight the paint stroke**: a drag means marquee in Select,
      stroke in Paint/Erase, and pan otherwise — decided by the active tool, and
      `draggable` is re-asked on every tool change so switching tools cannot leave
      the canvas panning when it should be painting.

## Notes

- The **layer / value / brush controls stayed in the top row** on purpose: they
  are options of four tools, not one, and putting them in the rail would mean
  switching tools to change a setting that outlives the switch. The rail owns
  only the per-tool options.
- Layer/value/brush in the rail is a one-line move if the author disagrees.
