---
type: task
status: done
area: characters
priority: high
---

# task-547: Observation signal: who saw whom this turn

**Filed:** 2026-09-27
**Related:** task-487

## Goal

Nothing in the engine records that one character observed another, so any effect that depends on being seen or being exposed has no signal to read. Add a per-turn record of observers, with the public/covert distinction, built on the existing bystander-reaction perception pass.

## Measured (2026-09-27) — the closest thing that exists

- `engine/npc_behaviors.py` `process_bystander_reactions()` already does the hard
  half: it walks every **simple** NPC sharing the actor's area, runs
  `calculate_perception_difficulty()` + `check_perception()`, and decides
  whether the NPC noticed. `process_intimacy_verb()` in
  `engine/pleasure_actions.py` already calls it for intimacy actions and
  appends the reaction lines.
- It is the wrong shape for a "being seen" signal, for three reasons:
  1. it returns only **strings**, not who perceived, so nothing downstream can
     read the observer set;
  2. it skips anything that is not `simple_npc`, so agent-driven and human
     characters — the ones a player would most expect to be *looking* — are
     excluded entirely;
  3. it is capped by `max_reactions` (default 1) and breaks out of the loop, so
     the cap is also a silent truncation of the observer list.
- There is no notion of "publicly exposed" vs "covert" anywhere: exposure is
  currently per-region paperdoll coverage (`is_exposed` in `engine/body_parts.py`),
  which answers *is this body part covered*, not *is anyone present to see it*.
- `engine/background_social.py` reads `attention_seeker` and uses it in exactly
  two places — `action_weights()` boosts `chat`/`joke`/`flirt` ×1.3, and
  `ignore_weight()` drops the ignore weight ×0.6. That is an expression of
  *seeking* attention, not a record of *receiving* it. task-487 needs the latter.

## Open design decisions (settle before implementing)

1. **What counts as public?** Presence in the same area with line of sight and
   enough light, or merely co-presence? A private/closed area, a stealth state, or
   a distracted observer should plausibly disqualify an observer.
2. **Who counts as an observer?** Only NPCs, or also agent-driven and human
   characters? Recommendation: everyone, since a human player's gaze is the case
   players will most want to matter — but that needs a decision, because it
   changes the cost profile of the pass.
3. **Lifetime of the record.** Per turn only, or a decaying "recently watched by"
   set? An effect like task-487's needs persistence across a few turns, since the
   exposure and the reaction do not happen on the same tick.
4. **Who computes it?** A dedicated pass, or refactoring
   `process_bystander_reactions()` to return structured observations and letting
   the reaction lines be built from those. The second avoids two passes over the
   same NPC set; the first is a smaller change.

## Acceptance

- A per-turn (or decaying) record of *who observed whom* exists and is readable
  without re-running perception.
- The record distinguishes a public observation from a covert or unobserved one.
- Every character tier that can look is included, not only simple NPCs, and the
  reaction cap no longer truncates the observer set.
- Test asserting: an observer in the same area is recorded; a character in another
  area (or one who fails the perception check) is not; the record does not
  persist beyond its intended lifetime.

## Related

- task-487 — the consumer this unblocks
- task-214 (done) — `NPC Perception & Reaction Framework`, the pass being widened
- task-468 / task-469 (done) — interrupt-driven background agendas, the same
  "did this character notice" question for the background tier

## Implementation — 2026-09-28 (WT-C)

### Files

- `engine/observation_signal.py` — **new**. The record itself.
- `engine/npc_behaviors.py` — `record_observations()` added;
  `process_bystander_reactions()` now builds its lines from that pass.
- `tests/test_observation_signal.py` — **new**, 30 tests.

No hub file was touched. The record is deliberately **not serialized**: it is
derived per-turn state, so persisting it would only store what the next
perception pass recomputes. Keeping it derived is what keeps this off
`engine/serialization.py` and `player.py`. The cost is that a page reload drops
the recent window; that self-heals on the next turn.

### Naming: this is NOT `engine/observation.py`

