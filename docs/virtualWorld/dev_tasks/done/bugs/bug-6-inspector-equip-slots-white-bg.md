# Bug 6: Character inspector equipment slot selector — same white bg as bug 2

**Filed**: 2026-07-23
**Priority**: High
**Status**: Fixed (same global Choices.js CSS overrides as bug 2)

## Summary

Same as bug 2 but in the character inspector (world items), not the library. The equipment slot multi-select in the item inspector (node-equip-slots-*) has a white background with unreadable light gray text.

## Root Cause

Same as bug 2 — Choices.js default light theme with no dark-mode CSS overrides. The fix in bug 2 may already cover this if the CSS overrides apply globally to all `.choices__*` elements, but needs verification.

## File

`static/js/inspector/item-view.js:190` — `<select multiple class="choices-init" id="node-equip-slots-${escapedId}">`

---
_Audited 2026-08-03 � duplicate file consolidated into this record._
