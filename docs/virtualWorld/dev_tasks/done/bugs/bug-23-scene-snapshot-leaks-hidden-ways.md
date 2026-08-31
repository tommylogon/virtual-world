# Bug 23 â€” Human turn panel scene leaks hidden (undiscovered) ways

**Status:** Done — confirmed by Tommy 2026-08-30.
1120 passed. Browser E2E pending.

## Found

2026-08-24 playtest (mansion foyer): the panel's WAYS OUT listed
`slaughterhouse-sewer_passage` with hover text "a hidden passage behind a
false wall panel in the foyer" â€” the secret, handed to the player for free.
Tommy spotted it in the turn composer screenshot.

## Why

`engine/scene_snapshot.py` (task-333) filters hidden ITEMS
(`current_state == "hidden"` â†’ skip) but the ways loop had no such check.
`look`'s `build_exits_for_area` (area_description.py:134-143) hides hidden
ways unless the viewer is the slasher or has the `(area_name, direction)`
key in `player.discovered_exits`; search/fumble discovery (narration.py)
writes that key and flips the way's state off "hidden". The panel snapshot
must obey the same contract.

## Fix

- `engine/scene_snapshot.py` ways loop: skip ways with
  `current_state == "hidden"` unless `player_manager.is_slasher(player_name)`
  or `(area_name, raw_direction)` is in `player.discovered_exits` â€” the
  exact rule + key shape used by look and narration.
- Module docstring updated.

## Tests

`tests/test_scene_snapshot.py`:
- `test_hidden_ways_stay_out_of_scene` â€” hidden way absent for a normal player
- `test_discovered_hidden_way_shows_in_scene` â€” appears once the
  `(area, direction)` key is in `discovered_exits`
- `test_slasher_sees_hidden_ways_in_scene` â€” slasher sees it undiscovered
- fixture pins `is_slasher` (MagicMock default would be truthy)

## Verification

- pytest: 19/19 scene+name tests, full suite 1120 passed
- Browser: reload panel in a room with an undiscovered hidden way â€” chip
  must be gone; after `search` finds it, it must appear.

