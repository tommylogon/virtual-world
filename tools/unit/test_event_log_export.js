/**
 * test_event_log_export.js — the event-log export mechanism (task-777).
 *
 * The wiring (the three header buttons, the live modal) is proven in the
 * browser; this pins the mechanism the browser run then confirms:
 *   - the DOM projection (rawText, data-seq, turn/day from the card, outcome,
 *     raw-LLM payload, the scope banner's label span — never its `×` button),
 *   - filter honesty (a display:none row is skipped unless ignoreFilters),
 *   - the JSON/JSONL envelope + counts, and the Markdown heading that must end
 *     with game time, not a stray `]`.
 *
 * A tiny fake element stands in for the DOM: it implements exactly the reads
 * the projection performs (classList.contains/iteration, getAttribute,
 * querySelector by class, dataset, style.display, children).
 */

function mkEl(tag, opts) {
    opts = opts || {};
    const classes = new Set((opts.classes || []).concat(opts.class ? [opts.class] : []));
    // My projection does Array.from(classList) — keep it a real (iterable) Set.
    classes.contains = (c) => classes.has(c);
    const node = {
        tagName: String(tag).toUpperCase(),
        children: [],
        style: Object.assign({}, opts.style || {}),
        dataset: Object.assign({}, opts.dataset || {}),
        textContent: opts.text != null ? opts.text : '',
        classList: classes,
        _attrs: Object.assign({}, opts.attrs || {}),
        getAttribute(n) { return n in node._attrs ? node._attrs[n] : null; },
        setAttribute(n, v) { node._attrs[n] = String(v); },
        appendChild(c) { node.children.push(c); return c; },
    };
    (opts.children || []).forEach((c) => node.appendChild(c));
    const matches = (n, sel) => (sel.charAt(0) === '.'
        ? n.classList.contains(sel.slice(1))
        : n.tagName === sel.toUpperCase());
    node.querySelector = (sel) => {
        for (const c of node.children) {
            if (matches(c, sel)) return c;
            const deep = c.querySelector(sel);
            if (deep) return deep;
        }
        return null;
    };
    return node;
}

function bubbleOf(extra) {
    const b = mkEl('div', Object.assign({
        classes: ['msg-bubble', 'msg-bubble-speech'],
        attrs: { 'data-seq': '7', 'data-actor': 'Lyrie', 'data-tick': '42', 'data-type': 'speech', 'data-stream-area': 'Goblin Camp' },
        dataset: { rawText: 'speaks: hello' },
    }, extra || {}));
    b.appendChild(mkEl('span', { class: 'bubble-icon', text: '💬' }));
    b.appendChild(mkEl('span', { class: 'bubble-tick', text: '[Tick 7 | 08:15]' }));
    b.appendChild(mkEl('span', { class: 'bubble-actor', text: 'Lyrie' }));
    b.appendChild(mkEl('span', { class: 'bubble-text', text: 'story-stripped hello' }));
    return b;
}

function streamWith(...children) {
    return mkEl('div', { attrs: { id: 'event-stream' }, children: children });
}

const E = window.EventLogExport;

// ───────────────────────── projection ─────────────────────────

test('event-log: projectStreamRows reads rawText, data-seq, turn/day and outcome', () => {
    const card = mkEl('div', { class: 'turn-card', attrs: { 'data-actor': 'Lyrie' } });
    card.appendChild(mkEl('span', { class: 'turn-card-tick', text: '[Turn 5 | Day 3, Month 1, Year 1 | 08:15 🌑]' }));
    const body = mkEl('div', { class: 'turn-card-body' });
    body.appendChild(bubbleOf({ classes: ['msg-bubble', 'msg-bubble-speech', 'outcome-success'] }));
    card.appendChild(body);
    const rows = E.projectStreamRows(streamWith(card), {});
    assertEq(rows.length, 1, 'one row');
    const r = rows[0];
    assertEq(r.seq, 7, 'seq from data-seq');
    assertEq(r.turn, 5, 'turn from the card header');
    assertEq(r.day, 'Day 3, Month 1, Year 1', 'day from the card header');
    assertEq(r.time, '08:15', 'time parsed from the label, no stray ]');
    assertEq(r.actor, 'Lyrie');
    assertEq(r.area, 'Goblin Camp');
    assertEq(r.type, 'speech');
    assertEq(r.text, 'speaks: hello', 'rawText wins over story-stripped .bubble-text');
    assertEq(r.outcome, 'success', 'outcome from the outcome-* class');
});

