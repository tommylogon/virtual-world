---
type: bug
status: done
area: graph
priority: high
---

# bug-53: Dragging a zone moves the wrong map: the nudge follows the active layer, not the zone's own art

**Filed:** 2026-09-27
**Related:** task-523, bug-51, bug-52
**Fixed:** 2026-09-27

## Symptom

The author dragged the **West woods** zone to reposition it. The result looked
wrong: the two background maps ended up stacked instead of aligned, and the
goblin camp's picture appeared to have followed the drag.

## Cause

`_startZoneDrag` moved the picture with `_nudgeActiveLayer(...)`, which reads
`_active()` — the layer **selected in the panel**. The layer list holds every
scope's map at once, so "active" is a UI selection and says nothing about which
zone is being dragged. Dragging west_woods could therefore shove the goblin camp's
art anywhere, and the zone's own map stayed behind. That is exactly the stacked
pair in the screenshot.

Hand-nudging the rect was also the wrong *mechanism*: since bug-51 the art is
**derived** from the grid plus the scope offset on every load, so a nudged rect is
discarded on the next render — two sources of truth that disagree, and the drag's
own movement lost on reload.

## Fix

One source, one answer, the same as everywhere else:

- `_referenceLayerFor(scopeId, payload)` picks the layer that **is** that scope's
  art by matching the scope's reference image, never by panel selection.
- `_gridPayloadFor(scopeId)` caches the scope's grid payload (the reconcile and
  both fits populate it), so the drag re-places the art synchronously without a
  request per mousemove; the cache is dropped on world refetch, so a grid from
  another scenario can never place a picture.
- `_reapplyZoneArt(scopeId)` re-places the art from the grid rect and the *live*
  offset through the same `_applyReferenceLayout` the load path uses, so nodes and
  art stay in step by construction. `_nudgeActiveLayer` is gone.
- The offset itself is still what gets persisted (`setScopeOffset`); the painter's
  cell coordinates are never touched.

## Verified

Live, on the author's world, dragging west_woods: the offset moved
(-4.39, -3.26) → (-0.71, -1.42) cells and the **west woods** art followed,
(-1271, 889) → (-315, 1367), while the **goblin camp** art stayed exactly where it
was at (-1467, -634). The zone was then put back to the author's own offset.
