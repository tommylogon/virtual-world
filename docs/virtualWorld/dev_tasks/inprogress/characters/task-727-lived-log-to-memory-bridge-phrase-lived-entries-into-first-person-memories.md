---
type: task
status: inprogress
area: characters
priority: high
---

# task-727: Lived log to memory bridge: phrase lived entries into first-person memories

**Filed:** 2026-10-06
**Related:** task-725, task-714, task-412, task-399

## Goal

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
  `death`, `relationship`, `pursuit` — the ones with no other memory writer.
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
