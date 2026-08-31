/**
 * Shared Trigger Editor — builds the add/edit trigger overlay modal.
 * Used by both Inspector (world items/doors) and ItemLibrary (library items).
 *
 * Flow: Trigger Type → Conditions (nested rule tree) → Effects → Messages
 *
 * Usage:
 *   TriggerEditor.show({
 *       mode: 'single' | 'multi',
 *       initialData: { ... } | null,
 *       onSave: function(triggerData),
 *       onClose: function(),
 *       onTriggerTypeChange: function(selectedTypes),
 *       effectTypes: [...],
 *       conditionTypes: [...],
 *       triggerTypes: [...],
 *       targetDatalistHtml: '',
 *       itemDatalistHtml: '',
 *   })
 */

// Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
const triggerEditorTag = (strings, ...values) => window.Lit.html(strings, ...values);

// ═══════ Recipe snippets (task-380) ═══════
// Each snippet sets the trigger type, replaces the effects list with a
// starting point (author tweaks params), and fills the success message.
const TRIGGER_SNIPPETS = [
    {
        id: 'book-read', icon: '📖', label: 'Book Read', triggerType: 'on_read',
        message: 'You read the passage aloud.',
        effects: [{ type: 'message', params: {} }],
    },
    {
        id: 'chest', icon: '📦', label: 'Chest (spawn item inside me)', triggerType: 'on_use',
        message: 'The chest creaks. Inside: {item_name}.',
        effects: [{ type: 'spawn_item', params: { item_id: '', into: 'container' } }],
    },
    {
        id: 'light', icon: '🕯', label: 'Light Source (fill the room)', triggerType: 'on_light',
        message: 'The {name} flares to life, casting warm light.',
        effects: [
            { type: 'set_state', params: { node_id: 'self', state: 'lit' } },
            { type: 'set_environment', params: { light: 55 } },
        ],
    },
    {
        id: 'heat', icon: '🔥', label: 'Heat Source (warm the room)', triggerType: 'on_use',
        message: 'The {name} roars, and the room slowly warms.',
        effects: [
            { type: 'set_state', params: { node_id: 'self', state: 'lit' } },
            { type: 'set_environment', params: { temperature: 30 } },
        ],
    },
    {
        id: 'recorder', icon: '🎙', label: 'Recorder (capture recent speech)', triggerType: 'on_use',
        message: 'The {name} clicks — recording what was just said.',
        effects: [{ type: 'spawn_item', params: { item_id: '', into: 'container', capture: 'speech', capture_limit: 5 } }],
    },
    {
        id: 'firstaid', icon: '💉', label: 'First Aid (heal + stop bleeding)', triggerType: 'on_use',
        message: 'You patch yourself up.',
        effects: [
            { type: 'adjust_vital', params: { stat: 'HP', amount: 10, target: 'self' } },
            { type: 'remove_condition', params: { condition: 'bleeding', target: 'self' } },
        ],
    },
    {
        id: 'whisper', icon: '🚪', label: 'Whispering Door', triggerType: 'on_open',
        message: 'A low voice breathes: "not yet…"',
        effects: [{ type: 'message', params: {} }],
    },
];

