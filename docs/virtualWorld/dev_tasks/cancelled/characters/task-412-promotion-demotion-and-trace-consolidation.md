---
type: task
status: cancelled
area: characters
priority: high
---

# task-412: Promotion/demotion and trace→memory consolidation

**Superseded by task-399 (2026-09-24).** The background runner (task-399) already
existed, so its one remaining gap — this seam — was built directly there rather
than as a separate task. The promotion/demotion **memory bridge** now lives in
`engine/promotion.py` (`offload` / `promote` / `pending_span` / `summarize`),
with `last_offload_tick` + `background_consolidated_through` marks on `Player`.
See task-399's Progress section.

Not yet done (carried by task-399): the *atomic* tick-boundary transition and the
scope-observation activation boundary. This file is kept as the historical spec.

## Original spec (kept for reference)

**Filed:** 2026-09-19  
**Depends on:** task-399 (background runner), task-411 (attention tiers),
task-418 (attended set), task-420 (one relationship write path).
Without task-420 the foreground and background tiers write relationship state
through different paths, so a tier change can jump the value.  
**Spec:** `docs/design/reversibility-contract.md`, `docs/design/trace-format.md`.

## Goal

Implement the promote/offload handoffs so a character can switch fidelity
without ever becoming a different person or rewriting their past.

## Changes

1. **Promotion handoff.** Build a catch-up summary from
   `engine/trace.summarize_window` since the character was last foreground;
   inject it as a **bounded** subjective memory (`source: "background"`); restore
   the standing goal/plan so promotion resumes rather than reinvents.
2. **Demotion handoff.** Roll the foreground span into the trace as facts +
   reasons; keep live memories in the memory store; mark the span consolidated
   so repeated activation is idempotent.
3. **Atomic transitions.** Activate/offload is atomic at its tick — no action is
   resolved twice.
4. **Invariants.** Enforce position continuity, object conservation, vital
   continuity, relationship symmetry, stable opaque id (task-316),
   determinism, and no orphan nodes (guards the duplicate-character-node class
   of bug).

## Acceptance

- Activate/offload twice at the same tick, then save/reload: no duplicate
  action, character, item, or summary memory.
- A character receives no duplicate background memory after repeated activation.
- A span with a fixed seed replays identically.
- The v1 summary is a deterministic template over trace facts (no LLM); an
  optional LLM summary comes later and only reads the trace.
- Save/load mid-transition is safe because transitions land on tick boundaries.

## Non-goals

- LLM-written catch-up summaries in v1 (template first).
- Editing past memories (the contract forbids rewriting history).

## Verification

- Unit: idempotent activation, no duplicate memory, determinism, invariant
  checks, save/load mid-span.
- Contract test: an item taken in background is neither duplicated nor lost
  across promote → demote.
