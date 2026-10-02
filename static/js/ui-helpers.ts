/**
 * @module ui-helpers — shared UI utilities
 * @contributes toast/notify helpers (Notyf) plus select-enhancement helpers
 * @powers consistent toasts and dropdowns across every panel
 * @relates leaf utility used app-wide (saveload-view, settings-view, engine-config-view, …)
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

// ─── Notyf Toast Notifications ───
// The first statement must stay a value declaration: tsc drops a file's leading
// JSDoc when the first statement is type-only, and js_module_index.py reads
// `@module` out of the emitted .js. All interfaces therefore live at the bottom.
let _notyf: NotyfInstance | null = null;

/**
 * Notyf and Choices.js are CDN globals, not modules, and neither is declared in
 * static/js/types/globals.d.ts. They are read off `window` through a local cast
 * rather than `declare`d bare — this is a classic script, so a bare declaration
 * would become a global that collides with the vendored bundles.
 */
interface CdnLibsSurface {
    Notyf?: new (options: Record<string, unknown>) => NotyfInstance;
    Choices?: new (el: Element, options: Record<string, unknown>) => ChoicesInstance;
}

function getNotyf(): NotyfInstance {
    if (!_notyf) {
        const NotyfCtor = (window as unknown as CdnLibsSurface).Notyf;
        _notyf = new NotyfCtor!({
            duration: 3000,
            position: { x: 'right', y: 'top' },
            dismissible: true,
            types: [
                { type: 'info', background: '#58a6ff', icon: { className: 'notyf-icon', tagName: 'span', text: 'ℹ️' } },
                { type: 'success', background: '#3fb950', icon: { className: 'notyf-icon', tagName: 'span', text: '✅' } },
                { type: 'error', background: '#f85149', icon: { className: 'notyf-icon', tagName: 'span', text: '❌' } },
                { type: 'warning', background: '#d29922', icon: { className: 'notyf-icon', tagName: 'span', text: '⚠️' } }
            ]
        });
    }
    return _notyf;
}

function toast(msg: string, type = 'success'): void {
    try {
        getNotyf().open({ type, message: msg });
    } catch (e) {
        console.log(`[toast ${type}] ${msg}`);
    }
}

function toastSuccess(msg: string): void { toast(msg, 'success'); }
function toastError(msg: string): void { toast(msg, 'error'); }
function toastInfo(msg: string): void { toast(msg, 'info'); }
function toastWarning(msg: string): void { toast(msg, 'warning'); }

// ─── Choices.js Select Helpers ───
function enhanceSelect(el: HTMLSelectElement | null, opts: Record<string, unknown> = {}): ChoicesInstance | null {
    const ChoicesCtor = (window as unknown as CdnLibsSurface).Choices;
    if (!el || !ChoicesCtor) return null;
    try {
        return new ChoicesCtor(el, {
            allowHTML: true,
            searchEnabled: opts.searchEnabled !== false,
            itemSelectText: '',
            removeItemButton: opts.removeItemButton !== false,
            shouldSort: false,
            placeholder: opts.placeholder || true,
            searchPlaceholderValue: opts.searchPlaceholder || 'Search...',
            noResultsText: 'No results found',
            noChoicesText: 'No options available',
            ...opts
        });
    } catch (e) {
        console.warn('Choices init failed:', e);
        return null;
    }
}

// Re-scan the document for choices-enhanced selects (call after dynamic content is added)
function reinitChoices(container?: ParentNode | null): void {
    if (!(window as unknown as CdnLibsSurface).Choices) return;
    const root = container || document;
    root.querySelectorAll('select.choices-init').forEach(el => {
        const enhanced = el as HTMLSelectElement & { _choices?: ChoicesInstance | null };
        if (!enhanced._choices) {
            enhanced._choices = enhanceSelect(enhanced);
        }
    });
}

// ─── Dropdown Menus (top bar "Game ▾", toolbar "More ▾") ───
function closeTopMenus(): void {
    document.querySelectorAll<HTMLElement>('.dropdown-menu.menu-open').forEach(m => { m.style.display = 'none'; m.classList.remove('menu-open'); });
    document.removeEventListener('click', closeTopMenus);
    // Toolbar popovers carry aria-expanded; this helper is called straight from
    // their menu items, so it has to leave the triggers' state truthful too.
    // GraphToolbar is declared as a bare global (not on Window) in
    // types/globals.d.ts. `typeof` keeps the original "absent means skip"
    // semantics — a bare `GraphToolbar.syncAria()` would throw a ReferenceError
    // on a page that never loaded graph/toolbar.js.
    if (typeof GraphToolbar !== 'undefined' && GraphToolbar) GraphToolbar.syncAria();
}

function toggleTopMenu(ev: Event | null, id: string): void {
    if (ev) ev.stopPropagation();
    const menu = document.getElementById(id);
    if (!menu) return;
    const wasOpen = menu.classList.contains('menu-open');
    closeTopMenus();
    if (!wasOpen) {
        menu.style.display = 'block';
        menu.classList.add('menu-open');
        setTimeout(() => document.addEventListener('click', closeTopMenus), 0);
    }
}

/* ── types ──
 * Declared at the BOTTOM on purpose: tsc drops a file's leading JSDoc when the
 * first statement is type-only, so an `interface` above the first value
 * declaration would strip `@module` from the emitted .js. */

/** The slice of the vendored Notyf toast library this file uses. */
interface NotyfInstance {
    open(options: { type: string; message: string }): unknown;
}

/** The slice of the vendored Choices.js select enhancer this file uses. */
interface ChoicesInstance {
    [key: string]: unknown;
}