---
type: task
status: done
area: refactor
priority: low
---

# task-657: ResponseParser.parseObservation and parseDecisionWithSpeech have zero call sites

**Filed:** 2026-09-30
**Related:** 

## Goal

Two functions extracted from agent-engine.js in task-218 are dead: across all of static/ and templates/ each appears only at its definition and export. git show 170d5f1:static/js/agent-engine.js shows neither was ever called from the engine, so this is pre-existing dead code, not an extraction regression. Either wire the observation phase through parseObservation (the observation memory written as src:observation evidently comes from another path) or delete both exports.

## Acceptance

- TODO

## Resolved — 2026-10-02 (deleted, not wired)

Re-verified before deleting: a word-boundary search across `static/` and
`templates/` still finds each name only at its definition and its export.
`git show 170d5f1:static/js/agent-engine.js` confirms neither was ever called,
so this is pre-existing dead code.

A **named superseding live path** exists for both (the AGENTS.md bar for calling
a JS symbol dead):

- `parseDecisionWithSpeech` → `ResponseParser.parseReaction`, called at
  `agent-engine.js:631` (combined think/decide), `:837` (non-reactive path),
  `:1188` and `:1252` (auto-retry). It already returns the same
  `inner`/`speech`/`speechVolume`/`action`/`emote` fields.
- `parseObservation` → the observation phase is folded into the combined
  think/decide call, whose `inner_monologue` is returned by
  `parseReaction` as `inner`. No separate observation response is parsed by the
  engine, so no caller is stranded.

Changes: deleted `parseObservation` and `parseDecisionWithSpeech` (and their two
export names) from `static/js/agent/response-parser.js`; 32 lines removed, no
insertions, no other file touched.

### Verification

- Grep across `static/` + `templates/`: the two names now appear nowhere.
- `node tools/unit/run.cjs` → 485 passed, 0 failed.
- `npm run lint`, `npm run typecheck` → clean.
- Live load on :4471 (Playwright) — `ResponseParser` exposes only
  `parseReaction`/`parseResultReaction`/`extractMemory`; the removed names are
  `undefined`. The deletion cannot change a turn: neither had a caller.

Remaining live check before `done`: one LLM turn through the real
`parseReaction` path on a working provider (LM Studio is reachable on :1234).

## Live turn — 2026-10-02 (port 4471, LM Studio on :1234)

Drove a real turn with `VW.agent.stepOnce()` and watched the event stream:

- stream bubbles grew 3 → 5 with **no page errors**;
- the new entries are a thought (`💭 [Tick 19] Kaelen Voss — "The door is locked.
  Again. ..."`) and a reaction (`🎭 [Tick 20] Kaelen Voss — "Kaelen Voss watches
  the door handle with tired eyes..."`), i.e. the live `parseReaction` /
  `parseResultReaction` path produced the inner monologue and the action.

So the surviving parser path works in a real LLM turn, which is the behaviour the
two deleted exports had no callers for. Moving to `done`.
