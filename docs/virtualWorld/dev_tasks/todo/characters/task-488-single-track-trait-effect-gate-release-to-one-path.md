---
type: task
status: todo
area: characters
priority: low
---

# task-488: Single Track trait effect: gate release to one path

**Filed:** 2026-09-23
**Related:** task-213

## Goal

Wire the single_track trait effect, which is currently defined but inert (effects: {single_track: true}, no consumer): gate the release path to a single predefined route so other stimulation only builds frustration. Tracked from task-213.

## Acceptance

- `single_track` gains a live consumer that gates release to one designated path; other stimulation builds frustration/edging instead of triggering release.
- Only active when `world.mature_content` is on.
- Test asserting a non-designated path does not release, and the designated path does.
