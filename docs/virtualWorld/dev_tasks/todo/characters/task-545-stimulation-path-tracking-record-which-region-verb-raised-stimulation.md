---
type: task
status: todo
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

- A `Stimulation` gain records its source (path key) on the affected player, and
  the record is cleared by a release.
- The release check can read the recorded path, so a path-gated gate is expressible
  without re-deriving history.
- Non-intimate sources (arousal conditions, clothing friction) are distinguishable
  from interaction sources.
- Mature-gated throughout: with `world.mature_content` off nothing is recorded and
  no state is created.
- Test asserting the recorded path survives accumulation and is cleared on release.

## Related

- task-488 — the consumer this unblocks
- task-546 — frustration, the other half of task-488
- task-212 / task-213 (done) — the multiplier pipeline this sits in
