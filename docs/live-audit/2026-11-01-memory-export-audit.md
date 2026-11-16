# Memory audit from run exports and a live save (2026-11-01)

Purpose: record what the exported runs and one saved world show about how
character memory behaves, so the next session can look closer. Every number
below was counted from a file named in the "Sources" section. Anything not
verified is listed under "Unverified" and is not a finding.

Goal this serves: a mind with memory, expectations, questions, assumptions,
trauma, history and observations that agents can use to have a character.
Aura is a separate project and out of scope here.

## Sources

| File | What it is | Used for |
|---|---|---|
| `data/exports/Millwood_tick_1-3188_event_log_2026-10-30T22-16-47.json` | 2,791 events, 13 actors, header says `world_tick` 10, 10 turns, 6 LLM characters | recall, actions, speech, errors |
| `data/sandbox_autosave.json` | save of the same run, game tick 9, 244 memories | memory fields |
| `data/exports/mansion_tick_6834_event_log_2026-09-07T23-26-55.md` | 85 turns, 400 actions, exported 2026-09-07 (before memory dynamics and task-908) | baseline for repetition |
| `data/exports/benchmark_*.json` (3 files) | model benchmarks, one roll per model | JSON validity |
| `data/exports/soak-e31a7b0521c4.json` | 1,440-tick headless soak, kraktooth_goblin_camp | summary only |

The filename "tick_1-3188" does not match the header (`world_tick` 10). Not
investigated.

Analysis scripts are in `scratch/` (export_repeat_audit.py, export_json_audit.py,
export_dup_check.py, export_jake_check.py). `scratch/` is gitignored, so they are
not versioned.

## Caveats

- The Millwood run is 10 turns with 6 LLM characters. Rates from it are small-sample.
- The mansion run predates memory dynamics (task-685) and associative retrieval
  (task-908). Its recall numbers describe the older retriever.
- The Millwood recall events show `0 keyword, 0 semantic, N associative`, so
  the task-908 retriever was live in that run.

## Findings (verified)

### 1. Recall always fills the lane
- Millwood: 60 recall events returned 521 memories. 39 of 60 returned exactly 10.
  The smallest recall was 2.
- Engine default is `max_results=6` (`engine/memory_retrieval.py:607`). The client passes
  `max_results: 10` (`static/js/agent/prompt-builder/memory-context.ts:304`).
- Consequence: the task-908 lane budget ("0..6, zero allowed") is not what runs.
- Mansion (old retriever): 660 of 918 recall events returned 10.

### 2. The same memories return every turn
- Per character over 10 turns, one memory was recalled 9 or 10 times (Lulu 10,
  Sammy 10, Jake 9, Kyrie 9, Kayla 7).
- Every recall reinforces (`memory_dynamics.reinforce`: reinforcements +1,
  activation and confidence up, decay resistance up). The save has a memory with
  18 reinforcements after about 10 ticks.
- Some repetition is expected (same room, same people). Whether reinforcement
  makes it self-sustaining is not shown by this data.

### 3. Room-description memories take recall slots
- "Observed Millwood High Cafeteria: <item list>" is the top hit in 10 of 60
  recalls (scores 7.15 to 8.56) and 35 of 521 recalled items. The room context
  already shows the same list.

### 4. Characters repeat their own words
- Millwood speech: 18 groups of repeated lines by the same actor, 17 of 18 with
  identical full text. Examples: Kyrie said "what's this about?" 8 times across
  ticks 0 to 8. Jake asked the same crimson-gel-pen question verbatim at tick 1
  and tick 2 (after a third phrasing).
- The save has 0 memories of type `speech` across all players. `Memory System.md`
  documents this as design: "people don't remember their own spoken lines".
