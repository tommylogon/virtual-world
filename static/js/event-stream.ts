/**
 * EventBus — Pub/sub event stream and terminal output
 *
 * @module event-stream — the event stream panel
 * @contributes EventBus service: log/emit, row kinds, turn cards, filters, persistence hooks, story mode
 * @powers the main event stream, stream search, the queue strip, and the log export
 * @relates publishes on event-bus; collaborators live in static/js/stream/*
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 *
 * task-340 (event stream v2): slimmed core with extracted collaborators in
 * static/js/stream/ (filters, turn cards, raw-LLM chips, persistence,
 * timeline scrubber). The bus remains the single public surface — every
 * legacy symbol still works. New in v2: collapsed LLM payload chips with
 * token meters, outcome-tinted results, phase pills, narration/reflection/
 * whisper/crisis/prune row kinds, area-transition dividers, time-gap rows,
 * turn-queue strip, timeline scrubber, stream search, and a story mode.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const eventStreamHtmlTag = (strings: TemplateStringsArray, ...values: unknown[]): any => window.Lit.html(strings, ...values);

/**
 * The v2 collaborators in static/js/stream/*. They are separate classic-script
 * classes, so a per-file build cannot see their shapes; the real contracts live
 * in those files and the real home for shared declarations is
 * static/js/types/globals.d.ts. Placeholder index signatures keep this file
 * compiling on its own without freezing a copy of a surface it does not own.
 */
declare class StreamTurnCards { constructor(bus: unknown); [key: string]: any; }
declare class StreamFilters { constructor(bus: unknown); [key: string]: any; }
declare class StreamRawLLM { constructor(bus: unknown); [key: string]: any; }
declare class StreamPersistence { constructor(bus: unknown); [key: string]: any; }
declare class StreamScrubber { constructor(bus: unknown); [key: string]: any; }
declare class StreamControlMode { constructor(bus: unknown); [key: string]: any; }

/** Assigned by shared/json-utils.js as a classic-script global. */
declare function extractAssistantText(raw: unknown): string;




/** Per-character turn state this bus accumulates for the react phase. */
interface CharacterStreamState {
    lastThought: string;
    lastSpeech: string | null;
    lastAction: string;
    actionHistory: { tick: number; action?: string; result?: string; thought: string }[];
    currentArea: string;
    lastActionResult: string;
    detailedTimeline?: { tick: number; timestamp: number; phase: string }[];
}

class EventBus {
    // `declare` keeps the emitted class free of field initializers.
    declare private MAX_LINES: number;
    declare private autoScroll: boolean;
    declare private _subscribers: Record<string, ((data?: unknown) => void)[]>;
    declare private _streamSpans: Record<string, HTMLElement>;
    declare private _streamLabels: Record<string, string>;
    declare private _isStreaming: boolean;
    declare private _areaEventLog: Record<string, any[]>;
    declare private _characterState: Record<string, CharacterStreamState>;
    declare private _characterAutonomy: Record<string, unknown>;
    declare private _knownActors: Set<string>;
    declare private _lineSeq: number;
    declare private _streamMode: string;
    declare private _lastGap: { minutes: number; day: number } | null;
    declare private _cards: StreamTurnCards;
    declare private _filters: StreamFilters;
    declare private _rawllm: StreamRawLLM;
    declare private _persist: StreamPersistence;
    declare private _scrubber: StreamScrubber;
    declare private _controlMode: StreamControlMode;

