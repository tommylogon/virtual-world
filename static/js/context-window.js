/**
 * ContextWindowManager — LLM context pruning and token management
 */
class ContextWindowManager {
    constructor(options = {}) {
        this.maxTokens = options.maxTokens || 4000;
        this.maxMessages = options.maxMessages || 20;
        this.recentTurnCount = options.recentTurnCount || 6;
        this.criticalContextRetention = options.criticalContextRetention || true;
        this.charsPerToken = options.charsPerToken || 4;
        this.messageMetadata = new Map();
        this.totalTokens = 0;
    }

    estimateTokens(message) {
        if (!message || !message.content) return 0;
        let contentLength = 0;
        if (typeof message.content === 'string') {
            contentLength = message.content.length;
        } else if (Array.isArray(message.content)) {
            for (const part of message.content) {
                if (part.type === 'text' && part.text) contentLength += part.text.length;
            }
        }
        return Math.ceil(contentLength / this.charsPerToken) + 10;
    }

    addMessage(message, metadata = {}) {
        const tokens = this.estimateTokens(message);
        this.totalTokens += tokens;
        const index = this.messageMetadata.size;
        this.messageMetadata.set(index, {
            tokens, importance: metadata.importance || 0,
            type: metadata.type || 'general', summary: metadata.summary || null,
            keepAlways: metadata.keepAlways || false
        });
        return index;
    }

    isOverLimit() {
        return this.totalTokens > this.maxTokens || this.messageMetadata.size > this.maxMessages;
    }

    prune(messages) {
        if (!this.isOverLimit() || messages.length === 0) return messages;
        const keepIndices = new Set();
        if (messages[0]?.role === 'system') keepIndices.add(0);
        let recentCount = 0;
        for (let i = messages.length - 1; i >= 0 && recentCount < this.recentTurnCount * 3; i--) {
            keepIndices.add(i); recentCount++;
            if (messages[i].role === 'assistant' && messages[i].tool_calls) {
                for (let j = i + 1; j < Math.min(i + 5, messages.length); j++) {
                    if (messages[j].role === 'tool') keepIndices.add(j);
                    else if (messages[j].role !== 'tool') break;
                }
            }
        }
        for (let i = 0; i < messages.length; i++) {
            const meta = this.messageMetadata.get(i);
            if (meta && (meta.importance >= 2 || meta.keepAlways)) keepIndices.add(i);
        }
        const sorted = Array.from(keepIndices).sort((a, b) => a - b);
        const pruned = [];
        if (sorted.length > 0 && sorted[0] > 0) {
            pruned.push({ role: 'system', content: `[Summary: ${sorted[0]} earlier turns omitted.]` });
        }
        for (const idx of sorted) { if (idx < messages.length) pruned.push(messages[idx]); }
        this.messageMetadata.clear(); this.totalTokens = 0;
        for (let i = 0; i < pruned.length; i++) {
            const tokens = this.estimateTokens(pruned[i]);
            this.totalTokens += tokens;
            this.messageMetadata.set(i, { tokens, importance: pruned[i].role === 'system' ? 2 : 0, type: pruned[i].role, keepAlways: pruned[i].role === 'system' });
        }
        return pruned;
    }

    reset() { this.messageMetadata.clear(); this.totalTokens = 0; }

    getStats() {
        return {
            totalMessages: this.messageMetadata.size, totalTokens: this.totalTokens,
            maxTokens: this.maxTokens, utilization: ((this.totalTokens / this.maxTokens) * 100).toFixed(1) + '%',
            isOverLimit: this.isOverLimit()
        };
    }
}