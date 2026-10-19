---
type: task
status: inprogress
area: library
priority: medium
blocked_by: [task-667]
---

# task-646: Rename space-separated registry ids (52 total) and resolve the hidden door collision

**Filed:** 2026-09-30
**Related:** [task-601]

<!-- deps:start -->
**Blocked by:** [[task-667-library-entries-are-keyed-by-filename-so-a-display-string-is-the-primary-key]]
<!-- deps:end -->

## What

task-601's lint check now reports 52 offenders: 36 characters (Arix, Croak-Mother, Old Iron-Back, the butcher...), 15 tags (frozen thicket, hidden door...), and 1 item (baker's_bread). load_registry keys entries by filename verbatim, so none resolve by their snake_case form. NOT a rename-and-done: the spaced ids are referenced in 20+ places across areas/characters/items/rooms/ways, and 'hidden door' would MERGE into the existing 'hidden_door' -- decide whether they are the same tag first. Character display names are unaffected (the name field is separate), so this is safe to do but needs the references updated in the same change.

## Acceptance

- [x] The 15 space-separated **tag** ids are renamed to snake_case.
- [x] The `hidden door` / `hidden_door` collision is resolved.
- [x] Before/after id counts and zero broken references are demonstrated below.
- [ ] The 37 space-separated **character** ids and the 1 item id
      (`baker's_bread`) are renamed. **These files belong to `wt/items-library`**
      (see the global cluster split) and are deliberately left to that session.

## What was done 2026-10-02 (tag registry only)

`data/library/tags/` had 592 entries, 15 with spaces. All 15 were `git mv`'d to
their snake_case form; `named`/display fields are unchanged, so nothing
user-facing moves. The 14 straightforward renames:

    blackwood mansion -> blackwood_mansion      root tunnel      -> root_tunnel
    create flame      -> create_flame           snowbound hollow -> snowbound_hollow
    everflame ember   -> everflame_ember        still shivering  -> still_shivering
    frozen thicket    -> frozen_thicket         valerius house   -> valerius_house
    grandfather clock -> grandfather_clock      willow gap       -> willow_gap
    high five         -> high_five              willow hollow    -> willow_hollow
    no clue           -> no_clue                recent blood     -> recent_blood

### The hidden door collision

`hidden door.json` and `hidden_door.json` were **identical auto-generated stubs**
(same "Auto-generated from agent memory" body, same colour/icon, empty
`applies_to`/`examples`; only the `name` casing differed). Neither id is
referenced as a tag anywhere in `data/` - the tag actually used is `hidden`
(21 references). Since they are the same tag and there is no content to lose,
`hidden door.json` was removed and `hidden_door.json` kept as the canonical id
(its display name set to "Hidden door").

### Proof: before / after and zero broken references

    tags before: 592 entries, 15 outside [a-z0-9_]
    tags after:  591 entries,  0 outside [a-z0-9_]
    `python tools/lint_library.py --check tag_id_charset`
      -> tags: no warning; only items (1) and characters (37) remain

A recursive scan of every JSON under `data/library/`, `data/scenarios/` and
`data/saves/` for the 15 ids in any tag-bearing key (`tags`, `interest_tags`,
`fear_tags`, `known_tags`, `applies_to`) returns **0 references**, so the rename
breaks nothing. (The only textual hits are way/exit `name`/`direction` strings
such as the `willow gap` way - display strings, not tag ids, and unchanged.)

## Why

Space-separated registry IDs break identifier normalization, API URL encoding, and slug-based lookup routines, and allowed duplicate identifiers to collide (such as hidden door entries). Normalizing them to snake_case guarantees deterministic addressing without altering user-facing display names.

## How

1. Rename space-separated tag IDs in `data/library/tags/` to snake_case.
2. Resolve the `hidden door` registry collision by deduplicating and consolidating tags.
3. Update reference scans across scenarios, library files, and saves to ensure 0 broken references.
4. Add lint enforcement in `tools/lint_library.py` to prevent regression of non-snake_case registry keys.

## Browser UI and intended live verification

Intended UI home: Not applicable - this card has no browser-facing behavior.

Current availability: Tag renames and the collision are resolved; character/item identifier files remain assigned to the separate library lane.

Live steps when available:

Why no browser UI: This renames registry identifiers and updates references without changing display names or adding browser behavior; the risk is data integrity.

Alternative verification steps:

1. Run the tag-id lint and scan library, scenario, and save references for renamed identifiers.
   - expected: Remaining tag IDs satisfy snake_case, references resolve with zero stale identifiers, and display names remain unchanged.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Run `python tools/lint_library.py --check tag_id_charset`.
   - expected: Zero warnings for tags outside [a-z0-9_].
   - observed: 591 tag entries pass with 0 non-compliant IDs.

2. Search library and scenario files for renamed tag references.
   - expected: All references resolve cleanly to normalized snake_case identifiers.
   - observed: Zero dangling references found across data/library and data/scenarios.

## Files

- `tools/lint_library.py`
- `data/library/tags/`


## Blocker Note (2026-10-19)
- Blocked by [[task-667-library-entries-are-keyed-by-filename-so-a-display-string-is-the-primary-key]].
- As documented in Acceptance criteria, the tag renaming and hidden door collision resolution are 100% complete and verified (591 tags conform, 0 tag warnings).
- The remaining 38 character IDs and 1 item ID belong to the parallel items/library lane and require task-667 primary-key filename decoupling to avoid merging distinct character entities (e.g. Shadow-Pelt and shadow_pelt).
