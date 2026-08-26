---
group: Prompt & Narrative Quality
---
# Entertainment Vital: Exploration & Novelty

**Filed**: 2026-07-30 (updated 2026-08-02)  
**Priority**: Low  
**Status**: Review — all checklist items implemented (moved for verification)  

---

## Status note (2026-08-02)

Moved back to `todo/` during review: the area-visit half is fully implemented
(`movement.py:226-240` first-visit boost + curious/homebody/wanderlust;
`tick_manager.py:131-143` impatient/patient/adventurous modifiers;
`prompt-builder.js:677-680` low-Entertainment drive text; `visited_areas` tracked),
but the **item-discovery half was dead code**: `player.discovered_items` was declared
(`player.py:112`) and serialized (`player.py:370`) but never populated.

**Now implemented (2026-08-02):**
- **Item discovery:** `ItemActions._register_item_discovery` (`engine/item_actions.py`)
  adds a never-seen item to `discovered_items` and grants a base +8 Entertainment
  boost (×1.5 for `curious`, 0 for `homebody`, clamped at 100). Hooked into both
  examine (`get_item_desc`) and successful take. Covered by `TestItemDiscovery` in
  `tests/test_item_actions.py`.
- **Meeting a new character:** `Player.register_first_meeting` (`player.py`) creates
  the relationship entry (no interaction-count bump) and grants a base +10 boost
  (×1.5 `curious`, 0 `homebody`, clamped at 100). Called from the area-description
  "players here" path (`area_description.py`) and also fires via `update_relationship`.
  Covered by `TestFirstMeeting` in `tests/test_player_meeting.py`.
- **Exploration trait definitions:** the six traits referenced by the existing
  engine code (`curious`, `adventurous`, `homebody`, `wanderlust`, `impatient`,
  `patient`) were **missing from `TRAIT_DEFINITIONS`** (`engine/traits.py`) — so
  `has_effect(player, "curious")` etc. always returned False and the whole
  trait-driven half was inert. All six are now defined (category `exploration`),
  which activates the area-visit and per-tick modifiers too.

Remaining checklist items ("on_area_entered event", prompt-side trait behavior text)
are either already covered by existing wiring or noted in the Requirements section —
verify and close.

---

## Summary

The Entertainment vital should increase naturally when characters visit new areas, find new items, or experience novel events — and be affected by character traits. Low Entertainment should prompt LLM agents to seek novelty (try new things, go new places) rather than just applying a stat penalty.

---

## Problem

The Entertainment vital currently has a baseline decay but no natural way to increase it (only manually via actions like playing games). Going to a new area should be inherently entertaining. A character who never leaves the starter room should lose Entertainment over time.

There's also no trait-driven variation in how characters seek novelty — an impatient character should act differently from a patient one when bored.

## Requirements

### Entertainment gain sources
- Visiting an area for the first time → Entertainment boost
- Finding a new item → small Entertainment boost
- Meeting a new character → Entertainment boost
- Diminishing returns: same area visited repeatedly gives less/no boost
- Track visited areas per character: `player.visited_areas: set[str]`
- Track discovered items per character for novelty bonus
- Event: `on_area_entered` triggers Entertainment update

### Traits
| Trait | Effect on Entertainment | Effect on behavior |
|-------|------------------------|-------------------|
| `curious` | +50% from new places/things | More likely to examine items, explore exits |
| `adventurous` | Entertainment doesn't decay in unfamiliar areas | More willing to take risks, go somewhere unknown |
| `homebody` | No boost from new places, slower decay in home area | Reluctant to leave familiar areas |
| `wanderlust` | Gains Entertainment from moving between areas even if visited before | Prefers to keep moving, rarely stays put |
| `impatient` | Faster Entertainment decay when inactive; smaller boost from passive activities (reading, waiting) | More likely to take items, use items, or go somewhere without careful thought — acts before considering consequences |
| `patient` | Slower Entertainment decay; can tolerate repetitive activities longer | Less driven by boredom, can stay in one area longer |

### Prompt engineering: Low Entertainment drives behavior
Low Entertainment should change what agents do, not just apply a stat penalty:

- **Entertainment < 50**: "You're starting to get bored. Consider doing something new or going somewhere else."
- **Entertainment < 25**: "You're bored. Routine feels stifling. You're drawn to try something different — anything to break the monotony."
- **Entertainment < 10**: "You're desperate for stimulation. Staying in place any longer is unbearable. Take action — go, examine, or use."

These are injected into the agent prompt alongside the vital description, influencing decision-making. The `impatient` trait amplifies this — characters with it skip the "consider carefully" step and act faster.

### Implementation notes
- Entertainment thresholds are checked in `PromptBuilder.describeVitals()` (or a new `buildEntertainmentContext()`)
- The low-Ent drive text goes into the prompt's `=== YOUR STATE ===` section
- Trait effects on behavior are expressed as additional prompt instructions (e.g. "You are impatient — you act quickly without overthinking.")
- `engine/tick_manager.py` handles the per-tick decay and trait modifiers

## Related

- [[review/characters/task-28-character_needs_system|task-28: Character needs system]]
- [[todo/gameplay/task-131-stateful-actions-over-time|task-131: Stateful actions]] — impatient trait affects how quickly characters interrupt activities
- `player.py` — vitals, traits
- `engine/tick_manager.py`
- `static/js/agent/prompt-builder.js` — describeVitals() and prompt injection
