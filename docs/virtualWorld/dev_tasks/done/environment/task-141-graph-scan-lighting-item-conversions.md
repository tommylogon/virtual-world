---
group: Environment & Climate
---
# Task 141: Graph-scan lighting — convert remaining item JSONs + cleanup

## Goal

Replace the dual system of `player.item_statuses` + `effect_target/effect_amount` toggle tracking with a single emergent approach: items hold their own state (`current_state: "lit"` / `"unlit"`) and the lighting engine scans the graph to calculate room brightness.

**Engine (steps 1–5) is already done.** What remains is converting item JSONs that still use legacy patterns, removing stale code, and covering gaps.

---

## Status: what's done

| Step | Component | Status |
|------|-----------|--------|
| 1 | `engine/lighting.py` — `get_item_light_contribution()` graph scan | ✅ Done |
| 2 | `engine/toggleable_items.py` — simplified to state-flip only | ✅ Done |
| 3 | `engine/tick_manager.py` — tick drain via graph scan | ✅ Done |
| 4 | `engine/item_actions.py:use_item()` — toggleable redirect | ✅ Done |
| 5 | `engine/effects.py:handle_set_state()` — defaults to item_node | ✅ Done |
| 6 | Legacy `item_statuses` cleanup | ✅ Done (removed from player.py and routes/players.py) |
| 7 | Item JSON conversions | ✅ Done (2026-08-02) |
| 8 | Legacy `effect_target: room:light` parallel path removed | ✅ Done |
| 9 | `items_registry` copies light/heat/sound props | ✅ Done |
| 10 | `get_item_light_contribution` tests | ✅ Done (7 tests) |

**Updated**: 2026-08-02

**Status: DONE** — moved to `done/environment/`. Remaining steps A–F below are all implemented.

---

## Remaining work

### A. Convert item JSONs to toggleable/graph-scan pattern

Each item must have:
- `light_level` (string enum or number 0–100)
- `current_state` (`"unlit"` by default)
- `toggleable` tag (if player can turn on/off)
- `on_toggle_on` / `on_toggle_off` / `on_depleted` triggers
- `on_tick` → `adjust_uses` for fuel drain while lit (if finite uses)
- `heat_source` tag + `target_temperature`/`heating_rate` (if it emits heat)

#### Items using legacy `effect_target: room:light:+N` (old system, no toggleable)

| File | Uses | light_level | heat_source | Problem |
|------|------|-------------|-------------|---------|
| `oil_lamp.json` | 20 | `"dim"` | ✅ | Has BOTH `light_level` and `effect_amount` — dual path |
| `candle_attic.json` | 5 | ❌ missing | ❌ | No `light_level`, uses `room:light:+25` |
| `silver_candle.json` | 15 | ❌ missing | ❌ | No `light_level`, uses `room:light:+50` |
| `candle_stub.json` | 1 | ❌ missing | ❌ | No `light_level`, uses `room:light:+15` |
| `phone.json` | -1 | ❌ missing | ❌ | No `light_level`, uses `room:light:+35` |

#### Items using `on_use` → `set_environment` (not toggleable)

| File | Uses | Current state | Problem |
|------|------|---------------|---------|
| `lamp.json` | -1 | `"unlit"` | `on_use` → `set_environment light:70`. Needs `toggleable`, `light_level`, toggle triggers |
| `desk_lamp.json` | -1 | `"unlit"` | Same as lamp.json |

#### Items missing `light_level` or `toggleable`

| File | light_level | toggleable | Notes |
|------|------------|-----------|-------|
| `unlit_torch.json` | ❌ missing | ❌ missing | Has `heat_source` |
| `candle_24cfcc0e.json` | ❌ missing | ❌ missing | Bare: uses:8, only description |
| `bundle_of_candles.json` | ❌ missing | ❌ missing | Uses `on_light` trigger type |
| `light_stone.json` | ❌ missing | ❌ missing | `current_state: "normal"`, only message triggers |
| `everflame_ember.json` | ❌ missing | ❌ missing | `heat_source`, uses:1, only on_use message |

### B. Remove stale legacy code

- `player.py:113` — `self.item_statuses = {}` still initialized (never read by engine)
- `routes/players.py:281` — still deserializes `item_statuses`
- `engine/item_actions.py:547-569` — legacy `effect_target`/`effect_stat`/`effect_amount` handler still runs for non-toggleable items (creates parallel lighting path)

### C. Frontend: graph overlay ignores item lights

`static/js/graph/network-manager.js:392-443` (`_computeAmbientLight()`) only reads `environment.light` from area nodes — does **not** account for lit items in the area. Should either add item contributions or mark as visual-only.

### D. Frontend: library editor missing `light_level` field

The world item inspector (`item-view.js:286-296`) already shows `light_level` when `light_source` tag is present. The library editor (`item-library.js`) is missing it.

### E. Missing test coverage

`get_item_light_contribution()` in `lighting.py:41` has **zero** test coverage. Should add tests for:
- Lit item in area contributes light
- Lit item in character's inventory contributes light
- Unlit item doesn't contribute
- Item without `light_source` tag doesn't contribute
- Stacking multiple lit items
- Clamping at 100

### F. flashlight.json missing fuel drain

`flashlight.json` has no `on_tick` → `adjust_uses` trigger, so it never drains battery after the initial use-decrement in `toggleable_items.py`.

---

## Files to touch

| File | Change |
|------|--------|
| `data/library/items/oil_lamp.json` | Remove legacy `effect_amount`/`effect_target`, add `toggleable` + triggers |
| `data/library/items/candle_attic.json` | Convert to toggleable pattern |
| `data/library/items/silver_candle.json` | Convert to toggleable pattern |
| `data/library/items/candle_stub.json` | Convert to toggleable pattern |
| `data/library/items/phone.json` | Convert to toggleable pattern |
| `data/library/items/lamp.json` | Convert to toggleable pattern |
| `data/library/items/desk_lamp.json` | Convert to toggleable pattern |
| `data/library/items/unlit_torch.json` | Add `light_level`, `toggleable`, triggers |
| `data/library/items/candle_24cfcc0e.json` | Add `light_level`, `toggleable`, triggers |
| `data/library/items/bundle_of_candles.json` | Add `light_level`, `toggleable`, triggers |
| `data/library/items/light_stone.json` | Add `light_level`, `toggleable`, triggers |
| `data/library/items/everflame_ember.json` | Add `light_level`, `toggleable`, triggers |
| `data/library/items/flashlight.json` | Add `on_tick` → `adjust_uses` trigger |
| `player.py` | Remove `item_statuses` field |
| `routes/players.py` | Remove `item_statuses` serialization |
| `engine/item_actions.py` | Remove legacy `effect_target` handler (lines 547-569) |
| `static/js/graph/network-manager.js` | Add item light contributions to `_computeAmbientLight()` |
| `static/js/item-library.js` | Add `light_level` dropdown when `light_source` tag present |
| `tests/test_lighting.py` | Add tests for `get_item_light_contribution()` |

---

## Verification

1. Toggle each converted item on/off → correct light contribution
2. Drop/pick up a lit lamp → room lighting adjusts immediately
3. Area transitions → no stale deltas
4. Per-tick fuel drain → depleted auto-off → `on_depleted` fires
5. Serialization round-trip → state preserved (already on graph nodes)
6. Graph overlay shows accurate light level
7. Library editor shows `light_level` for `light_source` items
