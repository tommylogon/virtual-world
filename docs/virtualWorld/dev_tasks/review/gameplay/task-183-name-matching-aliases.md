# Task: Name Matching — Word-Boundary + Item Aliases

**Status**: Implemented (verified 2026-08-06) — all changes present in code:
- `engine/matching.py`: word-boundary substring tier in `_match_item_name` (raw `input_lower in nl` replaced) and `_match_exit_direction`; single-char guard (`len(input_lower) < 2`); alias tier matching item `aliases` + description words before fuzzy; fuzzy `cutoff=0.7`.
- `data/library/items/kindling.json` + `world_template.json`: kindling aliases `["twigs","dry twigs","firewood"]`.
- `engine/serialization.py`: `aliases` survives save/load round-trip.
- `_fuzzy_match_note` still surfaced as `system_messages` (routes/action.py).
The `stove`→`Stovepipe Leather Boots` and `twigs`→`kindling` issues from the task evidence are resolved. Move to `done/` after a backend matching/parser test asserts both cases (referenced in task-184 test plan).

## Goal

Stop fuzzy name matching from resolving an input to a wrong item, and let
players/LLM agents use natural synonyms. Today `use kindling on stove` matches
`stove` → `Stovepipe Leather Boots (Pair)` because `_match_item_name` does a raw
substring check (`input_lower in nl`), and `take twigs` fails even though the
area has `kindling` ("a bundle of dry twigs").

Evidence from `event_log_2026-08-02T12-00-06.txt`:
- `matched 'stove' as item 'Stovepipe Leather Boots (Pair)' (substring match)` → "You use the Stovepipe Leather Boots (Pair)." (repeated ×5)
- `You search for 'twigs' but can't find it here` (repeated ×6) — area item is `kindling`

## Changes

### 1. Engine: `engine/matching.py` — `_match_item_name`
- **Fix the substring tier (lines 126-141):** the raw `if input_lower in nl` check matches
  "stove" inside "stovepipe". Replace the item-name tier with a **word-boundary-aware**
  match on *both* sides:
  - `re.search(r'(?<!\w)' + re.escape(input_lower) + r'(?!\w)', nl)` → exact whole-word-in-name.
  - Keep the existing reverse direction (item name appears as a complete word in input).
  - Only fall through to difflib fuzzy when no word-boundary match exists; keep the tight
    `cutoff=0.7` (or raise to 0.75).
- **Guard against pathological single-word inputs:** require the input to be ≥ 2 chars
  before substring/fuzzy tiers (prevents `use X on a` → arbitrary match).
- Add an **alias tier** before fuzzy matching: match `input_lower` against the union of
  `{item name}` ∪ `{item.properties.aliases}` ∪ `{item.properties.description words}`.
  A hit on an alias should emit the same `(substring match)`/`(alias match)` note so the
  player/agent sees what resolved.

### 2. Engine: `engine/matching.py` — `_match_exit_direction`
- Apply the same word-boundary treatment to the exit substring tier so inputs like
  `hollow floor` no longer fuzzy-match `willow gap` (seen in log:
  `matched 'hollow floor' as exit 'willow gap'`).

### 3. Content: aliases for real items
- `item_kindling` (world template + `data/library/items/kindling.json`): add
  `"aliases": ["twigs", "dry twigs", "firewood"]`.
- Add an optional `aliases` field read path in serialization so it survives save/load
  (check `engine/serialization.py` item node round-trip).

### 4. Surface the note
- Keep sending `_fuzzy_match_note` as `system_messages` (already wired in
  `routes/action.py:477-479`). Optionally include *resolved aliases* in the note so the
  agent can learn the canonical name: `matched 'twigs' as item 'kindling' (alias)`.

## Files Modified
- `engine/matching.py`
- `data/library/items/kindling.json`
- `world_template.json` (kindling node properties, if serialization needs it)
- `engine/serialization.py` (ensure `aliases` survives round-trip)
- `docs/virtualWorld/Items & Inventory/Items Overview.md` (document aliases field)
