---
type: task
status: todo
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
