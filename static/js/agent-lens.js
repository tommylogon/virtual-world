/**
 * agent-lens.js — Left-panel preview of area/agent prompt context (task-219).
 * Reuses PromptBuilder; preview-only way state overrides are not persisted.
 */

// Lazy tag: classic scripts parse before the deferred lit-bootstrap module
// runs, so window.Lit only exists when a view actually renders.
const agentLensHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

class AgentLens {
    constructor() {
        this._viewAs = null;
        this._hypotheticalArea = null;
        this._wayStateOverrides = {};
        this._debounceTimer = null;
        this._refreshing = false;
        this._lastPlainText = '';
        this._lastSig = '';
        this._SECTION_META = {
            'Context lead-in': { icon: '📍', accent: '#58a6ff' },
            'Area description': { icon: '🏠', accent: '#58a6ff' },
            'Environment': { icon: '🌡', accent: '#58a6ff' },
            'Items': { icon: '📦', accent: '#e3b341' },
            'People': { icon: '🧍', accent: '#f778ba' },
            'Exits': { icon: '🚪', accent: '#3fb950' },
            'Witnessed': { icon: '👁', accent: '#bc8cff' },
            'Room context': { icon: '🏠', accent: '#58a6ff' },
            'System prompt': { icon: '⚙️', accent: '#8b949e' },
            'Character context': { icon: '💭', accent: '#bc8cff' },
            'Think / decide user message': { icon: '🧠', accent: '#58a6ff' },
            'React prompt': { icon: '💬', accent: '#f778ba' },
            'Combined reaction prompt': { icon: '⚡', accent: '#e3b341' },
            'Note': { icon: 'ℹ️', accent: '#6e7681' },
            'Last action result': { icon: '▶️', accent: '#f0883e' },
            'Full context': { icon: '📄', accent: '#58a6ff' },
        };
    }

    init() {
        if (window.appEvents) {
            appEvents.on('state:updated', () => this._scheduleRefresh());
            appEvents.on('inspector:view', () => this._scheduleRefresh());
        }
    }

