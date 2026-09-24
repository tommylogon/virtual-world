---
group: Characters
---

# NPC Behavior Phase 2: Sensory Triggers, Faction Logic, Attack

**Filed**: 2026-09-02
**Priority**: High
**Status**: Done (2026-09-22) — schedule part deferred to task-409

---

## Status — implemented (2026-09-22)

**Live game, simple-NPC tier.** Builds on the shipped phase 1 (`add_memory`,
`set_emotion`, `set_flag`, `hide_in`/`hide_behind`/`hide_under`, `unhide`) and the
task-214 perception work. **Scheduling was intentionally dropped**: `schedule_tick`
overlaps task-409 (background schedules/work) and the newer Schedule system, so it
belongs there, not here.

### Already existed
- `attack` behavior action (`engine/triggers/behaviors.py`) — delegates to
  `CombatSystem.player_attack`; already shipped before this pass.
- `character_has_tag` condition (`engine/triggers/condition_tree.py`).

### Shipped this pass
- **Behavior actions** (`engine/triggers/behaviors.py`): `add_tag` / `remove_tag`
  on `self`/`npc`/a named character. This is what the faction example needs
  (mark the intruder `hostile`, then `attack`). Idempotent; tolerates a
  comma-string `tags` field.
- **Conditions** (`engine/triggers/condition_tree.py`):
  - `player_has_tag` — resolves a target character and matches a tag on anything
    they carry (`EDGE_CARRYING`) or wear (`player.equipped`).
  - `sight_holds` — same tag check, but only when the NPC shares the target's
    area (`npc_area`) and the target is not `hidden`.
  - `smell_detected` — matches an item tag in the area, with `range` hops of
    neighbours via `_build_exits_for_area`; uses `room_perception.visible_area_items`.
  - `sound_above` — reads `recent_hearing` and compares against the engine's
    0–3 sound scale; a 0–1 authored `threshold` maps onto `threshold × 3`.
  - `flag_equals` — compares a `flags[key]` value (phase 1 wrote these) with
    coercion for `"true"`/`"false"`/numbers.
- **Helpers**: `_player_item_tags`, `_area_id`, `_areas_within`,
  `_recent_sound_strength`.
- **Validator** (`engine/trigger_validator.py`): `CONDITION_TYPES` now lists the
  new conditions plus the previously-missing phase-1 ones
  (`npc_emotion_is`, `npc_is_hidden`, `character_has_tag`, `item_relationship`),
  so authored behaviors stop being flagged as unknown types.
- **Frontend**: `static/js/inspector/behaviors-view.js` exposes the five new
  conditions and two actions with field editors; `static/js/shared/trigger-types.js`
  lists the shared sensory conditions for item triggers.
- **Tests**: `tests/test_npc_behavior_phase2.py` (22) — item-tag senses, sight
  hidden/area gates, flags, sound thresholds, smell same-area + range expansion,
  add/remove tag idempotence, and the faction worked example.

### Not done / future
- `schedule_tick` / NPC routines → **task-409**.
- `smell_detected` scans only visible items; hidden items are not smelled.
- Sound strength for item-origin noise reads `sound_level`; speech maps via
  `SPEECH_LEVELS`.

---

## Original summary

Builds on Phase 1 to add sensory awareness (smell, sight, sound), tag-based faction logic, and the `attack` behavior action, enabling NPCs to react to what they sense, form factions, and engage in combat without LLM agents.

## Related

- Phase 1: `task-389` (shipped)
- `task-214` (NPC perception & reaction), `task-409` (background schedules)
