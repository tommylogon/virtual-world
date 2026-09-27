---
type: task
status: todo
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

