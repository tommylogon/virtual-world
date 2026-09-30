---
type: task
status: todo
area: library
priority: low
---

# task-601: Settle the tag id charset: data uses ':' and spaces, the declared pattern allows neither

**Filed:** 2026-09-30
**Related:** 

## Goal

engine/character_appearance.py::_ID_RE declares ids as ^[a-z0-9][a-z0-9_-]*$ but the data does not follow it: every Kraktooth character carries faction:goblin, faction:human, held_by:goblin, held_by:human, and the library has 'taco bell'. Nothing validates ordinary character tags against _ID_RE, so the two conventions have simply diverged. This already cost a real bug: a tag id normalizer that reshaped ':' to '-' produced faction-goblin, an id that matches nothing, and the generator then offered the model ids that could never work while describing them as in use. Decide whether tags may contain ':' and spaces (and document it), or migrate the data to the declared pattern - and note that only 155 of the 439 distinct item tags exist in the curated registry at data/library/tags, so the registry is not a reliable proxy for what items actually carry.

## Acceptance

- TODO
