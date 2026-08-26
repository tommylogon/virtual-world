---
group: Prompt & Narrative Quality
wiki: "[[Characters/Characters Overview]]"
---

# Editable Characters — Paperdoll, Grid Inventory, Auto-Appearance

**Filed**: 2026-07-15 (updated 2026-07-21)
**Priority**: Medium
**Status**: Review — major pieces done (paperdoll, grid inventory, auto-appearance, stacking, right-click). Remaining polish tracked in task-89.

---

## Summary

The character inspector needs a full overhaul: tabbed sections, an RPG-style grid inventory with tooltips, a paperdoll equipment view (editable, not read-only), and auto-generated appearance descriptions derived from equipped items. The equipment engine is tracked in `task-3-equipment_system.md` — this task covers the frontend UI.

## Current State (Already Implemented)

| Feature | Status |
|---------|--------|
| State dropdown | ✅ Editable |
| Current room | ✅ Editable |
| Emotion + intensity | ✅ Editable |
| Personality textarea | ✅ Editable |
| Appearance (base + current) | ✅ Split into base_description + description |
| Generate description from equipment | ✅ Button in inspector (now calls LLM via /api/players/<name>/generate-description) |
| Memory/world_knowledge | ✅ Editable |
| Behaviors (NPCs) | ✅ Editable |
| Stats (STR/DEX/CON/INT/WIS/CHA) | ✅ Editable |
| Skills | ✅ Editable |
| Relationships | ✅ Editable |
| Vitals display | ✅ Read-only bars |
| Examine other characters | ✅ Shows base + equipment + mood |
| Inventory | ✅ Grid layout with icon/name/weight, click-to-inspect, drop/equip buttons, add-item picker |
| Equipment paperdoll | ✅ CSS grid with 12 body slots (100x100px cells), tooltips, click-to-inspect, equip picker, unequip buttons |

## Part 1: Tabbed Inspector

Replace the single-page character inspector with tabbed sections:

- **Stats** — stats, skills, vitals
- **Equipment** — paperdoll view with editable slots (see Part 3)
- **Inventory** — grid layout with tooltips (see Part 2)
- **Bio** — personality, appearance, memories, behaviors (NPC)
- **Relationships** — relationship editor

## Part 2: RPG-Style Grid Inventory

### Layout

Items displayed in a **grid** (not a flat list). Each cell shows:
- Item icon/emoji (📦 by default, different emoji per item type)
- Item name
- Weight / quantity badge

### Interactions

| Action | Behavior |
|--------|----------|
| **Click** | Opens item inspector |
| **Hover** | Tooltip: name, description, weight, tags, equipment info |
| **Right-click** | Context menu: Examine, Equip, Drop, Use |
| **Drop** | Click drop button or right-click drop — removes item from character, places in current room |

### Add Item

"Add Item" button opens a searchable picker from:
- World items (all items in the current scenario)
- Library items (from item library)

### Container contents

Items marked `container: true` show an expandable list of contents. Clicking reveals items inside.

### Visual

```
┌─────────────┬─────────────┬─────────────┐
│ 📦 Rations  │ 📜 Old Map  │ 🔑 Rusty Key│
│ 0.5 kg      │ 0.1 kg      │ 0.2 kg      │
├─────────────┼─────────────┼─────────────┤
│ 🧪 Health   │ 💎 Silver   │ 📖 Journal  │
│ Potion      │ Ring        │             │
│ 0.3 kg      │ 0.05 kg     │ 0.5 kg      │
└─────────────┴─────────────┴─────────────┘
```

## Part 3: Paperdoll Equipment View

### Layout

A visual character outline with labeled body slots, each showing the equipped item (or "— empty —").

```
         ┌───── Head ─────┐
         │ [Steel Helmet] │
         ├───── Neck ─────┤
         │ [Gold Pendant] │
┌─ Arms ─┼──── Torso ─────┼─ Arms ─┐
│ [Brac- │  [Leather      │ [Brac- │
│  ers]  │   Jacket]      │  ers]  │
│        │  [Chainmail]   │        │
├─ Hands ┼─── Waist ──────┼─ Hands ┤
│        │ [Utility Belt] │        │
├─ Legs ─┴────────┬───────┴─ Legs ─┤
│ [Pants]         │ [Greaves]      │
├────── Feet ─────┴─────── Feet ───┤
│ [Hiking Boots]                   │
├─── Left Hand ───┬─── Right Hand ─┤
│ [Wooden Shield] │ [Longsword]    │
└─────────────────┴───────────────┘
```

