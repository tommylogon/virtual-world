---
group: Tech Debt & Testing
---
# Unit Tests

**Filed**: 2026-07-15 (updated 2026-07-24)
**Priority**: High
**Status**: Complete — 395 tests across 18 test files, all passing

---

## Summary

The project now has comprehensive pytest unit tests covering all major engine modules. Core functionality is covered. Depth tests for UI components (room/door inspector, trigger editor interactions) were deferred as they're better suited to the Playwright click-through test upgrade (see task-97).

## Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `test_traits.py` | 57 | All 23 trait definitions, effect resolution, tick processing |
| `test_trigger_system.py` | 46 | Conditions, effects, trigger chains, edge cases |
| `test_conditions.py` | 38 | Multi-condition support, duration, decay, removal |
| `test_equipment_system.py` | 35 | Paperdoll, equip/unequip, slots, stacking, layered items |
| `test_lighting.py` | 35 | Ambient light, spill through doors, dark vision, light levels |
| `test_ghost.py` | 27 | Ghost actions, visibility, movement restrictions |
| `test_skills.py` | 26 | Skill checks, progression, modifiers |
| `test_matching.py` | 24 | Fuzzy item/name matching, ambiguous items |
| `test_mcp_commands.py` | 17 | MCP tool commands |
| `test_mcp_state_players.py` | 15 | MCP state/player operations |
| `test_mcp_editing.py` | 14 | MCP editing tools |
| `test_engine_init.py` | 13 | Engine initialization, config, world loading |
| `test_combat.py` | 12 | Turn-based combat, attack/defense, damage |
| `test_mcp_misc.py` | 11 | Misc MCP tools |
| `test_tokenizer.py` | 10 | Token counting, context window management |
| `test_mcp_skeleton.py` | 9 | MCP skeleton/infrastructure |
| `test_emote.py` | 3 | Emote narrative generation |
| `test_mcp_integration.py` | 3 | MCP integration tests |
| **Total** | **395** | |

## What's Covered by Category

| Category | Status | Notes |
|----------|--------|-------|
| Item management (create/find/take/drop) | ✅ Covered | Through trigger tests + equipment tests |
| Area management | ✅ Covered | test_engine_init, test_lighting |
| Way management | ✅ Covered | test_lighting (spill through doors), engine_init |
| Player management | ✅ Covered | test_engine_init, test_mcp_state_players |
| Trigger system | ✅ Covered | test_trigger_system.py (46 tests) |
| Movement | ✅ Covered | test_ghost, test_lighting |
| Vitals/decay | ✅ Covered | test_traits (vital multipliers), test_conditions |
| NPC behaviors | ✅ Covered | test_ghost (NPC ghost behavior) |
| Ghost mode | ✅ Covered | test_ghost.py (27 tests) |
| Combat | ✅ Covered | test_combat.py (12 tests) |
| Equipment/paperdoll | ✅ Covered | test_equipment_system.py (35 tests) |
| Lighting/spill | ✅ Covered | test_lighting.py (35 tests) |
| Skills | ✅ Covered | test_skills.py (26 tests) |
| Conditions | ✅ Covered | test_conditions.py (38 tests) |
| Traits | ✅ Covered | test_traits.py (57 tests) |
| Container system | ❌ Deferred | Needs dedicated test file |
| API endpoints | ✅ Partial | Covered by MCP tests + Playwright tests |
| Edge cases | ✅ Partial | Some overlap in trigger/condition tests |

## What's Not Covered (Deferred)

- Container system (put/take from containers, container states)
- API endpoint CRUD tests for rooms/items/doors (partially covered by MCP tests)
- Edge cases: empty world, circular door references, concurrent modifications
- Integration scenarios: multi-step player walkthroughs, NPC interaction chains

These were deferred to post-merge feature branches and are not blocking.

## Verification

### Run Tests
```powershell
cd virtual_world
python -m pytest tests/ -v
```

Expected result: **395 tests pass, 0 failures**

### Check Key Files
- `virtual_world/tests/test_traits.py` — 57 trait tests
- `virtual_world/tests/test_conditions.py` — 38 condition tests
- `virtual_world/tests/test_trigger_system.py` — 46 trigger tests
- `virtual_world/tests/test_equipment_system.py` — 35 equipment tests
- `virtual_world/tests/test_lighting.py` — 35 lighting tests
- `virtual_world/conftest.py` — shared engine fixtures
