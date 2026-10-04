---
type: bug
status: todo
area: prompting
priority: high
---

# bug-517: AI room narration is broadcast as the character's own spoken line, polluting every listener's recent_hearing

**Filed:** 2026-10-04
**Related:** task-692

## Goal

Stop the narrated room description from being sent to
`/api/players/<name>/speak`, which attributes it to the character as
speech and appends a hearing entry to every listener.

## Measured 2026-10-04, by reading the call chain

`static/js/agent/prompt-builder/room-context.ts:886-887`, inside
`buildNarratedRoomContext`:

    const narratedDescription = await narrationUi()!.getNarratedRoomContext(contextObject, charName);
    if (narratedDescription) {
        contextString = contextString.replace(/^Description: .*/m, `Description: ${narratedDescription}`);
        try { await apiClient().playerSpeak(charName, `*${narratedDescription}*`, currentArea?.name as string); }
        catch(innerError) {}
    }

`playerSpeak` (`static/js/api.ts:187`) POSTs to
`/api/players/<name>/speak` → `routes/player_ops.py:471
handle_player_speak` → `app.world.broadcast_speech(name, text,
area_name=target_area.name)` (`engine/speech.py:191`).

`broadcast_speech`'s docstring states it "mutates the speaker's and
listeners' `Social` vital and appends hearing entries to each player's
`recent_hearing` list. Also triggers `on_speech_heard` NPC behaviors."

So the third-person prose the LLM wrote about the room is:

- attributed to the character as something they **said**,
- heard by every other character in the area, who each get a
  `recent_hearing` entry (capped at 20, `engine/speech.py:324`),
- able to fire `on_speech_heard` NPC behavior hooks,
- and — since `eed00a72` landed memory dynamics — eligible to be
  picked up by reinforcement/decay as a thing the character recalls.

In Kraktooth's Cooking Area, walking in as Jake Halloway makes Jake
appear to say a paragraph about the Cooking Area, and the cook, the
tinkerer, and anyone else present each form a memory of Jake saying it.

## Why this is a bug and not a feature

The `*asterisks*` are the app's emote convention, so the *shape* is
deliberate — the narration is meant to render as an emote in the event
stream. But routing it through `/speak` to achieve a display effect
means the display effect is implemented as a **world mutation**. The
two are not the same thing, and only one of them is what was intended.

Compounding it: this fires on **every** room context build for **every**
character, not once per room. A tick where several NPCs move through the
same area has each of them emit a spoken paragraph.

## Fix

Render the narration as an emote in the event stream locally (the
`events.log(..., 'system-msg')` call in `_generateAINarration` already
does this — see the duplicate) and do not post it as speech. If the
narration genuinely needs to be visible to other characters as an
observation rather than a spoken line, that is a different endpoint and
a deliberate decision, not a side effect of wanting italics.

## Acceptance

- Reproduce: enter a room with at least one other character, with
  narration mode `ai` and a configured model. Assert that character's
  `recent_hearing` gains an entry naming the speaker and the narrated
  text.
- After the fix: same steps, `recent_hearing` unchanged, and the
  narration still renders as an emote in the event stream.
- Assert `on_speech_heard` does not fire for narration.
- Confirm no duplicate: `_generateAINarration` already calls
  `events.log(\`[AI Narration] ${cleaned}\`, 'system-msg')`, so today the
  text appears twice — once from that log, once as the broadcast. State
  which one survives.
- Regression guard: a test that a narrated room context build performs
  no `POST /api/players/*/speak`.
