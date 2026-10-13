---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-700, task-691, task-714]
blocked_by: [task-807]
---

# task-813: MOSIAC: Obligations - the missing letter's data

**Filed:** 2026-10-12
**Related:** task-700

<!-- deps:start -->
**Blocked by:** [[task-807-gimp-the-goal-model-and-its-serialization]]
**Related:** [[task-700-grounded-plan-contract-the-llm-plan-phase-emits-typed-steps-validated-against-world-facts]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Give Obligations a home: the data for what a character owes (missions, promises, duties, appointments), and how an obligation spawns an Intention.

## Why

Obligations are the most demanded letter across the profiles and the least built. An obligation is an input that generates an intention, not a peer of one.

## How

A `Player.obligations` list (character-private, beside `goals`): each record is `{id, charge, status, from, due, reward, goal_id}`. `status` is one of `OBLIGATION_STATUSES` (offered / accepted / refused / forgotten / done). An obligation is an **input**: it sits `offered` until the character answers it, and only `accept` spawns a goal (the intention it generates), linked back via `goal_id`. `engine/goals.respond_obligation` does the answering; `expire_obligations` forgets one past its `due` tick. The `obligation` verb (free) answers one at runtime.

## Steps to verify

1. In the app, offer a character a mission, then accept it.
   - expected: a goal appears, tied to the mission, in the 🧠 Mind panel (`InspectorMindView`).
   - observed: VERIFIED 2026-10-12, live on localhost:4444. Offered `Deliver the sealed letter` (from Elder Mara) on the character record, then `obligation accept deliver_the_sealed_letter`. The obligation became `accepted` with a `goal_id`, and a goal spawned: `{what: "Deliver the sealed letter", status: active, intention: "obligation to Elder Mara"}`. The panel's new "Obligations - what they owe" block showed the charge + `accepted` badge, and the goal showed too.
2. Refuse a mission.
   - expected: no goal is spawned.
   - observed: VERIFIED 2026-10-12. `obligation refuse burn_the_warrant` set the obligation to `refused` and left the goal count unchanged (4 -> 4); no goal spawned.

## Acceptance

- [x] An obligation can be accepted, altered, refused or forgotten.
- [x] Accepting spawns a goal; the obligation is the record.

## Files

- `engine/goals.py`
- `engine/serialization.py`
- `engine/action_tiers.py`
- `routes/action_handlers.py`
- `routes/player_ops.py`
- `player.py`
- `static/js/inspector/mind-view.ts`

## Progress (2026-10-12)

- `engine/goals.py`: `OBLIGATION_STATUSES`, `normalize_obligations`, `offer_obligation`, `find_obligation`, `respond_obligation` (accept spawns a goal), `expire_obligations`, `describe_obligations`.
- `Player.obligations`; serialized in the players block, normalised on load, stripped in `lite`; the editor patch accepts `obligations`.
- The `obligation` verb (free): bare lists, `accept|refuse|forget <charge>` answers.
- Mind panel: an "Obligations - what they owe" section.
- `tests/test_goals.py`: accept spawns a goal, refuse spawns none, expiry by tick, a scenario round-trip, and a wiring test through the dispatcher.
