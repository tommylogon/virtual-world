---
type: task
status: todo
area: ui
priority: medium
---

# task-536: WorldPainter: left tool rail, marquee cell selection, move selection

**Filed:** 2026-09-27
**Related:** task-528 task-495 task-496

## Goal

Give the WorldPainter the selection/move ergonomics of a real paint tool (Unity/Blender/Aseprite) instead of four tool buttons in a top row. A vertical left rail holds the tools with keyboard shortcuts and an active state, plus the options that belong to the active tool; a Select tool adds click, shift-click and drag-a-marquee multi-selection of cells (Ctrl+A all, Escape clear), every paint/erase/route operation then acts on the whole selection in one request, and a Move tool (or arrow keys) shifts the selected cells' contents with bounds clamping. Selection is per-scope and survives tool switches. Must not fight the existing paint stroke: drag means marquee in Select mode and stroke in Paint mode, decided by the active tool. task-528's new Area tool goes in the rail from the start rather than the old top row, so the two changes meet in one place.

## Acceptance

- TODO
