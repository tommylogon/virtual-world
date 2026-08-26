---
group: Items
wiki: "[[UI & Settings/Inspector]]"
---

# Auto-create Base Trigger When Allowed Action is Enabled

**Filed**: 2026-08-16  
**Priority**: Low  
**Status**: Done — implemented 2026-08-16. World-item inspector only: toggling an allowed action **on** auto-creates a base empty `on_<action>` trigger; toggling **off** never removes triggers; idempotent (no duplicate on re-enable). Implemented via `_ensureActionTrigger()` in `static/js/inspector/item-view.js`. E2E-verified in-browser (world item: enable `use` → `on_use` empty trigger created; re-enable → still 1; disable → action removed, trigger persists). Move to review/. Server's Flask auto-reload reset the world mid-test, so the throwaway test item/trigger were created, verified, and cleaned up via API.

---

## Problem

When a designer enables a new allowed action on an item via the **world item inspector** (`_toggleAction` in `static/js/inspector/item-view.js`), there is no corresponding `on_<action>` trigger. The action is advertised to players/agents but has no hook to author effects — the designer must manually remember to add a trigger.

## Goal

When an allowed action is **toggled on** in the world item inspector, also create a **base empty trigger** for that action (e.g. enabling `use` creates an `on_use` trigger with no effects). When an action is **toggled off**, do **NOT** remove any triggers — a designer may have authored effects under the action's trigger and wants to keep them.

## Behavior

- Only the **world item inspector** (placed/item nodes in the graph) — NOT the Item Library editor.
- On toggle-on for action `X`, create a trigger edge on the item node with `trigger_type = on_<X>`, `effects: []` (base empty).
- Idempotency: if a trigger for `on_<X>` already exists on the node, do not create a duplicate.
- On toggle-off: only the `actions` list changes; trigger edges are untouched.

## Implementation

- `static/js/inspector/item-view.js` — extend `_toggleAction(nodeId, action)`:
  - when the action is being added, call a helper `_ensureActionTrigger(nodeId, action)` that checks existing `triggers` edges for `trigger_type: on_<X>` and creates the empty trigger (logic_trigger node + edge) if missing. Mirror the node/edge creation pattern already in `static/js/inspector/trigger-helpers.js` (e.g. `_openGraphEditor`'s persistCompiled create branch) / `inspector.js _addTriggerToNode`.
- No backend changes required — the graph edge/node API already exists.

## Verification

- [ ] Enable `use` on an item in the world inspector → an `on_use` trigger (empty) appears in the inspector's Trigger list
- [ ] Enabling a second time does not stack duplicate triggers
- [ ] Disable `use` → the `on_use` trigger stays
- [ ] clicking the trigger opens the editor (existing edit path works)