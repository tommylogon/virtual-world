---
type: task
status: review
area: ui
priority: low
---

# task-532: Graph toolbar: collapse zones into an overflow menu on narrow windows

**Filed:** 2026-09-27
**Related:** task-530 bug_18

## Goal

task-530 keeps the toolbar wrapping so nothing overflows off-screen, but on a narrow
window it still ate two to three rows. Collapse the bar's secondary controls into
More ▾ below ~900px, leaving the scope chip, the search, Build ▾, the layout segment
and View ▾ in the bar. Follow-up to bug_18, whose options 1 and 2 (scroll strip, wrap
within groups) were only partially applied and whose option 3 (shrink the search
boxes) task-530 finished.

## Acceptance

- [x] Below `(max-width: 900px)` six controls move **into** More ▾ under a "Canvas"
      heading: undo, redo, undo history, Fit, Physics, Export PNG. They are
      *relocated*, not hidden, so every handler, title and `aria-pressed` survives —
      a hidden control is unreachable, a moved one is still one click away.
- [x] Build ▾, the layout segment and View ▾ stay in the bar: they are what you reach
      for; the moved six are what you do not.
- [x] Each node's original home is recorded once, so expanding the window puts every
      control back **in place** (verified: all six return to their original zone).
- [x] Icon-only controls get their name back inside the menu via
      `data-overflow-label`; Physics and Export PNG keep their own text, so nothing
      reads "⏸ Physics Physics".
- [x] Using a relocated control runs the action and then closes the menu — except the
      undo-history panel, which is absolutely positioned inside the menu and would be
      hidden with it.
- [x] The More menu opens leftwards, or it hangs off the window edge at narrow widths.
- [x] The Do zone's leftover divider is hidden when it holds a single control.
- [x] Physics' disabled rule is recomputed after a move (it lives on the node, not the
      zone), so an unavailable control is still honest inside the menu.
- [x] Verified in the browser at 860px: the bar drops to two rows, More ▾ lists the
      Canvas section, Physics toggles and closes the menu, and at 1600px every control
      is back where it was.

## Notes

- The viewport is followed with `matchMedia(...).addEventListener('change')`; the rest
  of the bar's responsive behaviour stays in CSS media queries (1240px/1000px).
- The contextual scope bar (task-531) is hidden below 1240px rather than 900px: it is
  a whole row, and the scope chip keeps reporting what is loaded on its own.
