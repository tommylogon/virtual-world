# Bug 27 — Outcome lines render "the the <item>" with missing space before relation

**Status**: Done — fixed 2026-08-28.

## Found

`taco_bell_event_log_2026-08-23T16-19-57.txt` (reproduced twice):

- Tick 23: `You pick up the the blue butterfly earringfrom under the Booth Table.`
- Tick 39+ RECENTLY echo: same string.

Two defects in one line:

1. **Doubled article** — "the the". The model's action said
   `"item": "take the Blue Butterfly Earring"` (the verb leaked into the item
   field) and/or the pickup template prefixes its own "the" without checking
   whether the matched name already starts with one.
2. **Missing space before the relation clause** — `earringfrom`. The result
   template joins `<name>` + `from under the <surface>` with no separator.

## Why it matters

Outcome lines are the engine's voice (G2 in presence-gap analysis). This one
appears on nearly every container-surface pickup, so the most common action in
the game renders with a visible stutter right next to character prose.

## Fix sketch

Find the take/pickup result template (engine/matching.py handle or
routes/action_handlers.py take path — trace from `_execute_take`/item-actions).
- Strip a leading article ("the ", "a ", "an ") from the matched display name
  if the template adds its own, or never add one and always use the node's
  canonical name.
- Join relation clauses with a space; sweep sibling templates (put/reveal/search)
  for the same join pattern.

## Verify

- Take an item that sits *under/on/in* something → log shows exactly one
  article, `... earring from under ...` spacing.
- Grep any new export for regex `the the|e[a-z]+from` → zero hits.

## Implementation (2026-08-28)

Both defects were **engine-side**, in `engine/items/take_drop_actions.py` (not the export):

1. **Doubled article** — the result templates hardcoded `"the "` + the raw action
   `item_name` (e.g. `"the blue butterfly earring"`), producing `the the`. Added a
   module helper `_display_name(name)` that strips a leading `the`/`a`/`an`, and
   applied it across every take/drop phrasing (`take the …`, `pick up the …`,
   `put … away and take …`, `try to take the …`, `The … is gone.`,
   `already wearing/carrying the …`, `dropped the …`).
2. **Missing space** — the spatial relation clause was built as `f"{prep} the
   {surface}"` with no leading space, so `<name>` + `from under the <surface>`
   joined as `earringfrom`. Now the prep branch prefixes a space
   (`f" {prep} the {surface}"`), matching the container branch.

Verified: `engine/items/take_drop_actions.py` compiles; `tests/test_item_actions.py`
(61) all pass. Taking an item `under the Booth Table` now reads
`You pick up the blue butterfly earring from under the Booth Table.`
