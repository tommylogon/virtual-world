/**
 * turn-feed.js — "What happened" feed + since-your-turn digest for the
 * human turn panel (task-333 full redesign; digest = task-334 lane 2).
 *
 * Subscribes to the app event bus ('log' emissions from event-stream.js)
 * and keeps a small ring buffer. The panel renders the tail as its feed;
 * entries emitted between two panel opens form the turn-start digest.
 * Interjection (lane 3) posts guest speech through the normal command
 * path without touching turn state.
 *
 * Load AFTER event-stream.js, BEFORE human-turn-composer.js.
 */

window.TurnFeed = (() => {
    'use strict';

    const MAX = 60;
    const _ring = [];
    let _seq = 0;
    let _digestMark = 0;
    let _installed = false;

    function install() {
        if (_installed) return;
        if (typeof events === 'undefined' || typeof events.on !== 'function') return;
        events.on('log', (data) => {
            const text = String((data && data.text) ?? '').trim();
            if (!text) return;
            _ring.push({ text, className: (data && data.className) || '', seq: ++_seq });
            if (_ring.length > MAX) _ring.shift();
        });
        _installed = true;
    }

    /** Render the last *limit* entries into *host* (plain DOM). */
    function render(host, limit = 14) {
        install();
        host.textContent = '';
        const tail = _ring.slice(-limit);
        if (!tail.length) {
            const empty = document.createElement('div');
            empty.className = 'tfd-line tfd-empty';
            empty.textContent = 'nothing yet — the world is quiet.';
            host.appendChild(empty);
            return;
        }
        for (const entry of tail) {
            const line = document.createElement('div');
            line.className = 'tfd-line';
            if (entry.className.includes('error')) line.classList.add('tfd-err');
            else if (entry.className.includes('action')) line.classList.add('tfd-act');
            else if (entry.className.includes('system')) line.classList.add('tfd-sys');
            line.textContent = entry.text;
            host.appendChild(line);
        }
    }

    /** Mark the boundary for "since your turn" (call when the panel closes). */
    function markTurnEnd() {
        install();
        _digestMark = _seq;
    }

    /** Entries logged since the last markTurnEnd() — the turn-start digest. */
    function digest() {
        install();
        return _ring.filter((e) => e.seq > _digestMark);
    }

    function clearDigest() { _digestMark = _seq; }

    return { render, markTurnEnd, digest, clearDigest };
})();
