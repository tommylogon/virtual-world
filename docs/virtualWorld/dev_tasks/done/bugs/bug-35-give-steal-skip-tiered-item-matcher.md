---
type: bug
status: done
area: gameplay
---

# bug-35: give/steal skip the tiered item matcher — no fuzzy/alias fallback

**Status:** Done — fixed 2026-09-22.

**Filed**: 2026-08-30 from live playtest (John two / Jane three).

## Observed

Player is carrying/wearing the Jumpsuit; a misspelled `give jumptuit to jane`
failed with a bare "You aren't carrying 'jumptuit'." — no fuzzy resolution.
`take`/`examine`/`use` resolve the same input via the tiered matcher, so this
was a give/steal inconsistency.

## Root cause

`give_item` / `steal_item` (`engine/items/transfer_actions.py`) resolved the item
via `player_manager.find_item_node()` (strict exact/substring only) and an inline
strict scan, never calling the tiered resolver
(`engine/matching.py::_match_item_name`: exact → substring → alias/description →
difflib fuzzy, cutoff 0.7).

## Fix (2026-09-22)

- `engine/matching.py`: split the tier logic into `_match_item_name_from(input,
  names)` and added `match_item_name_in_inventory(input, owner_id)` — the same
  tiers scoped to one character's carried + equipped items (never area items).
  `_match_item_name` now collects area + inventory names and delegates, so its
  behaviour is unchanged.
- `engine/items/transfer_actions.py`:
  - `give_item` resolves through `match_item_name_in_inventory` for the giver,
    falls back to the strict lookup, and uses the canonical name in the output.
  - `steal_item` resolves through the same helper for the victim, with a strict
    fallback. Worn (equipped) items remain eligible.
  - Because the matcher sets `_fuzzy_match_note`, the note is surfaced through
    the existing `/api/action` `system_messages` channel (routes/action_handlers)
    — no new plumbing.
- **Latent transfer bug found while testing:** `give_item` removed only the
  `CARRYING` edge from the giver, so handing over a WORN item left a dangling
  `EDGE_EQUIPPED` edge (and multi-slot markers). It now removes the equipped edge
  and cleans markers too.

## Tests

- `tests/test_matching.py::TestInventoryScopedItemMatching` — fuzzy misspelling
  resolves, area items are out of scope, alias resolves a worn item.
- `tests/test_item_actions.py::TestGiveItem` — misspelled give transfers the
  resolved item; worn item give transfers and unequips.
- `tests/test_item_actions.py::TestStealItem` — misspelled steal resolves;
  equipped-item steal still works.
