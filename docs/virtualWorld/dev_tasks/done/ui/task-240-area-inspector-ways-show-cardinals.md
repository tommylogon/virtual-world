---
type: task
status: done
area: ui
priority: medium
---

# Task-240: Area Inspector Ways List Shows Cardinal Directions

**Status:** In backlog — filed 2026-08-16 from developer ideas backlog.
**Source:** `dev_tasks/developer ideas.md` (areas inspectors ways list to show cardinals too)

## What

The area inspector's ways list should display each way's cardinal direction (north/south/
east/west/up/down), matching how ways carry `dir` metadata, so designers can read a room's
exits at a glance without opening each way.

## Notes / open questions

- Ways store direction on the area↔way connection (`dir_a`/`dir_b`) or on the way node —
  confirm the source of truth.
- Show as a small badge/compass glyph next to each way in the inspector list (reuse the
  radial compass selector styling).

## Steps to verify

- expected: the area inspector's ways/exits list shows each exit's cardinal.
- observed (2026-10-10 live, Animal Pens): EXITS -> 'east passage -> Side Tunnels' with a '🧭 east' badge (area-view.ts:593-618).

## Why

TODO

## How

TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Select an area → Inspector → Exits list.

Current availability: The cardinal badge was live-observed on Animal Pens on
2026-10-10. The card's open question about source-of-truth should still be
resolved against the area-to-way connection metadata when the view is changed.

Live steps when available:
1. Open Animal Pens in the area Inspector and expand Exits; inspect the East
   Passage row and its destination.
   - expected: the row reads “east passage → Side Tunnels” and shows the 🧭 east
     badge beside that exit.
2. Open the corresponding way and inspect the connection from Animal Pens;
   compare the badge with the directional metadata for that side.
   - expected: the badge is derived from the Animal Pens side's connection
     direction, not from the way's display name or the opposite side.
3. Inspect a way with vertical movement and a way without cardinal metadata.
   - expected: up/down is shown for the vertical exit, and no invented compass
     direction appears when the source metadata is absent.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
