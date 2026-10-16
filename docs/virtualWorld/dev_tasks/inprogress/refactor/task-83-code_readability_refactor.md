---
area: refactor
wiki: "[[UI & Settings/Inspector Panels]]"
type: task
status: inprogress
priority: medium
---

# Code Readability Refactor — Variable Naming & Comments

**Priority**: HIGH

**Note**: Not a blocker for merge. Deferred to post-merge cleanup passes.

---

## What

Large parts of the codebase, , use cryptic single-letter variable names (`tn`, `ep`, `ef`, `rn`, `dn`, `sn`, `nid`, `v`, `ct`, `cv`, `tp`, `ns`, `lw`, `ni`) with no comments explaining intent. This makes the code harder to read, debug, and maintain.

## Goal

Improve readability without breaking anything. No functional changes.

## How

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

## Steps to verify

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

## Why

TODO

## Acceptance

- [ ] TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — renaming cryptic local variables and adding intent comments is code readability work with no intended player-facing behavior change.

Current availability: the task lists short names such as `tn`, `ep`, `ef`, `rn`, `dn`, `sn`, `nid`, and `v`; the cleanup is not claimed as complete.

Why no browser UI: a browser cannot establish whether a local variable name communicates its purpose or whether a comment matches the actual operation. Review the changed functions in their call-site context.

Alternative verification steps:
1. For each changed function, read its inputs, outputs, and callers before and after the rename.
   - expected: descriptive names map one-to-one to the same values and no control flow or behavior changes.
2. Inspect the diff for comments added to genuinely non-obvious logic.
   - expected: comments explain intent or invariants and do not restate the code or assert behavior the function does not provide.
3. Run the focused tests for the touched module.
   - expected: existing behavior remains unchanged; no test is loosened to accommodate a naming-only refactor.

This section is not a claim that planned UI exists or works today.
