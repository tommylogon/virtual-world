---
type: task
status: review
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-790: Human turn panel: a proper recap of what other characters did

**Filed:** 2026-10-12
**Related:** task-333, task-334, task-679

## What

Replace the 260-char sentence-join recap with a real summary of what other characters said and did while it was not your turn. Remove hard-coded text truncations across turn feed lines.

## Why

In turn-based play with multiple actors (such as ensemble cast drama like Millwood), several NPCs speak and act between human slots. The previous implementation in `static/js/agent/turn-feed.ts` capped the narrative at 260 characters using `text.slice(0, 257) + '...'` and truncated actions/results at 180/140 characters. This silently swallowed dialogue and physical movements after the first actor or two.

## How

- Remove arbitrary string slicing in `buildConciseNarrative` and `buildSummary` in `static/js/agent/turn-feed.ts`.
- Eliminate arbitrary truncation in `truncateResult` so full speech and action outcome text are preserved.
- Structure NPC turns by actor, grouping spoken lines and physical actions clearly.
- Render an informative fallback ("No other characters acted.") in the turn recap banner when no other actors acted during the interval.
- Enforce the policy against silent string truncation across narrative and log texts in `AGENTS.md`.

## Steps to verify

1. Author long dialogue exceeding the old 260-character threshold and verify no silent truncation:
   - expected: full lines retained without trailing ellipsis slicing.
   - observed: verified in `tools/unit/test_turn_feed_recap.js` (3 passed).
2. Author multiple NPC actions and speech lines in one turn interval:
   - expected: actors are summarized distinctly with their spoken lines and physical actions.
   - observed: verified in `tools/unit/test_turn_feed_recap.js`.
3. Check fallback when no other characters acted:
   - expected: recap indicates no other characters acted rather than leaving a stale banner or blank display.
   - observed: verified in `tools/unit/test_turn_feed_recap.js`.

## Acceptance

- [x] The 260-character hard cap and arbitrary string slicing in `turn-feed.ts` are removed.
- [x] Other characters' speech and actions are grouped and summarized by actor.
- [x] Empty intervals cleanly report that no other characters acted.
- [x] Unit tests cover multi-actor summarization, long dialogue preservation, and empty interval reporting.

## Files

- `static/js/agent/turn-feed.ts`
- `static/js/agent/turn-feed.js`
- `tools/unit/test_turn_feed_recap.js`
- `AGENTS.md`

## Browser UI and intended live verification

Intended UI home: Turn-based play -> resolve the controlled character's human-turn prompt -> Human Turn Panel's recap of the actors who took turns since that character last acted.

Current availability: Available in the Human Turn Composer / Turn Feed modal via the "Since your turn:" / "Observed:" recap header.

Live steps when available:
1. Load a turn-based scenario with the controlled character and at least two NPCs; let one NPC move and the other speak before the controlled character's next turn.
   - expected: the Human Turn Panel names both NPCs and separately summarizes the movement and spoken line that occurred while the player waited.
2. Add enough distinct actions and speech to exceed the old 260-character limit, then open the next human turn.
   - expected: the recap remains complete or provides an explicit expand affordance; later actors and their actions are not silently truncated.
3. Advance another turn with no NPC actions and open the panel.
   - expected: the recap says no other-character actions occurred instead of repeating stale content from the prior turn.
4. Compare the recap with the event stream for the same tick/turn interval.
   - expected: actor names and summarized actions correspond to events in that interval; the recap does not claim actions outside it.
