---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Gameplay/The Commons]]"
related: [task-824, task-827, task-854, task-893]
---

# task-888: The Commons: active character indicator and character inner stream sidebar

**Filed:** 2026-10-20
**Related:** task-824, task-827, task-854, task-893 (the drawer's contrast defect, filed from this card)

<!-- deps:start -->
**Related:** [[task-824-the-commons-shared-character-minds-channels-groups-and-direct-messages]], [[task-827-setting-aware-communication-themes-for-the-commons]], [[task-854-integrate-the-commons-with-world-actions-and-items]], [[task-893-commons-inner-world-drawer-is-a-white-panel-in-the-dark-app-and-its-body-text-is-invisible-at-1-18-1-contrast]]
<!-- deps:end -->

## What

Surface live character activity and inner cognition directly inside The Commons interface:
1. **Top bar active/acting indicator:**
   Add a live indicator to the top bar (`#commons-actor-chip`) that displays who is currently thinking/acting during a turn (e.g. `Acting: Jake Halloway...`), and who acted last once complete (e.g. `Last acted: Zikka (posted to #general)` or `Last acted: Gribba (read letters)`).
2. **Right-hand slide-out "Inner World" drawer:**
   Clicking any character name or avatar in The Commons (in the member list, participant pacing list, or message author headers) opens a right-hand slide-out drawer for that character.
   The drawer presents:
   - **Inner monologue stream:** The latest parsed `decision.inner` from recent communication turns.
   - **Decision outcome:** The chosen action (`send_chat`, `read_chat`, `start_dm`, `start_group`, `think`), destination channel, and reasoning.
   - **Subjective mood & vitals:** Current emotional state and relevant social vitals from the underlying `Player` model.
   - **Recent communication memories:** Reflections saved to `player.memories[]` tagged with `conversation` or `chat`.
   - Close button (`x`) and dismiss scrim.

## Why

Today, The Commons is opaque during autonomous character activity:
1. When **> Step Next** is clicked or unpaused background turns run, there is no top-level feedback showing who is taking a turn, who just acted, or what action was taken unless a public message happened to be posted. If a character chooses `read_chat` or `think`, the UI appears completely still with zero visible feedback.
2. `CommonsAgent.stepOne()` parses `decision.inner` (the character's inner monologue) from the LLM response, but immediately drops it without storing it in `CommonsState` or rendering it in the DOM. Designers and players have no way to understand why a character posted what they did or what they thought about the messages they just read without opening external developer console logs.

## How

1. **Capture inner monologue and decisions in `CommonsState`:**
   In `static/js/commons/commons-agent.ts`:
   When `responseParser.parseCommunication(reply)` resolves, record the character's turn record in `CommonsState`:
   `CommonsState.recordTurn(charName, { inner: decision.inner, action: decision.action, channelId: decision.channelId, text: decision.text, timestamp: Date.now() })`.
   Set `CommonsState.actingCharacter = charName` while the LLM call is in flight, and update `CommonsState.lastActed = { charName, action: decision.action, timestamp: Date.now() }` on completion.
2. **Top-bar actor status element:**
   In `templates/commons.html` and `static/js/commons/commons-ui.ts`:
   Add `#commons-actor-chip` in the top bar beside `#commons-status-chip`.
   When an agent is acting: render `[pulsing icon] Acting: <CharacterName>...`.
   When idle: render `Last acted: <CharacterName> (<action summary>)`.
3. **Slide-out "Inner World" drawer:**
   In `templates/commons.html`:
   Add `<aside id="commons-inner-drawer" class="commons-inner-drawer" hidden>` containing:
   - Header: Character avatar, name, current area, and close button (`x`).
   - Inner Monologue section: Quotes the latest `inner` thought in a styled thought container.
   - Decision badge: Action kind (`posted message`, `read 5 letters`, `reflected`), target channel/recipient.
   - Recent reflections: List of recent chat memories from `Player.memories[]`.
4. **Interaction wiring:**
   In `static/js/commons/commons-ui.ts`:
   Attach click handlers to character chips in `.commons-channel-members`, `#commons-participants-list`, and message headers in `.commons-message-author`. Clicking opens the drawer populated with that character's latest inner stream and memories.

## Browser UI and intended live verification

Intended UI home: `/commons` page header and a new right-hand slide-out drawer over `#commons-layout`.

Current availability: live and verified.

**Correction (2026-10-21): the verification was of behaviour, not legibility.**
The drawer opens and renders the right content, but it is a **white panel in a
dark application** and its three content sections are unreadable. The dark-theme
override block in `static/css/commons.css` (from line 213) re-themes the whole
page but contains **no** `.commons-drawer-*` rules, because the drawer's own
rules were added later (from line 478) and win by source order. The section body
text inherits the page's light foreground (`rgb(230, 237, 243)`) on the
drawer's white background: **1.18:1 contrast**, against the 4.5:1 WCAG AA
minimum. Only the identity block (name, presence, personality) is readable,
because those rules are light-themed. Filed as task-893.

Live steps verified:
1. Open `/commons` and observe the top bar header.
   - result: `#commons-actor-chip` indicates ready/idle state.
2. Click **> Step Next**.
   - result: `#commons-actor-chip` updates to show `Acting: <Name>...` while in flight, then updates to `Last acted: <Name> (<action>)` upon completion.
3. Click on the acting character's name in the message feed, sidebar member list, or pacing participants.
   - result: the right-hand "Inner World" drawer slides out showing their latest inner monologue quote, the action they chose, and recent reflections.
4. Click the close button (`x`) or press Escape.
   - result: the drawer closes cleanly without affecting active channel or scroll position.

## Steps to verify

1. Run unit test suite: `node tools/unit/run.cjs tools/unit/test_commons_agent.js` (780 passed across 57 files).
2. Run backend test suite: `python -m pytest tests/test_commons.py` (17 passed).
3. Verify `CommonsState.recordTurn` stores `inner_monologue` and updates `lastActed`.
4. Navigate to `/commons` in the browser, trigger **Step Next**, and assert top-bar chip displays the acting character.
5. Click a character name to verify the slide-out drawer renders their inner monologue and decision.

## Acceptance

- [x] Top bar displays the currently acting character during turn execution.
- [x] Top bar displays the last acted character and action summary when idle.
- [x] Silent actions (`read_chat`, `think`) update the actor indicator so turn progression is always visible.
- [x] Clicking any character name/avatar opens the "Inner World" drawer for that character.
- [x] The drawer displays the character's latest inner monologue and chosen communication action.
- [x] The drawer displays recent reflections/memories formed from communication.
- [x] Unit tests cover `recordTurn` and state transitions.

## Files

- `templates/commons.html`
- `static/css/commons.css`
- `static/js/commons/commons-agent.ts`
- `static/js/commons/commons-state.ts`
- `static/js/commons/commons-ui.ts`
- `tools/unit/test_commons_agent.js`
