/**
 * turn-minimap.js — "where you've been" for the human turn panel (task-677)
 *
 * Fetches GET /api/players/<name>/map and draws the cells that character has
 * actually walked, per scope. Hovering a cell reports what was last observed
 * there — when, what, and who — and a way the character knows is blocked draws
 * a mark on the boundary between its two cells.
 *
 * Three rules this file exists to enforce, each of which was wrong in a draft:
 *
 * 1. **The unit is the cell, not the area.** `properties.cell` is not unique per
 *    area — the storey index is part of place identity (World Building/Grid to
 *    Graph.md:53) — so cells are keyed by x/y and a cell holding more than one
 *    area gets a stack badge instead of two overlapping squares.
 * 2. **A way mark straddles the boundary.** Ways carry a half-integer
 *    coordinate (engine/world_compile.py:2055), so the mark sits on the grid
 *    line between the two cells with a small hit box. Drawn inside a cell it
 *    swallows that cell's own hover.
 * 3. **Blocking is the server's decision.** The payload's `way_blocked` already
 *    applies the same knowledge rule the turn panel uses, so an unlearned locked
 *    way is never marked. There is deliberately no client-side copy of that rule.
 *
 * Load AFTER api.js and turn-scene-view.js, BEFORE human-turn-composer.js.
 *
 * @module agent/turn-minimap — visited-cell map for the turn panel
 * @contributes TurnMinimap: GET /api/players/<name>/map → per-scope visited lattice, hover detail, boundary marks, fullscreen
 * @powers Where you've been
 * @relates reads the same observation rows the scene view reads; mounted by human-turn-composer after renderScene
 * @docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

interface TurnMinimapWindowSurface { TurnMinimap: unknown }
(window as unknown as TurnMinimapWindowSurface).TurnMinimap = (() => {
    'use strict';

    const STYLE_ID = 'tmn-styles';
    const HOST_ID = 'htc-map';

    /** Cell edge in px. Recomputed per render from the scope's extent. */
    let _pitch = 26;

    function ensureStyles(): void {
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            #${HOST_ID} { margin-top:10px; border-top:1px solid #333a45; padding-top:9px; }
            #${HOST_ID} .tmn-head { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
            #${HOST_ID} .tmn-label { font-size:10px; text-transform:uppercase; letter-spacing:1.2px; color:#6b7686; }
            #${HOST_ID} .tmn-sp { flex:1; }
            #${HOST_ID} select { background:#21262d; color:#e6edf3; border:1px solid #333a45;
                                 border-radius:5px; font-size:11px; padding:2px 5px; max-width:200px; }
            #${HOST_ID} button { background:#21262d; color:#8b949e; border:1px solid #333a45;
                                 border-radius:5px; font-size:11px; padding:2px 7px; cursor:pointer; }
            #${HOST_ID} button:hover { background:#30363d; color:#e6edf3; }
            #${HOST_ID} .tmn-grid { position:relative; overflow:auto; max-height:340px;
                                    background:#0a0e13; border:1px solid #333a45; border-radius:5px; }
            #${HOST_ID} .tmn-cell { position:absolute; box-sizing:border-box; background:#3b444f;
                                     border:1px solid #0a0e13; cursor:default; }
            #${HOST_ID} .tmn-cell:hover { background:#4a5563; }
            #${HOST_ID} .tmn-cell.tmn-now { background:#1f4a7d; box-shadow:inset 0 0 0 2px #58a6ff; }
            #${HOST_ID} .tmn-cell .tmn-n { position:absolute; top:0; right:1px; font-size:8px;
                                          color:#e3b341; font-weight:700; line-height:1; }
            #${HOST_ID} .tmn-mark { position:absolute; z-index:3; display:flex; align-items:center;
                                   justify-content:center; cursor:help; }
            #${HOST_ID} .tmn-mark span { color:#f85149; font-weight:700; line-height:1; }
            #${HOST_ID} .tmn-foot { display:flex; gap:12px; margin-top:5px; font-size:10px; color:#5b6570;
                                    flex-wrap:wrap; }
            #${HOST_ID} .tmn-sw { display:inline-block; width:9px; height:9px; border-radius:2px;
                                  border:1px solid #333a45; margin-right:3px; vertical-align:-1px; }
            #${HOST_ID} .tmn-loose { margin-top:7px; font-size:10.5px; color:#6b7686; line-height:1.5; }
            #${HOST_ID} .tmn-loose b { color:#8b949e; font-weight:500; }
            #${HOST_ID} .tmn-empty { font-size:10.5px; color:#5b6570; }
            .tmn-tip { position:fixed; z-index:1400; max-width:320px; background:#0b0f14;
                       border:1px solid #3a4350; border-radius:7px; padding:8px 10px;
                       box-shadow:0 10px 28px rgba(0,0,0,.7); pointer-events:none; display:none; }
            .tmn-tip h5 { margin:0 0 1px; font-size:12.5px; color:#e6edf3; }
            .tmn-tip .tmn-kind { font-size:9.5px; text-transform:uppercase; letter-spacing:1px;
                                color:#5b6570; margin-bottom:5px; }
            .tmn-tip .tmn-row { display:flex; gap:7px; font-size:11px; color:#8b949e;
                                padding:1.5px 0; line-height:1.45; }
            .tmn-tip .tmn-k { flex:0 0 58px; color:#5b6570; font-size:10px; padding-top:1px; }
            .tmn-tip .tmn-v { flex:1; color:#e6edf3; }
            .tmn-tip .tmn-chips span { display:inline-block; padding:0 5px; margin:0 3px 2px 0;
                                       border:1px solid #333a45; border-radius:9px; font-size:10px;
                                       color:#8b949e; }
            .tmn-tip .tmn-chips span.tmn-x { color:#f85149; border-color:#5c2226; }
            .tmn-tip .tmn-chips span.tmn-ok { color:#3fb950; border-color:#1f4a2c; }
            .tmn-full { position:fixed; inset:0; z-index:1500; background:#010409; padding:20px;
                        display:flex; flex-direction:column; }
            .tmn-full .tmn-fullbar { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
        `;
        document.head.appendChild(style);
    }

    function el(tag: string, cls?: string, text?: string): HTMLElement {
        const node = document.createElement(tag);
        if (cls) node.className = cls;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function esc(text: string): string {
        return String(text == null ? '' : text)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    async function apiGet(path: string): Promise<unknown> {
        const api = (window as unknown as { ApiClient?: { get(p: string): Promise<unknown> } }).ApiClient;
        if (!api) return null;
        return api.get(path);
    }

    /** The map payload for *charName*, or null when unavailable. */
    async function fetchMap(charName: string): Promise<MapPayload | null> {
        try {
            const data = await apiGet('/api/players/' + encodeURIComponent(charName) + '/map');
            if (!data || typeof data !== 'object') return null;
            const payload = data as MapPayload;
            return payload.error ? null : payload;
        } catch (err) {
            return null;
        }
    }

    function tipEl(): HTMLElement {
        let tip = document.getElementById('tmn-tip');
        if (!tip) {
            tip = el('div', 'tmn-tip');
            tip.id = 'tmn-tip';
            document.body.appendChild(tip);
        }
        return tip;
    }

    function showTip(html: string, ev: MouseEvent): void {
        const tip = tipEl();
        tip.innerHTML = html;
        tip.style.display = 'block';
        moveTip(ev);
    }

    function moveTip(ev: MouseEvent): void {
        const tip = tipEl();
        if (tip.style.display === 'none') return;
        const box = tip.getBoundingClientRect();
        let left = ev.clientX + 16;
        let top = ev.clientY + 14;
        if (left + box.width > window.innerWidth - 10) left = ev.clientX - box.width - 14;
        if (top + box.height > window.innerHeight - 10) top = ev.clientY - box.height - 12;
        tip.style.left = left + 'px';
        tip.style.top = top + 'px';
    }

    function hideTip(): void {
        tipEl().style.display = 'none';
    }

    function cellTipHtml(cell: MapCell, tick: number): string {
        const kind = cell.biome || cell.kind || 'area';
        const rows: string[][] = [];
        const seen = cell.current
            ? 'you are here'
            : (cell.last_seen === tick || cell.last_seen === null || cell.last_seen === undefined
                ? 'just now'
                : 'tick ' + cell.last_seen);
        rows.push(['seen', seen]);
        rows.push(['last known', cell.items.length
            ? cell.items.map(function (i) { return i.name; }).join(', ')
            : 'nothing you noticed']);
        // Unmet people have no name to show, so listing them one by one reads as
        // a stutter ("someone you have met" three times). Count them instead.
        const named = cell.people.filter(function (p) { return !!p.name; });
        const unnamed = cell.people.length - named.length;
        const whoParts: string[] = named.map(function (p) { return p.name as string; });
        if (unnamed === 1) whoParts.push('someone you have met');
        else if (unnamed > 1) whoParts.push(unnamed + ' people you have met');
        rows.push(['who was there', whoParts.length
            ? whoParts.join(', ')
            : 'nobody you have met']);
        const ways = cell.ways.length
            ? cell.ways.map(function (w) {
                const cls = w.state === 'blocked' || w.state === 'locked' ? ' tmn-x'
                    : (w.state === 'open' ? ' tmn-ok' : '');
                return '<span class="' + cls.trim() + '">' + esc(w.direction) + ' · ' + esc(w.state) + '</span>';
            }).join('')
            : '<span>no known ways out</span>';
        const at = cell.cell ? 'cell ' + cell.cell.x + ',' + cell.cell.y : 'no grid cell';
        return '<h5>' + esc(cell.name) + '</h5>'
            + '<div class="tmn-kind">' + esc(kind) + ' · ' + at + '</div>'
            + rows.map(function (r) {
                return '<div class="tmn-row"><span class="tmn-k">' + r[0]
                    + '</span><span class="tmn-v">' + r[1] + '</span></div>';
            }).join('')
            + '<div class="tmn-row"><span class="tmn-k">ways</span>'
            + '<span class="tmn-v tmn-chips">' + ways + '</span></div>';
    }

    function markTipHtml(way: MapWay, cell: MapCell): string {
        return '<h5>Way ' + esc(way.direction) + '</h5>'
            + '<div class="tmn-kind">' + esc(cell.name) + ' &rarr; ' + esc(way.name || 'somewhere') + '</div>'
            + '<div class="tmn-row"><span class="tmn-k">state</span><span class="tmn-v tmn-chips">'
            + '<span class="tmn-x">' + esc(way.real_state) + '</span></span></div>'
            + '<div class="tmn-row"><span class="tmn-k">you know</span>'
            + '<span class="tmn-v">yes — you have found this yourself</span></div>';
    }

    /**
     * Draw one scope's visited cells plus the boundary marks between them.
     *
     * Absolute positioning rather than a CSS grid: a way mark has to land on the
     * midpoint between two cell centres, and grid gutters make that arithmetic
     * wrong by a pixel per step.
     */
    function drawScope(
        grid: HTMLElement, areas: MapCell[], scope: MapScope | null, tick: number
    ): void {
        const painted = areas.filter(function (a) { return a.cell && typeof a.cell.x === 'number'; });
        const cols = (scope && scope.w) || (painted.reduce(function (m, a) {
            return Math.max(m, (a.cell ? a.cell.x : 0) + 1);
        }, 1));
        const rows = (scope && scope.h) || (painted.reduce(function (m, a) {
            return Math.max(m, (a.cell ? a.cell.y : 0) + 1);
        }, 1));

        const avail = Math.max(180, grid.clientWidth - 4);
        _pitch = Math.max(14, Math.min(34, Math.floor(avail / Math.max(1, cols))));
        grid.style.width = (cols * _pitch) + 'px';
        grid.style.height = (rows * _pitch) + 'px';

        // One square per cell; several areas in a cell stack into a badge.
        const byCell = new Map<string, MapCell[]>();
        painted.forEach(function (a) {
            const key = a.cell!.x + ',' + a.cell!.y;
            if (!byCell.has(key)) byCell.set(key, []);
            (byCell.get(key) as MapCell[]).push(a);
        });

        byCell.forEach(function (stack, key) {
            const parts = key.split(',');
            const cx = parseInt(parts[0] as string, 10);
            const cy = parseInt(parts[1] as string, 10);
            const head = stack[0] as MapCell;
            const cell = el('div', 'tmn-cell' + (head.current ? ' tmn-now' : ''));
            cell.style.left = (cx * _pitch) + 'px';
            cell.style.top = (cy * _pitch) + 'px';
            cell.style.width = _pitch + 'px';
            cell.style.height = _pitch + 'px';
            if (stack.length > 1) cell.appendChild(el('span', 'tmn-n', String(stack.length)));
            cell.addEventListener('mouseenter', function (ev: MouseEvent) {
                showTip(cellTipHtml(head, tick), ev);
            });
            cell.addEventListener('mousemove', moveTip);
            cell.addEventListener('mouseleave', hideTip);
            grid.appendChild(cell);
        });

        // Boundary marks, only where the character knows the way is blocked.
        const index = new Map<string, MapCell>();
        painted.forEach(function (a) {
            index.set(a.id, a);
        });
        painted.forEach(function (from) {
            from.ways.forEach(function (way) {
                if (!way.solid || !way.way_blocked || !way.to_area_id) return;
                const to = index.get(way.to_area_id);
                if (!to || !to.cell || !from.cell) return;
                const mx = ((from.cell.x + to.cell.x) / 2 + 0.5) * _pitch;
                const my = ((from.cell.y + to.cell.y) / 2 + 0.5) * _pitch;
                const mark = el('div', 'tmn-mark');
                mark.style.left = (mx - 9) + 'px';
                mark.style.top = (my - 9) + 'px';
                mark.style.width = '18px';
                mark.style.height = '18px';
                const glyph = el('span', undefined, '✖');
                glyph.style.fontSize = Math.max(10, Math.round(_pitch * 0.55)) + 'px';
                mark.appendChild(glyph);
                mark.addEventListener('mouseenter', function (ev: MouseEvent) {
                    showTip(markTipHtml(way, from), ev);
                });
                mark.addEventListener('mousemove', moveTip);
                mark.addEventListener('mouseleave', hideTip);
                grid.appendChild(mark);
            });
        });
    }

    function render(host: HTMLElement, payload: MapPayload): void {
        ensureStyles();
        const existing = document.getElementById(HOST_ID);
        if (existing) existing.remove();

        const wrap = el('div');
        wrap.id = HOST_ID;

        const areas = Array.isArray(payload.areas) ? payload.areas : [];
        const scopes = Array.isArray(payload.scopes) ? payload.scopes : [];

        if (!areas.length) {
            wrap.appendChild(el('div', 'tmn-empty',
                'No map yet — this character has not been anywhere.'));
            host.appendChild(wrap);
            return;
        }

        const head = el('div', 'tmn-head');
        head.appendChild(el('span', 'tmn-label', 'Where you’ve been'));
        const sel = el('select') as HTMLSelectElement;
        sel.setAttribute('aria-label', 'Which scope to show');
        scopes.forEach(function (s) {
            const opt = el('option', undefined, s.name + ' (' + s.visited_cells + ')') as HTMLOptionElement;
            opt.value = s.id;
            sel.appendChild(opt);
        });
        if (!scopes.length) {
            const opt = el('option', undefined, 'no scope') as HTMLOptionElement;
            opt.value = '';
            sel.appendChild(opt);
        }
        head.appendChild(sel);
        head.appendChild(el('span', 'tmn-sp'));

        const fsBtn = el('button', undefined, '⛶');
        fsBtn.title = 'Open the map fullscreen';
        head.appendChild(fsBtn);
        wrap.appendChild(head);

        const grid = el('div', 'tmn-grid');
        wrap.appendChild(grid);

        const foot = el('div', 'tmn-foot');
        foot.innerHTML = '<span><span class="tmn-sw" style="background:#3b444f"></span>been</span>'
            + '<span><span class="tmn-sw" style="background:#1f4a7d"></span>you are here</span>'
            + '<span><span style="color:#f85149;font-weight:700">✖</span> way you know is blocked</span>';
        wrap.appendChild(foot);

        const loose = areas.filter(function (a) { return !a.cell; });
        if (loose.length) {
            const note = el('div', 'tmn-loose');
            note.appendChild(el('b', undefined, 'No painted position: '));
            note.appendChild(document.createTextNode(
                loose.map(function (a) { return a.name; }).join(', ')
                + ' — these have no grid cell, so they are not on the lattice.'));
            wrap.appendChild(note);
        }

        host.appendChild(wrap);

        const tick = typeof payload.tick === 'number' ? payload.tick : 0;

        function paint(): void {
            const scopeId = sel.value;
            const inScope = areas.filter(function (a) {
                return scopeId ? a.scope_id === scopeId : true;
            });
            const scope = scopes.filter(function (s) { return s.id === scopeId; })[0] || null;
            grid.textContent = '';
            drawScope(grid, inScope, scope, tick);
        }

        sel.addEventListener('change', paint);
        fsBtn.addEventListener('click', function () { openFullscreen(areas, scopes, tick); });
        paint();
    }

    /** The same lattice, over the whole viewport. Escape closes it. */
    function openFullscreen(areas: MapCell[], scopes: MapScope[], tick: number): void {
        const prev = document.querySelector('.tmn-full');
        if (prev) prev.remove();
        hideTip();

        const overlay = el('div', 'tmn-full');
        const bar = el('div', 'tmn-fullbar');
        bar.appendChild(el('span', 'tmn-label', 'Map — fullscreen'));
        bar.appendChild(el('span', 'tmn-sp'));
        const close = el('button', undefined, 'close ✕');
        bar.appendChild(close);
        overlay.appendChild(bar);

        const sel = el('select') as HTMLSelectElement;
        sel.setAttribute('aria-label', 'Which scope to show');
        scopes.forEach(function (s) {
            const opt = el('option', undefined, s.name + ' (' + s.visited_cells + ')') as HTMLOptionElement;
            opt.value = s.id;
            sel.appendChild(opt);
        });
        bar.insertBefore(sel, close);

        const grid = el('div', 'tmn-grid');
        grid.style.maxHeight = 'none';
        grid.style.flex = '1';
        overlay.appendChild(grid);
        document.body.appendChild(overlay);

        function paint(): void {
            const scopeId = sel.value;
            const inScope = areas.filter(function (a) {
                return scopeId ? a.scope_id === scopeId : true;
            });
            const scope = scopes.filter(function (s) { return s.id === scopeId; })[0] || null;
            grid.textContent = '';
            drawScope(grid, inScope, scope, tick);
        }

        function shut(): void {
            overlay.remove();
            hideTip();
            document.removeEventListener('keydown', onKey);
        }
        function onKey(ev: KeyboardEvent): void {
            if (ev.key === 'Escape') shut();
        }

        sel.addEventListener('change', paint);
        close.addEventListener('click', shut);
        document.addEventListener('keydown', onKey);
        paint();
    }

    /**
     * Mount the map under the scene view. Called by the composer *after*
     * `renderScene`, because that clears its host.
     */
    async function mount(host: HTMLElement, charName: string): Promise<void> {
        const payload = await fetchMap(charName);
        if (!payload) return;
        render(host, payload);
    }

    return { fetchMap, render, mount };
})();

// ────────────────────────── local types ──────────────────────────
// Declared after the IIFE so the leading JSDoc block stays the first thing in
// the emitted .js and `@module` remains discoverable.

interface MapCellXY { x: number; y: number }

interface MapWay {
    way_id: string;
    direction: string;
    to_area_id?: string | null;
    name?: string;
    state: string;
    real_state: string;
    solid: boolean;
    way_blocked: boolean;
    visible_in_direction?: string;
}

interface MapCell {
    id: string;
    name: string;
    cell?: MapCellXY | null;
    floor: number;
    scope_id: string;
    biome?: string;
    kind?: string;
    last_seen?: number | null;
    current: boolean;
    items: Array<{ id: string; name: string }>;
    people: Array<{ id: string; name?: string | null; display: string }>;
    ways: MapWay[];
}

interface MapScope {
    id: string;
    name: string;
    visited_cells: number;
    w?: number | null;
    h?: number | null;
    cell_scale?: number;
}

interface MapPayload {
    error?: string;
    player?: string;
    current_area?: string;
    tick?: number;
    areas?: MapCell[];
    scopes?: MapScope[];
}
