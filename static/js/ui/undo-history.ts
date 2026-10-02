/**
 * undo-history.js — visible undo history dropdown (task-371).
 *
 * 📜 button in the graph toolbar: lists every labeled undo snapshot
 * (newest first; index 0 = what a single Undo restores). Clicking a row
 * restores the world back to that point via multi-step undo.
 *
 * @module ui/undo-history — visible undo history dropdown
 * @contributes UndoHistory: list labeled snapshots (newest first) and restore to any point
 * @powers Recent edits / undo — seeing and jumping through the edit history (task-371)
 * @relates reads the undo stack; opened from the 📜 button in the graph toolbar
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const UndoHistory = (() => {
    'use strict';

    let _open = false;

    function menuEl() { return document.getElementById('undo-history-menu'); }

    async function refresh() {
        const menu = menuEl();
        if (!menu) return;
        let entries: UndoEntry[] = [];
        try {
            const resp = await fetch('/api/undo/list');
            entries = (await resp.json()).entries || [];
        } catch (e) { entries = []; }
        menu.textContent = '';
        if (!entries.length) {
            const none = document.createElement('div');
            none.style.cssText = 'padding:8px;font-size:11px;color:var(--text-muted);';
            none.textContent = 'No undo history yet.';
            menu.appendChild(none);
            return;
        }
        entries.forEach((entry: UndoEntry, idx: number) => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;gap:6px;align-items:center;padding:5px 8px;font-size:11.5px;cursor:pointer;border-radius:6px;white-space:nowrap;';
            row.onmouseenter = () => { row.style.background = 'rgba(255,255,255,0.05)'; };
            row.onmouseleave = () => { row.style.background = 'transparent'; };
            row.onclick = () => restoreTo(idx);
            const icon = document.createElement('span');
            icon.textContent = '↩';
            const label = document.createElement('span');
            label.textContent = entry.label || ('snapshot ' + idx);
            label.style.cssText = 'overflow:hidden;text-overflow:ellipsis;max-width:260px;';
            const depth = document.createElement('span');
            depth.textContent = idx === 0 ? '(next undo)' : `+${idx} undos`;
            depth.style.cssText = 'font-size:10px;color:var(--text-dim);margin-left:auto;';
            row.appendChild(icon);
            row.appendChild(label);
            row.appendChild(depth);
            menu.appendChild(row);
        });
    }

    async function restoreTo(idx: number) {
        try {
            const resp = await fetch('/api/undo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ steps: idx + 1 })
            });
            const data = await resp.json();
            if (data.error) { toastError('Undo failed: ' + data.error); return; }
            try { graphManager.loadGraphData(); } catch (e) {}
            worldState.fetch();
            if (typeof toastInfo === 'function') toastInfo('Restored (' + (idx + 1) + ' step' + (idx ? 's' : '') + ').');
            close();
        } catch (e) {
            console.error('[undo-history] restore failed:', e);
            toastError('Undo failed: ' + (e instanceof Error ? e.message : String(e)));
        }
    }

    function close() {
        _open = false;
        const menu = menuEl();
        if (menu) menu.style.display = 'none';
    }

    async function toggle() {
        const menu = menuEl();
        if (!menu) return;
        _open = !_open;
        if (_open) {
            menu.style.display = 'block';
            await refresh();
        } else {
            menu.style.display = 'none';
        }
    }

    // Close on outside click / Escape.
    document.addEventListener('click', (ev) => {
        const menu = menuEl();
        if (!menu || menu.style.display === 'none') return;
        const target = ev.target as Element | null;
        if (target?.closest && target.closest('#undo-history-menu')) return;
        if (target?.closest && target.closest('[data-role="undo-history-toggle"]')) return;
        close();
    });
    document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') close(); });

    return { toggle, refresh, close };
})();

(window as unknown as { UndoHistory: typeof UndoHistory }).UndoHistory = UndoHistory;

// Declared below the first value statement on purpose: TypeScript drops a
// file's leading JSDoc block when the first statement is type-only, which
// would strip the `@module` header tools/js_module_index.py reads.
interface UndoEntry { label?: string; [key: string]: unknown }
