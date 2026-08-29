/**
 * InspectorItemView — Item inspector (showItem, improveItem, actions, parameters, move, tags)
 * Extracted from inspector.js for modularity.
 * task-216: renders lit-html TemplateResults through InspectorPanel (single panel owner).
 */
window.InspectorItemView = (() => {
    const IV = {};

    // Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

    // ─── Constants ───
    const ALL_ACTIONS = ['examine', 'take', 'use', 'open', 'close', 'eat', 'drink', 'read', 'light',
        'activate', 'equip', 'unequip', 'throw', 'break', 'drop'
    ];

    // Actions that imply their inverse — toggling one also toggles the other.
    const INVERSE_ACTIONS = {
        'take': 'drop', 'drop': 'take',
        'equip': 'unequip', 'unequip': 'equip',
    };

    const DAMAGE_TYPES = ['slashing', 'piercing', 'bludgeoning', 'fire', 'cold', 'toxic', 'magic', 'electric', 'radiant', 'necrotic', 'psychic', 'acid'];
    const SKILL_OPTIONS = ['Athletics', 'Acrobatics', 'Stealth', 'Perception', 'Investigation',
        'Survival', 'Persuasion', 'Performance', 'Medicine', 'Arcana', 'Intimidation', 'Lockpicking'
    ];

    const ACTION_COLORS = {
        'examine': '#58a6ff', 'take': '#3fb950', 'use': '#e3b341',
        'open': '#4ec9b0', 'close': '#f85149', 'eat': '#f0883e',
        'drink': '#58a6ff', 'read': '#bc8cff', 'light': '#e3b341',
        'activate': '#3fb950', 'equip': '#4ec9b0', 'unequip': '#f85149',
        'throw': '#f0883e', 'break': '#f85149'
    };

    const ACTION_ICONS = {
        'examine': '🔍', 'take': '✋', 'use': '⚡',
        'open': '🚪', 'close': '🚫', 'eat': '🍽️',
        'drink': '🥤', 'read': '📖', 'light': '🔥',
        'activate': '🔛', 'equip': '⚔️', 'unequip': '📦',
        'throw': '💨', 'break': '💥'
    };

    const ITEM_STATE_OPTIONS = ['normal', 'hidden', 'lit', 'unlit', 'open', 'closed', 'locked', 'broken', 'charged', 'depleted'];
    const EQUIP_SLOT_OPTIONS = ['head', 'neck', 'torso', 'arms', 'hands', 'legs', 'feet', 'back', 'waist', 'accessory', 'hand_left', 'hand_right'];

    /**
     * Get color for an action type
     * @param {string} action - Action name
     * @returns {string} CSS color value
     */
    const actionColor = (action) => ACTION_COLORS[action] || '#8b949e';

    /**
     * Get icon for an action type
     * @param {string} action - Action name
     * @returns {string} Icon emoji
     */
    const actionIcon = (action) => ACTION_ICONS[action] || '•';

    // ═══════════════════════════════════════════════
    //  Main showItem
    // ═══════════════════════════════════════════════

    /**
     * Render the full item inspector panel
     * @param {string} nodeId - Graph node ID
     * @param {object} graphNode - Graph node data
     */
    IV.showItem = function(nodeId, graphNode) {
        const name = graphNode.name;
        const props = graphNode.properties || {};
        const locked = props.locked_fields || [];
        const tags = props.tags || [];

        // Parse actions
        let actionList = [];
        if (Array.isArray(props.actions)) actionList = props.actions;
        else if (typeof props.actions === 'string') actionList = props.actions.split(',').map(action => action.trim()).filter(Boolean);

        const template = htmlTag`
            ${IV._renderItemHeader(name, nodeId)}
            ${IV._renderDescriptionSection(props, nodeId)}
            ${IV._renderActionsGrid(actionList, nodeId, locked)}
            ${IV._renderPropertiesSection(props, nodeId, locked)}
            ${IV._renderParametersSection(props, nodeId)}
            ${window.InspectorHelpers.graphGravityControl(nodeId, props)}
            ${IV._renderTagsSection(tags, nodeId, locked)}
            ${InspectorHelpers.renderAliasesSection(nodeId, props.aliases)}
            ${window.InspectorTriggers.buildTriggersHtml(nodeId, locked)}
            ${window.InspectorTriggers.buildContentsHtml(nodeId)}
            ${IV._renderMoveSection(nodeId)}
            <div id="known-by-mount"></div>
            ${IV._renderFooter(nodeId)}
        `;

        InspectorPanel.render(template);
        const kbMount = document.getElementById('known-by-mount');
        if (kbMount && window.KnownBySection) kbMount.replaceWith(window.KnownBySection.build('item', nodeId, name));
        IV._populateLibraryTemplate(nodeId);
        IV._initMoveTargetSearch();

        // Initialize TagMultiselect (render is synchronous, so the container exists).
        const tagContainer = document.getElementById(`tag-multiselect-container-${nodeId}`);
        if (tagContainer && typeof TagMultiselect !== 'undefined') {
            IV._tagMs = new TagMultiselect(tagContainer, {
                tags: Array.isArray(tags) ? tags : [],
                appliesTo: 'items',
                allowNew: true,
                placeholder: 'Search or create tags...',
                onChange: (newTags) => {
                    api.updateNode(nodeId, { properties: { tags: newTags } }).then(() => worldState.fetch());
                    const t = newTags || [];
                    const dEl = document.getElementById(`insp-equip-defense-${nodeId}`);
                    const wEl = document.getElementById(`insp-equip-weapon-${nodeId}`);
                    const tEl = document.getElementById(`insp-equip-temp-${nodeId}`);
                    const rEl = document.getElementById(`insp-equip-resists-${nodeId}`);
                    const lEl = document.getElementById(`insp-light-source-${nodeId}`);
                    const hEl = document.getElementById(`insp-heat-source-${nodeId}`);
                    if (dEl) dEl.style.display = (t.includes('armor') || t.includes('clothing')) ? 'block' : 'none';
                    if (wEl) wEl.style.display = t.includes('weapon') ? 'block' : 'none';
                    if (tEl) tEl.style.display = (t.includes('insulation') || t.includes('environmental')) ? 'block' : 'none';
                    if (rEl) rEl.style.display = t.includes('resistance') ? 'block' : 'none';
                    if (lEl) lEl.style.display = t.includes('light_source') ? 'block' : 'none';
                    if (hEl) hEl.style.display = t.includes('heat_source') ? 'block' : 'none';
                }
            });
        }
        reinitChoices(document.getElementById('inspector-panel'));
    };

    // ═══════════════════════════════════════════════
    //  Section renderers
    // ═══════════════════════════════════════════════

    /**
     * Render the item header (badge, editable name, node ID, close button)
     * @param {string} name - Item display name
     * @param {string} nodeId - Graph node ID
     * @returns {TemplateResult}
     */
    IV._renderItemHeader = function(name, nodeId) {
        return htmlTag`<div class="inspector-header">
            <span class="inspector-type-badge" style="background:#e3b341">📦 Item</span>
            <div style="flex:1;display:flex;flex-direction:column;">
                <h2 style="margin:0;font-size:16px;"><input type="text" .value=${name} @change=${(ev) => IV._updateItemProp(nodeId, 'name', ev.target.value)} style="font-size:1em;background:transparent;border:1px solid var(--border);color:inherit;width:100%;"></h2>
                <div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                    <div style="display:flex;gap:2px;align-items:center;">
                        <input type="text" .value=${nodeId} @change=${(ev) => InspectorHelpers.renameNode(nodeId, ev.target.value)} style="font-size:10px;padding:1px 4px;background:transparent;border:1px solid transparent;color:var(--text-muted);width:100%;cursor:text;" title="Change node ID (lowercase, no spaces)">
                        <button class="btn btn-sm btn-ghost" @click=${() => InspectorHelpers.syncIdFromName(nodeId, name)} title="Sync ID from name">🔄</button>
                    </div>
                </div>
            </div>
            <button class="btn btn-sm btn-ghost" @click=${() => hideInspectorPanel()}>✕</button>
        </div>`;
    };

    /**
     * Render the description section with AI improve button
     * @param {object} props - Node properties
     * @param {string} nodeId - Graph node ID
     * @returns {TemplateResult}
     */
    IV._renderLockToggle = function(field, lockedFields, nodeId) {
        return InspectorHelpers.renderLockToggle(field, lockedFields, nodeId);
    };

    IV._toggleFieldLock = function(nodeId, field, el) {
        return InspectorHelpers.toggleFieldLock(nodeId, field);
    };

    IV._renderDescriptionSection = function(props, nodeId) {
        const locked = props.locked_fields || [];
        return htmlTag`<div class="inspector-section"><h3 style="display:flex;align-items:center;gap:4px;">${IV._renderLockToggle('description', locked, nodeId)} Description</h3>
            <textarea rows="4" id="item-desc-${nodeId}" style="width:100%;padding:4px 8px;font-size:12px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);font-family:var(--font);resize:vertical;min-height:40px;"
                .value=${props.description || ''}
                @change=${(ev) => IV._updateItemProp(nodeId, 'description', ev.target.value)}></textarea>
            <div style="display:flex;gap:4px;margin-top:4px;">
                <button class="btn btn-sm" id="improve-item-btn" @click=${() => IV._improveItemWithAI(nodeId)} style="white-space:nowrap;background:#2a6a3a;border-color:#3a9a5a;color:#7cff9c;">✨ Improve</button>
            </div></div>`;
    };

    /**
     * Render the actions grid (toggleable checkboxes)
     * @param {string[]} actionList - Current action list
     * @param {string} nodeId - Graph node ID
     * @param {string[]} locked - Currently locked fields
     * @returns {TemplateResult}
     */
    IV._renderActionsGrid = function(actionList, nodeId, locked) {
        return htmlTag`<div class="inspector-section">
            <h3 style="display:flex;align-items:center;gap:4px;">${IV._renderLockToggle('actions', locked, nodeId)} Actions <span class="section-hint">(toggle which actions this item supports)</span></h3>
            <div class="checkbox-grid actions-grid" id="actions-grid-${nodeId}">
                ${ALL_ACTIONS.map((action) => {
                    const checked = actionList.includes(action);
                    const bg = actionColor(action);
                    return htmlTag`<label class="action-toggle ${checked ? 'active' : ''}"
                        style="${checked ? `background:${bg}22;border-color:${bg};color:${bg};` : ''}"
                        @change=${() => IV._toggleAction(nodeId, action)}>
                        <input type="checkbox" ?checked=${checked} value=${action}>
                        <span>${actionIcon(action)} ${action}</span>
                    </label>`;
                })}
            </div></div>`;
    };

    /**
     * Render the properties section (state, uses, weight, hidden, locked, equip slots)
     * @param {object} props - Node properties
     * @param {string} nodeId - Graph node ID
     * @param {string[]} locked - Currently locked fields
     * @returns {TemplateResult}
     */
    IV._renderPropertiesSection = function(props, nodeId, locked) {
        locked = locked || [];
        const itemState = props.current_state || 'normal';
        const stateOptions = ITEM_STATE_OPTIONS.map(stateName =>
            htmlTag`<option value=${stateName} ?selected=${itemState === stateName}>${stateName}</option>`
        );

        const slotOptions = EQUIP_SLOT_OPTIONS.map(slotName =>
            htmlTag`<option value=${slotName} ?selected=${(props.equip_slots || []).includes(slotName)}>${slotName}</option>`
        );

        const tags = props.tags || [];
        const showDefense = tags.includes('armor') || tags.includes('clothing');
        const showDamage = tags.includes('weapon');
        const showTemp = tags.includes('insulation') || tags.includes('environmental');
        const showResists = tags.includes('resistance');
        const showLightSource = tags.includes('light_source');
        const showHeatSource = tags.includes('heat_source');

        const resistStr = props.resistances ? Object.entries(props.resistances).map(([k,v]) => `${k}:${v}`).join(', ') : '';
        const damageSkill = props.damage_skill || 'Athletics';
        const damageType = props.damage_type || '';

        return htmlTag`<div class="inspector-section"><h3>⚙️ Properties</h3>
            <div class="field"><label>State</label>
                <select @change=${(ev) => api.updateNode(nodeId, { properties: { current_state: ev.target.value } }).then(() => worldState.fetch())}>${stateOptions}</select>
            </div>
            <div class="form-row">
                <div class="field"><label>Uses</label><input type="number" .value=${props.uses ?? -1} @change=${(ev) => api.updateNode(nodeId, { properties: { uses: parseInt(ev.target.value) } }).then(() => worldState.fetch())}></div>
                <div class="field"><label>Weight</label><input type="number" step="0.1" .value=${props.weight ?? 0.1} @change=${(ev) => api.updateNode(nodeId, { properties: { weight: parseFloat(ev.target.value) } }).then(() => worldState.fetch())}></div>
            </div>
            <div class="form-row">
                <div class="field"><label>Equipped Weight Mod</label><input type="number" step="0.1" .value=${props.equipped_weight_mod ?? 1.0} @change=${(ev) => api.updateNode(nodeId, { properties: { equipped_weight_mod: parseFloat(ev.target.value) || 1.0 } }).then(() => worldState.fetch())} title="Multiplier applied when equipped (default 1.0)"></div>
            </div>
            <div class="field"><label>Equip Slots (select one or more)</label>
                <select multiple class="choices-init" id="node-equip-slots-${nodeId}" @change=${(ev) => { const selectedValues = Array.from(ev.target.selectedOptions).map(opt => opt.value); api.updateNode(nodeId, { properties: { equip_slots: selectedValues } }).then(() => worldState.fetch()); }} style="width:100%;">
                    ${slotOptions}
                </select>
            </div>
            <div id="insp-equip-defense-${nodeId}" style="display:${showDefense ? 'block' : 'none'};margin-top:4px;">
                <div class="field"><label>${IV._renderLockToggle('defense', locked, nodeId)} Defense (DR)</label><input type="number" min="0" .value=${props.defense ?? 0} @change=${(ev) => api.updateNode(nodeId, { properties: { defense: parseInt(ev.target.value) } }).then(() => worldState.fetch())}></div>
            </div>
            <div id="insp-equip-weapon-${nodeId}" style="display:${showDamage ? 'block' : 'none'};margin-top:4px;">
                <div class="field"><label>${IV._renderLockToggle('damage', locked, nodeId)} Damage (e.g. "2d6+3", "1d8", or "8")</label><input type="text" .value=${props.damage ?? ''} placeholder="2d6+3" @change=${(ev) => api.updateNode(nodeId, { properties: { damage: ev.target.value } }).then(() => worldState.fetch())} style="width:100%;font-size:11px;"></div>
                <div class="field"><label>Damage Skill</label>
                    <select @change=${(ev) => api.updateNode(nodeId, { properties: { damage_skill: ev.target.value } }).then(() => worldState.fetch())} style="width:100%;font-size:11px;">
                        ${SKILL_OPTIONS.map(s => htmlTag`<option value=${s} ?selected=${damageSkill === s}>${s}</option>`)}
                    </select>
                </div>
                <div class="field"><label>Damage Type</label>
                    <select @change=${(ev) => api.updateNode(nodeId, { properties: { damage_type: ev.target.value } }).then(() => worldState.fetch())} style="width:100%;font-size:11px;">
                        <option value="">— None —</option>
                        ${DAMAGE_TYPES.map(dt => htmlTag`<option value=${dt} ?selected=${damageType === dt}>${dt}</option>`)}
                    </select>
                </div>
            </div>
            <div id="insp-equip-temp-${nodeId}" style="display:${showTemp ? 'block' : 'none'};margin-top:4px;">
                <div class="field"><label>${IV._renderLockToggle('insulation', locked, nodeId)} Insulation (°C shift)</label>
                    <input type="number" .value=${props.insulation ?? ''} step="1" placeholder="+warms, -cools" style="width:100%;font-size:11px;" @change=${(ev) => IV._updateInsulation(nodeId, ev.target.value)}>
                </div>
            </div>
            <div id="insp-equip-resists-${nodeId}" style="display:${showResists ? 'block' : 'none'};margin-top:4px;">
                <div class="field"><label>${IV._renderLockToggle('resistances', locked, nodeId)} Resistances (key:val, key:val)</label>
                    <input type="text" .value=${resistStr} placeholder="fire:5, cold:3, toxic:999" @change=${(ev) => IV._updateResistances(nodeId, ev.target.value)} style="width:100%;font-size:11px;">
                </div>
            </div>
            <div id="insp-light-source-${nodeId}" style="display:${showLightSource ? 'block' : 'none'};margin-top:4px;">
                <div class="field"><label>Light Level</label>
                    <select @change=${(ev) => IV._updateLightLevel(nodeId, ev.target.value)} style="width:100%;font-size:11px;">
                        <option value="pitch_black" ?selected=${props.light_level === 'pitch_black'}>Pitch Black</option>
                        <option value="dim" ?selected=${!props.light_level || props.light_level === 'dim'}>Dim</option>
                        <option value="normal" ?selected=${props.light_level === 'normal'}>Normal</option>
                        <option value="bright" ?selected=${props.light_level === 'bright'}>Bright</option>
                        <option value="blinding" ?selected=${props.light_level === 'blinding'}>Blinding</option>
                    </select>
                </div>
            </div>
            <div id="insp-heat-source-${nodeId}" style="display:${showHeatSource ? 'block' : 'none'};margin-top:4px;">
                <div class="field"><label>Target Temperature (°C)</label>
                    <input type="number" .value=${props.target_temperature ?? 30} step="1" placeholder="target temp" @change=${(ev) => IV._updateHeatSourceProp(nodeId, 'target_temperature', ev.target.value)} style="width:100%;font-size:11px;">
                </div>
                <div class="field" style="margin-top:4px;"><label>Heating Rate (°C/tick)</label>
                    <input type="number" .value=${props.heating_rate ?? 0.5} step="0.1" placeholder="degrees per tick" @change=${(ev) => IV._updateHeatSourceProp(nodeId, 'heating_rate', ev.target.value)} style="width:100%;font-size:11px;">
                </div>
            </div>
            <div id="insp-container-capacity-${nodeId}" style="display:${tags.includes('container') ? 'block' : 'none'};margin-top:4px;">
                <div class="field"><label>Max Weight Capacity (kg)</label>
                    <input type="number" step="0.1" .value=${props.max_weight_capacity ?? ''} placeholder="unlimited" @change=${(ev) => api.updateNode(nodeId, { properties: { max_weight_capacity: parseFloat(ev.target.value) || null } }).then(() => worldState.fetch())} style="width:100%;font-size:11px;">
                </div>
                <div class="field"><label>Container Weight Mod</label>
                    <input type="number" step="0.1" .value=${props.container_weight_mod ?? 1.0} @change=${(ev) => api.updateNode(nodeId, { properties: { container_weight_mod: parseFloat(ev.target.value) || 1.0 } }).then(() => worldState.fetch())} title="Multiplier for contents' weight toward encumbrance (default 1.0)" style="width:100%;font-size:11px;">
                </div>
                <div class="field"><label>Current Weight</label>
                    ${IV._containerFillBar(nodeId, props.max_weight_capacity)}
                </div>
            </div>
        </div>`;
    };

    /**
     * Compute the total weight of items inside a container.
     * @param {string} nodeId - Container's graph node ID
     * @returns {string} Formatted weight
     */
    IV._containerCurrentWeight = function(nodeId) {
        if (!worldState.graph?.edges) return 0;
        const edges = worldState.graph.edges;
        const nodeIdLower = String(nodeId).toLowerCase();
        let total = 0;
        for (const edge of edges) {
            if (edge.type === 'in' && String(edge.target).toLowerCase() === nodeIdLower) {
                const contentNode = worldState.getNode(edge.source);
                if (contentNode) {
                    total += parseFloat(contentNode.properties?.weight) || 0;
                }
            }
        }
        return total;
    };

    /**
     * Render container fill text + optional progress bar when max capacity is set.
     * @param {string} nodeId - Container's graph node ID
     * @param {number|string|null} maxCap - max_weight_capacity from properties
     * @returns {string} HTML
     */
    IV._containerFillBar = function(nodeId, maxCap) {
        const current = IV._containerCurrentWeight(nodeId);
        const max = parseFloat(maxCap);
        if (!max || isNaN(max)) {
            return `<span style="font-size:12px;color:var(--text-dim);">${current.toFixed(1)} kg</span>`;
        }
        const ratio = Math.min(current / max, 1);
        const pct = (ratio * 100).toFixed(0);
        let color = 'var(--green)';
        if (ratio >= 0.8) color = 'var(--red)';
        else if (ratio >= 0.5) color = 'var(--yellow)';
        return `<div>
            <span style="font-size:12px;color:var(--text-dim);">${current.toFixed(1)} / ${max.toFixed(1)} kg (${pct}%)</span>
            <div style="height:6px;background:var(--bg-inset);border-radius:4px;overflow:hidden;margin-top:4px;">
                <div style="width:${pct}%;height:100%;background:${color};border-radius:4px;transition:width 0.2s;"></div>
            </div>
        </div>`;
    };

    /**
     * Render the parameters section (key-value pairs)
     * @param {object} props - Node properties
     * @param {string} nodeId - Graph node ID
     * @returns {TemplateResult}
     */
    IV._renderParametersSection = function(props, nodeId) {
        const params = props.parameters || {};
        const paramKeys = Object.keys(params);
        return htmlTag`<div class="inspector-section"><h3>📐 Parameters <span class="section-hint">(key-value pairs for {param:&lt;key&gt;} in triggers)</span></h3>
            <div id="params-list-${nodeId}" style="margin-bottom:4px;">
                ${paramKeys.map((key) => htmlTag`<div style="display:flex;gap:4px;align-items:center;margin-bottom:3px;">
                    <input type="text" .value=${key} style="flex:2;font-size:11px;padding:2px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);"
                        @change=${(ev) => InspectorHelpers.updateParamKey(nodeId, key, ev.target.value)} placeholder="key">
                    <input type="text" .value=${String(params[key])} style="flex:3;font-size:11px;padding:2px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);"
                        @change=${(ev) => InspectorHelpers.updateParamValue(nodeId, key, ev.target.value)} placeholder="value">
                    <button class="btn btn-sm btn-ghost" @click=${() => InspectorHelpers.removeParam(nodeId, key)} style="padding:0 6px;font-size:14px;line-height:1;">✕</button>
                </div>`)}
            </div>
            <div style="display:flex;gap:4px;">
                <input type="text" id="param-key-${nodeId}" placeholder="key" style="flex:2;font-size:11px;padding:2px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);">
                <input type="text" id="param-val-${nodeId}" placeholder="value" style="flex:3;font-size:11px;padding:2px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);">
                <button class="btn btn-sm btn-blue" @click=${() => InspectorHelpers.addParam(nodeId)}>➕</button>
            </div>
        </div>`;
    };

    /**
     * Render the tags section
     * @param {string[]} tags - Current tags array
     * @param {string} nodeId - Graph node ID
     * @param {string[]} locked - Currently locked fields
     * @returns {TemplateResult}
     */
    IV._renderTagsSection = function(tags, nodeId, locked) {
        return htmlTag`<div class="inspector-section"><h3 style="display:flex;align-items:center;gap:4px;">${IV._renderLockToggle('tags', locked, nodeId)} Tags</h3>
            <div id="tag-multiselect-container-${nodeId}"></div>
        </div>`;
    };

    /**
     * Resolve the area a node currently lives in by walking its 'in' chain.
     * Returns the area node id, or null when carried/equipped/unplaced.
     * @param {string} nodeId - Graph node ID
     * @returns {string|null} Area node id or null
     */
    IV._getItemAreaId = function(nodeId) {
        const graph = worldState.graph;
        if (!graph?.nodes || !graph?.edges) return null;
        const areaIds = new Set(Object.values(graph.nodes)
            .filter(n => n.type === 'area').map(n => n.id));
        let cur = nodeId;
        for (let depth = 0; depth < 10; depth++) {
            const inEdge = graph.edges.find(e => e.source === cur && e.type === 'in');
            if (!inEdge) return null;
            if (areaIds.has(inEdge.target)) return inEdge.target;
            cur = inEdge.target;
        }
        return null;
    };

    /**
     * Render the move section (area or container destination)
     * @param {string} nodeId - Graph node ID
     * @returns {TemplateResult}
     */
    IV._renderMoveSection = function(nodeId) {
        const relationOptions = ['in','on','under','behind','beside','at']
            .map(r => htmlTag`<option value=${r}>${r}</option>`);

        return htmlTag`<div class="inspector-section"><h3>📍 Move To</h3>
            <div style="display:flex;gap:4px;margin-bottom:4px;">
                <label style="font-size:10px;display:flex;align-items:center;gap:2px;cursor:pointer;"><input type="radio" name="move-dest-type" value="item" checked @change=${() => IV._toggleMoveDestType()}> 📦 Item</label>
                <label style="font-size:10px;display:flex;align-items:center;gap:2px;cursor:pointer;"><input type="radio" name="move-dest-type" value="character" @change=${() => IV._toggleMoveDestType()}> 🧍 Character</label>
                <label style="font-size:10px;display:flex;align-items:center;gap:2px;cursor:pointer;"><input type="radio" name="move-dest-type" value="area" @change=${() => IV._toggleMoveDestType()}> 🏠 Area</label>
            </div>
            <input type="text" id="move-target-search" placeholder="Search items, characters, or areas..." style="width:100%;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;margin-bottom:4px;">
            <div id="move-target-results" style="display:none;position:absolute;z-index:1000;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;max-height:200px;overflow-y:auto;width:300px;box-shadow:0 4px 12px rgba(0,0,0,0.3);"></div>
            <input type="hidden" id="move-target-id">
            <div id="move-target-preview" style="font-size:10px;color:var(--text-muted);margin-bottom:4px;"></div>
            <select id="move-target-relation" style="width:100%;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;margin-bottom:4px;">${relationOptions}</select>
            <button class="btn btn-sm btn-blue" @click=${() => IV._moveItemToTarget(nodeId)}>📌 Move To</button>
        </div>`;
    };

    /**
     * Render the footer (save to library, delete)
     * @param {string} nodeId - Graph node ID
     * @returns {TemplateResult}
     */
IV._renderFooter = function(nodeId) {
        const libId = (worldState.getNode(nodeId)?.properties?.library_id) || '';
        return htmlTag`<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">
            <select id="item-lib-template-${nodeId}" title="Library template this node syncs against (task-295)" style="flex:1;min-width:140px;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">
                <option value="">(no template)</option>
                ${libId ? htmlTag`<option value=${libId} ?selected=${true}>${libId}</option>` : window.Lit.nothing}
            </select>
            <button class="btn btn-sm btn-green" @click=${() => IV._refreshFromLibrary(nodeId)}>🔄 Refresh from Library</button>
            <button class="btn btn-sm btn-yellow" @click=${() => itemLib.saveWorldItem(nodeId)}>📚 Save to Library</button>
            <button class="btn btn-sm btn-red" @click=${() => graphManager._deleteNode(nodeId)}>🗑 Delete</button>
        </div>`;
    };

    /**
     * Populate the Library Template dropdown from the item library registry.
     * @param {string} nodeId - Graph node ID
     */
    IV._populateLibraryTemplate = async function(nodeId) {
        const escapedId = nodeId.replace(/'/g, "\\'");
        const select = document.getElementById(`item-lib-template-${escapedId}`);
        if (!select) return;
        const current = select.value || worldState.getNode(nodeId)?.properties?.library_id || '';
        let libData = {};
        try { libData = await ApiClient.getLibraryType('items'); } catch (e) { /* ignore */ }
        const options = [htmlTag`<option value="">(no template)</option>`];
        for (const [id, entry] of Object.entries(libData)) {
            const label = (entry && entry.name) ? `${entry.name} (${id})` : id;
            options.push(htmlTag`<option value=${id}>${label}</option>`);
        }
        window.Lit.render(options, select);
        if (current) select.value = current;
    };

    // ═══════════════════════════════════════════════
    //  Action / Property mutation methods
    // ═══════════════════════════════════════════════

    /**
     * Toggle an action on an item node
     * @param {string} nodeId - Graph node ID
     * @param {string} action - Action name to toggle
     */
    IV._toggleAction = async function(nodeId, action) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const props = node.properties || {};
        let actions = [];
        if (Array.isArray(props.actions)) actions = [...props.actions];
        else if (typeof props.actions === 'string') actions = props.actions.split(',').map(a => a.trim()).filter(Boolean);
        else actions = [];

        const actionIndex = actions.indexOf(action);
        const adding = actionIndex < 0;
        const inverse = INVERSE_ACTIONS[action];
        if (adding) {
            actions.push(action);
            if (inverse && !actions.includes(inverse)) actions.push(inverse);
        } else {
            actions.splice(actionIndex, 1);
            if (inverse) {
                const inverseIndex = actions.indexOf(inverse);
                if (inverseIndex >= 0) actions.splice(inverseIndex, 1);
            }
        }

        await api.updateNode(nodeId, { properties: { actions } });
        if (adding) await IV._ensureActionTrigger(nodeId, action);
        if (adding && inverse) await IV._ensureActionTrigger(nodeId, inverse);
        worldState.fetch().then(() => {
            if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
        });
    };

    /**
     * Ensure a base empty `on_<action>` trigger exists on an item node.
     *
     * Called when an allowed action is toggled ON: creates a base empty trigger
     * so the designer immediately has a hook to author effects (task-252).
     * Toggling an action OFF never removes triggers. Idempotent — if an
     * on_<action> trigger already exists, nothing is created.
     * @param {string} nodeId - Graph node ID (item)
     * @param {string} action - Action name (e.g. 'use')
     */
    IV._ensureActionTrigger = async function(nodeId, action) {
        const triggerType = `on_${action}`;
        if (!TriggerTypes?.TRIGGER_TYPES?.includes(triggerType)) return;

        const nodeIdLower = String(nodeId).toLowerCase();
        const exists = (worldState.graph?.edges || []).some(edge => {
            if (edge.type !== 'triggers') return false;
            if (String(edge.source).toLowerCase() !== nodeIdLower) return false;
            const raw = edge.properties?.trigger_type;
            const types = Array.isArray(raw) ? raw : [raw || ''];
            return types.some(t => String(t).toLowerCase() === triggerType);
        });
        if (exists) return;

        const triggerId = `trigger_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
        const compiled = {
            trigger_type: triggerType,
            effects: [],
            conditions: [],
            success_message: '',
            fail_message: '',
        };
        const nodeRes = await ApiClient.createNode({
            id: triggerId,
            type: 'logic_trigger',
            name: `${triggerType} → ?`,
            properties: compiled
        });
        if (nodeRes?.error) return;
        await ApiClient.createEdge(nodeId, triggerId, 'triggers', compiled);
    };

    /**
     * Update the insulation field on an item node
     * @param {string} nodeId - Graph node ID
     * @param {string} val - Input value
     */
    IV._updateInsulation = async function(nodeId, val) {
        const num = parseFloat(val);
        const ins = isNaN(num) ? 0 : num;
        await api.updateNode(nodeId, { properties: { insulation: ins } });
        worldState.fetch();
    };

    /**
     * Update the resistances dict on an item node
     * @param {string} nodeId - Graph node ID
     * @param {string} str - Comma-separated key:val pairs
     */
    IV._updateResistances = async function(nodeId, str) {
        const resistances = {};
        str.split(',').forEach(pair => {
            const parts = pair.split(':').map(s => s.trim());
            if (parts.length === 2 && parts[0] && parts[1]) {
                const val = parseInt(parts[1]);
                if (!isNaN(val)) resistances[parts[0]] = val;
            }
        });
        await api.updateNode(nodeId, { properties: { resistances: Object.keys(resistances).length > 0 ? resistances : undefined } });
        worldState.fetch();
    };

    /**
     * Update the light_level property on an item node
     * @param {string} nodeId - Graph node ID
     * @param {string} val - Input value
     */
    IV._updateLightLevel = async function(nodeId, val) {
        await api.updateNode(nodeId, { properties: { light_level: val } });
        worldState.fetch();
    };

    /**
     * Update a heat_source property on an item node
     * @param {string} nodeId - Graph node ID
     * @param {string} field - Property name (target_temperature or heating_rate)
     * @param {string} val - Input value
     */
    IV._updateHeatSourceProp = async function(nodeId, field, val) {
        const num = parseFloat(val);
        const value = isNaN(num) ? (field === 'target_temperature' ? 30 : 0.5) : num;
        await api.updateNode(nodeId, { properties: { [field]: value } });
        worldState.fetch();
    };

    /**
     * Move item to a area
     * @param {string} nodeId - Graph node ID
     */
    IV._moveItemToTarget = async function(nodeId) {
        const targetType = document.querySelector('input[name="move-dest-type"]:checked')?.value || 'item';
        const targetId = document.getElementById('move-target-id')?.value || '';
        const relation = document.getElementById('move-target-relation')?.value || 'in';
        if (!targetId) { events.log('No target selected.', 'error-msg'); return; }
        const res = await ApiClient.moveItemToRoom(nodeId, null, null, null, targetType, targetId, relation);
        if (res.error) { events.log(`Move failed: ${res.error}`, 'error-msg'); return; }
        const targetName = worldState.getNode(targetId)?.name || targetId;
        events.log(`Moved "${worldState.getNode(nodeId)?.name || nodeId}" to "${targetName}" (${relation})`, 'system-msg');
        worldState.fetch();
        if (window.VW?.inspector) window.VW.inspector.showNode(targetId);
    };

    IV._toggleMoveDestType = function() {
        const selected = document.querySelector('input[name="move-dest-type"]:checked');
        const search = document.getElementById('move-target-search');
        const relation = document.getElementById('move-target-relation');
        if (!search || !relation || !selected) return;
        const labels = { item: 'Search items...', character: 'Search characters...', area: 'Search areas...' };
        search.placeholder = labels[selected.value] || 'Search...';
        relation.style.display = selected.value === 'item' ? 'block' : 'none';
    };

    IV._initMoveTargetSearch = function() {
        const input = document.getElementById('move-target-search');
        const results = document.getElementById('move-target-results');
        const preview = document.getElementById('move-target-preview');
        const hidden = document.getElementById('move-target-id');
        if (!input || !results || !hidden || !preview) return;
        const show = async (query) => {
            const targetType = document.querySelector('input[name="move-dest-type"]:checked')?.value || 'item';
            const q = encodeURIComponent(query.trim().toLowerCase());
            try {
                const resp = await fetch(`/api/search/placement-targets?q=${q}`);
                if (!resp.ok) return;
                const all = await resp.json();
                const items = all.filter(r => r.type === targetType);
                if (!items.length) { results.style.display = 'none'; return; }
                results.innerHTML = items.map(r => `<div class="tag-option" data-id="${r.id}" data-name="${(r.name || '').replace(/"/g, '&quot;')}" style="padding:6px 8px;cursor:pointer;font-size:11px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:6px;"><span>${r.icon}</span><span style="font-weight:600;">${r.name}</span><span style="color:var(--text-muted);font-size:9px;margin-left:auto;">${r.type}</span></div>`).join('');
                results.style.display = 'block';
                results.querySelectorAll('.tag-option').forEach(el => {
                    el.addEventListener('click', () => {
                        hidden.value = el.dataset.id;
                        preview.textContent = `Selected: ${el.dataset.name} (${el.dataset.id})`;
                        results.style.display = 'none';
                        input.value = el.dataset.name;
                    });
                });
            } catch { results.style.display = 'none'; }
        };
        input.oninput = () => { const q = input.value.trim(); if (!q) { results.style.display = 'none'; hidden.value = ''; preview.textContent = ''; } else show(q); };
        input.onblur = () => setTimeout(() => { results.style.display = 'none'; }, 150);
        input.onfocus = () => { if (input.value.trim()) show(input.value); };
    };

    /**
     * Update a single property on an item node
     * @param {string} nodeId - Graph node ID
     * @param {string} field - Property field name (or 'name')
     * @param {string|number} value - New value
     */
    IV._updateItemProp = async function(nodeId, field, value) {
        const update = {};
        if (field === 'name') {
            await api.updateNode(nodeId, { name: value });
        } else {
            update[field] = value;
            await api.updateNode(nodeId, { properties: update });
        }
        worldState.fetch();
    };

    // ═══════════════════════════════════════════════
    //  AI Improve
    // ═══════════════════════════════════════════════

    /**
     * Refresh item from library with diff modal (selective sections).
     */
    IV._refreshFromLibrary = async function(nodeId) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const templateSelect = document.getElementById(`item-lib-template-${nodeId}`);
        const libId = (templateSelect && templateSelect.value) || node.properties?.library_id;
        if (!libId) { toastInfo('No library template selected — cannot refresh.'); return; }

        let libEntry = {};
        try {
            const libData = await ApiClient.getLibraryType('items');
            libEntry = libData[libId] || {};
        } catch (e) { /* ignore */ }

        if (!Object.keys(libEntry).length) {
            toastInfo('No library entry found for this item. Save to library first.');
            return;
        }

        const props = node.properties || {};
        const worldPayload = {
            name: node.name || '',
            description: props.description || '',
            actions: (props.actions || []).join(',') || 'examine,take,use',
            uses: props.uses ?? -1,
            weight: props.weight ?? 0.1,
            equip_slots: props.equip_slots || [],
            current_state: props.current_state || 'normal',
            light_level: props.light_level,
            target_temperature: props.target_temperature,
            heating_rate: props.heating_rate,
            sound_level: props.sound_level,
            sound_pattern: props.sound_pattern,
            stun_chance: props.stun_chance,
            stun_duration: props.stun_duration,
            defense: props.defense || 0,
            damage: props.damage || 0,
            insulation: props.insulation || 0,
            resistances: props.resistances || {},
            action_costs: props.action_costs || {},
            skill_check: props.skill_check || {},
            contents: props.contents || [],
            aliases: props.aliases || [],
            tags: props.tags || [],
            triggers: itemLib._extractTriggersFromEdges(nodeId),
        };

        const sections = [
            { key: 'name', label: 'Name' },
            { key: 'description', label: 'Description' },
            { key: 'actions', label: 'Actions' },
            { key: 'uses', label: 'Uses' },
            { key: 'weight', label: 'Weight' },
            { key: 'equip_slots', label: 'Equip Slots' },
            { key: 'current_state', label: 'State' },
            { key: 'light_level', label: 'Light Level' },
            { key: 'target_temperature', label: 'Target Temp' },
            { key: 'heating_rate', label: 'Heating Rate' },
            { key: 'sound_level', label: 'Sound Level' },
            { key: 'sound_pattern', label: 'Sound Pattern' },
            { key: 'stun_chance', label: 'Stun Chance' },
            { key: 'stun_duration', label: 'Stun Duration' },
            { key: 'defense', label: 'Defense' },
            { key: 'damage', label: 'Damage' },
            { key: 'insulation', label: 'Insulation' },
            { key: 'resistances', label: 'Resistances' },
            { key: 'action_costs', label: 'Action Costs' },
            { key: 'skill_check', label: 'Skill Check' },
            { key: 'contents', label: 'Contents' },
            { key: 'aliases', label: 'Aliases' },
            { key: 'tags', label: 'Tags' },
            { key: 'triggers', label: 'Triggers' },
        ];

        const result = await DiffModal.show(libEntry, worldPayload, sections, {
            title: 'Refresh Item from Library',
            name: node.name,
            direction: 'to-world'
        });

        if (!result || !result.sections.length) return;

        const data = await ApiClient.refreshFromLibrary(nodeId, result.sections, libId);
        if (data.error) { toastError(data.error); return; }
        await worldState.fetch();
        if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
        events.log(`Refreshed "${node.name}" from library: ${data.applied?.join(', ')}`, 'system-msg');
    };

    IV._improveItemWithAI = async function(nodeId) {
        const system = `You are a procedural item enhancer for a text adventure game. The item data schema supports:

ACTIONS: examine, take, use, drop, inspect, read, eat, drink, wear, activate, combine, unlock, repair, break

PROPERTIES: uses (number, -1 = infinite), weight (number 0-100), current_state (string, e.g. normal/hidden/open/closed/locked/lit/broken), tags (string array), action_costs (per-action object with Energy/Hunger/Thirst/HP numbers), skill_check (object with skill name and dc number)

OUTPUT FORMAT: Respond with ONLY raw JSON. No markdown, no code fences, just JSON.`;

        const buildPrompt = (node, lockedFields) => {
            const name = node.name || '';
            const props = node.properties || {};
            const description = props.description || '';
            const actions = Array.isArray(props.actions) ? props.actions.join(', ') : (props.actions || 'examine,take,use');
            const tagList = (props.tags || []).join(', ');

            // Build prompt excluding locked fields
            const promptLines = [`Item Name: ${name}`];
            if (!lockedFields.includes('description')) promptLines.push(`Description: ${description}`);
            promptLines.push('');
            promptLines.push('Current properties:');
            if (!lockedFields.includes('actions')) promptLines.push(`- actions: ${actions}`);
            if (!lockedFields.includes('tags')) promptLines.push(`- tags: ${tagList}`);
            if (!lockedFields.includes('uses')) promptLines.push(`- uses: ${props.uses ?? -1}`);
            if (!lockedFields.includes('weight')) promptLines.push(`- weight: ${props.weight ?? 0.1}`);
            if (!lockedFields.includes('current_state')) promptLines.push(`- current_state: ${props.current_state || 'normal'}`);
            if (!lockedFields.includes('action_costs')) promptLines.push(`- action_costs: ${JSON.stringify(props.action_costs || {})}`);
            if (!lockedFields.includes('skill_check')) promptLines.push(`- skill_check: ${JSON.stringify(props.skill_check || {})}`);

            promptLines.push('');
            promptLines.push('Improve this item\'s description and properties. Make the description richer and more atmospheric. Suggest appropriate actions, tags, uses, weight, action_costs, and skill_check. Return the full item as JSON with name, description, actions, tags, uses, weight, current_state, action_costs, and skill_check fields.');
            return promptLines.join('\n');
        };

        const apply = (parsed, node, lockedFields, update) => {
            if (parsed.name) update.name = parsed.name;
            const propUpdate = {};
            if (parsed.description !== undefined && !lockedFields.includes('description')) propUpdate.description = parsed.description;
            if (parsed.actions && !lockedFields.includes('actions')) {
                propUpdate.actions = typeof parsed.actions === 'string'
                    ? parsed.actions.split(',').map(action => action.trim())
                    : parsed.actions;
            }
            if (parsed.uses !== undefined && !lockedFields.includes('uses')) propUpdate.uses = parsed.uses;
            if (parsed.weight !== undefined && !lockedFields.includes('weight')) propUpdate.weight = parsed.weight;
            if (parsed.current_state && !lockedFields.includes('current_state')) propUpdate.current_state = parsed.current_state;
            if (parsed.tags && !lockedFields.includes('tags')) {
                propUpdate.tags = Array.isArray(parsed.tags) ? parsed.tags : parsed.tags.split(',').map(t => t.trim());
            }
            if (parsed.action_costs && !lockedFields.includes('action_costs')) propUpdate.action_costs = parsed.action_costs;
            if (parsed.skill_check && !lockedFields.includes('skill_check')) propUpdate.skill_check = parsed.skill_check;
            if (Object.keys(propUpdate).length > 0) update.properties = propUpdate;
        };

        await InspectorHelpers.improveWithAI(nodeId, { btnId: 'improve-item-btn', system, buildPrompt, apply });
    };

    return IV;
})();
