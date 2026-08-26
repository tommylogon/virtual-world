# New Way Modal: More Properties

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: Done — verified 2026-08-03. Full way/connection modal properties in static/js/ui/create-modal.js (way state, pass message, skill check, auto-close, see-through, tags, triggers). Key-item selector intentionally dropped (`locked_with` obsolete).

---

## Summary

The "Connect Rooms" / door creation modal is minimal. It only collects room A/B, directions, a locked checkbox, and a locked_with item. The modal needs more properties to support the richer door system (state, description, door ID naming, lock state options).

the locked with property is obsolete as mentioned in a seperate task. triggers support this functioanlity now

## Current State

In `main.js:openCreateModal()` (line 409-417), the connection form has:

```html
<label>Area A</label><select id="conn-roomA">...</select>
<label>Direction A → B</label><input type="text" id="conn-dir1" placeholder="east">
<label>Area B</label><select id="conn-roomB">...</select>
<label>Direction B → A</label><input type="text" id="conn-dir2" placeholder="west">
<label><input type="checkbox" id="conn-locked"> Locked</label>
<div id="conn-locked-with-group" style="display:none;">
  <label>Locked with item</label>
  <input type="text" id="conn-locked-with" placeholder="key name">
</div>
```

### Missing Properties

Compared to the full door model in the inspector:
- **Way ID** — auto-generated, not editable
- **Description** — no field for door description (e.g., "A heavy oak door")
- **Way State** — limited to locked/unlocked, but ways support: open, closed, locked, hidden, blocked, broken
- **Lock Picking DC** — Skill check DC for lockpicking
- **Key Item** — which item unlocks this door (vs freeform text)
- **Hidden/Secret Way** — toggle for hidden ways

## Proposed Change

Expand the connection modal with additional fields:

### Basic Properties (always visible)

- Way ID (auto-generated from room+dir, but editable)
- Description (textarea/input, optional)

### State Properties (collapsible)

- Initial state: dropdown (open, closed, locked)
- If locked: key item selector (dropdown of library items, replacing the freeform text)
- Hidden door: checkbox

### Advanced Properties (collapsible)

- Lockpicking DC (number, 5-30, only shown if locked)
- Way properties (material, etc. — freeform tags)

### Implementation

Use the same collapsible sections pattern used elsewhere in the UI:

```
[+] Basic Properties (always expanded)
[-] Lock / State Settings (expandable)
    State: [dropdown: open/closed/locked]
    Key: [dropdown of library items]
    Lockpick DC: [number input]
    Hidden: [checkbox]
[-] Advanced (expandable)
    Tags: [comma-separated input]
```

## Files Affected

- `static/js/main.js` — expand connection modal form
- `templates/index.html` — may need additional modal HTML
- `app.py` — ensure all new fields are passed to the backend
