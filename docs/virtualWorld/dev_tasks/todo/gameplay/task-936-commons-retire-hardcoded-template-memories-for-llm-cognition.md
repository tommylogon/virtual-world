---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-824, task-854, task-935]
---

# task-936: Retire hardcoded template memories in The Commons for LLM cognitive reflection

**Filed:** 2026-11-09
**Related:** task-824, task-854, task-935

<!-- deps:start -->
**Related:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]], [[task-854-integrate-the-commons-with-world-actions-and-items]], [[task-935-commons-dialogue-testing-memory-toggle]]
<!-- deps:end -->

## What

Eliminate the hardcoded, deterministic template f-string memories currently injected by The Commons, replacing them with genuine LLM-driven cognitive reflection or a zero-write policy:

1. **Remove Hardcoded F-String Injections**:
   - Delete the hardcoded memory generation blocks in `routes/action_handlers.py` (lines 1956-1975 and lines 1992-2008) that inject rigid strings like `Saw message from {actor_name} in #{channel_name}: "{msg_text}"` and `Texted {matched_name}: "{msg_text}"`.
   - Commons communication state is message ledger state (`engine/commons.py`), not cognitive character memory.
2. **LLM Cognitive Reflection / Reaction**:
   - When memories are enabled, incoming Commons messages are delivered to the recipient's turn prompt context as part of conversation history.
   - The recipient character's own LLM evaluates the messages during their regular turn reaction phase or background reflection (`AgentMemory.reflect`), deciding:
     - Whether the message is emotionally or narratively salient.
     - What the character actually thought or felt about it.
     - The wording, importance, and tags of the resulting memory in the character's authentic voice.
3. **Strict Fallback Policy (No Fake Memories)**:
   - If an incoming message is not evaluated by an LLM (such as simple scripted NPCs or unreflected chat chatter), record **nothing**.
   - No robotic template f-strings are ever inserted to stand in for cognition.

## Why

Currently, The Commons forces rigid, automated strings into `player.memories` whenever any message is posted or texted. This bypasses character personality, emotions, and intelligence entirely: every character records identical, robotic memory entries for every chat line regardless of context. VirtualWorld simulation invariants dictate that character cognitive state belongs to the player model and agent reflection, not hardcoded route side effects. Either memories are generated through genuine LLM cognition, or nothing should be written.

## How

1. In `routes/action_handlers.py`:
   - Remove the direct `actor_player.add_memory()` and `recipient.add_memory()` calls in the `#channel` posting and `text <character>` branches.
   - Leave message distribution and unread indicators intact on `world.commons`.
2. In `static/js/agent/prompt-builder/conversation-context.ts`:
   - Ensure recent unread Commons channel messages and direct messages are formatted into the recipient's observation context so the LLM perceives them on its next turn.
3. In `static/js/agent-engine.ts` and `engine/agent_memory.py`:
   - Allow incoming Commons communications to be reflected during `AgentMemory.reflect(charName)` or the reaction memory step `_storeReactionMemory()`.
   - The model generates its own reaction: `memory: { text: "...", importance: ..., tags: [...] }`.
4. In `tests/test_action_handlers.py`:
   - Update tests that previously asserted hardcoded memory additions on Commons posting to assert that communication ledger updates without polluting `player.memories`.

## Browser UI and intended live verification

Intended UI home: The Commons drawer, Event Stream, and Character Inspector -> Mind / Memories tab.

Current availability: Posting to a channel or texting a character in Commons instantly writes hardcoded template strings into character memory lists without LLM reflection.

Live steps when available:
1. Open The Commons in the browser UI and post a message to `#general`: *"Who left the lantern burning near the hay bales?"*
   - expected: Message appears in `#general` chat.
2. Immediately inspect the author and recipient characters in Character Inspector -> Mind / Memories tab before an LLM turn runs.
   - expected: Memory list contains no hardcoded template entries like `Saw message from...`.
3. Advance simulation turn so the recipient LLM agent perceives the message.
   - expected: Recipient agent acts, and if they find the fire hazard notable, generates an in-character memory (e.g. *"Worried about someone starting a fire near the barn"*) in their authentic voice.
4. If a character ignores the message or takes a turn without finding it memorable, inspect their memory list.
   - expected: Zero memories recorded for that message.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In browser UI, send a message in The Commons and inspect character memories.
   - expected: No deterministic template memories added to recipient player object.
   - observed: Hardcoded f-string added immediately by backend route.
2. Trigger an autonomous LLM turn for the recipient character with conversation context present.
   - expected: LLM generates in-character memory only when deemed salient by the model.
   - observed: Memory already populated by route before LLM runs.
3. Run test suite: `pytest tests/test_commons.py` and `pytest tests/test_action_handlers.py`.
   - expected: All tests pass without asserting template memory strings.

## Acceptance

- [ ] Hardcoded f-string memory writes deleted from `routes/action_handlers.py`.
- [ ] Commons message delivery does not inject unreflected memories into `player.memories`.
- [ ] Recipient LLM agents perceive incoming Commons messages in their observation prompt and generate in-character memories through normal cognitive paths.
- [ ] If no cognitive reflection occurs, zero memory records are created.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `routes/action_handlers.py`
- `static/js/agent-engine.ts`
- `static/js/agent/prompt-builder/conversation-context.ts`
- `engine/agent_memory.py`
- `tests/test_action_handlers.py`
