---
group: Characters
status: inprogress
---
# Invisible Ghost NPC / Undead Traits

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: In progress — NPC ghost base shipped (v1.4.0); 3-axis visibility split not on master (lives on `foil-stranger`, commit 8039509, unmerged); resistance/immunity follow-ups filed as task-490

---

## Shipped / Gap

- **On master (v1.4.0):** NPC ghost base. `player_manager.is_undead_ghost` (`engine/player_manager.py:361`) makes a spectral entity skip vitals and be untargetable by normal attacks (`engine/combat.py:131`); ghost actions/`manifest` are handled by `engine/ghost.py` + `routes/action_handlers.py:847`.
- **Not on master:** the 5e-style three-axis split — `is_undead` / `is_incorporeal` / `is_visible`, a persisted `manifested` state, `get_players_in_area()` visibility gating, and `tests/test_ghost_visibility.py`. That work is on `foil-stranger` (commit 8039509) and needs merging/porting.
- **Still open (task-490):** incorporeal damage resistance/immunity (nonmagical weapons, cold/necrotic/poison) and condition immunities (grappled/restrained/prone/exhausted/...).

## Idea

Make the ghost in the mansion an invisible/ghost character — a "dead ghost" — with traits like undead.

## Notes

- Ghost mode (dead players acting) already exists via the ghost system; this is about an **NPC** that is a ghost: invisible, not attackable by normal means, carrying undead traits.
- Medium scope: an NPC-side ghost state (invisibility to agents/room lists, `undead` tag, phasing through ways) rather than a whole new system.
- Flavorful for the mansion scenario and reuses `docs/virtualWorld/Characters/` ghost/condition machinery.

## Related

- `task-490` — incorporeal damage resistance and condition immunities (still open)
- `developer ideas.md` line 16
- `engine/ghost.py`, `engine/conditions.py`, trait system (`data/library/traits/*.json`)
