---
type: task
status: review
area: ui
priority: medium
---

# task-530: Apply the graph toolbar redesign (two-tier) and fix its toggle bugs

**Filed:** 2026-09-26
**Related:** bug-48 task-526 task-527 task-521 bug_18

## Goal

docs/design/graph-toolbar-mockup.html was produced but never applied. Ship the redesign
(Do / Where / Look zones, progressive disclosure) and fix the documented bugs: Legend
force-opens with no close; the Map button renames itself; Levels is uncoordinated with
Map; btn-overlays renames itself; no 'None' entry; Cardinal wrongly listed among
overlays; duplicate Copy Prompt; Paste Response should gate on config.manualMode.
Coordinate with bug-48 (Map/Levels) and keep the newest controls (spacing -/+, Names).

## State before this task (measured 2026-09-27)

The bar had grown to **~36 peer controls** in 7 unlabelled groups, mixing four mental
models (Do / Where / Look / Session) at equal weight:

| Bug | Where |
|---|---|
| Map button rewrites itself to "🔮 Graph" when switched off | `graph-manager.js:241`, `:917` |
| `📊 Overlays ▾` is renamed to the active overlay, losing the word + caret for good (no way back) | `graph-manager.js:901-904` |
| Levels state is a label suffix ("🌳 Levels on"), no `active`/`aria-pressed` | `network-manager.js:636-645` |
| Levels silently wins over Map while Map still reads "🗺️ Map" and does nothing | `network-manager.js:431` (bug-48) |
| Legend force-opens on every overlay change — including returning to the structural view — and has no close | `network-manager.js:1177`, `:1235-1239` |
| KEEP flips state and persists with an empty query, where it does nothing | `focus.js:95` |
| Paste Response opens with Manual Mode off and only fails on submit | `main.js:707-711` |
| Cardinal is a *layout* listed as an overlay, and picking it silently switches Map on | `index.html:202` → `graph-manager.js:931-933` |
| Physics state is mutated in 5 places; always enabled, even where it cannot run | `network-manager.js:156`, `graph-manager.js:244`, `layout-engine.js:272,461`, `graph-background.js:1836` |
| Duplicate entry points: Fit (zoom cluster), Export PNG (More), Copy Prompt (paste modal, palette) | `index.html:211/266`, `212/253`, `258/725` + `command-palette.js:39` |

## Acceptance

### Behaviour — no self-renaming, no silent no-ops

- [x] The layout axis is a segmented `role="tablist"` (Graph · Map · Levels) with
      `aria-selected`; **all three keep fixed labels**, and clicking the already-selected
      tab is a no-op (Graph is the off state).
- [x] `#btn-overlays` keeps the text "👁 View ▾" forever; the active overlay is shown by
      the chip inside the popover, not by renaming the trigger.
- [x] `#btn-physics` keeps the text "⏸ Physics" forever; state is `aria-pressed`.
- [x] Levels owns positions → the Map tab is **disabled** with a title saying why, and
      clicking it does nothing (this is the UI half of bug-48).
- [x] Overlays offer an explicit **None** entry; `structural` is reachable from there
      as well as from the Graph tab.
- [x] Cardinal is re-scoped to a "way directions" overlay: it labels ways only and no
      longer switches the layout (the Map tab is the only layout control).
- [x] The legend **never force-opens**. It updates in place when already visible, and
      gains a ✕ close button plus an `aria-pressed` toggle in View ▾.
- [x] KEEP is disabled (and says why) while the search box is empty; the stored
      preference survives so it applies to the next search.
- [x] Paste Response is disabled with a tooltip unless `config.manualMode` is on, and
      re-syncs when the setting is toggled in Settings.
- [x] Physics is disabled **with a reason** whenever a layout or overlay owns node
      positions (Levels, any active overlay) or the node layout is explicitly locked.
      One pure function decides it — no more five independent label writers.
      **Amended 2026-09-27:** the painted grid no longer counts. A painted lattice
      is Map mode's *starting arrangement*, not a freeze, and the grid path places no
      way nodes at all — with physics unavailable they kept stale positions and every
      edge crossed the map. See "Map mode runs physics" in the notes.
- [x] Nothing shows what is loaded: the scope chip now shows the active scope plus a
      live "N areas · M ways · K nodes" stat.
