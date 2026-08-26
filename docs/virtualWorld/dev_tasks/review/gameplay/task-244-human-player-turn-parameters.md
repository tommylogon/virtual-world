# Task-244: Structured Human Turn Composer — Reply Like an Agent

**Status:** In Review — implemented 2026-08-16.
**Source:** `dev_tasks/developer ideas.md` (improved human player in turn with parameters like agents get) + clarifying discussion 2026-08-16.

## Implementation (2026-08-16)

- `static/js/agent/human-turn-composer.js` — new `HumanTurnComposer.request(charName, roomContext)`
  returns a Promise resolving to a normalized structured reply. Builds a modal with a
  form (action + item + target + relation + speech/volume + emote + optional memory) and a
  toggle to a raw-JSON textarea, with a live parse preview. Submits through the existing
  pipeline: `ActionNormalizer.normalizeStructuredAction` + `extractSpeechVolume`,
  `ResponseParser.extractMemory` — identical contract to an agent reply.
- `static/js/agent-engine.js` — `step()` no longer silently skips human characters; it now
  `await`s `_humanTurn(charName)`. The run loop pauses on the human's turn. `_humanTurn`
  fetches the character, shows the composer, then executes speech → action → emote → memory
  via the same helpers agents use (`_speakLine`, `ApiClient.action`, `_performEmote`,
  `_storeReactionMemory`), and advances the queue once the human acts (or passes).
- `templates/index.html` — composer script loaded after `response-parser.js`.
- `static/js/main.js` — `VW.humanTurnComposer` registered.

## Goal

On a human player's turn, prompt the human with a **structured action composer** instead of
the plain free-text command box — a form (or raw-JSON text area) to fill in the SAME
structured reply schema an LLM agent emits, then parse and execute it through the exact same
agent pipeline. The human gets the agents' structured power: combine an action with
`speech`+`volume`+`emote`+`memory` in one turn, with proper validation.

Explicitly **out of scope**: the human does NOT get the agent's full LLM user-prompt / room
context blocks (vitals/emotion/relationship summaries, plan guide, etc.). Those are separate
work to solve later. This task is only the reply interface + parsing.

## How it should work

1. On the active player's turn, surface a composer (modal/overlay beside `#command-input`).
2. The human fills in structured fields:
   - `action` (verb) + `item` + `target` + `relation` (for put/place)
   - `speech` + `volume` (whisper/say/shout/scream)
   - `emote` (optional), `memory` (optional)
   - OR skip the form and paste raw JSON into a text area.
3. Run the filled object through the **existing** parsers so human input gets identical
   handling/validation to an agent reply:
   - `ResponseParser.parseReaction(json)` (currently `static/js/agent/response-parser.js`)
   - `ActionNormalizer.normalizeStructuredAction(parsed)` → backend command string
     (`static/js/agent/action-normalizer.js:46`)
   - `ActionNormalizer.isValidAction(command)` → reject invalid verbs like an agent's would,
     or auto-skip/notify.
4. Execute:
   - main action → `ApiClient.action(finalCommand)`
   - `speech`/`volume` → `_speakLine` pattern (`ApiClient.action("<volume> <speech>")`,
     see `agent-engine.js:94-100`)
   - `emote` → `ApiClient.emote(charName, emote)` (`agent-engine.js:102-112`)
   - `memory` → write to the player's memories (reuse agent memory-store).
5. Advancing the turn afterward is unchanged from current manual-turn flow.

## Decisions (confirmed 2026-08-16)

1. **Form vs JSON textarea → toggle of either/or.** The composer offers both; the human
   switches between a form UI and a raw-JSON textarea with a live parse-preview (shows the
   normalized command before submit).
2. **Composer complements, does not replace, `#command-input`.** Free-text typing + Tab
   autocomplete stays; the structured composer is surfaced on the human's turn alongside it.
3. **Invalid actions behave like any character.** If the human says `take glass` but there's
   no glass in the room, it goes through normally → the backend returns the usual
   system response (in-world rejection), exactly as for agents. No special-casing.
4. **Memory is optional.** The human may leave it blank (nothing written) or attach their
   own subjective `memory` object; it's the human's choice per turn.

## Notes / open questions

- Relation picker for `put`/`place` (`on|under|beside|behind|at|in`) and a target picker
  scoped to the current room (items present, players present, exits).
- Reuse, don't duplicate: drive everything through the existing
  `ResponseParser` + `ActionNormalizer` so the contract stays identical to agents.

## FIXED (2026-08-16) — control-mode toggle did nothing visible

Bug: clicking the mode badge logged "→ NPC-controlled" every click with no visible change.

Root cause (two defects):
1. `cycleControlMode` (`event-stream.js`) never refetched `worldState` after
   `ApiClient.updateCharacter`, and only re-rendered on the `human` branch. The badge is
   computed from `getControlMode()` reading `player.simple_npc` from stale state, so it
   stayed frozen and every click re-applied the same mode (the NPC re-log loop).
2. `autonomy` was never persisted: no `Player.autonomy` attr, no `routes/players.py`
   handler, no serialization. Human mode was frontend-only memory, lost on reload.

Fix:
- `event-stream.js` `cycleControlMode`: `await worldState.fetch()` + `VW.ui.renderAll()`
  for ALL modes after a successful update.
- `event-stream.js` `isAutonomous`: seed the cache from `worldState.players[..].autonomy`
  when unset, so persisted human state survives reloads.
- `player.py`: added `self.autonomy = True` + `to_dict` field.
- `engine/serialization.py`: serialize `autonomy` out/in.
- `routes/players.py` `api_update_player`: handle `"autonomy" in data`.

Verified: `tools/test_control_mode.cjs` E2E — mode cycles llm → npc → human → llm with
`autonomy` + `simple_npc` persisted through the backend each click; 942 pytest pass.