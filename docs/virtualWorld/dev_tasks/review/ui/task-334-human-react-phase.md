# Task 334 — Human react phase + automatic memory capture

**Status:** In Review — implemented 2026-08-24 as part of task-333's human turn panel
redesign (lane 1: post-Act react + dash burst + deterministic auto-memory). Lanes 2/3
(digest + interjection queue) are deferred — see note.

## Why

Agents run think → act → react; react produces inner monologue, felt-emotion update,
reactive speech, reactive emote, and one stored memory — all bound to the RESULT.
Humans had none of it: submit → result → turn passes. The old modal's memory field was
also dropped by `/api/action` (no memory handling), so human chars never remembered
anything unless hand-added.

## What landed (task-333's "Full redesign implemented", 2026-08-24)

- `static/js/agent/human-turn-composer.js` — react phase state machine:
  compose → Act → **react()** (say/emote/memory bound to the result) → close turn.
  Phase pill `② react to the result`, `#htc-result` shows the result, speech placeholder
  reads "react to what just happened…", skip-react link, close buttons swap.
- **Dash = two-action turn**: dash → arrival result → **burst phase** (second action
  slot in the new area) → THEN react. Phase pill `⚡ dash burst — one more action`.
- **Deterministic auto-memory** per human turn (action + speech + emote + area + tick —
  no LLM call, instant) — via `agent-engine._humanTurn` / `_storeReactionMemory`.
- **Manual memory field persisted** through `/api/action` → `Player.memories[]`
  (source: manual) — the dropped-field bug is fixed.
- Reacts ride the same witnessed-event pipes as agent speech/emotes (multi-human ready).

## Verification (from task-333 log)

- pytest 1100 green; `node --check` on all six touched JS files.
- Human turn: act → react speech visible to agents' next observation (manual + code review).
- Auto-memory appears in inspector without manual input (deterministic line).

## Not implemented (lanes 2/3 — deferred)

- Lane 2: turn-start digest UI fed by a queued-events list (grabbed/damage/speech aimed
  at you during others' turns). The panel feed shows "since your turn" but a formal
  digest state is not built.
- Lane 3: interjection queue (say/emote-only, deferred to turn boundary).
- Optional: LLM "inner voice" suggestion (accept/edit/toss).

## Status decision

Lane 1 (the core "react + memory" ask) is done; lanes 2/3 remain future work. Marked
In Review for the implemented portion; reopen or file a follow-up for digest/interject.