test('event-log: a display:none row is skipped, and included by ignoreFilters', () => {
    const b = bubbleOf({ style: { display: 'none' } });
    assertEq(E.projectStreamRows(streamWith(b), {}).length, 0, 'filter-hidden row skipped');
    assertEq(E.projectStreamRows(streamWith(b), { ignoreFilters: true }).length, 1, 'escape hatch includes it');
});

test('event-log: the scope banner projects its label span, never the × button', () => {
    const banner = mkEl('div', { class: 'stream-scope-banner' });
    banner.appendChild(mkEl('span', { text: '📌 Scoped to: Weeping Willow Hollow' }));
    banner.appendChild(mkEl('button', { text: '×' }));
    const rows = E.projectStreamRows(streamWith(banner), {});
    assertEq(rows.length, 1);
    assertEq(rows[0].type, 'scope');
    assertEq(rows[0].text, '📌 Scoped to: Weeping Willow Hollow', 'no × glued on');
});

test('event-log: the scrubber and the queue strip are chrome, not rows', () => {
    const scrub = mkEl('div', { class: 'timeline-scrubber', text: '' });
    const strip = mkEl('div', { class: 'turn-queue-strip', text: '⏭ up next: Lyrie' });
    const rows = E.projectStreamRows(streamWith(scrub, strip), {});
    assertEq(rows.length, 0, 'neither is projected');
});

test('event-log: a raw-LLM chip carries its payload regardless of collapse', () => {
    const rl = mkEl('div', {
        classes: ['msg-bubble', 'msg-bubble-rawllm'],
        attrs: { 'data-seq': '9', 'data-type': 'rawllm', 'data-actor': 'LLM' },
    });
    const hdr = mkEl('div', { class: 'rawllm-chip-header', text: '[Tick 9 | 08:16] LLM → think' });
    rl.appendChild(hdr);
    rl.appendChild(mkEl('pre', { class: 'rawllm-chip-body', text: 'PROMPT BODY', style: { display: 'none' } }));
    const rows = E.projectStreamRows(streamWith(rl), {});
    assertEq(rows.length, 1);
    assertEq(rows[0].type, 'rawllm');
    assertEq(rows[0].text, '[Tick 9 | 08:16] LLM → think', 'the chip summary is its header');
    assertEq(rows[0].payload.body, 'PROMPT BODY', 'body read even when collapsed');
});

// ───────────────────────── scope / range ─────────────────────────

function opts(o) {
    return Object.assign({
        unit: 'tick', from: null, to: null, actors: [], area: null,
        format: 'json', ignoreFilters: false,
    }, o || {});
}
function rec(o) {
    return Object.assign({
        seq: 1, tick: 10, time: '08:15', day: '', turn: null, actor: 'Lyrie',
        area: 'Goblin Camp', type: 'speech', text: 'hi',
    }, o || {});
}

test('event-log: applyScope filters by tick range and drops metadata rows', () => {
    const rows = [rec({ seq: 5 }), rec({ seq: 20 }), rec({ seq: -1, type: 'scope' })];
    const scoped = E.applyScope(rows, opts({ from: 10, to: 30 }));
    assertEq(scoped.map((r) => r.seq), [20], 'only in-range ticked rows');
    assertEq(E.applyScope(rows, opts({})).length, 3, 'no range keeps the scope row');
});

