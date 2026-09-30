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

## Ways (doors, vents, facing)

### Normal rooms

- **`examine door`** — AT the way; if open/see-through, beyond visibility ([[dev_tasks/review/ui/task-201-area-visibility-beyond-ways|task-201]]) uses this viewpoint.
- **`open north`** — walk to north exit, AT it, toggle state.
- **`go north`** — walk to exit, AT it, traverse; arrive **AT the same way node** from the far side.

### Relative facing — left, right, forward, back

There is no turn-in-place verb. A character's orientation **is the heading of
its last crossing**, stamped onto the character when it moves, and it changes
only by moving again. So "left" is not stored, not guessed from the room, and
not a property of the door:

    come from the south  ->  travel north  ->  facing north
    so  forward = north    right = east    left = west    back = south
    come from the west   ->  travel east   ->  facing east
    so  forward = east     right = south   left = north   back = west

The resolved cardinal is then handed to **ordinary exit resolution**, so the
words *alias* the area's directions and never replace them. "Go left" becomes
"go west", and the room still calls the door whatever the author called it —
the exits list is never rewritten to say `back`/`forward`.

**Facing lives on the `Player`** (`player.facing`, plus `player.entered_from_way`
so the heading can be explained rather than merely asserted) and serialises with
the save. A character that has never moved has `facing = None`, and the relative
words say so — *"this character has not moved yet, so it has no facing"* — rather
than failing with a generic "can't go there".

**Authoring.** A way has an optional `cardinal` on its connection edge, read by
`engine/facing.py::edge_cardinal` (which falls back to `direction` when the
handle *is* a cardinal). Without a cardinal the way is simply never rotated —
the words stay literal and nothing is invented. Two rules the tagless design
keeps:

- **Vertical and diagonal ways are never rotated.** `up`/`down` are not on the
  ring; a diagonal produces no left/right rather than a false one. An eight-way
  ring would be a separate decision.
- **Standing AT a way is not the same as arriving through it.** Walking up to a
  door to examine it leaves facing alone.

**The `transit` tag is gone** (task-313). It was declared `applies_to:
["ways"]` while its only consumer read it off the *area*, so
`get_transit_roles` always returned `None` and the feature had never run in any
shipped content. It also *replaced* a way's handle instead of aliasing it,
hardcoded exactly two ways, and derived "back" from the way a character stood
at rather than the way it came through. Relative facing needs no tag at all, so
the tag, `is_transit_area`, `get_transit_roles`, `resolve_transit_movement` and
both handle-renaming branches (server description and agent prompt) are deleted.
Re-introducing it as an opt-in would be a second source of truth for a thing
that is now the default.

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
| `engine/character_spatial.py` | Edges, phrases, approach helpers |
| `engine/facing.py` | The cardinal ring and the `left`/`right`/`forward`/`back` rotation; `edge_cardinal()` is the one reader both sides share |
| `engine/movement.py` | `approach_way` on go/open/close; AT on arrival; drag `way_id`; stamps `facing` |
| `engine/matching.py` | `resolve_exit()` — relative words resolve as an ordinary direction, tier 1b |
| `engine/item_actions.py` | examine, use-on, give, steal, put/place |
| `engine/combat.py` | attack → `approach_character` |
| `engine/grapple.py` | grab → beside; drag → AT way |
| `engine/area_description.py` | People lines + `spatial_position_phrase()` |
| `tests/test_facing.py` | The ring, the wiring, persistence, and the real labs vent |
| `tests/test_character_spatial.py` | Ways, relative facing, items, characters, examine room clear |
| `tests/test_grapple.py` | Dragged target AT way |

---

## Related docs

- [[World Building/Doors & Connections|Doors & Connections]] — way graph structure
- [[AI & Narration/Agent Engine|Agent Engine]] — room context + prompts
- [[Rules Engine/Combat System|Combat System]] — attack positioning
