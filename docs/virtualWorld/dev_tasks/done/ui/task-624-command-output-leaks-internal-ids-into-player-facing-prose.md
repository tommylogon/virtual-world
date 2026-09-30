---
type: task
status: done
area: ui
priority: medium
---

# task-624: Command output leaks internal ids into player-facing prose

**Filed:** 2026-09-30
**Related:** 

## Goal

Grid coordinates like '(world 16,4)' appear in narration a player reads. Note the way *hover* resolves names correctly ('north trail -> Camp Entrance') while the at-rest button label does not, so the clean form already exists.

## Acceptance

- TODO

## Amended 2026-09-30 — the fix was incomplete, now widened

Loading `kraktooth_goblin_camp` to work task-616 showed this fix had only half
landed. The pattern was

    \(\s*world\s+[\d,\s]+\s*\)

which matches `Road (world 10,4)` and nothing else. But the painter uses a
**second** naming scheme, and it is the larger one:

    Sparse Forest (Eldenford interior 10,3)
    Road (Eldenford interior 10,4)
    Camp Entrance Trail to Road (Eldenford interior 10,4)

**326 ways and their areas** use that form. So the coordinate leak survived the
original fix on roughly three-quarters of the affected nodes, and the audit's own
claim that this was fixed was wrong.

Widened to any trailing parenthesised `N, M` pair:

    \(\s*[^()]*?\b\d+\s*,\s*\d+\s*\)\s*[.!]?\s*$

Checked against the cases that must **not** change, and confirmed unchanged:

    Bathroom (Kraktooth, level 2)   ->  Bathroom (Kraktooth, level 2)
    The Outhouse (West)              ->  The Outhouse (West)
    Cellar (Below Kitchen)           ->  Cellar (Below Kitchen)

and confirmed changed:

    Road (world 10,4)                            ->  Road
    Sparse Forest (Eldenford interior 10,3)       ->  Sparse Forest
    toward Road (world 9,4).                     ->  toward Road

**Verified live** in the painted world, seven commands, zero leaks:

    You follow the path north toward Road — you're in Road.
    You follow the path south toward Road — you're in Road.

The 3 pytest failures in `test_ownership` / `test_scenario_data_integrity` were
A/B'd with `git stash` and are identical with and without these changes —
pre-existing, not mine.

Note `/api/state.current_area` still reports `Road (world 9,3)` because that is
the stored *name*. Presentation is fixed; the data migration is task-638.