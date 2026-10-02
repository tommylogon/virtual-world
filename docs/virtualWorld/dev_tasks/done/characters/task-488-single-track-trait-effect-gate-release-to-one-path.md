---
type: task
status: done
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

- [x] **`single_track` gains a live consumer that gates release to one designated
      path** — it was `effects: {single_track: true}` with no consumer, and now
      the release cascade asks `_release_gate` before firing.
- [x] **Other stimulation builds frustration/edging instead of triggering
      release** — a refused build gets `frustrated` (task-546), so a gated
      character is never left sitting at 65 with nothing to show for it.
- [x] **Only active when `world.mature_content` is on** — the gate lives inside
      `_pleasure_tick`, which returns before it when the toggle is off, and the
      designated route is read from the trait's own `mature: true` flag.
- [x] **Tests asserting a non-designated path does not release and the designated
      path does** — plus that non-carriers and a trait with no named route are
      both completely unaffected.

## Implementation — 2026-10-02 (WT-characters-engine)

The two blockers named in the "Blocked" note above are now built (task-545 path
tracking, task-546 frustration), so this is the gate those two existed for.

### Files

- `engine/tick_manager.py` — `_release_gate`, `_single_track_designated`, and the
  call site inside the release branch of `_pleasure_tick`.
- `tests/test_stimulation_paths.py` — the gate tests.

### The decisions

1. **A gate, not a branch inside the cascade.** `_release_gate(p, stim)` returns
   `(allowed, reason)`, and for anyone without the trait that is `(True, "")` —
   the ordinary cascade is provably untouched, which is what the task asks for and
   what makes it safe to add.
2. **The designated route lives in the trait params** (`path`, or `region`, or
   `route`), where the task said it would, rather than in a new field on the
   character. This also means an author sets it on the trait instance:
   `"single_track": {"path": "genitals"}`.
3. **An unnamed route makes the trait inert.** "Single track" with no track named
   is not a rule an engine can execute, and inventing one would gate every
   character with the trait to an arbitrary region. `data/library/traits/
   single_track.json` ships with `params: null`, so the trait is opt-in per
   character rather than active-and-wrong for everyone who has it.
4. **An ancestor route matches a more specific record.** Naming `torso` covers a
   record under `genitals` (via `engine.body_parts.region_chain`), so an author is
   not forced to know which sub-region the engine resolves for them. An exact
   match is checked first, so naming the precise route is worth doing.
5. **The gate reads the recorded path, not history** — `stimulation_from_path`,
   which is task-545's whole point.

### The bug the negative test caught

`_single_track_designated` matched an ancestor route with
`if key in region_chain(key)` — true for every key — instead of
`if named in region_chain(key)`. It therefore returned the *first recorded path*
whatever the trait named, so the gate released every build and the trait was a
no-op. Every positive assertion passes with that bug in place; only
"a non-designated path does not release" catches it.

### Verify

```
python -m pytest tests/test_stimulation_paths.py -q                           # 21 passed
python -m pytest tests/test_pleasure_system.py tests/test_body_parts.py \
  tests/test_conditions.py tests/test_traits.py \
  tests/test_stimulation_paths.py -q                                          # 225 passed
```

**Full suite compared by failure NAME against the clean-master baseline**: 15
failed on both, `Compare-Object` empty.


### Live verification — 2026-10-02, `python app.py` on `VW_PORT=4466`

Each case: a probe character with `mature_content` on, one `caress` applied, the
meter forced past the threshold, then `_pleasure_tick`.

```
=== task-545: the path is recorded and read by the gate ===
  designated path        report.path='genitals'   conditions=['overstimulated', 'satisfied']
   recorded paths: {}              <- cleared by the release, as designed

=== task-488: the gate ===
  designated path        report.path='genitals'   conditions=['overstimulated', 'satisfied']
  WRONG path             report.path='mouth'      conditions=['frustrated']

=== task-488: non-carriers and an unnamed route are untouched ===
  no trait               report.path='mouth'      conditions=['overstimulated', 'satisfied']
  trait, no route        report.path='mouth'      conditions=['overstimulated', 'satisfied']

=== task-546: the ordinary cascade and the discharge ===
  after a release, frustrated present? False
  satisfied present? True
```

The designated route releases; a wrong route produces `frustrated` and no
release; a non-carrier and a trait with no named route are byte-identical to the
pre-change behaviour; and a release discharges the frustration it created.
