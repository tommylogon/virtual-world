---
group: Items & Crafting
wiki: "[[Rules Engine/Triggers & Effects]]"
---

# AI Generate Triggers for New Items

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: In Review — implemented (code-verified 2026-08-11). AI item generation includes trigger guidance + common patterns in system prompt (`main.js:246-256`); triggers parsed into create form / library.

---

## Summary

When generating an item with AI, no triggers are generated. The AI only generates basic properties (name, description, actions, uses, weight, hidden). Users must manually add triggers afterward, which defeats the purpose of AI generation for complex interactive items.

## Current State

In `main.js:generateWithAI()` (line 351-354), the AI response for items is parsed as:

```js
set('item-name', data.name);
set('item-desc', data.description);
set('item-uses', data.uses ?? -1);
set('item-weight', data.weight ?? 0.1);
const h = document.getElementById('item-hidden');
if (h) h.checked = data.hidden || false;
```

No trigger data is expected or parsed from the AI response. The format hint doesn't include trigger information.

## Proposed Change

### Step 1: Extend Format Hint

Update the JSON format hint to include triggers:

```js
const formatHint = '{"name":"...","description":"...","actions":"examine,take,use","uses":1,"weight":0.5,"hidden":false,"triggers":[{"trigger_type":"on_use","effect_type":"message","effect_params":{"message":"..."}}]}';
```

### Step 2: Extend System Prompt

Add instructions for the AI about what triggers are and how to generate them:

```
Triggers make items interactive. Common patterns:
- on_use → message: item tells the player something
- on_take → message: special message when picked up
- on_use_on → unlock_way: item unlocks a specific door
- on_examine → message: special description on examination

Generate appropriate triggers based on the item type and purpose.
```

### Step 3: Parse Trigger Data

After AI generation, parse the trigger data and populate the trigger fields (if the create modal supports triggers — see `create_item_modal_more_actions.md`).

If the create modal doesn't yet have trigger UI, store the generated triggers in a hidden field for later editing in the library.

## Audit

**Status**: Ready to test
**How to test**:
- Open the create modal for an Item, use AI generation. Verify the response JSON includes triggers in the format hint.
- After generation, scroll to the "Triggers JSON" textarea — verify it's populated with trigger data from the AI.
- Submit the item, then open it in the Item Library — verify triggers were saved and are editable.

## Files Affected

- `static/js/main.js` — extend format hint, parse triggers from AI response
- `static/js/item-library.js` — extend library AI generation to include triggers