---
type: bug
status: done
area: ui
priority: medium
---

# bug-514: Generate from Personality does nothing and says nothing when no LLM is configured

**Filed:** 2026-09-30
**Related:** 

## Goal

Both generators open with 'if (!player || !AIGenerator.isConfigured()) return;'. With no provider configured the button silently does nothing - no toast, no disabled state, no explanation - so it reads as a broken button rather than a missing setting. Verified in the browser: AIGenerator.isConfigured() false produces no prompt, no write and no message. Disable the button with a tooltip pointing at Settings, or toast a reason.

## Acceptance

- [x] With no provider, the button is disabled and its tooltip points at
      Settings (verified live, `disabled=true` + title).
- [x] With a provider, the button stays enabled and unchanged (verified live).
- [x] A programmatic call with no provider toasts immediately rather than
      silently returning.

## Fix — 2026-10-02

The half-right part: `AIGenerator.isConfigured()` *does* toast
("Configure API key and model in Settings first."), and did so since the initial
release. The real defect was **ordering**: the interest/fear buttons run an async
tag + vocabulary collection *before* `_generateTagsFromPersonality` reaches its
`isConfigured()` check, so the toast arrived late enough that the click read as
doing nothing. Measured live: after a real button click with `config.apiKey` and
`config.model` cleared, no toast at 900 ms; awaiting the handler directly
produced the toast.

Changes in `static/js/inspector/agent-view.js`:

- `AV._isAiConfigured()` — a side-effect-free provider read
  (`config.apiKey && config.model`), safe to call during render.
- Both **✨/😨 Generate from Personality** buttons now render `disabled` with a
  title ending "— No AI provider configured. Add an API key and model in
  Settings first." when no provider is set, and stay enabled otherwise.
- `_generateInterestTags` / `_generateFearTags` now call
  `AIGenerator.isConfigured()` at the very top, so a programmatic invocation
  toasts immediately instead of after the async collection.

### Live verification (port 4471, real button elements)

| provider state | ✨ button | 😨 button |
|---|---|---|
| `config.apiKey=''` (cleared, then inspector re-opened) | `disabled=true`, title carries the Settings sentence | `disabled=true`, same title |
| default profile (key `not-needed`) | `disabled=false` | `disabled=false` |

No page errors. `node tools/unit/run.cjs` → 485 passed; `npm run lint` and
`npm run typecheck` clean. No engine or data change.
