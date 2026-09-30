---
type: task
status: cancelled
area: gameplay
priority: medium
---

# task-609: state.area_presence holds 5 entries for 23 players and disagrees with the Player model

**Filed:** 2026-09-30
**Related:** 

## Goal

All 23 players carry current_area, but area_presence holds only 5 non-empty entries. Counted from the Player model, Camp Entrance Trail has Belne, Kiala and Eldenford Merchant plus the player; area_presence reports only Belne and the Merchant, and the human-turn modal renders 5 strangers. Either area_presence is a stale vestigial index or three sources disagree on occupancy.

## Acceptance

- TODO

## Cancellation

Cancelled 2026-09-30. The finding misread what the field is for.
``area_presence`` is the task-360 **presence ledger**: ``_record_area_presence``
(virtual_world_engine.py:539) is called only from ``movement.py``, so it records
"who has moved through here since tick N", not "who is here". A character who has
never moved is correctly absent from it. 3 entries against 23 players is that
mechanism working, not a stale index.

Measured, for the record: Player model has 23 players with ``current_area`` across
15 distinct areas; the ledger has 3.

The genuine residue is a naming one, not a correctness one: the state payload
publishes a movement ledger under a key that reads like an occupancy index. That
is a legibility point, not a bug, and it belongs with the audit's
method-limitation section rather than in the backlog.