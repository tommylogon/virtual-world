/**
 * stream-raw-llm.js — collapsed LLM payload chips + parse-error inspection
 *
 * task-340: request/response payloads now render as COLLAPSED chips
 * (click to expand) with an estimated token meter, so ordering matters less —
 * the outcome is always readable above a one-line chip.
 * Also tracks consecutive parse errors and offers a payload export when a
 * streak forms. Extracted from event-stream.js; loaded BEFORE it.
 */
class StreamRawLLM {
    constructor(bus) {
        this._bus = bus;
        this._rawResponses = [];
        this._rawSeq = 0;
        this.TOKEN_WARN = 7000;
    }

    /** Estimated token count for a messages array (~chars/4 heuristic). */
    static estimateTokens(messages) {
        try {
            return Math.round(messages.reduce((n, m) => n + (m.content || '').length, 0) / 4);
        } catch (e) { return 0; }
    }

    _chipBubble(tick, actorLabel, icon, labelText, contentHtmlBuilder, areaName) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble msg-bubble-rawllm';
        if (!config.filterRawLLM) bubble.style.display = 'none';
        bubble.setAttribute('data-actor', actorLabel);
        bubble.setAttribute('data-tick', tick);
        bubble.setAttribute('data-type', 'rawllm');
        bubble.setAttribute('data-stream-area', areaName || '');
        const header = document.createElement('div');
        header.className = 'rawllm-chip-header';
        window.Lit.render(window.Lit.html`
            <span class="bubble-icon">${icon}</span>
            <span class="bubble-tick">[${this._bus._nextLineLabel()}]</span>
            <span class="bubble-actor bubble-rawllm-actor">${labelText}</span>
            <span class="rawllm-toggle">▸</span>`, header);
        const body = document.createElement('pre');
        body.className = 'rawllm-chip-body';
        body.style.display = 'none';
        header.addEventListener('click', () => {
            const showing = body.style.display !== 'none';
            body.style.display = showing ? 'none' : 'block';
            header.querySelector('.rawllm-toggle').textContent = showing ? '▸' : '▾';
        });
        contentHtmlBuilder(body);
        bubble.append(header, body);
        this._bus._appendBubble(streamEl, bubble);
    }

    /** Log raw LLM request — collapsed chip with token estimate. */
    logRequest(phaseName, messages, estTokens) {
        const tick = VW?.state?.tick || 0;
        const tokens = estTokens != null ? estTokens : StreamRawLLM.estimateTokens(messages);
        const warn = tokens >= this.TOKEN_WARN;
        const tokSpan = window.Lit.html`<span class=${'tok-meter' + (warn ? ' warn' : '')} title=${warn ? 'Near the context ceiling — history pruning imminent' : 'Estimated tokens'}>~${(tokens / 1000).toFixed(1)}k tok${warn ? ' ⚠' : ''}</span>`;
        // Only attach the recall note when THIS call's messages actually recall
        // (contains the `=== I REMEMBER ===` block). Otherwise a still-fresh
        // _lastRecallStats from an earlier phase (e.g. the prior react call)
        // would falsely claim this LLM call recalled memories.
        const recall = (window._lastRecallStats && (Date.now() - (window._lastRecallStats.at || 0)) < 30000)
            ? window._lastRecallStats : null;
        const thisCallRecalls = recall && messages.some(m => /=== I REMEMBER ===/.test(String(m.content || '')));
        this._chipBubble(
            tick, 'LLM', '📤',
            window.Lit.html`LLM → ${phaseName} ${tokSpan}${thisCallRecalls ? window.Lit.html` <span class="recall-note">recalled: ${recall.count} memories${recall.semantic ? ` (${recall.semantic} semantic)` : ''}</span>` : ''}`,
            (body) => {
                // Body is PURELY the prompt text (for display). The retrieval
                // "why" is NOT included here — it lives on the separate always-
                // visible stream line, so it can never be mistaken for prompt text.
                body.textContent = messages.map(m => `${m.role}: ${m.content}`).join('\n\n---\n\n');
            },
            ''
        );
    }

    /** Log raw LLM response with explicit label — collapsed chip. */
    logResponse(label, content) {
        const tick = VW?.state?.tick || 0;
        const respArea = (label && !label.includes('.') && !label.includes('/'))
            ? (worldState.players?.[label]?.current_area || null) : null;
        this._chipBubble(
            tick, label, '🤖',
            window.Lit.html`${label} <span class="tok-meter">~${Math.round((content || '').length / 4)} tok</span>`,
            (body) => { body.textContent = String(content || ''); },
            respArea
        );
    }

    /** Log raw LLM response — content only, or (label, content) for model-tagged rows */
    log(contentOrLabel, optionalContent) {
        if (optionalContent !== undefined) { this.logResponse(contentOrLabel || 'LLM', optionalContent); return; }
        this.logResponse('LLM', contentOrLabel);
    }

    storeRawResponse(charName, phase, raw) {
        const seq = ++this._rawSeq;
        this._rawResponses.push({ seq, charName, phase: phase || '?', raw: String(raw || ''), at: Date.now() });
        if (this._rawResponses.length > 20) this._rawResponses.shift();
        return seq;
    }

    getRawResponse(seq) {
        return this._rawResponses.find(r => r.seq === seq);
    }

    /**
     * Log a clickable parse-error bubble revealing the raw response, and track
     * streaks: every 4th consecutive error for the same actor+phase emits a
     * summary row with a one-click payload export.
     */
    logParseError(charName, phase, errMsg, raw) {
        const seq = this.storeRawResponse(charName, phase, raw);
        this.emitStreakCheck(charName, phase);
        this._bus.emit('log', { text: errMsg, className: 'error-msg' });
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        this._bus._cards.close();
        const tick = VW?.state?.tick || 0;
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble msg-bubble-error parse-error-bubble';
        bubble.setAttribute('data-actor', charName);
        bubble.setAttribute('data-tick', tick);
        bubble.setAttribute('data-type', 'error');
        bubble.setAttribute('data-stream-area', worldState.players?.[charName]?.current_area || '');
        bubble.title = `${this._bus.tickToRelative(tick)}`;
        bubble.style.cursor = 'pointer';
        const err = this._bus._escapeHtml(errMsg || 'parse error');
        window.Lit.render(window.Lit.html`
<span class="bubble-icon">⚠️</span><span class="bubble-tick">[${this._bus._nextLineLabel()}]</span> <span class="bubble-actor bubble-error-actor">${charName}</span> <span class="bubble-text bubble-error-text">parse error: ${phase ? this._bus._escapeHtml(phase) + ' · ' : ''}${window.Lit.unsafeHTML(err)} <span style="color:var(--accent);text-decoration:underline;font-size:10px;">🔍 view raw response</span></span><div class="parse-raw" style="display:none;margin-top:6px;max-height:220px;overflow:auto;font-family:var(--font-mono);font-size:10px;color:var(--text-dim);white-space:pre-wrap;border-top:1px solid var(--border);padding-top:4px;"></div>`, bubble);
        bubble.addEventListener('click', () => {
            const rawBox = bubble.querySelector('.parse-raw');
            if (!rawBox) return;
            const showing = rawBox.style.display !== 'none';
            if (!showing) {
                const stored = this.getRawResponse(seq);
                rawBox.textContent = stored ? stored.raw : '';
                rawBox.style.display = 'block';
                bubble.setAttribute('data-expanded', 'true');
            } else {
                rawBox.style.display = 'none';
                bubble.removeAttribute('data-expanded');
            }
        });
        this._bus._appendBubble(streamEl, bubble);
    }

    emitStreakCheck(charName, phase) {
        const s = this._streak || (this._streak = { count: 0, actor: null, phase: null, at: 0 });
        const now = Date.now();
        if (s.actor !== charName || s.phase !== phase || now - s.at > 10 * 60 * 1000) {
            s.count = 0; s.actor = charName; s.phase = phase;
        }
        s.count += 1;
        s.at = now;
        if (s.count > 0 && s.count % 4 === 0) this._emitStreakSummary(charName, phase, s.count);
    }

    _emitStreakSummary(charName, phase, count) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        this._bus._cards.close();
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble msg-bubble-crisis parse-streak';
        bubble.setAttribute('data-actor', charName);
        bubble.setAttribute('data-type', 'crisis');
        bubble.setAttribute('data-stream-area', worldState.players?.[charName]?.current_area || '');
        window.Lit.render(window.Lit.html`
            <span class="bubble-icon">⚠️</span>
            <span class="bubble-text">${count} consecutive parse errors · ${this._bus._escapeHtml(phase)} · ${charName}
                <span class="export-link" title="Download the raw payloads for a bug report">export payloads</span></span>`, bubble);
        bubble.querySelector('.export-link').addEventListener('click', (e) => {
            e.stopPropagation();
            const payloads = this._rawResponses.filter(r => r.charName === charName && r.phase === phase).slice(-count);
            const text = payloads.map(p => `=== seq ${p.seq} · ${p.charName} · ${p.phase} · ${new Date(p.at).toISOString()} ===\n${p.raw}`).join('\n\n');
            const blob = new Blob([text], { type: 'text/plain' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `parse_errors_${charName}_${phase}.txt`;
            a.click();
            URL.revokeObjectURL(a.href);
        });
        streamEl.appendChild(bubble);
        this._bus._trimStream(streamEl);
        if (this._bus.autoScroll) streamEl.scrollTop = streamEl.scrollHeight;
    }
}
