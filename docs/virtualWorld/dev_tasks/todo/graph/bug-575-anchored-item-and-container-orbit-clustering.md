---
type: bug
status: todo
area: graph
priority: medium
wiki: "[[World Building/Graph System]]"
related: [task-485, task-771]
---

# bug-575: Anchored item and container nodes cluster and overlap on character orbit rings

**Filed:** 2026-11-09
**Related:** task-485, task-771

<!-- deps:start -->
**Related:** [[task-485-derived-parent-relative-node-layout-items-characters-follow-what-holds-them]], [[task-771-place-content-nodes-relative-to-their-area-in-graph-mode-stop-the-central-collapse]]
<!-- deps:end -->

## What

Items anchored to a character (or to a container like a backpack or coat) render severely cramped and overlapping on the graph canvas. Node diamonds collide with each other and text labels overlap into an unreadable knot.

Two distinct problems cause this behavior:

1. **Overly Aggressive Nested Scaling (`nestedScale: 0.45`) in Relative Layout**:
   In `static/js/graph/relative-layout.ts`, items orbiting a container carried by a character (depth 2) have their orbit radius and node spacing scaled down by `nestedScale = 0.45`:
   - `minRadius` drops from 130px to ~58.5px.
   - `spacing` drops from 92px to ~41.4px.
   Because diamond nodes are ~30px wide with text labels spanning 100-200px, packing 4 to 8 items on a 58px radius circle causes guaranteed diamond collisions and label overlap.
   Furthermore, container items (like `Backpack` or `Heavy Fur-Lined Coat`) sit on the character's direct ring, meaning the container's child item orbit directly collides with the character's other equipped gear (boots, vest, brooch).

2. **Misleading UI Controls for Spacing**:
   The View menu exposes a prominent stepper labeled **MAP GRID** (`[-] 560 [+] [A]`), which authors naturally assume controls map graph node spacing. However, this setting only adjusts the padding between *areas* in the Map layout, with zero effect on item orbit radii.
   The actual setting controlling item distance (`graphItemEdgeLength`) is buried inside `Settings -> Graph` (slider "Hug Parent <-> Stretched", defaulted to 60px). Even at maximum stretch, the 0.45 nested multiplier keeps container contents squashed.

## Why

Characters and containers routinely hold 5 to 15 items (clothing, weapons, tools, documents). If the orbit radius cannot accommodate item counts and containers do not push outward to clear the parent character, the graph becomes a cluttered visual pile that prevents selecting, inspecting, or reading items.

## How

1. In `static/js/graph/relative-layout.ts`:
   - Increase `ORBIT.nestedScale` from 0.45 to a dynamic scaling factor based on child count (or minimum 0.75) so containers with 4+ items expand outward.
   - Dynamic label-aware radius: ensure `minRadius` scales proportionally with node label length and child count so diamonds never sit closer than 65px center-to-center.
   - Outward container repulsion: push container hubs (`Backpack`, `Coat`) outward radially along their angle so their child orbits do not intersect the carrier's primary equipment ring.
2. In `static/js/graph/toolbar.ts` and `templates/index.html`:
   - Clarify the **Map grid** label to **Area pitch (Map layout)** so authors are not misled into thinking it spaces character items.
   - Expose an **Item spread** stepper or shortcut in the View menu (or graph toolbar) alongside edge label size, directly adjusting `config.graphItemEdgeLength`.

## Browser UI and intended live verification

Intended UI home: Main graph canvas -> Character node clusters with carried/contained items, and View dropdown menu.

Current availability: Reproducible on `localhost:4444` (e.g. `science_annex_investigation` or `millwood_high_1f` with character `Kaelen Voss` or `Jane two`). Carried items and container contents cluster into a dense overlapping knot.

Live steps when available:
1. Load a scenario with a fully equipped character carrying nested containers (e.g. `Kaelen Voss` with Backpack and Coat).
   - expected: Character node renders with equipped items and container items spread out cleanly.
2. Inspect the character's direct equipment ring.
   - expected: Equipped item diamonds and labels have sufficient angular spacing with zero overlapping text.
3. Inspect container nodes (`Backpack`, `Heavy Fur-Lined Coat`).
   - expected: Container items orbit their container on a sufficiently large circle that clears both the container and adjacent character gear.
4. Open the View dropdown menu and adjust the **Item spread** control.
   - expected: Item orbits expand or contract smoothly in real time.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In the graph view, inspect a character carrying 8+ items and at least one container with 4+ contents.
   - expected: All node diamonds and text labels are legible without overlapping collisions.
   - observed: Severe collision; container contents overlap each other and intersect the character's primary equipment ring.
2. In the View dropdown, adjust the Map grid stepper.
   - expected: Tooltip and label clarify that it only controls area spacing, or an Item spread control is provided.
   - observed: Map grid stepper has no effect on item clustering.
3. Run relative layout unit tests: `node tools/unit/run.cjs`.
   - expected: All unit tests pass.

## Acceptance

- [ ] Item nodes orbiting characters and containers do not overlap each other's diamond bounds.
- [ ] Nested container rings (depth >= 2) scale radius dynamically to fit child count without squashing into a 58px clump.
- [ ] Container hubs are pushed radially outward to prevent intersecting the carrier's primary equipment ring.
- [ ] View menu clarifies Area pitch vs Item spread controls.

## Files

- `static/js/graph/relative-layout.ts`
- `static/js/graph/separation.ts`
- `templates/index.html`
- `static/js/graph-manager.ts`
- `tools/unit/test_relative_layout.js`
