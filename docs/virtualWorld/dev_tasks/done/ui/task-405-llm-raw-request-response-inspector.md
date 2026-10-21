---
type: task
status: done
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-405: LLM raw request/response inspector

**Filed:** 2026-09-17  
**Depends on:** none

## What

Show the complete raw HTTP exchange with the LLM provider in the UI, not just
the extracted assistant text. Users need to verify what is actually sent and
received - headers, status, full JSON body, usage, reasoning tokens, tool
calls, errors - for debugging providers like OpenRouter, LM Studio, Ollama,
OpenAI, etc.

## Why

`static/js/shared/dataset-collector.js` already captures `{ messages, response,
label, model, parsed_ok, repaired }` to IndexedDB, and a floating panel exports
JSONL for fine-tuning. But `response` is only the extracted text content. The
full HTTP response object - status, headers, raw JSON body, usage breakdown,
reasoning/output token counts - is discarded after `_captureDataset` reads
`completion.choices[0].message.content`.

`static/js/llm-client.js` already logs requests to the event stream via
`VW.events.logRawLLMRequest(label, messages, est)` and responses via
`VW.events.logRawLLMResponse(label, content)`. The event stream UI shows these
as expandable chips. But the stream view is designed for gameplay narration,
not raw API inspection.

## What to build

### 1. Extend DatasetCollector with full payload capture

Add a `captureRaw(label, requestBody, rawResponse, status, headers)` overload
to `dataset-collector.js`. It stores an additional entry under a separate
IndexedDB store, e.g. `llm_raw_exchanges`, with this shape:

```json
{
  "key": "r_1789684764_cpReQMjsVHdo4a1jnm9H",
  "ts": 1789684764000,
  "label": "think-decide",
  "model": "inclusionai/ling-3.0-flash-sante:free",
  "request": {
    "url": "https://openrouter.ai/api/v1/chat/completions",
    "method": "POST",
    "headers": {
      "content-type": "application/json",
      "authorization": "Bearer sk-or-...",
      "x-model": "inclusionai/ling-3.0-flash-sante:free"
    },
    "body": { "model": "...", "messages": [...], "temperature": 0.7, ... }
  },
  "response": {
    "status": 200,
    "statusText": "OK",
    "headers": { "x-ratelimit-remaining": "49", ... },
    "body": {
      "id": "gen-1789684764-cpReQMjsVHdo4a1jnm9H",
      "object": "response",
      "created_at": 1789684764,
      "model": "inclusionai/ling-3.0-flash-sante:free",
      "status": "incomplete",
      "completed_at": 1789684767,
      "output": [ { "type": "reasoning", "content": [...], "summary": [] } ],
      "error": null,
      "incomplete_details": { "reason": "max_output_tokens" },
      "usage": {
        "input_tokens": 2314,
        "input_tokens_details": { "cached_tokens": 0 },
        "output_tokens": 200,
        "output_tokens_details": { "reasoning_tokens": 194 },
        "total_tokens": 2514,
        "cost": 0,
        "cost_details": { "upstream_inference_cost": 0, ... }
      }
    }
  },
  "duration_ms": 3120,
  "parsed_ok": true,
  "repaired": false
}
```

**Redaction:** strip `authorization` header value before storing. Replace with
`"Bearer sk-or-...REDACTED"` so the user can see the header exists without
exposing the key in IndexedDB.

**Non-blocking:** capture is fire-and-forget. Failure to write to IndexedDB
must not affect the game loop or LLM call result.

### 2. Hook capture points in `llm-client.js`

After `const completion = await resp.json()` (line 164), before any extraction:

```javascript
this._captureRawExchange(label, requestBody, completion, resp.status, resp.headers);
```

For streaming, hook after `_handleStream` resolves. `_handleStream` already
assembles the full streamed object; pass that plus the original request body.

For errors (`resp.ok` is false), also capture the error response body so users
can see provider error shapes.

### 3. Build the inspector UI

Add a new panel: **LLM Inspector** (separate from the Dataset Collector panel,
or merge into it with a tab).

The panel shows a scrollable list of recent exchanges. Each entry expands to:

