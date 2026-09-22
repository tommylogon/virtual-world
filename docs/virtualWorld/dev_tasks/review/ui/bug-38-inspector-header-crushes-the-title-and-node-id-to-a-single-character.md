---
type: bug
status: review
area: ui
priority: high
---

# bug-38: Inspector header crushes the title and node ID to a single character

**Filed:** 2026-09-22
**Related:** bug-37 (same panel), task-357

## Symptom

Reported from a screenshot of the Area inspector for the abandoned hunter's cabin. The
header showed:

- **NODE ID: `a`** - not the node's id, just its first character
- the area **name invisible** entirely ("Abandoned Hunter's Cabin" not readable)
- a small blue button beside the ID, which reads as a broken icon

The blue glyph is a red herring: it is the 🔄 **Sync ID from name** button, and Windows
renders 🔄 as a blue circular-arrow emoji. The button works. Everything else in that row
was the bug.

## Root cause

`.inspector-header` (`static/css/style.css:950`) is `display: flex` with the default
`flex-wrap: nowrap`. Its children are the type badge, a title/ID column
(`style="flex:1;display:flex;flex-direction:column;"`), and three non-shrinking action
buttons (Save to Library, Duplicate, close).

`flex: 1` is `1 1 0%`, so the title/ID column's hypothetical main size is **zero**. The
buttons can shrink only to their min-content width, so the column is handed whatever is
left over - and at the inspector's default ~320px panel that is 44px.

Measured live at panel width 319px, before the fix:

| element | width | content width |
|---|---|---|
| title/ID column | 44px | - |
| name input | 44px | 196px |
| node-ID input | **9px** | 149px |

The node-ID input sits in a second flex row beside the 32px sync button, so it inherited
`44 - 32 - gap = ~9px`: exactly one character. The name input rendered its full value at
44px, so it was clipped to a sliver behind the badge.

## Fix

Two changes, both about giving the column a floor instead of letting it absorb the
leftover space:

1. **`static/css/style.css`** - `flex-wrap: wrap` on `.inspector-header`, plus
   `.inspector-header > div { min-width: 140px; }`. The floor raises the column's
   hypothetical main size, which makes the header **wrap the action buttons onto their
   own line** rather than crush the column.
2. **`static/js/inspector/area-view.js`** and **`static/js/inspector/agent-view.js`** -
   the node-ID input's `width:100%` became `flex:1;min-width:0`, so it fills its row
   beside the sync button instead of fighting it.

Measured after, same node, same panel width:

| element | before | after |
|---|---|---|
| name input | 44px | **220px** |
| node-ID input | 9px (1 char) | **186px** (~30 chars) |
| action buttons | same crushed line | wrapped below |

The header grows from 84px to 112px when the buttons wrap. That is the intended trade:
the information is readable and nothing is hidden behind a collapse.

## Acceptance

- [ ] At the default inspector width no node ID is ever truncated to fewer than ~20
      characters, and the node name is fully readable.
- [ ] All five header renderers behave: area, item, way, agent, and world lore
      (`inspector/{area,item,way,agent,lore}-view.js`).
- [ ] Wider panels still keep everything on one line; nothing wraps unnecessarily when
      there is room.
- [ ] The 🔄 Sync ID from name button and the ✕ close button remain clickable.

## Files

- `static/css/style.css` - header flex wrapping and the column floor
- `static/js/inspector/area-view.js` - node-ID input sizing
- `static/js/inspector/agent-view.js` - node-ID input sizing
