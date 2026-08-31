---
type: bug
status: todo
area: gameplay
---

# bug-35: give/steal skip the tiered item matcher — no fuzzy/alias fallback

**Filed**: 2026-08-30

**Status**: Todo — confirmed 2026-08-30 from live playtest (John two / Jane three).

## Observed

Player is carrying/wearing the Jumpsuit (take + equip work with exact names):

```
[Tick 3] John two > take jumpsuit
[Tick 4] World You're already carrying the Jumpsuit.
[Tick 5] John two > equip jumpsuit
[Tick 6] World You're already wearing the Jumpsuit.
[Tick 7] John two > give jumptuit to jane
[Tick 8] World You aren't carrying 'jumptuit'.
```

A misspelled item name ("jumptuit" vs "jumpsuit") fails with a bare
"You aren't carrying …" — no fuzzy resolution, no "did you mean" fallback.
Other verbs (`take`, `examine`, `use`) resolve the same input via the
tiered matcher, so this is only a give/steal inconsistency.

(The character name match "jane" → "jane three" was CORRECT behavior — not a bug.)

## Root cause

`give_item` / `steal_item` in `engine/items/transfer_actions.py` resolve the
item via `player_manager.find_item_node()` (`engine/player_manager.py:119`),
which is strict substring matching only, and never calls
`matching._match_item_name` (the 3-tier resolver: exact → substring →
alias/description → difflib fuzzy, cutoff 0.7). No `_fuzzy_match_note` is
produced, and the "You don't know exactly who that is" style disambiguation
that the character matcher offers has no item-side equivalent here.

Note: `find_item_node` DOES scan `EDGE_EQUIPPED` as well as `EDGE_CARRYING`
(`player_manager.py:137`), so giving an item you're WEARING works with a
correct name (and `give_item` already strips the item out of the equipped
stack on transfer — `transfer_actions.py:44-49`). The gap is matching, not
search space.

## Fix direction

- Route give/steal item resolution through the same tiered matcher used by
  take/examine (exact → substring → alias → fuzzy with cutoff), preserving
  the carrying+equipped+area search space.
- Surface the fuzzy/alias match note in the output (e.g. "matched 'jumptuit'
  as item 'Jumpsuit' (fuzzy match)"), consistent with the notes the exit and
  character matchers already emit.
- Keep/verify the equipped-stack removal path so handing over a worn item
  remains risk-free.

## Tests

- Add `tests` coverage: misspelled item name on `give` fuzzy-resolves;
  exact worn-item give transfers + unequips; give with ambiguous candidates
  suggests like the character matcher does.