- [x] Exactly one entry point each for Fit, Export PNG and Copy Prompt in the graph bar
      (the zoom cluster keeps Fit/zoom; the palette keeps Copy Prompt).

### Layout / information architecture

- [x] Three labelled zones (Do · Where · Look) with `➕ Build ▾`, `👁 View ▾` and
      `⋯ More ▾` popovers. Top-level controls drop from ~36 to **≤ 10**.
- [x] The steppers (map pitch, edge-label size) move into View ▾ — they are settings,
      not primary actions.
- [x] Session actions (Copy Prompt, Paste Response) leave the main bar for More ▾.
      Deviation from the mockup, which wanted them in an agent/session area: there is no
      such area in the graph workspace, and More ▾ keeps them one click away.

### Accessibility

- [x] Popover triggers carry `aria-haspopup` / `aria-expanded`; popovers close on
      outside click and on Escape; every toggle carries `aria-pressed`; icon-only
      controls keep a `title`.

### Tests

- [x] `tools/unit/test_graph_toolbar.js` covers the pure availability helpers.
- [x] `node tools/unit/run.cjs` green, `npm run lint` and `npm run typecheck` clean,
      `python tools/js_module_index.py --check` passes.
- [x] Verified in the browser: build menu, layout tabs, View popover, disabled states.

## Notes

- `bug-48` stays open: this fixes the *incoherent UI* (Map is visibly disabled under
  Levels), the deeper invariant and its regression test belong to bug-48.
- The mockup's second tier (a separate scope bar with breadcrumb + Generate +
  WorldPainter + Clear) is filed as **task-531**; the loaded-node stat lands here
  because it is cheap, but the full contextual bar does not.
- Narrow-window collapse into an overflow menu is filed as **task-532**; wrapping is
  kept here so nothing overflows off-screen.
- New module `static/js/graph/toolbar.js` (`GraphToolbar`) is the single writer for the
  bar's state: the layout tabs, the overlay chips and every "cannot run right now"
  decision live there, and the pure `mapTabDisabled` / `physicsAvailability` /
  `keepInPlaceDisabled` / `pasteDisabled` helpers are unit-tested.
- Left alone on purpose: the paste-response modal keeps its own "copy prompt to
  clipboard" (a different surface, and the only copy target next to the paste box),
  and the help centre's `[data-help="worldpainter"]` spotlight now points at an item
  inside the Build menu.

## Map mode runs physics (2026-09-27, after review)

Asked for in review, on the grounds that freezing the solver in Map mode leaves the
graph looking broken. It did, and the cause was not the toggle: `_gridUpdates`
(`layout-engine.js`) places **areas** (their painted cells) and items/characters, and
**no way nodes at all**. With physics unavailable the ways kept whatever position they
had last been saved at — in a painted scope, a clump far from the areas — so every
edge stretched across the map. The lattice is Map's *starting arrangement*, not a
freeze, and the solver is the only thing that pulls those loose nodes in.

Three changes, each revertible on its own:

1. `physicsAvailability` no longer treats a painted grid as an owner of positions
   (an explicit 🔒 Lock still does — that one *is* the user saying "these positions
   are intentional"). To revert: restore the `paintedGrid` case next to `mapLocked`.
2. The load path restores the user's physics preference after any layout, instead of
   only when the layout was not a grid, and `_applyGridLayout` no longer clears
   `_physicsEnabled` (it still turns the solver off for the placement pass only).
   To revert: restore `if (wasPhysics && layoutKind !== 'grid')` in
   `network-manager.js` and the `graphManager._physicsEnabled = false` line in
   `layout-engine.js`.
3. **Areas on the painted lattice are now pinned** (`fixed: {x: true, y: true}` in
   `_gridUpdates`) while ways/items/characters stay free. Without this, letting
   physics run simply dragged the areas off their cells and left the map art behind
   — strictly worse. Pinning is also what makes the change safe: the map stays
   aligned, and only the loose nodes move.

Measured on `west_woods` (53 areas, 77 ways, 154 edges): mean way-to-area distance
24px, mean edge 24px, longest edge 45px.

Known limit, unchanged by this: at fit-all zoom on a scope this dense the way-node
labels overlap into mush. That is rendering scale, not physics — see task-526.


