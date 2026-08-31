/**
 * UIController — Renders left panel: agent list, vitals, alerts, turn info
 * Also handles initialization of form controls
 */
const uiControllerHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

class UIController {
    constructor() {
        this.AGENT_COLORS = ['#4ec9b0', '#58a6ff', '#ff7eb6', '#e3b341', '#bc8cff', '#f0883e', '#3fb950', '#f85149'];
        this._agentColorMap = {};
        this._modelList = [];
        this._rateLimitTimer = null;
        if (window.appEvents) {
            appEvents.on('state:updated', state => this.renderAll(state));
        }
    }

    getAgentColor(name) {
        if (!this._agentColorMap[name]) {
            this._agentColorMap[name] = this.AGENT_COLORS[Object.keys(this._agentColorMap).length % this.AGENT_COLORS.length];
        }
        return this._agentColorMap[name];
    }

    // --- Agent List ---

    renderAgentList(state) {
        const listEl = document.getElementById('agent-list');
        if (!listEl) return;
        const players = state.players || {};
        const activeName = state.active_player;

        // Turn-order markers when turn-based is active and a queue exists
        const orderActive = !!config.turnBased && agent.turnQueue.length > 0;
        const ctc = agent.getCurrentTurnCharacter();
        const rerollBtn = document.getElementById('reroll-init-btn');
        if (rerollBtn) rerollBtn.style.display = (orderActive && config.turnOrder === 'initiative') ? 'inline-block' : 'none';

        let names = Object.keys(players);
        let orderInfo = {};
        if (orderActive) {
            names = agent.turnQueue.filter(n => players[n]);
            for (let i = 0; i < agent.turnQueue.length; i++) {
                const name = agent.turnQueue[i];
                if (!players[name]) continue;
                const roll = agent.initiativeRolls?.[name];
                const noTurnsYet = agent.turnNumber === 0 && Object.keys(config.lastActionResult || {}).length === 0;
                const isCurrent = name === ctc;
                const isDone = i < agent.currentTurnIndex;
                orderInfo[name] = {
                    pos: i + 1,
                    icon: isCurrent ? '▶️' : (isDone ? '✅' : '⏳'),
                    isCurrent,
                    isDone,
                    rollStr: roll !== undefined ? ` <span style="font-size:9px;color:var(--text-dim);">(${roll})</span>` : '',
                    statusStr: isCurrent ? (noTurnsYet ? 'up next' : 'ACTING…') : (isDone ? 'done' : 'waiting'),
                    statusColor: isCurrent ? 'var(--green)' : 'var(--text-muted)'
                };
            }
        }

        let rows = [];
        for (const name of names) {
            const p = players[name];
            if (!p) continue;
            const isSelected = (name === activeName);
            const color = this.getAgentColor(name);
            let statusClass = 'idle';
            if (p.state === 'dead') statusClass = 'stuck';
            else if (config.busy && config.controllingPlayer === name) statusClass = 'acting';

            const vitals = p.vitals || {};
            let lowestVital = 100;
            for (const v of ['HP', 'Energy', 'Hunger', 'Thirst']) {
                if (vitals[v] !== undefined && vitals[v] < lowestVital) lowestVital = vitals[v];
            }
            const vitalColor = lowestVital > 50 ? '#3fb950' : (lowestVital > 20 ? '#e3b341' : '#f85149');

            const isSimpleNpc = p.simple_npc;
            const agentIcon = isSimpleNpc ? '🐱' : '🧍';
            const ord = orderInfo[name];
            const orderChips = ord
                ? uiControllerHtmlTag`<span class="initiative-pos" style="font-size:9px;color:var(--text-dim);min-width:14px;">${ord.pos}.</span><span style="font-size:9px;">${ord.icon}</span>${window.Lit.unsafeHTML(ord.rollStr)}`
                : '';
            const statusText = ord
                ? uiControllerHtmlTag`<span class="initiative-status" style="font-size:9px;color:${ord.statusColor};margin-left:auto;font-weight:${ord.isCurrent ? '600' : '400'};">${ord.statusStr}</span>`
                : '';
            if (!window.Lit) return; // startup race: first state:updated can arrive before Lit bootstrap

            rows.push(uiControllerHtmlTag`<div class="agent-item ${isSelected ? 'selected' : ''} ${statusClass === 'stuck' ? 'stuck' : ''}" @click=${() => selectAgent(name)} style="${isSimpleNpc ? 'opacity:0.85;cursor:pointer;' : ''}">
                <div class="agent-dot ${statusClass}" style="background:${color}"></div>
                ${orderChips}
                <span class="agent-name">${agentIcon} ${name}</span>
                ${p.current_area
                    ? uiControllerHtmlTag`<span class="agent-location" title="Focus area in graph" @click=${(e) => { e.stopPropagation(); if (window.graphManager) graphManager._selectRoom(p.current_area); }} style="cursor:pointer;text-decoration:underline dotted;">${p.current_area}</span>`
                    : uiControllerHtmlTag`<span class="agent-location">?</span>`}
                <div class="agent-need-bar"><div class="agent-need-fill" style="width:${lowestVital}%; background:${vitalColor}"></div></div>
                ${statusText}
            </div>`);
        }
        let listTemplate;
        if (orderActive) {
            listTemplate = uiControllerHtmlTag`<div style="margin-bottom:4px;font-size:10px;color:var(--text-muted);display:flex;justify-content:space-between;"><span>Round ${agent.turnNumber + 1}</span>${config.turnOrder === 'initiative' ? uiControllerHtmlTag`<span>Init + DEX</span>` : ''}</div>${rows}`;
        } else {
            listTemplate = uiControllerHtmlTag`${rows}<div style="padding:8px 12px;font-size:10px;color:var(--text-muted);">Turn-based mode is off — no initiative order. Toggle ⏭️ Turn-Based Mode below to show it.</div>`;
        }
        window.Lit.render(listTemplate, listEl);
    }

