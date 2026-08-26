/**
 * InspectorAreaView — Area inspector (showArea, improveRoomWithAI, environment editing)
 * Extracted from inspector.js for modularity.
 * task-216: renders lit-html TemplateResults through InspectorPanel (single panel owner).
 */

window.InspectorAreaView = (() => {
    const RV = {};

    // Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

    /**
     * Render the full area inspector panel
     * @param {string} nodeId - Graph node ID
     * @param {object} graphNode - Graph node data
     */
    RV.showArea = function(nodeId, graphNode) {
        const name = graphNode.name;
        const props = graphNode.properties || {};
        const description = props.description || '';
        const env = props.environment || {};

        // Resolve actual graph node ID
        let actualNodeId = nodeId;
        if (!worldState.getNode(nodeId) && worldState.graph?.nodes) {
            const found = Object.entries(worldState.graph.nodes).find(([, node]) => node.type === 'area' && node.name === name);
            if (found) actualNodeId = found[0];
        }

        // Exits
        const areaData = worldState.areas?.[name];
        const exits = areaData?.exits || {};
        const exitEntries = Object.entries(exits);

        // Agents here
        const agentsHere = Object.entries(worldState.players || {}).filter(([, player]) => player.current_area === name);

        // Area Event Log
        const roomEvents = events.getAreaEvents(name);

        // Area tags
        const areaTags = Array.isArray(props.tags) ? props.tags : [];

        // Items in area
        const items = worldState.getItemsInArea(name);

        const template = htmlTag`
            ${RV._renderRoomHeader(name, actualNodeId)}
            ${RV._renderDescriptionSection(description, actualNodeId)}
            ${RV._renderEnvironmentSection(env, actualNodeId)}
            ${RV._renderFloorSection(props, actualNodeId)}
            ${window.InspectorHelpers.graphGravityControl(actualNodeId, props)}

            <div class="inspector-section"><h3>🚪 Exits <span class="section-hint">(${exitEntries.length} found)</span></h3>
                <div style="display:flex;flex-direction:column;gap:4px;">
                    ${exitEntries.length > 0
                        ? exitEntries.map(([exitName, exitData]) => RV._renderExitItem(exitName, exitData, actualNodeId))
                        : htmlTag`<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No exits from this area.</div>`}
                </div>
            </div>

            <div class="inspector-section"><h3>📦 Actions</h3>
                <div style="font-size:11px;color:var(--text-muted);padding:4px 0;">Use 📚 Item Library in the toolbar to add items.</div>
            </div>

            <div class="inspector-section"><h3>🧍 Agents</h3>
                ${agentsHere.length > 0
                    ? agentsHere.map(([agentName]) => htmlTag`
                        <div class="relationship-item" @click=${() => VW.inspector.showAgent(agentName)}>
                            <span class="rel-node">${agentName}</span>
                        </div>`)
                    : htmlTag`<div style="font-size:11px;color:var(--text-muted);">No agents</div>`}
            </div>

            <div class="inspector-section"><h3>📜 Area Event Log <span class="section-hint">(who did what)</span></h3>
                <div class="area-event-log" style="max-height:240px;overflow-y:auto;font-size:11px;">
                    ${roomEvents.length > 0
                        ? roomEvents.map((evt) => {
                            const icon = EventBus.getActionIcon(evt);
                            const color = EventBus.getActionColor(evt);
                            const resultPreview = (evt.result || '');
                            return htmlTag`<div class="area-event-entry" style="padding:4px 8px;border-bottom:1px solid var(--border-light);display:flex;align-items:flex-start;gap:6px;">
                                <span style="flex-shrink:0;color:var(--text-muted);font-size:9px;">[${events.tickToTime(evt.tick)}]</span>
                                <span style="flex-shrink:0;">${icon}</span>
                                <span style="flex-shrink:0;font-weight:600;color:${color};">${evt.actor}</span>
                                <div style="flex:1;min-width:0;">
                                    ${evt.action ? htmlTag`<div style="color:var(--accent);font-family:var(--font-mono);font-size:10px;">${evt.action}</div>` : window.Lit.nothing}
                                    ${resultPreview ? htmlTag`<div style="color:var(--text-dim);font-size:10px;">→ ${resultPreview}${evt.result.length > 100 ? '...' : ''}</div>` : window.Lit.nothing}
                                </div>
                            </div>`;
                        })
                        : htmlTag`<div style="padding:8px;color:var(--text-muted);">No events recorded in this area yet. Events appear as characters take actions, speak, or affect the environment.</div>`}
                </div>
            </div>

            <div class="inspector-section"><h3>🏷️ Tags</h3>
                <div id="tag-multiselect-area-${actualNodeId}"></div>
                <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">Tag an area <code>exterior</code> to make it an infinite heat reservoir.</div>
            </div>

            ${InspectorHelpers.renderAliasesSection(actualNodeId, props.aliases)}

            <div class="inspector-section"><h3>📦 Items</h3>
                ${items.length > 0
                    ? items.map((item) => htmlTag`
                        <div class="relationship-item" @click=${() => VW.inspector.showNode(item.id)}>
                            <span class="rel-node">${item.properties?.current_state === 'locked' ? '🔒 ' : '📦 '}${item.name}</span>
                        </div>`)
                    : htmlTag`<div style="font-size:11px;color:var(--text-muted);">No items</div>`}
            </div>
        `;

        InspectorPanel.render(template);

        if (window.InspectorTemplateSync) {
            window.InspectorTemplateSync.populateSelector('area', actualNodeId);
        }

        if (window.events) events.setAreaFilter(name);

        // Initialize TagMultiselect for area tags (render is synchronous, so the
        // container exists by now).
        const tagContainer = document.getElementById(`tag-multiselect-area-${actualNodeId}`);
        if (tagContainer && typeof TagMultiselect !== 'undefined') {
            new TagMultiselect(tagContainer, {
                tags: areaTags,
                appliesTo: 'areas',
                allowNew: true,
                placeholder: 'Search or create tags...',
                onChange: (newTags) => {
                    api.updateNode(actualNodeId, { properties: { tags: newTags } }).then(() => worldState.fetch());
                }
            });
        }
    };

    /**
     * Render the area header (badge, editable name, node ID, close button)
     * @param {string} name - Area display name
     * @param {string} actualNodeId - Graph node ID
     * @returns {TemplateResult}
     */
    RV._renderRoomHeader = function(name, actualNodeId) {
        return htmlTag`<div class="inspector-header">
            <span class="inspector-type-badge" style="background:#58a6ff">🏠 Area</span>
            <div style="flex:1;display:flex;flex-direction:column;">
                <h2 style="margin:0;font-size:16px;"><input type="text" .value=${name} @change=${(ev) => api.updateNode(actualNodeId, { name: ev.target.value }).then(() => worldState.fetch())} style="font-size:1em;background:transparent;border:1px solid var(--border);color:inherit;width:100%;"></h2>
                <div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                    <div style="display:flex;gap:2px;align-items:center;">
                        <input type="text" .value=${actualNodeId} @change=${(ev) => InspectorHelpers.renameNode(actualNodeId, ev.target.value)} style="font-size:10px;padding:1px 4px;background:transparent;border:1px solid transparent;color:var(--text-muted);width:100%;cursor:text;" title="Change node ID (lowercase, no spaces)">
                        <button class="btn btn-sm btn-ghost" @click=${() => InspectorHelpers.syncIdFromName(actualNodeId, name)} title="Sync ID from name">🔄</button>
                    </div>
                </div>
            </div>
<button class="btn btn-sm btn-ghost" @click=${() => libraryBrowser.saveAreaByName(name)} title="Save this area to library" style="font-size:10px;">📚 Save to Library</button>
            <button class="btn btn-sm btn-ghost" @click=${() => hideInspectorPanel()}>✕</button>
        </div>`;
    };

    /**
     * Render the description section with AI improve button
     * @param {string} description - Area description text
     * @param {string} actualNodeId - Graph node ID
     * @returns {TemplateResult}
     */
    RV._renderDescriptionSection = function(description, actualNodeId) {
        return htmlTag`<div class="inspector-section"><h3>Description</h3>
            <textarea rows="2" style="width:100%;padding:4px 8px;font-size:12px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);font-family:var(--font);resize:vertical;min-height:40px;"
                .value=${description}
                @change=${(ev) => api.updateNode(actualNodeId, { properties: { description: ev.target.value } }).then(() => worldState.fetch())}></textarea>
            <div style="display:flex;gap:4px;margin-top:4px;">
                <button class="btn btn-sm" id="improve-area-btn" @click=${() => RV.improveRoomWithAI(actualNodeId)} style="white-space:nowrap;background:#2a6a3a;border-color:#3a9a5a;color:#7cff9c;">✨ Improve</button>
            </div></div>`;
    };

    /**
     * Render the environment section (light, temperature, air, smell, noise)
     * @param {object} env - Environment properties
     * @param {string} actualNodeId - Graph node ID
     * @returns {TemplateResult}
     */
    RV._renderEnvironmentSection = function(env, actualNodeId) {
        const lightValue = env.light ?? 'normal';
        const lightOptions = ['pitch_black', 'dim', 'normal', 'bright', 'blinding'].map(lightName =>
            htmlTag`<option value=${lightName} ?selected=${lightValue === lightName}>${lightName.replace(/_/g, ' ')}</option>`
        );

        const airValue = env.air || 'fresh';
        const airOptions = ['fresh', 'stale', 'humid', 'toxic', 'smoky', 'fragrant'].map(airName =>
            htmlTag`<option value=${airName} ?selected=${airValue === airName}>${airName.charAt(0).toUpperCase() + airName.slice(1)}</option>`
        );

        const noiseValue = env.noise || 'quiet';
        const noiseOptions = ['quiet', 'dripping', 'humming', 'windy', 'loud', 'chaotic', 'silent'].map(noiseName =>
            htmlTag`<option value=${noiseName} ?selected=${noiseValue === noiseName}>${noiseName.charAt(0).toUpperCase() + noiseName.slice(1)}</option>`
        );

return htmlTag`<div class="inspector-section"><h3>🌡️ Environment</h3>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Light</label>
                <select id="room-light" @change=${(ev) => RV._updateEnv(actualNodeId, 'light', ev.target.value)} style="flex:1;font-size:11px;">${lightOptions}</select>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Temp °C</label>
                <input type="number" min="-50" max="100" step="0.1" .value=${Math.round((env.temperature ?? 21) * 10) / 10} style="flex:1;" @change=${(ev) => RV._updateEnv(actualNodeId, 'temperature', Math.round(parseFloat(ev.target.value) * 10) / 10)}>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Air</label>
                <select id="room-air" @change=${(ev) => RV._updateEnv(actualNodeId, 'air', ev.target.value)} style="flex:1;">${airOptions}</select>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Smell</label>
                <input type="text" .value=${env.smell || 'neutral'} style="flex:1;font-size:11px;" @change=${(ev) => RV._updateEnv(actualNodeId, 'smell', ev.target.value || 'neutral')}>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Noise</label>
                <select @change=${(ev) => RV._updateEnv(actualNodeId, 'noise', ev.target.value)} style="flex:1;">${noiseOptions}</select>
            </div>
        </div>`;
    };

    /**
     * Render the floor section
     * @param {object} props - Node properties
     * @param {string} actualNodeId - Graph node ID
     * @returns {TemplateResult}
     */
    RV._renderFloorSection = function(props, actualNodeId) {
        const floorValue = props.floor ?? 0;
        return htmlTag`<div class="inspector-section"><h3>🏗️ Floor</h3>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <input type="number" min="-10" max="10" .value=${floorValue} style="flex:1;" @change=${(ev) => api.updateNode(actualNodeId, { properties: { floor: parseInt(ev.target.value) } }).then(() => worldState.fetch())}>
                <span style="font-size:10px;color:var(--text-muted);">${floorValue === 0 ? 'Ground' : `Floor ${floorValue}`}</span>
            </div>
        </div>`;
    };

    /**
     * Render a single exit/way entry in the area inspector
     * @param {string} exitName - Exit direction name
     * @param {object} exitData - Exit data object
     * @param {string} actualNodeId - Graph node ID (unused but passed for context)
     * @returns {TemplateResult}
     */
    RV._renderExitItem = function(exitName, exitData, actualNodeId) {
        const state = exitData.state || 'closed';
        const wayId = exitData.way_id || '';
        let stateIcon, stateColor;
        if (state === 'open') { stateIcon = '🟢'; stateColor = 'var(--green)'; }
        else if (state === 'closed') { stateIcon = '🟡'; stateColor = 'var(--yellow)'; }
        else if (state === 'locked') { stateIcon = '🔴'; stateColor = 'var(--red)'; }
        else if (state === 'hidden') { stateIcon = '⚫'; stateColor = 'var(--text-muted)'; }
        else if (state === 'blocked') { stateIcon = '⛔'; stateColor = 'var(--orange)'; }
        else if (state === 'broken') { stateIcon = '💥'; stateColor = 'var(--orange)'; }
        else { stateIcon = '❓'; stateColor = 'var(--text-muted)'; }

        const doorNode = wayId ? worldState.getNode(wayId) : null;
        const description = exitData.description || (doorNode?.properties?.description) || '';
        const resolvedDesc = doorNode
            ? InspectorHelpers.resolveWayParams(description, doorNode.properties?.parameters || {})
            : description;
        const badges = typeof WayAuthoring !== 'undefined'
            ? WayAuthoring.collectExitBadges(exitData, doorNode).filter(b => b.kind !== 'state')
            : [];
        const badgeRow = typeof WayAuthoring !== 'undefined'
            ? WayAuthoring.renderBadgeRow(badges, wayId)
            : '';
        const movementHint = doorNode && typeof WayAuthoring !== 'undefined'
            ? WayAuthoring.movementHint(doorNode, exitName)
            : '';
        const hasParamPreview = doorNode && /\{param:/.test(description)
            && InspectorHelpers.resolveWayParams(description, doorNode.properties?.parameters || {}) !== description;

        return htmlTag`<div class="exit-item" style="padding:6px 8px;background:var(--bg-inset);border-radius:4px;border-left:3px solid ${stateColor};margin-bottom:4px;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:6px;flex:1;min-width:0;">
                    <span style="flex-shrink:0;">${stateIcon}</span>
<span style="font-weight:600;font-size:12px;">${exitName}</span>
                    <span style="font-size:10px;color:var(--text-muted);">→ ${exitData.target || '?'}${movementHint}</span>
                </div>
                <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
                    <span class="state-badge" style="font-size:9px;background:${stateColor}22;color:${stateColor};border:1px solid ${stateColor};padding:1px 6px;border-radius:4px;font-weight:600;">${state.toUpperCase()}</span>
                </div>
            </div>
            ${badgeRow ? window.Lit.unsafeHTML(badgeRow) : window.Lit.nothing}
            ${description ? htmlTag`<div style="font-size:10px;color:var(--text-dim);margin-top:2px;" title="Appearance when closed/locked/blocked">${description}</div>` : window.Lit.nothing}
            ${hasParamPreview ? htmlTag`<div style="font-size:10px;color:var(--text-muted);margin-top:2px;">With parameters resolved: ${resolvedDesc}</div>` : window.Lit.nothing}
            <div style="display:flex;gap:4px;margin-top:4px;">
                ${wayId ? htmlTag`<button class="btn btn-sm btn-ghost" style="font-size:9px;color:var(--accent);" @click=${() => VW.inspector.showNode(wayId)}>🔍 Inspect Way</button>` : window.Lit.nothing}
                <button class="btn btn-sm btn-ghost" style="font-size:9px;color:var(--green);" @click=${() => toggleDoorState(exitName, 'open', wayId)}>🔓 Open</button>
                <button class="btn btn-sm btn-ghost" style="font-size:9px;color:var(--red);" @click=${() => toggleDoorState(exitName, 'close', wayId)}>🔒 Close</button>
            </div>
        </div>`;
    };

    /**
     * Update an environment property on a area node
     * @param {string} nodeId - Graph node ID
     * @param {string} key - Environment property key
     * @param {*} value - New value
     */
    RV._updateEnv = function(nodeId, key, value) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const env = { ...(node.properties?.environment || {}) };
        env[key] = value;
        api.updateNode(nodeId, { properties: { environment: env } }).then(() => worldState.fetch());
    };

    /**
     * Improve area description and environment via AI
     * @param {string} nodeId - Graph node ID
     */
    RV.improveRoomWithAI = async function(nodeId) {
        const system = `You are a procedural area enhancer for a text adventure game. The area data schema supports:

ENVIRONMENT: light (0-100), temperature (C, -50 to 100), air (fresh/stale/humid/toxic/smoky/fragrant), smell (text), noise (quiet/dripping/humming/windy/loud/chaotic/silent)

OUTPUT FORMAT: Respond with ONLY raw JSON. No markdown, no code fences, just JSON.`;

        const buildPrompt = (node, lockedFields) => {
            const name = node.name || '';
            const props = node.properties || {};
            const description = props.description || '';
            const env = props.environment || {};
            return `Area Name: ${name}
Description: ${description}

Current environment:
- light: ${env.light ?? 80}
- temperature: ${env.temperature ?? 21}
- air: ${env.air || 'fresh'}
- smell: ${env.smell || 'neutral'}
- noise: ${env.noise || 'quiet'}

Improve this area's description and environment settings. Make the description much richer — paint a vivid picture with sensory details (sights, sounds, smells, textures, atmosphere). Suggest appropriate environment values that match the mood. Return the full area as JSON with name, description, and environment fields.`;
        };

        const apply = (parsed, node, lockedFields, update) => {
            const props = node.properties || {};
            const env = props.environment || {};
            if (parsed.name) update.name = parsed.name;
            const propUpdate = {};
            if (parsed.description !== undefined) propUpdate.description = parsed.description;
            if (parsed.environment) propUpdate.environment = { ...env, ...parsed.environment };
            if (Object.keys(propUpdate).length > 0) update.properties = propUpdate;
        };

        await InspectorHelpers.improveWithAI(nodeId, { btnId: 'improve-area-btn', system, buildPrompt, apply });
    };

    // Register the template-sync pattern for areas.
    if (window.InspectorTemplateSync) {
        window.InspectorTemplateSync.register('area', {
            title: 'Refresh Area from Library',
            buildWorldPayload(nodeId, node) {
                const name = (node && node.name) || '';
                if (!name) return null;
                if (window.libraryBrowser && libraryBrowser._buildAreaPayload) {
                    return libraryBrowser._buildAreaPayload(name);
                }
                const props = (node && node.properties) || {};
                return {
                    name,
                    description: props.description || '',
                    tags: props.tags || [],
                    environment: props.environment || {},
                };
            },
            sections: [
                { key: 'description', label: 'Description' },
                { key: 'tags', label: 'Tags' },
                { key: 'environment', label: 'Environment' },
                { key: 'items', label: 'Items' },
                { key: 'exits', label: 'Exits' },
                { key: 'triggers', label: 'Triggers' },
            ],
        });
    }

    return RV;
})();
