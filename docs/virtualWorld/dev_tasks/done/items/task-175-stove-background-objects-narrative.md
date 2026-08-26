---
id: 175
title: Stove & Background Objects — Narrative Handling (no item needed)
status: done
priority: medium
created: 2026-08-02
updated: 2026-08-03
tags: [items, matching, flavor, narrative]
---

# Task 175: Stove & Background Objects — Narrative Handling (no item needed)

**Status**: Done — verified 2026-08-03.

## Goal

Background objects referenced only in descriptions (kitchen stove, loose tile, moon, fireplace) are handled **by narrative responses, not real items**. `examine stove` returns *"You examine stove. … It does not seem to be of any use."*, the character remembers it as narrative, and `stove` resolves against the room description — **not** against *Stovepipe Leather Boots (Pair)*.

## Status per requirement

### 1. Name-matching fix (dependency: word-boundary matching) ✅
`engine/matching.py:155-196` uses word-boundary regex (exact → word-boundary → alias → fuzzy), so `stove` no longer matches inside `stovepipe`. Locked by `tests/test_matching.py:170` `test_stove_does_not_match_stovepipe_boots`.

### 2. No-use note in examine flavor ✅
`_describe_flavor_target` (`engine/item_actions.py:256-300`) appends *"It does not seem to be of any use."* to every flavor hit (the "always append" decision the task left open).

### 3. Character memory of the narrative result ✅ (by design)
The flavor fallback returns narrative text, not a raw system string, so it flows through the existing observe/reaction memory synthesis per the system-vs-character separation. `_descriptive_target_failure` keeps logging `record_turn_event` so others witness failed attempts.

### 4. Test cases ✅ (one added this session)
- `examine stove` → flavor text + no-use note, **never** the boots — `tests/test_descriptive_targets.py::test_examine_stove_uses_flavor_not_boots` (added 2026-08-03, end-to-end through `get_item_desc`).
- `use kindling on stove` → scenery failure — `test_use_on_flavor_via_real_matching`.
- `use create flame on stove` → fire-appropriate failure — `test_fire_item_gets_fire_failure_text` / `test_fire_item_without_node_uses_generic`.
- Real targets still work — `test_matching.py` word-boundary + existing take/key/door cases.

## Observation (non-blocking)

- `data/library/items/stove.json` exists in the library despite the task's "rejected" note — but it is **not placed in the world graph** (no `item_stove` nodes in world_template/autosave), so `examine stove` still goes through the narrative fallback. The "no real item" decision holds in practice; the library file is a harmless unused entry.

## Files Modified

- `engine/item_actions.py` — `_describe_flavor_target` no-use note (already landed before this review)
- `engine/matching.py` — word-boundary tier via the name-matching work (F4)
- `tests/test_descriptive_targets.py` — end-to-end examine-stove case added during review

## Related

- `task-183-name-matching-aliases` (prerequisite, F4) — landed.
- `task-181-command-parser-multiwindow-targets` (multi-word `use X on Y`).
- `task-174` (fire mechanic) — `use create flame` alone spawns the lit ember.
- `task-160` (parameterized actions) — fixes emission, not resolution.