    // --- Agent Overview ---

    renderSelectedAgentOverview(state) {
        const section = document.getElementById('agent-overview-section');
        if (!section) return;
        const name = state.active_player;
        const player = state.players?.[name];
        if (!name || !player) { section.style.display = 'none'; return; }
        section.style.display = 'block';
        document.getElementById('agent-overview-name').textContent = name;
        document.getElementById('agent-overview-status').textContent = `${player.state || 'awake'} · ${player.current_area || '?'}`;
        
        const lastAction = config.lastActionResult?.[name] || '';
        document.getElementById('agent-overview-action').textContent = lastAction.length > 80 ? lastAction + '...' : (lastAction || 'No recent action');

        const vitalsEl = document.getElementById('agent-vitals');
        const vitals = player.vitals || {};
        const polarity = state.vital_polarity || {};
        let vitalsRows = [];
        for (const v of ['HP', 'Energy', 'Hunger', 'Thirst', 'Hygiene', 'Social', 'Bladder', 'Sanity', 'Entertainment']) {
            if (v === 'Max_HP' || vitals[v] === undefined) continue;
            const val = vitals[v];
            const max = v === 'HP' ? (vitals.Max_HP || 100) : 100;
            const pct = (val / max) * 100;
            const isDrive = polarity[v] === 'drive';
            const color = isDrive
                ? (val > 50 ? '#f85149' : (val > 20 ? '#e3b341' : '#3fb950'))
                : (val > 50 ? '#3fb950' : (val > 20 ? '#e3b341' : '#f85149'));
            vitalsRows.push(uiControllerHtmlTag`<div class="vital-mini"><span class="vital-mini-label">${v}</span><div class="vital-mini-bar"><div class="vital-mini-fill" style="width:${pct}%; background:${color}"></div></div><span class="vital-mini-val">${val}</span></div>`);
        }
        // Temperature mini-bar (Celsius, safe range 35-39)
        const temp = vitals.Temperature;
        if (temp !== undefined) {
            const tempPct = Math.max(0, Math.min(100, ((temp - 25) / 20) * 100));
            let tempColor;
            if (temp < 33) tempColor = '#f85149';
            else if (temp < 35) tempColor = '#58a6ff';
            else if (temp <= 39) tempColor = '#3fb950';
            else if (temp <= 40) tempColor = '#e3b341';
            else tempColor = '#f85149';
            vitalsRows.push(uiControllerHtmlTag`<div class="vital-mini"><span class="vital-mini-label">Temp</span><div class="vital-mini-bar"><div class="vital-mini-fill" style="width:${tempPct}%; background:${tempColor}"></div></div><span class="vital-mini-val">${temp}°</span></div>`);
        }
        window.Lit.render(uiControllerHtmlTag`${vitalsRows}`, vitalsEl);
    }

