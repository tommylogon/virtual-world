# Bug 21 — Steal/give crash: AttributeError get_player_node_id on facade

**Status:** In Review — fixed 2026-08-23, pending live repro

## Symptoms

Human-controlled `steal` from another character 500s with:

```
AttributeError: 'VirtualWorld' object has no attribute 'get_player_node_id'
```

`give` has the same latent bug one line up.

## Root cause

`engine/item_actions.py` called `player_manager.get_player_node_id(...)`
at the give site (was :1225) and steal site (was :1268), but `player_manager`
there is the `VirtualWorld` facade, which exposes `player_node_id()`
(virtual_world_engine.py:232) and `_player_node_id()` (:253) — never
`get_player_node_id`. That name only exists on the real PlayerManager /
test mocks, which is why the pytest suite stayed green while production
crashed.

The defensive helper `_pm_get_player_node_id`
(engine/character_spatial.py) already existed for exactly this duck-typing
problem but its fallback chain checked `get_player_node_id` →
`_player_node_id`, skipping the facade's public non-underscore
`player_node_id`.

## Fix

- `_pm_get_player_node_id` fallback chain extended:
  `get_player_node_id` → `player_node_id` → `_player_node_id` →
  final fallback `NodeIDHelper.player_node_id(name)` (engine/node_ids.py).
- Both call sites in `item_actions.py` now use the helper instead of
  calling the phantom method directly.

## Verification

- `python -m pytest tests/test_item_actions.py -q` — 54 passed.
- Full suite `pytest tests/ -q -k "not mcp and not emote"` —
  1055 passed, 2 skipped.
- Live browser repro of steal still pending.

## Audit follow-up (2026-08-23) — 4 more phantoms, same family

Scripted audit of every `player_manager.*` / `self.gs.*` / `self.skills.*`
call in `engine/*.py` against the VirtualWorld facade's attrs found four
more production crashes of the same class (all fixed same day, suite green
1056 passed):

| Site | Phantom call | Trigger | Fix |
|------|-------------|---------|-----|
| `item_actions.py:1764` | `player_manager.slasher_attack(...)` | `use` a weapon-ish item on a character | route to facade `player_attack` (combat.player_attack), pass weapon_node |
| `npc_behaviors.py:307` | `self.gs._slasher_attack(...)` | slasher NPC hunt reaches target area | `self.gs.player_attack(...)` |
| `tick_manager.py:199,245` | `player_manager.spawn_body_item(...)` | ANY tick death (exposure/starvation) — would break the tick loop | `self.gs._spawn_body_item(...)` |
| `combat.py:126,127,397` | `self.skills.get_player_node_id(...)` | attack while grappled; `_find_weapon_in_inventory` | `_pm_get_player_node_id` helper |

`_slasher_attack` was removed when task-54 generalized it into
`combat.player_attack`; both callers were never updated. The other modules
(activities/equipment/grapple/narration) call `get_player_node_id` on the
REAL PlayerManager, which has it — only facade-alias call sites were broken.

## Files touched

- `virtual_world/engine/character_spatial.py`
- `virtual_world/engine/item_actions.py`
- `virtual_world/engine/npc_behaviors.py`
- `virtual_world/engine/tick_manager.py`
- `virtual_world/engine/combat.py`
