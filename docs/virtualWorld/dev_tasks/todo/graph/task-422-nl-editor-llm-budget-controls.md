---
type: task
status: todo
area: graph
priority: medium
---

# task-422: NL editor LLM budget controls and context readout

**Filed:** 2026-09-20  
**Depends on:** task-387 (NL editor). Builds on the context-accounting fix landed
2026-09-20 in `static/js/context-window.js` (identity-keyed metadata, bounded
critical retention, array-measured pruning).  
**Relates:** `static/js/nl-editor/agent-loop.js`, `static/js/nl-editor/index.js`,
`static/js/nl-editor/ui.js`, `static/js/config.js`.

## Goal

Make the NL editor's LLM budget visible and adjustable from the NL editor tab,
instead of being hard-coded constants. The user asked for this directly: "set
max tokens to 60000, or even adjustable in the NL editor tab".

## Current state

The knobs exist but are buried and unadjustable:

| Knob | Where | Value |
|------|-------|-------|
| `maxIterations` | `agent-loop.js` — `this.maxIterations` | 100 |
| `maxTokens` | `ContextWindowManager` (NL editor) | 6000 |
| `maxMessages` | `ContextWindowManager` (NL editor) | 30 |
| `recentTurnCount` | `ContextWindowManager` (NL editor) | 8 |
| `maxCriticalMessages` | `ContextWindowManager` | 10 |

`ContextWindowManager.getStats()` already reports
`{totalMessages, totalTokens, maxTokens, maxMessages, utilization, isOverLimit}`
and **nothing consumes it**. `agent.maxIterations` is already read by
`index.js` for the status string, so the loop cap is exposed to the UI.

Missing, and worth fixing in the same pass: when the iteration cap is hit the
loop simply exits. If the model's last message had no text,
`finalAssistantResponse` is empty and the UI shows nothing — a silent stop.

## Design

1. **Knobs, in the NL editor panel.** A compact collapsed "⚙ Budget" row in the
   panel header (next to Reset), expanding to a small form:
   - Max rounds (iterations)
   - Max context tokens
   - Max messages retained
   - Recent turns kept
   Keep it out of the chat stream; the panel is narrow and the chat is the point.

2. **Persistence** via the existing helper pattern —
   `storage.setConfig('nl_max_iterations', ...)` / `storage.getConfig(...)`
   (see `config.js` for the established shape). Defaults reproduce today's
   behaviour exactly when nothing is saved: 100 / 6000 / 30 / 8 / 10.

3. **Model-aware default for `maxTokens`.** 60000 is only safe if the active
   provider/model actually has that window; a local LM Studio model with an 8k
   context would overflow. Derive the default from the active model's known
   context length and clamp, falling back to a conservative value when the model
   is unknown. **This needs a model → context-length lookup that does not exist
   yet** — a small table keyed by the same model names used in
   `getFallbackModels`, with an explicit "unknown → conservative" path. Scope
   this sub-piece carefully; do not guess large windows for unknown models.

4. **Readout.** Show `context 4.2k/6k · round 12/100` in the status area using
   `getStats()`. This is the observability that would have made the pruning bug
   obvious; keep it live per iteration.

5. **Report a capped stop.** If the loop exits because `currentIteration` reached
   `this.maxIterations`, emit it — set the turn-end payload with a flag and have
   the UI append a visible note such as "Stopped at the 100-round limit; the
   edit may be incomplete." Do not end silently with an empty response.

6. **Apply to the next turn without a reload.** Read the knobs at `runUserTurn`
   start and construct/update the `ContextWindowManager` options there, so a
   changed value takes effect on the next prompt.

## Acceptance

- Changing any knob persists across a reload and takes effect on the next turn
  with no code change.
- Defaults with nothing saved reproduce current behaviour (100 / 6000 / 30 / 8).
- The status area shows the live context window and round counter.
- Hitting the round cap produces a visible message in the chat, never a silent
  stop.
- `maxTokens` default is clamped to the active model's window; unknown models get
  a conservative default rather than an assumed large one.
- The **main agent engine's** own `ContextWindowManager`
  (`agent-engine.js:39`, `maxTokens: 9500`) is unaffected — its options are not
  driven by these NL-editor settings.

## Non-goals

- Changing pruning semantics or retention policy (that fix already landed).
- Dollar cost accounting or prompt caching.
- Per-scenario or per-character budget overrides.
- Making the same knobs adjustable for the foreground agent engine.

## Verification

- Unit: options round-trip through `storage` config; clamp/fallback logic for
  known, unknown, and absurd values (0, negative, 10x the model window).
- Unit: `getStats()` reporting matches the window actually sent.
- Manual: set max rounds to 20, run a long multi-tool edit, confirm it stops at
  round 20 and says so in the chat.
- Regression: `npm run lint`, `npm run typecheck`, and the existing pytest suite
  stay green.
