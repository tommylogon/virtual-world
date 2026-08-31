/**
 * LLMClient — OpenAI-compatible API calls with streaming support
 * Handles URL normalization, auth, retry logic, streaming, and error handling.
 */
class LLMClient {
    constructor() {
        this.apiKey = '';
        this.apiBase = 'http://localhost:1234/v1';
        this.model = 'qwen3.5-0.8b';
        this.provider = 'openai';  // Provider type (openai, lmstudio, openrouter, etc.)
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
     *  options.label — human name for this call shown on the raw-LLM chips
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

        // Store last messages for clipboard export
        this._lastMessages = messages;

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
            try { est = Math.round(messages.reduce((n, m) => n + (m.content || '').length, 0) / 4); } catch (e) {}
            VW.events.logRawLLMRequest(label, messages, est);
        }

        const maxRetries = 3;
        let lastError = null;

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const requestBody = isResponses
                    ? this._buildResponsesBody(messages, { model, temperature, streaming, maxTokens: options.max_tokens })
                    : (() => {
                        const body = { model, messages, temperature: parseFloat(temperature) || 0.7 };
                        if (streaming) body.stream = true;
                        if (options.max_tokens) body.max_tokens = options.max_tokens;
                        if (options.tools && Array.isArray(options.tools)) {
                            body.tools = options.tools;
                            if (options.tool_choice) body.tool_choice = options.tool_choice;
                        }
                        // Thinking mode (DeepSeek reasoning models): extra_body + reasoning_effort.
                        // When OFF we send explicit disables instead of omitting the param —
                        // providers often default reasoning models to thinking ON, so omitting it
                        // would silently re-enable thinking. DeepSeek's native toggle plus
                        // OpenRouter/OpenAI's unified `reasoning.exclude` (supported on all models,
                        // so no risk of rejection by non-reasoning backends) both fire.
                        // Qwen 3.5 in LM Studio ignores all disable flags; the only reliable
                        // workaround is a trailing empty assistant message, which forces the
                        // model to skip the  block and emit content directly.
                        // Gated by `suppressLocalThinking` so it only fires when opted in.
                        if (this.thinking) {
                            body.reasoning_effort = this.thinkingEffort || 'high';
                            body.extra_body = { thinking: { type: 'enabled' } };
                        } else {
                            body.extra_body = { thinking: { type: 'disabled' } };
                            body.reasoning = { exclude: true };
                            body.enable_thinking = false;
                            if (this.suppressLocalThinking) body.messages.push({ role: 'assistant', content: ' ' });
                        }
                        return body;
                    })();

                const headers = { 'Content-Type': 'application/json' };
                if (this.apiKey && this.apiKey !== 'not-needed' && this.apiKey !== 'none') {
                    headers['Authorization'] = 'Bearer ' + this.apiKey;
                }
                const resp = await fetch(base + (isResponses ? '/responses' : '/chat/completions'), {
                    method: 'POST',
                    headers,
                    body: JSON.stringify(requestBody), signal
                });

                if (!resp.ok) {
                    let errText = '';
                    try { const err = await resp.json(); errText = err.error?.message || JSON.stringify(err); }
                    catch (e) { errText = await resp.text(); }
                    if ((resp.status === 429 || resp.status >= 500) && attempt < maxRetries) {
                        const delay = Math.pow(2, attempt - 1) * 1000;
                        if (VW?.events) VW.events.log(`⏱️ LLM retry ${attempt}/${maxRetries} after ${resp.status}...`, 'system-msg');
                        await new Promise(r => setTimeout(r, delay)); continue;
                    }
                    throw new Error(`HTTP ${resp.status}: ${errText}`);
                }

