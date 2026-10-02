"use strict";
/**
 * stream-turn-cards.js — turn card grouping for the event stream
 *
 * Extracted from event-stream.js (task-340). Loaded BEFORE event-stream.js.
 *
 * @module stream/stream-turn-cards — turn card grouping
 * @contributes StreamTurnCards: group log entries into per-character turn cards
 * @powers Event stream — the collapsible turn cards in the event stream
 * @relates loaded before event-stream.js
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// NOTE: TurnCardBus is declared *below* on purpose — a leading type-only
// statement makes tsc drop this file's leading JSDoc, and js_module_index.py
// reads @module out of the emitted .js. Keep a value declaration first.
class StreamTurnCards {
    _bus;
    current;
    actor;
    constructor(bus) {
        this._bus = bus;
        this.current = null;
        this.actor = null;
    }
    open(charName, streamEl) {
        this.close();
        const card = document.createElement('div');
        card.className = 'turn-card';
        card.setAttribute('data-actor', charName);
        window.Lit.render(window.Lit.html `
            <div class="turn-card-header">
                <span class="turn-card-collapse">▾</span>
                <span class="turn-card-actor">${charName}</span>
                <span class="turn-card-tick">[${this._bus._turnLabel()}]</span>
            </div>
            <div class="turn-card-body"></div>`, card);
        streamEl.appendChild(card);
        this.current = card;
        this.actor = charName;
        this._bindToggle(card);
        this._bus._scrubber?.scheduleRebuild();
    }
    close() {
        this.current = null;
        this.actor = null;
    }
    /** Body of the open card for the given actor. forceNew starts a fresh
     *  card even for the same actor (used at turn-start phase markers). */
    bodyFor(charName, streamEl, forceNew = false) {
        if (forceNew || this.actor !== charName)
            this.open(charName, streamEl);
        return this.current?.querySelector('.turn-card-body') || null;
    }
    _bindToggle(card) {
        card.querySelector('.turn-card-header').addEventListener('click', () => {
            const body = card.querySelector('.turn-card-body');
            const collapse = card.querySelector('.turn-card-collapse');
            if (body) {
                const hidden = body.style.display === 'none';
                body.style.display = hidden ? '' : 'none';
                if (collapse)
                    collapse.textContent = hidden ? '▾' : '▸';
            }
        });
    }
    /** Re-bind collapse handlers after IndexedDB restore. */
    rebindAll(streamEl) {
        for (const card of streamEl.querySelectorAll('.turn-card'))
            this._bindToggle(card);
    }
}