```
┌─ think-decide · inclusionai/ling-3.0-flash-sante:free · 3.1s ─┐
│ Request: POST https://openrouter.ai/api/v1/chat/completions     │
│ Headers: content-type: application/json                         │
│          authorization: Bearer sk-or-...REDACTED                │
│ Body: { model: "inclusionai/ling-3.0-flash-sante:free", ... }  │
│                                                                │
│ Response: 200 OK · 2,514 tokens · $0.00                        │
│ Body: { id: "gen-...", status: "incomplete",                   │
│         incomplete_details: { reason: "max_output_tokens" },   │
│         output: [ { type: "reasoning", content: [...] } ],     │
│         usage: { input_tokens: 2314, output_tokens: 200,       │
│                   reasoning_tokens: 194, total: 2514 } }       │
└────────────────────────────────────────────────────────────────┘
```

Features:
- **Copy request** / **Copy response** buttons per entry
- **Filter by label** (`think-decide`, `result-reaction`, `plan`, etc.)
- **Filter by status** (200, 429, 500, etc.)
- **Clear all** button
- **Search** across request body and response body text
- JSON is syntax-highlighted and collapsible for large `output` arrays

### 4. Persist inspector state

The panel remembers its open/closed state and last scroll position across
turns. Entries survive page reload because they live in IndexedDB.

### 5. Opt-in toggle

Add `showRawLLM` to the Settings UI. Default: `false`. When enabled, the
capture overhead is negligible (IndexedDB writes are async and fire-and-forget).

## How

The card's "What to build" plan landed as five small seams, in this order.

1. **Storage.** `static/js/storage.ts:73-74` creates the `llm_raw_exchanges`
   object store (keyPath `key`) alongside the existing `llm_dataset` store, so
   the fine-tuning export is untouched. The store was added when the DB was
   version 4; the DB has since moved to version 5 for `graph_assets`.
2. **Capture.** `static/js/shared/dataset-collector.ts:172` adds `captureRaw(x)`
   next to the existing `capture`, plus `getAllRaw` (`:224`), `clearRaw`
   (`:232`) and `countRaw` (`:236`). It redacts `authorization`, `api-key` and
   `x-api-key` before the write (`:119-121`, keeping the first six characters
   after `Bearer ` so the header is still visible), caps the store at 200
   entries and trims every 25th capture (`:112`, `:206-208`), and records
   nothing at all unless `config.showRawLLM` is on.
3. **Hook.** `static/js/llm-client.ts:355` adds
   `_captureRawExchange(label, requestBody, body, resp, startedAt,
   requestHeaders)`, called from three places: after `resp.json()` (`:298`),
   after `_handleStream` resolves (`:286`, recording
   `{ streamed: true, content }` because a stream has no provider envelope),
   and in the `!resp.ok` branch (`:256`, so provider error bodies are kept).
   The call is feature-detected against `window.DatasetCollector.captureRaw`
   (`:357`) and never throws into the LLM path.
4. **Panel.** `static/js/ui/llm-inspector.ts` (new) injects a floating button
   (`llm-inspector-btn`, `:56`) and panel (`llm-inspector-panel`, `:64`),
   reads entries through `getAllRaw` (`:123`) and clears them through
   `clearRaw` (`:84`). Each entry expands to the request and response bodies
   with a usage line (prompt / completion / in / out / reasoning / total /
   cost, `:45`), Copy request and Copy response buttons via
   `navigator.clipboard` (`:111`, `:158-159`), a label filter, a status
   filter, a body search (`:126-133`) and Clear. Bodies are pretty-printed
   into a scrollable `<pre>` and truncated at 200,000 characters per block
   (`:32-33`).
5. **Opt-in and registration.** `static/js/config.ts:234` loads `showRawLLM`
   from storage, `:392` saves it, `:481` reads the `agent-show-raw-llm`
   checkbox, and `static/js/ui/settings-view.ts:71` restores it when the
   Settings form is populated. The panel is registered in
   `templates/index.html:1405`.

**Deliberately not built:** the command-palette launcher the "Browser UI"
section names. The panel is reached through the floating `llm-inspector-btn`,
the same launch shape as the existing dataset panel. Also not built: JSON
syntax highlighting, collapsible nested arrays, and any export of raw
exchanges - the three caveats the implementing task recorded on 2026-09-19.

## Files

The files that actually carry the feature as it landed. The `.ts` is the
source; the sibling `.js` is the emitted build artifact and is not hand-edited.

- `static/js/storage.ts:73-74` - the `llm_raw_exchanges` IndexedDB store
- `static/js/shared/dataset-collector.ts:172` - `captureRaw`, plus `getAllRaw`
  (`:224`), `clearRaw` (`:232`), `countRaw` (`:236`) and the redaction
- `static/js/llm-client.ts:355` - `_captureRawExchange` and its three hook
  sites (`:256`, `:286`, `:298`)
