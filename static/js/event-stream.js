/**
 * EventBus — Pub/sub event stream and terminal output
 *
 * task-340 (event stream v2): slimmed core with extracted collaborators in
 * static/js/stream/ (filters, turn cards, raw-LLM chips, persistence,
 * timeline scrubber). The bus remains the single public surface — every
 * legacy symbol still works. New in v2: collapsed LLM payload chips with
 * token meters, outcome-tinted results, phase pills, narration/reflection/
 * whisper/crisis/prune row kinds, area-transition dividers, time-gap rows,
 * turn-queue strip, timeline scrubber, stream search, and a story mode.
 */
const eventStreamHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

class EventBus {
    constructor() {
        this.MAX_LINES = 5000;
        this.autoScroll = true;
        this._subscribers = {};
        this._streamSpans = {};
        this._isStreaming = false;
        this._areaEventLog = {};
        this._characterState = {};
        this._characterAutonomy = {};
        this._knownActors = new Set();
        this._lineSeq = 0;
        this._streamMode = 'cards';
        this._lastGap = null;

        // v2 collaborators (loaded before this file)
        this._cards = new StreamTurnCards(this);
        this._filters = new StreamFilters(this);
        this._rawllm = new StreamRawLLM(this);
        this._persist = new StreamPersistence(this);
        this._scrubber = new StreamScrubber(this);
        this._controlMode = new StreamControlMode(this);

        let savedMode = 'cards';
        try { savedMode = localStorage.getItem('vw_stream_mode') || 'cards'; } catch (e) {}
        this.setStreamMode(savedMode);
    }

    /** Subscribe to event types */
    on(event, callback) {
        if (!this._subscribers[event]) this._subscribers[event] = [];
        this._subscribers[event].push(callback);
    }

    /** Emit an event */
    emit(event, data) {
        const subs = this._subscribers[event] || [];
        subs.forEach(cb => cb(data));
    }

    // --- Delegates to v2 collaborators ---

    applyFilters() { this._filters.applyFilters(); }
    setAgentFilter(actor) { this._filters.setAgentFilter(actor); }
    toggleTickDisplay(show) { this._filters.toggleTickDisplay(show); }
    setAreaFilter(areaName) { this._filters.setAreaFilter(areaName); }
    clearAreaFilter() { this._filters.clearAreaFilter(); }
    getAreaFilter() { return this._filters.getAreaFilter(); }
    updateAgentFilterDropdown() { this._filters.updateAgentFilterDropdown(); }
    async _persistLog() { await this._persist.persist(); }
    async restoreLog() { await this._persist.restore(); }

    /** Live stream search — filters cards/rows containing the query. */
    search(query) {
        this._filters.applyFilters();
    }

    /** Density/story mode: 'cards' | 'compact' | 'story' (persisted). */
    setStreamMode(mode) {
        mode = ['cards', 'compact', 'story'].includes(mode) ? mode : 'cards';
        this._streamMode = mode;
        const el = document.getElementById('event-stream');
        if (el) {
            el.classList.toggle('compact', mode === 'compact');
            el.classList.toggle('story-mode', mode === 'story');
        }
        try { localStorage.setItem('vw_stream_mode', mode); } catch (e) {}
        for (const m of ['cards', 'compact', 'story']) {
            const btn = document.getElementById('stream-mode-' + m);
            if (btn) btn.classList.toggle('active', m === mode);
        }
    }

    getStreamMode() { return this._streamMode; }