    // --- Alerts ---

    renderAlerts(state) {
        const alertEl = document.getElementById('alert-list');
        if (!alertEl) return;
        const alerts = [];
        for (const [name, p] of Object.entries(state.players || {})) {
            const v = p.vitals || {};
            const maxHp = v.Max_HP || 100;
            const hpCriticalThreshold = Math.max(1, Math.floor(maxHp * 0.2));
            if (v.HP > 0 && v.HP <= hpCriticalThreshold) alerts.push({ type: 'error', name, text: `${name}: HP critical (${v.HP})` });
            else if (v.HP === 0) alerts.push({ type: 'error', name, text: `${name}: DEAD` });
            if (v.Energy <= 15) alerts.push({ type: 'warning', name, text: `${name}: Exhausted (${v.Energy})` });
            if (v.Hunger >= 85) alerts.push({ type: 'warning', name, text: `${name}: Starving (${v.Hunger})` });
            if (v.Thirst >= 85) alerts.push({ type: 'warning', name, text: `${name}: Dehydrated (${v.Thirst})` });
            if (v.Bladder >= 85) alerts.push({ type: 'warning', name, text: `${name}: Bladder full (${v.Bladder}%)` });
            if (v.Sanity <= 15) alerts.push({ type: 'warning', name, text: `${name}: Losing sanity (${v.Sanity})` });
            if (v.Entertainment <= 15) alerts.push({ type: 'warning', name, text: `${name}: Bored (${v.Entertainment})` });
            if (v.Temperature !== undefined && (v.Temperature < 34 || v.Temperature > 40)) alerts.push({ type: 'danger', name, text: `${name}: Critical body temp (${v.Temperature}°C)` });
        }
        // Click an alert to select & inspect the affected agent.
        window.Lit.render(alerts.length === 0
            ? uiControllerHtmlTag`<div class="alert-empty">No alerts</div>`
            : uiControllerHtmlTag`${alerts.map(a => uiControllerHtmlTag`<div class="alert-item ${a.type}" title="Click to inspect ${a.name}" @click=${() => selectAgent(a.name)}>${a.text}</div>`)}`, alertEl);
    }

    // --- Turn Info ---

    renderTurnInfo(state) {
        const turnEl = document.getElementById('turn-display');
        const stepEl = document.getElementById('step-display');
        const activeEl = document.getElementById('active-char-display');

        // When turn queue is empty (no turn-based mode / single character scenario),
        // fall back to world state tick info
        if (agent.turnQueue.length === 0) {
            const tick = state?.time_ticks ?? 0;
            if (turnEl) turnEl.textContent = `Turn: ${tick}`;
            if (stepEl) stepEl.textContent = `Step: ${tick}`;
        } else {
            if (turnEl) turnEl.textContent = `Turn: ${agent.turnNumber}`;
            if (stepEl) stepEl.textContent = `Step: ${agent.currentTurnIndex + 1}/${agent.turnQueue.length}`;
        }

        const ctc = agent.getCurrentTurnCharacter();
        const activeName = state?.active_player || ctc || '—';
        if (activeEl) activeEl.textContent = `Active: ${activeName}`;
    }

    /**
     * @deprecated Folded into renderAgentList (agents + initiative unified per task-250).
     */
    _renderInitiative(state) {
        // Initiative order now renders inline in the merged agent list.
    }

    // --- Full Render ---

    renderAll(state) {
        this.renderAgentList(state);
        this.renderSelectedAgentOverview(state);
        this.renderAlerts(state);
        this.renderTurnInfo(state);
        const timeEl = document.getElementById('ui-time');
        if (timeEl && state.game_time) timeEl.textContent = state.game_time;
        const outlinePane = document.getElementById('left-tab-outline');
        if (outlinePane && outlinePane.classList.contains('active')) {
            GraphTreeView.renderOutlinePanel(document.getElementById('outline-container'));
        }
    }

