---
type: task
status: done
area: characters
priority: medium
---

# task-420: One relationship mutation path

**Filed:** 2026-09-20  
**Depends on:** task-417 (co-presence meetings).  
**Prerequisite for:** task-412 (promotion/demotion handoff).  
**Relates:** task-350 (`engine/derive.py`), task-409.

## Outcome (2026-09-21)

Done. `engine/relationships.py` holds the single mutation path:

- `apply_relationship_delta(player, other, delta, cause, tick, area_id)` — the
  only writer of `closeness`. Clamps in one place, stamps
  `last_interaction_tick`/`interaction_count`, and records the cause on the trace
  as `why="social:<cause>"` with `delta={closeness, cause, with}`.
- `apply_symmetric_delta(a, b, delta, cause)` — symmetry is a property of the
  *call*, so a meeting cannot be applied to one side by accident. Each side still
  gets its own trace entry, because each side's history is its own.
- `closeness_band` / `band_at_least` / `BAND_LABELS` — the band ladder was inline
  in `Player.get_relationship_nl`; it is now defined once and the prose calls it,
  so a band-gated rule can never disagree with the wording about the edges.
  `band_at_least` is the gate task-423 needs for `flirt`/`confide` (the Diary's
  `has_relationship: {min_quality}`).
- `ensure_relationship(player, other, tick)` → `(record, created)`. Creating a
  record is not the same as feeling something: no closeness, no novelty.

Refactored callers: `player.update_relationship` (cause `dialogue`),
`player.register_first_meeting`, `player.felt_toward`, `player.get_relationship_nl`,
`engine/combat.py` (cause `combat`, was an inline inline `-30`), the `label`
command (writes `label`, not closeness — a declaration is not a measurement), and
the felt-toward route. `engine/derive.py` turned out to be a *reader* only, so it
needed no change.

Guarded by `tests/test_relationships.py::test_relationships_are_written_only_through_the_one_path`,
which scans `engine/`, `routes/` and `player.py` for `relationships[...] = ` and
allows exactly two elsewhere: the bulk import in `routes/player_ops.py` (a
payload replacing the store — deserialization, not a mutation). 32 tests.

### Deliberately left alone

`_grant_meeting_entertainment` is a **second Entertainment path for meeting
someone**, and since task-425 pays character novelty through perception it now
double-pays when a character walks into a room. Folding it into the novelty curve
needs the name → character-node-id mapping that task-423 establishes when it
populates `entity_ids` with `[actor_id, target_id, area_id]`, so it is recorded
there rather than half-fixed here.

## Problem

Relationship state is written from several places with no shared entry point:

- `engine/combat.py:159-165` mutates `target.relationships[attacker]` inline.
- `engine/derive.py` (task-350) derives closeness from experience.
- task-417's coarse meetings will write symmetric deltas.
- The foreground LLM loop writes its own outcome.

The store itself is a single blunt scalar — `player.relationships[npc] =
{"closeness": ...}` (read at `engine/area_description.py:371`).

Two consequences:

1. **No cause is recorded.** A delta from a beating looks identical to one from
   a shared meal, so nothing downstream (trace, memory, reflection) can explain
   a relationship.
2. **The two fidelity tiers diverge.** Foreground social interaction and
   background relationship drift are separate code paths writing the same
   scalar. At promotion/demotion (task-412) the value can jump, because the two
   paths never agreed on how it evolves.

## Design

A single mutation entry point:

```python
def apply_relationship_delta(actor, target, delta, cause, area_id=None):
    """The only writer of player.relationships.*.closeness."""
```

Rules:

- **All** writers go through it: combat, derive, coarse meetings, foreground
  outcomes. No direct `relationships[...] = ...` writes anywhere else.
- `cause` is a short token (`combat`, `meeting`, `gift`, `derive`, `dialogue`)
  and is recorded on the trace alongside the delta.
- `area_id` is recorded when known, so a relationship change can be located
  (and so task-417's co-presence gate is auditable after the fact).
- Deltas are clamped consistently in one place; symmetry for meetings is a
  caller-visible property (call twice with opposite actors, or pass a symmetric
  pair in one call).
- Foreground LLM output is converted into deltas before it reaches this
  function — the LLM never writes the store directly.

## Why this is the prerequisite for task-412

Promotion/demotion should change **who produces deltas**, not how they are
stored. With one write path, demoting a character mid-conversation cannot make
the relationship jump, because both tiers were always writing the same field
through the same clamp with a recorded cause.

## Acceptance

- A test/whitelist proves `relationships[...] = ` appears only in the new
  module (combat and derive refactored to call it).
- Every delta carries a `cause` and appears in the trace.
- Coarse meetings produce symmetric deltas through the same call.
- Save/load format unchanged (no schema change, still `{"closeness": float}`).
- Promotion/demotion fixture: relationship value is continuous across a tier
  change.

## Non-goals

- Richer relationship models (trust/fear/respect) — out of scope; the scalar
  stays a scalar for now.
- Relationship simulation of any new kind (this is plumbing only).
- Replacing `engine/derive.py`; it becomes a *caller* of the new function.

## Verification

- Unit: each cause produces the expected delta and trace entry.
- Unit: clamping is identical regardless of caller.
- Regression: combat relationship test (the "psychotic friend" betrayal case at
  `engine/combat.py:159`) still passes.
