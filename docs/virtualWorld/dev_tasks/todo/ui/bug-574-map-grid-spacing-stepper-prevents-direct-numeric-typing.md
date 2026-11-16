---
type: bug
status: todo
area: ui
priority: medium
wiki: "[[World Building/World Painter & Scope Editor]]"
related: [task-765, bug-542]
---

# bug-574: Map grid spacing and stepper controls prevent direct numeric typing

**Filed:** 2026-11-09
**Related:** task-765, bug-542

<!-- deps:start -->
**Related:** [[task-765-centralize-the-graph-physics-policy-in-one-module]], [[bug-542-graph-physics-button-never-reflects-the-node-layout-lock-so-a-locked-world-reads-as-a-dead-toggle]]
<!-- deps:end -->

## What

In the View dropdown menu on the main graph canvas, the **Map grid** spacing control (`#map-spacing`) and the **Edge label size** control (`#edge-label-size`) are rendered as static `<span>` elements flanked by `-` and `+` buttons. Authors cannot click into the value to type a number directly.

When setting map spacing on a large scenario (for example, stepping down from 560 to 300), the author is forced to click the `-` button 13 consecutive times in fixed 20-pixel steps. There is no text input, spinbox, or editable field affordance.

## Why

Setting map layout pitch and font sizes requires quick, precise values. Forcing repetitive button clicks across large numeric ranges creates unnecessary UI friction and prevents authoring exact target values quickly.

## How

1. In `templates/index.html`:
   - Replace `<span id="map-spacing" class="stepper-value">40</span>` with an editable numeric input (e.g. `<input type="number" id="map-spacing" class="stepper-input" min="20" max="2000" step="20" value="40">`) or an editable stepper pattern that allows direct typing while preserving the `-`, `+`, and `A` buttons.
   - Apply the same editable input affordance to `#edge-label-size`.
2. In `static/js/graph-manager.ts` (and `graph-manager.js`):
   - Add `onchange` / `oninput` listener for direct typed values: parse integer, clamp within valid range, unset the Auto (`A`) flag, and trigger `setMapSpacing(val, false)`.
3. In `static/css/` or layout styling:
   - Style `.stepper-input` to match the glass dark-mode aesthetic, centered text, without native browser spin arrows obscuring the digits.

## Browser UI and intended live verification

Intended UI home: Main graph view -> View dropdown menu (`#btn-view-menu` or View button on toolbar) -> Map grid section.

Current availability: Present and reproducible on `localhost:4444`. The `#map-spacing` and `#edge-label-size` elements are static `<span>` tags that ignore keyboard input.

Live steps when available:
1. Load any scenario on `localhost:4444` and switch to the **Map** layout tab.
   - expected: Graph canvas displays areas arranged on the map grid layout.
2. Click the **View** dropdown menu in the top toolbar and locate the **Map grid** section at the bottom.
   - expected: Map grid control is visible with `-`, value input, `+`, and `A` (auto) button.
3. Click directly onto the numeric spacing value, select all, and type `320`. Press Enter or blur.
   - expected: The field updates to `320`, the Auto `A` button toggles off (aria-pressed false), and the graph spacing updates immediately to 320px without clicking `-` or `+` repeatedly.
4. Click into the **Edge label size** control, type `12`, and press Enter.
   - expected: Edge labels on the canvas immediately rescale to 12px.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Open the View dropdown on the graph toolbar and attempt to focus and type into `#map-spacing`.
   - expected: Field focuses, accepts keyboard input, and applies value on blur/Enter.
   - observed: Element is a static `<span>` with zero keyboard focus or typing affordance.
2. Click the `-` and `+` buttons.
   - expected: Value increments/decrements by step and reflects in the input field.
   - observed: Stepper buttons work, but require repeated manual clicks.
3. Run graph toolbar unit tests: `node tools/unit/run.cjs`.
   - expected: All unit tests pass.

## Acceptance

- [ ] `#map-spacing` allows free-form keyboard entry of positive integer values.
- [ ] Entering a manual value automatically disengages the Auto (`A`) spacing derivation.
- [ ] `#edge-label-size` allows direct numeric typing as well as stepper clicks.
- [ ] Invalid non-numeric input is rejected or clamped gracefully.

## Files

- `templates/index.html`
- `static/js/graph-manager.ts`
- `static/js/graph/toolbar.ts`
