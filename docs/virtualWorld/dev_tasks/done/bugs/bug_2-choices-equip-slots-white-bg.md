---
wiki: "[[UI & Settings/Inspector Panels]]"
---

# Bug 2: Equipment slot selector — white background, unreadable text

**Filed**: 2026-07-23
**Priority**: High
**Status**: Fixed

## Summary

The equipment slot multi-select dropdown in the library item editor uses the Choices.js library with default light theme, rendering a white background with light gray text that's unreadable on the dark-themed UI.

## Root Cause

Choices.js default light theme with no dark-mode CSS overrides. The library applies its own inline styles that override the site's dark theme.

## Fix

Add dark-theme CSS overrides for Choices.js elements in `static/css/style.css`. Key classes to override:

- `.choices__inner` — input area background/border
- `.choices__list--dropdown` — dropdown background/border
- `.choices__list--dropdown .choices__item--selectable` — item text color
- `.choices__list--dropdown .choices__item--selectable.is-highlighted` — hover/selected state
- `.choices__input` — search input inside the widget

Colors should match the existing dark palette: `--bg-input`, `--bg-card`, `--text`, `--text-muted`, `--border`.

## Files

`static/css/style.css` — add Choices.js dark-theme overrides

## Verification

### Manual Test Steps:
1. Open the game in browser at http://127.0.0.1:4444
2. Click "Item Library" button
3. Click any item, look for equipment slot multi-select dropdown
4. Click the dropdown to expand it
5. **Expected**: Dropdown has dark background with readable white/light text, not white background with gray text
6. Also check in Item Inspector: click an item in the graph, look at equip slots selector
7. Verify `.choices__list--dropdown` items have proper contrast (check CSS computed styles)

### Files to verify:
`static/css/style.css` should have `.choices__*` dark-theme CSS overrides.
