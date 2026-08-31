# Bug 33 â€” Human-initiated speech lands outside turn cards in event stream

**Status:** Todo â€” diagnosed 2026-08-23 from taco_bell playtest, not yet fixed

## Symptoms

In the event-stream view, speech/emotes issued by the human-controlled
character via `/api/action` render as bare `ðŸ’¬ [Tick N] <name> says ...`
entries BEFORE the next `â–¾ <name> [Turn N]` card opens â€” visually outside
the turn grouping. Agent-initiated lines group correctly inside their turn
cards.

Observed during taco_bell_date.json playtest (2026-08-23).

## Root cause (diagnosis)

The event stream groups entries into turn cards keyed on agent turns.
Human actions emitted through `/api/action` produce log events immediately,
while the enclosing turn card is only opened by the next agent-driven tick
â€” so the human line precedes any card and falls into the ungrouped zone.

## Also noticed in the same session (fold into fix or split)

- Take-failure message concatenation glitch: "pick up the the blue
  butterfly earring**from** under the Booth Table" â€” missing space between
  item name and trailing clause ("earring" + "from"), plus doubled "the".
  Likely string building in the take/failure message path
  (`engine/item_actions.py` take messaging or matching display-name reuse).
  Worth its own bug if it's a separate code path.

## Fix plan

- Event stream: open/attribute a turn card for human-controlled actions
  too (or render human lines inside the current turn context) so ordering
  is preserved.
- Concatenation: audit take-message construction for missing separators.

## Verification

- Repro: load scenario, control a character, speak â†’ check event stream
  grouping; take an item with a long name near a surface â†’ inspect message.



