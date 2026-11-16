/**
 * stream-persistence.js - IndexedDB round-trip for the event stream
 *
 * task-779: Persist the event stream as structured records rather than HTML strings.
 * Reuses the record projection from ui/event-log-export.js (task-777).
 * Persistence cap is explicitly 2000 records (DOM keeps 5000).
 * Pre-v2 logs (HTML rows) are dropped cleanly on restore.
 *
 * @module stream/stream-persistence - IndexedDB round-trip for the stream
 * @contributes save/restore of the event stream (cap 2000) + the persisted area filter
 * @powers Event stream - keeping your scrollback across reloads
 * @relates uses storage + ui/event-log-export; loaded before event-stream.js
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */

// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

function _escStream(s: unknown): string {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

class StreamPersistence {
    _bus: PersistenceBus;
    CAP: number;
    _storedWorldKey: string;

    constructor(bus: PersistenceBus) {
        this._bus = bus;
        this.CAP = 2000;
        this._storedWorldKey = '';
    }

    /**
     * Identity of the world the stream is recording. Worlds differ by scenario
     * name, with the scenario source path as a fallback for scenarios that were
     * never named.
     */
    _worldKey(): string {
        try {
            const data = (window.worldState && window.worldState.data) || {};
            return String(data._scenario_name || data.scenario_source
                || (document.body && document.body.dataset.scenarioName) || '');
        } catch (err) {
            return '';
        }
    }

    /** Save current event log as structured records to IndexedDB */
    async persist(): Promise<void> {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;

        const exporter = (window as unknown as {
            EventLogExport?: { projectStreamRows(el: HTMLElement, opts?: { ignoreFilters?: boolean }): PersistedStreamRecord[] };
        }).EventLogExport;

        if (!exporter || typeof exporter.projectStreamRows !== 'function') return;

        let records = exporter.projectStreamRows(streamEl, { ignoreFilters: true });
        if (records.length > this.CAP) {
            records = records.slice(records.length - this.CAP);
        }

        const worldKey = this._worldKey();
        if (this._storedWorldKey && worldKey && this._storedWorldKey !== worldKey) {
            this._storedWorldKey = worldKey;
            await storage.saveEventLog([]);
            await storage.setConfig('event_log_version', '2');
            await storage.setConfig('event_log_world', worldKey);
            return;
        }
        this._storedWorldKey = worldKey;
        await storage.saveEventLog(records);
        await storage.setConfig('event_log_version', '2');
        if (worldKey) await storage.setConfig('event_log_world', worldKey);
    }

    /** Restore event log from IndexedDB records */
    async restore(): Promise<void> {
        if (!window.Lit) return;
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;

        const worldKey = this._worldKey();
        this._storedWorldKey = worldKey;
        let savedWorldKey = '';
        try { savedWorldKey = await storage.getConfig('event_log_world') || ''; } catch (err) { savedWorldKey = ''; }
        if (savedWorldKey && worldKey && savedWorldKey !== worldKey) {
            await storage.saveEventLog([]);
            await storage.setConfig('event_log_version', '2');
            await storage.setConfig('event_log_world', worldKey);
            return;
        }

        const entries: any[] = await storage.loadEventLog();
        if (!entries || entries.length === 0) return;

        let version = '';
        try { version = await storage.getConfig('event_log_version') || ''; } catch (err) { version = ''; }

        // Clean drop for pre-v2 HTML format logs (task-779)
        const hasLegacyHtml = entries.some(e => e && e.html !== undefined && e.type === undefined);
        if (version !== '2' || hasLegacyHtml) {
            console.info('Dropping pre-v2 HTML-format event log (migrated to structured records)');
            await storage.saveEventLog([]);
            await storage.setConfig('event_log_version', '2');
            return;
        }

        // Reconstruct stream DOM from structured records
        if (typeof streamEl.replaceChildren === 'function') {
            streamEl.replaceChildren();
        } else {
            while (streamEl.firstChild) streamEl.removeChild(streamEl.firstChild);
        }

        let currentCard: HTMLElement | null = null;
        let currentCardKey = '';
        let maxSeq = -1;

        for (const rec of entries as PersistedStreamRecord[]) {
            if (!rec) continue;
            if (rec.seq !== undefined && Number.isFinite(rec.seq)) {
                maxSeq = Math.max(maxSeq, rec.seq);
            }

            const inCard = rec.turn != null && Boolean(rec.card_actor || rec.actor);
            const cardKey = inCard ? `${rec.turn}:${rec.card_actor || rec.actor}` : '';

            if (inCard) {
                if (!currentCard || currentCardKey !== cardKey) {
                    const card = document.createElement('div');
                    card.className = 'turn-card';
                    const cardActor = rec.card_actor || rec.actor;
                    card.setAttribute('data-actor', cardActor);
                    const collapsed = Boolean(rec.card_collapsed);

                    const header = document.createElement('div');
                    header.className = 'turn-card-header';
                    const collapseSpan = document.createElement('span');
                    collapseSpan.className = 'turn-card-collapse';
                    collapseSpan.textContent = collapsed ? '▸' : '▾';
                    const actorSpan = document.createElement('span');
                    actorSpan.className = 'turn-card-actor';
                    actorSpan.textContent = cardActor;
                    const tickSpan = document.createElement('span');
                    tickSpan.className = 'turn-card-tick';
                    tickSpan.textContent = `[Turn ${rec.turn}${rec.day ? ` | ${rec.day}` : ''}]`;
                    header.appendChild(collapseSpan);
                    header.appendChild(actorSpan);
                    header.appendChild(tickSpan);

                    const body = document.createElement('div');
                    body.className = 'turn-card-body';
                    if (collapsed) body.style.display = 'none';

                    card.appendChild(header);
                    card.appendChild(body);
                    streamEl.appendChild(card);
                    currentCard = card;
                    currentCardKey = cardKey;
                }
            } else {
                currentCard = null;
                currentCardKey = '';
            }

            const targetContainer: HTMLElement = currentCard
                ? (currentCard.querySelector('.turn-card-body') as HTMLElement || streamEl)
                : streamEl;

            // Render element according to record type
            if (rec.type === 'scope') {
                const banner = document.createElement('div');
                banner.className = 'stream-scope-banner';
                if (rec.area) banner.setAttribute('data-stream-area', rec.area);
                const sp = document.createElement('span');
                sp.textContent = rec.text || '';
                banner.appendChild(sp);
                targetContainer.appendChild(banner);
                continue;
            }

            if (rec.type === 'scope-empty') {
                const empty = document.createElement('div');
                empty.className = 'stream-scope-empty';
                empty.textContent = rec.text || '';
                targetContainer.appendChild(empty);
                continue;
            }

            if (rec.type === 'time-gap' || (rec.type === 'system' && (rec.text || '').includes('minutes pass'))) {
                const gap = document.createElement('div');
                gap.className = 'time-gap';
                gap.textContent = rec.text || '';
                targetContainer.appendChild(gap);
                continue;
            }

            if (rec.payload) {
                // Raw-LLM chip
                const chip = document.createElement('div');
                chip.className = 'msg-bubble msg-bubble-rawllm';
                chip.setAttribute('data-actor', rec.actor || 'LLM');
                chip.setAttribute('data-tick', String(rec.tick ?? 0));
                chip.setAttribute('data-type', 'rawllm');
                if (rec.area) chip.setAttribute('data-stream-area', rec.area);
                if (rec.seq !== undefined && rec.seq >= 0) chip.setAttribute('data-seq', String(rec.seq));
                if (rec.actor_id) chip.setAttribute('data-actor-id', rec.actor_id);
                if (rec.request_id) chip.setAttribute('data-request-id', rec.request_id);
                if (rec.phase) chip.setAttribute('data-phase', rec.phase);

                window.Lit.render(window.Lit.html`
                    <span class="bubble-icon">🤖</span>
                    <span class="bubble-tick">[Tick ${rec.tick}${rec.time ? ` | ${rec.time}` : ''}]</span>
                    <span class="bubble-actor bubble-rawllm-actor">${rec.actor || 'LLM'}</span>
                    <span class="rawllm-chip-header" style="cursor:pointer;font-size:11px;color:var(--text-muted);">${rec.payload.header || 'LLM payload'}</span>
                    <div class="rawllm-chip-body" style="display:none;font-family:monospace;font-size:10px;white-space:pre-wrap;background:var(--bg-input);padding:6px;border-radius:4px;margin-top:4px;">${rec.payload.body || ''}</div>
                `, chip);

                chip.querySelector('.rawllm-chip-header')?.addEventListener('click', () => {
                    const b = chip.querySelector<HTMLElement>('.rawllm-chip-body');
                    if (b) b.style.display = b.style.display === 'none' ? 'block' : 'none';
                });
                targetContainer.appendChild(chip);
                continue;
            }

            // Message bubble
            const bubble = document.createElement('div');
            let classes = `msg-bubble msg-bubble-${rec.type}`;
            if (rec.outcome) classes += ` outcome-${rec.outcome}`;
            bubble.className = classes;
            if (rec.actor) bubble.setAttribute('data-actor', rec.actor);
            if (rec.tick !== undefined) bubble.setAttribute('data-tick', String(rec.tick));
            bubble.setAttribute('data-type', rec.type || 'action');
            if (rec.area) bubble.setAttribute('data-stream-area', rec.area);
            if (rec.seq !== undefined && rec.seq >= 0) bubble.setAttribute('data-seq', String(rec.seq));
            bubble.dataset.rawText = String(rec.text || '');

            const icon = rec.icon || (rec.type === 'thought' ? '💭' : rec.type === 'speech' ? '💬' : rec.type === 'action' ? '▶️' : '⚙️');
            const outcomeBadge = rec.outcome === 'success' ? '<span class="result-badge ok">✓</span>'
                : rec.outcome === 'failure' ? '<span class="result-badge fail">✕</span>'
                : rec.outcome === 'minor' ? '<span class="result-badge minor">ℹ</span>' : '';

            const shown = (this._bus as any)._gearVisibleText
                ? (this._bus as any)._gearVisibleText(rec.type, rec.text)
                : rec.text;
            const textSpan = window.Lit.unsafeHTML(outcomeBadge + _escStream(shown));

            window.Lit.render(window.Lit.html`
                <span class="bubble-icon">${icon}</span>
                <span class="bubble-tick">[Tick ${rec.tick}${rec.time ? ` | ${rec.time}` : ''}]</span>
                <span class="bubble-actor bubble-${rec.type}-actor">${rec.actor || ''}</span>
                <span class="bubble-text bubble-${rec.type}-text">${textSpan}</span>
            `, bubble);

            targetContainer.appendChild(bubble);
        }

        streamEl.scrollTop = streamEl.scrollHeight;

        if (maxSeq >= 0) {
            this._bus._lineSeq = maxSeq + 1;
        }

        this._bus._cards.rebindAll(streamEl);

        for (const rec of entries as PersistedStreamRecord[]) {
            const name = rec?.actor;
            if (name && name !== '⚙️' && name !== 'World' && !name.startsWith('LLM')) {
                this._bus._knownActors.add(name);
            }
        }

        this._bus._filters.updateAgentFilterDropdown();
        this._bus._filters.restoreSaved();
        this._bus._scrubber?.scheduleRebuild();

        const currentMode = (this._bus as any)._streamMode;
        if (currentMode && typeof (this._bus as any).setStreamMode === 'function') {
            (this._bus as any).setStreamMode(currentMode);
        }
    }
}

(window as unknown as { StreamPersistence: typeof StreamPersistence }).StreamPersistence = StreamPersistence;

/* ── types ──
 * Declared at the BOTTOM deliberately. tsc drops a file's leading JSDoc when
 * the first statement is type-only, and tools/js_module_index.py reads
 * `@module` out of the EMITTED .js - so an `interface` above the first value
 * declaration would silently strip the module contract. */

interface PersistedStreamRecord {
    seq: number;
    tick: number;
    time: string;
    day: string;
    turn: number | null;
    actor: string;
    area: string;
    type: string;
    text: string;
    icon?: string;
    outcome?: string;
    payload?: { header: string; body: string };
    actor_id?: string;
    request_id?: string;
    phase?: string;
    card_actor?: string;
    card_collapsed?: boolean;
}

interface PersistenceBus {
    _lineSeq: number;
    _cards: { rebindAll(streamEl: HTMLElement): void };
    _knownActors: Set<string>;
    _filters: { updateAgentFilterDropdown(): void; restoreSaved(): void };
    _scrubber?: { scheduleRebuild(): void } | null;
}
