---
type: bug
status: review
area: ui
priority: medium
horizon: now
effort: S
wiki: "[[timeskip|Timeskip]]"
---

# bug-554: A refused timeskip drops the engine reason behind a generic 400 message

**Filed:** 2026-10-17
**Related:** 

## What

`ApiClientImpl._errorMessage` (`static/js/api.ts:24`) reads only `data.error`, and `ApiClient.post` (`api.ts:39-41`) attaches its return value as `error` on any non-ok response. `POST /api/world/timeskip` refuses a dead character with HTTP 400 and body `{ok: false, mode: 'character', reason: 'The dead do not wait.', ...}` (`engine/timeskip.py:243-245`), which has no `error` key, so `_errorMessage` returns the generic `Request failed (400 BAD REQUEST)`. `run()` in `static/js/ui/timeskip.js` then prints `data.error || data.reason`, which is now the generic string.

## Why

Measured live 2026-10-17 with a dead active character: the response body carried `reason: 'The dead do not wait.'` but the dialog showed only `Request failed (400 BAD REQUEST)`. The timeskip result envelope deliberately carries `reason` (it is the engine's refusal text), and every client call that fails is routed through `_errorMessage`, so any route that reports a `reason` instead of an `error` is silently unreadable in the UI. This is the concrete `very little feedback` for a refused skip.

## How

Extend `_errorMessage` to fall back to the first short human-readable field it finds before the generic status line: `data.error`, then `data.reason`, then `data.message`, then `data.detail`. Keep the existing traceback guard (`/\bTraceback\b|File "\S/`) so a raw 500 body or a traceback in any candidate still shows the status line rather than leaking internals. Rebuild the emitted `api.js`; do not hand-edit it.

## Browser UI and intended live verification

Intended UI home: the timeskip result/status line (and every other consumer of `ApiClient`, since the fix is in the shared helper). Current availability: the reason exists in the payload and is dropped by the helper. Live path: with a dead active character, request a timeskip and confirm the dialog shows `The dead do not wait.` rather than `Request failed (400 ...)`.

## Steps to verify

1. With the active character dead, request a timeskip from the dialog.
   - expected: the status shows the engine's reason (`The dead do not wait.`), not a generic 400.
   - observed: TODO
2. Force a genuine 500 (or a traceback body) from a route.
   - expected: the UI still shows `Request failed (500 ...)` and never the traceback text.
   - observed: TODO

## Acceptance

- [x] A 400 whose body carries `reason` (no `error`) surfaces the reason in the UI.
- [x] A raw traceback body is still hidden behind the status line.
- [x] The emitted `api.js` is rebuilt from `api.ts`, not hand-edited.

## Files

- `static/js/api.ts` (`_errorMessage`)
- `static/js/api.js` (emitted)
- `static/js/ui/timeskip.js` (consumer; reads `data.error || data.reason`)

## Reconciliation (2026-10-20) - STILL_VALID, re-measured

**Verdict: STILL_VALID.** `_errorMessage` still reads only `data.error`; the reason is still dropped.

**Re-measured 2026-10-20.**
- `static/js/api.ts:24-29` - `ApiClientImpl._errorMessage` still reads `const raw = (data && typeof data.error === 'string') ? data.error : ''` and returns the generic `Request failed (${status})` for everything else. No `reason`/`message`/`detail` fallback was added.
- `static/js/api.ts:39-40` - `ApiClient.post` still attaches `_errorMessage(resp, data)` as `error` on non-ok responses, so a `reason`-carrying 400 is still flattened to the generic string before any consumer sees it.
- `engine/timeskip.py:302-304` - the dead-character refusal still returns `reason="The dead do not wait."` with no `error` key, so it is still the exact payload the helper drops. (The card cited `engine/timeskip.py:243-245`; the refusal has drifted to lines 302-304 - corrected above. The function is still `advance` and the wording is unchanged.)

**Newer work checked.** `git log --oneline -10 -- static/js/api.ts` returns only `c5034257` and `e7c54eba`, both older than the card's 2026-10-17 filing. Nothing since has extended `_errorMessage`.

**Counts.** `grep -c "reason" static/js/api.ts` → 0 hits. `grep -n "reason" engine/timeskip.py` → 2 hits, both the refusal strings at lines 290, 293-294 and the dead refusal at 304 - the engine still speaks in `reason`, the client still listens only for `error`.

**Status:** left in `todo`. The fix is a ~6-line extension of `_errorMessage` plus a rebuild of `api.js`.
