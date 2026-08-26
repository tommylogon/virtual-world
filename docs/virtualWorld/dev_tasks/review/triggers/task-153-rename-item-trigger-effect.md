---
id: 153
title: Rename Item Trigger Effect
status: review
priority: high
created: 2026-08-02
updated: 2026-08-05
tags: [triggers, items, discovery]
---

# Rename Item Trigger Effect

**Status**: In Review — implemented 2026-08-05. `handle_rename` added to `engine/effects.py` (targets triggering item by default, `node_id`/`"self"` supported, name mirrored into `properties["name"]` for legacy readers, message templated). Frontend already serialized `params.name` correctly (no `node_id` field needed for default targeting). 4 new tests; suite 497 passed, 1 skipped.

## Summary

Implement the `rename` trigger effect so a trigger can change an item's name. This is the key enabler for the "unknown name" discovery flow: a character examines an item and it goes from a generic/unknown name (e.g. `photo`) to its true name (e.g. `photo of james`).

## Problem

`rename` is listed in `EFFECT_TYPES` (engine/trigger_system.py:55) and the trigger editor already renders a rename field (static/js/shared/trigger-editor.js:258,746), **but there is no `handle_rename` method in engine/effects.py**, so executing it returns `[Unknown effect type: rename]`. The frontend lies to the user — the editor lets you configure the effect but it silently fails at runtime.

## Implementation

### Backend effect handler

Add `handle_rename` to `engine/effects.py` — ✅ done 2026-08-05:

- Read `params.get("node_id")`; fall back to `item_node` (for `on_examine`, `on_use`, `on_take`, etc.)
- If `node_id == "self"`, target the triggering item node
- Set `target_node.name = new_name` (also set `properties["name"]` if the node stores the display name there)
- Optionally support `params.get("message")` as the result message
- Return the result message so it shows in the action output

### Frontend

Verify the existing rename field in the trigger editor serializes `params.name` correctly (it currently sends `eff.params.name = ...`), and that the effect renders for the right trigger types. — ✅ verified: `trigger-editor.js:259` sends `params.name`, `:748` renders the "New Name" input. No `node_id` field exists; default targeting covers the discovery flow.

## Files to Modify

1. `engine/effects.py` — add `handle_rename`
2. `static/js/shared/trigger-editor.js` — verify rename field wiring
3. `engine/trigger_system.py` — no change needed (`rename` already in EFFECT_TYPES)

## Testing

- [x] `on_examine` trigger with rename effect changes the item name in the graph — covered by unit tests (default + `node_id` + `self`)
- [ ] Name change persists after save/load — rename writes `node.name`; serialization persists it (same path as any name change). Live-verify when convenient.
- [x] Name change is reflected in area descriptions, examine output, and inventory — `node.name` is the canonical display/matching field
- [x] Unknown effect type error no longer appears — `handle_rename` registered
- [x] `node_id` targeting works for named nodes
- [x] Full suite: 497 passed, 1 skipped

## Related

- [[todo/characters/task-154-target-by-description-when-name-unknown|task-154: Target by description when name unknown]]
