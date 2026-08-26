# Task 338 — Document turn-queue & human-turn gating architecture

**Status:** Todo — filed 2026-08-23 after Tommy corrected a wrong
assumption in the panel redesign work (task-333/334)

## Why

The turn system EXISTS and is real — `static/js/agent/turn-queue.js`
manages character ordering (sequential / random / **initiative** with d20
+ DEX rolls, re-roll support) consumed by AgentEngine as
`.turnQueue` / `.currentTurnIndex` / `.turnNumber`. The human turn panel
is gated to the controlled character's slot in that queue. Meanwhile the
always-available command line / guest-speaker path in the event stream is
a **deliberate godmode-level override**, not a missing scheduler.

None of this was understood during the panel redesign until Tommy
corrected it — the architecture lives in code + Tommy's head, not docs.
That's a documentation gap: future work (react phases, digests, dash
two-action turns, multi-human tables) all builds on these semantics.

## What to document (AGENTS.md section + guide chapter)

1. **Turn queue** (`turn-queue.js`): order modes, initiative rolls,
   re-roll, how currentTurnIndex advances, what happens on
   join/leave/death mid-queue.
2. **Human turn gating**: how the panel knows it's "your turn"; what the
   world does while waiting (autopilot paused? ticks continue?); what
   happens if the human idles.
3. **Godmode override semantics**: the free-typing command line /
   guest-speaker event-stream path — always available by design, bypasses
   the queue, when to use vs when it breaks scene logic.
4. **Interaction rules**: override actions vs queued turns (does an
   override consume the character's queued slot?), digest/react
   implications (task-334 builds on this).
5. Where the panel's "next up" indicator reads from.

## Files

- `AGENTS.md` — new "Turn system" gotcha block
- `docs/virtualWorld/` — architecture chapter (or extend an existing
  engine doc)
- Cross-link from task-333/334

## Verification

- A fresh agent (or human) can explain whose turn it is and why the
  command line still works, purely from the docs.
