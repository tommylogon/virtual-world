# Task: Stove & Background Objects — Narrative Handling (no item needed)

**Status**: Implemented (verified 2026-08-06) — both core changes present in code:
- `engine/matching.py`: word-boundary substring matching (comment: `"stove" must not match "stovepipe"`); `stove` resolves against room description, not `Stovepipe Leather Boots (Pair)`. Prereq task-183 landed.
- `engine/item_actions.py` `_describe_flavor_target`: appends `"It does not seem to be of any use."` to flavor-target examine responses (lines ~327-330), so `examine stove` returns in-character narrative.
- Character memory of the narrative result flows via the observe/reaction synthesis (system-vs-character separation); `_descriptive_target_failure` still logs a witnessable turn event.
The decision to NOT implement a real stove item stands. Move to `done/` after a backend test asserts `examine stove` → flavor text (never boots) and `use kindling on stove` → scenery-failure narrative.

## Goal

Background objects referenced only in descriptions (the Kitchen stove, the loose
tile, the moon, the fireplace) should be handled **by narrative responses, not by
implementing real items for every one of them**. `examine stove` should reveal
something like *"You examine the stove, but it does not seem to be of any use"*,
the character should **remember that** (as a character memory), and `stove` must
resolve against the room description — **not** against *Stovepipe Leather Boots
(Pair)*.

Originally filed as "implement a stove item". Decision (2026-08-02): **do not
implement the item.** The engine already has the narrative fallbacks; the real bug
is that name matching resolves `stove` → `Stovepipe Leather Boots (Pair)` (via raw
substring) *before* the fallback ever runs.

## Why no item is needed — existing fallbacks (verified)

| Path | Function | Behavior today |
|---|---|---|
| `examine <flavor target>` | `_describe_flavor_target` (`engine/item_actions.py:181-222`) | Returns "You examine X. <sentence from area/item/way description>" |
| `use <item> on <flavor target>` | `_descriptive_target_failure` (`engine/item_actions.py:948-1014`) | Returns "You try to use the X on Y, but it doesn't budge — it's part of the scenery / purely decorative" (randomized reasons) |

Both scan the area description + visible item descriptions + way descriptions for
the target phrase (word-boundary aware), and both are reached **only after** real
item/exit/character resolution fails. So the stove narrative already works — it just
never gets reached because substring matching hijacks `stove` first.

## Changes

### 1. Rely on the name-matching fix (dependency)
- `task-183-name-matching-aliases` must land first: word-boundary matching in
  `_match_item_name` / `_match_exit_direction` (engine/matching.py) so `stove` no
  longer matches inside `stovepipe`. Real targets are not blocked — word-boundary
  precision replaces substring greediness, and the alias tier covers synonyms.
- Ordering guarantee: exact → word-boundary → alias → exit → player → **flavor last**.
  Flavor is the last resort and returns in-character text, never an error, so it
  cannot block genuine attempts.

### 2. Make the examine flavor message clearly "of no use"
- `_describe_flavor_target` currently echoes the raw sentence ("You examine stove.
  The stove is out…"). For background objects that offer no interaction, append a
  no-use note so the model doesn't keep trying: e.g.
  `"…— it does not seem to be of any use."` Keep the echoed sentence (it's the
  grounding the character should remember).
- Do **not** add a generic "not usable" suffix to every flavor hit — doors/trees in
  descriptions may still be genuinely interesting. Only append the no-use note for
  obvious inert objects (stove, furniture, decor) OR keep it simple: always append,
  since flavor targets by definition can't be acted on. Decide during implementation
  with the kitchen stove as the test case.

### 3. Character memory of the narrative result
- After `examine stove` → flavor response, the character should remember
  *"I examined the stove — it seems to be of no use"*, not a raw system string.
  Per the system-vs-character separation (see `task-185-plan-loop-breaking` design
  principle), the flavor response is already narrative — ensure it flows into the
  character-facing memory via the observe/reaction synthesis, not as
  `examine stove → <raw result>`.
- The turn event logged by `_descriptive_target_failure` (record_turn_event, line
  1008) already lets other characters witness the failed attempt — keep that.

### 4. Test cases (backfill into the matching/parser tests)
- `examine stove` → flavor text about the stove, **never** the boots description.
- `use kindling on stove` → "…doesn't budge / part of the scenery", **never**
  "You use the Stovepipe Leather Boots (Pair)."
- `use create flame on stove` → same narrative failure (stove is inert), while
  `use create flame` (alone) spawns a lit ember per `task-174-fire-mechanic-heat-source`.
- A real target still works: `use key on cellar_way`, `take twigs` (→ kindling
  via alias), `door` still matches `front door` — proving word-boundary matching
  doesn't block genuine attempts.

## Out of scope

- Implementing `item_stove` / `data/library/items/stove.json` (rejected).
- Warmth/heating interactions — revisit only if a *real* stove item is ever wanted
  (then it follows `task-174-fire-mechanic-heat-source` patterns).

## Files Modified
- `engine/item_actions.py` — `_describe_flavor_target` no-use note (optional, small)
- `engine/matching.py` — via `task-183-name-matching-aliases` (word-boundary)
- Tests: backend matching/parser test file + `tools/test_all.cjs`

## Related
- `task-183-name-matching-aliases` (prerequisite)
- `task-181-command-parser-multiwindow-targets` (multi-word `use X on Y` targets)
- `task-174-fire-mechanic-heat-source` (Create Flame as `use` alone)
- `task-160-parameterized-actions-in-prompts` (agent emits clean structured targets;
  fixes emission, not resolution)
