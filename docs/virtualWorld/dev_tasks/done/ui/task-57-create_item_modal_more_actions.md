# Create Item Modal: More Actions and Trigger Support

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: Done — verified 2026-08-03. 14-action checkbox grid + collapsible triggers section in static/js/ui/create-modal.js.

---

## Summary

The "Add New Item" create modal currently only shows 3 action checkboxes (examine, take, use). Users need more action options and the ability to add triggers directly when creating an item.

## Current State

In `main.js:openCreateModal()` (line 404), the item form has:

```html
<label>Actions</label>
<div class="checkbox-row">
  <label><input type="checkbox" class="act-chk" value="examine" checked> examine</label>
  <label><input type="checkbox" class="act-chk" value="take" checked> take</label>
  <label><input type="checkbox" class="act-chk" value="use" checked> use</label>
</div>
```

Only 3 actions. No triggers. No way to add container contents.

## Proposed Change

### Expand Actions

Use the same `ALL_ACTIONS` array from the inspector (`inspector.js` line 613) to render all available actions:

```js
['examine', 'take', 'use', 'open', 'close', 'eat', 'drink', 'read', 'light', 'activate', 'equip', 'unequip', 'throw', 'break']
```

Render as a compact checkbox grid (2-3 columns) with consistent styling.

### Add Triggers Section

Add a basic trigger editor to the create modal, using the same trigger overlay system from `item-library.js:_addTrigger()`. This allows users to add triggers when first creating the item, rather than having to:
1. Create the item
2. Find it in the library
3. Edit triggers separately

### Implementation Approach

**Option A (Recommended):** Add a "⚡ Triggers (optional)" collapsible section to the create modal that imports the trigger overlay from the library module.

**Option B:** After item creation, redirect the user to the library editor with the new item selected and triggers ready to add.

Option A is preferred because it's a single workflow.

## Files Affected

- `static/js/main.js` — expand action checkboxes, add trigger section to create modal
- `templates/index.html` — may need additional modal HTML for triggers
