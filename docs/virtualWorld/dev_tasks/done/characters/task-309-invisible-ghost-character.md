---
group: Characters
---
# Invisible Ghost NPC / Undead Traits

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Done (2026-09-22) — 5e-aligned split

## Shipped & refactored (2026-09-22)

Modelled on the 5e Ghost, which keeps three axes independent. The old single
`is_undead_ghost()` check conflated them (making a `undead`-tagged zombie
invisible and untargetable), so it was split:

| Axis | Tag | Behaviour |
| --- | --- | --- |
| Not alive | `undead` | skips vitals/needs (`player_manager.is_undead`) |
| Intangible | `ghost` | phases through ways (`is_incorporeal`) |
| Seen / not | state | listed + targetable only when visible (`is_visible`) |

- `engine/player_manager.py`: `is_undead`, `is_incorporeal`, `is_visible`
  (`hidden` always hides; a `ghost` is unseen until `manifested`); the broad
  `is_undead_ghost` remains as a compat alias for "spectral entity".
- `get_players_in_area()` now gates on `is_visible` — which also fixes a
  pre-existing leak where mundane `hidden` NPCs were still listed.
- `engine/combat.py`: you can only strike what you can see ("swings at empty
  air" when unseen); a **manifested ghost is solid and hittable**. D&D-style
  damage resistance for incorporeals is not implemented.
- `engine/movement.py`: phasing keys off `is_incorporeal`.
- `engine/tick_manager.py`: vitals skip keys off the broad alias (undead or ghost).
- `engine/triggers/behaviors.py`: `manifest` / `vanish` now toggle
  `player.manifested` (they were listed in the editor but inert).
- `player.py` + `engine/serialization.py`: new `manifested` state, persisted.
- `static/js/agent/plan-manager.js`: needs-suppression also honours the
  `undead` / `ghost` tags (not just the `traits.undead` path).
- Tests: `tests/test_ghost_visibility.py` (18).

Still open: damage resistance/immunity for incorporeal undead (5e has
resistance to nonmagical weapons, immunity to cold/necrotic/poison), and
condition immunities (grappled/restrained/prone/exhausted/...).

---

## Original idea

Make the ghost in the mansion an invisible/ghost character — a "dead ghost" — with traits like undead.

## Notes

- Ghost mode (dead players acting) already exists via the ghost system; this is about an **NPC** that is a ghost: invisible, not attackable by normal means, carrying undead traits.
- Medium scope: an NPC-side ghost state (invisibility to agents/room lists, `undead` tag, phasing through ways) rather than a whole new system.
- Flavorful for the mansion scenario and reuses `docs/virtualWorld/Characters/` ghost/condition machinery.

## Related

- `developer ideas.md` line 16
- `engine/ghost.py`, `engine/conditions.py`, trait system (`data/library/traits/*.json`)
