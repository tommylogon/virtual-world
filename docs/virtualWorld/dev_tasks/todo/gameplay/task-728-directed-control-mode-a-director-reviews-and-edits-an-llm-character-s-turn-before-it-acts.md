---
type: task
status: todo
area: gameplay
priority: medium
---

# task-728: Directed control mode: a director reviews and edits an LLM character's turn before it acts

**Filed:** 2026-10-07
**Related:** task-340, task-692, task-245

## Goal

Add a fourth character control mode, 'directed', beside npc / human / llm: the character's LLM still generates its turn (nudge -> action, speech, inner monologue, emote, emotion, memory) but does NOT act on its own. Instead the HTC modal opens pre-filled with the generated draft, the director may edit any field, reroll any field individually, or chat with a director prompt to guide a regeneration, then press Act to commit through the existing compose-then-commit path. Design-only for now.

## Acceptance

- TODO

## The flow the designer described

1. Press **Step**. The turn reaches a character in `directed` mode.
2. The character's LLM runs its normal decide/nudge phase and produces a draft —
   it wants to do X, say Y, thinks Z, feels W, and would remember V.
3. **Nothing is submitted.** The HTC modal opens **pre-filled** with that draft.
4. The director may:
   - **edit any field** (action, speech, inner monologue, emote, emotion, memory);
   - **reroll any field on its own** — regenerate just the action, or just the
     line, or just the emotion, without rerolling the rest;
   - **chat with a director prompt** — e.g. *"I want jake to examine that thing
     while he says 'wonder if anything's in there'"* — and the LLM produces a
     matching draft to accept or keep editing.
5. Press **Act** → the draft commits through the existing compose-then-commit
   path, and the react phase follows as it does for a human turn.

## Why this is a fourth mode, not a tweak

`StreamControlMode.getControlMode` (`static/js/stream/stream-control-mode.ts`)
answers with exactly three values — `'npc'` (simple_npc, backend tick drives
it), `'human'` (autonomy off, the human drives via commands), `'llm'`
(autonomous, the agent engine drives it). Directed mode is none of them: the
LLM still runs (unlike `human`), but its output is intercepted instead of
applied (unlike `llm`). It needs a real fourth state, resolved in the same one
vocabulary every badge already uses.

## Existing seams to build on (do not reinvent)

- **The draft shape already exists.** `ResponseParser.parseReaction`
  (`agent-engine.ts`) returns `{inner, speech, speechVolume, action, emote,
  memory, emotion, target, parseError}`; `parseResultReaction` returns the react
  subset. Those are exactly the fields the director edits and rerolls.
- **Compose-then-commit already exists.** `human-turn-composer.ts` is explicitly
  built on it: *"Menu picks and typed input only FILL the draft — nothing fires
  until Act."* Its `request()`/`react()` already take and return
  `{action, speech, speechVolume, …}`. Directed mode is the same modal with the
  draft **pre-filled from the LLM** instead of empty.
- **Per-turn control** already keys off autonomy per character (task-340);
  directed mode adds a character state, not a global toggle.

## Design questions to settle before building

- **State home.** Directed is a per-character control state. Does it extend
  `autonomy` (a third value instead of a bool) or add a parallel field? It has to
  survive reload and serialize with the player.
- **Cost — not a concern (designer, 2026-10-07).** A reroll is a few hundred
  tokens, not a scale problem; no budget cap is needed for this. Still decide
  whether a reroll reuses the existing prompt context (cheaper and more
  consistent) purely for quality, not for cost.
- **What the nudge returns.** The decide phase already distinguishes plan vs
  action vs reaction; directed mode needs the decide output *without* the act
  submission. Find the exact seam in `agent-engine.ts` between "generated" and
  "submitted" — that is where directed mode intercepts.
- **The director chat.** Is the chat a separate prompt that produces a fresh
  whole-draft, or does it produce a *patch* to the current draft? A patch is
  cheaper and preserves the parts the director liked.
- **Turn queue interaction.** A directed character pauses the loop for a modal,
  like a human does. Confirm it takes the human-style blocking slot rather than
  the autonomous one.

## Non-goals

- Changing what the LLM generates — this is a review/approve layer over it.
- Multiplayer direction (task-245).

## Notes

Design-only. Not implemented.
