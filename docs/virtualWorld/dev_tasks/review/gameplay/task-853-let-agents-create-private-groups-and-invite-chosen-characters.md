---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
---

# task-853: Let agents create private groups and invite chosen characters

**Filed:** 2026-10-16
**Related:** task-824

## What

Let an agentic character start a private group conversation, choose specific existing characters as members, name the group, and send its opening message. Keep the creator included in the member list and use the existing Commons channel, authorization, persistence, and memory paths.

## Why

The Commons already lets the human perspective create a group by selecting named participants, and the communication prompt exposes group conversations an agent can access. But agent decisions currently support read_chat, send_chat, start_dm, and think only. Agents cannot initiate group conversations or invite selected people.

## How

Extend the existing communication prompt and response parser with a group-creation action that carries a group name, an explicit list of invitees, and an opening message. The invitee list must be limited to characters this Player actually knows by name, using the existing Player name-knowledge source (`Player.knows_name` / relationship state); do not treat every scenario participant or mere recognition of a stranger as someone the agent can name and invite. Ensure the prompt's candidate list and action validation enforce the same rule, including the existing DM path if it shares the candidate list. Apply the decision in CommonsAgent through the existing channel-creation and message APIs. Reuse the current group model and server validation; do not add another conversation store, membership system, or agent identity. Cover malformed output, unknown or not-known recipients, and minimum membership using established validation behavior, and prove the selected invitees and message route are correct.

## Browser UI and intended live verification

Intended UI home: The Commons page at `/commons`; autonomous character communication decisions run through `CommonsAgent`. Current availability: a character can start a private group with explicitly chosen recipients and an opening message, but only for characters whose names the sender knows. The server returns those eligible names from the existing `Player.knows_name()` relationship state; the Commons UI still shows the full scenario roster for human selection. The deterministic decision/action path is covered by `tools/unit/test_commons_agent.js`; route eligibility and existing authorization are covered by `tests/test_commons.py`. The live Commons page was not used to trigger an LLM decision in this verification pass.

## Steps to verify

1. Return a deterministic group-creation decision for an existing character who knows two invitees by name, while another scenario character is only recognized or unknown by name.
   - expected: The creator and exactly the two name-known invitees can see the new group and its opening message; the stranger is not offered as a candidate and cannot see the group.
   - observed: VERIFIED 2026-10-16 by the deterministic CommonsAgent harness in `tools/unit/test_commons_agent.js`: the parsed action created a group with exactly `Mira`, `Lysa`, and `Joren`, then posted the opening message to the returned group id. `tests/test_commons.py::test_commons_state_lists_only_characters_whose_names_the_perspective_knows` uses the real `Player.knows_name()` relationship rule and returns `Lysa` but not the first-sighting stranger. Existing private-channel route tests continue to prove non-members are denied access.
2. Return invalid group decisions including a not-known recipient, an unknown recipient, or missing required fields.
   - expected: No malformed group is created; candidate generation and action validation enforce Player name knowledge, and existing Commons authorization remains authoritative.
   - observed: VERIFIED 2026-10-16 in the CommonsAgent harness: a non-candidate invitee, unknown DM recipient, and group without an opening message create no channel or post. The route candidate test confirms the relationship-backed source of truth.
3. Verify persistence and explicit read behavior for the new group.
   - expected: The channel, membership, message, and per-character read cursors use the existing Commons state and save/load path.
   - observed: VERIFIED 2026-10-16 by `tests/test_commons.py -k 'saved_world_round_trips or commons_messages_and_read_cursors'` (2 passed); the existing Commons save/load and autosave path persists channel membership, message, and read cursor state.

## Acceptance

- [x] An agent can choose to create a private group instead of only reading, posting to an accessible channel, starting a DM, or thinking.
- [x] The agent specifies the group name and exact invitees; the creator is included, and other invitees are limited to existing characters whose names this Player knows according to the existing Player name-knowledge state.
- [x] Recognizing a stranger without knowing their name, or merely appearing in the scenario participant list, does not make that character an eligible invitee. The prompt's candidates and action validation apply the same rule; the shared candidate-list behavior for starting DMs is consistent.
- [x] The opening message is posted to the newly created group, not another channel.
- [x] Group visibility and read/post authorization continue to be enforced by the existing Commons server model and routes.
- [x] No parallel communication, character identity, or memory store is introduced.
- [x] Targeted tests prove the parsed decision, exact known-member list, rejection/omission of unknown-by-name invitees, opening-message destination, and denied access for a non-member.

## Files

- `routes/commons.py` (relationship-backed invite candidate projection)
- `static/js/agent/prompt-builder/turn-prompts.ts`
- `static/js/agent/response-parser.ts`
- `static/js/commons/commons-agent.ts`
- `docs/virtualWorld/Gameplay/The Commons.md`
- `tools/unit/test_commons_agent.js`
- `tests/test_commons.py`
