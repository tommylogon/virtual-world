# Character Spatial Position

**Task:** [[dev_tasks/review/gameplay/task-135-character-item-spatial-relationships|task-135]] (ways + items + characters) · transit: [[dev_tasks/review/gameplay/task-224-transit-areas-entry-relative-exits|task-224]]

Text worlds have no implicit geometry. VirtualWorld stores **where a character is relative to something in the room** as graph edges from the player node:

| Edge type | Meaning | Example witness line |
|-----------|---------|----------------------|
| `at` | At/near, engaging | `Jake at the north` · `Jake at the piano` |
| `on` | Standing on | `Jake on the trapdoor` |
| `under` | Underneath | `Jake under the chandelier` |
| `behind` | Behind | `Jake behind the counter` |
| `beside` | Next to (people, objects) | `Jake beside the woman` |

**One anchor at a time** — a new positioning action clears the previous edge. Source of truth: `engine/character_spatial.py`.

---

## Core rule: physical action walks you there

You do **not** need a separate `examine` before `open`, `go`, `give`, etc. Any action that physically involves something in the room **steps you to it** and sets the spatial edge.

| Action | Position set |
|--------|----------------|
| `open` / `close` | **AT** the way |
| `go` / `crawl` / `climb` / `jump` / `dash` | **AT** the way (on approach + on arrival in new room) |
| `use [item] on [door/way]` | **AT** the way |
| `use [item] on [room item]` | **at/on/under/…** from item tags + phrasing |
| `use [item] on [person]` | **beside** them |
| `give` / `steal` | **beside** target |
| `grab` (success) | grappler **beside** target |
| `attack [person]` | **beside** target |
| `put` / `place X on table` | relation on that surface (`on`, `under`, `at`, …) |
| `examine [way/item/person]` | same as above, look-only |
| `examine room` / `here` / area name | **clears** position (step back, survey room) |
| `look` | no change (glance from current spot) |

Plain `use` on inventory-only items (Create Flame, eat ration) does **not** set room position.

Implementation hooks: `approach_way`, `approach_item`, `approach_character` in `character_spatial.py`; called from `engine/movement.py`, `engine/item_actions.py`, `engine/combat.py`, `engine/grapple.py`.

---

## Ways (doors, vents, transit)

### Normal rooms

- **`examine door`** — AT the way; if open/see-through, beyond visibility ([[dev_tasks/review/ui/task-201-area-visibility-beyond-ways|task-201]]) uses this viewpoint.
- **`open north`** — walk to north exit, AT it, toggle state.
- **`go north`** — walk to exit, AT it, traverse; arrive **AT the same way node** from the far side.

### Transit areas

Tag the area `transit` or `passage` (or `transit: true` on properties). When **AT an entry way**:

- Exit labels become **`back`** (way you're AT) and **`forward`** (other connection).
- `go back` / `go forward` resolve via `resolve_transit_movement()`.

See [[dev_tasks/review/gameplay/task-224-transit-areas-entry-relative-exits|task-224]] for authoring notes.

---

## Items

Default relation from item tags (`default_relation_for_item()`):

| Tags | Default relation |
|------|------------------|
| `in_roof`, `on_ceiling`, `ceiling` | `under` |
| `in_floor`, `on_ground`, `floor` | `on` |
| (none) | `at` |

Override with phrasing: `examine chandelier from below` → `under`; `stand on rug` → `on`.

---

## Characters

- **`beside`** is the default relation to another person (examine, give, steal, grab, attack, use-on).
- **`examine self`** does not set position.

### Grab + drag

When a grappler `go`s through a way, **dragged targets** are moved to the new area and set **AT the same way** on arrival (`grapple.drag_all(..., way_id)`).

---

## Witness text + targeting

Room look and Agent Lens append a spatial suffix to each person line:

```text
People here:
  - the woman (awake) beside the piano — A musician in a green cloak.
  - the stranger at the north — A tall figure in a dark coat.
```

### Stranger labels

Unmet characters use `Player.unknown_display_name()` (`the man`, `the woman`, `the stranger`, …) — **never the database name** until met. The spatial suffix uses the same anonymous label for character anchors when the viewer hasn't met them.

### Why this helps targeting

1. **Room context shows handle + position together** — `"the man at the north"` tells the agent both *who* (appearance label) and *where* (exit handle).
2. **Parser resolution** — `NameMatching._match_character_name()` resolves `attack the tall man`, `give key to the woman`, etc. by name, substring, fuzzy name, and **description words** in the same area.
3. **Structured state** — each player in API state carries:
   - `at_way_id` — way node id when AT a door (legacy/convenience)
   - `spatial_position` — `{ relation, target_id, target_type, target_name }` for full position

Agents are instructed in `system-prompt.js`: physical actions walk you there; `examine room` steps back.

---

## API / serialization

Per player in world state (`engine/serialization.py`, `engine/player_manager.py`):

```json
{
  "at_way_id": "way_Lab A_vent",
  "spatial_position": {
    "relation": "beside",
    "target_id": "player_Jane",
    "target_type": "character",
    "target_name": "the woman"
  }
}
```

`spatial_position` is `null` when nowhere specific in the room.

Frontend mirror: `static/js/agent/prompt-builder/room-context.js` (`spatialPositionSuffix` on people lines).

---

## Code map

| Module | Role |
|--------|------|
| `engine/character_spatial.py` | Edges, phrases, approach helpers, transit roles |
| `engine/movement.py` | `approach_way` on go/open/close; AT on arrival; drag `way_id` |
| `engine/item_actions.py` | examine, use-on, give, steal, put/place |
| `engine/combat.py` | attack → `approach_character` |
| `engine/grapple.py` | grab → beside; drag → AT way |
| `engine/area_description.py` | People lines + `spatial_position_phrase()` |
| `tests/test_character_spatial.py` | Ways, transit, items, characters, examine room clear |
| `tests/test_grapple.py` | Dragged target AT way |

---

## Related docs

- [[World Building/Doors & Connections|Doors & Connections]] — way graph structure
- [[AI & Narration/Agent Engine|Agent Engine]] — room context + prompts
- [[Rules Engine/Combat System|Combat System]] — attack positioning
