// ui-helpers.js — Shared UI utility functions for toast, tooltips, and select enhancements

// ─── Notyf Toast Notifications ───
let _notyf = null;
function getNotyf() {
    if (!_notyf) {
        _notyf = new Notyf({
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

function toast(msg, type = 'success') {
    try {
        getNotyf().open({ type, message: msg });
    } catch (e) {
        console.log(`[toast ${type}] ${msg}`);
    }
}

function toastSuccess(msg) { toast(msg, 'success'); }
function toastError(msg) { toast(msg, 'error'); }
function toastInfo(msg) { toast(msg, 'info'); }
function toastWarning(msg) { toast(msg, 'warning'); }

// ─── Tippy.js Tooltip Helpers ───
function initTooltip(el, content, opts = {}) {
    if (!el || typeof tippy === 'undefined') return;
    try {
        tippy(el, {
            content,
            placement: opts.placement || 'top',
            arrow: true,
            animation: 'shift-away',
            duration: [200, 150],
            maxWidth: opts.maxWidth || 250,
            allowHTML: true,
            interactive: opts.interactive || false,
            ...opts
        });
    } catch (e) { /* silently ignore */ }
}

// ─── Choices.js Select Helpers ───
function enhanceSelect(el, opts = {}) {
    if (!el || typeof Choices === 'undefined') return null;
    try {
        return new Choices(el, {
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
function reinitChoices(container) {
    if (typeof Choices === 'undefined') return;
    const root = container || document;
    root.querySelectorAll('select.choices-init').forEach(el => {
        if (!el._choices) {
            el._choices = enhanceSelect(el);
        }
    });
}

// ─── Dropdown Menus (top bar "Game ▾", toolbar "More ▾") ───
function closeTopMenus() {
    document.querySelectorAll('.dropdown-menu.menu-open').forEach(m => { m.style.display = 'none'; m.classList.remove('menu-open'); });
    document.removeEventListener('click', closeTopMenus);
}

function toggleTopMenu(ev, id) {
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
