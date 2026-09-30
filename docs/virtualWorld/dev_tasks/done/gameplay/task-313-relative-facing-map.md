---
type: task
status: done
area: gameplay
priority: medium
---

# task-313: Relative facing map (forward/left/right/back)

**Filed:** 2026-08-19 (as an idea stub; rewritten 2026-09-27 into a spec)
**Relates:** `engine/character_spatial.py`, `engine/movement.py`, `engine/matching.py`,
`engine/area_description.py`, `engine/timeskip.py`, `data/library/tags/transit.json`.

Origin: `developer ideas.md` items 20 and 21 — "mapping of forward, left, right and
back to a character, like the suggested transit tag on areas, based on cardinal
directions and origin ways… if you come from the south, right is east, left is
west; if you come from the west, right is south, left is north."

## Scoping notes (2026-09-27, measured)

**1. Nothing records where a character came from.** Grepped the whole repo: no
`facing`, `entered_from`, `origin_way`, `arrived_from`, or equivalent on a
character, a character node, or player state. `engine/movement.py` writes a
turn event when a character changes area but does not stamp the entry way. So
there is no state for facing to derive from — that is the actual work, and it is
what the transit tag has been quietly standing in for.

**2. `left` and `right` already parse, then dead-end.** They are classified as
traversal words in `engine/movement.py` (`_APPROACH_CARDINAL_WORDS`), so
"go to the left" is treated as crossing, not as an approach target. But the
direction string is then handed to `name_matcher.resolve_exit(area_id, direction)`
(`movement.py`, `movement.py`), which looks for a way whose own handle is
literally `left`/`right`. No way is authored that way, so the words are accepted by
the parser and then fail to resolve. The vocabulary is already half-wired; only the
resolver is missing.

**3. The transit tag is dead *and* could not work as authored.** This was the
original design ("like the suggested transit tag on areas") and it is being
dropped. Three independent reasons:

- **No area carries it.** An exhaustive search for the exact `"transit"` token
 across every `.json`/`.txt` under `data/` (excluding exports) matches exactly one
 file: the tag definition itself. Not the 90 `data/library/areas/` files, not any
 of the 24 scenarios. The other `transit`-ish matches in `data/` are the unrelated
 scheduler fields `transition_interval` / `transition_table`.
- **It was attempted and failed quietly, in the labs vent.** The motivating case
 is real and still sitting in content: `data/scenarios/labs.json`,
 `Task 18 - ventilation shaft`, is a two-way area —
 `Shaft 1` (`"cardinal": "north"`) to `Task 18 - Room 3`, and `Vent 2` to
 `Task 18 - Room 4` — with `"tags": []`. That is exactly the shape
 `get_transit_roles` was written for (`len(ways) == 2`, one is `back`, the other
 `forward`). The author plainly expected back/forward to work in a crawl-through
 shaft, and it did nothing, because the gate it required was never set. Note also
 that it is authored **asymmetrically**: `Shaft 1` carries a cardinal and `Vent 2`
 carries none. Both need one for facing to work, whichever you crawled in through.
- **It is on the wrong node type.** `data/library/tags/transit.json` declares
 `applies_to: ["ways"]`, but the only consumer,
 `is_transit_area` (`engine/character_spatial.py`), returns `False`
 unless `area_node.type == "area"` and then looks for the tag on the **area**.
 Tag on a way can never satisfy the check that reads it.
- **So `get_transit_roles` always returns `None`.** Therefore the
 `handle = "back"` / `handle = "forward"` override in
 `engine/area_description.py` never fires in any shipped content, and
 `resolve_transit_movement` (`engine/matching.py`) never resolves
 anything. The feature has never run.

Because nothing depends on it, retiring the gate is free: no content migration, no
back-compat shim. **Scope now includes deleting `is_transit_area`,
`get_transit_roles`, `resolve_transit_movement`, the `area_description.py`
override, and `data/library/tags/transit.json`.** The transit tag should not be
reintroduced as an opt-in for relative facing — relative facing is the default.

**4. The transit branch is also the wrong shape for this feature, independent of
the tag.** Three problems to carry over correctly rather than delete blindly:

- It **replaces** a way's handle instead of aliasing it. For relative facing,
 "left" must resolve *in addition to* the way's own cardinal/narrative handle,
 never instead of it — otherwise a room loses the name of the door you can see.
- It **hardcodes two ways** (`len(ways) < 2` and
 `len(forward_candidates) != 1` both bail). Left/right have to pick among *all*
 the ways in an area by cardinal, which is the general case.
