"use strict";
/**
 * LLMClient - OpenAI-compatible API calls with streaming support
 * Handles URL normalization, auth, retry logic, streaming, and error handling.
 *
 * @module llm-client - the provider client (Chat Completions / Responses)
 * @contributes LLMClient.chat/chatWithTools: retries, streaming, JSON repair, thinking/reasoning controls, truncation escalation, raw-capture hook
 * @powers all character and narration LLM calls, plus the 🔬 LLM inspector's raw exchanges
 * @relates configured from config.toLLMConfig(); feeds dataset-collector.captureRaw
 * @docs docs/virtualWorld/AI & Narration/LLM Providers.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// Shared by editor and standalone pages. The LLM client logs into VW when the
// editor namespace is available, but communication pages also use this client.
window.VW = window.VW || {};
/** How many times a length-stopped response is re-requested with a larger
 *  budget before the caller is told the answer is genuinely incomplete. */
const MAX_TRUNCATION_RETRIES = 3;
/** Hard ceiling for that escalation - well past any local model's practical
 *  output length, so this only stops a pathological loop. */
const MAX_TOKEN_CEILING = 32768;
class LLMClient {
    constructor() {
        this.apiKey = '';
        this.apiBase = 'http://localhost:1234/v1';
        this.model = 'qwen3.5-0.8b';
        this.provider = 'openai'; // Provider type (openai, lmstudio, openrouter, etc.)
        this.temperature = 0.7;
        this.streaming = false;
        this.showLogs = false;
        this.thinking = false;
        this.thinkingEffort = 'high';
        this.suppressLocalThinking = false;
        // API format: auto | chat-completions | responses.
        // auto currently routes to chat-completions (safest); manual opt-in to responses required.
        this.apiFormat = 'auto';
        this._lastMessages = null;
        this._manualResponse = null;
        this._manualMode = false;
        // Actor + request id of the call in flight, so the response chip
        // correlates with its request chip (and with the right character).
        this._callMeta = null;
        // Structured output bookkeeping: log once per schema when attached,
        // and detect providers that silently IGNORE the schema (LM Studio
        // with sub-7B models does this - no error, model just emits free JSON).
        this._structuredLogged = new Set();
        this._schemaIgnoredWarned = new Set();
    }
    static normalizeBase(url) {
        return (url || '').replace(/\/+$/, '');
    }
    configure(config) {
        this.apiKey = config.apiKey || this.apiKey;
        this.apiBase = config.apiBase || this.apiBase;
        this.model = config.model || this.model;
        this.provider = config.provider || this.provider;
        this.temperature = config.temperature !== undefined ? config.temperature : this.temperature;
        this.streaming = config.streaming !== undefined ? config.streaming : this.streaming;
        this.showLogs = config.showLogs !== undefined ? config.showLogs : this.showLogs;
        this.thinking = config.thinking !== undefined ? config.thinking : this.thinking;
        this.thinkingEffort = config.thinkingEffort || this.thinkingEffort;
        this.suppressLocalThinking = config.suppressLocalThinking !== undefined ? config.suppressLocalThinking : this.suppressLocalThinking;
        this.apiFormat = config.apiFormat || this.apiFormat;
    }
    /** Chat completion with retry: 3 attempts, 1s/2s/4s backoff on 429/5xx/network errors.
     *  options.label - human name for this call shown on the raw-LLM chips
     *  (e.g. 'think-decide', 'result-reaction', 'plan', 'reflect'); defaults
     *  to the model id. */
    async chat(messages, options = {}) {
        const model = options.model || this.model;
        const label = options.label || model;
        const temperature = options.temperature !== undefined ? options.temperature : this.temperature;
        const streaming = options.streaming !== undefined ? options.streaming : this.streaming;
        const signal = options.signal || null;
        const base = LLMClient.normalizeBase(this.apiBase);
        const format = this._resolveFormat();
        const isResponses = format === 'responses';
        const isLMStudio = format === 'lmstudio';
        // Store last messages for clipboard export
        this._lastMessages = messages;
        // Trace metadata for this call: who it is for, and a correlation id
        // shared by the request chip and the response chip.
        this._callMeta = { actor: options.actor, requestId: options.requestId };
        // Manual mode: return injected response instead of calling API
        // Response stays active until replaced or manual mode turned off
        if (this._manualMode && this._manualResponse !== null) {
            VW?.events?.log('✋ Using manual response instead of API call', 'system-msg');
            return this._manualResponse;
        }
        // Log full request to event stream for all LLM calls
        if (VW?.events?.logRawLLMRequest && !this._manualMode) {
            // token estimate computed here so the chip can show a budget meter
            let est = 0;
            try {
                est = Math.round(messages.reduce((n, m) => n + (m.content || '').length, 0) / 4);
            }
            catch (e) { }
            VW.events.logRawLLMRequest(label, messages, est, { actor: options.actor, requestId: options.requestId });
        }
        const maxRetries = 3;
        let lastError = null;
        const startedAt = Date.now();
        // Truncation escalation. `max_tokens` is a HARD cap at the provider, and
        // until now the stop reason was discarded - every caller received a
        // silently cut-off string with no way to tell it from a complete one.
        // A truncated answer is worse than a slow one (a half-written JSON plan
        // silently becomes no plan), so a length stop re-requests with a larger
        // budget instead of returning the fragment.
        // Centralized token budgeting:
        const configuredMax = window?.config?.maxTokens
            ? parseInt(String(window.config?.maxTokens), 10)
            : 2048;
        const requestedCap = options.max_tokens || configuredMax || 2048;
        // Reasoning tokens count towards completion tokens in modern reasoning models.
        // A tiny cap like 560 or 400 will starve the model before it emits any visible tokens.
        // Guarantee a reasoning headroom floor of at least 4096 tokens when thinking is active.
        const isThinkingActive = (!this.thinking ? false : (this.thinkingEffort !== 'none')) || (!!options.reasoningEffort && options.reasoningEffort !== 'none');
        const minThinkingHeadroom = 4096;
        const baseMaxTokens = (isThinkingActive && !options.max_tokens) ? Math.max(requestedCap, minThinkingHeadroom) : requestedCap;
        let effectiveMaxTokens = baseMaxTokens;
        let truncationRetries = 0;
        // Transport retries and truncation retries are SEPARATE budgets. Sharing
        // one counter means three length stops exhaust the network budget and
        // the call throws "failed after retries" having never failed at
        // transport at all - which is how the first version of this behaved.
        let attempt = 0;
        const maxIterations = maxRetries + MAX_TRUNCATION_RETRIES;
        for (let iteration = 0; iteration < maxIterations; iteration++) {
            // Structured output (task: structured output): response_format is
            // requested per-call via options.responseFormat, gated by the
            // config toggle, never mixed with tool calls, and auto-disabled
            // for the session if the provider rejects the parameter.
            const responseFormat = this._effectiveResponseFormat(options);
            if (responseFormat) {
                const key = responseFormat.type === 'json_schema' ? responseFormat.json_schema.name : 'json_object';
                this._structuredLogged.add(key);
            }
            try {
                const requestBody = isLMStudio
                    ? this._buildLMStudioBody(messages, { model, temperature, maxTokens: effectiveMaxTokens })
                    : (isResponses
                        ? this._buildResponsesBody(messages, { model, temperature, streaming, maxTokens: effectiveMaxTokens, tools: options.tools, tool_choice: options.tool_choice, responseFormat })
                        : (() => {
                            const body = { model, messages, temperature: parseFloat(temperature) || 0.7 };
                            if (streaming) {
                                body.stream = true;
                                body.stream_options = { include_usage: true };
                            }
                            if (effectiveMaxTokens)
                                body.max_tokens = effectiveMaxTokens;
                            if (responseFormat)
                                body.response_format = responseFormat;
                            if (options.tools && Array.isArray(options.tools)) {
                                body.tools = options.tools;
                                if (options.tool_choice)
                                    body.tool_choice = options.tool_choice;
                            }
                            // Thinking mode (DeepSeek reasoning models): extra_body + reasoning_effort.
                            // DeepSeek defaults thinking ON at effort `high`, so we must send an
                            // explicit disable when it is off - omitting the parameter silently
                            // re-enables high-effort reasoning on every call.
                            // `effort: "none"` is the disable spelling for providers that key
                            // thinking off the effort value, so treat it as OFF here too rather
                            // than sending an invalid `reasoning_effort: "none"`.
                            // OpenRouter/OpenAI's unified `reasoning.exclude` is supported on all
                            // models, so it can't be rejected by a non-reasoning backend.
                            // Qwen 3.5 in LM Studio ignores all disable flags; the only reliable
                            // workaround is a trailing empty assistant message, which forces the
                            // model to skip its reasoning block and emit content directly.
                            // Gated by `suppressLocalThinking` so it only fires when opted in.
                            const thinkingOff = (!this.thinking || this.thinkingEffort === 'none') && (!options.reasoningEffort || options.reasoningEffort === 'none');
                            if (!thinkingOff) {
                                // For mechanical or structured phases like 'plan', scale effort to 'low' unless caller explicitly asks for more.
                                const phaseEffort = options.reasoningEffort || (options.label === 'plan' ? 'low' : (this.thinkingEffort || 'medium'));
                                body.reasoning_effort = phaseEffort;
                                body.extra_body = { thinking: { type: 'enabled' } };
                                body.reasoning = {
                                    effort: phaseEffort,
                                    max_tokens: options.reasoningMaxTokens || (options.label === 'plan' ? 1024 : 2048)
                                };
                            }
                            else {
                                body.extra_body = { thinking: { type: 'disabled' } };
                                body.reasoning = { exclude: true };
                                body.enable_thinking = false;
                                if (this.suppressLocalThinking)
                                    body.messages.push({ role: 'assistant', content: ' ' });
                            }
                            return body;
                        })());
                const headers = { 'Content-Type': 'application/json' };
                if (this.apiKey && this.apiKey !== 'not-needed' && this.apiKey !== 'none') {
                    headers['Authorization'] = 'Bearer ' + this.apiKey;
                }
                let endpointUrl = base + (isResponses ? '/responses' : '/chat/completions');
                if (isLMStudio) {
                    const hostBase = base.replace(/\/v1\/?$/, '');
                    endpointUrl = hostBase + '/api/v1/chat';
                }
                const resp = await fetch(endpointUrl, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify(requestBody), signal
                });
                if (!resp.ok) {
                    let errText = '';
                    let errBody = null;
                    try {
                        errBody = await resp.json();
                        errText = errBody.error?.message || JSON.stringify(errBody);
                    }
                    catch (e) {
                        errText = await resp.text();
                        errBody = { text: errText };
                    }
                    // Capture provider error shapes (400/429/500) too (task-405).
                    this._captureRawExchange(label, requestBody, errBody || { error: errText }, resp, startedAt, headers);
                    // Provider rejected structured output (unknown param, json
                    // word missing, schema unsupported) - drop it for the rest
                    // of the session and retry immediately without burning the
                    // remaining attempts on the same 400.
                    if (responseFormat && (resp.status === 400 || resp.status === 422)
                        && /response_format|json_schema|json object|structured|word ['"]?json['"]?/i.test(errText)) {
                        this._structuredUnsupported = true;
                        if (VW?.events)
                            VW.events.log('⚠️ Provider rejected structured output - falling back to plain prompts for this session.', 'system-msg');
                        attempt++;
                        continue;
                    }
                    attempt++;
                    if ((resp.status === 429 || resp.status >= 500) && attempt < maxRetries) {
                        const retryAfter = resp.headers?.get?.('Retry-After');
                        let delay = Math.pow(2, attempt - 1) * 1000;
                        if (retryAfter) {
                            const parsed = parseFloat(retryAfter);
                            if (!isNaN(parsed) && parsed > 0) {
                                delay = Math.min(parsed * 1000, 30_000);
                            }
                        }
                        const waitSec = (delay / 1000).toFixed(1);
                        if (VW?.events)
                            VW.events.log(`LLM retry ${attempt}/${maxRetries} after ${resp.status} (waiting ${waitSec}s)...`, 'system-msg');
                        await new Promise(r => setTimeout(r, delay));
                        continue;
                    }
                    throw new Error(`HTTP ${resp.status}: ${errText}`);
                }
                if (streaming) {
                    const streamInfo = { truncated: false };
                    // A retry must not paint a SECOND stream over the partial
                    // text already on screen, so onChunk is suppressed once the
                    // retry budget is in play - the complete answer replaces it.
                    const chunkSink = truncationRetries > 0 ? undefined : options.onChunk;
                    const streamed = await this._handleStream(resp, format, chunkSink, label, messages, options, streamInfo, startedAt);
                    // A stream isn't reassembled into a provider envelope, so
                    // capture the request plus the assembled text (task-405).
                    this._captureRawExchange(label, requestBody, { streamed: true, content: streamed }, resp, startedAt, headers);
                    if (streamInfo.truncated && truncationRetries < MAX_TRUNCATION_RETRIES) {
                        truncationRetries++;
                        effectiveMaxTokens = this._nextTokenBudget(baseMaxTokens, truncationRetries);
                        VW?.events?.log(`✂️ ${label || 'LLM'} hit the token cap mid-stream - retrying with ${effectiveMaxTokens} tokens`, 'system-msg');
                        continue;
                    }
                    if (streamInfo.truncated)
                        this._warnTruncated(label, effectiveMaxTokens, streamed);
                    this._checkSchemaEnforcement(streamed, responseFormat);
                    return streamed;
                }
                const completion = await resp.json();
                this._captureRawExchange(label, requestBody, completion, resp, startedAt, headers);
                if (this._truncationReason(completion, isResponses, isLMStudio) && truncationRetries < MAX_TRUNCATION_RETRIES) {
                    truncationRetries++;
                    effectiveMaxTokens = this._nextTokenBudget(baseMaxTokens, truncationRetries);
                    VW?.events?.log(`✂️ ${label || 'LLM'} hit the token cap (${this._truncationReason(completion, isResponses, isLMStudio)}) - retrying with ${effectiveMaxTokens} tokens`, 'system-msg');
                    continue;
                }
                if (this._truncationReason(completion, isResponses, isLMStudio)) {
                    this._warnTruncated(label, effectiveMaxTokens, isLMStudio ? this._extractLMStudioContent(completion) : this._extractChatCompletionContent(completion));
                }
                if (completion?.error)
                    throw new Error(completion.error.message || JSON.stringify(completion.error));
                const content = isLMStudio
                    ? this._extractLMStudioContent(completion)
                    : (isResponses
                        ? this._extractResponsesContent(completion)
                        : this._extractChatCompletionContent(completion));
                this._checkSchemaEnforcement(content, responseFormat);
                const tool_calls = isResponses
                    ? this._extractResponsesToolCalls(completion)
                    // An empty array is truthy; normalise it to null so callers
                    // treat "no native tool calls" as absent. Some providers send
                    // `tool_calls: []` rather than omitting the field, which used
                    // to suppress the XML-in-content fallback in the agent loop.
                    : ((Array.isArray(completion?.choices?.[0]?.message?.tool_calls)
                        && completion.choices[0].message.tool_calls.length)
                        ? completion.choices[0].message.tool_calls
                        : null);
                const durationMs = startedAt ? (Date.now() - startedAt) : 0;
                const compTokens = completion?.usage?.completion_tokens || Math.round((content || '').length / 4);
                const tokPerSec = durationMs > 0 && compTokens > 0 ? (compTokens / (durationMs / 1000)) : undefined;
                const openrouterProvider = resp?.headers?.get?.('x-openrouter-provider') || (this.apiBase.includes('openrouter') ? 'OpenRouter' : '');
                const cost = completion?.usage?.total_cost || undefined;
                const responseMeta = {
                    actor: options.actor,
                    requestId: options.requestId,
                    phase: options.phase,
                    tokPerSec,
                    provider: openrouterProvider,
                    cost,
                    durationMs
                };
                this._logAssistantResponse(label, content || (tool_calls && tool_calls.length ? `[tool_calls: ${tool_calls.length}]` : ''), responseMeta);
                this._captureDataset(messages, content, label, options);
                if (options.withTools || options.tools) {
                    return { content, tool_calls };
                }
                return content;
            }
            catch (e) {
                if (e.name === 'AbortError')
                    return null;
                lastError = e;
                attempt++;
                if (attempt < maxRetries && (e.message.includes('Failed to fetch') || e.message.includes('NetworkError'))) {
                    const delay = Math.pow(2, attempt - 1) * 1000;
                    if (VW?.events)
                        VW.events.log(`⏱️ LLM retry ${attempt}/${maxRetries} after network error...`, 'system-msg');
                    await new Promise(r => setTimeout(r, delay));
                    continue;
                }
                throw e;
            }
        }
        throw lastError || new Error('LLM request failed after retries');
    }
    /** Chat completion helper for tool calling (forces non-streaming and returns { content, tool_calls }). */
    async chatWithTools(messages, options = {}) {
        return this.chat(messages, { ...options, streaming: false, withTools: true });
    }
    /**
     * Capture the full HTTP exchange for the LLM Inspector (task-405).
     * No-ops unless `config.showRawLLM` is on and the collector is loaded;
     * never throws and never affects the LLM call result.
     */
    _captureRawExchange(label, requestBody, body, resp, startedAt, requestHeaders) {
        try {
            if (typeof window === 'undefined' || !window.DatasetCollector?.captureRaw)
                return;
            if (typeof config !== 'undefined' && config && !config.showRawLLM)
                return;
            const responseHeaders = {};
            try {
                resp?.headers?.forEach?.((v, k) => { responseHeaders[k] = v; });
            }
            catch (e) { /* ignore */ }
            window.DatasetCollector.captureRaw({
                label,
                model: requestBody?.model || this.model,
                url: (resp && resp.url) || '',
                requestHeaders: requestHeaders || { 'content-type': 'application/json' },
                requestBody,
                status: resp?.status ?? null,
                statusText: resp?.statusText || '',
                responseHeaders,
                body,
                durationMs: startedAt ? (Date.now() - startedAt) : null,
            });
        }
        catch (e) { /* capture must never affect the call */ }
    }
    /**
     * Resolve the response_format to send for this call, or null when
     * structured output is off, unsupported, or mixed with tool calls
     * (many providers reject response_format together with tools).
     * @param {Object} options - chat() options, may carry responseFormat
     * @returns {Object|null} response_format payload or null
     */
    _effectiveResponseFormat(options) {
        if (!options.responseFormat)
            return null;
        if (options.tools && Array.isArray(options.tools))
            return null;
        if (this._structuredUnsupported)
            return null;
        if (typeof config !== 'undefined' && config && config.structuredOutput === false)
            return null;
        return options.responseFormat;
    }
    /**
     * Detect providers that silently IGNORE a strict json_schema (LM Studio
     * does this for models without grammar support - no error is raised, the
     * model just emits free JSON). Proof of non-enforcement: the response
     * parses as an object but contains keys the closed schema forbids.
     * Warns once per schema and disables structured output for the session,
     * since continuing would only burn request tokens on an ignored payload.
     */
    _checkSchemaEnforcement(content, responseFormat) {
        if (!responseFormat || responseFormat.type !== 'json_schema')
            return;
        const def = responseFormat.json_schema;
        if (this._schemaIgnoredWarned.has(def.name))
            return;
        let parsed;
        try {
            parsed = JSON.parse(String(content || '').replace(/^```(?:json)?\s*/i, '').replace(/\s*```\s*$/, ''));
        }
        catch (e) {
            return;
        } // parse failures are the repair path's job, not ours
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
            return;
        const allowed = def.schema && def.schema.properties;
        if (!allowed)
            return;
        const extras = Object.keys(parsed).filter(k => !(k in allowed));
        if (!extras.length)
            return;
        this._schemaIgnoredWarned.add(def.name);
        this._structuredUnsupported = true;
        if (VW?.events)
            VW.events.log(`⚠️ ${def.name}: provider ignored the JSON schema (unexpected keys: ${extras.join(', ')}) - the loaded model likely can't do structured output (LM Studio: models under 7B usually can't). Structured output disabled for this session.`, 'error-msg');
    }
    getLastPrompt() {
        if (!this._lastMessages)
            return '';
        return this._lastMessages.map(m => {
            const role = m.role || 'user';
            const content = m.content || '';
            return `=== ${role.toUpperCase()} ===\n${content}`;
        }).join('\n\n');
    }
    /**
     * Resolve which API format to use for requests.
     * auto currently routes to chat-completions (DeepSeek v4-pro only works on chat-completions
     * until early Aug 2026; the Responses API only supports the Flash model). Manual opt-in to
     * 'responses' activates the new path. Reserved for future smart routing.
     */
    _resolveFormat() {
        if (this.apiFormat === 'lmstudio')
            return 'lmstudio';
        if (this.apiFormat === 'responses')
            return 'responses';
        return 'chat-completions';
    }
    /** Strip provider wrappers; never return chain-of-thought reasoning text. */
    _normalizeAssistantText(raw) {
        if (typeof extractAssistantText === 'function')
            return extractAssistantText(raw);
        return String(raw || '').trim();
    }
    _extractChatCompletionContent(completion) {
        const msg = completion?.choices?.[0]?.message;
        if (!msg)
            return '';
        return this._normalizeAssistantText(msg.content || '');
    }
    _extractLMStudioContent(completion) {
        const outMsg = completion?.output?.find((o) => o.type === 'message') || completion?.output?.[0];
        const text = outMsg?.content || '';
        if (completion?.stats?.tokens_per_second) {
            const tps = Math.round(completion.stats.tokens_per_second * 10) / 10;
            const ttft = completion.stats.time_to_first_token_seconds ? ` · TTFT ${(completion.stats.time_to_first_token_seconds * 1000).toFixed(0)}ms` : '';
            if (VW?.events?.log && (typeof config === 'undefined' || config.showLogs)) {
                VW.events.log(`⚡ [LM Studio Native] ${tps} t/s${ttft}`, 'system-msg');
            }
        }
        return this._normalizeAssistantText(text);
    }
    /**
     * The provider's own signal that generation stopped AT the token cap.
     * Chat Completions reports `finish_reason: 'length'`; the Responses API
     * reports `incomplete_details.reason`. Returns null when the answer
     * finished on its own ('stop' / 'tool_calls' / no signal at all), so a
     * provider that omits the field never triggers a spurious retry.
     */
    _truncationReason(completion, isResponses, isLMStudio = false) {
        if (!completion || typeof completion !== 'object')
            return null;
        if (isLMStudio) {
            const reason = completion?.incomplete_details?.reason;
            if (reason === 'max_output_tokens' || reason === 'max_tokens')
                return reason;
            const total = completion?.stats?.total_output_tokens;
            if (total && completion?.max_output_tokens && total >= completion.max_output_tokens)
                return 'max_tokens';
            return null;
        }
        if (isResponses) {
            const reason = completion?.incomplete_details?.reason;
            if (reason === 'max_output_tokens' || reason === 'max_tokens')
                return reason;
            const status = completion?.status;
            return status === 'incomplete' ? (reason || 'incomplete') : null;
        }
        const finish = completion?.choices?.[0]?.finish_reason;
        return finish === 'length' ? 'length' : null;
    }
    /** Next budget for a truncation retry: double the caller's cap, or start
     *  from the hard default, and never climb past the model's ceiling. */
    _nextTokenBudget(current, retry) {
        const base = current && current > 0 ? current : 512;
        const doubled = base * Math.pow(2, retry);
        return Math.min(doubled, MAX_TOKEN_CEILING);
    }
    /** Last resort when even the ceiling truncates: say so loudly rather than
     *  handing a half-written answer to a parser as if it were complete. */
    _warnTruncated(label, budget, content) {
        if (!VW?.events?.log)
            return;
        const tail = String(content || '').slice(-60).replace(/\s+/g, ' ');
        VW.events.log(`✂️ ${label || 'LLM'} STILL truncated at ${budget || MAX_TOKEN_CEILING} tokens - the answer is incomplete. Raise Max Tokens in Settings.${tail ? ` …"${tail}"` : ''}`, 'system-msg');
    }
    _logAssistantResponse(label, content, meta) {
        const text = this._normalizeAssistantText(content);
        if (!text || !VW?.events?.logRawLLMResponse)
            return;
        // The streaming paths call this from inside the chunk reader, where
        // `options` is not in scope - the in-flight call's meta is the
        // fallback, so the response chip carries the same actor and
        // request id as the request chip.
        const effective = meta || this._callMeta || undefined;
        VW.events.logRawLLMResponse(label || 'LLM', text, effective);
    }
    /** Feed one completed request/response pair to the dataset collector.
     *  Never throws - capture is best-effort and must not affect gameplay. */
    _captureDataset(messages, content, label, options) {
        try {
            if (typeof DatasetCollector !== 'undefined' && DatasetCollector && content) {
                DatasetCollector.capture(messages, content, label, {
                    responseFormat: options && options.responseFormat ? options.responseFormat.type : null,
                });
            }
        }
        catch (e) { }
    }
    /** Build a Responses API request body from chat-style messages. */
    _buildResponsesBody(messages, opts) {
        const systemMessage = messages.find(m => m.role === 'system');
        const input = [];
        for (const m of messages) {
            if (m === systemMessage)
                continue;
            // Tool results must become function_call_output entries.
            if (m.role === 'tool') {
                if (m.tool_call_id)
                    input.push({ type: 'function_call_output', call_id: m.tool_call_id, output: String(m.content ?? '') });
                continue;
            }
            // Assistant tool calls become function_call entries; their text is dropped
            // (contains only the tool-call intent, and responses-api may reject free text
            // alongside a call).
            if (m.role === 'assistant' && Array.isArray(m.tool_calls) && m.tool_calls.length) {
                for (const tc of m.tool_calls) {
                    const args = typeof tc.function?.arguments === 'string'
                        ? tc.function.arguments
                        : JSON.stringify(tc.function?.arguments ?? {});
                    input.push({ type: 'function_call', call_id: tc.id, name: tc.function?.name, arguments: args });
                }
                continue;
            }
            if (m.content) {
                input.push({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content });
            }
        }
        const body = {
            model: opts.model,
            input,
            temperature: parseFloat(opts.temperature) || 0.7
        };
        if (systemMessage?.content)
            body.instructions = systemMessage.content;
        if (opts.streaming)
            body.stream = true;
        if (opts.maxTokens)
            body.max_output_tokens = opts.maxTokens;
        // Responses API uses a flat function tool shape:
        //   { type: 'function', name, description, parameters }
        // (chat-completions nests them:  { type:'function', function:{...} })
        if (opts.tools && Array.isArray(opts.tools)) {
            body.tools = opts.tools.map(t => {
                const fn = t.function || {};
                return { type: 'function', name: fn.name, description: fn.description, parameters: fn.parameters };
            });
            if (opts.tool_choice !== undefined)
                body.tool_choice = opts.tool_choice;
        }
        // Responses API carries structured output under text.format (flat shape).
        if (opts.responseFormat) {
            body.text = {
                format: opts.responseFormat.type === 'json_schema'
                    ? {
                        type: 'json_schema',
                        name: opts.responseFormat.json_schema.name,
                        strict: opts.responseFormat.json_schema.strict !== false,
                        schema: opts.responseFormat.json_schema.schema
                    }
                    : { type: 'json_object' }
            };
        }
        // Thinking OFF - or an explicit `none` effort - disables reasoning by
        // sending effort 'none'; otherwise the selected effort passes through.
        const thinkingOff = !this.thinking || this.thinkingEffort === 'none';
        body.reasoning = { effort: thinkingOff ? 'none' : (this.thinkingEffort || 'high') };
        return body;
    }
    /** Build an LM Studio Native API (/api/v1/chat) request body. */
    _buildLMStudioBody(messages, opts) {
        const systemMessage = messages.find(m => m.role === 'system');
        const inputMsgs = [];
        for (const m of messages) {
            if (m === systemMessage)
                continue;
            if (m.content) {
                if (m.role === 'user') {
                    inputMsgs.push(m.content);
                }
                else {
                    inputMsgs.push(`[${m.role}]: ${m.content}`);
                }
            }
        }
        const thinkingOff = !this.thinking || this.thinkingEffort === 'none';
        const body = {
            model: opts.model,
            input: inputMsgs.join('\n\n'),
            temperature: parseFloat(opts.temperature) || 0.7,
            reasoning: thinkingOff ? 'off' : 'on'
        };
        if (systemMessage?.content) {
            body.system_prompt = systemMessage.content;
        }
        if (opts.maxTokens) {
            body.max_output_tokens = opts.maxTokens;
        }
        return body;
    }
    /** Extract tool_calls from a Responses API completion (output[] entries of type 'function_call'). */
    _extractResponsesToolCalls(completion) {
        const output = Array.isArray(completion?.output) ? completion.output : [];
        const calls = output
            .filter((o) => o.type === 'function_call')
            .map((o) => ({
            id: o.call_id || o.id,
            type: 'function',
            function: { name: o.name, arguments: o.arguments || '{}' }
        }));
        return calls.length ? calls : null;
    }
    /**
     * Extract text content from a non-stream Responses API response.
     * Prefers top-level output_text (DeepSeek), falls back to concatenating
     * output[] message items (LM Studio), then empty string.
     */
    _extractResponsesContent(completion) {
        if (completion?.output_text)
            return completion.output_text;
        if (Array.isArray(completion?.output)) {
            return completion.output
                .filter((item) => item.type === 'message')
                .map((item) => Array.isArray(item.content)
                ? item.content.map((c) => c.text || '').join('')
                : (item.content || ''))
                .join('');
        }
        return '';
    }
    /** Handle streaming response - OpenAI SSE + LM Studio formats (chat-completions and responses) */
    async _handleStream(resp, format, onChunk, label, messages, options, info, startedAt) {
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '', fullContent = '', currentEvent = '';
        let streamUsage = null;
        let streamProvider = resp?.headers?.get?.('x-openrouter-provider') || (this.apiBase.includes('openrouter') ? 'OpenRouter' : '');
        let firstTokenAt = null;
        const isResponses = format === 'responses';
        const yieldToBrowser = () => new Promise(r => setTimeout(r, 0));
        const getStreamMeta = () => {
            const streamDur = startedAt ? (Date.now() - startedAt) : 0;
            const compTokens = streamUsage?.completion_tokens || Math.round(fullContent.length / 4);
            const tokPerSec = streamDur > 0 && compTokens > 0 ? (compTokens / (streamDur / 1000)) : undefined;
            const ttftMs = (firstTokenAt && startedAt) ? (firstTokenAt - startedAt) : undefined;
            const cost = streamUsage?.total_cost != null ? streamUsage.total_cost : streamUsage?.cost;
            return {
                actor: options?.actor,
                requestId: options?.requestId,
                phase: options?.phase,
                tokPerSec,
                ttftMs,
                provider: streamProvider || (this.apiBase.includes('openrouter') ? 'OpenRouter' : ''),
                cost,
                durationMs: streamDur
            };
        };
        while (true) {
            const { done, value } = await reader.read();
            if (done)
                break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed)
                    continue;
                if (trimmed.startsWith('event:')) {
                    currentEvent = trimmed.slice(6).trim();
                    continue;
                }
                if (!trimmed.startsWith('data:'))
                    continue;
                const data = trimmed.slice(5).trim();
                if (data === '[DONE]' || currentEvent === 'chat.end')
                    continue;
                // Responses API has no [DONE] - terminate on response.completed / response.failed
                if (isResponses && (currentEvent === 'response.completed' || currentEvent === 'response.failed')) {
                    // Some local providers emit NO delta chunks - the whole
                    // answer rides inside the final envelope as
                    // { response: { output: [{ content: [{ text }] }] } }.
                    // Pull it out so we don't return an empty string, and log
                    // it to the event stream exactly like the non-responses
                    // path does (task-396: without this, local Responses-API
                    // models never surface their output as a chip).
                    try {
                        const env = JSON.parse(data);
                        if (env && env.response) {
                            const full = this._extractResponsesContent(env.response);
                            if (full && !fullContent)
                                fullContent = full;
                        }
                    }
                    catch (e) { }
                    fullContent = this._normalizeAssistantText(fullContent);
                    if (VW?.events?.logRawLLMResponse && fullContent && !onChunk) {
                        this._logAssistantResponse(label, fullContent, getStreamMeta());
                    }
                    this._captureDataset(messages, fullContent, label, options);
                    return fullContent;
                }
                try {
                    const parsed = JSON.parse(data);
                    if (parsed?.usage)
                        streamUsage = parsed.usage;
                    if (parsed?.provider)
                        streamProvider = parsed.provider;
                    // A length stop arrives on the LAST chunk before [DONE], so
                    // the stream is only known to be cut off once it has ended.
                    if (info && this._truncationReason(parsed, isResponses))
                        info.truncated = true;
                    let content;
                    if (isResponses) {
                        if (parsed?.type === 'response.completed' || parsed?.type === 'response.failed') {
                            if (parsed.response) {
                                const full = this._extractResponsesContent(parsed.response);
                                if (full && !fullContent)
                                    fullContent = full;
                            }
                            fullContent = this._normalizeAssistantText(fullContent);
                            if (VW?.events?.logRawLLMResponse && fullContent && !onChunk) {
                                this._logAssistantResponse(label, fullContent, getStreamMeta());
                            }
                            this._captureDataset(messages, fullContent, label, options);
                            return fullContent;
                        }
                        content = parsed?.delta || parsed?.output_text || '';
                    }
                    else {
                        // Content tokens only - ignore reasoning/thinking deltas (Nemotron, DeepSeek, etc.)
                        content = parsed.choices?.[0]?.delta?.content
                            || parsed.choices?.[0]?.message?.content
                            || parsed.content
                            || '';
                    }
                    if (content) {
                        if (!firstTokenAt && startedAt)
                            firstTokenAt = Date.now();
                        fullContent += content;
                        if (onChunk)
                            onChunk(content);
                        await yieldToBrowser();
                    }
                }
                catch (e) { }
            }
        }
        fullContent = this._normalizeAssistantText(fullContent);
        if (VW?.events?.logRawLLMResponse && fullContent && !onChunk) {
            this._logAssistantResponse(label, fullContent, getStreamMeta());
        }
        this._captureDataset(messages, fullContent, label, options);
        return fullContent;
    }
    async fetchModels(apiBase, apiKey) {
        const base = LLMClient.normalizeBase(apiBase || this.apiBase);
        if (base.toLowerCase().includes('deepseek'))
            return null;
        const isLocal = base.includes('localhost') || base.includes('127.0.0.1');
        if (!apiKey && !isLocal)
            return null;
        try {
            const headers = { 'Content-Type': 'application/json' };
            if (apiKey && apiKey !== 'not-needed' && apiKey !== 'none') {
                headers['Authorization'] = 'Bearer ' + apiKey;
            }
            const resp = await fetch(base + '/models', {
                headers,
                signal: AbortSignal.timeout(5000)
            });
            if (resp.ok) {
                const data = await resp.json();
                if (data.data && Array.isArray(data.data))
                    return data.data.map((m) => m.id || m.name || m).filter(Boolean).sort();
                if (Array.isArray(data))
                    return data.map((m) => m.id || m.name || m).filter(Boolean).sort();
            }
            if (isLocal) {
                try {
                    const hostBase = base.replace(/\/v1\/?$/, '');
                    const nativeResp = await fetch(hostBase + '/api/v0/models', { headers, signal: AbortSignal.timeout(3000) });
                    if (nativeResp.ok) {
                        const data = await nativeResp.json();
                        if (data.data && Array.isArray(data.data))
                            return data.data.map((m) => m.id || m.name || m).filter(Boolean).sort();
                    }
                }
                catch (e) { }
            }
        }
        catch (e) { }
        return null;
    }
    async embeddings(input) {
        if (!input)
            return null;
        const base = (this.apiBase || '').toLowerCase();
        // Only OpenAI and LM Studio / local proxies support this embeddings API
        if (!base.includes('openai') && !base.includes('127.0.0.1') && !base.includes('localhost')) {
            return null;
        }
        try {
            const resp = await fetch(LLMClient.normalizeBase(this.apiBase) + '/embeddings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + this.apiKey },
                body: JSON.stringify({ model: config?.embeddingModel || 'text-embedding-3-small', input: input })
            });
            if (!resp.ok)
                return null;
            const data = await resp.json();
            return data.data?.[0]?.embedding || null;
        }
        catch (e) {
            return null;
        }
    }
    static getFallbackModels(apiBase) {
        const base = (apiBase || '').toLowerCase();
        if (base.includes('openai'))
            return ['gpt-4.1-mini', 'gpt-4o', 'gpt-4o-mini', 'o1', 'o3-mini'];
        if (base.includes('deepseek'))
            return ['deepseek-flash', 'deepseek-v4-pro'];
        if (base.includes('groq'))
            return ['llama3-70b-8192', 'llama3-8b-8192', 'mixtral-8x7b-32768', 'gemma2-9b-it'];
        if (base.includes('openrouter'))
            return ['openai/gpt-4o', 'anthropic/claude-3.5-sonnet', 'google/gemini-2.0-flash-001', 'meta-llama/llama-3.3-70b-instruct', 'deepseek/deepseek-chat', 'mistralai/mistral-7b-instruct'];
        if (base.includes('127.0.0.1') || base.includes('localhost'))
            return ['local-model'];
        if (base.includes('anthropic'))
            return ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229'];
        if (base.includes('googleapis') || base.includes('gemini'))
            return ['gemini-2.0-flash', 'gemini-pro'];
        if (base.includes('mistral'))
            return ['mistral-small-latest', 'mistral-medium-latest'];
        return [];
    }
}
// globals.d.ts already declares `llmClient: any` so every other module can reach
// this singleton without importing it, which rules out re-declaring the same
// `const` here. Publishing through `window` is equivalent for a classic script:
// a bare `llmClient` reference in another file resolves through the global
// object, exactly as it did when this was a top-level `const`.
window.llmClient = new LLMClient();
