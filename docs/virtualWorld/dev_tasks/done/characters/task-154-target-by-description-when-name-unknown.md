---
id: 154
title: Target by Description When Name Unknown
status: review
priority: high
created: 2026-08-02
updated: 2026-08-03
tags: [characters, targeting, matching, discovery]
---

# Target by Description When Name Unknown

## Summary

Let actions like `attack`, `examine`, or `steal from` target a character by their description/appearance when the actor doesn't know their name yet — `attack the tall man in the corner` resolves to the right character, and strangers are presented by appearance, not their database name.

## Status — VERIFIED LIVE 2026-08-03 (review)

Backend suite green (**438 passed, 1 skipped**). Live-verified on port 4444:
- `examine the woman` (John two, same room as Jane doe) → matched Jane doe by description, confirmed via `system_messages`.
- Unmet characters appear by appearance in the room; real name appears after meeting.
- Four gaps found and fixed during live verification (see below).

## Gaps Fixed 2026-08-03 (live verification)

1. **Mid-turn name leak in DECIDE/ACT prompts.** OBSERVE anonymized strangers, but the frontend `People here:` block revealed the real name one phase later — because `register_first_meeting` creates the relationship during the observe, and the frontend's `hasMet = relationships[x].closeness !== undefined` saw it as met immediately. **Fix:** `register_first_meeting` stamps `first_sighting: True` on the new record; `area_description.py` clears it on the *next* encounter (so the name reveals from the second sighting); a shared `worldState.hasMet(charName, targetName)` (`static/js/world-state.js`) now gates `prompt-builder.js` `anonymousName`/`People here` and `agent-engine.js` threat alerts. `update_relationship` (a real interaction) reveals the name immediately (no flag).
2. **Examineable-list leak.** `examine <unknown>` printed real player names in "Things you can examine right now:". **Fix:** `item_actions.py` now skips the actor and lists unmet characters via `unknown_display_name()`.
3. **Generic descriptors failed.** `examine the woman` errored even when exactly one woman was present ("woman" is a 5-char generic word; tier 4 requires ≥6-char distinctive words). **Fix:** tier-5 generic fallback in `_match_character_name` — resolves when the kind word literally appears in exactly one description, or matches one character's gender pronouns; genderless kinds ("stranger") only with a single occupant; suppressed when the input carries non-generic descriptive words ("distant room man" must not match).
4. **Pronoun-starting labels.** `unknown_display_name()` produced "the she stands bare and unadorned…" for descriptions starting with "She…". **Fix:** maps to "the woman who stands bare and unadorned…".

New tests: `tests/test_matching.py` (generic woman/man/stranger cases), `tests/test_player_meeting.py` (first_sighting stamp, pronoun label), `tests/test_item_actions.py` (examineable-list anonymization).

## Implementation

### Backend matching — `engine/matching.py` ✅
New `_match_character_name(input_str, exclude_self=True)` returning `(name, candidates)`:
- Tier 1: exact name (case-insensitive)
- Tier 2: word-boundary substring on the name
- Tier 3: fuzzy difflib name match (tight cutoff)
- Tier 4: **description-word matching** — significant words from the input (≥4 chars, stopword-filtered) matched word-boundary against each same-area character's `description` + `base_description`. Score ≥ 2 → unique winner; ambiguous ties → `candidates` list for prompting; single-word matches only resolve when the word is distinctive (≥6 chars, not a generic like man/woman/stranger).

### Hidden names — `player.py` + `area_description.py` ✅
- New `Player.unknown_name` field (serialized in `to_dict`) + `unknown_display_name()` — explicit label when authored, otherwise derived from the description (first sentence, leading article stripped, e.g. → "the tall woman with long auburn hair").
- New `Player.has_met(other)` — true once a relationship record exists (`register_first_meeting` / `update_relationship`).
- `engine/area_description.py` "People here" list now shows the **unknown display name** for unmet characters (and skips the redundant `— description` suffix for them); real name + description after meeting.

### Integration ✅
- `routes/action.py` — `attack` resolves via `world._match_character_name`; ambiguous inputs prompt "Do you mean: X, Y?"; unmatched keep "You don't see X."
- `engine/item_actions.py` — `examine` character path falls back to description matching before item matching; `steal_item` target resolves by description too (ambiguous → ValueError listing candidates).
- `static/js/agent/prompt-builder.js` — `anonymousName()` now returns a description-derived label (e.g. "the tall woman in a green cloak") for strangers instead of the real name + "(unknown to you)". "People here" no longer repeats the description for strangers.

## Files Modified

1. `engine/matching.py` — description-based character matching ✅
2. `routes/action.py` — attack resolves via matcher with ambiguity handling ✅
3. `static/js/agent/prompt-builder.js` — `anonymousName` returns true unknown display name ✅
4. `player.py` — `unknown_name` field + `unknown_display_name()` + `has_met()` + serialization ✅
5. `engine/item_actions.py` — examine + steal description fallback ✅
6. `engine/area_description.py` — strangers shown by appearance ✅
7. `virtual_world_engine.py` — `_match_character_name` delegate ✅

## Testing

- [x] Attack by description resolves to the correct character — matcher tests (`tests/test_matching.py::TestCharacterMatching`)
- [x] Ambiguous descriptions prompt for a choice — candidates returned, surfaced in attack/steal/examine
- [x] Unknown name is shown until the character is met — area description + prompt-builder
- [x] Real name appears after meeting (relationship set) — `has_met` + `unknown_display_name` tests (`tests/test_player_meeting.py`)
- [x] Examine by description — `tests/test_item_actions.py::test_examine_character_by_description`

## Notes / Follow-ups

- **Live-verify:** spawn a fresh world, walk two NPCs together — a stranger should appear as "the tall woman…", `attack the tall woman` should resolve, and after the first shared-area meeting the real name shows.
- `talk to` and `give to` aren't separate command surfaces in `routes/action.py` (speech is directional via say/whisper/shout) — nothing to hook there yet.
- **Fixed in this round (task-171 follow-up):** `area_description.py` no longer prints `[holding: Create Flame]` for anyone — intrinsic-ability items are filtered from the carried list. Also fixed a reveal ordering bug: the first sighting now shows the stranger by appearance, and the real name appears from the next encounter (the meeting was being registered before the line was built, leaking the name on first sight).
- The `worldState.data.players` keys stay as real names (used as map keys); anonymization happens at render time (area description / prompts).
