---
type: bug
status: todo
area: ui
priority: high
---

# bug-533: Item inspector 'Save to Library' silently does nothing: _external('itemLib') reads bare window, but the library is only published as VW.itemLib

**Filed:** 2026-10-09
**Related:** bug-50 (rename no-ops), task-446 (node identity)

## Goal

In the item inspector, the **📚 Save to Library** button does nothing — no event-log
line, no console output, no backend request. User-reported on a goblin spear from
the world. Root cause confirmed by reading the load path.

The button (`static/js/inspector/item-view.ts:643`):

    <button ... @click=${() => _external('itemLib')?.saveWorldItem(nodeId)}>📚 Save to Library</button>

`_external` (`item-view.ts:133-136`) resolves names from **bare `globalThis`**:

    const value = (globalThis as unknown as Record<string, unknown>)[name];
    return (value === undefined ? null : value) as ...;

But the item library is published only under the `VW` namespace:

- `static/js/main.ts:22` — `window.VW = {};`
- `static/js/main.ts:81` — `VW.itemLib = itemLib;`

Bare `window.itemLib` / `globalThis.itemLib` is never set. So `_external('itemLib')`
returns `null`, and the optional-chaining call `?.` short-circuits: the click runs
no code, logs nothing, and reaches no endpoint. A silent no-op, not an error.

The codebase already documents this exact trap at
`static/js/library-browser.ts:39` — *"a load-time snapshot (`window.itemLib`) was
always undefined"* — so resurrecting `window.itemLib` is the wrong fix.

Same latent failure at `item-view.ts:818`, which builds the save payload's trigger
list with `_external('itemLib')?._extractTriggersFromEdges(nodeId)` — with the
reference null, the triggers array is silently empty.

Worked example of the *working* pattern: `InspectorPanel` and `TagMultiselect` are
published **bare on `window`** (`inspector/panel.ts:85`, `window.InspectorPanel = …`),
which is why `_external('InspectorPanel')` resolves and `_external('itemLib')` does
not. The mismatch is the bug: the resolver expects bare globals, the publisher uses
the `VW` namespace.

## Acceptance

- [ ] Clicking **Save to Library** on a world item reaches `saveWorldItem` — a
      library write or a DiffModal appears, and an event-log line is produced.
- [ ] The resolver matches the publisher: either `_external` falls back to
      `VW[name]`, or the item library is published where `_external` looks.
      Prefer the `VW` fallback (bare `window.itemLib` is a known-bad snapshot).
- [ ] `_extractTriggersFromEdges` at `item-view.ts:818` resolves too, so the saved
      payload carries the item's triggers.
- [ ] A silent `null` from `_external` is not swallowed without a visible
      symptom — at minimum a log line when a required external is missing.
- [ ] No other `_external(...)` call site resolves a `VW`-namespaced name and
      fails the same way (audit the call sites).
