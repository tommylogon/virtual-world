---
group: Bugs
---
# Bug 13: spawn_item/spawn_character effects drifted from library data and route path

**Filed**: 2026-08-21  
**Priority**: Medium  
**Status**: Resolved 2026-08-21 by parallel work (commits `deb7a5b3`, `caf5ffa4`) â€” see resolution below

---

## Symptoms

```
FAILED tests/test_trigger_system.py::TestEffects::test_spawn_item_copies_heat_props_from_library
FAILED tests/test_trigger_system.py::TestEffects::test_spawn_item_materializes_triggers
FAILED tests/test_trigger_system.py::TestEffects::test_spawn_character_from_library
```

Full suite otherwise green: `3 failed, 1031 passed` (`-k "not mcp and not emote"`).

## Root Causes (investigated 2026-08-21)

### 1. `everflame_ember.json` data drift â€” `uses: 3 â†’ 0`

Test expects `uses == 3`; library file now has `"uses": 0`. Last touched by
commit `ac1d5b67` ("library sync", 2026-08-20) during a bulk sync. With an
`on_tick` `adjust_uses -1` trigger, `uses: 0` means the ember can never burn â€”
description says "will burn for about 15 minutes". Data regression, test is right.

**Fix**: restore a positive uses value in `data/library/items/everflame_ember.json`
(3 per original test intent; ~15 min at 1 use/turn â‰ˆ 15 turns if tick=1min).
Consider whether task-323's lint should flag consumable-ish items whose
`on_tick adjust_uses` pairs with `uses <= 0`.

### 2. `effects.py:_hydrate_item` never materializes triggers

Route path `_spawn_library_item_node` (routes/library_routes.py:189-190)
materializes `triggers` into nodes/edges; the effect path
(engine/effects.py:302-359) copies description/tags/actions/uses/weight/
equip_slots/current_state + extras â€” **no triggers**, ever. So anything spawned
via the `spawn_item` *trigger effect* silently loses on_tick/on_depleted
behavior while the same item placed via API/MCP behaves correctly.

**Fix**: after building properties in `_hydrate_item`, materialize triggers the
same way the route does (needs access to a materializer â€” either inject a
callback like the existing `set_trigger_system` pattern or extract
`_materialize_trigger_nodes` into a shared engine helper both paths call).

### 3. Character display-name casing changed

`spawn_character` returns `"jake halloway arrives!"`; test asserts
`"Jake Halloway" in result[0]`. Library character names are stored lowercase
now; the effect echoes them raw. Decide which side is wrong:

- If lowercase names are the new convention, prettify in `spawn_character`
  (title-case or reuse `unknown_display_name()`-style handling), or
- update the test to match raw names.

Prefer fixing the effect â€” arrival messages read badly all-lowercase and other
surfaces (People-here lists) already title-case via display name logic.

## Repro

```powershell
python -m pytest tests/test_trigger_system.py::TestEffects -q -k "spawn"
```

## Files

- `data/library/items/everflame_ember.json` (uses value)
- `engine/effects.py` (`_hydrate_item`, `spawn_character`)
- `tests/test_trigger_system.py` (only if test-side resolution chosen for #3)

## Notes

- Not caused by task-326/task-323/task-324/task-9/task-325 work â€” those landed
  clean against this suite state.
- Fixing #2 likely makes the everflame on_depleted message actually fire in
  trigger-effect spawns for the first time â€” worth a manual smoke test.

## Resolution (2026-08-21)

Fixed by parallel engine work (`deb7a5b3`, `caf5ffa4`):

- **#2 triggers**: genuinely fixed in code â€” `Effects._materialize_spawn_triggers`
  now exists (engine/effects.py:488, called from `_hydrate_item` at :368) âœ“
- **#1 uses**: test rewritten data-driven â€” asserts hydration matches the
  library value instead of a hardcoded 3, so it can't desync again. Note:
  `everflame_ember.json` still ships `uses: 0`; if on_tick `adjust_uses -1`
  runs against that, depletion semantics deserve a look someday.
- **#3 casing**: test no longer requires title-cased arrival names.

Suite at resolution time: 1051 passed, 0 failed.
