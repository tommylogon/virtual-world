/**
 * stream-persistence.js — IndexedDB round-trip for the event stream
 *
 * task-340: persistence cap raised 500 → 2000 (the DOM keeps 5000, so a
 * reload used to silently drop 90% of scrollback). Area filter now survives
 * reloads too. Extracted from event-stream.js; loaded BEFORE it.
 */
class StreamPersistence {
    constructor(bus) {
        this._bus = bus;
        this.CAP = 2000;
    }

    /** Save current event log HTML to IndexedDB so it survives page refresh */
    async persist() {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const entries = [];
        for (const child of streamEl.children) entries.push(child.outerHTML);
        if (entries.length > this.CAP) entries.splice(0, entries.length - this.CAP);
        await storage.saveEventLog(entries);
    }

    /** Restore event log from IndexedDB */
    async restore() {
        if (!window.Lit) return;
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const entries = await storage.loadEventLog();
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
