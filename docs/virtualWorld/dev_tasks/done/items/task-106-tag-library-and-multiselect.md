---
group: Tech Debt & Testing
wiki: "[[Library System/Library System Overview]]"
---
# Task 106: Tag Library + Searchable Tag Multiselect System

**Status**: ✅ Done (2026-08-02)  
**Priority**: High  
**Filed**: 2026-07-26  
**Updated**: 2026-08-02  

---

## Summary

Tags are currently freeform strings scattered across items, characters, and rooms with no central registry, no autocomplete, and no consistent UI. Every place that edits tags has its own duplicated input pattern. This task creates a proper tag library and replaces all tag inputs with a searchable multiselect component.

**Why this matters:** Tags are becoming a core query system (see task-98 Phase 1). Triggers use `target_tag`, agents will use `interest_tags`, and the `find` command will search by tag. Without a library, tags drift — "flammable" vs "flamable", "magic" vs "magical" — and queries break silently.

---

## Phase 1: Tag Library (Backend)

### 1.1 Create `data/library/tags/` directory

Per-file JSON registry, same pattern as traits/conditions/behaviours:

```json
// data/library/tags/flammable.json
{
  "id": "flammable",
  "name": "Flammable",
  "description": "Can be set on fire and burn",
  "category": "physical",
  "color": "#ff6600",
  "icon": "🔥",
  "applies_to": ["items"],
  "examples": ["wooden chair", "curtains", "paper"]
}
```

```json
// data/library/tags/magic.json
{
  "id": "magic",
  "name": "Magic",
  "description": "Magical or enchanted",
  "category": "essence",
  "color": "#9944ff",
  "icon": "✨",
  "applies_to": ["items", "characters", "rooms"],
  "examples": ["enchanted sword", "wizard", "arcane chamber"]
}
```

Fields:
- `id` — unique slug (lowercase, underscores)
- `name` — display name
- `description` — what this tag means
- `category` — grouping category (physical, essence, location, state, faction, etc.)
- `color` — hex color for UI badge
- `icon` — emoji icon for UI badge
- `applies_to` — which entity types this tag is valid for: `["items"]`, `["characters"]`, `["rooms"]`, or combinations
- `examples` — example usages for documentation/autocomplete hints

### 1.2 Add `tags` to `REGISTRY_TYPES` in `routes/library_routes.py`

Add `'tags'` to the `REGISTRY_TYPES` list so it gets the generic CRUD routes automatically.

### 1.3 Add `tags` tab to `LibraryBrowser` in `static/js/library-browser.js`

- Add `tags` to the data object, `_getEditorConfigs()`, and all the id/count/search maps
- Editor fields: name, description, category (select), color (color picker or text), icon (text), applies_to (multiselect checkboxes: items/characters/rooms), examples (textarea, one per line)
- Icon: `🏷️`

### 1.4 Tag validation endpoint

New route `GET /api/tags/validate` that checks a list of tag strings against the library and returns unknown/misspelled tags with suggestions:

```json
GET /api/tags/validate?tags=flammable,flamable,magik
→ {
  "valid": ["flammable"],
  "unknown": [
    {"tag": "flamable", "suggestion": "flammable"},
    {"tag": "magik", "suggestion": "magic"}
  ]
}
```

Uses simple Levenshtein or prefix matching for suggestions.

### 1.5 Tag autocomplete endpoint

New route `GET /api/tags/search?q=flam` that returns matching tags from the library:

```json
GET /api/tags/search?q=flam
→ [
  {"id": "flammable", "name": "Flammable", "icon": "🔥", "color": "#ff6600"},
  {"id": "flame_retardant", "name": "Flame Retardant", "icon": "🛡️", "color": "#3366ff"}
]
```

### Files to touch (Phase 1)
- `data/library/tags/` — new directory with seed files
- `routes/library_routes.py` — add `'tags'` to REGISTRY_TYPES
- `routes/tags.py` — new route module for validate + search endpoints
- `routes/__init__.py` — register new route module
- `static/js/library-browser.js` — add tags tab

---

## Phase 2: Searchable Tag Multiselect Component (Frontend)

### 2.1 Create `static/js/shared/tag-multiselect.js`

A reusable UI component class `TagMultiselect` that replaces all current tag inputs:

```
┌─────────────────────────────────────┐
│ 🔥 flammable ✕  ✨ magic ✕  📦 metal ✕  │
│ [type to search...            ▼]    │
│ ┌─────────────────────────────┐     │
│ │ 🔥 Flammable    (physical)  │     │
│ │ ✨ Magic        (essence)   │     │
│ │ 📦 Metal        (physical)  │     │
│ │ 🪵 Wooden       (material)  │     │
│ └─────────────────────────────┘     │
└─────────────────────────────────────┘
```