const TriggerEditor = {
    _overlay: null,
    _onSave: null,
    _onClose: null,
    _mode: 'single',
    _effectTypes: [],
    _conditionTypes: [],
    _triggerTypes: [],
    _condOpts: null,
    _itemDatalist: '',
    _contextItemId: '',
    _targetDatalistHtml: '',

    _buildGroupedCondOpts(conditionTypes, selectedValue) {
        const groups = {};
        conditionTypes.forEach(c => {
            const g = c.group || 'general';
            if (!groups[g]) groups[g] = [];
            groups[g].push(c);
        });
        const groupLabels = {
            general: '⚙️ General',
            character: '🧍 Character',
            item: '📦 Item',
            way: '🚪 Way',
            area: '🌍 Area/Environment',
            tag: '🏷️ Tag'
        };
        return Object.entries(groups).map(([g, conds]) => {
            const label = groupLabels[g] || g;
            const opts = conds.map(c =>
                `<option value="${c.value}" ${c.value === selectedValue ? 'selected' : ''}>${c.label}</option>`
            ).join('');
            return `<optgroup label="${label}">${opts}</optgroup>`;
        }).join('');
    },

    _buildGroupedEffectOpts(effectTypes, selectedValue) {
        const groups = {};
        effectTypes.forEach(e => {
            const g = e.group || 'general';
            if (!groups[g]) groups[g] = [];
            groups[g].push(e);
        });
        const groupLabels = {
            general: '⚙️ General',
            character: '🧍 Character',
            item: '📦 Item',
            way: '🚪 Way',
            area: '🌍 Area/Environment'
        };
        return Object.entries(groups).map(([g, effects]) => {
            const label = groupLabels[g] || g;
            const opts = effects.map(e =>
                `<option value="${e.value}" ${e.value === selectedValue ? 'selected' : ''}>${e.label}</option>`
            ).join('');
            return `<optgroup label="${label}">${opts}</optgroup>`;
        }).join('');
    },

    open(itemId, triggerType) {
        return this.show({ initialData: null, mode: 'single' });
    },

    show(options) {
        this.close();
        this._onSave = options.onSave || null;
        this._onClose = options.onClose || null;
        this._mode = options.mode || 'single';
        this._effectTypes = options.effectTypes || [];
        this._conditionTypes = options.conditionTypes || [];
        this._triggerTypes = options.triggerTypes || [];
        this._itemDatalist = options.itemDatalistHtml || '';
        this._contextItemId = options.contextItemId || '';
        this._targetDatalistHtml = options.targetDatalistHtml || '';
        const initial = options.initialData || null;
        const targetDatalist = this._targetDatalistHtml;

        const effectOpts = this._buildGroupedEffectOpts(this._effectTypes);
        this._condOpts = this._buildGroupedCondOpts(this._conditionTypes);

        const initialTriggerType = initial?.trigger_type;
        const triggerTypeHtml = this._mode === 'multi'
            ? triggerEditorTag`<select id="te-trigger-type" multiple size="6" style="height:auto;min-height:100px;width:100%;">
                    ${this._triggerTypes.map(t => triggerEditorTag`<option value=${t} ?selected=${(initialTriggerType || []).includes(t)}>${t.replace(/_/g, ' ')}</option>`)}
                </select>`
            : triggerEditorTag`<select id="te-trigger-type" style="width:100%;">
                    ${this._triggerTypes.map(t => triggerEditorTag`<option value=${t} ?selected=${initialTriggerType === t}>${t.replace(/_/g, ' ')}</option>`)}
                </select>`;

        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';

        const isEdit = !!initial;
        const editTitle = isEdit ? '✏️ Edit Trigger' : '⚡ Add Trigger';

        let effectRowsHtml = [];
        if (initial && initial.effects && initial.effects.length > 0) {
            initial.effects.forEach((eff, idx) => {
                effectRowsHtml.push(TriggerEditor._buildEffectRowHtml(effectOpts, eff, idx));
            });
        } else {
            effectRowsHtml.push(TriggerEditor._buildEffectRowHtml(effectOpts, null, 0));
        }

window.Lit.render(triggerEditorTag`
            <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:480px;max-height:85vh;overflow-y:auto;">
                <h3 style="margin:0 0 12px 0;">${editTitle}</h3>

                <div class="field"><label>Trigger Name</label>
                    <input type="text" id="te-trigger-name" .value=${initial?.name || ''} placeholder="e.g. Button 7 on_use" style="width:100%;font-size:11px;">
                </div>

                <div class="field"><label>Trigger Type${this._mode === 'multi' ? ' (Ctrl+click for multiple)' : ''}</label>
                    ${triggerTypeHtml}
                </div>
                <div class="field" id="te-target-state-field" style="display:none;">
                    <label>Target State (e.g. lit, open)</label>
                    <input type="text" id="te-target-state" .value=${initial?.target_state || ''} placeholder="e.g. lit" style="width:100%;font-size:11px;">
                </div>
                <div class="field" id="te-target-field" style="display:none;">
                    <label>Target (searchable — exits, doors, items)</label>
                    <div class="eff-select" data-kind="targets" data-input-class="te-target-name" data-input-id="te-target-name" data-value=${initial?.target_name || ''} data-placeholder="Search or type target..." data-free="true"></div>
                    <datalist id="te-target-list">${window.Lit.unsafeHTML(targetDatalist)}</datalist>
                </div>

                <!-- ═══════ Conditions (before Effects) ═══════ -->
                <div style="border-top:1px solid var(--border);padding-top:12px;margin-top:12px;">
                    <h3 style="font-size:12px;margin:0 0 4px 0;color:var(--pink);">🧩 Conditions</h3>
                </div>
                <div id="te-conditions-container">
                    <div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No conditions — always fires.</div>
                </div>
                <div style="display:flex;gap:4px;margin-top:4px;">
                    <button class="btn btn-sm btn-blue" @click=${() => TriggerEditor._addCondLeaf()} style="flex:1;">➕ Add Condition</button>
                    <button class="btn btn-sm btn-purple" @click=${() => TriggerEditor._addCondGroup()} style="flex:1;">📁 Add Group</button>
                </div>

                <!-- ═══════ Effects ═══════ -->
                <div style="border-top:1px solid var(--border);padding-top:12px;margin-top:12px;">
                    <h3 style="font-size:12px;margin:0 0 8px 0;color:var(--orange);">⚡ Effects</h3>
                </div>
                <div id="te-effects-container" data-count=${effectRowsHtml.length || 1}>
                    ${effectRowsHtml.map(r => window.Lit.unsafeHTML(r))}
                </div>
                <div style="display:flex;gap:4px;margin-top:4px;">
                    <button class="btn btn-sm btn-blue" @click=${() => TriggerEditor._addEffectRow()} style="flex:1;">➕ Add Effect</button>
                    <button class="btn btn-sm btn-purple" @click=${() => TriggerEditor._toggleSnippetMenu()} style="flex:1;">🧩 Snippets ▾</button>
                </div>
                <div id="te-snippet-menu" style="display:none;margin-top:4px;border:1px solid var(--border);border-radius:8px;padding:6px;background:var(--bg-inset);">
                    <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">Recipes fill the effects list + trigger type (tweak params, then save).</div>
                    ${TRIGGER_SNIPPETS.map(s => `<div class="te-snippet-item" style="display:flex;justify-content:space-between;align-items:center;padding:4px 6px;cursor:pointer;font-size:12px;border-radius:6px;" onmouseenter="this.style.background='rgba(255,255,255,0.05)'" onmouseleave="this.style.background='transparent'" onclick="TriggerEditor._applySnippet('${s.id}')"><span>${s.icon} ${s.label}</span><span style="font-size:10px;color:var(--text-dim);">${s.triggerType.replace(/_/g, ' ')}</span></div>`).join('')}
                </div>

                <!-- ═══════ Messages ═══════ -->
                <div style="border-top:1px solid var(--border);padding-top:12px;margin-top:12px;">
                    <h3 style="font-size:12px;margin:0 0 8px 0;color:var(--green);">💬 Messages</h3>
                    <div class="field"><label>✅ Success Message</label>
                        <input type="text" id="te-success-msg" .value=${initial?.success_message || initial?.effects?.[0]?.params?.success_message || ''} placeholder="What happens on success..." style="width:100%;">
                    </div>
                    <div class="field" id="te-fail-msg-group" style="display:none;">
                        <label>❌ Fail Message</label>
                        <input type="text" id="te-fail-msg" .value=${initial?.fail_message || initial?.effects?.[0]?.params?.fail_message || ''} placeholder="What happens if condition not met..." style="width:100%;">
                    </div>
                </div>

                <div style="display:flex;gap:6px;margin-top:12px;justify-content:flex-end;border-top:1px solid var(--border);padding-top:12px;">
                    <button class="btn btn-purple" @click=${() => TriggerEditor._onTestClick()}>▶ Run Test</button>
                    ${typeof TriggerGraph !== 'undefined' ? triggerEditorTag`<button class="btn btn-yellow" @click=${() => TriggerEditor._onOpenGraphClick()}>🧩 Graph</button>` : ''}
                    <button class="btn" @click=${() => TriggerEditor.close()}>Cancel</button>
                    <button class="btn btn-green" @click=${() => TriggerEditor._onSaveClick()}>✅ ${isEdit ? 'Save Changes' : 'Add'}</button>
                </div>
                <div id="te-test-result" style="display:none;margin-top:10px;background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;padding:10px;font-size:11px;line-height:1.6;"></div>
            </div>`, overlay);
        document.body.appendChild(overlay);
        this._overlay = overlay;

        // Ensure shared datalists
        ['eff-vital-stat-list', 'eff-state-node-list', 'eff-state-val-list', 'eff-trait-list', 'eff-tag-list', 'eff-weather-list', 'eff-char-list', 'eff-condition-list'].forEach(id => {
            if (!document.getElementById(id)) {
                const dl = document.createElement('datalist');
                dl.id = id;
                document.body.appendChild(dl);
            }
        });
        const vitals = document.getElementById('eff-vital-stat-list');
        if (!vitals.children.length) ['HP','Energy','Bladder','Sanity','Entertainment','Temperature'].forEach(v => {
            const o = document.createElement('option'); o.value = v; vitals.appendChild(o);
        });
        const states = document.getElementById('eff-state-val-list');
        if (!states.children.length) ['on','off','open','closed','locked','unlocked','lit','unlit','broken','pristine','activated','deactivated','hidden','visible'].forEach(s => {
            const o = document.createElement('option'); o.value = s; states.appendChild(o);
        });
        const traitList = document.getElementById('eff-trait-list');
        if (traitList && !traitList.children.length) {
            ApiClient.getLibraryType('traits').then(traits => {
                if (traits && typeof traits === 'object') {
                    Object.keys(traits).forEach(id => {
                        const o = document.createElement('option'); o.value = id; traitList.appendChild(o);
                    });
                }
            }).catch(() => {});
        }
        const tagList = document.getElementById('eff-tag-list');
        if (tagList && !tagList.children.length) {
            ApiClient.getLibraryType('tags').then(tags => {
                if (tags && typeof tags === 'object') {
                    Object.keys(tags).forEach(id => {
                        const o = document.createElement('option'); o.value = id; tagList.appendChild(o);
                    });
                }
            }).catch(() => {});
        }
        const weatherList = document.getElementById('eff-weather-list');
        if (weatherList && !weatherList.children.length) {
            ['clear', 'cloudy', 'fog', 'rain', 'storm', 'snow', 'windy'].forEach(w => {
                const o = document.createElement('option'); o.value = w; weatherList.appendChild(o);
            });
        }
        const conditionList = document.getElementById('eff-condition-list');
        if (conditionList && !conditionList.children.length) {
            ['awake','dead','unconscious','paralysed','stunned','grappled','restrained','prone','busy',
             'exhausted','sick','poisoned','blind','deaf','mute','frightened','charmed'].forEach(c => {
                const o = document.createElement('option'); o.value = c; conditionList.appendChild(o);
            });
        }
        const charList = document.getElementById('eff-char-list');
        if (charList && !charList.children.length) {
            const chars = worldState?.players || {};
            Object.keys(chars).forEach(name => {
                const o = document.createElement('option'); o.value = name; charList.appendChild(o);
            });
        }
        const nodeList = document.getElementById('eff-state-node-list');
        if (!nodeList.children.length && worldState?.graph?.nodes) {
            Object.keys(worldState.graph.nodes).forEach(id => {
                const o = document.createElement('option'); o.value = id; nodeList.appendChild(o);
            });
        }
        const itemList = document.getElementById('te-item-list');
        if (!itemList) {
            const dl = document.createElement('datalist');
            dl.id = 'te-item-list';
            document.body.appendChild(dl);
        }
        const itemListEl = document.getElementById('te-item-list');
        if (!itemListEl.children.length) {
            if (worldState?.graph?.nodes) {
                Object.entries(worldState.graph.nodes).forEach(([id, node]) => {
                    if (node.type === 'item') {
                        const o = document.createElement('option'); o.value = id; itemListEl.appendChild(o);
                    }
                });
            }
            if (window.VW?.itemLib?.data) {
                Object.keys(window.VW.itemLib.data).forEach(id => {
                    const o = document.createElement('option'); o.value = id; itemListEl.appendChild(o);
                });
            }
        }

        // Trigger type change handler
        overlay.querySelector('#te-trigger-type').addEventListener('change', function () {
            const vals = Array.from(this.selectedOptions).map(o => o.value);
            document.getElementById('te-target-field').style.display = vals.includes('on_use_on') ? 'block' : 'none';
            const tf = document.getElementById('te-target-state-field');
            if (tf) tf.style.display = (vals.includes('on_state_enter') || vals.includes('on_state_exit')) ? 'block' : 'none';
            if (options.onTriggerTypeChange) options.onTriggerTypeChange(vals);
        });
        // Reflect the initially-selected trigger type (fixes the target/state
        // fields staying hidden when opening an existing on_use_on trigger).
        overlay.querySelector('#te-trigger-type').dispatchEvent(new Event('change'));

        // Load initial conditions tree
        const initConditions = initial?.conditions;
        const condContainer = document.getElementById('te-conditions-container');
        if (initConditions && (Array.isArray(initConditions) && initConditions.length > 0 || (typeof initConditions === 'object' && !Array.isArray(initConditions) && initConditions?.conditions?.length > 0))) {
            window.Lit.render(triggerEditorTag`${window.Lit.nothing}`, condContainer);
            TriggerEditor._loadConditionTree(initConditions, initial?.conditions_logic || 'and', condContainer);
        }

        // Show fail message group if conditions exist
        TriggerEditor._updateFailGroupVisibility();

        // Trigger effect params for first row
        const firstEff = overlay.querySelector('.eff-type');
        if (firstEff) TriggerEditor._toggleEffectParams(firstEff);
        TriggerEditor._initEffectSearchSelects(overlay);
        TriggerEditor._initCondTagMultis(overlay);
    },

    _updateFailGroupVisibility() {
        const group = document.getElementById('te-fail-msg-group');
        if (!group) return;
        const container = document.getElementById('te-conditions-container');
        const hasConditions = container ? !!container.querySelector('.cond-row') : false;
        group.style.display = hasConditions ? 'block' : 'none';
    },

    _searchSelectOptions(kind) {
        const opts = [];
        const nodes = worldState?.graph?.nodes || {};
        switch (kind) {
            case 'ways':
                opts.push({ value: 'target', label: 'target (used-on)', icon: '🎯' });
                for (const [id, n] of Object.entries(nodes)) {
                    if (n.type === 'way') opts.push({ value: id, label: n.name || id, icon: '🚪' });
                }
                break;
            case 'items':
                for (const [id, n] of Object.entries(nodes)) {
                    if (n.type === 'item') opts.push({ value: id, label: n.name || id, icon: '📦' });
                }
                if (window.VW?.itemLib?.data) {
                    for (const id of Object.keys(window.VW.itemLib.data)) {
                        if (!opts.some(o => o.value === id)) opts.push({ value: id, label: id, icon: '📦' });
                    }
                }
                break;
            case 'nodes':
                for (const [id, n] of Object.entries(nodes)) {
                    const icon = { area: '🗺️', way: '🚪', item: '📦', player: '🧍', character: '🧍', logic_trigger: '⚡' }[n.type] || '▪️';
                    opts.push({ value: id, label: n.name || id, icon });
                }
                break;
            case 'areas':
                for (const name of Object.keys(worldState?.areas || {})) {
                    opts.push({ value: name, label: name, icon: '🗺️' });
                }
                break;
            case 'states':
                ['on','off','open','closed','locked','unlocked','lit','unlit','broken','pristine','activated','deactivated','hidden','visible'].forEach(s => {
                    opts.push({ value: s, label: s });
                });
                break;
            case 'conditions':
                ['awake','dead','unconscious','paralysed','stunned','grappled','restrained','prone','busy',
                 'exhausted','sick','poisoned','blind','deaf','mute','frightened','charmed'].forEach(c => {
                    opts.push({ value: c, label: c, icon: '🩹' });
                });
                break;
            case 'vitals':
                ['HP','Energy','Bladder','Sanity','Entertainment','Temperature','Hunger','Thirst','Hygiene','Social'].forEach(v => {
                    opts.push({ value: v, label: v });
                });
                break;
            case 'skills':
                ['STR','DEX','CON','INT','WIS','CHA','Athletics','Acrobatics','Stealth','Perception','Survival','Persuasion','Investigation'].forEach(s => {
                    opts.push({ value: s, label: s });
                });
                break;
            case 'chars':
                opts.push({ value: 'self', label: 'self (actor)', icon: '🎯' });
                opts.push({ value: 'target', label: 'target (on_use_on)', icon: '🎯' });
                for (const name of Object.keys(worldState?.players || {})) {
                    opts.push({ value: name, label: name, icon: '🧍' });
                }
                break;
            case 'traits': {
                const dl = document.getElementById('eff-trait-list');
                if (dl) {
                    for (const o of dl.querySelectorAll('option')) {
                        opts.push({ value: o.value, label: o.value, icon: '🧬' });
                    }
                }
                break;
            }
            case 'tags': {
                const dl = document.getElementById('eff-tag-list');
                if (dl) {
                    for (const o of dl.querySelectorAll('option')) opts.push({ value: o.value, label: o.value, icon: '🎗️' });
                }
                break;
            }
            case 'targets': {
                const dl = document.getElementById('te-target-list');
                if (dl) {
                    for (const o of dl.querySelectorAll('option')) opts.push({ value: o.value, label: o.label || o.value });
                }
                break;
            }
        }
        opts.sort((a, b) => (a.label || '').localeCompare(b.label || ''));
        return opts;
    },

    _initEffectSearchSelects(root) {
        if (typeof SearchSelect === 'undefined') return;
        (root || document).querySelectorAll('.eff-select').forEach(container => {
            if (container.dataset.searchSelectInit) return;
            container.dataset.searchSelectInit = '1';
            const kind = container.dataset.kind || '';
            const initial = container.dataset.value || '';
            const free = container.dataset.free === 'true';
            const opts = TriggerEditor._searchSelectOptions(kind);
            if (initial && !opts.some(o => o.value === initial)) {
                opts.unshift({ value: initial, label: initial });
            }
            new SearchSelect(container, {
                options: opts,
                value: initial,
                placeholder: container.dataset.placeholder || 'Search...',
                inputClass: container.dataset.inputClass || '',
                inputId: container.dataset.inputId || '',
                allowFreeText: free
            });
        });
    },

    _initCondTagMultis(root) {
        if (typeof TagMultiselect === 'undefined') return;
        (root || document).querySelectorAll('.cond-tag-multi').forEach(container => {
            if (container.__condTagMulti) return;
            const raw = (container.dataset.value || '')
                .split(',').map(s => s.trim()).filter(Boolean);
            container.__condTagMulti = new TagMultiselect(container, {
                tags: raw,
                allowNew: false,
                placeholder: 'Search tags...',
            });
        });
    },

    _removeCondItem(span) {
        const item = span.closest('.cond-group-item');
        if (item) item.remove();
        TriggerEditor._updateFailGroupVisibility();
    },

    close() {
        if (this._overlay) {
            this._overlay.remove();
            this._overlay = null;
        }
        if (this._onClose) this._onClose();
    },

    _onSaveClick() {
        const data = this._collectData();
        if (this._onSave) this._onSave(data);
        this.close();
    },

    _onOpenGraphClick() {
        if (typeof TriggerGraph === 'undefined') return;
        const data = this._collectData();
        const onSave = this._onSave;
        const bridge = {
            mode: this._mode,
            effectTypes: this._effectTypes,
            conditionTypes: this._conditionTypes,
            triggerTypes: this._triggerTypes,
            targetDatalistHtml: this._targetDatalistHtml,
            itemDatalistHtml: this._itemDatalist,
            contextItemId: this._contextItemId,
            onSave,
            initialName: data.name || '',
            success_message: data.success_message || '',
            fail_message: data.fail_message || '',
        };
        this.close();
        TriggerGraph.show({
            graph: TriggerGraph.triggerToGraph(data),
            contextItemId: this._contextItemId,
            sourceNodeId: this._contextItemId,
            editorBridge: bridge,
            onSave: (newGraph) => {
                const compiled = TriggerGraph.compileToEngine(newGraph);
                if (!compiled || !onSave) return;
                onSave({
                    ...TriggerGraph.engineToFormData(compiled),
                    name: bridge.initialName || data.name || '',
                    success_message: bridge.success_message || data.success_message || '',
                    fail_message: compiled.fail_message || bridge.fail_message || data.fail_message || '',
                });
            },
        });
    },

    async _onTestClick() {
        const data = this._collectData();
        const resultEl = document.getElementById('te-test-result');
        if (!resultEl) return;
        resultEl.style.display = 'block';
        window.Lit.render(triggerEditorTag`<span style="color:var(--text-secondary);">Testing…</span>`, resultEl);

        // Trigger type may be an array (multi-select) — test the first for now.
        const triggerType = Array.isArray(data.trigger_type)
            ? data.trigger_type[0]
            : data.trigger_type;

        const conditions = data.conditions || {};
        const payload = {
            trigger: {
                trigger_type: triggerType || '',
                conditions,
                effects: data.effects || [],
            },
            dry_run: true,
            context: {},
        };
        if (Array.isArray(conditions)) {
            payload.trigger.conditions_logic = 'and';
        }
        // Expose the target item if one is set, so item-scoped conditions resolve.
        if (this._contextItemId) {
            payload.item_id = this._contextItemId;
        } else if (data.target_name) {
            const node = worldState?.getNodeByIdentifier ? worldState.getNodeByIdentifier(data.target_name) : null;
            if (node) payload.item_id = node.id;
        }

        try {
            const resp = await fetch('/api/triggers/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const res = await resp.json();
            if (res.error) throw new Error(res.error);

            const rows = (res.conditions || []).map(c =>
                triggerEditorTag`<div style="display:flex;gap:6px;align-items:center;">
                    <span style="color:${c.passed ? 'var(--green)' : 'var(--red)'};font-weight:600;">${c.passed ? '✓' : '✕'}</span>
                    <span style="color:var(--text-primary);">${String(c.condition || '(none)')}</span>
                    <span style="color:var(--text-muted);">${c.detail?.phrase ? `— "${c.detail.phrase}" (${c.detail.mode || 'contains'})` : ''}</span>
                </div>`
            );

            const fireable = res.fireable !== false;
            const fireableMsg = res.fireable_reason
                || `this trigger type (${String(triggerType)}) needs an item/way context to fire — no target node matched "${String(data.target_name || '')}".`;
            const outputs = (res.outputs || []).map(o =>
                triggerEditorTag`<div style="padding-left:8px;color:${o.includes('dry-run') ? 'var(--text-secondary)' : 'var(--accent-green)'};">${o}</div>`
            );

            const typeLabel = Array.isArray(triggerType) ? (triggerType[0] || '(none selected)') : (triggerType || '(none selected)');

            window.Lit.render(triggerEditorTag`
                <div style="color:var(--text-secondary);font-weight:600;margin-bottom:4px;">🧪 Trigger Test</div>
                <div>Type: <span style="color:var(--text-primary);">${String(typeLabel)}</span></div>
                ${res.fireable === false ? triggerEditorTag`<div style="color:var(--accent-orange);">⚠️ ${String(fireableMsg)}</div>` : ''}
                <div style="margin-top:4px;font-weight:600;color:${res.conditions_pass ? 'var(--green)' : 'var(--red)'};">Conditions: ${res.conditions_pass ? 'PASS' : 'FAIL'}</div>
                ${rows.length ? rows : triggerEditorTag`<div style="color:var(--text-muted);">(no conditions — always fires)</div>`}
                <div style="margin-top:4px;font-weight:600;">Would run:</div>
                ${outputs.length ? outputs : triggerEditorTag`<div style="color:var(--text-muted);">(no effects)</div>`}
                ${res.side_effects && res.side_effects.length ? triggerEditorTag`<div style="margin-top:4px;color:var(--accent-orange);font-size:10px;">⚠️ ${res.side_effects.join(' · ')}</div>` : ''}
                <div style="margin-top:6px;font-size:10px;color:var(--text-muted);">Dry-run — no effects were applied.</div>
            `, resultEl);
        } catch (e) {
            window.Lit.render(triggerEditorTag`<div style="color:var(--red);">Test failed: ${String(e.message || e)}</div>`, resultEl);
        }
    },

    _collectData() {
        const typeEl = document.getElementById('te-trigger-type');
        const triggerType = this._mode === 'multi'
            ? Array.from(typeEl.selectedOptions).map(o => o.value)
            : typeEl.value;

        const effects = [];
        document.querySelectorAll('#te-effects-container .eff-row').forEach(row => {
            const eff = { type: row.querySelector('.eff-type')?.value || 'message', params: {} };
            const effType = eff.type;
            if (effType === 'damage' || effType === 'heal') {
                eff.params.amount = parseInt(row.querySelector('.eff-amount')?.value) || 5;
                if (effType === 'damage') eff.params.target = row.querySelector('.eff-dmg-target')?.value || 'self';
            } else if (effType === 'adjust_vital') {
                eff.params.stat = row.querySelector('.eff-vital-stat')?.value || 'HP';
                eff.params.amount = parseInt(row.querySelector('.eff-vital-amount')?.value) || 0;
                eff.params.target = row.querySelector('.eff-vital-target')?.value || 'self';
            } else if (effType === 'spawn_item') {
                eff.params.item_id = row.querySelector('.eff-spawn-id')?.value || '';
                eff.params.display_name = row.querySelector('.eff-spawn-name')?.value || '';
                const into = row.querySelector('.eff-spawn-into')?.value || 'area';
                if (into !== 'area') eff.params.into = into;
                const capture = row.querySelector('.eff-spawn-capture')?.value || '';
                if (capture) eff.params.capture = capture;
            } else if (effType === 'spawn_character') {
                eff.params.character_id = row.querySelector('.eff-spawn-char-id')?.value || '';
                eff.params.display_name = row.querySelector('.eff-spawn-char-name')?.value || '';
                eff.params.area = row.querySelector('.eff-spawn-char-area')?.value || '';
                eff.params.message = row.querySelector('.eff-spawn-char-msg')?.value || '';
            } else if (effType === 'give_item') {
                eff.params.item_id = row.querySelector('.eff-give-id')?.value || '';
                eff.params.target = row.querySelector('.eff-give-target')?.value || 'self';
                eff.params.message = row.querySelector('.eff-give-msg')?.value || '';
            } else if (effType === 'remove_item') {
                eff.params.item_id = row.querySelector('.eff-remove-id')?.value || '';
            } else if (effType === 'set_state') {
                eff.params.node_id = row.querySelector('.eff-state-node')?.value || 'self';
                eff.params.state = row.querySelector('.eff-state-val')?.value || 'on';
            } else if (effType === 'set_hidden') {
                eff.params.node_id = row.querySelector('.eff-hidden-node')?.value || 'self';
                eff.params.hidden = row.querySelector('.eff-hidden-val')?.value === 'true';
            } else if (effType === 'adjust_uses') {
                eff.params.node_id = row.querySelector('.eff-uses-node')?.value || 'self';
                eff.params.delta = parseInt(row.querySelector('.eff-uses-delta')?.value) || 0;
            } else if (effType === 'set_parameter' || effType === 'adjust_parameter') {
                eff.params.node_id = row.querySelector('.eff-param-node')?.value || 'self';
                eff.params.key = row.querySelector('.eff-param-key')?.value || '';
                if (effType === 'set_parameter') {
                    eff.params.value = row.querySelector('.eff-param-value')?.value ?? '';
                } else {
                    eff.params.delta = parseInt(row.querySelector('.eff-param-delta')?.value) || 0;
                }
            } else if (effType === 'rename') {
                eff.params.name = row.querySelector('.eff-rename')?.value || '';
            } else if (effType === 'teleport') {
                eff.params.area = row.querySelector('.eff-teleport')?.value || '';
            } else if (effType === 'unlock_way') {
                eff.params.way_id = row.querySelector('.eff-unlock')?.value || '';
            } else if (effType === 'set_description') {
                eff.params.target = row.querySelector('.eff-setdesc-target')?.value || '';
                eff.params.value = row.querySelector('.eff-setdesc-value')?.value || '';
            } else if (effType === 'append_description') {
                eff.params.target = row.querySelector('.eff-setdesc-target')?.value || '';
                eff.params.text = row.querySelector('.eff-appenddesc-text')?.value || '';
            } else if (effType === 'schedule_trigger') {
                eff.params.delay_ticks = parseInt(row.querySelector('.eff-schedule-delay')?.value) || 3;
                eff.params.target = row.querySelector('.eff-schedule-target')?.value || '';
            } else if (effType === 'set_environment') {
                const lightVal = row.querySelector('.eff-env-light')?.value || '';
                if (lightVal) eff.params.light = lightVal;
                const tempVal = row.querySelector('.eff-env-temp')?.value;
                if (tempVal !== undefined && tempVal !== '') eff.params.temperature = parseInt(tempVal);
                const airVal = row.querySelector('.eff-env-air')?.value || '';
                if (airVal) eff.params.air = airVal;
                const smellVal = row.querySelector('.eff-env-smell')?.value || '';
                if (smellVal) eff.params.smell = smellVal;
                const noiseVal = row.querySelector('.eff-env-noise')?.value || '';
                if (noiseVal) eff.params.noise = noiseVal;
                const nodeVal = row.querySelector('.eff-env-node')?.value || '';
                if (nodeVal) eff.params.target_node = nodeVal;
            } else if (effType === 'adjust_environment') {
                const adjTemp = row.querySelector('.eff-adj-temp')?.value;
                if (adjTemp !== undefined && adjTemp !== '') eff.params.temperature = parseInt(adjTemp);
                const adjLight = row.querySelector('.eff-adj-light')?.value;
                if (adjLight !== undefined && adjLight !== '') eff.params.light = parseInt(adjLight);
            } else if (effType === 'save') {
                const mode = row.querySelector('.eff-save-mode')?.value || 'stat';
                if (mode === 'skill') {
                    eff.params.skill = row.querySelector('.eff-save-skill')?.value || 'Athletics';
                    delete eff.params.stat;
                } else {
                    eff.params.stat = row.querySelector('.eff-save-stat')?.value || 'WIS';
                    delete eff.params.skill;
                }
                eff.params.dc = parseInt(row.querySelector('.eff-save-dc')?.value) || 12;
                eff.params.on_success = TriggerEditor._buildSaveBranchEffect(row, 'success');
                eff.params.on_fail = TriggerEditor._buildSaveBranchEffect(row, 'fail');
            } else if (effType === 'add_tag' || effType === 'remove_tag') {
                eff.params.node_id = row.querySelector('.eff-tag-node')?.value || 'self';
                eff.params.tag = row.querySelector('.eff-tag-name')?.value || '';
                const tagMsg = row.querySelector('.eff-tag-msg')?.value;
                if (tagMsg) eff.params.message = tagMsg;
            } else if (effType === 'apply_trait' || effType === 'remove_trait') {
                eff.params.trait = row.querySelector('.eff-trait-id')?.value || '';
                eff.params.target = row.querySelector('.eff-trait-target')?.value || 'self';
                if (effType === 'apply_trait') {
                    const paramVal = row.querySelector('.eff-trait-param')?.value;
                    eff.params.param = (paramVal === undefined || paramVal === '') ? true : paramVal;
                }
            } else if (effType === 'apply_condition' || effType === 'remove_condition') {
                eff.params.condition = row.querySelector('.eff-condition-id')?.value || '';
                const by = row.querySelector('.eff-condition-target-by')?.value || 'self';
                if (by === 'self') {
                    eff.params.target = 'self';
                    delete eff.params.target_by;
                    delete eff.params.target_value;
                } else if (by === 'all_in_area') {
                    eff.params.target_by = 'all_in_area';
                    delete eff.params.target_value;
                    delete eff.params.target;
                } else {
                    eff.params.target_by = by;
                    eff.params.target_value = row.querySelector('.eff-condition-target')?.value || '';
                    delete eff.params.target;
                }
                if (effType === 'apply_condition') {
                    const durVal = row.querySelector('.eff-condition-duration')?.value;
                    if (durVal !== undefined && durVal !== '') eff.params.duration = parseInt(durVal);
                    const srcVal = row.querySelector('.eff-condition-source')?.value;
                    if (srcVal) eff.params.source = srcVal;
                    // Per-tick drain form: only non-zero vitals are serialized.
                    // All zeros → omit periodic entirely (catalog default applies).
                    const drain = {};
                    ['HP','Energy','Hunger','Thirst','Hygiene','Social','Bladder','Sanity','Entertainment','Temperature'].forEach(v => {
                        const el = row.querySelector(`.eff-periodic-${v}`);
                        if (!el) return;
                        const val = parseFloat(el.value);
                        if (!isNaN(val) && val !== 0) drain[v] = val;
                    });
                    if (Object.keys(drain).length > 0) eff.params.periodic = drain;
                    const symVal = row.querySelector('.eff-condition-symptoms')?.value;
                    if (symVal) {
                        try { eff.params.symptoms = JSON.parse(symVal); } catch (e) {}
                    }
                    const extraVal = row.querySelector('.eff-condition-extras')?.value;
                    if (extraVal) {
                        try { eff.params.extra_conditions = JSON.parse(extraVal); } catch (e) {}
                    }
                }
            }
            effects.push(eff);
        });

        // Collect condition tree
        const condContainer = document.getElementById('te-conditions-container');
        const conditions = TriggerEditor._collectConditionGroup(condContainer);

        const result = {
            name: document.getElementById('te-trigger-name')?.value || '',
            trigger_type: triggerType,
            effects: effects,
            conditions: conditions,
            target_name: document.getElementById('te-target-name')?.value || '',
            target_state: document.getElementById('te-target-state')?.value || '',
            success_message: document.getElementById('te-success-msg')?.value || '',
            fail_message: document.getElementById('te-fail-msg')?.value || ''
        };

        // The runtime reads messages from the first effect's params
        // (trigger_system.py reads fail_message there) — mirror them so
        // configured messages actually surface in-game.
        if (effects.length > 0) {
            if (!effects[0].params) effects[0].params = {};
            if (result.success_message) effects[0].params.success_message = result.success_message;
            if (result.fail_message) effects[0].params.fail_message = result.fail_message;
        }

        // For backward compat: if single trigger type, store as string
        if (this._mode === 'single' && Array.isArray(result.trigger_type)) {
            result.trigger_type = result.trigger_type[0] || 'message';
        }

        return result;
    },

    // ─────────────────── Condition Rule Tree ───────────────────

    _loadConditionTree(conditions, defaultOperator, container) {
        // Accept tree object {operator, conditions} or flat array
        let tree = conditions;
        if (Array.isArray(conditions)) {
            tree = { operator: defaultOperator || 'and', conditions: conditions };
        }
        if (!tree || !tree.conditions || tree.conditions.length === 0) {
            window.Lit.render(triggerEditorTag`<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No conditions — always fires.</div>`, container);
            return;
        }
        window.Lit.render(triggerEditorTag`${window.Lit.nothing}`, container);
        TriggerEditor._renderConditionGroup(tree, container, 0);
    },

    _renderConditionGroup(group, parentEl, depth) {
        const operator = group.operator || 'and';
        const items = group.conditions || [];

        const groupDiv = document.createElement('div');
        groupDiv.className = 'cond-group';
        groupDiv.style.cssText = `margin:${depth === 0 ? '0' : '4px 0'};padding-left:${depth === 0 ? '0' : '12px'};`;

        // Header: operator selector
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;align-items:center;gap:4px;margin-bottom:4px;';
        if (depth > 0) {
            const bracket = document.createElement('span');
            bracket.textContent = '└─';
            bracket.style.cssText = 'color:var(--text-muted);font-size:10px;margin-right:2px;';
            header.appendChild(bracket);
        }
        const opSelect = document.createElement('select');
        opSelect.className = 'cond-group-op';
        opSelect.style.cssText = 'font-size:10px;padding:1px 4px;border-radius:4px;background:var(--bg-input);color:var(--text);border:1px solid var(--pink);';
        window.Lit.render(triggerEditorTag`<option value="and" ?selected=${operator === 'and'}>ALL</option><option value="or" ?selected=${operator === 'or'}>ANY</option>`, opSelect);
        header.appendChild(opSelect);
        const label = document.createElement('span');
        label.style.cssText = 'font-size:10px;color:var(--text-muted);';
        label.textContent = depth === 0 ? 'of these are true:' : 'of:';
        header.appendChild(label);

        // Ungroup button (for nested groups)
        if (depth > 0) {
            const ungroupBtn = document.createElement('button');
            ungroupBtn.textContent = '↑ ungroup';
            ungroupBtn.style.cssText = 'margin-left:auto;font-size:9px;padding:1px 6px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--text-muted);cursor:pointer;';
            ungroupBtn.onclick = () => TriggerEditor._ungroupGroup(groupDiv);
            header.appendChild(ungroupBtn);
        }

        groupDiv.appendChild(header);

        // Items container
        const itemsDiv = document.createElement('div');
        itemsDiv.className = 'cond-group-items';
        itemsDiv.style.cssText = 'border-left:2px solid var(--pink);padding-left:8px;';

        items.forEach((item, idx) => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'cond-group-item';

            // Operator pill between items
            if (idx > 0) {
                const pill = document.createElement('div');
                pill.className = 'cond-op-pill';
                pill.style.cssText = 'font-size:9px;font-weight:600;color:var(--pink);padding:1px 0;margin:2px 0;text-transform:uppercase;letter-spacing:0.5px;';
                pill.textContent = operator;
                itemDiv.appendChild(pill);
            }

            if (item.operator) {
                // Nested group
                TriggerEditor._renderConditionGroup(item, itemDiv, depth + 1);
            } else {
                // Leaf condition
                const row = TriggerEditor._buildConditionRowEl(item);
                itemDiv.appendChild(row);
            }

            itemsDiv.appendChild(itemDiv);
        });

        groupDiv.appendChild(itemsDiv);

        // Action buttons
        const actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:4px;margin-top:4px;';
        const addCondBtn = document.createElement('button');
        addCondBtn.className = 'btn btn-sm';
        addCondBtn.textContent = '➕ Condition';
        addCondBtn.style.cssText = 'font-size:9px;padding:2px 6px;';
        addCondBtn.onclick = () => TriggerEditor._addCondLeafTo(itemsDiv, operator);
        actions.appendChild(addCondBtn);
        const addGroupBtn = document.createElement('button');
        addGroupBtn.className = 'btn btn-sm';
        addGroupBtn.textContent = '📁 Group';
        addGroupBtn.style.cssText = 'font-size:9px;padding:2px 6px;';
        addGroupBtn.onclick = () => TriggerEditor._addCondGroupTo(itemsDiv, operator);
        actions.appendChild(addGroupBtn);

        groupDiv.appendChild(actions);
        parentEl.appendChild(groupDiv);
    },

    _buildConditionRowEl(existingCond) {
        const ctype = existingCond?.type || 'skill_check';
        const cv = existingCond?.value || '';
        const cStat = existingCond?.stat || 'HP';
        const cOp = existingCond?.operator || 'lt';
        const cSkill = existingCond?.skill || existingCond?.stat || 'Athletics';
        const cSaveType = existingCond?.save_type || 'stat';
        const cDc = existingCond?.dc || (existingCond?.type === 'save_throw' ? 12 : 10);
        const cTarget = existingCond?.target && existingCond.target !== 'self' ? existingCond.target : '';
        const cMode = existingCond?.mode || 'contains';
        const cPhrase = existingCond?.phrase || existingCond?.value || '';
        const isItems = ctype === 'has_items';
        const dispVal = isItems ? (Array.isArray(cv) ? cv.join(', ') : cv) : cv;
        const condOptionsHtml = (this._conditionTypes || []).length
            ? this._buildGroupedCondOpts(this._conditionTypes, existingCond?.type || 'skill_check')
            : `<option value="skill_check">Skill check</option>`;

        const SHOWS = (types) => types.includes(ctype) ? 'block' : 'none';
        const OPTS = ['lt', 'le', 'eq', 'ge', 'gt'].map(o =>
            triggerEditorTag`<option value=${o} ?selected=${cOp === o}>${o}</option>`);
        const SKILL_OPTS = ['STR','DEX','CON','INT','WIS','CHA','Athletics','Acrobatics','Stealth','Perception','Survival','Persuasion','Investigation']
            .map(s => triggerEditorTag`<option value=${s} ?selected=${(cSaveType === 'stat' ? cStat : cSkill) === s}>${s}</option>`);

        const row = document.createElement('div');
        row.className = 'cond-row';
        row.style.cssText = 'background:var(--bg-inset);border-radius:4px;padding:6px;margin-bottom:0;border-left:3px solid var(--pink);position:relative;';

        window.Lit.render(triggerEditorTag`
            <select class="cond-type" style="width:100%;font-size:10px;margin-bottom:3px;" @change=${(e) => TriggerEditor._toggleConditionFields(e.target)}>
                ${window.Lit.unsafeHTML(condOptionsHtml)}
            </select>
            <div class="cond-fields">
                <div class="cond-field" data-cond="uses_reached,uses_above,random_chance,has_item,has_items,has_trait,has_tag,state_equals,speech_matches,time_of_day,weather" style="display:${SHOWS(['uses_reached','uses_above','random_chance','has_item','has_items','has_trait','has_tag','state_equals','speech_matches','time_of_day','weather'])};">
                    <div data-subcond="uses_reached,uses_above,random_chance,has_item,has_items,has_trait,speech_matches,time_of_day,weather" style="display:${ctype === 'has_tag' ? 'none' : 'block'};">
                    ${ctype === 'has_item'
                        ? triggerEditorTag`<label style="font-size:9px;">Item Name</label><div class="eff-select" data-kind="items" data-input-class="cond-value" data-value=${cv} data-placeholder="key, torch..." data-free="true" style="width:100%;font-size:11px;"></div>`
                        : ctype === 'has_trait'
                        ? triggerEditorTag`<label style="font-size:9px;">Trait ID</label><div class="eff-select" data-kind="traits" data-input-class="cond-value" data-value=${cv} data-placeholder="dark_vision, hardy..." data-free="true" style="width:100%;font-size:11px;"></div>`
                        : ctype === 'random_chance'
                        ? triggerEditorTag`<label style="font-size:9px;">Chance %</label><input type="number" class="cond-value" .value=${dispVal} min="0" max="100" placeholder="0-100" style="width:100%;font-size:11px;">`
                        : ctype === 'time_of_day'
                        ? triggerEditorTag`<label style="font-size:9px;">Clock time (HH:MM)</label><input type="time" class="cond-value" .value=${cv} style="width:100%;font-size:11px;">`
                        : ctype === 'weather'
                        ? triggerEditorTag`<label style="font-size:9px;">Weather</label><input type="text" class="cond-value" .value=${cv} list="eff-weather-list" placeholder="rain, clear, fog, storm..." style="width:100%;font-size:11px;">`
                        : ctype === 'speech_matches'
                        ? triggerEditorTag`<label style="font-size:9px;">Phrase</label><input type="text" class="cond-value" .value=${cPhrase} placeholder="e.g. hello, help..." style="width:100%;font-size:11px;">`
                        : triggerEditorTag`<label style="font-size:9px;">${ctype === 'has_items' ? 'Comma-separated items' : 'Value'}</label><input type="text" class="cond-value" .value=${dispVal} style="width:100%;font-size:11px;">`}
                    </div>
                    <div data-subcond="has_tag" style="display:${ctype === 'has_tag' ? 'block' : 'none'};">
                        <label style="font-size:9px;">Tags (any of)</label><div class="cond-tag-multi" data-value=${Array.isArray(existingCond?.value) ? existingCond.value.join(',') : (existingCond?.value || '')}></div>
                    </div>
                </div>
                <div class="cond-field" data-cond="area_temp,vital,vital_above,vital_below" style="display:${SHOWS(['area_temp','vital','vital_above','vital_below'])};">
                    <div style="display:flex;gap:4px;">
                        <div style="flex:1;"><label style="font-size:9px;">Comparator</label>
                            <select class="cond-operator" style="width:100%;font-size:10px;">${OPTS}</select>
                        </div>
                        <div style="flex:1;"><label style="font-size:9px;">Value</label>
                            <input type="number" class="cond-value" .value=${cv} step="any" style="width:100%;font-size:11px;">
                        </div>
                    </div>
                </div>
                <div class="cond-field" data-cond="vital,vital_above,vital_below" style="display:${SHOWS(['vital','vital_above','vital_below'])};">
                    <label style="font-size:9px;">Vital</label>
                    <div class="eff-select" data-kind="vitals" data-input-class="cond-stat" data-value=${cStat} data-placeholder="HP, Energy, Hunger..." data-free="true" style="width:100%;font-size:11px;"></div>
                </div>
                <div class="cond-field" data-cond="is_equipped" style="display:${SHOWS(['is_equipped'])};">
                    <label style="font-size:9px;">Item</label>
                    <div class="eff-select" data-kind="items" data-input-class="cond-item" data-value=${existingCond?.item || ''} data-placeholder="torch, key..." data-free="true" style="width:100%;font-size:11px;"></div>
                </div>
                <div class="cond-field" data-cond="state_equals" style="display:${SHOWS(['state_equals'])};">
                    <label style="font-size:9px;">Target Node</label>
                    <div class="eff-select" data-kind="nodes" data-input-class="cond-node" data-value=${existingCond?.node || cTarget} data-placeholder="node_id or name" style="width:100%;font-size:11px;"></div>
                    <label style="font-size:9px;">State</label>
                    <div class="eff-select" data-kind="states" data-input-class="cond-state" data-value=${existingCond?.state || cv} data-placeholder="on, off, open, lit..." data-free="true" style="width:100%;font-size:11px;"></div>
                </div>
                <div class="cond-field" data-cond="speech_matches" style="display:${SHOWS(['speech_matches'])};">
                    <label style="font-size:9px;">Match Mode</label>
                    <select class="cond-mode" style="width:100%;font-size:10px;">
                        <option value="contains" ?selected=${cMode === 'contains'}>Contains</option>
                        <option value="exact" ?selected=${cMode === 'exact'}>Exact match</option>
                        <option value="startswith" ?selected=${cMode === 'startswith'}>Starts with</option>
                        <option value="endswith" ?selected=${cMode === 'endswith'}>Ends with</option>
                        <option value="fuzzy" ?selected=${cMode === 'fuzzy'}>Whole word</option>
                    </select>
                </div>
                <div class="cond-field" data-cond="skill_check" style="display:${SHOWS(['skill_check'])};">
                    <label style="font-size:9px;">Skill</label><div class="eff-select" data-kind="skills" data-input-class="cond-skill" data-value=${cSkill} data-placeholder="Athletics, Perception..." data-free="true" style="width:100%;font-size:11px;"></div>
                    <label style="font-size:9px;">DC</label><input type="number" class="cond-dc" .value=${cDc} style="width:100%;font-size:11px;">
                </div>
                <div class="cond-field" data-cond="save_throw" style="display:${SHOWS(['save_throw'])};">
                    <label style="font-size:9px;">Type</label>
                    <select class="cond-save-type" style="width:100%;font-size:10px;" @change=${(e) => { const row=e.target.closest('.cond-row'); row.querySelector('.cond-stat-or-skill').style.display = e.target.value==='stat' ? 'block':'none'; row.querySelector('.cond-skill-or-stat').style.display = e.target.value==='skill' ? 'block':'none'; }}>
                        <option value="stat" ?selected=${cSaveType !== 'skill'}>Base Stat</option>
                        <option value="skill" ?selected=${cSaveType === 'skill'}>Skill</option>
                    </select>
                    <div class="cond-stat-or-skill" style="display:${cSaveType !== 'skill' ? 'block' : 'none'};">
                        <label style="font-size:9px;">Stat</label><select class="cond-save-stat" style="width:100%;font-size:11px;">
                            ${['STR','DEX','CON','INT','WIS','CHA'].map(s => triggerEditorTag`<option value=${s} ?selected=${(existingCond?.stat || 'DEX') === s}>${s}</option>`)}
                        </select>
                    </div>
                    <div class="cond-skill-or-stat" style="display:${cSaveType === 'skill' ? 'block' : 'none'};">
                        <label style="font-size:9px;">Skill</label><div class="eff-select" data-kind="skills" data-input-class="cond-save-skill" data-value=${existingCond?.skill || 'Athletics'} data-placeholder="Athletics, Perception..." data-free="true" style="width:100%;font-size:11px;"></div>
                    </div>
                    <label style="font-size:9px;">DC</label><input type="number" class="cond-dc" .value=${cDc} style="width:100%;font-size:11px;">
                </div>
                <div class="cond-field" data-cond="save_throw,has_trait,has_tag,vital,vital_above,vital_below,is_equipped,area_temp" style="display:${SHOWS(['state_equals','save_throw','has_trait','has_tag','vital','vital_above','vital_below','is_equipped','area_temp'])};">
                    <label style="font-size:9px;">Target (blank = self)</label><div class="eff-select" data-kind="chars" data-input-class="cond-target" data-value=${cTarget} data-placeholder="self or character name" data-free="true" style="width:100%;font-size:11px;"></div>
                </div>
            </div>
            <span @click=${(e) => TriggerEditor._removeCondItem(e.target)} style="position:absolute;top:4px;right:4px;cursor:pointer;color:var(--red);font-size:10px;">✕</span>
        `, row);

        return row;
    },

    _collectConditionGroup(parentEl) {
        // Check for the placeholder "no conditions" text
        const placeholder = parentEl.querySelector('[style*="font-size:11px;color:var(--text-muted)"]');
        const group = parentEl.querySelector(':scope > .cond-group');
        if (placeholder || !group) {
            return {};
        }

        const opSelect = group.querySelector('.cond-group-op');
        const operator = opSelect?.value || 'and';
        const itemsDiv = group.querySelector('.cond-group-items');
        const conditions = [];

        if (itemsDiv) {
            const itemEls = itemsDiv.querySelectorAll(':scope > .cond-group-item');
            itemEls.forEach(itemEl => {
                const nestedGroup = itemEl.querySelector(':scope > .cond-group');
                if (nestedGroup) {
                    conditions.push(TriggerEditor._collectConditionGroup(itemEl));
                } else {
                    const row = itemEl.querySelector('.cond-row');
                    if (row) {
                        const ctype = row.querySelector('.cond-type')?.value || '';
                        const cond = { type: ctype };
                        const q = (cls) => row.querySelector(`.${cls}`)?.value;
                        if (ctype === 'has_item') {
                            cond.value = q('cond-value') || '';
                        } else if (ctype === 'skill_check') {
                            cond.skill = q('cond-skill') || 'Athletics';
                            cond.dc = parseInt(q('cond-dc')) || 10;
                        } else if (ctype === 'save_throw') {
                            if ((q('cond-save-type') || 'stat') === 'skill') {
                                cond.skill = q('cond-save-skill') || 'Athletics';
                            } else {
                                cond.stat = q('cond-save-stat') || 'DEX';
                            }
                            cond.dc = parseInt(q('cond-dc')) || 12;
                            cond.target = q('cond-target') || 'self';
                        } else if (ctype === 'state_equals') {
                            const node = q('cond-node') || '';
                            const state = q('cond-state') || '';
                            if (node) cond.target = node;
                            cond.value = state || q('cond-value') || '';
                        } else if (ctype === 'has_trait') {
                            cond.value = q('cond-value') || '';
                            cond.target = q('cond-target') || 'self';
                        } else if (ctype === 'has_tag') {
                            const multi = row.querySelector('.cond-tag-multi');
                            cond.value = (multi && multi.__condTagMulti) ? multi.__condTagMulti.tags : (q('cond-value') || '');
                            cond.target = q('cond-target') || 'self';
                        } else if (ctype === 'has_items') {
                            const val = q('cond-value') || '';
                            cond.value = val.split(',').map(s => s.trim()).filter(Boolean);
                        } else if (ctype === 'speech_matches') {
                            cond.phrase = q('cond-value') || '';
                            cond.mode = q('cond-mode') || 'contains';
                        } else if (ctype === 'area_temp' || ctype === 'vital' || ctype === 'vital_above' || ctype === 'vital_below') {
                            cond.value = parseFloat(q('cond-value')) || 0;
                            cond.operator = q('cond-operator') || 'lt';
                            if (ctype === 'vital' || ctype === 'vital_above' || ctype === 'vital_below') {
                                cond.stat = q('cond-stat') || 'HP';
                            }
                            cond.target = q('cond-target') || 'self';
                        } else if (ctype === 'is_equipped') {
                            cond.item = q('cond-item') || '';
                            cond.target = q('cond-target') || 'self';
                        } else if (ctype === 'random_chance') {
                            cond.value = parseInt(q('cond-value')) || 0;
                        } else if (ctype === 'time_of_day' || ctype === 'weather') {
                            cond.value = q('cond-value') || '';
                        } else {
                            cond.value = q('cond-value') || '';
                        }
                        conditions.push(cond);
                    }
                }
            });
        }

        if (conditions.length === 0) {
            return {};
        }

        return { operator, conditions };
    },

    _addCondLeaf() {
        const container = document.getElementById('te-conditions-container');
        if (!container) return;
        const group = container.querySelector(':scope > .cond-group');
        if (!group) {
            // First items — create default group
            TriggerEditor._addCondGroup();
            // Then add condition to it
            const newGroup = container.querySelector(':scope > .cond-group');
            if (newGroup) {
                const itemsDiv = newGroup.querySelector('.cond-group-items');
                TriggerEditor._addLeafTo(itemsDiv, 'and');
            }
            return;
        }
        const itemsDiv = group.querySelector('.cond-group-items');
        TriggerEditor._addLeafTo(itemsDiv, group.querySelector('.cond-group-op')?.value || 'and');
    },

    _addCondGroup() {
        const container = document.getElementById('te-conditions-container');
        if (!container) return;
        const existing = container.querySelector(':scope > .cond-group');
        if (!existing) {
            window.Lit.render(triggerEditorTag`${window.Lit.nothing}`, container);
            TriggerEditor._renderConditionGroup({ operator: 'and', conditions: [] }, container, 0);
            return;
        }
        const itemsDiv = existing.querySelector('.cond-group-items');
        const operator = existing.querySelector('.cond-group-op')?.value || 'and';
        TriggerEditor._addGroupTo(itemsDiv, operator);
    },

    _addCondLeafTo(itemsDiv, parentOperator) {
        TriggerEditor._addLeafTo(itemsDiv, parentOperator);
    },

    _addCondGroupTo(itemsDiv, parentOperator) {
        TriggerEditor._addGroupTo(itemsDiv, parentOperator);
    },

    _addLeafTo(itemsDiv, parentOperator) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'cond-group-item';

        // Operator pill
        const existingItems = itemsDiv.querySelectorAll(':scope > .cond-group-item');
        if (existingItems.length > 0) {
            const pill = document.createElement('div');
            pill.className = 'cond-op-pill';
            pill.style.cssText = 'font-size:9px;font-weight:600;color:var(--pink);padding:1px 0;margin:2px 0;text-transform:uppercase;letter-spacing:0.5px;';
            pill.textContent = parentOperator;
            itemDiv.appendChild(pill);
        }

        const row = TriggerEditor._buildConditionRowEl(null);
        itemDiv.appendChild(row);
        itemsDiv.appendChild(itemDiv);
        TriggerEditor._initEffectSearchSelects(itemDiv);
        TriggerEditor._initCondTagMultis(itemDiv);
        TriggerEditor._updateFailGroupVisibility();
    },

    _addGroupTo(itemsDiv, parentOperator) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'cond-group-item';

        // Operator pill
        const existingItems = itemsDiv.querySelectorAll(':scope > .cond-group-item');
        if (existingItems.length > 0) {
            const pill = document.createElement('div');
            pill.className = 'cond-op-pill';
            pill.style.cssText = 'font-size:9px;font-weight:600;color:var(--pink);padding:1px 0;margin:2px 0;text-transform:uppercase;letter-spacing:0.5px;';
            pill.textContent = parentOperator;
            itemDiv.appendChild(pill);
        }

        TriggerEditor._renderConditionGroup({ operator: 'and', conditions: [] }, itemDiv, 1);
        itemsDiv.appendChild(itemDiv);
        TriggerEditor._initEffectSearchSelects(itemDiv);
        TriggerEditor._initCondTagMultis(itemDiv);
        TriggerEditor._updateFailGroupVisibility();
    },

    _ungroupGroup(groupDiv) {
        // Move all children of this group up to the parent group
        const parentItem = groupDiv.closest('.cond-group-item');
        if (!parentItem) return;
        const parentItemsDiv = groupDiv.closest('.cond-group-items');
        if (!parentItemsDiv) return;

        const itemsDiv = groupDiv.querySelector('.cond-group-items');
        if (!itemsDiv) return;
        const children = Array.from(itemsDiv.querySelectorAll(':scope > .cond-group-item'));

        const idx = Array.from(parentItemsDiv.querySelectorAll(':scope > .cond-group-item')).indexOf(parentItem);

        // Remove the group item
        parentItem.remove();
        TriggerEditor._updateFailGroupVisibility();

        // Insert children at the same position
        children.forEach((child, ci) => {
            // If not first child in the list, prepend operator pill
            if (ci > 0) {
                const existingPill = child.querySelector('.cond-op-pill');
                if (!existingPill) {
                    const pill = document.createElement('div');
                    pill.className = 'cond-op-pill';
                    pill.style.cssText = 'font-size:9px;font-weight:600;color:var(--pink);padding:1px 0;margin:2px 0;text-transform:uppercase;letter-spacing:0.5px;';
                    const opSelect = groupDiv.querySelector('.cond-group-op');
                    pill.textContent = opSelect?.value || 'and';
                    child.insertBefore(pill, child.firstChild);
                }
            }
        });

        const insertAfter = parentItemsDiv.children[idx];
        if (insertAfter) {
            children.forEach(child => {
                parentItemsDiv.insertBefore(child, insertAfter.nextSibling);
            });
        } else {
            children.forEach(child => {
                parentItemsDiv.appendChild(child);
            });
        }
    },

    /**
     * Render a condition tree as an array of HTML summary strings.
     * Handles both tree format {operator, conditions} and flat array format.
     */
    _renderConditionSummary(conditions) {
        if (!conditions) return [];
        // Tree format
        if (typeof conditions === 'object' && !Array.isArray(conditions) && conditions.operator) {
            const items = conditions.conditions || [];
            const op = conditions.operator === 'and' ? '+' : '|';
            const results = [];
            items.forEach((item, idx) => {
                if (item.operator) {
                    // Nested group
                    const nested = TriggerEditor._renderConditionSummary(item);
                    if (nested.length > 0) {
                        results.push(`<span style="color:var(--pink);font-size:9px;">(</span>`);
                        results.push(...nested);
                        results.push(`<span style="color:var(--pink);font-size:9px;">)</span>`);
                    }
                } else {
                    results.push(TriggerEditor._renderConditionLeaf(item));
                }
                if (idx < items.length - 1) {
                    results.push(`<span style="color:var(--text-muted);font-size:9px;font-weight:600;"> ${op} </span>`);
                }
            });
            return results;
        }
        // Flat array format
        if (Array.isArray(conditions)) {
            return conditions.map(c => TriggerEditor._renderConditionLeaf(c));
        }
        return [];
    },

    _renderConditionLeaf(cond) {
        if (!cond || !cond.type) return '';
        if (cond.type === 'skill_check' || cond.type === 'save_throw') {
            const check = cond.type === 'save_throw' ? (cond.stat || cond.skill || 'DEX') : (cond.skill || 'Athletics');
            const dc = cond.dc || (cond.type === 'save_throw' ? 12 : 10);
            const tgt = cond.type === 'save_throw' && cond.target && cond.target !== 'self' ? ` target=${cond.target}` : '';
            return `<span style="color:var(--pink);font-size:9px;">if ${cond.type}(${check} DC${dc}${tgt})</span>`;
        }
        if (cond.type === 'has_items') {
            const items = Array.isArray(cond.value) ? cond.value.join(',') : (cond.value||'');
            return `<span style="color:var(--pink);font-size:9px;">if ${cond.type}=[${items}]</span>`;
        }
        return `<span style="color:var(--pink);font-size:9px;">if ${cond.type}=${cond.value||cond.target||''}</span>`;
    },

    // ─────────────────── Effects ───────────────────

    _parseSaveBranchEffect(branchArr) {
        const first = (branchArr || [])[0];
        if (!first?.type) return { type: 'none' };
        const params = first.params || {};
        if (first.type === 'message') return { type: 'message', message: params.message || '' };
        if (first.type === 'apply_condition') {
            return {
                type: 'apply_condition',
                condition: params.condition || '',
                duration: params.duration,
                source: params.source || '',
                source_type: params.source_type || '',
            };
        }
        if (first.type === 'damage') return { type: 'damage', amount: params.amount || 5 };
        return { type: 'none' };
    },

    _buildSaveBranchEffect(row, prefix) {
        const jsonVal = row.querySelector(`.eff-save-${prefix}-json`)?.value?.trim();
        if (jsonVal) {
            try {
                const parsed = JSON.parse(jsonVal);
                return Array.isArray(parsed) ? parsed : [];
            } catch (e) {
                return [];
            }
        }
        const type = row.querySelector(`.eff-save-${prefix}-type`)?.value || 'none';
        if (type === 'none') return [];
        if (type === 'message') {
            const msg = row.querySelector(`.eff-save-${prefix}-msg`)?.value || '';
            return msg ? [{ type: 'message', params: { message: msg } }] : [];
        }
        if (type === 'apply_condition') {
            const params = { condition: row.querySelector(`.eff-save-${prefix}-cond`)?.value || '', target: 'self' };
            const durVal = row.querySelector(`.eff-save-${prefix}-dur`)?.value;
            if (durVal !== undefined && durVal !== '') params.duration = parseInt(durVal);
            const src = row.querySelector(`.eff-save-${prefix}-source`)?.value;
            if (src) params.source = src;
            const srcType = row.querySelector(`.eff-save-${prefix}-src-type`)?.value;
            if (srcType) params.source_type = srcType;
            return [{ type: 'apply_condition', params }];
        }
        if (type === 'damage') {
            return [{
                type: 'damage',
                params: {
                    amount: parseInt(row.querySelector(`.eff-save-${prefix}-dmg`)?.value) || 5,
                    target: 'self',
                },
            }];
        }
        return [];
    },

    _toggleSaveMode(select) {
        const row = select.closest('.eff-row');
        if (!row) return;
        const mode = select.value;
        const statWrap = row.querySelector('.eff-save-stat-wrap');
        const skillWrap = row.querySelector('.eff-save-skill-wrap');
        if (statWrap) statWrap.style.display = mode === 'stat' ? 'block' : 'none';
        if (skillWrap) skillWrap.style.display = mode === 'skill' ? 'block' : 'none';
    },

    _toggleSaveBranch(row, prefix) {
        if (typeof row === 'string') {
            prefix = row;
            row = null;
        }
        if (!row || !row.querySelector) {
            row = document.querySelector(`.eff-save-${prefix}-type`)?.closest('.eff-row');
        }
        if (!row) return;
        const type = row.querySelector(`.eff-save-${prefix}-type`)?.value || 'none';
        row.querySelectorAll(`.eff-save-${prefix}-field`).forEach(el => {
            const branches = (el.dataset.branch || '').split(',');
            el.style.display = branches.includes(type) ? 'block' : 'none';
        });
    },

    _buildEffectRowHtml(effectOpts, existingEff, idx) {
        const effType = existingEff?.type || 'message';
        const ep = existingEff?.params || {};
        const failFx = TriggerEditor._parseSaveBranchEffect(ep.on_fail);
        const successFx = TriggerEditor._parseSaveBranchEffect(ep.on_success);
        const saveMode = ep.skill ? 'skill' : 'stat';
        const saveCheck = ep.stat || ep.skill || 'WIS';
        const advFailJson = (ep.on_fail?.length > 1 || (ep.on_fail?.length && failFx.type === 'none'))
            ? JSON.stringify(ep.on_fail, null, 2) : '';
        const advSuccessJson = (ep.on_success?.length > 1 || (ep.on_success?.length && successFx.type === 'none'))
            ? JSON.stringify(ep.on_success, null, 2) : '';
        return `
            <div class="eff-row" data-idx="${idx}" style="background:var(--bg-inset);border-radius:6px;padding:6px;margin-bottom:4px;border-left:3px solid var(--orange);position:relative;">
                <select class="eff-type" style="width:100%;font-size:11px;margin-bottom:4px;" onchange="TriggerEditor._toggleEffectParams(this)">
                    ${effectOpts.replace(`value="${effType}"`, `value="${effType}" selected`)}
                </select>
                <div class="eff-params" style="display:${effType === 'message' ? 'none' : 'block'};">
                    <div class="eff-param" data-effect="damage,heal" style="display:${['damage','heal'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Amount</label><input type="number" class="eff-amount" value="${ep.amount || 5}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="damage" style="display:${effType === 'damage' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target</label>
                        <select class="eff-dmg-target" style="width:100%;">
                            <option value="self" ${ep.target === 'self' ? 'selected' : ''}>Self</option>
                            <option value="other" ${ep.target === 'other' ? 'selected' : ''}>Other</option>
                        </select>
                    </div>
                    <div class="eff-param" data-effect="adjust_vital" style="display:${effType === 'adjust_vital' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Stat</label>
                        <div class="eff-select" data-kind="vitals" data-input-class="eff-vital-stat" data-value="${escapeForHtmlAttribute(ep.stat || 'HP')}" data-placeholder="HP, Energy, Bladder..." data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="adjust_vital" style="display:${effType === 'adjust_vital' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Amount (+/-)</label>
                        <input type="number" class="eff-vital-amount" value="${ep.amount || 0}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="adjust_vital" style="display:${effType === 'adjust_vital' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target</label>
                        <select class="eff-vital-target" style="width:100%;">
                            <option value="self" ${ep.target === 'self' ? 'selected' : ''}>Self</option>
                            <option value="other" ${ep.target === 'other' ? 'selected' : ''}>Other</option>
                        </select>
                    </div>
                    <div class="eff-param" data-effect="save" style="display:${effType === 'save' ? 'block' : 'none'};border-top:1px solid var(--border);padding-top:6px;margin-top:4px;">
                        <label style="font-size:10px;font-weight:600;">Save roll</label>
                        <select class="eff-save-mode" style="width:100%;font-size:10px;margin-bottom:4px;" onchange="TriggerEditor._toggleSaveMode(this)">
                            <option value="stat" ${saveMode === 'stat' ? 'selected' : ''}>Ability</option>
                            <option value="skill" ${saveMode === 'skill' ? 'selected' : ''}>Skill</option>
                        </select>
                        <div class="eff-save-stat-wrap" style="display:${saveMode === 'stat' ? 'block' : 'none'};margin-bottom:4px;">
                            <label style="font-size:9px;">Stat</label>
                            <select class="eff-save-stat" style="width:100%;font-size:11px;">
                                ${['STR','DEX','CON','INT','WIS','CHA'].map(s => `<option value="${s}" ${saveCheck === s ? 'selected' : ''}>${s}</option>`).join('')}
                            </select>
                        </div>
                        <div class="eff-save-skill-wrap" style="display:${saveMode === 'skill' ? 'block' : 'none'};margin-bottom:4px;">
                            <label style="font-size:9px;">Skill</label>
                            <div class="eff-select" data-kind="skills" data-input-class="eff-save-skill" data-value="${escapeForHtmlAttribute(saveMode === 'skill' ? saveCheck : 'Athletics')}" data-placeholder="Athletics, Perception..." data-free="true" style="width:100%;"></div>
                        </div>
                        <label style="font-size:9px;">DC</label>
                        <input type="number" class="eff-save-dc" value="${ep.dc || 12}" min="1" max="30" style="width:100%;margin-bottom:6px;">
                        <label style="font-size:10px;font-weight:600;margin-top:4px;display:block;">On success</label>
                        <select class="eff-save-success-type" style="width:100%;font-size:10px;margin-bottom:4px;" onchange="TriggerEditor._toggleSaveBranch(this.closest('.eff-row'), 'success')">
                            ${['none','message','apply_condition','damage'].map(t => `<option value="${t}" ${successFx.type === t ? 'selected' : ''}>${t.replace(/_/g,' ')}</option>`).join('')}
                        </select>
                        <div class="eff-save-success-field" data-branch="message" style="display:${successFx.type === 'message' ? 'block' : 'none'};margin-bottom:4px;">
                            <input type="text" class="eff-save-success-msg" value="${escapeForHtmlAttribute(successFx.message || '')}" placeholder="You resist!" style="width:100%;font-size:11px;">
                        </div>
                        <div class="eff-save-success-field" data-branch="apply_condition" style="display:${successFx.type === 'apply_condition' ? 'block' : 'none'};margin-bottom:4px;">
                            <div class="eff-select" data-kind="conditions" data-input-class="eff-save-success-cond" data-value="${escapeForHtmlAttribute(successFx.condition || '')}" data-placeholder="frightened, poisoned..." data-free="true" style="width:100%;margin-bottom:2px;"></div>
                            <input type="number" class="eff-save-success-dur" value="${successFx.duration !== undefined ? successFx.duration : ''}" placeholder="duration ticks" style="width:100%;font-size:11px;margin-bottom:2px;">
                            <input type="text" class="eff-save-success-source" value="${escapeForHtmlAttribute(successFx.source || '')}" placeholder="source label" style="width:100%;font-size:11px;">
                        </div>
                        <div class="eff-save-success-field" data-branch="damage" style="display:${successFx.type === 'damage' ? 'block' : 'none'};margin-bottom:4px;">
                            <input type="number" class="eff-save-success-dmg" value="${successFx.amount || 5}" placeholder="damage amount" style="width:100%;font-size:11px;">
                        </div>
                        <textarea class="eff-save-success-json" rows="2" placeholder="Advanced: full on_success JSON array" style="width:100%;font-size:10px;margin-bottom:6px;display:${advSuccessJson ? 'block' : 'none'};">${escapeForHtmlAttribute(advSuccessJson)}</textarea>
                        <label style="font-size:10px;font-weight:600;margin-top:4px;display:block;">On fail</label>
                        <select class="eff-save-fail-type" style="width:100%;font-size:10px;margin-bottom:4px;" onchange="TriggerEditor._toggleSaveBranch(this.closest('.eff-row'), 'fail')">
                            ${['none','message','apply_condition','damage'].map(t => `<option value="${t}" ${failFx.type === t ? 'selected' : ''}>${t.replace(/_/g,' ')}</option>`).join('')}
                        </select>
                        <div class="eff-save-fail-field" data-branch="message" style="display:${failFx.type === 'message' ? 'block' : 'none'};margin-bottom:4px;">
                            <input type="text" class="eff-save-fail-msg" value="${escapeForHtmlAttribute(failFx.message || '')}" placeholder="You fail the save!" style="width:100%;font-size:11px;">
                        </div>
                        <div class="eff-save-fail-field" data-branch="apply_condition" style="display:${failFx.type === 'apply_condition' ? 'block' : 'none'};margin-bottom:4px;">
                            <div class="eff-select" data-kind="conditions" data-input-class="eff-save-fail-cond" data-value="${escapeForHtmlAttribute(failFx.condition || '')}" data-placeholder="frightened, poisoned..." data-free="true" style="width:100%;margin-bottom:2px;"></div>
                            <input type="number" class="eff-save-fail-dur" value="${failFx.duration !== undefined ? failFx.duration : ''}" placeholder="duration ticks" style="width:100%;font-size:11px;margin-bottom:2px;">
                            <input type="text" class="eff-save-fail-source" value="${escapeForHtmlAttribute(failFx.source || '')}" placeholder="source label" style="width:100%;font-size:11px;margin-bottom:2px;">
                            <select class="eff-save-fail-src-type" style="width:100%;font-size:10px;">
                                <option value="" ${!failFx.source_type ? 'selected' : ''}>— source type —</option>
                                ${['way','area','item','character'].map(st => `<option value="${st}" ${failFx.source_type === st ? 'selected' : ''}>${st}</option>`).join('')}
                            </select>
                        </div>
                        <div class="eff-save-fail-field" data-branch="damage" style="display:${failFx.type === 'damage' ? 'block' : 'none'};margin-bottom:4px;">
                            <input type="number" class="eff-save-fail-dmg" value="${failFx.amount || 5}" placeholder="damage amount" style="width:100%;font-size:11px;">
                        </div>
                        <textarea class="eff-save-fail-json" rows="2" placeholder="Advanced: full on_fail JSON array" style="width:100%;font-size:10px;display:${advFailJson ? 'block' : 'none'};">${escapeForHtmlAttribute(advFailJson)}</textarea>
                        <button type="button" class="btn btn-sm btn-ghost" style="font-size:9px;margin-top:4px;" onclick="const r=this.closest('.eff-row'); r.querySelector('.eff-save-fail-json').style.display='block'; r.querySelector('.eff-save-success-json').style.display='block';">Show advanced JSON</button>
                    </div>
                    <div class="eff-param" data-effect="add_tag,remove_tag" style="display:${['add_tag','remove_tag'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target Node</label>
                        <div class="eff-select" data-kind="nodes" data-input-class="eff-tag-node" data-value="${escapeForHtmlAttribute(ep.node_id || 'self')}" data-placeholder="self or node_id" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="add_tag,remove_tag" style="display:${['add_tag','remove_tag'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Tag</label>
                        <div class="eff-select" data-kind="tags" data-input-class="eff-tag-name" data-value="${escapeForHtmlAttribute(ep.tag || '')}" data-placeholder="flammable, container..." data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="add_tag,remove_tag" style="display:${['add_tag','remove_tag'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Message (optional)</label>
                        <input type="text" class="eff-tag-msg" value="${escapeForHtmlAttribute(ep.message || '')}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="spawn_item" style="display:${effType === 'spawn_item' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Item ID</label>
                        <div class="eff-select" data-kind="items" data-input-class="eff-spawn-id" data-value="${escapeForHtmlAttribute(ep.item_id || '')}" data-placeholder="item_key" data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="spawn_item" style="display:${effType === 'spawn_item' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Display Name</label>
                        <input type="text" class="eff-spawn-name" value="${escapeForHtmlAttribute(ep.display_name || '')}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="spawn_item" style="display:${effType === 'spawn_item' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Place into</label>
                        <select class="eff-spawn-into" style="width:100%;font-size:11px;">
                            <option value="area" ${(!ep.into || ep.into === 'area') ? 'selected' : ''}>Current area</option>
                            <option value="container" ${ep.into === 'container' ? 'selected' : ''}>This container (self)</option>
                        </select>
                    </div>
                    <div class="eff-param" data-effect="spawn_item" style="display:${effType === 'spawn_item' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Capture</label>
                        <select class="eff-spawn-capture" style="width:100%;font-size:11px;">
                            <option value="" ${!ep.capture ? 'selected' : ''}>— none —</option>
                            <option value="speech" ${ep.capture === 'speech' ? 'selected' : ''}>Recent speech (recorder)</option>
                        </select>
                    </div>
                    <div class="eff-param" data-effect="spawn_character" style="display:${effType === 'spawn_character' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Character ID</label>
                        <div class="eff-select" data-kind="chars" data-input-class="eff-spawn-char-id" data-value="${escapeForHtmlAttribute(ep.character_id || '')}" data-placeholder="character_id (library file name)" data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="spawn_character" style="display:${effType === 'spawn_character' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Display Name (optional override)</label>
                        <input type="text" class="eff-spawn-char-name" value="${escapeForHtmlAttribute(ep.display_name || '')}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="spawn_character" style="display:${effType === 'spawn_character' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Area (optional, blank = current area)</label>
                        <div class="eff-select" data-kind="areas" data-input-class="eff-spawn-char-area" data-value="${escapeForHtmlAttribute(ep.area || '')}" data-placeholder="Search areas..." data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="spawn_character" style="display:${effType === 'spawn_character' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Message (optional, supports {character_name})</label>
                        <input type="text" class="eff-spawn-char-msg" value="${escapeForHtmlAttribute(ep.message || '')}" placeholder="{character_name} arrives!" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="give_item" style="display:${effType === 'give_item' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Item ID to Give</label>
                        <div class="eff-select" data-kind="items" data-input-class="eff-give-id" data-value="${escapeForHtmlAttribute(ep.item_id || '')}" data-placeholder="item_key" data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="give_item" style="display:${effType === 'give_item' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target</label>
                        <div class="eff-select" data-kind="chars" data-input-class="eff-give-target" data-value="${escapeForHtmlAttribute(ep.target || 'self')}" data-placeholder="self, target, or character name" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="give_item" style="display:${effType === 'give_item' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Message (optional)</label>
                        <input type="text" class="eff-give-msg" value="${escapeForHtmlAttribute(ep.message || '')}" placeholder="supports {target_name}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="remove_item" style="display:${effType === 'remove_item' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Item ID to Remove</label>
                        <div class="eff-select" data-kind="items" data-input-class="eff-remove-id" data-value="${escapeForHtmlAttribute(ep.item_id || '')}" data-placeholder="item_key" data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="set_state" style="display:${effType === 'set_state' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Node ID</label>
                        <div class="eff-select" data-kind="nodes" data-input-class="eff-state-node" data-value="${escapeForHtmlAttribute(ep.node_id || 'self')}" data-placeholder="self or node_id" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="set_state" style="display:${effType === 'set_state' ? 'block' : 'none'};">
                        <label style="font-size:10px;">New State</label>
                        <div class="eff-select" data-kind="states" data-input-class="eff-state-val" data-value="${escapeForHtmlAttribute(ep.state || 'on')}" data-placeholder="on, off, open..." data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="set_hidden,adjust_uses" style="display:${['set_hidden','adjust_uses'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Node ID</label>
                        <div class="eff-select" data-kind="nodes" data-input-class="eff-hidden-node" data-value="${escapeForHtmlAttribute(ep.node_id || 'self')}" data-placeholder="self or node_id" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="adjust_uses" style="display:${effType === 'adjust_uses' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Delta (+/-)</label>
                        <input type="number" class="eff-uses-delta" value="${ep.delta || -1}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="set_parameter,adjust_parameter" style="display:${['set_parameter','adjust_parameter'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Node ID</label>
                        <div class="eff-select" data-kind="nodes" data-input-class="eff-param-node" data-value="${escapeForHtmlAttribute(ep.node_id || 'self')}" data-placeholder="self or node_id" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="set_parameter,adjust_parameter" style="display:${['set_parameter','adjust_parameter'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Parameter Key</label>
                        <input type="text" class="eff-param-key" value="${escapeForHtmlAttribute(ep.key || '')}" placeholder="e.g. light" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="set_parameter" style="display:${effType === 'set_parameter' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Value</label>
                        <input type="text" class="eff-param-value" value="${escapeForHtmlAttribute(ep.value ?? '')}" placeholder="e.g. green" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="adjust_parameter" style="display:${effType === 'adjust_parameter' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Delta (+/-)</label>
                        <input type="number" class="eff-param-delta" value="${ep.delta || 0}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="rename" style="display:${effType === 'rename' ? 'block' : 'none'};">    
                        <label style="font-size:10px;">New Name</label>
                        <input type="text" class="eff-rename" value="${escapeForHtmlAttribute(ep.name || '')}" placeholder="Empty Bottle" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="teleport" style="display:${effType === 'teleport' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target Area</label>
                        <div class="eff-select" data-kind="areas" data-input-class="eff-teleport" data-value="${escapeForHtmlAttribute(ep.area || '')}" data-placeholder="Search areas..." style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="unlock_way" style="display:${effType === 'unlock_way' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Way ID</label>
                        <div class="eff-select" data-kind="ways" data-input-class="eff-unlock" data-value="${escapeForHtmlAttribute(ep.way_id || '')}" data-placeholder="Search ways..." style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="set_description,append_description" style="display:${['set_description','append_description'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target Node</label>
                        <input type="text" class="eff-setdesc-target" value="${escapeForHtmlAttribute(ep.target || '')}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="set_description" style="display:${effType === 'set_description' ? 'block' : 'none'};">
                        <label style="font-size:10px;">New Description</label>
                        <input type="text" class="eff-setdesc-value" value="${escapeForHtmlAttribute(ep.value || ep.description || '')}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="append_description" style="display:${effType === 'append_description' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Text to Append</label>
                        <input type="text" class="eff-appenddesc-text" value="${escapeForHtmlAttribute(ep.text || '')}" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="schedule_trigger" style="display:${effType === 'schedule_trigger' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Delay (ticks)</label>
                        <input type="number" class="eff-schedule-delay" value="${ep.delay_ticks || 3}" min="1" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="schedule_trigger" style="display:${effType === 'schedule_trigger' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target (name or node ID, blank = this item)</label>
                        <input type="text" class="eff-schedule-target" value="${escapeForHtmlAttribute(ep.target || '')}" placeholder="cursed_ring" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="schedule_trigger" style="display:${effType === 'schedule_trigger' ? 'block' : 'none'};">
                        <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">Fires the target's <b>on_delayed</b> trigger. Add an <b>on_delayed</b> trigger to that item to say what happens.</div>
                    </div>
                    <div class="eff-param" data-effect="set_environment" style="display:${effType === 'set_environment' ? 'block' : 'none'};border-top:1px solid var(--border);padding-top:6px;margin-top:4px;">
                        <label style="font-size:10px;">Target Area/Node (leave blank = current)</label>
                        <div class="eff-select" data-kind="nodes" data-input-class="eff-env-node" data-value="${escapeForHtmlAttribute(ep.target_node || '')}" data-placeholder="area_id or blank" data-free="true" style="width:100%;font-size:10px;"></div>
                        <label style="font-size:10px;">Light</label>
                        <select class="eff-env-light" style="width:100%;">
                            <option value="">— Keep —</option>
                            <option value="pitch_black" ${ep.light === 'pitch_black' ? 'selected' : ''}>Pitch Black</option>
                            <option value="dim" ${ep.light === 'dim' ? 'selected' : ''}>Dim</option>
                            <option value="normal" ${ep.light === 'normal' ? 'selected' : ''}>Normal</option>
                            <option value="bright" ${ep.light === 'bright' ? 'selected' : ''}>Bright</option>
                            <option value="blinding" ${ep.light === 'blinding' ? 'selected' : ''}>Blinding</option>
                        </select>
                        <label style="font-size:10px;">Temp °C</label>
                        <input type="number" class="eff-env-temp" value="${ep.temperature !== undefined ? ep.temperature : ''}" min="-50" max="100" placeholder="e.g. 25" style="width:100%;">
                        <label style="font-size:10px;">Air</label>
                        <select class="eff-env-air" style="width:100%;">
                            <option value="">— Keep —</option>
                            <option value="fresh" ${ep.air === 'fresh' ? 'selected' : ''}>Fresh</option>
                            <option value="stale" ${ep.air === 'stale' ? 'selected' : ''}>Stale</option>
                            <option value="humid" ${ep.air === 'humid' ? 'selected' : ''}>Humid</option>
                            <option value="toxic" ${ep.air === 'toxic' ? 'selected' : ''}>Toxic</option>
                            <option value="smoky" ${ep.air === 'smoky' ? 'selected' : ''}>Smoky</option>
                            <option value="fragrant" ${ep.air === 'fragrant' ? 'selected' : ''}>Fragrant</option>
                        </select>
                        <label style="font-size:10px;">Smell</label>
                        <input type="text" class="eff-env-smell" value="${escapeForHtmlAttribute(ep.smell || '')}" placeholder="musty, floral..." style="width:100%;">
                        <label style="font-size:10px;">Noise</label>
                        <select class="eff-env-noise" style="width:100%;">
                            <option value="">— Keep —</option>
                            <option value="quiet" ${ep.noise === 'quiet' ? 'selected' : ''}>Quiet</option>
                            <option value="dripping" ${ep.noise === 'dripping' ? 'selected' : ''}>Dripping</option>
                            <option value="humming" ${ep.noise === 'humming' ? 'selected' : ''}>Humming</option>
                            <option value="windy" ${ep.noise === 'windy' ? 'selected' : ''}>Windy</option>
                            <option value="loud" ${ep.noise === 'loud' ? 'selected' : ''}>Loud</option>
                            <option value="chaotic" ${ep.noise === 'chaotic' ? 'selected' : ''}>Chaotic</option>
                            <option value="silent" ${ep.noise === 'silent' ? 'selected' : ''}>Silent</option>
                        </select>
                    </div>
                    <div class="eff-param" data-effect="adjust_environment" style="display:${effType === 'adjust_environment' ? 'block' : 'none'};border-top:1px solid var(--border);padding-top:6px;margin-top:4px;">
                        <label style="font-size:10px;">Temperature (+/-)</label>
                        <input type="number" class="eff-adj-temp" value="${ep.temperature !== undefined ? ep.temperature : 0}" placeholder="5 or -3" style="width:100%;">
                        <label style="font-size:10px;">Light (+/-)</label>
                        <input type="number" class="eff-adj-light" value="${ep.light !== undefined ? ep.light : 0}" placeholder="10 or -20" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="apply_trait,remove_trait" style="display:${['apply_trait','remove_trait'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Trait ID</label>
                        <div class="eff-select" data-kind="traits" data-input-class="eff-trait-id" data-value="${escapeForHtmlAttribute(ep.trait || '')}" data-placeholder="dark_vision, hardy, allergic..." data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="apply_trait,remove_trait" style="display:${['apply_trait','remove_trait'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target</label>
                        <div class="eff-select" data-kind="chars" data-input-class="eff-trait-target" data-value="${escapeForHtmlAttribute(ep.target || 'self')}" data-placeholder="self or character name" data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="apply_trait" style="display:${effType === 'apply_trait' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Param Value</label>
                        <input type="text" class="eff-trait-param" value="${ep.param !== undefined ? escapeForHtmlAttribute(String(ep.param)) : 'true'}" placeholder="true or value (e.g. pollen)" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="apply_condition" style="display:${effType === 'apply_condition' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Condition</label>
                        <div class="eff-select" data-kind="conditions" data-input-class="eff-condition-id" data-value="${escapeForHtmlAttribute(ep.condition || '')}" data-placeholder="poisoned, blind, exhausted, charmed..." data-free="true" style="width:100%;"></div>
                    </div>
                    <div class="eff-param" data-effect="apply_condition,remove_condition" style="display:${['apply_condition','remove_condition'].includes(effType) ? 'block' : 'none'};">
                        <label style="font-size:10px;">Target</label>
                        <select class="eff-condition-target-by" style="width:100%;font-size:10px;" onchange="const row=this.closest('.eff-row'); const inp=row.querySelector('.eff-condition-target'); const show=this.value && this.value!=='self' && this.value!=='all_in_area'; inp.style.display=show?'block':'none'; inp.placeholder={name:'Character or node name',tag:'Tag',trait:'Trait id',type:'item / character / way / area'}[this.value]||'self or character name'; if(this.value==='self') inp.value='';">
                            <option value="self" ${!ep.target_by && (ep.target==='self' || !ep.target) ? 'selected' : ''}>Self (actor)</option>
                            <option value="all_in_area" ${ep.target_by==='all_in_area' ? 'selected' : ''}>All characters in area</option>
                            <option value="name" ${ep.target_by==='name' ? 'selected' : ''}>By name</option>
                            <option value="tag" ${ep.target_by==='tag' ? 'selected' : ''}>By tag</option>
                            <option value="trait" ${ep.target_by==='trait' ? 'selected' : ''}>By trait</option>
                            <option value="type" ${ep.target_by==='type' ? 'selected' : ''}>By type</option>
                        </select>
                        <input type="text" class="eff-condition-target" value="${escapeForHtmlAttribute(ep.target_by ? (ep.target_value || '') : (ep.target === 'self' ? '' : (ep.target || '')))}" list="eff-char-list" placeholder="self or character name" style="width:100%;font-size:10px;margin-top:2px;display:${(!ep.target_by && ep.target && ep.target !== 'self') || (ep.target_by && ep.target_by !== 'all_in_area') ? 'block' : 'none'};">
                    </div>
                    <div class="eff-param" data-effect="apply_condition" style="display:${effType === 'apply_condition' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Duration (ticks, blank = catalog default)</label>
                        <input type="number" class="eff-condition-duration" value="${ep.duration !== undefined ? ep.duration : ''}" placeholder="10" style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="apply_condition" style="display:${effType === 'apply_condition' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Source (shown on the condition card)</label>
                        <input type="text" class="eff-condition-source" value="${escapeForHtmlAttribute(ep.source || '')}" placeholder="poisoned wine, viper..." style="width:100%;">
                    </div>
                    <div class="eff-param" data-effect="apply_condition" style="display:${effType === 'apply_condition' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Per-tick drain (blank = catalog default; set 0 to disable that vital)</label>
                        <div class="eff-condition-periodic-form" style="display:grid;grid-template-columns:1fr 1fr;gap:2px 8px;margin-top:2px;">
                            ${['HP','Energy','Hunger','Thirst','Hygiene','Social','Bladder','Sanity','Entertainment','Temperature'].map(v =>
                                `<label style="display:flex;align-items:center;gap:4px;font-size:9px;justify-content:space-between;">
                                    <span style="flex:1;">${v}</span>
                                    <input type="number" step="any" class="eff-periodic-${v}" value="${ep.periodic?.[v] !== undefined ? ep.periodic[v] : 0}" style="width:52px;font-size:10px;">
                                </label>`
                            ).join('')}
                        </div>
                        <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">Leave all at 0 to use the condition's catalog default.</div>
                    </div>
                    <div class="eff-param" data-effect="apply_condition" style="display:${effType === 'apply_condition' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Symptoms — progression by ticks left (e.g. {"8":"a queasy twist...","4":"cold sweat...","1":"everything spins"}; blank = catalog)</label>
                        <textarea class="eff-condition-symptoms" rows="3" placeholder='{"8": "A queasy twist in your stomach.", "4": "Cold sweat beads on your forehead.", "1": "Everything spins."}' style="width:100%;font-size:11px;">${ep.symptoms ? escapeForHtmlAttribute(JSON.stringify(ep.symptoms, null, 1)) : ''}</textarea>
                        <div style="font-size:9px;color:var(--text-muted);">Keyed by ticks remaining — the highest threshold ≤ current time wins. Use "level" keys instead for leveled conditions (exhausted).</div>
                    </div>
                    <div class="eff-param" data-effect="apply_condition" style="display:${effType === 'apply_condition' ? 'block' : 'none'};">
                        <label style="font-size:10px;">Extra conditions — applied alongside (e.g. [{"condition":"blind","duration":3}]); blank = none</label>
                        <textarea class="eff-condition-extras" rows="2" placeholder='[{"condition": "blind", "duration": 3}, {"condition": "exhausted", "level": 1}]' style="width:100%;font-size:11px;">${ep.extra_conditions ? escapeForHtmlAttribute(JSON.stringify(ep.extra_conditions)) : ''}</textarea>
                    </div>
                </div>
                <span onclick="this.closest('.eff-row').remove()" style="position:absolute;top:4px;right:4px;cursor:pointer;color:var(--red);font-size:12px;">✕</span>
            </div>`;
    },

    _toggleEffectParams(select) {
        const row = select.closest('.eff-row');
        const params = row.querySelector('.eff-params');
        const val = select.value;
        params.style.display = val !== 'message' ? 'block' : 'none';
        row.querySelectorAll('.eff-param').forEach(p => {
            const effects = (p.getAttribute('data-effect') || '').split(',');
            p.style.display = effects.includes(val) ? 'block' : 'none';
        });
    },

    _toggleConditionFields(select) {
        const row = select.closest('.cond-row');
        const ctype = select.value;
        row.querySelectorAll('.cond-field').forEach(f => {
            const conds = (f.getAttribute('data-cond') || '').split(',');
            f.style.display = conds.includes(ctype) ? 'block' : 'none';
        });
        row.querySelectorAll('[data-subcond]').forEach(f => {
            const conds = (f.getAttribute('data-subcond') || '').split(',');
            f.style.display = conds.includes(ctype) ? 'block' : 'none';
        });
    },

    _toggleSnippetMenu() {
        const menu = document.getElementById('te-snippet-menu');
        if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    },

    _applySnippet(id) {
        const snippet = TRIGGER_SNIPPETS.find(s => s.id === id);
        if (!snippet) return;
        const typeSelect = document.getElementById('te-trigger-type');
        if (typeSelect && typeSelect.tagName === 'SELECT' && !typeSelect.multiple && snippet.triggerType) {
            typeSelect.value = snippet.triggerType;
        }
        const msgInput = document.getElementById('te-success-msg');
        if (msgInput && snippet.message) msgInput.value = snippet.message;
        const container = document.getElementById('te-effects-container');
        if (container) {
            const effectOpts = TriggerEditor._buildGroupedEffectOpts(TriggerEditor._effectTypes);
            container.innerHTML = '';
            container.setAttribute('data-count', String(snippet.effects.length));
            const wrap = document.createElement('div');
            wrap.innerHTML = snippet.effects.map((eff, idx) => TriggerEditor._buildEffectRowHtml(effectOpts, eff, idx)).join('');
            const fragment = document.createDocumentFragment();
            while (wrap.firstElementChild) fragment.appendChild(wrap.firstElementChild);
            container.appendChild(fragment);
            container.querySelectorAll('.eff-row .eff-type').forEach(sel => TriggerEditor._toggleEffectParams(sel));
            TriggerEditor._initEffectSearchSelects(container);
        }
        const menu = document.getElementById('te-snippet-menu');
        if (menu) menu.style.display = 'none';
    },

    _addEffectRow() {
        const container = document.getElementById('te-effects-container');
        if (!container) return;
        const count = parseInt(container.getAttribute('data-count') || '0');
        container.setAttribute('data-count', count + 1);
        const effectOpts = TriggerEditor._buildGroupedEffectOpts(TriggerEditor._effectTypes);
        const rowHtml = TriggerEditor._buildEffectRowHtml(effectOpts, null, count);
        const div = document.createElement('div');
        window.Lit.render(triggerEditorTag`${window.Lit.unsafeHTML(rowHtml)}`, div);
        container.appendChild(div.firstElementChild);
        const lastEff = container.querySelector('.eff-row:last-child .eff-type');
        if (lastEff) TriggerEditor._toggleEffectParams(lastEff);
        TriggerEditor._initEffectSearchSelects(container);
    }
};

// Ensure escapeForHtmlAttribute exists
if (typeof escapeForHtmlAttribute === 'undefined') {
    window.escapeForHtmlAttribute = function (value) {
        return String(value == null ? '' : value).replace(/"/g, '&quot;');
    };
}
