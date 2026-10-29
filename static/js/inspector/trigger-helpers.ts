/**
 * InspectorTriggers — Trigger system helpers for the Inspector
 * Extracted from inspector.js for modularity.
 * Handles display and removal of trigger edges on item/way nodes.
 *
 * @module inspector/trigger-helpers — trigger display/removal for item & way inspectors
 * @contributes InspectorTriggers: list a node's trigger edges, remove one, open the trigger editor
 * @powers viewing and editing the triggers attached to an item or way
 * @relates renders through InspectorPanel; used by item-view + way-view
 * @docs docs/virtualWorld/Rules Engine/Triggers & Effects.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

// `InspectorTriggers` is already declared as an ambient global const in
// types/globals.d.ts, so the local binding is prefixed to avoid TS2451.
const _InspectorTriggers = (() => {
    const api: TriggerHelpersApi = {} as TriggerHelpersApi;

    /** ApiClient surface this module uses beyond the declared shared shape. */
    function _api(): TriggerApiClient {
        return ApiClient as unknown as TriggerApiClient;
    }

    /** TriggerGraph (graph/trigger-graph.js) is not declared in globals.d.ts. */
    function _triggerGraph(): TriggerGraphApi {
        return (window as unknown as { TriggerGraph: TriggerGraphApi }).TriggerGraph;
    }

    /**
     * Remove a trigger edge and its associated logic_trigger node
     * @param nodeId - The source node ID (item/way being inspected)
     * @param source - Edge source node ID
     * @param target - Edge target node ID (logic_trigger)
     */
    api.removeTriggerFromNode = async function(nodeId: string, source: string, target: string) {
        const ok = await (window as any).Dialog?.confirm?.({
            title: 'Remove Trigger',
            message: 'Remove this trigger?',
            danger: true
        });
        if (!ok) return;
        const node = worldState.getNode(nodeId);
        const TG = (window as unknown as { TriggerGraph?: TriggerGraphApi }).TriggerGraph;
        if (node) {
            const current = TG
                ? TG.normalizeTriggerList((node.properties as any)?.triggers)
                : (Array.isArray(node.properties?.triggers) ? node.properties.triggers : []);
            const updated = current.filter((t: any) => t && t.id !== target);
            if (updated.length !== current.length) {
                await _api().updateNode(nodeId, { properties: { ...node.properties, triggers: updated } });
            }
        }
        // Only a legacy edge needs deleting; a property entry has none.
        if (target && api._getNodeTriggers(nodeId).some((edge) => edge.target === target)) {
            await _api().deleteEdge(source, target, 'triggers');
        }
        const triggerNode = worldState.getNode(target);
        if (triggerNode && triggerNode.type === 'logic_trigger') {
            await _api().deleteNode(target);
        }
        worldState.fetch().then(() => {
            if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
        });
    };

    /**
     * Build HTML option list of all way nodes in the graph
     * @returns {string} HTML option elements
     */
    api.getDoorOptions = function(): string {
        const doors: Array<{ id: string; name: string }> = [];
        if (worldState.graph?.nodes) {
            for (const [id, node] of Object.entries(worldState.graph.nodes as Record<string, TriggerHelpersGraphNode>)) {
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
    api.getTargetDatalist = function(): string {
        const seen = new Set<string>();
        const opts: Array<{ value: string; label: string }> = [];

        if (worldState.graph?.nodes) {
            for (const [id, node] of Object.entries(worldState.graph.nodes as Record<string, TriggerHelpersGraphNode>)) {
                const lbl = node.name || id;
                if (node.type === 'way' && !seen.has(lbl)) {
                    seen.add(lbl);
                    opts.push({ value: lbl, label: `🚪 ${lbl}` });
                }
            }
        }

        if (worldState.areas) {
            for (const [, area] of Object.entries(worldState.areas as Record<string, WorldArea>)) {
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
                        const itemName = (item && typeof item === 'object' ? item.name || item.id : item) as string;
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
    api.getItemDatalist = function(): string {
        const seen = new Set<string>();
        const opts: Array<{ value: string; label: string }> = [];
        if (worldState.graph?.nodes) {
            for (const [id, node] of Object.entries(worldState.graph.nodes as Record<string, TriggerHelpersGraphNode>)) {
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
     * @param nodeId - Graph node ID
     * @param lockedFields - Currently locked fields
     */
    api.buildTriggersHtml = function(nodeId: string, lockedFields?: string[]) {
        const locked = lockedFields || [];
        // One reader for both stores (properties first, legacy edges deduped by
        // id), so the card, the suggest diff and the graph editor agree.
        const triggers = api._getNodeTriggerData(nodeId);

        const lockToggle = typeof InspectorHelpers !== 'undefined'
            ? InspectorHelpers.renderLockToggle('triggers', locked, nodeId)
            : window.Lit.nothing;
        const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);
        const nothing = window.Lit.nothing;

        /** Short human label for one effect, e.g. `adjust_vital (HP -10)`. */
        const effectLabel = (eff: TriggerHelpersTriggerEffect): string => {
            const effectType = eff?.type || 'unknown';
            const effectParams = eff?.params || {};
            let detail = effectType;
            if (effectType === 'damage' && effectParams.amount) detail += ` (${effectParams.amount})`;
            else if (effectType === 'heal' && effectParams.amount) detail += ` (${effectParams.amount} ${effectParams.stat || 'HP'})`;
            else if (effectType === 'adjust_vital') detail += ` (${effectParams.stat||'HP'} ${effectParams.amount > 0 ? '+' : ''}${effectParams.amount})`;
            else if (effectType === 'adjust_environment') {
                const parts = [];
                if (effectParams.temperature !== undefined) parts.push(`temp${effectParams.temperature > 0 ? '+' : ''}${effectParams.temperature}`);
                if (effectParams.light !== undefined) parts.push(`light${effectParams.light > 0 ? '+' : ''}${effectParams.light}`);
                if (parts.length) detail += ` (${parts.join(', ')})`;
            }
            else if (effectType === 'spawn_item' && effectParams.item_id) detail += ` (${effectParams.item_id})`;
            else if (effectType === 'give_item' && effectParams.item_id) detail += ` → ${effectParams.target || 'self'}: ${effectParams.item_id}`;
            else if (effectType === 'save') {
                const check = effectParams.stat || effectParams.skill || 'WIS';
                detail += ` (${check} DC${effectParams.dc || 12})`;
            }
            else if ((effectType === 'add_tag' || effectType === 'remove_tag') && effectParams.tag) {
                detail += ` (${effectParams.tag} → ${effectParams.node_id || 'self'})`;
            }
            else if (effectType === 'set_environment') {
                const parts = ['light','temperature','air','smell','noise'].filter(k => effectParams[k] !== undefined).map(k => `${k}:${effectParams[k]}`);
                if (parts.length) detail += ` (${parts.join(', ')})`;
            }
            else if (effectType === 'set_state' && effectParams.state) detail += ` (${effectParams.state})`;
            else if (effectType === 'teleport' && effectParams.area) detail += ` → ${effectParams.area}`;
            else if (effectType === 'unlock_way' && effectParams.way_id) detail += ` (${effectParams.way_id})`;
            else if (effectType === 'rename' && (effectParams.name || effectParams.new_name)) detail += ` → ${effectParams.name || effectParams.new_name}`;
            else if (effectType === 'remove_item' && effectParams.item_id) detail += ` (${effectParams.item_id})`;
            else if (effectType === 'set_description' && (effectParams.value || effectParams.description)) {
                const descVal = effectParams.value || effectParams.description || '';
                detail += ` (${descVal.substring(0, 30)}${descVal.length > 30 ? '...' : ''})`;
            }
            else if (effectType === 'append_description' && effectParams.text) detail += ` +"${(effectParams.text||'').substring(0,25)}${(effectParams.text||'').length > 25 ? '...' : ''}"`;
            else if (effectType === 'apply_trait' || effectType === 'remove_trait') detail += ` (${effectParams.trait || '?'}${effectParams.target && effectParams.target !== 'self' ? ' → ' + effectParams.target : ''}${effectType === 'apply_trait' && effectParams.param !== undefined && effectParams.param !== true ? '=' + effectParams.param : ''})`;
            else if (effectType === 'apply_condition' || effectType === 'remove_condition') detail += ` (${effectParams.condition || '?'}${effectParams.target && effectParams.target !== 'self' ? ' → ' + effectParams.target : ''}${effectParams.duration ? ', ' + effectParams.duration + 't' : ''})`;
            return detail;
        };

        /** Short label for one leaf condition. */
        const conditionLabel = (cond: TriggerCondition | null): string => {
            if (!cond) return '';
            const anyCond = cond as any;
            return `${cond.type}${anyCond.value !== undefined ? `=${anyCond.value}` : cond.skill ? `(${cond.skill} DC${cond.dc})` : ''}`;
        };

        return htmlTag`<div class="inspector-section">
            <h3 style="display:flex;flex-wrap:wrap;gap:4px;justify-content:space-between;align-items:center;">
                <span>${lockToggle} ⚡ Triggers</span>
                <div style="display:flex;flex-wrap:wrap;gap:3px;justify-content:flex-end;">
                    <button class="btn btn-sm" @click=${() => api._openGraphEditor(nodeId)} style="font-size:10px;">🧩 Graph</button>
                    <button class="btn btn-sm" @click=${() => api.validateNode(nodeId)} style="font-size:10px;" title="Scan this node's triggers for broken references">⚠ Validate</button>
                    <button class="btn btn-sm" @click=${(e: Event) => api.suggestForNode(nodeId, false, e.currentTarget as HTMLButtonElement)} style="font-size:10px;background:var(--bg-inset);border-color:var(--orange);color:var(--orange);" title="Suggest a full set of useful triggers from this node (no AI)">⚡ Suggest</button>
                    <button class="btn btn-sm" @click=${(e: Event) => api.suggestForNode(nodeId, true, e.currentTarget as HTMLButtonElement)} style="font-size:10px;background:var(--bg-inset);border-color:var(--blue);color:var(--blue);" title="Ask the LLM to suggest a full set of useful triggers (AI)">✨ Suggest (AI)</button>
                    <button class="btn btn-sm btn-blue" @click=${() => VW.inspector._addTriggerToNode(nodeId)}>➕ Add</button>
                </div>
            </h3>
            <div style="max-height:300px;overflow-y:auto;">
                ${triggers.length > 0
                    ? triggers.map((def) => {
                // Every effect and every condition, not just the first: this
                // card is the only surface that lists a node's whole trigger set.
                const rawTriggerType = def.trigger_type || '?';
                const triggerType = Array.isArray(rawTriggerType) ? rawTriggerType.join(', ') : rawTriggerType;
                const effectsList: TriggerHelpersTriggerEffect[] = def.effects || [];
                const conds = def.conditions as { operator?: string; conditions?: unknown[] } | undefined;
                const conditionsList: unknown[] = Array.isArray(conds) ? conds : (conds?.conditions || []);
                const messageEffect = effectsList.find((e) => e?.params && (e.params.message || e.params.success_message));
                const message = messageEffect?.params?.message || messageEffect?.params?.success_message || '';
                const effectDetail = effectsList.length ? effectsList.map(effectLabel).join(' · ') : 'none';
                const effectPrefix = effectsList.length > 1 ? `${effectsList.length} effects: ` : '';
                const conditionStr = conditionsList.length
                    ? conditionsList.map((c) => conditionLabel(c as TriggerCondition)).join(' · ')
                    : null;
                const conditionPrefix = conditionsList.length > 1
                    ? `Conditions${conds?.operator ? ` (${conds.operator})` : ''}: `
                    : 'Condition: ';
                const triggerId = def.id || '';

                        return htmlTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:6px;margin-bottom:4px;">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <strong>${triggerType}</strong>
                                <div>
                                    <button class="btn btn-sm" @click=${() => VW.inspector._editTriggerFromNode(nodeId, JSON.stringify(def))} style="font-size:10px;">✏️</button>
                                    <button class="btn btn-sm btn-red" @click=${() => api.removeTriggerFromNode(nodeId, nodeId, triggerId)} style="font-size:10px;">✕</button>
                                </div>
                            </div>
                            <div style="font-size:10px;color:var(--text-dim);margin-top:2px;">Effect: ${effectPrefix}${effectDetail}</div>
                            ${message ? htmlTag`<div style="font-size:10px;color:var(--text-muted);">${message}</div>` : nothing}
                            ${conditionStr ? htmlTag`<div style="font-size:10px;color:var(--pink);">${conditionPrefix}${conditionStr}</div>` : nothing}
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
    api.validateNode = async function(nodeId: string) {
        const panel = (window as unknown as { ValidatorPanel?: ValidatorPanelApi }).ValidatorPanel;
        if (!panel) {
            toastInfo('Trigger validation not loaded yet.');
            return;
        }
        const container = document.getElementById(`validator-inline-${nodeId}`);
        if (container) {
            container.style.display = container.style.display === 'none' ? 'block' : 'none';
            if (container.style.display === 'block') {
                await panel.validateNodeInline(nodeId, container);
            }
        } else {
            toastInfo('Validation area not found.');
        }
    };

    api._openGraphEditor = function(escId: string) {
        const nodeId = escId.replace(/\\'/g, "'");
        const TG = _triggerGraph();
        // properties.triggers is the authoritative store; legacy edges are read
        // and deduped by id. Every trigger is drawn, one root block each.
        const triggers = api._getNodeTriggerData(nodeId);
        const graph = TG.triggersToGraph(triggers);

        const persistDefinitions = async (defs: TriggerDef[]) => {
            if (!defs.length) return;
            const node = worldState.getNode(nodeId);
            if (!node) return;
            const current = TG.normalizeTriggerList((node.properties as any)?.triggers);
            const byId = new Map<string, TriggerDef>();
            for (const trigger of current) {
                if (trigger && trigger.id) byId.set(String(trigger.id), trigger);
            }
            const next: TriggerDef[] = [];
            for (const def of defs) {
                if (!def) continue;
                const id = String(def.id || `trigger_${nodeId}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`);
                // Merge over the stored entry so fields the graph has no widget
                // for (once, fired, cooldown, name) survive a canvas save.
                next.push({ ...(byId.get(id) || {}), ...def, id });
            }
            await _api().updateNode(nodeId, {
                properties: { ...node.properties, triggers: next },
            });
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector.showNode(nodeId); });
        };

        TG.show({
            graph,
            contextItemId: nodeId,
            sourceNodeId: nodeId,
            editorBridge: {
                ...(window.VW?.inspector?._triggerEditorOptions(nodeId) || {}),
                initialName: triggers[0]?.name || '',
                fail_message: triggers[0]?.fail_message || '',
                onSave: async (data: TriggerDef) => persistDefinitions([data]),
            },
            onSave: async (newGraph: unknown) => {
                const defs = TG.compileToTriggers(newGraph);
                const refused = defs.find((def) => TG.compileError(def));
                if (refused && TG.reportCompileError(refused)) return;
                await persistDefinitions(defs);
            }
        });
    };

    /**
     * Collect the trigger edges (source node → logic_trigger) for a node.
     * @param nodeId - Graph node ID
     * @returns trigger edges
     */
    api._getNodeTriggers = function(nodeId: string): TriggerHelpersGraphEdge[] {
        const out: TriggerHelpersGraphEdge[] = [];
        const lower = String(nodeId).toLowerCase();
        if (worldState.graph?.edges) {
            for (const edge of worldState.graph.edges as TriggerHelpersGraphEdge[]) {
                if (String(edge.source).toLowerCase() === lower && edge.type === 'triggers') {
                    out.push(edge);
                }
            }
        }
        return out;
    };

    /**
     * Create a trigger on a node by appending to properties.triggers, the
     * authoritative store (task-886).
     * @param nodeId - Source node ID
     * @param data   - Trigger data ({ trigger_type, effects, conditions, ... })
     */
    api.createTriggerOnNode = async function(nodeId: string, data: TriggerDef) {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const current = _triggerGraph().normalizeTriggerList((node.properties as any)?.triggers);
        const triggerId = `trigger_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
        current.push({ ...data, id: triggerId });
        await _api().updateNode(nodeId, {
            properties: { ...node.properties, triggers: current },
        });
    };

    /**
     * Build input fields for the trigger suggesters from a live graph node.
     * @param nodeId - Graph node ID
     * @returns { kind, name, description, tags, actions, uses, current_state, requires }
     */
    api._suggestFieldsForNode = function(nodeId: string): SuggestFields | null {
        const node = worldState.getNode(nodeId);
        if (!node) return null;
        const props = node.properties || {};
        const actions = Array.isArray(props.actions)
            ? props.actions
            : (typeof props.actions === 'string' ? props.actions.split(',').map((s: string) => s.trim()).filter(Boolean) : []);
        const usesRaw = parseInt(props.uses ?? -1);
        return {
            kind: node.type,
            name: node.name || nodeId,
            description: props.description || '',
            tags: Array.isArray(props.tags) ? props.tags : [],
            actions,
            uses: Number.isNaN(usesRaw) ? -1 : usesRaw,
            current_state: props.current_state || '',
            requires: props.requires || '',
        };
    };

    /**
     * ⚡ Suggest / ✨ Suggest (AI) — item / way / area inspector.
     *
     * Plan-driven: the heuristic computes WHICH trigger types the item's
     * actions call for (planForNode). The heuristic authors them directly; the
     * AI authors the same types (missing ones backfilled from the heuristic
     * floor). Result is diffed against existing triggers and shown in a review
     * modal — per-trigger keep/use-suggested/skip — never a blind overwrite.
     */
    api.suggestForNode = async function(nodeId: string, useAI?: boolean, btn?: HTMLButtonElement) {
        const Suggester = (window as unknown as { ItemLibraryTriggerSuggester?: TriggerSuggesterApi }).ItemLibraryTriggerSuggester;
        const fields = api._suggestFieldsForNode(nodeId);
        if (!fields) {
            if (typeof toastInfo === 'function') toastInfo('Node not found.');
            return;
        }
        const label = fields.name;
        if (btn) {
            btn.disabled = true;
            btn.dataset.old = btn.textContent;
            btn.textContent = '⏳…';
        }
        try {
            const planTypes = Suggester ? Suggester.planForNode(fields.kind, fields) : null;
            const heuristicFloor = Suggester ? Suggester.suggestForNode(fields.kind, fields) : [];
            const floorByType = new Map<string, TriggerDef>(
                heuristicFloor.map((t: TriggerDef) => [String(t.trigger_type), t]));

            let triggers: TriggerDef[] | null = null;
            if (useAI) {
                const suggestAi = (window as unknown as { TriggerSuggestAI?: TriggerSuggestAiApi }).TriggerSuggestAI;
                if (!suggestAi || typeof suggestAi.suggest !== 'function') {
                    if (typeof toastError === 'function') toastError('AI trigger suggester is not loaded.');
                    return;
                }
                triggers = await suggestAi.suggest(fields, fields.kind, planTypes);
                if (triggers === null) return;
                // Backfill any planned type the model skipped from the heuristic
                // floor, so the suggested set always matches the plan.
                if (planTypes) {
                    const have = new Set<string>(triggers.map(t => String(t.trigger_type)));
                    for (const type of planTypes) {
                        if (!have.has(type) && floorByType.has(type)) {
                            const fromFloor = floorByType.get(type);
                            if (fromFloor) triggers.push(fromFloor);
                            have.add(type);
                        }
                    }
                }
            } else {
                if (!Suggester) {
                    if (typeof toastError === 'function') toastError('Trigger suggester is not loaded.');
                    return;
                }
                triggers = heuristicFloor.length ? heuristicFloor : Suggester.suggestForNode(fields.kind, fields);
            }
            if (!triggers || !triggers.length) {
                if (typeof toastInfo === 'function') toastInfo('No triggers suggested for this node.');
                return;
            }

            // Diff against what already exists on the node.
            const existingData = api._getNodeTriggerData(nodeId);
            const suggestDiff = (window as unknown as { TriggerSuggestDiff?: TriggerSuggestDiffApi }).TriggerSuggestDiff;
            const rows: DiffRow[] = (suggestDiff && planTypes)
                ? suggestDiff.diff(existingData, planTypes, triggers)
                : [];
            if (!suggestDiff || !rows.length) {
                if (existingData.length) {
                    if (typeof toastInfo === 'function' && rows.length === 0) toastInfo('All planned triggers are already covered — nothing to change.');
                } else {
                    const ok = await (window as any).Dialog?.confirm?.({
                        title: 'Add Suggested Triggers',
                        message: `Add ${triggers.length} suggested trigger${triggers.length === 1 ? '' : 's'} to "${label}"?`
                    });
                    if (!ok) return;
                }
            }

            const apply = async (result: DiffResult) => {
                await api._applyTriggerDiff(nodeId, existingData, result);
                worldState.fetch().then(() => {
                    if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
                });
                if (typeof events !== 'undefined' && events.log) {
                    const added = result.add.length + result.replace.length;
                    events.log(`${useAI ? '🤖 AI-' : '⚡ '}applied ${added} suggested trigger${added === 1 ? '' : 's'} on "${label}" (${result.keep.length} kept).`, 'system-msg');
                }
            };

            if (suggestDiff && rows.length) {
                suggestDiff.show({
                    title: useAI ? '🤖 Review AI-suggested triggers' : '⚡ Review suggested triggers',
                    subtitle: `${label} — keep existing triggers you already like; conflicts pick per-row.`,
                    rows,
                    onApply: apply,
                });
            } else if (rows.length === 0 && !existingData.length) {
                await apply({ keep: [], replace: [], add: triggers.map((t: TriggerDef) => ({ type: String(t.trigger_type), data: t })) });
            }
        } catch (err) {
            console.error(err);
            if (typeof toastError === 'function') toastError('Trigger suggestion failed: ' + (err instanceof Error ? err.message : String(err)));
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = btn.dataset?.old || (useAI ? '✨ Suggest (AI)' : '⚡ Suggest');
                delete btn.dataset.old;
            }
        }
    };

    /**
     * Read the triggers attached to a node. properties.triggers is authoritative
     * (task-886); legacy triggers edges are appended, deduped by id.
     * @param nodeId - Graph node ID
     * @returns [{ id, trigger_type, effects, conditions, ... }]
     */
    api._getNodeTriggerData = function(nodeId: string): TriggerDef[] {
        const TG = (window as unknown as { TriggerGraph?: TriggerGraphApi }).TriggerGraph;
        if (!TG || typeof TG.triggersFromGraphEdges !== 'function') return [];
        return TG.triggersFromGraphEdges(
            worldState.graph?.edges, worldState.graph?.nodes, nodeId);
    };

    /**
     * Apply a diff-modal result to a node's trigger edges — as ONE batched
     * /api/graph/batch request (single undo snapshot, single state reload)
     * instead of N sequential create/delete round-trips.
     * @param nodeId
     * @param existingData - the pre-existing trigger data
     * @param result - { keep: [types], replace: [{type,data}], add: [{type,data}] }
     */
    api._applyTriggerDiff = async function(nodeId: string, existingData: TriggerDef[], result: DiffResult) {
        const TG = _triggerGraph();
        const toTypeKey = (t: unknown) => Array.isArray(t) ? t.join(',') : String(t || '');
        const kept = new Set<string>(result.keep);
        const node = worldState.getNode(nodeId);
        if (!node) return;

        // New definitions go to the property array (one update). A legacy edge
        // whose rule the user did not keep is deleted with its trigger node, so
        // it cannot keep firing from the retired store.
        const legacyDeletes: string[] = [];
        for (const edge of api._getNodeTriggers(nodeId)) {
            const def = TG.triggerDefFromEdge(edge, worldState.graph?.nodes);
            if (!kept.has(toTypeKey(def.trigger_type))) legacyDeletes.push(edge.target);
        }

        const next = TG.normalizeTriggerList((node.properties as any)?.triggers)
            .filter((def) => kept.has(toTypeKey(def.trigger_type)));
        for (const { data } of [...result.replace, ...result.add]) {
            next.push({ ...data, id: `trigger_${Date.now()}_${Math.random().toString(36).slice(2, 6)}` });
        }

        if (legacyDeletes.length) {
            let batchOk = true;
            try {
                const res = await _api().batchGraph(
                    legacyDeletes.map((id) => ({ type: 'delete_node', payload: { node_id: id } })),
                );
                const failed = res && Array.isArray(res.errors) && res.errors.length;
                if (failed) {
                    console.warn('[suggestForNode] batch partial failure:', res.errors);
                }
                batchOk = !!res && !failed && res.status === 'success';
            } catch (e) {
                console.warn('[suggestForNode] batch endpoint failed, falling back to sequential:',
                    e instanceof Error ? e.message : String(e));
                batchOk = false;
            }
            if (!batchOk) {
                for (const id of legacyDeletes) { try { await _api().deleteNode(id); } catch (e) {} }
            }
        }

        await _api().updateNode(nodeId, {
            properties: { ...node.properties, triggers: next },
        });
    };

    /**
     * Build the container contents section as a lit template
     * @param nodeId - Graph node ID
     */
    api.buildContentsHtml = function(nodeId: string) {
        const contained: Array<{ id: string; name: string; node: TriggerHelpersGraphNode | undefined }> = [];
        if (worldState.graph?.edges) {
            for (const edge of worldState.graph.edges as TriggerHelpersGraphEdge[]) {
                if (edge.target === nodeId && edge.type === 'in') {
                    const cn = worldState.getNode(edge.source);
                    contained.push({ id: edge.source, name: cn?.name || edge.source, node: cn });
                }
            }
        }
        const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);
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

    return api;
})();
(window as unknown as { InspectorTriggers: typeof _InspectorTriggers }).InspectorTriggers = _InspectorTriggers;

/**
 * Type declarations live BELOW the first value statement on purpose: TypeScript
 * drops a file's leading JSDoc when the first statement is type-only, and
 * `tools/js_module_index.py` reads `@module` out of the emitted .js.
 */

/** The graph node fields these helpers read. */
interface TriggerHelpersGraphNode {
    id?: string;
    type?: string;
    name?: string;
    properties?: Record<string, any>;
}

/** The graph edge fields these helpers read. */
interface TriggerHelpersGraphEdge {
    source: string;
    target: string;
    type: string;
}

/** One exit of a world area, as `worldState.areas[...].exits`. */
interface WorldExit {
    target?: string;
    way_id?: string;
}

/** One contained item of a world area. */
interface WorldAreaItem {
    name?: string;
    id?: string;
}

/** The area fields these helpers read. */
interface WorldArea {
    exits?: Record<string, WorldExit>;
    items?: Array<WorldAreaItem | string>;
}

/** One effect of a compiled trigger. */
interface TriggerHelpersTriggerEffect {
    type?: string;
    params?: Record<string, any>;
}

/** A compiled trigger definition (edge copy merged with node copy). */
interface TriggerDef {
    trigger_type?: string | string[];
    effects?: TriggerHelpersTriggerEffect[];
    /** May be an array of conditions, or the `{ conditions: [...] }` envelope. */
    conditions?: unknown[] | { conditions?: unknown[] };
    name?: string;
    success_message?: string;
    fail_message?: string;
    [key: string]: any;
}

/** graph/trigger-graph.js — not declared in types/globals.d.ts. */
interface TriggerGraphApi {
    triggerDefFromEdge(edge: TriggerHelpersGraphEdge, nodes: unknown): TriggerDef;
    triggerDefFromProperty(entry: unknown): TriggerDef | null;
    triggersFromGraphEdges(edges: unknown, nodes: unknown, nodeId: string): TriggerDef[];
    normalizeTriggerEntry(entry: unknown): TriggerDef | null;
    normalizeTriggerList(value: unknown): TriggerDef[];
    triggerToGraph(data: TriggerDef, opts?: Record<string, unknown>): unknown;
    triggersToGraph(data: TriggerDef[]): unknown;
    compileToEngine(graph: unknown): TriggerDef;
    compileToTriggers(graph: unknown): TriggerDef[];
    compileError(compiled: TriggerDef | null): string;
    reportCompileError(compiled: TriggerDef | null): boolean;
    show(opts: Record<string, unknown>): void;
}

/** item-library/trigger-suggester.js — not declared in types/globals.d.ts. */
interface TriggerSuggesterApi {
    planForNode(kind: string, fields: SuggestFields): string[] | null;
    suggestForNode(kind: string, fields: SuggestFields): TriggerDef[];
}

/** shared/trigger-suggest-ai.js — not declared in types/globals.d.ts. */
interface TriggerSuggestAiApi {
    suggest(fields: SuggestFields, kind: string, planTypes: string[] | null): Promise<TriggerDef[] | null>;
}

/** The trigger diff modal's API. */
interface TriggerSuggestDiffApi {
    diff(existing: TriggerDef[], planTypes: string[] | null,
         suggested: TriggerDef[]): DiffRow[];
    show(opts: { title: string; subtitle: string; rows: DiffRow[]; onApply(r: DiffResult): Promise<void> }): void;
}

/** validator-panel.js — the one method this module calls. */
interface ValidatorPanelApi {
    validateNodeInline(nodeId: string, container: HTMLElement): Promise<void>;
}

/** The ApiClient endpoints this module calls beyond the declared shared shape. */
interface TriggerApiClient {
    deleteEdge(source: string, target: string, type: string): Promise<unknown>;
    deleteNode(nodeId: string): Promise<unknown>;
    updateNode(nodeId: string, data: unknown): Promise<unknown>;
    updateEdge(source: string, target: string, data: unknown): Promise<unknown>;
    createNode(data: unknown): Promise<{ error?: string } | null>;
    createEdge(source: string, target: string, type: string, properties?: unknown): Promise<unknown>;
    batchGraph(ops: unknown[]): Promise<{ errors?: unknown[]; status?: string } | null>;
}

/** The node snapshot the suggesters plan against. */
interface SuggestFields {
    kind: string;
    name: string;
    description: string;
    tags: unknown[];
    actions: unknown[];
    uses: number;
    current_state: string;
    requires: string;
}

/** One row of the trigger diff modal. */
interface DiffRow {
    type: string;
    [key: string]: unknown;
}

/** The diff modal's answer. */
interface DiffResult {
    keep: string[];
    replace: Array<{ type: string; data: TriggerDef }>;
    add: Array<{ type: string; data: TriggerDef }>;
}

/** One condition of a compiled trigger, as the summary line reads it. */
interface TriggerCondition {
    type?: string;
    value?: unknown;
    skill?: string;
    dc?: number;
}

/** The public surface of inspector/trigger-helpers. */
interface TriggerHelpersApi {
    removeTriggerFromNode(nodeId: string, source: string, target: string): Promise<void>;
    getDoorOptions(): string;
    getTargetDatalist(): string;
    getItemDatalist(): string;
    buildTriggersHtml(nodeId: string, lockedFields?: string[]): unknown;
    validateNode(nodeId: string): Promise<void>;
    _openGraphEditor(escId: string): void;
    _getNodeTriggers(nodeId: string): TriggerHelpersGraphEdge[];
    createTriggerOnNode(nodeId: string, data: TriggerDef): Promise<void>;
    _suggestFieldsForNode(nodeId: string): SuggestFields | null;
    suggestForNode(nodeId: string, useAI?: boolean, btn?: HTMLButtonElement): Promise<void>;
    _getNodeTriggerData(nodeId: string): TriggerDef[];
    _applyTriggerDiff(nodeId: string, existingData: TriggerDef[], result: DiffResult): Promise<void>;
    buildContentsHtml(nodeId: string): unknown;
}
