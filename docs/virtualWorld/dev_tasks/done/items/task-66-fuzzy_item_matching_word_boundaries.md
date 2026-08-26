# Fuzzy Item Matching: Word Boundaries

**Filed**: 2026-07-19
**Priority**: High
**Status**: Done — Option A (word-boundary regex) + alias tier live in engine/matching.py:155-196. Audited 2026-08-03

## Summary

`_match_item_name()` uses substring matching (`nn in ni`) which matches item names inside compound words. `examine dusty_bookshelf` matches item `"Book"` because "book" is a substring of "bookshelf". The engine should respect word boundaries.

## Current State

`virtual_world_engine.py:167` (`_match_item_name`):

```python
# Tier 2: substring
for item_name in candidates:
    nn = item_name.lower().replace('_', ' ').replace('-', ' ')
    if ni in nn or nn in ni:
```

- `ni` = normalized input = "dusty bookshelf"
- `nn` = normalized item name = "book"
- `nn in ni` → `"book" in "dusty bookshelf"` → True (because "book" is part of "bookshelf")

This produces false positives when the item name is a partial substring of a word in the input.

## Affected Commands

All commands using `_match_item_name`:
- `examine X` → via `get_item_desc` (line 1630)
- `take/get/pickup X` → via `take_item` (line 1768)
- `use X` / `use X on Y` → via `_find_item_node` / `_match_item_name`
- `drop X`, `toggle X`

## Fix Options

### Option A: `re.fullmatch` with word boundaries

Replace the substring check with word-boundary regex:

```python
import re
# Word-boundary aware match
if re.search(r'(?<!\w)' + re.escape(nn) + r'(?!\w)', ni) or \
   re.search(r'(?<!\w)' + re.escape(ni) + r'(?!\w)', nn):
```

This requires "book" to appear as a complete word in "dusty bookshelf" — which it doesn't (it's part of "bookshelf").

### Option B: Prioritize exact name components

Split input into space-separated words and check if any word matches an item name exactly. Then fall back to substring.

### Option C: Match item name as prefix/suffix of input words

Only match if the item name starts or ends at a word boundary in the input. E.g., "book" in "red book" matches (space before "book"), but "book" in "bookshelf" doesn't.

**Recommendation**: Option A — word-boundary regex. It's the most correct and handles all edge cases.

## Edge Cases

| Input | Item Name | Current | Expected |
|-------|-----------|---------|----------|
| "dusty bookshelf" | "Book" | MATCH (wrong) | no match |
| "dusty book" | "Book" | MATCH | MATCH |
| "books" | "Book" | MATCH | no match (plural ≠ singular — let substring handle if needed) |
| "book" | "Bookshelf" | MATCH (ni in nn) | no match (keep? maybe keep as fallback) |
| "sand" | "Sandwich" | MATCH | no match |
| "key" | "Keycard" | MATCH | debatable — "key" is a meaningful prefix of "keycard" |

For the last case, "key" matching "Keycard" is useful but "key" matching "Donkey" would be wrong. The `nn in ni` check (item name in user input) is less prone to false positives than `ni in nn` (user input in item name). Consider removing `ni in nn` entirely and only keeping `nn in ni` with word boundaries.

## Files

- `virtual_world_engine.py:167-218` — `_match_item_name()`
