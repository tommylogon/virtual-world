---
type: bug
status: review
area: bugs
priority: high
wiki: "[[AI & Narration/LLM Providers]]"
related: [task-933]
---

# bug-583: LM Studio Native API (/api/v1/chat) fails with HTTP 400 on non-reasoning models and returns empty string when streaming is enabled

**Filed:** 2026-11-09
**Related:** task-933

<!-- deps:start -->
**Related:** [[task-933-character-controller-selector-and-director-turn-composer]]
<!-- deps:end -->

## What

When `LLMClient` (`static/js/llm-client.ts`) is configured with `apiFormat: 'lmstudio'` (hitting LM Studio's Native `/api/v1/chat` endpoint), two bugs broke LLM calls in the browser:
1. `_buildLMStudioBody()` unconditionally sent `reasoning: 'off' | 'on'`. For non-reasoning models (such as `arrowcanaria-llama-8b-sft-v0.1`), LM Studio rejects the request with `HTTP 400: Model '...' does not expose reasoning configuration`.
2. `_buildLMStudioBody()` builds a non-streaming JSON request (`stream` is not set), so `/api/v1/chat` returns a single JSON object (`{ output: [{ type: 'message', content: '...' }] }`). However, `LLMClient.chat()` checked `if (streaming)` (`line 489`) without `!isLMStudio`, routing the plain JSON response into the SSE stream reader (`_handleStream`), which found zero `data:` lines and returned `""`.

## Why

1. LM Studio's `/api/v1/chat` endpoint only accepts the `reasoning` parameter on models that declare a reasoning template.
2. The `isLMStudio` branch in `chat()` was only wired into the non-streaming `resp.json()` path (`line 515`), while `if (streaming)` intercepted responses whenever `config.streaming` was `true`.

## How

1. In `static/js/llm-client.ts`:
   - Added `_lmStudioReasoningUnsupported` detection on `HTTP 400` responses matching `/does not expose reasoning|reasoning configuration/i`, omitting `body.reasoning` in `_buildLMStudioBody()` and retrying immediately in the same call.
   - Changed `if (streaming)` at `line 489` to `if (streaming && !isLMStudio)` so `/api/v1/chat` JSON responses parse via `_extractLMStudioContent(completion)`.

## Steps to verify

1. In the browser on `http://localhost:4444` with `apiFormat: 'lmstudio'`, `streaming: true`, and `model: 'arrowcanaria-llama-8b-sft-v0.1'`, click **🎬 Ask Director** in the Human Turn Composer.
   - expected: `LLMClient.chat()` automatically drops `reasoning` on the 400 response, parses the `/api/v1/chat` JSON completion, and populates the composer fields.

## Acceptance

- [x] `LLMClient` automatically omits `reasoning` on `/api/v1/chat` when a model does not expose reasoning configuration.
- [x] `LLMClient` parses `/api/v1/chat` JSON responses when `config.streaming === true`.
- [x] Zero em-dashes in code or task files.

## Files

- `static/js/llm-client.ts`
