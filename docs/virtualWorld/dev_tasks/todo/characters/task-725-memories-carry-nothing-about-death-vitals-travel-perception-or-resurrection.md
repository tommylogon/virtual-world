---
type: task
status: todo
area: characters
priority: high
related: ['task-404', 'task-734', 'task-736', 'task-786', 'task-789']
---

# task-725: Memories carry nothing about death, vitals, travel, perception, or resurrection

**Filed:** 2026-10-06
**Related:** task-714, task-707

<!-- deps:start -->
**Related:** [[task-404-character-life-experience-generator]], [[task-734-knowledge-is-memory-fold-known-recipes-known-places-into-one-prose-data-record-with-episodic-vs-semantic-kinds]], [[task-736-per-character-cognitive-map-a-belief-based-memory-of-places-and-routes-in-the-mind-panel]], [[task-786-recall-transparency-show-why-a-memory-was-recalled-automatic-and-action-driven]], [[task-789-consolidate-per-area-observation-memories-into-one-spatial-parent-with-linked-evidence]]
<!-- deps:end -->

## What

A character's memory store records no first-person account of dying, being resurrected, being driven by vitals, where they travelled, or what they perceived over time. Live repro: the Eldenford blacksmith died and his Mind contained nothing about why, where he had been, how he felt, what vitals drove him, or his reaction to resurrection. Author engine-side memory writes for these life events so both background-simulation and live-agent characters retain a real account, then Mind (task-714) can display it.

## Measured evidence (2026-10-06)

Live repro: the Eldenford blacksmith died; his Mind showed nothing about why, where he
had been, how he felt, what vitals drove him, or his reaction to resurrection.

The facts exist in more than one store, and the Mind reads only one of them:

- **Death is recorded in `lived_log`, not `memories`.** `kill_player`
  (`virtual_world_engine.py:525`, task-538) writes
  `lived_record(player, tick, "death", f"died of {cause}", ...)` to
  `engine/lived_log.py`. `memories` gets nothing. The character Mind panel (task-714)
  reads `memories`. So a death is recorded and still invisible in Mind - two stores, one
  of them displayed.
- **The death store is not uniform across causes.** The task-538 comment
  (`virtual_world_engine.py:513-523`) documents four sites that each did a different
  subset of the aftermath before 538 unified them; confirm every current path now writes
  a lived record.
- **Travel** is only captured as `record_observation` of visited areas
  (`engine/observation.py:144,158`), i.e. per-area "you have been in X" observations -
  not a travel narrative, and (per `to_scenario_dict`, `serialization.py:565-577`)
  observation memories are treated as runtime and stripped from scenarios.
- **Feelings** - `engine/background_social.py:699,1325` and the emotion system write some
  relationship/emotion memories, but there is no general "what I felt and why" record.
- **Resurrection** - `engine/effect_handlers/vitals.py:285` restores a dead character;
  no memory is written for the event, so the character does not know they died.
- **Vitals-driven death** - hunger/thirst/energy are state on the `Player`, not memory.
  Nothing records the slide to death as a first-person account.

Memory writers found (for reference, not a complete call graph): `player.add_memory`
(`player.py:987`), `player.record_observation` (`player.py:1040`),
`engine/observation.py`, `engine/background_social.py`, `engine/timeskip.py`,
`engine/promotion.py`, `engine/npc_behaviors.py::record_observations`, plus trigger and
effect handlers. None of them is the death/resurrection path.

## Why this is not "merge lived_log into memories" (measured 2026-10-06)

`lived_log` and `memories` are a deliberate two-tier design, documented in
`engine/lived_log.py` and `docs/design/lived-log-format.md`:

- **`lived_log`** is the *objective* record - code-written, **no LLM**, salience-filtered,
  now unbounded (2026-10-06), stored on the `Player` in the save. Its stated
  question is "would a person remember this?" (`engine/lived_log.py` docstring; renamed from
  `trace` in task-542 precisely to keep it distinct from soak telemetry).
- **`memories`** is the *subjective* first-person recall. Mind and the LLM prompts read it.
- **`engine/promotion.py` is already the bridge**: when a background character is promoted
  to attended, the `lived_log` span since the last consolidation is summarized
  deterministically (no LLM) into **one bounded memory** with `source="background"`
  (`promotion.py` `promote()` → `player.add_memory(...)`). `offload()` stamps the boundary
  tick; `pending_span()` shows what a promotion would summarize.

