/**
 * event-log-export.js — projected event-log export: Markdown, Plain, JSON and
 * JSONL, behind one consolidated export modal (tick-sequence range, actor and
 * area scope, format, destination, filter honesty).
 *
 * Reads only what the stream DOM already carries — `data-seq`, `data-actor`,
 * `data-tick`, `data-type`, `data-stream-area` and `dataset.rawText` — so there
 * is no second event model: the client stream stays the source of truth.
 *
 * Dependencies:
 *   - window.events (EventBus; `_knownActors` roster)
 *   - window.worldState (world clock, scenario name)
 *   - window.WorldExport.saveFileWithDialog (native save / download fallback)
 *   - Global: toastInfo, toastError
 *   - DOM: #event-stream and the stream toolbar filter controls
 *
 * @module ui/event-log-export — projected event-log export
 * @contributes EventLogExport: DOM→record projection, Markdown/Plain/JSON/JSONL renderers,
 *   the consolidated export modal, and filter-honest range/scope selection
 * @powers Export — the event-log half: the DOM→record projection, the four renderers
 *   and the export modal; queryable (jq-able) export without the app running
 * @relates reads the stream DOM; called by ui/world-export; uses WorldExport.saveFileWithDialog
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */

(window as unknown as { EventLogExport: unknown }).EventLogExport = (() => {
    'use strict';

    type Format = 'markdown' | 'plain' | 'json' | 'jsonl';
    type Unit = 'tick' | 'turn';
    type Destination = 'file' | 'clipboard';

    /** One projected stream row. `seq` is -1 for non-ticked metadata rows. */
    interface StreamEvent {
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
        /**
         * Trace correlation. `actorId` is the character the LLM call was FOR
         * (the stream's `actor` column is a display label and can disagree);
         * `requestId` pairs a request chip with its response chip; `phase` is
         * the turn phase. Present on LLM rows, absent elsewhere.
         */
        actor_id?: string;
        request_id?: string;
        phase?: string;
    }

    interface ProjectOpts { ignoreFilters?: boolean }

    interface FiltersBlock {
        actor: string | null;
        area: string | null;
        search: string;
        ignored: boolean;
        kinds: Record<string, boolean>;
    }

    interface ExportOpts {
        unit: Unit;
        from: number | null;
        to: number | null;
        actors: string[];
        area: string | null;
        format: Format;
        ignoreFilters: boolean;
    }

    interface RenderMeta {
        scenario: string;
        exportedAt: string;
        worldTick: number;
        unit: Unit;
        from: number | null;
        to: number | null;
        filters: FiltersBlock;
        /** Human line for the markdown/plain header, e.g. `ticks 12–340 · 412 rows`. */
        line: string;
    }

    const EXT: Record<Format, string> = { markdown: 'md', plain: 'txt', json: 'json', jsonl: 'jsonl' };
    const MIME: Record<Format, string> = {
        markdown: 'text/markdown', plain: 'text/plain',
        json: 'application/json', jsonl: 'application/x-ndjson'
    };
    // Rows that are stream chrome / metadata rather than ticked events.
    const META_SEQ = -1;

    // ───────────────────────────── helpers ─────────────────────────────

    function clean(t: unknown): string {
        return String(t == null ? '' : t).replace(/[\t\r]+/g, ' ').replace(/\s+/g, ' ').trim();
    }

    function scenarioName(): string {
        return ((document.body.dataset.scenarioName || 'unnamed').trim()) || 'unnamed';
    }

    function nowStamp(): string {
        return new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    }

    function intAttr(el: Element | null, name: string): number {
        if (!el) return 0;
        const v = parseInt(el.getAttribute(name) || '', 10);
        return Number.isFinite(v) ? v : 0;
    }

    function firstText(root: Element | null, selector: string): string {
        const el = root ? root.querySelector(selector) : null;
        return el ? clean(el.textContent) : '';
    }

    function inRange(value: number | null, from: number | null, to: number | null): boolean {
        if (value == null) return false;
        if (from != null && value < from) return false;
        if (to != null && value > to) return false;
        return true;
    }

    /** Active stream filters, read live off the toolbar — the honesty block. */
    function activeFilters(ignored: boolean): FiltersBlock {
        const cfg = (window as unknown as { config?: Record<string, unknown> }).config || {};
        const actorEl = document.getElementById('stream-agent-filter') as HTMLInputElement | null;
        const searchEl = document.getElementById('stream-search') as HTMLInputElement | null;
        const areaFilter = (() => {
            try { return localStorage.getItem('vw_area_filter') || ''; } catch (e) { return ''; }
        })();
        return {
            actor: (actorEl && actorEl.value) || null,
            area: areaFilter || null,
            search: clean(searchEl && searchEl.value),
            ignored: ignored,
            kinds: {
                thoughts: cfg.filterThoughts !== false,
                speech: cfg.filterSpeech !== false,
                actions: cfg.filterActions !== false,
                recalls: cfg.filterRecalls !== false,
                npc: cfg.filterNpc !== false,
                system: cfg.filterSystem !== false,
                rawLLM: cfg.filterRawLLM !== false
            }
        };
    }

    // ───────────────────────────── projection ─────────────────────────────

    /**
     * Walk the event-stream DOM and produce a structured record per visible row.
     * Skips filter-hidden rows unless `ignoreFilters` is set; skips the
     * timeline-scrubber and turn-queue-strip (chrome); projects the scope banner
     * and scope-empty note as messages (their label span, never the container
     * `textContent`, so the clear button's `×` is not glued on).
     */
    function projectStreamRows(streamEl: HTMLElement, opts?: ProjectOpts): StreamEvent[] {
        const ignore = !!(opts && opts.ignoreFilters);
        const out: StreamEvent[] = [];
        let fallbackSeq = 1;

        function visible(el: HTMLElement): boolean {
            return ignore || el.style.display !== 'none';
        }

        function seqOf(bubble: HTMLElement): number {
            const attr = parseInt(bubble.getAttribute('data-seq') || '', 10);
            if (Number.isFinite(attr)) return attr;
            const m = firstText(bubble, '.bubble-tick').match(/Tick\s+(\d+)/);
            if (m) return parseInt(m[1], 10);
            return fallbackSeq++;
        }

        function typeOf(bubble: HTMLElement): string {
            const dt = bubble.getAttribute('data-type');
            if (dt) return dt;
            const cls = Array.from(bubble.classList)
                .find((c) => c.startsWith('msg-bubble-') && c !== 'msg-bubble');
            return cls ? cls.replace('msg-bubble-', '') : 'event';
        }

        function record(bubble: HTMLElement, turn: number | null, day: string): StreamEvent | null {
            if (!visible(bubble)) return null;
            const isRaw = bubble.classList.contains('msg-bubble-rawllm');
            const textEl = bubble.querySelector('.bubble-text') || bubble.querySelector('.bubble-phase-pill');
            const rawText = bubble.dataset ? bubble.dataset.rawText : undefined;
            // Raw-LLM chips have no `.bubble-text`; their meaningful text is the
            // header. Falling back to `bubble.textContent` would glue the
            // collapsed payload body on (the same trap the scope banner had).
            const text = clean(isRaw
                ? firstText(bubble, '.rawllm-chip-header')
                : (rawText != null ? rawText : (textEl ? textEl.textContent : bubble.textContent)));
            if (!text) return null;
            const tickText = firstText(bubble, '.bubble-tick');
            const timeM = tickText.match(/(\d{1,2}:\d{2})/);
            let outcome: string | undefined;
            for (const o of ['success', 'failure', 'minor']) {
                if (bubble.classList.contains('outcome-' + o)) { outcome = o; break; }
            }
            let payload: { header: string; body: string } | undefined;
            if (bubble.classList.contains('msg-bubble-rawllm')) {
                const bodyEl = bubble.querySelector('.rawllm-chip-body');
                payload = {
                    header: firstText(bubble, '.rawllm-chip-header') || 'LLM payload',
                    body: bodyEl ? String(bodyEl.textContent || '').trim() : ''
                };
            }
            const actor = clean(bubble.getAttribute('data-actor')) ||
                firstText(bubble, '.bubble-actor') || firstText(bubble, '.bubble-thought-actor') ||
                firstText(bubble, '.bubble-rawllm-actor') || firstText(bubble, '.bubble-phase-actor');
            return {
                seq: seqOf(bubble),
                tick: intAttr(bubble, 'data-tick'),
                time: timeM ? timeM[1] : '',
                day: day,
                turn: turn,
                actor: actor,
                area: clean(bubble.getAttribute('data-stream-area')),
                type: typeOf(bubble),
                text: text,
                icon: isRaw ? undefined : (firstText(bubble, '.bubble-icon') || undefined),
                outcome: outcome,
                payload: payload,
                actor_id: clean(bubble.getAttribute('data-actor-id')) || undefined,
                request_id: clean(bubble.getAttribute('data-request-id')) || undefined,
                phase: clean(bubble.getAttribute('data-phase')) || undefined,
            };
        }

        function metaRow(type: string, text: string, area: string): StreamEvent {
            return {
                seq: META_SEQ, tick: 0, time: '', day: '', turn: null, actor: '',
                area: area, type: type, text: text
            };
        }

        function chromeRow(node: HTMLElement, turn: number | null, day: string): StreamEvent | null {
            if (!visible(node)) return null;
            const text = clean(node.textContent);
            if (!text) return null;
            return {
                seq: META_SEQ, tick: intAttr(node, 'data-tick'), time: '', day: day, turn: turn,
                actor: clean(node.getAttribute('data-actor')), area: clean(node.getAttribute('data-stream-area')),
                type: 'system', text: text
            };
        }

        for (let i = 0; i < streamEl.children.length; i++) {
            const child = streamEl.children[i] as HTMLElement;
            if (!child) continue;
            if (child.classList.contains('timeline-scrubber')) continue;
            if (child.classList.contains('turn-queue-strip')) continue;

            if (child.classList.contains('stream-scope-banner')) {
                if (visible(child)) {
                    const labelEl = child.querySelector('span');
                    const label = clean(labelEl ? labelEl.textContent : child.textContent);
                    if (label) out.push(metaRow('scope', label, clean(child.getAttribute('data-stream-area'))));
                }
                continue;
            }
            if (child.classList.contains('stream-scope-empty')) {
                if (visible(child)) out.push(metaRow('scope-empty', clean(child.textContent), ''));
                continue;
            }

            if (child.classList.contains('turn-card')) {
                const cardVisible = visible(child);
                const header = firstText(child, '.turn-card-tick');
                const turnM = header.match(/Turn\s+(\d+)/);
                const turn = turnM ? parseInt(turnM[1], 10) : null;
                const dayM = header.match(/Day\s+(\d+),\s*Month\s+(\d+),\s*Year\s+(\d+)/);
                const day = dayM ? `Day ${dayM[1]}, Month ${dayM[2]}, Year ${dayM[3]}` : '';
                const body = child.querySelector('.turn-card-body');
                if (!body) continue;
                for (let b = 0; b < body.children.length; b++) {
                    const node = body.children[b] as HTMLElement;
                    if (!node) continue;
                    if (!cardVisible && !ignore) continue; // whole card hidden by a filter
                    if (node.classList.contains('msg-bubble')) {
                        const rec = record(node, turn, day);
                        if (rec) out.push(rec);
                    } else if (node.classList.contains('time-gap') || node.classList.contains('area-transition')) {
                        const rec = chromeRow(node, turn, day);
                        if (rec) out.push(rec);
                    }
                }
                continue;
            }

            if (child.classList.contains('msg-bubble')) {
                const rec = record(child, null, '');
                if (rec) out.push(rec);
                continue;
            }
            if (child.classList.contains('time-gap') || child.classList.contains('area-transition')) {
                const rec = chromeRow(child, null, '');
                if (rec) out.push(rec);
            }
        }
        return out;
    }

    // ───────────────────────── scope / range selection ─────────────────────────

    /**
     * Apply the modal's range + actor/area scope to a projected row set.
     * `opts.from`/`to` are inclusive bounds in `opts.unit`. Metadata rows
     * (`seq === -1`) survive only when no range is set, so a ticked-range export
     * never claims a `seq` outside the range.
     */
    function applyScope(rows: StreamEvent[], opts: ExportOpts): StreamEvent[] {
        const hasRange = opts.from != null || opts.to != null;
        const actors = opts.actors && opts.actors.length ? opts.actors : null;
        return rows.filter((r) => {
            if (actors && r.actor && actors.indexOf(r.actor) === -1) return false;
            if (actors && !r.actor) return false;
            if (opts.area && r.area !== opts.area) return false;
            if (r.seq === META_SEQ) return !hasRange;
            if (opts.unit === 'tick') return inRange(r.seq, opts.from, opts.to);
            return r.turn != null && inRange(r.turn, opts.from, opts.to);
        });
    }

    /** Inclusive bounds of what the stream contains, in the given unit. */
    function bounds(rows: StreamEvent[], unit: Unit): { min: number; max: number } | null {
        let min = Infinity, max = -Infinity, found = false;
        for (const r of rows) {
            let v: number | null = null;
            if (unit === 'tick') { if (r.seq !== META_SEQ) v = r.seq; }
            else v = r.turn;
            if (v == null) continue;
            found = true;
            if (v < min) min = v;
            if (v > max) max = v;
        }
        return found ? { min: min, max: max } : null;
    }

    // ───────────────────────────── renderers ─────────────────────────────

    function heading(e: StreamEvent): string {
        let h = 'Turn ' + (e.turn == null ? '?' : e.turn);
        if (e.actor) h += ' — ' + e.actor;
        return h;
    }

    function renderMarkdown(rows: StreamEvent[], meta: RenderMeta): string {
        let buf = '# ' + (meta.scenario || 'unnamed') + ' — event log\n\n';
        buf += '> ' + meta.line + '\n\n';
        let openTurn: number | null = -1;
        for (const e of rows) {
            if (e.type === 'scope') { buf += '> **' + e.text + '**\n\n'; continue; }
            if (e.type === 'scope-empty') { buf += '> ' + e.text + '\n\n'; continue; }
            if (e.turn != null && e.turn !== openTurn) {
                buf += '\n## ' + heading(e) + (e.time ? ' · ' + e.time : '') + (e.day ? ' · ' + e.day : '') + '\n\n';
                openTurn = e.turn;
            }
            if (e.type === 'system') { buf += e.text + '\n'; continue; }
            if (e.payload) {
                buf += '- _' + e.payload.header + '_\n';
                if (e.payload.body) {
                    buf += '  <details><summary>payload</summary>\n\n  ```text\n'
                        + e.payload.body.split('\n').map((l) => '  ' + l).join('\n')
                        + '\n  ```\n  </details>\n';
                }
                continue;
            }
            const line = (e.icon ? e.icon + ' ' : '') + (e.actor ? '**' + e.actor + '** — ' : '') + e.text;
            buf += '- ' + line + '\n';
        }
        return buf;
    }

    function renderPlain(rows: StreamEvent[], meta: RenderMeta): string {
        let buf = '';
        let openTurn: number | null = -1;
        for (const e of rows) {
            if (e.type === 'scope' || e.type === 'scope-empty') { buf += e.text + '\n'; continue; }
            if (e.turn != null && e.turn !== openTurn) {
                const h = heading(e);
                buf += '\n' + h + '\n' + new Array(h.length + 1).join('—') + '\n';
                openTurn = e.turn;
            }
            if (e.type === 'system') { buf += e.text + '\n'; continue; }
            buf += (e.actor ? '[' + e.actor + '] ' : '') + e.text + '\n';
        }
        return (meta.scenario ? '== ' + meta.scenario + ' · ' + meta.line + ' ==\n' : '') + buf;
    }

    function ticked(rows: StreamEvent[]): StreamEvent[] {
        return rows.filter((r) => r.seq !== META_SEQ);
    }

    function counts(events: StreamEvent[]): { events: number; turns: number; actors: number; areas: number } {
        const turns = new Set<number>(); const actors = new Set<string>(); const areas = new Set<string>();
        for (const e of events) {
            if (e.turn != null) turns.add(e.turn);
            if (e.actor) actors.add(e.actor);
            if (e.area) areas.add(e.area);
        }
        return { events: events.length, turns: turns.size, actors: actors.size, areas: areas.size };
    }

    function renderJson(rows: StreamEvent[], meta: RenderMeta): string {
        const events = ticked(rows);
        const envelope = {
            schema: 1,
            scenario: meta.scenario,
            exported_at: new Date().toISOString(),
            world_tick: meta.worldTick,
            range: { unit: meta.unit, from: meta.from, to: meta.to },
            filters: meta.filters,
            counts: counts(events),
            events: events
        };
        return JSON.stringify(envelope, null, 2);
    }

    function renderJsonl(rows: StreamEvent[]): string {
        return ticked(rows).map((e) => JSON.stringify(e)).join('\n') + '\n';
    }

    function render(rows: StreamEvent[], meta: RenderMeta, format: Format): string {
        if (format === 'plain') return renderPlain(rows, meta);
        if (format === 'json') return renderJson(rows, meta);
        if (format === 'jsonl') return renderJsonl(rows);
        return renderMarkdown(rows, meta);
    }

    // ───────────────────────────── saving ─────────────────────────────

    async function saveText(text: string, filename: string, mime: string): Promise<void> {
        const blob = new Blob([text], { type: mime + ';charset=utf-8' });
        const we = (window as unknown as {
            WorldExport?: { saveFileWithDialog?: (b: Blob, n: string) => Promise<void> };
        }).WorldExport;
        if (we && typeof we.saveFileWithDialog === 'function') {
            await we.saveFileWithDialog(blob, filename);
            return;
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    async function writeClipboard(text: string): Promise<void> {
        try {
            await navigator.clipboard.writeText(text);
        } catch (e) {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
    }

    // ───────────────────────── legacy entry points ─────────────────────────

    /**
     * Build a log for a turn range (legacy `WorldExport.buildRangeLog` shape).
     * Returns the rendered text plus the count of included turns, or an error.
     */
    function buildRangeLog(scenarioNameIn: string, fromTurn: number, toTurn: number, ts: string,
        format: string): { text: string; turns: number } | { error: string; text?: undefined; turns?: undefined } {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return { error: 'Event stream not found.' };
        const rows = projectStreamRows(streamEl, { ignoreFilters: false });
        const fmt: Format = format === 'plain' ? 'plain' : 'markdown';
        const opts: ExportOpts = {
            unit: 'turn', from: fromTurn, to: toTurn, actors: [], area: null,
            format: fmt, ignoreFilters: false
        };
        const scoped = applyScope(rows, opts);
        if (!scoped.some((r) => r.turn != null)) return { error: 'No turns in range ' + fromTurn + '–' + toTurn + '.' };
        const meta: RenderMeta = {
            scenario: scenarioNameIn, exportedAt: ts, worldTick: (window as unknown as { worldState?: any }).worldState?.tick || 0,
            unit: 'turn', from: fromTurn, to: toTurn, filters: activeFilters(false),
            line: 'turns ' + fromTurn + '–' + toTurn
        };
        return { text: render(scoped, meta, fmt), turns: scoped.filter((r) => r.turn != null).length };
    }

    // ───────────────────────────── the modal ─────────────────────────────

    interface Preset { destination?: Destination; unit?: Unit; focusRange?: boolean }

    function showExportModal(preset?: Preset): void {
        preset = preset || {};
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) { toastError('Event stream not found.'); return; }
        const allRows = projectStreamRows(streamEl, { ignoreFilters: true });

        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:15000;';
        const box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px;width:440px;max-height:90vh;overflow:auto;display:flex;flex-direction:column;gap:10px;';
        overlay.appendChild(box);
        document.body.appendChild(overlay);

        const header = document.createElement('h3');
        header.style.cssText = 'margin:0;font-size:14px;';
        header.textContent = '📤 Export event log';

        // unit
        const unitSel = document.createElement('select');
        ([['tick', 'Tick sequence'], ['turn', 'Turn']] as Array<[Unit, string]>).forEach(([v, label]) => {
            const o = document.createElement('option'); o.value = v; o.textContent = label; unitSel.appendChild(o);
        });
        unitSel.value = preset.unit || 'tick';

        // from/to
        const fromInput = document.createElement('input');
        fromInput.type = 'number'; fromInput.min = '0'; fromInput.placeholder = 'from';
        const toInput = document.createElement('input');
        toInput.type = 'number'; toInput.min = '0'; toInput.placeholder = 'to (blank = latest)';

        // actor multi-select
        const actorSel = document.createElement('select');
        actorSel.multiple = true; actorSel.size = 4;
        actorSel.style.cssText = 'min-height:64px;';
        const known: string[] = [];
        const busActors = (window as unknown as { events?: { _knownActors?: Set<string> } }).events?._knownActors;
        if (busActors) for (const a of busActors) { if (a && a !== '⚙️' && !a.startsWith('LLM')) known.push(a); }
        known.sort().forEach((a) => {
            const o = document.createElement('option'); o.value = a; o.textContent = a; actorSel.appendChild(o);
        });

        // area select
        const areaSel = document.createElement('select');
        const areas: string[] = [];
        const areaSeen: Record<string, boolean> = {};
        for (const r of allRows) { if (r.area && !areaSeen[r.area]) { areaSeen[r.area] = true; areas.push(r.area); } }
        const allOpt = document.createElement('option'); allOpt.value = ''; allOpt.textContent = 'All areas'; areaSel.appendChild(allOpt);
        areas.sort().forEach((a) => { const o = document.createElement('option'); o.value = a; o.textContent = a; areaSel.appendChild(o); });

        // format
        const formatSel = document.createElement('select');
        ([['markdown', 'Markdown'], ['plain', 'Plain lines'], ['json', 'JSON'], ['jsonl', 'JSONL']] as Array<[Format, string]>)
            .forEach(([v, label]) => { const o = document.createElement('option'); o.value = v; o.textContent = label; formatSel.appendChild(o); });

        // destination
        const destSel = document.createElement('select');
        ([['file', 'Save to file'], ['clipboard', 'Copy to clipboard']] as Array<[Destination, string]>)
            .forEach(([v, label]) => { const o = document.createElement('option'); o.value = v; o.textContent = label; destSel.appendChild(o); });
        destSel.value = preset.destination || 'file';

        // ignore filters
        const ignoreWrap = document.createElement('label');
        ignoreWrap.style.cssText = 'display:flex;gap:6px;align-items:center;font-size:12px;';
        const ignoreCb = document.createElement('input'); ignoreCb.type = 'checkbox';
        ignoreWrap.appendChild(ignoreCb);
        ignoreWrap.appendChild(document.createTextNode('Ignore stream filters (include hidden rows)'));

        // summary
        const summary = document.createElement('div');
        summary.style.cssText = 'font-size:11px;color:var(--text-dim);line-height:1.5;';

        function currentOpts(): ExportOpts {
            const actors = Array.from(actorSel.selectedOptions).map((o) => o.value).filter(Boolean);
            return {
                unit: unitSel.value as Unit,
                from: fromInput.value === '' ? null : (parseInt(fromInput.value, 10) || 0),
                to: toInput.value === '' ? null : (parseInt(toInput.value, 10) || 0),
                actors: actors,
                area: areaSel.value || null,
                format: formatSel.value as Format,
                ignoreFilters: ignoreCb.checked
            };
        }

        function targets(): StreamEvent[] {
            const opts = currentOpts();
            const rows = projectStreamRows(streamEl!, { ignoreFilters: opts.ignoreFilters });
            return applyScope(rows, opts);
        }

        function buildMeta(opts: ExportOpts, included: StreamEvent[]): RenderMeta {
            const b = bounds(projectStreamRows(streamEl!, { ignoreFilters: true }), opts.unit);
            const from = opts.from != null ? opts.from : (b ? b.min : null);
            const to = opts.to != null ? opts.to : (b ? b.max : null);
            const unitLabel = opts.unit === 'tick' ? 'ticks' : 'turns';
            return {
                scenario: scenarioName(),
                exportedAt: nowStamp(),
                worldTick: (window as unknown as { worldState?: any }).worldState?.tick || 0,
                unit: opts.unit,
                from: from,
                to: to,
                filters: activeFilters(opts.ignoreFilters),
                line: unitLabel + ' ' + (from == null ? '?' : from) + '–' + (to == null ? '?' : to)
                    + ' · ' + included.length + ' row' + (included.length === 1 ? '' : 's')
            };
        }

        function refreshBounds(): void {
            const b = bounds(allRows, unitSel.value as Unit);
            fromInput.min = '0';
            toInput.min = '0';
            fromInput.placeholder = b ? String(b.min) : 'from';
            toInput.placeholder = b ? ('to (' + b.max + ')') : 'to (blank = latest)';
        }

        function refreshSummary(): void {
            const opts = currentOpts();
            const scoped = targets();
            const count = ticked(scoped).length;
            const actorLabel = opts.actors.length ? opts.actors.join(', ') : 'all actors';
            const areaLabel = opts.area || 'all areas';
            const b = bounds(allRows, opts.unit);
            const from = opts.from != null ? opts.from : (b ? b.min : '?');
            const to = opts.to != null ? opts.to : (b ? b.max : '?');
            summary.textContent = (opts.unit === 'tick' ? 'ticks ' : 'turns ') + from + '–' + to
                + ' | ' + actorLabel + ' | ' + areaLabel
                + ' | ' + count + ' event' + (count === 1 ? '' : 's')
                + ' | ' + opts.format
                + ' | filters ' + (opts.ignoreFilters ? 'IGNORED' : 'applied');
        }

        function filename(opts: ExportOpts): string {
            const b = bounds(allRows, opts.unit);
            const from = opts.from != null ? opts.from : (b ? b.min : 0);
            const to = opts.to != null ? opts.to : (b ? b.max : 0);
            return scenarioName() + '_' + opts.unit + '_' + from + '-' + to + '_event_log_' + nowStamp() + '.' + EXT[opts.format];
        }

        async function doExport(): Promise<void> {
            const opts = currentOpts();
            const scoped = targets();
            if (opts.format !== 'markdown' && opts.format !== 'plain' && ticked(scoped).length === 0) {
                toastError('Nothing to export in that range/scope.');
                return;
            }
            const meta = buildMeta(opts, scoped);
            const text = render(scoped, meta, opts.format);
            if (destSel.value === 'clipboard') {
                if (text.length > 2000000) {
                    const ok = await (window as any).Dialog?.confirm?.({
                        title: 'Large Export',
                        message: 'This export is ' + Math.round(text.length / 1048576 * 10) / 10 +
                            ' MB. Some browsers refuse a clipboard write that large. Copy anyway?',
                        danger: true
                    });
                    if (!ok) return;
                }
                await writeClipboard(text);
                toastInfo('📋 Copied ' + ticked(scoped).length + ' event(s) to clipboard.');
            } else {
                await saveText(text, filename(opts), MIME[opts.format]);
                toastInfo('📥 Saved ' + ticked(scoped).length + ' event(s) to file.');
            }
            overlay.remove();
        }

        // ── layout ──
        const grid = document.createElement('div');
        grid.style.cssText = 'display:grid;grid-template-columns:auto 1fr;gap:6px 8px;align-items:center;font-size:12px;';
        function lab(t: string): HTMLElement { const l = document.createElement('label'); l.textContent = t; l.style.fontSize = '11px'; return l; }
        grid.appendChild(lab('Unit')); grid.appendChild(unitSel);
        grid.appendChild(lab('Range')); grid.appendChild(rowOf(fromInput, toInput));
        grid.appendChild(lab('Actors')); grid.appendChild(actorSel);
        grid.appendChild(lab('Area')); grid.appendChild(areaSel);
        grid.appendChild(lab('Format')); grid.appendChild(formatSel);
        grid.appendChild(lab('To')); grid.appendChild(destSel);
        grid.appendChild(lab('')); grid.appendChild(ignoreWrap);

        const actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:6px;justify-content:flex-end;';
        const goBtn = document.createElement('button');
        goBtn.className = 'btn btn-sm btn-green';
        goBtn.textContent = 'Export';
        goBtn.onclick = () => { void doExport(); };
        const closeBtn = document.createElement('button');
        closeBtn.className = 'btn btn-sm'; closeBtn.textContent = '✕';
        closeBtn.onclick = () => overlay.remove();
        actions.appendChild(goBtn); actions.appendChild(closeBtn);

        box.appendChild(header); box.appendChild(grid); box.appendChild(summary); box.appendChild(actions);

        [unitSel, fromInput, toInput, actorSel, areaSel, formatSel, destSel, ignoreCb].forEach((el) => {
            el.addEventListener('change', () => { refreshBounds(); refreshSummary(); });
            el.addEventListener('input', refreshSummary);
        });
        overlay.addEventListener('mousedown', (ev) => { if (ev.target === overlay) overlay.remove(); });

        refreshBounds();
        refreshSummary();
        setTimeout(() => { (preset!.focusRange ? fromInput : unitSel).focus(); }, 20);
    }

    function rowOf(...els: HTMLElement[]): HTMLElement {
        const d = document.createElement('div');
        d.style.cssText = 'display:flex;gap:6px;align-items:center;';
        els.forEach((e) => d.appendChild(e));
        return d;
    }

    // ───────────────────────── public entry points ─────────────────────────

    /** File button: the whole log, destination = file. */
    function exportEventLog(): void { showExportModal({ destination: 'file' }); }

    /** Clipboard button: the whole log, destination = clipboard. */
    async function copyEventLogToClipboard(): Promise<void> { showExportModal({ destination: 'clipboard' }); }

    /** Range button: the modal, range controls focused. */
    function showRangeExport(): void { showExportModal({ focusRange: true }); }

    return {
        projectStreamRows: projectStreamRows,
        projectEventLog: projectStreamRows,
        applyScope: applyScope,
        bounds: bounds,
        renderMarkdown: renderMarkdown,
        renderPlain: renderPlain,
        renderJson: renderJson,
        renderJsonl: renderJsonl,
        buildRangeLog: buildRangeLog,
        exportEventLog: exportEventLog,
        copyEventLogToClipboard: copyEventLogToClipboard,
        showRangeExport: showRangeExport,
        showExportModal: showExportModal
    };
})();
