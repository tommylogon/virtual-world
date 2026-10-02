/**
 * command-palette.js — Ctrl+K command palette (task-370).
 *
 * Fuzzy search across:
 *   - every graph node (areas / items / ways / characters) → jump + inspect
 *   - menu & system actions (save, commit, restart, wizard, settings, undo…)
 *   - left-panel tabs (Agents / Outline / Lens / Issues)
 *
 * Keyboard: Ctrl+K (or ⌘K) open · ↑↓ navigate · Enter run · Esc close.
 *
 * @module ui/command-palette — Ctrl+K fuzzy command palette
 * @contributes CommandPalette: fuzzy search over graph nodes, menu actions, and left-panel tabs
 * @powers Command palette — keyboard-first navigation and commands (task-370)
 * @relates navigates the graph + opens the inspector; runs toolbar actions
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

window.CommandPalette = (() => {
    'use strict';

    // NOTE ON PLACEMENT: every type below is declared inside this IIFE on
    // purpose. A top-level `interface`/`type` in a classic script is a GLOBAL
    // binding, so two files declaring the same name is a redeclaration error —
    // and tsc drops the leading `@module` JSDoc above when the first statement
    // in a file is type-only. Keeping them in function scope avoids both.

    /** One palette row: a graph node, a menu action, or the synthetic '>' row. */
    interface CommandPaletteEntry {
        icon: string;
        label: string;
        sub?: string;
        tags?: string[];
        run(): void;
    }

    /** The part of a graph node this palette reads to build a row. */
    interface CommandPaletteNode {
        type?: string;
        name?: string;
        properties?: { tags?: unknown };
    }

    /** The `graphEditor` toolbar object owned by main.ts (undo/redo/templates). */
    interface CommandPaletteGraphEditor {
        undo(): void;
        redo(): void;
    }

    /** Shape of every top-level `function` declaration this palette invokes. */
    type CommandPaletteMainAction = () => unknown;

    /**
     * Reads a name out of this script's global scope.
     *
     * Why not a bare identifier and why not `window.X`:
     *
     * - These bindings live in main.ts. `ts_convert.py build-one` type-checks
     *   this file against `globals.d.ts` alone, which declares none of them, so
     *   a bare `saveGame` is TS2304 here even though `npm run build:ts` (which
     *   also compiles main.ts) accepts it. The pre-conversion source used the
     *   bare spelling.
     * - `window.saveGame` happens to work — a top-level `function` declaration
     *   does become a globalThis property — but `window.graphEditor` does NOT:
     *   a top-level `const` in a classic script is a global *lexical* binding
     *   and leaves no property behind. That is exactly why
     *   templates/index.html's inline `onclick="graphEditor.undo()"` works and
     *   `window.graphEditor` would silently be `undefined`.
     *
     * Direct `eval` walks this IIFE's scope chain and then the global
     * environment, so it finds both kinds of binding, and a name that does not
     * exist still raises the same ReferenceError the bare call raised.
     *
     * Needs in globals.d.ts: saveGame, loadGameList, saveScenarioToFile,
     * newScenario, restartScenario, populateSettingsForm, toggleSpectator,
     * copyPromptToClipboard, startAgent, stopAgent, graphEditor.
     */
    function mainGlobal<T>(name: string): T {
        return eval(name) as T;
    }

    const NODE_ICONS: Record<string, string> = { area: '🏠', item: '📦', way: '🚪', character: '🧍', logic_trigger: '⚡', trigger: '⚡' };
    const TAB_NAMES: Record<string, string> = { '🧍 Agents': 'Agents', '🗺️ Outline': 'Outline', '👁 Lens': 'Lens', '🛠 Issues': 'Issues', '✨ NL Editor': 'NL Editor' };

    const mainActions = {
        saveGame: () => mainGlobal<CommandPaletteMainAction>('saveGame')(),
        loadGameList: () => mainGlobal<CommandPaletteMainAction>('loadGameList')(),
        saveScenarioToFile: () => mainGlobal<CommandPaletteMainAction>('saveScenarioToFile')(),
        newScenario: () => mainGlobal<CommandPaletteMainAction>('newScenario')(),
        restartScenario: () => mainGlobal<CommandPaletteMainAction>('restartScenario')(),
        populateSettingsForm: () => mainGlobal<CommandPaletteMainAction>('populateSettingsForm')(),
        toggleSpectator: () => mainGlobal<CommandPaletteMainAction>('toggleSpectator')(),
        copyPromptToClipboard: () => mainGlobal<CommandPaletteMainAction>('copyPromptToClipboard')(),
        startAgent: () => mainGlobal<CommandPaletteMainAction>('startAgent')(),
        stopAgent: () => mainGlobal<CommandPaletteMainAction>('stopAgent')(),
        // `const`, not `function` — see mainGlobal's note before touching this.
        graphEditor: () => mainGlobal<CommandPaletteGraphEditor>('graphEditor'),
    };

    const ACTIONS: CommandPaletteEntry[] = [
        { icon: '⏩', label: 'Timeskip… (wait / mingle / search / explore / travel)', run: () => window.Timeskip?.openDialog() },
        { icon: '✨', label: 'Natural-Language Editor (Cmd+L / Ctrl+L)', run: () => window.NLEditor?.openPanel() },
        { icon: '💾', label: 'Save Game', run: () => mainActions.saveGame() },
        { icon: '📂', label: 'Load Game…', run: () => { (document.getElementById('load-game-modal') as HTMLElement).style.display = 'flex'; mainActions.loadGameList(); } },
        { icon: '📄', label: 'Load JSON… (import with preview)', run: () => (document.getElementById('file-upload') as HTMLButtonElement).click() },
        { icon: '📤', label: 'Export Scenario File…', run: () => mainActions.saveScenarioToFile() },
        { icon: '💾', label: 'Commit Scenario (save live world into source)', run: () => window.ScenarioStatus.commit() },
        { icon: '🆕', label: 'New Scenario', run: () => mainActions.newScenario() },
        { icon: '🔄', label: 'Restart Scenario', run: () => mainActions.restartScenario() },
        { icon: '✨', label: 'Scenario from Text…', run: () => window.ScenarioWizard.open() },
        { icon: '⚙️', label: 'Settings', run: () => { (document.getElementById('settings-modal') as HTMLElement).style.display = 'flex'; setTimeout(mainActions.populateSettingsForm, 50); } },
        { icon: '👁', label: 'Toggle Spectator', run: () => mainActions.toggleSpectator() },
        { icon: '↩️', label: 'Undo', run: () => mainActions.graphEditor().undo() },
        { icon: '↪️', label: 'Redo', run: () => mainActions.graphEditor().redo() },
        { icon: '📋', label: 'Copy Prompt', run: () => mainActions.copyPromptToClipboard() },
        { icon: '🏁', label: 'Start Agents', run: () => mainActions.startAgent() },
        { icon: '⏸', label: 'Stop Agents', run: () => mainActions.stopAgent() },
        { icon: '🧍', label: 'Panel: Agents', run: () => switchTab('Agents') },
        { icon: '🗺️', label: 'Panel: Outline', run: () => switchTab('Outline') },
        { icon: '👁', label: 'Panel: Lens', run: () => switchTab('Lens') },
        { icon: '🛠', label: 'Panel: Issues', run: () => switchTab('Issues') },
        { icon: '✨', label: 'Panel: NL Editor', run: () => switchTab('NL Editor') },
        { icon: '🧪', label: 'LLM Dataset (capture & export fine-tuning data)', run: () => window.DatasetCollector?.togglePanel() },
    ];

    function switchTab(name: string) {
        const tab = Array.from(document.querySelectorAll<HTMLElement>('[role="tab"]'))
            .find(t => (t.textContent || '').trim().endsWith(name));
        if (tab) tab.click();
    }

    function nodeEntries(): CommandPaletteEntry[] {
        const out: CommandPaletteEntry[] = [];
        const nodes: Record<string, CommandPaletteNode> =
            (worldState && worldState.graph && worldState.graph.nodes) || {};
        for (const [id, node] of Object.entries(nodes)) {
            if (!node || !node.type) continue;
            const tags = node.properties?.tags;
            const tagList = Array.isArray(tags)
                ? tags.map(String)
                : (tags ? String(tags).split(',').map(s => s.trim()).filter(Boolean) : []);
            out.push({
                icon: NODE_ICONS[node.type] || '📌',
                label: node.name || id,
                sub: tagList.length ? `${node.type} · ${id} · tags: ${tagList.join(', ')}` : `${node.type} · ${id}`,
                tags: tagList.map(t => t.toLowerCase()),
                run: () => {
                    try { graphManager.showNodeAndFocus(id); }
                    // Neither surface answered: the node is not focusable here.
                    catch (e) { try { VW.inspector.showNode(id); } catch (e2) { /* neither surface available */ } }
                },
            });
        }
        return out;
    }

    function score(entry: CommandPaletteEntry, q: string): number {
        const label = (entry.label || '').toLowerCase();
        const sub = (entry.sub || '').toLowerCase();
        let s = 0;
        if (label === q) s = 10;
        else if (label.startsWith(q)) s = 7;
        else if (label.includes(' ' + q) || label.startsWith(q)) s = 6;
        else if (label.includes(q)) s = 5;
        else if (sub.includes(q)) s = 3;
        else if ((entry.tags || []).some(t => t === q)) s = 8;
        else if ((entry.tags || []).some(t => t.includes(q))) s = 4;
        return s;
    }

    let overlayEl: HTMLElement | null = null;
    let inputEl: HTMLInputElement | null = null;
    let listEl: HTMLElement | null = null;
    let results: CommandPaletteEntry[] = [];
    let selected = 0;
    let entriesCache: CommandPaletteEntry[] | null = null;

    function buildEntries(): CommandPaletteEntry[] {
        if (!entriesCache) entriesCache = [...nodeEntries(), ...ACTIONS];
        return entriesCache;
    }

    function render(filter: string) {
        // render() only runs from open(), which assigns listEl before the first
        // call; the assertion states that invariant instead of re-testing it.
        const list = listEl!;
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
            list.textContent = '';
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 10px;font-size:12.5px;cursor:pointer;border-radius:6px;background:rgba(88,166,255,0.14);';
            row.appendChild(Object.assign(document.createElement('span'), { textContent: results[0].icon }));
            const label = document.createElement('span');
            label.textContent = results[0].label;
            label.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            row.appendChild(label);
            const sub = document.createElement('span');
            sub.textContent = results[0].sub || '';
            sub.style.cssText = 'font-size:10px;color:var(--text-dim);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            row.appendChild(sub);
            row.onclick = () => { selected = 0; runSelected(); };
            list.appendChild(row);
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
        list.textContent = '';
        if (!results.length) {
            const empty = document.createElement('div');
            empty.style.cssText = 'padding:12px;font-size:12px;color:var(--text-muted);';
            empty.textContent = q ? 'Nothing matches "' + filter + '".' : '';
            list.appendChild(empty);
            return;
        }
        results.forEach((entry, idx) => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 10px;font-size:12.5px;cursor:pointer;border-radius:6px;' +
                (idx === selected ? 'background:rgba(88,166,255,0.14);' : '');
            row.dataset.idx = String(idx);
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
            list.appendChild(row);
        });
    }

    function paintSelection() {
        (Array.from(listEl!.children) as HTMLElement[]).forEach((row, idx) => {
            row.style.background = idx === selected ? 'rgba(88,166,255,0.14)' : 'transparent';
        });
    }

    /** task-387: '>' prefix — run a natural-language edit from the palette. */
    function runEditorText(text: string) {
        close();
        window.NLEditor?.openPanel();
        setTimeout(() => {
            const el = document.getElementById('nl-input') as HTMLInputElement | null;
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
        input.placeholder = 'Jump to a node (name or tag), type an action…, or type "> …" to run the NL Editor (Ctrl+K)';
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
        const target = ev.target as HTMLElement | null;
        const typing = target && (
            target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' ||
            target.tagName === 'SELECT' || target.isContentEditable
        );
        if (typing) return;
        if ((ev.ctrlKey || ev.metaKey) && (ev.key === 's' || ev.key === 'S')) {
            ev.preventDefault();
            window.ScenarioStatus.commit();
        } else if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'z' || ev.key === 'Z') && !ev.shiftKey) {
            ev.preventDefault();
            mainActions.graphEditor().undo();
        } else if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'Z') && ev.shiftKey) {
            ev.preventDefault();
            mainActions.graphEditor().redo();
        }
    });

    return { open, close, toggle: open };
})();