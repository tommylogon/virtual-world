---
id: 169
title: Add Tag to Target via Trigger
status: done
priority: low
created: 2026-08-02
tags: [triggers, tags, graph]
---

# Add Tag to Target via Trigger

## Summary

Add a trigger effect that adds (or removes) a tag on a target node, so a trigger can change how the world categorizes items/areas over time.

## Problem

Trigger effects can *target* items by tag (`target_tag` in engine/trigger_system.py:1267) and can `set_hidden`, `adjust_uses`, `rename`, etc. — but nothing can *add* or *remove* a tag. If a trigger should make something flammable, mark a room as discovered, or turn an item into a light source after use, there's no way to do it.

## Implementation

### Effects

- Add `add_tag` and `remove_tag` to `EFFECT_TYPES` (engine/trigger_system.py:45) and handlers in engine/effects.py:
  - `params: {"tag": "flammable", "target": "self" | node_id | target_tag}`
  - Add to / remove from `node.properties["tags"]` (handle both list and comma-string formats)
- Support targeting like the existing effects: `self` (triggering item), explicit `node_id`, or the `target_tag` fan-out

### Cascading uses

- After add_tag, other effects in the same trigger (or later triggers) can use tag-based targeting to hit the newly tagged item
- e.g. use item → add_tag "light_source" → lighting system picks it up

## Files to Modify

1. `engine/trigger_system.py` — `add_tag`/`remove_tag` added to EFFECT_TYPES ✅
2. `engine/effects.py` — `handle_add_tag`/`handle_remove_tag` handlers + `_resolve_effect_target`/`_normalize_tags` helpers ✅
3. `static/js/shared/trigger-editor.js`, `static/js/shared/trigger-graph.js`, `static/js/inspector.js`, `static/js/item-library.js` — effect options + tag/node param fields ✅

## Testing

- [x] add_tag adds the tag to the target item's properties
- [x] remove_tag removes it
- [x] Works with comma-string tag lists
- [x] Tag-based effect targeting sees the new tag immediately

**Implemented 2026-08-02** — `add_tag`/`remove_tag` effects target via `node_id`/`self`/`target_tag` fan-out and normalize both list and comma-string tag formats. Tests in `tests/test_trigger_system.py::TestAddRemoveTagEffect` (4 tests) — the integration test confirms tag-based targeting finds an item right after `add_tag` applies.

**Status: DONE** — moved to `done/triggers/`.

## Related

- [[todo/triggers/task-153-rename-item-trigger-effect|task-153: Rename effect]]
- [[review/items/task-98-tags-as-core-query-system|task-98: Tags as core query system]]
