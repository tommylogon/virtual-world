---
type: bug
status: review
area: ui
priority: high
---

# bug-518: NPC action results render as 'You' in the turn feed because result rows carry no actor

**Filed:** 2026-10-04
**Related:** task-692, task-340

## What

Carry the performing actor on result rows so turn-feed stops attributing every NPC action to the human.

## Acceptance

- Reproduce: an NPC performs an action in a live session; assert the
  🔎 result row displays that NPC's name, not `You`.
- A human action still displays `You`.
- Assert the attribution comes from a carried actor, not from a name
  comparison against `activePlayer` - a test that renames the active
  player mid-session and re-checks.
- No regression in the `tf-you` / `tf-other` grouping, which also keys
  off `isPlayer`.

## Measured 2026-10-04, from a live HTC trace (mansion scenario)

Three consecutive NPC actions, all attributed to `You`:

    ▶️ sammy lopez   eat granola_bar
    🔎 You           You eat the granola_bar.

    ▶️ kayla jenkins  use lighter
    🔎 You           You light the lighter. The area is now dim.

The actors are known - the `▶️ action` row immediately above each one
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
(`agent-engine.ts:790`) - plain text with no actor prefix - so
`parsed.actor` is empty, `isPlayer` is true, and the NPC's action is
rendered as the human's.

Note the fallback `worldState.data.activePlayer` is a **display name**,
so this compares against the active player's name and inherits every
name-matching concern from `engine/matching.py` (task-619 records the
same field being stored in two shapes).

## How

Emit result rows with the actor, the way action rows already do. This is
the same fix surface as task-692's director pass, which is why the two
are related - a narration row that carries its actor makes this
unrepresentable rather than merely fixed.

## Implemented (2026-10-06)

Two halves, because the actor was available at the emit site and thrown away at
the read site:

