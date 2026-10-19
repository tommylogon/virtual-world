# Library Browser & Template System UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- Unified Library Browser (`static/js/library-browser.ts`) - 1,349 lines
- Item Library (`static/js/item-library.ts`, `placement.ts`, `contents-editor.ts`) - 1,200+ lines
**Rendering Tech:** Lit-html mounted into `#library-modal`.

---

## 1. Measured Ground Truth & Architecture

The Library provides authoring templates and archetypes across 7 distinct tabs:
`Items`, `Characters`, `Rooms`, `Traits`, `Conditions`, `Behaviours`, and `Vocabulary`.

### The Singleton Timing Trap (lines 49-58)
- `LibraryBrowser` delegates the `Items` tab directly to `itemLib` (`item-library.ts`).
- Because `itemLib` is loaded via a classic script tag, `window.itemLib` used to resolve to `undefined` during early execution, crashing the modal with `"itemLibRef is undefined"`.
- It now relies on a lazy resolver `itemLibRef()` to check both `window.itemLib` and `window.VW.itemLib`.

### Template vs Instance Invariant
- Library items are **templates / archetypes**, not physical graph nodes.
- When an item is imported from the library into an area, the engine clones the template, mints a brand new unique ID (`item_93817`), and attaches an authoritative location edge.

---

## 2. Usability & Layout Critique

### A. Fragmented Editor Paradigms Across Tabs
- Switching tabs in the Library exposes 3 completely different editing UIs:
  - **Items Tab:** Uses a rich custom layout with visual tags, equip slot toggles, weapon dice formulas, and container viewers.
  - **Characters / Rooms Tabs:** Uses raw input forms with minimal formatting.
  - **Traits / Conditions Tabs:** Uses a two-column master-detail list with basic key-value text inputs.
  - **Vocabulary Tab:** Uses a raw JSON editor.
- The interface feels like 4 different applications stitched together into one tabbed frame.

### B. Biome Affinity Blindness (task-571)
- Items carry biome affinity tags (`affinity: ["forest", "mountain"]`) to govern procedural loot distribution.
- In the Library item editor, affinity is hidden inside a collapsed "Advanced Tags" field. Authors cannot easily see which biomes will naturally spawn an item.

### C. Import Modal Stiff Positioning
- When clicking "Import to World", an un-resizable popup appears asking for a target Room ID.
- The author cannot see the canvas or check room names while this popup is open, forcing them to cancel the modal, look up the room name on the graph, reopen the library, find the item again, and type the room name.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: The Asset Forge

```
+----------------------------------------------------------------------------------------------------+
| 📚 UNIFIED ASSET LIBRARY                                                    [ + New Asset ] [X]     |
+----------------------------------------------------------------------------------------------------+
| TABS: [ 🗡 Items ] [ 👤 Characters ] [ 🏛 Rooms ] [ 🧬 Traits ] [ ☣ Conditions ] [ 📖 Vocabulary ]   |
+----------------------------------------------------------------------------------------------------+
| SEARCH & FILTERS                                                                                   |
| [ 🔍 Search templates by name, tag, or tier... ]  Category: [ Weapons ▾ ]  Rarity: [ Uncommon ▾ ]   |
+--------------------------------------+-------------------------------------------------------------+
| ASSET CATALOG (Left List - 340px)    | ASSET INSPECTOR & FORGE (Right Pane - Auto Stretch)         |
|                                      |                                                             |
| • Iron Broadsword (Weapon · Tier 1)  | 🗡 IRON BROADSWORD                                          |
| • Oak Quarterstaff (Weapon · Tier 0) | Type: Weapon (Slashing) · Weight: 3.0 kg · Value: 15 gp     |
| • Leather Jerkin (Armor · Light)     |                                                             |
| • Healing Draught (Consumable)       | ┌ Combat Stats ───────────────────────────────────────────┐ |
| • Lockpicks (Tool)                   | │ Damage: 1d8 + STR  ·  Critical: 19-20 (x2)              │ |
| • Torches (Quantity Pool)            | │ Equip Slot: Main Hand / Versatile (1d10)                │ |
|                                      | └─────────────────────────────────────────────────────────┘ |
|                                      | ┌ Distribution & Biomes ──────────────────────────────────┐ |
|                                      | │ Affinities: [ Forest ] [ Dungeon ] [ Barracks ]         │ |
|                                      | │ Rarity Weight: 45% (Common Drop)                        │ |
|                                      | └─────────────────────────────────────────────────────────┘ |
|                                      |                                                             |
|                                      | ACTIONS:                                                    |
|                                      | [ 📍 Spawn Directly on Selected Area ]  [ 💾 Save Changes ] |
+--------------------------------------+-------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **One-Click World Spawning**
   - If an area or character is currently selected on the canvas, the Library offers a prominent `[📍 Drop on Selected Target]` button, eliminating manual room ID typing.

2. **Unified Schema-Driven Editor**
   - Standardize all 7 library tabs to use the same consistent Lit-html card structure with visual chips for tags, dice formulas, and affinities.
