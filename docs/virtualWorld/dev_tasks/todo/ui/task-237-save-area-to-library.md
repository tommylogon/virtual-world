# Task-237: Save Area to Library Button

**Status:** In backlog — filed 2026-08-16 from developer ideas backlog.
**Source:** `dev_tasks/developer ideas.md` (no save area button to library)
**Related:** `todo/library/task-334-structure-save-load-connected-areas.md` — recursive
structure bundles; this task is the single-area special case and should be implemented
as part of (or right after) 334 rather than separately.

## Goal

Add a "save area to library" action so a designed area in a scenario can be exported to
`data/library/areas/` as a reusable library entry, mirroring how items and characters are
saved to their library registries.

## Notes / open questions

- What to capture: area description, environment (light/temperature/air/smell/noise), ways
  and their directions, and any area-placed items/triggers — or just the area node itself?
- Library areas exist (`data/library/areas/`)? Confirm the registry format and how
  `build_area`/placement ingests them.
- Where the button lives: area inspector header and/or context menu ("Add Item to Area" area).
- Should existing library areas be upserted or require a unique name (reuse the
  duplicate-name suffix handling)?