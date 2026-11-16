/**
 * UIController - Renders left panel: agent list, vitals, alerts, turn info
 * Also handles initialization of form controls
 *
 * @module ui-controller - the left-hand roster panel
 * @contributes UIController: agent list, per-agent vitals bars, alerts, turn info, form init
 * @powers the agent list you click to select/inspect a character, and its vitals readout
 * @relates reads worldState; drives agent selection used by the turn panel and inspector
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// `any` because window.Lit.html is declared as returning `unknown`; the templates
// are interpolated straight back into render() calls, never inspected.
const uiControllerHtmlTag = (strings: TemplateStringsArray, ...values: unknown[]): any => window.Lit.html(strings, ...values);

// Module state lives on the instance; the declarations are `declare` so they add
// nothing to the emitted classic script (a bare field would emit `AGENT_COLORS;`).
type ModelDescriptor = {
    id: string;
    name?: string;
    description?: string;
    params?: string;
    quant?: string;
    context_length?: number;
    max_output_tokens?: number;
    vision?: boolean;
    tools?: boolean;
    structured_outputs?: boolean;
    supports_temperature?: boolean;
    supports_top_p?: boolean;
    reasoning?: boolean;
    reasoning_details?: {
        mandatory?: boolean;
        supported_efforts?: string[];
        default_effort?: string;
    };
    loaded?: boolean;
    size_bytes?: number;
    status?: string;
    reason?: string;
    is_free?: boolean;
    pricing?: {
        prompt?: string | number;
        completion?: string | number;
    };
    score?: number;
    supported_parameters?: string[];
    ratings?: {
        average_score?: number;
        total_reviews?: number;
    };
};

/** Feature-detected `window` members this module reads. */
type UIWin = {
    appEvents?: { on(event: string, cb: (state: unknown) => void): void };
    /** The event bus publishes `getControlMode` / `cycleControlMode`; the shared
     *  badge vocabulary hangs off it as `controlBadge`. */
    events?: {
        getControlMode(charName: string): string;
        controlBadge(mode: string): { emoji: string; label: string; title: string };
        cycleControlMode(charName: string, anchorEl?: HTMLElement | EventTarget | null): void;
        openControlModeMenu?(charName: string, anchorEl?: HTMLElement | EventTarget | null): void;
        setControlMode?(charName: string, mode: string): Promise<void>;
    };
    VitalThresholds?: { temperatureBand(player: unknown): { cold_mild: number; heat_severe: number } };
    SkyScape?: { wire?: { _done?: boolean }; renderTopBar(el: HTMLElement, state: unknown): void };
    ValidatorPanel?: { refresh(): void };
    graphManager?: { _selectRoom(area: string): void };
    agent?: { _rateLimiter?: { msUntilAvailable(): number }; turnQueue?: string[]; currentTurnIndex?: number; turnNumber?: number };
};

class UIController {
    declare private AGENT_COLORS: string[];
    declare private _agentColorMap: Record<string, string>;
    declare private _modelList: string[];
    declare private _modelDescriptors: Array<{ id: string; name?: string; params?: string; quant?: string; context_length?: number; vision?: boolean; tools?: boolean; reasoning?: boolean; loaded?: boolean; size_bytes?: number }>;
    declare private _rateLimitTimer: ReturnType<typeof setInterval> | null;

    constructor() {
        this.AGENT_COLORS = ['#4ec9b0', '#58a6ff', '#ff7eb6', '#e3b341', '#bc8cff', '#f0883e', '#3fb950', '#f85149'];
        this._agentColorMap = {};
        this._modelList = [];
        this._modelDescriptors = [];
        this._rateLimitTimer = null;
        if ((window as unknown as UIWin).appEvents) {
            appEvents.on('state:updated', state => this.renderAll(state));
        }
    }

    getAgentColor(name: string) {
        if (!this._agentColorMap[name]) {
            this._agentColorMap[name] = this.AGENT_COLORS[Object.keys(this._agentColorMap).length % this.AGENT_COLORS.length];
        }
        return this._agentColorMap[name];
    }

    // --- Agent List ---

