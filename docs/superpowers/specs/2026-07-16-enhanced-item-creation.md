# Enhanced Item Creation: Multi-Target Placement, Trigger Generation, Prompt Preview

**Filed**: 2026-07-16

## Summary

The "Create New Item" modal currently only places items in rooms and its AI generator doesn't parse triggers. This spec extends the modal to support placing items in rooms, containers, or character inventories; fixes trigger generation; adds an editable prompt preview; and updates all LLM generator prompts with comprehensive trigger documentation.

---

## 1. Target Type Selector

**Current**: Single "Target Area" dropdown in the create modal.

**New**: Replace with a radio group for target type, then a dynamic select list.

| Radio | Select shows |
|-------|-------------|
| 🏠 Area | All rooms from `worldState.rooms` |
| 📦 Container Item | All item nodes (excluding current) from graph |
| 🧍 Character | All nodes of type `character` from graph |

When the user picks a type, the select list updates to show matching targets.

### AI Context

The target's description is passed to the LLM system prompt:

- **Area**: `worldState.rooms[areaName].description` (already implemented)
- **Container**: `worldState.getNode(containerId).properties.description`
- **Character**: `worldState.getNode(charId).properties.description || worldState.getNode(charId).name`

The prompt line added: `\nThis item will be placed in/inside/carried by "${targetName}": ${description}`

### Backend (`/api/build/item`)

The `POST /api/build/item` endpoint currently creates a `location` edge to a room. Extend to:

- `container` field → create `contains` edge (item → container)
- `character` field → create `carried_by` edge (item → character)
- If `room` provided → existing `location` edge behavior (unchanged)
- Only one target type is allowed per request

---

## 2. Trigger Generation Fix

**Problem**: `main.js:generateWithAI('item')` includes triggers in the format hint (line 335) but the parse step (lines 386-389) discards them.

**Fix**: Add trigger parsing to the item branch:

```js
// After setting basic fields
const triggersField = document.getElementById('item-triggers-json');
if (triggersField && data.triggers) {
    triggersField.value = JSON.stringify(data.triggers);
}
```

**System prompt update** (main.js, line 318): Replace the generic "Respond with raw JSON" with the same detailed trigger/container documentation that `item-library.js` already has in its `improveWithAI` prompt.

---

## 3. Prompt Preview/Editor

**UX**: A small button `👁️` next to the "Generate" button in the create modal and item library.

On click, opens a modal showing the full assembled prompt in an editable textarea:

```
[System]
You are a procedural content generator...
[Context]
...
[User prompt]
...
```

The user can edit the text before sending. When they click "Send", the edited text replaces what would have been sent.

**Implementation**: 
- Assemble the prompt (system + user messages) the same way `generateWithAI` does
- Display in a textarea
- On "Send", parse the textarea to extract the user message part (everything after the last `[User prompt]\n` line, or use a separator)
- Pass the edited user message + original system message to `llmClient.chat()`
- If the user edited the system message too, use the modified version

**Simple approach**: Prepend `[System]\n{systemMsg}\n\n[Context]\n{context}\n\n[User prompt]\n{prompt}` in a full-screen textarea modal. On send, extract the portion after `[User prompt]\n` as the user message. The system message stays as originally assembled (user edits only the user portion). The modal has:
- The editable textarea
- "Send" button → uses the edited user message
- "Cancel" button → closes modal, no change
- "Copy" button → copies full prompt to clipboard

---

## 4. LLM Generator Prompt Audit

All AI generation points need comprehensive, consistent trigger documentation:

| Location | Function | Has triggers? | Has full docs? |
|----------|----------|--------------|----------------|
| `main.js` | `generateWithAI('item')` | Format hint only | No |
| `item-library.js` | `generateWithAI()` | Format hint + basic | No (lacks full docs) |
| `item-library.js` | `improveWithAI()` | Full docs + examples | Yes |

**Action**: Extract the trigger/effect/condition documentation from `item-library.js:improveWithAI` (lines ~930-987) into a shared file `static/js/prompt-docs.js`:

```js
// prompt-docs.js — registered before main.js and item-library.js
window.VW = window.VW || {};
VW.PromptDocs = {
    ITEM_GENERATION_SYSTEM: `...trigger docs...`
};
```

Insert in load order between `api.js` and `agent-engine.js` in the HTML template.

Both `main.js:generateWithAI` and `item-library.js:generateWithAI` reference `VW.PromptDocs.ITEM_GENERATION_SYSTEM` instead of duplicating the prompt text.

---

## 5. Files Affected

- `static/js/main.js` — trigger parsing, system prompt docs, target type selector HTML, prompt preview, generateWithAI refactoring
- `static/js/item-library.js` — updated system prompt in generateWithAI, prompt preview
- `app.py` — extend `/api/build/item` for container/character targets
- `static/js/api.js` — update `createItem()` to send new fields
- `docs/superpowers/specs/2026-07-16-enhanced-item-creation.md` — this spec

---

## 6. Error Handling

- If no target selected → alert "Select a target"
- If container/character doesn't exist in graph → backend returns 404
- Backend validates only one target type per request

---

## 7. Testing

- Manual: create items targeted at room, container, character via both create modal and library
- Manual: AI generate with triggers → verify triggers field is populated
- Manual: prompt preview → edit and verify modified prompt is sent
