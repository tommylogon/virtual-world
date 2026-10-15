---
type: task
status: todo
area: characters
priority: medium
---

# task-789: Consolidate per-area observation memories into one spatial parent with linked evidence

**Filed:** 2026-10-12
**Related:** task-688, task-690, task-725, task-734, task-736

## What

Add a spatial consolidation tier: one parent memory per area summarising its observed elements, with per-subject observations retained as linked evidence; additive, never superseding has_seen, novelty or the minimap.

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

Intended UI home: select a character → Mind panel → spatial observations/memories for a known area. The area summary belongs with the character's existing observations; linked subject memories remain the evidence beneath it.

Current availability: the card proposes one spatial parent memory per area with linked observations. It explicitly preserves `has_seen`, novelty, and the turn minimap; the consolidated parent view is not claimed as available.

Live steps when available:
1. In a scratch area containing a named object and a distinct feature, let one character observe both, then open that character's Mind observations for the area.
   - expected: one area-level parent summarizes the two observed elements and links to the two subject-specific evidence memories.
2. Have the same character observe a third element in the same area and reopen the entry.
   - expected: the existing area parent updates and links the new evidence; a second competing parent for the same area is not created.
3. Select a second character who has not observed the area.
   - expected: the first character's area summary and evidence do not appear in the second character's Mind panel.
4. Use the current minimap and `has_seen`/novelty views before and after consolidation.
   - expected: their existing exploration behavior is unchanged; consolidation adds a summary layer without replacing those sources.

This section is not a claim that planned UI exists or works today.