- **`static/js/agent/turn-feed.ts`** - the `result` branch of `parseEntry` now
  returns `actor: structuralActor` (the row's stamped actor) instead of a
  hardcoded `null`. A row with no actor (a human action, or a system row) still
  resolves to `null` and renders as `You`.
- **`static/js/agent-engine.ts`** - the five `msg-result` emissions now pass the
  performing character as the 4th `actor` argument of `events.log`
  (`event-stream.ts:211` `log(text, className, meta?, actor?)`), so attribution
  comes from a **carried actor**, not a name comparison against `activePlayer`.
  Note: the actor had to be the 4th argument, not a key in `meta` - the bus
  carries `actor` at the top level (`event-stream.ts:218`) and the feed reads
  `data.actor` (`turn-feed.ts:57`); a `meta.actor` would be silently ignored.

Sites updated: the human-reply result (`:486`), action rejected (`:742`), noop
(`:752`), the main per-character result (`:790`), and the retry result (`:1302`).

**Regression test** added to `tools/unit/test_turn_feed_scope.js`: an NPC result
row carries its actor, an actor-less result row stays `null` (→ `You`). Unit
runner green: **618 passed, 0 failed**.

Not yet verified in a live LLM turn (that needs a real NPC action); the parse
fix - the exact defect - is covered by the unit test.

## Why

Action-result rows in the turn feed previously lacked an explicit performing actor field. The parser defaulted unassigned rows to the human player (You), misattributing NPC actions in multi-actor turn feeds.

## Steps to verify

1. Run turn feed unit tests
   - expected: node tools/unit/run.cjs passes turn feed scope tests
   - observed: 828 passed, 1 failed - the sole failure is the pre-existing
     `test_plan_grounding.js :: carried items satisfy use/take even when absent
     from the area`; every `test_turn_feed_scope.js` case is green
2. Verify NPC action result row attribution live
   - expected: an NPC action-result row carries its actor and renders in
     `.tf-other`, not as `You`
   - observed: live LLM turn, Arix's `dash meat racks` result rendered
     `🔎 Arix   No exit 'meat racks'. Visible exits: south passage` in
     `tf-group tf-other`
3. Verify a human action still reads `You` live
   - expected: the controlled character's own result row renders in `.tf-you`
   - observed: `Gribba` running `look` rendered `🔎 You   Bright light floods
     the area...` in `tf-group tf-you` (after the `activePlayerName` fix; before
     it the same row rendered `🔎 Gribba` in `tf-other`)

## Files

- `static/js/agent/turn-feed.ts`
- `static/js/agent-engine.ts`
- `static/js/event-stream.ts` (the 4th `actor` argument on `log`)
- `tools/unit/test_turn_feed_scope.js`

## Browser UI and intended live verification

Intended UI home: Event stream → the action-result row inside the active turn card. It must use the actor carried by that result row, then apply the existing `tf-you` / `tf-other` grouping.

Current availability: implemented on 2026-10-06 and re-verified at code and unit level on
2026-10-21 (see below). The live LLM turn is the only thing still unobserved: the
parse fix is covered by a unit test, but no real NPC action has been driven
through a browser session since the change.

Live steps:

1. Settings -> Agent Settings -> enable `⏭️ Turn-Based Mode`, turn mode
   `Sequential`. An API key is required, because NPC turns are LLM calls.
2. Load a scenario with NPCs (for example `kraktooth_goblin_camp`, active player
   `Gribba`). The human turn composer (`#htc-modal`) opens for the controlled
   slot; `Turn: 0` with the modal open is correct, not a hang.
3. Press `⏭ end turn`. NPCs take their slots.
4. When the composer reopens, read the right-hand `What happened` feed
   (`#htc-feed-lines`).
   - expected: the NPC's action-result row sits in a purple-left `.tf-group.tf-other`
     headed by the NPC's name and does not say `You`; your rows sit in the
     blue-left `.tf-group.tf-you` and say `You`.
5. Act once yourself (`Act`) and confirm your own result row still says `You`.
6. Rename the controlled character mid-session:
   `await ApiClient.updateCharacter('Gribba', {new_name: 'Gribba Two'})`, then
   end another turn.
   - expected: NPC attribution is unchanged, because it follows the actor
     carried by the result row, not a display-name comparison.
7. Read-only console dump of the feed groups:
   ```js
   [...document.querySelectorAll('#htc-feed-lines .tf-group')].map(g => ({
     group: g.className,
     actor: g.querySelector('.tf-actor')?.innerText,
     text: g.innerText.slice(0, 100)
   }))
   ```

This section defines intended access and live acceptance. It is not a claim that
the live steps have been run.

## Verified 2026-10-21

- `static/js/agent/turn-feed.ts:284` returns `actor: structuralActor` on the
  `result` branch; a row with no actor still yields `null` and renders as `You`.
- All five `msg-result` emissions in `static/js/agent-engine.ts` pass the
  performing character as the 4th argument of `events.log` (`:537`, `:824`,
  `:834`, `:872`, `:1488`). `static/js/event-stream.ts:217-218` puts that value on
  the bus payload as a top-level `actor`, not inside `meta`.
- `node tools/unit/run.cjs` - 782 passed, 0 failed. The bug-518 cases are in
  `tools/unit/test_turn_feed_scope.js` ("an NPC result row is attributed to its
  actor, not to You", "an actor-less result row still reads as the player").
- Not verified: a live LLM turn. That needs the server plus a real NPC action, so
  the browser acceptance above is still open.

## Verified 2026-10-22 (live), and a second defect it exposed

The parse fix was correct, but the `playerName` it compares an actor against was
itself broken, and a live human action is what showed it.

- The read site resolved the controlled character as
  `worldState.data.activePlayer`. That key does not exist: the payload key is
  `active_player` and the supported accessor is the `worldState.activePlayer`
  getter (`static/js/world-state.ts:327`). `playerName` therefore always fell
  back to `'You'`, so once result rows began carrying an actor, a human's own
  result row (`actor: 'Gribba'`) no longer matched and rendered as `Gribba` in a
  `tf-other` group. The actor-carrying fix turned an NPC misattribution into a
  human misattribution on the same lookup.
- Fix: `activePlayerName()` resolves through `worldState.activePlayer`, falls
  back to a camelCase `data.activePlayer` for older states, and returns `null`
  when unknown. Both feed renderers (`renderStructured`, `renderDetailedFeed`)
  use it, so a human actor resolves to `You` again and an NPC actor cannot.

Live evidence. Isolated server in a detached worktree at HEAD plus this fix
(port 4455), scenario `kraktooth_goblin_camp`, real LLM turns through OpenRouter:

- NPC turn, Arix acting autonomously. A real `msg-result` row, grouped
  `tf-other`:

      ▶️ Arix   dash meat racks
      🔎 Arix   No exit 'meat racks'. Visible exits: south passage

- Human turn, the controlled character `Gribba` executing `look`. Grouped
  `tf-you`:

      ▶️ You   look
      🔎 You   Bright light floods the area, illuminating every detail...

- Rendering was read through `TurnFeed.render` into a detached host (the
  function the composer drives through `#htc-feed-lines`), so the grouping and
  the actor substitution are the production code path, not a re-implementation.

Remaining gaps, stated plainly:

- The mid-session rename is covered at unit level (the resolver follows the new
  name) and not by a second live LLM turn.
- A `render`-level unit test could not be written: `tools/unit/run.cjs` loads
  `static/js/agent/turn-feed.js`, and `tools/unit/test_graph_background.js`
  replaces `window.document` with a two-method stub and never restores it, so
  every later test file that renders DOM loses `document.createElement`. That
  leak is a harness defect in its own right, not part of this bug.

