/**
 * command-palette.js — Ctrl+K command palette (task-370).
 *
 * Fuzzy search across:
 *   - every graph node (areas / items / ways / characters) → jump + inspect
 *   - menu & system actions (save, commit, restart, wizard, settings, undo…)
 *   - left-panel tabs (Agents / Outline / Lens / Issues)
 *
 * Keyboard: Ctrl+K (or ⌘K) open · ↑↓ navigate · Enter run · Esc close.
 */

window.CommandPalette = (() => {
    'use strict';

    const NODE_ICONS = { area: '🏠', item: '📦', way: '🚪', character: '🧍', logic_trigger: '⚡', trigger: '⚡' };
    const TAB_NAMES = { '🧍 Agents': 'Agents', '🗺️ Outline': 'Outline', '👁 Lens': 'Lens', '🛠 Issues': 'Issues', '✨ NL Editor': 'NL Editor' };

    const ACTIONS = [
        { icon: '✨', label: 'Natural-Language Editor (Cmd+L / Ctrl+L)', run: () => window.NLEditor?.openPanel() },
        { icon: '💾', label: 'Save Game', run: () => saveGame() },
        { icon: '📂', label: 'Load Game…', run: () => { document.getElementById('load-game-modal').style.display = 'flex'; loadGameList(); } },
        { icon: '📄', label: 'Load JSON… (import with preview)', run: () => document.getElementById('file-upload').click() },
        { icon: '📤', label: 'Export Scenario File…', run: () => saveScenarioToFile() },
        { icon: '💾', label: 'Commit Scenario (save live world into source)', run: () => ScenarioStatus.commit() },
        { icon: '🆕', label: 'New Scenario', run: () => newScenario() },
        { icon: '🔄', label: 'Restart Scenario', run: () => restartScenario() },
        { icon: '✨', label: 'Scenario from Text…', run: () => ScenarioWizard.open() },
        { icon: '⚙️', label: 'Settings', run: () => { document.getElementById('settings-modal').style.display = 'flex'; setTimeout(populateSettingsForm, 50); } },
        { icon: '👁', label: 'Toggle Spectator', run: () => toggleSpectator() },
        { icon: '↩️', label: 'Undo', run: () => graphEditor.undo() },
        { icon: '↪️', label: 'Redo', run: () => graphEditor.redo() },
        { icon: '📋', label: 'Copy Prompt', run: () => copyPromptToClipboard() },
        { icon: '🏁', label: 'Start Agents', run: () => startAgent() },
        { icon: '⏸', label: 'Stop Agents', run: () => stopAgent() },
        { icon: '🧍', label: 'Panel: Agents', run: () => switchTab('Agents') },
        { icon: '🗺️', label: 'Panel: Outline', run: () => switchTab('Outline') },
        { icon: '👁', label: 'Panel: Lens', run: () => switchTab('Lens') },
        { icon: '🛠', label: 'Panel: Issues', run: () => switchTab('Issues') },
        { icon: '✨', label: 'Panel: NL Editor', run: () => switchTab('NL Editor') },
    ];

    function switchTab(name) {
        const tab = Array.from(document.querySelectorAll('[role="tab"]'))
            .find(t => (t.textContent || '').trim().endsWith(name));
        if (tab) tab.click();
    }

    function nodeEntries() {
        const out = [];
        const nodes = (worldState && worldState.graph && worldState.graph.nodes) || {};
        for (const [id, node] of Object.entries(nodes)) {
            if (!node || !node.type) continue;
            out.push({
                icon: NODE_ICONS[node.type] || '📌',
                label: node.name || id,
                sub: `${node.type} · ${id}`,
                run: () => {
                    try { graphManager.showNodeAndFocus(id); }
                    catch (e) { try { VW.inspector.showNode(id); } catch (e2) {} }
                },
            });
        }
        return out;
    }

    function score(entry, q) {
        const label = (entry.label || '').toLowerCase();
        const sub = (entry.sub || '').toLowerCase();
        let s = 0;
        if (label === q) s = 10;
        else if (label.startsWith(q)) s = 7;
        else if (label.includes(' ' + q) || label.startsWith(q)) s = 6;
        else if (label.includes(q)) s = 5;
        else if (sub.includes(q)) s = 3;
        return s;
    }

    let overlayEl = null, inputEl = null, listEl = null;
    let results = [];
    let selected = 0;
    let entriesCache = null;

    function buildEntries() {
        if (!entriesCache) entriesCache = [...nodeEntries(), ...ACTIONS];
        return entriesCache;
    }

    function render(filter) {
        const q = (filter || '').toLowerCase().trim();
        if ((filter || '').trim().startsWith('>')) {
            // task-387: '>' routes the rest of the line to the NL Editor.
            results = [{
                icon: '✨',
                label: `NL Editor: ${(filter || '').trim().slice(1).trim() || '…'}`,
                sub: 'natural-language edit — opens the ✨ NL Editor and runs it',
                run: () => runEditorText((filter || '').trim().slice(1).trim())
            }];
            selected = 0;
            listEl.textContent = '';
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 10px;font-size:12.5px;cursor:pointer;border-radius:6px;background:rgba(88,166,255,0.14);';
            row.appendChild(Object.assign(document.createElement('span'), { textContent: results[0].icon }));
            const label = document.createElement('span');
            label.textContent = results[0].label;
            label.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            row.appendChild(label);
            const sub = document.createElement('span');
            sub.textContent = results[0].sub;
            sub.style.cssText = 'font-size:10px;color:var(--text-dim);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            row.appendChild(sub);
            row.onclick = () => { selected = 0; runSelected(); };
            listEl.appendChild(row);
            return;
        }
        let entries = buildEntries();
        if (q) {
            entries = entries
                .map(e => ({ e, s: score(e, q) }))
                .filter(x => x.s > 0)
                .sort((a, b) => b.s - a.s)
                .map(x => x.e);
        }
        results = entries.slice(0, 14);
        selected = 0;
        listEl.textContent = '';
        if (!results.length) {
            const empty = document.createElement('div');
            empty.style.cssText = 'padding:12px;font-size:12px;color:var(--text-muted);';
            empty.textContent = q ? 'Nothing matches "' + filter + '".' : '';
            listEl.appendChild(empty);
            return;
        }
        results.forEach((entry, idx) => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 10px;font-size:12.5px;cursor:pointer;border-radius:6px;' +
                (idx === selected ? 'background:rgba(88,166,255,0.14);' : '');
            row.dataset.idx = idx;
            row.onmouseenter = () => { selected = idx; paintSelection(); };
            row.onclick = () => { selected = idx; runSelected(); };
            const icon = document.createElement('span');
            icon.textContent = entry.icon;
            const label = document.createElement('span');
            label.textContent = entry.label;
            label.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            const sub = document.createElement('span');
            sub.textContent = entry.sub || '';
            sub.style.cssText = 'font-size:10px;color:var(--text-dim);max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            row.appendChild(icon);
            row.appendChild(label);
            row.appendChild(sub);
            listEl.appendChild(row);
        });
    }

    function paintSelection() {
        Array.from(listEl.children).forEach((row, idx) => {
            row.style.background = idx === selected ? 'rgba(88,166,255,0.14)' : 'transparent';
        });
    }

    /** task-387: '>' prefix — run a natural-language edit from the palette. */
    function runEditorText(text) {
        close();
        window.NLEditor?.openPanel();
        setTimeout(() => {
            const el = document.getElementById('nl-input');
            if (el && text) {
                el.value = text;
                el.focus();
            }
            if (text) window.NLEditor?.send(text);
        }, 180);
    }

    function runSelected() {
        const entry = results[selected];
        if (entry) {
            entriesCache = null;
            close();
            try { entry.run(); } catch (e) { console.error('[command-palette] action failed:', e); }
        }
    }

    function close() {
        if (overlayEl && overlayEl.parentNode) overlayEl.parentNode.removeChild(overlayEl);
        overlayEl = null; inputEl = null; listEl = null; results = []; entriesCache = null;
    }

    function open() {
        if (overlayEl) { close(); return; }
        entriesCache = null;
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.45);display:flex;align-items:flex-start;justify-content:center;z-index:20000;';
        const box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:12px;margin-top:90px;width:560px;max-width:92vw;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.5);';
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Jump to a node, type an action…, or type "> …" to run the NL Editor (Ctrl+K)';
        input.style.cssText = 'width:100%;font-size:14px;padding:12px 14px;background:transparent;border:none;border-bottom:1px solid var(--border);color:var(--text);outline:none;box-sizing:border-box;';
        input.oninput = () => render(input.value);
        input.onkeydown = (ev) => {
            if (ev.key === 'ArrowDown') { ev.preventDefault(); selected = Math.min(selected + 1, results.length - 1); paintSelection(); }
            else if (ev.key === 'ArrowUp') { ev.preventDefault(); selected = Math.max(selected - 1, 0); paintSelection(); }
            else if (ev.key === 'Enter') { ev.preventDefault(); runSelected(); }
            else if (ev.key === 'Escape') { ev.preventDefault(); close(); }
        };
        const list = document.createElement('div');
        list.style.cssText = 'max-height:46vh;overflow-y:auto;padding:6px;';
        const hint = document.createElement('div');
        hint.style.cssText = 'font-size:10px;color:var(--text-dim);padding:6px 12px;border-top:1px solid var(--border);';
        hint.textContent = '↑↓ navigate · Enter run · Esc close — search nodes, actions, panels';
        overlay.appendChild(box);
        box.appendChild(input);
        box.appendChild(list);
        box.appendChild(hint);
        overlay.addEventListener('mousedown', (ev) => { if (ev.target === overlay) close(); });
        document.body.appendChild(overlay);
        overlayEl = overlay; inputEl = input; listEl = list;
        render('');
        setTimeout(() => input.focus(), 20);
    }

    document.addEventListener('keydown', (ev) => {
        if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'l' || ev.key === 'L')) {
            ev.preventDefault();
            window.NLEditor?.openPanel();
            return;
        }
        if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'k' || ev.key === 'K')) {
            ev.preventDefault();
            open();
            return;
        }
        // Keyboard map (task-386): Ctrl+S commit, Ctrl+Z undo — only when
        // not typing in a field (native shortcuts keep working there).
        const typing = ev.target && (
            ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA' ||
            ev.target.tagName === 'SELECT' || ev.target.isContentEditable
        );
        if (typing) return;
        if ((ev.ctrlKey || ev.metaKey) && (ev.key === 's' || ev.key === 'S')) {
            ev.preventDefault();
            ScenarioStatus.commit();
        } else if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'z' || ev.key === 'Z') && !ev.shiftKey) {
            ev.preventDefault();
            graphEditor.undo();
        } else if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'Z') && ev.shiftKey) {
            ev.preventDefault();
            graphEditor.redo();
        }
    });

    return { open, close, toggle: open };
})();
