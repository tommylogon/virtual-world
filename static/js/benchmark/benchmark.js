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
        models: [],
        selectedModels: new Set(),
        currentPrompt: null,
        activeRun: false,
        abortController: null,
        results: {},
        pastRuns: [],
    };

    const els = {};

    function init() {
        cacheElements();
        attachEvents();
        wireRuntime();
        refreshModels();
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
        els.selectAllModels = document.getElementById('bench-select-all');
        els.characterSelect = document.getElementById('bench-character');
        els.temperatureInput = document.getElementById('bench-temperature');
        els.maxTokensInput = document.getElementById('bench-max-tokens');
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
        els.diffOverlay = document.getElementById('bench-diff-overlay');
        els.diffClose = document.getElementById('bench-diff-close');
        els.diffSelectA = document.getElementById('bench-diff-select-a');
        els.diffSelectB = document.getElementById('bench-diff-select-b');
        els.diffTitleA = document.getElementById('bench-diff-title-a');
        els.diffTitleB = document.getElementById('bench-diff-title-b');
        els.diffBoxA = document.getElementById('bench-diff-box-a');
        els.diffBoxB = document.getElementById('bench-diff-box-b');
    }

    function attachEvents() {
        els.refreshModelsBtn.addEventListener('click', refreshModels);
        els.providerSelect.addEventListener('change', () => {
            const val = els.providerSelect.value;
            if (val === 'lmstudio') els.apiBaseInput.value = 'http://localhost:1234/v1';
            else if (val === 'ollama') els.apiBaseInput.value = 'http://localhost:11434/v1';
            else if (val === 'openrouter') els.apiBaseInput.value = 'https://openrouter.ai/api/v1';
            refreshModels();
        });

        els.selectAllModels.addEventListener('change', (e) => {
            const checked = e.target.checked;
            document.querySelectorAll('.bench-model-cb').forEach(cb => {
                cb.checked = checked;
                if (checked) state.selectedModels.add(cb.value);
                else state.selectedModels.delete(cb.value);
            });
        });

        els.characterSelect.addEventListener('change', () => {
            state.selectedChar = els.characterSelect.value;
            assembleCharacterPrompt();
        });
        els.runBtn.addEventListener('click', startBenchmark);
        els.cancelBtn.addEventListener('click', cancelBenchmark);

        if (els.refreshRunsBtn) els.refreshRunsBtn.addEventListener('click', loadPastRuns);
        if (els.openDiffBtn) els.openDiffBtn.addEventListener('click', openDiffModal);
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
            return;
        }

        names.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            els.characterSelect.appendChild(opt);
        });

        state.selectedChar = names[0];
        assembleCharacterPrompt();
    }

    /**
     * Assemble the prompt the benchmark sends: the SAME system + user messages
     * the simulation would send this character on its next turn, built by the
     * shared PromptBuilder capture (prompt-builder/capture.js), which mirrors
     * agent-engine's think-decide call sequence.
     *
     * There is deliberately no hand-written fallback. A stub prompt measures the
     * stub, and the silent fallback is exactly how this page shipped a
     * two-line prompt for months while the real one sat in the code.
     */
    async function assembleCharacterPrompt() {
        if (!state.selectedChar || !state.worldData) return;

        const roomName = state.worldData.players?.[state.selectedChar]?.current_area || 'Unknown';

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
            const captured = await window.PromptBuilder.captureTurnPrompt(state.selectedChar);
            state.currentPrompt = { system: captured.systemPrompt, user: captured.userPrompt };

            if (els.promptSystem) els.promptSystem.textContent = captured.systemPrompt;
            if (els.promptUser) els.promptUser.textContent = captured.userPrompt;
            if (els.promptSummary) {
                els.promptSummary.textContent = `Character: ${state.selectedChar} | Area: ${roomName} | System: ${captured.systemPrompt.length} chars | User: ${captured.userPrompt.length} chars`;
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
            renderModelList();
        } catch (e) {
            els.modelList.innerHTML = `<div style="color:var(--b-red);padding:6px;">Network error: ${e.message}</div>`;
        }
    }

    function renderModelList() {
        els.modelList.innerHTML = '';
        if (state.models.length === 0) {
            els.modelList.innerHTML = '<div style="color:var(--b-muted);padding:8px;">No models reported by provider.</div>';
            return;
        }

        state.models.forEach((m, idx) => {
            const label = document.createElement('label');
            label.className = 'bench-model-item';

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'bench-model-cb';
            cb.value = m;
            if (idx < 3) {
                cb.checked = true;
                state.selectedModels.add(m);
            }

            cb.addEventListener('change', () => {
                if (cb.checked) state.selectedModels.add(m);
                else state.selectedModels.delete(m);
            });

            label.appendChild(cb);
            const span = document.createElement('span');
            span.textContent = m;
            label.appendChild(span);

            els.modelList.appendChild(label);
        });
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
                const id = sanitizeId(r.model);
                const proseEl = document.getElementById(`prose-${id}`);
                const actionEl = document.getElementById(`action-${id}`);
                const flagsEl = document.getElementById(`flags-${id}`);
                const ttftEl = document.getElementById(`metric-ttft-${id}`);
                const tpsEl = document.getElementById(`metric-tps-${id}`);
                const totalEl = document.getElementById(`metric-total-${id}`);
                const rawEl = document.getElementById(`raw-${id}`);

                if (ttftEl && r.metrics?.ttft) ttftEl.textContent = `${r.metrics.ttft.toFixed(2)}s`;
                if (tpsEl && r.metrics?.tps) tpsEl.textContent = `${r.metrics.tps}/s`;
                if (totalEl && r.metrics?.total) totalEl.textContent = `${r.metrics.total.toFixed(2)}s`;
                if (proseEl) proseEl.textContent = r.prose || 'No prose';
                if (rawEl && r.output) rawEl.textContent = r.output;

                if (actionEl && r.actions_summary) {
                    actionEl.innerHTML = r.actions_summary.map(a => `
                        <div class="bench-action-chip">
                            <span class="bench-action-chip-verb">${escapeHtml(a.verb)}</span>
                            ${a.target ? `<span class="bench-action-chip-target">${escapeHtml(a.target)}</span>` : ''}
                        </div>
                    `).join('');
                }

                if (flagsEl && r.flags) {
                    flagsEl.innerHTML = r.flags.map(f => `
                        <span class="bench-flag-item ${f.pass ? 'bench-flag-pass' : 'bench-flag-fail'}">
                            ${f.pass ? '✅' : '❌'} ${escapeHtml(f.text || f)}
                        </span>
                    `).join('');
                }

                state.results[r.model] = r;
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

        els.runBtn.disabled = true;
        els.cancelBtn.disabled = false;
        els.statusBadge.className = 'bench-status-badge bench-status-running';
        els.statusBadge.textContent = 'Running';
        els.cardsGrid.innerHTML = '';
        if (els.openDiffBtn) els.openDiffBtn.style.display = 'none';

        const modelsToRun = Array.from(state.selectedModels);
        modelsToRun.forEach(model => createModelCard(model));

        for (let i = 0; i < modelsToRun.length; i++) {
            if (!state.activeRun) break;
            const model = modelsToRun[i];
            els.statusText.textContent = `Running model ${i + 1}/${modelsToRun.length}: ${model}`;
            await runSingleModel(model, state.abortController.signal);
        }

        state.activeRun = false;
        els.runBtn.disabled = false;
        els.cancelBtn.disabled = true;
        els.statusBadge.className = 'bench-status-badge bench-status-done';
        els.statusBadge.textContent = 'Complete';
        els.statusText.textContent = `Completed ${modelsToRun.length} model evaluations.`;

        checkEnableDiff();
        saveRunRecord(modelsToRun);
    }

    function cancelBenchmark() {
        if (!state.activeRun) return;
        state.activeRun = false;
        if (state.abortController) {
            state.abortController.abort();
        }
        els.runBtn.disabled = false;
        els.cancelBtn.disabled = true;
        els.statusBadge.className = 'bench-status-badge bench-status-idle';
        els.statusBadge.textContent = 'Cancelled';
        els.statusText.textContent = 'Benchmark sweep was cancelled by user.';
        checkEnableDiff();
    }

    function createModelCard(model) {
        const card = document.createElement('div');
        card.className = 'bench-card';
        card.id = `bench-card-${sanitizeId(model)}`;

        card.innerHTML = `
            <div class="bench-card-header">
                <div class="bench-card-model" title="${escapeHtml(model)}">${escapeHtml(model)}</div>
                <div class="bench-card-metrics">
                    <div class="bench-metric">
                        <span class="bench-metric-val" id="metric-ttft-${sanitizeId(model)}">-</span>
                        <span class="bench-metric-lbl">TTFT</span>
                    </div>
                    <div class="bench-metric">
                        <span class="bench-metric-val" id="metric-tps-${sanitizeId(model)}">-</span>
                        <span class="bench-metric-lbl">TPS</span>
                    </div>
                    <div class="bench-metric">
                        <span class="bench-metric-val" id="metric-total-${sanitizeId(model)}">-</span>
                        <span class="bench-metric-lbl">Total</span>
                    </div>
                </div>
            </div>
            <div class="bench-card-body">
                <div>
                    <div class="bench-section-label">Inner Monologue &amp; Prose</div>
                    <div class="bench-prose-box" id="prose-${sanitizeId(model)}">Waiting to execute...</div>
                </div>
                <div>
                    <div class="bench-section-label">Intended Actions</div>
                    <div class="bench-action-strip" id="action-${sanitizeId(model)}">
                        <span style="color:var(--b-dim);font-size:11px;">-</span>
                    </div>
                </div>
                <div>
                    <div class="bench-section-label">Validation &amp; Ground Truth</div>
                    <div class="bench-flag-list" id="flags-${sanitizeId(model)}">
                        <span style="color:var(--b-dim);font-size:11px;">Pending...</span>
                    </div>
                </div>
                <details class="bench-raw-toggle">
                    <summary>View Raw Response</summary>
                    <div class="bench-raw-output" id="raw-${sanitizeId(model)}"></div>
                </details>
            </div>
        `;

        els.cardsGrid.appendChild(card);
    }

    async function runSingleModel(model, signal) {
        const id = sanitizeId(model);
        const proseEl = document.getElementById(`prose-${id}`);
        const rawEl = document.getElementById(`raw-${id}`);
        const ttftEl = document.getElementById(`metric-ttft-${id}`);
        const tpsEl = document.getElementById(`metric-tps-${id}`);
        const totalEl = document.getElementById(`metric-total-${id}`);
        const flagsEl = document.getElementById(`flags-${id}`);

        if (proseEl) proseEl.textContent = 'Streaming...';

        const startTime = performance.now();
        let firstTokenTime = null;
        let tokenCount = 0;
        let accumulatedText = '';

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
                    max_tokens: parseInt(els.maxTokensInput.value, 10) || 512,
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
                        const delta = parsedChunk.choices?.[0]?.delta?.content || '';
                        if (delta) {
                            if (firstTokenTime === null) {
                                firstTokenTime = performance.now();
                                if (ttftEl) ttftEl.textContent = `${((firstTokenTime - startTime) / 1000).toFixed(2)}s`;
                            }
                            tokenCount++;
                            accumulatedText += delta;
                            if (rawEl) rawEl.textContent = accumulatedText;
                        }
                    } catch (parseErr) {}
                }
            }

            const endTime = performance.now();
            const totalSec = (endTime - startTime) / 1000;
            if (totalEl) totalEl.textContent = `${totalSec.toFixed(2)}s`;

            const tps = tokenCount > 0 && totalSec > 0 ? (tokenCount / totalSec).toFixed(1) : '0';
            if (tpsEl) tpsEl.textContent = `${tps}/s`;

            evaluateModelOutput(model, accumulatedText, {
                ttft: firstTokenTime ? (firstTokenTime - startTime) / 1000 : null,
                total: totalSec,
                tps: parseFloat(tps),
                tokens: tokenCount
            });

        } catch (err) {
            if (err.name === 'AbortError') {
                if (proseEl) proseEl.textContent = 'Cancelled.';
            } else {
                if (proseEl) proseEl.textContent = `Error: ${err.message}`;
                if (flagsEl) flagsEl.innerHTML = `<span class="bench-flag-item bench-flag-fail">❌ Failed: ${escapeHtml(err.message)}</span>`;
            }
        }
    }

    function evaluateModelOutput(model, text, metrics) {
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
            if (proseEl) proseEl.textContent = text || 'Empty response.';
            if (flagsEl) flagsEl.innerHTML = '<span class="bench-flag-item bench-flag-fail">❌ Invalid JSON response</span>';
            state.results[model] = { json_valid: false, metrics, flags: [{ pass: false, text: 'Invalid JSON' }], output: text };
            return;
        }

        const monologue = parsed.inner_monologue || parsed.monologue || parsed.thought || '';
        const speech = parsed.speech ? `\n"${parsed.speech}"` : '';
        const emote = parsed.emote ? ` (${parsed.emote})` : '';
        const prose = `${monologue}${speech}${emote}`.trim() || 'No monologue or dialogue provided.';
        if (proseEl) proseEl.textContent = prose;

        // Ground truth verification against current room
        const player = state.worldData.players?.[state.selectedChar] || {};
        const roomName = player.current_area || player.area;
        const room = state.worldData.areas?.[roomName] || {};

        const validExits = Object.keys(room.exits || {});
        const validItems = (room.items || []).concat(player.inventory || []);
        const validPeople = (room.occupants || []).concat(room.characters || []);

        flags.push({ pass: true, text: 'Valid JSON output' });

        // Collect all actions (supports both single action and multi-action array)
        const actionsList = [];
        if (Array.isArray(parsed.actions)) {
            parsed.actions.forEach(a => {
                actionsList.push({ verb: a.action || a.verb || 'wait', target: a.target || a.item || '', item: a.item });
            });
        } else if (parsed.action) {
            actionsList.push({ verb: parsed.action, target: parsed.target || parsed.item || '', item: parsed.item });
        }

        if (actionsList.length === 0) {
            actionsList.push({ verb: 'wait', target: '' });
        }

        if (actionEl) {
            actionEl.innerHTML = actionsList.map(a => `
                <div class="bench-action-chip">
                    <span class="bench-action-chip-verb">${escapeHtml(a.verb)}</span>
                    ${a.target ? `<span class="bench-action-chip-target">${escapeHtml(a.target)}</span>` : ''}
                </div>
            `).join('');
        }

        actionsList.forEach(a => {
            if (['go', 'approach', 'dash'].includes(a.verb) && a.target) {
                const matchesExit = validExits.some(e => fuzzyMatch(e, a.target));
                if (!matchesExit) {
                    flags.push({ pass: false, text: `Target exit '${a.target}' not in room exits (${validExits.join(', ') || 'none'})` });
                } else {
                    flags.push({ pass: true, text: `Exit '${a.target}' recognized` });
                }
            }
            if (a.item) {
                const matchesItem = validItems.some(i => fuzzyMatch(i, a.item));
                if (!matchesItem) {
                    flags.push({ pass: false, text: `Item '${a.item}' not in room or inventory` });
                } else {
                    flags.push({ pass: true, text: `Item '${a.item}' verified` });
                }
            }
            if (a.target && !['go', 'approach', 'dash', 'wait'].includes(a.verb)) {
                const matchesPerson = validPeople.some(p => fuzzyMatch(p, a.target));
                const matchesItem = validItems.some(i => fuzzyMatch(i, a.target));
                if (!matchesPerson && !matchesItem) {
                    flags.push({ pass: false, text: `Target '${a.target}' not found in room` });
                }
            }
        });

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
            actions_summary: actionsList,
            output: text,
        };
    }

    function checkEnableDiff() {
        const completedModels = Object.keys(state.results);
        if (completedModels.length >= 2 && els.openDiffBtn) {
            els.openDiffBtn.style.display = 'inline-flex';
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

    return { init };
})();

document.addEventListener('DOMContentLoaded', () => {
    window.BenchmarkApp.init();
});
