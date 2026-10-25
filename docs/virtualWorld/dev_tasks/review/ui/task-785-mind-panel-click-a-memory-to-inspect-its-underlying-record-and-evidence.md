---
type: task
status: review
area: ui
priority: medium
related: ["'task-691'", "'task-730'", "'task-787'", 'task-691', 'task-714', 'task-730', 'task-787', 'task-788']
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-785: Mind panel: click a memory to inspect its underlying record and evidence

**Filed:** 2026-10-12
**Related:** task-691, task-727, task-734

<!-- deps:start -->
**Related:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-730-chat-based-interactive-memory-creation-the-character-reacts-in-voice-to-author-new-memories]], [[task-787-mind-panel-migrate-the-remaining-mind-surfaces-out-of-the-bio-and-advanced-tabs]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-788-mind-panel-fullscreen-mode]]
<!-- deps:end -->

## What

Clicking a memory shows the record behind it (tick, entity_ids, location, source, kind, visits, tags, and the lived_log entries) as inspectable data, not only prose.

## Why

A memory in VirtualWorld is backed by a structured record (tick, location, kind, entity_ids, tags, visits) and grounded in actual lived turns. Showing only the narrative prose conceals why a memory exists, which entities it refers to, and what underlying turn generated it. Making the record inspectable alongside matching lived-log trace entries gives authors and debugging designers transparency into character memory formation.

## How

1. In `static/js/inspector/mind-view.ts`, implement `_recordAndEvidenceHtml(m, charName)`:
   - Extract memory attributes: `id`, `tick` (with formatted game time), `source`, `type`, `category`, `kind`, `location`, `visits`, `entity_ids`, and `tags`.
   - Match against `player.lived_log`: find lived-log entries within +/- 2 ticks matching location or `rel:` relationship tags.
   - Format matching entries into a `lived-log trace` list showing tick, kind, what, why, area, and with.
   - Wrap the inspection payload in an expandable `<details class="mind-underlying-record">` element.
2. In `_detailHtml(m, all)`, mount `_recordAndEvidenceHtml(m)` directly in the memory detail column so selecting any memory card reveals its structured record and evidence.

## Steps to verify

1. Select a character and open Inspector -> Mind -> Memories tab.
   - expected: Clicking any memory card opens the detail column with Dynamics, Emotional encoding, Connections, and an expandable 'Underlying record & lived-log evidence' disclosure.
   - observed: Verified live; clicking a card opens `<details class="mind-underlying-record">` rendering id, tick, source, type, location, visits, entity_ids, tags, and matched lived-log entries.
2. Select a memory that has no matching lived-log entries.
   - expected: Detail panel renders record fields with an explicit empty trace message ('No lived-log entries linked to this memory').
   - observed: Verified; empty fallback element renders with text-muted styling without fabricating event data.

## Acceptance

- [x] Clicking a memory card renders the underlying record attributes (id, tick, source/type, category, kind, location, visits, entity_ids, tags) as inspectable key-value rows.
- [x] Matches and displays related entries from `player.lived_log` within a 2-tick window matching location or relationship tags.
- [x] Displays an explicit empty state when no lived-log evidence is present.
- [x] Selecting a different memory updates the record and evidence view immediately.
- [x] TypeScript compiles cleanly (`npm run build:ts`) and unit tests pass.

## Files

- `static/js/inspector/mind-view.ts`

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
