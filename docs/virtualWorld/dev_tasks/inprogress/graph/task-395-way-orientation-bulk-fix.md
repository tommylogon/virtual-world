---
type: task
status: inprogress
area: graph
priority: medium
---

# task-395: way-orientation-authoring

**Filed**: 2026-09-07
**Status**: In Progress — reworked 2026-09-07 after engine review. The original
blind-fill (minted "north" cardinals + templated pass/visible messages) was WRONG
and has been replaced. No bulk op writes way data anymore; the pattern is now
"downgrade to info + AI-draft for review."

## Source

Conversation 2026-09-07. The mansion validator lists ~180 warnings all generated
by the same class: ways missing `pass_message`, cardinal direction, and/or
`visible_in_direction` on their connection edges (× 2 sides × ~30 ways).

## Rework: why the first version was wrong (post-mortem)

- **pass_message is NOT required.** `engine/movement.py:743-749` falls back to
  "You head through {direction}." when unset; the check was informational only.
  Also, per-direction pass prose is coming — currently the field is a single
  way-node property shared by BOTH sides, so a bulk template would also be a
  direction-collapse footgun.
- **`north` minting lies.** `engine/matching.py:155-160` uses `cardinal` to match
  "go north" commands; `layout-engine.js:32-36` uses it to place rooms. Ways can
  connect to any number of areas, and direction commands are freeform ("up the
  stairs", "into the closet", "to Narnia") and never route through the cardinal
  tier — so forcing "north" creates a silent match bug and piles rooms in layout.
  Geometry can't rescue it either: layout GENERATES positions FROM cardinals, so
  deriving cardinal from position is circular.
- **visible_in_direction is author prose, and the engine already has a default.**
  `engine/area_description.py:509-549`: unset → "X is visible beyond"; set →
  author's view text. The invented "A glimpse of {area} beyond." was redundant
  AND wrong. The right authoring path is the existing per-way ✨ Improve AI
  (`way-view.js:931`), not a template.

## What we actually changed (rework)

1. `routes/graph_ops.py`:
   - `fix_way_orientation` → **removed entirely** (was a no-op). Nothing calls it
     and nothing should — the guess-writing route is gone, not just inert.
   - new `clear_way_fix_fields` batch op: removes ONLY values that exactly match
     the old minted templates (`You pass through <name>.`, `A glimpse of <source>
     beyond.`, `cardinal=='north'` AND direction not a real cardinal). Author
     text survives by construction; idempotent; one undo.
2. `engine/trigger_validator.py` — `_validate_way_authoring()` downgraded
   `way_missing_pass_message` / `way_missing_cardinal` /
   `way_missing_view_direction` from `warning` to `info` with honest reason text
   ("engine falls back to its default"). This kills the ~180 warning rows without
   pretending there's a defect.
3. `static/js/validator-panel.js` — the old "⚡ Fix all ways" became
   "✨ AI-write ways": runs the cleanup op, then opens the top missing-field way
   in the existing per-way ✨ Improve AI (draft-for-review, never auto-applied
   en masse).

## Verification

- `pytest tests/test_trigger_validator.py tests/test_undo_history.py tests/test_way_connect_repair.py` — 54 passed.
- Live: author-set pass_message preserved by cleanup; minted template values removed.
- Repo gate `pytest -k "not mcp and not emote"` — 2632 passed.
- Manual browser pass still TODO (panel ✨ AI-write flow + info-severity styling).

## Future (not this task)

- Per-direction pass/visible prose → move those fields onto the area→way edges
  (they're currently single node-level props), then an AI "write missing flavor"
  batch can target per-direction text with real context.