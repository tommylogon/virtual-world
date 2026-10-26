---
type: bug
status: review
area: prompting
priority: medium
wiki: "[[AI & Narration/Narration System]]"
---

# bug-517: AI narration leaves engine system messages outside the narrated action result

**Filed:** 2026-10-04 (reconciled 2026-10-21)
**Related:** task-692, task-340

## What

When AI narration is active, the Agent Engine sends `data.output` to the
narrator, but logs each `data.system_messages` entry as a raw system row before
the narration result is known. A successful narration therefore appears beside
the un-narrated engine messages instead of replacing the complete action result.

The earlier claim that room narration calls `/api/players/<name>/speak` is
disproved by the current source: `room-context.ts` contains no `playerSpeak`
call, and `buildNarratedRoomContext` has no runtime caller. The narration mode
selector also lacked a change handler; `main.ts` now calls `narrationUI.setMode`
when the selector changes. These are not remaining acceptance criteria for
this card.

## Why

Narration is a presentation layer. Raw systemic messages can contradict the
narrated result and leave the event stream showing both versions of one action.

## How

1. Gather `data.output` and `data.system_messages` before logging either.
2. When narration mode is active and narration succeeds, emit the narrated
   result and suppress the duplicate raw system messages.
3. When narration is off, skipped, or fails, preserve the current raw system
   messages and action-result fallback.

## Acceptance

- [x] In AI narration mode, a successful action narration includes the action output
  and its systemic consequences.
- [x] The event stream shows the narrated result without duplicate raw system rows
  for that action.
- [x] When narration is off or fails, the existing system rows and action result
  remain visible.
- [x] No narration text is sent through the character speech endpoint.

## Verification

- static/js/narration-ui.ts: updated getNarratedActionResult to combine systemMessages with action output into prompt context (ullOutput), passing consequences to LLM narrator.
- static/js/agent-engine.ts: gathered ctionResult and data.system_messages before logging. Passed sysMsgs into 
arrationUi.getNarratedActionResult(). When narration succeeds (
arratedText returned), duplicate raw system messages are suppressed. When narration is off, skipped, or fails, raw system messages are logged via events.log(systemMessage, 'system-msg').
- Unit test 	ools/unit/test_narration_system_messages.js: verified that getNarratedActionResult combines output and system messages into LLM prompt context in AI mode, returns null in none mode, and handles fallback.
- 
pm run typecheck and 
pm run build:ts pass with 0 errors.

## Files

- static/js/agent-engine.ts
- static/js/narration-ui.ts
- 	ools/unit/test_narration_system_messages.js

## Browser UI and intended live verification

**Intended UI home:** top-bar Narration mode selector, Simulation controls,
Event Stream.

**Availability:** The current `labs` page has the narration selector and event
stream. A browser scenario that produces an action with non-empty
`system_messages` has not been identified yet. Author that content before
claiming this behavior is live-verified.

**Steps once the scenario is available:**

1. Reload the editor, choose **AI Narrate** in the top-bar selector, then reload
   and confirm the selector still shows **AI Narrate**.
2. In **Agents**, select an NPC and use **Step Once** to perform an action that
   produces an engine system message.
3. In **Event Stream**, keep **Action** and **System** rows visible. Confirm the
   narrated action includes the consequence and the raw system message is not
   duplicated as a separate row.
4. Choose **No Narration** and repeat. Confirm the raw result and system row are
   visible as the fallback.

This card is corrected from the 2026-10-20 reconciliation: its speech-pollution
finding had no current caller or matching code. The surviving systemic-message
issue remains unverified in a live browser.
