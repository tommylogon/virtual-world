---
group: Environment & Climate
wiki: "[[World Building/Rooms & Areas]]"
---

# Dynamic Area Descriptions from Items and Environment

**Filed**: 2026-07-15
**Priority**: High
**Status**: In Review — implemented (code-verified 2026-08-11). `get_area_description()` in `engine/area_description.py` composes base + item descriptions + environment + characters + exits; environment summary only shows notable conditions.

---

## Summary

Area descriptions are currently static text. Items in the room are listed separately as a flat list after the description. The goal is to make room descriptions **dynamic** — composed from a base description, items' descriptions, environment (temp/smell/sound), and character positions — so that `look` outputs a rich, natural narrative of what's actually in the room and where things are.

## Current State

### How `look` works now (`virtual_world_engine.py:567-686`)

1. Returns `self.current_area.description` (static text)
2. Appends list of players present with their held items
3. Appends environment warnings (hot/cold/toxic/etc.)
4. Appends exit descriptions from door nodes
5. Items are NOT included in the description — they're listed separately via `get_area_items()` (`app.py:277-279`)

### The result

```
A cold living room with wooden floors. The fireplace is unlit...

Tommy is here.

Through the east, the Kitchen is visible beyond.

Items here: fireplace, bookshelf, armchair, grandfather_clock
```

The items are just a flat name list. Their descriptions are not woven into the narrative.

### `get_narration_context_for_area()` (`virtual_world_engine.py:3297-3358`)

This returns a structured dict with `description`, `environment`, `items` (name + description), `characters`, and `recent_events`. It's used for LLM context, but the player-facing `look` doesn't use item descriptions.

## Design

### Phase 1: Compose item descriptions into room description

When the player `look`s, the output should include item descriptions naturally:

```
A cold living room with wooden floors. The fireplace is unlit and the room is filled
with an icy chill.

A worn leather armchair sits by the cold hearth.
Faded photographs hang above the mantlepiece.
An old grandfather clock ticks steadily in the corner.

Tommy is here.

Through the east, the Kitchen is visible beyond.
```

Implementation approach:
- Each item in the room has a `description` field (e.g., "A worn leather armchair sits by the cold hearth.")
- The room has a base description
- `get_area_description()` merges: base description + item descriptions (as a list bullet or natural text) + environment summary + characters + exits
- Item descriptions can optionally include positional/placement language set in the item's description field

### Phase 2: Environment summary in `look`

Instead of just warnings when things are bad, include a brief environment summary:

```
The air is cold and stale. A musty smell hangs in the room. The only sound is dripping water.
```

This would come from `environment.temperature`, `environment.air`, `environment.smell`, `environment.noise` fields.

The format should be dynamic:
- If temp is normal (18-25°C), skip temperature line
- If air is "fresh", skip air quality line
- If noise is "quiet", skip noise line
- Only mention notable environment details

### Phase 3: Item-specific positioning

Future enhancement: Items could have a `position` field that says where they are in the room (e.g., "on the table", "in the corner", "hanging on the wall"), and the description generator would use this to give spatial context. For now, item descriptions should include positional language.

### Phase 4: Default vs dynamic

The base room description serves as a **fallback / foundation**. Items override or add to it. This means:
- Area description: "A cold living room with wooden floors."
- Items: fireplace (description: "The fireplace is unlit..."), armchair ("A worn leather armchair...")
- Combined: "A cold living room with wooden floors. The fireplace is unlit. A worn leather armchair sits by the cold hearth."

If items are taken, moved, or destroyed, the description updates automatically since items are looked up dynamically from graph edges.

## Open Questions

1. **How to merge item descriptions with base description?** 
   - Option A: Base + bullet-point list of item descriptions
   - Option B: Base + natural prose (items' descriptions joined with ". ")
   - Option C: Items have a `when_looking` field vs `description` field
   - **Recommendation**: Option B — items' descriptions should be written as full sentences that can follow naturally. The room description is the anchor, item descriptions are additive prose.

2. **Item description length?** Keep `look` items short (1-2 sentences). Detailed description is for `examine`.

3. **Item order?** By item type (furniture first, then objects, then details) or by position in the room? Start with insertion order (as returned from the graph), add sort by a `priority` field later.

4. **Hidden items?** Hidden items should NOT appear in the room's `look` output.

## Audit

**Status**: Ready to test
**How to test**:
- Load a scenario with items in areas (e.g. mansion2). Type `look`. Verify room description includes item descriptions woven in naturally (not a flat "Items here:" list).
- Verify environment summary appears (temperature, air, smell, noise) only for notable conditions.
- Verify hidden items do NOT appear in the look output.

## Files Affected

- `virtual_world_engine.py` — rewrite `get_area_description()` to compose item descriptions; update `get_narration_context_for_area()` similarly
- `app.py` — the `look` command handler may need simplification since items would be in the description now (line 274-279)