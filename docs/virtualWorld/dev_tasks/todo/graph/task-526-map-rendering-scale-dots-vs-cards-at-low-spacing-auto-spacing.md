---
type: task
status: todo
area: graph
priority: medium
---

# task-526: Map rendering scale: dots vs cards at low spacing + auto spacing

**Filed:** 2026-09-26
**Related:** task-523 task-496

## Goal

A compiled area renders as a ~200px card, so at the default 40px/cell the cards overlap into what looks like a physics blob (only fixed by dialling the spacing control to ~200). Make the map view scale-aware: draw compact dots (or name-less markers) below a spacing/zoom threshold and full cards above it, and/or auto-derive a default spacing from the grid dimensions so a 20x40 zone and a 200x133 world are each readable without hand-tuning. The manual spacing control stays as an override.

## Acceptance

- TODO
