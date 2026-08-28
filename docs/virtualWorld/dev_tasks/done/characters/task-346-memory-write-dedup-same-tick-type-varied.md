# task-346 — Dedup same-tick near-verbatim memory writes

**Status**: Done — implemented 2026-08-27.

## Found

Mansion session, sammy lopez decide-phase `=== I REMEMBER ===`:

```
[1 minute ago] 💭 the calling cards in the foyer name the family:
    augustus, cordelia, and three blackwood children — likely connected to the diary...
[1 minute ago] 👁️ jake's idea. it's always jake's idea...
[1 minute ago] 📝 the calling cards in the foyer name the family:
    augustus, cordelia, and three blackwood children — likely connected to the diary...
```

The identical insight written as both a thought (💭) and a memory write (📝)
within the same turn. Existing dedup (`static/js/agent/memory-manager.js`
`_storeReactionMemory`: dedup by text + tick±1) only guards the reaction
memory against itself; it doesn't compare across writers (think-phase 💭,
observed 👁️ events surfacing as memories, react 📝).

## Impact

Each duplicate permanently occupies recall slots and shows up together in
every future I REMEMBER block — attention tax on every subsequent turn, and
the character treats one insight as three distinct beats when reflecting.

## Fix sketch

At write time, compare candidate entry against recent entries (same tick
window ±2) with normalized-text similarity (casefold, strip punctuation,
maybe token Jaccard > 0.8) regardless of type; skip or merge types keeping
highest importance. Server-side guard preferable (single choke point on
`POST /api/players/{name}/memories/entry`) so all writers benefit.

Related context: recall ALREADY-KNOWN guard exists client-side
(memory-context.js) — this is the WRITE-side sibling.

## Verify

Unit test: post same-text observation+thought+memory entries in one tick →
one stored row survives. Play session where a discoverable fact triggers
multiple writes → single line in next turn's I REMEMBER.

## Implementation (2026-08-27)

- **Server-side write choke point** `routes/memories.py::add_player_memory`
  (`POST /api/players/<name>/memories/entry`). Before appending, it scans the
  character's existing memories for a near-verbatim duplicate within a small
  tick window (`_is_near_duplicate`, Jaccard ≥ 0.8 on normalized lowercase
  tokens, `tick` within ±2), **regardless of type**. On a hit it merges the
  higher importance + union of tags, keeps the longer text, and returns the
  existing entry with `"deduped": true` instead of appending a third copy.
- **Opt-out**: `force: true` in the payload bypasses dedup — used by the manual
  memory editor / generator saves so a deliberate user save is never silently
  collapsed.
- **Tests**: `tests/test_memory_api.py` — `test_write_dedup_collapses_same_tick_near_verbatim`
  (two same-tick writes → one row, highest importance kept) and
  `test_write_dedup_allows_force_and_distinct` (force bypass + distinct text
  stays). `tests/test_memory_api.py`, `tests/test_memory_effects.py`,
  `tests/test_vector_store.py` all pass (43 total).
