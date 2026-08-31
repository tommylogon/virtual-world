/**
 * InspectorAgentView — Full agent inspector (showAgent + all agent-related methods)
 * Extracted from inspector.js for modularity.
 * Tabs: Inventory (paperdoll on top + gear below), Bio (personality, appearance,
 * stats/skills/traits, relationships, memories), Advanced (graph physics,
 * behaviors, timeline, save/export).
 */
window.InspectorAgentView = (() => {
    const AV = {};

    // Lazy tag for the PICKERS/OVERLAYS only (trait option, condition editor,
    // timeline detail, add-item/container pickers). The main agent template and
    // its deferred gravity/alias helpers stay as STRINGS via unsafeHTML (the
    // documented HEAD design) — never mix this tag into those string builds.
    const agentViewTag = (strings, ...values) => window.Lit.html(strings, ...values);

    // ─── Internal state ───
    let _activeTab = 'Bio';

    // Deferred renders: agent-view builds one big HTML string, so helpers that
    // return lit TemplateResults (graphGravityControl, renderAliasesSection)
    // get rendered into placeholder containers AFTER the panel render runs.
    let _deferredRenders = [];
    const _deferRender = (renderFn) => {
        _deferredRenders.push(renderFn);
    };
    const _runDeferredRenders = () => {
        const pending = _deferredRenders;
        _deferredRenders = [];
        pending.forEach(renderFn => {
            try { renderFn(); } catch (error) { console.error('[agent-view] deferred render failed:', error); }
        });
    };

    // ─── Constants ───
    const EMOTION_ICONS = { happy: '😊', sad: '😢', angry: '😠', afraid: '😨', surprised: '😲', disgusted: '🤢', neutral: '😐' };
    const STAT_LABELS = { STR: '\u{1F4AA} Strength', DEX: '\u{1F938} Dexterity', CON: '\u{1F6E1}\uFE0F Constitution', INT: '\u{1F9E0} Intelligence', WIS: '\u{1F441}\uFE0F Wisdom', CHA: '\u{1F4AC} Charisma' };
    const SKILL_LIST = ['Athletics', 'Acrobatics', 'Stealth', 'Perception', 'Investigation', 'Survival', 'Persuasion', 'Performance', 'Medicine', 'Arcana', 'Intimidation', 'Lockpicking'];
    const TABS = ['Inventory', 'Bio', 'Advanced'];

    /**
     * HTML-escape double quotes for attribute safety
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    const esc = InspectorHelpers.esc;

    /**
     * Render the full agent inspector panel
     * @param {string} agentName - Character name
     */
    AV.showAgent = function(agentName) {
        const panel = document.getElementById('inspector-panel');
        if (!panel || !worldState.data) return;

        // Set current view on the Inspector singleton so _reRender() works
        if (window.VW?.inspector) {
            window.VW.inspector._currentView = { type: 'agent', name: agentName };
        }
        if (window.appEvents) appEvents.emit('inspector:view', { type: 'agent', name: agentName });

        const player = worldState.players[agentName];
        if (!player) return;

        const color = ui.getAgentColor(agentName);
        const area = worldState.areas?.[player.current_area];
        const charState = events.getCharacterState(agentName);
        const isAuto = events.isAutonomous(agentName);
        const escName = agentName.replace(/'/g, "\\'");
        const characterNode = Object.entries(worldState.graph?.nodes || {})
            .find(([, node]) => node.type === 'character' && node.name === agentName);

        let html = AV._renderAgentHeader(agentName, player, color, characterNode);
        html += AV._renderStatusRow(agentName, player, color, isAuto, escName);
        if (characterNode) {
            html += AV._deferredGravityControl(characterNode[0], characterNode[1].properties || {});
        }
        html += AV._renderEmotionSelector(agentName, player, escName);
        html += AV._renderVitals(player, agentName);

        // Tab navigation
        html += AV._renderTabNav(escName);

        // Inventory tab (paperdoll on top, inventory below)
        html += AV._renderInventoryTab(agentName, player, escName);

        // Bio tab (personality, appearance, stats/skills/traits, relationships, memories)
        html += AV._renderBioTab(agentName, player, charState, area, escName, isAuto, color);

        // Advanced tab (graph physics, behaviors, timeline, save/export)
        html += AV._renderAdvancedTab(agentName, player, charState, escName, isAuto, characterNode);

        // The whole agent view is one big string template with inline onclick
        // handlers. Render it through InspectorPanel (single panel owner) inside
        // an unsafeHTML marker so lit never tries to diff against string content
        // and its part tracking stays intact across re-renders.
        const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
        window.InspectorPanel.render(htmlTag`${window.Lit.unsafeHTML(html)}`);

        // Known-by authoring: who knows THIS character (the Knowledge modal
        // for what they know lives in the Advanced tab).
        if (window.KnownBySection) {
            const panelBody = document.querySelector('#inspector-panel');
            if (panelBody) {
                panelBody.appendChild(window.KnownBySection.build('character', player.name, player.name));
            }
        }

        // Render lit-helper TemplateResults (gravity control, aliases) that
        // couldn't be embedded in the string into their placeholder containers.
        _runDeferredRenders();

        if (window.InspectorTemplateSync && characterNode && characterNode[0]) {
            window.InspectorTemplateSync.populateSelector('character', characterNode[0]);
        }

        // Initialize TagMultiselect for character tags
        const tagContainer = document.getElementById(`tag-multiselect-agent-${escName}`);
        if (tagContainer && typeof TagMultiselect !== 'undefined') {
            new TagMultiselect(tagContainer, {
                tags: Array.isArray(player.tags) ? player.tags : [],
                appliesTo: 'characters',
                allowNew: true,
                placeholder: 'Search or create tags...',
                onChange: (newTags) => {
                    ApiClient.updateCharacter(agentName, { tags: newTags }).then(() => worldState.fetch());
                }
            });
        }

        // Initialize TagMultiselect for interest tags
        const interestTagContainer = document.getElementById(`interest-tag-multiselect-agent-${escName}`);
        if (interestTagContainer && typeof TagMultiselect !== 'undefined') {
            new TagMultiselect(interestTagContainer, {
                tags: Array.isArray(player.interest_tags) ? player.interest_tags : [],
                appliesTo: 'characters',
                allowNew: true,
                placeholder: 'e.g. magic, food, documents...',
                onChange: (newTags) => {
                    ApiClient.updateCharacter(agentName, { interest_tags: newTags }).then(() => worldState.fetch());
                }
            });
        }

        // Initialize Tippy tooltips
        if (typeof tippy !== 'undefined') {
            try {
                // Multi-line tips (vital hover) need pre-line whitespace —
                // tippy renders content as text, so a bare \n collapses.
                if (!document.getElementById('tippy-preline-style')) {
                    const st = document.createElement('style');
                    st.id = 'tippy-preline-style';
                    st.textContent = '[data-tippy-root] .tippy-content { white-space: pre-line; }';
                    document.head.appendChild(st);
                }
                tippy('[data-tippy-content]', { placement: 'top', arrow: true, animation: 'shift-away', duration: [200, 150], maxWidth: 250 });
            } catch (error) {}
        }
        reinitChoices(panel);

        // Relationship slider events
        AV._bindRelationshipSliders(panel, agentName);

        // Populate trait dropdown from library
        AV._populateTraitDropdown(escName);
    };

    /**
     * Render the graph physics gravity control into a placeholder container.
     * graphGravityControl returns a lit TemplateResult (not a string), so it
     * can't be string-concatenated into the agent view HTML. We defer the lit
     * render until after the panel render and inject it into a placeholder div.
     * @param {string} nodeId - Graph node ID
     * @param {object} props - Node properties
     * @returns {string} Placeholder HTML (filled in by _runDeferredRenders)
     */
    AV._deferredGravityControl = function(nodeId, props = {}) {
        const cleanId = String(nodeId ?? 'node').replace(/[^a-zA-Z0-9_-]/g, '_');
        const containerId = `agent-gravity-${cleanId}`;
        _deferRender(() => {
            const container = document.getElementById(containerId);
            if (container && window.Lit) {
                window.Lit.render(window.InspectorHelpers.graphGravityControl(nodeId, props), container);
            }
        });
        return `<div id="${containerId}"></div>`;
    };

    /**
     * Render the aliases section into a placeholder container (lit TemplateResult
     * can't be string-concatenated into the agent view HTML).
     * @param {string} nodeId - Graph node ID
     * @param {Array|string} aliases - Current aliases
     * @returns {string} Placeholder HTML (filled in by _runDeferredRenders)
     */
    AV._deferredAliasesSection = function(nodeId, aliases = []) {
        const cleanId = String(nodeId ?? 'node').replace(/[^a-zA-Z0-9_-]/g, '_');
        const containerId = `agent-aliases-${cleanId}`;
        _deferRender(() => {
            const container = document.getElementById(containerId);
            if (container && window.Lit) {
                window.Lit.render(window.InspectorHelpers.renderAliasesSection(nodeId, aliases), container);
            }
        });
        return `<div id="${containerId}"></div>`;
    };

    AV._populateTraitDropdown = async function(escName) {
        const sel = document.getElementById(`trait-add-select-${escName}`);
        if (!sel) return;
        try {
            // Session cache (60s): the inspector re-renders on every state
            // update and this dropdown is rebuilt each time.
            let traits = window._traitLibrary;
            if (!traits || Date.now() - (window._traitLibraryAt || 0) > 60000) {
                traits = await ApiClient.getLibraryType('traits');
                window._traitLibrary = traits;
                window._traitLibraryAt = Date.now();
            }
            const current = worldState.players?.[escName === escName.replace(/'/g, "\\'") ? escName.replace(/\\'/g, "'") : escName]?.traits || {};
            // Preserve placeholder
            window.Lit.render(agentViewTag`<option value="">➕ Add trait...</option>`, sel);
            for (const [id, def] of Object.entries(traits)) {
                if (current[id] !== undefined) continue;
                const name = def.name || id;
                const cat = def.category || '';
                const opt = document.createElement('option');
                opt.value = id;
                opt.textContent = `${name}${cat ? ` (${cat})` : ''}`;
                sel.appendChild(opt);
            }
        } catch (e) {}
    };

    // ═══════════════════════════════════════════════
    //  Header / Status / Emotion / Vitals helpers
    // ═══════════════════════════════════════════════

    /**
     * Render the agent inspector header (badge, name, close button)
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {string} color - Agent color
     * @param {Array|null} characterNode - [nodeId, node] pair or null
     * @returns {string} HTML
     */
    AV._renderAgentHeader = function(agentName, player, color, characterNode) {
        const tick = worldState.tick;
        const nodeId = characterNode ? characterNode[0] : '';
        const escapedNodeId = nodeId.replace(/'/g, "\\'");
        return `<div class="inspector-header">
            <span class="inspector-type-badge" style="background:${color}">🧍 Agent</span>
            <div style="flex:1;display:flex;flex-direction:column;">
                <h2 style="margin:0;font-size:16px;"><input type="text" value="${agentName}" onchange="ApiClient.updateCharacter('${agentName.replace(/'/g, "\\'")}',{name:this.value}).then(()=>worldState.fetch())" style="font-size:1em;background:transparent;border:1px solid var(--border);color:inherit;width:100%;"></h2>
                ${nodeId ? `<div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                    <div style="display:flex;gap:2px;align-items:center;">
                        <input type="text" value="${escapedNodeId}" onchange="window.InspectorHelpers.renameNode('${escapedNodeId}',this.value)" style="font-size:10px;padding:1px 4px;background:transparent;border:1px solid transparent;color:var(--text-muted);width:100%;cursor:text;" title="Change node ID (lowercase, no spaces)">
                        <button class="btn btn-sm btn-ghost" onclick="InspectorHelpers.syncIdFromName('${escapedNodeId}','${agentName}')" title="Sync ID from name">🔄</button>
                    </div>
                </div>` : ''}
            </div>
            <span style="font-size:10px;color:var(--text-muted);margin-right:6px;">tick ${tick}</span>
            <button class="btn btn-sm btn-ghost" onclick="hideInspectorPanel()">✕</button>
        </div>`;
    };

    /**
     * Render the status row (area selector, state selector, control-mode button)
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {string} color - Agent color
     * @param {boolean} isAuto - Whether autonomous
     * @param {string} escName - HTML-escaped name
     * @returns {string} HTML
     */
    AV._renderStatusRow = function(agentName, player, color, isAuto, escName) {
        const roomOptions = Object.keys(worldState.areas || {}).map(areaName =>
            `<option value="${areaName}" ${player.current_area === areaName ? 'selected' : ''}>${areaName}</option>`
        ).join('');
        // stacked instance (4 vials of poison = 4 cards under `poisoned`).
        const condColors = {
            dead: 'var(--red)', unconscious: '#e65100', paralysed: '#555',
            stunned: '#ab47bc', prone: '#8d6e63', busy: '#9e9d24',
            grappled: '#d50000', restrained: '#b71c1c', exhausted: '#ff6f00',
            sick: '#ff6f00', poisoned: '#00c853', blind: '#37474f', deaf: '#455a64',
            mute: '#546e7a', frightened: '#7b1fa2', charmed: '#f06292', awake: 'var(--green)'
        };
        const conds = (player.conditions && typeof player.conditions === 'object' && !Array.isArray(player.conditions)) ? player.conditions : {};
        // The state badge duplicates the interactive condition chip when the
        // state IS a listed condition (e.g. "grappled") — show the chip only.
        const stateHasChip = Array.isArray(conds[player.state]) && conds[player.state].length > 0;
        const condBadges = Object.entries(conds).map(([cid, instances]) => {
            if (!Array.isArray(instances) || instances.length === 0) return '';
            const color = condColors[cid] || '#888';
            const label = `${cid}${instances.length > 1 ? ' ×' + instances.length : ''}`;
            const cards = instances.map(inst => {
                const bits = [];
                if (inst.source) bits.push(`why: <b>${inst.source}</b>`);
                bits.push(inst.duration ? `left: <b>${inst.duration}t</b>` : '<b>permanent</b>');
                if (inst.level) bits.push(`lvl <b>${inst.level}</b>`);
                if (inst.periodic && Object.keys(inst.periodic).length) {
                    bits.push(`per tick: <b>${Object.entries(inst.periodic).map(([k, v]) => `${k} ${v > 0 ? '+' : ''}${v}`).join(', ')}</b>`);
                }
                if (inst.ends_on && inst.ends_on.length) bits.push(`ends on: <b>${inst.ends_on.join(', ')}</b>`);
                return `<div style="padding:2px 4px;border-left:2px solid ${color};color:var(--text-dim);display:flex;gap:8px;flex-wrap:wrap;font-size:10px;">${bits.join(' ')}</div>`;
            }).join('');
            return `<span style="position:relative;display:inline-block;font-size:9px;padding:1px 5px;border-radius:3px;background:${color}22;color:${color};border:1px solid ${color};cursor:pointer;" onclick="const pop=this.querySelector('.cond-pop'); pop.style.display = pop.style.display==='block'?'none':'block';">${label} ▾<div class="cond-pop" style="display:none;position:absolute;top:100%;left:0;z-index:99;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;padding:4px;min-width:220px;box-shadow:0 4px 12px rgba(0,0,0,0.4);">${cards}<div style="border-top:1px solid var(--border);margin-top:4px;padding-top:3px;"><span style="cursor:pointer;color:var(--red);font-size:10px;" onclick="event.stopPropagation();InspectorAgentView._removeCondition('${escName}','${cid}')">✕ Clear ${cid}</span></div></div></span>`;
        }).join(' ');

        // Control mode: npc | human | llm
        const mode = events.getControlMode(agentName);
        const modeMeta = {
            human: { label: '👤 Human', bg: 'var(--accent)', fg: '#000', bd: 'var(--accent-dim)' },
            llm:   { label: '🤖 LLM',   bg: 'var(--bg-input)', fg: 'var(--text)', bd: 'var(--border)' },
            npc:   { label: '👾 NPC',   bg: 'var(--bg-input)', fg: 'var(--text-muted)', bd: 'var(--border)' }
        }[mode];
        return `<div style="display:flex;align-items:center;gap:8px;padding:6px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);font-size:11px;flex-wrap:wrap;">
            <span>📍</span>
            <select id="player-room" name="area" onchange="ApiClient.updateCharacter('${escName}',{current_area:this.value}).then(()=>worldState.fetch())" style="font-size:10px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:1px 4px;max-width:100px;">
                ${roomOptions}
            </select>
            ${stateHasChip ? '' : `<span title="Most significant condition (derived from conditions)" style="font-size:10px;background:${player.state === 'dead' ? 'var(--red)' : 'var(--accent-dim)'};color:${player.state === 'dead' ? '#fff' : '#000'};border-radius:4px;padding:2px 8px;font-weight:600;border:1px solid var(--border);">${player.state}</span>`}
            ${condBadges}
            <button class="btn btn-sm" onclick="InspectorAgentView._openConditionEditor('${escName}')" title="Add a specific condition (blind, poisoned, unconscious...) with a duration, source, or level" style="font-size:10px;">➕ Add Condition</button>
            <span style="flex:1;"></span>
            <span onclick="events.cycleControlMode('${escName}')" title="Click to cycle control mode: Human → LLM → NPC" style="cursor:pointer;padding:2px 8px;border-radius:4px;font-weight:600;font-size:10px;background:${modeMeta.bg};color:${modeMeta.fg};border:1px solid ${modeMeta.bd};">${modeMeta.label}</span>
        </div>`;
    };

    /**
     * Render the emotion selector row
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {string} escName - HTML-escaped name
     * @returns {string} HTML
     */
    AV._renderEmotionSelector = function(agentName, player, escName) {
        const emotion = player.emotion || { current: 'neutral', intensity: 0 };
        const emotionOptions = Object.keys(EMOTION_ICONS).map(emotionName =>
            `<option value="${emotionName}" ${emotion.current === emotionName ? 'selected' : ''}>${EMOTION_ICONS[emotionName]} ${emotionName}</option>`
        ).join('');

        return `<div style="display:flex;align-items:center;gap:8px;padding:6px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);font-size:11px;flex-wrap:wrap;">
            <span style="font-size:13px;">${EMOTION_ICONS[emotion.current] || '😐'}</span>
            <select id="player-emotion" name="emotion" onchange="ApiClient.updateCharacter('${escName}',{emotion:{current:this.value,intensity:parseFloat(document.getElementById('emotion-intensity-${escName}').value)||0}}).then(()=>worldState.fetch())" style="font-size:10px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:1px 4px;">
                ${emotionOptions}
            </select>
            <span style="font-size:10px;color:var(--text-dim);">intensity</span>
            <input type="range" id="emotion-intensity-${escName}" min="0" max="1" step="0.05" value="${emotion.intensity || 0}" style="width:60px;" oninput="document.getElementById('emotion-val-${escName}').textContent=parseFloat(this.value).toFixed(2);ApiClient.updateCharacter('${escName}',{emotion:{current:'${emotion.current}',intensity:parseFloat(this.value)}}).then(()=>worldState.fetch())">
            <span id="emotion-val-${escName}" style="min-width:30px;font-size:10px;color:var(--text-dim);">${(emotion.intensity || 0).toFixed(2)}</span>
            ${emotion.description ? `<span style="font-size:10px;color:var(--text-muted);font-style:italic;">${emotion.description}</span>` : ''}
        </div>`;
    };

    /**
     * Polarity-aware vital bar color — shared implementation
     * (static/js/shared/vital-color.js, task-337/342).
     */
    function vitalBarColor(vitalName, value) {
        return window.VitalColor.bar({ [vitalName]: value }, vitalName);
    }

    /**
     * Render vitals grouped into Physical and Mental
     * @param {object} player - Player data
     * @returns {string} HTML
     */
    AV._renderVitals = function(player, agentName) {
        const vitals = player.vitals || {};
        const escAgent = (agentName || '').replace(/'/g, "\\'");
        const openModal = (vn) => `openVitalModal('${escAgent}','${vn}')`;

        const renderVital = (vitalName) => {
            if (vitals[vitalName] === undefined) return '';
            const value = vitalName === 'Temperature' ? Math.round(vitals[vitalName]) : vitals[vitalName];
            const max = vitalName === 'HP' ? (vitals.Max_HP || 100) : (vitalName === 'Temperature' ? 45 : (vitalName === 'Mana' ? (vitals.Max_Mana || 100) : 100));
            const percentage = vitalName === 'Temperature'
                ? Math.max(0, Math.min(100, ((vitals[vitalName] - 25) / 20) * 100))
                : Math.max(0, Math.min(100, (value / max) * 100));
            const barColor = vitalBarColor(vitalName, vitals[vitalName]);
            const suffix = vitalName === 'Temperature' ? '°C' : '';
            // Quiet vitals: color is reserved for problems (VitalColor.level),
            // so healthy bars dim back and the troubled one pops.
            const lvl = window.VitalColor?.level?.(vitals, vitalName) || 'ok';
            const quiet = lvl === 'ok' ? 'opacity:0.6;' : '';
            // Full hover: value + what the vital does + human natural language
            // (task-129). VitalThresholds.hoverText falls back to the raw
            // number line when unavailable.
            const tipText = (window.VitalThresholds?.hoverText?.(vitals, vitalName))
                || `${vitalName}: ${value}/${max}${suffix}`;
            return `<div style="flex:1;min-width:60px;text-align:center;cursor:pointer;${quiet}" data-tippy-content="${tipText}" onclick="${openModal(vitalName)}">
                <div style="font-size:9px;text-transform:uppercase;">${vitalName}</div>
                <div style="height:4px;background:var(--bg-input);border-radius:2px;margin:2px 0;overflow:hidden;"><div style="height:100%;width:${percentage}%;background:${barColor};border-radius:2px;"></div></div>
                <div style="font-size:10px;">${value}${suffix}</div>
            </div>`;
        };

        const physicalVitals = ['HP', 'Energy', 'Hunger', 'Thirst', 'Bladder', 'Temperature'];
        const mentalVitals = ['Sanity', 'Social', 'Entertainment', 'Hygiene'];
        const manaGroup = vitals.Mana !== undefined
            ? `<div style="margin-top:4px;padding-top:4px;border-top:1px solid var(--border);">
                <div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;margin-bottom:2px;">Arcane</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${renderVital('Mana')}</div>
              </div>`
            : '';

        return `<div style="padding:8px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);">
            <div style="display:flex;gap:12px;">
                <div style="flex:1;"><div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;margin-bottom:2px;">Physical</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${physicalVitals.map(renderVital).join('')}</div></div>
                <div style="flex:1;"><div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;margin-bottom:2px;">Mental</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${mentalVitals.map(renderVital).join('')}</div></div>
            </div>
            ${manaGroup}
        </div>`;
    };

    // ═══════════════════════════════════════════════
    //  Tab navigation
    // ═══════════════════════════════════════════════

    /**
     * Render tab navigation bar
     * @param {string} escName - HTML-escaped name (unused but kept for consistency)
     * @returns {string} HTML
     */
    AV._renderTabNav = function() {
        return `<div class="inspector-tabs" style="display:flex;border-bottom:2px solid var(--border);background:var(--bg-card);padding:0 8px;gap:2px;">
            ${TABS.map(tabName => `<div class="inspector-tab" data-tab-btn="${tabName}" onclick="InspectorAgentView._switchAgentTab('${tabName}')" style="padding:6px 12px;font-size:11px;cursor:pointer;border-bottom:2px solid ${_activeTab === tabName ? 'var(--accent)' : 'transparent'};color:${_activeTab === tabName ? 'var(--accent)' : 'var(--text-dim)'};font-weight:${_activeTab === tabName ? '600' : '400'};">${tabName}</div>`).join('')}
        </div>`;
    };

    /**
     * Switch active tab and re-render
     * @param {string} tabName - Tab name to switch to
     */
    AV._switchAgentTab = function(tabName) {
        _activeTab = tabName;
        document.querySelectorAll('.inspector-tab').forEach(el => {
            const on = el.dataset.tabBtn === tabName;
            el.style.borderBottomColor = on ? 'var(--accent)' : 'transparent';
            el.style.color = on ? 'var(--accent)' : 'var(--text-dim)';
            el.style.fontWeight = on ? '600' : '400';
        });
        document.querySelectorAll('#inspector-panel [data-tab]').forEach(el => {
            el.style.display = el.dataset.tab === tabName ? '' : 'none';
        });
    };

    // ═══════════════════════════════════════════════
    //  Tab content renderers
    // ═══════════════════════════════════════════════

    /**
     * Render the Stats / Skills / Traits blocks (used inside the Bio tab)
     * @param {object} player - Player data
     * @param {string} escName - HTML-escaped name
     * @returns {string} HTML
     */
    AV._renderStatsBlocks = function(player, escName) {
        let html = '';

        // Stats grid
        const stats = player.stats || {};
        html += `<div class="inspector-section"><h3>\u{1F4CA} Stats</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">`;
        for (const [statKey, statLabel] of Object.entries(STAT_LABELS)) {
            const value = stats[statKey] ?? 10;
            html += `<div style="display:flex;align-items:center;gap:4px;background:var(--bg-inset);border-radius:4px;padding:4px 8px;">
                <span style="font-size:10px;flex:1;">${statLabel}</span>
                <input type="number" min="1" max="20" value="${value}" name="stat-${statKey}" style="width:48px;font-size:11px;text-align:center;"
                    onchange="var s=Object.assign({},worldState.players['${escName}']?.stats||{});s['${statKey}']=parseInt(this.value)||10;ApiClient.updateCharacter('${escName}',{stats:s}).then(()=>worldState.fetch())">
            </div>`;
        }
        html += `</div></div>`;

        // Skills
        const skills = player.skills || {};
        html += `<div class="inspector-section"><h3>\u{1F3AF} Skills</h3>
            <div id="skills-list-${escName}" style="display:flex;flex-direction:column;gap:3px;margin-bottom:6px;">`;
        if (Object.keys(skills).length > 0) {
            for (const [skillName, skillRank] of Object.entries(skills)) {
                html += `<div style="display:flex;align-items:center;gap:4px;background:var(--bg-inset);border-radius:4px;padding:3px 8px;">
                    <span style="font-size:11px;flex:1;">${skillName}</span>
                    <input type="number" min="-20" max="20" value="${skillRank}" name="skill-${skillName}" style="width:48px;font-size:11px;text-align:center;"
                        onchange="var s=Object.assign({},worldState.players['${escName}']?.skills||{});s['${skillName}']=parseInt(this.value)||0;ApiClient.updateCharacter('${escName}',{skills:s}).then(()=>worldState.fetch())">
                    <span onclick="var s=Object.assign({},worldState.players['${escName}']?.skills||{});delete s['${skillName}'];ApiClient.updateCharacter('${escName}',{skills:s}).then(()=>worldState.fetch());VW.inspector._reRender();" style="cursor:pointer;color:var(--red);font-size:12px;padding:2px;">\u2715</span>
                </div>`;
            }
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No skills yet. Add one below.</div>`;
        }
        html += `</div>
            <div style="display:flex;gap:4px;">
                <select id="skill-add-select-${escName}" style="flex:1;font-size:11px;padding:2px 4px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">
                    ${SKILL_LIST.map(skillName => `<option value="${skillName}">${skillName}</option>`).join('')}
                </select>
                <button class="btn btn-sm btn-blue" onclick="var sel=document.getElementById('skill-add-select-${escName}');var skill=sel.value;var s=Object.assign({},worldState.players['${escName}']?.skills||{});if(!s[skill]){s[skill]=1;ApiClient.updateCharacter('${escName}',{skills:s}).then(()=>{worldState.fetch();VW.inspector._reRender();});}" style="font-size:10px;">\u2795 Add</button>
            </div>`;
        html += `</div>`;  // End skills section
        // Traits
        const traits = player.traits || {};
        html += `<div class="inspector-section"><h3>\u{1F9E0} Traits</h3>`;
        const traitKeys = Object.keys(traits);
        if (traitKeys.length > 0) {
            html += `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">`;
            for (const [traitId, traitVal] of Object.entries(traits)) {
                const displayVal = traitVal === true ? '' : `: ${traitVal}`;
                const chipDef = window._traitLibrary?.[traitId] || {};
                const tip = [chipDef.behavior_prompt, chipDef.description,
                             chipDef.conflicts ? 'Conflicts: ' + chipDef.conflicts.join(', ') : '']
                            .filter(Boolean).join(' — ');
                html += `<span title="${tip}" style="display:inline-flex;align-items:center;gap:3px;font-size:10px;padding:2px 8px;border-radius:4px;background:rgba(188,140,255,0.15);color:#bc8cff;border:1px solid rgba(188,140,255,0.3);cursor:help;">
                    ${traitId}${displayVal}
                    <span onclick="var t=Object.assign({},worldState.players['${escName}']?.traits||{});delete t['${traitId}'];ApiClient.updateCharacter('${escName}',{traits:t}).then(()=>{worldState.fetch();VW.inspector._reRender();});" style="cursor:pointer;color:var(--red);margin-left:2px;font-size:12px;">\u2715</span>
                </span>`;
            }
            html += `</div>`;
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">No traits assigned.</div>`;
        }
        html += `<div style="display:flex;gap:4px;">
            <select id="trait-add-select-${escName}" style="flex:1;font-size:11px;padding:2px 4px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">
                <option value="">\u2795 Add trait...</option>
            </select>
            <button class="btn btn-sm btn-blue" onclick="InspectorAgentView._addTrait('${escName}')" style="font-size:10px;">Add</button>
        </div></div>`;

        return html;
    };

    AV._addTrait = async function(charName) {
        const sel = document.getElementById(`trait-add-select-${charName}`);
        if (!sel || !sel.value) return;
        const traitId = sel.value;
        const isParametric = window._traitLibrary?.[traitId]?.params;
        let value = true;
        if (isParametric) {
            const input = prompt(`Enter value for "${traitId}" trait:`, isParametric.default || '');
            if (input === null) return;
            value = input.trim() || true;
        }
        const t = Object.assign({}, worldState.players?.[charName]?.traits || {});
        t[traitId] = value;
        await ApiClient.updateCharacter(charName, { traits: t });
        worldState.fetch();
        VW.inspector._reRender();
    };

    /**
     * Remove a condition instance from a character via the backend.
     * @param {string} charName - Character name
     * @param {string} conditionId - Condition id to clear (e.g. "grappled")
     */
    AV._removeCondition = async function(charName, conditionId) {
        await ApiClient.updateCharacter(charName, { remove_condition: conditionId });
        worldState.fetch();
        if (VW?.inspector) VW.inspector._reRender();
        events.log(`Cleared "${conditionId}" from ${charName}`, 'system-msg');
    };

    // Cached status-condition catalog (from /api/conditions).
    AV._conditionCatalog = null;

    /**
     * Open the condition editor modal for a character, mirroring the trigger
     * editor flow. Lets the user add a specific condition (blind, poisoned,
     * unconscious, paralysed...) with a duration, source, level, ends-on, and
     * optional advanced periodic/override settings.
     * @param {string} charName - Character name
     */
    AV._openConditionEditor = async function(charName) {
        if (!AV._conditionCatalog) {
            try {
                const res = await ApiClient.conditionsCatalog();
                AV._conditionCatalog = (res && res.conditions) || [];
            } catch (err) {
                AV._conditionCatalog = [];
            }
        }
        const catalog = AV._conditionCatalog;

        const esc = (s) => String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

        const grouped = (defs) => {
            const groups = { blocking: [], other: [] };
            (defs || []).forEach(c => (c.blocks_actions ? groups.blocking : groups.other).push(c));
            const opt = (label, list) => list.length
                ? `<optgroup label="${label}">${list.map(c => `<option value="${esc(c.value)}">${esc(c.label)}</option>`).join('')}</optgroup>`
                : '';
            return opt('🔒 Blocking', groups.blocking) + opt('✨ Other', groups.other);
        };

        const defMap = {};
        (catalog || []).forEach(c => { defMap[c.value] = c; });

        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
        overlay.className = 'modal-overlay';
        window.Lit.render(agentViewTag`
            <div class="modal-window" style="width:480px;max-width:94vw;max-height:90vh;display:flex;flex-direction:column;">
                <div class="modal-head">
                    <h3 style="margin:0;font-size:14px;">🩸 Add Condition — ${charName}</h3>
                </div>
                <div style="padding:12px 16px;overflow:auto;font-size:12px;color:var(--text);">
                    <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Condition</label>
                    <select id="ce-condition" style="width:100%;">${window.Lit.unsafeHTML(grouped(catalog))}</select>
                    <div id="ce-desc" style="margin:4px 0 10px;font-size:11px;color:var(--text-muted);font-style:italic;">Select a condition to see its description.</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                        <div>
                            <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Duration (ticks)</label>
                            <input id="ce-duration" type="number" min="1" style="width:100%;" placeholder="permanent">
                            <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">Leave blank for permanent.</div>
                        </div>
                        <div>
                            <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Level</label>
                            <input id="ce-level" type="number" min="1" style="width:100%;" placeholder="—">
                            <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">e.g. exhausted 1–6.</div>
                        </div>
                    </div>
                    <div style="margin-top:8px;">
                        <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Source (optional)</label>
                        <input id="ce-source" type="text" style="width:100%;" placeholder="e.g. spider bite, betrayal, the curse">
                    </div>
                    <div style="margin-top:8px;">
                        <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Ends on (optional, comma-separated)</label>
                        <input id="ce-ends-on" type="text" style="width:100%;" placeholder="e.g. stand, duration, wake">
                    </div>
                    <details style="margin-top:8px;">
                        <summary style="cursor:pointer;font-size:11px;color:var(--accent);">Advanced (periodic / overrides)</summary>
                        <div style="margin-top:6px;">
                            <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Periodic (JSON)</label>
                            <textarea id="ce-periodic" rows="2" style="width:100%;font-family:monospace;font-size:11px;" placeholder='{"hp": -2, "Energy": -1}'></textarea>
                        </div>
                        <div style="margin-top:6px;">
                            <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Overrides (JSON)</label>
                            <textarea id="ce-overrides" rows="2" style="width:100%;font-family:monospace;font-size:11px;" placeholder='{"blocks_speech": true, "drops_held_items": true}'></textarea>
                        </div>
                    </details>
                </div>
                <div style="padding:12px 16px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end;">
                    <button class="btn btn-sm btn-ghost" id="ce-cancel">Cancel</button>
                    <button class="btn btn-sm btn-blue" id="ce-add">➕ Add</button>
                </div>
            </div>`, overlay);

        document.body.appendChild(overlay);
        const overlayCloser = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.addEventListener('click', overlayCloser);
        overlay.querySelector('#ce-cancel').onclick = () => overlay.remove();
        overlay.querySelector('#ce-add').onclick = () => {
            const condition = overlay.querySelector('#ce-condition').value;
            if (!condition) { events.log('Pick a condition first.', 'error-msg'); return; }
            const def = defMap[condition];
            const durationRaw = overlay.querySelector('#ce-duration').value;
            const duration = durationRaw === '' ? null : parseInt(durationRaw, 10);
            const levelRaw = overlay.querySelector('#ce-level').value;
            const level = levelRaw === '' ? null : parseInt(levelRaw, 10);
            const source = overlay.querySelector('#ce-source').value.trim() || null;
            const endsOnRaw = overlay.querySelector('#ce-ends-on').value.trim();
            const endsOn = endsOnRaw ? endsOnRaw.split(',').map(s => s.trim()).filter(Boolean) : null;
            const parseJson = (el, field) => {
                const raw = el.value.trim();
                if (!raw) return null;
                try { return JSON.parse(raw); }
                catch (err) { events.log(`Invalid ${field} JSON — not adding.`, 'error-msg'); throw err; }
            };
            let periodic, overrides;
            try {
                periodic = parseJson(overlay.querySelector('#ce-periodic'), 'periodic');
                overrides = parseJson(overlay.querySelector('#ce-overrides'), 'overrides');
            } catch (err) { return; }

            const payload = { condition };
            if (duration !== null) payload.duration = duration;
            if (level !== null) payload.level = level;
            if (source) payload.source = source;
            if (endsOn) payload.ends_on = endsOn;
            if (periodic) payload.periodic = periodic;
            if (overrides) payload.overrides = overrides;
            overlay.remove();
            AV._applyCondition(charName, payload, def);
        };

        overlay.querySelector('#ce-condition').addEventListener('change', function () {
            const def = defMap[this.value];
            const desc = overlay.querySelector('#ce-desc');
            const duration = overlay.querySelector('#ce-duration');
            if (def) {
                desc.textContent = def.description || 'No description on file.';
                if (def.default_duration) {
                    duration.placeholder = `default ${def.default_duration}`;
                    if (!duration.value) duration.value = def.default_duration;
                } else {
                    duration.placeholder = 'permanent';
                }
            } else {
                desc.textContent = 'Select a condition to see its description.';
            }
        });
        const first = overlay.querySelector('#ce-condition');
        if (first.options.length > 1) first.selectedIndex = 0;
        first.dispatchEvent(new Event('change'));
    };

    /**
     * Apply a configured condition to a character via the backend.
     * @param {string} charName - Character name
     * @param {Object} payload - { condition, duration?, source?, level?, periodic?, ends_on?, overrides? }
     * @param {Object} [def] - Catalog entry for logging the label
     */
    AV._applyCondition = async function(charName, payload, def) {
        try {
            await ApiClient.updateCharacter(charName, { add_condition: payload });
            const label = (def && def.label) || payload.condition;
            const durText = payload.duration ? ` for ${payload.duration}t` : '';
            events.log(`Added "${label}" to ${charName}${durText}`, 'system-msg');
        } catch (err) {
            events.log(`Failed to add condition: ${err.message}`, 'error-msg');
        }
        worldState.fetch();
        if (VW?.inspector) VW.inspector._reRender();
    };

    /**
     * Render the Bio tab content (personality, appearance, relationships, thoughts, memories, behaviors)
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {object} charState - Character state from events
     * @param {object} area - Area data
     * @param {string} escName - HTML-escaped name
     * @param {boolean} isAuto - Whether autonomous
     * @param {string} color - Agent color
     * @returns {string} HTML
     */
    AV._renderBioTab = function(agentName, player, charState, area, escName, isAuto, color) {
        const showTab = (tabName) => _activeTab === tabName ? '' : 'display:none;';
        const firstImpression = AV._computeFirstImpression(player);
        let html = `<div data-tab="Bio" style="${showTab('Bio')}">`;

        // Stats / Skills / Traits
        html += AV._renderStatsBlocks(player, escName);

        // Personality
        html += `<div class="inspector-section">
            <h3>🧬 Personality</h3>
            <div style="display:flex;gap:4px;margin-bottom:4px;">
                <input type="text" id="inspector-ai-prompt" placeholder="AI: e.g. 'a cowardly thief'" style="flex:1;font-size:11px;">
                <button class="btn btn-sm btn-purple" onclick="InspectorAgentView._generatePersonality('${escName}')" style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">🤖</button>
            </div>
            <div class="field"><textarea id="inspector-personality" rows="3" style="font-size:11px;">${player.personality}</textarea></div>
            <button class="btn btn-sm btn-green" onclick="InspectorAgentView._savePersonality('${escName}')">💾 Save</button>
        </div>`;

        // Appearance
        html += `<div class="inspector-section">
            <h3>👤 Appearance</h3>
            <div class="field"><label style="font-size:10px;color:var(--text-muted);">Base Description (naked/baseline look)</label>
                <textarea id="inspector-base-description" rows="2" style="font-size:11px;margin-bottom:4px;">${player.base_description || ''}</textarea></div>
            <div class="field"><label style="font-size:10px;color:var(--text-muted);">Current Description (derived from base + equipment, or manual override)</label>
                <textarea id="inspector-description" rows="3" style="font-size:11px;" oninput="InspectorAgentView._updateFirstImpression('${escName}')">${player.description || ''}</textarea></div>
            <div style="background:var(--bg-inset);border:1px dashed var(--border);border-radius:4px;padding:4px 6px;font-size:10px;color:var(--text-muted);margin-bottom:4px;">
                <span style="font-weight:600;">First impression:</span> <span id="inspector-first-impression">${firstImpression}</span>
            </div>
            <button class="btn btn-sm btn-green" onclick="InspectorAgentView._saveDescription('${escName}')">💾 Save Appearance</button>
            <button class="btn btn-sm" onclick="InspectorAgentView._generateDescription('${escName}')">🤖 Generate from Equipment</button>
        </div>`;

        // Relationships
        if (area) {
            const allOtherPlayers = Object.entries(worldState.players || {}).filter(([name]) => name !== agentName);
            const hasUnrelated = allOtherPlayers.some(([name]) => !player.relationships?.[name]);
            html += `<div class="inspector-section">
                <h3 style="display:flex;justify-content:space-between;align-items:center;">
                    <span>🤝 Relationships</span>
                    ${hasUnrelated ? `<select id="rel-add-select-${escName.replace(/\s+/g,'_')}" style="font-size:10px;max-width:120px;">
                        <option value="">+ Add...</option>
                        ${allOtherPlayers.filter(([name]) => !player.relationships?.[name]).map(([name]) => `<option value="${name}">${name}</option>`).join('')}
                    </select>` : ''}
                </h3>`;
            for (const [otherName] of allOtherPlayers) {
                const relationship = player.relationships?.[otherName];
                if (!relationship) continue;
                const closeness = relationship.closeness ?? 0;
                const relColor = closeness > 0 ? (closeness > 50 ? '#3fb950' : '#e3b341') : (closeness < 0 ? (closeness < -50 ? '#f85149' : '#d47766') : 'var(--text-muted)');
                const closenessDesc = closeness <= -75 ? 'mortal enemy' : closeness <= -50 ? 'enemy' : closeness <= -25 ? 'rival' : closeness < 0 ? 'unfriendly' : closeness === 0 ? 'neutral' : closeness <= 25 ? 'acquaintance' : closeness <= 50 ? 'friend' : closeness <= 75 ? 'close friend' : 'inseparable';
                html += `<div class="relationship-item-inspector" data-other="${otherName}">
                    <span style="min-width:70px;font-size:11px;font-weight:500;">${otherName}</span>
                    <input type="range" min="-100" max="100" value="${closeness}" class="rel-slider" data-agent="${agentName}" data-other="${otherName}" style="flex:1;height:4px;accent-color:${relColor};">
                    <span style="font-size:10px;color:var(--text-muted);min-width:28px;text-align:right;" class="rel-val">${closeness}</span>
                    <span style="font-size:9px;color:var(--text-dim);min-width:70px;" class="rel-label">${closenessDesc}</span>
                    <label title="Tick if you know their name (first_sighting=false)" style="display:flex;align-items:center;gap:2px;font-size:9px;color:var(--text-dim);cursor:pointer;">
                        <input type="checkbox" class="rel-known" data-agent="${agentName}" data-other="${otherName}" ${relationship.first_sighting ? '' : 'checked'}> name
                    </label>
                    <span onclick="InspectorAgentView._removeRelationship('${agentName}','${otherName}')" style="cursor:pointer;color:var(--red);font-size:12px;padding:0 2px;" title="Remove relationship">✕</span>
                </div>`;
            }
            if (allOtherPlayers.every(([name]) => player.relationships?.[name])) {
                html += `<div style="font-size:10px;color:var(--text-muted);padding:4px 0;">All players have a relationship entry.</div>`;
            }
            html += `</div>`;
        }

        // Tags
        const tags = player.tags || [];
        html += `<div class="inspector-section"><h3>🏷️ Tags</h3>
            <div id="tag-multiselect-agent-${escName}"></div>
        </div>`;

        // Aliases — subjective names others use to target this character
        const agentNodeId = `player_${agentName.replace(/\s+/g, '_')}`;
        const agentNode = worldState.getNode(agentNodeId);
        html += AV._deferredAliasesSection(agentNodeId, agentNode?.properties?.aliases || []);

        // Interest tags — what this character pays attention to in a room
        html += `<div class="inspector-section"><h3>✨ Interest Tags</h3>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">Items matching these surface in the agent's prompt. Examine/take removes them from attention.</div>
            <div id="interest-tag-multiselect-agent-${escName}"></div>
        </div>`;

        // What they see
        html += `<div class="inspector-section"><h3>👁️ What I See</h3>
            <div style="font-size:12px;padding:8px 12px;background:var(--bg-inset);border-radius:6px;border-left:3px solid ${color};">`;
        if (area) {
            html += `<div>${area.description || ''}</div>`;
            const items = area.items?.map(item => item.name).filter(Boolean).join(', ');
            if (items) html += `<div style="margin-top:4px;color:var(--text-dim);font-size:11px;">Items: ${items}</div>`;
            const others = Object.entries(worldState.players || {}).filter(([name, p]) => name !== agentName && p.current_area === player.current_area);
            if (others.length) html += `<div style="margin-top:4px;color:var(--pink);font-size:11px;">Also: ${others.map(([name]) => name).join(', ')}</div>`;
        } else {
            html += `<span style="color:var(--text-muted);">Unknown location</span>`;
        }
        html += `</div></div>`;

        // Latest Thoughts
        html += `<div class="inspector-section"><h3>💭 Latest Thoughts</h3>
            <div class="decision-trace"><div class="trace-thought">${charState.lastThought || 'No recent thoughts.'}</div>
            ${charState.lastSpeech ? `<div style="color:var(--pink);font-style:italic;margin-top:4px;">💬 "${charState.lastSpeech}"</div>` : ''}
            ${charState.lastAction ? `<div style="color:var(--accent);font-weight:500;margin-top:4px;">⚡ ${charState.lastAction}</div>` : ''}
            ${charState.lastActionResult ? `<div style="color:var(--orange);font-size:10px;margin-top:4px;">→ ${charState.lastActionResult}</div>` : ''}
        </div></div>`;

        // Plan
        const plan = agent?._plans?.[agentName];
        if (plan && plan.length > 0) {
            html += `<div class="inspector-section"><h3>📋 Plan</h3>
                <ol style="margin:0;padding-left:20px;font-size:11px;line-height:1.7;">`;
            for (const step of plan) {
                html += `<li>${step}</li>`;
            }
            html += `</ol></div>`;
        }

        // Memories (delegated)
        html += window.InspectorMemory.renderMemoriesHtml(agentName, player, escName, esc);

        html += `</div>`;  // End Bio tab
        return html;
    };

    /**
     * Render the Inventory tab content
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {string} escName - HTML-escaped name
     * @returns {string} HTML
     */
    AV._renderInventoryTab = function(agentName, player, escName) {
        const showTab = (tabName) => _activeTab === tabName ? '' : 'display:none;';
        let html = `<div data-tab="Inventory" style="${showTab('Inventory')}">`;

        // Paperdoll / equipment on top
        html += window.InspectorPaperdoll.renderPaperdollEquipmentHtml(agentName, player, esc, escName);

        const inventory = worldState.getInventory(agentName);
        const equipped = player.equipped || {};
        const equippedItems = new Set();
        for (const stack of Object.values(equipped)) {
            for (const item of stack) {
                if (item && !String(item).startsWith('__')) equippedItems.add(item);
            }
        }
        const carried = inventory.filter(itemName => !equippedItems.has(worldState.getNodeByIdentifier(itemName)?.id || itemName));

        const allGraphItems = Object.values(worldState.graph?.nodes || {}).filter(n => n.type === 'item');
        const containersInInv = carried.filter(name => {
            const node = worldState.getNodeByIdentifier(name);
            const tags = node?.properties?.tags || [];
            return Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container');
        });

        html += `<div class="inspector-section"><h3>🎒 Inventory <span class="section-hint">(${carried.length} carried${inventory.length > carried.length ? `, ${inventory.length - carried.length} worn` : ''}${containersInInv.length ? `, ${containersInInv.length} container` : ''})</span></h3>
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:4px;">`;
        if (carried.length > 0) {
            carried.forEach(itemName => {
                const itemNode = worldState.getNodeByIdentifier(itemName);
                const itemId = itemNode?.id || itemName;
                const weight = itemNode?.properties?.weight || '';
                const slots = itemNode?.properties?.equip_slots || [];
                const tags = itemNode?.properties?.tags || [];
                const isContainer = Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container');
                const isEquippable = slots.length > 0;
                const borderStyle = isContainer ? 'border:2px solid #d29922;' : '';
                const icon = isContainer ? '📦' : '📦';
                const containerOpenBtn = isContainer ? `<button class="btn btn-sm" onclick="event.stopPropagation();VW.inspector.showNode('${itemId.replace(/'/g, "\\'")}')" style="font-size:8px;padding:1px 4px;" title="Open Container">📂</button>` : '';
                html += `<div style="background:var(--bg-inset);border-radius:4px;padding:4px 6px;text-align:center;cursor:pointer;${borderStyle}position:relative;" onclick="VW.inspector.showNode('${itemId.replace(/'/g, "\\'")}')" oncontextmenu="InspectorPaperdoll.showInventoryContextMenu(event,'${escName}','${itemName.replace(/'/g, "\\'")}','${itemId.replace(/'/g, "\\'")}')" data-tippy-content="${itemNode?.properties?.description || itemName}">
                    <div style="font-size:16px;">${icon}</div>
                    <div style="font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;${isContainer ? 'font-weight:bold;color:#d29922;' : ''}">${itemName}</div>
                    ${weight ? `<div style="font-size:8px;color:var(--text-dim);">${weight} kg</div>` : ''}
                    <div style="display:flex;gap:2px;justify-content:center;margin-top:2px;">
                        ${isEquippable ? `<button class="btn btn-sm" onclick="event.stopPropagation();runAction('wear ${itemName}', '${escName}')" style="font-size:8px;padding:1px 4px;" title="Equip">🎽</button>` : ''}
                        ${!isContainer ? `<button class="btn btn-sm" onclick="event.stopPropagation();InspectorAgentView._showContainerPicker('${escName}','${itemName.replace(/'/g, "\\'")}','${itemId.replace(/'/g, "\\'")}')" style="font-size:8px;padding:1px 4px;" title="Put in container">📥</button>` : ''}
                        ${containerOpenBtn}
                        <button class="btn btn-sm btn-red" onclick="event.stopPropagation();runAction('drop ${itemName}', '${escName}')" style="font-size:8px;padding:1px 4px;" title="Drop">✕</button>
                    </div>
                </div>`;
            });
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);padding:8px;grid-column:1/-1;text-align:center;">Nothing carried.</div>`;
        }
        html += `</div>`;

        // Container contents section — show what's inside containers inline
        const containerCandidates = [];
        for (const itemName of inventory) {
            const itemNode = worldState.getNodeByIdentifier(itemName);
            if (!itemNode) continue;
            const tags = itemNode?.properties?.tags || [];
            if (Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container'))
                containerCandidates.push(itemNode);
        }
        for (const stack of Object.values(equipped)) {
            for (const itemId of stack) {
                if (!itemId || String(itemId).startsWith('__')) continue;
                const itemNode = worldState.getNodeByIdentifier(itemId);
                if (!itemNode) continue;
                const tags = itemNode?.properties?.tags || [];
                if (Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container'))
                    if (!containerCandidates.some(existing => existing.id === itemNode.id))
                        containerCandidates.push(itemNode);
            }
        }
        const edges = worldState.graph?.edges || [];
        for (const containerNode of containerCandidates) {
            const contents = edges
                .filter(edge => edge.type === 'in' && edge.target === containerNode.id)
                .map(edge => ({ id: edge.source, node: worldState.getNode(edge.source) }))
                .filter(entry => entry.node);
            if (contents.length === 0) continue;
            html += `<div class="inspector-section" style="margin-top:4px;"><h3>📦 ${containerNode.name} <span class="section-hint">(${contents.length} item${contents.length !== 1 ? 's' : ''})</span></h3>
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:4px;">`;
            contents.forEach(({ id: contentId, node: contentNode }) => {
                const safeContentId = contentId.replace(/'/g, "\\'");
                const contentName = contentNode.name;
                html += `<div style="background:var(--bg-inset);border-radius:4px;padding:4px 6px;text-align:center;cursor:pointer;border:1px solid var(--border);position:relative;" onclick="VW.inspector.showNode('${safeContentId}')" data-tippy-content="${contentNode?.properties?.description || contentName}">
                    <div style="font-size:16px;">📦</div>
                    <div style="font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${contentName}</div>
                    <div style="display:flex;gap:2px;justify-content:center;margin-top:2px;">
                        <button class="btn btn-sm btn-red" onclick="event.stopPropagation();runAction('take ${contentName}', '${escName}')" style="font-size:8px;padding:1px 4px;" title="Take from container">✕</button>
                    </div>
                </div>`;
            });
            html += `</div></div>`;
        }

        html += `
            <button class="btn btn-sm btn-blue" onclick="InspectorAgentView._showAddItemPicker('${escName}')" style="margin-top:4px;width:100%;font-size:10px;">+ Add Item to Inventory</button></div></div>`;  // End Inventory tab
        return html;
    };

    /**
     * Render the Advanced tab content (graph physics, behaviors, timeline, conversation memory, save/export, nudge, manual command)
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {object} charState - Character state from events
     * @param {string} escName - HTML-escaped name
     * @param {boolean} isAuto - Whether autonomous
     * @param {Array|null} characterNode - [nodeId, node] pair or null
     * @returns {string} HTML
     */
    AV._renderAdvancedTab = function(agentName, player, charState, escName, isAuto, characterNode) {
        const showTab = (tabName) => _activeTab === tabName ? '' : 'display:none;';
        let html = `<div data-tab="Advanced" style="${showTab('Advanced')}">`;

        if (characterNode) {
            html += window.InspectorHelpers.renderImageSection(characterNode[0], characterNode[1].properties || {});
            html += AV._deferredGravityControl(characterNode[0], characterNode[1].properties || {});
        }

        // Behaviors
        if (player.simple_npc && Array.isArray(player.behaviors)) {
            html += `<div class="inspector-section">
                <h3 style="display:flex;justify-content:space-between;align-items:center;">🤖 Behaviors <span style="color:var(--text-dim);font-size:10px;">(${player.behaviors.length})</span>
                    <button class="btn btn-sm" onclick="InspectorBehaviors.openGraphEditor('${escName}')" style="font-size:10px;" title="Open all behaviors in the graph editor">🧩 Graph</button>
                </h3>
                <div style="max-height:300px;overflow-y:auto;">`;
            player.behaviors.forEach((behavior, behaviorIndex) => {
                const trigger = behavior.trigger || '?';
                const conditionText = behavior.conditions ? JSON.stringify(behavior.conditions) : 'none';
                const actionText = behavior.actions ? behavior.actions.map(action => action.type).join(', ') : 'none';
                html += `<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:6px;margin-bottom:4px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong>${esc(trigger)}</strong>
                        <div>
                            <button class="btn btn-sm" onclick="InspectorBehaviors.editBehavior('${escName}',${behaviorIndex})" style="font-size:10px;">✏️</button>
                            <button class="btn btn-sm btn-red" onclick="InspectorBehaviors.deleteBehavior('${escName}',${behaviorIndex})" style="font-size:10px;">🗑</button>
                        </div>
                    </div>
                    <div style="font-size:10px;color:var(--text-dim);margin-top:2px;">Conditions: ${esc(conditionText)}</div>
                    <div style="font-size:10px;color:var(--text-dim);">Actions: ${esc(actionText)}</div>
                </div>`;
            });
            html += `</div>
                <button class="btn btn-sm btn-green" onclick="InspectorBehaviors.addBehavior('${escName}')" style="margin-top:4px;width:100%;">+ Add Behavior</button>
            </div>`;
        }

        // Knowledge (what this character knows from the start — authored
        // `known` registry). Chips are lit-free DOM, filled by deferred render.
        const kbChipId = String(agentName ?? '').replace(/[^a-zA-Z0-9_-]/g, '_');
        html += `<div class="inspector-section">
            <h3 style="display:flex;justify-content:space-between;align-items:center;">🧠 Knowledge
                <button class="btn btn-sm btn-blue" onclick="KnownBySection.openKnowledgeModal('${escName}')" style="font-size:10px;" title="Select every runtime entity this character knows, grouped by category">🎛 Manage</button>
            </h3>
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:6px;">Known from the start — hidden ways/items visible, people never masked, known areas reveal hidden exits.</div>
            <div id="knowledge-chips-${kbChipId}"></div>
        </div>`;
        _deferRender(() => {
            const container = document.getElementById('knowledge-chips-' + kbChipId);
            if (container && window.KnownBySection) {
                container.textContent = '';
                container.appendChild(window.KnownBySection.buildKnownChips(agentName));
            }
        });

        // Timeline
        const timeline = charState.detailedTimeline || [];
        html += `<div class="inspector-section"><h3>📜 Timeline <span class="section-hint">(click to expand)</span></h3>
            <div class="timeline-viewer" id="timeline-${escName}">`;
        if (timeline.length > 0) {
            const startIdx = Math.max(0, timeline.length - 50);
            for (let entryIndex = startIdx; entryIndex < timeline.length; entryIndex++) {
                const entry = timeline[entryIndex];
                const phase = entry.phase || 'unknown';
                const phaseIcons = { think: '💭', decide: '🎯', act: '⚡', action: '⚡', result: '→', react: '🔄', speech: '💬', observe: '👁️' };
                const phaseIcon = phaseIcons[phase] || '•';
                const phaseLabel = phase.charAt(0).toUpperCase() + phase.slice(1);

                let contentText = '';
                if (entry.thought) contentText = entry.thought;
                else if (entry.speech) contentText = `"${entry.speech}"`;
                else if (entry.action) contentText = entry.action;
                else if (entry.result) contentText = entry.result;
                else if (entry.message) contentText = entry.message;
                else contentText = phase;

                html += `<div class="timeline-entry" onclick="InspectorAgentView._showTimelineDetail('${escName}', ${entryIndex}, this)">
                    <div class="timeline-entry-header">
                        <span class="timeline-tick">[${events.tickToTime(entry.tick || 0)}]</span>
                        <span class="timeline-phase-badge timeline-phase-${phase}">${phaseIcon} ${phaseLabel}</span>
                    </div>
                    <div class="timeline-entry-content">${contentText}</div>
                </div>`;
            }
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);padding:8px;">No timeline entries yet. The timeline captures every thought, decision, action, result, and reaction as the character experiences them.</div>`;
        }
        html += `</div>
            <div id="timeline-detail-${escName}" style="display:none;"></div>
        </div>`;

        // Conversation Memory
        const chatHistory = agent.getDisplayHistory(agentName);
        html += `<div class="memory-section"><h3>🧠 Conversation Memory (${chatHistory.length} exchanges)</h3>
            <div style="max-height:300px;overflow-y:auto;font-size:11px;">`;
        if (chatHistory.length > 0) {
            for (let msgIndex = 0; msgIndex < chatHistory.length; msgIndex++) {
                const msg = chatHistory[msgIndex];
                const role = msg.role || 'unknown';
                const content = (msg.content || '');
                const roleLabel = role === 'user' ? '👤 Prompt' : '🤖 Response';
                const roleColor = role === 'user' ? 'var(--accent)' : 'var(--purple)';
                html += `<div style="padding:6px 8px;border-bottom:1px solid var(--border-light);">
                    <div style="font-size:9px;color:${roleColor};font-weight:600;margin-bottom:2px;">${roleLabel} #${msgIndex + 1}</div>
                    <div style="color:var(--text-dim);font-size:10px;max-height:40px;overflow:hidden;">${content}${content.length > 250 ? '...' : ''}</div>
                </div>`;
            }
        } else {
            html += `<div class="memory-empty">This character has no conversation history yet. History builds as the agent takes actions.</div>`;
        }
        html += `</div></div>`;

        // Save / Import to World
        html += `<div class="inspector-section" style="border-top:1px solid var(--border);padding-top:12px;">
            <h3>💾 Library</h3>
            <div style="display:flex;gap:4px;">
                <button class="btn btn-sm btn-green" onclick="InspectorAgentView._saveCharacter('${escName}')">💾 Save to Library</button>
                <button class="btn btn-sm btn-purple" onclick="InspectorAgentView._importCharacter()" style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;" title="Load a character JSON file into the world (no library entry needed)">📤 Import JSON → World</button>
            </div>
            <div style="display:flex;gap:4px;margin-top:6px;">
                <button class="btn btn-sm" style="background:#5a1a1a;border-color:#8a2a2a;color:#ff6b6b;" onclick="InspectorAgentView._killCharacter('${escName}')">💀 Kill</button>
                <button class="btn btn-sm" style="background:#3a1a1a;border-color:#6a2a2a;color:#ff4444;" onclick="InspectorAgentView._removeCharacter('${escName}')">🗑️ Remove</button>
            </div>
        </div>`;

        // Library template row (same pattern as item/way/area inspectors)
        if (characterNode && characterNode[0] && window.InspectorTemplateSync) {
            html += `<div class="inspector-section" style="border-top:1px solid var(--border);padding-top:12px;">
                <h3>📚 Library Template</h3>
                <div style="display:flex;gap:6px;flex-wrap:wrap;">
                    ${window.InspectorTemplateSync.renderTemplateRow('character', characterNode[0], characterNode[1].properties || {})}
                </div>
            </div>`;
        }

        // Nudge
        html += `<div class="inspector-section" style="border-top:1px solid var(--border);padding-top:12px;">
            <h3>🎯 Nudge</h3>
            <div style="display:flex;gap:4px;">
                <input type="text" id="nudge-input" placeholder="Inject a thought for ${agentName}..." style="flex:1;font-size:11px;">
                <button class="btn btn-sm btn-green" onclick="agent.nudge('${escName}', document.getElementById('nudge-input')?.value); document.getElementById('nudge-input').value='';">Send</button>
            </div>
        </div>`;

        // Manual Command
        if (!isAuto) {
            html += `<div class="inspector-section" style="border-top:1px solid var(--border);padding-top:12px;">
                <h3>✋ Manual Command</h3>
                <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">Type a command for ${agentName} to execute.</div>
                <div style="display:flex;gap:4px;">
                    <input type="text" id="manual-cmd-input" placeholder="e.g. go north, take key, speak hello..." style="flex:1;font-size:11px;" onkeypress="if(event.key==='Enter') InspectorAgentView._sendManualCommand('${escName}')">
                    <button class="btn btn-sm btn-green" onclick="InspectorAgentView._sendManualCommand('${escName}')">Send</button>
                </div>
            </div>`;
        }

        html += `</div>`;  // End Advanced tab
        return html;
    };

    // ═══════════════════════════════════════════════
    //  Helper event bindings
    // ═══════════════════════════════════════════════

    /**
     * Bind relationship slider and dropdown events after rendering
     * @param {HTMLElement} panel - The inspector panel element
     * @param {string} agentName - Character name
     */
    AV._bindRelationshipSliders = function(panel, agentName) {
        panel.querySelectorAll('.rel-slider').forEach(slider => {
            slider.addEventListener('input', function() {
                const value = this.value;
                const row = this.closest('.relationship-item-inspector');
                if (row) {
                    const label = row.querySelector('.rel-label');
                    const valueSpan = row.querySelector('.rel-val');
                    if (valueSpan) valueSpan.textContent = value;
                    const numericValue = parseInt(value);
                    let description = 'mortal enemy';
                    if (numericValue <= -75) description = 'mortal enemy';
                    else if (numericValue <= -50) description = 'enemy';
                    else if (numericValue <= -25) description = 'rival';
                    else if (numericValue < 0) description = 'unfriendly';
                    else if (numericValue === 0) description = 'neutral';
                    else if (numericValue <= 25) description = 'acquaintance';
                    else if (numericValue <= 50) description = 'friend';
                    else if (numericValue <= 75) description = 'close friend';
                    else description = 'inseparable';
                    if (label) label.textContent = description;
                }
            });
            slider.addEventListener('change', function() {
                const agent = this.dataset.agent;
                const other = this.dataset.other;
                const value = parseInt(this.value);
                const existing = worldState.players?.[agent]?.relationships?.[other] || {};
                ApiClient.updateCharacter(agent, {
                    relationships: { [other]: { closeness: value, last_interaction_tick: worldState.data?.time_ticks || 0, interaction_count: existing.interaction_count || 0, first_sighting: existing.first_sighting ?? false } }
                }).then(() => {});
            });
        });

        // "knows their name" toggle -> sets first_sighting (false = knows).
        panel.querySelectorAll('.rel-known').forEach(cb => {
            cb.addEventListener('change', function() {
                const agent = this.dataset.agent;
                const other = this.dataset.other;
                const knowsName = this.checked;
                const existing = worldState.players?.[agent]?.relationships?.[other] || {};
                ApiClient.updateCharacter(agent, {
                    relationships: { [other]: { closeness: existing.closeness || 0, last_interaction_tick: worldState.data?.time_ticks || 0, interaction_count: existing.interaction_count || 0, first_sighting: !knowsName } }
                }).then(() => worldState.fetch());
            });
        });

        const addSelect = document.getElementById('rel-add-select-' + agentName.replace(/\s+/g, '_'));
        if (addSelect) {
            addSelect.addEventListener('change', function() {
                const other = this.value;
                if (!other) return;
                this.value = '';
                ApiClient.updateCharacter(agentName, {
                    relationships: { [other]: { closeness: 0, last_interaction_tick: worldState.data?.time_ticks || 0, interaction_count: 0, first_sighting: false } }
                }).then(() => worldState.fetch().then(() => {
                    if (window.VW?.inspector) window.VW.inspector.showAgent(agentName);
                }));
            });
        }
    };

    // ═══════════════════════════════════════════════
    //  Agent action methods
    // ═══════════════════════════════════════════════

    /**
     * Send a manual command for this character via the API
     * @param {string} charName - Character name
     */
    AV._sendManualCommand = function(charName) {
        const input = document.getElementById('manual-cmd-input');
        const command = (input?.value || '').trim();
        if (!command) return;
        if (input) input.value = '';
        events.log(`📝 Manual command for ${charName}: ${command}`, 'system-msg');
        runAction(command, charName);
    };

    /**
     * Generate personality via AI
     * @param {string} charName - Character name
     */
    AV._generatePersonality = async function(charName) {
        const input = document.getElementById('inspector-ai-prompt');
        const prompt = (input?.value || '').trim();
        if (!prompt) { input?.focus(); return; }
        if (!config.apiKey || !config.model) { toastInfo('Configure API key and model in Settings first.'); return; }

        input.disabled = true;
        input.value = 'Generating...';

        const system = 'You are a character designer. Generate a personality based on the prompt. Respond with ONLY raw JSON:\n{"personality":"Detailed character personality, fears, motivations, quirks."}';

        try {
            const resp = await llmClient.chat([
                { role: 'system', content: system },
                { role: 'user', content: prompt }
            ], { temperature: 0.9 });
            if (!resp) { toastError('No response from LLM.'); return; }

            let cleaned = resp.trim();
            const jsonMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
            if (jsonMatch) cleaned = jsonMatch[1].trim();
            else { const firstBrace = cleaned.indexOf('{'), lastBrace = cleaned.lastIndexOf('}'); if (firstBrace !== -1 && lastBrace > firstBrace) cleaned = cleaned.substring(firstBrace, lastBrace + 1); }
            const parsed = JSON.parse(cleaned);

            const personalityText = parsed.personality || parsed.description || 'A mysterious character.';
            const textarea = document.getElementById('inspector-personality');
            if (textarea) textarea.value = personalityText;
            await ApiClient.updateCharacter(charName, { personality: personalityText });
            events.log(`AI generated personality for ${charName}`, 'system-msg');
        } catch (error) {
            console.error(error);
            toastError('AI generation failed: ' + error.message);
        } finally {
            input.disabled = false;
            input.value = '';
            input.placeholder = 'AI: e.g. \'a cowardly thief\'';
        }
    };

    /**
     * Save personality from the inspector textarea
     * @param {string} charName - Character name
     */
    AV._savePersonality = function(charName) {
        return window.InspectorHelpers.savePersonality(charName);
    };

    /**
     * Generate description via AI (server-side LLM or client-side fallback)
     * @param {string} charName - Character name
     */
    AV._generateDescription = async function(charName) {
        const player = worldState.players[charName];
        if (!player) return;
        if (!AIGenerator.isConfigured()) return;

        const base = player.base_description || '';
        const equipped = player.equipped || {};

        const equipLines = [];
        for (const [slotName, items] of Object.entries(equipped)) {
            if (items && items.length > 0) {
                const realItems = items.filter(item => item && !String(item).startsWith('__'));
                if (realItems.length === 0) continue;
                const resolved = realItems.map(id => {
                    const node = worldState.getNodeByIdentifier(id);
                    if (!node) return id;
                    const desc = node.properties?.description || '';
                    return desc ? `${node.name} (${desc})` : node.name;
                });
                equipLines.push(`${slotName}: ${resolved.join(' worn under ')}`);
            }
        }
        const equipText = equipLines.length > 0 ? equipLines.join('\n') : 'Nothing worn.';

        const prompt = `Describe this character's appearance as a narrator would — vivid, natural, and specific.\n\n`
            + `CHARACTER BASELINE\n${base || '(no base description)'}\n\n`
            + `CURRENT ATTIRE\n${equipText}\n\n`
            + `Writing Directives\n`
            + `Open with a single striking sentence about their face, hair, or a defining physical feature — this is the first thing a stranger would notice. Do not lead with clothing.\n`
            + `Weave the clothing into the description naturally. Mention how each piece fits, drapes, or contrasts with their skin. Use the item descriptions as texture and detail — not as a checklist.\n`
            + `If they are nude, describe their body, posture, and how they carry themselves without flinching.\n`
            + `2-4 sentences total. No bullet points. No backstory. No personality. No internal thoughts. Only what can be seen.`;

        const textarea = document.getElementById('inspector-description');
        if (textarea) textarea.value = 'Generating...';

        try {
            const response = await llmClient.chat([
                { role: 'user', content: prompt }
            ], { temperature: 0.7 });

            if (response && response.trim()) {
                if (textarea) textarea.value = response.trim();
                await AV._saveDescription(charName);
                return;
            }
        } catch (e) {
            // fall through to fallback
        }

        // Fallback: merge base_description + equipment client-side
        const slots = [];
        for (const [slotName, items] of Object.entries(equipped)) {
            if (items && items.length > 0) {
                const realItems = items.filter(item => item && !String(item).startsWith('__'));
                if (realItems.length > 0) slots.push(`${slotName}: ${realItems.join(' > ')}`);
            }
        }
        let description = base;
        if (slots.length > 0) {
            description += (description ? '\n\n' : '') + 'Wearing: ' + slots.join('; ') + '.';
        }
        if (textarea) {
            textarea.value = description || 'Nothing equipped.';
            await AV._saveDescription(charName);
        }
    };

    /**
     * Compute the "first impression" label a stranger sees at a glance:
     * the tag-derived handle (the man / the woman / a girl ...) plus the
     * first sentence of the description. Mirrors prompt-builder's anonymousName.
     * @param {object} player - Player data object
     * @returns {string} First impression text
     */
    AV._computeFirstImpression = function(player) {
        if (!player) return '';
        const tagMap = {
            female: 'the woman', male: 'the man', woman: 'the woman', man: 'the man',
            girl: 'a girl', boy: 'a boy', child: 'a child', animal: 'an animal'
        };
        let handle = '';
        for (const tag of (player.tags || [])) {
            const mapped = tagMap[String(tag).toLowerCase()];
            if (mapped) { handle = mapped; break; }
        }
        const desc = (player.description || player.base_description || '').trim();
        const firstSentence = desc.split('.')[0].trim() + (desc.includes('.') ? '.' : '');
        const parts = [];
        if (handle) parts.push(handle);
        if (firstSentence && firstSentence !== handle) parts.push(firstSentence);
        if (parts.length === 0) parts.push('the stranger');
        return parts.join(' — ');
    };

    /**
     * Live-update the first impression preview as the description is typed.
     * @param {string} charName - Character name
     */
    AV._updateFirstImpression = function(charName) {
        const player = Object.assign({}, worldState.players[charName]);
        const ta = document.getElementById('inspector-description');
        if (ta) player.description = ta.value;
        const preview = document.getElementById('inspector-first-impression');
        if (preview) preview.textContent = AV._computeFirstImpression(player);
    };

    /**
     * Save description and base description from inspector textareas
     * @param {string} charName - Character name
     */
    AV._saveDescription = function(charName) {
        return window.InspectorHelpers.saveDescription(charName);
    };

    /**
     * Build the canonical character library payload from live world state.
     * This is the single source of truth for saving to the library AND for
     * exporting — both must produce the same shape so exports round-trip
     * back into the library without data loss.
     *
     * `inventory` is stored as structured entries `{name, library_id, node_id}`
     * so imports can re-link items from the library (or rebuild them) instead
     * of guessing from a bare name.
     * @param {string} charName - Character name
     * @returns {object} Character card in library format
     */
    AV._buildCharacterCard = function(charName) {
        const player = worldState.players[charName];
        if (!player) return null;
        const charNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        const inventory = [];
        const seen = new Set();
        for (const edge of worldState.graph?.edges || []) {
            if (edge.target !== charNodeId) continue;
            if (edge.type !== 'carrying' && edge.type !== 'equipped') continue;
            if (seen.has(edge.source)) continue;
            seen.add(edge.source);
            const node = worldState.getNode(edge.source);
            if (!node || node.type !== 'item') continue;
            inventory.push({
                name: node.name,
                node_id: edge.source,
                library_id: node.properties?.library_id || null,
                properties: node.properties || {},
            });
        }
        return {
            name: charName,
            personality: player.personality || '',
            description: player.description || '',
            base_description: player.base_description || '',
            unknown_name: player.unknown_name || '',
            stats: player.stats || {},
            vitals: player.vitals || {},
            decay_rates: player.decay_rates || {},
            skills: player.skills || {},
            traits: player.traits || {},
            tags: player.tags || [],
            interest_tags: player.interest_tags || [],
            state: player.state || 'awake',
            conditions: player.conditions || {},
            equipped: (() => {
                const eq = {};
                for (const [slot, stack] of Object.entries(player.equipped || {})) {
                    eq[slot] = (Array.isArray(stack) ? stack : []).map(id => {
                        const n = worldState.getNode(id);
                        return { name: n?.name || id, node_id: id, library_id: n?.properties?.library_id || null, properties: n?.properties || {} };
                    });
                }
                return eq;
            })(),
            activity: player.activity || null,
            current_area: player.current_area,
            inventory,
            emotion: player.emotion && typeof player.emotion === 'object'
                ? player.emotion
                : { current: player.emotion || 'neutral', intensity: 0 },
            memories: player.memories || [],
            relationships: player.relationships || {},
            behaviors: player.behaviors || [],
            npc_behavior: player.npc_behavior || 'wander',
            npc_action_interval: player.npc_action_interval ?? 3,
            npc_state: player.npc_state || 'idle',
            simple_npc: player.simple_npc || false,
            recent_hearing: player.recent_hearing || [],
        };
    };

    /**
     * Save character to registry
     * @param {string} charName - Character name
     */
    AV._saveCharacter = async function(charName) {
        const charCard = AV._buildCharacterCard(charName);
        if (!charCard) return;

        try {
            await ApiClient.saveCharacterToRegistry(charName, charCard);
            events.log(`Character "${charName}" saved to registry!`, 'system-msg');
        } catch (error) {
            // Fallback: retry via the same unified endpoint
            await ApiClient.saveCharacterToRegistry(charName, charCard);
            events.log(`Character "${charName}" saved!`, 'system-msg');
        }
        // Sync description to runtime
        const descTextarea = document.getElementById('inspector-description');
        if (descTextarea && descTextarea.value !== (player.description || '')) {
            await ApiClient.updateCharacter(charName, { description: descTextarea.value });
        }
    };

    /**
     * Import character from JSON file — loads arbitrary JSON into the WORLD as
     * an active player (not the library). Distinct from "Add from Library":
     * no library entry required; sets active player and inventory edges.
     */
    AV._importCharacter = async function() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.style.display = 'none';
        document.body.appendChild(input);
        input.onchange = async () => {
            document.body.removeChild(input);
            const file = input.files?.[0];
            if (!file) return;
            try {
                const text = await file.text();
                const data = JSON.parse(text);
                if (!data.name) { events.log('Invalid character file: missing name.', 'error-msg'); return; }
                const res = await ApiClient.importPlayer(data);
                if (res.error) { events.log(`Import failed: ${res.error}`, 'error-msg'); return; }
                events.log(`Character "${data.name}" imported!`, 'system-msg');
                await worldState.fetch();
                AV.showAgent(data.name);
            } catch (error) {
                events.log(`Import error: ${error.message}`, 'error-msg');
            }
        };
        input.click();
    };

    /**
     * Kill a character
     * @param {string} charName - Character name
     */
    AV._killCharacter = async function(charName) {
        if (!confirm(`Kill "${charName}"? This will set HP to 0 and state to dead.`)) return;
        const res = await ApiClient.killCharacter(charName);
        if (res.error) { events.log(`Kill failed: ${res.error}`, 'error-msg'); return; }
        events.log(`"${charName}" has been killed.`, 'system-msg');
        await worldState.fetch();
        if (window.VW?.inspector) window.VW.inspector.showAgent(charName);
    };

    /**
     * Permanently remove a character from the world
     * @param {string} charName - Character name
     */
    AV._removeCharacter = async function(charName) {
        if (!confirm(`Permanently remove "${charName}" from the world? This cannot be undone.`)) return;
        const res = await ApiClient.deleteCharacter(charName);
        if (res.error) {
            // Not a registered player (e.g. a bare character node) — fall back
            // to deleting the graph node itself so the node can always be removed.
            const nodeId = `player_${charName.replace(/\s+/g, '_')}`;
            const fallback = await ApiClient.deleteNode(nodeId);
            if (fallback.error) {
                events.log(`Remove failed: ${res.error}`, 'error-msg');
                return;
            }
            events.log(`"${charName}" removed (bare graph node, no player state).`, 'system-msg');
            await worldState.fetch();
            if (window.VW?.inspector) window.VW.inspector.hide();
            return;
        }
        events.log(`"${charName}" has been removed from the world.`, 'system-msg');
        await worldState.fetch();
        if (window.VW?.inspector) window.VW.inspector.hide();
    };

    /**
     * Show expanded detail for a timeline entry
     * @param {string} charName - Character name
     * @param {number} entryIndex - Index of the timeline entry
     * @param {HTMLElement} entryEl - The clicked timeline entry element
     */
    AV._showTimelineDetail = function(charName, entryIndex, entryEl) {
        const charState = events.getCharacterState(charName);
        const timeline = charState.detailedTimeline || [];
        if (entryIndex < 0 || entryIndex >= timeline.length) return;
        const entry = timeline[entryIndex];

        const detailContainer = document.getElementById(`timeline-detail-${charName.replace(/'/g, "\\'")}`);
        if (!detailContainer) return;

        // Toggle: if already showing this entry, hide it
        if (detailContainer.style.display !== 'none' && detailContainer.dataset.index === String(entryIndex)) {
            detailContainer.style.display = 'none';
            document.querySelectorAll('.timeline-entry.active').forEach(el => el.classList.remove('active'));
            return;
        }

        // Show active state on the clicked entry
        document.querySelectorAll('.timeline-entry.active').forEach(el => el.classList.remove('active'));
        if (entryEl) entryEl.classList.add('active');

        const phaseIcons = { think: '💭', decide: '🎯', act: '⚡', action: '⚡', result: '→', react: '🔄', speech: '💬', observe: '👁️' };
        const phase = entry.phase || 'unknown';
        const phaseIcon = phaseIcons[phase] || '•';

        const detailRows = [];
        detailRows.push(agentViewTag`<div class="timeline-detail-row">
            <span class="timeline-detail-label">Phase</span>
            <span class="timeline-detail-value">${phaseIcon} ${phase} (${events.tickToTime(entry.tick || 0)})</span>
        </div>`);

        if (entry.thought) {
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">💭 Thought</span>
                    <span class="timeline-detail-value" style="font-style:italic;color:var(--purple);">${entry.thought}</span>
                </div>`);
        }

        if (entry.speech) {
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">💬 Said</span>
                    <span class="timeline-detail-value" style="color:var(--pink);">"${entry.speech}"</span>
                </div>`);
        }

        if (entry.action) {
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">⚡ Action</span>
                    <span class="timeline-detail-value" style="color:var(--accent);font-weight:500;font-family:var(--font-mono);">${entry.action}</span>
                </div>`);
        }

        if (entry.result) {
            const isError = entry.result.toLowerCase().includes('valueerror') || entry.result.toLowerCase().includes("don't");
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">→ Result</span>
                    <span class="timeline-detail-value" style="color:${isError ? 'var(--red)' : 'var(--orange)'};">${entry.result}</span>
                </div>`);
        }

        if (entry.message) {
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">📝 Message</span>
                    <span class="timeline-detail-value">${entry.message}</span>
                </div>`);
        }

        window.Lit.render(agentViewTag`<div class="timeline-detail">${detailRows}</div>`, detailContainer);
        detailContainer.style.display = 'block';
        detailContainer.dataset.index = String(entryIndex);
    };

    /**
     * Remove a relationship between two characters
     * @param {string} agentName - Character name
     * @param {string} otherName - Other character name
     */
    AV._removeRelationship = async function(agentName, otherName) {
        if (!agentName || !otherName) return;
        await ApiClient.updateCharacter(agentName, { relationships: { [otherName]: null } });
        worldState.fetch().then(() => {
            if (window.VW?.inspector) window.VW.inspector.showAgent(agentName);
        });
    };

    /**
     * Show a modal to pick an item to add to inventory
     * @param {string} charName - Character name
     */
    AV._showAddItemPicker = async function(charName) {
        const allItems = worldState.getInventory(charName);
        const playerNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        const currentArea = worldState.players[charName]?.current_area || '';

        const graphNodes = Object.entries(worldState.graph?.nodes || {})
            .filter(([id, node]) => node.type === 'item')
            .filter(([id]) => !allItems.includes(id));

        const libraryData = await ApiClient.getLibraryItems().catch(() => ({}));
        const graphNames = new Set(graphNodes.map(([, n]) => n.name.toLowerCase()));
        const libraryNodes = Object.entries(libraryData)
            .filter(([id, item]) => !allItems.includes(id) && !allItems.includes(item.name))
            .filter(([id, item]) => !graphNames.has((item.name || id).toLowerCase()));

        function getItemTags(source, item, node) {
            const raw = source === 'graph' ? node?.properties?.tags : item?.tags || item?.properties?.tags;
            if (Array.isArray(raw)) return raw.map(t => String(t).toLowerCase()).join(',');
            if (typeof raw === 'string') return raw.toLowerCase();
            return '';
        }

        function renderItem(id, name, source, tagsStr) {
            const lower = name.toLowerCase();
            const isLib = source === 'library';
            const badge = isLib ? agentViewTag`<span style="font-size:9px;color:var(--text-muted);margin-left:4px;">(library)</span>` : '';
            return agentViewTag`<div data-name=${lower} data-tags=${tagsStr} style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid var(--border);">
                <span style="font-size:11px;">📦 ${name}${badge}</span>
                <button class="btn btn-sm btn-blue" @click=${(e) => {
                    e.currentTarget.closest('.modal-overlay').remove();
                    if (isLib) {
                        ApiClient.placeItemFromLibrary({ type: 'character', id: playerNodeId }, id).then(() => worldState.fetch());
                    } else {
                        fetch(`/api/graph/item/${id}/move`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ area: currentArea }) })
                            .then(r => r.json())
                            .then(() => runAction(`take ${name}`, charName));
                    }
                }}>Add</button>
            </div>`;
        }

        const allNodes = [
            ...graphNodes.map(([id, node]) => renderItem(id, node.name, 'graph', getItemTags('graph', null, node))),
            ...libraryNodes.map(([id, item]) => renderItem(id, item.name || id, 'library', getItemTags('library', item)))
        ];

        const picker = document.createElement('div');
        picker.className = 'modal-overlay';
        picker.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        window.Lit.render(agentViewTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:350px;max-height:80vh;overflow-y:auto;">
            <h3 style="margin:0 0 12px 0;">Add Item to Inventory</h3>
            <input type="text" id="add-item-filter" placeholder="Search items or tags..." style="width:100%;font-size:11px;padding:4px;margin-bottom:8px;" @input=${(e) => {
                const t = e.target.value.toLowerCase();
                e.target.nextElementSibling.querySelectorAll('[data-name]').forEach(el => el.style.display = (el.getAttribute('data-name').includes(t) || (el.getAttribute('data-tags') || '').includes(t)) ? 'flex' : 'none');
            }}>
            <div style="max-height:50vh;overflow-y:auto;">
                ${allNodes}
            </div>
            <button class="btn btn-sm" @click=${(e) => e.currentTarget.closest('.modal-overlay').remove()} style="margin-top:8px;width:100%;">Cancel</button>
        </div>`, picker);
        document.body.appendChild(picker);
        setTimeout(() => document.getElementById('add-item-filter')?.focus(), 100);
    };

    AV._showContainerPicker = function(charName, itemName, itemId) {
        const inventory = worldState.getInventory(charName);
        const player = worldState.players[charName];
        const equipped = player?.equipped || {};
        const equippedContainers = Object.values(equipped)
            .flat()
            .filter(id => id && !String(id).startsWith('__'))
            .map(id => worldState.getNodeByIdentifier(id))
            .filter(node => node && node.type === 'item');
        const allContainers = [...inventory, ...equippedContainers.map(node => node.name)];
        const uniqueContainers = [...new Set(allContainers)];
        const containers = uniqueContainers.filter(name => {
            const node = worldState.getNodeByIdentifier(name);
            const tags = node?.properties?.tags || [];
            return Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container');
        });

        const items = containers.length
            ? containers.map(name => agentViewTag`<div data-name="${name.toLowerCase()}" style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid var(--border);">
                <span style="font-size:11px;">📦 ${name}</span>
                <button class="btn btn-sm btn-blue" @click=${(e) => { e.currentTarget.closest('.modal-overlay').remove(); runAction(`put ${itemName} in ${name}`, charName); }}>Put in</button>
            </div>`)
            : [agentViewTag`<div style="font-size:11px;color:var(--text-muted);padding:8px;">No containers in inventory.</div>`];

        const picker = document.createElement('div');
        picker.className = 'modal-overlay';
        picker.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        window.Lit.render(agentViewTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:350px;max-height:80vh;overflow-y:auto;">
            <h3 style="margin:0 0 12px 0;">Put ${itemName} in...</h3>
            <div style="max-height:50vh;overflow-y:auto;">
                ${items}
            </div>
            <button class="btn btn-sm" @click=${(e) => e.currentTarget.closest('.modal-overlay').remove()} style="margin-top:8px;width:100%;">Cancel</button>
        </div>`, picker);
        document.body.appendChild(picker);
    };

    // Register the template-sync pattern for characters. The diff only covers
    // author-editable fields — never runtime state (vitals, current_area,
    // memories, relationships, emotion, inventory, conditions, equipped).
    if (window.InspectorTemplateSync) {
        window.InspectorTemplateSync.register('character', {
            title: 'Refresh Character from Library',
            buildWorldPayload(nodeId, node) {
                const name = (node && node.name) || '';
                const player = worldState.players[name];
                if (!player) return null;
                return {
                    name,
                    personality: player.personality || '',
                    description: player.description || '',
                    base_description: player.base_description || '',
                    unknown_name: player.unknown_name || '',
                    stats: player.stats || {},
                    skills: player.skills || {},
                    traits: player.traits || {},
                    tags: player.tags || [],
                    interest_tags: player.interest_tags || [],
                    behaviors: player.behaviors || [],
                    npc_behavior: player.npc_behavior || 'wander',
                    npc_action_interval: player.npc_action_interval ?? 3,
                    npc_state: player.npc_state || 'idle',
                    simple_npc: player.simple_npc || false,
                    memories: player.memories || [],
                    relationships: player.relationships || {},
                    vitals: player.vitals || {},
                    decay_rates: player.decay_rates || {},
                    conditions: player.conditions || {},
                    equipped: player.equipped || {},
                    recent_hearing: player.recent_hearing || [],
                    activity: player.activity || null,
                    current_area: player.current_area || '',
                    emotion: (player.emotion && typeof player.emotion === 'object')
                        ? player.emotion
                        : { current: player.emotion || 'neutral', intensity: player.emotion_intensity || 0 },
                };
            },
            sections: [
                { key: 'personality', label: 'Personality' },
                { key: 'description', label: 'Description' },
                { key: 'base_description', label: 'Base Description' },
                { key: 'unknown_name', label: 'Unknown Name' },
                { key: 'stats', label: 'Stats' },
                { key: 'skills', label: 'Skills' },
                { key: 'traits', label: 'Traits' },
                { key: 'tags', label: 'Tags' },
                { key: 'interest_tags', label: 'Interest Tags' },
                { key: 'behaviors', label: 'Behaviours' },
                { key: 'npc_behavior', label: 'NPC Config' },
                { key: 'memories', label: 'Memories', perEntry: true },
                { key: 'relationships', label: 'Relationships', perEntry: true },
                { key: 'vitals', label: 'Vitals', perEntry: true },
                { key: 'decay_rates', label: 'Decay Rates', perEntry: true },
                { key: 'conditions', label: 'Conditions', perEntry: true },
                { key: 'equipped', label: 'Equipped', perEntry: true },
                { key: 'recent_hearing', label: 'Recent Hearing' },
                { key: 'activity', label: 'Activity' },
                { key: 'current_area', label: 'Current Area' },
                { key: 'emotion', label: 'Emotion' },
            ],
        });
    }

    return AV;
})();
