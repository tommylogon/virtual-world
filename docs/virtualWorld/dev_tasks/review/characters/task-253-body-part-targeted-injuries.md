---
group: Characters
---

# Body Part Targeted Injuries & Combat Routing

**Filed**: 2026-08-16
**Priority**: High
**Status**: In Review — implemented 2026-08-19, pending browser E2E

---

## Problem

Combat (`engine/combat.py` `player_attack()`, line 62) routes **all** damage straight
to `target.vitals["HP"]` with no body-part concept. There is no `where` parameter, no
`interact` vs `attack` branch, and nothing connects a combat hit → a body region → an
`injured`/`bleeding` condition that drops items or blocks actions. "A gash to the arm"
and "a bruise on the leg" are mechanically identical. This is the core gap for
bodies/injuries and is currently undefined.

## Design (proposal — resolve GAP A + GAP B in the audit doc)

- **Add a body-region taxonomy** used for BOTH injury and (later) erogenous targeting:
  `head`, `torso`, `arm_left`, `arm_right`, `leg_left`, `leg_right`, `hand_left`,
  `hand_right`, `foot_left`, `foot_right`. Keep it a fixed set on the schema, not graph
  nodes.
- **`where` parameter on the action schema**: `{action, type, target, where, intensity,
  emote}`. `type ∈ interact (no damage) | attack (existing combat path)`. Default
  `type: interact`.
- **Combat routing**: `player_attack()` accepts an optional `where` region. On a hit:
  apply the same damage to `HP`, and ALSO apply a region-scoped condition instance
  (e.g. `injured` with a `body_part` override) if damage crosses a per-region threshold.
  Bleeding can then trail/spawn items in that region.
- **Region conditions** reuse the multi-instance condition shape — each body part can
  hold its own `injured`/`bleeding` instance with its own `duration`/`ends_on`.
- **Accessibility check** (`_resolve_body_part()`): a region is reachable unless blocked
  by clothing `coverage` on the relevant equip slot stack (paperdoll layers) or a
  condition like `restrained`.
- **Genericity**: injury/bleeding are NON-sexual and always active — do NOT gate behind
  the mature-content toggle. Only arousal/pleasure coupling is mature-gated.

## Implemented (2026-08-19)

- **`engine/body_parts.py`** (NEW): flat + zoned `BODY_REGIONS` catalog — 12 coarse injury
  regions (`head`, `neck`, `torso`, `back`, `arm_left/right`, `hand_left/right`,
  `leg_left/right`, `foot_left/right`) with nested erogenous zones (`nipple_left/right`,
  `breast_left/right`, `genitals`, `cheeks`, `lips`, `thigh_left/right`) as `parent`
  references — plus constants `INJURY_DAMAGE_THRESHOLD=5`, `BLEEDING_DAMAGE_THRESHOLD=10`,
  `COVERAGE_EXPOSED_THRESHOLD=0.8`, and helpers `resolve_region()` (exact id / alias /
  "left X" side forms), `injury_region()` (erogenous → parent injury region),
  `region_chain()`, `coverage_slots()`, `is_exposed()` (checks OUTER layer coverage of
  the equip-slot stack, ignores `__multi_slot_` markers), `default_body_state()`,
  `region_injury_level()` (damage → 0/1/2/3), and a d20 `HIT_LOCATION_TABLE` with
  `roll_hit_location()`.
- **`player.py`**: `self.body_state = default_body_state()` after `decay_rates`;
  `end_instances()` already handles `ends_on` resolution. `CONDITION_DEFINITIONS`
  loads `injured`/`bleeding` from the library.
- **`engine/serialization.py`**: player dict round-trips `body_state`.
- **`data/library/conditions/injured.json` + `bleeding.json`** (NEW): region-scoped,
  `stack: "accumulate"` (per-region instances), `ends_on: ["fix","heal","medicine"]`,
  `default_duration: null`, `level_periodic` HP drain, `symptoms` keyed by remaining
  duration (JSON keys must be QUOTED strings — the loader coerces them back to ints;
  unquoted numeric keys break JSON parsing).
- **`engine/combat.py`**: `player_attack(..., where=None)` resolves an aimed region up
  front; un-aimed attacks roll `roll_hit_location()` on a HIT (misses don't consume a
  roll). On a hit with an exposed region and damage ≥ 5, `_apply_region_injury()` adds
  an `injured` instance (level from `region_injury_level`, `body_part` = injury region,
  i.e. erogenous zones collapse to their parent) plus `bleeding` at damage ≥ 10. Hit
  messages append `(in the <region>)` and the injury note.
- **`routes/action.py`**: attack branch strips a trailing region phrase (` on `,
  ` where `, ` in the `, ` in ` — earliest match), re-tokenizes, passes
  `where=attack_where` (resolved id or raw text fallback) to both weapon and
  bare-handed `_player_attack()` calls.
- **`virtual_world_engine.py`**: `_player_attack()` forwards `where`.
- **`static/js/agent/action-normalizer.js`**: `attack` case returns
  `attack ${obj} on ${where}` when the agent supplies a `where`.
- **`tests/test_body_parts.py`** (NEW, 29 tests): taxonomy shape, resolution (id/alias/
  side forms), chains, exposure (bare / low coverage / high coverage), injury levels,
  hit-location table integrity + determinism, aimed region injury, un-aimed location
  roll, low-damage no-injury, bleed on threshold, fix-action end.

## Files

- `engine/body_parts.py` — NEW: region catalog, resolver, coverage, hit-location table
- `engine/combat.py` — `player_attack(where=...)`, `_resolve_hit_region`, `_apply_region_injury`
- `engine/serialization.py` — `body_state` round-trip
- `routes/action.py` — `where` region phrase parsing
- `virtual_world_engine.py` — `_player_attack(..., where=...)` facade
- `player.py` — `body_state` init
- `data/library/conditions/injured.json`, `bleeding.json` — region-aware conditions
- `static/js/agent/action-normalizer.js` — `attack ... on <where>`
- `tests/test_body_parts.py` — NEW test module

## Testing

- [x] Weapon hit to a specified `where` applies damage AND a region-scoped injury
- [x] Bare-handed aimed attack applies region injury
- [x] Un-aimed attack rolls a d20 hit-location on a hit (deterministic + table tests)
- [x] Low-damage hit below threshold applies no injury
- [x] Covered region (high `coverage` clothing) blocks direct skin injury
- [x] `injured`/`bleeding` region instances end independently via `ends_on`
- [x] Bleeding applied at damage ≥ 10
- [ ] Full-suite + JS syntax (DONE: 1017 passed, 1 skipped; node --check clean)
- [ ] Browser E2E: `attack jake on the head` through `/api/action`

## Related

- `review/characters/pleasure-system-audit-gaps-2026-08.md` — GAP A / GAP B / GAP C
- `todo/characters/task-190-more-conditions.md` — `injured`/`bleeding`/suffocating
- `todo/characters/task-211-intimacy-verbs-actions.md` — `where`/`type`/`interact`
- `todo/characters/task-207-body-state-and-vitals.md` — `body_state` per-part `injury`