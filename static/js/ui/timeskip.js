/**
 * timeskip — the wait/mingle/search/explore/travel dialog (task-464).
 *
 * @module ui/timeskip — intent + duration dialog over POST /api/world/timeskip
 * @contributes Timeskip.openDialog/closeDialog/run + a best-effort summary render
 * @powers the "⏩ Wait / Timeskip…" menu item
 * @relates posts via ApiClient and refreshes window.worldState afterwards
 * @docs docs/virtualWorld/dev_tasks/inprogress/gameplay/task-464-timeskip-actions-idle-leisure-search-explore-travel.md
 *
 * The dialog only collects an intent and a span; the engine decides everything
 * else (policy, interrupts, consequences). A timeskip is never "safe": vitals
 * decay and the world runs its minute-by-minute clock.
 */
window.Timeskip = (() => {
    'use strict';

    const PRESETS = { '30m': 30, '1h': 60, '2h': 120, '4h': 240, '8h': 480 };
    const DEFAULT_PRESET = '2h';

    /** Minutes for a preset key ('2h'), or null. */
    function presetMinutes(key) {
        return Object.prototype.hasOwnProperty.call(PRESETS, key) ? PRESETS[key] : null;
    }

    function _el(id) { return document.getElementById(id); }

    function _setStatus(text) {
        const el = _el('timeskip-status');
        if (el) el.textContent = text || '';
    }

    function _selected(name) {
        const el = document.querySelector(`input[name="${name}"]:checked`);
        return el ? el.value : null;
    }

    /** Resolve the dialog's span in minutes (custom overrides the preset). */
    function _minutes() {
        const custom = _el('timeskip-minutes');
        const value = custom ? Number(custom.value) : 0;
        if (value > 0) return Math.round(value);
        const preset = _el('timeskip-preset');
        return presetMinutes(preset ? preset.value : DEFAULT_PRESET) || 120;
    }

    function _text(id) {
        const el = _el(id);
        return el && el.value ? String(el.value).trim() : '';
    }

    function _payload() {
        const payload = {
            intent: _selected('timeskip-intent') || 'idle',
            minutes: _minutes(),
        };
        const target = _text('timeskip-target');
        if (target) payload.target = target;
        const heading = _text('timeskip-heading');
        if (heading) payload.heading = heading;
        const tags = _text('timeskip-tags');
        if (tags) {
            payload.watch_tags = tags.split(',').map((t) => t.trim()).filter(Boolean);
        }
        return payload;
    }

    function openDialog() {
        const modal = _el('timeskip-modal');
        if (!modal) return;
        _setStatus('');
        const result = _el('timeskip-result');
        if (result) { result.textContent = ''; result.style.display = 'none'; }
        modal.style.display = 'flex';
    }

    function closeDialog() {
        const modal = _el('timeskip-modal');
        if (modal) modal.style.display = 'none';
    }

    function _round(value) {
        return typeof value === 'number' ? Math.round(value * 10) / 10 : value;
    }

    function _renderSummary(data) {
        const box = _el('timeskip-result');
        if (!box) return;
        const lines = [];
        lines.push(`Elapsed: ${data.elapsed_minutes} min (${data.ticks} ticks) → ${data.clock_after || ''}`);
        if (data.interrupted && data.interrupt) {
            lines.push(`Interrupted: ${data.interrupt.detail || data.interrupt.why}`);
        }
        const before = data.vitals_before || {};
        const after = data.vitals_after || {};
        const changed = Object.keys(after).filter(
            (k) => before[k] !== undefined && before[k] !== after[k]);
        if (changed.length) {
            lines.push('Vitals: ' + changed
                .map((k) => `${k} ${_round(before[k])}→${_round(after[k])}`)
                .join(', '));
        }
        if (data.lines && data.lines.length) {
            lines.push('');
            lines.push(...data.lines.slice(-8));
        }
        box.textContent = lines.join('\n');
        box.style.display = 'block';
    }

    async function run() {
        const button = _el('timeskip-go');
        if (button) button.disabled = true;
        _setStatus('Advancing the world minute by minute…');
        try {
            const data = await ApiClient.post('/api/world/timeskip', _payload());
            if (!data || data.error || data.ok === false) {
                _setStatus('⚠ ' + ((data && (data.error || data.reason)) || 'Timeskip failed.'));
                return;
            }
            _setStatus('');
            _renderSummary(data);
            if (window.worldState && typeof worldState.fetch === 'function') {
                try { await worldState.fetch(); } catch (e) { /* non-fatal */ }
            }
        } catch (e) {
            _setStatus('⚠ ' + (e && e.message ? e.message : e));
        } finally {
            if (button) button.disabled = false;
        }
    }

    return {
        openDialog,
        closeDialog,
        run,
        // Pure logic exposed for tools/unit/run.cjs. Not a product API.
        _internals: { presetMinutes },
    };
})();
