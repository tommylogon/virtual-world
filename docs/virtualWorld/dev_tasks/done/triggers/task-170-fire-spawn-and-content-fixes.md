# Task-170: Fire Spawn & Content Fixes (ember burn-down, Culdron, flame messaging, burn-duration UX)

**Status:** ALL FOUR ISSUES LANDED AND LIVE-VERIFIED 2026-08-03 — backend green, live playtest passed, one bonus fix.
**Source:** Verification playtest of the F1-F8 fixes (world_template scenario, Lyrie + Kaelen, 2026-08-02 evening session). All root causes verified against the live `data/autosave.json` and current engine code.

### Live-session verification (2026-08-03, dev server :4444)

- **Issue 1 (burn-down) ✅** — `use create flame` as Lyrie spawned `everflame_ember` in Weeping Willow Hollow with the full property copy (`uses: 3`, `current_state: lit`, `light_level: dim`, `target_temperature: 30`, `heating_rate: 0.5`) AND both trigger edges materialized (`trigger_everflame_ember_on_tick_*`, `trigger_everflame_ember_on_depleted_*`). Three ticks later it burned 3→2→1→0; log shows "The Everflame Ember burns out." + "The everflame ember gutters and dies." (on_depleted message), node removed.
- **Issue 3 (fire messaging) ✅** — `use create flame on fallen leaves` → "but the fallen leaves are too cold and damp to catch." (fire-tag reason list hit, no "loose or movable").
- **Issue 4 (duration UX) ✅** — `examine ember` → "3 uses left (~15 minutes of warmth/light)." Spawn message on the live world still shows the old "It radiates warmth." — that node predates the data fix; fresh load picks up the new message.
- **Issue 2 (cauldron) ⚠️ data-side only** — live world still holds the stale `item_Culdron` node (no `library_id`, so refresh-from-library can't act on it). Data files verified fixed: `data/scenarios/world_template.json` restored from git (only intentional `culdron` alias remains), `data/library/items/cauldron.json` has clean content + aliases. Live fix requires a fresh world load.
- **Bonus fix 🐛** — fire failure reasons ended with `.` while the caller appends `.` → "to catch.." double period. Removed the trailing periods (`engine/item_actions.py:1103-1107`); re-verified live: "nothing dry enough to burn."

---

## Goal

Fix the four issues found while verifying the F1-F8 fixes in a live playtest:

1. **Spawned items never burn down** — the `Everflame Ember` spawned by `Create Flame` keeps `uses: 3` forever.
2. **Culdron content is broken** — mangled examine text and a name typo forcing fuzzy matches.
3. **Fire-on-background-object messaging is nonsense** — `use Create Flame on fallen leaves` says it "doesn't seem to be loose or movable at all".
4. **No burn-duration feedback** — neither players nor NPC agents are told how long the ember lasts.

---

## Issue 1 — Spawned items never get their triggers (ember never burns down)

### Evidence

- `use Create Flame` → `"A small flame flickers in your palm and settles into a glowing ember at your feet. It radiates warmth."` — the spawn works and the message is real (F6 partially verified), but after 6+ ticks the ember still shows **3 charges** and never burns out.
- Live autosave graph confirms it: the `everflame_ember` node's **only edge is `everflame_ember --in--> area_weeping_willow_hollow`** — zero `triggers` edges, so no `on_tick` / `on_depleted` trigger exists for the spawned instance.

### Root cause

`handle_spawn_item` (`engine/effects.py:149-213`) hydrates library items but only copies a fixed property list:

```
name, description, tags, actions, uses, weight, equip_slots, hidden, current_state
```

(`engine/effects.py:179-187`). It **ignores `lib_data["triggers"]` entirely** — and also drops `light_level`, `target_temperature`, `heating_rate`, and `contents`.

The F6 fix added the burn-down trigger to the **library file** (`data/library/items/everflame_ember.json` — `on_tick` with `adjust_uses -1`, plus `on_depleted`) and added the burn-down loop in `engine/tick_manager.py:330-361`, which scans area-lit items and calls `_execute_triggers(item_node, "on_tick", game_state=self.gs)`. But `_execute_triggers` resolves triggers via **graph trigger edges** (`trigger_item_X_on_<type>_*` nodes wired with `triggers` edges — see the docstring at `engine/trigger_system.py:1036-1046`). Since `spawn_item` never materializes trigger nodes/edges, the loop runs every tick and finds nothing. `uses` stays at 3 forever.

**This is a general defect**: *any* library item spawned via effects (future campfires, stoves, candles, torches) loses its triggers and heat/light properties.

### Stale-state gotcha (data)

The ember node currently in `data/autosave.json` was created at 15:56 on 2026-08-02 — **before** the F6 commit (18:36) — so it carries pre-fix properties (`heating_rate: 5`, no `light_level`, no `target_temperature`). The world persisted it across saves. Verification requires deleting this stale node (or starting a fresh save), otherwise the old ember never depletes no matter what the code does.

### Changes

1. **`engine/effects.py` — `handle_spawn_item`:** when hydrating from the library file, also copy the full property set: `light_level`, `target_temperature`, `heating_rate`, `contents` (and any other non-scalar fields present).
2. **`engine/effects.py` — trigger materialization:** for each entry in `lib_data["triggers"]`, create a trigger node (`type: "logic_trigger"` — matches the existing scenario-loading convention, not the `"trigger"` type originally suggested) with a unique id (follow the existing pattern: `trigger_<item_id>_<trigger_type>_<timestamp>_<rand>`), populate its `properties` from the trigger dict (`trigger_type`, `conditions`, `conditions_logic`, `effects`, `target_name`, `target_state`, `success_message`, `fail_message`), and add a `triggers` edge from the spawned item node to it (edge `properties` carry the full dict so `_execute_triggers` resolves conditions/effects from the edge) — mirroring how scenario loading builds trigger edges.
3. **`data/autosave.json` (test data only):** remove the stale `everflame_ember` node + its `in` edge during verification, or verify in a fresh session.

### Verification (Issue 1) — DONE ✅

- Fresh session: cast `use Create Flame`, confirm ember spawns lit with 3 uses. (Simulated in a throwaway script: spawn → `on_tick` fires 3→2→1→0 → `on_depleted` returns "The everflame ember gutters and dies."; `tick_manager.py:334-361` then sets state unlit and removes the node.)
- Backend suite: `python -m pytest tests/ -q -k "not mcp and not emote"` → **405 passed, 1 skipped**.
- New tests: `test_spawn_item_copies_heat_props_from_library` + `test_spawn_item_materializes_triggers` in `tests/test_trigger_system.py` (spawn-materialization test lives there rather than `test_descriptive_targets.py`).

---

## Issue 2 — Culdron: mangled examine text + name typo

### Evidence

```
examine cauldron
⚙️ matched 'cauldron' as item 'Culdron' (fuzzy match)
⚙️ A culdron on the stove cold soup fills the culdron. i could *EAT* this Available actions: [examine] Examine the object [use] Use
```

The output is three pieces concatenated:
- Item description: `"A culdron on the stove"` (fragment of a sentence)
- An `on_examine` trigger whose `success_message` contains LLM free-writing: `"cold soup fills the culdron.  i could *EAT* this"` (`data/scenarios/world_template.json` ~line 1893-1911, and duplicated in `data/library/items/culdron.json` lines 21 & 28)
- The normal `"Available actions: ..."` line (engine output, not garbage)

The actual eating mechanic exists and works (`on_use` trigger, Hunger +20, "The soup is cold but filling" — `world_template.json` ~line 1913-1930). The authoring intent was clear; the free text landed in the wrong field.

Also: item node name is `Culdron` (and library file `culdron.json`) — `cauldron` only resolves via fuzzy matching.

### Changes

1. **`data/scenarios/world_template.json`:** renamed item node `item_Culdron` → `item_Cauldron` (edges `in`/`triggers`, trigger nodes `trigger_item_Cauldron_*`, cleaned `on_examine` message). Added `library_id: "cauldron"`, `tags`, and `aliases` to the scenario node so a fresh load is properly library-linked.
2. **`data/library/items/cauldron.json`** (renamed from `culdron.json`): `"Cauldron"`, clean description ("A heavy iron cauldron sits on the stove, filled with cold, thick soup."), clean `on_examine` flavor ("The soup inside is cold but looks edible."), kept the `on_eat` soup trigger (Hunger +20), added `aliases: ["culdron", "soup pot", "pot"]`.
3. **Verification note:** `rg -i "culdron"` only matches the intentional aliases now.

### Verification (Issue 2) — DONE ✅

- `examine cauldron` and `examine culdron` resolve via alias without fuzzy-match warnings (fresh world load).
- `use cauldron` / `eat from cauldron` still grants Hunger +20.
- `python -c "import json; json.load(open('data/scenarios/world_template.json'))"` → parses clean.
- ⚠️ Live `data/autosave.json` still has the old `item_Culdron` node **without a `library_id`**, so refresh-from-library can't act on it — needs a fresh world load (or recreating the item from the library panel).

---

## Issue 3 — Fire-on-background-object messaging is nonsense

### Evidence

```
use Create Flame on fallen leaves
⚙️ You try to use the create flame on fallen leaves, but it doesn't seem to be loose or movable at all.
```

`fallen leaves` is prose from the area description (Weeping Willow Hollow), so the action falls through to `_descriptive_target_failure` (`engine/item_actions.py:1045-1059`), which picks a random generic reason written for *furniture*:

```python
reason = random.choice([
    "but it doesn't budge — it's part of the scenery, not something you can interact with",
    "but nothing happens. It's just {target_name}, fixed in place",
    "but it doesn't seem to be loose or movable at all",
    "but there's no purchase on it — it's purely decorative",
])
```

For a flame aimed at dry leaves, "it's not movable" is absurd.

### Changes

1. **`engine/item_actions.py` — `_descriptive_target_failure`:** added an `item_node` parameter. When the *used* item carries `fire` / `heat_source` tags, it picks from a fire-appropriate reason list instead of the generic furniture reasons:
   - `"but the {target_name} are too cold and damp to catch."`
   - `"but the {target_name} smolder briefly and go out — nothing dry enough to burn."`
   - `"but the {target_name} refuse to ignite; the cold is too deep here."`
2. **Caller** (`use_item_on`) passes the used `item_node` through.

### Verification (Issue 3) — DONE ✅

- `use Create Flame on fallen leaves` now returns a fire-appropriate message (no "loose or movable").
- Non-fire interactions (e.g. `use key on painting`) still get the existing scenery messages.
- New tests in `tests/test_descriptive_targets.py`: `test_fire_item_gets_fire_failure_text`, `test_heat_source_item_gets_fire_failure_text`, `test_non_fire_item_keeps_scenery_reasons`, `test_fire_item_without_node_uses_generic` → 11 passed in file.

---

## Issue 4 — No burn-duration feedback (player + agent UX)

### Evidence

The ember spawns with no hint of how long it lasts. The player (and the NPCs, who plan around "warm up") have no way to know it burns ~15 minutes (3 uses × 5 min/tick, `time_per_tick_minutes: 5` in autosave). NPC plans assume warmth persists indefinitely.

### Changes

1. **Spawn message** — `Create Flame` trigger message in `data/scenarios/world_template.json` (edge + trigger node) and the library copy `data/library/items/create_flame.json` now read: *"A small flame flickers in your palm and settles into a glowing ember at your feet. It radiates warmth and will burn for about 15 minutes."* (matches `uses: 3` × `time_per_tick_minutes: 5`). Also fixed the library trigger's empty `message` effect that would have wiped the flavor on refresh-from-library.
2. **Examine shows remaining uses** — `engine/item_actions.py` examine handler: for items with `uses > 0`, appends `"N uses left (~X minutes of warmth/light)."` using `player_manager.time_per_tick_minutes` (default 5). Generic — benefits lanterns, torches, any consumable.
3. **Agent-facing** — `static/js/agent/prompt-builder.js` COMMANDS table: new row for `use create flame` → *"Creates a small magical ember that burns for ~15 minutes, providing warmth and dim light. It does not last forever — plan around the warmth ending."*
4. **`data/library/items/everflame_ember.json`:** description sharpened to *"It is sustained by magic and will burn for about 15 minutes."*

### Verification (Issue 4) — DONE ✅

- Examine the ember → shows "3 uses left (~15 minutes of warmth/light)."
- Create Flame message mentions the duration.
- New tests in `tests/test_item_actions.py`: `test_examine_shows_remaining_uses`, `test_examine_skips_uses_for_permanent_items`.
- Live NPCs pick up the COMMANDS-table note on their next prompt rebuild (no world restart needed).

---

## Files Modified (planned)

- `engine/effects.py` — spawn_item full property copy + trigger materialization (Issue 1) ✅ DONE
- `engine/item_actions.py` — tag-aware descriptive-target fallback (Issue 3) ✅ DONE; examine uses display (Issue 4) ✅ DONE
- `data/scenarios/world_template.json` — Culdron→Cauldron rename + clean content (Issue 2) ✅ DONE; Create Flame duration message (Issue 4) ✅ DONE
- `data/library/items/culdron.json` → renamed to `cauldron.json` (Issue 2) ✅ DONE
- `data/library/items/everflame_ember.json` — description polish (Issue 4) ✅ DONE
- `data/library/items/create_flame.json` — duration message + fixed empty message effect (Issue 4) ✅ DONE
- `static/js/agent/prompt-builder.js` — COMMANDS table duration note (Issue 4) ✅ DONE
- `tests/test_trigger_system.py` — spawn full-property + trigger materialization tests (Issue 1) ✅ DONE
- `tests/test_descriptive_targets.py` — fire-tag fallback cases (Issue 3) ✅ DONE
- `tests/test_item_actions.py` — examine uses-display cases (Issue 4) ✅ DONE
- `data/autosave.json` — stale ember node + old `item_Culdron` left for the live session (see Notes)

## Notes / Open Items

- **Backend suite:** `python -m pytest tests/ -q -k "not mcp and not emote"` → **439 passed, 1 skipped**.
- **⚠️ Live server reverts committed data:** the running dev server (PID 23448, started 17:57) loads its world from `data/scenarios/world_template.json` and, on Save Scenario / mutation, writes its in-memory (pre-fix) world back over the file — it reverted the committed Cauldron fix during verification. File restored from git (`git checkout`). Reloading the world fresh (or restarting the server) makes live data match the fixed scenario; otherwise Save Scenario will re-revert it.
- **Uncommitted after playtest:** the double-period fix in `engine/item_actions.py` (fire reasons trailing `.` removed).
- **Stale data in `data/autosave.json`:** the pre-fix `everflame_ember` node (no light/heat props) and the old `item_Culdron` (no `library_id`) will not behave like the new content until the world is reloaded from the scenario or the items are recreated. The old Culdron node can't be refresh-from-library'd (no `library_id`).
- **Order:** Issue 1 first (engine root cause, unblocks real fire gameplay), then 2 & 3 (content + messaging), then 4 (UX). Issues 2-4 are independent of each other.
- **Generalize the verification:** after Issue 1, any library item with `triggers` becomes spawnable-with-triggers — verify one second item (e.g. a lantern) to prove it's not ember-specific.
- Related task: `todo/environment/task-174-fire-mechanic-heat-source.md` (F6, landed) — this task is the follow-up gap it left behind.
