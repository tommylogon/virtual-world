---
type: bug
status: review
area: graph
priority: medium
---

# bug-37: Graph physics checkbox keeps the previous node's state until the inspector is rebuilt

**Filed:** 2026-09-22
**Related:** task-40 (introduced the per-node toggle), bug-22 (same family: panel not
refreshing), bug-26 (panel resolving nodes by name)

## Symptom

Reported live, in the graph inspector:

1. Select node A and **uncheck** its physics toggle.
2. Click node B (whose physics is still on, i.e. the checkbox should read checked).
3. B's inspector shows **A's unchecked state**.
4. It corrects itself only after clicking empty canvas, which tears the panel down
   and rebuilds it.

The state on disk is correct throughout — only the checkbox lies.

## Root cause

Two things, and the bug needs both.

**The binding was a boolean attribute.** `InspectorHelpers.graphGravityControl`
(`static/js/inspector/helpers.js:35`) rendered

```js
<input type="checkbox" ?checked=${enabled} @change=${...}>
```

`?checked` toggles the *content attribute*. lit-html's part diffs against the value
it last **bound**, not against the DOM. So: the panel renders A with `enabled: true`
(part value `true`); the user unchecks A, which flips the DOM *property* to `false`
while the bound value stays `true`; selecting B, whose value is also `true`, is
therefore **not a change** and lit skips the DOM write. The stale unchecked DOM
survives into B's panel.

**Nothing re-rendered after the toggle.** `H.setCentralGravity`
(`helpers.js:49`) saves the node, refetches state and reloads the graph, but never
re-renders the inspector. The generic `state:updated` → `_reRender` path
(`inspector.js:17`) exists, but it is **debounced 250 ms** (`inspector.js:26`), so a
normal-speed click on the next node lands before any render ever observes A's new
value — and once B is the current view, the value it binds is still the stale `true`,
so the diff stays silent forever.

## Fix

Bind the checkbox as a **property**, through lit's `live()` directive:

```js
<input type="checkbox" .checked=${window.Lit.live(enabled)} ...>
```

`live()` compares the bound value against the element's *current* DOM property on
every render and rewrites it when they differ, so the control cannot inherit a
previous node's state regardless of when the next render happens. `live` is already
vendored and stamped onto `window.Lit` (`static/js/shared/lit-bootstrap.js:27,52`)
but had no callers until now. No re-render was added to `setCentralGravity`:
re-rendering the panel from inside its own `@change` handler risks focus loss and
scroll jumps, and `live` removes the need.

## Label fix (same edit)

The control was titled **"Central pull enabled"**, which is not what it does. The
stored property is vis-network's per-node **`physics`** flag
(`static/js/graph/network-manager.js:530` — `physics: central_gravity_enabled !== false`),
so the feature is physics on/off, not a gravity strength. Relabelled to
**"Physics enabled"**, with the hint and the node tooltip reworded to match.

The stored key stays `central_gravity_enabled`: renaming it is a data migration
across every scenario and library file and would break existing saves for no gain.

## Acceptance

- [ ] Uncheck A, then select B (physics on) → B's box is **checked**.
- [ ] Check A, then select B (physics off) → B's box is **unchecked**.
- [ ] Round-trip A → B → A with no canvas click and no 250 ms wait; state is right
      every time.
- [ ] Toggling off still freezes the node while the rest of the graph settles
      (task-40 behaviour intact), and the setting survives a reload.
- [ ] Same behaviour from all four hosts of the control: area, item, way, and the
      agent panel (which renders it into a deferred per-node container).

## Files

- `static/js/inspector/helpers.js` — binding + label
- `static/js/graph/tooltips.js` — "Graph gravity disabled" tooltip wording