    /**
     * Turn-queue strip — shows who acts next; the human slot glows pink.
     * Reads VW.agent.turnQueue/currentTurnIndex unless names are passed.
     */
    renderQueueStrip(names) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const queue = names || VW?.agent?.turnQueue || [];
        let strip = streamEl.querySelector('.turn-queue-strip');
        if (!queue.length) { if (strip) strip.remove(); return; }
        const idx = VW?.agent?.currentTurnIndex ?? 0;
        if (!strip) {
            strip = document.createElement('div');
            strip.className = 'turn-queue-strip';
            const anchor = streamEl.querySelector('.timeline-scrubber');
            if (anchor && anchor.nextSibling) anchor.after(strip); else streamEl.insertBefore(strip, streamEl.firstChild);
        }
        const upcoming = queue.slice(idx, idx + 5);
        window.Lit.render(eventStreamHtmlTag`
            <span>⏭ up next:</span>
            ${upcoming.map((name, i) => {
                const human = !worldState.players?.[name]?.simple_npc && worldState.players?.[name]?.autonomy === false;
                return eventStreamHtmlTag`<span class=${i === 0 ? 'q-next' : ''}>${human ? '🎤 YOU (' : ''}${name}${human ? ')' : ''}</span>${i < upcoming.length - 1 ? eventStreamHtmlTag`<span class="q-arrow">→</span>` : ''}`;
            })}`, strip);
    }

    setStyle(style) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        streamEl.setAttribute('data-style', style);
    }

    /** Log a message to the event stream — uses styled bubbles.
     *  meta (optional): {outcome:'success'|'failure'|'minor'} for results. */
    log(text, className, meta) {
        this.emit('log', { text, className });

        if (className === 'msg-thought') {
            const match = text.match(/^\[([^\]]+) inner\]\s*(.*)/);
            if (match) {
                this.logThought(match[1], match[2]);
                return;
            }
        }
        // Memory reflections arrive as generic system messages — give them
        // their own purple row kind (task-340 §reflection styling).
        if (className === 'system-msg' && /^\s*🧠/.test(text)) className = 'msg-reflection';

        this._routeToStream(text, className, meta);
    }

    tickToTime(tick) {
        const raw = VW?.state?.data || {};
        const tpm = raw.time_per_tick_minutes ?? 5;
        const startH = raw.clock_start_hour ?? 8;
        const startM = raw.clock_start_minute ?? 0;
        const total = tick * tpm + startH * 60 + startM;
        const h = Math.floor(total / 60) % 24;
        const m = total % 60;
        return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
    }

    _gameClock() {
        const raw = VW?.state?.data || {};
        const tpm = raw.time_per_tick_minutes ?? 5;
        const total = (VW?.state?.tick || 0) * tpm + (raw.clock_start_hour ?? 8) * 60 + (raw.clock_start_minute ?? 0);
        return { minutes: total % 1440, day: Math.floor(total / 1440) };
    }

    // --- Action Icon Helpers (restored — EventBus.getActionIcon/getActionColor) ---

    static getActionIcon(entry) {
        const r = (entry.result || '').toLowerCase();
        if (!entry.result || r.includes('pick up') || r.includes('moves into') || r.includes('opens') || r.includes('closes')) return '▶️';
        if (r.includes('valueerror') || r.includes("don't")) return '⚠️';
        if (r.includes('dead') || r.includes('killed')) return '✕';
        return '▶️';
    }

    static getActionColor(entry) {
        const icon = EventBus.getActionIcon(entry);
        if (icon === '✕') return 'var(--red)';
        if (icon === '⚠️') return 'var(--orange)';
        return 'var(--green)';
    }

    /** Turn-card header label — shows the round number + current game time. */
    _turnLabel() {
        const turn = VW?.state?.data?.turn_number ?? 0;
        const time = this.tickToTime(VW?.state?.tick || 0);
        return `Turn ${turn} | ${time}`;
    }

    /** Per-line bubble label — global monotonic sequence + current game time. */
    _nextLineLabel() {
        const seq = this._lineSeq++;
        const time = this.tickToTime(VW?.state?.tick || 0);
        return `Tick ${seq} | ${time}`;
    }

    tickToRelative(tick) {
        if (tick == null || typeof tick !== 'number') return 'a while ago';
        const raw = VW?.state?.data || {};
        const currentTick = raw.time_ticks ?? 0;
        const tpm = raw.time_per_tick_minutes ?? 5;
        const diffMinutes = Math.max(0, currentTick - tick) * tpm;
        if (diffMinutes < 1) return 'just now';
        if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
        const hours = Math.floor(diffMinutes / 60);
        if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
        const days = Math.floor(hours / 24);
        return `${days} day${days === 1 ? '' : 's'} ago`;
    }

    /** Log a thought bubble — separate styled block in the event stream */
    logThought(charName, thought) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const tick = VW?.state?.tick || 0;
        this._filters.noteActor(charName);
        const bubble = document.createElement('div');
        bubble.className = 'thought-bubble';
        bubble.setAttribute('data-actor', charName);
        bubble.setAttribute('data-tick', tick);
        bubble.setAttribute('data-type', 'thought');
        bubble.setAttribute('data-stream-area', worldState.players?.[charName]?.current_area || '');
        bubble.title = this.tickToRelative(tick);
        const body = this._cards.bodyFor(charName, streamEl);
        this._insertTimeGap(body || streamEl);
        window.Lit.render(eventStreamHtmlTag`<span class="bubble-icon">💭</span><span class="bubble-tick">[${this._nextLineLabel()}]</span> <span class="bubble-actor bubble-thought-actor">${charName}</span><span class="bubble-text bubble-thought-text">${thought}</span>`, bubble);
        this._appendBubble(streamEl, bubble);
        this._recordPhase(charName, 'think', { thought });
    }

    /** Time compression: ≥30 unlogged game-minutes become a visible gap row. */
    _insertTimeGap(target) {
        if (!target) return;
        const clock = this._gameClock();
        if (this._lastGap) {
            const dayChanged = clock.day !== this._lastGap.day;
            const elapsed = clock.minutes >= this._lastGap.minutes
                ? clock.minutes - this._lastGap.minutes
                : clock.minutes + 1440 - this._lastGap.minutes;
            if (elapsed >= 30 || dayChanged) {
                const gap = document.createElement('div');
                gap.className = 'time-gap';
                gap.textContent = dayChanged
                    ? `— ${elapsed} minutes pass · day ${clock.day + 1} begins —`
                    : `— ${elapsed} minutes pass —`;
                target.appendChild(gap);
                this._scrubber.scheduleRebuild();
            }
        }
        this._lastGap = clock;
    }

    /**
     * Record a phase entry in the character's detailed timeline.
     */
    _recordPhase(charName, phase, data = {}) {
        const state = this.initCharacterState(charName);
        if (!state.detailedTimeline) {
            state.detailedTimeline = [];
        }
        state.detailedTimeline.push({
            tick: VW?.state?.tick || 0,
            timestamp: Date.now(),
            phase,
            ...data
        });
        if (state.detailedTimeline.length > 100) {
            state.detailedTimeline.splice(0, state.detailedTimeline.length - 100);
        }
    }

    /**
     * Record a full phase transition: think → decide → act → result → react
     */
    trackPhase(charName, phase, data = {}) {
        this._recordPhase(charName, phase, data);

        const state = this.initCharacterState(charName);
        if (phase === 'think' && data.thought) state.lastThought = data.thought;
        if (phase === 'speech' && data.speech) state.lastSpeech = data.speech;
        if (phase === 'action' && data.action) state.lastAction = data.action;
        if (phase === 'result' && data.result) state.lastActionResult = data.result;
    }

    _routeToStream(text, className, meta) {
        let agentName = '⚙️';
        let streamType = 'action';
        let streamText = text;
        let icon = '▶️';

        switch (className) {
            case 'user-msg':
                agentName = VW?.state?.activePlayer || 'Player';
                streamText = '> ' + text.replace(/^>\s*/, '');
                icon = '👤';
                break;
            case 'msg-speech': {
                streamType = 'speech';
                const match = text.match(/^\[([^\]]+)\]/);
                if (match) agentName = match[1];
                streamText = text.replace(/^\[([^\]]+)\]\s*/, '');
                icon = '💬';
                break;
            }
            case 'msg-action':
                streamType = 'action';
                streamText = text.replace(/^\[Action\]\s*/, '');
                icon = '▶️';
                break;
            case 'msg-emote':
                streamType = 'emote';
                icon = '🎭';
                break;
            case 'msg-result':
                streamType = 'result';
                icon = '↳';
                break;
            case 'msg-narrated':
                streamType = 'narrated';
                icon = '🎭';
                break;
            case 'msg-whisper':
                streamType = 'whisper';
                icon = '🔒';
                break;
            case 'msg-reflection':
                streamType = 'reflection';
                icon = '🧠';
                break;
            case 'msg-crisis':
                streamType = 'crisis';
                icon = '⚠️';
                break;
            case 'msg-prune':
                streamType = 'prune';
                icon = '✂';
                break;
            case 'msg-error':
            case 'error-msg':
                streamType = 'error';
                icon = '⚠️';
                break;
            case 'agent-msg':
            case 'system-msg':
                streamType = 'system';
                icon = '⚙️';
                break;
            default:
                break;
        }

        // Turn boundaries are defined by phase markers, not by chatter — only
        // the player and hard errors end a card. Engine system rows emitted
        // mid-turn (match info, skill text) stay INSIDE the acting turn's
        // card instead of fragmenting it into two cards.
        if (['user-msg', 'msg-error', 'error-msg'].includes(className)) {
            this._cards.close();
        }
        // Rows without an explicit actor inherit the open card's actor, so
        // actions/results/emotes inside a turn attribute to the right person.
        if (agentName === '⚙️' && this._cards.actor) {
            agentName = this._cards.actor;
        }

        if (text.includes('Welcome to') || text.includes('Available Commands:')) return;

        const tick = VW?.state?.tick || 0;
        if (agentName && agentName !== '⚙️') this._filters.noteActor(agentName);
        this._addBubble(tick, agentName, streamType, streamText, icon, meta || {});
    }

    _trimStream(streamEl) {
        while (streamEl.children.length > this.MAX_LINES) {
            streamEl.removeChild(streamEl.firstChild);
        }
    }

    /** Append a bubble to the current turn card body or stream, then trim + autoscroll */
    _appendBubble(streamEl, bubble) {
        const body = this._cards.current?.querySelector('.turn-card-body');
        (body || streamEl).appendChild(bubble);
        this._trimStream(streamEl);
        this._scrubber.scheduleRebuild();
        if (this.autoScroll) streamEl.scrollTop = streamEl.scrollHeight;
    }

    _addBubble(tick, agentName, type, text, icon, meta = {}) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;

        this._filters.noteActor(agentName);

        const isAgentEvent = type !== 'system' && type !== 'error';

        const bubble = document.createElement('div');
        let classes = `msg-bubble msg-bubble-${type}`;
        if (type === 'phase' && meta.phaseClass) classes += ` phase-${meta.phaseClass}`;
        if (type === 'result' && meta.outcome) classes += ` outcome-${meta.outcome}`;
        bubble.className = classes;
        bubble.setAttribute('data-actor', agentName);
        bubble.setAttribute('data-tick', tick);
        bubble.setAttribute('data-type', type);
        const actorArea = (agentName && agentName !== '⚙️' && agentName !== 'LLM') ? (worldState.players?.[agentName]?.current_area || null) : null;
        bubble.setAttribute('data-stream-area', actorArea || '');
        bubble.title = this.tickToRelative(tick);

        const filterMap = { thought: config.filterThoughts, speech: config.filterSpeech, action: config.filterActions, emote: config.filterActions, result: config.filterActions, whisper: config.filterSpeech, reflection: config.filterThoughts, narrated: config.filterSystem, crisis: config.filterSystem, prune: config.filterSystem, system: config.filterSystem, error: config.filterSystem };
        if (filterMap[type] !== undefined && !filterMap[type]) bubble.style.display = 'none';

        const outcomeBadge = type === 'result'
            ? (meta.outcome === 'success' ? '<span class="result-badge ok">✓</span>'
              : meta.outcome === 'failure' ? '<span class="result-badge fail">✕</span>'
              : meta.outcome === 'minor' ? '<span class="result-badge minor">ℹ</span>' : '')
            : '';
        const badge = this._renderSkillBadge(text);
        const displayText = badge ? text.replace(/^\[Skill Check\].*/, '') : this._escapeHtml(text);
        const badgeHtml = badge ? `<br>${badge}` : '';

        const textSpan = badge
            ? window.Lit.unsafeHTML(outcomeBadge + displayText + badgeHtml)
            : window.Lit.unsafeHTML(outcomeBadge + displayText);

        window.Lit.render(eventStreamHtmlTag`<span class="bubble-icon">${icon}</span><span class="bubble-tick">[${this._nextLineLabel()}]</span> <span class="bubble-actor bubble-${type}-actor">${agentName}</span> <span class="bubble-text bubble-${type}-text">${textSpan}</span>`, bubble);

        const body = this._cards.current?.querySelector('.turn-card-body');
        if (body && isAgentEvent) {
            this._insertTimeGap(body);
            body.appendChild(bubble);
        } else {
            this._insertTimeGap(streamEl);
            streamEl.appendChild(bubble);
        }

        this._trimStream(streamEl);
        this._scrubber.scheduleRebuild();

        if (this.autoScroll) {
            streamEl.scrollTop = streamEl.scrollHeight;
        }
    }

    // --- Streaming output ---

    startStreaming(id) {
        const chatEl = document.getElementById('event-stream');
        if (!chatEl) return null;
        if (this._streamSpans[id]) return this._streamSpans[id];
        const chip = document.createElement('div');
        chip.className = 'msg-bubble msg-bubble-stream';
        chip.setAttribute('data-type', 'stream');
        // Streaming carve-out: build the fixed skeleton ONCE via lit so the
        // bubble-icon and bubble-stream-text spans are present. The bubble is
        // never re-rendered by lit afterwards, so the token stream below
        // appends into the captured span via plain DOM appends.
        window.Lit.render(eventStreamHtmlTag`<span class="bubble-icon">🧠</span><span class="bubble-text bubble-stream-text">thinking...</span>`, chip);
        chatEl.appendChild(chip);
        this._streamSpans[id] = chip;
        this._isStreaming = true;
        if (this.autoScroll) {
            chatEl.scrollTop = chatEl.scrollHeight;
        }
        return chip;
    }

    appendStream(id, chunk) {
        const chip = this._streamSpans[id];
        if (!chip) return;
        // Streaming carve-out: never a lit re-render (would wipe streamed text).
        const streamTextSpan = chip.querySelector('.bubble-stream-text');
        if (streamTextSpan) {
            streamTextSpan.insertAdjacentHTML('beforeend', chunk);
        }
        if (this.autoScroll) {
            const chatEl = document.getElementById('event-stream');
            if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
        }
    }

    finishStreaming(id, fallbackContent) {
        const chip = this._streamSpans[id];
        if (chip && chip.parentNode) {
            const rawContent = chip.textContent || '';
            let cleanContent = (fallbackContent != null && String(fallbackContent).trim())
                ? String(fallbackContent).trim()
                : rawContent.replace(/^🧠?\s*thinking\.\.\./i, '').trim();
            if (typeof extractAssistantText === 'function') {
                cleanContent = extractAssistantText(cleanContent);
            }
            chip.remove();
            if (cleanContent) {
                this.logRawLLM(cleanContent);
            }
        }
        delete this._streamSpans[id];
        this._isStreaming = Object.keys(this._streamSpans).length > 0;
    }

    // --- Raw LLM payloads (delegated to stream-raw-llm.js) ---

    logRawLLMRequest(phaseName, messages, estTokens) { this._rawllm.logRequest(phaseName, messages, estTokens); }
    logRawLLMResponse(label, content) { this._rawllm.logResponse(label, content); }
    logRawLLM(contentOrLabel, optionalContent) { this._rawllm.log(contentOrLabel, optionalContent); }
    storeRawResponse(charName, phase, raw) { return this._rawllm.storeRawResponse(charName, phase, raw); }
    getRawResponse(seq) { return this._rawllm.getRawResponse(seq); }
    logParseError(charName, phase, errMsg, raw) { this._rawllm.logParseError(charName, phase, errMsg, raw); }

    /** Log a phase marker as a colored pill inside the actor's turn card. */
    logPhase(charName, phase, subtext) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const tick = VW?.state?.tick || 0;
        this._filters.noteActor(charName);

        const bubble = document.createElement('div');
        bubble.className = `msg-bubble msg-bubble-phase phase-${phase}`;
        bubble.setAttribute('data-actor', charName);
        bubble.setAttribute('data-tick', tick);
        bubble.setAttribute('data-type', 'phase');
        bubble.setAttribute('data-stream-area', worldState.players?.[charName]?.current_area || '');
        bubble.title = this.tickToRelative(tick);
        const icons = { observe: '👁️', think: '💭', decide: '🎯', act: '⚡', react: '🔄' };
        const icon = icons[phase] || '➡️';
        const label = subtext ? `${phase} · ${subtext}` : phase;
        window.Lit.render(eventStreamHtmlTag`<span class="bubble-icon">${icon}</span><span class="bubble-tick">[${this._nextLineLabel()}]</span><span class="bubble-phase-pill">${label}</span>`, bubble);

        // observe/think always start a fresh card — same actor's NEXT turn
        // must not merge into the previous turn's card.
        const body = this._cards.bodyFor(charName, streamEl, phase === 'observe' || phase === 'think');
        this._insertTimeGap(body || streamEl);
        (body || streamEl).appendChild(bubble);

        this._trimStream(streamEl);
        this._scrubber.scheduleRebuild();
        if (this.autoScroll) {
            streamEl.scrollTop = streamEl.scrollHeight;
        }
    }

    // --- Area Event Log ---

    logAreaEvent(area, charName, action, result) {
        if (!area) return;
        if (!this._areaEventLog[area]) this._areaEventLog[area] = [];
        this._areaEventLog[area].push({
            tick: worldState.tick || 0,
            actor: charName,
            action: action,
            result: result || ''
        });
        if (this._areaEventLog[area].length > 50) this._areaEventLog[area].shift();
    }

    getAreaEvents(area) {
        return this._areaEventLog[area] || [];
    }

    clearAll() {
        const streamEl = document.getElementById('event-stream');
        // Imperative wipe: Lit.render() only clears between its own markers,
        // so bubbles appended via appendChild would survive every clear.
        if (streamEl) {
            while (streamEl.firstChild) {
                streamEl.removeChild(streamEl.firstChild);
            }
        }
        this._areaEventLog = {};
        this._characterState = {};
        this._streamSpans = {};
        this._isStreaming = false;
        this._knownActors.clear();
        this._lineSeq = 0;
        this._lastGap = null;
        this._rawllm._rawResponses = [];
        this._rawllm._streak = null;
        this._scrubber.scheduleRebuild();
        storage.saveEventLog([]);
    }

    clearAreaEvents() {
        this._areaEventLog = {};
    }

    // --- Character State Tracking ---

    initCharacterState(charName) {
        if (!this._characterState[charName]) {
            this._characterState[charName] = {
                lastThought: '',
                lastSpeech: null,
                lastAction: '',
                actionHistory: [],
                currentArea: '',
                lastActionResult: ''
            };
        }
        return this._characterState[charName];
    }

    trackAction(charName, inner, speech, action, result) {
        const state = this.initCharacterState(charName);
        state.lastThought = inner || state.lastThought;
        state.lastSpeech = speech !== undefined ? speech : state.lastSpeech;
        state.lastAction = action || state.lastAction;
        const tick = worldState.tick || 0;
        state.actionHistory.push({
            tick,
            action, result,
            thought: inner || ''
        });
        if (state.actionHistory.length > 20) state.actionHistory.shift();
        if (result) state.lastActionResult = result;

        const area = worldState.players?.[charName]?.current_area;
        if (area && (action || result || speech)) {
            let actionText = action || '';
            let resultText = result || '';
            if (speech && !actionText) {
                actionText = `speak: "${speech}"`;
            } else if (speech && actionText) {
                resultText = `"${speech}"${resultText ? ' | ' + resultText : ''}`;
            }
            this.logAreaEvent(area, charName, actionText, resultText);
            const prevRoom = state.currentArea;
            if (prevRoom && prevRoom !== area && action) {
                this.logAreaEvent(prevRoom, charName, action + ' (left toward ' + area + ')', 'Exits the area.');
                this._emitTransition(charName, prevRoom, area);
            }
            state.currentArea = area;
        }
    }

    /** Area-transition divider — movement becomes visible in the stream. */
    _emitTransition(charName, fromArea, toArea) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const divider = document.createElement('div');
        divider.className = 'area-transition';
        divider.setAttribute('data-stream-area', toArea);
        divider.setAttribute('data-actor', charName);
        window.Lit.render(eventStreamHtmlTag`<span>${charName} · ${fromArea} → ${toArea}</span>`, divider);
        streamEl.appendChild(divider);
        this._trimStream(streamEl);
        this._scrubber.scheduleRebuild();
        if (this.autoScroll) streamEl.scrollTop = streamEl.scrollHeight;
    }

    getCharacterState(charName) {
        return this._characterState[charName] || this.initCharacterState(charName);
    }

    // --- Character Control Mode (delegates to stream-control-mode.js) ---

    isAutonomous(charName) { return this._controlMode.isAutonomous(charName); }

    getControlMode(charName) { return this._controlMode.getControlMode(charName); }

    cycleControlMode(charName) { this._controlMode.cycleControlMode(charName); }

    /** Render skill check badge HTML, or null if text doesn't match */
    _renderSkillBadge(text) {
        const match = text.match(/^\[Skill Check\]\s*(\w+)\s+vs\s+DC\s+(\d+)\s+\(([^)]+)\):\s*roll=(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)\s*=>\s*(\w+)/);
        if (!match) return null;
        const [, skill, dc, diffDesc, roll, bonus, total, result] = match;
        const ok = result === 'success';
        const icon = ok ? '✅' : '❌';
        const color = ok ? 'var(--green)' : 'var(--red)';
        return `<span class="skill-badge" style="border-color:${color}" title="DC ${dc} ${diffDesc}"><span class="skill-badge-icon">${icon}</span><span class="skill-badge-skill">${this._escapeHtml(skill)}</span><span class="skill-badge-dc">DC ${dc}</span><span class="skill-badge-roll">${roll}+${bonus}=${total}</span><span class="skill-badge-result" style="color:${color}">${result}</span></span>`;
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

const events = new EventBus();
