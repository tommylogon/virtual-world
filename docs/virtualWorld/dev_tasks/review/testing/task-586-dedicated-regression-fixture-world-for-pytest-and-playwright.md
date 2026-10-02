---
type: task
status: review
area: testing
priority: high
---

# task-586: Dedicated regression fixture world for pytest and Playwright

**Filed:** 2026-09-29
**Related:** bug-55, task-444, task-572

## Goal

world_template.json is three things at once: the boot default a real player starts from, a selectable entry in the scenario picker (`engine/soak_runner.py:1062-1072`), and the de-facto fixture ~139 `create_app()` call sites depend on. It satisfies the third by accident — tests rely on incidental content (the first way node in insertion order, `Backpack` carrying `unequip`, `Living Area` never existing) — and that accident is what made bug-55 possible. Ship one declared, inert fixture under `tests/`, assert its contract in a test, and stop conflating it with shipped content.

## What exists now

The root `world_template.json` is 376,793 bytes: 19 areas, 98 item nodes, 19 way nodes, 3 players. `app.py:41-59` loads it for **everyone**, TESTING or not, and `app.py:62` points `_scenario_source` at it. Consequences, all of them real today:

- A new player's "new game" boots a world with an NPC called `rat` and a school bathroom. That is a test artifact shipped as content.
- `data/scenarios/world_template.json` is a **byte-identical duplicate** (376,793 bytes, same mtime). Two files, one name, one truth, and nothing keeps them in sync.
- `tools/test_all.cjs:227` runs `POST /api/save-game` against a live server booted from that file, so the Playwright suite derives saves from the unit-test fixture and writes them into the real saves directory.
- ~100 tests depend on content nobody wrote down, and some already pass for the wrong reason: `tests/test_action_inverses.py:84-98` picks the template's `Backpack` and asserts `unequip` on it.

## The contract (what a fixture has to declare)

These are referenced by tests that never create them, so the fixture must ship them. Every row becomes an assertion in `tests/test_fixture_contract.py`.

| | Requirement | Who depends on it |
|---|---|---|
| Areas | `Blizzard Forest Clearing`, `Kitchen`, `Study`, `Cellar` | ~30 sites; the "move everyone else to Kitchen" pattern is everywhere |
| Characters | `Kaelen Voss` (active, **first** in the registry, `traits == {}`), `Lyrie`, `rat` (`simple_npc`, >= 8 behaviours, stationary) | `next(iter(players))` in ~12 files; `player_Kaelen_Voss` hard-coded at `tests/test_trigger_system.py:2597` |
| Items | `item_bread`, `item_Create Flame`, `item_water_pitcher` | collisions are why tests invent `testgrub`-style names; `water_pitcher` is authored with an `on_drink` |
| Structure | every `way` node wired to exactly 2 areas; canonical `area_<slug>` ids; >= 2 areas, >= 1 item node, >= 1 character node; non-empty exits from the clearing; some 2-hop route | `tests/test_way_connect_repair.py:192-193` walks *all* way nodes |
| Clock | `time_per_tick_minutes: 5`, `clock_start_hour: 8`, `game_time "08:00:00"` | `tests/test_pleasure_system.py:24-29` pins it; `tests/test_schedule.py` asserts deltas from it |
| Rates | no `decay_rates` overrides, or exactly `vital_rates.BASELINE_DECAY` | `tests/test_decay_rate_bake.py:88-90` |
| Save payload | `players` and `areas` present after `to_scenario_dict()` | `tests/test_saveload.py:64` |

## The other half: what it must NOT contain

**The fixture has to be inert — nothing moves unless a test moves it.** Today the rat has a behaviour tree and autonomy, so a test that "isolates" a character gets company back on tick 1 because the cast wandered into the room. That is bug-55, and any fixture that can only express "one character, alone" by accident will keep minting order-dependent failures. Two tiers from one file:

- **inert by default** — no wandering, no agendas, so decay/vitals/company tests need no `skip_npcs=True`
- **actors opt in** — the ~10 tests that *want* NPC behaviour enable it explicitly

Also: no decorative items with names tests collide with, and **no `Living Area`**. That string is the `app.py` fallback name *and* the "404" literal in `tests/test_graph_move.py:72` and `tests/test_library_build.py:63`; add it one day and those tests fail in a way that reads as a routing bug.

## Steps

