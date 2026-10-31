---
type: task
status: review
area: gameplay
priority: low
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
---

# task-728: Directed control mode: a director reviews and edits an LLM character's turn before it acts

**Filed:** 2026-10-07
**Related:** task-340, task-692, task-245

## What

Add a fourth character control mode, 'directed', beside npc / human / llm: the character's LLM still generates its turn (nudge -> action, speech, inner monologue, emote, emotion, memory) but does NOT act on its own. Instead the HTC modal opens pre-filled with the generated draft, the director may edit any field, review inner thoughts, then press Act to commit through the existing compose-then-commit path.

## Acceptance

1. Control mode supports 'directed' beside 'human', 'llm', and 'npc'.
2. Badge vocabulary renders 🎬 Directed for directed characters.
3. Directed mode serializes on the player (`autonomy: "directed"`) and survives saves and reloads.
4. During an LLM step, think-decide generates a draft without immediate world submission, opening HumanTurnComposer with the draft prefilled.
5. Director can edit action, speech, emote, memory, or dismiss/end turn. Clicking Act commits the reviewed turn cleanly.

## The flow the designer described

1. Press **Step**. The turn reaches a character in `directed` mode.
2. The character's LLM runs its normal decide/nudge phase and produces a draft -
   it wants to do X, say Y, thinks Z, feels W, and would remember V.
3. **Nothing is submitted.** The HTC modal opens **pre-filled** with that draft.
4. The director may edit any field (action, speech, inner monologue, emote, emotion, memory).
5. Press **Act** -> the draft commits through the existing compose-then-commit
   path, and the react phase follows as it does for a human turn.

## Why this is a fourth mode, not a tweak

`StreamControlMode.getControlMode` (`static/js/stream/stream-control-mode.ts`)
answers with four values: `'npc'`, `'human'`, `'llm'`, and `'directed'`. Directed mode is distinct: the LLM still runs (unlike `human`), but its output is intercepted instead of applied automatically (unlike `llm`). It uses the clapperboard badge 🎬 across stream, roster, and inspectors.

## Existing seams to build on (do not reinvent)

- **The draft shape already exists.** `ResponseParser.parseReaction`
  (`agent-engine.ts`) returns `{inner, speech, speechVolume, action, emote, memory, emotion, target, parseError}`. Those are exactly the fields the director edits.
- **Compose-then-commit already exists.** `human-turn-composer.ts` is explicitly
  built on it: menu picks and typed input fill the draft, nothing fires until Act.

## Why

Storytelling and narrative simulation often require curated steering without losing character initiative. An ensemble drama (like Millwood) benefits from characters having internal motivations drafted by LLMs, while allowing the director to adjust lines, tone, or actions before they enter the simulation.

## How

1. Extend `routes/player_ops.py` and `engine/serialization.py` to support string `"directed"` in `player.autonomy`.
2. Update `StreamControlMode` in `static/js/stream/stream-control-mode.ts` with `'directed'`, cycle order `['human', 'directed', 'llm', 'npc']`, and badge `{ emoji: '🎬', label: 'Directed', title: '...' }`.
3. Add prefill support (`TurnPrefill`, `#htc-thought-row`, `applyPrefill`) to `HumanTurnComposer` (`static/js/agent/human-turn-composer.ts`).
4. In `AgentEngine` (`static/js/agent-engine.ts`), intercept think-decide phase when `events.getControlMode(charName) === 'directed'`, passing the draft to `HumanTurnComposer.request(charName, { prefill })` and applying the reviewed payload before action execution.

## Steps to verify

1. Run unit test `node tools/unit/run.cjs test_directed_mode`.
   - expected: 3 passed, 0 failed.
   - observed: 3 passed, 0 failed.
2. Run serialization test `python -m pytest tests/test_serialization.py`.
   - expected: 22 passed, 0 failed.
   - observed: 22 passed, 0 failed.

## Files

- `routes/player_ops.py`
- `engine/serialization.py`
- `static/js/stream/stream-control-mode.ts`
- `static/js/agent/human-turn-composer.ts`
- `static/js/agent-engine.ts`
- `tools/unit/test_directed_mode.js`

## Browser UI and intended live verification

Intended UI home: enable `directed` control for a character -> Human Turn Composer opens with that character's generated draft -> edit fields -> press **Act** to commit through the existing compose-then-commit flow.

Live steps:
1. Set one character (e.g. Jake) to `directed` mode via roster or inspector.
2. Advance a turn. Observe that the HTC modal opens pre-filled with the drafted action, speech, emote, memory, and thought.
3. Edit speech or action and click Act.
4. Verify the event stream and character action match the edited draft.
