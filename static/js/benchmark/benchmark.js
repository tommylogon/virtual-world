/**
 * @module benchmark/benchmark - LLM prompt benchmark controller
 * @contributes window.BenchmarkApp
 * @powers Developer Tooling, Benchmarks
 * @relates routes/benchmark.py, static/js/llm-client.js
 * @docs none
 */

window.BenchmarkApp = (() => {
    'use strict';

    const state = {
        worldData: null,
        characters: [],
        selectedChar: null,
        selectedArea: null,
        models: [],
        selectedModels: new Set(),
        currentPrompt: null,
        activeRun: false,
        abortController: null,
        results: {},
        modelHistory: {},
        activeRollIndex: {},
        pastRuns: [],
        profileMap: {},
        lastLoadedModel: null,
    };

    const els = {};

    async function init() {
        cacheElements();
        attachEvents();
        wireRuntime();
        await loadProfiles();
        if (Object.keys(state.profileMap).length === 0) {
            refreshModels();
        }
        loadPastRuns();
        loadWorldState();
    }

    /**
     * Publish the singletons the prompt builder reads, the same way main.js
     * does for the editor: VW.state is the world-state cache and VW.events is
     * the event bus (memory recall renders relative ticks through it).
     */
    function wireRuntime() {
        window.VW = window.VW || {};
        window.VW.state = window.worldState;
        window.VW.events = window.events;
    }

    function cacheElements() {
        els.providerSelect = document.getElementById('bench-provider');
        els.apiBaseInput = document.getElementById('bench-api-base');
        els.apiKeyInput = document.getElementById('bench-api-key');
        els.refreshModelsBtn = document.getElementById('bench-refresh-models');
        els.modelList = document.getElementById('bench-model-list');
        els.modelSearchInput = document.getElementById('bench-model-search');
        els.sizeSlider = document.getElementById('bench-size-slider');
        els.sizeVal = document.getElementById('bench-size-val');
        els.modelsCount = document.getElementById('bench-models-count');
        els.selectAllModels = document.getElementById('bench-select-all');
        els.unloadCycleCb = document.getElementById('bench-unload-cycle');
        els.characterSelect = document.getElementById('bench-character');
        els.areaSelect = document.getElementById('bench-area');
        els.temperatureInput = document.getElementById('bench-temperature');
        els.maxTokensInput = document.getElementById('bench-max-tokens');
        els.contextLengthInput = document.getElementById('bench-context-length');
        els.reasoningEffortSelect = document.getElementById('bench-reasoning-effort');
        els.runBtn = document.getElementById('bench-run-btn');
        els.cancelBtn = document.getElementById('bench-cancel-btn');
        els.statusBadge = document.getElementById('bench-status-badge');
        els.statusText = document.getElementById('bench-status-text');
        els.cardsGrid = document.getElementById('bench-cards-grid');
        els.promptSystem = document.getElementById('bench-prompt-system');
        els.promptUser = document.getElementById('bench-prompt-user');
        els.promptSummary = document.getElementById('bench-prompt-summary');
        els.historyList = document.getElementById('bench-history-list');
        els.refreshRunsBtn = document.getElementById('bench-refresh-runs');
        els.openDiffBtn = document.getElementById('bench-open-diff');
        els.exportJsonBtn = document.getElementById('bench-export-json');
        els.diffOverlay = document.getElementById('bench-diff-overlay');
        els.diffClose = document.getElementById('bench-diff-close');
        els.diffSelectA = document.getElementById('bench-diff-select-a');
        els.diffSelectB = document.getElementById('bench-diff-select-b');
        els.diffTitleA = document.getElementById('bench-diff-title-a');
        els.diffTitleB = document.getElementById('bench-diff-title-b');
        els.diffBoxA = document.getElementById('bench-diff-box-a');
        els.diffBoxB = document.getElementById('bench-diff-box-b');
    }

    async function loadProfiles() {
        if (!window.config || typeof window.config.getProfiles !== 'function') return;
        try {
            if (window.config._initPromise) await window.config._initPromise;
            state.profileMap = await window.config.getProfiles();
            populateProviders();
        } catch (e) {
            console.error('[Benchmark] Error loading profiles:', e);
        }
    }

    function populateProviders() {
        if (!els.providerSelect) return;
        const profileNames = Object.keys(state.profileMap || {});
        if (profileNames.length === 0) return;

        els.providerSelect.innerHTML = '';
        profileNames.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            els.providerSelect.appendChild(opt);
        });

        const customOpt = document.createElement('option');
        customOpt.value = '__custom__';
        customOpt.textContent = 'Custom (OpenAI-compatible)';
        els.providerSelect.appendChild(customOpt);

        const activeName = window.config?.currentProfile || profileNames[0];
        if (state.profileMap[activeName]) {
            els.providerSelect.value = activeName;
        } else {
            els.providerSelect.value = profileNames[0];
        }
        applySelectedProfile();
    }

    function applySelectedProfile() {
        const val = els.providerSelect.value;
        if (val === '__custom__') {
            return;
        }
        const profile = state.profileMap[val];
        if (profile) {
            if (profile.apiBase) els.apiBaseInput.value = profile.apiBase;
            if (profile.apiKey !== undefined && profile.apiKey !== 'not-needed') {
                els.apiKeyInput.value = profile.apiKey;
            } else if (profile.apiKey === 'not-needed') {
                els.apiKeyInput.value = '';
            }
            refreshModels();
        }
    }

    function attachEvents() {
        els.refreshModelsBtn.addEventListener('click', refreshModels);
        els.providerSelect.addEventListener('change', () => {
            const val = els.providerSelect.value;
            if (state.profileMap[val]) {
                applySelectedProfile();
            } else {
                if (val === 'lmstudio') els.apiBaseInput.value = 'http://localhost:1234/v1';
                else if (val === 'ollama') els.apiBaseInput.value = 'http://localhost:11434/v1';
                else if (val === 'openrouter') els.apiBaseInput.value = 'https://openrouter.ai/api/v1';
                refreshModels();
            }
        });

        els.selectAllModels.addEventListener('change', (e) => {
            const checked = e.target.checked;
            document.querySelectorAll('.bench-model-cb').forEach(cb => {
                cb.checked = checked;
                if (checked) state.selectedModels.add(cb.value);
                else state.selectedModels.delete(cb.value);
            });
        });

        if (els.modelSearchInput) {
            els.modelSearchInput.addEventListener('input', () => {
                renderModelList();
            });
        }

        if (els.sizeSlider) {
            els.sizeSlider.addEventListener('input', () => {
                const val = parseInt(els.sizeSlider.value, 10);
                if (val >= 40) {
                    if (els.sizeVal) els.sizeVal.textContent = 'Any';
                } else {
                    if (els.sizeVal) els.sizeVal.textContent = `≤ ${val}B`;
                }
                renderModelList();
            });
        }

        els.characterSelect.addEventListener('change', () => {
            state.selectedChar = els.characterSelect.value;
            populateAreas();
            assembleCharacterPrompt();
        });

        if (els.areaSelect) {
            els.areaSelect.addEventListener('change', () => {
                state.selectedArea = els.areaSelect.value || null;
                assembleCharacterPrompt();
            });
        }

        els.runBtn.addEventListener('click', startBenchmark);
        els.cancelBtn.addEventListener('click', cancelBenchmark);

        if (els.refreshRunsBtn) els.refreshRunsBtn.addEventListener('click', loadPastRuns);
        if (els.openDiffBtn) els.openDiffBtn.addEventListener('click', openDiffModal);
        if (els.exportJsonBtn) els.exportJsonBtn.addEventListener('click', exportResultsAsJson);
        if (els.diffClose) els.diffClose.addEventListener('click', () => { els.diffOverlay.style.display = 'none'; });
        if (els.diffSelectA) els.diffSelectA.addEventListener('change', updateDiffView);
        if (els.diffSelectB) els.diffSelectB.addEventListener('change', updateDiffView);
    }

    async function loadWorldState() {
        try {
            // The prompt builder reads the app's singletons, so the benchmark
            // page uses the same world-state cache the editor does. Loading it
            // here also keeps `worldState.data` fresh for the ground-truth
            // checks that run against every model output.
            if (window.config && window.config._initPromise) {
                await window.config._initPromise;
            }
            await window.worldState.fetch();
            state.worldData = window.worldState.data;
            if (!state.worldData) throw new Error('The server returned no world state.');
            populateCharacters();
        } catch (e) {
            console.error('[Benchmark] Error loading world state:', e);
            state.worldData = null;
            state.currentPrompt = null;
            if (els.statusText) els.statusText.textContent = `Failed to load world state: ${e.message}`;
            if (els.promptSummary) els.promptSummary.textContent = `World state unavailable: ${e.message}`;
        }
    }

    function populateCharacters() {
        els.characterSelect.innerHTML = '';
        const players = state.worldData?.players || {};
        const names = Object.keys(players);
        state.characters = names;

        if (names.length === 0) {
            els.characterSelect.innerHTML = '<option value="">No characters in world</option>';
            if (els.areaSelect) els.areaSelect.innerHTML = '<option value="">(No areas)</option>';
            return;
        }

        names.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            els.characterSelect.appendChild(opt);
        });

        state.selectedChar = names[0];
        populateAreas();
        assembleCharacterPrompt();
    }

    function populateAreas() {
        if (!els.areaSelect) return;
        els.areaSelect.innerHTML = '';

        const player = state.worldData?.players?.[state.selectedChar];
        const actualArea = player?.current_area || player?.area || 'Unknown';

        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = `(Actual Location: ${actualArea})`;
        els.areaSelect.appendChild(defaultOpt);

        const areaNames = Object.keys(state.worldData?.areas || {}).sort();
        areaNames.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            els.areaSelect.appendChild(opt);
        });

        if (state.selectedArea && areaNames.includes(state.selectedArea)) {
            els.areaSelect.value = state.selectedArea;
        } else {
            els.areaSelect.value = '';
            state.selectedArea = null;
        }
    }

    /**
     * Assemble the prompt the benchmark sends: the SAME system + user messages
     * the simulation would send this character on its next turn, built by the
     * shared PromptBuilder capture (prompt-builder/capture.js), which mirrors
     * agent-engine's think-decide call sequence.
     *
     * Supports area simulation: if an area is selected in bench-area, builds a
     * simulated state where the character is in that area to evaluate targeting.
     */
    async function assembleCharacterPrompt() {
        if (!state.selectedChar || !state.worldData) return;

        const player = state.worldData.players?.[state.selectedChar] || {};
        const actualArea = player.current_area || player.area || 'Unknown';
        const evalArea = state.selectedArea || actualArea;

        if (!window.PromptBuilder || typeof window.PromptBuilder.captureTurnPrompt !== 'function') {
            state.currentPrompt = null;
            const msg = 'Prompt builder is not loaded on this page.';
            if (els.promptSystem) els.promptSystem.textContent = msg;
            if (els.promptUser) els.promptUser.textContent = '';
            if (els.promptSummary) els.promptSummary.textContent = msg;
            if (els.statusText) els.statusText.textContent = msg;
            return;
        }

        try {
            // Build a cloned world state placing the character in evalArea
            const simulatedState = {
                ...state.worldData,
                players: {
                    ...state.worldData.players,
                    [state.selectedChar]: {
                        ...player,
                        current_area: evalArea,
                        area: evalArea,
                    }
                }
            };

            const captured = await window.PromptBuilder.captureTurnPrompt(state.selectedChar, {
                state: simulatedState
            });
            state.currentPrompt = { system: captured.systemPrompt, user: captured.userPrompt, evalArea };

            if (els.promptSystem) els.promptSystem.textContent = captured.systemPrompt;
            if (els.promptUser) els.promptUser.textContent = captured.userPrompt;
            if (els.promptSummary) {
                const simNote = state.selectedArea ? ` [Simulated in ${evalArea}, actual: ${actualArea}]` : '';
                els.promptSummary.textContent = `Character: ${state.selectedChar} | Area: ${evalArea}${simNote} | System: ${captured.systemPrompt.length} chars | User: ${captured.userPrompt.length} chars`;
            }
        } catch (err) {
            console.error('[Benchmark] Prompt capture failed:', err);
            state.currentPrompt = null;
            const msg = `Prompt capture failed: ${err.message}`;
            if (els.promptSystem) els.promptSystem.textContent = msg;
            if (els.promptUser) els.promptUser.textContent = '';
            if (els.promptSummary) els.promptSummary.textContent = msg;
            if (els.statusText) els.statusText.textContent = msg;
        }
    }

    async function refreshModels() {
        els.modelList.innerHTML = '<div style="color:var(--b-dim);padding:8px;">Fetching models...</div>';
        state.models = [];
        state.selectedModels.clear();

        try {
            const resp = await fetch('/api/bench/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_base: els.apiBaseInput.value.trim(),
                    api_key: els.apiKeyInput.value.trim(),
                })
            });

            const data = await resp.json();
            if (!resp.ok || data.error) {
                els.modelList.innerHTML = `<div style="color:var(--b-red);padding:6px;">${data.error || 'Failed to reach provider.'}</div>`;
                return;
            }

            state.models = data.models || [];
            if (state.selectedModels.size === 0 && state.models.length > 0) {
                for (let i = 0; i < Math.min(3, state.models.length); i++) {
                    const m = state.models[i];
                    state.selectedModels.add(m.id || m.name || m);
                }
            }
            renderModelList();
        } catch (e) {
            els.modelList.innerHTML = `<div style="color:var(--b-red);padding:6px;">Network error: ${e.message}</div>`;
        }
    }

    function parseModelSizeB(m) {
        if (!m) return null;
        const pStr = m.params || '';
        if (pStr) {
            if (/M$/i.test(pStr)) {
                const num = parseFloat(pStr);
                return isNaN(num) ? null : num / 1000;
            }
            const moeMatch = pStr.match(/^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)B/i);
            if (moeMatch) {
                return parseFloat(moeMatch[1]) * parseFloat(moeMatch[2]);
            }
            const bMatch = pStr.match(/^(\d+(?:\.\d+)?)B/i);
            if (bMatch) {
                return parseFloat(bMatch[1]);
            }
        }
        const str = `${m.name || ''} ${m.id || ''}`;
        const match = str.match(/[\-_](\d+(?:\.\d+)?)b\b/i) || str.match(/\b(\d+(?:\.\d+)?)b\b/i);
        if (match) {
            return parseFloat(match[1]);
        }
        if (m.size_bytes && m.size_bytes > 0) {
            return (m.size_bytes / (1024 * 1024 * 1024)) * 1.6;
        }
        return null;
    }

    function renderModelList() {
        els.modelList.innerHTML = '';
        if (state.models.length === 0) {
            els.modelList.innerHTML = '<div style="color:var(--b-muted);padding:8px;">No models reported by provider.</div>';
            if (els.modelsCount) els.modelsCount.textContent = '';
            return;
        }

        const searchQuery = (els.modelSearchInput?.value || '').toLowerCase().trim();
        const searchTokens = searchQuery ? searchQuery.split(/\s+/).filter(Boolean) : [];
        const maxSize = els.sizeSlider ? parseInt(els.sizeSlider.value, 10) : 40;

        let visibleCount = 0;

        state.models.forEach((mObj, idx) => {
            const m = typeof mObj === 'string' ? { id: mObj, name: mObj } : mObj;
            const modelId = m.id || m.name;
            const modelName = m.name || modelId;

            // 1. Max size filter
            const sizeB = parseModelSizeB(m);
            if (maxSize < 40 && sizeB !== null && sizeB > maxSize) {
                return;
            }

            // 2. Search query filter
            if (searchTokens.length > 0) {
                const searchHaystack = [
                    modelName,
                    modelId,
                    m.params || '',
                    m.quant || '',
                    m.vision ? 'vision multimodal image' : '',
                    m.reasoning ? 'reasoning think thinking' : '',
                    m.tools ? 'tools tool function' : '',
                    m.loaded ? 'loaded active vram' : '',
                ].join(' ').toLowerCase();

                const matchesAll = searchTokens.every(tok => searchHaystack.includes(tok));
                if (!matchesAll) return;
            }

            visibleCount++;

            const label = document.createElement('label');
            label.className = 'bench-model-item';

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'bench-model-cb';
            cb.value = modelId;
            cb.checked = state.selectedModels.has(modelId);

            cb.addEventListener('change', () => {
                if (cb.checked) state.selectedModels.add(modelId);
                else state.selectedModels.delete(modelId);
            });

            label.appendChild(cb);

            const wrap = document.createElement('div');
            wrap.className = 'bench-model-label-wrap';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'bench-model-name';
            nameSpan.textContent = modelName;
            wrap.appendChild(nameSpan);

            // Capabilities and architecture badges
            if (m.params || m.quant) {
                const qSpan = document.createElement('span');
                qSpan.className = 'bench-tag bench-tag-quant';
                qSpan.textContent = `${m.params || ''} ${m.quant || ''}`.trim();
                wrap.appendChild(qSpan);
            }
            if (m.context_length) {
                const ctxSpan = document.createElement('span');
                ctxSpan.className = 'bench-tag bench-tag-ctx';
                const k = Math.round(m.context_length / 1024);
                ctxSpan.textContent = k >= 1024 ? `${(k / 1024).toFixed(1)}M ctx` : `${k}K ctx`;
                wrap.appendChild(ctxSpan);
            }
            if (m.loaded) {
                const loadSpan = document.createElement('span');
                loadSpan.className = 'bench-tag bench-tag-loaded';
                loadSpan.textContent = '⚡ Loaded';
                loadSpan.title = 'Active in VRAM';
                wrap.appendChild(loadSpan);
            }
            if (m.vision) {
                const vSpan = document.createElement('span');
                vSpan.className = 'bench-tag bench-tag-vision';
                vSpan.textContent = '👁️ Vision';
                vSpan.title = 'Multimodal image support';
                wrap.appendChild(vSpan);
            }
            if (m.reasoning) {
                const rSpan = document.createElement('span');
                rSpan.className = 'bench-tag bench-tag-reasoning';
                rSpan.textContent = '🧠 Reasoning';
                rSpan.title = 'Thinking model';
                wrap.appendChild(rSpan);
            }
            if (m.tools) {
                const tSpan = document.createElement('span');
                tSpan.className = 'bench-tag bench-tag-tools';
                tSpan.textContent = '🛠️ Tools';
                tSpan.title = 'Trained for tool use';
                wrap.appendChild(tSpan);
            }

            label.appendChild(wrap);
            els.modelList.appendChild(label);
        });

        if (els.modelsCount) {
            els.modelsCount.textContent = `Showing ${visibleCount} of ${state.models.length} models`;
        }

        if (visibleCount === 0) {
            els.modelList.innerHTML = '<div style="color:var(--b-dim);padding:8px;font-size:11px;">No models match filter or size slider.</div>';
        }
    }

    async function loadPastRuns() {
        if (!els.historyList) return;
        els.historyList.innerHTML = '<div style="color:var(--b-dim);padding:6px;font-size:11px;">Loading past runs...</div>';
        try {
            const resp = await fetch('/api/bench/runs');
            if (!resp.ok) return;
            const data = await resp.json();
            state.pastRuns = data.runs || [];
            renderPastRuns();
        } catch (e) {
            els.historyList.innerHTML = '<div style="color:var(--b-dim);padding:6px;font-size:11px;">No runs recorded.</div>';
        }
    }

    function renderPastRuns() {
        els.historyList.innerHTML = '';
        if (state.pastRuns.length === 0) {
            els.historyList.innerHTML = '<div style="color:var(--b-muted);padding:6px;font-size:11px;">No saved runs yet.</div>';
            return;
        }

        state.pastRuns.forEach(r => {
            const item = document.createElement('div');
            item.className = 'bench-history-item';
            const dateStr = r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : r.run_id;
            item.innerHTML = `
                <div>
                    <div class="bench-history-name">${escapeHtml(r.character || 'Character')} (${r.model_count || 0} models)</div>
                    <div class="bench-history-meta">${escapeHtml(r.run_id)} · ${dateStr}</div>
                </div>
                <button type="button" class="bench-btn" style="padding:2px 6px;font-size:10px;">Load</button>
            `;
            item.querySelector('button').addEventListener('click', (e) => {
                e.stopPropagation();
                loadSpecificRun(r.run_id);
            });
            els.historyList.appendChild(item);
        });
    }

    async function loadSpecificRun(runId) {
        try {
            const resp = await fetch(`/api/bench/runs/${runId}`);
            if (!resp.ok) return;
            const run = await resp.json();

            state.results = {};
            els.cardsGrid.innerHTML = '';
            els.statusBadge.className = 'bench-status-badge bench-status-done';
            els.statusBadge.textContent = 'Loaded Run';
            els.statusText.textContent = `Viewing run ${run.run_id} (${run.character} - ${run.results?.length || 0} models)`;

            if (run.prompt_meta && els.promptSummary) {
                els.promptSummary.textContent = `Run ${run.run_id} | Character: ${run.character} | Provider: ${run.provider}`;
            }

            (run.results || []).forEach(r => {
                createModelCard(r.model);
                state.results[r.model] = r;
                state.modelHistory = state.modelHistory || {};
                if (Array.isArray(r.history) && r.history.length > 0) {
                    state.modelHistory[r.model] = r.history;
                } else {
                    state.modelHistory[r.model] = [{
                        ...r,
                        roll_number: 1,
                        timestamp: run.timestamp || new Date().toISOString()
                    }];
                }
                state.activeRollIndex = state.activeRollIndex || {};
                state.activeRollIndex[r.model] = state.modelHistory[r.model].length - 1;
                renderCardData(r.model, r);
                updateCardRollsUI(r.model);
            });

            checkEnableDiff();

        } catch (e) {
            console.error('[Benchmark] Failed to load run:', e);
        }
    }

    async function startBenchmark() {
        if (state.selectedModels.size === 0) {
            alert('Please select at least one model to benchmark.');
            return;
        }

        // Re-capture before every run: the world may have moved since the page
        // loaded, and a benchmark of a stale prompt measures the wrong turn.
        await assembleCharacterPrompt();

        if (!state.currentPrompt) {
            els.statusBadge.className = 'bench-status-badge bench-status-idle';
            els.statusBadge.textContent = 'No prompt';
            els.statusText.textContent = 'Could not capture the turn prompt. Check the prompt panel for the error.';
            return;
        }

        state.activeRun = true;
        state.abortController = new AbortController();
        state.results = {};
        state.modelHistory = {};
        state.activeRollIndex = {};

        els.runBtn.disabled = true;
        els.cancelBtn.disabled = false;
        els.statusBadge.className = 'bench-status-badge bench-status-running';
        els.statusBadge.textContent = 'Running';
        els.cardsGrid.innerHTML = '';
        if (els.openDiffBtn) els.openDiffBtn.style.display = 'none';
        if (els.exportJsonBtn) els.exportJsonBtn.style.display = 'none';

        const modelsToRun = Array.from(state.selectedModels);
        modelsToRun.forEach(model => createModelCard(model));

        // 1. Initial cleanup: unload any model currently hanging in VRAM
        if (els.unloadCycleCb && els.unloadCycleCb.checked) {
            els.statusText.textContent = 'Clearing VRAM (unloading active models)...';
            try {
                await fetch('/api/bench/unload-all', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_base: els.apiBaseInput.value.trim(),
                        api_key: els.apiKeyInput.value.trim()
                    })
                });
                await new Promise(r => setTimeout(r, 400));
            } catch (e) {
                console.warn('[Benchmark] Initial unload-all error:', e);
            }
        }

        // 2. Per-model loop: Load -> Generate -> Unload
        for (let i = 0; i < modelsToRun.length; i++) {
            if (!state.activeRun) break;
            const model = modelsToRun[i];
            const prefix = `[${i + 1}/${modelsToRun.length}] `;
            await executeModelLifecycle(model, state.abortController.signal, false, prefix);
        }

        state.activeRun = false;
        els.runBtn.disabled = false;
        els.cancelBtn.disabled = true;
        els.statusBadge.className = 'bench-status-badge bench-status-done';
        els.statusBadge.textContent = 'Complete';
        els.statusText.textContent = `Completed ${modelsToRun.length} model evaluations.`;

        modelsToRun.forEach(m => updateCardRollsUI(m));

        checkEnableDiff();
        saveRunRecord(modelsToRun);
    }

    async function cancelBenchmark() {
        if (!state.activeRun) return;
        state.activeRun = false;
        if (state.abortController) {
            state.abortController.abort();
        }
        els.runBtn.disabled = false;
        els.cancelBtn.disabled = true;
        els.statusBadge.className = 'bench-status-badge bench-status-idle';
        els.statusBadge.textContent = 'Cancelled';
        els.statusText.textContent = 'Benchmark sweep was cancelled by user. Releasing VRAM...';
        try {
            await fetch('/api/bench/unload-all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_base: els.apiBaseInput.value.trim(),
                    api_key: els.apiKeyInput.value.trim()
                })
            });
            state.lastLoadedModel = null;
        } catch (e) {}
        els.statusText.textContent = 'Benchmark sweep was cancelled by user. VRAM released.';
        Object.keys(state.results).forEach(m => updateCardRollsUI(m));
        checkEnableDiff();
    }

    function createModelCard(model) {
        const id = sanitizeId(model);
        const card = document.createElement('div');
        card.className = 'bench-card';
        card.id = `bench-card-${id}`;

        card.innerHTML = `
            <div class="bench-card-header">
                <div class="bench-card-header-top">
                    <div class="bench-card-model" title="${escapeHtml(model)}">${escapeHtml(model)}</div>
                    <div class="bench-card-actions">
                        <div class="bench-card-rolls" id="rolls-${id}"></div>
                        <button class="bench-reroll-btn" id="btn-reroll-${id}" title="Reroll this model with current prompt" disabled>
                            <span>&#x1F504;</span> Reroll
                        </button>
                    </div>
                </div>
                <div class="bench-card-metrics">
                    <div class="bench-metric">
                        <span class="bench-metric-val" id="metric-ttft-${id}">-</span>
                        <span class="bench-metric-lbl">TTFT</span>
                    </div>
                    <div class="bench-metric">
                        <span class="bench-metric-val" id="metric-tps-${id}">-</span>
                        <span class="bench-metric-lbl">TPS</span>
                    </div>
                    <div class="bench-metric" title="Completion tokens (reasoning / content)">
                        <span class="bench-metric-val" id="metric-tokens-${id}">-</span>
                        <span class="bench-metric-lbl">Tokens</span>
                    </div>
                    <div class="bench-metric">
                        <span class="bench-metric-val" id="metric-total-${id}">-</span>
                        <span class="bench-metric-lbl">Total</span>
                    </div>
                </div>
            </div>
            <div class="bench-card-body">
                <div>
                    <div class="bench-section-label">Inner Monologue &amp; Prose</div>
                    <div class="bench-prose-box" id="prose-${id}">Waiting to execute...</div>
                </div>
                <div>
                    <div class="bench-section-label">Intended Actions</div>
                    <div class="bench-action-strip" id="action-${id}">
                        <span style="color:var(--b-dim);font-size:11px;">-</span>
                    </div>
                </div>
                <div>
                    <div class="bench-section-label">Validation &amp; Ground Truth</div>
                    <div class="bench-flag-list" id="flags-${id}">
                        <span style="color:var(--b-dim);font-size:11px;">Pending...</span>
                    </div>
                </div>
                <details class="bench-raw-toggle">
                    <summary>View Raw Response</summary>
                    <div class="bench-raw-output" id="raw-${id}"></div>
                </details>
            </div>
        `;

        const rerollBtn = card.querySelector(`#btn-reroll-${id}`);
        if (rerollBtn) {
            rerollBtn.addEventListener('click', () => rerollSingleModel(model));
        }

        els.cardsGrid.appendChild(card);
    }

    function renderCardData(model, r) {
        if (!r) return;
        const id = sanitizeId(model);
        const proseEl = document.getElementById(`prose-${id}`);
        const actionEl = document.getElementById(`action-${id}`);
        const flagsEl = document.getElementById(`flags-${id}`);
        const ttftEl = document.getElementById(`metric-ttft-${id}`);
        const tpsEl = document.getElementById(`metric-tps-${id}`);
        const tokensEl = document.getElementById(`metric-tokens-${id}`);
        const totalEl = document.getElementById(`metric-total-${id}`);
        const rawEl = document.getElementById(`raw-${id}`);

        if (ttftEl) ttftEl.textContent = (r.metrics?.ttft != null) ? `${r.metrics.ttft.toFixed(2)}s` : '-';
        if (tpsEl) tpsEl.textContent = (r.metrics?.tps != null) ? `${r.metrics.tps}/s` : '-';
        if (tokensEl) {
            tokensEl.textContent = (r.metrics?.tokens != null) ? `${r.metrics.tokens}` : '-';
            if (r.metrics?.reasoning_tokens != null) {
                tokensEl.title = `${r.metrics.reasoning_tokens} reasoning / ${r.metrics.content_tokens || 0} content tokens`;
            } else {
                tokensEl.title = 'Completion tokens (reasoning / content)';
            }
        }
        if (totalEl) totalEl.textContent = (r.metrics?.total != null) ? `${r.metrics.total.toFixed(2)}s` : '-';
        if (proseEl) proseEl.textContent = r.prose || 'No prose';
        if (rawEl) {
            const rawContent = r.output || '';
            const rawReasoning = r.reasoning || '';
            if (rawReasoning && !rawContent.includes('<think>')) {
                rawEl.textContent = `<think>\n${rawReasoning}\n</think>\n\n${rawContent}`;
            } else {
                rawEl.textContent = rawContent;
            }
        }

        if (actionEl) {
            if (r.actions_summary && r.actions_summary.length > 0) {
                actionEl.innerHTML = r.actions_summary.map(a => `
                    <div class="bench-action-chip">
                        <span class="bench-action-chip-verb">${escapeHtml(a.verb)}</span>
                        ${a.target ? `<span class="bench-action-chip-target">${escapeHtml(a.target)}</span>` : ''}
                    </div>
                `).join('');
            } else {
                actionEl.innerHTML = '<span style="color:var(--b-dim);font-size:11px;">-</span>';
            }
        }

        if (flagsEl) {
            if (r.flags && r.flags.length > 0) {
                flagsEl.innerHTML = r.flags.map(f => `
                    <span class="bench-flag-item ${f.pass ? 'bench-flag-pass' : 'bench-flag-fail'}">
                        ${f.pass ? '✅' : '❌'} ${escapeHtml(f.text || f)}
                    </span>
                `).join('');
            } else {
                flagsEl.innerHTML = '<span style="color:var(--b-dim);font-size:11px;">Pending...</span>';
            }
        }
    }

    function archiveCurrentRoll(model) {
        state.modelHistory = state.modelHistory || {};
        if (!state.modelHistory[model]) {
            state.modelHistory[model] = [];
        }
        const currentResult = state.results[model];
        if (!currentResult) return;
        const rollNum = state.modelHistory[model].length + 1;
        const entry = {
            ...currentResult,
            roll_number: rollNum,
            timestamp: new Date().toISOString()
        };
        state.modelHistory[model].push(entry);
        state.activeRollIndex = state.activeRollIndex || {};
        state.activeRollIndex[model] = state.modelHistory[model].length - 1;
        updateCardRollsUI(model);
    }

    function displayModelRoll(model, rollIndex) {
        const history = state.modelHistory?.[model];
        if (!history || !history[rollIndex]) return;
        state.activeRollIndex = state.activeRollIndex || {};
        state.activeRollIndex[model] = rollIndex;
        const rollData = history[rollIndex];
        state.results[model] = rollData;
        renderCardData(model, rollData);
        updateCardRollsUI(model);
    }

    function updateCardRollsUI(model) {
        const id = sanitizeId(model);
        const rollsEl = document.getElementById(`rolls-${id}`);
        const rerollBtn = document.getElementById(`btn-reroll-${id}`);
        if (rerollBtn && !state.activeRun) {
            rerollBtn.disabled = false;
            rerollBtn.innerHTML = '<span>&#x1F504;</span> Reroll';
        }
        if (!rollsEl) return;
        const history = state.modelHistory?.[model] || [];
        if (history.length <= 1) {
            rollsEl.innerHTML = '';
            return;
        }
        const activeIdx = state.activeRollIndex?.[model] ?? (history.length - 1);
        rollsEl.innerHTML = history.map((_, idx) => `
            <button class="bench-roll-tab ${idx === activeIdx ? 'active' : ''}" data-model="${escapeHtml(model)}" data-roll="${idx}">
                #${idx + 1}
            </button>
        `).join('');

        rollsEl.querySelectorAll('.bench-roll-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.stopPropagation();
                const rollIdx = parseInt(tab.getAttribute('data-roll'), 10);
                displayModelRoll(model, rollIdx);
            });
        });
    }

    async function rerollSingleModel(model) {
        if (state.activeRun) {
            alert('A benchmark run is currently in progress. Please wait for it to finish or cancel it before rerolling.');
            return;
        }
        if (!state.currentPrompt) {
            alert('No current prompt captured. Please check the prompt panel.');
            return;
        }
        const id = sanitizeId(model);
        const rerollBtn = document.getElementById(`btn-reroll-${id}`);
        if (rerollBtn) {
            rerollBtn.disabled = true;
            rerollBtn.innerHTML = '<span>&#x23F3;</span> Rolling...';
        }
        const proseEl = document.getElementById(`prose-${id}`);
        if (proseEl) proseEl.textContent = 'Rerolling with current prompt...';

        const abortCtrl = new AbortController();
        try {
            await executeModelLifecycle(model, abortCtrl.signal, true, 'Reroll: ');
            if (els.statusText) {
                els.statusText.textContent = `Completed reroll for ${model}.`;
            }
        } catch (err) {
            console.error('[Benchmark] Reroll error:', err);
            if (els.statusText) {
                els.statusText.textContent = `Reroll failed for ${model}: ${err.message}`;
            }
        } finally {
            if (rerollBtn) {
                rerollBtn.disabled = false;
                rerollBtn.innerHTML = '<span>&#x1F504;</span> Reroll';
            }
            checkEnableDiff();
        }
    }

    async function executeModelLifecycle(model, signal, isReroll, statusPrefix = '') {
        let modelInstanceId = model;
        if (els.unloadCycleCb && els.unloadCycleCb.checked) {
            if (isReroll) {
                try {
                    await fetch('/api/bench/unload-all', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            api_base: els.apiBaseInput.value.trim(),
                            api_key: els.apiKeyInput.value.trim()
                        })
                    });
                    await new Promise(r => setTimeout(r, 300));
                } catch (e) {
                    console.warn('[Benchmark] Reroll unload-all error:', e);
                }
            }
            if (els.statusText) {
                els.statusText.textContent = `${statusPrefix}Loading ${model}...`;
            }
            try {
                const loadBody = {
                    api_base: els.apiBaseInput.value.trim(),
                    api_key: els.apiKeyInput.value.trim(),
                    model: model
                };
                const ctxVal = parseInt(els.contextLengthInput?.value, 10);
                if (ctxVal && !isNaN(ctxVal) && ctxVal > 0) {
                    loadBody.context_length = ctxVal;
                }
                const loadResp = await fetch('/api/bench/load', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(loadBody)
                });
                const loadData = await loadResp.json().catch(() => ({}));
                if (loadData.instance_id) {
                    modelInstanceId = loadData.instance_id;
                }
                state.lastLoadedModel = modelInstanceId;
                await new Promise(r => setTimeout(r, 400));
            } catch (e) {
                console.warn('[Benchmark] Load error:', e);
            }
        }

        if (els.statusText) {
            els.statusText.textContent = `${statusPrefix}Running ${model}...`;
        }
        try {
            await runSingleModel(model, signal);
        } catch (runErr) {
            console.error('[Benchmark] Run single model error:', runErr);
        }

        if (els.unloadCycleCb && els.unloadCycleCb.checked) {
            if (els.statusText) {
                els.statusText.textContent = `${statusPrefix}Unloading ${model}...`;
            }
            try {
                await fetch('/api/bench/unload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_base: els.apiBaseInput.value.trim(),
                        api_key: els.apiKeyInput.value.trim(),
                        instance_id: modelInstanceId
                    })
                });
                state.lastLoadedModel = null;
                await new Promise(r => setTimeout(r, 400));
            } catch (e) {
                console.warn('[Benchmark] Unload error:', e);
            }
        }
    }

    async function runSingleModel(model, signal) {
        const id = sanitizeId(model);
        const proseEl = document.getElementById(`prose-${id}`);
        const rawEl = document.getElementById(`raw-${id}`);
        const ttftEl = document.getElementById(`metric-ttft-${id}`);
        const tpsEl = document.getElementById(`metric-tps-${id}`);
        const tokensEl = document.getElementById(`metric-tokens-${id}`);
        const totalEl = document.getElementById(`metric-total-${id}`);
        const flagsEl = document.getElementById(`flags-${id}`);

        if (proseEl) proseEl.textContent = 'Streaming...';

        const startTime = performance.now();
        let firstTokenTime = null;
        let tokenCount = 0;
        let contentText = '';
        let reasoningText = '';
        let serverUsage = null;

        try {
            const resp = await fetch('/api/bench/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal,
                body: JSON.stringify({
                    api_base: els.apiBaseInput.value.trim(),
                    api_key: els.apiKeyInput.value.trim(),
                    model: model,
                    temperature: parseFloat(els.temperatureInput.value) || 0.7,
                    max_tokens: parseInt(els.maxTokensInput.value, 10) || 1512,
                    reasoning_effort: els.reasoningEffortSelect?.value || 'default',
                    messages: [
                        { role: 'system', content: state.currentPrompt.system },
                        { role: 'user', content: state.currentPrompt.user },
                    ],
                    stream: true,
                })
            });

            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                throw new Error(errData.error || `HTTP ${resp.status}`);
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed || !trimmed.startsWith('data:')) continue;
                    const jsonStr = trimmed.replace(/^data:\s*/, '');
                    if (jsonStr === '[DONE]') continue;

                    try {
                        const parsedChunk = JSON.parse(jsonStr);
                        if (parsedChunk.usage) {
                            serverUsage = parsedChunk.usage;
                        }
                        const delta = parsedChunk.choices?.[0]?.delta?.content || '';
                        const reasoningDelta = parsedChunk.choices?.[0]?.delta?.reasoning_content || parsedChunk.choices?.[0]?.delta?.thought || '';
                        const chunkText = delta || reasoningDelta;
                        if (chunkText) {
                            if (firstTokenTime === null) {
                                firstTokenTime = performance.now();
                                if (ttftEl) ttftEl.textContent = `${((firstTokenTime - startTime) / 1000).toFixed(2)}s`;
                            }
                            tokenCount++;
                            if (delta) contentText += delta;
                            if (reasoningDelta) reasoningText += reasoningDelta;

                            if (rawEl) {
                                rawEl.textContent = (reasoningText ? `<think>\n${reasoningText}\n</think>\n\n` : '') + contentText;
                            }
                            if (proseEl) {
                                if (contentText) {
                                    proseEl.textContent = contentText;
                                } else if (reasoningText) {
                                    proseEl.textContent = `[Thinking...]\n${reasoningText.slice(-300)}`;
                                }
                            }
                            if (tokensEl) {
                                tokensEl.textContent = `${tokenCount}`;
                            }
                        }
                    } catch (parseErr) {}
                }
            }

            const endTime = performance.now();
            const totalSec = (endTime - startTime) / 1000;
            if (totalEl) totalEl.textContent = `${totalSec.toFixed(2)}s`;

            let totalTokens = tokenCount;
            let rTokens = 0;
            let cTokens = 0;

            if (serverUsage) {
                totalTokens = serverUsage.completion_tokens ?? tokenCount;
                rTokens = serverUsage.completion_tokens_details?.reasoning_tokens ?? 0;
                cTokens = totalTokens - rTokens;
            } else {
                const rLen = reasoningText.length;
                const cLen = contentText.length;
                if (rLen + cLen > 0) {
                    rTokens = Math.round(tokenCount * (rLen / (rLen + cLen)));
                    cTokens = tokenCount - rTokens;
                } else {
                    cTokens = tokenCount;
                }
            }

            const tps = totalTokens > 0 && totalSec > 0 ? (totalTokens / totalSec).toFixed(1) : '0';
            if (tpsEl) tpsEl.textContent = `${tps}/s`;

            if (tokensEl) {
                tokensEl.textContent = `${totalTokens}`;
                if (rTokens > 0) {
                    tokensEl.title = `${rTokens} reasoning / ${cTokens} content tokens`;
                } else {
                    tokensEl.title = `${totalTokens} content tokens`;
                }
            }

            const outputToEval = contentText.trim() || reasoningText.trim();
            await evaluateModelOutput(model, outputToEval, {
                ttft: firstTokenTime ? (firstTokenTime - startTime) / 1000 : null,
                total: totalSec,
                tps: parseFloat(tps),
                tokens: totalTokens,
                reasoning_tokens: rTokens,
                content_tokens: cTokens
            }, reasoningText.trim());

        } catch (err) {
            if (err.name === 'AbortError') {
                if (proseEl) proseEl.textContent = 'Cancelled.';
            } else {
                if (proseEl) proseEl.textContent = `Error: ${err.message}`;
                if (flagsEl) flagsEl.innerHTML = `<span class="bench-flag-item bench-flag-fail">❌ Failed: ${escapeHtml(err.message)}</span>`;
            }
        }
    }

    async function evaluateModelOutput(model, text, metrics, reasoning = '') {
        const id = sanitizeId(model);
        const proseEl = document.getElementById(`prose-${id}`);
        const actionEl = document.getElementById(`action-${id}`);
        const flagsEl = document.getElementById(`flags-${id}`);

        let jsonValid = false;
        let parsed = null;

        const cleaned = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```\s*$/, '').trim();
        try {
            parsed = JSON.parse(cleaned);
            jsonValid = true;
        } catch (e) {
            const match = text.match(/\{[\s\S]*\}/);
            if (match) {
                try {
                    parsed = JSON.parse(match[0]);
                    jsonValid = true;
                } catch (e2) {}
            }
        }

        const flags = [];

        if (!jsonValid || !parsed) {
            if (proseEl) {
                if (reasoning && (!text || text === reasoning)) {
                    proseEl.textContent = `[Thinking - exhausted token budget before JSON response]\n\n${reasoning}`;
                } else {
                    proseEl.textContent = text || (reasoning ? `[Thinking]: ${reasoning}` : 'Empty response.');
                }
            }
            const failMsg = (reasoning && (!text || text === reasoning))
                ? 'Hit token limit while reasoning (increase Max Tokens)'
                : 'Invalid JSON response';
            let failProse = '';
            if (proseEl) failProse = proseEl.textContent || '';
            if (flagsEl) flagsEl.innerHTML = `<span class="bench-flag-item bench-flag-fail">❌ ${failMsg}</span>`;
            state.results[model] = { json_valid: false, metrics, flags: [{ pass: false, text: failMsg }], output: text, reasoning: reasoning || '', prose: failProse };
            archiveCurrentRoll(model);
            return;
        }

        const monologue = parsed.inner_monologue || parsed.monologue || parsed.thought || '';
        const speech = parsed.speech ? `\n"${parsed.speech}"` : '';
        const emote = parsed.emote ? ` (${parsed.emote})` : '';
        const prose = `${monologue}${speech}${emote}`.trim() || 'No monologue or dialogue provided.';
        if (proseEl) proseEl.textContent = prose;

        flags.push({ pass: true, text: 'Valid JSON output' });

        // Collect all actions (supports single action or multi-action array)
        const actionsList = [];
        if (Array.isArray(parsed.actions)) {
            parsed.actions.forEach(a => {
                actionsList.push({ action: a.action || a.verb || 'wait', target: a.target || a.item || '', item: a.item });
            });
        } else if (parsed.action) {
            actionsList.push({ action: parsed.action, target: parsed.target || parsed.item || '', item: parsed.item });
        }

        if (actionsList.length === 0) {
            actionsList.push({ action: 'wait', target: '' });
        }

        if (actionEl) {
            actionEl.innerHTML = actionsList.map(a => `
                <div class="bench-action-chip">
                    <span class="bench-action-chip-verb">${escapeHtml(a.action)}</span>
                    ${a.target ? `<span class="bench-action-chip-target">${escapeHtml(a.target)}</span>` : ''}
                </div>
            `).join('');
        }

        // Ground-truth validation using real engine validator (POST /api/action/validate)
        for (const a of actionsList) {
            let cmdStr = '';
            if (window.ActionNormalizer && typeof window.ActionNormalizer.normalizeStructuredAction === 'function') {
                cmdStr = window.ActionNormalizer.normalizeStructuredAction(a);
            } else {
                const v = String(a.action || 'wait').trim();
                const t = String(a.target || a.item || '').trim();
                cmdStr = t ? `${v} ${t}` : v;
            }

            try {
                const valResp = await fetch('/api/action/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: cmdStr,
                        character: state.selectedChar,
                        area: state.selectedArea,
                    })
                });
                if (valResp.ok) {
                    const valData = await valResp.json();
                    if (valData.valid) {
                        flags.push({ pass: true, text: valData.detail || `Action '${cmdStr}' verified by engine` });
                    } else {
                        flags.push({ pass: false, text: valData.detail || `Action '${cmdStr}' rejected: ${valData.category || 'invalid'}` });
                    }
                } else {
                    flags.push({ pass: false, text: `Engine validation error for '${cmdStr}'` });
                }
            } catch (vErr) {
                flags.push({ pass: false, text: `Could not reach engine validator for '${cmdStr}'` });
            }
        }

        if (flagsEl) {
            flagsEl.innerHTML = flags.map(f => `
                <span class="bench-flag-item ${f.pass ? 'bench-flag-pass' : 'bench-flag-fail'}">
                    ${f.pass ? '✅' : '❌'} ${escapeHtml(f.text)}
                </span>
            `).join('');
        }

        state.results[model] = {
            json_valid: true,
            metrics,
            parsed,
            flags,
            prose,
            actions_summary: actionsList.map(a => ({ verb: a.action, target: a.target, item: a.item })),
            output: text,
            reasoning: reasoning || '',
        };
        archiveCurrentRoll(model);
    }

    function checkEnableDiff() {
        const completedModels = Object.keys(state.results);
        if (completedModels.length >= 1 && els.exportJsonBtn) {
            els.exportJsonBtn.style.display = 'inline-flex';
        }
        if (completedModels.length >= 2 && els.openDiffBtn) {
            els.openDiffBtn.style.display = 'inline-flex';
        }
    }

    function exportResultsAsJson() {
        const completedModels = Object.keys(state.results);
        if (completedModels.length === 0) {
            alert('No benchmark results to export.');
            return;
        }

        const exportData = {
            benchmark_version: '1.0',
            exported_at: new Date().toISOString(),
            character: state.selectedChar || 'unknown',
            simulated_area: state.selectedArea || '(Actual Location)',
            prompt: {
                summary: els.promptSummary?.textContent?.trim() || '',
                system: state.currentPrompt?.system || '',
                user: state.currentPrompt?.user || ''
            },
            config: {
                provider: els.providerSelect?.value || 'custom',
                api_base: els.apiBaseInput?.value?.trim() || '',
                temperature: parseFloat(els.temperatureInput?.value) || 0.7,
                max_tokens: parseInt(els.maxTokensInput?.value, 10) || 1512,
                reasoning_effort: els.reasoningEffortSelect?.value || 'default',
                context_length: parseInt(els.contextLengthInput?.value, 10) || null
            },
            summary: {
                model_count: completedModels.length,
                models_evaluated: completedModels
            },
            results: completedModels.map(model => {
                const r = state.results[model] || {};
                const history = state.modelHistory?.[model] || [];
                return {
                    model: model,
                    rolls_count: history.length || 1,
                    active_roll_index: state.activeRollIndex?.[model] ?? (history.length ? history.length - 1 : 0),
                    history: history.length > 0 ? history.map(h => ({
                        roll_number: h.roll_number,
                        timestamp: h.timestamp,
                        metrics: {
                            ttft_seconds: h.metrics?.ttft ?? null,
                            total_seconds: h.metrics?.total ?? null,
                            tokens_per_second: h.metrics?.tps ?? null,
                            total_tokens: h.metrics?.tokens ?? null,
                            reasoning_tokens: h.metrics?.reasoning_tokens ?? 0,
                            content_tokens: h.metrics?.content_tokens ?? (h.metrics?.tokens ?? null)
                        },
                        json_valid: h.json_valid ?? false,
                        parsed_response: h.parsed ?? null,
                        actions: h.actions_summary || [],
                        validation_flags: h.flags || [],
                        inner_monologue_prose: h.prose || '',
                        reasoning_trace: h.reasoning || '',
                        raw_output: h.output || ''
                    })) : [{
                        roll_number: 1,
                        timestamp: new Date().toISOString(),
                        metrics: {
                            ttft_seconds: r.metrics?.ttft ?? null,
                            total_seconds: r.metrics?.total ?? null,
                            tokens_per_second: r.metrics?.tps ?? null,
                            total_tokens: r.metrics?.tokens ?? null,
                            reasoning_tokens: r.metrics?.reasoning_tokens ?? 0,
                            content_tokens: r.metrics?.content_tokens ?? (r.metrics?.tokens ?? null)
                        },
                        json_valid: r.json_valid ?? false,
                        parsed_response: r.parsed ?? null,
                        actions: r.actions_summary || [],
                        validation_flags: r.flags || [],
                        inner_monologue_prose: r.prose || '',
                        reasoning_trace: r.reasoning || '',
                        raw_output: r.output || ''
                    }],
                    metrics: {
                        ttft_seconds: r.metrics?.ttft ?? null,
                        total_seconds: r.metrics?.total ?? null,
                        tokens_per_second: r.metrics?.tps ?? null,
                        total_tokens: r.metrics?.tokens ?? null,
                        reasoning_tokens: r.metrics?.reasoning_tokens ?? 0,
                        content_tokens: r.metrics?.content_tokens ?? (r.metrics?.tokens ?? null)
                    },
                    json_valid: r.json_valid ?? false,
                    parsed_response: r.parsed ?? null,
                    actions: r.actions_summary || [],
                    validation_flags: r.flags || [],
                    inner_monologue_prose: r.prose || '',
                    reasoning_trace: r.reasoning || '',
                    raw_output: r.output || ''
                };
            })
        };

        const jsonString = JSON.stringify(exportData, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const safeChar = (state.selectedChar || 'bench').replace(/[^a-z0-9_-]/gi, '_');
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const fileName = `benchmark_${safeChar}_${timestamp}.json`;

        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);

        if (els.statusText) {
            els.statusText.textContent = `Exported ${completedModels.length} model results as ${fileName}`;
        }
    }

    function openDiffModal() {
        const completedModels = Object.keys(state.results);
        if (completedModels.length < 2) return;

        els.diffSelectA.innerHTML = '';
        els.diffSelectB.innerHTML = '';

        completedModels.forEach((m, idx) => {
            const optA = document.createElement('option');
            optA.value = m; optA.textContent = m;
            if (idx === 0) optA.selected = true;
            els.diffSelectA.appendChild(optA);

            const optB = document.createElement('option');
            optB.value = m; optB.textContent = m;
            if (idx === 1) optB.selected = true;
            els.diffSelectB.appendChild(optB);
        });

        updateDiffView();
        els.diffOverlay.style.display = 'flex';
    }

    function updateDiffView() {
        const modelA = els.diffSelectA.value;
        const modelB = els.diffSelectB.value;
        els.diffTitleA.textContent = modelA;
        els.diffTitleB.textContent = modelB;

        const proseA = state.results[modelA]?.prose || '';
        const proseB = state.results[modelB]?.prose || '';

        els.diffBoxA.innerHTML = renderInlineDiff(proseB, proseA);
        els.diffBoxB.innerHTML = renderInlineDiff(proseA, proseB);
    }

    function renderInlineDiff(reference, current) {
        const refWords = new Set(reference.toLowerCase().split(/\s+/).filter(Boolean));
        const words = current.split(/(\s+)/);
        return words.map(w => {
            if (/^\s+$/.test(w)) return w;
            const clean = w.toLowerCase().replace(/[^a-z0-9]/g, '');
            if (clean && !refWords.has(clean)) {
                return `<span class="bench-diff-ins">${escapeHtml(w)}</span>`;
            }
            return escapeHtml(w);
        }).join('');
    }

    function fuzzyMatch(truth, candidate) {
        if (!truth || !candidate) return false;
        const a = String(truth).toLowerCase().trim();
        const b = String(candidate).toLowerCase().trim();
        return a === b || a.includes(b) || b.includes(a);
    }

    async function saveRunRecord(models) {
        try {
            await fetch('/api/bench/runs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: els.providerSelect.value,
                    api_base: els.apiBaseInput.value,
                    character: state.selectedChar,
                    scenario: state.worldData?.meta?.name || 'unknown',
                    prompt_meta: {
                        system_chars: state.currentPrompt?.system?.length || 0,
                        user_chars: state.currentPrompt?.user?.length || 0,
                    },
                    results: Object.entries(state.results).map(([model, data]) => ({
                        model,
                        ...data
                    }))
                })
            });
            loadPastRuns();
        } catch (e) {
            console.warn('[Benchmark] Could not persist run to server:', e);
        }
    }

    function sanitizeId(str) {
        return String(str).replace(/[^a-zA-Z0-9_-]/g, '_');
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    return {
        init,
        _state: state,
        displayModelRoll,
        rerollSingleModel,
        archiveCurrentRoll,
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    window.BenchmarkApp.init();
});
