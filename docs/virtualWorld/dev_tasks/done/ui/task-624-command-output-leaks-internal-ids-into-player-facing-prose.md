---
type: task
status: done
area: ui
priority: medium
---

# task-624: Command output leaks internal ids into player-facing prose

**Filed:** 2026-09-30
**Related:** 

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. In `kraktooth_goblin_camp`, follow the north and south paths that lead toward Road and read each event-stream line.
   - expected: movement prose says “toward Road” and “you're in Road”, without grid coordinates.
   - observed: live in the painted world across seven commands; zero coordinate leaks.
2. Inspect labels containing coordinate pairs and legitimate parentheses.
   - expected: `Road (world 10,4)` and `Sparse Forest (Eldenford interior 10,3)` display without coordinates, while `Bathroom (Kraktooth, level 2)`, `The Outhouse (West)`, and `Cellar (Below Kitchen)` remain unchanged.
   - observed: the card records all six before/after examples, including `toward Road (world 9,4).` becoming `toward Road`.
3. Inspect `/api/state.current_area` for the same location.
   - expected: the data record remains unchanged; this task fixes presentation, not stored names.
   - observed: recorded as `Road (world 9,3)`; the data migration belongs to task-638.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Load `kraktooth_goblin_camp`, use the command input for movement, and read the resulting line in the event stream; the at-rest way labels and their hover text are the companion wayfinding surface.

Current availability: The card records seven live commands in the painted world with zero coordinate leaks. It records that `Road (world 10,4)` and `Sparse Forest (Eldenford interior 10,3)` lose coordinate suffixes while semantic names such as `Bathroom (Kraktooth, level 2)` remain intact.

Live steps when available:
1. From the camp, use the north and south paths that lead toward Road and inspect each event-stream result.
   - expected: the line says “You follow the path north/south toward Road — you're in Road.”; no `(world N,M)` or `(Eldenford interior N,M)` suffix reaches player-facing prose.
2. Open the way label at rest, then hover that same way.
   - expected: the at-rest label and hover resolve the display name consistently; the node's stored name in `/api/state` is not silently migrated by this presentation fix.
3. Inspect legitimate parenthetical names in the same scenario, including `Bathroom (Kraktooth, level 2)` and `The Outhouse (West)`.
   - expected: descriptive parentheses remain; only a trailing coordinate pair is removed.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
