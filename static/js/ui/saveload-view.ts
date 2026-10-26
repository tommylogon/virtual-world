/**
 * saveload-view.js  -  Save/load game UI module
 * Extracted from main.js. Provides SaveLoadView singleton.
 *
 * Dependencies:
 *   - window.api / window.ApiClient
 *   - window.events (EventBus)
 *   - agent (AgentEngine)
 *   - worldState (WorldState)
 *   - window.config (ConfigManager)
 *   - window.WorldExport.saveFileWithDialog (for downloadWorld)
 *   - Global: toastSuccess, toastError, toastInfo (from ui-helpers.js)
 *   - DOM elements: #save-game-list, #save-game-name-input, #load-game-modal, etc.
 *
 * @module ui/saveload-view  -  save/load game UI
 * @contributes SaveLoadView: save list, save/load/delete, named saves
 * @powers keeping and restoring your world (extracted from main.js)
 * @relates uses api + events + config; delegates downloads to shared WorldExport
 * @docs docs/virtualWorld/UI & Settings/Settings & Configuration.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const saveLoadViewTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);

// ui-helpers.js stamps toastSuccess on window, but it has no
// globals.d.ts declaration  -  call it through a cast at call time.
function saveloadToastSuccess(message: string) {
    (window as unknown as { toastSuccess: (message: string) => void }).toastSuccess(message);
}

// catch vars are `unknown` under strict; this keeps the original
// `err.message` behaviour for Error throws and stringifies anything else.
function saveloadErrMessage(err: unknown): string {
    return err instanceof Error ? err.message : String(err);
}

window.SaveLoadView = (() => {
    'use strict';

    function initScenarioNameEditor() {
        var container = document.getElementById('scenario-name-container');
        var textSpan = document.getElementById('scenario-name-text');
        if (!container || !textSpan) return;

        container.addEventListener('click', function(e) {
            if ((e.target as HTMLElement).tagName === 'INPUT') return;
            var currentName = document.body.dataset.scenarioName || textSpan!.textContent || 'unnamed';
            var input = document.createElement('input');
            input.type = 'text';
            input.value = currentName;
            input.style.cssText = 'background:var(--bg-input);color:var(--text);border:1px solid var(--accent);padding:2px 6px;font-size:12px;width:160px;font-family:var(--font);';
            textSpan!.replaceWith(input);
            input.focus();
            input.select();

            function saveName() {
                var newName = input.value.trim() || 'unnamed';
                var newText = document.createElement('span');
                newText.id = 'scenario-name-text';
                newText.textContent = newName;
                input.replaceWith(newText);
                if (newName !== currentName) persistScenarioName(newName, currentName, newText);
            }

            input.addEventListener('blur', saveName);
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
                if (e.key === 'Escape') { input.value = currentName; input.blur(); }
            });
        });
    }

    /**
     * Persist the scenario name on the SERVER.
     *
     * The name is not cosmetic  -  it decides where a commit writes (so a world
     * booted from a shared template stops committing into that template), and it
     * keys the per-scenario graph-background cache. The server is the source of
     * truth, so a failure reverts the chip rather than lying to the user.
     */
    async function persistScenarioName(name: string, previous: string, textEl: HTMLElement | null) {
        try {
            const resp = await fetch('/api/scenario/name', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name }),
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok || data.error) throw new Error(data.error || ('HTTP ' + resp.status));

            const applied = data.name || name;
            document.body.dataset.scenarioName = applied;
            if (textEl) textEl.textContent = applied;
            // Update the cached world state so the background cache re-keys now.
            if (typeof worldState !== 'undefined' && worldState && worldState.data) {
                worldState.data._scenario_name = applied;
            }
            if (data.warning && typeof toastInfo === 'function') toastInfo(data.warning);
            try { events.log(`🌍 Scenario named "${applied}".`, 'system-msg'); } catch (e) { /* ignore */ }
        } catch (err) {
            document.body.dataset.scenarioName = previous;
            if (textEl) textEl.textContent = previous;
            if (typeof toastError === 'function') {
                toastError('Rename failed: ' + saveloadErrMessage(err));
            }
        }
    }

    /**
     * Download the current world state as a JSON file.
     */
    function downloadWorld() {
        api.saveWorld().then(function(data: any) {
            var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            WorldExport.saveFileWithDialog(blob, 'world_save.json');
        });
    }

    /**
     * Upload/load a world from a user-selected JSON file  -  WITH a preview.
     * Shows counts + sanity issues before anything touches the live world.
     * @param {Event} event - The file input change event
     */
    function uploadWorld(event: Event) {
        var file = (event.target as HTMLInputElement).files?.[0];
        if (!file) return;
        var scenarioName = file.name.replace(/\.json$/i, '');
        var reader = new FileReader();
        reader.onload = function(e) {
            try {
                var data = JSON.parse((e.target as FileReader).result as string);
            } catch (err) {
                toastError('Invalid JSON: ' + saveloadErrMessage(err));
                (event.target as HTMLInputElement).value = '';
                return;
            }
            openImportPreview(file!.name, scenarioName, data);
        };
        reader.readAsText(file);
        (event.target as HTMLInputElement).value = '';
    }

    /**
     * Rough counts + sanity pass over an incoming world/template dict.
     * Never blocks  -  the preview is informational; Apply is undo-protected.
     */
    function inspectImport(data: any) {
        var isTemplate = ('player' in data) && !('players' in data);
        var areas = data.areas || {};
        var areaKeys: Record<string, boolean> = {};
        var roomCount = 0;
        var graph = data.graph || {};
        var nodes = graph.nodes || {};

        // Authoring templates store areas in `areas`; saved world states use
        // graph area nodes as the single source of truth.
        function addArea(id: any, name: any) {
            var aliases = [id, name].filter(function(value) {
                return value !== undefined && value !== null && String(value).trim();
            }).map(function(value) { return String(value).toLowerCase(); });
            var alreadyCounted = aliases.some(function(alias) { return !!areaKeys[alias]; });
            aliases.forEach(function(alias) { areaKeys[alias] = true; });
            if (!alreadyCounted) roomCount += 1;
        }

        if (isTemplate) {
            Object.keys(areas).forEach(function(k) {
                var area = areas[k] || {};
                addArea(area.id || k, area.name);
            });
        }
        Object.keys(nodes).forEach(function(id) {
            var node = nodes[id];
            if (node && node.type === 'area') addArea(node.id || id, node.name);
        });
        var itemCount = 0, wayCount = 0, playerNames = [];

        function countExits(exits: any) {
            var n = 0;
            Object.keys(exits || {}).forEach(function(dir) {
                n += 1;
                var t = exits[dir];
                var target = (t && typeof t === 'object') ? (t.target || '') : t;
                if (target && !areaKeys[String(target).toLowerCase()]) {
                    issues.push('- Exit "' + dir + '" points at missing area "' + target + '".');
                }
            });
            return n;
        }
        var issues: string[] = [];

        if (isTemplate) {
            playerNames.push(data.player && data.player.name ? data.player.name : 'Traveler');
            (data.characters || []).forEach(function(c: any) {
                if (c && c.name) playerNames.push(c.name);
                if (c && c.area && !areaKeys[String(c.area).toLowerCase()]) {
                    issues.push('- Character "' + (c.name || c.area) + '" starts in missing area "' + c.area + '".');
                }
            });
        } else {
            Object.keys(nodes).forEach(function(id) {
                var node = nodes[id];
                if (!node) return;
                if (node.type === 'item') itemCount += 1;
                else if (node.type === 'way') wayCount += 1;
            });
            Object.keys(data.players || {}).forEach(function(pname) { playerNames.push(pname); });
        }
        // Template items and exits still use the authoring `areas` shape.
        // World-state imports count graph nodes only.
        if (isTemplate) {
            Object.keys(areas).forEach(function(aname) {
                var a = areas[aname] || {};
                (a.items || []).forEach(function(it: any) {
                    itemCount += 1;
                    itemCount += (it && it.contents ? it.contents.length : 0);
                });
            });
            Object.keys(areas).forEach(function(aname) {
                wayCount += countExits((areas[aname] || {}).exits);
            });
        }
        if (!isTemplate) {
            Object.values(data.players || {}).forEach(function(p: any) {
                var currentArea = p && (p.current_area || p.current_area_id);
                if (currentArea && !areaKeys[String(currentArea).toLowerCase()]) {
                    issues.push('- Player "' + p.name + '" is in missing area "' + currentArea + '".');
                }
            });
        }
        if (!roomCount) issues.push('- No areas found  -  the world will be empty after load.');
        if (!playerNames.length) issues.push('- No players found.');
        return {
            file: null as string | null,
            isTemplate: isTemplate,
            rooms: roomCount,
            items: itemCount,
            ways: wayCount,
            players: playerNames,
            issues: issues
        };
    }

    /** Refresh every client view after the server replaces the world. */
    async function refreshReplacedWorld() {
        worldState.setRuntimeFocus([]);
        var gm = (window as any).graphManager;
        if (gm) {
            gm._scopeFilter = null;
            if (typeof gm._persistScopeFilter === 'function') gm._persistScopeFilter();
            if (typeof gm.loadScopeFilterOptions === 'function') await gm.loadScopeFilterOptions();
        }
        await worldState.fetch();
        if (gm && typeof gm.loadGraphData === 'function') await gm.loadGraphData();
        var playMode = (window as any).PlayMode;
        if (playMode && typeof playMode.checkStatus === 'function') await playMode.checkStatus();
    }

    /**
     * Preview modal for imported worlds: counts + issues, then [Apply] / [Cancel].
     */
    function openImportPreview(fileName: string, scenarioName: string, data: any) {
        var info = inspectImport(data);
        info.file = fileName;
        var overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        var box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px;width:520px;max-height:85vh;display:flex;flex-direction:column;gap:10px;';

        var header = document.createElement('div');
        header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
        var title = document.createElement('h3');
        title.style.cssText = 'margin:0;font-size:14px;';
        title.textContent = '📂 Import Preview  -  ' + fileName;
        var close = document.createElement('button');
        close.className = 'btn btn-sm';
        close.textContent = '\u2715';
        close.onclick = function() { overlay.remove(); };
        header.appendChild(title);
        header.appendChild(close);
        box.appendChild(header);

        var counts = document.createElement('div');
        counts.style.cssText = 'font-size:12px;';
        counts.innerHTML =
            '🏠 <strong>' + info.rooms + '</strong> rooms · 📦 <strong>' + info.items +
            '</strong> items · 🚪 <strong>' + info.ways + '</strong> ways · 🧍 <strong>' +
            info.players.length + '</strong> characters<br>' +
            '<span style="font-size:10px;color:var(--text-muted);">' +
            (info.isTemplate ? 'format: authoring template' : 'format: world state') +
            '  -  the current world will be replaced (↩ Undo restores it).</span>';
        box.appendChild(counts);

        var issuesBox: HTMLElement | null = null;
        if (info.issues.length) {
            issuesBox = document.createElement('div');
            issuesBox.style.cssText = 'font-size:11px;color:#e3b341;background:rgba(227,179,65,0.08);border:1px solid rgba(227,179,65,0.3);border-radius:8px;padding:8px;max-height:140px;overflow-y:auto;';
            issuesBox.innerHTML = '<strong>⚠ Notes:</strong><br>' + info.issues.map(function(i) { return i.replace(/^- /, ''); }).join('<br>');
            box.appendChild(issuesBox);
        } else {
            issuesBox = document.createElement('div');
            issuesBox.style.cssText = 'font-size:11px;color:#3fb950;';
            issuesBox.textContent = '✅ No sanity issues found.';
            box.appendChild(issuesBox);
        }

        var players = document.createElement('div');
        players.style.cssText = 'font-size:11px;color:var(--text-dim);max-height:80px;overflow-y:auto;';
        players.textContent = info.players.length ? ('Characters: ' + info.players.join(', ')) : 'No characters.';
        box.appendChild(players);

        var footer = document.createElement('div');
        footer.style.cssText = 'display:flex;justify-content:flex-end;gap:8px;';
        var cancel = document.createElement('button');
        cancel.className = 'btn btn-sm';
        cancel.textContent = '✕ Cancel';
        cancel.onclick = function() { overlay.remove(); };
        var audit = document.createElement('button');
        audit.className = 'btn btn-sm';
        audit.textContent = '🔬 Deep audit';
        audit.title = 'Run the full trigger validator on this file (server-side, no load)';
        audit.onclick = function() {
            audit.disabled = true;
            audit.textContent = 'Auditing…';
            fetch('/api/import/audit', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(function(r) { return r.json(); }).then(function(j) {
                audit.disabled = false;
                audit.textContent = '🔬 Deep audit';
                if (j.error) { toastError(j.error); return; }
                var sev = j.severities || {};
                var parts = [];
                if (j.count === 0) parts.push('<span style="color:#3fb950;">✅ Full audit passed  -  no trigger/authoring issues.</span>');
                if (sev.error) parts.push(sev.error + ' error(s)');
                if (sev.warning) parts.push(sev.warning + ' warning(s)');
                if (sev.info) parts.push(sev.info + ' info note(s)');
                var detail = (j.issues || []).slice(0, 6).map(function(i: any) {
                    return (i.severity === 'error' ? '✕ ' : i.severity === 'warning' ? '⚠ ' : 'ℹ ') +
                        String(i.message || '');
                }).join('<br>');
                issuesBox!.innerHTML = '<strong>🔬 Deep audit:</strong> ' + (j.count === 0 ? parts[0] : parts.join(' · ')) +
                    (detail ? '<br>' + detail : '') +
                    (j.count > 6 ? '<br><span style="color:var(--text-muted);">…and ' + (j.count - 6) + ' more (load the world to see them in Issues).</span>' : '');
            }).catch(function(e) {
                audit.disabled = false;
                audit.textContent = '🔬 Deep audit';
                toastError('Audit failed: ' + e.message);
            });
        };
        var apply = document.createElement('button');
        apply.className = 'btn btn-sm btn-green';
        apply.textContent = '✅ Apply (Undo protects)';
        apply.onclick = async function() {
            overlay.remove();
            data._scenario_name = scenarioName;
            data.persist = true;  // GUI apply: keep the scenario file as the source
            api.loadWorld(data).then(async function(resp: any) {
                if (resp && resp.error) {
                    toastError('Load failed: ' + resp.error);
                    events.log('❌ Load failed: ' + resp.error, 'error-msg');
                    return;
                }
                document.body.dataset.scenarioName = scenarioName;
                if (resp.schema_notice) toastInfo(resp.schema_notice);
                events.clearAll();
                agent.reset();
                await refreshReplacedWorld();
                events.log('World loaded!', 'system-msg');
            }).catch(function(err: any) {
                toastError('Network error: ' + err.message);
                events.log('❌ Load network error: ' + err.message, 'error-msg');
            });
        };
        footer.appendChild(cancel);
        footer.appendChild(audit);
        footer.appendChild(apply);
        box.appendChild(footer);

        overlay.appendChild(box);
        document.body.appendChild(overlay);
    }

    /**
     * Save the current scenario to a JSON file with native Save As dialog or fallback.
     */
    async function saveScenarioToFile() {
        var defaultName = document.body.dataset.scenarioName || 'unnamed';
        try {
            // 1. Save to server (persists + sets _scenario_source)
            var res = await api.saveScenario(defaultName);
            if (res.error) { toastError(res.error); return; }
            var name = res.name || defaultName;
            var data = res.data;
            if (!data) { toastError('No scenario data returned.'); return; }

            // 2. Native save dialog (Chromium) or fallback download
            var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            if ('showSaveFilePicker' in window) {
                // The File System Access picker is not on Window in the
                // TS lib, so spell it through a cast (window-assigned API).
                var pickerWindow = window as unknown as { showSaveFilePicker: (options: unknown) => Promise<{ name: string; createWritable(): Promise<{ write(blob: Blob): Promise<void>; close(): Promise<void> }> }> };
                var handle = await pickerWindow.showSaveFilePicker({
                    suggestedName: name + '.json',
                    types: [{ description: 'JSON Scenario', accept: { 'application/json': ['.json'] } }]
                });
                var writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                document.body.dataset.scenarioName = name;
                events.log('Scenario saved to ' + handle.name, 'system-msg');
            } else {
                // Fallback: download + let user rename
                var a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = name + '.json';
                a.click();
                URL.revokeObjectURL(a.href);
                document.body.dataset.scenarioName = name;
                events.log('Scenario "' + name + '" saved!', 'system-msg');
            }
        } catch (e) {
            if (e instanceof Error && (e.name === 'AbortError' || e.name === 'SecurityError')) return; // user cancelled
            toastError('Save failed: ' + saveloadErrMessage(e));
            events.log('Save failed: ' + saveloadErrMessage(e), 'error-msg');
        }
    }

    /**
     * Save the current game state via the API with an optional name.
     * @param {string} [name] - Optional save name from the input field
     */
    async function saveGame(name?: string) {
        var nameInput = document.getElementById('save-game-name-input') as HTMLInputElement | null;
        var saveName = name || (nameInput ? nameInput.value.trim() : '');
        var result = await api.saveGame(saveName || undefined);
        if (result && result.filename) {
            saveloadToastSuccess('Game saved as ' + result.filename);
            if (nameInput) nameInput.value = '';
            events.log('💾 Game saved: ' + result.filename, 'system-msg');
            loadGameList();
        } else {
            toastError('Save failed: ' + (result?.error || 'unknown error'));
        }
    }

    /**
     * Overwrite an existing save slot with the current state.
     * @param {string} filename - Slot file to overwrite
     * @param {string} [label] - Existing display name (kept unless re-entered)
     */
    async function saveGameToSlot(filename: string, label?: string) {
        var result = await api.saveGame(label || undefined, filename);
        if (result && result.filename) {
            saveloadToastSuccess('Slot updated: ' + result.filename);
            events.log('💾 Slot updated: ' + result.filename, 'system-msg');
            loadGameList();
        } else {
            toastError('Slot save failed: ' + (result?.error || 'unknown error'));
        }
    }

    /**
     * Rename a saved game (display name; timestamped files also get renamed).
     */
    /**
     * Rename a saved game using the in-app promise-based prompt (task-455).
     */
    async function doRenameSave(filename: string, currentName?: string) {
        var dialog = window.VW && window.VW.dialog;
        var newName: string | null = null;
        if (dialog && typeof dialog.prompt === 'function') {
            var out = await dialog.prompt({
                title: 'Rename Save',
                message: 'Enter a new display name for "' + (currentName || filename) + '":',
                confirmLabel: 'Rename',
                fields: [{ key: 'name', label: 'Save Name', value: currentName || filename }]
            });
            if (!out) return;
            newName = out.name;
        } else {
            return;
        }
        newName = (newName || '').trim();
        if (!newName) {
            toastError('Save name cannot be empty.');
            return;
        }
        if (newName === currentName) return;

        try {
            var saves = await api.listSaveGames() || [];
            if (saves.some(function(s: any) { return s.filename !== filename && (s.name === newName || s.filename === newName); })) {
                toastError('A save named "' + newName + '" already exists.');
                return;
            }
        } catch (e) { /* non-fatal duplicate check */ }

        var result = await api.renameSaveGame(filename, newName);
        if (result && result.status === 'success') {
            saveloadToastSuccess('Renamed to ' + result.filename);
            events.log('✏️ Save renamed: ' + filename + ' → ' + result.filename, 'system-msg');
            loadGameList();
        } else {
            toastError('Rename failed: ' + (result?.error || 'unknown error'));
        }
    }

    /** Format a byte size for the modal ("3.2 MB"). */
    function fmtSize(bytes: number) {
        if (!bytes && bytes !== 0) return '';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }

    /**
     * Render a single savegame row for the load-game list (task-456).
     */
    function renderSaveRow(save: any) {
        var ts = save.timestamp ? save.timestamp.replace('_', ' ') : '';
        var tickStr = events.tickToTime(save.tick ?? 0);
        var stats = [];
        if (ts) stats.push(ts);
        if (tickStr) stats.push(tickStr);
        if (save.turn != null && save.turn !== 0) stats.push('Turn ' + save.turn);
        if (save.player) stats.push(save.player);
        if (save.scenario) stats.push(save.scenario);
        if (save.players) stats.push(save.players + ' PC' + (save.players > 1 ? 's' : ''));
        if (save.areas) stats.push(save.areas + ' areas');
        var size = fmtSize(save.size);
        if (size) stats.push(size);
        var statLine = stats.join(' · ');
        var isAuto = !!save.autosave;
        var badge = isAuto
            ? saveLoadViewTag`<span class="save-badge save-badge-auto">AUTO</span>`
            : '';
        var versionBadge = save.version
            ? saveLoadViewTag`<span class="save-version-badge">v${save.version}</span>`
            : '';
        var actions = isAuto
            ? saveLoadViewTag`<button class="btn btn-sm" @click=${() => window.SaveLoadView.saveGameToSlot(save.filename, save.name)} style="font-size:10px;padding:2px 6px;" title="Overwrite this slot with current state">💾</button>`
            : saveLoadViewTag`
                <button class="btn btn-sm" @click=${() => window.SaveLoadView.saveGameToSlot(save.filename, save.name)} style="font-size:10px;padding:2px 6px;" title="Overwrite this slot with current state">💾</button>
                <button class="btn btn-sm" @click=${() => window.SaveLoadView.doRenameSave(save.filename, save.name)} style="font-size:10px;padding:2px 6px;" title="Rename save">✏️</button>
                <button class="btn btn-sm btn-red" @click=${() => window.SaveLoadView.doDeleteSave(save)} style="font-size:10px;padding:2px 6px;" title="Delete save">🗑</button>
            `;
        return saveLoadViewTag`<div class="save-game-item ${isAuto ? 'save-game-auto' : ''}">
            <div class="save-game-info" @click=${() => window.SaveLoadView.doLoadGame(save)}>
                <strong>${badge}${save.name || save.filename}</strong>${versionBadge}
                <div class="save-game-stats">${statLine}</div>
            </div>
            <div class="save-game-actions">
                ${actions}
            </div>
        </div>`;
    }

    /**
     * Fetch and render the list of saved games in the load-game modal.
     */
    async function loadGameList() {
        var listEl = document.getElementById('save-game-list');
        if (!listEl) return;
        window.Lit.render(saveLoadViewTag`<div style="color:var(--text-muted);padding:20px;text-align:center;">Loading saves...</div>`, listEl);
        try {
            var saves = await api.listSaveGames();
            if (!saves || saves.length === 0) {
                window.Lit.render(saveLoadViewTag`<div style="color:var(--text-muted);padding:20px;text-align:center;">No saves found.</div>`, listEl);
                return;
            }
            window.Lit.render(saveLoadViewTag`${saves.map(renderSaveRow)}`, listEl);
        } catch (err) {
            window.Lit.render(saveLoadViewTag`<div style="color:var(--text-error);padding:20px;text-align:center;">Error: ${saveloadErrMessage(err)}</div>`, listEl);
        }
    }

    /**
     * Load a saved game by filename or save object with in-modal confirmation (task-455).
     * @param {string|object} filenameOrSave - The save file name or save object to load
     */
    async function doLoadGame(filenameOrSave: any) {
        var filename = typeof filenameOrSave === 'object' ? filenameOrSave.filename : filenameOrSave;
        var displayName = (typeof filenameOrSave === 'object' && filenameOrSave.name) ? filenameOrSave.name : filename;
        var ts = (typeof filenameOrSave === 'object' && filenameOrSave.timestamp) ? filenameOrSave.timestamp.replace('_', ' ') : '';
        var msg = 'Load "' + displayName + '"' + (ts ? ' (' + ts + ')' : '') + '?\n" + "Current progress will be replaced.';

        var dialog = window.VW && window.VW.dialog;
        if (dialog && typeof dialog.confirm === 'function') {
            var ok = await dialog.confirm({
                title: 'Load Game',
                message: msg,
                confirmLabel: 'Load',
                danger: true
            });
            if (!ok) return;
        } else {
            return;
        }

        var result = await api.loadGame(filename);
        if (result && result.status === 'success') {
            if (result.schema_notice) toastInfo(result.schema_notice);
            events.log('📂 Game loaded: ' + filename, 'system-msg');
            events.clearAll();
            agent.reset();
            await refreshReplacedWorld();
            var modal = document.getElementById('load-game-modal');
            if (modal) modal.style.display = 'none';
        } else {
            toastError('Load failed: ' + (result?.error || 'unknown error'));
        }
    }

    /**
     * Delete a saved game with in-modal confirmation (task-455).
     * @param {string|object} filenameOrSave - The save file name or save object to delete
     */
    async function doDeleteSave(filenameOrSave: any) {
        var filename = typeof filenameOrSave === 'object' ? filenameOrSave.filename : filenameOrSave;
        var displayName = (typeof filenameOrSave === 'object' && filenameOrSave.name) ? filenameOrSave.name : filename;
        var ts = (typeof filenameOrSave === 'object' && filenameOrSave.timestamp) ? filenameOrSave.timestamp.replace('_', ' ') : '';
        var msg = 'Delete "' + displayName + '"' + (ts ? ' (' + ts + ')' : '') + '?\n" + "This cannot be undone.';

        var dialog = window.VW && window.VW.dialog;
        if (dialog && typeof dialog.confirm === 'function') {
            var ok = await dialog.confirm({
                title: 'Delete Save',
                message: msg,
                confirmLabel: 'Delete',
                danger: true
            });
            if (!ok) return;
        } else {
            return;
        }

        var result = await api.deleteSaveGame(filename);
        if (result && result.status === 'success') {
            events.log('🗑 Save deleted: ' + filename, 'system-msg');
            loadGameList();
        } else {
            toastError('Delete failed: ' + (result?.error || 'unknown error'));
        }
    }

    /**
     * Delete all user saves, keeping the autosave slot (bug-42, task-455).
     */
    async function confirmDeleteAllSaves() {
        var saves: any[] = [];
        try {
            saves = await api.listSaveGames() || [];
        } catch (err) {
            toastError('Could not list saves: ' + saveloadErrMessage(err));
            return;
        }
        var userSaves = saves.filter(function(s: any) { return !s.autosave; });
        if (userSaves.length === 0) {
            toastInfo('No user saves to delete. Autosave is kept.');
            return;
        }
        var noun = userSaves.length === 1 ? 'save' : 'saves';
        var msg = 'Delete all ' + userSaves.length + ' ' + noun + '? Autosave is kept. This cannot be undone.';
        var dialog = window.VW && window.VW.dialog;
        if (dialog && typeof dialog.confirm === 'function') {
            var ok = await dialog.confirm({
                title: 'Delete All Saves',
                message: msg,
                confirmLabel: 'Delete All',
                danger: true
            });
            if (!ok) return;
        } else {
            return;
        }
        try {
            var result = await api.deleteAllSaveGames(false);
            if (result && result.status === 'success') {
                events.log('🗑 ' + (result.deleted || []).length + ' ' + noun + ' deleted (autosave kept)', 'system-msg');
                loadGameList();
            } else {
                toastError('Delete failed: ' + (result?.error || 'unknown error'));
            }
        } catch (err) {
            toastError('Error deleting saves: ' + saveloadErrMessage(err));
        }
    }

    /**
     * Restart the scenario by calling the reset API endpoint.
     * Clears all agent state, event log, and memory stores.
     */
    async function restartScenario() {
        try {
            agent.cancel();
            var resp = await fetch('/api/reset', { method: 'POST' });
            var data = await resp.json();
            if (data.status === 'success') {
                agent.reset();
                await refreshReplacedWorld();
                events.clearAll();
                events.log('🔄 World reset to initial state.', 'system-msg');
                events._persistLog();
            } else {
                events.log('❌ Reset failed: ' + (data.error || 'unknown'), 'error-msg');
            }
        } catch (err) {
            events.log('❌ Reset failed: ' + saveloadErrMessage(err), 'error-msg');
        }
    }

    /**
     * Delegates for world settings toggles moved to SettingsView (task-456).
     */
    function toggleSpectator() {
        if (window.SettingsView && typeof window.SettingsView.toggleSpectator === 'function') {
            return window.SettingsView.toggleSpectator();
        }
        var checkbox = document.getElementById('spectator-mode') as HTMLInputElement | null;
        if (checkbox?.checked) {
            worldState.startPolling();
        } else {
            worldState.stopPolling();
        }
    }

    function updateTimePerTick(minutes: number) {
        if (window.SettingsView && typeof window.SettingsView.updateTimePerTick === 'function') {
            return window.SettingsView.updateTimePerTick(minutes);
        }
    }

    function updateClockStart(value: string) {
        if (window.SettingsView && typeof window.SettingsView.updateClockStart === 'function') {
            return window.SettingsView.updateClockStart(value);
        }
    }

    return {
        openImportPreview: openImportPreview,
        downloadWorld: downloadWorld,
        uploadWorld: uploadWorld,
        saveScenarioToFile: saveScenarioToFile,
        saveGame: saveGame,
        saveGameToSlot: saveGameToSlot,
        doRenameSave: doRenameSave,
        renderSaveRow: renderSaveRow,
        loadGameList: loadGameList,
        doLoadGame: doLoadGame,
        doDeleteSave: doDeleteSave,
        confirmDeleteAllSaves: confirmDeleteAllSaves,
        restartScenario: restartScenario,
        refreshReplacedWorld: refreshReplacedWorld,
        toggleSpectator: toggleSpectator,
        updateTimePerTick: updateTimePerTick,
        updateClockStart: updateClockStart,
        initScenarioNameEditor: initScenarioNameEditor
    };
})();
