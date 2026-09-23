---
type: task
status: done
area: characters
priority: high
---

# task-417: Co-presence gate for coarse meetings

**Filed:** 2026-09-20  
**Amends:** task-409 §4 ("Coarse meetings").  
**Depends on:** task-416 (area → character index), task-399 (background runner).

## Outcome (2026-09-21)

**Done as a component of task-423**, not separately — the "symmetric meeting"
this task specifies was the placeholder that task-423's action-and-outcome pass
replaces, so building it standalone would have meant implementing the pairing
twice. `engine/background_social.py` implements the gate:

- `pair_for_area` runs **per area, never globally** — greedy by mutual affinity
  descending, ties by name, so the same relationship state always yields the same
  pairs and each character is in at most one pair per pass. There is no distance
  in this world model, so nothing else would stop two characters on opposite
  sides of the camp from meeting.
- Same area, both `simulation_mode == "background"` (`is_background`), both
  conscious and not mid-activity (`is_available`).
- **An attended character is never paired** — their social life belongs to the
  LLM loop (the task-412 seam).
- The cap is `MEETINGS_PER_CHARACTER_PER_DAY = 6`, rolled over on the in-game day
  and therefore tick-length independent, plus a `SOCIAL_COOLDOWN_MINUTES = 90`
  cooldown between one character's interactions so the day's allowance is spread
  rather than burst.
- Traces name the area and both parties and carry `rel:<other>` tags, so a
  relationship change is auditable after the fact.

Task-416 (area → character index) was **not** needed: the pass groups the ~23
characters by `current_area` in one pass, which is cheaper than the index and has
no cache to invalidate. If character counts grow an order of magnitude, revisit.

The blocking-activity part of the design this task fed into was **removed** —
see task-423's outcome for the measurement that killed it.

## Problem

task-409 §4 defines coarse meetings as *"Deterministic from relationships +
traits + vitals + seeded RNG; apply symmetric relationship deltas."*

There is **no spatial constraint in that rule.** Nothing requires the two
characters to be in the same area, so the background planner will pair
characters on opposite sides of the camp, apply mutual relationship deltas, and
give both a memory of a conversation that never happened. That is not a missing
feature; it is incorrect behaviour written into a high-priority task, and it is
the direct consequence of the relational world model (there is no distance to
accidentally prevent it).

## Design

The meeting pass runs **per area**, never globally:

```
for area_id in areas (sorted):
    present = background_characters_in(area_id)      # from task-416 index
    if len(present) < 2: continue
    pair greedily by (affinity desc, id asc)
    for each pair:
        apply symmetric relationship deltas
        record a meeting trace entry for both sides
```

Additional rules:

- Foreground/attended characters are **not** paired by this pass. An attended
  character's social interaction is decided by the normal LLM loop.
- Cap meetings per background character per in-game day to avoid a
  relationship drift treadmill in crowded areas.
- If both parties are background and co-present, the meeting is eligible. If
  either is attended, it defers to the foreground path (task-412 seam).
- Meetings are recorded with `area_id` on the trace, and with an anchor if one
  is available (task-419).

## Acceptance

- Two background characters in **different areas never meet**, under any seed.
- Meeting pairing is deterministic: same seed + same relationship state yields
  the same pairs.
- Relationship deltas are symmetric on both sides (this is already an
  acceptance criterion of task-409; keep it).
- No meeting is scheduled in an area with fewer than two background characters.
- A meeting trace entry names the area and both parties.
- Cap is enforced and logged.

## Non-goals

- Dialogue generation, full conversation simulation, or meeting content.
- Foreground social interaction (that stays with the LLM loop).
- Schedules/work (still task-409 §1–3).

## Verification

- Unit: three characters in two areas → only the co-present pair meets.
- Unit: same-area pair with negative affinity → no meeting, or a hostile one, per
  the authored rule (must be explicit, not accidental).
- Determinism: seed replay with reflection disabled.
- Extend `tests/test_background_simulation.py`.
