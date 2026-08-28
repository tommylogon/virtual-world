/**
 * Inspector — Context-sensitive right panel rendering for agents, rooms, items, doors
 * Enhanced with full Actions/Effects/Triggers grid
 */
const inspectorUiHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

class Inspector {
    constructor() {
        this._currentView = null; // { type: 'node', id: string } | { type: 'agent', name: string }
        if (window.appEvents) {
            appEvents.on('state:updated', () => this._reRender());
        }
    }

    _reRender() {
        if (!this._currentView) return;
        // Coalesce state:updated bursts — a full inspector rebuild on every tick
        // fires a large bundle of API calls (graph + library + tag + memory/embed).
        clearTimeout(this._rerenderTimer);
        this._rerenderTimer = setTimeout(() => {
            if (this._currentView.type === 'node') {
                this.showNode(this._currentView.id);
            } else if (this._currentView.type === 'agent') {
                this.showAgent(this._currentView.name);
            }
        }, 250);
    }

    hide() {
        this._currentView = null;
        if (window.events) events.clearAreaFilter();
        const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
        window.InspectorPanel.render(htmlTag`
            <div class="inspector-empty"><div class="inspector-empty-icon">🔍</div><p>Select a node or agent to inspect</p><p class="section-hint">Click on the graph or an agent in the list</p>
                <button class="btn btn-sm" @click=${() => VW.inspector.showWorldLore()} style="margin-top:12px;font-size:12px;padding:6px 16px;">🌍 World Lore</button>
            </div>
        `);
    }

    /** Dispatch to the correct renderer based on node type */
    showRoom(nodeId) { return this.showNode(nodeId); }

    showNode(nodeId) {
        this._currentView = { type: 'node', id: nodeId };
        if (window.appEvents) appEvents.emit('inspector:view', this._currentView);
        if (!worldState.data) return;

        const graphNode = worldState.getNode(nodeId);
        if (graphNode && graphNode.type !== 'area') {
            if (window.events) events.clearAreaFilter();
        }

        if (graphNode) {
            switch (graphNode.type) {
                case 'area': return this._showArea(nodeId, graphNode);
                case 'item': return this._showItem(nodeId, graphNode);
                case 'way': return this._showWay(nodeId, graphNode);
                case 'character': {
                    const player = worldState.players?.[graphNode.name];
                    if (player) return this.showAgent(graphNode.name);
                    window.InspectorPanel.render(this._emptyTemplate(`Character "${graphNode.name}" has no player state.`, 'This node exists in the graph but is not a registered player (e.g. an old bare duplicate). Delete it and duplicate the original character again.'));
                    return;
                }
                case 'logic_trigger': {
                    const parentId = worldState._findTriggerParent(nodeId);
                    if (parentId) {
                        const triggerEdge = worldState._findTriggerEdge(nodeId);
                        if (triggerEdge) {
                            return this._editTriggerFromNode(parentId, JSON.stringify(triggerEdge));
                        }
                        return this.showNode(parentId);
                    }
                    window.InspectorPanel.render(this._emptyTemplate(`Orphaned trigger: ${nodeId}`, 'This trigger node has no parent edge. It may be a stale copy — delete it from the graph.'));
                    return;
                }
            }
        }

        // Fallback: try direct lookup by name
        if (worldState.areas[nodeId]) return this._showArea(nodeId, { name: nodeId, properties: worldState.areas[nodeId], type: 'area' });
        window.InspectorPanel.render(this._emptyTemplate(`Node not found: ${nodeId}`, ''));
    }

    /** Build a lit-html empty-state template for inspector fallbacks. */
    _emptyTemplate(title, hint) {
        const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
        return htmlTag`<div class="inspector-empty"><p>${title}</p>${hint ? htmlTag`<p class="section-hint">${hint}</p>` : ''}</div>`;
    }

    showAgent(agentName) {
        return InspectorAgentView.showAgent(agentName);
    }

    /**
     * Show expanded detail for a timeline entry
     */
    _showTimelineDetail(charName, entryIndex, entryEl) {
        return InspectorAgentView._showTimelineDetail(charName, entryIndex, entryEl);
    }

    // --- Area Inspector ---

    _updateEnv(nodeId, key, value) {
        return InspectorAreaView._updateEnv(nodeId, key, value);
    }

