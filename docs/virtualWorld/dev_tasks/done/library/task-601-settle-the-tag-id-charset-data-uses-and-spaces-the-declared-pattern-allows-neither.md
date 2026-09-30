---
type: task
status: done
area: library
priority: low
---

# task-601: Settle the tag id charset: data uses ':' and spaces, the declared pattern allows neither

**Filed:** 2026-09-30
**Related:** 

## Goal

engine/character_appearance.py::_ID_RE declares ids as ^[a-z0-9][a-z0-9_-]*$ but the data does not follow it: every Kraktooth character carries faction:goblin, faction:human, held_by:goblin, held_by:human, and the library has 'taco bell'. Nothing validates ordinary character tags against _ID_RE, so the two conventions have simply diverged. This already cost a real bug: a tag id normalizer that reshaped ':' to '-' produced faction-goblin, an id that matches nothing, and the generator then offered the model ids that could never work while describing them as in use. Decide whether tags may contain ':' and spaces (and document it), or migrate the data to the declared pattern - and note that only 155 of the 439 distinct item tags exist in the curated registry at data/library/tags, so the registry is not a reliable proxy for what items actually carry.

## Acceptance

- [x] A lint check reports every registry id outside `[a-z0-9_]`
- [x] It runs by default as part of `tools/lint_library.py`
- [x] It names the specific offenders rather than a count
- [x] It reports ids that would COLLIDE if normalised, so a blind rename is blocked
- [x] Covered by tests
- [x] Verified live against the real library

## Resolution (2026-09-30) — check landed, rename deferred to task-646

The gap was real and is now guarded. `routes/helpers.py::load_registry` keys
every entry by its **filename verbatim**, so an id is whatever the file is called
and there is no normalisation anywhere. Verified functionally against the running
app: of 591 tag ids, 576 are `snake_case` and 15 use spaces; both resolve by
their *exact* id, but `blackwood_mansion` does **not** find
`blackwood mansion.json`. An author writing the conventional form gets a silent
miss.

**Why this was not caught:** `tag_case_drift` already exists and is an ERROR
check, but it compares **casing** (`Foo` vs `foo`) only. Separators are invisible
to it, so all 15 space-separated ids passed cleanly.

**Added** `tag_id_charset` (warning level) to `tools/lint_library.py`, reporting
the offenders by name rather than a bare count. It also flags ids that would
**collide** if normalised, which is what blocks a careless rename. `tags` and
`ways` were added to the lint context, which previously loaded only items,
characters and areas -- so the registry where the problem actually lives was
never in scope for any check.

Current output against the real library:

    items:      1   baker's_bread
    characters: 36  Arix, Croak-Mother, Old Iron-Back, the butcher, ...
    tags:       15  frozen thicket, hidden door, willow hollow, ...
    COLLISION:  'hidden door' and 'hidden_door' both normalise to 'hidden_door'

**Left to task-646 deliberately.** The rename is not a lint fix:

- the spaced ids are referenced in **20+ places** across areas, characters,
  items, rooms and ways, so those references must move in the same change;
- `hidden door` and `hidden_door` are **separate files today** and normalising
  merges them, so whether they are the same tag is a content decision, not a
  mechanical one.

Character *display* names are unaffected -- `name` is a separate field -- so the
fix is safe once the collision is decided. The point of landing the check first
is that the set is now visible and can no longer grow silently, which was the
actual defect.

- TODO
