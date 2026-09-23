# Bug 33 — Human-initiated speech lands outside turn cards in event stream

**Status:** Done — fixed 2026-09-22.

## Symptoms

Speech/emotes issued by a human-controlled character via `/api/action` rendered
as bare `💬 [Tick N] <name> says ...` entries BEFORE the next `▾ <name> [Turn N]`
card opened — visually outside the turn grouping. Agent-initiated lines grouped
correctly inside their turn cards.

## Root cause

Turn cards open only from agent phase markers (`event-stream.js` `logPhase` →
`StreamTurnCards.bodyFor`, `observe`/`think` force a fresh card). A human turn has
no phase marker before its speech: `agent-engine.js::_executeHumanReply` calls
`_speakLine` (and `_performEmote`) before the first `logPhase(charName, 'act')`,
so the speech row is emitted with no open card and drops into the bare stream.

## Fix (2026-09-22)

- `event-stream.js`: new `EventBus.beginActorTurn(charName)` — opens (or reuses)
  the turn card for an actor, safe to call repeatedly within a turn.
- `agent-engine.js::_executeHumanReply`: calls `events.beginActorTurn(charName)`
  before speech/emote/action, so the human's whole turn groups under one card
  (the subsequent `act` phase reuses it).
- `human-turn-composer.js::interject`: opens the card for the character and logs
  the aside's output as `msg-result` (an agent-family row) instead of
  `system-msg`, so the interjection and its result also group.

## Also noticed in the same session (fold into fix or split)

The take-failure concatenation glitch ("earringfrom", doubled "the") was already
fixed separately in bug-27 (`_display_name` + a leading space before the relation
clause); no remaining work here.

## Verification

- `npm run lint` and `npm run typecheck` clean.
- Manual: control a character and speak → the speech line, emote, action and
  result all sit inside the character's turn card; interjections likewise.
