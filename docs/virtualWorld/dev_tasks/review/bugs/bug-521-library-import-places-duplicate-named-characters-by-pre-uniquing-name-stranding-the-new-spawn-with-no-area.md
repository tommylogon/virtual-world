---
type: bug
status: review
area: bugs
priority: medium
---

# bug-521: Library import places duplicate-named characters by pre-uniquing name, stranding the new spawn with no area

**Filed:** 2026-10-04
**Related:** 

## Goal

Importing a library character whose display name already exists in the world
leaves the NEW spawn with `current_area: null` — even when an explicit area is
chosen in the place dialog. Found live 2026-10-04: imported "zombie" three times
into kraktooth_goblin_camp at Old Dwarven Ruins; the client showed area "?" for
two of the three and `worldState.players` confirmed `current_area: null` for both
duplicates (`zombie__9dcb3e`, `zombie__c4d808`), while the first "zombie" sat in
Old Dwarven Ruins.

## Why

`PlayerManager.add_player` (engine/player_manager.py:182) registers a duplicate
display name under a uniqued registry key (`zombie__<id6>`) — per task-446 the
display name is free to repeat. But `handle_library_import_character`
(routes/library_ops.py:717) then calls `set_player_area(player_name, ...)`
with the ORIGINAL name, which the matcher resolves to the primary holder of
that name — the first zombie. The new spawn's area is never set.

## Fix (2026-10-04)

After `add_player`, re-resolve the registry key the world actually assigned:
`player_name = pm._players_by_id.get(player.id, player_name)` — guarded on the
player having an id. All downstream placement (and the expression-pack node
lookup) then target the new spawn. `tests/test_library_character_import.py`
5 passed after the change.

## Acceptance

- [x] Importing the same library character twice with an explicit area puts
      BOTH spawns in that area (fix verified by test suite; live re-verification
      needs a server restart, which reloads the scenario and loses the
      unsaved world)
- [x] The first-holder zombie keeps its area

TODO

## Acceptance

- TODO

## Workaround (pre-restart) and live resolution

The agent inspector's location dropdown (`#player-room`, rendered per selected
character) fires `ApiClient.updateCharacter(<registry key>, {current_area})`
with the CORRECT uniqued key, so it repairs stranded spawns manually. Used live
2026-10-04 to move both duplicates into Old Dwarven Ruins; verified in
`data/autosave.json` server-side: all three zombies carry
`current_area: "Old Dwarven Ruins"` in scenario kraktooth_goblin_camp.
The import path itself still needed the code fix above.