### EDITABLE, not read-only

Each slot is clickable:
- **Click on empty slot** → opens item picker filtered by compatible items for that slot
- **Click on equipped item** → options: Unequip, Swap, Inspect
- **Right-click on equipped item** → context menu
- Slots can be set to "empty" to remove items

This is how scenarios start with equipped characters — the GM/editor assigns items to slots directly.

### Stacked items

Slots with stacked items show the outermost item with a "+N more" badge:
```
[Torso]  Leather Jacket +2 more  ▼
```
Click to expand the stack and see/remove inner layers.

### Paperdoll CSS

Implemented as a CSS grid/table with:
- Character-shaped layout (head at top, feet at bottom, arms at sides)
- Each cell is 100x100px
- Color-coded: filled slot vs empty slot
- Back slot moved to top row beside head
- Hover tooltip shows item name
- Click to open item inspector

### Remaining frontend work (moved to task-89)

- **Container contents expandable** in inventory — click container item to see items inside
- **Click empty paperdoll slot** → auto-open equip picker (currently only + button)
- **Swap option** on equipped items in paperdoll
- **Drag-and-drop** from inventory to paperdoll slots (future)

## Part 4: Auto-Generated Appearance

### The problem

Currently characters have a static `appearance` text field. With equipment, the appearance should change based on what's worn. A character in chainmail + jacket looks different from one in a t-shirt.

### Solution: Base appearance + equipment overlay

1. **Base appearance** — the character's naked/neutral description (body type, hair, face, skin, distinguishing features). Stored in `base_description` field.
2. **Derived appearance** — base + equipment described on top of it, stored in `description` field.
3. **Backend fallback** — `_update_equipment_description()` in `engine/equipment.py:392` runs on every equip/unequip via the backend. It builds a code-generated fallback template (never calls the LLM directly).
4. **Frontend LLM hook** — `api.js:381` auto-triggers `InspectorAgentView._generateDescription()` after `wear`/`remove`/`unequip` actions. This calls `llmClient.chat()` with base_description + equipment, then saves the result back via `POST /api/players/<name>/description`.
5. **Manual button** — "Generate from Equipment" in the inspector calls the same frontend LLM path.

### How it shows to others

| Situation | What they see |
|-----------|---------------|
| Fully clothed | LLM-generated (via frontend): "Kaelen is a tall woman with sharp features, wearing a leather jacket over a chainmail shirt..." |
| Nude | LLM-generated from base_description only |
| LLM fails or backend-only path | Fallback template: "[p.name] is wearing chainmail on their torso, boots on their feet..." |

### Triggering the description

- `wear` / `remove` / `unequip` commands — frontend `api.js:381` hook fires `InspectorAgentView._generateDescription()` via `llmClient.chat()`
- Manual "Generate from Equipment" button — same frontend LLM path
- Backend `_update_equipment_description()` runs the fallback template on every equip/unequip regardless (sets `player.description` to code-generated text as a safety net)

## Part 5: NPC Starting Equipment

Scenarios need a way to define what characters start with:

### In world data

```json
{
  "characters": {
    "guard": {
      "name": "Marcus",
      "description": "A broad-shouldered man...",
      "equipped": {
        "head": "steel_helmet",
        "torso": ["tunic", "chainmail"],
        "legs": ["pants"],
        "feet": ["boots"],
        "hand_right": "spear",
        "waist": "belt_pouch"
      }
    }
  }
}
```

When the scenario loads, these items are created (if not existing) and equipped to slots. The character's appearance is auto-generated from the equipped state.

### In inspector

When editing a character, equipment slots can be pre-filled from the paperdoll editor. This sets up starting gear for any character before the scenario begins.

## Files Affected

- `static/js/inspector.js` — tabbed layout, paperdoll editor, grid inventory, tooltips, context menus
- `static/js/main.js` — right-click context menu handlers, drop command
- `app.py` — inventory add/remove/drop endpoints, equip/unequip from inspector, appearance LLM endpoint
- `virtual_world_engine.py` — appearance derivation from equipment, nude/base description
- `static/js/item-library.js` — equip_slots, container fields in item editor
- `player.py` — base_appearance vs derived_appearance
- Scenario data files — `equipped` field on character definitions