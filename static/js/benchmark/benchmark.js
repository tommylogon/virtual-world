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
        lastSavedRunId: null,
    };

    const els = {};

    async function init() {
        cacheElements();
        attachEvents();
        wireModelMetaModal();
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
        els.sizeMinSlider = document.getElementById('bench-size-min');
        els.sizeMaxSlider = document.getElementById('bench-size-max');
        els.sizeHighlight = document.getElementById('bench-size-highlight');
        els.sizeSlider = els.sizeMaxSlider || document.getElementById('bench-size-slider');
        els.sizeVal = document.getElementById('bench-size-val');
        els.modelsCount = document.getElementById('bench-models-count');
        els.selectAllModels = document.getElementById('bench-select-all');
        els.hideBlockedCb = document.getElementById('bench-hide-blocked');
        els.onlyFreeCb = document.getElementById('bench-only-free');
        els.unloadCycleCb = document.getElementById('bench-unload-cycle');
        els.characterSelect = document.getElementById('bench-character');
        els.areaSelect = document.getElementById('bench-area');
        els.modeSelect = document.getElementById('bench-mode');
        els.proseWrap = document.getElementById('bench-prose-wrap');
        els.proseInput = document.getElementById('bench-prose-input');
        els.preferredActionInput = document.getElementById('bench-preferred-action');
        els.preferredActionList = document.getElementById('bench-preferred-action-list');
        els.temperatureInput = document.getElementById('bench-temperature');
        els.maxTokensInput = document.getElementById('bench-max-tokens');
        els.softMaxTokensInput = document.getElementById('bench-soft-max-tokens');
        els.contextLengthInput = document.getElementById('bench-context-length');
        els.reasoningEffortSelect = document.getElementById('bench-reasoning-effort');
        els.reasoningMaxTokensInput = document.getElementById('bench-reasoning-max-tokens');
        els.resultFilterWrap = document.getElementById('bench-result-filter');
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
        els.metaOverlay = document.getElementById('bench-meta-overlay');
        els.metaTitle = document.getElementById('bench-meta-title');
        els.metaId = document.getElementById('bench-meta-id');
        els.metaStatus = document.getElementById('bench-meta-status');
        els.metaVision = document.getElementById('bench-meta-vision');
        els.metaTools = document.getElementById('bench-meta-tools');
        els.metaReasoning = document.getElementById('bench-meta-reasoning');
        els.metaStructured = document.getElementById('bench-meta-structured');
        els.metaFree = document.getElementById('bench-meta-free');
        els.metaCtx = document.getElementById('bench-meta-ctx');
        els.metaRatingSummary = document.getElementById('bench-meta-rating-summary');
        els.metaStars = document.getElementById('bench-meta-stars');
        els.metaNotes = document.getElementById('bench-meta-notes');
        els.metaFeedback = document.getElementById('bench-meta-feedback');
        els.metaClose = document.getElementById('bench-meta-close');
        els.metaCancel = document.getElementById('bench-meta-cancel');
        els.metaSave = document.getElementById('bench-meta-save');
        els.sceneTruthTitle = document.getElementById('bench-scene-truth-title');
        els.sceneTruthBody = document.getElementById('bench-scene-truth-body');
        els.sceneClearHl = document.getElementById('bench-scene-clear-hl');
        els.e2eInterpreterWrap = document.getElementById('bench-e2e-interpreter-wrap');
        els.e2eInterpreterSelect = document.getElementById('bench-e2e-interpreter');
    }

    function populateE2EInterpreterSelect() {
        const sel = els.e2eInterpreterSelect;
        if (!sel) return;
        const prev = sel.value;
        const hasDedicated = !!(window.config?.interpreterModelEnabled && window.config?.interpreterModel);
        const defaultLabel = hasDedicated
            ? `Settings Interpreter (${window.config.interpreterModel})`
            : 'Same as Candidate Model (Settings off)';
        sel.innerHTML = '';
        const defOpt = document.createElement('option');
        defOpt.value = '';
        defOpt.textContent = defaultLabel;
        sel.appendChild(defOpt);
        const seen = new Set();
        (state.models || []).forEach(m => {
            const id = typeof m === 'string' ? m : (m?.id || '');
            if (!id || seen.has(id)) return;
            seen.add(id);
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            sel.appendChild(opt);
        });
        if (prev && seen.has(prev)) {
            sel.value = prev;
        }
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
            if (window.llmClient && typeof window.llmClient.configure === 'function') {
                window.llmClient.configure({
                    apiBase: profile.apiBase || els.apiBaseInput.value.trim(),
                    apiKey: profile.apiKey || 'not-needed',
                    model: profile.model || undefined,
                    apiFormat: profile.apiFormat || 'auto',
                });
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

        const updateSizeSliderUI = () => {
            if (!els.sizeMinSlider || !els.sizeMaxSlider) {
                if (els.sizeSlider) {
                    const val = parseInt(els.sizeSlider.value, 10);
                    if (els.sizeVal) els.sizeVal.textContent = val >= 40 ? 'Any' : ('<=' + val + 'B');
                }
                return;
            }
            let minVal = parseInt(els.sizeMinSlider.value, 10) || 0;
            let maxVal = parseInt(els.sizeMaxSlider.value, 10) || 72;
            if (minVal > maxVal) {
                const temp = minVal;
                minVal = maxVal;
                maxVal = temp;
            }
            const maxLimit = parseInt(els.sizeMaxSlider.max, 10) || 72;
            if (els.sizeHighlight) {
                const leftPercent = Math.min(100, Math.max(0, (minVal / maxLimit) * 100));
                const rightPercent = Math.min(100, Math.max(0, 100 - (maxVal / maxLimit) * 100));
                els.sizeHighlight.style.left = leftPercent + '%';
                els.sizeHighlight.style.right = rightPercent + '%';
            }
            if (els.sizeVal) {
                if (minVal <= 0 && maxVal >= maxLimit) {
                    els.sizeVal.textContent = 'Any';
                } else if (minVal <= 0) {
                    els.sizeVal.textContent = '<=' + maxVal + 'B';
                } else if (maxVal >= maxLimit) {
                    els.sizeVal.textContent = '>=' + minVal + 'B';
                } else {
                    els.sizeVal.textContent = minVal + 'B - ' + maxVal + 'B';
                }
            }
        };

        if (els.sizeMinSlider && els.sizeMaxSlider) {
            const onMinInput = () => {
                const minVal = parseInt(els.sizeMinSlider.value, 10) || 0;
                const maxVal = parseInt(els.sizeMaxSlider.value, 10) || 72;
                if (minVal > maxVal) {
                    els.sizeMinSlider.value = maxVal;
                }
                updateSizeSliderUI();
                renderModelList();
            };
            const onMaxInput = () => {
                const minVal = parseInt(els.sizeMinSlider.value, 10) || 0;
                const maxVal = parseInt(els.sizeMaxSlider.value, 10) || 72;
                if (maxVal < minVal) {
                    els.sizeMaxSlider.value = minVal;
                }
                updateSizeSliderUI();
                renderModelList();
            };
            els.sizeMinSlider.addEventListener('input', onMinInput);
            els.sizeMaxSlider.addEventListener('input', onMaxInput);
            els.sizeMinSlider.addEventListener('pointerdown', () => {
                els.sizeMinSlider.style.zIndex = '3';
                els.sizeMaxSlider.style.zIndex = '2';
            });
            els.sizeMaxSlider.addEventListener('pointerdown', () => {
                els.sizeMaxSlider.style.zIndex = '3';
                els.sizeMinSlider.style.zIndex = '2';
            });
            updateSizeSliderUI();
        } else if (els.sizeSlider) {
            els.sizeSlider.addEventListener('input', () => {
                const val = parseInt(els.sizeSlider.value, 10);
                if (els.sizeVal) els.sizeVal.textContent = val >= 40 ? 'Any' : ('<=' + val + 'B');
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

        if (els.preferredActionInput) {
            els.preferredActionInput.addEventListener('input', () => {
                reapplyPreferredActionScoring();
            });
        }

        els.runBtn.addEventListener('click', startBenchmark);
        els.cancelBtn.addEventListener('click', cancelBenchmark);

        if (els.hideBlockedCb) els.hideBlockedCb.addEventListener('change', renderModelList);
        if (els.onlyFreeCb) els.onlyFreeCb.addEventListener('change', renderModelList);
        if (els.refreshRunsBtn) els.refreshRunsBtn.addEventListener('click', loadPastRuns);
        if (els.resultFilterWrap) {
            state.resultFilter = 'all';
            els.resultFilterWrap.querySelectorAll('.bench-filter-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    state.resultFilter = btn.dataset.filter || 'all';
                    applyResultFilter();
                });
            });
        }
        if (els.modeSelect) {
            els.modeSelect.addEventListener('change', () => {
                const mode = els.modeSelect.value || 'direct';
                if (els.proseWrap) {
                    els.proseWrap.style.display = mode === 'interpreter' ? '' : 'none';
                }
                if (els.e2eInterpreterWrap) {
                    els.e2eInterpreterWrap.style.display = mode === 'e2e' ? '' : 'none';
                    if (mode === 'e2e') populateE2EInterpreterSelect();
                }
                if (mode === 'interpreter' && els.proseInput && !els.proseInput.value.trim()) {
                    const evalArea = state.selectedArea || state.worldData?.players?.[state.selectedChar]?.current_area || 'here';
                    const exits = Object.keys(state.worldData?.areas?.[evalArea]?.exits || {});
                    const firstExit = exits[0] ? ` and heads ${exits[0]}` : ' and takes a careful look around';
                    els.proseInput.value = `"Hold on, let me check this out," ${state.selectedChar || 'they'} mutters, glancing over their shoulder${firstExit}.`;
                }
                assembleCharacterPrompt();
            });
        }
        if (els.proseInput) {
            els.proseInput.addEventListener('input', () => {
                if ((els.modeSelect?.value || 'direct') === 'interpreter') {
                    assembleCharacterPrompt();
                }
            });
        }
        if (els.softMaxTokensInput) {
            els.softMaxTokensInput.addEventListener('change', () => assembleCharacterPrompt());
        }
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

            const softMax = parseInt(els.softMaxTokensInput?.value, 10);
            const captured = await window.PromptBuilder.captureTurnPrompt(state.selectedChar, {
                state: simulatedState,
                softMaxTokens: (Number.isFinite(softMax) && softMax > 0) ? softMax : 512,
            });
            const mode = els.modeSelect?.value || 'direct';
            const interpContext = buildRoomInterpreterContext(simulatedState, state.selectedChar, evalArea, player);
            state.interpreterContext = interpContext;

            let finalSystem = captured.systemPrompt;
            let finalUser = captured.userPrompt;
            if (mode === 'interpreter' && window.ActionInterpreter?.buildExtractionPrompt) {
                const sampleProse = (els.proseInput?.value || '').trim()
                    || `${state.selectedChar} glances around ${evalArea} and pauses to get their bearings.`;
                const ext = window.ActionInterpreter.buildExtractionPrompt({
                    prose: sampleProse,
                    charName: state.selectedChar,
                    context: interpContext,
                });
                finalSystem = ext.systemPrompt;
                finalUser = ext.userPrompt;
            } else if (mode === 'e2e') {
                finalSystem = `You are roleplaying as ${state.selectedChar} in a living virtual world. Write 2-4 sentences of natural in-character prose describing what ${state.selectedChar} thinks, says, and physically does next. Do NOT output JSON; a separate Action Interpreter will translate your prose into engine actions.`;
                finalUser = captured.userPrompt
                    .replace(/Follow the standing ACTION, SPEECH & VOLUME, and JSON rules in your system prompt\.\s*/gi, '')
                    .replace(/Respond with ONLY a single raw JSON object[\s\S]*$/i, 'Write your immediate in-character response as natural narrative prose (thoughts, dialogue, and physical action). Do NOT output JSON.');
            }

            state.currentPrompt = { system: finalSystem, user: finalUser, evalArea, mode };

            if (els.promptSystem) els.promptSystem.textContent = finalSystem;
            if (els.promptUser) els.promptUser.textContent = finalUser;
            if (els.promptSummary) {
                const simNote = state.selectedArea ? ` [Simulated in ${evalArea}, actual: ${actualArea}]` : '';
                const modeLabel = mode === 'interpreter' ? ' | Mode: Interpreter Only' : (mode === 'e2e' ? ' | Mode: End-to-End' : '');
                els.promptSummary.textContent = `Character: ${state.selectedChar} | Area: ${evalArea}${simNote}${modeLabel} | System: ${finalSystem.length} chars | User: ${finalUser.length} chars`;
            }
            renderSceneGroundTruth(simulatedState, state.selectedChar, evalArea, player);
            populatePreferredActionSuggestions(evalArea, player);
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

    function buildRoomInterpreterContext(simulatedState, charName, evalArea, player) {
        const areaObj = simulatedState?.areas?.[evalArea] || {};
        const exitsObj = areaObj.exits || {};
        const waysOut = Object.entries(exitsObj)
            .filter(([, ed]) => !ed?.hidden)
            .map(([dir, ed]) => ({
                name: ed?.name || dir,
                direction: dir,
                destination: ed?.destination || dir,
            }));
        const rawItems = (window.worldState?.getItemsInArea)
            ? (window.worldState.getItemsInArea(evalArea) || [])
            : (Array.isArray(areaObj.items) ? areaObj.items : []);
        const thingsVisible = rawItems
            .filter(it => it && it.properties?.current_state !== 'hidden')
            .map(it => typeof it === 'string' ? it : (it.name || it.id || ''))
            .filter(Boolean);
        const peopleHere = (window.PromptBuilder?.playersInAreaFor)
            ? window.PromptBuilder.playersInAreaFor(simulatedState, charName, evalArea).map(p => p.name).filter(Boolean)
            : [];
        const inventory = (Array.isArray(player?.inventory) ? player.inventory : [])
            .map(it => typeof it === 'string' ? it : (it?.name || ''))
            .filter(Boolean);
        return { waysOut, thingsVisible, peopleHere, inventory };
    }

    let _activeHighlightTerm = '';

    function applyEntityHighlight(term) {
        _activeHighlightTerm = term || '';
        if (els.sceneClearHl) {
            els.sceneClearHl.style.display = _activeHighlightTerm ? 'inline-block' : 'none';
        }
        if (els.sceneTruthBody) {
            els.sceneTruthBody.querySelectorAll('.bench-truth-chip').forEach(btn => {
                btn.classList.toggle('is-active', !!_activeHighlightTerm && btn.dataset.hlTerm === _activeHighlightTerm);
            });
        }
        const targets = document.querySelectorAll('#bench-cards-grid .bench-prose, #bench-cards-grid .bench-action-chip, #bench-prompt-user');
        const escapedRe = _activeHighlightTerm
            ? new RegExp(`(${_activeHighlightTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
            : null;
        targets.forEach(el => {
            if (el.dataset.rawText === undefined) {
                el.dataset.rawText = el.textContent || '';
            }
            const raw = el.dataset.rawText;
            if (!escapedRe) {
                el.textContent = raw;
            } else {
                const safe = escapeHtml(raw);
                const reSafe = new RegExp(`(${escapeHtml(_activeHighlightTerm).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
                el.innerHTML = safe.replace(reSafe, '<mark class="bench-entity-hit">$1</mark>');
            }
        });
    }

    function renderSceneGroundTruth(simulatedState, charName, evalArea, player) {
        if (!els.sceneTruthBody) return;
        const areaObj = simulatedState?.areas?.[evalArea] || {};
        const areaNode = (window.worldState?.getNode && areaObj.id) ? window.worldState.getNode(areaObj.id) : null;
        const areaTags = (Array.isArray(areaNode?.properties?.tags) ? areaNode.properties.tags : []).map(t => String(t).toLowerCase());
        const isOutdoor = areaTags.includes('outdoor') || areaTags.includes('exterior') || areaNode?.properties?.is_exterior === true;
        if (els.sceneTruthTitle) {
            els.sceneTruthTitle.textContent = `Room Ground Truth · ${evalArea} (${isOutdoor ? 'Outdoor' : 'Indoor'})`;
        }
        if (els.sceneClearHl && !els.sceneClearHl.dataset.wired) {
            els.sceneClearHl.dataset.wired = '1';
            els.sceneClearHl.addEventListener('click', () => applyEntityHighlight(''));
        }

        const people = (window.PromptBuilder?.playersInAreaFor)
            ? window.PromptBuilder.playersInAreaFor(simulatedState, charName, evalArea)
            : [];

        const rawItems = (window.worldState?.getItemsInArea)
            ? (window.worldState.getItemsInArea(evalArea) || [])
            : (Array.isArray(areaObj.items) ? areaObj.items : []);
        const items = rawItems
            .filter(it => it && it.properties?.current_state !== 'hidden')
            .map(it => typeof it === 'string' ? it : (it.name || it.id || ''))
            .filter(Boolean);

        const exitsObj = areaObj.exits || {};
        const exits = Object.entries(exitsObj)
            .filter(([, ed]) => !ed?.hidden)
            .map(([dir, ed]) => ({
                label: ed?.destination ? `${dir} -> ${ed.destination}` : dir,
                term: dir,
                title: ed?.description || `Exit ${dir}`,
            }));

        const rawInv = (typeof window.worldState?.getInventory === 'function' && charName)
            ? window.worldState.getInventory(charName)
            : (Array.isArray(player?.inventory) ? player.inventory : []);
        const carried = (Array.isArray(rawInv) ? rawInv : [])
            .map(it => typeof it === 'string' ? it : (it?.name || ''))
            .filter(Boolean);

        els.sceneTruthBody.innerHTML = '';

        const makeGroup = (title, chipClass, entries, emptyText) => {
            const grp = document.createElement('div');
            grp.className = 'bench-truth-group';
            const lbl = document.createElement('div');
            lbl.className = 'bench-truth-label';
            lbl.textContent = `${title} (${entries.length})`;
            grp.appendChild(lbl);

            const wrap = document.createElement('div');
            wrap.className = 'bench-truth-chips';
            if (entries.length === 0) {
                const emp = document.createElement('span');
                emp.className = 'bench-truth-empty';
                emp.textContent = emptyText;
                wrap.appendChild(emp);
            } else {
                entries.forEach(entry => {
                    const chip = document.createElement('button');
                    chip.type = 'button';
                    chip.className = `bench-truth-chip ${chipClass}`;
                    chip.textContent = entry.label;
                    chip.dataset.hlTerm = entry.term;
                    chip.title = `${entry.title || entry.label} (click to highlight in prompt & results)`;
                    if (_activeHighlightTerm && _activeHighlightTerm === entry.term) {
                        chip.classList.add('is-active');
                    }
                    chip.addEventListener('click', () => {
                        const next = (_activeHighlightTerm === entry.term) ? '' : entry.term;
                        applyEntityHighlight(next);
                    });
                    wrap.appendChild(chip);
                });
            }
            grp.appendChild(wrap);
            els.sceneTruthBody.appendChild(grp);
        };

        makeGroup(
            'People here',
            'bench-truth-chip-person',
            people.map(p => ({
                label: p.holding?.length ? `${p.name} [${p.holding.join(', ')}]` : p.name,
                term: p.name,
                title: `${p.name} (${p.state || 'awake'})`,
            })),
            'None (alone)'
        );
        makeGroup(
            'Items here',
            'bench-truth-chip-item',
            items.map(name => ({ label: name, term: name, title: `Item: ${name}` })),
            'No visible items'
        );
        makeGroup(
            'Exits',
            'bench-truth-chip-exit',
            exits,
            'No visible exits'
        );
        makeGroup(
            'Carrying',
            'bench-truth-chip-carry',
            carried.map(name => ({ label: name, term: name, title: `Carried: ${name}` })),
            'Nothing'
        );
    }

    function populatePreferredActionSuggestions(evalArea, player) {
        if (!els.preferredActionList || !state.worldData) return;
        const suggestions = new Set();
        const areaObj = state.worldData.areas?.[evalArea] || {};
        const exits = areaObj.exits || {};
        Object.keys(exits).forEach(ex => {
            suggestions.add(`go ${ex}`);
            suggestions.add(`approach ${ex}`);
        });
        if (evalArea) suggestions.add(`examine ${evalArea}`);
        const areaItems = Array.isArray(areaObj.items) ? areaObj.items : [];
        areaItems.forEach(it => {
            const name = typeof it === 'string' ? it : it?.name;
            if (name) {
                suggestions.add(`examine ${name}`);
                suggestions.add(`take ${name}`);
                suggestions.add(`use ${name}`);
            }
        });
        const inv = Array.isArray(player?.inventory) ? player.inventory : [];
        inv.forEach(name => {
            if (name) suggestions.add(`use ${name}`);
        });
        ['relieve', 'rest', 'look', 'search', 'wait', 'plan'].forEach(v => suggestions.add(v));
        els.preferredActionList.innerHTML = Array.from(suggestions)
            .slice(0, 60)
            .map(s => `<option value="${escapeHtml(s)}"></option>`)
            .join('');
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
            if (els.selectAllModels) els.selectAllModels.checked = false;
            renderModelList();
            populateE2EInterpreterSelect();
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
        const minSize = els.sizeMinSlider ? (parseInt(els.sizeMinSlider.value, 10) || 0) : 0;
        const maxLimit = els.sizeMaxSlider ? (parseInt(els.sizeMaxSlider.max, 10) || 72) : 40;
        const maxSize = els.sizeMaxSlider ? (parseInt(els.sizeMaxSlider.value, 10) || maxLimit) : (els.sizeSlider ? parseInt(els.sizeSlider.value, 10) : maxLimit);

        const hideBlocked = els.hideBlockedCb ? els.hideBlockedCb.checked : true;
        const onlyFree = els.onlyFreeCb ? els.onlyFreeCb.checked : false;
        let visibleCount = 0;

        state.models.forEach((mObj, idx) => {
            const m = typeof mObj === 'string' ? { id: mObj, name: mObj } : mObj;
            const modelId = m.id || m.name;
            const modelName = m.name || modelId;


            // 0. Status & Free filters (task-934)
            const isBlocked = m.status === 'blocked' || m.status === 'do_not_use';
            if (hideBlocked && isBlocked) return;
            if (onlyFree && !m.is_free) return;

            // 1. Min/Max size filter
            const sizeB = parseModelSizeB(m);
            if (sizeB !== null) {
                if (minSize > 0 && sizeB < minSize) {
                    return;
                }
                if (maxSize < maxLimit && sizeB > maxSize) {
                    return;
                }
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

            // Capabilities and operational badges (task-934)
            if (m.is_free) {
                const fSpan = document.createElement('span');
                fSpan.className = 'bench-tag bench-tag-free';
                fSpan.textContent = 'FREE';
                fSpan.title = 'Zero token cost / free-tier model';
                wrap.appendChild(fSpan);
            }
            if (m.status === 'blocked') {
                const bSpan = document.createElement('span');
                bSpan.className = 'bench-tag bench-tag-blocked';
                bSpan.textContent = 'BLOCKED';
                bSpan.title = 'Model is blocked or out of credit';
                wrap.appendChild(bSpan);
            } else if (m.status === 'do_not_use') {
                const dSpan = document.createElement('span');
                dSpan.className = 'bench-tag bench-tag-donotuse';
                dSpan.textContent = m.reason ? `DO NOT USE: ${m.reason}` : 'DO NOT USE';
                dSpan.title = m.notes || 'Unsuitable for standard chat turns';
                wrap.appendChild(dSpan);
            }
            if (m.ratings && m.ratings.average_score) {
                const rateSpan = document.createElement('span');
                rateSpan.className = 'bench-tag';
                rateSpan.style.color = '#e3b341';
                rateSpan.textContent = `★ ${m.ratings.average_score}`;
                rateSpan.title = `${m.ratings.total_reviews} ratings recorded`;
                wrap.appendChild(rateSpan);
            }
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

            if (isBlocked) {
                label.classList.add('is-blocked');
            }

            label.appendChild(wrap);

            const rowActions = document.createElement('span');
            rowActions.className = 'bench-model-row-actions';

            const editBtn = document.createElement('button');
            editBtn.type = 'button';
            editBtn.className = 'bench-model-icon-btn';
            editBtn.textContent = '⚙';
            editBtn.title = 'Edit status, capabilities, rating & notes';
            editBtn.addEventListener('click', (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                openModelMetaModal(m);
            });
            rowActions.appendChild(editBtn);

            const toggleBanBtn = document.createElement('button');
            toggleBanBtn.type = 'button';
            toggleBanBtn.className = 'bench-model-icon-btn';
            toggleBanBtn.textContent = isBlocked ? '↩' : '🚫';
            toggleBanBtn.title = isBlocked ? 'Restore model to Active' : 'Quick-mark as Do Not Use';
            toggleBanBtn.addEventListener('click', async (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                const nextStatus = isBlocked ? 'active' : 'do_not_use';
                const nextReason = isBlocked ? null : 'custom';
                await saveModelRegistryPatch(m, { status: nextStatus, reason: nextReason });
            });
            rowActions.appendChild(toggleBanBtn);

            label.appendChild(rowActions);
            els.modelList.appendChild(label);
        });

        if (els.modelsCount) {
            els.modelsCount.textContent = `Showing ${visibleCount} of ${state.models.length} models`;
        }

        if (visibleCount === 0) {
            els.modelList.innerHTML = '<div style="color:var(--b-dim);padding:8px;font-size:11px;">No models match filter or size slider.</div>';
        }
    }

    let _metaEditingModel = null;
    let _metaSelectedRating = 0;

    async function saveModelRegistryPatch(mObj, patch) {
        const modelId = mObj.id || mObj.name;
        const payload = Object.assign({ model_id: modelId, display_name: mObj.name || modelId }, patch);
        try {
            const resp = await fetch('/api/bench/models/metadata', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
            const saved = data.metadata || {};
            Object.assign(mObj, {
                status: saved.status ?? mObj.status,
                reason: 'reason' in saved ? saved.reason : mObj.reason,
                notes: 'notes' in saved ? saved.notes : mObj.notes,
                is_free: 'is_free' in saved ? saved.is_free : mObj.is_free,
                vision: 'vision' in saved ? saved.vision : mObj.vision,
                tools: 'tools' in saved ? saved.tools : mObj.tools,
                reasoning: 'reasoning' in saved ? saved.reasoning : mObj.reasoning,
                structured_outputs: 'structured_outputs' in saved ? saved.structured_outputs : mObj.structured_outputs,
                context_length: saved.context_length || mObj.context_length,
                ratings: saved.ratings || mObj.ratings,
            });
            if (mObj.status === 'blocked' || mObj.status === 'do_not_use') {
                state.selectedModels.delete(modelId);
            }
            renderModelList();
            return true;
        } catch (e) {
            console.error('[Benchmark] Failed saving model metadata:', e);
            return false;
        }
    }

    function openModelMetaModal(mObj) {
        if (!els.metaOverlay || !mObj) return;
        _metaEditingModel = mObj;
        _metaSelectedRating = 0;
        const modelId = mObj.id || mObj.name;
        if (els.metaTitle) els.metaTitle.textContent = mObj.name || modelId;
        if (els.metaId) els.metaId.textContent = modelId;
        if (els.metaStatus) {
            if (mObj.status === 'blocked') {
                els.metaStatus.value = 'blocked';
            } else if (mObj.status === 'do_not_use') {
                const candidate = `do_not_use:${mObj.reason || 'custom'}`;
                const hasOpt = Array.from(els.metaStatus.options).some(o => o.value === candidate);
                els.metaStatus.value = hasOpt ? candidate : 'do_not_use:custom';
            } else {
                els.metaStatus.value = 'active';
            }
        }
        if (els.metaVision) els.metaVision.checked = !!mObj.vision;
        if (els.metaTools) els.metaTools.checked = !!mObj.tools;
        if (els.metaReasoning) els.metaReasoning.checked = !!mObj.reasoning;
        if (els.metaStructured) els.metaStructured.checked = !!mObj.structured_outputs;
        if (els.metaFree) els.metaFree.checked = !!mObj.is_free;
        if (els.metaCtx) els.metaCtx.value = mObj.context_length || '';
        if (els.metaNotes) els.metaNotes.value = mObj.notes || '';
        if (els.metaFeedback) els.metaFeedback.textContent = '';

        if (els.metaRatingSummary) {
            if (mObj.ratings && mObj.ratings.total_reviews > 0) {
                const tags = (mObj.ratings.common_tags || []).length ? ` · ${mObj.ratings.common_tags.join(', ')}` : '';
                els.metaRatingSummary.textContent = `★ ${mObj.ratings.average_score} (${mObj.ratings.total_reviews} review${mObj.ratings.total_reviews === 1 ? '' : 's'})${tags}`;
                els.metaRatingSummary.style.color = '#e3b341';
            } else {
                els.metaRatingSummary.textContent = 'No ratings yet (click a star to add one)';
                els.metaRatingSummary.style.color = 'var(--b-dim)';
            }
        }
        if (els.metaStars) {
            els.metaStars.querySelectorAll('.bench-star-btn').forEach(btn => btn.classList.remove('active'));
        }
        els.metaOverlay.style.display = 'flex';
    }

    function closeModelMetaModal() {
        if (els.metaOverlay) els.metaOverlay.style.display = 'none';
        _metaEditingModel = null;
        _metaSelectedRating = 0;
    }

    function wireModelMetaModal() {
        if (els.metaClose) els.metaClose.addEventListener('click', closeModelMetaModal);
        if (els.metaCancel) els.metaCancel.addEventListener('click', closeModelMetaModal);
        if (els.metaOverlay) {
            els.metaOverlay.addEventListener('click', (e) => {
                if (e.target === els.metaOverlay) closeModelMetaModal();
            });
        }
        if (els.metaStars) {
            els.metaStars.querySelectorAll('.bench-star-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    _metaSelectedRating = parseInt(btn.dataset.star, 10) || 0;
                    els.metaStars.querySelectorAll('.bench-star-btn').forEach(b => {
                        b.classList.toggle('active', parseInt(b.dataset.star, 10) <= _metaSelectedRating);
                    });
                });
            });
        }
        if (els.metaSave) {
            els.metaSave.addEventListener('click', async () => {
                if (!_metaEditingModel) return;
                const rawStatus = els.metaStatus ? els.metaStatus.value : 'active';
                let status = 'active';
                let reason = null;
                if (rawStatus === 'blocked') {
                    status = 'blocked';
                    reason = 'blocked';
                } else if (rawStatus.startsWith('do_not_use:')) {
                    status = 'do_not_use';
                    reason = rawStatus.split(':')[1] || 'custom';
                }
                const patch = {
                    status,
                    reason,
                    vision: !!(els.metaVision && els.metaVision.checked),
                    tools: !!(els.metaTools && els.metaTools.checked),
                    reasoning: !!(els.metaReasoning && els.metaReasoning.checked),
                    structured_outputs: !!(els.metaStructured && els.metaStructured.checked),
                    is_free: !!(els.metaFree && els.metaFree.checked),
                    notes: els.metaNotes ? els.metaNotes.value.trim() : '',
                };
                if (els.metaCtx && els.metaCtx.value.trim()) {
                    const ctxNum = parseInt(els.metaCtx.value.trim(), 10);
                    if (!isNaN(ctxNum) && ctxNum > 0) patch.context_length = ctxNum;
                }
                if (_metaSelectedRating > 0) {
                    patch.rating = _metaSelectedRating;
                }
                if (els.metaFeedback) els.metaFeedback.textContent = 'Saving...';
                const ok = await saveModelRegistryPatch(_metaEditingModel, patch);
                if (ok) {
                    closeModelMetaModal();
                } else if (els.metaFeedback) {
                    els.metaFeedback.textContent = 'Failed to save.';
                }
            });
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

    function applyResultFilter() {
        if (!els.resultFilterWrap) return;
        const entries = Object.entries(state.results || {});
        if (entries.length === 0) {
            els.resultFilterWrap.style.display = 'none';
            return;
        }
        let completed = 0;
        let failed = 0;
        const activeFilter = state.resultFilter || 'all';
        entries.forEach(([model, data]) => {
            const isFailed = Boolean(data?.error) || data?.status === 'error' || data?.status === 'failed';
            if (isFailed) failed += 1;
            else completed += 1;
            const card = document.getElementById(`card-${sanitizeId(model)}`);
            if (card) {
                const show = activeFilter === 'all'
                    || (activeFilter === 'completed' && !isFailed)
                    || (activeFilter === 'failed' && isFailed);
                card.style.display = show ? '' : 'none';
            }
        });
        els.resultFilterWrap.style.display = 'flex';
        els.resultFilterWrap.querySelectorAll('.bench-filter-btn').forEach(btn => {
            const f = btn.dataset.filter;
            btn.classList.toggle('active', f === activeFilter);
            btn.style.borderColor = f === activeFilter ? 'var(--b-accent, #58a6ff)' : '';
            if (f === 'all') btn.textContent = `All (${entries.length})`;
            else if (f === 'completed') btn.textContent = `Completed (${completed})`;
            else if (f === 'failed') btn.textContent = `Failed (${failed})`;
        });
    }

    function _formatRunProvider(r) {
        if (r.provider) return r.provider;
        if (r.api_base) {
            try { return new URL(r.api_base).host; } catch (_) { return r.api_base; }
        }
        return 'unknown';
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
            let dateStr = r.run_id;
            if (r.timestamp) {
                const d = new Date(r.timestamp);
                if (!isNaN(d.getTime())) {
                    dateStr = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                        + ' · ' + d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
                }
            }
            const prov = _formatRunProvider(r);
            const total = r.model_count || 0;
            const ok = typeof r.completed_count === 'number' ? r.completed_count : total;
            const fail = typeof r.failed_count === 'number' ? r.failed_count : 0;
            const countBadge = fail > 0
                ? `<span style="color:var(--b-green,#3fb950);">${ok}/${total} ok</span> · <span style="color:var(--b-red,#f85149);">${fail} fail</span>`
                : `<span>${total} ${total === 1 ? 'model' : 'models'}</span>`;
            const locText = r.area || r.scenario || '';
            const cfg = r.config || {};
            const tooltipLines = [
                `Run: ${r.run_id}`,
                `Character: ${r.character || 'Character'}`,
                `Provider: ${prov}${r.api_base ? ` (${r.api_base})` : ''}`,
                locText ? `Location/Scenario: ${locText}` : '',
                `Results: ${ok}/${total} completed${fail > 0 ? `, ${fail} failed` : ''}`,
                cfg.temperature !== undefined ? `Temp: ${cfg.temperature}` : '',
                `Max Tokens: ${cfg.max_tokens ? cfg.max_tokens : 'Auto'}`,
                cfg.reasoning_effort ? `Reasoning Effort: ${cfg.reasoning_effort}` : '',
                cfg.reasoning_max_tokens ? `Reasoning Budget: ${cfg.reasoning_max_tokens} tok` : '',
                cfg.preferred_action ? `Preferred Action: ${cfg.preferred_action}` : '',
                r.top_model?.model ? `Top Model: ${r.top_model.model} (score ${r.top_model.score})` : '',
            ].filter(Boolean);
            item.title = tooltipLines.join('\n');
            item.innerHTML = `
                <div style="min-width:0;">
                    <div class="bench-history-name" style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                        <span>${escapeHtml(r.character || 'Character')}</span>
                        <span style="font-size:10px;padding:1px 5px;border-radius:3px;background:rgba(88,166,255,0.14);color:#79c0ff;">${escapeHtml(prov)}</span>
                    </div>
                    <div class="bench-history-meta">${dateStr} · ${countBadge}${locText ? ` · ${escapeHtml(locText)}` : ''}</div>
                </div>
                <button type="button" class="bench-btn" style="padding:2px 6px;font-size:10px;flex-shrink:0;">Load</button>
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

            // Sync provider, API base, API key, and character to match the loaded run
            // so Reroll and Save Rating hit the right provider and run ID.
            state.lastSavedRunId = run.run_id || runId;
            if (run.provider || run.api_base) {
                const normalizeUrl = (u) => String(u || '').trim().replace(/\/+$/, '').toLowerCase();
                let matchedProfile = null;
                if (run.provider && state.profileMap[run.provider]) {
                    matchedProfile = run.provider;
                } else if (run.api_base) {
                    const wantBase = normalizeUrl(run.api_base);
                    matchedProfile = Object.keys(state.profileMap || {}).find(
                        k => normalizeUrl(state.profileMap[k]?.apiBase) === wantBase
                    ) || null;
                }
                if (matchedProfile && els.providerSelect) {
                    if (els.providerSelect.value !== matchedProfile) {
                        els.providerSelect.value = matchedProfile;
                        applySelectedProfile();
                    }
                } else if (run.api_base && els.apiBaseInput) {
                    if (els.providerSelect && Array.from(els.providerSelect.options).some(o => o.value === '__custom__')) {
                        els.providerSelect.value = '__custom__';
                    }
                    els.apiBaseInput.value = run.api_base;
                }
            }
            if (run.character && els.characterSelect && state.characters.includes(run.character)) {
                if (els.characterSelect.value !== run.character) {
                    els.characterSelect.value = run.character;
                    state.selectedChar = run.character;
                    assembleCharacterPrompt();
                }
            }

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
                        <select class="bench-status-select" id="status-${id}" title="Set model status">
                            <option value="active">Active</option>
                            <option value="free">Free Tier</option>
                            <option value="blocked">Blocked</option>
                            <option value="do_not_use:embeddings">Do Not Use: Embeddings</option>
                            <option value="do_not_use:broken">Do Not Use: Broken Format</option>
                            <option value="do_not_use:audio_video">Do Not Use: Audio/Video</option>
                            <option value="do_not_use:custom">Do Not Use: Custom</option>
                        </select>
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
                    <div class="bench-metric" title="Validation score (JSON + Engine Action + Preferred Action)">
                        <span class="bench-metric-val" id="metric-score-${id}">-</span>
                        <span class="bench-metric-lbl">Score</span>
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
            <div class="bench-card-footer">
                <div class="bench-rating-row">
                    <span style="font-size:11px;font-weight:600;color:var(--b-dim);">Score Output:</span>
                    <div class="bench-stars-wrap" id="stars-${id}">
                        <button type="button" class="bench-star-btn" data-star="1" title="1 star: unusable">★</button>
                        <button type="button" class="bench-star-btn" data-star="2" title="2 stars: poor">★</button>
                        <button type="button" class="bench-star-btn" data-star="3" title="3 stars: acceptable">★</button>
                        <button type="button" class="bench-star-btn" data-star="4" title="4 stars: good">★</button>
                        <button type="button" class="bench-star-btn" data-star="5" title="5 stars: excellent">★</button>
                    </div>
                    <span id="rating-val-${id}" style="font-size:11px;color:var(--b-dim);min-width:32px;">-</span>
                </div>
                <div class="bench-feedback-tags" id="tags-${id}">
                    <button type="button" class="bench-chip-btn" data-tag="Crisp dialogue">Crisp dialogue</button>
                    <button type="button" class="bench-chip-btn" data-tag="Valid JSON">Valid JSON</button>
                    <button type="button" class="bench-chip-btn" data-tag="Natural phrasing">Natural phrasing</button>
                    <button type="button" class="bench-chip-btn" data-tag="Broken format">Broken format</button>
                    <button type="button" class="bench-chip-btn" data-tag="Hallucinated item">Hallucinated item</button>
                    <button type="button" class="bench-chip-btn" data-tag="Repetitive loop">Repetitive loop</button>
                </div>
                <div style="display:flex;gap:6px;align-items:center;">
                    <input type="text" class="bench-feedback-input" id="feedback-${id}" placeholder="Review notes (e.g. clean action choices)...">
                    <button type="button" class="bench-btn" id="btn-submit-rate-${id}" style="font-size:10px;padding:3px 8px;white-space:nowrap;">Save Rating</button>
                </div>
                <div id="rate-status-${id}" style="font-size:10px;color:var(--b-dim);text-align:right;"></div>
            </div>
        `;

        const rerollBtn = card.querySelector(`#btn-reroll-${id}`);
        if (rerollBtn) {
            rerollBtn.addEventListener('click', () => rerollSingleModel(model));
        }

        // Initialize status dropdown
        const statusSelect = card.querySelector(`#status-${id}`);
        const mObj = state.models.find(m => (m.id || m.name) === model);
        if (mObj && statusSelect) {
            if (mObj.status === 'do_not_use') {
                statusSelect.value = `do_not_use:${mObj.reason || 'custom'}`;
            } else if (mObj.status === 'blocked') {
                statusSelect.value = 'blocked';
            } else if (mObj.is_free) {
                statusSelect.value = 'free';
            } else {
                statusSelect.value = 'active';
            }
        }
        if (statusSelect) {
            statusSelect.addEventListener('change', async () => {
                const raw = statusSelect.value;
                let status = 'active';
                let reason = null;
                let is_free = false;
                if (raw === 'free') {
                    is_free = true;
                } else if (raw === 'blocked') {
                    status = 'blocked';
                } else if (raw.startsWith('do_not_use:')) {
                    status = 'do_not_use';
                    reason = raw.split(':')[1];
                }
                try {
                    await fetch('/api/bench/models/metadata', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ model_id: model, status, reason, is_free })
                    });
                    if (mObj) {
                        mObj.status = status;
                        mObj.reason = reason;
                        mObj.is_free = is_free;
                    }
                    renderModelList();
                } catch (e) {
                    console.error('Failed saving status:', e);
                }
            });
        }

        // Initialize interactive star rating & tag chips
        let cardRating = 0;
        const starsWrap = card.querySelector(`#stars-${id}`);
        const ratingValSpan = card.querySelector(`#rating-val-${id}`);
        if (starsWrap && ratingValSpan) {
            starsWrap.querySelectorAll('.bench-star-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    cardRating = parseInt(btn.dataset.star, 10);
                    ratingValSpan.textContent = `${cardRating} ★`;
                    starsWrap.querySelectorAll('.bench-star-btn').forEach(b => {
                        const s = parseInt(b.dataset.star, 10);
                        b.classList.toggle('active', s <= cardRating);
                    });
                });
            });
        }

        const tagContainer = card.querySelector(`#tags-${id}`);
        if (tagContainer) {
            tagContainer.querySelectorAll('.bench-chip-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    btn.classList.toggle('selected');
                });
            });
        }

        const rateBtn = card.querySelector(`#btn-submit-rate-${id}`);
        const rateStatus = card.querySelector(`#rate-status-${id}`);
        if (rateBtn && rateStatus) {
            rateBtn.addEventListener('click', async () => {
                if (!cardRating) {
                    rateStatus.textContent = 'Please click a star rating first.';
                    rateStatus.style.color = 'var(--b-dim)';
                    return;
                }
                const targetRunId = state.lastSavedRunId || (state.pastRuns[0]?.run_id);
                if (!targetRunId) {
                    rateStatus.textContent = 'Run benchmark first before rating.';
                    rateStatus.style.color = 'var(--b-dim)';
                    return;
                }
                const feedbackInput = card.querySelector(`#feedback-${id}`);
                const feedbackText = feedbackInput ? feedbackInput.value.trim() : '';
                const selectedTags = Array.from(card.querySelectorAll(`#tags-${id} .bench-chip-btn.selected`)).map(c => c.dataset.tag);

                try {
                    rateStatus.textContent = 'Saving rating...';
                    rateStatus.style.color = 'var(--b-dim)';
                    const resp = await fetch(`/api/bench/runs/${targetRunId}/rate`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            model: model,
                            rating: cardRating,
                            feedback: feedbackText,
                            tags: selectedTags
                        })
                    });
                    const res = await resp.json();
                    if (resp.ok) {
                        rateStatus.textContent = 'Rating saved to run & registry!';
                        rateStatus.style.color = '#3fb950';
                    } else {
                        rateStatus.textContent = res.error || 'Failed to save';
                        rateStatus.style.color = 'var(--b-red)';
                    }
                } catch (e) {
                    rateStatus.textContent = e.message;
                    rateStatus.style.color = 'var(--b-red)';
                }
            });
        }

        els.cardsGrid.appendChild(card);
    }

    function renderStructuredProse(proseEl, parsed, fallbackText) {
        if (!proseEl) return;
        delete proseEl.dataset.rawText;
        if (!parsed || typeof parsed !== 'object') {
            proseEl.textContent = fallbackText || 'No prose';
            return;
        }
        const thought = (parsed.inner_monologue || parsed.monologue || parsed.thought || '').trim();
        const speech = (parsed.speech || '').trim();
        const volume = (parsed.volume || 'say').trim();
        const emote = (parsed.emote || '').trim();
        const emotions = Array.isArray(parsed.emotion)
            ? parsed.emotion.filter(e => e && (e.label || typeof e === 'string'))
            : (parsed.emotion && typeof parsed.emotion === 'object' && parsed.emotion.label ? [parsed.emotion] : []);

        if (!thought && !speech && !emote && emotions.length === 0) {
            proseEl.textContent = fallbackText || 'No monologue or dialogue provided.';
            return;
        }

        const sections = [];
        if (thought) {
            sections.push(`
                <div class="bench-prose-part bench-part-thought">
                    <div class="bench-prose-part-head"><span>💭 Thought</span></div>
                    <div class="bench-prose-part-body">${escapeHtml(thought)}</div>
                </div>
            `);
        }
        if (speech) {
            const volBadge = volume && volume !== 'say'
                ? `<span class="bench-tag bench-tag-ctx">${escapeHtml(volume)}</span>`
                : `<span class="bench-tag bench-tag-ctx">say</span>`;
            sections.push(`
                <div class="bench-prose-part bench-part-speech">
                    <div class="bench-prose-part-head"><span>💬 Speech</span>${volBadge}</div>
                    <div class="bench-prose-part-body">"${escapeHtml(speech)}"</div>
                </div>
            `);
        }
        if (emote) {
            sections.push(`
                <div class="bench-prose-part bench-part-emote">
                    <div class="bench-prose-part-head"><span>🎭 Emote</span></div>
                    <div class="bench-prose-part-body">${escapeHtml(emote)}</div>
                </div>
            `);
        }
        if (emotions.length > 0) {
            const pills = emotions.map(e => {
                if (typeof e === 'string') return `<span class="bench-emotion-pill">${escapeHtml(e)}</span>`;
                const lbl = escapeHtml(e.label || '');
                const inten = e.intensity != null ? ` ${escapeHtml(String(e.intensity))}/10` : '';
                const toward = e.toward ? ` -> ${escapeHtml(String(e.toward))}` : '';
                return `<span class="bench-emotion-pill">${lbl}${inten}${toward}</span>`;
            }).join('');
            sections.push(`
                <div class="bench-prose-part bench-part-emotion">
                    <div class="bench-prose-part-head"><span>❤️ Emotion</span></div>
                    <div class="bench-emotion-pills">${pills}</div>
                </div>
            `);
        }
        proseEl.innerHTML = `<div class="bench-prose-parts">${sections.join('')}</div>`;
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
        const scoreEl = document.getElementById(`metric-score-${id}`);
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
        if (scoreEl) {
            if (r.score && typeof r.score.earned === 'number' && typeof r.score.max === 'number') {
                scoreEl.textContent = `${r.score.earned}/${r.score.max}`;
            } else {
                scoreEl.textContent = '-';
            }
        }
        if (proseEl) renderStructuredProse(proseEl, r.parsed, r.prose || 'No prose');
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
                        <span class="bench-action-chip-actionWord">${escapeHtml(a.actionWord)}</span>
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
        let finishReason = null;
        const captureExchange = (reqPayload, respBody, respObj) => {
            try {
                if (!window.DatasetCollector?.captureRaw) return;
                const safeBody = { ...reqPayload };
                if (safeBody.api_key) safeBody.api_key = '[redacted]';
                const responseHeaders = {};
                try { respObj?.headers?.forEach?.((v, k) => { responseHeaders[k] = v; }); } catch (e) {}
                window.DatasetCollector.captureRaw({
                    label: `benchmark:${state.selectedChar || 'turn'}`,
                    model: model,
                    url: `${els.apiBaseInput.value.trim().replace(/\/+$/, '')}/chat/completions (via /api/bench/chat)`,
                    requestHeaders: { 'content-type': 'application/json' },
                    requestBody: safeBody,
                    status: respObj?.status ?? null,
                    statusText: respObj?.statusText || '',
                    responseHeaders,
                    body: respBody,
                    durationMs: Math.round(performance.now() - startTime),
                });
            } catch (e) {}
        };
        const rawMaxTokens = els.maxTokensInput?.value?.trim() || '';
        const parsedMaxTokens = rawMaxTokens ? parseInt(rawMaxTokens, 10) : 0;
        const hardMaxTokens = (Number.isFinite(parsedMaxTokens) && parsedMaxTokens > 0) ? parsedMaxTokens : null;
        const benchPayload = {
            api_base: els.apiBaseInput.value.trim(),
            api_key: els.apiKeyInput.value.trim(),
            model: model,
            temperature: parseFloat(els.temperatureInput.value) || 0.7,
            ...(hardMaxTokens !== null ? { max_tokens: hardMaxTokens } : {}),
            reasoning_effort: els.reasoningEffortSelect?.value || 'default',
            ...(() => {
                const rawRm = els.reasoningMaxTokensInput?.value?.trim() || '';
                const parsedRm = parseInt(rawRm, 10);
                return (rawRm !== '' && Number.isFinite(parsedRm) && parsedRm > 0) ? { reasoning_max_tokens: parsedRm } : {};
            })(),
            messages: [
                { role: 'system', content: state.currentPrompt.system },
                { role: 'user', content: state.currentPrompt.user },
            ],
            stream: true,
        };

        try {
            const resp = await fetch('/api/bench/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal,
                body: JSON.stringify(benchPayload)
            });

            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                captureExchange(benchPayload, errData, resp);
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
                        if (parsedChunk.choices?.[0]?.finish_reason) {
                            finishReason = parsedChunk.choices[0].finish_reason;
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
            captureExchange(benchPayload, {
                streamed: true,
                finish_reason: finishReason,
                content: contentText,
                reasoning: reasoningText || undefined,
                usage: serverUsage || undefined,
            }, resp);
            if (!outputToEval && finishReason && finishReason !== 'stop') {
                const msg = `Blocked / stopped by provider (${finishReason}).`;
                if (proseEl) proseEl.textContent = msg;
                if (rawEl) rawEl.textContent = msg;
                if (flagsEl) flagsEl.innerHTML = `<span class="bench-flag-item bench-flag-fail">⚠️ ${escapeHtml(msg)}</span>`;
                state.results[model] = {
                    prose: msg,
                    raw: msg,
                    error: msg,
                    finish_reason: finishReason,
                    flags: [{ pass: false, label: msg }],
                    score: 0,
                    maxScore: 2,
                    metrics: { ttft: null, total: totalSec, tps: 0, tokens: totalTokens },
                };
                return;
            }
            let evalInput = outputToEval;
            if (state.currentPrompt?.mode === 'e2e' && outputToEval && window.ActionInterpreter?.buildExtractionPrompt) {
                if (proseEl) proseEl.textContent = `${outputToEval}\n\n[Interpreting prose -> engine action...]`;
                try {
                    const ext = window.ActionInterpreter.buildExtractionPrompt({
                        prose: outputToEval,
                        charName: state.selectedChar,
                        context: state.interpreterContext || undefined,
                    });
                    const overrideModel = els.e2eInterpreterSelect?.value?.trim() || '';
                    const useDedicated = !overrideModel && !!(window.config?.interpreterModelEnabled && window.config?.interpreterModel);
                    const interpBase = useDedicated ? window.config.interpreterApiBase : els.apiBaseInput.value.trim();
                    const interpKey = useDedicated ? (window.config.interpreterApiKey || els.apiKeyInput.value.trim()) : els.apiKeyInput.value.trim();
                    const interpModel = overrideModel || (useDedicated ? window.config.interpreterModel : model);
                    const interpResp = await fetch('/api/bench/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        signal,
                        body: JSON.stringify({
                            api_base: interpBase,
                            api_key: interpKey,
                            model: interpModel,
                            temperature: 0.1,
                            ...(hardMaxTokens !== null ? { max_tokens: hardMaxTokens } : {}),
                            reasoning_effort: 'none',
                            messages: [
                                { role: 'system', content: ext.systemPrompt },
                                { role: 'user', content: ext.userPrompt },
                            ],
                            stream: false,
                        }),
                    });
                    const interpData = await interpResp.json().catch(() => ({}));
                    const interpText = interpData?.choices?.[0]?.message?.content || '';
                    if (interpText.trim()) {
                        evalInput = interpText.trim();
                        if (rawEl) {
                            rawEl.textContent = `=== MODEL PROSE ===\n${outputToEval}\n\n=== INTERPRETER (${interpModel}) ===\n${evalInput}`;
                        }
                    }
                } catch (interpErr) {
                    console.warn('[Benchmark] E2E interpreter step failed:', interpErr);
                }
            }
            await evaluateModelOutput(model, evalInput, {
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
                const errMsg = `Error: ${err.message}`;
                if (proseEl) proseEl.textContent = errMsg;
                if (flagsEl) flagsEl.innerHTML = `<span class="bench-flag-item bench-flag-fail">❌ Failed: ${escapeHtml(err.message)}</span>`;
                state.results[model] = {
                    prose: errMsg,
                    raw: errMsg,
                    error: err.message,
                    flags: [{ pass: false, label: `Failed: ${err.message}` }],
                    score: 0,
                    maxScore: 2,
                    metrics: { ttft: null, total: (performance.now() - startTime) / 1000, tps: 0, tokens: 0 },
                };
            }
        }
    }

    function normalizeActionSpecForCompare(rawStr) {
        return String(rawStr || '')
            .toLowerCase()
            .replace(/\b(?:the|a|an)\b/g, ' ')
            .replace(/[_-]+/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function matchPreferredAction(preferredRaw, validatedActions) {
        const prefInput = String(preferredRaw || '').trim();
        if (!prefInput) return null;
        const candidates = prefInput.split(',').map(s => s.trim()).filter(Boolean);
        if (candidates.length === 0) return null;

        for (const cand of candidates) {
            const normCand = normalizeActionSpecForCompare(cand);
            const candParts = normCand.split(' ');
            const candAction = candParts[0];
            const candTarget = candParts.slice(1).join(' ');

            for (const va of (validatedActions || [])) {
                const normCmd = normalizeActionSpecForCompare(va.cmd);
                const normAction = normalizeActionSpecForCompare(va.actionWord);
                const normTarget = normalizeActionSpecForCompare(va.target);
                const normResolved = normalizeActionSpecForCompare(va.resolved_target || '');

                if (normCmd === normCand) return { matched: true, candidate: cand, actual: va.cmd };
                if (candAction === normAction) {
                    if (!candTarget) {
                        return { matched: true, candidate: cand, actual: va.cmd };
                    }
                    if (
                        (normTarget && (normTarget.includes(candTarget) || candTarget.includes(normTarget))) ||
                        (normResolved && (normResolved.includes(candTarget) || candTarget.includes(normResolved))) ||
                        normCmd.includes(candTarget)
                    ) {
                        return { matched: true, candidate: cand, actual: va.cmd };
                    }
                }
            }
        }
        return { matched: false, expected: candidates.join(' OR ') };
    }

    function computeScoreAndFlags(baseFlags, jsonValid, validatedActions) {
        const flags = [...(baseFlags || [])];
        if (!jsonValid) {
            const prefRaw = els.preferredActionInput?.value?.trim() || '';
            return { flags, score: { earned: 0, max: prefRaw ? 3 : 2, preferred_matched: false } };
        }
        const allActionsValid = (validatedActions || []).length > 0 && validatedActions.every(a => a.valid);
        let earned = 1 + (allActionsValid ? 1 : 0);
        let max = 2;
        let preferredMatched = null;

        const prefRaw = els.preferredActionInput?.value?.trim() || '';
        const prefCheck = matchPreferredAction(prefRaw, validatedActions);
        if (prefCheck) {
            max = 3;
            if (prefCheck.matched) {
                earned += 1;
                preferredMatched = true;
                flags.push({ pass: true, is_preferred: true, text: `+1 Preferred Action Match: '${prefCheck.actual}' (matched '${prefCheck.candidate}')` });
            } else {
                preferredMatched = false;
                flags.push({ pass: false, is_preferred: true, text: `Missed preferred action (expected: ${prefCheck.expected})` });
            }
        }
        return {
            flags,
            score: { earned, max, preferred_matched: preferredMatched }
        };
    }

    function reapplyPreferredActionScoring() {
        Object.keys(state.results || {}).forEach(model => {
            const r = state.results[model];
            if (!r) return;
            const baseFlags = (r.base_flags || (r.flags || []).filter(f => !f.is_preferred));
            r.base_flags = baseFlags;
            const { flags, score } = computeScoreAndFlags(baseFlags, r.json_valid, r.validated_actions || []);
            r.flags = flags;
            r.score = score;
            renderCardData(model, r);
        });
    }

    async function evaluateModelOutput(model, text, metrics, reasoning = '') {
        const id = sanitizeId(model);
        const proseEl = document.getElementById(`prose-${id}`);
        const actionEl = document.getElementById(`action-${id}`);
        const flagsEl = document.getElementById(`flags-${id}`);
        const scoreEl = document.getElementById(`metric-score-${id}`);

        let jsonValid = false;
        let parsed = null;
        let repairedNote = null;

        const cleaned = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```\s*$/, '').trim();
        try {
            if (typeof window.repairJSON === 'function') {
                const repaired = window.repairJSON(cleaned);
                if (window.__repairStats?.repaired) {
                    repairedNote = 'JSON repaired (truncated response)';
                    window.__repairStats.repaired = false;
                }
                parsed = JSON.parse(repaired);
                jsonValid = !!(parsed && typeof parsed === 'object');
            } else {
                parsed = JSON.parse(cleaned);
                jsonValid = true;
            }
        } catch (e) {
            const match = text.match(/\{[\s\S]*\}/);
            if (match) {
                try {
                    const candidate = typeof window.repairJSON === 'function' ? window.repairJSON(match[0]) : match[0];
                    parsed = JSON.parse(candidate);
                    jsonValid = !!(parsed && typeof parsed === 'object');
                } catch (e2) {}
            }
        }

        const baseFlags = [];

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
            const { flags, score } = computeScoreAndFlags([{ pass: false, text: failMsg }], false, []);
            if (flagsEl) flagsEl.innerHTML = `<span class="bench-flag-item bench-flag-fail">❌ ${failMsg}</span>`;
            if (scoreEl) scoreEl.textContent = `${score.earned}/${score.max}`;
            state.results[model] = {
                json_valid: false,
                metrics,
                base_flags: [{ pass: false, text: failMsg }],
                flags,
                score,
                validated_actions: [],
                output: text,
                reasoning: reasoning || '',
                prose: failProse
            };
            archiveCurrentRoll(model);
            return;
        }

        const monologue = parsed.inner_monologue || parsed.monologue || parsed.thought || '';
        const speech = parsed.speech ? `\n"${parsed.speech}"` : '';
        const emote = parsed.emote ? ` (${parsed.emote})` : '';
        const prose = `${monologue}${speech}${emote}`.trim() || 'No monologue or dialogue provided.';
        if (proseEl) renderStructuredProse(proseEl, parsed, prose);

        baseFlags.push({ pass: true, text: repairedNote ? `Valid JSON output (${repairedNote})` : 'Valid JSON output' });

        // Collect all actions while preserving full structured payload (relation, where, intensity, amount, text)
        const rawActions = [];
        if (Array.isArray(parsed.actions)) {
            parsed.actions.forEach(a => {
                if (a && typeof a === 'object') {
                    rawActions.push({ ...a, action: a.action || a.actionWord || 'wait' });
                }
            });
        } else if (parsed.action !== undefined && parsed.action !== null && parsed.action !== '') {
            rawActions.push({ ...parsed });
        }

        if (rawActions.length === 0) {
            rawActions.push({ action: 'wait' });
        }

        const actionsList = [];
        const validatedActions = [];

        // Ground-truth validation using ActionNormalizer + real engine validator (POST /api/action/validate)
        for (const rawAct of rawActions) {
            let cmdStr = '';
            if (window.ActionNormalizer && typeof window.ActionNormalizer.normalizeStructuredAction === 'function') {
                cmdStr = window.ActionNormalizer.normalizeStructuredAction(rawAct);
            } else {
                const v = String(rawAct.action || 'wait').trim();
                const t = String(rawAct.target || rawAct.item || '').trim();
                cmdStr = t ? `${v} ${t}` : v;
            }

            const actionStr = typeof rawAct.action === 'string'
                ? rawAct.action.trim()
                : (cmdStr ? cmdStr.split(/\s+/)[0] : 'wait');
            const displayTarget = cmdStr.length > actionStr.length && cmdStr.toLowerCase().startsWith(actionStr.toLowerCase() + ' ')
                ? cmdStr.slice(actionStr.length + 1).trim()
                : String(rawAct.target || rawAct.item || '').trim();

            actionsList.push({
                action: actionStr,
                target: displayTarget,
                item: rawAct.item || ''
            });

            if (window.ActionNormalizer && typeof window.ActionNormalizer.classifyAction === 'function') {
                const verdict = window.ActionNormalizer.classifyAction(cmdStr, state.selectedChar);
                if (!verdict.ok) {
                    const msg = `Action '${cmdStr || actionStr}' rejected [${verdict.category}]: ${verdict.detail}`;
                    baseFlags.push({ pass: false, text: msg });
                    validatedActions.push({ cmd: cmdStr, actionWord: actionStr, target: displayTarget, valid: false, category: verdict.category, detail: verdict.detail });
                    continue;
                }
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
                        baseFlags.push({ pass: true, text: valData.detail || `Action '${cmdStr}' verified by engine` });
                    } else {
                        baseFlags.push({ pass: false, text: valData.detail || `Action '${cmdStr}' rejected: ${valData.category || 'invalid'}` });
                    }
                    validatedActions.push({
                        cmd: cmdStr,
                        actionWord: actionStr,
                        target: displayTarget,
                        resolved_target: valData.resolved_target || '',
                        valid: !!valData.valid,
                        category: valData.category || '',
                        detail: valData.detail || ''
                    });
                } else {
                    baseFlags.push({ pass: false, text: `Engine validation error for '${cmdStr}'` });
                    validatedActions.push({ cmd: cmdStr, actionWord: actionStr, target: displayTarget, valid: false });
                }
            } catch (vErr) {
                baseFlags.push({ pass: false, text: `Could not reach engine validator for '${cmdStr}'` });
                validatedActions.push({ cmd: cmdStr, actionWord: actionStr, target: displayTarget, valid: false });
            }
        }

        if (actionEl) {
            actionEl.innerHTML = actionsList.map(a => `
                <div class="bench-action-chip">
                    <span class="bench-action-chip-actionWord">${escapeHtml(a.action)}</span>
                    ${a.target ? `<span class="bench-action-chip-target">${escapeHtml(a.target)}</span>` : ''}
                </div>
            `).join('');
        }

        const { flags, score } = computeScoreAndFlags(baseFlags, true, validatedActions);

        if (flagsEl) {
            flagsEl.innerHTML = flags.map(f => `
                <span class="bench-flag-item ${f.pass ? 'bench-flag-pass' : 'bench-flag-fail'}">
                    ${f.pass ? '✅' : '❌'} ${escapeHtml(f.text)}
                </span>
            `).join('');
        }
        if (scoreEl) {
            scoreEl.textContent = `${score.earned}/${score.max}`;
        }

        state.results[model] = {
            json_valid: true,
            metrics,
            parsed,
            base_flags: baseFlags,
            flags,
            score,
            validated_actions: validatedActions,
            prose,
            actions_summary: actionsList.map(a => ({ action: a.action, actionWord: a.action, target: a.target, item: a.item })),
            output: text,
            reasoning: reasoning || '',
        };
        archiveCurrentRoll(model);
    }

    function checkEnableDiff() {
        applyResultFilter();
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
            preferred_action: els.preferredActionInput?.value?.trim() || null,
            prompt: {
                summary: els.promptSummary?.textContent?.trim() || '',
                system: state.currentPrompt?.system || '',
                user: state.currentPrompt?.user || ''
            },
            config: {
                provider: els.providerSelect?.value || 'custom',
                api_base: els.apiBaseInput?.value?.trim() || '',
                temperature: parseFloat(els.temperatureInput?.value) || 0.7,
                max_tokens: (() => {
                    const v = parseInt(els.maxTokensInput?.value, 10);
                    return (Number.isFinite(v) && v > 0) ? v : null;
                })(),
                soft_max_tokens: parseInt(els.softMaxTokensInput?.value, 10) || 512,
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
                    score: r.score || null,
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
            const resp = await fetch('/api/bench/runs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: els.providerSelect.value,
                    api_base: els.apiBaseInput.value,
                    character: state.selectedChar,
                    scenario: state.worldData?.meta?.name || 'unknown',
                    area: els.areaSelect?.value || state.worldData?.players?.[state.selectedChar]?.current_area || '',
                    config: {
                        temperature: parseFloat(els.temperatureInput?.value) || 0.7,
                        max_tokens: (() => {
                            const v = parseInt(els.maxTokensInput?.value || '', 10);
                            return Number.isFinite(v) && v > 0 ? v : null;
                        })(),
                        soft_max_tokens: parseInt(els.softMaxTokensInput?.value || '512', 10) || 512,
                        reasoning_effort: els.reasoningEffortSelect?.value || 'default',
                        reasoning_max_tokens: (() => {
                            const v = parseInt(els.reasoningMaxTokensInput?.value || '', 10);
                            return Number.isFinite(v) && v > 0 ? v : 0;
                        })(),
                        preferred_action: els.preferredActionInput?.value?.trim() || '',
                        mode: els.modeSelect?.value || 'direct',
                        e2e_interpreter: (els.modeSelect?.value === 'e2e')
                            ? (els.e2eInterpreterSelect?.value?.trim()
                                || (window.config?.interpreterModelEnabled && window.config?.interpreterModel ? window.config.interpreterModel : 'candidate'))
                            : '',
                        area: els.areaSelect?.value || state.worldData?.players?.[state.selectedChar]?.current_area || '',
                    },
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
            if (resp && resp.ok) {
                const rData = await resp.json();
                state.lastSavedRunId = rData.run_id;
            }
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
