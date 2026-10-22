---
type: task
status: todo
area: characters
priority: high
related: ['task-725', 'task-734', 'task-736', 'task-789']
wiki: "[[World Building/Character Creation & Archetypes]]"
---

# task-786: Recall transparency: show why a memory was recalled, automatic and action-driven

**Filed:** 2026-10-12  
**Updated:** 2026-10-21 (aligned with memory-redesign-3.md)  
**Related:** task-685, task-686, task-690, task-714  

<!-- deps:start -->
**Related:** [[task-725-memories-carry-nothing-about-death-vitals-travel-perception-or-resurrection]], [[task-734-knowledge-is-memory-fold-known-recipes-known-places-into-one-prose-data-record-with-episodic-vs-semantic-kinds]], [[task-736-per-character-cognitive-map-a-belief-based-memory-of-places-and-routes-in-the-mind-panel]], [[task-789-consolidate-per-area-observation-memories-into-one-spatial-parent-with-linked-evidence]]
<!-- deps:end -->

## What

Surface why a memory fired in both the prompt telemetry and the editor UI: multi-signal breakdown (spatial proximity, copresent actors, spoken words, current emotions/mood, keyword/tag overlap, recency, and semantic embeddings). Every recalled memory carries its provenance and score breakdown so retrieval stops being a black box.

## Multi-Signal Retrieval Architecture

The retrieval system scores candidates based on weighted contributions from seven distinct channels:

1. **Spatial Proximity (Area match)**: The character is currently in or adjacent to the memory's `location`.
2. **Social Presence (Copresent actors)**: Actors standing in the current room match people mentioned in the memory (`entity_ids` or `about`).
3. **Conversational Echo (Recently heard words)**: Recent hearing buffer matches keywords or embeddings in the memory text.
4. **Emotional Congruency (Mood bias)**: If the character's active emotion is high intensity (e.g. fear, rage), memories with matching emotion tags get a salience multiplier.
5. **Physical Need / Vitals Drive**: High hunger, fatigue, or pain boosts retrieval of memories tagged with relevant resources or hazards (e.g. food locations).
6. **Temporal Recency & Activation**: Fresh memories and memories with high activation (`activation` decaying via power-law curve).
7. **Semantic Embedding Similarity**: Cosine distance via the embedding store for deeper thematic associations.

## Editor & Prompt Requirements

- **Inspector / Mind Panel**: Clicking a recalled memory exposes an inspector chip detailing its score breakdown:
  e.g. `[Match: 88%] 📍 Spatial (Food Storage: +35) · 👥 Social (Mikka: +25) · 🥩 Need (Hunger > 50: +20) · 🧠 Semantic (+8)`.
- **Stream / Raw LLM telemetry**: In the Event Stream, the `recalled: N memories` pill expands to show which memories were pulled into `=== I REMEMBER ===` and the primary signal that triggered each.
- **Negative Knowledge Support (Absence)**: Support `kind: "absence"` memories so that confirmed empty containers or clearings prevent redundant repetitive searching.
- **Sleep Consolidation**: Routine episodic memories consolidate during rest/sleep, fading minor noise while reinforcing emotionally salient events.

## Acceptance

- [ ] Retrieval scoring calculates explicit signal components (spatial, social, conversational, emotional, need, recency, semantic).
- [ ] Memory recall payload passed to the prompt builder includes a `_provenance` breakdown per recalled item.
- [ ] Mind panel displays the match signal tags beside recalled memories.
- [ ] Absence memories (`kind: "absence"`) can be written and surfaced to block obsolete goals.
- [ ] Unit tests verify multi-signal weighting and that mood-congruent memories receive their salience boost when emotion intensity >= 6.
