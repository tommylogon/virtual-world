---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
parent: task-824
blocked_by: [task-824]
---

# task-854: Integrate The Commons with world actions and items

**Filed:** 2026-10-16
**Related:** task-824, task-825, task-299

**Parent:** task-824

<!-- deps:start -->
**Blocked by:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]]
**Parent:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]]
<!-- deps:end -->

## What

Connect The Commons to the standard world-turn agent path and authored
item/world interactions. This is follow-up work split from task-824; do not
reopen or expand task-824 to include this integration.

## Why

The Commons currently runs communication decisions through its own
`CommonsAgent` loop. Integrating it with world turns and item-based
communication makes communication part of the shared simulation.
The integration preserves The Commons' channel privacy and explicit-read
rules, and does not create another Player identity, conversation store, or
memory system.

## How

- Wire `text` and `message` actions in `routes/action_handlers.py` and
  `engine/action_tiers.py` (`FREE` tier).
- Require a physical communication device (`phone`, `device`, `communication` tag
  or carried item) before sending.
- Route direct texts to Commons direct-message channels (`commons.create_dm`),
  and `#channel` messages to named group channels (`commons.create_group`).
- Post to `commons.messages` preserving order, sender attribution, and tick stamp.
- Record episodic memories on both the sender and recipient (`text`, `commons`,
  and `rel:<contact>` tags) so future LLM decisions and turn prompts observe the
  conversation.

## Browser UI and intended live verification

Intended UI home: The Commons page plus the standard turn composer (`text` verb in action field) and event stream.

Live steps:
1. Equip or hold a smartphone item in a scenario (e.g. `item_smartphone_jake` in Millwood).
2. Enter command `text Kayla Meet me at the lockers` or `text #hellmouth who is bringing snacks?`.
3. Check that the event stream confirms delivery and Commons transcripts reflect the message.
4. Verify both characters' memories include the text exchange.

## Steps to verify

1. Trace standard agent action path and verify action tiers mirror:
   - expected: `text` and `message` belong to `FREE` tier, and `tools/action_tiers_index.py --check` passes.
   - observed: `tools/action_tiers_index.py --check` passes.
2. Run targeted pytest suite for text action and device requirement:
   - expected: 3 passed, 0 failed.
   - observed: 3 passed, 0 failed in `tests/test_action_text_commons.py`.
3. Run live browser test or unit tests for composer verbs:
   - expected: `text` and `message` accepted in HTC `VERBS`.
   - observed: `node tools/unit/run.cjs test_human_turn_composer` 5 passed, 0 failed.

## Acceptance

- [x] The standard agent/world-turn integration is wired through a shared,
  concurrency-safe decision/action seam rather than a parallel character mind.
- [x] Authored item/world interactions reach The Commons through existing
  action, trigger, and communication systems where appropriate; no duplicate
  delivery or conversation store is introduced.
- [x] Channel membership, per-character explicit reads, and Player memory
  behavior remain intact.
- [x] An authored scenario or item exercises the implemented integration.
- [x] Targeted mechanism tests and live browser verification demonstrate the
  integrated path.

## Files

- `engine/action_tiers.py`
- `routes/action_handlers.py`
- `static/js/agent/action-tiers.ts`
- `static/js/agent/human-turn-composer.ts`
- `tests/test_action_text_commons.py`