    constructor() {
        this.MAX_LINES = 5000;
        this.autoScroll = true;
        this._subscribers = {};
        this._streamSpans = {};
        this._streamLabels = {};
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
    on(event: string, callback: (data?: unknown) => void): void {
        if (!this._subscribers[event]) this._subscribers[event] = [];
        this._subscribers[event].push(callback);
    }

    /** Emit an event */
    emit(event: string, data?: unknown): void {
        const subs = this._subscribers[event] || [];
        subs.forEach(cb => cb(data));
    }

    // --- Delegates to v2 collaborators ---

    applyFilters() { this._filters.applyFilters(); }
    setAgentFilter(actor: string): void { this._filters.setAgentFilter(actor); }
    toggleTickDisplay(show: boolean): void { this._filters.toggleTickDisplay(show); }
    setAreaFilter(areaName: string): void { this._filters.setAreaFilter(areaName); }
    clearAreaFilter() { this._filters.clearAreaFilter(); }
    getAreaFilter() { return this._filters.getAreaFilter(); }
    updateAgentFilterDropdown() { this._filters.updateAgentFilterDropdown(); }
    async _persistLog() { await this._persist.persist(); }
    async restoreLog() { await this._persist.restore(); }

    /** Live stream search — filters cards/rows containing the query. */
    search(query: string): void {
        this._filters.applyFilters();
    }

    /** Set the stream density: 'cards' | 'compact' | 'story' (persisted).
     *  Story mode also hides the gear-data brackets ([wearing: …]/[holding: …])
     *  from character-presence rows — the raw text stays in cards/compact and
     *  in every export preference; story is prose-only. */
    setStreamMode(mode: string): void {
        mode = ['cards', 'compact', 'story'].includes(mode) ? mode : 'cards';
        this._streamMode = mode;
        const el = document.getElementById('event-stream');
        if (el) {
            el.classList.toggle('compact', mode === 'compact');
            el.classList.toggle('story-mode', mode === 'story');
            // Re-render existing rows between raw and prose-only text.
            for (const bubble of el.querySelectorAll<HTMLElement>('.msg-bubble')) {
                if (bubble.dataset.rawText === undefined) continue;
                const span = bubble.querySelector('.bubble-text');
                if (!span) continue;
                span.textContent = this._gearVisibleText(bubble.getAttribute('data-type') as string, bubble.dataset.rawText as string);
            }
        }
        try { localStorage.setItem('vw_stream_mode', mode); } catch (e) {}
        for (const m of ['cards', 'compact', 'story']) {
            const btn = document.getElementById('stream-mode-' + m);
            if (btn) btn.classList.toggle('active', m === mode);
        }
    }

    /** Strip gear bracket segments in story mode, keep raw elsewhere. */
    _gearVisibleText(type: string, raw: unknown): string {
        const text = String(raw || '');
        if (this._streamMode === 'story' && (type === 'result' || type === 'narrated')) {
            return text.replace(/\[wearing:[^\]]*\]/gi, '').replace(/\[holding:[^\]]*\]/gi, '').replace(/[ \t]{2,}/g, ' ');
        }
        return text;
    }

    getStreamMode() { return this._streamMode; }

    /**
     * Turn-queue strip — shows who acts next; the human slot glows pink.
     * Reads VW.agent.turnQueue/currentTurnIndex unless names are passed.
     */
    renderQueueStrip(names?: string[]): void {
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
            ${upcoming.map((name: string, i: number) => {
                const human = !worldState.players?.[name]?.simple_npc && worldState.players?.[name]?.autonomy === false;
                return eventStreamHtmlTag`<span class=${i === 0 ? 'q-next' : ''}>${human ? '🎤 YOU (' : ''}${name}${human ? ')' : ''}</span>${i < upcoming.length - 1 ? eventStreamHtmlTag`<span class="q-arrow">→</span>` : ''}`;
            })}`, strip);
    }

    setStyle(style: string): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        streamEl.setAttribute('data-style', style);
    }

    /**
     * Open (or reuse) the turn card for a human-controlled actor so rows they
     * emit directly through /api/action (speech, emotes, interjections) group
     * under their character instead of landing in the bare stream (bug-33).
     * Safe to call repeatedly within one turn — a card for the same actor is
     * reused, and the next phase marker starts a fresh one.
     */
    beginActorTurn(charName: string): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl || !charName) return;
        this._cards.bodyFor(charName, streamEl);
    }

    /** Log a message to the event stream — uses styled bubbles.
     *  meta (optional): {outcome:'success'|'failure'|'minor'} for results.
     *  actor (optional): explicit owner for rows that would otherwise inherit
     *  the open turn card (e.g. memory recalls logged on behalf of a character). */
    log(text: string, className: string, meta?: Record<string, unknown>, actor?: string): void {
        // The bus payload carries the acting character so subscribers (the turn
        // digest) can scope what the human is allowed to perceive. An explicit
        // actor wins; otherwise action/result rows inherit the open turn card's
        // actor, while system/world rows stay unattributed.
        const isSystemRow = className === 'system-msg' || className === 'agent-msg';
        const busActor = actor || (isSystemRow ? null : (this._cards && this._cards.actor)) || null;
        this.emit('log', { text, className, meta, actor: busActor });

        if (className === 'msg-thought') {
            const match = text.match(/^\[([^\]]+) inner\]\s*(.*)/);
            if (match) {
                this.logThought(match[1], match[2]);
                return;
            }
        }
        // Memory reflections arrive as generic system messages — give them
        // their own colored row kind (task-340 §reflection styling). Recalls
        // (🧠 recalled N memories) and simple-NPC rows (👾) get their own
        // kinds too so each is filterable on its own.
        if (className === 'system-msg' && /^\s*🧠\s*recalled/.test(text)) className = 'msg-recall';
        else if (className === 'system-msg' && /^\s*👾/.test(text)) className = 'msg-npc';
        else if (className === 'system-msg' && /^\s*🧠/.test(text)) className = 'msg-reflection';

        this._routeToStream(text, className, meta, actor);
    }

    /** task-448: a disambiguation chooser. Renders one button per candidate,
     *  each labelled with a distinguishing detail; clicking re-runs the action
     *  against that candidate's identity key (`verb key`), which the matcher
     *  accepts verbatim. Never auto-picks. */
    logChoices(verb: string, options: { key: string; label: string; detail?: string }[], actor?: string): void {
        if (!verb || !Array.isArray(options) || !options.length) return;
        const text = 'Which one did you mean?';
        this.emit('log', { text, className: 'msg-choices', meta: {}, actor: actor || null });
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble msg-bubble-choices';
        bubble.setAttribute('data-actor', actor || '');
        bubble.setAttribute('data-tick', VW?.state?.tick || 0);
        const label = document.createElement('span');
        label.className = 'bubble-text bubble-choices-text';
        label.textContent = text + ' ';
        bubble.appendChild(label);
        for (const option of options) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-sm choice-btn';
            btn.style.cssText = 'margin:2px 4px 2px 0;font-size:10px;';
            btn.textContent = option.detail ? `${option.label} — ${option.detail}` : option.label;
            btn.title = `Target ${option.key}`;
            btn.addEventListener('click', async () => {
                btn.disabled = true;
                try {
                    const data = await (ApiClient as unknown as { action(verb: string, actor?: string): Promise<any> }).action(`${verb} key:${option.key}`, actor || undefined);
                    if (data?.output) {
                        this.log(data.output, 'msg-result', { outcome: data?.success !== false ? 'success' : 'failure' });
                    } else if (data?.error) {
                        this.log('❌ ' + data.error, 'error-msg');
                    }
                } catch (err) {
                    this.log('❌ ' + (err as Error).message, 'error-msg');
                }
                if (window.worldState && typeof worldState.fetch === 'function') worldState.fetch();
            });
            bubble.appendChild(btn);
        }
        const body = this._cards.current?.querySelector('.turn-card-body');
        if (body) body.appendChild(bubble);
        else streamEl.appendChild(bubble);
        this._trimStream(streamEl);
        this._scrubber.scheduleRebuild();
        if (this.autoScroll) streamEl.scrollTop = streamEl.scrollHeight;
    }

    tickToTime(tick: number): string {
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

    static getActionIcon(entry: { result?: string }): string {
        const r = (entry.result || '').toLowerCase();
        if (!entry.result || r.includes('pick up') || r.includes('moves into') || r.includes('opens') || r.includes('closes')) return '▶️';
        if (r.includes('valueerror') || r.includes("don't")) return '⚠️';
        if (r.includes('dead') || r.includes('killed')) return '✕';
        return '▶️';
    }

    static getActionColor(entry: { result?: string }): string {
        const icon = EventBus.getActionIcon(entry);
        if (icon === '✕') return 'var(--red)';
        if (icon === '⚠️') return 'var(--orange)';
        return 'var(--green)';
    }

    /** Turn-card header label — round number, calendar date, game time, moon. */
    _turnLabel() {
        const raw = VW?.state?.data || {};
        const turn = raw.turn_number ?? 0;
        const time = this.tickToTime(VW?.state?.tick || 0);
        // task-228/229: calendar date + moon phase when the engine exposes them.
        let datePart = '';
        if (raw.game_day != null) {
            datePart = ` | Day ${raw.game_day}, Month ${raw.game_month ?? 1}, Year ${raw.game_year ?? 1}`;
        }
        const moon = raw.moon_phase;
        const moonPart = moon?.icon ? ` ${moon.icon}` : '';
        return `Turn ${turn}${datePart} | ${time}${moonPart}`;
    }

    /** Per-line bubble label — global monotonic sequence + current game time. */
    _nextLineLabel() {
        const seq = this._lineSeq++;
        const time = this.tickToTime(VW?.state?.tick || 0);
        return `Tick ${seq} | ${time}`;
    }

    tickToRelative(tick: number | null | undefined): string {
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
    logThought(charName: string, thought: string): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const tick = VW?.state?.tick || 0;
        this._filters.noteActor(charName);
        const bubble = document.createElement('div');
        bubble.className = 'thought-bubble msg-bubble-thought';
        bubble.setAttribute('data-actor', charName);
        bubble.setAttribute('data-tick', tick as unknown as string);
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
    _insertTimeGap(target: HTMLElement | null): void {
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
    _recordPhase(charName: string, phase: string, data: Record<string, any> = {}): void {
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
    trackPhase(charName: string, phase: string, data: Record<string, any> = {}): void {
        this._recordPhase(charName, phase, data);

        const state = this.initCharacterState(charName);
        if (phase === 'think' && data.thought) state.lastThought = data.thought;
        if (phase === 'speech' && data.speech) state.lastSpeech = data.speech;
        if (phase === 'action' && data.action) state.lastAction = data.action;
        if (phase === 'result' && data.result) state.lastActionResult = data.result;
    }

    _routeToStream(text: string, className: string, meta: Record<string, unknown> | undefined, actor?: string): void {
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
            case 'msg-recall':
                streamType = 'recall';
                icon = '🧠';
                break;
            case 'msg-npc':
                streamType = 'npc';
                icon = '👾';
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
        // Global/system-family rows do NOT: they go to the neutral "World"
        // lane instead of being misfiled under whoever's card happens to be
        // open (e.g. "Event stream copied" under Lyrie's turn). An explicit
        // `actor` (memory recalls) wins over both.
        if (agentName === '⚙️') {
            if (actor) {
                agentName = actor;
            } else if (['system', 'error', 'recall', 'npc'].includes(streamType)) {
                agentName = 'World';
            } else if (this._cards.actor) {
                agentName = this._cards.actor;
            }
        }

        if (text.includes('Welcome to') || text.includes('Available Commands:')) return;

        const tick = VW?.state?.tick || 0;
        if (agentName && agentName !== '⚙️') this._filters.noteActor(agentName);
        this._addBubble(tick, agentName, streamType, streamText, icon, meta || {});
    }

    _trimStream(streamEl: HTMLElement): void {
        while (streamEl.children.length > this.MAX_LINES) {
            streamEl.removeChild(streamEl.firstChild!);
        }
    }

    /** Append a bubble to the current turn card body or stream, then trim + autoscroll */
    _appendBubble(streamEl: HTMLElement, bubble: HTMLElement): void {
        const body = this._cards.current?.querySelector('.turn-card-body');
        (body || streamEl).appendChild(bubble);
        this._trimStream(streamEl);
        this._scrubber.scheduleRebuild();
        if (this.autoScroll) streamEl.scrollTop = streamEl.scrollHeight;
    }

    _addBubble(tick: number, agentName: string, type: string, text: string, icon: string, meta: Record<string, any> = {}): void {
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
        bubble.setAttribute('data-tick', tick as unknown as string);
        bubble.setAttribute('data-type', type);
        const actorArea = (agentName && agentName !== '⚙️' && agentName !== 'LLM') ? (worldState.players?.[agentName]?.current_area || null) : null;
        bubble.setAttribute('data-stream-area', actorArea || '');
        bubble.title = this.tickToRelative(tick);

        const filterMap: Record<string, unknown> = { thought: config.filterThoughts, speech: config.filterSpeech, action: config.filterActions, emote: config.filterActions, result: config.filterActions, whisper: config.filterSpeech, reflection: config.filterThoughts, recall: config.filterRecalls, npc: config.filterNpc, narrated: config.filterSystem, crisis: config.filterSystem, prune: config.filterSystem, system: config.filterSystem, error: config.filterSystem };
        if (filterMap[type] !== undefined && !filterMap[type]) bubble.style.display = 'none';

        const outcomeBadge = type === 'result'
            ? (meta.outcome === 'success' ? '<span class="result-badge ok">✓</span>'
              : meta.outcome === 'failure' ? '<span class="result-badge fail">✕</span>'
              : meta.outcome === 'minor' ? '<span class="result-badge minor">ℹ</span>' : '')
            : '';
        const badge = this._renderSkillBadge(text);
        // Raw text is kept on the bubble so story mode can strip gear brackets
        // on the fly without losing the data in cards/compact/exports.
        bubble.dataset.rawText = String(text || '');
        const shown = this._gearVisibleText(type, text);
        const displayText = badge ? shown.replace(/^\[Skill Check\].*/, '') : this._escapeHtml(shown);
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

    startStreaming(id: string, label?: string): HTMLElement | null {
        const chatEl = document.getElementById('event-stream');
        if (!chatEl) return null;
        this._streamLabels[id] = label || 'LLM';
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

    appendStream(id: string, chunk: string): void {
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

    finishStreaming(id: string, fallbackContent?: string | null): void {
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
                this.logRawLLM(this._streamLabels[id] || 'LLM', cleanContent);
            }
        }
        delete this._streamSpans[id];
        delete this._streamLabels[id];
        this._isStreaming = Object.keys(this._streamSpans).length > 0;
    }

    // --- Raw LLM payloads (delegated to stream-raw-llm.js) ---

    logRawLLMRequest(phaseName: string, messages: unknown, estTokens?: number): void { this._rawllm.logRequest(phaseName, messages, estTokens); }
    logRawLLMResponse(label: string, content: unknown): void { this._rawllm.logResponse(label, content); }
    logRawLLM(contentOrLabel: string, optionalContent?: string): void { this._rawllm.log(contentOrLabel, optionalContent); }
    storeRawResponse(charName: string, phase: string, raw: string): any { return this._rawllm.storeRawResponse(charName, phase, raw); }
    getRawResponse(seq: number): any { return this._rawllm.getRawResponse(seq); }
    logParseError(charName: string, phase: string, errMsg: string, raw?: string): void { this._rawllm.logParseError(charName, phase, errMsg, raw); }

    /** Log a phase marker as a colored pill inside the actor's turn card. */
    logPhase(charName: string, phase: string, subtext?: string): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const tick = VW?.state?.tick || 0;
        this._filters.noteActor(charName);

        const bubble = document.createElement('div');
        bubble.className = `msg-bubble msg-bubble-phase phase-${phase}`;
        bubble.setAttribute('data-actor', charName);
        bubble.setAttribute('data-tick', tick as unknown as string);
        bubble.setAttribute('data-type', 'phase');
        bubble.setAttribute('data-stream-area', worldState.players?.[charName]?.current_area || '');
        bubble.title = this.tickToRelative(tick);
        const icons: Record<string, string> = { observe: '👁️', think: '💭', decide: '🎯', act: '⚡', react: '🔄' };
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

    logAreaEvent(area: string, charName: string, action: string, result?: string): void {
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

    getAreaEvents(area: string): any[] {
        return this._areaEventLog[area] || [];
    }

    clearAll() {
        const streamEl = document.getElementById('event-stream');
        // Imperative wipe: Lit.render() only clears between its own markers,
        // so bubbles appended via appendChild would survive every clear.
        if (streamEl) {
            while (streamEl.firstChild) {
                streamEl.removeChild(streamEl.firstChild!);
            }
        }
        this._areaEventLog = {};
        this._characterState = {};
        this._streamSpans = {};
        this._streamLabels = {};
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

    initCharacterState(charName: string): CharacterStreamState {
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

    trackAction(charName: string, inner?: string, speech?: string, action?: string, result?: string): void {
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
    _emitTransition(charName: string, fromArea: string, toArea: string): void {
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

    getCharacterState(charName: string): CharacterStreamState {
        return this._characterState[charName] || this.initCharacterState(charName);
    }

    // --- Character Control Mode (delegates to stream-control-mode.js) ---

    isAutonomous(charName: string): boolean { return this._controlMode.isAutonomous(charName); }

    getControlMode(charName: string): string { return this._controlMode.getControlMode(charName); }

    cycleControlMode(charName: string): void { this._controlMode.cycleControlMode(charName); }

    /** Render skill check badge HTML, or null if text doesn't match */
    _renderSkillBadge(text: string): string | null {
        const match = text.match(/^\[Skill Check\]\s*(\w+)\s+vs\s+DC\s+(\d+)\s+\(([^)]+)\):\s*roll=(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)\s*=>\s*(\w+)/);
        if (!match) return null;
        const [, skill, dc, diffDesc, roll, bonus, total, result] = match;
        const ok = result === 'success';
        const icon = ok ? '✅' : '❌';
        const color = ok ? 'var(--green)' : 'var(--red)';
        return `<span class="skill-badge" style="border-color:${color}" title="DC ${dc} ${diffDesc}"><span class="skill-badge-icon">${icon}</span><span class="skill-badge-skill">${this._escapeHtml(skill)}</span><span class="skill-badge-dc">DC ${dc}</span><span class="skill-badge-roll">${roll}+${bonus}=${total}</span><span class="skill-badge-result" style="color:${color}">${result}</span></span>`;
    }

    _escapeHtml(str: string): string {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// globals.d.ts already declares `events: any` so the rest of the app can reach this
// bus without importing it; publishing through `window` keeps a bare `events`
// reference in another file resolving to the same singleton.
(window as unknown as { events: unknown }).events = new EventBus();
