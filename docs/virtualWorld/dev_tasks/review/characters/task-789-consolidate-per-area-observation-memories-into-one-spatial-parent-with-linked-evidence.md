---
type: task
status: review
area: characters
priority: high
related: ['task-725', 'task-786', 'task-734']
wiki: "[[World Building/Character Creation & Archetypes]]"
---

# task-789: Consolidate per-area observation memories into one spatial parent with linked evidence

**Filed:** 2026-10-12  
**Updated:** 2026-10-21 (aligned with memory-redesign-3.md schema)  
**Related:** task-688, task-690, task-725, task-734, task-736, task-786  

<!-- deps:start -->
**Related:** [[task-725-memories-carry-nothing-about-death-vitals-travel-perception-or-resurrection]], [[task-786-recall-transparency-show-why-a-memory-was-recalled-automatic-and-action-driven]], [[task-734-knowledge-is-memory-fold-known-recipes-known-places-into-one-prose-data-record-with-episodic-vs-semantic-kinds]]
<!-- deps:end -->

## What

Adopt the `memory-redesign-3.md` schema for observation memories: consolidate per-item area sightings into **one spatial parent scene memory per area visit** (`kind: "episodic"`, `event: "scene_observed"`), with individual observed items, exits, and environment conditions stored as structured data and linked evidence rather than 10 separate flat memory entries.

## Why

Currently, when a character enters an area like Food Storage, the engine writes 10 to 15 separate observation memories:
- `👁️ You have seen bacon_rasher in the Food Storage.`
- `👁️ You have seen Hanging Dried Meats in the Food Storage.`
- `👁️ You have seen cheddar_cheese in the Food Storage.`
...etc.

When the memory retrieval step runs, these 10 trivial item memories consume the entire memory retrieval budget (capped at 10 items in `=== I REMEMBER ===`). As a result, the character's real backstory, personal relationships, secrets, and quest goals are completely locked out of the prompt.

## How (Aligned with memory-redesign-3.md)

1. **One Consolidated Scene Record**:
   When `observe_area` runs in `engine/observation.py`, instead of emitting N independent observation memory objects into `player.memories`, it records or updates a single episodic scene observation for that area:
   ```json
   {
     "id": "mem_<ulid>",
     "kind": "episodic",
     "category": "resource",
     "type": "observation",
     "text": "Observed Food Storage: cool and dimly lit, holding dried meats, cheeses, honey, and fresh fruit.",
     "data": {
       "event": "scene_observed",
       "area": "area_food_storage",
       "environment": { "light": "dim", "smell": "dried meat, spices", "temperature": 17.9 },
       "items_seen": ["bacon_rasher", "cheddar_cheese", "heather_honey", "cod", "apple"],
       "exits_seen": [{ "direction": "south passage", "target": "Cooking Area" }]
     },
     "location": "area_food_storage",
     "observed_at": 1792576376,
     "importance": 4,
     "tags": ["observed", "area:food_storage"]
   }
   ```
2. **Reinforce in place**: Re-visiting the same unchanged area updates `observed_at`, bumps `reinforcements`, and refreshes the text in-place rather than appending new rows.
3. **Preserve Sub-Item Indices**: Fast lookups like `player.has_seen(item_id)` and novelty curves continue to check `data.items_seen` so no existing engine queries break.

## Acceptance

- [ ] `engine/observation.py:observe_area` produces a single consolidated scene memory per area visit.
- [ ] Multiple items observed in the area are recorded in `data.items_seen` and summarized in the record's rendered `text`.
- [ ] Memory retrieval returns the single consolidated area memory, leaving the remaining memory slots available for narrative/social/goal memories.
- [ ] Existing `player.has_seen()` and novelty decay tests continue to pass.
- [ ] Zero em-dashes introduced into task or code files.
