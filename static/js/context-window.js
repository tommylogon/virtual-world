/**
 * ContextWindowManager — LLM context pruning and token management
 *
 * @module context-window — context pruning and token budgeting
 * @contributes ContextWindowManager: token accounting and history pruning for chat contexts
 * @powers keeping prompts within the model window instead of overflowing
 * @relates used by the agent/LLM call paths that carry conversation history
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
class ContextWindowManager {
    constructor(options = {}) {
        this.maxTokens = options.maxTokens || 4000;
        this.maxMessages = options.maxMessages || 20;
        this.recentTurnCount = options.recentTurnCount || 6;
        this.criticalContextRetention = options.criticalContextRetention || true;
        this.maxCriticalMessages = options.maxCriticalMessages || 10;
        this.charsPerToken = options.charsPerToken || 4;
        // Metadata is keyed by the message OBJECT, never by array position:
        // prune() returns a NEW array, so index-keyed metadata desyncs from the
        // caller's live log as soon as a window is applied.
        this._meta = new WeakMap();
        this.totalTokens = 0;
        this.totalMessages = 0;
    }

    estimateTokens(message) {
        if (!message) return 0;
        let contentLength = 0;
        if (typeof message.content === 'string') {
            contentLength = message.content.length;
        } else if (Array.isArray(message.content)) {
            for (const part of message.content) {
                if (part.type === 'text' && part.text) contentLength += part.text.length;
            }
        }
        // Tool calls carry real prompt weight with empty content, so count them
        // or a tool-calling loop looks free and its budget never trips.
        if (Array.isArray(message.tool_calls) && message.tool_calls.length) {
            try { contentLength += JSON.stringify(message.tool_calls).length; } catch (e) { /* ignore */ }
        }
        return Math.ceil(contentLength / this.charsPerToken) + 10;
    }

    addMessage(message, metadata = {}) {
        if (!message || typeof message !== 'object') return this.totalMessages;
        const known = this._meta.has(message);
        if (!known) {
            this.totalTokens += this.estimateTokens(message);
            this.totalMessages++;
        }
        this._meta.set(message, {
            tokens: this.estimateTokens(message),
            importance: metadata.importance || 0,
            type: metadata.type || 'general',
            summary: metadata.summary || null,
            keepAlways: metadata.keepAlways || false
        });
        return this.totalMessages;
    }

    /** Measure a real message array. Authoritative when one is supplied. */
    _measure(messages) {
        let tokens = 0;
        for (const m of messages) tokens += this.estimateTokens(m);
        return { tokens, count: messages.length };
    }

    /**
     * Over budget? Pass the array you are about to send to get an authoritative
     * answer; call with no argument to use the accumulated totals.
     */
    isOverLimit(messages = null) {
        if (Array.isArray(messages)) {
            const { tokens, count } = this._measure(messages);
            return tokens > this.maxTokens || count > this.maxMessages;
        }
        return this.totalTokens > this.maxTokens || this.totalMessages > this.maxMessages;
    }

    _metaFor(message) {
        return (message && typeof message === 'object' && this._meta.get(message)) || null;
    }

    prune(messages) {
        if (!Array.isArray(messages) || messages.length === 0) return messages;
        // Measure the array we were actually given. Measuring stored counters
        // here made prune() disable itself: it reset the counters it then
        // guarded on, so the next call returned the whole transcript.
        if (!this.isOverLimit(messages)) return messages;

        const keepIndices = new Set();
        if (messages[0]?.role === 'system') keepIndices.add(0);

        let recentCount = 0;
        for (let i = messages.length - 1; i >= 0 && recentCount < this.recentTurnCount * 3; i--) {
            keepIndices.add(i); recentCount++;
            if (messages[i].role === 'assistant' && messages[i].tool_calls) {
                for (let j = i + 1; j < messages.length; j++) {
                    if (messages[j].role === 'tool') keepIndices.add(j);
                    else break;
                }
            }
        }

        // Critical retention is BOUNDED and newest-first. Unbounded, it kept
        // every tool-calling assistant forever, which is the whole transcript.
        if (this.criticalContextRetention) {
            let keptCritical = 0;
            for (let i = messages.length - 1; i >= 0 && keptCritical < this.maxCriticalMessages; i--) {
                const meta = this._metaFor(messages[i]);
                if (meta && (meta.importance >= 2 || meta.keepAlways)) {
                    keepIndices.add(i);
                    keptCritical++;
                }
            }
        }

        // Post-validation: ensure atomic assistant-tool pairings
        for (let i = 0; i < messages.length; i++) {
            if (messages[i].role === 'tool' && keepIndices.has(i)) {
                for (let j = i - 1; j >= 0; j--) {
                    if (messages[j].role === 'assistant' && messages[j].tool_calls) {
                        keepIndices.add(j);
                        break;
                    }
                    if (messages[j].role !== 'tool') break;
                }
            }
        }
        for (let i = 0; i < messages.length; i++) {
            if (messages[i].role === 'assistant' && messages[i].tool_calls && keepIndices.has(i)) {
                for (let j = i + 1; j < messages.length; j++) {
                    if (messages[j].role === 'tool') keepIndices.add(j);
                    else break;
                }
            }
        }
        const sorted = Array.from(keepIndices).sort((a, b) => a - b);
        // The leading system prompt is always kept, so gating the marker on
        // "index 0 was dropped" meant it was never emitted and the model lost
        // context with no signal. Emit it whenever anything was omitted.
        const leadingSystemKept = sorted.length > 0 && sorted[0] === 0;
        const omitted = messages.length - sorted.length;
        const pruned = [];
        if (leadingSystemKept) pruned.push(messages[0]);
        if (omitted > 0) {
            pruned.push({ role: 'system', content: `[Summary: ${omitted} earlier message(s) omitted from this window.]` });
        }
        for (const idx of sorted) {
            if (leadingSystemKept && idx === 0) continue;
            if (idx < messages.length) pruned.push(messages[idx]);
        }

        // Report the window for getStats(). The caller's own log is untouched.
        this.totalTokens = this._measure(pruned).tokens;
        this.totalMessages = pruned.length;
        return pruned;
    }

    reset() { this._meta = new WeakMap(); this.totalTokens = 0; this.totalMessages = 0; }

    getStats() {
        return {
            totalMessages: this.totalMessages, totalTokens: this.totalTokens,
            maxTokens: this.maxTokens, maxMessages: this.maxMessages,
            utilization: ((this.totalTokens / this.maxTokens) * 100).toFixed(1) + '%',
            isOverLimit: this.isOverLimit()
        };
    }
}

if (typeof window !== 'undefined') {
    window.ContextWindowManager = ContextWindowManager;
}
