# DiffModal — Per-Item / Per-Property Upgrade

The conflict-resolution modal for world-to-library sync now supports **per-entry**
selection, not just whole-section clobbering. Instead of "everything or nothing"
per category, you can pick individual memories, items, relationships, conditions,
vitals, decay rates, and equipped slots to carry across in either direction.

## Where it lives

- static/js/shared/diff-modal.js — the modal itself (rendering + result shape).
- static/js/library-browser.js — **save** direction (world → library).
- static/js/inspector/agent-view.js — marks scriptable character sections.
- static/js/shared/template-sync.js — **refresh** direction (library → world).
- routes/library_ops.py — backend refresh apply (_refresh_character).

## What changed

### 1. Sections can opt into per-entry granularity

A section definition may set perEntry: true. When set (and the data is eligible —
object-with-entries, or an array whose entries each carry id or name), the
DiffModal renders that section as an **expandable group** instead of a one-line
diff cell:

- A **whole-category checkbox** + an expand/collapse chevron.
- An **N chg / M add / K rem** summary in the header.
- One **row per entry**, each with its own checkbox, a +/-/~ status badge, and the
  library→world value comparison.
- A **Select all N entries** toggle.

### 2. Status badges

| Badge | Meaning |
|-------|---------|
| = | identical on both sides |
| + | only in the source / copy-over side |
| - | only on the other side (removed) |
| ~ | differs, both present |

### 3. Direction-aware pre-selection

- **Save (world → lib):** entries changed or only-in-world come pre-selected
  (the data you carry into the library).
- **Refresh (lib → world):** entries changed or only-in-library come pre-selected
  (the data you copy onto the world).

The whole-category checkbox still exists for when you want to clobber the entire
section, exactly as before.

## Result shape

DiffModal.show(...) now returns both selection forms:

    {
      action: 'update' | 'duplicate',
      sections: ['personality', 'description', ...],   // whole-section keys
      entries: { memories: ['aa1', 'dd8'],             // per-entry keys
                 relationships: ['jake'],
                 equipped: ['katana'] }
    }

A section selected wholesale appears in sections and is NOT repeated in entries.
A partially-selected per-entry section appears only in entries.

## Entry identifiers

| Section kind | Identifier |
|--------------|-----------|
| object-of-objects (relationships, conditions, equipped, vitals, decay_rates) | the object key (e.g. jake) |
| array-of-objects (memories, inventory) | id when present, else name |

## Apply logic

DiffModal.applyEntrySelection(target, source, selKeys) merges ONLY the selected
entries from source onto target, preserving everything else:

- Array entries match by id/name and are updated in place or appended.
- Dict (object) entries are matched by key and updated/added.

Callers order the args per direction:

- Save: applyEntrySelection(libValue, worldValue, keys)
- Refresh: applyEntrySelection(worldValue, libValue, keys)

The same helper exists server-side as _apply_entry_selection in
routes/library_ops.py, used by /api/library/refresh-to-world when the request
carries an entries body.

## Character sections that are now per-entry

memories, relationships, vitals, decay_rates, conditions, equipped, and inventory
(items). Scalar sections (description, emotion, stats, ...) remain whole-section.

## Example flows

**Save only 3 changed memories, keep the rest in the library:**
1. Open the character editor → Save to Library.
2. Expand Memories; uncheck whole-category; check the 3 you want.
3. Update Selected. The other memories in the library entry are left untouched.

**Refresh two relationships from the library onto a world NPC:**
1. In the character inspector → Refresh from Library → the DiffModal opens with
   lib→world direction.
2. Expand Relationships; check the two you want copied from the library.
3. Update Selected. Only those two relationship entries overwrite the NPC.

## Tests

pytest tests/ -k 'library or refresh' covers the backend refresh + save
round-trips. DiffModal.applyEntrySelection is exercised for both directions via
the library save/sync paths in library-browser.js.
