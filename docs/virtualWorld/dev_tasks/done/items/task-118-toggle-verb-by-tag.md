---
group: Trigger System
---
# Toggle Verb by Item Tag

**Filed**: 2026-07-29  
**Priority**: Medium  
**Status**: Done

---

## Summary

The base toggle message currently uses "on"/"off" universally after the fix in `toggleable_items.py`. Instead, the verb should adapt to the item type:

- Items tagged `electric` or `synthetic` → "turn on / turn off"
- Everything else (torches, furnaces, candles, fireplaces) → "light / extinguish"

## Implementation

- `engine/toggleable_items.py` — check `tags` for `electric`/`synthetic` to choose status_word verb
- Keep `current_state` as `"lit"/"unlit"` for the lighting system — only the message changes

## Reference

Trigger messages (when they fire correctly per task-116) already have contextual flavor. This fix only affects the base fallback message.