- It derives "back" from the way a character is **AT** (`get_character_at_way`),
 not from where it came in. Those are different situations and both should feed
 facing: AT a way means examining it, not arriving through it.

**5. Facing must derive from the entry way, per the standing decision that exterior
ways stay cardinals** and only narrative/entry ways act as entry features. If
facing were derived from any cardinal way, it would fight the map editor's
cardinal layout instead of complementing it.

## Problem

A character has no orientation, so "to your left" resolves to nothing. The words
`left` and `right` are already accepted by the parser and then fail, and `back` /
`forward` are handled only by a transit branch that no area can reach. The user
experience is that relative movement words are typed, accepted, and dead.

## Design

**Facing is the heading of travel, and it persists until the character moves
again.** When a character crosses a way into an area, stamp the entry way on the
character and derive `facing` as the direction of travel (coming from the south
means travelling north, so you face north). Standing still, examining things, or
talking does not change it. There is no turn-in-place verb; facing changes only by
moving, which keeps the model to one piece of state.

Resolve the four words by rotating `facing` on the cardinal ring
(`N → E → S → W → N`):

| word | result |
| --------- |
| `forward` | `facing` |
| `right` | one step clockwise |
| `left` | one step counter-clockwise |
| `back` | opposite of `facing` |

Then look up the resulting cardinal as an ordinary direction, i.e. hand the
resolved cardinal to the same exit resolution that "go north" uses today. This is
what makes it additive: "go left" becomes "go <cardinal>", and the area's own
handles are untouched.

## Acceptance criteria

- [ ] Crossing a way stamps the entry way and derived `facing` on the character;
 the value survives turns where the character does not move.
- [ ] `go left` / `go right` / `go forward` / `go back` resolve to the real
 matching way, in an ordinary multi-way area, with no transit tag present.
- [ ] The two worked examples from the original idea hold: entering from the
 south, right is east and left is west; entering from the west, right is
 south and left is north.
- [ ] A way's own handle still resolves alongside the relative words — the
 relative words alias, they never overwrite. The exits list in the area
 description shows the authored handles, not `back`/`forward` replacements.
- [ ] A character with no entry way (spawned in place, or a save predating this)
 resolves cardinals normally and fails cleanly on relative words, with a
 message that says why rather than a generic "can't go there".
- [ ] `up` / `down` ways are never rotated; they stay literal and are not offered
 as left/right/forward/back.
- [ ] A way in a direction that is not a cardinal (a diagonal) does not become a
 false left/right; the relative word is simply unresolved for that side.
- [ ] The labs vent works: crawl into `Task 18 - ventilation shaft` from either
 end, and `go back` returns the way you came in by. Both its exits are given
 cardinals as part of this (`Shaft 1` has one, `Vent 2` has none today).
- [ ] The transit machinery is gone: `is_transit_area`, `get_transit_roles`,
 `resolve_transit_movement`, the `area_description.py` handle override, and
 `data/library/tags/transit.json` are deleted, and no other module imports
 them.
- [ ] Per the standing rule, the relative-facing rules are documented in code
 comments and in the user guide / technical docs — not only in this file.
 This is exactly the kind of non-obvious behaviour that has been
 misunderstood before.
- [ ] `python tools/tasks.py validate` is clean.

## Non-goals

- A turn-in-place / "face north" verb, or a compass shown in the UI.
- Diagonal-aware rotation (an 8-way ring is a separate decision).
- Rotating `engine/timeskip.py` `HEADING_WORDS` — belief travel is a separate
 path and stays cardinal-only.
- Re-authoring the 90 library areas. Nothing in the library needs to change,
 which is the main payoff of dropping the tag. The one content edit this task
 does carry is the two exits on the labs ventilation shaft.

## Verification

- Unit: a four-way area; enter from the south, assert `go left` resolves to the
  west way and `go right` to the east way; repeat entering from the west and
  assert the rotation.
- Unit: `facing` survives a non-movement turn and updates on the next crossing.
- Unit: relative words in a spawn-point area return the "no entry way" message,
  not a generic failure.
- Unit: an area tagged `transit` in a fixture behaves identically to an untagged
  one — the tag is gone, so it must be inert rather than load-bearing.
- Full suite: compare against the ~60 failed / 3239 passed baseline.

## Result (2026-09-30) — implemented, and verified in a browser

All acceptance criteria are met. `engine/facing.py` owns the ring and the
rotation; `player.facing` / `player.entered_from_way` hold the state; the
transit machinery and the tag are gone.

### The scoping notes were right, and one was load-bearing

