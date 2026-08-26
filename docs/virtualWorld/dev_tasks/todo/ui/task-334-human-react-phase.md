# Task 334 — Human react phase + automatic memory capture

**Status:** Todo — design locked 2026-08-23 via mockup feedback sessions;
mockup reference `docs/design/human-turn-panel-v2-mockup.html`

## Why

Agents run think → act → react (agent-engine.js:568-597); react produces
inner monologue, felt-emotion update, reactive speech, reactive emote, and
one stored memory — all bound to the RESULT of the action
(`buildResultReactionPrompt` feeds the result back in). Humans get none of
it: submit → result → turn passes. Worse, the old modal's "Memory"
field is silently dropped (`routes/action.py` has no memory handling), so
human characters never remember anything unless hand-added via inspector.

This matters beyond single-human play: reacts ride the same witnessed-event
pipes as agent speech/emotes, so a future 4-player human DND-style table
needs this machinery to exist at all.

## Design (locked with Tommy)

### React lanes

1. **Post-Act react (lane 1)** — after Act returns its result, the panel
   enters a light "respond to this…" state: say + emote (+ optional manual
   memory note) pre-contextualized to the result. Submitting posts
   speech/emote only — **no second world interaction**, or the turn never
   ends. Then the turn passes.
   - **Dash = two-action turn (locked)**: `dash_to_area`
     (movement.py:519) is "the first hop of a burst" — the turn grants a
     SECOND decision after dashing through the way (agent engine already
     chains another `go`, agent-engine.js:570-574 arrival context). Human
     flow: dash → arrival result → **second action slot** (in the new
     area) → THEN the react step. So the turn state machine is not linear:
     dash extends the act phase by one action before react opens.
2. **Turn-start digest (lane 2)** — incoming events that hit you during
   others' turns (grabbed, damage, saves forced by others, speech aimed at
   you) stack into a catch-up digest shown at the top of your next turn,
   pre-loading the composer with context.
3. **Interjection (lane 3, optional)** — say/emote-only injection for
   urgent incoming moments, queued until the current actor finishes so
   initiative sequencing stays clean.

Saves you roll yourself (entering an area, touching an item) live in your
own action result → lane 1. Saves forced by others' actions → lane 2/3.

### Memory capture

- **Automatic deterministic line** per human turn (action + speech +
  emote + area + tick) — no LLM call, keeps human turns instant, works
  even when the player never journals.
- **Manual memory field persists**: wire the composer's optional memory
  textarea through `/api/action` → `Player.memories[]` (source: manual),
  fixing the dropped-field bug.
- Optional later: LLM "inner voice" suggestion the human can accept/edit/
  toss (agents-quality reflection, opt-in).

## Implementation checklist

- [ ] Panel: react step state machine (act → result → react → pass),
      with dash extending the act phase by a second action slot before
      react (dash → arrival → second action → react)
- [ ] Panel: turn-start digest UI fed by a queued-events list
- [ ] Backend: persist `memory` field from `/api/action` payload
- [ ] Backend: deterministic auto-memory write per human turn
- [ ] Backend/panel: interjection queue (say/emote only, deferred to
      turn boundary)
- [ ] Optional: LLM inner-voice suggestion toggle
- [ ] Event-stream grouping fix (bug_22) interacts with how reacts render

## Verification

- Human turn: act → react speech visible to agents' next observation
- Auto-memory appears in character inspector without manual input
- Multi-human dry-run: two controlled characters exchange reacts
