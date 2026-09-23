---
type: bug
status: review
area: bugs
priority: medium
---

# bug-45: Disabling physics on a way still gets pushed

**Filed:** 2026-09-23
**Related:** 

## Goal

Reported: 'disable physics on ways does not work, I tried to place a way where I want it and it still gets physics pushed'. Cause: applyCardinalLayout (static/js/graph/layout-engine.js) rebuilt wayUpdates/looseUpdates with an anchor position and physics:true, fixed:{x:false,y:false}, overriding the inspector's central_gravity_enabled=false freeze; GraphRelativeLayout.apply also positioned children without checking the flag. Fixed: the cardinal layout now filters out any node with central_gravity_enabled === false, relative-layout.apply skips frozen nodes (and records no offset, so the follow pass ignores them), and dragging a frozen node now writes its position to properties.x/y so the placement survives a reload.

## Acceptance

- TODO

## Verification

Reproduced and fixed live in the running app, through the same API the inspector's "Physics enabled" checkbox uses:

1. `api.updateNode(way, { properties: { central_gravity_enabled: false } })` -> rebuilt graph -> dataset node `physics=false`.
2. `moveNode(way, 4321, -1234)`, then 2.5s of simulation -> **0px drift**.
3. Forced a full `loadGraphData()` rebuild (what a state refresh does) -> **0px** movement, held at exactly (4321, -1234).
4. The flag was restored afterwards, so the world was left as found.

For contrast, an unfrozen way is still re-anchored by the cardinal layout (it moved 354px when moved off its anchor), which is the intended behaviour for a way that has not been frozen.

Also added: dragging a **frozen** node writes its position to `properties.x/y` (`GraphRelativeLayout.frozenDropOps` / `persistFrozenDrop` on `dragEnd`), because nothing else restores it — the layout deliberately leaves frozen nodes alone, so without this a page reload would lose the placement.

`node tools/unit/run.cjs` -> 157 passed (two new cases: a frozen node is not repositioned and gets no offset; only frozen nodes produce position-save ops).