Notes 1–3 verified as written on re-measurement: no facing state existed, the
four words were already in `_APPROACH_CARDINAL_WORDS` and dead-ended at
`resolve_exit`, and the transit tag had no reader that could ever match.

**What the notes did not say, and which would have shipped a dead feature:** the
authored `cardinal` never reached the graph. `serialization_legacy` read the
exit *key* (which in labs is the label `"Shaft 1"`, not a heading) and never
looked at `exit_info["cardinal"]`, so the cardinals authors had already filled
in reached neither the graph nor anything else. Two further gaps behind it:

- **Only `world_compile` wrote `cardinal` onto edges.** `movement.connect_areas`
  and the `create_way` effect wrote `direction` only, so reading `cardinal`
  alone would have made facing work in compiled zones and fail silently
  everywhere else. `facing.edge_cardinal()` reads `cardinal` then falls back to
  `direction`, and it is the single reader both the stamper and the resolver use.
- **labs.json holds connectivity twice** — a legacy `areas` block *and* a
  pre-built `graph` — and the loader uses the `graph`. Filling in the `areas`
  cardinals changed nothing observable, which is rule 1's failure mode caught in
  the act. The four `Vent 2` connection edges in the `graph` needed the
  cardinals too.

### Changes

- **`engine/facing.py`** (new) — `CARDINAL_RING`, `RELATIVE_WORDS`,
  `normalize_cardinal`, `cardinal_opposite`, `rotate`, `edge_cardinal`,
  `explain_unresolved`, `resolve_for_player`.
- **`engine/movement.py`** — stamps `facing`/`entered_from_way` on a crossing,
  from the edge's cardinal rather than the typed word (a narrative handle still
  gets a heading); `connect_areas` gained `cardinal1`/`cardinal2`.
- **`engine/matching.py`** — `resolve_exit` tier 1b resolves the relative word
  and hands the cardinal to ordinary exit resolution. After the exact-handle
  tier, so an authored `back` still wins.
- **`engine/serialization_legacy.py`** — carries `cardinal` through, deriving the
  far side by opposition (`return_cardinal` overrides).
- **Deleted** — `is_transit_area`, `get_transit_roles`,
  `resolve_transit_movement`, the `area_description.py` handle override, the
  `room-context.js` prompt rename (which was the same bug on the agent side),
  `trigger_validator`'s `"transit"` entry, and `data/library/tags/transit.json`.
- **Content** — `labs.json`: `Vent 2` cardinals on both the `areas` entries and
  the four `graph` edges. That is the whole content change; no library area
  needed one, which is the payoff of dropping the tag.
- **Docs** — the "Relative facing" section of
  `Gameplay/Character Spatial Position.md`, plus a superseded-by note on
  task-224 (which shipped in 2026-08 and never ran) so the next reader does not
  re-implement it.

### Tests

`tests/test_facing.py` (52 tests) covers the ring and both worked examples, the
aliasing, every off-ring `None`, the messages, `edge_cardinal`'s fallback, the
stamping, rotation through real `move_to_area` calls, persistence round-trip,
the tag being inert, and **the real labs vent crawled in from both ends**. The
transit tests in `test_character_spatial.py` were **ported, not deleted** — they
stood a character *AT* a way, which the scoping notes correctly call a different
situation from arriving through one.

### Live browser verification

Not unit tests. Drove the real labs scenario in a browser via the engine-command
override (`#command-input`) on a fresh instance:

- Crawled into `Task 18 - ventilation shaft` from `Task 18 - Room 3`; in the
  shaft the exits list read **`[Vent 2]`** and **`[Shaft 1]`** — the authored
  handles, with no `back`/`forward` substitution anywhere.
- `go left` from Room 3 while facing north resolved to **`Door 3`** (west, then
  refused as locked) while `go back` took **`Shaft 1`** (south) — two different
  doors from one position, which is the rotation working.
- `go left` inside the shaft answered *"'left' would be east from here (you are
  facing south), and there is no east exit."* rather than "can't go there".
- The event stream recorded the resolution outright:
  **`matched 'back' as exit 'Shaft 1' (north of facing south)`**

### Known limits, deliberately

`up`/`down` and diagonals are never rotated (an eight-way ring is its own
decision); a way with no cardinal is never rotated; facing is client-visible
state on the `Player`, not an area property, so two characters in one room can
face differently — which is the point.

## Related

- `developer ideas.md` lines 20–23
- `engine/character_spatial.py`, `engine/movement.py`, `engine/matching.py`
- Decision: exterior ways stay cardinals; only narrative/entry ways act as entry
 features.