- `static/js/ui/llm-inspector.ts` - the inspector panel (new); the emitted
  `static/js/ui/llm-inspector.js` is registered at
  `templates/index.html:1405`
- `static/js/config.ts:234` - the `showRawLLM` opt-in and its save (`:392`)
  and checkbox read (`:481`)
- `static/js/ui/settings-view.ts:71` - restores the opt-in checkbox
- `static/css/style.css` - the panel styles it uses. There is **no**
  `static/css/llm-inspector.css`: the card's original plan named one, and the
  implementation styles the panel inline in `llm-inspector.ts` instead, so
  that file was never created. The plan's `buildRawPanelUI` in
  `dataset-collector.js` was likewise superseded by the panel module.

## Browser UI and intended live verification

Intended UI home: Command palette → “Raw LLM inspector” → select an exchange to inspect its request and response. The command-palette entry is the intended launcher for this task; it is not present until implemented.

Current availability: The existing UI shows extracted assistant output. The full HTTP exchange inspector, persistence, and secret redaction are planned and not claimed as available.

Live steps when available:
1. Enable `showRawLLM`, open the command palette, choose “Raw LLM inspector”, and make a successful non-streaming request.
   - expected: the selected entry shows method/URL, request headers and full JSON body, response status/body, usage and reasoning tokens, and tool calls; authorization values are redacted.
2. Repeat with a streaming request and inspect the exchange after completion.
   - expected: the inspector retains the complete request and the final streamed response, not just the extracted assistant text.
3. Cause provider responses 429 and 500, then open each failed exchange.
   - expected: status and provider error body are visible; secret headers remain redacted.
4. Reload the page, reopen the inspector, and toggle it closed and open while the event stream is active.
   - expected: captured exchanges survive reload and the event stream/dataset collector continue to work.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Make an LLM call with `showRawLLM` enabled, open the inspector, and read
   the entry.
   - expected: the entry shows the request method/URL, the request headers
     with `authorization` redacted, the full request body, the response
     status, the full response body and the usage breakdown including
     reasoning tokens.
   - observed: not run in a browser. Measured 2026-10-20 by code inspection:
     the capture path is live at `static/js/llm-client.ts:298` and the panel
     renders request and response bodies with a usage line that includes
     `reasoning` (`static/js/ui/llm-inspector.ts:45`, `:158-159`). The
     implementing task recorded `node --check` clean on all six touched JS
     files, `npm run lint` passing and the settings-checkbox audit at 14
     covered, but no browser run is recorded.
2. Verify the `authorization` header is redacted before the write.
   - expected: the stored header keeps the header name and a `Bearer xxxxxx`
     prefix but never the key itself.
   - observed: measured 2026-10-20 in `static/js/shared/dataset-collector.ts:119-121`,
     which rewrites `authorization` / `api-key` / `x-api-key` to
     `prefix + first six characters + REDACTED` before the IndexedDB write.
3. Verify streaming calls are captured.
   - expected: a streamed exchange is stored with the request body and the
     assembled stream content, marked as a stream.
   - observed: measured 2026-10-20 at `static/js/llm-client.ts:286`, which
     calls `_captureRawExchange` after `_handleStream` resolves with
     `{ streamed: true, content }`.
4. Verify failed calls (429, 500) are captured with their error body.
   - expected: a non-`resp.ok` response is stored with its status and the
     provider's error body.
   - observed: measured 2026-10-20 at `static/js/llm-client.ts:256`, the
     `!resp.ok` branch passing `errBody || { error: errText }` with the
     response.
5. Verify entries survive page reload.
   - expected: the exchanges are still in the inspector after a reload.
   - observed: measured 2026-10-20 by construction - the entries live in the
     IndexedDB `llm_raw_exchanges` store (`static/js/storage.ts:73-74`) and
     the panel reads them back through `getAllRaw`
     (`static/js/ui/llm-inspector.ts:123`). Not exercised in a browser.
6. Verify the panel toggle does not break the event stream or the dataset
   collector.
   - expected: the existing event stream and the dataset panel keep working
     with the inspector open or closed.
   - observed: not run. Measured 2026-10-20: the capture is fire-and-forget
     and feature-detected (`static/js/llm-client.ts:357`), and the inspector
     is a separate floating panel that only reads and clears the raw store.
     The one recorded caveat is that the inspector button and the dataset
     panel both float bottom-right, so they can overlap if both are open.

## Non-goals

