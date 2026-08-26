# Bug 22: Static inspector empty-state lingers above every render

**Status**: In Review — implemented + browser-verified 2026-08-23

## Symptom

Selecting a node in the right panel showed the real inspector *below* the
"Select a node or agent to inspect" placeholder instead of replacing it. The
placeholder never went away for the rest of the session.

## Root cause

`templates/index.html` shipped the `.inspector-empty` placeholder as **static
markup inside `#inspector-panel`**. Since the task-216 lit migration, the panel
is rendered via `window.Lit.render()`, which only manages its own part range —
**lit never removes DOM children it doesn't own**. So the static div survived
every render, with lit content appended after it.

Not `unsafeHTML`'s fault: agent-view's `unsafeHTML(html)` sits at a lit-managed
position and replaces correctly. The leftover was purely the pre-lit static
child.

## Fix

1. `templates/index.html` — removed the static placeholder from
   `#inspector-panel` **and from all 7 library-modal editors**
   (`item-lib-editor`, `lib-char/area/trait/cond/beh/way-editor`), which had
   the identical latent bug (lit-render targets with static placeholders).
2. `static/js/inspector/panel.js` — `render()` now clears pre-lit children
   once (`panel.dataset.litBound` guard) before lit takes ownership, so any
   future static markup can't regress this.
3. `static/js/main.js` `init()` — after the existing `window.Lit` wait, renders
   the lit empty-state (`Inspector.hide()`) if the panel is still empty, so
   boot shows the placeholder (now with the 🌍 World Lore button — the static
   version had silently diverged and lacked it).

Empty-states now have a single source of truth: the lit templates
(`inspector.js hide()`, `_emptyTemplate`, `library-browser._showEditorEmpty`,
`item-library.open`).

## Verification

Playwright against live server (fresh reload):
- Boot: exactly one `.inspector-empty`, lit-rendered, has World Lore button.
- `showNode(player_elena_vance)`: empty count 0, `.inspector-header` present.
- `hide()` → empty back (1); `showNode` → gone (0). Round trip clean.
- Item library: `open()` renders one placeholder; `showEditor()` replaces it
  (0 empty, real editor children present).
- Console: 0 errors.

`node --check` on panel.js + main.js.
