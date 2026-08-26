# BUG: Item Description Fields Have Wrong CSS (White/Cramped)

**Filed**: 2026-07-15
**Priority**: High
**Status**: Done — verified 2026-08-03. Item description textarea styled with --bg-input/--border/--text vars + resize:vertical (static/js/inspector/item-view.js:185).

---

## Summary

Item description text fields (and possibly other fields in the item inspector) display with white backgrounds and cramped spacing, unlike other text fields in the app which use the dark theme's input styling.

## Current State

In `inspector.js:_showItem()` (line 650), the item description textarea is rendered as:

```js
<textarea rows="2" id="item-desc-${escId}" 
  onchange="VW.inspector._updateItemProp('${escId}','description',this.value)">
  ${esc(props.description)}
</textarea>
```

This textarea does NOT have inline styles for `background`, `border`, `color`, `font-family`, etc. It inherits the browser default (white background) instead of using `var(--bg-input)` like other text fields in the app.

Compare with the room description field (line 458) which uses:

```html
style="width:100%;padding:4px 8px;font-size:12px;background:var(--bg-input);
border:1px solid var(--border);border-radius:4px;color:var(--text);
font-family:var(--font);resize:vertical;min-height:40px;"
```

## Proposed Fix

Apply the same styling pattern to the item description textarea as the room inspector uses. Specifically, add inline styles for:
- `background: var(--bg-input)`
- `border: 1px solid var(--border)`
- `color: var(--text)`
- `font-family: var(--font)`
- `padding: 4px 8px`
- `border-radius: 4px`
- `resize: vertical`

## Additional fields to check

- Way description field in `_showDoor()` (need to read it)
- Any other textarea/input in item inspector that lacks proper styling

## Files Affected

- `static/js/inspector.js` — add proper styling to item description and other fields
