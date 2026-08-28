# Agent Lessons — things I must NOT do again

Working notes for the agent (and any future context) on this project, so the
same mistakes are not repeated. Written in response to a long relationship/
emotion/name/memory feature session that over-reached and reinvented things.

## 1. Find the existing mechanism BEFORE building a new one
- The click-to-expand on LLM request/response chips ALREADY existed
  (stream-raw-llm.js `_chipBubble`). I built a parallel `events.log` feedback,
  then re-used the chip. Waste, and it confused the user.
- `window._lastRecallStats` was ALREADY read by the request chip (line 61) but
  never set — a dead pipe. I should have found and populated it, not built a
  second path.
- PRACTICE: grep for the feature/pipe first. If a half-wired pipe exists, set
  it. Never build a parallel mechanism without checking.

## 2. NEVER render diagnostics adjacent to / inside the prompt display
- I appended `── RECALLED MEMORIES ──` to the SAME DOM `<pre>` as the prompt
  text. It LOOKED like part of the prompt. That is a UX lie and it erodes
  trust even when the LLM never actually received it.
- PRACTICE: diagnostic/UI output must be structurally separate from the LLM
  request display (a different row/chip/panel). And VERIFY by tracing the
  `messages` array actually sent to the model, not the on-screen body.

## 3. The prompt-invariant: `messages` must never carry diagnostic metadata
- Source/score/keywords/query stay OUT of the prompt. The `=== I REMEMBER ===`
  block is memory text only (parts.push(entry.text)).
- PRACTICE: after any prompt-builder change, grep every builder file for the
  diagnostic global and confirm no builder reads it.

## 4. Root-cause the actual failing component, not the nearest subsystem
- "use the steamed meal" → "You don't have it". The reachability fix (
  find_reachable) WAS in place. The real failure was NAME RESOLUTION: "the
  steamed meal" vs "Steamed Meal (Holding Chute)" (article + parenthetical).
- PRACTICE: grep the exact error string, read the matcher, reproduce the
  specific failing input, THEN fix. Don't assume it is the subsystem you
  were last editing.

## 5. Don't redesign what already works / don't over-scope
- Big model session built an experience-driven relationship layer + name/
  feeling wiring when the user already had an alias system + relationship
  system. Pushback: "spent hours redesigning what I already had, but worse."
- PRACTICE: ask whether the existing system already solves it. Prefer
  additive + dormant changes (that fall back when there is no signal) over
  redesigns. Confirm scope before building a large layer.

## 6. Respect the phase semantics (recipient-judge locus)
- react phase = react to YOUR OWN action outcome, before others act.
- Recipient-decides how a line landed belongs at TURN START (observe/think,
  the === WITNESSED === block), NOT the react phase.
- The recipient decides the feeling; the ENGINE owns the magnitude (bounded
  vocab + clamp + deterministic reduction). LLM never writes a raw number.
- FACTS (who's present, what's their name) are graph/evidence-gated, NOT
  trusted from a memory or an LLM guess.
- Name-knowledge: unknown → `first_sighting:true` (appearance label), known →
  false (real name). Names are earned by hearing/reading, not guessed.

## 7. Trace the REAL data flow and verify the live build
- The duplicate memories were the RETRIEVAL dedup gap (3 pipelines, no dedup),
  not my storage change. The recall note leaked to the react call via the 30s
  freshness window (now gated on the call actually containing I REMEMBER).
- PRACTICE: when a bug is reported, trace across ALL pipelines (storage ->
  retrieval -> display) and confirm the running build picked up the fix
  (hard refresh). Diagnose the observed behavior, not the code you last touched.

## 8. Communicate honestly, don't claim what you can't verify
- Be clear what is engine-tested vs what needs a live run. When wrong, own it
  plainly ("that was my bug"), and state the fix + the residual unknown.

## Files historically touched by this work
- engine/derive.py (new), engine/grapple.py, engine/item_reach.py
- player.py, routes/{player_ops,memories,players}.py
- static/js/agent-engine.js, response-parser.js, memory-manager.js
- static/js/agent/prompt-builder/{schema-fragments,turn-prompts,character-state,memory-context,room-context}.js
- static/js/stream/stream-raw-llm.js, static/js/inspector/agent-view.js
- tests/test_derive.py (new), tests/test_grapple.py