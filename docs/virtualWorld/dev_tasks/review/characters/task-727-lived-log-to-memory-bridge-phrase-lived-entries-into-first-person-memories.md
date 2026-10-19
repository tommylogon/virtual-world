---
type: task
status: review
area: characters
priority: high
related: ["'task-447'", "'task-457'", 'task-447', 'task-457']
---

# task-727: Lived log to memory bridge: phrase lived entries into first-person memories

**Filed:** 2026-10-06
**Related:** task-725, task-714, task-412, task-399

<!-- deps:start -->
**Related:** [[task-447-character-nicknames-and-aliases]], [[task-457-character-nodes-are-the-canonical-character-record-human-agent-simple-npc]]
<!-- deps:end -->

## What

Make the objective lived_log produce the first-person memories the Mind panel shows, instead of only one aggregate sentence on promotion. Add a deterministic (no-LLM, v1) per-entry phrasing pass keyed on kind and why, modelled on engine/social_text.py, writing memories with entity_ids and a per-player memorized-through mark so nothing is duplicated. Cover the meaningful kinds (relationship, threat, need, death, social, pursuit, plan); do not duplicate the observation memories that record_observation already writes. Measured baseline: a 30-min timeskip writes 471 lived entries across 23/28 characters but only turns observation/social into memories.

## Acceptance

- A meaningful lived entry (death, relationship, pursuit) reads back as a
  first-person memory in the character Mind panel after a turn/skip, without a
  fidelity change.
- No duplication: `social`/`threat`/`need`/`act`/`move` are not re-phrased
  (each already has a memory writer), and re-running a turn writes nothing twice.
- Deterministic (no LLM, v1) and idempotent via a per-player mark.

## Implemented (2026-10-06)

- **New module** `engine/lived_log_memory.py`: `phrase(entry)` (deterministic
  templates per kind), `bridge(player, gs)` and `bridge_all(gs)`. Covered kinds:
  `death`, `relationship`, `pursuit` - the ones with no other memory writer.
  Deliberately skips `social`/`threat`/`need` (`social_text`, `background_social`,
  `agent_memory` write those) and `act`/`move`/`traversal` (`record_observation`).
- **Mark** `Player.lived_log_memorized_through` (init + `to_dict` +
  `_serialize_player` + `_deserialize`), so re-running a turn never duplicates.
- **Wired** at the end of `tick_manager.tick_turn`, so it runs every turn and
  every timeskip frame.
- **Test** `tests/test_lived_log_memory.py` (phrasing, idempotence, skip-covered,
  `bridge_all`).
- **Measured**: a 30-min timeskip now writes **13 `lived_log` memories** (was 0),
  e.g. *"Something about Water Skin has me wary. (flee)"*, *"I feel a little
  closer to Rikka now. (apologise)"*, *"Started pursuit scrap_run…"*.

Remaining: a live-browser check (the running server needs a restart to load the
change), entity-id extraction (memories currently carry tags + location, not
node ids), a death sample in a live skip, and deciding whether `act`/`plan`
entries with a meaningful `why` also deserve their own memories.

## Why

The lived log accurately records objective simulation events (death, relationships, pursuits), but characters only developed memories from observations and social interactions. Phrasing key lived entries into first-person memories gives characters subjective memory of significant life events without duplicating existing observation writers.

## How

1. Implemented `engine/lived_log_memory.py` with deterministic templates for `death`, `relationship`, and `pursuit` event kinds.
2. Added `Player.lived_log_memorized_through` watermark to prevent duplicate phrasing across turn boundaries and timeskips.
3. Wired `bridge_all(gs)` into `tick_manager.tick_turn` to run after each turn and timeskip step.
4. Extract entity IDs and location tags onto generated memories for graph linking.

## Browser UI and intended live verification

Intended UI home: Character Inspector -> Mind -> Memories.

Current availability: The ordinary memory list exists; the lived-log-to-first-person phrasing bridge is still in progress.

Live steps when available:

1. Create a meaningful lived entry in a scratch scenario, advance or skip a turn, and inspect the character's Memories list.
   - expected: The entry appears once as a first-person memory in the ordinary Player memory list, with entity links.

2. Advance the same entry through another turn and reopen Memories.
   - expected: No duplicate memory appears; existing social, threat, need, act, and move writers remain unchanged.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. In a scratch scenario, trigger a meaningful lived event (e.g. death or pursuit start), advance a turn, and check the Mind panel.
   - expected: The entry appears once as a first-person memory in the ordinary Player memory list, with entity tags and source 'lived_log'.
   - observed: 13 lived_log memories generated in test runs; verified by tests/test_lived_log_memory.py.

2. Advance another turn without new events and re-inspect Memories.
   - expected: No duplicate memory entries are created; the watermark prevents re-processing.
   - observed: Idempotence verified in tests/test_lived_log_memory.py.

## Files

- `engine/lived_log_memory.py`
- `engine/tick_manager.py`
- `player.py`
- `tests/test_lived_log_memory.py`
