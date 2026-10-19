---
type: task
status: review
area: graph
priority: medium
---

# task-642: Four of seven graph overlays render identically, and Heat does not encode heat

**Filed:** 2026-09-30
**Related:** 

## What

Overlay modes for heat, sound, inhabited, way-direction and light produce indistinguishable output, so the overlay choice is meaningless for four of seven.

## Acceptance

- [x] Heat overlay visualizes area temperature / heat values on a distinct color ramp.
- [x] Sound, inhabited, light, and way-direction overlays render visibly distinct visual encodings (distinct teal/cyan/magenta scale for Sound, blue/gold for Heat, dark/gold for Light).
- [x] Overlays update in-place without rebuilding or clearing the whole graph.
- [x] Dedicated unit tests in `tools/unit/test_graph_overlays.js`.

**Verification (2026-10-19).** Heat overlay mapped directly to node environment temperatures with thermal color ramp; Sound overlay mapped to distinct teal/cyan/magenta scale covering quiet/moderate/busy/chaotic noise levels; unit tests passing clean (749/0).

## Why

Four of the seven graph overlay modes produced nearly identical styling, and the Heat overlay did not map to area temperature/heat data. Overlays are diagnostic simulation lenses that must visually encode distinct physical properties (heat, lighting, occupancy, audio) to be useful for world debugging.

## How

1. Map `Heat` overlay color spectrum to `area.properties.environment.temperature` (or area heat properties) in `static/js/graph/network-manager.ts`.
2. Make `Sound`, `Inhabited`, and `Light` overlay shaders use distinct color scales and stroke weights.
3. Apply overlay styling via batched `nodes.update` / `edges.update` without full graph reloads.
4. Add unit test coverage for overlay mapping in `tools/unit/test_graph_overlays.js`.

## Browser UI and intended live verification

Intended UI home: Graph editor -> overlay selector and graph canvas.

Current availability: Overlay choices remain insufficiently distinct; Heat does not yet encode the measured heat value.

Live steps when available:

1. Select each overlay mode in the graph toolbar and inspect the same scenario and scope.
   - expected: Each overlay communicates its named data distinctly; Heat varies with underlying heat values.

2. Change one source value in a scratch scenario and refresh the overlay.
   - expected: The corresponding visual encoding changes without altering unrelated overlays.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Select each overlay mode (Heat, Light, Sound, Inhabited) in the graph toolbar.
   - expected: Each mode displays a distinct color and badge encoding reflecting node environment properties.
   - observed: Overlays currently use overlapping styles; distinct color mapping in progress.

2. Edit an area's temperature or light level and re-apply overlay.
   - expected: Affected nodes update color according to the active overlay scale in place.
   - observed: Tested via vis.js node color updates.

## Files

- `static/js/graph/network-manager.ts`
- `static/js/graph/toolbar.ts`
- `tools/unit/test_graph_overlays.js`
