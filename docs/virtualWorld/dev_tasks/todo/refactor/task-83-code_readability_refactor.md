---
group: Tech Debt & Testing
wiki: "[[UI & Settings/Inspector Panels]]"
---
# Code Readability Refactor — Variable Naming & Comments

**Priority**: Low (ongoing)
**Status**: Ongoing — apply boy-scout rule when touching files for other reasons
**Note**: Not a blocker for merge. Deferred to post-merge cleanup passes.

---

## Summary

Large parts of the codebase, especially `virtual_world_engine.py` (~4600 lines), use cryptic single-letter variable names (`tn`, `ep`, `ef`, `rn`, `dn`, `sn`, `nid`, `v`, `ct`, `cv`, `tp`, `ns`, `lw`, `ni`) with no comments explaining intent. This makes the code harder to read, debug, and maintain.

## Goal

Improve readability without breaking anything. No functional changes.

## Approach

**Boy-scout rule** — clean up code as you touch it for features/bugfixes:

1. When modifying a function, rename its single-letter variables to descriptive names
2. Add a brief comment explaining what non-obvious blocks do
3. Never rename in isolation — always paired with a functional change to that area

## Worst Offenders (for reference when touching)

### `virtual_world_engine.py`

| Pattern | Example | Better Name |
|---------|---------|-------------|
| `tn` (target node) | `tn = self.graph.get_node(node_id)` | `target_node` |
| `ep` (effect params) | `ep = effect_params` | `params` |
| `ef` (effect type) | `ef === 'set_state'` | `effect_type` |
| `rn` (room node) | `rn = self.graph.get_node(target_id)` | `area_node` |
| `dn` (door node) | `dn = self.graph.get_node(way_id)` | `way_node` |
| `sn` (spawn node) | `sn = self.graph.get_node(spawn_id)` | `spawn_node` |
| `nid` (node id) | `nid = effect_params.get(...)` | `node_id` |
| `ct` (condition type) | `ct = condition.get("type")` | `cond_type` |
| `cv` (condition value) | `cv = condition.get("value")` | `cond_value` |
| `tp` (trigger type) | `tp = edge.properties...` | `trigger_type` |
| `ns` (new state) | `ns = effect_params...` | `new_state` |
| `lw` (locked with) | `lw = target_node...` | `required_key` |
| `ni` (normalized item) | `ni = item_node.name...` | `item_name` |

### `inspector.js` / `item-library.js`

| Pattern | Better Name |
|---------|-------------|
| `q('cls')` helper (single-letter query) | Keep as convention but comment at definition |
| `ef`, `ep`, `tp`, `ct`, `cv` (same as Python) | match engine naming |

## Guidelines for New Code

- No single-letter variable names (except loop indices `i`, `j`)
- Function-local temp vars are fine short (`key`, `door`, `item`) but not opaque (`tn`, `ep`)
- Add a comment for any block that isn't immediately obvious — especially trigger dispatch, effect execution, condition evaluation
- No action-at-a-distance: if a function depends on a subtle side effect, document it

## Verification

No functional changes — verify by:
1. Run `pytest tests/` before and after — same results
2. Reload the game and play through a basic interaction loop (look, move, take, use)
3. No change in behavior, only readability

## Files

- `virtual_world_engine.py` — primary target
- `app.py` — secondary target  
- `static/js/inspector.js` — tertiary
- `static/js/item-library.js` — tertiary
- Any other file touched during feature work