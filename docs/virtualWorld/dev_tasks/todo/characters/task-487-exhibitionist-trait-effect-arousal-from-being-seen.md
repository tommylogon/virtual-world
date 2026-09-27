---
type: task
status: todo
area: characters
priority: low
---

# task-487: Exhibitionist trait effect: arousal from being seen

**Filed:** 2026-09-23
**Related:** task-213, task-547

## Blocked (2026-09-27) — no "being seen" signal exists

Re-measured before implementing: this is not a one-line trait consumer. Nothing in
the engine records that one character *observed* another, and nothing distinguishes
a public observation from a covert one.

- `engine/background_social.py` reads `attention_seeker` in exactly two places —
  `action_weights()` boosts `chat`/`joke`/`flirt` ×1.3 and `ignore_weight()` drops
  the ignore weight ×0.6. That is *seeking* attention, not *receiving* it.
- The nearest existing signal is `process_bystander_reactions()` in
  `engine/npc_behaviors.py`, which already runs perception checks, but returns only
  reaction **strings**, skips every non-`simple_npc` character, and is capped by
  `max_reactions` (default 1) — so the observer set is never actually available.
- "Publicly exposed" has no meaning today: `is_exposed()` in
  `engine/body_parts.py` answers *is this body part covered*, not *is anyone
  present to see it*.

Build task-547 first, then this task becomes a consumer over the observation
record. The mature gating and picker hiding already in place
(`routes/library_ops.py` filters traits while `mature_content` is off) do not need
to change.

## Goal

Wire the exhibitionist trait effect, which is currently defined but inert (effects: {exhibitionist: true}, no consumer): grant arousal/pleasure when the character is publicly exposed or being looked at, and add a behavior_prompt. Tracked from task-213.

## Acceptance

- `exhibitionist` gains a live consumer (`TraitSystem.has_effect(p, "exhibitionist")`), granting arousal/pleasure when the character is publicly exposed or being looked at.
- A `behavior_prompt` is added so the agent references the trait.
- Only active when `world.mature_content` is on; the trait stays hidden from pickers when off (`routes/library_ops.py:195-205`).
- Test asserting the effect fires (and does not fire for non-carriers).
