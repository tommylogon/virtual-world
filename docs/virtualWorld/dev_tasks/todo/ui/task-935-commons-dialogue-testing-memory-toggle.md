---
type: task
status: todo
area: ui
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-824, task-854, task-936]
---

# task-935: The Commons dialogue testing memory toggle (UI button and config suppression)

**Filed:** 2026-11-09
**Related:** task-824, task-854, task-936

<!-- deps:start -->
**Related:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]], [[task-854-integrate-the-commons-with-world-actions-and-items]], [[task-936-commons-retire-hardcoded-template-memories-for-llm-cognition]]
<!-- deps:end -->

## What

Add a user-facing toggle button in The Commons interface to enable or disable memory generation when testing dialogue and chatting directly:

1. **Commons Header Toggle Affordance**:
   - In `static/js/commons/commons-ui.ts` (and `templates/index.html`), place a toggle button in the Commons chat drawer/header:
     - Active state: `🧠 Memories: ON` (accent pill, default behavior).
     - Suppressed state: `🧠 Memories: OFF` (muted pill, memory generation disabled).
   - Backed by client configuration `config.commons_record_memories` and stored in localStorage.
2. **API & Route Guarding**:
   - Pass `record_memory` boolean flag in `POST /api/action` (when posting to channels or sending DMs via Commons) and in `POST /api/commons/messages`.
   - In `routes/action_handlers.py` and `routes/commons.py`, check the flag before triggering any memory write path. When `record_memory` is false, completely suppress memory generation for both actor and recipients.
3. **Clear Authoring Feedback**:
   - When memory recording is toggled off, display a subtle hint in the chat composer placeholder: *"Testing mode: messages will not generate character memories"*.

## Why

Currently, whenever an author or tester sends messages in The Commons to check character responsiveness, formatting, or dialogue tone, the engine automatically injects memory records into the sender and every recipient. Testing 15 lines of chat creates 30 memory records, quickly drowning out genuine narrative events with testing noise. Authors need a quick, accessible toggle to turn off memory logging while experimenting with dialogue.

## How

1. In `static/js/config.ts`:
   - Add `commons_record_memories: boolean` defaulting to `true`, persisted via `storage`.
2. In `static/js/commons/commons-ui.ts`:
   - Render a toggle pill `#commons-memory-toggle` in the chat header actions bar.
   - On click, toggle `config.commons_record_memories`, update button label and styles (`ON` vs `OFF`), and save state.
   - Include `record_memory: config.commons_record_memories` in the message post payload.
3. In `routes/action_handlers.py`:
   - In the `#channel` post and `text <character>` branches, read `record_memory = data.get("record_memory", True)`.
   - Guard memory creation: only proceed if `record_memory` is true.
4. In `routes/commons.py`:
   - Read `record_memory` in `post_message` route and bypass memory hooks if false.

## Browser UI and intended live verification

Intended UI home: The Commons drawer header (top action bar next to channel title and close button).

Current availability: The Commons header has channel title, theme badges, and close button. No memory toggle button exists, and sending messages unconditionally records memories.

Live steps when available:
1. Open The Commons drawer in the browser UI (click the Commons icon in the navigation bar or top toolbar).
   - expected: Commons drawer opens, and the header displays the memory toggle pill `🧠 Memories: ON`.
2. Click the `🧠 Memories: ON` pill.
   - expected: Label flips to `🧠 Memories: OFF` with muted styling. The message composer input placeholder updates to indicate testing mode.
3. Type and send a test message into `#general` or a direct message to a character.
   - expected: Message posts cleanly to the chat stream.
4. Open the recipient character in Character Inspector -> Mind / Memories tab.
   - expected: No memory record was added for the test message.
5. Click the memory toggle pill again to switch back to `🧠 Memories: ON`, and send another message.
   - expected: Toggle returns to active styling, and normal memory processing occurs for the new message.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In browser UI, open The Commons drawer and inspect the header controls.
   - expected: Shows `🧠 Memories: ON` toggle button.
   - observed: No memory toggle exists in header.
2. Toggle the button to OFF and send a message.
   - expected: POST payload carries `record_memory: false`.
   - observed: Message endpoint does not accept or pass memory suppression flags.
3. Inspect character memories before and after sending a message in OFF mode.
   - expected: Character memory count remains identical.
   - observed: Memory count increases with hardcoded template entry.
4. Run frontend tests: `node tools/unit/run.cjs`.
   - expected: All unit tests pass.

## Acceptance

- [ ] Commons header contains a clickable `🧠 Memories: ON / OFF` toggle pill.
- [ ] Toggle state persists in client config and localStorage across page reloads.
- [ ] When toggled OFF, posting messages in channels or DMs writes zero memories to any character.
- [ ] When toggled ON, standard memory logging operates normally.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `static/js/config.ts`
- `static/js/commons/commons-ui.ts`
- `routes/action_handlers.py`
- `routes/commons.py`
