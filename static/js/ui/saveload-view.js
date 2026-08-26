/**
 * saveload-view.js — Save/load game UI module
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
 */

const saveLoadViewTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.SaveLoadView = (() => {
    'use strict';

    /**
     * Download the current world state as a JSON file.
     */
    function downloadWorld() {
        api.saveWorld().then(function(data) {
            var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            WorldExport.saveFileWithDialog(blob, 'world_save.json');
        });
    }

    /**
     * Upload/load a world from a user-selected JSON file.
     * @param {Event} event - The file input change event
     */
    function uploadWorld(event) {
        var file = event.target.files[0];
        if (!file) return;
        var scenarioName = file.name.replace(/\.json$/i, '');
        var reader = new FileReader();
        reader.onload = function(e) {
            try {
                var data = JSON.parse(e.target.result);
                data._scenario_name = scenarioName;
                api.loadWorld(data).then(function(resp) {
                    if (resp && resp.error) {
                        toastError('Load failed: ' + resp.error);
                        events.log('❌ Load failed: ' + resp.error, 'error-msg');
                        return;
                    }
                    document.body.dataset.scenarioName = scenarioName;
                    events.log('World loaded!', 'system-msg');
                    events.clearAll();
                    agent.reset();
                    worldState.fetch();
                }).catch(function(err) {
                    toastError('Network error: ' + err.message);
                    events.log('❌ Load network error: ' + err.message, 'error-msg');
                });
            } catch (err) {
                toastError('Invalid JSON: ' + err.message);
            }
        };
        reader.readAsText(file);
        event.target.value = '';
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
                var handle = await window.showSaveFilePicker({
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
            if (e.name === 'AbortError' || e.name === 'SecurityError') return; // user cancelled
            toastError('Save failed: ' + e.message);
            events.log('Save failed: ' + e.message, 'error-msg');
        }
    }

    /**
     * Save the current game state via the API with an optional name.
     * @param {string} [name] - Optional save name from the input field
     */
    async function saveGame(name) {
        var nameInput = document.getElementById('save-game-name-input');
        var saveName = name || (nameInput ? nameInput.value.trim() : '');
        var result = await api.saveGame(saveName || undefined);
        if (result && result.filename) {
            toastSuccess('Game saved as ' + result.filename);
            if (nameInput) nameInput.value = '';
            events.log('💾 Game saved: ' + result.filename, 'system-msg');
            loadGameList();
        } else {
            toastError('Save failed: ' + (result?.error || 'unknown error'));
        }
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
            window.Lit.render(saveLoadViewTag`${saves.map(function(save) {
                var ts = save.timestamp ? save.timestamp.replace('_', ' ') : '';
                return saveLoadViewTag`<div class="save-game-item" style="display:flex;justify-content:space-between;align-items:center;padding:8px 6px;border-bottom:1px solid var(--border);">
                    <div style="flex:1;cursor:pointer;" @click=${() => window.SaveLoadView.doLoadGame(save.filename)}>
                    <strong>${save.name || save.filename}</strong>
                    <div style="font-size:10px;color:var(--text-muted);">
                    ${ts ? ts + ' · ' : ''}${events.tickToTime(save.tick ?? 0)} · Turn ${save.turn ?? '?'} · ${save.player || ''}
                    </div></div>
                    <button class="btn btn-sm btn-red" @click=${() => window.SaveLoadView.doDeleteSave(save.filename)} style="font-size:10px;padding:2px 6px;" title="Delete save">🗑</button>
                </div>`;
            })}`, listEl);
        } catch (err) {
            window.Lit.render(saveLoadViewTag`<div style="color:var(--text-error);padding:20px;text-align:center;">Error: ${err.message}</div>`, listEl);
        }
    }

    /**
     * Load a saved game by filename.
     * @param {string} filename - The save file name to load
     */
    async function doLoadGame(filename) {
        if (!confirm('Load game "' + filename + '"? Current progress will be replaced.')) return;
        var result = await api.loadGame(filename);
        if (result && result.status === 'success') {
            events.log('📂 Game loaded: ' + filename, 'system-msg');
            events.clearAll();
            agent.reset();
            worldState.fetch();
            var modal = document.getElementById('load-game-modal');
            if (modal) modal.style.display = 'none';
        } else {
            toastError('Load failed: ' + (result?.error || 'unknown error'));
        }
    }

    /**
     * Delete a saved game by filename.
     * @param {string} filename - The save file name to delete
     */
    async function doDeleteSave(filename) {
        if (!confirm('Delete save "' + filename + '"?')) return;
        var result = await api.deleteSaveGame(filename);
        if (result && result.status === 'success') {
            events.log('🗑 Save deleted: ' + filename, 'system-msg');
            loadGameList();
        } else {
            toastError('Delete failed: ' + (result?.error || 'unknown error'));
        }
    }

    /**
     * Delete all saved games after double confirmation.
     */
    async function confirmDeleteAllSaves() {
        if (!confirm('Delete ALL saves? This cannot be undone.')) return;
        if (!confirm('Are you sure?')) return;
        try {
            var saves = await api.listSaveGames();
            for (var i = 0; i < saves.length; i++) {
                await api.deleteSaveGame(saves[i].filename);
            }
            events.log('🗑 All saves deleted', 'system-msg');
            loadGameList();
        } catch (err) {
            toastError('Error deleting saves: ' + err.message);
        }
    }

    /**
     * Restart the scenario by calling the reset API endpoint.
     * Clears all agent state, event log, and memory stores.
     */
    async function restartScenario() {
        try {
            // Abort any in-flight agent step and stop the loop BEFORE wiping
            // state, so a mid-iteration step() can't repopulate the event
            // stream with drugs while we're trying to give a clean slate.
            agent.cancel();
            var resp = await fetch('/api/reset', { method: 'POST' });
            var data = await resp.json();
            if (data.status === 'success') {
                agent.reset();
                await worldState.fetch();
                // Clear AFTER fetch: any straggler bubble the aborted step
                // managed to log while the async fetch was resolving is wiped
                // here too, leaving only the reset banner below.
                events.clearAll();
                events.log('🔄 World reset to initial state.', 'system-msg');
                events._persistLog();
            } else {
                events.log('❌ Reset failed: ' + (data.error || 'unknown'), 'error-msg');
            }
        } catch (err) {
            events.log('❌ Reset failed: ' + err.message, 'error-msg');
        }
    }

    /**
     * Toggle spectator mode on/off.
     * When enabled, the world state is polled every 1.5s for live updates.
     */
    function toggleSpectator() {
        var checkbox = document.getElementById('spectator-mode');
        if (checkbox?.checked) {
            worldState.startPolling();
        } else {
            worldState.stopPolling();
        }
    }

    /**
     * Update the time-per-tick setting on the backend.
     * @param {number} minutes - Game minutes per agent step
     */
    async function updateTimePerTick(minutes) {
        try {
            var resp = await fetch('/api/settings/time_per_tick', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ time_per_tick_minutes: minutes })
            });
            var data = await resp.json();
            if (data.status === 'success') {
                events.log('⏰ Time per tick set to ' + data.time_per_tick_minutes + ' min', 'system-msg');
                worldState.fetch();
            }
        } catch (err) {
            events.log('❌ Failed to update time per tick: ' + err.message, 'error-msg');
        }
    }

    /**
     * Update the scenario clock start time on the backend.
     * @param {string} value - "HH:MM" 24h time string
     */
    async function updateClockStart(value) {
        var m = /^(\d{1,2}):(\d{2})$/.exec(value || '');
        if (!m) {
            events.log('❌ Invalid clock start time: ' + value, 'error-msg');
            return;
        }
        var hour = parseInt(m[1], 10);
        var minute = parseInt(m[2], 10);
        try {
            var resp = await fetch('/api/settings/clock_start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ clock_start_hour: hour, clock_start_minute: minute })
            });
            var data = await resp.json();
            if (data.status === 'success') {
                events.log('⏰ Clock start set to ' + String(data.clock_start_hour).padStart(2, '0') + ':' + String(data.clock_start_minute).padStart(2, '0'), 'system-msg');
                worldState.fetch();
            } else {
                events.log('❌ ' + (data.error || 'Failed to update clock start'), 'error-msg');
            }
        } catch (err) {
            events.log('❌ Failed to update clock start: ' + err.message, 'error-msg');
        }
    }

    return {
        downloadWorld: downloadWorld,
        uploadWorld: uploadWorld,
        saveScenarioToFile: saveScenarioToFile,
        saveGame: saveGame,
        loadGameList: loadGameList,
        doLoadGame: doLoadGame,
        doDeleteSave: doDeleteSave,
        confirmDeleteAllSaves: confirmDeleteAllSaves,
        restartScenario: restartScenario,
        toggleSpectator: toggleSpectator,
        updateTimePerTick: updateTimePerTick,
        updateClockStart: updateClockStart
    };
})();
