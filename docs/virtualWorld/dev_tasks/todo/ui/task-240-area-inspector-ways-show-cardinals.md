# Task-240: Area Inspector Ways List Shows Cardinal Directions

**Status:** In backlog — filed 2026-08-16 from developer ideas backlog.
**Source:** `dev_tasks/developer ideas.md` (areas inspectors ways list to show cardinals too)

## Goal

The area inspector's ways list should display each way's cardinal direction (north/south/
east/west/up/down), matching how ways carry `dir` metadata, so designers can read a room's
exits at a glance without opening each way.

## Notes / open questions

- Ways store direction on the area↔way connection (`dir_a`/`dir_b`) or on the way node —
  confirm the source of truth.
- Show as a small badge/compass glyph next to each way in the inspector list (reuse the
  radial compass selector styling).