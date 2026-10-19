---
related: [task-508, task-155]
area: gameplay
type: task
status: review
priority: medium
---

# Use N Items on Target (quantity)

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

<!-- deps:start -->
**Related:** [[task-508-consume-depletion-contract-engine-auto-decrement-vs-item-authored-fix-the-trigger-suggester-ai-assumption]], [[task-155-item-uses-affect-weight]]
<!-- deps:end -->

## Why

Players want to express quantity when using items on a target: "use 2 kindling in fireplace", "use 2 eggs on pan". Today the use-on action only handles a single item, so these require repetitive single-item commands instead of a natural one-shot instruction. This is idea #8 from developer ideas.

## How

- Doable now with LLM response params - no engine rework.
- Model emits a structured action: `{action:"use_on", item:"eggs", amount:2, target:"pan"}`.
- Add amount/quantity parsing to the use-on action handler, defaulting to 1 when absent so existing behavior is unchanged.
- Trigger/effect path consumes N uses of the item (decrement uses/item count by the parsed amount) and emits the right narrative.
- Validate amount against available count before consuming; clamp or fail gracefully on overuse.

## Files

- `routes/action.py` - accept and forward `amount` in the use-on action payload.
- `engine/item_actions.py` - parse amount, validate against item quantity, consume N uses, emit narrative.
- `static/js/agent/prompt-builder.js` - instruct the model to emit `amount` for use-on actions.


## What

Enable `use <count> <item> on <target>` syntax to consume or apply multiple pooled units in a single turn.

## Acceptance

- [x] Command parser extracts quantity count for pooled item interactions.
- [x] Action deducts specified quantity from inventory stack.