**Features:**
- Text input with debounced autocomplete dropdown (queries `/api/tags/search`)
- Selected tags shown as colored badges with ✕ remove button
- Dropdown shows icon + name + category, filtered by typed text
- Click dropdown item to add, click ✕ to remove
- Keyboard navigation: up/down arrows, enter to select, escape to close
- If user types a tag that doesn't exist in library, show a "+ Create 'tagname'" option at bottom of dropdown
- Optional `applies_to` filter (e.g., only show tags that apply to items)
- Emits `change` event with current tag list

**API:**
```js
new TagMultiselect(containerElement, {
  tags: ['flammable', 'magic'],     // initial tags
  appliesTo: 'items',                // optional filter
  allowNew: true,                    // allow creating new tags on the fly
  placeholder: 'Search tags...',
  onChange: (tags) => { ... }        // callback when tags change
})
```

### 2.2 Replace tag inputs in Inspector views

**`static/js/inspector/item-view.js`** — `_renderTagsSection()` at ~line 232:
- Replace the current text input + badge pattern with `TagMultiselect`
- Filter: `appliesTo: 'items'`

**`static/js/inspector/agent-view.js`** — `_addTag()` at ~line 370:
- Replace the current text input + badge pattern with `TagMultiselect`
- Filter: `appliesTo: 'characters'`

**`static/js/inspector/room-view.js`** — if it has tag editing:
- Replace with `TagMultiselect`
- Filter: `appliesTo: 'rooms'`

### 2.3 Replace tag inputs in Library Browser

**`static/js/library-browser.js`** — character and room editors:
- Replace the `tags (comma-separated)` text field with `TagMultiselect`
- On save, serialize as comma-separated or array

### 2.4 Replace tag input in Trigger Editor

**`static/js/shared/trigger-editor.js`** — if it has tag fields for `target_tag`:
- Replace with `TagMultiselect` (single-select mode for `target_tag`)

### Files to touch (Phase 2)
- `static/js/shared/tag-multiselect.js` — new component
- `static/js/inspector/item-view.js` — replace tag input
- `static/js/inspector/agent-view.js` — replace tag input
- `static/js/inspector/room-view.js` — replace tag input (if exists)
- `static/js/inspector/helpers.js` — can remove `addTag`/`removeTag` (replaced by component)
- `static/js/library-browser.js` — replace tag text fields
- `static/js/shared/trigger-editor.js` — replace tag fields
- `templates/index.html` — add script tag for new module

---

## Phase 3: Tag Propagation & Validation

### 3.1 Auto-register new tags

When a tag is added to an item/character/room that doesn't exist in the library:
- If `allowNew: true`, create a minimal entry in the tag library automatically
- Fields: `id` (slug), `name` (humanized), `description` (empty), `category` ("custom"), `color` (auto from hash), `icon` ("🏷️"), `applies_to` (from context)
- This keeps the library self-populating without manual data entry

### 3.2 Tag validation on save

