---
type: bug
status: review
area: prompting
priority: medium
wiki: "[[AI & Narration/Narration System]]"
---

# bug-517: DM-style AI narration is broadcast as character speech instead of replacing systemic action results

**Filed:** 2026-10-04 (Updated: 2026-10-20)
**Related:** task-692, task-340

## What

AI narration is intended as a DM (Dungeon Master) presentation layer that replaces dry systemic messages and action results with immersive, second-person narration in the event feed. Instead, room narration is currently routed through `/api/players/<name>/speak`, forcing the character to literally vocalize the DM prose into the room as speech, which mutates Social vitals and pollutes every nearby character's `recent_hearing` memory.

The fix requires:
1. Eliminating the `playerSpeak` call from `buildNarratedRoomContext` entirely.
2. Routing systemic action results and engine messages (`data.output`, `data.system_messages`) through the DM narration layer to produce unified narrative action outcomes in the event feed instead of raw mechanical status messages.

## Measured 2026-10-04 and 2026-10-20
### Reconciliation (2026-10-20)

Current code state:
- static/js/agent/prompt-builder/room-context.ts:942 still calls wait apiClient().playerSpeak(charName, **, currentArea?.name as string); when narrated description is produced (3 total matches including type declaration at line 976). This call mutates the world via POST /api/players/<name>/speak, affecting Social vitals, 
ecent_hearing, and on_speech_heard hooks.
- static/js/agent-engine.ts:854-856 logs raw data.system_messages as system-msg even when narration is attempted. Narration consumes only outputText at line 863 and replaces it at 864; raw system messages remain emitted separately (855), so systemic messages are not absorbed into the narrated outcome.
- static/js/narration-ui.ts: 0 matches for playerSpeak.
- No done tasks reference bug-517; code unchanged relative to measured state.

Verdict: **STILL_VALID**. No newer work has fixed the broadcast of room narration as speech or bundled systemic messages into the narrated outcome. The card remains accurate; cited lines are current.

## Plan position (2026-10-20)

**Which NEWER cards (higher number, in `done/` or `review/`) bear on this card, and what did each one actually do?**
- No done/review cards with higher number than 517 were found to touch narration/speech routing. task-692 is related (todo, lower priority context) but not done/review. task-340 related but older.

**Did that newer work CHANGE THE APPROACH of this card, or does it merely IMPLEMENT PART OF IT, or is it UNRELATED?**
- Unrelated to newer done/review work.

**Does this card still stand as a DISTINCT piece of the overall plan, or has a newer card absorbed its scope?**
- Stands as a distinct piece. No newer card absorbed its scope.

**Verdict:** holds, distinct.

### 1. In-world speech pollution (room-context.ts)
In `static/js/agent/prompt-builder/room-context.ts:941-943`:

```typescript
const narratedDescription = await narrationUi()!.getNarratedRoomContext(contextObject, charName);
if (narratedDescription) {
    contextString = contextString.replace(/^Description: .*/m, `Description: ${narratedDescription}`);
    try { await apiClient().playerSpeak(charName, `*${narratedDescription}*`, currentArea?.name as string); }
    catch(innerError) {}
}
```

`apiClient().playerSpeak` calls `POST /api/players/<name>/speak` -> `app.world.broadcast_speech` (`engine/speech.py:191`).
`broadcast_speech` mutates `Social` vitals for the speaker and all listeners, appends hearing records to each player's `recent_hearing` list (capped at 20), triggers `on_speech_heard` hooks, and seeds memories.

In Kraktooth's Cooking Area, Jake Halloway entering the room causes Jake to appear to shout a paragraph describing the pots and walls. The cook, the tinkerer, and any bystander each record a memory that Jake said it.

### 2. Disconnected systemic results (agent-engine.ts)
In `static/js/agent-engine.ts:850-874`:
Action outcomes receive engine results and log `system_messages` mechanically:

```typescript
actionResult = data?.output || '';
actionSucceeded = data?.success !== false;
if (data?.system_messages) {
    data.system_messages.forEach((systemMessage: any) => events.log(systemMessage, 'system-msg'));
}
```

When AI narration is enabled, `getNarratedActionResult` runs only on `outputText` (`data.output`), while `data.system_messages` bypass narration and get dumped as bare engine strings. The player sees disjointed engine logging alongside or before the narration, instead of the DM rephrasing the complete action outcome (action + consequences + systemic messages) into a coherent narrative beat.

## Why this is a defect

Narration is a **presentation/DM layer**, not an **in-world physical action**:
- The DM describing what happened or setting the scene is commentary for the player/observer. It must NEVER become in-world dialogue spoken by the character.
- Routing display text through `/speak` turns a client-side presentation effect into a world mutation, corrupting character relationships, vitals, and conversation histories.
- The intended role of the narrator is to replace the dry systemic messages of action outcomes (e.g. "Door unlocked. Moved east.") with descriptive prose (e.g. "The iron key turns with a sharp click, and you push into the shadowy corridor.").

## How to fix

1. **Remove playerSpeak from room-context.ts:**
   Delete line 942's call to `apiClient().playerSpeak`. Room narration updates `contextString` for the character's prompt and logs to the event stream via `events.log` (already in `narration-ui.ts:204` as a system/DM message), with zero world mutation.
2. **Feed systemic messages into action narration:**
   In `static/js/agent-engine.ts`:
   When `narrationMode` is active (`'ai'` or `'player'`), combine `actionResult` and `data.system_messages` into the input context given to `narrationUI.getNarratedActionResult(combinedText, charName, finalAction)`.
3. **Suppress raw systemic logs when narrated:**
   When `narratedText` successfully resolves, render `narratedText` as `msg-narrated` in the event feed and suppress the duplicate raw `system_messages` display. If narration is off (`'none'`) or fails/skips, fall back to logging raw `system_messages` and `msg-result`.
4. **Ensure DM perspective in narration prompts:**
   Confirm that prompt instructions in `narration-ui.ts` clearly prompt the model as the Dungeon Master describing the results of the action to the player, rather than character thoughts or spoken lines.

## Acceptance criteria

- **Zero speech pollution:** Triggering room narration or action narration never makes a network request to `POST /api/players/*/speak`.
- **Clean listener memory:** Characters in the same area as the acting player experience 0 additions to `recent_hearing` from narration events.
- **No on_speech_heard triggers:** Narration text never fires NPC conversational triggers or alters Social vitals.
- **Systemic message replacement:** When narration mode is `ai` or `player`, engine `system_messages` are absorbed into the narrated outcome rather than printed as separate mechanical lines in the event feed.
- **Fallback safety:** If narration mode is `none`, or if the AI provider fails/skips, the standard engine `system_messages` and `msg-result` render exactly as they do today.
- **Unit test guard:** A targeted test asserts `buildNarratedRoomContext` does not call `apiClient().playerSpeak`, and action-result handling properly bundles systemic messages when narration is active.

## Files

- `static/js/agent/prompt-builder/room-context.ts`
- `static/js/agent-engine.ts`
- `static/js/narration-ui.ts`
- Targeted prompt-builder/narration tests
