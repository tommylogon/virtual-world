---
type: task
status: todo
area: characters
priority: low
---

# task-488: Single Track trait effect: gate release to one path

**Filed:** 2026-09-23
**Related:** task-213, task-545, task-546

## Blocked (2026-09-27) — two prerequisites do not exist

Re-measured before implementing: gating a release by path needs two things the
engine cannot currently express.

- **No path tracking.** `engine/pleasure_actions.py` `apply_stimulation()` already
  receives `verb`, `region_id`, `intensity` and coverage, then folds all of it into
  one integer on `vitals["Stimulation"]` and discards the inputs. The release
  check in `engine/tick_manager.py` reads a bare scalar
  (`if stim >= 65 and arousal >= 40:`), with no memory of how the meter got there.
- **No frustration state.** There is no frustration value, condition, or
  accumulator anywhere. The only outlet for a full meter is the same release
  cascade, so "other stimulation builds frustration" currently has nowhere to go.
- Also unresolved: the mature arousal conditions and the clothing-friction trickle
  add `Stimulation` on their own, so a "designated path only" gate has to decide
  what it does with a background drip that is not on any path.

Build task-545 (path tracking) and task-546 (frustration) first; this task then
becomes a gate over the recorded path plus a consumer of the frustration state.

## Goal

Wire the single_track trait effect, which is currently defined but inert (effects: {single_track: true}, no consumer): gate the release path to a single predefined route so other stimulation only builds frustration. Tracked from task-213.

## Acceptance

- `single_track` gains a live consumer that gates release to one designated path; other stimulation builds frustration/edging instead of triggering release.
- Only active when `world.mature_content` is on.
- Test asserting a non-designated path does not release, and the designated path does.
