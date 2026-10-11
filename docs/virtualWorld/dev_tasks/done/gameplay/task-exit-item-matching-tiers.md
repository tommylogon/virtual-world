---
group: Gameplay
---

# Exit & Item Matching Tiers: Cardinal, Area Name, Description Words, Way Handles

**Filed**: 2026-08-09
**Priority**: Medium
**Status**: In Review — implemented 2026-08-09, test_matching.py 55 passed (1 pre-existing skip), full suite 787 passed (only the 11 pre-existing give-item fixture failures), JS syntax clean.

---

## Summary

While testing Jane Two in Task 18, the agent tried `examine circular door` / `go north` and the engine failed to resolve them: `_match_exit_direction` only matched the exit **label** (the bracketed key, e.g. `Door 4`), and `_match_item_name` only matched name/alias — never description words. The code comment at `matching.py` even claimed "(or description words)" for items but the implementation never did it.

**Second round (this task's core)**: the Task 18 final door has `"direction": ""` on **all four** connection edges (autosave.json). That made it completely unreachable — the renderer printed `[]`, `go` couldn't resolve it (the old matcher skipped empty directions), and examine's candidate list showed `()`. The fix: a way is resolvable by any of its identity facets, with a derived handle when the direction label is missing.

## Changes

### 1. `engine/matching.py` — `way_handle` + `resolve_exit`

`way_handle(way_node, direction, area_name)` is the reference handle: the per-side `direction` label wins when set; otherwise a short name derived from the way node's name (current area's `"Name - "` prefix stripped, underscores → spaces) — `"Task 18 - final door"` → `"final door"`; falls back to `"door"`.

`resolve_exit(area_id, input)` replaces the label-only matcher and returns `(edge, way_node, handle)`:

1. Exact handle (`Door 4`, `final door`)
2. Cardinal (`north`)
3. Word-boundary substring on the handle
4. Way node name / target area name (`Task 18 - Room 1`, `the next room`)
5. Description words (`circular door`, `the circular door with the keycard slot`; distinctive ≥6-char word fallback)
6. **State word** (`locked`, `open`, `closed` — "examine locked door" resolves)
7. Fuzzy difflib

Empty-direction edges are **included** (the old `if not direction: continue` skip is gone). `_match_exit_direction` remains as a backward-compat wrapper returning the handle.

### 2. `engine/matching.py` — `_match_item_name` description tier

Wired the description words into the alias tier (matching the previously-stale comment): input's significant words scored against the item description, ≥2 word hits or a single distinctive (≥6 char) word resolves. `take pale petals` now finds the "Dried Flower Crown (Crushed)" whose description mentions "pale petals".

### 3. Renderers use the handle everywhere

- `engine/area_description.py` — `build_exits_for_area` keys exits by the handle (added `"label"` to exit_data); the look output prints `[final door] ...` instead of `[]`.
- `static/js/agent/prompt-builder.js` — JS-side `wayHandle` mirror in the "paths you can see" listing.
- `engine/item_actions.py` — examine's "Things you can examine" list shows ways by handle instead of a blank `() `.

### 4. Movement / examine / triggers use `resolve_exit`

- `engine/movement.py` (`move_to_area`, `toggle_way`) — resolve via `resolve_exit`, so `go final door` works even with empty directions.
- `engine/item_actions.py` — examine + use_on target resolution via `resolve_exit`.
- `engine/trigger_system.py` + `virtual_world_engine.py` — `resolve_exit` facade, `_match_exit_direction` kept for compat.

### 5. Prompt consolidation (`static/js/agent/prompt-builder.js`)

The ACTION STRUCTURE + SPEECH & VOLUME blocks were duplicated in the **system prompt** AND in every per-turn user message. Kept the (improved) rules in the system prompt, stripped them from `buildReactionPrompt` and `buildResultReactionPrompt`, which now point at the system rules and keep only phase-specific instructions + their JSON schema. Also fixed: blank lines before `=== WITNESSED ===` and `=== I REMEMBER ===`; `reactContext` now carries `[Tick N]` + area name (`agent-engine.js`).

## Verification

- `tests/test_matching.py` — TestExitMatchingTiers (cardinal, way-name, target-area, description, state word, non-match), TestItemDescriptionMatching, and **TestEmptyDirectionWayHandle** (handle derivation + resolve by handle/name/area/description/state with empty-direction edges).
- Full suite: 787 passed, only the 11 pre-existing `TestUnifiedEffectTargeting`/`TestGiveItemEffect` fixture failures (`set_active_player` ValueError, unrelated).
- Gotcha fixed mid-flight: `build_exits_for_area` must not read `self.player_manager.current_area` (it re-enters `build_exits_for_area` via `legacy_compat.current_area` → RecursionError) — the `area_name` param is used instead.