test('event-log: applyScope filters by turn, actor and area', () => {
    const rows = [rec({ turn: 1, actor: 'A', area: 'X' }), rec({ turn: 2, actor: 'B', area: 'Y' })];
    assertEq(E.applyScope(rows, opts({ unit: 'turn', from: 2, to: 2 })).length, 1);
    assertEq(E.applyScope(rows, opts({ actors: ['A'] })).length, 1);
    assertEq(E.applyScope(rows, opts({ area: 'Y' })).length, 1);
});

// ───────────────────────── renderers ─────────────────────────

const META = {
    scenario: 'goblin_camp', exportedAt: '2026-10-11T00-00-00', worldTick: 42,
    unit: 'tick', from: 5, to: 20, filters: { actor: null, area: null, search: '', ignored: false, kinds: {} },
    line: 'ticks 5–20 · 2 rows',
};

test('event-log: JSONL is one event object per line, metadata rows excluded', () => {
    const rows = [rec({ seq: 5 }), rec({ seq: 6, actor: 'Bork' }), rec({ seq: -1, type: 'scope' })];
    const out = E.renderJsonl(rows);
    const lines = out.trim().split('\n');
    assertEq(lines.length, 2, 'two event lines, no scope row');
    const first = JSON.parse(lines[0]);
    assertEq(first.seq, 5);
    assertEq(first.actor, 'Lyrie');
    assertEq(first.type, 'speech');
    assertEq(first.text, 'hi');
});

test('event-log: JSON is a schema-1 envelope with range, filters and counts', () => {
    const rows = [rec({ seq: 5, actor: 'Lyrie' }), rec({ seq: 6, actor: 'Bork', turn: 2, area: 'Y' })];
    const env = JSON.parse(E.renderJson(rows, META));
    assertEq(env.schema, 1);
    assertEq(env.scenario, 'goblin_camp');
    assertEq(env.world_tick, 42);
    assertEq(env.range, { unit: 'tick', from: 5, to: 20 });
    assertEq(env.filters.ignored, false);
    assertEq(env.counts, { events: 2, turns: 1, actors: 2, areas: 2 });
    assertEq(env.events.length, 2);
});

test('event-log: Markdown heading ends with game time, not a stray ]', () => {
    const rows = [
        rec({ seq: 5, turn: 5, actor: 'Lyrie', time: '08:15', day: 'Day 3, Month 1, Year 1', text: 'first' }),
        rec({ seq: 6, turn: 5, actor: 'Lyrie', time: '08:15', day: 'Day 3, Month 1, Year 1', text: 'second' }),
    ];
    const md = E.renderMarkdown(rows, META);
    assertEq((md.match(/## Turn 5/g) || []).length, 1, 'one heading for the turn');
    assertTrue(md.indexOf('## Turn 5 — Lyrie · 08:15 · Day 3, Month 1, Year 1') !== -1, 'heading text');
    assertFalse(/\]\s*$/.test(md.split('\n').find((l) => l.startsWith('## Turn'))), 'heading does not end with ]');
    assertEq((md.match(/^- /gm) || []).length, 2, 'one bullet per event');
});

test('event-log: Markdown renders the scope message and raw-LLM payload details', () => {
    const rows = [
        rec({ seq: -1, type: 'scope', text: '📌 Scoped to: X' }),
        rec({ seq: 5, type: 'rawllm', payload: { header: 'LLM → think', body: 'PROMPT' } }),
    ];
    const md = E.renderMarkdown(rows, META);
    assertTrue(md.indexOf('> **📌 Scoped to: X**') !== -1, 'scope as its own message');
    assertTrue(md.indexOf('<details><summary>payload</summary>') !== -1, 'payload details block');
    assertTrue(md.indexOf('PROMPT') !== -1, 'payload body included');
});

test('event-log: bounds reports the range the stream actually contains', () => {
    const rows = [rec({ seq: 4, turn: 1 }), rec({ seq: 30, turn: 3 }), rec({ seq: -1, type: 'scope' })];
    assertEq(E.bounds(rows, 'tick'), { min: 4, max: 30 });
    assertEq(E.bounds(rows, 'turn'), { min: 1, max: 3 });
});
