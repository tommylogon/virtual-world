/**
 * InspectorPanel — THE single render entrypoint for #inspector-panel (task-216 migration)
 *
 * Every other file that once did `panel.innerHTML = ...` must instead call
 * `InspectorPanel.render(template)` with a lit-html TemplateResult. Mixing raw
 * innerHTML writes with lit's render() on the same container corrupts lit's
 * internal part tracking, so this module is the ONLY place allowed to touch
 * the panel element.
 *
 * Views stay classic scripts (Option B): they build TemplateResults via the
 * lazy `window.Lit.html` tag and hand them here. window.Lit is only read at
 * call time, so the deferred ES-module bootstrap never races with classic
 * script parse.
 *
 * @module inspector/panel — the single owner of #inspector-panel
 * @contributes InspectorPanel.render(template): the only code allowed to write the panel element
 * @powers Node inspectors — all inspector rendering (mixing innerHTML with lit corrupts lit's part tracking)
 * @relates every inspector view hands it a lit-html TemplateResult
 * @docs docs/virtualWorld/UI & Settings/Inspector Panels.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const InspectorPanel = (() => {
    const P = {} as {
        render(template: unknown): void;
        renderStatic(template: unknown): void;
        clear(): void;
        htmlTag(strings: TemplateStringsArray, ...values: unknown[]): unknown;
    };

    const panelEl = () => document.getElementById('inspector-panel');

    // Lazy tag: classic scripts parse before the deferred lit-bootstrap module
    // runs, so window.Lit only exists when a view actually renders.
    const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);

    /**
     * Render a lit-html TemplateResult into the inspector panel.
     * @param template - lit-html template
     */
    P.render = function (template: unknown) {
        const panel = panelEl();
        if (!panel) return;
        if (!window.Lit) { console.warn('InspectorPanel.render: window.Lit not ready'); return; }
        // lit-html never removes children it doesn't own — any pre-lit static
        // markup in the container would linger above every render. Clear it
        // once, before lit takes ownership (empty states are lit-rendered by
        // Inspector.showEmpty; index.html ships no static placeholder).
        if (!panel.dataset.litBound) {
            panel.textContent = '';
            panel.dataset.litBound = '1';
        }
        // task-579: append the documentation section for every node type in one
        // place, rather than editing all fifteen views. lit renders an array.
        const docPanel = (window as unknown as { DocPanel?: { section(): unknown } }).DocPanel;
        const value = docPanel ? [template, docPanel.section()] : template;
        window.Lit.render(value, panel);
    };

    /**
     * Render plain fallback HTML (empty states, "not found", orphan triggers).
     * These are static strings with no user data, so they are safe to inject
     * directly — and doing it through the lit render path keeps lit's DOM
     * ownership intact. Values passed here MUST be trusted/static.
     * @param template - lit-html template
     */
    P.renderStatic = function (template: unknown) {
        this.render(template);
    };

    /**
     * Clear the inspector panel back to its empty state.
     */
    P.clear = function (): void {
        const panel = panelEl();
        if (!panel) return;
        if (!window.Lit) { panel.innerHTML = ''; return; }
        window.Lit.render(window.Lit.nothing, panel);
    };

    /**
     * Escape helpers are obsolete under lit (auto-escaping). Kept only so any
     * straggler call doesn't hard-crash during migration.
     */
    P.htmlTag = htmlTag;

    return P;
})();

(window as unknown as { InspectorPanel: typeof InspectorPanel }).InspectorPanel = InspectorPanel;
