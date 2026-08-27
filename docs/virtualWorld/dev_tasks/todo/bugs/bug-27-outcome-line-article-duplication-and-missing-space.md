# Bug 27 — Outcome lines render "the the <item>" with missing space before relation

**Status**: Todo — filed 2026-08-27 from export-log review (taco_bell date session).

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
