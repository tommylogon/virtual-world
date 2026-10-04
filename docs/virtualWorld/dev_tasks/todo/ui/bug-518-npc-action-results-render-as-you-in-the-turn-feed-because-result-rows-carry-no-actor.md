---
type: bug
status: todo
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
