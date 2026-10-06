---
type: bug
status: review
area: ui
priority: high
---

# bug-518: NPC action results render as 'You' in the turn feed because result rows carry no actor

**Filed:** 2026-10-04
**Related:** task-692, task-340

## Goal

Carry the performing actor on result rows so turn-feed stops attributing every NPC action to the human.

## Acceptance

- Reproduce: an NPC performs an action in a live session; assert the
  🔎 result row displays that NPC's name, not `You`.
- A human action still displays `You`.
- Assert the attribution comes from a carried actor, not from a name
  comparison against `activePlayer` — a test that renames the active
  player mid-session and re-checks.
- No regression in the `tf-you` / `tf-other` grouping, which also keys
  off `isPlayer`.

## Measured 2026-10-04, from a live HTC trace (mansion scenario)

Three consecutive NPC actions, all attributed to `You`:

    ▶️ sammy lopez   eat granola_bar
    🔎 You           You eat the granola_bar.

    ▶️ kayla jenkins  use lighter
    🔎 You           You light the lighter. The area is now dim.

The actors are known — the `▶️ action` row immediately above each one
names them, because `events.log(\`[Action] ${finalAction}\`,
"msg-action")` is emitted inside the per-character loop in
`static/js/agent-engine.ts`.

## Cause

`static/js/agent/turn-feed.ts:560-563`:

    const playerName = ... worldState.data.activePlayer ... : 'You';
    const isPlayer = !parsed.actor || parsed.actor === 'You' || parsed.actor === playerName;
    const actorKey = parsed.actor || '???';
    const displayActor = isPlayer ? 'You' : observerName(parsed.actor);

`!parsed.actor` makes an actor-less row count as the player's. The
result row is logged as `events.log(outputText, 'msg-result', {...})`
(`agent-engine.ts:790`) — plain text with no actor prefix — so
`parsed.actor` is empty, `isPlayer` is true, and the NPC's action is
rendered as the human's.

Note the fallback `worldState.data.activePlayer` is a **display name**,
so this compares against the active player's name and inherits every
name-matching concern from `engine/matching.py` (task-619 records the
same field being stored in two shapes).

## Fix

Emit result rows with the actor, the way action rows already do. This is
the same fix surface as task-692's director pass, which is why the two
are related — a narration row that carries its actor makes this
unrepresentable rather than merely fixed.

## Implemented (2026-10-06)

Two halves, because the actor was available at the emit site and thrown away at
the read site:

- **`static/js/agent/turn-feed.ts`** — the `result` branch of `parseEntry` now
  returns `actor: structuralActor` (the row's stamped actor) instead of a
  hardcoded `null`. A row with no actor (a human action, or a system row) still
  resolves to `null` and renders as `You`.
- **`static/js/agent-engine.ts`** — the five `msg-result` emissions now pass the
  performing character as the 4th `actor` argument of `events.log`
  (`event-stream.ts:211` `log(text, className, meta?, actor?)`), so attribution
  comes from a **carried actor**, not a name comparison against `activePlayer`.
  Note: the actor had to be the 4th argument, not a key in `meta` — the bus
  carries `actor` at the top level (`event-stream.ts:218`) and the feed reads
  `data.actor` (`turn-feed.ts:57`); a `meta.actor` would be silently ignored.

Sites updated: the human-reply result (`:486`), action rejected (`:742`), noop
(`:752`), the main per-character result (`:790`), and the retry result (`:1302`).

**Regression test** added to `tools/unit/test_turn_feed_scope.js`: an NPC result
row carries its actor, an actor-less result row stays `null` (→ `You`). Unit
runner green: **618 passed, 0 failed**.

Not yet verified in a live LLM turn (that needs a real NPC action); the parse
fix — the exact defect — is covered by the unit test.
