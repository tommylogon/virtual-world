/**
 * InspectorTriggers — Trigger system helpers for the Inspector
 * Extracted from inspector.js for modularity.
 * Handles display and removal of trigger edges on item/way nodes.
 */

window.InspectorTriggers = (() => {
    const T = {};

    /**
     * Remove a trigger edge and its associated logic_trigger node
     * @param {string} nodeId - The source node ID (item/way being inspected)
     * @param {string} source - Edge source node ID
     * @param {string} target - Edge target node ID (logic_trigger)
     */
    T.removeTriggerFromNode = async function(nodeId, source, target) {
        if (!confirm('Remove this trigger?')) return;
        await ApiClient.deleteEdge(source, target, 'triggers');
        const triggerNode = worldState.getNode(target);
        if (triggerNode && triggerNode.type === 'logic_trigger') {
            await ApiClient.deleteNode(target);
        }
        worldState.fetch().then(() => {
            if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
        });
    };

    /**
     * Build HTML option list of all way nodes in the graph
     * @returns {string} HTML option elements
     */
    T.getDoorOptions = function() {
        const doors = [];
        if (worldState.graph?.nodes) {
            for (const [id, node] of Object.entries(worldState.graph.nodes)) {
                if (node.type === 'way') {
                    doors.push({ id, name: node.name || id });
                }
            }
        }
        return doors.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
    };

    /**
     * Build searchable datalist options for on_use_on target: exits, doors, area items
     * @returns {string} HTML option elements for a datalist
     */
    T.getTargetDatalist = function() {
        const seen = new Set();
        const opts = [];

        if (worldState.graph?.nodes) {
            for (const [id, node] of Object.entries(worldState.graph.nodes)) {
                const lbl = node.name || id;
                if (node.type === 'way' && !seen.has(lbl)) {
                    seen.add(lbl);
                    opts.push({ value: lbl, label: `🚪 ${lbl}` });
                }
            }
        }

        if (worldState.areas) {
            for (const [areaName, area] of Object.entries(worldState.areas)) {
                if (area.exits) {
                    for (const [dir, exit] of Object.entries(area.exits)) {
                        if (!seen.has(dir)) {
                            seen.add(dir);
                            const targetName = exit.target || '';
                            opts.push({ value: dir, label: `🚪 ${dir} → ${targetName}` });
                        }
                        if (exit.way_id && !seen.has(exit.way_id)) {
                            seen.add(exit.way_id);
                            opts.push({ value: exit.way_id, label: `🚪 ${exit.way_id}` });
                        }
                    }
                }
                if (area.items) {
                    for (const item of area.items) {
                        const itemName = item.name || item.id || item;
                        if (!seen.has(itemName)) {
                            seen.add(itemName);
                            opts.push({ value: itemName, label: `📦 ${itemName}` });
                        }
                    }
                }
            }
        }

        opts.sort((a, b) => a.value.localeCompare(b.value));
        return opts.map(o => `<option value="${o.value}">${o.label}</option>`).join('');
    };

    /**
     * Build searchable datalist options for spawn/give/remove item fields.
     * @returns {string} HTML option elements for a datalist
     */
    T.getItemDatalist = function() {
        const seen = new Set();
        const opts = [];
        if (worldState.graph?.nodes) {
            for (const [id, node] of Object.entries(worldState.graph.nodes)) {
                if (node.type !== 'item') continue;
                const lbl = node.name || id;
                if (!seen.has(lbl)) {
                    seen.add(lbl);
                    opts.push({ value: lbl, label: `📦 ${lbl}` });
                }
                if (id !== lbl && !seen.has(id)) {
                    seen.add(id);
                    opts.push({ value: id, label: `📦 ${id}` });
                }
            }
        }
        opts.sort((a, b) => a.value.localeCompare(b.value));
        return opts.map(o => `<option value="${o.value}">${o.label}</option>`).join('');
    };

    /**
     * Build the triggers section of an item/way inspector as a lit template
     * @param {string} nodeId - Graph node ID
     * @param {string[]} lockedFields - Currently locked fields
     * @returns {TemplateResult}
     */
    T.buildTriggersHtml = function(nodeId, lockedFields) {
        const triggers = [];
        const locked = lockedFields || [];
        const nodeIdLower = String(nodeId).toLowerCase();
        if (worldState.graph?.edges) {
            for (const edge of worldState.graph.edges) {
                if (String(edge.source).toLowerCase() === nodeIdLower && edge.type === 'triggers') {
                    triggers.push(edge);
                }
            }
        }

        const lockToggle = typeof InspectorHelpers !== 'undefined'
            ? InspectorHelpers.renderLockToggle('triggers', locked, nodeId)
            : window.Lit.nothing;
        const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
        const nothing = window.Lit.nothing;

        return htmlTag`<div class="inspector-section">
            <h3 style="display:flex;justify-content:space-between;align-items:center;">
                <span>${lockToggle} ⚡ Triggers</span>
                <div style="display:flex;gap:3px;">
                    <button class="btn btn-sm" @click=${() => T._openGraphEditor(nodeId)} style="font-size:10px;">🧩 Graph</button>
                    <button class="btn btn-sm" @click=${() => T.validateNode(nodeId)} style="font-size:10px;" title="Scan this node's triggers for broken references">⚠ Validate</button>
                    <button class="btn btn-sm btn-blue" @click=${() => VW.inspector._addTriggerToNode(nodeId)}>➕ Add</button>
                </div>
            </h3>
            <div style="max-height:300px;overflow-y:auto;">
                ${triggers.length > 0
                    ? triggers.map((trigger) => {
                const triggerType = trigger.properties?.trigger_type || '?';
                const effectsList = trigger.properties?.effects || [];
                const conditionsList = trigger.properties?.conditions || [];
                const firstEff = effectsList[0] || {};
                const effectType = effectsList.length > 0 ? (firstEff.type || 'unknown') : 'none';
                const effectParams = firstEff.params || {};
                const message = effectParams.success_message || effectParams.message || '';
                const condition = conditionsList[0] || null;

                // Build effect summary
                let effectDetail = effectType;
                if (effectType === 'damage' && effectParams.amount) effectDetail += ` (${effectParams.amount})`;
                else if (effectType === 'heal' && effectParams.amount) effectDetail += ` (${effectParams.amount} ${effectParams.stat || 'HP'})`;
                else if (effectType === 'adjust_vital') effectDetail += ` (${effectParams.stat||'HP'} ${effectParams.amount > 0 ? '+' : ''}${effectParams.amount})`;
                else if (effectType === 'adjust_environment') {
                    const parts = [];
                    if (effectParams.temperature !== undefined) parts.push(`temp${effectParams.temperature > 0 ? '+' : ''}${effectParams.temperature}`);
                    if (effectParams.light !== undefined) parts.push(`light${effectParams.light > 0 ? '+' : ''}${effectParams.light}`);
                    if (parts.length) effectDetail += ` (${parts.join(', ')})`;
                }
                else if (effectType === 'spawn_item' && effectParams.item_id) effectDetail += ` (${effectParams.item_id})`;
                else if (effectType === 'give_item' && effectParams.item_id) effectDetail += ` → ${effectParams.target || 'self'}: ${effectParams.item_id}`;
                else if (effectType === 'save') {
                    const check = effectParams.stat || effectParams.skill || 'WIS';
                    effectDetail += ` (${check} DC${effectParams.dc || 12})`;
                }
                else if ((effectType === 'add_tag' || effectType === 'remove_tag') && effectParams.tag) {
                    effectDetail += ` (${effectParams.tag} → ${effectParams.node_id || 'self'})`;
                }
                else if (effectType === 'set_environment') {
                    const parts = ['light','temperature','air','smell','noise'].filter(k => effectParams[k] !== undefined).map(k => `${k}:${effectParams[k]}`);
                    if (parts.length) effectDetail += ` (${parts.join(', ')})`;
                }
                else if (effectType === 'set_state' && effectParams.state) effectDetail += ` (${effectParams.state})`;
                else if (effectType === 'teleport' && effectParams.area) effectDetail += ` → ${effectParams.area}`;
                else if (effectType === 'unlock_way' && effectParams.way_id) effectDetail += ` (${effectParams.way_id})`;
                else if (effectType === 'rename' && (effectParams.name || effectParams.new_name)) effectDetail += ` → ${effectParams.name || effectParams.new_name}`;
                else if (effectType === 'remove_item' && effectParams.item_id) effectDetail += ` (${effectParams.item_id})`;
                else if (effectType === 'set_description' && (effectParams.value || effectParams.description)) {
                    const descVal = effectParams.value || effectParams.description || '';
                    effectDetail += ` (${descVal.substring(0, 30)}${descVal.length > 30 ? '...' : ''})`;
                }
                else if (effectType === 'append_description' && effectParams.text) effectDetail += ` +"${(effectParams.text||'').substring(0,25)}${(effectParams.text||'').length > 25 ? '...' : ''}"`;
                else if (effectType === 'apply_trait' || effectType === 'remove_trait') effectDetail += ` (${effectParams.trait || '?'}${effectParams.target && effectParams.target !== 'self' ? ' → ' + effectParams.target : ''}${effectType === 'apply_trait' && effectParams.param !== undefined && effectParams.param !== true ? '=' + effectParams.param : ''})`;
                else if (effectType === 'apply_condition' || effectType === 'remove_condition') effectDetail += ` (${effectParams.condition || '?'}${effectParams.target && effectParams.target !== 'self' ? ' → ' + effectParams.target : ''}${effectParams.duration ? ', ' + effectParams.duration + 't' : ''})`;

                const conditionStr = condition ? `${condition.type}${condition.value !== undefined ? `=${condition.value}` : condition.skill ? `(${condition.skill} DC${condition.dc})` : ''}` : null;

                        return htmlTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:6px;margin-bottom:4px;">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <strong>${triggerType}</strong>
                                <div>
                                    <button class="btn btn-sm" @click=${() => VW.inspector._editTriggerFromNode(nodeId, JSON.stringify(trigger))} style="font-size:10px;">✏️</button>
                                    <button class="btn btn-sm btn-red" @click=${() => T.removeTriggerFromNode(nodeId, trigger.source, trigger.target)} style="font-size:10px;">✕</button>
                                </div>
                            </div>
                            <div style="font-size:10px;color:var(--text-dim);margin-top:2px;">Effect: ${effectDetail}</div>
                            ${message ? htmlTag`<div style="font-size:10px;color:var(--text-muted);">${message}</div>` : nothing}
                            ${conditionStr ? htmlTag`<div style="font-size:10px;color:var(--pink);">Condition: ${conditionStr}</div>` : nothing}
                        </div>`;
                    })
                    : htmlTag`<div style="font-size:11px;color:var(--text-muted);padding:8px;">No triggers. Click + Add to add one.</div>`}
            </div>
            <div id="validator-inline-${nodeId}" class="validator-inline" style="display:none;border-top:1px solid var(--border-light);margin-top:4px;padding-top:4px;"></div>
        </div>`;
    };

    /**
     * Validate this node's triggers and show the issues inline below the
     * trigger list. Clickable jump buttons open the owning node in the
     * inspector + graph.
     */
    T.validateNode = async function(nodeId) {
        if (!window.ValidatorPanel) {
            toastInfo('Trigger validation not loaded yet.');
            return;
        }
        const container = document.getElementById(`validator-inline-${nodeId}`);
        if (container) {
            container.style.display = container.style.display === 'none' ? 'block' : 'none';
            if (container.style.display === 'block') {
                await window.ValidatorPanel.validateNodeInline(nodeId, container);
            }
        } else {
            toastInfo('Validation area not found.');
        }
    };

    T._openGraphEditor = function(escId) {
        const nodeId = escId.replace(/\\'/g, "'");
        const nodeIdLower = String(nodeId).toLowerCase();
        const triggerEdges = [];
        const triggers = [];
        if (worldState.graph?.edges) {
            for (const edge of worldState.graph.edges) {
                if (String(edge.source).toLowerCase() === nodeIdLower && edge.type === 'triggers') {
                    triggerEdges.push(edge);
                    const props = edge.properties || {};
                    const rawConds = props.conditions || (props.condition ? [props.condition] : []);
                    triggers.push({
                        trigger_type: props.trigger_type || 'on_use',
                        effects: props.effects || (props.effect_type ? [{ type: props.effect_type, params: props.effect_params || {} }] : []),
                        conditions: rawConds,
                        target_name: props.target_name || '',
                        target_state: props.target_state || ''
                    });
                }
            }
        }
        if (triggers.length > 1 && typeof toastInfo === 'function') {
            toastInfo('Graph editor edits the first trigger only — use ✏️ for others.');
        }
        const primaryEdge = triggerEdges[0] || null;
        const triggerData = triggers[0] || {};
        const graph = TriggerGraph.triggerToGraph(triggerData);

        const persistCompiled = async (compiled) => {
            if (!compiled) return;
            const typeLabel = Array.isArray(compiled.trigger_type)
                ? compiled.trigger_type.join('+')
                : (compiled.trigger_type || 'custom');
            const triggerName = `${typeLabel} → ${compiled.effects?.[0]?.type || '?'}`;

            if (primaryEdge) {
                const triggerId = primaryEdge.target;
                await ApiClient.updateNode(triggerId, {
                    properties: compiled,
                    name: triggerName
                });
                await ApiClient.updateEdge(nodeId, triggerId, {
                    old_type: 'triggers',
                    properties: compiled
                });
            } else {
                const triggerId = `trigger_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
                const nodeRes = await ApiClient.createNode({
                    id: triggerId,
                    type: 'logic_trigger',
                    name: triggerName,
                    properties: compiled
                });
                if (nodeRes?.error) {
                    console.warn('[GraphEditor] trigger node create failed:', nodeRes.error);
                    return;
                }
                await ApiClient.createEdge(nodeId, triggerId, 'triggers', compiled);
            }
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector.showNode(nodeId); });
        };

        TriggerGraph.show({
            graph,
            contextItemId: nodeId,
            sourceNodeId: nodeId,
            editorBridge: {
                ...(window.VW?.inspector?._triggerEditorOptions(nodeId) || {}),
                initialName: primaryEdge ? (worldState.getNode(primaryEdge.target)?.name || '') : '',
                success_message: triggerData.success_message || '',
                fail_message: triggerData.fail_message || '',
                onSave: async (data) => persistCompiled(data),
            },
            onSave: async (newGraph) => {
                const compiled = TriggerGraph.compileToEngine(newGraph);
                await persistCompiled(compiled);
            }
        });
    };

    /**
     * Build the container contents section as a lit template
     * @param {string} nodeId - Graph node ID
     * @returns {TemplateResult}
     */
    T.buildContentsHtml = function(nodeId) {
        const contained = [];
        if (worldState.graph?.edges) {
            for (const edge of worldState.graph.edges) {
                if (edge.target === nodeId && edge.type === 'in') {
                    const cn = worldState.getNode(edge.source);
                    contained.push({ id: edge.source, name: cn?.name || edge.source, node: cn });
                }
            }
        }
        const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
        const nothing = window.Lit.nothing;

        let total = 0;
        for (const c of contained) {
            const w = c.node?.properties?.weight;
            if (w != null && !isNaN(parseFloat(w))) total += parseFloat(w);
        }

        return htmlTag`<div class="inspector-section">
            <h3>📦 Container Contents</h3>
            ${contained.length > 0
                ? htmlTag`<div style="display:flex;flex-direction:column;gap:2px;">
                    ${contained.map((c) => {
                        const w = c.node?.properties?.weight;
                        return htmlTag`<div class="relationship-item" @click=${() => VW.inspector.showNode(c.id)} style="cursor:pointer;display:flex;justify-content:space-between;align-items:center;">
                            <span class="rel-node">📦 ${c.name}</span>
                            ${w != null && !isNaN(parseFloat(w)) ? htmlTag`<span style="font-size:9px;color:var(--text-dim);white-space:nowrap;">⚖️ ${w} kg</span>` : nothing}
                        </div>`;
                    })}
                </div>
                ${total > 0 ? htmlTag`<div style="text-align:right;font-size:10px;color:var(--text-dim);padding-top:2px;">⚖️ Total: ${total.toFixed(1)} kg</div>` : nothing}`
                : htmlTag`<div style="font-size:11px;color:var(--text-muted);">No contained items.</div>`}
        </div>`;
    };

    return T;
})();
