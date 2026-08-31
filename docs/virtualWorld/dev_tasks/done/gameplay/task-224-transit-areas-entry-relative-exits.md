---
group: Gameplay
wiki: "[[dev_tasks/level-design-workflow]]"
---

# Transit Areas — Entry-Relative Exit Labels (back / forward)

**Filed**: 2026-08-13  
**Priority**: Medium  
**Status**: Done — implemented 2026-08-13 (`get_transit_roles`, `go back`/`forward`, transit tag); unit tests green (`tests/test_character_spatial.py`, 16 passed). Moved to review/ 2026-08-16 — pending browser E2E walkthrough (Task 18 shaft no longer exists in the New Dawn scenario; natural candidate: Frozen Stream Crossing).

---

## Problem

**Between-rooms** are a first-class level-design pattern: ventilation shaft crawl, stair landing, elevator cage, chase tunnel, free-fall sequence (call out each turn), etc. The player stands in a **transit area** with two (or more) ways out.

From **outside**, both entries can share narrative commands (`enter vent`) — different areas, no collision.

From **inside**, the headscratcher:

- "Exit the vent ahead" is **relative to entry** — if Jane entered from Room 4, the grate back is "behind"; if she entered from Room 3, the same opening is "ahead."
- Fixed labels like `Vent 1` / `Vent 2` work for authors and parsers but break immersion — Jane has no reason to know arbitrary IDs.
- Compass (`north` / `east`) is wrong for underground labs — no in-fiction orientation.
- Destination-sensory names (`flutter`, `grate`) work today but fail on first visit and don't generalize to symmetric tunnels.

Text worlds lack 2D spatial relations; **entry-relative labeling** is the clean fix for transit areas.

## Goal

When a character enters a tagged **transit area**, remember **where they came from** via **character AT entry way** (graph edge — see [[todo/gameplay/task-135-character-item-spatial-relationships|task-135]]). While inside, the way they're AT is **back**; the other connection is **forward**.

Prefer **`character AT way`** over a `transit_entry` player JSON blob — same spatial system as examine-at-door and task-201 viewpoint.

| Role | Prose (example) | Command handle |
|------|-----------------|----------------|
| **Back** | the opening you crawled in through | `back` (alias to real direction) |
| **Forward** | the duct continues toward … (from `visible_in_direction`) | sensory word or `forward` |

No compass. "Ahead" and "behind" follow **entry vector**, not map north.

## Example — Task 18 ventilation shaft

```
Room 4  ──[enter vent]──►  Ventilation shaft (transit)  ──►  Room 3
                              ▲
                    entered from Room 4
```

Jane enters from Room 4. Inside shaft, prompts show:

- `[back]` — square grate back to the room you came from (→ Room 4)
- `[forward]` — cooler draft, flickering light ahead (→ Room 3)

She enters from Room 3 → labels swap. Same graph, same way nodes, different prompt handles.

## Requirements

### 1. Transit area tag

- Area tag or property: `transit` (or `passage`, `corridor` — pick one in implementation)
- Optional subtypes later (`freefall`, `chase`) — out of scope for v1

### 2. Entry memory → **character AT way**

On successful `go` / crawl / climb **into** a transit-tagged area via way `W`:

- Create graph edge: **`character AT W`** (or `beside W` — pick one in implementation)
- On leave (any exit): clear character↔way spatial edges (shared with task-135 movement hook)

Optional compat: mirror `from_area` in edge lookup for prompts if needed; primary source of truth is **AT way**.

~~Runtime JSON blob~~ (superseded by AT way):

```json
{
  "transit_entry": {
    "area": "Task 18 - ventilation shaft",
    "from_area": "Task 18 - Room 4",
    "via_way_id": "way_task_18__vent_shaft_2",
    "via_command": "enter vent",
    "tick": 42
  }
}
```

### 3. Exit presentation (human look + agent room context)

Resolve exits by spatial relation:

- Way player is **AT** → **back** handle + "the opening you came through"
- Other way(s) in area player is **not** AT → **forward** (+ `visible_in_direction` prose)

When building exits for a transit area, use AT-way lookup (not `from_area` string compare):

Prose templates (defaults, overridable per area in properties?):

- Back: `"the opening you came through"`
- Forward: use existing `visible_in_direction` or target area first-impression

Bracket handles in prompt: `[back]`, `[forward]` — LLM-friendly.

### 4. Parser / movement aliases (transit areas only)

Inside transit areas, accept:

- `go back` / `back` → resolve to the way the character is **AT**
- `go forward` / `forward` → resolve to the other way connection (if exactly two exits; if 3+, forward = ambiguous — document or disable)

Must not affect non-transit areas.

### 5. Authoring (inspector)

- Area tag checkbox: **Transit area** (entry-relative exits)
- Optional area property overrides for back/forward prose templates
- Way commands on outer sides stay author-defined (`enter vent` both sides OK)
- Document pattern in level-design workflow wiki

### 6. Interim authoring (until implemented)

Destination-sensory commands from inside shaft (`flutter` / `grate`) — no engine change. Link from this task as workaround.

## Out of scope (v1)

- Full 2D/spatial coordinate system
- Compass directions
- Replacing transit areas with multi-turn way-only crawl (task-131 activities) — complementary, not exclusive
- Dynamic renaming of graph edge labels (editor stays author-facing; prompts are player-facing)

## Implementation sketch

| Layer | Files |
|-------|--------|
| Entry memory write/clear | `engine/movement.py`, `player.py` |
| Exit rebuild | `engine/area_description.py` (`build_exits_for_area`, look exits block) |
| Agent prompts | `static/js/agent/prompt-builder/room-context.js` |
| Command matching | `engine/matching.py` or movement resolver |
| Serialization | player state in autosave / `Player.to_dict` |
| UI tag | `static/js/inspector/area-view.js` |
| Tests | `tests/test_transit_areas.py` — enter from A, back goes A; enter from B, back goes B |

## Verification

- [ ] Task 18 shaft tagged transit: enter from Room 4 → look shows `[back]` to Room 4, `[forward]` toward Room 3
- [ ] Same shaft, enter from Room 3 → back/forward swap
- [ ] `go back` and `go forward` work for human and agent action path
- [ ] Leaving shaft clears `transit_entry`
- [ ] Non-transit area unchanged (no back/forward)
- [ ] Agent Lens exits section reflects relative labels (task-219)
- [ ] Two outer commands both `enter vent` still works

## Related

- **Same architecture as** [[todo/gameplay/task-135-character-item-spatial-relationships|task-135: Character ↔ item spatial relationships]] — text worlds need *stored relations*, not inferred geometry. 135 = anchor on **items** in a room; 224 = anchor on **entry** in a transit area.
- Labs pain point: Task 18 ventilation shaft (`way_task_18__vent_shaft_1/2`)
- [[todo/ui/task-220-unified-way-editor|task-220]] — per-side commands
- [[review/ui/task-221-way-authoring-ux-and-tooltips|task-221]] — exit badges / movement hints
- [[review/gameplay/task-131-stateful-actions-over-time|task-131]] — multi-turn transit as activity (free-fall, chase)
- [[review/gameplay/task-223-way-prevent-close-open-passages|task-223]] — open passages
- Existing **todo** [[todo/gameplay/task-135-character-item-spatial-relationships|task-135]] — sibling task (character↔item relations in rooms); see 135 summary for unified "explicit relations in text" framing

## Notes

User quote: *"The crawl area is the point — landing between stairs, elevator, chase tunnel, free fall each turn. Text world has no north; entry-relative is the fix."*
