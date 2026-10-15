---
type: bug
status: done
area: ui
priority: medium
---

# bug-514: Generate from Personality does nothing and says nothing when no LLM is configured

**Filed:** 2026-09-30
**Related:** 

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. With a test profile whose API key and model are empty, open a character's
   Bio tab and hover ✨ Generate interests and 😨 Generate fears.
   - expected: both buttons are disabled and their tooltips tell the author to
     configure an API key and model in Settings.
   - observed (2026-10-02): both real buttons were disabled and carried the
     Settings message after the inspector was reopened with empty values.
2. Switch to a profile with a configured provider and reopen the same inspector.
   - expected: both buttons are enabled; invoking either without configuration
     cannot wait for tag collection before explaining the missing provider.
   - observed (2026-10-02): both buttons were enabled with the default provider
     profile; the no-provider handler was measured to toast immediately.

## Browser UI and intended live verification

Intended UI home: Character Inspector → Bio → Interest tags / Fear tags →
Generate from Personality.

Current availability: The disabled buttons, tooltips, configured-provider
state, and immediate no-provider message were live-checked on 2026-10-02. The
test used a profile with empty credentials and then restored the default
profile; do not clear a user's saved credentials to reproduce it.

Live steps when available:
1. Use a disposable profile with no API key or model, select a character, open
   Bio, and scroll to both tag sections; hover each Generate from Personality
   button.
   - expected: both controls are disabled and each tooltip points to Settings.
2. With the same profile, invoke each generator through its UI action handler.
   - expected: the missing-provider explanation appears immediately, before
     any async tag or vocabulary lookup can make the click appear stalled.
3. Switch to a configured test profile and reopen the inspector.
   - expected: the two controls are enabled and the existing configured-provider
     flow remains available.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Files

- TODO
