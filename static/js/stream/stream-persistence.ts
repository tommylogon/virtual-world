/**
 * stream-persistence.js — IndexedDB round-trip for the event stream
 *
 * task-340: persistence cap raised 500 → 2000 (the DOM keeps 5000, so a
 * reload used to silently drop 90% of scrollback). Area filter now survives
 * reloads too. Extracted from event-stream.js; loaded BEFORE it.
 *
 * @module stream/stream-persistence — IndexedDB round-trip for the stream
 * @contributes save/restore of the event stream (cap 2000) + the persisted area filter
 * @powers Event stream — keeping your scrollback across reloads
 * @relates uses storage; loaded before event-stream.js
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// NOTE: PersistenceBus is declared *below* on purpose — a leading type-only
// statement makes tsc drop this file's leading JSDoc, and js_module_index.py
// reads @module out of the emitted .js. Keep a value declaration first.
class StreamPersistence {
    _bus: PersistenceBus;
    CAP: number;
    // Which world the persisted bubbles belong to (see _worldKey).
    _storedWorldKey: string;

    constructor(bus: PersistenceBus) {
        this._bus = bus;
        this.CAP = 2000;
        // Which world the persisted bubbles belong to (see _worldKey).
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

    /** Save current event log HTML to IndexedDB so it survives page refresh */
    async persist(): Promise<void> {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const entries: string[] = [];
        for (const child of streamEl.children) entries.push(child.outerHTML);
        if (entries.length > this.CAP) entries.splice(0, entries.length - this.CAP);

        // The stream is per world. These bubbles carry no world tag, so if the
        // world changed since they were recorded they cannot be salvaged: drop
        // them rather than export one world's log under another's name.
        const worldKey = this._worldKey();
        if (this._storedWorldKey && worldKey && this._storedWorldKey !== worldKey) {
            this._storedWorldKey = worldKey;
            await storage.saveEventLog([]);
            await storage.setConfig('event_log_world', worldKey);
            return;
        }
        this._storedWorldKey = worldKey;
        await storage.saveEventLog(entries);
        if (worldKey) await storage.setConfig('event_log_world', worldKey);
    }

    /** Restore event log from IndexedDB */
    async restore(): Promise<void> {
        if (!window.Lit) return;
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;

        const worldKey = this._worldKey();
        this._storedWorldKey = worldKey;
        let savedWorldKey = '';
        try { savedWorldKey = await storage.getConfig('event_log_world') || ''; } catch (err) { savedWorldKey = ''; }
        if (savedWorldKey && worldKey && savedWorldKey !== worldKey) {
            // Left over from another world: do not restore it into this one.
            await storage.saveEventLog([]);
            await storage.setConfig('event_log_world', worldKey);
            return;
        }

        const entries: string[] = await storage.loadEventLog();
        if (entries.length === 0) return;

        window.Lit.render(window.Lit.html`${entries.map(e => window.Lit.unsafeHTML(e))}`, streamEl);
        streamEl.scrollTop = streamEl.scrollHeight;
        let maxSeq = -1;
        for (const el of streamEl.querySelectorAll('.bubble-tick')) {
            const m = el.textContent.match(/\[Tick\s+(\d+)\|/);
            if (m) maxSeq = Math.max(maxSeq, parseInt(m[1], 10));
        }
        this._bus._lineSeq = maxSeq + 1;
        this._bus._cards.rebindAll(streamEl);
        for (const actorEl of streamEl.querySelectorAll('.bubble-actor, .turn-card-actor, .thought-actor, .bubble-phase-actor, .bubble-rawllm-actor')) {
            const name = actorEl.textContent.trim();
            if (name && name !== '⚙️' && !name.startsWith('LLM')) {
                this._bus._knownActors.add(name);
            }
        }
        this._bus._filters.updateAgentFilterDropdown();
        this._bus._filters.restoreSaved();
        this._bus._scrubber?.scheduleRebuild();
    }
}

interface PersistenceBus {
    _lineSeq: number;
    _cards: { rebindAll(streamEl: HTMLElement): void };
    _knownActors: Set<string>;
    _filters: { updateAgentFilterDropdown(): void; restoreSaved(): void };
    _scrubber?: { scheduleRebuild(): void } | null;
}