1. Add `tests/fixtures/world.json` — the contract above, characters made inert — and `tests/conftest.py` helpers `world()`, `solo(world, who, area=...)`, `company(world, a, b)`. `solo()` is the real point: a fixture that cannot express isolation is what produced bug-55.
2. `tests/test_fixture_contract.py` asserting every row of the table, plus the *negative* rows (no `Living Area`, no autonomous NPC).
3. Point `create_app({"TESTING": True})` at that path explicitly, instead of "whatever is at the repo root". Fall back to the old template only if a non-TESTING boot.
4. Write safety: under TESTING, leave `_scenario_source` unset (or inside a temp `DATA_DIR`) so `POST /api/scenario/commit` cannot reach the fixture. `tests/test_scenario_name.py:1-6` already names this hazard.
5. Repoint the three tests that read the template **as a file**: `tests/test_npc_behaviors.py:74-83`, `tests/test_decay_rate_bake.py:37-40`, `tests/test_soak_runner.py:156-160`.
6. Fix the tests that pass for the wrong reason while the contract is fresh: `tests/test_action_inverses.py:84-98` (`Backpack`), `tests/test_library_consumable_relief.py:55-60` (its claim that a colliding item id makes `add_node` *replace* the node is stale — `graph.py:167-170` suffixes instead).

## Acceptance

- [x] `create_app({"TESTING": True})` loads `tests/fixtures/world.json`, and `tests/test_fixture_contract.py` passes.
- [x] The full suite still matches the clean-`master` failure *names*. Measured 2026-10-02: baseline `15 failed / 6607 passed`; after this work `16 failed / 6644 passed`, the only extra being the pre-existing flaky `test_undead_resistance.py::TestCombatHook::test_a_magic_blade_hurts_a_ghost`, which fails 3/8 on a clean `master` worktree too. (The old "1 failed / 5025" figure is stale.)
- [x] `tests/test_social_company.py` passes with its `skip_npcs=True` line **removed**, proving the fixture is inert rather than the test working around it. (If it needs the flag, the fixture is not inert and this task is not done.)
- [x] No TESTING run can write to the fixture: `git status` is clean after the suite, and a `POST /api/scenario/commit` under TESTING writes nothing (`_scenario_source` is unset).
- [x] Every test that reads the template as a file points at the fixture or has been repointed.
- [x] Every one of the "wrong reason" tests named in step 6 either fails without the template or asserts its own node.

## Outcome (2026-10-02)

- `tests/fixtures/world.json` is the fixture: a copy of the shipped content with
  **every player's `autonomy` set False and `npc_behavior` stationary**. The
  graph/areas/items are untouched so all ~146 `create_app()` sites see the same
  content; only the cast stops acting. `tests/test_fixture_contract.py` (15 tests)
  asserts every contract row plus the negative rows (`no Living Area`, no
  autonomous NPC, the cast does not move on a full turn) and the write-safety.
- `app.py` boots the fixture under TESTING (`app.config['TESTING_TEMPLATE']`) and
  leaves `world._scenario_source = None`, so `_save_scenario()` refuses. Reset
  reloads the fixture but keeps the source unset (both `routes/saveload.py`).
- Inertness needed one engine seam: `engine/npc_behaviors.process_simple_npcs`
  now honours `autonomy is False`, the same marker
  `background_simulation.py:234` already uses. A simple NPC with `autonomy` False
  keeps its behaviour tree (so `test_rat_template_behaviors_parse` still parses
  it) but does not run it until a test opts in.
- `tests/conftest.py` gains `new_world()`, `solo()`, `company()` and a `world`
  fixture.
- Repointed the file-reading tests (`test_npc_behaviors`, `test_decay_rate_bake`)
  at the fixture. `test_soak_runner`'s assertion is about the scenario *picker*
  scanning `data/scenarios/`, not the boot template, so it is unchanged by design.
- The fixture exposed a second use of `autonomy: False` — the timeskip route's
  "another attended human" check — so `test_soak_orders._hero` and
  `test_timeskip._hero` now declare the rest of the cast NPCs, and
  `test_health_model_fixes`'s regen test ticks with `skip_npcs=True` (its gate is
  the per-character block, not the water policy).

**Follow-ups (unchanged):** the boot default a real player starts from, deleting
`data/scenarios/world_template.json` (the duplicate), and applying
`solo()`/`company()` suite-wide (task-572).

## Follow-ups (deliberately NOT this task)

- **What a real player's new game starts from.** The boot default needs its own small authored scenario, and `data/scenarios/world_template.json` (the duplicate) should be deleted. That is a content decision, not a testing one — file it separately.
- **The Playwright harness on the fixture** — pinned seed, pinned start hour, `DATA_DIR` in a temp dir, and the Phase 3–5 work already tracked by **task-444**. This task only has to make the fixture *usable* by it.
- **The `solo()`/`company()` helpers applied suite-wide**, replacing the hand-rolled "move everyone else to Kitchen" helpers one file at a time. That is **task-572**'s integration-layer territory, not a prerequisite for this fixture.