So a secondary source is not the problem - the split is intended and the bridge exists.
The gap is that **the bridge only fires on a fidelity change** (background → attended,
task-399), and it summarizes the span; it does not fire for a character who dies or is
resurrected while their tier does not change. Mind reads `memories`, not `lived_log`, so a
salient `kind == "death"` entry can sit in `lived_log` and never reach Mind. That is why
the blacksmith's mind was empty.

Merging the stores would break three things: the bounded/no-LLM mechanical guarantee, the
idempotent promote/demote handoff, and the task-542 separation from telemetry. Do not merge
them.

## Acceptance

- A character retains a first-person memory of dying (cause), of being resurrected, and of
  the vitals slide that killed them, written for both background-sim and live-agent
  characters **without requiring a fidelity change**.
- Extend the existing `lived_log` → memory bridge (`engine/promotion.py`) to salient life
  events, or have Mind read salient `lived_log` entries directly, or both. Do not create a
  third store and do not move `lived_log` into `memories`.
- Travel and perception attain enough of an account that Mind can answer "where have I been
  and what did I notice", without inventing values.

## Status (2026-10-06)

- **Death: done** by task-727. `engine/lived_log_memory.py` phrases a `death`
  entry into a first-person memory ("I died - <cause>.") for every character,
  every turn, without a fidelity change.
- **Resurrection: open, and entangled with a possible bug.** `kill_player`
  (`virtual_world_engine.py`) sets `player.state = "dead"` **and** the `dead`
  condition. Resurrection is done by an effect composed of `set_vital` + the
  `remove_condition` effect (`engine/effect_handlers/conditions.py`), but
  `condition_remove_condition` (`engine/player_conditions.py:871`) only pops the
  condition - it does **not** reset `player.state`. Confirm whether a resurrected
  character is left with `state == "dead"`, and write the resurrection memory at
  whichever site is the real one.
- **Vitals: covered** by `agent_memory._surface_need_recall` (source
  `need_recall`).
- **Travel / perception: partially covered** by `record_observation`
  ("You have been in X" / "You have seen Y"). Task-727 deliberately skips
  `move`/`act` there to avoid duplicating those; revisit only if the observation
  account proves too thin.

## Related

- task-714 (Mind display - the consumer), task-538 (unified death path), task-707 (memory
  decay), task-399 (promote/demote fidelity seam), task-542 (lived_log vs telemetry).

## Why

TODO

## How

TODO

## Steps to verify

1. Load the Eldenford blacksmith fixture and open the blacksmith's Mind panel
   before the test event. Record the existing memories and `lived_log` entries.
2. Let the blacksmith die from a known vital decline, then inspect the Mind
   panel and `/api/state` memory list.
   - expected: a first-person memory names the cause and relevant vital change;
     values agree with the event record and do not require a fidelity setting.
3. Resurrect the same character and reopen Mind.
   - expected: a distinct first-person resurrection memory appears for the
     same character; the old death memory remains available.
4. Move the character through two areas and have it observe one event in each.
   Ask Mind/recall where it has been and what it noticed.
   - expected: the account refers only to recorded travel and perception
     events, with no invented area, direction, vital, or observation.
5. Repeat with a background-simulation character and a live-agent character.
   - expected: both paths produce the same categories of authored memory in
     the existing memory projection.

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: load the authored life-event fixture → let the character
experience the event in simulation → select the character → Mind panel →
Memories. The view reuses the existing `memories` and `lived_log` bridge; it is
not a new memory store.

Current availability: the card records a live Eldenford blacksmith death with
no corresponding Mind account. Death, resurrection, vitals-driven memories,
travel, and perception coverage are planned here; no new event-memory UI is
claimed as available.

Live steps when available:
1. Open the Eldenford blacksmith's Mind panel before the event, then let that
   character die from the recorded vital decline.
   - expected: Mind shows a first-person death memory naming the cause and the
     relevant vital change; those details match the event record.
2. Resurrect the blacksmith and reopen the same Mind panel.
   - expected: a separate resurrection memory appears and the death memory is
     still present.
3. Move the character across two areas and expose it to one observable event
   in each. Ask Mind/recall where it has been and what it noticed.
   - expected: the answer names only recorded travel and perceptions; no area,
     direction, vital change, or observation is invented.
4. Repeat once for a background-simulation character and once for a live-agent
   character, comparing their Mind entries with `/api/state` and `lived_log`.
   - expected: both execution paths produce the same supported memory
     categories using the existing memory projection.

These steps define the intended Mind-panel evidence. They do not claim the
additional event memories are implemented today.

This section is not a claim that planned UI exists or works today.
