---
type: task
status: done
area: characters
priority: high
---

# task-545: Stimulation path tracking: record which region/verb raised Stimulation

**Filed:** 2026-09-27
**Related:** task-488

## Goal

Stimulation is a single anonymous scalar, so nothing can tell a release threshold which path produced it. Record the source of Stimulation gains per player so path-sensitive effects have something to read.

## Measured (2026-09-27) — why task-488 is not a one-line trait consumer

- `engine/pleasure_actions.py` `apply_stimulation()` already receives everything a
  "path" could be built from — `actor`, `target`, `verb`, `region_id`, `intensity`,
  `covered`, `closeness` — and folds all of it into one integer:
  `vitals["Stimulation"] += stim_gain`. The inputs are discarded on return; the
  report dict carries `region` back to the caller for the message text and nothing
  else.
- `region_id` is already a resolved body-region id from `engine/body_parts.py`
  (`resolve_region`, `region_chain`), and `verb` is one of the `VERB_BASE` keys.
  Both are stable, already-normalized values, so they are usable as a path key
  without new vocabulary.
- `engine/tick_manager.py` reads the outcome as a bare scalar:
  `if stim >= 65 and arousal >= 40:` fires the release cascade. There is no
  memory of how `stim` got there.
- The mature conditions also add `Stimulation` on their own (`warming_up` +1,
  `aroused` +2, `highly_aroused` +3, `frantic` +4, `sensitized` +1, clothing
  friction in the tick pass), so periodic and friction sources would need a
  distinguishable path too — otherwise "only the designated path releases" would
  also block the background drip.
- `data/library/traits/single_track.json` (and the runtime definition in
  `engine/traits.py`) declare `effects: {"single_track": true}` with no consumer.

## Open design decisions (settle before implementing)

1. **What is a path?** A body region (`region_id`), a verb, or a
   region-under-a-verb pair. Recommendation: the region id alone, because it is
   already normalized and the trait description talks about a *route* to release,
   not about a specific move.
2. **Where does the designated path live?** On the player/trait params (the trait
   already has a `params` field) rather than a new field on the character.
3. **Attribution vs. accumulation.** Keep a per-player record of which regions
   contributed since the last release, or a single "last path" field. The former
   supports a "you have been edged on everything but X" narrative; the latter is
   much cheaper.
4. **How do periodic/friction sources behave?** Decide whether they are exempt,
   or treated as a neutral path that also builds frustration.

## Acceptance

- [x] **A `Stimulation` gain records its source (path key)** on the affected
      player — `apply_stimulation` files it under the resolved `region_id` before
      the inputs are discarded.
- [x] **The record survives accumulation and is cleared by a release** — the
      release cascade empties it, and the record is transient (not serialized),
      so a save cannot restore a build history the character never lived through.
- [x] **The release check can read the recorded path**, so a path-gated gate is
      expressible without re-deriving history — that is task-488, and it reads
      `stimulation_from_path`.
- [x] **Non-intimate sources are distinguishable from interaction sources.** The
      key carries a `source`: an interaction files under its region, the
      clothing-friction trickle files under `clothing_friction`.
- [x] **Mature-gated throughout** — with `world.mature_content` off nothing is
      recorded and no state is created; and turning the toggle *off* clears an
      existing record rather than leaving invisible bookkeeping.
- [x] Tests in `tests/test_stimulation_paths.py` (21 tests across 545/546/488).

## Decisions, following the task's own recommendations

1. **A path is the region id**, not a verb and not a region-under-verb pair.
   `region_id` is already a resolved id from `engine/body_parts.py` and the trait
   talks about a *route*, not a move; a `region.verb` key would make "any touch
   to the same route counts" false.
2. **The designated path lives in the trait params** (`path` / `region` /
   `route`), not in a new field on the character.
3. **Attribution, not a single "last path"** — `stimulation_paths` is a
   path→points map, so "you have been edged on everything but X" is answerable,
   *and* `stimulation_last_path` is kept for the "what is happening right now"
   question that a dict's insertion order answers arbitrarily.
4. **Periodic/friction sources are their own path**, not exempt and not silent.
   The friction trickle files under `clothing_friction`, which is what lets a
   path gate distinguish "you were touched elsewhere" from "nobody touched you,
   your clothes did".

## Implementation — 2026-10-02 (WT-characters-engine)

### Files

- `player.py` — `stimulation_paths` / `stimulation_last_path`, the
  `stimulation_path_key` staticmethod, `record_stimulation_path`,
  `stimulation_from_path`, `clear_stimulation_paths`,
  `stimulation_path_total`; and the toggle-off clear inside
  `sync_pleasure_vitals`.
- `engine/pleasure_actions.py` — `apply_stimulation` files the gain and adds
  `report["path"]`.
- `engine/tick_manager.py` — the friction trickle records its own source; the
  release clears the record.
- `tests/test_stimulation_paths.py` — **new**, 21 tests (shared with 546/488).

### A non-positive gain records nothing

Decay must not be able to erase the history of what raised the meter. Waiting
around would otherwise cancel a path out of the record and quietly re-open a gate
that had been closed.

### Verification note

`apply_stimulation`'s multiplier pipeline returns 0 for a bare `Player` (empty
`body_state` → default sensitivity), so the path tests set a responsive
`body_state` first. Without that the record is correctly empty and the tests would
"pass" for the wrong reason.

### Verify

```
python -m pytest tests/test_stimulation_paths.py -q                           # 21 passed
python -m pytest tests/test_pleasure_system.py tests/test_body_parts.py \
  tests/test_conditions.py tests/test_traits.py \
  tests/test_stimulation_paths.py -q                                          # 225 passed
```

**Full suite compared by failure NAME against the clean-master baseline**: 15
failed on both, `Compare-Object` empty.

`tests/test_condition_catalog.py::test_mature_conditions_flagged_in_data` counts
mature conditions and asserted 10; `frustrated` makes it 11. That count was
updated with the reason, not loosened.


## Related

- task-488 — the consumer this unblocks
- task-546 — frustration, the other half of task-488
- task-212 / task-213 (done) — the multiplier pipeline this sits in
