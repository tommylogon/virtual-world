/**
 * timeskip — the wait/mingle/search/explore/travel dialog (task-464).
 *
 * @module ui/timeskip — intent + duration dialog over POST /api/world/timeskip
 * @contributes Timeskip.openDialog/closeDialog/run + a best-effort summary render
 * @powers the "⏩ Wait / Timeskip…" menu item
 * @relates posts via ApiClient and refreshes window.worldState afterwards
 * @docs Simulation Model.md
 *
 * The dialog only collects an intent and a span; the engine decides everything
 * else (policy, interrupts, consequences). A timeskip is never "safe": vitals
 * decay and the world runs its minute-by-minute clock.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.Timeskip = (() => {
    'use strict';

    const PRESETS: Record<string, number> = { '30m': 30, '1h': 60, '2h': 120, '4h': 240, '8h': 480 };
    const DEFAULT_PRESET = '2h';

    interface TimeskipPayloadInput {
        intent?: string | null;
        customMinutes?: string | number | null;
        preset?: string | null;
        target?: string | null;
        heading?: string | null;
        tags?: string | null;
    }

    /** Minutes for a preset key ('2h'), or null. */
    function presetMinutes(key: string | null | undefined): number | null {
        return key != null && Object.prototype.hasOwnProperty.call(PRESETS, key) ? PRESETS[key] : null;
    }

    // One id-lookup helper used against inputs, selects, textareas and plain
    // divs. A union return type made every .value/.disabled access an error at
    // the call site instead of here, so it is ny - the honest annotation
    // for a helper whose element type varies by id.
    function _el(id: string): any {
        return document.getElementById(id);
    }

    function _setStatus(text: string): void {
        const el = _el('timeskip-status');
        if (el) el.textContent = text || '';
    }

    function _selected(name: string): string | null {
        const el = document.querySelector<HTMLInputElement>(`input[name="${name}"]:checked`);
        return el ? el.value : null;
    }

    function _text(id: string): string {
        const el = _el(id);
        return el && el.value ? String(el.value).trim() : '';
    }

    /**
     * Build the request body. Travel to a target takes its span from the route
     * (the server computes it) unless the user typed an explicit duration, so a
     * long fast-travel is not cut short by a 2 h preset.
     */
    function _buildPayload({ intent, customMinutes, preset, target, heading, tags }: TimeskipPayloadInput): Record<string, unknown> {
        const payload: Record<string, unknown> = { intent: intent || 'idle' };
        const custom = Number(customMinutes) > 0 ? Math.round(Number(customMinutes)) : 0;
        const routedTravel = payload.intent === 'travel' && !!target && !custom;
        const until = String(preset || '').indexOf('until:') === 0
            ? String(preset).slice(6) : null;
        if (!routedTravel) {
            if (custom) payload.minutes = custom;
            else if (until) payload.until = until;
            else payload.minutes = presetMinutes(preset) || 120;
        }
        if (target) payload.target = target;
        if (heading) payload.heading = heading;
        if (tags) {
            payload.watch_tags = String(tags).split(',').map((t) => t.trim()).filter(Boolean);
        }
        return payload;
    }

    function _payload() {
        const preset = _el('timeskip-preset');
        return _buildPayload({
            intent: _selected('timeskip-intent') || 'idle',
            customMinutes: _el('timeskip-minutes') ? _el('timeskip-minutes').value : 0,
            preset: preset ? preset.value : DEFAULT_PRESET,
            target: _text('timeskip-target'),
            heading: _text('timeskip-heading'),
            tags: _text('timeskip-tags'),
        });
    }

    function _activeCharacter() {
        try {
            if (window.worldState && worldState.data) {
                return worldState.data.active_player || null;
            }
        } catch (e) { /* ignore */ }
        return null;
    }

    /**
     * With no active character there is no one to stand in for, so the dialog
     * drops the intent/target fields and the request becomes a world advance:
     * every character is soak and the clock simply runs.
     */
    function _setWorldMode(on: boolean): void {
        ['timeskip-intent-block', 'timeskip-target-block', 'timeskip-tags-block']
            .forEach((id) => {
                const el = _el(id);
                if (el) el.style.display = on ? 'none' : '';
            });
        const go = _el('timeskip-go');
        if (go) go.textContent = on ? '⏩ Advance world' : '⏩ Skip';
        if (on) {
            _setStatus('No active character — this advances the world with everyone in soak mode.');
        }
    }

    function openDialog() {
        const modal = _el('timeskip-modal');
        if (!modal) return;
        _setStatus('');
        const result = _el('timeskip-result');
        if (result) { result.textContent = ''; result.style.display = 'none'; }
        _setWorldMode(!_activeCharacter());
        modal.style.display = 'flex';
    }

    function closeDialog() {
        const modal = _el('timeskip-modal');
        if (modal) modal.style.display = 'none';
    }

    function _round(value: number): number {
        return typeof value === 'number' ? Math.round(value * 10) / 10 : value;
    }

    /**
     * A shared world cannot block on one character's span: the handler hands it to
     * the turn loop as a soak order and returns at once, so that envelope carries
     * an order and no elapsed figures at all. Printing the elapsed line for it is
     * what produced "Elapsed: undefined min (undefined ticks)".
     */
    function _soakLines(order: any): string[] {
        const who = _activeCharacter() || 'The character';
        const span = _round(order.declared_minutes);
        const lines = [`Soak order for ${who}: ${span} min of ${order.intent || 'idle'}`];
        const where = [order.target, order.heading].filter(Boolean).join(' · ');
        if (where) lines[0] += ` toward ${where}`;
        if (order.watch_tags && order.watch_tags.length) {
            lines.push(`Watching for: ${order.watch_tags.join(', ')}`);
        }
        lines.push('It runs on their turn, so the clock advances then — not now.');
        lines.push('Control comes back early if something demands their attention.');
        return lines;
    }

    /** Summary lines for a timeskip response. Pure, so it is unit-testable. */
    function _summarize(data: any): string[] {
        const lines = [];
        if (data.mode === 'world') {
            lines.push('No active character — the world advances.');
        }
        if (data.mode === 'soak') {
            lines.push(..._soakLines(data.order || {}));
        } else {
            lines.push(`Elapsed: ${data.elapsed_minutes} min (${data.ticks} ticks) → ${data.clock_after || ''}`);
        }
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
        return lines;
    }

    function _renderSummary(data: any): void {
        const box = _el('timeskip-result');
        if (!box) return;
        box.textContent = _summarize(data).join('\n');
        box.style.display = 'block';
    }

    async function run() {
        const button = _el('timeskip-go');
        if (button) button.disabled = true;
        const worldMode = !_activeCharacter();
        const planned = _payload();
        const body = worldMode
            ? ((planned.minutes !== undefined || planned.until !== undefined)
                ? Object.assign({}, planned.minutes !== undefined ? { minutes: planned.minutes } : {},
                    planned.until !== undefined ? { until: planned.until } : {})
                : { minutes: 120 })
            : planned;
        _setStatus(worldMode
            ? 'Advancing the world with everyone in soak mode…'
            : 'Advancing the world minute by minute…');
        try {
            const data = await (ApiClient as unknown as { post(p: string, b: unknown): Promise<any> }).post('/api/world/timeskip', body);
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
            _setStatus('⚠ ' + (e instanceof Error ? e.message : String(e)));
        } finally {
            if (button) button.disabled = false;
        }
    }

    return {
        openDialog,
        closeDialog,
        run,
        // Pure logic exposed for tools/unit/run.cjs. Not a product API.
        _internals: { presetMinutes, buildPayload: _buildPayload, summarize: _summarize },
    };
})();