                if (streaming) return await this._handleStream(resp, format, options.onChunk, label);
                const completion = await resp.json();
                if (completion?.error) throw new Error(completion.error.message || JSON.stringify(completion.error));
                const content = isResponses
                    ? this._extractResponsesContent(completion)
                    : this._extractChatCompletionContent(completion);
                const tool_calls = completion?.choices?.[0]?.message?.tool_calls || null;
                this._logAssistantResponse(label, content || (tool_calls ? `[tool_calls: ${tool_calls.length}]` : ''));
                if (options.withTools || options.tools) {
                    return { content, tool_calls };
                }
                return content;

            } catch (e) {
                if (e.name === 'AbortError') return null;
                lastError = e;
                if (attempt < maxRetries && (e.message.includes('Failed to fetch') || e.message.includes('NetworkError'))) {
                    const delay = Math.pow(2, attempt - 1) * 1000;
                    if (VW?.events) VW.events.log(`⏱️ LLM retry ${attempt}/${maxRetries} after network error...`, 'system-msg');
                    await new Promise(r => setTimeout(r, delay)); continue;
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

    getLastPrompt() {
        if (!this._lastMessages) return '';
        return this._lastMessages.map(m => {
            const role = m.role || 'user';
            const content = m.content || '';
            return `=== ${role.toUpperCase()} ===\n${content}`;
        }).join('\n\n');
    }

    /**
     * Resolve which API format to use for requests.
     * auto currently routes to chat-completions (DeepSeek v4-pro only works on chat-completions
     * until early Aug 2026; the Responses API only supports deepseek-v4-flash). Manual opt-in to
     * 'responses' activates the new path. Reserved for future smart routing.
     */
    _resolveFormat() {
        if (this.apiFormat === 'responses') return 'responses';
        return 'chat-completions';
    }

    /**
     * Translate chat-completions effort levels (low/high/xhigh/max) to Responses API
     * levels (low/medium/high). One-way and lossy: xhigh/max collapse to high.
     */
    _translateEffort(effort) {
        if (effort === 'xhigh' || effort === 'max') return 'high';
        return effort || 'high';
    }

    /** Strip provider wrappers; never return chain-of-thought reasoning text. */
    _normalizeAssistantText(raw) {
        if (typeof extractAssistantText === 'function') return extractAssistantText(raw);
        return String(raw || '').trim();
    }

    _extractChatCompletionContent(completion) {
        const msg = completion?.choices?.[0]?.message;
        if (!msg) return '';
        return this._normalizeAssistantText(msg.content || '');
    }

    _logAssistantResponse(label, content) {
        const text = this._normalizeAssistantText(content);
        if (!text || !VW?.events?.logRawLLMResponse) return;
        VW.events.logRawLLMResponse(label || 'LLM', text);
    }

    /** Build a Responses API request body from chat-style messages. */
    _buildResponsesBody(messages, opts) {
        const systemMessage = messages.find(m => m.role === 'system');
        const body = {
            model: opts.model,
            input: messages
                .filter(m => m !== systemMessage)
                .map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content || '' }))
                .filter(m => m.content),
            temperature: parseFloat(opts.temperature) || 0.7
        };
        if (systemMessage?.content) body.instructions = systemMessage.content;
        if (opts.streaming) body.stream = true;
        if (opts.maxTokens) body.max_output_tokens = opts.maxTokens;
        if (this.thinking) body.reasoning = { effort: this._translateEffort(this.thinkingEffort) };
        else body.reasoning = { exclude: true }
        return body;
    }

    /**
     * Extract text content from a non-stream Responses API response.
     * Prefers top-level output_text (DeepSeek), falls back to concatenating
     * output[] message items (LM Studio), then empty string.
     */
    _extractResponsesContent(completion) {
        if (completion?.output_text) return completion.output_text;
        if (Array.isArray(completion?.output)) {
            return completion.output
                .filter(item => item.type === 'message')
                .map(item => Array.isArray(item.content)
                    ? item.content.map(c => c.text || '').join('')
                    : (item.content || ''))
                .join('');
        }
        return '';
    }

    /** Handle streaming response — OpenAI SSE + LM Studio formats (chat-completions and responses) */
    async _handleStream(resp, format, onChunk, label) {
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '', fullContent = '', currentEvent = '';
        const isResponses = format === 'responses';
        const yieldToBrowser = () => new Promise(r => setTimeout(r, 0));

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;
                if (trimmed.startsWith('event:')) { currentEvent = trimmed.slice(6).trim(); continue; }
                if (!trimmed.startsWith('data:')) continue;
                const data = trimmed.slice(5).trim();
                if (data === '[DONE]' || currentEvent === 'chat.end') continue;
                // Responses API has no [DONE] — terminate on response.completed / response.failed
                if (isResponses && (currentEvent === 'response.completed' || currentEvent === 'response.failed')) {
                    return fullContent;
                }
                try {
                    const parsed = JSON.parse(data);
                    let content;
                    if (isResponses) {
                        if (parsed?.type === 'response.completed' || parsed?.type === 'response.failed') return fullContent;
                        content = parsed?.delta || parsed?.output_text || '';
                    } else {
                        // Content tokens only — ignore reasoning/thinking deltas (Nemotron, DeepSeek, etc.)
                        content = parsed.choices?.[0]?.delta?.content
                            || parsed.choices?.[0]?.message?.content
                            || parsed.content
                            || '';
                    }
                    if (content) { fullContent += content; if (onChunk) onChunk(content); await yieldToBrowser(); }
                } catch (e) {}
            }
        }
        fullContent = this._normalizeAssistantText(fullContent);
        if (VW?.events?.logRawLLMResponse && fullContent && !onChunk) {
            this._logAssistantResponse(label, fullContent);
        }
        return fullContent;
    }

    async fetchModels(apiBase, apiKey) {
        const base = LLMClient.normalizeBase(apiBase || this.apiBase);
        if (base.toLowerCase().includes('deepseek')) return null;
        const isLocal = base.includes('localhost') || base.includes('127.0.0.1');
        if (!apiKey && !isLocal) return null;
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
                if (data.data && Array.isArray(data.data)) return data.data.map(m => m.id || m.name || m).filter(Boolean).sort();
                if (Array.isArray(data)) return data.map(m => m.id || m.name || m).filter(Boolean).sort();
            }
        } catch (e) {}
        return null;
    }

    async embeddings(input) {
        if (!input) return null;
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
            if (!resp.ok) return null;
            const data = await resp.json();
            return data.data?.[0]?.embedding || null;
        } catch (e) { return null; }
    }

    static getFallbackModels(apiBase) {
        const base = (apiBase || '').toLowerCase();
        if (base.includes('openai')) return ['gpt-4.1-mini', 'gpt-4o', 'gpt-4o-mini', 'o1', 'o3-mini'];
        if (base.includes('deepseek')) return ['deepseek-v4-flash', 'deepseek-chat', 'deepseek-reasoner'];
        if (base.includes('groq')) return ['llama3-70b-8192', 'llama3-8b-8192', 'mixtral-8x7b-32768', 'gemma2-9b-it'];
        if (base.includes('openrouter')) return ['openai/gpt-4o', 'anthropic/claude-3.5-sonnet', 'google/gemini-2.0-flash-001', 'meta-llama/llama-3.3-70b-instruct', 'deepseek/deepseek-chat', 'mistralai/mistral-7b-instruct'];
        if (base.includes('127.0.0.1') || base.includes('localhost')) return ['local-model'];
        if (base.includes('anthropic')) return ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229'];
        if (base.includes('googleapis') || base.includes('gemini')) return ['gemini-2.0-flash', 'gemini-pro'];
        if (base.includes('mistral')) return ['mistral-small-latest', 'mistral-medium-latest'];
        return [];
    }
}

const llmClient = new LLMClient();