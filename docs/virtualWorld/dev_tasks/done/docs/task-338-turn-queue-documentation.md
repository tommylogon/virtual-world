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

## Result (2026-09-30)

The chapter already existed — `docs/virtualWorld/Gameplay/Turn Queue & Human
Turns.md`, already declared as `@docs` from `turn-queue.js:8`. Measuring it
against the five requested points: **4 of 5 were covered** (queue modes,
gating, override semantics, interaction rules). Two gaps were real:

1. **Point 5 was absent** — "where does the next-up indicator read from". Added
   a section covering the three views, and corrected my own first draft: I had
   written that the modal and the strip "read different things", but a live
   measurement had them **agree** on the head of the order (modal
   `tick 2 · next up: Silver-Talon`, strip `⏭ up next: Silver-Talon → Leslie →
   Tusker → Vekka → Gribba`). The difference is width and gating, not meaning.
   The Turn Order panel is a third view and is now documented too.
2. **The AGENTS.md "Turn system" gotcha block did not exist** — only incidental
   mentions of the modal's hint text. Added, carrying the same measured
   correction.

Also added, from a question the doc could not previously answer: **what the
world does while it waits for a human, and what happens if they never answer.**
The gate is `agent-engine.js:459` → `await this._humanTurn(charName)` →
`HumanTurnComposer.request()`, and **there is no timeout** — the sim waits
indefinitely until Act or end-turn.

### Doc-completeness test

Ran a fresh subagent restricted to the two documents (no source access) against
the acceptance criterion. It answered "is `Turn: 0` a bug / may I fix the
command line / do the next-up indicators disagree" all **correctly from the
docs alone**, citing the sections. Its unanswerable list was live-runtime
values (`turnQueue` contents, DOM coordinates) — never in scope. One item was
actionable and became the "what the world does while it waits" section: it
could not tell whether the modal is *guaranteed* to appear.

### Live confirmation of the documented facts

On a real session with a human-controlled slot, all three indicators read:
`#htc-meta` = `tick 2 · next up: Silver-Talon`, the strip =
`⏭ up next: Silver-Talon → Leslie → Tusker → Vekka → Gribba`, modal title =
`player_human_explorer's turn`. The panel also showed the documented
stranger-masking ("the woman") and the hover/click hint. Separately confirmed
that a scenario whose every character is autonomous (`autonomy: true`) opens
**no** modal — correct per the gate, and the reason an earlier attempt found
`#htc-meta` missing.