    /** Per-node graph-physics setting, saved with the node. */
    _graphGravityControl(nodeId, props = {}) {
        return InspectorHelpers.graphGravityControl(nodeId, props);
    }

    async _setCentralGravity(nodeId, enabled) {
        return InspectorHelpers.setCentralGravity(nodeId, enabled);
    }

    _showArea(nodeId, graphNode) {
        return InspectorAreaView.showArea(nodeId, graphNode);
    }


    // --- Item Inspector (ENHANCED: Full Actions/Effects/Triggers Grid) ---

    _showItem(nodeId, graphNode) {
        return InspectorItemView.showItem(nodeId, graphNode);
    }

    // --- Way Inspector ---

    _showWay(nodeId, graphNode) {
        return InspectorWayView.showWay(nodeId, graphNode);
    }

    async _reconnectDoor(wayId) {
        return InspectorWayView._reconnectDoor(wayId);
    }

    // --- AI Personality Generation ---

    async _generatePersonality(charName) {
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
            const jm = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
            if (jm) cleaned = jm[1].trim();
            else { const fb = cleaned.indexOf('{'), lb = cleaned.lastIndexOf('}'); if (fb !== -1 && lb > fb) cleaned = cleaned.substring(fb, lb + 1); }
            const parsed = JSON.parse(cleaned);

            const personalityText = parsed.personality || parsed.description || 'A mysterious character.';
            const ta = document.getElementById('inspector-personality');
            if (ta) ta.value = personalityText;
            await ApiClient.updateCharacter(charName, { personality: personalityText });
            events.log(`AI generated personality for ${charName}`, 'system-msg');
        } catch (err) {
            console.error(err);
            toastError('AI generation failed: ' + err.message);
        } finally {
            input.disabled = false;
            input.value = '';
            input.placeholder = 'AI: e.g. \'a cowardly thief\'';
        }
    }

    async _savePersonality(charName) {
        return InspectorHelpers.savePersonality(charName);
    }

    _switchAgentTab(tabName) {
        return InspectorAgentView._switchAgentTab(tabName);
    }

    async _showEquipPicker(charName, slot) {
        return InspectorPaperdoll.showEquipPicker(charName, slot);
    }

    async _showAddItemPicker(charName) {
        return InspectorAgentView._showAddItemPicker(charName);
    }

    async _saveDescription(charName) {
        return InspectorHelpers.saveDescription(charName);
    }

    async _generateDescription(charName) {
        return InspectorAgentView._generateDescription(charName);
    }

    _showStackPopup(badgeEl, charName, slot) {
        return InspectorPaperdoll.showStackPopup(badgeEl, charName, slot);
    }

    _showContextMenu(event, items) {
        event.preventDefault();
        const menu = document.getElementById('context-menu');
        if (!menu) return;
        menu.style.display = 'none';
        window.Lit.render(inspectorUiHtmlTag`${window.Lit.unsafeHTML(items)}`, menu);
        menu.style.display = 'block';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        setTimeout(() => document.addEventListener('click', () => { menu.style.display = 'none'; }, { once: true }), 0);
    }

    _showInventoryContextMenu(event, charName, itemName, itemId) {
        return InspectorPaperdoll.showInventoryContextMenu(event, charName, itemName, itemId);
    }

    _showPaperdollContextMenu(event, charName, slot) {
        return InspectorPaperdoll.showPaperdollContextMenu(event, charName, slot);
    }

    // ─── Save / Import Character ───
    async _saveCharacter(charName) {
        return InspectorAgentView._saveCharacter(charName);
    }

    async _importCharacter() {
        return InspectorAgentView._importCharacter();
    }

    async _killCharacter(charName) {
        return InspectorAgentView._killCharacter(charName);
    }

    async _removeCharacter(charName) {
        return InspectorAgentView._removeCharacter(charName);
    }

    // ─────────── Item helper methods (called from _showItem inline onchange) ───────────

    async _updateItemProp(nodeId, field, value) {
        return InspectorItemView._updateItemProp(nodeId, field, value);
    }

    async _renameNode(oldId, newId) {
        return InspectorHelpers.renameNode(oldId, newId);
    }

    async _moveItem(nodeId) {
        return InspectorItemView._moveItem(nodeId);
    }

    async _moveItemToContainer(nodeId) {
        return InspectorItemView._moveItemToContainer(nodeId);
    }

    _toggleMoveDestType() {
        return InspectorItemView._toggleMoveDestType();
    }

    async _toggleAction(nodeId, action) {
        return InspectorItemView._toggleAction(nodeId, action);
    }

    async _addTriggerToNode(nodeId) {
        const graphNode = worldState.getNode(nodeId);
        if (!graphNode) return;
        if (typeof TriggerEditor === 'undefined') return;
        TriggerEditor.show({
            ...this._triggerEditorOptions(nodeId),
            onSave: async (data) => {
                const triggerId = `trigger_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
                const typeLabel = Array.isArray(data.trigger_type) ? data.trigger_type.join('+') : (data.trigger_type || 'custom');
                const triggerName = (data.name || '').trim() || `${typeLabel} → ${data.effects?.[0]?.type || '?'}`;
                const nodeRes = await ApiClient.createNode({
                    id: triggerId,
                    type: 'logic_trigger',
                    name: triggerName,
                    properties: data
                });
                if (nodeRes?.error) {
                    console.warn('[_addTriggerToNode] trigger node create failed:', nodeRes.error);
                    return;
                }
                await ApiClient.createEdge(nodeId, triggerId, 'triggers', data);
                worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector.showNode(nodeId); });
            }
        });
    }

    _triggerEditorOptions(nodeId) {
        return {
            triggerTypes: TriggerTypes.TRIGGER_TYPES,
            effectTypes: TriggerTypes.EFFECT_TYPES,
            conditionTypes: TriggerTypes.CONDITION_TYPES,
            targetDatalistHtml: InspectorTriggers.getTargetDatalist(),
            itemDatalistHtml: InspectorTriggers.getItemDatalist(),
            contextItemId: nodeId,
            mode: 'multi',
        };
    }

    /**
     * Open the TriggerEditor in edit mode for an existing trigger on a node.
     * @param {string} nodeId - The source node ID (item/way being inspected)
     * @param {string} triggerEdgeJson - JSON string of the trigger edge object
     */
    async _editTriggerFromNode(nodeId, triggerEdgeJson) {
        const graphNode = worldState.getNode(nodeId);
        if (!graphNode) { console.warn('[_editTriggerFromNode] source node not found:', nodeId); return; }
        if (typeof TriggerEditor === 'undefined') { console.warn('[_editTriggerFromNode] TriggerEditor not loaded'); return; }

        let triggerEdge;
        try { triggerEdge = JSON.parse(triggerEdgeJson); } catch (e) { console.warn('[_editTriggerFromNode] bad edge JSON:', triggerEdgeJson); return; }
        const triggerNode = worldState.getNode(triggerEdge.target);
        if (triggerNode && triggerNode.type !== 'logic_trigger') {
            console.warn('[_editTriggerFromNode] target is not a logic_trigger:', triggerNode.type);
            return;
        }
        if (!triggerNode) {
            // Edges created before node-existence was enforced may reference
            // missing trigger nodes — fall back to the edge's data copy.
            console.warn('[_editTriggerFromNode] trigger node missing, using edge properties:', triggerEdge.target);
        }

        // Prefer the trigger node's properties; fall back to the edge copy.
        const nodeProps = triggerNode?.properties && Object.keys(triggerNode.properties).length ? triggerNode.properties : null;
        const props = nodeProps || triggerEdge.properties || {};
        const triggerData = { ...props };
        if (!triggerData.effects) {
            triggerData.effects = [{ type: 'message', params: {} }];
        }
        if (!triggerData.conditions) {
            triggerData.conditions = [];
        }

        TriggerEditor.show({
            ...this._triggerEditorOptions(nodeId),
            initialData: triggerData,
            onSave: async (data) => {
                const updatedProps = { ...data };
                const typeLabel = Array.isArray(data.trigger_type) ? data.trigger_type.join('+') : (data.trigger_type || 'custom');
                const newName = (data.name || '').trim() || `${typeLabel} → ${data.effects?.[0]?.type || '?'}`;
                // Keep node + edge in sync: the runtime reads edge properties first.
                try {
                    let targetId = triggerEdge ? triggerEdge.target : (triggerNode ? triggerNode.id : null);
                    
                    // If the trigger ID embeds a different parent node name (stale copy
                    // pattern), regenerate a clean ID so the stale-copy validator stays
                    // happy and the trigger list stays tidy.
                    if (triggerNode && targetId) {
                        const parentPrefix = `trigger_${nodeId.toLowerCase()}_`;
                        const lowerId = String(targetId).toLowerCase();
                        if (!lowerId.startsWith(parentPrefix) && lowerId.startsWith('trigger_')) {
                            targetId = `trigger_${nodeId.toLowerCase()}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
                        }
                    }
                    
                    // If the ID changed, rename the node first (this updates all edges too)
                    if (triggerNode && targetId && targetId !== triggerNode.id) {
                        await ApiClient.renameNode(triggerNode.id, targetId);
                    }
                    
                    // Update node properties and name
                    if (triggerNode || (triggerEdge && targetId)) {
                        await ApiClient.updateNode(targetId || triggerNode.id, {
                            properties: updatedProps,
                            name: newName
                        });
                    }
                    
                    // Update edge properties
                    if (triggerEdge) {
                        await ApiClient.updateEdge(nodeId, triggerEdge.target, {
                            old_type: 'triggers',
                            properties: updatedProps
                        });
                    }
                } catch (e) {
                    console.warn('[_editTriggerFromNode] save failed:', e);
                }
                worldState.fetch().then(() => {
                    if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
                });
            }
        });
    }

    // ─── Parameter helpers ───

    async _addParam(nodeId) {
        return InspectorHelpers.addParam(nodeId);
    }

    async _removeParam(nodeId, key) {
        return InspectorHelpers.removeParam(nodeId, key);
    }

    async _updateParamKey(nodeId, oldKey, newKey) {
        return InspectorHelpers.updateParamKey(nodeId, oldKey, newKey);
    }

    async _updateParamValue(nodeId, key, value) {
        return InspectorHelpers.updateParamValue(nodeId, key, value);
    }

    async _saveCosts(nodeId) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const actionCosts = node.properties?.action_costs || {};
        const costActions = [
'use', 'take', 'examine', 'eat', 'drink', 'read', 'activate'
];
        const costStats = [
'Energy', 'Hunger', 'Thirst', 'HP'
];
        const inputs = document.querySelectorAll(`.costs-input[data-action][data-stat]`);
        for (const input of inputs) {
            const action = input.dataset.action;
            const stat = input.dataset.stat;
            if (!actionCosts[action]) actionCosts[action] = {};
            actionCosts[action][stat] = parseInt(input.value) || 0;
        }
        await api.updateNode(nodeId, { properties: { action_costs: actionCosts } });
        worldState.fetch();
    }

    async _saveSkillCheck(nodeId) {
        return InspectorHelpers.saveSkillCheck(nodeId);
    }

    // ─── AI Improve Item ───
    async _improveItemWithAI(nodeId) {
        return InspectorItemView._improveItemWithAI(nodeId);
    }

    // ─── AI Improve Area ───

    async _improveRoomWithAI(nodeId) {
        return InspectorAreaView.improveRoomWithAI(nodeId);
    }

    // ─── Behavior Action Types (matching backend _execute_behavior_actions) ───
    // Delegated to InspectorBehaviors

    // ─── Behavior Editor ───

    _addBehavior(charName) {
        return InspectorBehaviors.addBehavior(charName);
    }

    _deleteBehavior(charName, index) {
        return InspectorBehaviors.deleteBehavior(charName, index);
    }

    _editBehavior(charName, index) {
        return InspectorBehaviors.editBehavior(charName, index);
    }

    _saveBehavior(charName, index) {
        return InspectorBehaviors.saveBehavior(charName, index);
    }

    // ─────────── Memory Management ───────────

    _addMemory(charName) {
        return InspectorMemory.addMemory(charName);
    }

    _editMemory(charName, entryId) {
        return InspectorMemory.editMemory(charName, entryId);
    }

    _saveMemory(charName, entryId) {
        return InspectorMemory.saveMemory(charName, entryId);
    }

    _deleteMemory(charName, entryId) {
        return InspectorMemory.deleteMemory(charName, entryId);
    }

    // ─────────── World Lore Editor ───────────

    showWorldLore() {
        this._currentView = { type: 'world_lore' };
        InspectorLore.renderWorldLore();
    }

    async _renderWorldLore() {
        return InspectorLore.renderWorldLore();
    }

    _addLoreEntry() {
        return InspectorLore.addLoreEntry();
    }

    _editLoreEntry(entryId) {
        return InspectorLore.editLoreEntry(entryId);
    }

    async _showLoreEditor(entryId) {
        return InspectorLore.showLoreEditor(entryId);
    }

    async _saveLoreEntry(entryId) {
        return InspectorLore.saveLoreEntry(entryId);
    }

    async _deleteLoreEntry(entryId) {
        return InspectorLore.deleteLoreEntry(entryId);
    }

    async _removeRelationship(agentName, otherName) {
        return InspectorAgentView._removeRelationship(agentName, otherName);
    }

    showTemplates() {
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
        window.Lit.render(inspectorUiHtmlTag`
            <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:520px;max-height:85vh;overflow-y:auto;">
                <h3 style="margin:0 0 12px 0;">📋 Template Parameters</h3>
                <p style="font-size:11px;color:var(--text-muted);margin:0 0 12px 0;">Use these in trigger messages, descriptions, and effects. They are replaced at runtime.</p>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div style="background:var(--bg-inset);border-radius:6px;padding:8px;">
                        <div style="font-size:10px;font-weight:600;color:var(--pink);margin-bottom:4px;">🌍 World</div>
                        <div style="font-size:11px;line-height:1.8;">
                            <div><code>{game_time}</code> — current time (HH:MM:SS)</div>
                            <div><code>{time_ticks}</code> — total ticks elapsed</div>
                            <div><code>{turn_number}</code> — current turn</div>
                        </div>
                    </div>
                    <div style="background:var(--bg-inset);border-radius:6px;padding:8px;">
                        <div style="font-size:10px;font-weight:600;color:var(--orange);margin-bottom:4px;">🧍 Player</div>
                        <div style="font-size:11px;line-height:1.8;">
                            <div><code>{player_name}</code> — active character</div>
                            <div><code>{player_hp}</code> — current HP</div>
                            <div><code>{player_energy}</code> — current Energy</div>
                            <div><code>{player_sanity}</code> — current Sanity</div>
                        </div>
                    </div>
                    <div style="background:var(--bg-inset);border-radius:6px;padding:8px;">
                        <div style="font-size:10px;font-weight:600;color:var(--green);margin-bottom:4px;">📦 Item</div>
                        <div style="font-size:11px;line-height:1.8;">
                            <div><code>{item_name}</code> — item name</div>
                            <div><code>{item_state}</code> — current state</div>
                            <div><code>{item_description}</code> — description text</div>
                            <div><code>{item_properties}</code> — full props dict</div>
                            <div><code>{item_params}</code> — parameters dict</div>
                            <div><code>{uses}</code> — remaining uses</div>
                            <div><code>{weight}</code> — item weight</div>
                        </div>
                    </div>
                    <div style="background:var(--bg-inset);border-radius:6px;padding:8px;">
                        <div style="font-size:10px;font-weight:600;color:var(--blue);margin-bottom:4px;">🌍 Area</div>
                        <div style="font-size:11px;line-height:1.8;">
                            <div><code>{area_name}</code> — current area</div>
                            <div><code>{area_light}</code> — light level</div>
                            <div><code>{area_temp}</code> — temperature</div>
                            <div><code>{area_smell}</code> — smell text</div>
                        </div>
                    </div>
                    <div style="background:var(--bg-inset);border-radius:6px;padding:8px;">
                        <div style="font-size:10px;font-weight:600;color:var(--purple);margin-bottom:4px;">🎯 Target</div>
                        <div style="font-size:11px;line-height:1.8;">
                            <div><code>{target_name}</code> — on_use_on target</div>
                        </div>
                    </div>
                    <div style="background:var(--bg-inset);border-radius:6px;padding:8px;">
                        <div style="font-size:10px;font-weight:600;color:var(--text-muted);margin-bottom:4px;">🩹 Conditions</div>
                        <div style="font-size:11px;line-height:1.8;">
                            <div><code>{condition}</code> — active condition id</div>
                            <div><code>{condition_severity}</code> — level</div>
                            <div><code>{condition_duration}</code> — ticks left</div>
                            <div><code>{condition_cause}</code> — source</div>
                            <div><code>{condition_effects}</code> — effect text</div>
                        </div>
                    </div>
                </div>
                <div style="margin-top:12px;text-align:right;">
                    <button class="btn btn-green" @click=${() => overlay.remove()}>Close</button>
                </div>
            </div>
        `, overlay);
        document.body.appendChild(overlay);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });
    }

}

// Singleton
const inspector = new Inspector();

