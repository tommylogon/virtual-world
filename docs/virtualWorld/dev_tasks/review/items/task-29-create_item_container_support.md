---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---

# Create Item Modal: Container Contents Support

**Filed**: 2026-07-15
**Priority**: Low
**Status**: In Review — implemented (code-verified 2026-08-11). Create modal has 📦 Container checkbox + contents JSON + container/character targets (`create-modal.js:122-127/157-161/252-268`).

---

## Summary

The "Add New Item" create modal does not support setting items as containers with contents inside. Users must create the item, then separately edit it in the library to add container contents.

## Current State

In `main.js:openCreateModal()` (line 396-407), the item create form has fields for:
- Name
- Description
- Actions (3 checkboxes)
- Uses
- Weight
- Hidden

No field for container contents.

The item library editor (`item-library.js` line 453-460) already has container contents support:
```html
<h3>📦 Container Contents</h3>
<div id="lib-contents-list">...</div>
<button class="btn btn-sm btn-blue" onclick="VW.itemLib._addContentUi()">➕ Add Contained Item</button>
```

## Proposed Change

Add a collapsible "📦 Container Contents" section to the create item modal, using the same pattern as the library editor:

1. A "Contains items?" checkbox
2. When checked, show the contents editor with:
   - Add content button (opens the same item picker overlay)
   - List of contained items with remove button
3. The contents are serialized with the submit data

### Data Flow

The modal submit handler should include `contents` in the payload:

```js
result = {
  room: ...,
  name: ...,
  description: ...,
  actions: ...,
  uses: ...,
  weight: ...,
  hidden: ...,
  contents: JSON.parse(document.getElementById('item-contents-json')?.value || '[]')
};
```

### Backend

The `api.createItem()` must handle the `contents` field and create `contains` edges for each contained item.

## Audit

**Status**: Ready to test
**How to test**:
- Click "Create" → "Item". Verify a "📦 Container (contains items)" checkbox appears below the form.
- Check it, fill in JSON contents in the textarea that appears, submit. Verify the item is created with container contents visible in the inspector.
- Open the Item Library, create/edit an item — verify the "📦 Container Contents" section with add/remove UI exists.

## Files Affected

- `static/js/main.js` — add container contents section to create modal
- `templates/index.html` — may need additional HTML for contents editor
- `app.py` — ensure container contents are created as edges