- Jake has 0 memories mentioning that he asked about the pen.
- This matches the failure named in `memory_architecture.md` ("act like they
  don't remember that they said or did something minutes ago"). Whether the
  missing speech memory is the cause is not proven (see Unverified).

### 5. Characters repeat actions and retry failed ones inside one tick
- Crude metric (action equals one of the actor's last 5 actions): Millwood 58 of
  169 (34%), mansion 126 of 400 (31.5%). The metric also counts legitimate
  repeats such as eating twice, so read it as an upper bound.
- Clear cases, Millwood tick 2: Kayla called `inventory` 6 times in one tick with the
  same result each time. At tick 1 she tried `examine Jake's note` 3 times, after the
  first reply was "you look for 'jake s note' but don't see it here" (the object is
  named "crimson-ink note").
- Clear cases, mansion: the butcher did `take oil_can` 7 times, 6 results were
  "You're already carrying the oil_can". Examines ending in "can't figure out what
  to do with" repeated 6 times (oil_can), 3 (tiny_key), 2 (iron_key).
- Result lines "no major action left this turn" are followed by further attempts.

### 6. Memory writing depends on JSON that often breaks
- Millwood: 95 errors in 10 turns. 20 were hard `parse error: result-reaction`,
  and many more were "response was repaired (truncated JSON) - retrying once".
  `result-reaction` is the phase that writes the turn's memory.
- Benchmarks (one roll per model, `json_valid`): LM Studio local 7 of 17, Google
  11 of 12, OpenRouter free 5 of 11.

### 7. Contradiction linking is wrong in the way it is built
- 125 of 244 memories (51%) have `contradicts` links after 9 ticks. 995 links,
  414 unique pairs, 167 links (17%) point at ids not present in the save.
- 405 of the 414 pairs satisfy the current rule in
  `memory_dynamics.detect_contradiction`, so the rule fires as written. The
  shared-entity gate is satisfied by the room id (`area_cafeteria`).
- Linked pairs include "couldn't find the note" and "found the note in my bag".
  That is a fact that changed over time, not a contradiction.
- 9 pairs do not satisfy the current rule (created by an older version).

### 8. Temporal validity is read but never written
- `invalid_at` set: 0 of 244. `superseded_by` set: 0 of 244.
- `memory_retrieval.is_active_memory` honors both. The only writers are request
  passthroughs (`routes/memories.py:426,532`) and a client forward that sends
  `invalid_at` only if the LLM emits it (`agent-engine.ts:447`).

### 9. Part of the mind model has no content in this run
- Categories in the save: social 102, episodic 70, belief 36, procedural 36,
  question 0, semantic 0. (Semantic is expected at tick 9; consolidation needs age.)
- With zero `question` memories, the open-questions lane of task-908 had nothing to
  surface.
- 98 of 244 memories (40%) are derived (`reflection_depth` 1: 62 reflections plus
  36 expectations). Not judged good or bad.

### 10. Confirmed working
- Decay: minimum activation 0.90 at tick 9 equals 1 minus 9 times
  `memory.decay_per_tick` (0.01). `tick_manager.py` calls it.
- `memory_retrieval.retrieve_associative_memories` is called from
  `routes/memories.py:660`. `tests/test_memory_retrieval_associative.py`: 5 passed.
- `consolidate_sleep` is called from `tick_manager.py:1016`. `memory.consolidate`
  defaults to false (cap pressure still triggers it).
- Write path stamps `entity_ids` and `location`: 139 of 236 auto-written memories
  have `entity_ids`. The task-908 acceptance box about this is probably stale.

## Unverified (do not treat as findings)

- Whether remembering own speech would stop the verbatim repeats. The prompt may
  already carry recent conversation (`conversation-context.ts` was not read).
- Whether a failed JSON parse loses that turn's memory, or the retry recovers it.
- Whether the repeated-action rate was reduced by the anti-repeat guard
  (`buildAlreadyKnownContext`). Pre-fix and post-fix rates look similar, but the
  runs differ in scenario and length.
- Whether reinforcement on every recall produces a rich-get-richer loop in longer runs.
- Live behavior in Agent Lens. Nothing here was verified in the browser.
- The 16 MB mansion log was analyzed only for actions, results and speech. Its
  recall text was not parsed.

## Not read

`world_issues_2026-10-19.md` (1.37 MB), the other md/txt exports (taco_bell_date,
kraktooth tick 414 and 739, valerious case, world_template, older event_log_*.txt,
"export of diffrent local models responses", "lyrie 28082026.txt"), and the
Millwood `.md` twin. The soak was read at summary level only: 23 of 23 characters
died (21 exhaustion, 2 dehydration), first at tick 682. Not investigated; may be
by design for a headless run.

## Where to look next

1. Reproduce finding 1 in Agent Lens: select a character, read the
   `=== I REMEMBER ===` block, confirm 10 entries, then remove the client override
   and compare.
2. Read the exact prompt a character gets at tick 2 in Millwood: does it contain
   the character's own previous speech and the previous action result? This
   decides findings 4 and 5.
3. Check `world_issues_2026-10-19.md` for items already known.
4. Replay the note scenario against `detect_contradiction` after ignoring area ids.
5. Decide where a state change ("note was not there, now it is") should be written:
   `invalid_at` on the old memory, or a new memory with `superseded_by`.
6. Count `question` memories over a longer run and check whether the free-action
   path that emits them is reached.
