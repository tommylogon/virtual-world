---
type: task
status: todo
area: docs
priority: low
wiki: "[[Feature Map]]"
---

# task-782: Retire Connections.md or absorb what it uniquely holds

**Filed:** 2026-10-11
**Related:** 

## What

World Building/Connections.md (renamed from Doors & Connections) is a legacy architecture note that still describes a door node type and stale line numbers. Ways.md now covers the way behaviour and authoring surface, and Graph System.md covers the node and edge model, so most of it is duplicated or wrong. Decide the two things it still uniquely holds, the area-way-area four-edge layout and the graph state colours, then move them into Graph System.md (or Ways.md) and delete the page, retargeting inbound wikilinks and regenerating Connected blocks.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — this task retires or relocates a documentation page and updates wikilinks; it does not change the live graph or connection UI.

Current availability: Ways.md covers current way behavior and Graph System.md covers node/edge structure, while Connections.md retains stale door terminology and unique area-way-area and state-color details. The page consolidation is not claimed as complete.

Why no browser UI: the deliverable is vault content and links. Browser interaction cannot show whether all note references resolve or whether the obsolete page's unique facts were preserved.

Alternative verification steps:
1. Compare the four-edge area-way-area layout and graph state colors in Connections.md with the current Graph System.md/Ways.md destination before retiring the old page.
   - expected: both unique facts have one accurate home; no stale `door` node claim is copied forward.
2. Retarget every inbound wikilink and regenerate the affected `## Connected` blocks.
   - expected: no surviving link points at the retired page and the destination notes list their current connections.
3. Run `npm run precommit`.
   - expected: vault guards report no broken links, duplicate notes, or stale generated Connected blocks.

This section is not a claim that planned documentation changes are complete today.