    // --- Left Panel Tabs ---

    switchLeftTab(tabName) {
        document.querySelectorAll('#left-tabs .left-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        ['agents', 'outline', 'lens', 'issues', 'nl-editor'].forEach(name => {
            const pane = document.getElementById('left-tab-' + name);
            if (pane) pane.classList.toggle('active', name === tabName);
        });
        const leftPanel = document.getElementById('left-panel');
        if (leftPanel) leftPanel.classList.toggle('left-panel--lens', tabName === 'lens');
        if (tabName === 'outline') {
            GraphTreeView.renderOutlinePanel(document.getElementById('outline-container'));
        }
        if (tabName === 'lens') {
            agentLens.refresh();
        }
        if (tabName === 'issues' && window.ValidatorPanel) {
            ValidatorPanel.refresh();
        }
    }

    // --- Character Select ---

    selectAgent(name) {
        if (worldState.players?.[name]) {
            ApiClient.setActivePlayer(name).then(async () => {
                await worldState.fetch();
                VW?.inspector?.showAgent(name);
                config.controllingPlayer = name;
                graphManager.focusNode(`player_${name.replace(/\s+/g, '_')}`);
            });
        }
    }

    // --- Agent UI form controls ---

    initAgentUI() {
        const k = document.getElementById('agent-api-key');
        const b = document.getElementById('agent-api-base');
        const m = document.getElementById('agent-model');
        const lc = document.getElementById('agent-show-logs');
        const sc = document.getElementById('agent-streaming');

        // Init turn-based controls
        const turnBasedCb = document.getElementById('agent-turn-based');
        const turnOrderSel = document.getElementById('agent-turn-order');
        const turnSettings = document.getElementById('turn-settings');
        if (turnBasedCb) {
            turnBasedCb.checked = config.turnBased;
            turnBasedCb.onchange = () => {
                config.turnBased = turnBasedCb.checked;
                config.save();
                if (turnSettings) turnSettings.style.display = turnBasedCb.checked ? 'block' : 'none';
                events.log(turnBasedCb.checked ? 'Turn-based enabled' : 'Turn-based disabled', 'system-msg');
                if (window.appEvents) appEvents.emit('state:updated', worldState?.data);
            };
        }
        if (turnOrderSel) turnOrderSel.value = config.turnOrder;
        if (turnSettings) turnSettings.style.display = config.turnBased ? 'block' : 'none';

        // Fill form fields from config
        if (k) k.value = config.apiKey;
        const kVisible = document.getElementById('api-key-input');
        if (kVisible) kVisible.value = config.apiKey;
        if (b) b.value = config.apiBase;
        const bVisible = document.getElementById('api-base-input');
        if (bVisible) bVisible.value = config.apiBase;
        if (m) m.value = config.model;
        if (lc) {
            lc.checked = !!config.showLogs;
            lc.addEventListener('change', () => {
                config.showLogs = lc.checked;
                events.log("LLM logs " + (lc.checked ? "ON" : "OFF"), "system-msg");
            });
        }
        if (sc) {
            sc.checked = !!config.streaming;
            sc.addEventListener('change', () => {
                config.streaming = sc.checked;
                events.log("Streaming " + (sc.checked ? "ON" : "OFF"), "system-msg");
            });
        }

        // Restore temperature slider from config
        const tempSlider = document.getElementById('agent-temperature');
        const tempVal = document.getElementById('agent-temperature-val');
        if (tempSlider) {
            tempSlider.value = config.temperature || '0.7';
            if (tempVal) tempVal.textContent = parseFloat(config.temperature || '0.7').toFixed(2);
        }

        // Restore max tokens from config
        const maxTokensInput = document.getElementById('max-tokens-input');
        if (maxTokensInput) maxTokensInput.value = config.maxTokens || '512';

        this.updateButtons();
        this.setStatus("Idle.", "info");
    }

    updateButtons() {
        const stepBtn = document.getElementById('sim-step');
        if (stepBtn) stepBtn.disabled = config.busy || config.running;
        const cancelBtn = document.getElementById('sim-cancel');
        if (cancelBtn) cancelBtn.style.display = (config.busy || config.running) ? 'inline-flex' : 'none';
        const maxInput = document.getElementById('sim-max-steps');
        if (maxInput) maxInput.disabled = config.running;
    }

    setStatus(text, kind) {
        const el = document.getElementById('agent-status');
        if (el) {
            el.innerText = text;
            el.style.color = (kind === 'error') ? '#f85149' : '#8b949e';
        }
    }

    /** Show API rate-limit countdown beside max-steps (0 = hide). */
    setRateLimitCountdown(seconds) {
        const el = document.getElementById('sim-rate-limit');
        if (!el) return;
        const sec = Math.ceil(Number(seconds) || 0);
        if (sec <= 0) {
            el.hidden = true;
            el.textContent = '';
            return;
        }
        el.hidden = false;
        el.textContent = `⏱ ${sec}s`;
    }

    clearRateLimitCountdown() {
        this.setRateLimitCountdown(0);
    }

    /** Tick the toolbar countdown from the agent rate limiter (idle between steps). */
    syncRateLimitDisplay() {
        const limiter = window.agent?._rateLimiter;
        const rpm = config.rpmLimit || 0;
        if (!limiter || rpm <= 0) {
            this.stopRateLimitMonitor();
            return;
        }
        const ms = limiter.msUntilAvailable();
        if (ms <= 0) {
            this.stopRateLimitMonitor();
            return;
        }
        this.setRateLimitCountdown(Math.ceil(ms / 1000));
        if (!this._rateLimitTimer) {
            this._rateLimitTimer = setInterval(() => this._tickRateLimitDisplay(), 1000);
        }
    }

    _tickRateLimitDisplay() {
        const limiter = window.agent?._rateLimiter;
        if (!limiter || !(config.rpmLimit > 0)) {
            this.stopRateLimitMonitor();
            return;
        }
        const ms = limiter.msUntilAvailable();
        if (ms <= 0) {
            this.stopRateLimitMonitor();
            return;
        }
        this.setRateLimitCountdown(Math.ceil(ms / 1000));
    }

    stopRateLimitMonitor() {
        if (this._rateLimitTimer) {
            clearInterval(this._rateLimitTimer);
            this._rateLimitTimer = null;
        }
        this.clearRateLimitCountdown();
    }

    showPlayPause(showPlay, showPause) {
        const playBtn = document.getElementById('sim-play');
        const pauseBtn = document.getElementById('sim-pause');
        if (playBtn) playBtn.style.display = showPlay ? 'flex' : 'none';
        if (pauseBtn) pauseBtn.style.display = showPause ? 'flex' : 'none';
    }

    updateMaxStepsDisplay() {
        const el = document.getElementById('step-display');
        if (!el) return;
        if (config.running && config.maxSteps > 0) {
            const turnsRun = config.turnBased ? Math.floor(config.stepsRun / Math.max(1, (window.agent?.turnQueue?.length || 1))) : config.stepsRun;
            const remaining = Math.max(0, config.maxSteps - turnsRun);
            const label = config.turnBased ? 'Turn' : 'Step';
            el.textContent = `${label}: ${turnsRun}/${config.maxSteps} (${remaining} left)`;
        } else {
            const turnQueue = window.agent?.turnQueue || [];
            const idx = window.agent?.currentTurnIndex ?? 0;
            if (config.turnBased && turnQueue.length > 0) {
                const turnNum = window.agent?.turnNumber ?? 0;
                el.textContent = `Turn ${turnNum + 1} — ${idx + 1}/${turnQueue.length}`;
            } else {
                el.textContent = `Step: ${idx + 1}/${turnQueue.length}`;
            }
        }
    }

    // --- Profile Select ---

    async populateModelSelect(apiBase) {
        const modelSelect = document.getElementById('agent-model-select');
        if (!modelSelect) return;
        
        const base = LLMClient.normalizeBase(apiBase || config.apiBase || 'https://api.openai.com/v1');
        const apiKey = config.apiKey || '';
        
        window.Lit.render(uiControllerHtmlTag`<option value="" disabled>Loading models...</option>`, modelSelect);
        modelSelect.disabled = true;
        
        let models = null;
        try {
            models = await llmClient.fetchModels(base, apiKey);
        } catch (e) {}
        
        const hadModels = models && models.length > 0;
        if (!hadModels && apiKey) {
            models = LLMClient.getFallbackModels(base);
        }
        
        this._modelList = models || [];
        
        // Populate hidden select for test compat
        modelSelect.disabled = false;
        while (modelSelect.firstChild) {
            modelSelect.removeChild(modelSelect.firstChild);
        }
        if (this._modelList.length === 0) {
            const msg = document.createElement('option');
            msg.value = '';
            msg.textContent = '⚠️ Could not fetch models — type manually';
            msg.disabled = true;
            modelSelect.appendChild(msg);
        } else {
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = '-- Select model --';
            placeholder.disabled = true;
            modelSelect.appendChild(placeholder);
            this._modelList.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                modelSelect.appendChild(opt);
            });
        }
        
        this.renderModelList();
        
        // Wire search + sort once
        const searchInput = document.getElementById('model-search');
        const sortSelect = document.getElementById('model-sort');
        if (searchInput && !searchInput._wired) {
            searchInput._wired = true;
            searchInput.addEventListener('input', () => this.renderModelList());
        }
        if (sortSelect && !sortSelect._wired) {
            sortSelect._wired = true;
            sortSelect.addEventListener('change', () => this.renderModelList());
        }
    }

    renderModelList() {
        const listEl = document.getElementById('model-list');
        if (!listEl) return;
        
        const searchInput = document.getElementById('model-search');
        const sortSelect = document.getElementById('model-sort');
        const query = (searchInput?.value || '').toLowerCase();
        const sort = sortSelect?.value || 'name-asc';
        
        let models = this._modelList.slice();
        if (query) {
            models = models.filter(m => m.toLowerCase().includes(query));
        }
        models.sort((a, b) => {
            const cmp = a.toLowerCase().localeCompare(b.toLowerCase());
            return sort === 'name-asc' ? cmp : -cmp;
        });
        
        // Imperative wipe: Lit.render() only clears content between its own
        // comment markers, so items appended via appendChild would survive it
        // and stack up on every keystroke/sort change.
        while (listEl.firstChild) {
            listEl.removeChild(listEl.firstChild);
        }
        if (models.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'model-list-empty';
            empty.textContent = query ? 'No matches' : 'No models loaded';
            listEl.appendChild(empty);
            return;
        }
        
        const currentModel = config.model || '';
        models.forEach(m => {
            const item = document.createElement('div');
            item.className = 'model-list-item' + (m === currentModel ? ' selected' : '');
            item.textContent = m;
            item.addEventListener('click', () => {
                const modelInput = document.getElementById('agent-model');
                if (modelInput) modelInput.value = m;
                config.model = m;
                config.save();
                VW?.llm?.configure(config.toLLMConfig());
                listEl.querySelectorAll('.model-list-item').forEach(el => el.classList.remove('selected'));
                item.classList.add('selected');
            });
            listEl.appendChild(item);
        });
    }

    async populateProfileSelect() {
        const sel = document.getElementById('profile-select');
        if (!sel) return;
        const currentValue = sel.value;
        while (sel.firstChild) {
            sel.removeChild(sel.firstChild);
        }
        const profiles = await config.getProfiles();
        const names = Object.keys(profiles);
        if (names.length === 0) {
            sel.appendChild(new Option('-- No profiles --', ''));
            return;
        }
        names.forEach(name => sel.appendChild(new Option(name, name)));
        if (names.includes(currentValue)) {
            sel.value = currentValue;
        } else {
            sel.value = names[0];
        }
    }

    async initProfiles() {
        await config._initPromise;
        
        // Ensure defaults are seeded
        const profiles = await config.getProfiles();
        const names = Object.keys(profiles);
        
        await this.populateProfileSelect();
        
        // Restore last used profile
        let targetProfile = null;
        if (config.lastProfile && names.includes(config.lastProfile)) {
            targetProfile = config.lastProfile;
        } else {
            targetProfile = names[0];
        }
        
        if (targetProfile) {
            const sel = document.getElementById('profile-select');
            if (sel) sel.value = targetProfile;
            await config.applyProfile(targetProfile);
        }
    }
}

// Singleton
const ui = new UIController();