# Goblin Scenario + Generation Scripts — Verification (2026-09-18)

Server: `http://127.0.0.1:4444` (verified listening, `/api/health` → running).

## Verdict

| Artifact | Works? | Notes |
|---|---|---|
| `tools/validate_scenario.py` on goblin scenario | ✅ pass | Shallow check only — it did **not** catch the runtime bugs below. |
| `tools/build_scenario.py` (component build) | ⚠️ after fix | Two real code bugs found and fixed; still blocked by an **incomplete component set**. |
| `tools/assemble_scenario.py` | ⚠️ after fix | Was dumping the entire library; now gated by constraints. |
| Goblin scenario in the running engine | ❌ **broken** | Toolless/scene runtime shows duplicate characters and the player as a stranger. |

The validator passing is misleading: the scenario loads (`{"status":"success"}`) but is functionally wrong at runtime.

## Bug 1 — `player.current_area` must be the area *display name*, not the node id

- Goblin scenario originally stored `"current_area": "area_camp_entrance_trail"`.
- Engine resolves areas by **name** first (`engine/room_perception.py:resolve_area_node`).
- Result before fix: `GET /api/scene/player_human_explorer` returned
  `name: "area_camp_entrance_trail"`, `desc: ""`, `ways: []`, and `in` edges pointed at
  non-existent `area_area_camp_entrance_trail`.
- Known-good scenarios store names: `pines.json` uses `"apartment 2e"`, not `area_*`.
- **Severity:** total — the starting scene was empty (no description, no exits, no items).
- Status: the canonical file has since been updated to display names (all 23 resolve).

## Bug 2 — Character nodes are duplicated (still present)

- Scenario authors 23 `character_*` nodes **and** a `players` block with 23 entries.
- The engine treats `players` as authoritative and creates its own `player_<key>` anchors.
- On load there are **46 character nodes** (23 `character_*` + 23 `player_*`).
- Runtime evidence (current canonical, no-persist load) — starting area contains:
  ```
  id=player_human_explorer   <- the active player, shown as a separate stranger
  id=Kiala      id=player_Kiala   <- duplicate
  id=Belne      id=player_Belne   <- duplicate
  ```
- Canonical convention (`pines.json`): exactly one `player_<key>` node per player key,
  node name == player key, **no** `character_*` nodes.
- Extra failure: the human explorer's node name is `"Human Explorer"` but the player key is
  `player_human_explorer`, so the scene's self-exclusion fails.

## Bug 3 — `build_scenario.py` derived IDs from names → punctuation drift

- `_slugify("Chief's Pit")` → `area_chief_s_pit`, but components reference `area_chiefs_pit`.
- Crashed with `Character character_thrazz references missing area 'area_chiefs_pit'`.
- **Fix applied:** component filename stem is now the authoritative node id
  (`load_components_with_ids()` in `tools/build_scenario.py`).

## Bug 4 — `build_scenario.py` normalized triggers twice, first with an empty node set

- `triggers = [normalize_trigger(t, set()) ...]` ran before all node ids existed, so any
  trigger with a `target` raised `targets missing node`.
- **Fix applied:** single normalization pass after `all_node_ids` is computed.

## Bug 5 — `assemble_scenario.py` dumped the whole library

- With `--constraints '{}'` it imported **456 items and 45 characters** into the seed,
  producing 474 items / 68 characters / 570 edges and 4 validation errors (characters with
  no description).
- **Fix applied:** item/character/way imports are now gated on explicit
  `items`/`characters`/`ways` constraint targets and stop at the target.
- Re-run result: seed preserved exactly (30 areas, 29 ways, 18 items, 23 chars, 114 edges).

## Still open — component set is incomplete

`tools/build_scenario.py` now fails only because `tools/scenario_components/` is missing
areas that its ways/triggers reference:

```
Way way_entrance_to_pit references unknown area(s): area_camp_entrance, area_chiefs_pit
Trigger logic_trigger_examine_camp_trail targets missing node 'area_camp_entrance_trail'
```

Only `area_chiefs_pit.json` is present, but the way needs `area_camp_entrance` and the
trigger needs `area_camp_entrance_trail`. Either add those area components or remove the
dangling way/trigger components.

## Remaining remediation for the scenario to actually work

1. Delete the 23 authored `character_*` nodes (keep the `players` block authoritative), or
   rewrite them to `player_<player_key>` matching the player keys with node name == key.
2. Align the human player: player key and character node name must match
   (`player_human_explorer`), otherwise the scene shows the player as a stranger.
3. Re-verify with `GET /api/scene/player_human_explorer` (expect: 1 explorer excluded,
   no duplicates) and `GET /api/scene/Thrazz` for the camp interior.
4. Note `"persist": true` in the scenario: loading it writes scenario files to disk, and a
   peer session (`main`) is active in this project — coordinate before bulk edits.

## Files changed by this verification

- `tools/build_scenario.py` — filename-as-id; single trigger normalization pass.
- `tools/assemble_scenario.py` — constraint-gated library imports.
- Report: this file.
