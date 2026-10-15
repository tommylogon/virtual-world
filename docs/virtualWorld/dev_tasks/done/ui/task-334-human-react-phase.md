---
type: task
status: done
area: ui
priority: medium
---

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

> **Turn-system semantics:** the queue, the human-turn gate, the dash-burst second
> action slot, and the deliberate always-available command-line override are all
> documented in `docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md` (task-338).
> Read that before changing phase timing or turn advancement here.

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

## What

TODO

## How

TODO

## Steps to verify

1. In a turn-based scenario, submit a human action from the Human Turn panel
   and inspect the next phase and result text.
   - expected: the panel advances Compose → Act → “② react to the result”; it
     shows the action result before offering speech/emote/memory controls.
   - observed (task-333 record, 2026-08-24): phase state, result area, skip-react,
     and changing close controls are recorded as implemented; no browser E2E is
     recorded for this card.
2. React with one line of speech and one emote, then pass; inspect Event Stream
   as another character and open the actor's Memories in the Inspector.
   - expected: both reactions are witnessed through normal speech/emote events
     and one deterministic action/result memory plus the manual memory are in
     the character's existing memory store.
3. Repeat with `dash` and inspect the phase before react.
   - expected: one burst action is offered in the new area before react; a
     non-dash action has no burst phase.

## Browser UI and intended live verification

Intended UI home: Human Turn panel → Act result → “② react to the result”
phase; Event Stream and Character Inspector → Mind → Memories show the effects.

Current availability: Compose/Act/react/pass, dash burst, automatic memory,
manual memory, and witnessed react events are implemented according to this
card's record. Digest and interjection lanes remain explicitly deferred. The
integrated browser flow is not recorded as tested.

Live steps when available:
1. Submit a human action, then read the result in the panel before entering a
   reaction; add speech, an emote, and a manual memory, then pass.
   - expected: phase order is Compose → Act → React → pass and every reaction
     is visibly tied to the just-returned result.
2. Inspect the event stream as a second character and open the actor's Mind →
   Memories after the turn.
   - expected: speech/emote are witnessed normally and the deterministic memory
     plus manual entry are stored in that same Player memory list.
3. Repeat with dash and with a normal action.
   - expected: only dash exposes one burst action in the destination area
     before react.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Acceptance

- [ ] Human turn flow is compose → Act → react (say / emote / memory bound to the result) → pass; the phase pill reads "② react to the result" and the close controls swap accordingly.
- [ ] A dash grants one extra action slot (burst phase) in the new area before react.
- [ ] A deterministic auto-memory line is stored per human turn (action + speech + emote + area + tick, no LLM call); the manual memory field persists through `/api/action` into `Player.memories[]` (source: manual).
- [ ] React speech/emotes ride the same witnessed-event pipes as agent speech (so a later observer sees them).
- [ ] (Deferred, not this card) lanes 2/3 — turn-start digest UI and the interjection queue.

## Files

- TODO