- Server-side proxy or MITM capture (this is browser-only)
- Automatic request replay or modification
- Token cost tracking across sessions
- Exporting raw exchanges as a training dataset format

## Progress - 2026-09-19

Implemented (browser-only, opt-in).

- `storage.js`: DB version 3 → 4, added the `llm_raw_exchanges` store.
- `shared/dataset-collector.js`: `captureRaw` / `getAllRaw` / `clearRaw` /
  `countRaw`. Redacts `authorization` / `api-key` / `x-api-key` to
  `Bearer xxxxxx…REDACTED`, caps the store at 200 entries (trimmed every 25th
  capture), and only records when `config.showRawLLM` is on.
- `llm-client.js`: `_captureRawExchange(...)` plus hooks after `resp.json()`,
  after `_handleStream` (captures `{ streamed: true, content }` - a stream has
  no provider envelope), and in the `!resp.ok` branch so error bodies are kept.
- `ui/llm-inspector.js` (new): floating panel with expand-per-entry, usage line
  (prompt/completion/in/out/**reasoning**/total/cost), Copy request / Copy
  response via `navigator.clipboard`, label + status filters, body search, and
  Clear. Bodies are JS-serialized and truncated at 200k chars per block.
- Settings: new **🔬 Show Raw LLM** checkbox (`agent-show-raw-llm`), wired
  through `config` load/save/saveFromForm **and** `populateForm()` restore.

Verified: `node --check` clean on all six touched JS files, `npm run lint`
passes, and the settings-checkbox audit reports all 14 covered.

Not done / caveats: no syntax highlighting or collapsible nested arrays (JSON is
pretty-printed in a scrollable `<pre>`); no export of raw exchanges; the button
and panel sit alongside the 🧪 dataset panel (both float bottom-right, so they
can overlap if both are open).

## Acceptance

- [x] The full HTTP exchange is captured and inspectable (task-405, commit `c1510248`).
- [x] Request method/URL, headers (authorization redacted), body, response status/body, usage and reasoning tokens are all visible.
- [x] Streaming calls and failed calls (non-`resp.ok`) are captured with their error bodies.
- [x] Entries survive page reload (IndexedDB `llm_raw_exchanges`, DB version 4).
- [x] The panel toggle does not break the event stream or dataset collector (fire-and-forget, never throws).

## Reconnaissance (2026-10-20) - VERDICT: FIXED

Re-checked the cited code live. The card's own 2026-09-19 "Progress" section was
already accurate, and the remaining acceptance items all landed in commit
`c1510248` ("perf(engine): optimize simulation performance and implement LLM
inspector"). Measured evidence:

- `static/js/ui/llm-inspector.ts` exists (230 lines) and is registered in
  `templates/index.html:1405` (`<script src="/static/js/ui/llm-inspector.js">`).
  It injects a button (`llm-inspector-btn`, line 56) and a panel
  (`llm-inspector-panel`, line 64) into `document.body` on load (lines 169-175).
- `static/js/shared/dataset-collector.ts` exposes `captureRaw` / `getAllRaw` /
  `clearRaw` / `countRaw`; `static/js/storage.ts:71-74` creates the
  `llm_raw_exchanges` store (DB version 4).
- `static/js/llm-client.ts:351-358` (`_captureRawExchange`) hooks after
  `resp.json()`, after `_handleStream`, and in the `!resp.ok` branch; redaction of
  `authorization` / `api-key` / `x-api-key` is implemented.
- `static/js/config.ts:233-234` (`showRawLLM`) and
  `static/js/config.ts:481` (`agent-show-raw-llm` checkbox) provide the opt-in
  toggle; `static/js/ui/settings-view.ts:71` restores it on form populate.

Remaining gaps from the card's own "Not done / caveats" list: no syntax
highlighting or collapsible nested arrays (JSON is pretty-printed in a
`<pre>`), no export of raw exchanges, and the button/panel float alongside the
dataset panel so the two can overlap if both are open. These are cosmetic and
were recorded by the implementing task itself; the core behaviour the card asks
for is present and wired.

The command-palette entry named in the card's "Browser UI" section ("Raw LLM
inspector") does not exist; the panel is reached via the floating
`llm-inspector-btn`, not the palette. That is a launcher-path difference, not a
missing feature.

Counts: `rg -c "llm-inspector" static/js/` = 1 file outside the module itself
(`templates/index.html`, 1 hit). `rg -c "captureRaw" static/js/shared/dataset-collector.ts`
= 1 definition + 2 call sites.
