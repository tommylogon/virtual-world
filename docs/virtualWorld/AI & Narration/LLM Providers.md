# LLM Providers

VirtualWorld uses an OpenAI-compatible API client (`LLMClient`) to power agent behavior, narration, memory reflection, plan generation, and AI-assisted content creation. The system supports multiple providers through a unified interface.

## Configuration

Settings are managed by `ConfigManager` in `static/js/config.js` and persisted to IndexedDB via the `storage` abstraction.

### ConfigManager Properties (config.js:6-58)

| Property | Storage Key | Default | Description |
|----------|-------------|---------|-------------|
| `apiKey` | `api_key` | `''` | API key for the provider |
| `apiBase` | `api_base` | `https://api.openai.com/v1` | Base URL for API |
| `model` | `model` | `gpt-4.1-mini` | Model identifier |
| `provider` | `provider` | `openai` | Provider name |
| `temperature` | `temperature` | `0.7` | LLM temperature |
| `maxTokens` | `max_tokens` | `512` | Max tokens per response |
| `rpmLimit` | `rpm_limit` | `0` | Rate limit (requests/min) |
| `tpmLimit` | `tpm_limit` | `0` | Token rate limit |
| `streaming` | `streaming` | `false` | Enable streaming responses |
| `reactiveMode` | `reactive_mode` | `true` | thought→act→react phases |
| `showLogs` | `show_logs` | `false` | Log LLM requests |

### Provider Types

The `_getDefaultProfiles()` method in `config.js:275` defines built-in profiles:

```javascript
'OpenAI (GPT-4.1-mini)': { apiBase: 'https://api.openai.com/v1', model: 'gpt-4.1-mini' },
'OpenAI (GPT-4o)':       { apiBase: 'https://api.openai.com/v1', model: 'gpt-4o' },
'LM Studio (Local)':     { apiBase: 'http://localhost:1234/v1', model: '' },
'DeepSeek':              { apiBase: 'https://api.deepseek.com/v1', model: 'deepseek-v4-flash' },
'Groq':                  { apiBase: 'https://api.groq.com/openai/v1', model: 'llama3-70b-8192' },
```

### API Key and Base URL

API keys are configured in the Settings UI and stored in browser IndexedDB. They are **never sent to the backend** — all LLM calls are made **directly from the browser frontend** via `fetch()`. There are no server-side API keys or proxy routes.

The `LLMClient` sets the auth header on every request:
```javascript
headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + this.apiKey }
```

For local providers (LM Studio, Ollama), the UI auto-detects `localhost` or `127.0.0.1` in the base URL and shows a text input field instead of a model dropdown (`settings-view.js:133`). The API key check is also bypassed for local endpoints:

```javascript
// agent-engine.js:105
if (!config.apiKey && !config.apiBase?.includes('localhost') && !config.apiBase?.includes('127.0.0.1'))
```

## How LLM Calls Are Made

All calls go through `LLMClient` in `static/js/llm-client.js`, a singleton (`window.llmClient`).

### Chat Completions (`chat()`, line 35)

```javascript
async chat(messages, options = {})
```

Parameters:
- `messages` — Array of `{role, content}` objects (OpenAI format)
- `options.model` — Model override
- `options.temperature` — Temperature override
- `options.streaming` — Enable SSE streaming
- `options.tools` — Array of OpenAI tool definitions (functions with JSON schemas)
- `options.tool_choice` — Optional tool choice mode (e.g. `'auto'`, `'none'`, `'required'`)
- `options.withTools` — If true, returns structured `{ content, tool_calls }`
- `options.onChunk` — Per-call chunk callback `(chunk) => void`, invoked as streamed content arrives
- `options.signal` — AbortController signal for cancellation

The method sends `POST {base}/chat/completions` with standard OpenAI-compatible JSON body.

### Tool Calling (`chatWithTools()`, line 160)

```javascript
async chatWithTools(messages, options = {})
```

Convenience helper for tool-calling agents (such as the Natural-Language Editor). Forces `streaming: false` and `withTools: true`, returning structured `{ content, tool_calls }` where `tool_calls` contains the parsed OpenAI function calling requests.

### Manual Mode (line 50)

When `this._manualMode` is enabled (via the Settings "Manual Mode" checkbox), the LLMClient returns a pre-injected `_manualResponse` instead of making API calls. This lets users manually craft agent responses for debugging or story purposes.

