---
type: task
status: inprogress
area: library
priority: medium
---

# task-646: Rename space-separated registry ids (52 total) and resolve the hidden door collision

**Filed:** 2026-09-30
**Related:** [task-601]

## Goal

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
referenced as a tag anywhere in `data/` — the tag actually used is `hidden`
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
such as the `willow gap` way — display strings, not tag ids, and unchanged.)
