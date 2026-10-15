---
type: task
status: todo
area: ui
priority: medium
---

# task-785: Mind panel: click a memory to inspect its underlying record and evidence

**Filed:** 2026-10-12
**Related:** task-691, task-727, task-734

## What

Clicking a memory shows the record behind it (tick, entity_ids, location, source, kind, visits, tags, and the lived_log entries) as inspectable data, not only prose.

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

Intended UI home: Select a character → Inspector → 🧠 Mind → Memories tab → click a memory card → memory detail/evidence panel.

Current availability: The task says cards currently show prose only; the structured record and `lived_log` evidence view are planned and not claimed as present.

Live steps when available:
1. Open Mind → Memories for a character with a memory carrying a tick, entity, location, source, kind, visits, and tags; click that card.
   - expected: the detail panel shows those fields from the selected memory record and the related lived-log entries, without changing the card's prose or creating a second memory record.
2. Click a second memory card and compare its evidence fields.
   - expected: the panel switches to the second record's evidence; no fields from the first memory remain visible.
3. Open the detail panel for a memory with no lived-log entries.
   - expected: the panel shows the available record fields and an explicit empty-evidence state, not fabricated event data.
4. Close the detail panel, change the memory filter, and select another result.
   - expected: filtering and selection continue to work and the evidence always belongs to the currently selected card.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
