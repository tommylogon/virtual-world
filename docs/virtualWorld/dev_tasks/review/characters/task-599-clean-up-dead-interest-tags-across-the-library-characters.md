---
type: task
status: review
area: characters
priority: medium
---

# task-599: Clean up dead interest tags across the library characters

**Filed:** 2026-09-30
**Related:** 

## What

tools/lint_library.py reports 23 dead_interests errors today (for example characters/Vekka: maps, routes, secrets; characters/Zikka: weapons, training, prestige). interest_tags is matched against item tags and item names by the room attention list and by auto-dress, so these do nothing. Decide per character whether the intent was a real interest that needs an item to carry the tag, or a tag that should be dropped. Note that several are plural/case drift of a live tag (weapons -> weapon, maps -> map), which is a fix rather than a deletion.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. Run `python tools/lint_library.py --check dead_interests` before editing,
   then inspect Vekka's and Zikka's `interest_tags` alongside item tags and
   names in `data/library/items/`.
   - expected: the initial report identifies each unmatched interest and the
     data review distinguishes plural/case drift from interests with no
     matching item.
   - observed (filed 2026-09-30): the baseline listed 23 `dead_interests`
     errors, including Vekka's `maps` and Zikka's `weapons`.
2. After correcting the character library entries, rerun the same targeted
   linter command.
   - expected: zero `dead_interests` errors, with any intentionally retained
     interest backed by a matching item tag or name.
   - observed: the fix has not been recorded in this card yet.

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — this card reconciles authored character
library data against item tags; it does not add a player-facing behavior or
authoring control.

Current availability: `tools/lint_library.py` has a targeted `dead_interests`
check. Character interest tags are authored in files such as
`data/library/characters/Vekka.json` and `data/library/characters/Zikka.json`.

Why no browser UI: The result is whether each stored interest tag matches an
item tag or item name. The library linter reports that fact directly, and a
game screen would not add a more authoritative check.

Alternative verification steps:
1. After correcting plural/case drift or removing interests that have no
   intended item, run `python tools/lint_library.py --check dead_interests`.
   - expected: the command exits successfully and reports zero `dead_interests`
     errors for the character library.
2. Open Vekka and Zikka's character JSON files and compare each remaining
   `interest_tags` entry with the item tags/names used by the library.
   - expected: every retained interest has a matching library item; unsupported
     interests are not left as inert authored data.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