That module is task-403's *observation memories* — "what has this character
seen", a per-subject belief on the character, updated by `observe_area()`. This
task is the mirror image — "who has seen *this* character", an audience fact
about the target. Different question, different pass, different lifetime, so a
separate module. Both docstrings cross-reference the other.

### The decisions, settled

1. **What counts as public** — same area, ambient light at or above
   `PUBLIC_LIGHT_FLOOR` (20), and an observer who is not asleep, unconscious,
   dead or blind. Covert means *registered but not onlooker-visible*: someone
   caught a shape in the dark, but nobody was watching it happen. This is
   deliberately grounded in what the engine actually models. There is no
   private/closed area concept, no facing, and no stealth state to key off —
   inventing any of those would be scope this task does not have. It also
   answers the question `body_parts.is_exposed` cannot: exposure there means
   "is this body part covered", and a covered body part in an empty room is
   nobody's business.
2. **Who counts as an observer** — everyone who can look: simple NPCs,
   agent-driven characters and human players alike, per the recommendation in
   the task. The old pass skipped non-simple tiers for a good reason that does
   not apply here — it only ever returned reaction *lines*, which those tiers
   already narrate through their own prompts. A "was I seen" record is not a
   line, and the tiers a player most expects to be watching were exactly the
   ones being dropped.
3. **Lifetime** — a decaying window, `DEFAULT_MEMORY_TURNS = 3`, because the
   exposure and the reaction it causes land on different ticks. The store is
   bounded by *pairs* of characters, not by turns: re-seeing refreshes in
   place, so a week of wandering does not grow a row per turn. Pruning happens
   on write; reads filter by window without mutating.
4. **Who computes it** — the existing pass, refactored, not a second pass.
   `record_observations()` does perception once for every tier and writes the
   record; `process_bystander_reactions()` reads the same results and filters
   them down to simple-NPC lines.

### What the refactor actually fixed

Three real defects, all from the old loop treating the observer set and the line
list as the same thing:

- **The cap truncated observers.** `max_reactions` (default 1) `break`ed out of
  the *candidate* loop, so it silently capped who was seen, not who spoke. The
  cap now bounds lines, applied after perception.
- **Noticing was conflated with commenting.** An observer whose reaction trait
  resolved to `ignore` returned `None` and left no trace — they had demonstrably
  seen the thing. They are now recorded; they just have no line.
- **The tiers were filtered before the roll.** Non-simple characters never
  consumed a d20, because the roll was only ever a step toward a line.

### One finding worth carrying forward

`Player.state` is **derived** from a precedence hierarchy
(`engine/player_conditions.py:940`), and `awake` outranks lesser conditions — so
a character who is asleep still reports `state == "awake"`, and "sleeping" is
primarily an *activity*, not a condition. Any "is this character watching"
check that reads `state` is therefore quietly wrong. `_is_public_observation()`
reads conditions and the activity instead, and
`test_sleeping_is_read_from_the_activity_not_the_state` asserts that `state`
genuinely fails to show the sleep, so the fallback cannot rot unnoticed.

### Not fixed here

`engine/npc_behaviors.py:237` calls `self.gs.is_undead_ghost(npc)` with a
`Player`, but `is_undead_ghost(player_name: str)` takes a name, so the lookup
can never match and that exclusion has never fired. The new pass calls it
correctly with `npc.name`. The stale call in `process_npc_reaction` is
pre-existing and outside this task's scope — it is the only known caller left
with the bug, so it is a one-word fix for whoever owns that path.

### Handed to WT-0

Nothing. This task needed no hub change.

### Verify

`python -m pytest tests/test_observation_signal.py tests/test_npc_perception.py -q`
— 50 tests, covering: an observer in the same area is recorded; one in another
area is not; one who fails the perception roll is not; public and covert are
distinguishable and can coexist; agent and human tiers are included; the dead do
not observe; a non-mature world records nothing for a sexual stimulus; the line
cap does not truncate the observer set; an ignoring observer is still recorded;
and the record ages out past its window without growing per turn.

