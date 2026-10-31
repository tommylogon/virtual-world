---
type: task
status: done
area: characters
priority: low
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903", "bug-570"]
---

# task-922: Media schema formalization feeding lorebook knowledge and memories

**Filed:** 2026-10-31
**Related:** task-903, bug-570

## What

Formalize the `narrative.media` block in character persona as structured records (title, creator, genre, character reaction/affinity, key takeaways) that feed directly into the character's seeded memory store and lorebook knowledge rather than remaining an unread list.

## Why

Characters often list favorite books, songs, games, or myths in their backstory. Currently, `narrative.media` is not an identity trait or GIMP dial; without formalizing its projection into memory records or lore knowledge, the field sits in the schema unread.

## How

- In `engine/character_appearance.py`, define the schema for `narrative.media` entries (`title`, `medium`, `opinion`, `familiarity`).
- On initial scenario load or character hydration, generate semantic memory records (e.g. `You read 'The Art of War' and learned...`) with `source: "backstory"`.
- Add unit tests verifying that media items generate appropriate memory entries.

## Acceptance

- [x] `narrative.media` accepts structured media items.
- [x] Initial character hydration translates media entries into background memory records.
- [x] Media entries do not compile into physical appearance prose.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
