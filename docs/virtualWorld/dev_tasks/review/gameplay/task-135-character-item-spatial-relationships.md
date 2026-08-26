---
group: Agent AI & Behavior
wiki: "[[dev_tasks/level-design-workflow]]"
---
# Character ? Item Spatial Relationships

**Filed**: 2026-07-30  
**Priority**: Low  
**Status**: In Review — ways + items + characters + approach-on-action implemented 2026-08-13; docs [[Gameplay/Character Spatial Position|Character Spatial Position]]; pytest `tests/test_character_spatial.py` (14+), `tests/test_grapple.py` drag AT; browser E2E pending  

**Canonical doc:** [[Gameplay/Character Spatial Position]]

---

## Summary

When a character interacts with an item (examines it, uses it, stands on/near/under it), create a spatial edge between the character and that item — `character AT piano`, `character UNDER chandelier`, `character ON trap`. This gives other characters a sense of where people are positioned relative to objects in the room, beyond just "they're in the same area."

**Same problem class as transit areas** ([[review/gameplay/task-224-transit-areas-entry-relative-exits|task-224]]): in a text world there is no implicit geometry — you only get "where am I relative to X?" if the engine **stores a relation**. Task 135 = relations to **items in a room**. Task 224 = relations to **which exit you came from in a corridor**. Both are pun-intended *spatial relationships*.

---

## Implemented (2026-08-13)

See [[Gameplay/Character Spatial Position]] for full behavior tables.

- **`engine/character_spatial.py`** — `approach_way` / `approach_item` / `approach_character`; one spatial edge per player; witness phrases; transit back/forward
- **Physical actions walk you there** — open/close/go/use-on/give/steal/grab/attack/put do not require `examine` first
- **`examine room`** clears position; **`look`** does not
- **Serialization** — `at_way_id` + `spatial_position` on each player
- **Agent Lens** — `room-context.js` people lines show spatial suffix; `system-prompt.js` rules updated
- **Grab drag** — dragged characters AT arrival way

### Remaining / polish

- Tag transit areas in scenario data (Task 18 ventilation shaft)
- Browser E2E verification
- Optional: NPC behaviors set spatial position when they act

---

## Requirements (original design)

### Spatial relationship edge types (already exist in graph.py)
| Edge type | Meaning | Example |
|-----------|---------|---------|
| `at` | Standing at/near, engaging with | `Jake AT piano`, `Butcher AT bookshelf` |
| `on` | Standing on top of | `Jake ON trapdoor` |
| `under` | Underneath | `Jake UNDER chandelier` |
| `behind` | Behind | `Jake BEHIND counter` |
| `beside` | Next to | `Jake BESIDE fireplace` |

### How the correct edge type is determined

Items can have tags that hint at their natural spatial position:

| Tag | Default edge type | Example |
|-----|-------------------|---------|
| `in_roof` / `on_ceiling` | `under` | Chandelier, hanging lamp, ceiling fan |
| `in_floor` / `on_ground` | `on` (or `at` if too big to stand on) | Trapdoor, rug, grate |
| (no tag) | `at` | Default — examine or use sets `at` |

- The player can override with explicit positioning in their action: `examine chandelier from below` ? `under`, `stand on rug` ? `on`
- The action parser looks for spatial keywords (on/under/behind/beside/at) in the command and uses that as the edge type

### Character AT way (doors, vents, transit)

| Situation | Edge | Effect |
|-----------|------|--------|
| `open` / `close` / `go` / use-on door | `character AT way` | Walk to opening as part of the action |
| `examine door` | `character AT way` | Look without opening |
| Door open + you're AT it | (edge + task-201) | Beyond visibility from this viewpoint |
| Transit area + AT entry | back / forward | [[review/gameplay/task-224-transit-areas-entry-relative-exits|task-224]] |

### Witness + targeting

People lines: `the stranger at the north`, `the woman beside the piano`. Stranger labels use `unknown_display_name()`; spatial suffix gives agents a **handle + position** for commands like `attack the man`, `examine the north`.

## Related

- [[Gameplay/Character Spatial Position]] — **main reference**
- [[World Building/Doors & Connections]]
- [[AI & Narration/Agent Engine]]
- [[review/ui/task-201-area-visibility-beyond-ways|task-201]]
- [[review/gameplay/task-224-transit-areas-entry-relative-exits|task-224]]
