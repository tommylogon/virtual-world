---
group: Items & Crafting
---
# Library Conflict-Aware Sync — Phase 1: Items + Ways

## Problem
"Save to Library" does a silent overwrite. If you save a world item that happens to share a name with a library entry, the library version gets replaced entirely — tags, triggers, properties and all. This is how the hand_lamp lost its proper definition.

## Solution
Replace silent overwrite with a diff modal (same pattern as graph-editor's selective import at `graph-editor/js/ui.js:3700-3780`). Sections that match are skipped; differing sections are highlighted green; user picks which to update or saves as a duplicate.

## Status: ✅ Done — moved to review/

## Phase 1 Scope (this task)

Items and ways only. Characters and rooms come in Phase 2 (see task-95).

### Backend
- `routes/library_routes.py` — added `'ways'` to `REGISTRY_TYPES`. Existing generic CRUD at `/api/library/ways` handles listing, saving, and deleting way entries. No separate endpoint needed.
- Way entries stored in `data/library/ways/<id>.json`

### Frontend

**1. `static/js/shared/diff-modal.js`** — reusable diff modal component
```
DiffModal.show(current, incoming, sections, options)
  → returns null (cancel) | { action: 'update', sections: [...] } | { action: 'duplicate', name, id, sections }
```
- Section-by-section comparison using stringified equality
- Green highlight on differing sections
- Checkbox per section, pre-ticked if different
- "Update Selected" button → merge checked sections
- "Save as Duplicate" → prompt for new name, generate lowercase_id
- **Bug fix**: modal-window was sibling of modal-overlay (black screen). Now appended as child so flexbox centering works.

**Item sections:** name, description, actions, uses, weight, state, defense, damage, insulation, resistances, tags, triggers, contents

**Way sections:** name, description, state, pass_message, needs_open, auto_close, see_through, tags, triggers

**2. `item-library.js:saveWorldItem()`** — refactored with DiffModal
- Uses `ApiClient.getLibraryType('items')` instead of broken `/api/registry/items/<id>` individual fetch
- No existing entry → saves directly (still respects `locked_fields`)
- Existing entry → shows DiffModal with 13 flat sections
- "Update Selected" → merge checked sections, `locked_fields` enforced (library values win for locked fields)
- "Save as Duplicate" → new entry with world data

**3. `way-view.js`** — added library save
- `_saveToLibrary(nodeId)` method + green button in footer
- Wraps way properties + triggers → saves to `/api/library/ways`
- Same DiffModal flow when entry already exists

### Known issues
- `syncAllWorldItems()` still does silent overwrite (planned for Phase 3)
- `_saveToLibrary()` duplicate case doesn't apply `locked_fields` (ways don't use them yet)
- No character/room library diff yet (Phase 2)

### Files changed

```
virtual_world/
├── static/js/
│   ├── shared/diff-modal.js           ← bugfix: modal→overlay nesting
│   ├── item-library.js                ← refactored saveWorldItem with DiffModal
│   └── inspector/way-view.js          ← added save button + _saveToLibrary
├── routes/
│   └── library_routes.py              ← added 'ways' to REGISTRY_TYPES
└── templates/
    └── index.html                     ← already loaded diff-modal.js
```
## Phase 2: Character + Room sync (task-95)

Not in scope here. See task-95 for full spec.
