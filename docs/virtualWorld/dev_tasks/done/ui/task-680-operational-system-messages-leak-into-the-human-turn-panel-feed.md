---
type: task
status: done
area: ui
priority: medium
---

# task-680: Operational system messages leak into the human turn panel feed

**Filed:** 2026-10-04
**Related:** 

## Goal

Reporter sees save/load/library chatter in the HTC 'What happened' feed: 'scenario saved', loadout and grid messages. They are editor/GM operations with no place in the narrative a player reads. turn-feed.isObserverVisible already drops parsed.type === 'system', but parseEntry re-labels a system row as type 'action' whenever _tryParsePrefixedName matches (and as 'npc' for 'did nothing this turn'), so those rows leak. Filter operational chatter at the feed boundary rather than at each of the ~230 events.log('system-msg') call sites, which the raw event stream still needs.

## Acceptance

- [x] `system-msg` / `agent-msg` rows never enter the turn-feed ring
- [x] the one system row that IS a turn row (`<name> did nothing this turn`) survives
- [x] speech / emote / action / result rows unaffected
- [x] the raw event stream still shows everything (the filter is feed-local)
- [x] regression test proven to fail without the filter

## Resolution

Filtered at the ring push in `static/js/agent/turn-feed.ts` `install()`, which is
the feed's boundary with the whole-app event log. `className` is
`system-msg`/`agent-msg` and the text is not `did nothing this turn`.

Measured before choosing this: of every `system-msg` row, `parseEntry` leaves
`kind = 'system'` (already dropped by `isObserverVisible`) for all but two
shapes — `did nothing this turn` → `npc` (legitimate, kept) and a
`_tryParsePrefixedName` match → `action` (the leak). `👾 <actor> <action>: …`
rows do not match the parser, so nothing else that renders today is lost.

Tests: `tools/unit/test_turn_feed_scope.js` (4). Verified failing with the
filter disabled (`564 passed, 1 failed`) and green with it (`565 passed`).
