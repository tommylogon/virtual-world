---

group: Items & Crafting
wiki: "[[Library System/Library System Overview]]"
---
# Idempotent Sync to Library — Conflict-Aware Entity Sync

**Filed**: 2026-07-23 (updated 2026-07-31)
**Priority**: High
**Status**: Done

---

## What's Already Done

### DiffModal component
Built as part of task 115 (`static/js/shared/diff-modal.js`). Reusable modal with:
- Section-by-section comparison (`JSON.stringify` per section)
- Checkbox per section, pre-ticked if different
- "Update Selected" → saves only checked sections
- "Save as Duplicate" → auto-generates unique ID
- Returns result: `{ action: 'update', sections: [...] }` or `{ action: 'duplicate', name, id }`

### Single-item world→library sync (item-level)
`item-library.js:saveWorldItem()` — saves one world item to library:
- Reads `locked_fields` to preserve locked properties
- If no existing library entry → saves directly
- If conflict → shows `DiffModal` for section-by-section merge
- Supports duplicate with auto-generated ID

### Character save to library (no conflict handling)
`library-browser.js:saveWorldToCharacter()` — saves character to library:
- Builds entry from `worldState.players[name]` with embedded inventory
- Saves via `ApiClient.saveLibraryType('characters', ...)`
- **Silent overwrite** — no DiffModal, no conflict detection

---

## What's Left

### 1. Items: `syncAllWorldItems()` needs DiffModal

`item-library.js:1206` iterates all world items and syncs them to library, but:
- Silently overwrites existing library entries via `ApiClient.saveLibraryItem()`
- No conflict detection, no diff UI
- Should use the same DiffModal pattern as `saveWorldItem()` (batch with per-item prompts, or queue conflicts)

### 2. Character sync: wire DiffModal

`library-browser.js:420` needs the conflict flow:
- Check if library already has entry with same id or name
- If no conflict → save directly
- If conflict → compute section diffs, show DiffModal
- Sections for character sync: Basic, Personality, Description, Stats, Skills, Traits, Tags, Emotion, Relationships, Memories, World Knowledge, Behaviours, NPC Config, Items

### 3. Area sync: missing entirely

No world→area-library sync exists. Needs:
- Build entry from graph node + embedded items + exits (as templates) + triggers
- Check for existing library entry
- DiffModal conflict flow
- Sections: Basic (name, description, tags), Items, Exits, Triggers

### 4. "Sync from World" buttons per library tab

Library browser (`library-browser.js`) has 3 tabs (Items, Characters, Rooms):
- **Items tab** — button that calls `syncAllWorldItems()` with DiffModal
- **Characters tab** — button that syncs all `worldState.players` with individual DiffModals per character
- **Rooms tab** — button that syncs all `type: "area"` graph nodes with individual DiffModals

The global "📋 Sync to Library" toolbar button (`main.js`) should open the library browser and trigger the appropriate tab's sync.

### 5. Self-contained entries + import-as-library-items

When importing a self-contained character or room that has embedded item definitions:
- Each embedded item should also be saved as a standalone library entry (if not already present)
- This makes them reusable independently

### 6. Export templates, not connections

Area exits save as templates (descriptive + state fields + `target_room_hint` string), not graph connections. Already designed in the task — needs implementation in the area sync builder.

---

## Files to touch

| File | Change |
|------|--------|
| `static/js/item-library.js` | Add DiffModal to `syncAllWorldItems()` |
| `static/js/library-browser.js` | Add sync buttons per tab, wire DiffModal for characters/rooms |
| `static/js/main.js` | Update "📋 Sync to Library" to open library browser + trigger tab sync |
| `static/js/api.js` | May need generic save wrapper |
| `routes/library_routes.py` | Verify import handles inline items |
| — | New area sync builder (could be in library-browser.js or a new module) |

---

## Implementation Order

1. Add DiffModal to `syncAllWorldItems()` — replace silent overwrite with conflict-aware batch
2. Wire DiffModal into `saveWorldToCharacter()`
3. Build area sync builder + wire into DiffModal
4. Add "Sync from World" buttons to each library tab
5. On import, save embedded items as library entries
6. Update "📋 Sync to Library" toolbar button