    renderAgentList(state: any) {
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
        let orderInfo: Record<string, any> = {};
        if (orderActive) {
            const queued = agent.turnQueue.filter((n: string) => players[n]);
            const nonQueued = Object.keys(players).filter(n => !queued.includes(n));
            names = [...queued, ...nonQueued];
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

        let rows: unknown[] = [];
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
            for (const v of ['HP', 'Energy', 'Hunger', 'Thirst'] as (keyof typeof vitals)[]) {
                if (vitals[v] !== undefined && vitals[v] < lowestVital) lowestVital = vitals[v];
            }
            const vitalColor = lowestVital > 50 ? '#3fb950' : (lowestVital > 20 ? '#e3b341' : '#f85149');

            const isSimpleNpc = p.simple_npc;
            // Who is actually driving this character, in the one shared
            // vocabulary (👾 NPC / 🤖 LLM / 👤 human - StreamControlMode
            // .controlBadge), which is also what the graph badges, the inspector
            // header and the event-stream filter chips read.
            //
            // This used to draw a SECOND glyph before the name - 🧍 for anything
            // non-simple-NPC, 🐱 for a simple one - so every row carried two
            // controller signals that could disagree ("🧍 elena vance" beside an
            // LLM badge, "🐱 ghost" beside an NPC badge), and neither 🧍 nor 🐱 is
            // a control-mode word anywhere else. There is now exactly one glyph,
            // in the badge's place, and clicking it still cycles the mode through
            // the backend (human → LLM → NPC), which task-340 built.
            const es = (window as unknown as UIWin).events;
            const mode = es ? es.getControlMode(name) : (isSimpleNpc ? 'npc' : 'llm');
            const badge = es
                ? es.controlBadge(mode)
                : { emoji: mode === 'npc' ? '👾' : '🤖', label: mode.toUpperCase(), title: mode };
            const ord = orderInfo[name];
            const orderChips = ord
                ? uiControllerHtmlTag`<span class="initiative-pos" style="font-size:9px;color:var(--text-dim);min-width:14px;">${ord.pos}.</span><span style="font-size:9px;">${ord.icon}</span>${window.Lit.unsafeHTML(ord.rollStr)}`
                : '';
            const statusText = ord
                ? uiControllerHtmlTag`<span class="initiative-status" style="font-size:9px;color:${ord.statusColor};margin-left:auto;font-weight:${ord.isCurrent ? '600' : '400'};">${ord.statusStr}</span>`
                : (mode === 'paused'
                    ? uiControllerHtmlTag`<span class="initiative-status" style="font-size:9px;color:var(--text-muted);margin-left:auto;font-style:italic;">paused</span>`
                    : '');
            const soak = p.soak;
            let soakText = '';
            if (soak) {
                const soakLabels: Record<string, string> = { idle: 'wait', leisure: 'mingle', search: 'search', explore: 'explore', travel: 'travel' };
                const left = Math.round(soak.remaining_minutes || 0);
                const verb = soakLabels[soak.intent] || soak.intent;
                soakText = uiControllerHtmlTag`<span class="initiative-status" title="Soaking - ${soak.intent}, ${left} min left" style="font-size:9px;color:#a371f7;margin-left:auto;font-weight:600;display:inline-flex;align-items:center;gap:3px;">⏩ ${verb} ${left}m <button type="button" class="soak-cancel" title="Cancel this soak order" @click=${(e: any) => { e.stopPropagation(); this.cancelSoak(name); }} style="background:none;border:0;color:#a371f7;cursor:pointer;padding:0 2px;font-size:9px;">✕</button></span>`;
            }
            if (!window.Lit) return; // startup race: first state:updated can arrive before Lit bootstrap

            rows.push(uiControllerHtmlTag`<div class="agent-item ${isSelected ? 'selected' : ''} ${statusClass === 'stuck' ? 'stuck' : ''}" @click=${() => selectAgent(name)} style="${isSimpleNpc ? 'opacity:0.85;cursor:pointer;' : ''}">
                <div class="agent-dot ${statusClass}" style="background:${color}"></div>
                ${orderChips}
                <span class="agent-ctrl" title="${badge.title} - click to select controller (Human, LLM, NPC, Paused)"
                      @click=${(e: any) => {
                          e.stopPropagation();
                          if (es?.openControlModeMenu) {
                              es.openControlModeMenu(name, e.currentTarget);
                          } else if (es?.cycleControlMode) {
                              es.cycleControlMode(name);
                          }
                      }}>${badge.emoji} ▾</span>
                <span class="agent-name">${name}</span>
                ${p.current_area
                    ? uiControllerHtmlTag`<span class="agent-location" title="Focus area in graph" @click=${(e: any) => { e.stopPropagation(); if ((window as unknown as UIWin).graphManager) graphManager._selectRoom(p.current_area); }} style="cursor:pointer;text-decoration:underline dotted;">${p.current_area}</span>`
                    : uiControllerHtmlTag`<span class="agent-location">?</span>`}
                <div class="agent-need-bar"><div class="agent-need-fill" style="width:${lowestVital}%; background:${vitalColor}"></div></div>
                ${soakText || statusText}
            </div>`);
        }
        let listTemplate;
        if (orderActive) {
            listTemplate = uiControllerHtmlTag`<div style="margin-bottom:4px;font-size:10px;color:var(--text-muted);display:flex;justify-content:space-between;"><span>Round ${agent.turnNumber + 1}</span>${config.turnOrder === 'initiative' ? uiControllerHtmlTag`<span>Init + DEX</span>` : ''}</div>${rows}`;
        } else {
            listTemplate = uiControllerHtmlTag`${rows}<div style="padding:8px 12px;font-size:10px;color:var(--text-muted);">Turn-based mode is off - no initiative order. Toggle ⏭️ Turn-Based Mode below to show it.</div>`;
        }
        window.Lit.render(listTemplate, listEl);
    }

    /**
     * Cancel a character's soak order from the roster row (task-481) and refresh
     * so the badge and queue update.
     */
    async cancelSoak(name: string) {
        try {
            await (ApiClient as unknown as { cancelSoak(name: string): Promise<unknown> }).cancelSoak(name);
            await worldState.fetch();
        } catch (err) {
            console.error('Cancel soak failed:', err);
        }
    }

    // --- Agent Overview ---