When saving an item/character/room via API:
- Backend validates all tags against the library
- Returns warning for unknown tags (but doesn't block save)
- Logs warning: `"Tag 'flamable' not in library — did you mean 'flammable'?"`

### 3.3 Tag usage stats

New route `GET /api/tags/stats` that returns:
```json
{
  "flammable": { "items": 12, "characters": 0, "rooms": 3 },
  "magic": { "items": 8, "characters": 2, "rooms": 5 },
  ...
}
```

Useful for seeing which tags are actually used, and for cleaning up unused tags.

### Files to touch (Phase 3)
- `routes/tags.py` — add stats endpoint, validation logic
- `engine/serialization.py` — add tag validation on save
- `routes/helpers.py` — add tag auto-registration helper

---

## Phase 4: Tag Library UI Polish

### 4.2 Tag color coding in graph view

Tags with defined colors show as colored dots/badges on graph nodes:
- Small colored circles on item/character/room nodes indicating their tags
- Hover shows tag names
- Filter graph by tag (click tag to highlight all nodes with that tag)

### Files to touch (Phase 4)
- `static/js/graph/` — add tag color indicators

---

## Seed Data

Initial tag library entries to create:

### Physical
| ID | Name | Icon | Color |
|----|------|------|-------|
| flammable | Flammable | 🔥 | #ff6600 |
| metal | Metal | ⚙️ | #888888 |
| wooden | Wooden | 🪵 | #8B4513 |
| glass | Glass | 🫙 | #66ccff |
| stone | Stone | 🪨 | #666666 |
| cloth | Cloth | 👕 | #cc9966 |
| liquid | Liquid | 💧 | #3399ff |
| food | Food | 🍎 | #ff4444 |
| organic | Organic | 🌿 | #44aa44 |
| paper | Paper | 📄 | #eeeeee |

### Essence
| ID | Name | Icon | Color |
|----|------|------|-------|
| magic | Magic | ✨ | #9944ff |
| cursed | Cursed | ☠️ | #660066 |
| blessed | Blessed | ⛪ | #ffdd00 |
| ghostly | Ghostly | 👻 | #aaaaff |
| enchanted | Enchanted | 🔮 | #cc66ff |
| eldritch | Eldritch | 👁️ | #440044 |

### Location / Environment
| ID | Name | Icon | Color |
|----|------|------|-------|
| indoor | Indoor | 🏠 | #cc8844 |
| outdoor | Outdoor | 🌳 | #44aa44 |
| exterior | Exterior | 🌤️ | #4488ff |
| dark | Dark | 🌑 | #333333 |
| wet | Wet | 💦 | #3399ff |
| cold | Cold | ❄️ | #aaddff |
| hot | Hot | 🌡️ | #ff4400 |
| noisy | Noisy | 🔊 | #ffaa00 |
| quiet | Quiet | 🤫 | #aaddaa |

### Faction / Affiliation
| ID | Name | Icon | Color |
|----|------|------|-------|
| faction_guard | Guard | 🛡️ | #0044aa |
| faction_thief | Thief | 🗡️ | #444444 |
| faction_noble | Noble | 👑 | #ffcc00 |
| faction_cultist | Cultist | 🔮 | #660066 |
| faction_merchant | Merchant | 💰 | #44aa44 |

### State / Status
| ID | Name | Icon | Color |
|----|------|------|-------|
| broken | Broken | 💔 | #cc0000 |
| locked | Locked | 🔒 | #888800 |
| hidden | Hidden | 👁️ | #666688 |
| trap | Trap | ⚠️ | #ff0000 |
| container | Container | 📦 | #cc8844 |
| weapon | Weapon | ⚔️ | #cc4400 |
| tool | Tool | 🔧 | #888800 |
| key | Key | 🔑 | #ffcc00 |
| light_source | Light Source | 💡 | #ffff00 |
| wearable | Wearable | 👘 | #cc66cc |

### Character Traits (as tags)
| ID | Name | Icon | Color |
|----|------|------|-------|
| vampire | Vampire | 🧛 | #880000 |
| werewolf | Werewolf | 🐺 | #444400 |
| ghost | Ghost | 👻 | #aaaaff |
| human | Human | 🧑 | #88aa88 |
| elf | Elf | 🧝 | #44aa44 |
| dwarf | Dwarf | ⛏️ | #884400 |
| synthetic | Synthetic | 🤖 | #8888cc |
| animal | Animal | 🐾 | #aa8844 |

---

## Migration

Existing tags on items/characters/rooms will continue to work. The tag library is advisory, not enforced — unknown tags are warned but not blocked. Over time, as users interact with the multiselect, tags naturally converge to library entries.

Optional: a one-time `POST /api/tags/migrate` endpoint that scans all entities and auto-creates library entries for any tags not yet in the library.

---

## What's Left

### Phase 3 (only gap)
- `engine/serialization.py` — tag validation on save not implemented

### Phase 4 (not started)
- `static/js/graph/` — tag color indicators on graph nodes

---

## Files left to touch

### Backend
- `engine/serialization.py` — tag validation on save

### Frontend
- `static/js/graph/` — tag color indicators

---

> **Completion note (2026-08-02):** The two remaining gaps are implemented.
> - Phase 3b: `validate_tags_on_save()` added to `routes/helpers.py`; wired into `PATCH /api/graph/node/<id>` — warns (logs + `tag_warnings` in response) on unknown/misspelled tags, never blocks saves.
> - Phase 4: graph tag panel in `static/js/graph/network-manager.js` — tag icons prepended to node labels (from the tag library), a clickable `🏷️ Tags` toolbar panel listing each used tag with its color dot/icon/count, click-to-filter highlight (matching nodes full opacity, others dimmed), and tag names in hover tooltips for area/character/item nodes. Toolbar button + CSS added in `templates/index.html` and `static/css/style.css`.

## Commit History

| Commit | What |
|--------|------|
| ✅ | Phase 1: Tag library + CRUD + search/validate endpoints |
| ✅ | Phase 2: TagMultiselect component + item-view/agent-view migration |
| ✅ | Phase 2b: Migrate remaining old tag inputs (library-browser, way-view, create-modal, helpers, inspector.js, agent-view) |
| ✅ | Phase 3: Auto-registration in TagMultiselect + stats endpoint |
| ✅ | Phase 3b: Tag validation on save (routes/helpers.py + PATCH node route) |
| ✅ | Phase 4: Graph tag color indicators (tag panel, label icons, click-to-filter) |