    _scheduleRefresh() {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => this.refresh(), 300);
    }

    _esc(text) {
        return String(text ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    _playerNames() {
        return Object.keys(worldState.data?.players || worldState.players || {}).sort();
    }

    _agentColor(name) {
        return VW?.ui?.getAgentColor?.(name) || '#58a6ff';
    }

    _modeIcon(mode) {
        return ({ area: '🏠', agent: '🧍', way: '🚪' })[mode] || '👁';
    }

    setViewAs(name) {
        this._viewAs = name;
        this.refresh();
    }

    setHypotheticalArea(areaName) {
        this._hypotheticalArea = areaName || null;
        this.refresh();
    }

    setWayOverride(wayId, state) {
        if (!wayId) return;
        if (!state) delete this._wayStateOverrides[wayId];
        else this._wayStateOverrides[wayId] = state;
        this.refresh();
    }

    clearWayOverrides() {
        this._wayStateOverrides = {};
        this.refresh();
    }

    expandAll() {
        document.querySelectorAll('#agent-lens-content .agent-lens-section').forEach(el => { el.open = true; });
    }

    collapseAll() {
        document.querySelectorAll('#agent-lens-content .agent-lens-section').forEach(el => { el.open = false; });
    }

    copyAll() {
        const text = this._lastPlainText || document.getElementById('agent-lens-content')?.innerText || '';
        navigator.clipboard?.writeText(text.trim()).then(() => toastInfo?.('Full preview copied')).catch(() => {});
    }

    _currentSelection() {
        return window.VW?.inspector?._currentView || null;
    }

    _resolveAreaName(selection) {
        if (!selection) return null;
        if (selection.type === 'agent') {
            const player = worldState.players?.[selection.name];
            return this._hypotheticalArea || player?.current_area || null;
        }
        if (selection.type === 'node') {
            const node = worldState.getNode(selection.id);
            if (!node) return null;
            if (node.type === 'area') return node.name;
            if (node.type === 'way') return null;
            if (node.type === 'item') {
                for (const areaName of Object.keys(worldState.data?.areas || {})) {
                    const inArea = worldState.getItemsInArea(areaName).some(
                        item => item.id === selection.id || item.name === node.name
                    );
                    if (inArea) return areaName;
                }
                return null;
            }
            if (node.type === 'character') {
                return worldState.players?.[node.name]?.current_area || null;
            }
        }
        return null;
    }

    _focusItemName(selection) {
        if (selection?.type !== 'node') return null;
        const node = worldState.getNode(selection.id);
        return node?.type === 'item' ? (node.name || null) : null;
    }

    _buildLensState(areaName, charName) {
        const base = worldState.data;
        if (!base || !areaName) return null;
        const area = base.areas?.[areaName];
        if (!area) return null;

        const areaClone = JSON.parse(JSON.stringify(area));
        if (areaClone.exits) {
            Object.values(areaClone.exits).forEach(exit => {
                const wayId = exit?.way_id;
                if (wayId && this._wayStateOverrides[wayId]) {
                    exit.state = this._wayStateOverrides[wayId];
                }
            });
        }

        const playersInArea = [];
        Object.entries(base.players || {}).forEach(([name, pdata]) => {
            if (name === charName || pdata.current_area !== areaName) return;
            playersInArea.push({
                name,
                state: pdata.state || 'awake',
                description: pdata.description || '',
                activity: pdata.activity || null,
            });
        });

        return {
            ...base,
            current_area: areaName,
            players_in_area: playersInArea,
            areas: { ...base.areas, [areaName]: areaClone },
        };
    }

    _wordCount(text) {
        const n = String(text || '').trim().split(/\s+/).filter(Boolean).length;
        return n ? `${n} words` : 'empty';
    }

    _formatBody(text) {
        const lines = String(text || '').split('\n');
        if (!lines.length) return '<div class="lens-line lens-dim">(empty)</div>';
        return lines.map(line => {
            let cls = 'lens-line';
            const t = line.trim();
            if (t.startsWith('⚠️')) cls += ' lens-warn';
            else if (t.startsWith('===')) cls += ' lens-heading';
            else if (t.startsWith('- ') || t.startsWith('  - ')) cls += ' lens-bullet';
            else if (/^\[[^\]]+\]/.test(t)) cls += ' lens-tag';
            else if (!t) cls += ' lens-dim';
            return `<div class="${cls}">${this._esc(line) || '&nbsp;'}</div>`;
        }).join('');
    }

    _sectionHtml(title, body, open = true) {
        const text = String(body || '').trim();
        const meta = this._SECTION_META[title] || { icon: '📝', accent: '#58a6ff' };
        const hex = meta.accent.replace('#', '');
        const r = parseInt(hex.slice(0, 2), 16);
        const g = parseInt(hex.slice(2, 4), 16);
        const b = parseInt(hex.slice(4, 6), 16);
        const style = `--lens-accent:${meta.accent};--lens-accent-bg:rgba(${r},${g},${b},0.12)`;
        return `<details class="agent-lens-section" ${open ? 'open' : ''} style="${style}">
            <summary>
                <span class="agent-lens-section-icon">${meta.icon}</span>
                <span class="agent-lens-section-title">${this._esc(title)}</span>
                <span class="agent-lens-section-meta">${this._wordCount(text)}</span>
                <button type="button" class="agent-lens-copy" onclick="event.preventDefault();agentLens._copyText(this)">Copy</button>
            </summary>
            <div class="agent-lens-section-body">${this._formatBody(text)}</div>
        </details>`;
    }

    _copyText(btn) {
        const body = btn.closest('.agent-lens-section')?.querySelector('.agent-lens-section-body');
        const text = body?.innerText || '';
        navigator.clipboard?.writeText(text.trim()).then(() => toastInfo?.('Copied')).catch(() => {});
    }

    _splitRoomContext(roomContext, { authoring = false } = {}) {
        const text = String(roomContext || '');
        const sections = [];
        let rest = text;

        if (authoring) {
            const envMatch = rest.match(/^([^\n]+ — [^\n]+)\n\n([\s\S]*?)(?=\nItems that catch your attention:|\nPeople here:|\n⚠️|\nFrom where you stand|\n\(no visible exits\)|\n\n=== WITNESSED ===|$)/);
            if (envMatch) {
                sections.push(['Environment', envMatch[1].trim()]);
                if (envMatch[2].trim()) sections.push(['Area description', envMatch[2].trim()]);
                rest = rest.slice(envMatch[0].length);
            } else {
                const descMatch = rest.match(/^([\s\S]*?)(?=\nItems that catch your attention:|\nPeople here:|\n⚠️|\nFrom where you stand|\n\(no visible exits\)|\n\n=== WITNESSED ===|$)/);
                if (descMatch?.[0]?.trim()) {
                    sections.push(['Area description', descMatch[0].trim()]);
                    rest = rest.slice(descMatch[0].length);
                }
            }
        } else {
            const leadMatch = rest.match(/^([\s\S]*?)(?=\nItems that catch your attention:|\nPeople here:|\nFrom where you stand|\n\(no visible exits\)|\n⚠️|$)/);
            if (leadMatch?.[0]?.trim()) {
                sections.push(['Context lead-in', leadMatch[0].trim()]);
                rest = rest.slice(leadMatch[0].length);
            }
        }

        const extract = (label, regex) => {
            const match = rest.match(regex);
            if (match) {
                sections.push([label, match[0].trim()]);
                rest = rest.replace(match[0], '');
            }
        };
        extract('Items', /^Items that catch your attention:[\s\S]*?(?=\nPeople here:|\nYou see no one else here:|\nFrom where you stand|\n\(no visible exits\)|\n⚠️|\nCarrying:|\nYour appearance:|\n=== AVAILABLE ACTIONS ===|\n\n=== WITNESSED ===)/m);
        extract('People', /^People here:[\s\S]*?(?=\nFrom where you stand|\n\(no visible exits\)|\n⚠️|\nCarrying:|\n=== AVAILABLE ACTIONS ===|\n\n=== WITNESSED ===)/m);
        extract('Exits', /^(?:From where you stand|\(no visible exits\))[\s\S]*?(?=\nCarrying:|\nYour appearance:|\nItems that catch your attention:|\nPeople here:|\n=== AVAILABLE ACTIONS ===|\n\n=== WITNESSED ===)/m);
        extract('Witnessed', /^=== WITNESSED ===[\s\S]*/m);
        if (!sections.length) sections.push(['Room context', text.trim()]);
        return sections;
    }

    _areaStats(areaName) {
        const area = worldState.data?.areas?.[areaName];
        if (!area) return null;
        const items = worldState.getItemsInArea(areaName).filter(i => i.properties?.current_state !== 'hidden');
        const people = Object.values(worldState.players || {}).filter(p => p.current_area === areaName).length;
        const lightVal = area.ambient_light ?? area.environment?.light ?? 50;
        const light = PromptBuilder.lightToLevel(Number(lightVal));
        const temp = area.environment?.temperature ?? '—';
        const exits = Object.keys(area.exits || {}).length;
        return { items: items.length, people, light, temp, exits };
    }

    _renderHeader(mode, title, subtitle, charName) {
        const header = document.getElementById('agent-lens-header');
        if (!header) return;
        const color = charName ? this._agentColor(charName) : '#58a6ff';
        const avatarStyle = `background:linear-gradient(135deg, ${color}33 0%, ${color}11 100%);color:${color}`;
        const modePillClass = `agent-lens-mode-pill ${mode}`;
        window.Lit.render(agentLensHtmlTag`
            <div class="agent-lens-header-inner">
                <div class="agent-lens-avatar" style=${avatarStyle}>
                    ${this._modeIcon(mode)}
                </div>
                <div class="agent-lens-header-text">
                    <div class="agent-lens-header-top">
                        <span class=${modePillClass}>${mode}</span>
                        <span class="agent-lens-live"><span class="agent-lens-live-dot"></span>Live</span>
                    </div>
                    <div class="agent-lens-title" title=${title}>${title}</div>
                    <div class="agent-lens-subtitle">${subtitle}</div>
                </div>
            </div>`, header);
    }

    _renderStats(areaName) {
        const el = document.getElementById('agent-lens-stats');
        if (!el) return;
        const stats = areaName ? this._areaStats(areaName) : null;
        if (!stats) {
            el.hidden = true;
            window.Lit.render(agentLensHtmlTag`${''}`, el);
            return;
        }
        el.hidden = false;
        window.Lit.render(agentLensHtmlTag`
            <span class="agent-lens-stat">💡 <strong>${stats.light}</strong></span>
            <span class="agent-lens-stat">🌡 <strong>${stats.temp}°</strong></span>
            <span class="agent-lens-stat">🧍 <strong>${stats.people}</strong> here</span>
            <span class="agent-lens-stat">📦 <strong>${stats.items}</strong> items</span>
            <span class="agent-lens-stat">🚪 <strong>${stats.exits}</strong> exits</span>`, el);
    }

    _renderWayOverrideControls(areaName) {
        const area = worldState.data?.areas?.[areaName];
        if (!area?.exits || !Object.keys(area.exits).length) return window.Lit.nothing;
        const blocks = Object.entries(area.exits).map(([label, exit]) => {
            const wayId = exit.way_id || '';
            const doorNode = wayId ? worldState.getNode(wayId) : null;
            const badges = typeof WayAuthoring !== 'undefined'
                ? WayAuthoring.collectExitBadges(exit, doorNode).filter(b => b.kind !== 'state')
                : [];
            const badgeHtml = badges.length
                ? agentLensHtmlTag`<span style="margin-left:6px;font-size:10px;">${badges.map(b => b.emoji).join(' ')}</span>`
                : window.Lit.nothing;
            const current = this._wayStateOverrides[wayId] || '';
            const actual = exit.state || 'closed';
            const pill = (value, labelText, extraClass) => {
                const active = value === '' ? !current : current === value;
                const pillClass = `agent-lens-pill${active ? ' active' : ''}${extraClass ? ` ${extraClass}` : ''}`;
                return agentLensHtmlTag`<button type="button" class=${pillClass}
                    @click=${() => this.setWayOverride(wayId, value)}>${labelText}</button>`;
            };
            return agentLensHtmlTag`<div class="agent-lens-way-block">
                <div class="agent-lens-way-label">🚪 ${label}${badgeHtml} <span style="color:var(--text-muted);font-weight:400;">→ preview state</span></div>
                <div class="agent-lens-way-pills">
                    ${pill('', `Actual (${actual})`, '')}
                    ${pill('open', 'Open', 'open')}
                    ${pill('closed', 'Closed', 'closed')}
                    ${pill('locked', 'Locked', 'locked')}
                </div>
            </div>`;
        });
        return agentLensHtmlTag`<div class="agent-lens-field">
            <label>Way preview <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--text-muted);">— not saved</span></label>
            ${blocks}
            <button type="button" class="agent-lens-reset" @click=${() => this.clearWayOverrides()}>↺ Reset all way overrides</button>
        </div>`;
    }

    _renderControls(selection, areaName, mode) {
        const controls = document.getElementById('agent-lens-controls');
        if (!controls) return;

        if (!this._viewAs) {
            this._viewAs = worldState.data?.active_player || this._playerNames()[0] || null;
        }
        const names = this._playerNames();
        const areaNames = Object.keys(worldState.data?.areas || {}).sort();

        const fields = [
            agentLensHtmlTag`<div class="agent-lens-field">
                <label>View as character</label>
                <select id="lens-view-as" @change=${(e) => this.setViewAs(e.target.value)}>
                    ${names.map(name => agentLensHtmlTag`<option value=${name} ?selected=${name === this._viewAs}>${name}</option>`)}
                </select>
            </div>`
        ];

        if (mode === 'agent') {
            fields.push(agentLensHtmlTag`<div class="agent-lens-field">
                <label>Hypothetical location</label>
                <select id="lens-hypo-area" @change=${(e) => this.setHypotheticalArea(e.target.value)}>
                    <option value="">📍 Actual — ${areaName || 'unknown'}</option>
                    ${areaNames.map(name => agentLensHtmlTag`<option value=${name} ?selected=${this._hypotheticalArea === name}>${name}</option>`)}
                </select>
            </div>`);
        }

        if (areaName && mode !== 'way') {
            fields.push(this._renderWayOverrideControls(areaName));
        }
        window.Lit.render(agentLensHtmlTag`${fields}`, controls);
    }

    _pipelineHtml(reactive = true) {
        if (!reactive) {
            return `<div class="agent-lens-pipeline">
                <span class="agent-lens-pipe-step">System</span><span class="agent-lens-pipe-arrow">→</span>
                <span class="agent-lens-pipe-step highlight">Think + Act + React</span>
            </div>`;
        }
        return `<div class="agent-lens-pipeline">
            <span class="agent-lens-pipe-step">System</span><span class="agent-lens-pipe-arrow">→</span>
            <span class="agent-lens-pipe-step highlight">Think / Decide</span><span class="agent-lens-pipe-arrow">→</span>
            <span class="agent-lens-pipe-step">Action</span><span class="agent-lens-pipe-arrow">→</span>
            <span class="agent-lens-pipe-step highlight">React</span>
        </div>`;
    }

    /** Turn artifacts from the last agent step (for react prompt preview). */
    _getTurnContext(charName) {
        const charState = events?.getCharacterState?.(charName) || {};
        const lastResult = config.lastActionResult?.[charName] || charState.lastActionResult || '';
        return {
            inner: charState.lastThought || '',
            lastAction: charState.lastAction || '',
            lastSpeech: charState.lastSpeech || '',
            lastResult,
            hasTurnData: !!(charState.lastThought || charState.lastAction || lastResult),
        };
    }

    /** Abbreviated room context used in the react phase (matches agent-engine.js). */
    _buildReactRoomContext(areaName, movedViaDash = false) {
        const tickNum = worldState.data?.time_ticks ?? 0;
        if (movedViaDash) {
            return `[Tick ${tickNum}] You just sprinted and are now in ${areaName} — react to arriving here.`;
        }
        return `[Tick ${tickNum}] You are still in ${areaName}. Your surroundings are unchanged — see your observation above in this conversation.`;
    }

    async _renderAreaLens(areaName, charName, { authoring = false, focusItem = null } = {}) {
        const lensState = this._buildLensState(areaName, charName);
        const player = lensState?.players?.[charName];
        const area = lensState?.areas?.[areaName];
        if (!lensState || !player || !area) {
            return '<div class="agent-lens-empty">Could not build area preview for this location.</div>';
        }

        const roomContext = PromptBuilder.buildRoomContext(lensState, charName, player, area, {
            includePlan: !authoring,
            agentFraming: !authoring,
            preview: true,
        });
        const sections = this._splitRoomContext(roomContext, { authoring });
        let html = '';
        if (focusItem) {
            html += `<div class="agent-lens-focus-item">📦 Lens focus: <strong>${this._esc(focusItem)}</strong> in this area</div>`;
        }
        if (authoring) {
            html += `<div class="agent-lens-authoring-note">Room view for <strong>${this._esc(charName)}</strong> — no tick, personality, or inventory (those appear in Agent lens only).</div>`;
        }
        html += sections.map(([title, body]) =>
            this._sectionHtml(title, body, title === 'Exits' || title === 'Items' || title === 'People' || title === 'Area description')
        ).join('');
        return html;
    }

    async _renderAgentLens(charName, areaName) {
        const lensState = this._buildLensState(areaName, charName);
        const player = lensState?.players?.[charName];
        const area = lensState?.areas?.[areaName];
        if (!lensState || !player || !area) {
            return '<div class="agent-lens-empty">This agent has no current area to preview.</div>';
        }

        const reactive = !!config.reactiveMode;
        const roomContext = PromptBuilder.buildRoomContext(lensState, charName, player, area, { preview: true });
        const roomParts = PromptBuilder.buildRoomContextParts(lensState, charName, player, area, { preview: true });
        const vitalsNL = PromptBuilder.describeVitals?.(player) || '';
        const emotionNL = PromptBuilder.buildEmotionContext(player);
        const relationshipNL = PromptBuilder.buildRelationshipContext(player, charName);
        const memoryNL = await PromptBuilder.buildMemoryContext(charName, { preview: true });
        const turnCtx = this._getTurnContext(charName);
        const lastResult = turnCtx.lastResult;
        const systemPrompt = PromptBuilder.buildCharacterSystemPrompt(charName, player);

        let html = this._pipelineHtml(reactive);
        html += this._sectionHtml('System prompt', systemPrompt, false);
        html += this._sectionHtml('Room context (observe / decide)', roomContext, true);

        const ctxBlock = [
            vitalsNL && `Vitals: ${vitalsNL}`,
            emotionNL && `Emotion: ${emotionNL}`,
            relationshipNL && `Relationships: ${relationshipNL}`,
            memoryNL && `Memory:\n${memoryNL}`,
        ].filter(Boolean).join('\n\n');
        if (ctxBlock) html += this._sectionHtml('Character context', ctxBlock, false);

        if (reactive) {
            const thinkDecidePrompt = PromptBuilder.buildReactionPrompt(
                player, roomParts, vitalsNL, emotionNL, relationshipNL, memoryNL, lastResult
            );
            html += this._sectionHtml('Think / decide prompt', thinkDecidePrompt, true);

            const previewAction = turnCtx.lastAction || 'examine door';
            const previewResult = lastResult
                || 'You examine the door. A heavy oak door with an iron handle. It is currently closed.';
            const previewInner = turnCtx.inner
                || '(Inner monologue from the think/decide response — run an agent step to populate)';
            const previewSpeech = turnCtx.lastSpeech || '';
            const movedViaDash = previewAction.split(/\s+/)[0]?.toLowerCase() === 'dash';
            const reactRoomContext = this._buildReactRoomContext(areaName, movedViaDash);

            const reactPrompt = PromptBuilder.buildResultReactionPrompt(
                charName, player, reactRoomContext,
                vitalsNL, emotionNL, relationshipNL,
                previewInner, previewAction, previewResult,
                memoryNL, previewSpeech
            );

            const reactNote = turnCtx.hasTurnData
                ? '📎 Preview uses this character\'s last turn (action, speech, result).'
                : '📎 Placeholder action/result — run an agent step to populate real turn data.';
            html += this._sectionHtml(
                'React prompt',
                `${reactNote}\n\n${reactPrompt}`,
                true
            );
        } else {
            const combinedPrompt = PromptBuilder.buildReactionPrompt(
                player, roomParts, vitalsNL, emotionNL, relationshipNL, memoryNL, lastResult, true
            );
            html += this._sectionHtml(
                'Combined reaction prompt (think + act + memory in one call)',
                combinedPrompt,
                true
            );
        }

        if (lastResult) {
            html += this._sectionHtml('Last action result (feeds next turn)', lastResult, false);
        }
        return html;
    }

    async _renderWayLens(wayId) {
        const wayNode = worldState.getNode(wayId);
        if (!wayNode) return '<div class="agent-lens-empty">Way not found.</div>';
        const edges = (worldState.graph?.edges || []).filter(edge =>
            edge.target === wayId && edge.type === 'connection'
        );
        const charName = this._viewAs || worldState.data?.active_player;
        if (!charName) return '<div class="agent-lens-empty">Pick a character in Preview settings.</div>';

        let html = '';
        for (const edge of edges) {
            const areaNode = worldState.getNode(edge.source);
            if (!areaNode || areaNode.type !== 'area') continue;
            const areaName = areaNode.name;
            const preview = await this._renderAreaLens(areaName, charName, { authoring: true });
            html += `<div class="agent-lens-area-group">
                <div class="agent-lens-area-group-title">🏠 From ${this._esc(areaName)}</div>
                ${preview}
            </div>`;
        }
        return html || '<div class="agent-lens-empty">No connected areas on this way.</div>';
    }

    _setLoading(loading) {
        const content = document.getElementById('agent-lens-content');
        const btn = document.getElementById('lens-refresh-btn');
        if (content) content.classList.toggle('is-loading', loading);
        if (btn) btn.classList.toggle('is-loading', loading);
    }

    async refresh() {
        if (this._refreshing) return;
        const content = document.getElementById('agent-lens-content');
        if (!content) return;

        const selection = this._currentSelection();
        if (!this._viewAs) {
            this._viewAs = worldState.data?.active_player || this._playerNames()[0] || null;
        }

        // Preview-input signature: skip rebuilds when nothing the preview
        // depends on changed. State polling / re-renders fire state:updated
        // continuously, and rebuilding the identical preview each cycle re-ran
        // the memory pipeline (and, before preview mode, the embedding server).
        const live = worldState.data?.players?.[this._viewAs || ''] || null;
        const areaName = selection ? this._resolveAreaName(selection) : null;
        const areaData = areaName ? worldState.data?.areas?.[areaName] : null;
        const areaItems = areaName ? worldState.getItemsInArea(areaName).map(i => String(i.name) + '|' + String(i.properties?.current_state || '')).join(',') : '';
        const sig = JSON.stringify({
            sel: selection ? [selection.type, selection.type === 'agent' ? selection.name : selection.id] : null,
            viewAs: this._viewAs,
            hypo: this._hypotheticalArea || '',
            ways: this._wayStateOverrides,
            tick: (worldState.data && worldState.data.time_ticks) || 0,
            live: live ? [live.current_area, live.state, JSON.stringify(live.vitals || {}), live.emotion && live.emotion.current] : null,
            area: areaData ? [areaData.description || '', JSON.stringify(areaData.environment || {}), (areaData.exits ? Object.values(areaData.exits).map(e => e.state).join(',') : ''), areaItems] : null,
        });
        if (sig === this._lastSig) return;

        if (!selection) {
            window.Lit.render(agentLensHtmlTag`${''}`, document.getElementById('agent-lens-header'));
            document.getElementById('agent-lens-stats').hidden = true;
            window.Lit.render(agentLensHtmlTag`${''}`, document.getElementById('agent-lens-controls'));
            window.Lit.render(agentLensHtmlTag`
                <div class="agent-lens-welcome">
                    <div class="agent-lens-welcome-icon">👁</div>
                    <h3>Agent Lens</h3>
                    <p>See exactly what an agent gets in their prompt — live, no LLM or embedding calls.</p>
                    <div class="agent-lens-welcome-hints"><span>🏠 Area</span><span>🧍 Agent</span><span>🚪 Way</span></div>
                    <p class="agent-lens-welcome-foot">Click something in the graph to start.</p>
                </div>`, content);
            this._lastPlainText = '';
            this._lastSig = sig;
            return;
        }

        this._refreshing = true;
        this._setLoading(true);
        try {
            let html = '';
            let mode = 'area';
            let areaName = null;
            let charName = this._viewAs;

            if (selection.type === 'agent') {
                mode = 'agent';
                charName = selection.name;
                areaName = this._hypotheticalArea || worldState.players?.[charName]?.current_area;
                this._renderHeader(mode, charName, areaName ? `@ ${areaName}` : 'No location', charName);
                this._renderStats(areaName);
                this._renderControls(selection, areaName, mode);
                html = await this._renderAgentLens(charName, areaName);
            } else if (selection.type === 'node') {
                const node = worldState.getNode(selection.id);
                const focusItem = this._focusItemName(selection);
                if (node?.type === 'way') {
                    mode = 'way';
                    this._renderHeader(mode, node.name || 'Way', 'Connected area viewpoints', charName);
                    this._renderStats(null);
                    this._renderControls(selection, null, mode);
                    html = await this._renderWayLens(selection.id);
                } else if (node?.type === 'item') {
                    mode = 'area';
                    areaName = this._resolveAreaName(selection);
                    this._renderHeader(mode, focusItem || 'Item', areaName ? `in ${areaName}` : 'Unknown area', charName);
                    this._renderStats(areaName);
                    this._renderControls(selection, areaName, mode);
                    html = areaName
                        ? await this._renderAreaLens(areaName, charName, { authoring: true, focusItem })
                        : '<div class="agent-lens-empty">Could not find which area this item is in.</div>';
                } else {
                    areaName = this._resolveAreaName(selection);
                    this._renderHeader(mode, areaName || 'Unknown', `Room preview · ${charName}'s perception`, charName);
                    this._renderStats(areaName);
                    this._renderControls(selection, areaName, mode);
                    html = areaName
                        ? await this._renderAreaLens(areaName, charName, { authoring: true })
                        : '<div class="agent-lens-empty">Select an area, item, way, or agent in the graph.</div>';
                }
            }

            window.Lit.render(agentLensHtmlTag`${html ? window.Lit.unsafeHTML(html) : agentLensHtmlTag`<div class="agent-lens-empty">Nothing to preview yet.</div>`}`, content);
            this._lastPlainText = content.innerText || '';
            this._lastSig = sig;
        } catch (err) {
            window.Lit.render(agentLensHtmlTag`<div class="agent-lens-empty">Something went wrong: ${err.message}</div>`, content);
        } finally {
            this._refreshing = false;
            this._setLoading(false);
        }
    }
}

const agentLens = new AgentLens();
