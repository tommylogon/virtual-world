/**
 * recent-edits.js — "where was I" rail (task-372).
 *
 * Records every node the GUI edits via ApiClient (updateNode / duplicateNode)
 * into a session-local history and exposes a floating 🕘 button (bottom-left)
 * that opens the list; click an entry to jump to that node.
 */

(() => {
    'use strict';

    const KEY = 'vw_recent_edits';
    const MAX = 10;

    function load() {
        try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; }
    }
    function save(list) {
        try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) {}
    }

    function record(nodeId, label) {
        if (!nodeId) return;
        let list = load().filter(e => e.id !== nodeId);
        list.unshift({ id: String(nodeId), label: label || 'edited', at: Date.now() });
        list = list.slice(0, MAX);
        save(list);
        renderBadge();
    }

    const NODE_ICONS = { area: '🏠', item: '📦', way: '🚪', character: '🧍' };

    function nodeLabel(id) {
        const node = (window.worldState && worldState.getNode && worldState.getNode(id)) || null;
        if (node) return `${NODE_ICONS[node.type] || '📌'} ${node.name || id}`;
        return id;
    }

    function renderBadge() {
        const btn = document.getElementById('recent-edits-toggle');
        if (!btn) return;
        const n = load().length;
        btn.textContent = '🕘';
        btn.title = n ? `Recently edited (${n})` : 'Recently edited (none yet)';
        btn.style.opacity = n ? '1' : '0.45';
    }

    function buildUI() {
        document.addEventListener('DOMContentLoaded', () => {
            const btn = document.createElement('button');
            btn.id = 'recent-edits-toggle';
            btn.className = 'btn btn-sm';
            btn.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:9000;opacity:0.45;';
            btn.onclick = () => toggleList();
            document.body.appendChild(btn);

            const menu = document.createElement('div');
            menu.id = 'recent-edits-menu';
            menu.style.cssText = 'display:none;position:fixed;left:8px;bottom:38px;z-index:9000;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:4px;min-width:220px;max-width:320px;';
            document.body.appendChild(menu);

            renderBadge();
        });
    }

    function toggleList() {
        const menu = document.getElementById('recent-edits-menu');
        if (!menu) return;
        const showing = menu.style.display !== 'none';
        menu.style.display = showing ? 'none' : 'block';
        if (!showing) {
            menu.textContent = '';
            const list = load();
            if (!list.length) {
                const none = document.createElement('div');
                none.style.cssText = 'padding:8px;font-size:11px;color:var(--text-muted);';
                none.textContent = 'Nothing edited yet in this browser.';
                menu.appendChild(none);
                return;
            }
            list.forEach((entry, idx) => {
                const row = document.createElement('div');
                row.style.cssText = 'display:flex;gap:6px;align-items:center;padding:5px 8px;font-size:11.5px;cursor:pointer;border-radius:6px;';
                row.onmouseenter = () => { row.style.background = 'rgba(255,255,255,0.05)'; };
                row.onmouseleave = () => { row.style.background = 'transparent'; };
                row.onclick = () => {
                    try { graphManager.showNodeAndFocus(entry.id); } catch (e) { try { VW.inspector.showNode(entry.id); } catch (e2) {} }
                    menu.style.display = 'none';
                };
                const label = document.createElement('span');
                label.textContent = nodeLabel(entry.id);
                label.style.cssText = 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:240px;';
                const when = new Date(entry.at);
                const ago = document.createElement('span');
                ago.textContent = when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                ago.style.cssText = 'font-size:10px;color:var(--text-dim);margin-left:auto;';
                row.appendChild(label);
                row.appendChild(ago);
                menu.appendChild(row);
            });
        }
    }

    // Hook the API client — record what WE edit, not remote agents.
    const origUpdate = ApiClient.updateNode;
    ApiClient.updateNode = function (nodeId, data) {
        record(nodeId, 'updated');
        return origUpdate.apply(this, arguments);
    };
    const origDup = ApiClient.duplicateNode;
    ApiClient.duplicateNode = function (nodeId) {
        record(nodeId, 'duplicated');
        return origDup.apply(this, arguments);
    };

    buildUI();
})();
