---
area: refactor
wiki: "[[UI & Settings/Inspector Panels]]"
type: task
status: inprogress
priority: medium
---

# Code Readability Refactor - Variable Naming & Comments

**Priority**: HIGH

**Note**: Not a blocker for merge. Deferred to post-merge cleanup passes.

---

## What

Large parts of the codebase use cryptic single-letter variable names (`tn`, `ep`, `ef`, `rn`, `dn`, `sn`, `nid`, `v`, `ct`, `cv`, `tp`, `ns`, `lw`, `ni`) with no comments explaining intent. This makes the code harder to read, debug, and maintain.

## Goal

Improve readability without breaking anything. No functional changes.

## How

1. When modifying a function, rename its single-letter variables to descriptive names
2. Add a brief comment explaining what non-obvious blocks do
3. Never rename in isolation - always paired with a functional change to that area

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
- Add a comment for any block that isn't immediately obvious - especially trigger dispatch, effect execution, condition evaluation
- No action-at-a-distance: if a function depends on a subtle side effect, document it

## Steps to verify

No functional changes - verify by:
1. Run `pytest tests/` before and after - same results
2. Reload the game and play through a basic interaction loop (look, move, take, use)
3. No change in behavior, only readability

## Files

- `virtual_world_engine.py` - primary target
- `app.py` - secondary target  
- `static/js/inspector.js` - tertiary
- `static/js/item-library.js` - tertiary
- Any other file touched during feature work

## Why

Cryptic abbreviations and single-letter local variables obscure developer intent, make debugging and codebase exploration significantly slower for agents and humans alike, and increase defect rates during refactoring. Standardizing on descriptive names and clarifying complex logic blocks with concise intent comments ensures long-term maintainability.

## Acceptance

- [ ] Cryptic single-letter variables in touched functions (e.g. irtual_world_engine.py, pp.py) are renamed to descriptive equivalents.
- [ ] Non-obvious logic blocks (trigger dispatch, condition matching, effect execution) carry brief intent comments.
- [ ] No behavioral or functional regressions introduced; targeted unit test suites continue to pass identically.

## Browser UI and intended live verification

Intended UI home: Not applicable - renaming cryptic local variables and adding intent comments is code readability work with no intended player-facing behavior change.

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

## Refactor discipline (applies to this task)

Applies to every refactor in this repo, per the 2026-10-16 card refresh:

1. **Dedup & reuse pass (mandatory).** While working, scan the touched concern and its
   neighbours for duplicate logic, parallel data homes, and near-identical helpers;
   consolidate onto one owner instead of copying. Prefer reusing an existing seam over
   creating a second one. Record any dedup decision in the move table / notes.
2. **Agent-experience & cleanliness (mandatory).** Name modules/files by concern (not
   by size), keep each under ~600 lines where the seam allows, add a one-line module
   docstring stating its owner and public surface, and ensure a fresh agent session can
   understand it without reading the host. No new abstraction unless an existing seam
   already represents the concept.
3. **No behaviour change unless the card says so.** Extraction and consolidation only;
   keep public imports/API stable and re-export moved members as thin delegates.
4. **One file/concern at a time**, verified with a targeted test selection (never the
   full suite by default, never -q).


## Standing Policy Note (2026-10-19)
- Rule 3 under How: Never rename in isolation - always paired with a functional change to that area.
- Line 13: Not a blocker for merge. Deferred to post-merge cleanup passes.
- This task functions as an ongoing repo policy rather than a standalone batch PR.
