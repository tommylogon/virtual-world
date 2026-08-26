---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---

# Enhanced Item Creation: Multi-Target, Triggers, Prompt Preview

**Filed**: 2026-07-16
**Priority**: High
**Status**: In Review — implemented (code-verified 2026-08-11). Multi-target radio (Area/Container/Character) + AI trigger parsing + 👁️ prompt preview in `create-modal.js`/`main.js`.

---

## Summary

The "Create New Item" modal (main.js) and Item Library generation (item-library.js) need three enhancements:

1. **Target selector** — choose Area, Container Item, or Character as the placement target
2. **Trigger generation** — AI generates triggers but parse step discards them; all LLM prompts need up-to-date trigger docs
3. **Prompt preview** — view and edit the assembled prompt before sending to the LLM

## Current State

### Trigger parsing missing in main.js (line 386-389)

The format hint includes triggers (`"triggers":[{"trigger_type":"on_use","effect_type":"message","effect_params":{"message":"..."}}]`) but the parsing only sets name, description, uses, weight, hidden — triggers are ignored.

### LLM prompts inconsistent

| Location | Function | Has triggers? | Has full docs? |
|----------|----------|--------------|----------------|
| `main.js:335` | `generateWithAI('item')` | Format hint only | No |
| `item-library.js:1065` | `generateWithAI()` | Format hint + basic | No |
| `item-library.js:~930` | `improveWithAI()` | Full docs + examples | Yes |

### Single target type

The create modal only has a "Target Area" dropdown. There's no way to place items into containers or character inventories.

### No prompt preview

The Generate button sends the prompt directly. Users can't see or edit what will be sent.

## Proposed Changes

### 1. Shared trigger documentation

Extract the trigger/effect/condition docs from `item-library.js:improveWithAI` into a new shared file `static/js/prompt-docs.js`, registered as `VW.PromptDocs.ITEM_GENERATION_SYSTEM`. Insert it in the script load order between `api.js` and `agent-engine.js`.

Both `main.js` and `item-library.js` reference this shared constant.

### 2. Fix trigger parsing (main.js:386-389)

Add parsing for `data.triggers` → populate `#item-triggers-json` textarea after AI generation.

### 3. Target type selector

Replace the "Target Area" dropdown with a radio group:

- 🏠 Area → select from rooms
- 📦 Container Item → select from graph item nodes
- 🧍 Character → select from graph character nodes

The target's description is passed to the LLM system prompt for context.

### 4. Prompt preview

Add a `👁️` button next to Generate. Opens a modal showing the full assembled prompt in an editable textarea. On send, extracts the user portion and sends it.

### 5. Backend extension

Extend `POST /api/build/item` (app.py:1014) to accept `container` and `character` fields alongside `room`. Creates the appropriate edge type:
- `room` → `location` edge (existing)
- `container` → `contains` edge
- `character` → `carried_by` edge

## Files Affected

- **NEW** `static/js/prompt-docs.js` — shared trigger documentation
- `static/js/main.js` — trigger parsing, system prompt, target selector, prompt preview
- `static/js/item-library.js` — use shared prompt docs, prompt preview
- `static/js/api.js` — if needed for new fields
- `app.py` — extend `/api/build/item`
- `templates/index.html` — script load order for new file

## Verification

- Create item → target room → AI generate with triggers → verify triggers populate
- Create item → target container → verify `contains` edge
- Create item → target character → verify `carried_by` edge
- Prompt preview → edit text → verify modified prompt used