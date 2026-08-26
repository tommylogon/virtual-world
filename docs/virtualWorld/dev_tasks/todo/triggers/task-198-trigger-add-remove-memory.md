---
group: Trigger System
---

# Trigger Effects for Character Memory

**Filed**: 2026-08-10
**Priority**: High
**Status**: Todo

---

## Problem

Triggers can modify the world (items, conditions, environment) but cannot touch `Player.memories[]`. We want trigger effects that let in-world events surface, suppress, or strengthen a character's memories — without requiring authors to track individual memory IDs at scale.

Narrative injection is already covered by the `message` effect. This task adds the *memory-state* operations: surface existing memories, suppress them, and reinforce them through repeated exposure.

---

## Design

Three new effect types, all targeting memories by **tag or keyword filter**,
never by individual ID:

### `surface_memory`

Force a matching memory into the agent's active recall for the current turn.

- params:
  - `tags` (list[str]) — memories tagged with ALL of these are surfaced
  - `keywords` (str) — text substring match (case-insensitive)
  - `importance_min` (int, default 0) — minimum importance threshold
  - `salience_boost` (int, default 3) — temporary relevance bump for matching
    memories this turn (written into the memory entry as `salience_override`)
- Matching: tag AND (keyword OR all). If `tags` is empty, match on keywords
  alone. If both are empty, no-op.
- Multiple matches: surface the highest-importance one, then also mark all
  matches with the salience boost so the prompt builder weights them higher.
- Output: a `message`-style narrative line is also emitted: *"A memory surfaces:
  <text>"* (uses the matched memory's text).

### `suppress_memory`

Mark matching memories as inaccessible for the current turn.

- params:
  - `tags` (list[str])
  - `keywords` (str)
  - `duration` (int, default 1) — turns to keep suppressed; 0 = permanent until
    `unblock_memory` fires
  - `scope` (str, default `"self"`) — `"self"` or explicit character name
- Suppressed memories are excluded from `get_relevant_memories()` and from the
  prompt builder's memory context while the suppression is active.
- A memory can carry multiple active suppressions (stack as list); all must
  expire before it surfaces again.
- No output message by default (narrative: the character just can't recall).

### `unblock_memory`

Remove an active suppression from matching memories.

- params:
  - `tags` (list[str])
  - `keywords` (str)
  - `scope` (str, default `"self"`)
- Clears all matching active suppressions immediately.
- No-op if no matching suppressions exist (silent).

### Engine-level `reinforce_memory` (automatic, not a trigger effect)

When a memory is surfaced via `surface_memory` or recalled naturally by the
prompt builder, bump its `importance` by 1 (capped at 10). This is the
spaced-repetition signal — memories that keep coming up organically grow
stronger. Implemented as a post-recall hook inside `get_relevant_memories()` in
`player.py`, not as a trigger effect. Trigger effects should not directly modify
importance; the engine does it based on actual recall frequency.

---

## Memory Entry Shape

Extend `Player.memories[]` entries with two new optional fields:

```python
{
    "id": "abc12345",
    "text": "...",
    "tick": 42,
    "timestamp": 1700000000.0,
    "importance": 5,          # 1-10, engine bumps on reinforce
    "type": "observation",    # existing
    "tags": ["watcher", "keycard"],  # existing, list[str]
    "salience_override": 0,   # NEW: >0 means temporarily weighted higher this turn
    "suppressions": [],       # NEW: list of {"until_tick": N} or [{"source": "..."}]
}
```

`salience_override` is reset to 0 at the start of each turn (in
`advance_clock` / turn-init). `suppressions` is checked in
`get_relevant_memories()` — entries with an active suppression are excluded
from results.

---

## Files

- `player.py` — extend `add_memory` to accept optional `tags` list; add
  `suppress_memory` / `unblock_memory` / `clear_expired_suppressions` methods;
  update `get_relevant_memories` to respect `salience_override` and
  `suppressions`; add reinforce hook (importance +1 on recall, cap 10).
- `engine/effects.py` — add `handle_surface_memory`, `handle_suppress_memory`,
  `handle_unblock_memory`.
- `engine/trigger_system.py` — register the three new effect types in
  `EFFECT_TYPES`.
- `tests/test_memory_effects.py` — new test file covering:
  - surface_memory by tag, by keyword, by both
  - surface_memory with no matches is silent no-op
  - suppress blocks get_relevant_memories for duration
  - suppress with duration=0 persists until unblock
  - unblock removes suppression
  - reinforce bumps importance on recall, caps at 10
  - salience_override resets each turn
  - multiple overlapping suppressions
- `docs/virtualWorld/Rules Engine/Memory System.md` — document the three new
  effect types and the reinforce mechanic.

---

## Out of Scope

- ID-based memory removal (rejected: unauthorable at scale).
- Memory editor UI changes (separate task).
- Embedding-based memory retrieval (separate task; keyword matching is the
  matching mechanism here).