### Streaming (line 109)

The `_handleStream(resp, format, onChunk)` method parses SSE (Server-Sent Events) in OpenAI and LM Studio formats. It reads the response body as a stream, accumulating content chunks and calling the per-call `onChunk` callback for real-time UI updates.

The chunk callback is **per-call**, passed via `chat()`'s `options.onChunk`. There is no shared `_onChunk` instance field anymore, so concurrent `chat()` calls each get their own stream destination without clobbering each other. The caller owns a unique `streamId` and drives the matching `events.startStreaming(streamId)` / `events.appendStream(streamId, chunk)` / `events.finishStreaming(streamId)` lifecycle (see `agent-engine.js` `_callLLMMessages`).

### Model List Fetching (`fetchModels()`, line 139)

Queries `{base}/models` to list available models. Returns `null` for DeepSeek (known incompatibility). Supports both `{data: [...]}` (OpenAI format) and bare array responses.

### Fallback Models (`getFallbackModels()`, line 176)

Returns a hardcoded list of suggested models per provider:

| Provider base URL | Models |
|-------------------|--------|
| `openai` | `gpt-4.1-mini`, `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini` |
| `deepseek` | `deepseek-v4-flash`, `deepseek-chat`, `deepseek-reasoner` |
| `groq` | `llama3-70b-8192`, `llama3-8b-8192`, `mixtral-8x7b-32768`, `gemma2-9b-it` |
| `openrouter` | `openai/gpt-4o`, `anthropic/claude-3.5-sonnet`, `google/gemini-2.0-flash-001`, `meta-llama/llama-3.3-70b-instruct`, `deepseek/deepseek-chat` |
| `localhost` / `127.0.0.1` | `local-model` |

### Embeddings (`embeddings()`, line 167)

Generates text embeddings via `{base}/embeddings`. Only enabled for OpenAI and local endpoints. Uses the model name configured in **Settings → Embedding** (`config.embeddingModel`, defaults to `text-embedding-3-small`). Returns the embedding vector or `null` on failure.

The embedding source is configurable in the Settings panel:
- **Local (sentence-transformers)**: Uses a built-in `all-MiniLM-L6-v2` model loaded on demand — no API key needed. Configured as the default.
- **API (LLM Provider)**: Sends to your LLM provider's `/embeddings` endpoint with the configured model name.

## Rate Limiting

Implemented in `static/js/agent/rate-limiter.js` as the `RateLimiter` class.

### `waitMs()` (line 24)

Calculates how long to wait before the next API call based on `config.rpmLimit` (requests per minute). Maintains a sliding window of timestamps — if the window is full, returns the milliseconds until the oldest timestamp falls out of the 60-second window.

### `getCooldown()` (line 40)

Returns remaining cooldown time in seconds. Used by the UI to display rate limit status.

### Usage in AgentEngine

The rate limiter is checked at the start of each `agent-engine.js` step (line 75):

```javascript
const waitMs = this._rateLimiter.waitMs();
if (waitMs > 0) {
    // Display countdown to user
    for (let r = sec; r > 0; r--) { ... }
}
```

## Error Handling & Fallbacks

### Retry Logic (llm-client.js:60-96)

`chat()` implements a 3-retry strategy with exponential backoff:

1. **HTTP 429 or 5xx**: Retries with `2^(attempt-1) * 1000ms` delay (1s, 2s, 4s)
2. **Network errors** (`Failed to fetch`, `NetworkError`): Same exponential backoff
3. **AbortError**: Returns `null` immediately (cancellation)
4. **Other errors**: Throws immediately after max retries

Errors are logged to the event stream via `VW.events.log()`.

### Agent Engine Recovery

If an LLM call returns `null` (failure after retries), the agent engine:
1. Logs `"❌ LLM call failed for {charName}"` to the event stream
2. Sets `config.running = false` (stops the agent loop)
3. Displays `"LLM Error - Stopped"` status in the UI

This prevents infinite retry loops and makes failures visible to the user.

### Health Check

The server exposes `/api/health` (`routes/health.py:41`) which reports `llm_enabled` status from `app.config['LLM_ENABLED']`.

## Related tasks

- [[dev_tasks/review/testing/task-88-llm_logging|task-88: LLM logging]]