    renderSelectedAgentOverview(state: any) {
        const section = document.getElementById('agent-overview-section');
        if (!section) return;
        const name = state.active_player;
        const player = state.players?.[name];
        if (!name || !player) { section.style.display = 'none'; return; }
        section.style.display = 'block';
        document.getElementById('agent-overview-name')!.textContent = name;
        document.getElementById('agent-overview-status')!.textContent = `${player.state || 'awake'} · ${player.current_area || '?'}`;
        
        const lastAction = (config.lastActionResult as Record<string, string>)?.[name] || '';
        document.getElementById('agent-overview-action')!.textContent = lastAction.length > 80 ? lastAction + '...' : (lastAction || 'No recent action');

        const vitalsEl = document.getElementById('agent-vitals');
        const vitals = player.vitals || {};
        const polarity = state.vital_polarity || {};
        let vitalsRows: unknown[] = [];
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
            let tempColor: string;
            if (temp < 33) tempColor = '#f85149';
            else if (temp < 35) tempColor = '#58a6ff';
            else if (temp <= 39) tempColor = '#3fb950';
            else if (temp <= 40) tempColor = '#e3b341';
            else tempColor = '#f85149';
            vitalsRows.push(uiControllerHtmlTag`<div class="vital-mini"><span class="vital-mini-label">Temp</span><div class="vital-mini-bar"><div class="vital-mini-fill" style="width:${tempPct}%; background:${tempColor}"></div></div><span class="vital-mini-val">${temp}°</span></div>`);
        }
        window.Lit.render(uiControllerHtmlTag`${vitalsRows}`, vitalsEl!);
    }

    // --- Alerts ---

    renderAlerts(state: any) {
        const alertEl = document.getElementById('alert-list');
        if (!alertEl) return;
        const alerts: { type: string; name: string; text: string }[] = [];
        for (const [name, p] of Object.entries(state.players || {}) as [string, any][]) {
            const vitals = p.vitals || {};
            const maxHp = vitals.Max_HP || 100;
            const hpCriticalThreshold = Math.max(1, Math.floor(maxHp * 0.2));
            if (vitals.HP > 0 && vitals.HP <= hpCriticalThreshold) alerts.push({ type: 'error', name, text: `${name}: HP critical (${vitals.HP})` });
            else if (vitals.HP === 0) alerts.push({ type: 'error', name, text: `${name}: DEAD` });
            if (vitals.Energy <= 15) alerts.push({ type: 'warning', name, text: `${name}: Exhausted (${vitals.Energy})` });
            if (vitals.Hunger >= 85) alerts.push({ type: 'warning', name, text: `${name}: Starving (${vitals.Hunger})` });
            if (vitals.Thirst >= 85) alerts.push({ type: 'warning', name, text: `${name}: Dehydrated (${vitals.Thirst})` });
            if (vitals.Bladder >= 85) alerts.push({ type: 'warning', name, text: `${name}: Bladder full (${vitals.Bladder}%)` });
            if (vitals.Sanity <= 15) alerts.push({ type: 'warning', name, text: `${name}: Losing sanity (${vitals.Sanity})` });
            if (vitals.Entertainment <= 15) alerts.push({ type: 'warning', name, text: `${name}: Bored (${vitals.Entertainment})` });
            // Species-aware: a cold-blooded frog at 20°C is comfortable, not critical.
            const tempBand = (window as unknown as UIWin).VitalThresholds?.temperatureBand?.(p);
            if (vitals.Temperature !== undefined && tempBand
                    && (vitals.Temperature < tempBand.cold_mild - 1 || vitals.Temperature > tempBand.heat_severe)) {
                alerts.push({ type: 'danger', name, text: `${name}: Critical body temp (${Number(vitals.Temperature).toFixed(1)}°C)` });
            }
        }
        // Click an alert to select & inspect the affected agent.
        window.Lit.render(alerts.length === 0
            ? uiControllerHtmlTag`<div class="alert-empty">No alerts</div>`
            : uiControllerHtmlTag`${alerts.map(a => uiControllerHtmlTag`<div class="alert-item ${a.type}" title="Click to inspect ${a.name}" @click=${() => selectAgent(a.name)}>${a.text}</div>`)}`, alertEl);
    }

    // --- Turn Info ---

    renderTurnInfo(state: any) {
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
        const activeName = state?.active_player || ctc || '-';
        if (activeEl) activeEl.textContent = `Active: ${activeName}`;
    }

    /**
     * @deprecated Folded into renderAgentList (agents + initiative unified per task-250).
     */
    _renderInitiative(state: any) {
        // Initiative order now renders inline in the merged agent list.
    }

    // --- Full Render ---

    renderAll(state: any) {
        this.renderAgentList(state);
        this.renderSelectedAgentOverview(state);
        this.renderAlerts(state);
        this.renderTurnInfo(state);
        const timeEl = document.getElementById('sky-time');
        if (timeEl && state.game_time) {
            // task-387: if the SkyScape widget is active, it manages #sky-time;
            // the legacy clock-text overwrite would wipe the widget's span.
            if (typeof (window as unknown as UIWin).SkyScape !== 'undefined' && (window as unknown as UIWin).SkyScape!.wire?._done) {
                (window as unknown as UIWin).SkyScape!.renderTopBar(timeEl, state);
            } else {
                timeEl.textContent = `🕐 ${state.game_time.slice(0, 5)}`;
            }
        }
        const outlinePane = document.getElementById('left-tab-outline');
        if (outlinePane && outlinePane.classList.contains('active')) {
            GraphTreeView.renderOutlinePanel(document.getElementById('outline-container'));
        }
    }

    // --- Left Panel Tabs ---

    switchLeftTab(tabName: string) {
        document.querySelectorAll<HTMLElement>('#left-tabs .left-tab').forEach(btn => {
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
        if (tabName === 'issues' && (window as unknown as UIWin).ValidatorPanel) {
            ValidatorPanel.refresh();
        }
    }

    // --- Character Select ---

    selectAgent(name: string) {
        if (!worldState.players?.[name]) return;
        worldState.setRuntimeFocusForCharacter(name);
        // Open the inspector from the state we ALREADY hold. This used to await
        // `setActivePlayer` and then a full `worldState.fetch()` before showing
        // anything, so on a large world (kraktooth: 2763 nodes, ~14 MB
        // /api/state) the panel appeared seconds after the click.
        VW?.inspector?.showAgent(name);
        config.controllingPlayer = name;
        graphManager.focusNode(`player_${name.replace(/\s+/g, '_')}`);
        // The write needs NO explicit refetch: app.py's after_request broadcasts
        // `world_changed` for every mutating /api/ call, and the SSE
        // (world-state.ts connectLiveEdits) fetches state on it, which re-renders
        // the panels. The explicit fetch here was a second full /api/state
        // download per click (the SSE already did one).
        (ApiClient as unknown as { setActivePlayer(name: string): Promise<unknown> })
            .setActivePlayer(name)
            .catch(() => { /* the SSE refetch still lands; nothing to do here */ });
    }

    // --- Agent UI form controls ---

    initAgentUI() {
        const k = document.getElementById('agent-api-key') as HTMLInputElement | null;
        const b = document.getElementById('agent-api-base') as HTMLInputElement | null;
        const m = document.getElementById('agent-model') as HTMLInputElement | null;
        const lc = document.getElementById('agent-show-logs') as HTMLInputElement | null;
        const sc = document.getElementById('agent-streaming') as HTMLInputElement | null;

        // Init turn-based controls
        const turnBasedCb = document.getElementById('agent-turn-based') as HTMLInputElement | null;
        const turnOrderSel = document.getElementById('agent-turn-order') as HTMLSelectElement | null;
        const turnSettings = document.getElementById('turn-settings');
        if (turnBasedCb) {
            turnBasedCb.checked = config.turnBased as boolean;
            turnBasedCb.onchange = () => {
                config.turnBased = turnBasedCb.checked;
                config.save();
                if (turnSettings) turnSettings.style.display = turnBasedCb.checked ? 'block' : 'none';
                events.log(turnBasedCb.checked ? 'Turn-based enabled' : 'Turn-based disabled', 'system-msg');
                if ((window as unknown as UIWin).appEvents) (appEvents as unknown as { emit(event: string, payload?: unknown): void }).emit('state:updated', worldState?.data);
            };
        }
        if (turnOrderSel) turnOrderSel.value = config.turnOrder as string;
        if (turnSettings) turnSettings.style.display = config.turnBased ? 'block' : 'none';

        // Fill form fields from config
        if (k) k.value = config.apiKey as string;
        const kVisible = document.getElementById('api-key-input') as HTMLInputElement | null;
        if (kVisible) kVisible.value = config.apiKey as string;
        if (b) b.value = config.apiBase as string;
        const bVisible = document.getElementById('api-base-input') as HTMLInputElement | null;
        if (bVisible) bVisible.value = config.apiBase as string;
        if (m) m.value = config.model as string;
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
        const tempSlider = document.getElementById('hub-temperature') as HTMLInputElement | null;
        const tempVal = document.getElementById('hub-temperature-val');
        if (tempSlider) {
            tempSlider.value = (config.temperature as string) || '0.7';
            if (tempVal) tempVal.textContent = parseFloat((config.temperature as string) || '0.7').toFixed(2);
        }

        // Restore max tokens from config
        const maxTokensInput = document.getElementById('hub-max-tokens') as HTMLInputElement | null;
        if (maxTokensInput) maxTokensInput.value = (config.maxTokens || '512') as string;

        this.updateButtons();
        this.setStatus("Idle.", "info");
    }

    updateButtons() {
        const stepBtn = document.getElementById('sim-step') as HTMLButtonElement | null;
        if (stepBtn) stepBtn.disabled = (config.busy || config.running) as boolean;
        const cancelBtn = document.getElementById('sim-cancel');
        if (cancelBtn) cancelBtn.style.display = (config.busy || config.running) ? 'inline-flex' : 'none';
        const maxInput = document.getElementById('sim-max-steps') as HTMLInputElement | null;
        if (maxInput) maxInput.disabled = config.running as boolean;
        // task-533: only meaningful in a simultaneous mode, where a round waits
        // on the player. Turn-based mode already closes a round on its own.
        const endRoundBtn = document.getElementById('sim-end-round');
        if (endRoundBtn) {
            const showEndRound = !!config.simultaneousMode && !config.busy;
            endRoundBtn.style.display = showEndRound ? 'inline-flex' : 'none';
        }
        if (!config.running) {
            this.showPlayPause(true, false);
        }
    }

    setStatus(text: string, kind: string) {
        const el = document.getElementById('agent-status');
        if (el) {
            el.innerText = text;
            el.style.color = (kind === 'error') ? '#f85149' : '#8b949e';
        }
    }

    /** Show API rate-limit countdown beside max-steps (0 = hide). */
    setRateLimitCountdown(seconds: number) {
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
        const limiter = (window as unknown as UIWin).agent?._rateLimiter;
        const rpm = (config.rpmLimit || 0) as number;
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
        const limiter = (window as unknown as UIWin).agent?._rateLimiter;
        if (!limiter || !((config.rpmLimit as number) > 0)) {
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

    showPlayPause(showPlay: boolean, showPause: boolean) {
        const playBtn = document.getElementById('sim-play');
        const pauseBtn = document.getElementById('sim-pause');
        if (playBtn) playBtn.style.display = showPlay ? 'flex' : 'none';
        if (pauseBtn) pauseBtn.style.display = showPause ? 'flex' : 'none';
    }

    updateMaxStepsDisplay() {
        const el = document.getElementById('step-display');
        if (!el) return;
        if (config.running && (config.maxSteps as number) > 0) {
            const turnsRun: number = config.turnBased ? Math.floor((config.stepsRun as number) / Math.max(1, ((window as unknown as UIWin).agent?.turnQueue?.length || 1))) : (config.stepsRun as number);
            const remaining = Math.max(0, (config.maxSteps as number) - turnsRun);
            const label = config.turnBased ? 'Turn' : 'Step';
            el.textContent = `${label}: ${turnsRun}/${config.maxSteps} (${remaining} left)`;
        } else {
            const turnQueue = (window as unknown as UIWin).agent?.turnQueue || [];
            const idx = (window as unknown as UIWin).agent?.currentTurnIndex ?? 0;
            if (config.turnBased && turnQueue.length > 0) {
                const turnNum = (window as unknown as UIWin).agent?.turnNumber ?? 0;
                el.textContent = `Turn ${turnNum + 1} - ${idx + 1}/${turnQueue.length}`;
            } else {
                el.textContent = `Step: ${idx + 1}/${turnQueue.length}`;
            }
        }
    }

    // --- Profile Select ---

    async populateModelSelect(apiBase?: string) {
        const modelSelect = document.getElementById('agent-model-select') as HTMLSelectElement | null;
        if (!modelSelect) return;
        
        const base = LLMClient.normalizeBase(apiBase || config.apiBase || 'https://api.openai.com/v1');
        const apiKey = config.apiKey || '';
        
        window.Lit.render(uiControllerHtmlTag`<option value="" disabled>Loading models...</option>`, modelSelect);
        modelSelect.disabled = true;
        
        let richModels: any[] | null = null;
        try {
            // First priority: unified rich model discovery route (/api/models) sharing Benchmark native telemetry
            const apiRes = await ApiClient.fetchModels(base, apiKey);
            if (apiRes && Array.isArray(apiRes.models) && apiRes.models.length > 0) {
                richModels = apiRes.models;
            }
        } catch (e) {}

        if (!richModels || richModels.length === 0) {
            try {
                // Second priority: direct browser-to-provider fetch fallback
                const clientModels = await llmClient.fetchModels(base, apiKey);
                if (clientModels && clientModels.length > 0) {
                    richModels = clientModels.map((m: any) => typeof m === 'string' ? { id: m, name: m } : m);
                }
            } catch (e) {}
        }
        
        const hadModels = richModels && richModels.length > 0;
        if (!hadModels && apiKey) {
            const fallback = LLMClient.getFallbackModels(base);
            richModels = (fallback || []).map(m => ({ id: m, name: m }));
        }
        
        this._modelDescriptors = (richModels || []).map((m: any): ModelDescriptor => {
            if (typeof m === 'string') return { id: m, name: m };
            return {
                id: m.id || m.name || '',
                name: m.name || m.id || '',
                description: m.description,
                params: m.params,
                quant: m.quant,
                context_length: m.context_length,
                max_output_tokens: m.max_output_tokens,
                vision: m.vision,
                tools: m.tools,
                structured_outputs: m.structured_outputs,
                supports_temperature: m.supports_temperature,
                supports_top_p: m.supports_top_p,
                reasoning: m.reasoning,
                reasoning_details: m.reasoning_details,
                loaded: m.loaded,
                size_bytes: m.size_bytes,
                status: m.status,
                reason: m.reason,
                is_free: m.is_free,
                pricing: m.pricing,
                score: m.score,
                supported_parameters: m.supported_parameters,
                ratings: m.ratings
            };
        }).filter(m => m.id);

        this._modelList = this._modelDescriptors.map(m => m.id);
        
        // Populate hidden select for test compat
        modelSelect.disabled = false;
        while (modelSelect.firstChild) {
            modelSelect.removeChild(modelSelect.firstChild);
        }
        if (this._modelList.length === 0) {
            const msg = document.createElement('option');
            msg.value = '';
            msg.textContent = 'Could not fetch models - type manually';
            msg.disabled = true;
            modelSelect.appendChild(msg);
        } else {
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = '-- Select model --';
            placeholder.disabled = true;
            modelSelect.appendChild(placeholder);
            this._modelDescriptors.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = m.name || m.id;
                modelSelect.appendChild(opt);
            });
        }
        
        this.renderModelList();
        
        // Wire search + sort + category filter chips once
        const searchInput = document.getElementById('model-search') as (HTMLInputElement & { _wired?: boolean }) | null;
        const sortSelect = document.getElementById('model-sort') as (HTMLSelectElement & { _wired?: boolean }) | null;
        const filterContainer = document.getElementById('model-filter-chips') as (HTMLElement & { _wired?: boolean }) | null;
        if (searchInput && !searchInput._wired) {
            searchInput._wired = true;
            searchInput.addEventListener('input', () => this.renderModelList());
        }
        if (sortSelect && !sortSelect._wired) {
            sortSelect._wired = true;
            sortSelect.addEventListener('change', () => this.renderModelList());
        }
        if (filterContainer && !filterContainer._wired) {
            filterContainer._wired = true;
            filterContainer.querySelectorAll<HTMLButtonElement>('.model-filter-chip').forEach(btn => {
                btn.addEventListener('click', () => {
                    filterContainer.querySelectorAll('.model-filter-chip').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this._modelCategoryFilter = btn.dataset.filter || 'all';
                    this.renderModelList();
                });
            });
        }
    }

    _modelCategoryFilter: string = 'all';

    _getModelTier(modelOrName: ModelDescriptor | string): { category: string; label: string; badgeClass: string; weight: number } {
        const id = typeof modelOrName === 'string' ? modelOrName : (modelOrName.id || '');
        const name = typeof modelOrName === 'string' ? modelOrName : (modelOrName.name || id);
        const lower = `${name} ${id}`.toLowerCase();
        const p = typeof modelOrName === 'object' && modelOrName.params ? modelOrName.params.toUpperCase() : '';

        if (lower.includes('embed') || lower.includes('nomic')) {
            return { category: 'embed', label: 'embed', badgeClass: 'model-badge-embed', weight: 4 };
        }
        if (p.includes('1.') || p.includes('2B') || p.includes('3B') || /\b(1\.7b|2b|3b|tiny|mini|nano)\b/i.test(lower) || lower.includes('lfm3') || lower.includes('ling-3.0') || lower.includes('spark-x2') || lower.includes('ministral')) {
            return { category: 'fast', label: p || 'fast 1-3B', badgeClass: 'model-badge-fast', weight: 1 };
        }
        if (p.includes('7B') || p.includes('8B') || p.includes('9B') || p.includes('12B') || p.includes('14B') || /\b(7b|8b|9b|12b|14b)\b/i.test(lower)) {
            return { category: 'mid', label: p || '7-14B', badgeClass: 'model-badge-mid', weight: 2 };
        }
        if (p || /\b(24b|27b|32b|35b|70b)\b/i.test(lower) || lower.includes('qwq')) {
            return { category: 'heavy', label: p || '20B+', badgeClass: 'model-badge-heavy', weight: 3 };
        }
        return { category: 'other', label: '', badgeClass: '', weight: 5 };
    }

    renderModelList() {
        const listEl = document.getElementById('model-list')!;
        if (!listEl) return;
        
        const searchInput = document.getElementById('model-search') as (HTMLInputElement & { _wired?: boolean }) | null;
        const sortSelect = document.getElementById('model-sort') as (HTMLSelectElement & { _wired?: boolean }) | null;
        const query = (searchInput?.value || '').toLowerCase();
        const sort = sortSelect?.value || 'name-asc';
        
        const descriptors: ModelDescriptor[] = this._modelDescriptors.length > 0
            ? this._modelDescriptors
            : this._modelList.map((id: string): ModelDescriptor => ({ id, name: id }));

        let models = descriptors.slice();
        if (query) {
            models = models.filter(m => (m.name || m.id).toLowerCase().includes(query) || (Boolean(m.params) && (m.params as string).toLowerCase().includes(query)));
        }
        if (this._modelCategoryFilter && this._modelCategoryFilter !== 'all') {
            if (this._modelCategoryFilter === 'free') {
                models = models.filter(m => Boolean(m.is_free) || m.id.endsWith(':free') || m.id.includes(':free'));
            } else if (this._modelCategoryFilter === 'reasoning') {
                models = models.filter(m => Boolean(m.reasoning || (m as any).has_reasoning));
            } else {
                models = models.filter(m => this._getModelTier(m).category === this._modelCategoryFilter);
            }
        }

        models.sort((a, b) => {
            if (sort === 'fast-first') {
                const wa = this._getModelTier(a).weight;
                const wb = this._getModelTier(b).weight;
                if (wa !== wb) return wa - wb;
                return (a.name || a.id).toLowerCase().localeCompare((b.name || b.id).toLowerCase());
            }
            const cmp = (a.name || a.id).toLowerCase().localeCompare((b.name || b.id).toLowerCase());
            return sort === 'name-asc' ? cmp : -cmp;
        });
        
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
            item.className = 'model-list-item' + (m.id === currentModel ? ' selected' : '');
            
            const nameWrap = document.createElement('div');
            nameWrap.style.display = 'flex';
            nameWrap.style.flexDirection = 'column';
            nameWrap.style.gap = '2px';
            nameWrap.style.minWidth = '0';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'model-name';
            nameSpan.textContent = m.name || m.id;
            nameWrap.appendChild(nameSpan);

            const badgesWrap = document.createElement('div');
            badgesWrap.style.display = 'flex';
            badgesWrap.style.gap = '4px';
            badgesWrap.style.flexWrap = 'wrap';
            badgesWrap.style.alignItems = 'center';

            if (m.params || m.quant) {
                const qBadge = document.createElement('span');
                qBadge.className = 'model-list-badge model-badge-mid';
                qBadge.textContent = `${m.params || ''} ${m.quant || ''}`.trim();
                badgesWrap.appendChild(qBadge);
            } else {
                const tier = this._getModelTier(m);
                if (tier.label) {
                    const badge = document.createElement('span');
                    badge.className = `model-list-badge ${tier.badgeClass}`;
                    badge.textContent = tier.label;
                    badgesWrap.appendChild(badge);
                }
            }

            if (m.context_length) {
                const ctxBadge = document.createElement('span');
                ctxBadge.className = 'model-list-badge model-badge-ctx';
                const k = Math.round(m.context_length / 1024);
                ctxBadge.textContent = k >= 1024 ? `${(k / 1024).toFixed(1)}M ctx` : `${k}K ctx`;
                badgesWrap.appendChild(ctxBadge);
            }

            if (m.loaded) {
                const loadBadge = document.createElement('span');
                loadBadge.className = 'model-list-badge model-badge-loaded';
                loadBadge.textContent = 'Loaded';
                badgesWrap.appendChild(loadBadge);
            }

            if (m.reasoning) {
                const rBadge = document.createElement('span');
                rBadge.className = 'model-list-badge model-badge-reasoning';
                rBadge.textContent = 'Reasoning';
                badgesWrap.appendChild(rBadge);
            }

            if (m.tools) {
                const tBadge = document.createElement('span');
                tBadge.className = 'model-list-badge model-badge-tools';
                tBadge.textContent = 'Tools';
                badgesWrap.appendChild(tBadge);
            }

            if (m.vision) {
                const vBadge = document.createElement('span');
                vBadge.className = 'model-list-badge model-badge-vision';
                vBadge.textContent = 'Vision';
                badgesWrap.appendChild(vBadge);
            }

            // Rich hover tooltip (task-941)
            const tip: string[] = [`ID: ${m.id}`];
            if (m.name && m.name !== m.id) tip.push(`Display: ${m.name}`);
            if (m.context_length) {
                const k = Math.round(m.context_length / 1024);
                tip.push(`Context Window: ${k >= 1024 ? (k / 1024).toFixed(1) + 'M' : k + 'K'} (${m.context_length.toLocaleString()} tokens)`);
            }
            if (m.params || m.quant) tip.push(`Architecture: ${m.params || ''} ${m.quant || ''}`.trim());
            const capsList: string[] = [];
            if (m.vision) capsList.push('Vision');
            if (m.reasoning) capsList.push('Reasoning');
            if (m.tools) capsList.push('Tools');
            if (capsList.length > 0) tip.push(`Capabilities: ${capsList.join(', ')}`);
            if (m.status === 'do_not_use') tip.push(`Status: DO NOT USE (${m.reason || 'unsuitable'})`);
            else if (m.is_free) tip.push('Status: Free Tier');
            if (m.ratings && m.ratings.average_score) tip.push(`Rating: ★ ${m.ratings.average_score} (${m.ratings.total_reviews} runs)`);
            item.title = tip.join('\n');

            item.appendChild(nameWrap);
            if (badgesWrap.children.length > 0) {
                item.appendChild(badgesWrap);
            }

            item.addEventListener('click', () => {
                const modelInput = document.getElementById('agent-model') as HTMLInputElement | null;
                if (modelInput) modelInput.value = m.id;
                config.model = m.id;

                // Auto-detect vision capability (task-941)
                if (m.vision) {
                    const visionCb = document.getElementById('agent-vision-enabled') as HTMLInputElement | null;
                    if (visionCb && !visionCb.checked) {
                        visionCb.checked = true;
                        (config as Record<string, unknown>).visionEnabled = true;
                        events?.log?.(`Auto-enabled Vision mode based on model capabilities (${m.name || m.id})`, 'system-msg');
                    }
                }

                config.save();
                VW?.llm?.configure((config.toLLMConfig as () => unknown)());
                listEl.querySelectorAll('.model-list-item').forEach(el => el.classList.remove('selected'));
                item.classList.add('selected');
                this.updateModelSpecsSummary(m);
            });
            listEl.appendChild(item);
        });

        const activeObj = descriptors.find(m => m.id === currentModel) || (currentModel ? { id: currentModel, name: currentModel } : undefined);
        if (activeObj) {
            this.updateModelSpecsSummary(activeObj);
        }
    }

    renderActiveModelInspector(m?: ModelDescriptor) {
        const cardEl = document.getElementById('active-model-card');
        if (!cardEl) return;
        if (!m || !m.id) {
            cardEl.style.display = 'none';
            return;
        }
        cardEl.style.display = 'block';

        // Title and ID
        const titleEl = document.getElementById('card-model-title');
        if (titleEl) {
            titleEl.textContent = m.name || m.id;
            titleEl.title = 'ID: ' + m.id;
        }

        // Badges container
        const badgesEl = document.getElementById('card-model-badges');
        if (badgesEl) {
            badgesEl.innerHTML = '';
            
            // Free or Pricing badge
            if (m.is_free || m.id.includes(':free')) {
                const freeBadge = document.createElement('span');
                freeBadge.className = 'model-list-badge model-badge-free';
                freeBadge.textContent = '🎁 Free Tier';
                badgesEl.appendChild(freeBadge);
            } else if (m.pricing && (m.pricing.prompt !== undefined || m.pricing.completion !== undefined)) {
                const priceBadge = document.createElement('span');
                priceBadge.className = 'model-list-badge';
                const pIn = m.pricing.prompt ?? 0;
                const pOut = m.pricing.completion ?? 0;
                priceBadge.textContent = `$${pIn} / $${pOut} per 1M`;
                badgesEl.appendChild(priceBadge);
            }

            // Score badge
            if (m.score !== undefined && m.score !== null) {
                const scoreBadge = document.createElement('span');
                scoreBadge.className = 'model-list-badge model-badge-reasoning';
                scoreBadge.textContent = `⚡ AA Index: ${m.score}`;
                scoreBadge.title = 'Artificial Analysis Intelligence Index';
                badgesEl.appendChild(scoreBadge);
            }

            // Tier / Architecture
            const tier = this._getModelTier(m);
            if (tier.label) {
                const tBadge = document.createElement('span');
                tBadge.className = `model-list-badge ${tier.badgeClass}`;
                tBadge.textContent = tier.label;
                badgesEl.appendChild(tBadge);
            }

            // User rating
            if (m.ratings && m.ratings.average_score) {
                const rBadge = document.createElement('span');
                rBadge.className = 'model-list-badge';
                rBadge.textContent = `★ ${m.ratings.average_score} (${m.ratings.total_reviews ?? 0})`;
                badgesEl.appendChild(rBadge);
            }
        }

        // Description block
        const descEl = document.getElementById('card-model-desc');
        if (descEl) {
            if (m.description && m.description.trim()) {
                descEl.textContent = m.description.trim();
                descEl.style.display = 'block';
            } else {
                descEl.style.display = 'none';
            }
        }

        // Token Budget
        const ctxTextEl = document.getElementById('card-context-window-text');
        const hubMaxTokens = document.getElementById('hub-max-tokens') as HTMLInputElement | null;
        const hubSoftMaxTokens = document.getElementById('hub-soft-max-tokens') as HTMLInputElement | null;
        const btnPreset4k = document.getElementById('btn-preset-4k') as HTMLButtonElement | null;
        const btnPreset8k = document.getElementById('btn-preset-8k') as HTMLButtonElement | null;
        const btnPresetMax = document.getElementById('btn-preset-max') as HTMLButtonElement | null;

        const maxAllowed = m.max_output_tokens || (m.context_length ? Math.min(m.context_length, 1048576) : 1048576);

        if (ctxTextEl) {
            if (m.context_length) {
                const k = Math.round(m.context_length / 1024);
                const ctxFormatted = k >= 1024 ? `${(k / 1024).toFixed(1)}M` : `${k}K`;
                const maxOutFormatted = m.max_output_tokens ? ` | Max Output Ceiling: ${m.max_output_tokens.toLocaleString()}` : '';
                ctxTextEl.textContent = `Context Window: ${ctxFormatted} (${m.context_length.toLocaleString()} tokens)${maxOutFormatted}`;
            } else {
                ctxTextEl.textContent = 'Context Window: Standard / Provider Default';
            }
        }

        const persistAndApply = () => {
            config.save();
            VW?.llm?.configure?.((config as any).toLLMConfig?.());
        };

        if (hubMaxTokens) {
            hubMaxTokens.max = String(maxAllowed);
            hubMaxTokens.value = String(config.maxTokens || 2048);
            hubMaxTokens.onchange = () => {
                const val = parseInt(hubMaxTokens.value, 10) || 2048;
                config.maxTokens = val;
                persistAndApply();
            };
        }

        if (hubSoftMaxTokens) {
            hubSoftMaxTokens.max = String(maxAllowed);
            hubSoftMaxTokens.value = String(config.softMaxTokens || 0);
            hubSoftMaxTokens.onchange = () => {
                const val = parseInt(hubSoftMaxTokens.value, 10) || 0;
                config.softMaxTokens = val;
                persistAndApply();
            };
        }

        // Preset buttons
        if (btnPreset4k) {
            btnPreset4k.onclick = () => {
                const tok = Math.min(4096, maxAllowed);
                if (hubMaxTokens) hubMaxTokens.value = String(tok);
                config.maxTokens = tok;
                persistAndApply();
                events?.log?.(`Applied 4K token preset (${tok})`, 'system-msg');
            };
        }
        if (btnPreset8k) {
            btnPreset8k.onclick = () => {
                const tok = Math.min(8192, maxAllowed);
                if (hubMaxTokens) hubMaxTokens.value = String(tok);
                config.maxTokens = tok;
                persistAndApply();
                events?.log?.(`Applied 8K token preset (${tok})`, 'system-msg');
            };
        }
        if (btnPresetMax) {
            if (m.max_output_tokens && m.max_output_tokens > 8192) {
                btnPresetMax.style.display = 'inline-block';
                const labelK = Math.round(m.max_output_tokens / 1024);
                btnPresetMax.textContent = `Full Max (${labelK >= 1024 ? (labelK/1024).toFixed(1)+'M' : labelK+'K'})`;
                btnPresetMax.onclick = () => {
                    const tok = m.max_output_tokens!;
                    if (hubMaxTokens) hubMaxTokens.value = String(tok);
                    config.maxTokens = tok;
                    config.save();
                    VW?.llm?.configure?.((config as any).toLLMConfig?.());
                    events?.log?.(`Applied full model max token ceiling (${tok.toLocaleString()})`, 'system-msg');
                };
            } else {
                btnPresetMax.style.display = 'none';
            }
        }

        // Reasoning & Thinking
        const hubThinkingCb = document.getElementById('hub-thinking') as HTMLInputElement | null;
        const mandatoryBadge = document.getElementById('card-thinking-mandatory-badge');
        const hubThinkingOptions = document.getElementById('hub-thinking-options');
        const hubEffortSel = document.getElementById('hub-thinking-effort') as HTMLSelectElement | null;
        const hubSuppressCb = document.getElementById('hub-suppress-thinking') as HTMLInputElement | null;

        const isMandatory = Boolean(m.reasoning_details?.mandatory);
        let configChanged = false;

        if (mandatoryBadge) {
            mandatoryBadge.style.display = isMandatory ? 'inline-block' : 'none';
        }

        if (isMandatory && !config.thinking) {
            config.thinking = true;
            configChanged = true;
        }

        if (hubThinkingCb) {
            hubThinkingCb.checked = Boolean(config.thinking);
            hubThinkingCb.disabled = isMandatory;
            hubThinkingCb.title = isMandatory ? 'Reasoning is mandatory for this model' : 'Include chain-of-thought reasoning tokens';
            hubThinkingCb.onchange = () => {
                config.thinking = hubThinkingCb.checked;
                persistAndApply();
                if (hubThinkingOptions) hubThinkingOptions.style.display = hubThinkingCb.checked ? 'block' : 'none';
            };
        }

        if (hubThinkingOptions) {
            hubThinkingOptions.style.display = config.thinking ? 'block' : 'none';
        }

        if (hubEffortSel) {
            while (hubEffortSel.firstChild) hubEffortSel.removeChild(hubEffortSel.firstChild);
            const allEfforts = ['none', 'minimal', 'low', 'medium', 'high', 'max'];
            let supported = (m.reasoning_details?.supported_efforts && m.reasoning_details.supported_efforts.length > 0)
                ? m.reasoning_details.supported_efforts
                : allEfforts;
            if (isMandatory && supported.some(e => e !== 'none')) {
                supported = supported.filter(e => e !== 'none');
            }

            supported.forEach(eff => {
                const opt = document.createElement('option');
                opt.value = eff;
                opt.textContent = eff.charAt(0).toUpperCase() + eff.slice(1);
                hubEffortSel.appendChild(opt);
            });

            const rawEffort = (config.thinkingEffort as string) || m.reasoning_details?.default_effort || 'high';
            const preferredDefault = (m.reasoning_details?.default_effort && m.reasoning_details.default_effort !== 'none')
                ? m.reasoning_details.default_effort
                : (supported[supported.length - 1] || 'high');
            const resolvedEffort = (supported.includes(rawEffort) && !(isMandatory && rawEffort === 'none'))
                ? rawEffort
                : (supported.includes(preferredDefault) ? preferredDefault : (supported[supported.length - 1] || 'high'));

            hubEffortSel.value = resolvedEffort;
            if (config.thinkingEffort !== resolvedEffort) {
                config.thinkingEffort = resolvedEffort;
                configChanged = true;
            }

            hubEffortSel.onchange = () => {
                config.thinkingEffort = hubEffortSel.value;
                persistAndApply();
            };
        }

        if (configChanged) {
            config.save();
            VW?.llm?.configure?.((config as any).toLLMConfig?.());
        }

        if (hubSuppressCb) {
            hubSuppressCb.checked = Boolean(config.suppressLocalThinking);
            hubSuppressCb.onchange = () => {
                config.suppressLocalThinking = hubSuppressCb.checked;
                persistAndApply();
            };
        }

        // Sampling: Temperature
        const hubTemp = document.getElementById('hub-temperature') as HTMLInputElement | null;
        const hubTempVal = document.getElementById('hub-temperature-val');
        const hubTempWarn = document.getElementById('hub-temp-warning');
        const supportsTemp = m.supported_parameters ? m.supported_parameters.includes('temperature') : (m.supports_temperature !== false);

        if (hubTemp && hubTempVal) {
            const curTemp = typeof config.temperature === 'number' ? config.temperature : 0.70;
            hubTemp.value = String(curTemp);
            hubTempVal.textContent = curTemp.toFixed(2);
            hubTemp.oninput = () => {
                const val = parseFloat(hubTemp.value);
                hubTempVal.textContent = val.toFixed(2);
                config.temperature = val;
                persistAndApply();
            };
        }
        if (hubTempWarn) hubTempWarn.style.display = supportsTemp ? 'none' : 'inline-block';
        if (hubTemp && hubTemp.parentElement) {
            hubTemp.parentElement.classList.toggle('param-unsupported', !supportsTemp);
        }

        // Sampling: Top-P
        const hubTopP = document.getElementById('hub-top-p') as HTMLInputElement | null;
        const hubTopPVal = document.getElementById('hub-top-p-val');
        const hubTopPWarn = document.getElementById('hub-topp-warning');
        const supportsTopP = m.supported_parameters ? m.supported_parameters.includes('top_p') : (m.supports_top_p !== false);

        if (hubTopP && hubTopPVal) {
            const curTopP = typeof config.topP === 'number' ? config.topP : 0.95;
            hubTopP.value = String(curTopP);
            hubTopPVal.textContent = curTopP.toFixed(2);
            hubTopP.oninput = () => {
                const val = parseFloat(hubTopP.value);
                hubTopPVal.textContent = val.toFixed(2);
                config.topP = val;
                persistAndApply();
            };
        }
        if (hubTopPWarn) hubTopPWarn.style.display = supportsTopP ? 'none' : 'inline-block';
        if (hubTopP && hubTopP.parentElement) {
            hubTopP.parentElement.classList.toggle('param-unsupported', !supportsTopP);
        }

        // Capabilities Checklist
        const capTools = document.getElementById('card-cap-tools');
        const capStructured = document.getElementById('card-cap-structured');
        const capVision = document.getElementById('card-cap-vision');

        if (capTools) {
            capTools.classList.toggle('active', Boolean(m.tools));
            capTools.classList.toggle('inactive', !m.tools);
        }
        if (capStructured) {
            capStructured.classList.toggle('active', Boolean(m.structured_outputs));
            capStructured.classList.toggle('inactive', !m.structured_outputs);
        }
        if (capVision) {
            capVision.classList.toggle('active', Boolean(m.vision));
            capVision.classList.toggle('inactive', !m.vision);
        }
    }

    updateModelSpecsSummary(m?: ModelDescriptor) {
        this.renderActiveModelInspector(m);
        const summaryEl = document.getElementById('model-specs-summary');
        if (!summaryEl) return;
        if (!m || (!m.context_length && !m.params && !m.quant && !m.reasoning && !m.tools)) {
            summaryEl.style.display = 'none';
            return;
        }
        const parts: string[] = [];
        if (m.context_length) {
            const k = Math.round(m.context_length / 1024);
            const formatted = k >= 1024 ? `${(k / 1024).toFixed(1)}M (${m.context_length.toLocaleString()})` : `${k}K (${m.context_length.toLocaleString()})`;
            parts.push(`Context: ${formatted} tokens`);
        }
        if (m.params || m.quant) {
            parts.push(`Arch: ${m.params || ''} ${m.quant || ''}`.trim());
        }
        const caps: string[] = [];
        if (m.reasoning) caps.push('Reasoning');
        if (m.tools) caps.push('Tools');
        if (m.vision) caps.push('Vision');
        if (caps.length > 0) parts.push(`Capabilities: ${caps.join(', ')}`);

        summaryEl.textContent = parts.join(' | ');
        summaryEl.style.display = 'block';
    }
    async populateProfileSelect() {
        const sel = document.getElementById('profile-select') as HTMLSelectElement | null;
        if (!sel) return;
        const currentValue = sel.value;
        while (sel.firstChild) {
            sel.removeChild(sel.firstChild);
        }
        const profiles = await (config.getProfiles as () => Promise<Record<string, unknown>>)();
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
        const profiles = await (config.getProfiles as () => Promise<Record<string, unknown>>)();
        const names = Object.keys(profiles);
        
        await this.populateProfileSelect();
        
        // Restore last used profile
        let targetProfile = null;
        if (config.lastProfile && names.includes(config.lastProfile as string)) {
            targetProfile = config.lastProfile as string;
        } else {
            targetProfile = names[0];
        }
        
        if (targetProfile) {
            const sel = document.getElementById('profile-select') as HTMLSelectElement | null;
            if (sel) sel.value = targetProfile;
            await (config.applyProfile as (name: string) => Promise<unknown>)(targetProfile);
        }
    }
}

// Singleton
const ui = new UIController();
