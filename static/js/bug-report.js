"use strict";
/**
 * bug-report — file what you are looking at as a real dev-task file.
 *
 * @module bug-report — the 🐞 dialog: description, screenshot, picked DOM elements
 * @contributes BugReport: the report dialog, the DOM element picker, and the multipart POST to /api/bugs/report
 * @powers Report a bug — "🐞 Report a bug": turn the current view, a screenshot and any picked DOM elements into a task file under docs/virtualWorld/dev_tasks/todo
 * @relates reads graphManager mode/pitch/camera and the vis canvas; captures the picture with GraphExport.snapshotView; posts multipart to /api/bugs/report
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 *
 * Why there are two screenshot mechanisms and not one. The graph and the
 * WorldPainter grid are `<canvas>`; the map background is DOM `<img>` layers; the
 * inspector, toolbars and modals are plain DOM. A canvas grab gets the nodes with
 * no chrome, so the "capture view" button reuses `GraphExport.snapshotView()`,
 * which composites the graph canvas with the map layers exactly as the PNG export
 * does. And because no DOM rasteriser is vendored anywhere in this repo (no
 * html2canvas, no `toDataURL` outside tests), a full-window shot is *pasted* or
 * *attached* rather than faked. Both paths end up as the same `screenshot` field.
 *
 * The element picker exists because "the inspector looked wrong" is not a report.
 * It records a selector path, the box geometry, the ancestor chain, a subset of
 * computed styles and the outerHTML, so the report says which element and what
 * state it was in rather than asking the next reader to go and look.
 *
 * One constraint worth knowing before touching this: `document.elementFromPoint`
 * over the graph container resolves to the *container*, never a node, because
 * vis.js draws to a canvas. Picking is for DOM chrome; for a graph node the
 * report needs the node id from the selection, which `_context()` already reads.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.BugReport = (() => {
    'use strict';
    const ENDPOINT = '/api/bugs/report';
    const MAX_ELEMENTS = 12;
    const MAX_HTML_CHARS = 4000;
    const AREAS = ['bugs', 'ui', 'graph', 'world', 'gameplay', 'items', 'characters',
        'conditions', 'docs', 'library', 'refactor', 'testing', 'triggers'];
    /** Computed properties worth having in a bug report — the ones that decide
     *  whether something is visible, clickable, or on top of something else. */
    const STYLE_KEYS = ['display', 'position', 'visibility', 'opacity', 'zIndex',
        'width', 'height', 'overflow', 'pointerEvents', 'color', 'backgroundColor',
        'fontSize', 'lineHeight', 'transform', 'flexDirection', 'gap'];
    let screenshot = null;
    let previewUrl = null;
    let elements = [];
    let busy = false;
    // ── picker state ──────────────────────────────────────────────────────────
    let picking = false;
    let hoverEl = null;
    let highlight = null;
    let onMove = null;
    let onClick = null;
    let onKey = null;
    // ── small helpers ─────────────────────────────────────────────────────────
    function _el(id) {
        return document.getElementById(id);
    }
    function _toast(message, kind) {
        if (kind === 'error' && typeof toastError === 'function')
            toastError(message);
        else if (typeof toastInfo === 'function')
            toastInfo(message);
    }
    function _setStatus(text) {
        const node = _el('bug-report-status');
        if (node)
            node.textContent = text;
    }
    function _truncate(text, limit) {
        return text.length > limit ? `${text.slice(0, limit)}\n… (truncated)` : text;
    }
    function _modal() {
        return _el('bug-report-modal');
    }
    // ── context: what the app looked like when the report was filed ───────────
    /**
     * The state a reader cannot infer from the screenshot: which layout, which
     * pitch, where the camera was, what was selected, and the window size.
     */
    function _context() {
        const context = {
            capturedAt: new Date().toISOString(),
            url: window.location.href,
            viewport: { width: window.innerWidth, height: window.innerHeight },
            devicePixelRatio: window.devicePixelRatio,
            userAgent: navigator.userAgent,
        };
        const gm = (typeof graphManager !== 'undefined' ? graphManager : null);
        if (gm) {
            context.layoutMode = gm._cardinalLayout ? 'map' : 'graph';
            context.cardinalLayout = gm._cardinalLayout === true;
            context.physicsEnabled = gm._physicsEnabled === true;
            context.viewMode = gm._viewMode;
            if (typeof gm.getViewMode === 'function')
                context.getViewMode = gm.getViewMode();
            if (gm.network) {
                try {
                    context.camera = {
                        scale: gm.network.getScale(),
                        position: gm.network.getViewPosition(),
                    };
                    if (typeof gm.network.getSelectedNodes === 'function') {
                        context.selectedNodes = gm.network.getSelectedNodes();
                    }
                }
                catch (error) { /* camera is best-effort */ }
            }
        }
        const engine = (typeof window !== 'undefined' ? window.GraphLayoutEngine : null);
        if (engine && typeof engine.mapSpacing === 'function') {
            context.mapSpacingPx = engine.mapSpacing();
        }
        const cfg = (typeof config !== 'undefined' ? config : null);
        if (cfg) {
            context.graphMapSpacing = cfg.graphMapSpacing;
            context.graphMapSpacingAuto = cfg.graphMapSpacingAuto;
            context.graphLayoutMode = cfg.graphLayoutMode;
        }
        return context;
    }
    // ── element description ───────────────────────────────────────────────────
    /** A selector that resolves back to this element, most specific step first. */
    function _cssPath(target) {
        const parts = [];
        let node = target;
        while (node && node.nodeType === 1 && node !== document.body) {
            let part = node.tagName.toLowerCase();
            if (node.id) {
                parts.unshift(`#${node.id}`);
                break;
            }
            const parent = node.parentElement;
            if (parent) {
                const sameTag = Array.prototype.filter.call(parent.children, (c) => c.tagName === node.tagName);
                if (sameTag.length > 1)
                    part += `:nth-of-type(${sameTag.indexOf(node) + 1})`;
            }
            const classes = (node.getAttribute('class') || '')
                .split(/\s+/).filter((c) => c && !/^(ng-|css-)/.test(c)).slice(0, 3);
            if (classes.length)
                part += `.${classes.join('.')}`;
            parts.unshift(part);
            node = node.parentElement;
        }
        return parts.join(' > ');
    }
    /** The ancestor chain, nearest first — the "inside what" an element needs. */
    function _ancestors(target) {
        const chain = [];
        let node = target.parentElement;
        while (node && node !== document.body && chain.length < 8) {
            chain.push(_cssPath(node));
            node = node.parentElement;
        }
        return chain;
    }
    function _describe(target) {
        const rect = target.getBoundingClientRect();
        const computed = {};
        try {
            const style = window.getComputedStyle(target);
            STYLE_KEYS.forEach((key) => {
                const value = style.getPropertyValue(key);
                if (value)
                    computed[key] = value;
            });
        }
        catch (error) { /* computed style is best-effort */ }
        return {
            selector: _cssPath(target),
            summary: `<${target.tagName.toLowerCase()}>`
                + (target.id ? `#${target.id}` : '')
                + ((target.getAttribute('class') || '').trim()
                    ? `.${(target.getAttribute('class') || '').trim().split(/\s+/).join('.')}` : ''),
            rect: {
                x: Math.round(rect.x), y: Math.round(rect.y),
                width: Math.round(rect.width), height: Math.round(rect.height),
            },
            ancestors: _ancestors(target),
            computed,
            text: _truncate((target.innerText || '').trim(), 500),
            outerHTML: _truncate(target.outerHTML || '', MAX_HTML_CHARS),
        };
    }
    // ── picker ────────────────────────────────────────────────────────────────
    function _ensureHighlight() {
        if (!highlight) {
            highlight = document.createElement('div');
            highlight.style.cssText = 'position:fixed;z-index:2147483000;pointer-events:none;'
                + 'border:2px dashed #38bdf8;background:rgba(56,189,248,0.12);border-radius:2px;';
            document.body.appendChild(highlight);
        }
        return highlight;
    }
    function _hideHighlight() {
        if (highlight)
            highlight.style.display = 'none';
    }
    function _destroyHighlight() {
        if (highlight && highlight.parentNode)
            highlight.parentNode.removeChild(highlight);
        highlight = null;
        hoverEl = null;
    }
    /** The element under the cursor, ignoring our own overlay and the dialog. */
    function _targetAt(event) {
        const found = document.elementFromPoint(event.clientX, event.clientY);
        if (!found)
            return null;
        if (highlight && (found === highlight || highlight.contains(found)))
            return null;
        const modal = _modal();
        if (modal && (found === modal || modal.contains(found)))
            return null;
        return found;
    }
    function _startPick() {
        if (picking)
            return;
        picking = true;
        const modal = _modal();
        // The dialog would swallow the click you are trying to make, so it steps
        // aside for the duration of the pick and comes back with the result.
        if (modal)
            modal.style.display = 'none';
        _setStatus('Click the element you want in the report · Esc to cancel');
        onMove = (event) => {
            hoverEl = _targetAt(event);
            const box = _ensureHighlight();
            if (!hoverEl) {
                box.style.display = 'none';
                return;
            }
            const rect = hoverEl.getBoundingClientRect();
            box.style.display = 'block';
            box.style.left = `${rect.left}px`;
            box.style.top = `${rect.top}px`;
            box.style.width = `${rect.width}px`;
            box.style.height = `${rect.height}px`;
        };
        onClick = (event) => {
            const target = _targetAt(event);
            if (!target)
                return;
            event.preventDefault();
            event.stopPropagation();
            _addElement(_describe(target));
            _stopPick();
        };
        onKey = (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                _stopPick();
            }
        };
        document.addEventListener('mousemove', onMove, true);
        document.addEventListener('click', onClick, true);
        document.addEventListener('keydown', onKey, true);
    }
    function _stopPick() {
        if (onMove)
            document.removeEventListener('mousemove', onMove, true);
        if (onClick)
            document.removeEventListener('click', onClick, true);
        if (onKey)
            document.removeEventListener('keydown', onKey, true);
        onMove = null;
        onClick = null;
        onKey = null;
        _destroyHighlight();
        picking = false;
        const modal = _modal();
        if (modal)
            modal.style.display = 'flex';
        _renderElements();
    }
    function _addElement(record) {
        if (elements.length >= MAX_ELEMENTS) {
            _toast(`That is the ${MAX_ELEMENTS}-element limit for one report.`, 'error');
            return;
        }
        // Re-picking the same element should not fill the report with duplicates.
        if (elements.some((e) => e.selector === record.selector)) {
            _toast('That element is already in the report.', 'error');
            return;
        }
        elements.push(record);
    }
    function _renderElements() {
        const list = _el('bug-report-elements');
        if (!list)
            return;
        list.textContent = '';
        if (!elements.length) {
            list.innerHTML = '<div style="color:var(--text-dim);font-size:11px;">'
                + 'No elements picked. The picker records the selector, box, computed styles and markup.</div>';
            return;
        }
        elements.forEach((record, index) => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;gap:8px;align-items:flex-start;padding:4px 0;'
                + 'border-bottom:1px solid var(--border-light);font-size:11px;';
            const label = document.createElement('code');
            label.style.cssText = 'flex:1;color:var(--accent,#7dd3fc);word-break:break-all;';
            label.textContent = `${index + 1}. ${record.selector}`;
            const rect = record.rect;
            const size = document.createElement('span');
            size.style.cssText = 'color:var(--text-dim);white-space:nowrap;';
            size.textContent = rect ? `${rect.width}×${rect.height}` : '';
            const drop = document.createElement('button');
            drop.className = 'btn btn-secondary';
            drop.style.cssText = 'padding:1px 6px;font-size:10px;';
            drop.textContent = '✕';
            drop.title = 'Remove this element';
            drop.onclick = () => { elements.splice(index, 1); _renderElements(); };
            row.append(label, size, drop);
            list.appendChild(row);
        });
    }
    // ── screenshot ────────────────────────────────────────────────────────────
    function _setScreenshot(next) {
        screenshot = next;
        const preview = _el('bug-report-preview');
        const label = _el('bug-report-shot-label');
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
        if (!next) {
            if (preview) {
                preview.removeAttribute('src');
                preview.style.display = 'none';
            }
            if (label)
                label.textContent = 'No screenshot attached';
            return;
        }
        previewUrl = URL.createObjectURL(next.blob);
        if (preview) {
            preview.src = previewUrl;
            preview.style.display = 'block';
        }
        const kb = Math.round(next.blob.size / 1024);
        if (label)
            label.textContent = `${next.source} · ${next.name} · ${kb} KB`;
    }
    async function _captureView() {
        const button = _el('bug-report-capture');
        if (button)
            button.disabled = true;
        _setStatus('Capturing the current view…');
        try {
            const exportApi = window.GraphExport;
            if (!exportApi || typeof exportApi.snapshotView !== 'function') {
                _setStatus('Graph export module is not loaded — paste a screenshot instead.');
                return;
            }
            const blob = await exportApi.snapshotView();
            if (!blob) {
                _setStatus('Nothing to capture — paste a screenshot instead.');
                return;
            }
            _setScreenshot({ blob, name: 'current-view.png', source: 'captured view' });
            _setStatus('Attached the current view. Paste or attach to replace it.');
        }
        catch (error) {
            _setStatus('Capture failed: ' + (error?.message || String(error)));
        }
        finally {
            if (button)
                button.disabled = false;
        }
    }
    function _onPaste(event) {
        if (!event.clipboardData)
            return;
        const items = event.clipboardData.items;
        for (let i = 0; i < items.length; i++) {
            if (items[i].kind !== 'file' || !items[i].type.startsWith('image/'))
                continue;
            const file = items[i].getAsFile();
            if (!file)
                continue;
            event.preventDefault();
            _setScreenshot({
                blob: file,
                name: file.name || 'pasted.png',
                source: 'pasted',
            });
            _setStatus('Attached the pasted image.');
            return;
        }
    }
    function _onAttach(event) {
        const input = event.target;
        const file = input.files && input.files[0];
        if (!file)
            return;
        _setScreenshot({ blob: file, name: file.name || 'attachment.png', source: 'attached' });
        _setStatus('Attached the chosen image.');
    }
    // ── dialog ────────────────────────────────────────────────────────────────
    function _populateAreas() {
        const select = _el('bug-report-area');
        if (!select || select.options.length)
            return;
        AREAS.forEach((area) => {
            const option = document.createElement('option');
            option.value = area;
            option.textContent = area;
            if (area === 'bugs')
                option.selected = true;
            select.appendChild(option);
        });
    }
    function openDialog() {
        const modal = _modal();
        if (!modal)
            return;
        _populateAreas();
        _setStatus('');
        _setScreenshot(null);
        elements = [];
        _renderElements();
        const message = _el('bug-report-message');
        const title = _el('bug-report-title');
        if (message)
            message.value = '';
        if (title)
            title.value = '';
        modal.style.display = 'flex';
        if (message)
            message.focus();
    }
    function closeDialog() {
        if (picking)
            _stopPick();
        const modal = _modal();
        if (modal)
            modal.style.display = 'none';
        // A filed report reports itself in a toast; leaving "Filing…" behind in a
        // dialog nobody can see reads as a hang when the next one opens.
        _setStatus('');
        _setScreenshot(null);
    }
    async function _submit() {
        if (busy)
            return;
        const message = _el('bug-report-message')?.value.trim() || '';
        if (!message) {
            _setStatus('Describe what went wrong first.');
            return;
        }
        busy = true;
        const button = _el('bug-report-submit');
        if (button)
            button.disabled = true;
        _setStatus('Filing…');
        try {
            const form = new FormData();
            form.append('message', message);
            form.append('title', _el('bug-report-title')?.value.trim() || '');
            form.append('area', _el('bug-report-area')?.value || 'bugs');
            form.append('context', JSON.stringify(_context()));
            form.append('elements', JSON.stringify(elements));
            if (screenshot) {
                form.append('screenshot', screenshot.blob, screenshot.name || 'screenshot.png');
            }
            const response = await fetch(ENDPOINT, { method: 'POST', body: form });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.status !== 'success') {
                _setStatus(payload.error || `Filing failed (${response.status}).`);
                _toast(payload.error || 'Filing failed.', 'error');
                return;
            }
            closeDialog();
            _toast(`Filed ${payload.id} — ${payload.path}`);
        }
        catch (error) {
            _setStatus('Filing failed: ' + (error?.message || String(error)));
        }
        finally {
            busy = false;
            if (button)
                button.disabled = false;
        }
    }
    function _init() {
        const pick = _el('bug-report-pick');
        if (pick)
            pick.onclick = _startPick;
        const capture = _el('bug-report-capture');
        if (capture)
            capture.onclick = () => { void _captureView(); };
        const attach = _el('bug-report-attach');
        if (attach)
            attach.onchange = _onAttach;
        const clearShot = _el('bug-report-shot-clear');
        if (clearShot)
            clearShot.onclick = () => _setScreenshot(null);
        const submit = _el('bug-report-submit');
        if (submit)
            submit.onclick = () => { void _submit(); };
        const modal = _modal();
        if (modal)
            modal.addEventListener('paste', _onPaste);
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    }
    else {
        _init();
    }
    return {
        openDialog,
        closeDialog,
        // Exposed for tools/unit/run.cjs. Not a product API.
        _internals: { _cssPath, _truncate, _context, AREAS, STYLE_KEYS },
    };
})();
