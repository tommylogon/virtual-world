"use strict";
/**
 * DocPanel — the documentation section shown beside an inspector (task-579).
 *
 * Selecting a node or item asks the resolver (task-578) once which note covers
 * it, and renders the title, a one-line summary and an open action. "No
 * documentation" is a first-class, quiet state — most library items start
 * there — never an error.
 *
 * The panel is appended by inspector/panel.js for every node type, so no view
 * is edited to add it. A world node resolves by its library id when it has one
 * and otherwise by the inspector module that renders it.
 *
 * @module inspector/doc-panel — which note documents the selected node or item
 * @contributes DocPanel.section() and the resolver fetch for a selection
 * @powers Node inspectors — seeing the reference note for the thing currently selected
 * @relates inspector/panel, routes/docs_ops (task-578), item-library
 * @docs docs/virtualWorld/UI & Settings/Inspector Panels.md
 */
window.DocPanel = (() => {
    const P = {};
    //: node type -> the module whose @docs describes it, for a world node with
    //: no library id (an area, a hand-made way). Repo-relative, as @docs are.
    P.MODULE_BY_TYPE = {
        area: 'static/js/inspector/area-view.js',
        item: 'static/js/inspector/item-view.js',
        way: 'static/js/inspector/way-view.js',
        character: 'static/js/inspector/agent-view.js',
    };
    let selection = null;
    let state = { status: 'idle', rows: [] };
    /** The resolver URL for a selection, or null when there is no key. */
    P.requestUrl = function (sel) {
        if (!sel || !sel.value)
            return null;
        const param = sel.kind === 'module' ? 'module' : 'node';
        return '/api/docs/resolve?' + param + '=' + encodeURIComponent(sel.value);
    };
    /** Pick the resolver key for a graph node: library id first, else its view. */
    P.selectionForNode = function (node) {
        if (!node)
            return null;
        const lib = node.properties && node.properties.library_id;
        if (lib)
            return { kind: 'node', value: lib };
        const mod = P.MODULE_BY_TYPE[node.type];
        return mod ? { kind: 'module', value: mod } : null;
    };
    /**
     * Pure view-model for a resolver response.
     * @returns {{empty: boolean, title: string, summary: string, url: ?string}}
     */
    P.format = function (rows) {
        const list = Array.isArray(rows) ? rows : [];
        if (!list.length) {
            return { empty: true, title: 'No documentation yet',
                summary: 'This has no page yet.', url: null };
        }
        const r = list[0] || {};
        return {
            empty: false,
            title: r.title || r.path || 'Documentation',
            summary: r.summary || '',
            url: r.body_url || null,
        };
    };
    P.state = function () { return state; };
    /** Select a node/module and load its documentation. Safe with no key. */
    P.setSelection = function (sel) {
        selection = sel || null;
        state = { status: 'loading', rows: [] };
        P._paint();
        return P._load();
    };
    P.reset = function () {
        selection = null;
        state = { status: 'idle', rows: [] };
        P._paint();
    };
    P._load = function () {
        const url = P.requestUrl(selection);
        if (!url) {
            state = { status: 'ready', rows: [] };
            P._paint();
            return Promise.resolve(state);
        }
        return fetch(url)
            .then((res) => res.json())
            .then((rows) => {
            state = { status: 'ready', rows: Array.isArray(rows) ? rows : [] };
            P._paint();
            return state;
        })
            .catch(() => {
            // A resolver failure is the same quiet state as "no page".
            state = { status: 'ready', rows: [] };
            P._paint();
            return state;
        });
    };
    /** The lit-html section; panel.js appends this to every inspector render. */
    P.section = function () {
        setTimeout(P._paint, 0);
        return window.Lit.html `
            <div class="inspector-section" id="doc-panel-section" style="padding:10px 16px;border-top:1px solid var(--border);">
                <h3 style="font-size:11px;font-weight:600;margin:0 0 6px 0;color:var(--text-dim);display:flex;align-items:center;gap:4px;">📖 Documentation</h3>
                <div id="doc-panel-body"></div>
            </div>`;
    };
    P._paint = function () {
        const el = document.getElementById('doc-panel-body');
        if (!el)
            return;
        el.textContent = '';
        if (state.status === 'loading') {
            el.appendChild(P._text('Looking…', 'section-hint'));
            return;
        }
        const f = P.format(state.rows);
        el.appendChild(P._text(f.title, f.empty ? 'section-hint' : 'doc-panel-title'));
        if (!f.empty && f.summary)
            el.appendChild(P._text(f.summary, 'section-hint'));
        if (!f.empty && f.url) {
            const a = document.createElement('a');
            a.className = 'btn btn-sm';
            a.textContent = 'Open documentation';
            a.setAttribute('href', f.url);
            a.setAttribute('target', '_blank');
            a.setAttribute('rel', 'noopener');
            a.style.marginTop = '4px';
            a.style.display = 'inline-block';
            el.appendChild(a);
        }
    };
    P._text = function (value, cls) {
        const d = document.createElement('div');
        if (cls)
            d.className = cls;
        d.textContent = value;
        return d;
    };
    return P;
})();
