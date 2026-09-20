---
type: task
status: review
area: ui
priority: medium
---

# task-405: LLM raw request/response inspector

**Filed:** 2026-09-17  
**Depends on:** none

## Goal

Show the complete raw HTTP exchange with the LLM provider in the UI, not just
the extracted assistant text. Users need to verify what is actually sent and
received — headers, status, full JSON body, usage, reasoning tokens, tool
calls, errors — for debugging providers like OpenRouter, LM Studio, Ollama,
OpenAI, etc.

## Current state

`static/js/shared/dataset-collector.js` already captures `{ messages, response,
label, model, parsed_ok, repaired }` to IndexedDB, and a floating panel exports
JSONL for fine-tuning. But `response` is only the extracted text content. The
full HTTP response object — status, headers, raw JSON body, usage breakdown,
reasoning/output token counts — is discarded after `_captureDataset` reads
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

## Files

- `static/js/shared/dataset-collector.js` — add `captureRaw`, `getAllRaw`,
  `clearRaw`, `buildRawPanelUI`
- `static/js/llm-client.js` — call `_captureRawExchange` after every response
- `static/js/ui/llm-inspector.js` (new) — inspector panel UI
- `static/css/llm-inspector.css` (new) — syntax highlighting, layout
- `templates/index.html` or command palette — entry point for the inspector

## Verification

- Make an LLM call with `showRawLLM` enabled
- Open inspector, verify request headers + body + response status + full body
  + usage stats are visible
- Verify `authorization` header is redacted
- Verify streaming calls are captured
- Verify failed calls (429, 500) are captured with error body
- Verify entries survive page reload
- Verify panel toggle doesn't break existing event stream or dataset collector

## Non-goals

- Server-side proxy or MITM capture (this is browser-only)
- Automatic request replay or modification
- Token cost tracking across sessions
- Exporting raw exchanges as a training dataset format

## Progress — 2026-09-19

Implemented (browser-only, opt-in).

- `storage.js`: DB version 3 → 4, added the `llm_raw_exchanges` store.
- `shared/dataset-collector.js`: `captureRaw` / `getAllRaw` / `clearRaw` /
  `countRaw`. Redacts `authorization` / `api-key` / `x-api-key` to
  `Bearer xxxxxx…REDACTED`, caps the store at 200 entries (trimmed every 25th
  capture), and only records when `config.showRawLLM` is on.
- `llm-client.js`: `_captureRawExchange(...)` plus hooks after `resp.json()`,
  after `_handleStream` (captures `{ streamed: true, content }` — a stream has
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
