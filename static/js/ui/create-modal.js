/**
 * Create Modal — opens the modal for creating rooms, items, and connections.
 * Used by graph-manager add buttons and the legacy openCreateModal() wrapper.
 */
// Lazy tag: classic scripts parse before the deferred lit-bootstrap module
// runs, so window.Lit only exists when this module actually renders.
const createModalHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

const ITEM_ACTIONS = ['examine', 'take', 'use', 'open', 'close', 'eat', 'drink', 'read', 'light', 'activate', 'equip', 'unequip', 'throw', 'break'];
const ITEM_DEFAULT_ACTIONS = ['examine', 'take', 'use'];
const ITEM_EQUIP_SLOTS = ['head', 'neck', 'torso', 'arms', 'hands', 'legs', 'feet', 'back', 'waist', 'accessory', 'hand_left', 'hand_right'];
const ITEM_STATES = ['normal', 'hidden', 'open', 'closed', 'locked', 'lit', 'unlit', 'on', 'broken', 'charged', 'depleted'];
const ITEM_RELATIONS = ['in', 'on', 'under', 'behind', 'beside', 'at'];
const DAMAGE_SKILLS = ['Athletics', 'Acrobatics', 'Stealth', 'Perception', 'Investigation', 'Survival', 'Persuasion', 'Performance', 'Medicine', 'Arcana', 'Intimidation', 'Lockpicking'];
const DAMAGE_TYPES = ['slashing', 'piercing', 'bludgeoning', 'fire', 'cold', 'toxic', 'magic', 'electric', 'radiant', 'necrotic', 'psychic', 'acid'];

// Mechanical capabilities — each chip owns one engine tag. Enabling a chip
// adds the tag (via the tag picker) and reveals its tuning fields. The
// engine counterparts live in lighting.py (light_source), environment_propagation.py
// (heat_source), sound.py (sound_source), toggleable_items.py (toggleable)
// and equipment_bonuses.py (insulation/armor/clothing/weapon/resistance).
const ITEM_MECH = [
    { tag: 'light_source', icon: '💡', label: 'Light source' },
    { tag: 'heat_source', icon: '🌡️', label: 'Heat source' },
    { tag: 'sound_source', icon: '🔊', label: 'Sound source' },
    { tag: 'toggleable', icon: '🎚️', label: 'Toggleable' },
    { tag: 'insulation', icon: '🧥', label: 'Insulation' },
    { tag: 'armor', icon: '🛡️', label: 'Armor' },
    { tag: 'clothing', icon: '👕', label: 'Clothing' },
    { tag: 'weapon', icon: '⚔️', label: 'Weapon' },
    { tag: 'resistance', icon: '🧿', label: 'Resistance' },
    { tag: 'container', icon: '📦', label: 'Container' },
    { tag: 'electric', icon: '⚡', label: 'Electric' },
    { tag: 'two_handed', icon: '✌️', label: 'Two-handed' }
];

const CreateModal = {
    /** Open the create modal for a given entity type with a submit callback. */
    open(type, onSubmit) {
        const modal = document.getElementById('create-modal');
        const title = document.getElementById('create-modal-title');
        const body = document.getElementById('create-modal-body');
        if (!modal || !body) return;

        // The item form is sectioned and wider; other forms keep the compact width.
        body.style.width = type === 'item' ? '620px' : '480px';

        let formTemplate;
        if (type === 'area') {
            formTemplate = this._buildRoomForm();
            title.innerText = 'Add New Area';
        } else if (type === 'item') {
            formTemplate = this._buildItemForm();
            title.innerText = 'Add New Item';
        } else if (type === 'connection') {
            formTemplate = this._buildConnectionForm();
            title.innerText = 'Connect Rooms';
        }

        const contentEl = document.getElementById('create-modal-content');
        if (contentEl && formTemplate) window.Lit.render(formTemplate, contentEl);
        this._initTagMultiselects(type);
        if (type === 'item') this._initItemTargetSearch();
        modal.style.display = 'flex';

        const closeOnEscape = (event) => { if (event.key === 'Escape') this.close(); };
        document.addEventListener('keydown', closeOnEscape);
        modal._closeOnEscape = closeOnEscape;

        modal.onclick = (event) => { if (event.target === modal) this.close(); };

        const submitButton = document.getElementById('create-modal-submit');
        submitButton.onclick = () => {
            const result = this._collectFormData(type);
            if (result && onSubmit) onSubmit(result);
            this.close();
        };
    },

    _initTagMultiselects(type) {
        if (this._tagMSArea) { this._tagMSArea.destroy(); this._tagMSArea = null; }
        if (this._tagMSItem) { this._tagMSItem.destroy(); this._tagMSItem = null; }
        if (this._tagMSConn) { this._tagMSConn.destroy(); this._tagMSConn = null; }
        if (typeof TagMultiselect === 'undefined') return;
        if (type === 'area') {
            const container = document.getElementById('area-tags');
            if (container) {
                this._tagMSArea = new TagMultiselect(container, {
                    tags: [],
                    appliesTo: 'areas',
                    allowNew: true,
                    placeholder: 'Search or create tags...'
                });
            }
        } else if (type === 'item') {
            const container = document.getElementById('item-tags');
            if (container) {
                this._tagMSItem = new TagMultiselect(container, {
                    tags: [],
                    appliesTo: 'items',
                    allowNew: true,
                    placeholder: 'Search or create tags...',
                    onChange: (tags) => this._syncMechChips(tags || [])
                });
            }
        } else if (type === 'connection') {
            const container = document.getElementById('conn-tags');
            if (container) {
                this._tagMSConn = new TagMultiselect(container, {
                    tags: [],
                    appliesTo: 'areas',
                    allowNew: true,
                    placeholder: 'Search or create tags...'
                });
            }
        }
    },

    /** Close the create modal */
    close() {
        const modal = document.getElementById('create-modal');
        if (modal) {
            modal.style.display = 'none';
            const closeHandler = modal._closeOnEscape;
            if (closeHandler) document.removeEventListener('keydown', closeHandler);
        }
    },

    async _searchPlacementTargets(query) {
        const targetType = document.querySelector('input[name="item-target-type"]:checked')?.value || 'item';
        const q = encodeURIComponent(query.trim().toLowerCase());
        try {
            const resp = await fetch(`/api/search/placement-targets?q=${q}`);
            if (!resp.ok) return [];
            const all = await resp.json();
            return all.filter(r => r.type === targetType);
        } catch {
            return [];
        }
    },

    _initItemTargetSearch() {
        const input = document.getElementById('item-target-search');
        const results = document.getElementById('item-target-results');
        const preview = document.getElementById('item-target-preview');
        const hidden = document.getElementById('item-target-id');
        if (!input || !results || !hidden || !preview) return;
        const show = (items) => {
            if (!items.length) {
                results.style.display = 'none';
                return;
            }
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
        };
        input.oninput = async () => {
            const q = input.value.trim();
            if (!q) { results.style.display = 'none'; hidden.value = ''; preview.textContent = ''; return; }
            const items = await this._searchPlacementTargets(q);
            show(items);
        };
        input.onblur = () => setTimeout(() => { results.style.display = 'none'; }, 150);
        input.onfocus = () => { if (input.value.trim()) input.oninput({ target: input }); };
    },

    _buildRoomForm() {
        return createModalHtmlTag`<div style="display:flex;gap:4px;margin-bottom:8px;">
            <input type="text" id="ai-prompt" placeholder="AI prompt..." style="flex:1;font-size:11px;">
            <button class="btn btn-sm btn-purple" @click=${() => generateWithAI('area')} style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">🤖 Generate</button>
            <button class="btn btn-sm" @click=${() => VW._previewPrompt('area')} title="Preview and edit prompt" style="background:var(--bg-inset);border-color:var(--border);">👁️</button>
        </div>
        <label style="margin-top:0;">Area Name</label><input type="text" id="area-name" placeholder="e.g. Library">
        <label>Description</label><textarea id="area-desc" rows="2" placeholder="A dusty area..."></textarea>
        <div class="cm-grid-3">
            <div><label>Light</label><select id="area-light"><option value="pitch_black">Pitch Black</option><option value="dim">Dim</option><option value="normal" selected>Normal</option><option value="bright">Bright</option><option value="blinding">Blinding</option></select></div>
            <div><label>Temp (°C)</label><input type="number" id="area-temp" value="21"></div>
            <div><label>Air</label><select id="area-air"><option>fresh</option><option>stale</option><option>humid</option><option>toxic</option></select></div>
        </div>
        <div class="cm-grid-2">
            <div><label>Smell</label><input type="text" id="area-smell" placeholder="musty, floral..."></div>
            <div><label>Noise</label><input type="text" id="area-noise" placeholder="quiet, dripping..."></div>
        </div>
        <label>Tags</label><div id="area-tags" style="position:relative;"></div>
        <label style="font-size:10px;margin-top:8px;"><input type="checkbox" id="gen-use-context" checked> 🧠 Use world context</label>`;
    },

    _buildItemForm() {
        const chipToggle = (e) => e.target.closest('.chip-toggle').classList.toggle('on', e.target.checked);
        const actionChips = ITEM_ACTIONS.map(a => createModalHtmlTag`<label class="chip-toggle"><input type="checkbox" class="act-chk" value=${a} ?checked=${ITEM_DEFAULT_ACTIONS.includes(a)} @change=${chipToggle}> ${a}</label>`);
        const slotChips = ITEM_EQUIP_SLOTS.map(s => createModalHtmlTag`<label class="chip-toggle"><input type="checkbox" class="slot-chk" data-slot=${s} @change=${chipToggle}> ${s}</label>`);
        const mechChips = ITEM_MECH.map(m => createModalHtmlTag`<label class="chip-toggle" title=${m.label}><input type="checkbox" class="mech-chk" data-tag=${m.tag} @change=${(e) => this._onMechChipChange(m.tag, e.target.checked)}> ${m.icon} ${m.label}</label>`);
        const stateOptions = ITEM_STATES.map(s => createModalHtmlTag`<option .value=${s} ?selected=${s === 'normal'}>${s}</option>`);
        const relationOptions = ITEM_RELATIONS.map(r => createModalHtmlTag`<option .value=${r} ?selected=${r === 'in'}>${r}</option>`);
        const damageSkillOptions = DAMAGE_SKILLS.map(s => createModalHtmlTag`<option .value=${s} ?selected=${s === 'Athletics'}>${s}</option>`);
        const damageTypeOptions = [['', '— none —'], ...DAMAGE_TYPES.map(dt => [dt, dt])]
            .map(([v, lbl]) => createModalHtmlTag`<option .value=${v} ?selected=${v === ''}>${lbl}</option>`);
        return createModalHtmlTag`<div style="display:flex;gap:4px;margin-bottom:2px;">
            <input type="text" id="ai-prompt" placeholder="AI prompt — e.g. 'an old brass lantern'" style="flex:1;font-size:11px;">
            <button class="btn btn-sm btn-purple" @click=${() => generateWithAI('item')} style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">🤖 Generate</button>
            <button class="btn btn-sm" @click=${() => VW._previewPrompt('item')} title="Preview and edit prompt" style="background:var(--bg-inset);border-color:var(--border);">👁️</button>
            <label class="chip-toggle" title="Give the AI the target's description so the item fits the scene" style="align-self:center;"><input type="checkbox" id="gen-use-context" checked> 🧠 Context</label>
        </div>

        <div class="cm-section" style="border-top:none;margin-top:4px;">
            <div class="cm-section-title">📦 Place on / in</div>
            <div style="display:flex;gap:10px;margin-bottom:4px;">
                <label class="chip-toggle"><input type="radio" name="item-target-type" value="item" checked @change=${() => VW._toggleItemTargetType()}> 📦 Item</label>
                <label class="chip-toggle"><input type="radio" name="item-target-type" value="character" @change=${() => VW._toggleItemTargetType()}> 🧍 Character</label>
                <label class="chip-toggle"><input type="radio" name="item-target-type" value="area" @change=${() => VW._toggleItemTargetType()}> 🏠 Area</label>
            </div>
            <input type="text" id="item-target-search" placeholder="Search items, characters, or areas..." style="width:100%;font-size:11px;">
            <div id="item-target-results" style="display:none;position:absolute;z-index:1000;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;max-height:200px;overflow-y:auto;width:100%;box-shadow:0 4px 12px rgba(0,0,0,0.3);margin-top:2px;"></div>
            <input type="hidden" id="item-target-id">
            <div id="item-target-preview" style="font-size:10px;color:var(--text-muted);margin-top:2px;"></div>
            <div id="item-target-relation-wrap" style="display:flex;align-items:center;gap:6px;margin-top:4px;">
                <span style="font-size:10px;color:var(--text-muted);">Relation</span>
                <select id="item-target-relation" style="width:120px;font-size:11px;padding:3px 6px;">${relationOptions}</select>
                <span class="cm-hint" style="margin:0;">where inside/on the target item it sits</span>
            </div>
        </div>

        <div class="cm-section">
            <div class="cm-section-title">📝 Identity</div>
            <div style="display:flex;gap:8px;">
                <div style="flex:1;"><label style="margin-top:2px;">Name</label><input type="text" id="item-name" placeholder="Brass Lantern"></div>
            </div>
            <label>Description</label><textarea id="item-desc" rows="2" placeholder="What it looks like, and anything odd about it…"></textarea>
        </div>

        <div class="cm-section">
            <div class="cm-section-title">✅ Actions <span class="cm-hint">what players can do with it</span></div>
            <div class="chip-row">${actionChips}</div>
        </div>

        <div class="cm-section">
            <div class="cm-section-title">⚙️ Properties</div>
            <div class="cm-grid-3">
                <div><label>Uses</label><input type="number" id="item-uses" value="-1"><div class="cm-hint">-1 = infinite</div></div>
                <div><label>Weight (kg)</label><input type="number" id="item-weight" step="0.1" value="0.1"><div class="cm-hint">counts toward carry capacity</div></div>
                <div><label>Initial state</label><select id="item-state">${stateOptions}</select><div class="cm-hint">lit/on items are active</div></div>
            </div>
        </div>

        <div class="cm-section">
            <div class="cm-section-title">🧩 Mechanics <span class="cm-hint">chips add the matching mechanical tag</span></div>
            <div class="chip-row" id="item-mech-chips">${mechChips}</div>
            <div id="item-mech-fields">
                <div class="mech-fields" data-mech="light_source">
                    <div class="cm-grid-2">
                        <div><label>Light level</label>
                            <select id="item-light-level">
                                <option .value=${'pitch_black'}>Pitch black</option>
                                <option .value=${'dim'} ?selected=${true}>Dim</option>
                                <option .value=${'normal'}>Normal</option>
                                <option .value=${'bright'}>Bright</option>
                                <option .value=${'blinding'}>Blinding</option>
                            </select>
                            <div class="cm-hint">Applied to the area while the item is lit.</div>
                        </div>
                    </div>
                </div>
                <div class="mech-fields" data-mech="heat_source">
                    <div class="cm-grid-2">
                        <div><label>Target temp (°C)</label><input type="number" id="item-target-temp" value="30" step="1"><div class="cm-hint">area drifts toward this while lit</div></div>
                        <div><label>Heating rate (°C/tick)</label><input type="number" id="item-heating-rate" value="0.5" step="0.1"></div>
                    </div>
                </div>
                <div class="mech-fields" data-mech="sound_source">
                    <div class="cm-grid-2">
                        <div><label>Sound level</label>
                            <select id="item-sound-level">
                                <option .value=${'1'} ?selected=${true}>1 · nearby only</option>
                                <option .value=${'2'}>2 · adjacent areas</option>
                                <option .value=${'3'}>3 · distant areas</option>
                            </select>
                            <div class="cm-hint">How far it carries when active.</div>
                        </div>
                        <div><label>Sound pattern</label><input type="text" id="item-sound-pattern" placeholder="a tinny pop song, crackling…"><div class="cm-hint">Heard as "You hear … from the north".</div></div>
                    </div>
                </div>
                <div class="mech-fields" data-mech="insulation">
                    <div class="cm-grid-2">
                        <div><label>Insulation (°C shift)</label><input type="number" id="item-insulation" step="1" placeholder="+ warms, − cools"><div class="cm-hint">While equipped. Stacks across worn items.</div></div>
                    </div>
                </div>
                <div class="mech-fields" data-mech="defense">
                    <div class="cm-grid-2">
                        <div><label>Defense (DR)</label><input type="number" id="item-defense" min="0" value="0"><div class="cm-hint">Flat damage reduction while equipped.</div></div>
                    </div>
                </div>
                <div class="mech-fields" data-mech="weapon">
                    <div class="cm-grid-3">
                        <div><label>Damage</label><input type="text" id="item-damage" placeholder="2d6+3" style="margin-top:2px;"><div class="cm-hint">dice ("1d8") or flat ("8")</div></div>
                        <div><label>Skill</label><select id="item-damage-skill" style="margin-top:2px;">${damageSkillOptions}</select></div>
                        <div><label>Type</label><select id="item-damage-type" style="margin-top:2px;">${damageTypeOptions}</select></div>
                    </div>
                    <div class="cm-grid-2" style="margin-top:4px;">
                        <div><label>Stun chance %</label><input type="number" id="item-stun-chance" min="0" max="100" placeholder="0"></div>
                        <div><label>Stun duration (turns)</label><input type="number" id="item-stun-duration" min="1" placeholder="2"></div>
                    </div>
                </div>
                <div class="mech-fields" data-mech="resistance">
                    <div><label>Resistances</label><input type="text" id="item-resistances" placeholder="fire:5, cold:3, toxic:999"><div class="cm-hint">type:amount — amount subtracted from that damage type; 999 ≈ immune.</div></div>
                </div>
                <div class="mech-fields" data-mech="container">
                    <div class="cm-section-title" style="margin-top:2px;">📦 Contents</div>
                    <div id="item-contents-rows"></div>
                    <button class="btn btn-sm btn-blue" @click=${() => this._addContentRow()} style="margin-top:2px;">➕ Add contained item</button>
                    <div class="cm-hint">Contents are hidden until the container is opened/used.</div>
                </div>
            </div>
            <div class="cm-hint" id="item-mech-summary" style="margin-top:6px;"></div>
        </div>

        <div class="cm-section">
            <div class="cm-section-title">🧍 Equip slots <span class="cm-hint">where it can be worn / held</span></div>
            <div class="chip-row" id="item-slot-chips">${slotChips}</div>
        </div>

        <div class="cm-section">
            <div class="cm-section-title">🏷️ Tags</div>
            <div id="item-tags" style="position:relative;"></div>
        </div>

        <div class="cm-section">
            <details style="font-size:10px;">
                <summary style="cursor:pointer;color:var(--accent);font-weight:600;">⚡ Triggers (optional) <span style="color:var(--text-muted);font-weight:400;">— advanced, JSON</span></summary>
                <textarea id="item-triggers-json" rows="4" placeholder='[{"trigger_type":"on_eat","effect_type":"adjust_vital","effect_params":{"stat":"Hunger","amount":30,"message":"You feel nourished."}}]' style="width:100%;font-size:10px;margin-top:4px;"></textarea>
                <div class="cm-hint">Trigger types: on_take, on_drop, on_examine, on_use, on_use_on, on_eat, on_drink, on_read, on_light, on_activate, on_equip, on_unequip, on_toggle_on/off, on_tick, on_open, on_close, on_depleted. Edit later in the library editor.</div>
            </details>
        </div>`;
    },

    _onMechChipChange(tag, checked) {
        // Keep chip visuals and the tag picker in sync: the chip owns the tag.
        const chk = document.querySelector(`#item-mech-chips .mech-chk[data-tag="${tag}"]`);
        if (chk) chk.closest('.chip-toggle').classList.toggle('on', checked);
        if (this._tagMSItem) {
            const cur = this._tagMSItem.getValue();
            const next = checked ? (cur.includes(tag) ? cur : [...cur, tag]) : cur.filter(t => t !== tag);
            if (next.length !== cur.length) this._tagMSItem.setValue(next);
        }
        if (tag === 'container' && checked) {
            const rows = document.getElementById('item-contents-rows');
            if (rows && !rows.children.length) this._addContentRow();
        }
        this._updateMechRows();
    },

    _syncMechChips(tags) {
        document.querySelectorAll('#item-mech-chips .mech-chk').forEach(chk => {
            const on = tags.includes(chk.dataset.tag);
            chk.checked = on;
            chk.closest('.chip-toggle').classList.toggle('on', on);
        });
        this._updateMechRows();
    },

    _updateMechRows() {
        const checked = (tag) => !!document.querySelector(`#item-mech-chips .mech-chk[data-tag="${tag}"]`)?.checked;
        const show = (key, on) => {
            const el = document.querySelector(`#item-mech-fields .mech-fields[data-mech="${key}"]`);
            if (el) el.classList.toggle('visible', on);
        };
        show('light_source', checked('light_source'));
        show('heat_source', checked('heat_source'));
        show('sound_source', checked('sound_source'));
        show('insulation', checked('insulation'));
        show('defense', checked('armor') || checked('clothing'));
        show('weapon', checked('weapon'));
        show('resistance', checked('resistance'));
        show('container', checked('container'));
        const active = ITEM_MECH.map(m => m.tag).filter(checked);
        const summary = document.getElementById('item-mech-summary');
        if (summary) summary.textContent = active.length
            ? 'Active: ' + active.join(', ')
            : 'No mechanics — a plain prop. Add chips above to make it glow, hum, heat, protect…';
    },

    _addContentRow(name = '', description = '', relation = 'in') {
        const rows = document.getElementById('item-contents-rows');
        if (!rows) return;
        const row = document.createElement('div');
        row.className = 'cm-content-row';
        const relOptions = ITEM_RELATIONS.map(r => `<option value="${r}"${r === relation ? ' selected' : ''}>${r}</option>`).join('');
        row.innerHTML = `
            <input type="text" class="cr-name" placeholder="Name" value="${name.replace(/"/g, '&quot;')}">
            <input type="text" class="cr-desc" placeholder="Short description" value="${description.replace(/"/g, '&quot;')}">
            <select class="cr-rel">${relOptions}</select>
            <button class="btn btn-sm" title="Remove" style="background:var(--bg-inset);border-color:var(--border);">✕</button>`;
        row.querySelector('button').addEventListener('click', () => row.remove());
        rows.appendChild(row);
    },

    _buildConnectionForm() {
        const roomOptions = Object.keys(worldState.areas || {}).map(area => `<option value="${area}">${area}</option>`).join('');
        const skillOptions = DAMAGE_SKILLS
            .map(skill => `<option value="${skill}">${skill}</option>`).join('');
        return createModalHtmlTag`<div style="display:flex;gap:4px;margin-bottom:8px;">
            <input type="text" id="ai-prompt" placeholder="Describe the way..." style="flex:1;font-size:11px;">
            <button class="btn btn-sm btn-purple" @click=${() => generateWithAI('connection')} style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">🤖 Generate</button>
            <button class="btn btn-sm" @click=${() => VW._previewPrompt('connection')} title="Preview and edit prompt" style="background:var(--bg-inset);border-color:var(--border);">👁️</button>
        </div>
        <label>Way ID (optional)</label>
        <input type="text" id="conn-id" placeholder="auto-generated (door_RoomA_dir1)">
        <label>Appearance when closed/locked/blocked <span style="font-weight:400;color:var(--text-muted);">(optional)</span></label>
        <textarea id="conn-desc" rows="2" placeholder="What players see when the way is closed…" style="width:100%;font-size:11px;"></textarea>
        <div class="section-hint" style="font-size:9px;color:var(--text-muted);margin:-4px 0 6px;">Shown in look/examine when the way is not open. Use {param:key} for dynamic text.</div>
        <label>Area A</label><select id="conn-roomA" @change=${() => VW._onConnRoomChange()}>${window.Lit.unsafeHTML(roomOptions)}</select>
        <label>Command from A → B <span style="font-weight:400;color:var(--text-muted);">(go ___)</span></label><input type="text" id="conn-dir1" placeholder="swinging door">
        <label>Area B</label><select id="conn-roomB">${window.Lit.unsafeHTML(roomOptions)}</select>
        <label>Command from B → A <span style="font-weight:400;color:var(--text-muted);">(go ___)</span></label><input type="text" id="conn-dir2" placeholder="enter">
        <div style="margin-top:6px;">
            <label style="font-size:11px;">View when open (from Area A)</label>
            <textarea id="conn-view-from-a" rows="2" placeholder="What you see through the way when open…" style="width:100%;font-size:11px;"></textarea>
        </div>
        <div style="margin-top:4px;">
            <label style="font-size:11px;">View when open (from Area B)</label>
            <textarea id="conn-view-from-b" rows="2" placeholder="What you see through the way when open…" style="width:100%;font-size:11px;"></textarea>
        </div>
        <div style="border-top:1px solid var(--border);margin-top:8px;padding-top:8px;">
            <label style="font-weight:600;">Initial Way State</label>
            <select id="conn-state">
                <option value="open">🚪 Open</option>
                <option value="closed">🚪 Closed</option>
                <option value="locked">🔒 Locked</option>
                <option value="blocked">⛔ Blocked</option>
                <option value="broken">💥 Broken</option>
                <option value="hidden">👻 Hidden</option>
            </select>
        </div>
        <div style="border-top:1px solid var(--border);margin-top:8px;padding-top:8px;">
            <label style="font-weight:600;">🚪 Way Behavior</label>
            <div class="field" style="margin-top:4px;"><label>On traverse narration</label>
                <input type="text" id="conn-pass-msg" placeholder="Message when walked through…" style="width:100%;padding:4px 8px;font-size:11px;">
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;margin-top:6px;">
                <input type="checkbox" id="conn-needs-open" @change=${(e) => document.getElementById('conn-needs-config').style.display = e.target.checked ? 'flex' : 'none'}>
                <label for="conn-needs-open" style="font-size:11px;cursor:pointer;">🔒 Needs skill check to open</label>
            </div>
            <div id="conn-needs-config" style="display:none;gap:8px;margin-left:24px;">
                <div class="field" style="flex:1;"><label style="font-size:10px;">Skill</label>
                    <select id="conn-needs-skill" style="font-size:10px;width:100%;">${window.Lit.unsafeHTML(skillOptions)}</select>
                </div>
                <div class="field" style="flex:0 0 60px;"><label style="font-size:10px;">DC</label>
                    <input type="number" id="conn-needs-dc" value="15" min="5" max="30" style="width:50px;font-size:10px;">
                </div>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;margin-top:6px;">
                <input type="checkbox" id="conn-auto-close">
                <label for="conn-auto-close" style="font-size:11px;cursor:pointer;">🚪 Auto-close after passing</label>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;margin-top:6px;">
                <input type="checkbox" id="conn-see-through">
                <label for="conn-see-through" style="font-size:11px;cursor:pointer;">👁️ See-through (light & vision pass through)</label>
            </div>
        </div>
        <div style="border-top:1px solid var(--border);margin-top:8px;padding-top:8px;">
            <label style="font-weight:600;">🏷️ Tags</label>
            <div id="conn-tags" style="position:relative;margin-top:4px;"></div>
        </div>
        <details style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px;">
            <summary style="cursor:pointer;color:var(--accent);font-weight:600;">⚡ Triggers (optional)</summary>
            <textarea id="conn-triggers-json" rows="3" placeholder='[{"trigger_type":"on_open","effect_type":"message","effect_params":{"message":"The way creaks."}}]' style="width:100%;font-size:10px;margin-top:4px;"></textarea>
        </details>
        <label style="font-size:10px;margin-top:4px;"><input type="checkbox" id="gen-use-context" checked> 🧠 Use world context</label>`;
    },

    _collectFormData(type) {
        if (type === 'area') {
            return {
                name: document.getElementById('area-name')?.value,
                description: document.getElementById('area-desc')?.value,
                light: document.getElementById('area-light')?.value || 'normal',
                temperature: parseInt(document.getElementById('area-temp')?.value),
                air: document.getElementById('area-air')?.value,
                smell: document.getElementById('area-smell')?.value,
                noise: document.getElementById('area-noise')?.value,
                tags: this._tagMSArea ? this._tagMSArea.getValue() : []
            };
        } else if (type === 'item') {
            const tags = this._tagMSItem ? this._tagMSItem.getValue() : [];
            const has = (tag) => tags.includes(tag);
            const num = (id) => { const v = document.getElementById(id)?.value; return v === '' || v === undefined ? undefined : parseFloat(v); };
            const str = (id) => document.getElementById(id)?.value || undefined;
            const contents = Array.from(document.querySelectorAll('#item-contents-rows .cm-content-row')).map((row, i) => {
                const name = row.querySelector('.cr-name')?.value.trim() || '';
                const description = row.querySelector('.cr-desc')?.value.trim() || '';
                if (!name && !description) return null;
                const slug = name.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_|_$/g, '') || `content_${i}`;
                return { id: `item_${slug}`, name: name || description, description, relation: row.querySelector('.cr-rel')?.value || 'in', actions: 'examine,take' };
            }).filter(Boolean);
            const triggers = (() => { try { return JSON.parse(document.getElementById('item-triggers-json')?.value || '[]'); } catch { return []; } })();
            const targetType = document.querySelector('input[name="item-target-type"]:checked')?.value || 'item';
            const targetId = document.getElementById('item-target-id')?.value || '';
            const relation = document.getElementById('item-target-relation')?.value || 'in';
            const payload = {
                target_type: targetType,
                target_id: targetId,
                relation: relation,
                name: document.getElementById('item-name')?.value,
                description: document.getElementById('item-desc')?.value,
                actions: Array.from(document.querySelectorAll('.act-chk:checked')).map(checkbox => checkbox.value).join(','),
                uses: parseInt(document.getElementById('item-uses')?.value),
                weight: parseFloat(document.getElementById('item-weight')?.value),
                current_state: document.getElementById('item-state')?.value || 'normal',
                equip_slots: Array.from(document.querySelectorAll('#item-slot-chips .slot-chk:checked')).map(c => c.dataset.slot),
                tags,
                contents,
                triggers
            };
            // Mechanical props — only sent when their capability chip is on.
            if (has('light_source')) payload.light_level = document.getElementById('item-light-level')?.value || 'dim';
            if (has('heat_source')) {
                payload.target_temperature = num('item-target-temp') ?? 30;
                payload.heating_rate = num('item-heating-rate') ?? 0.5;
            }
            if (has('sound_source')) {
                payload.sound_level = parseInt(document.getElementById('item-sound-level')?.value) || 1;
                payload.sound_pattern = document.getElementById('item-sound-pattern')?.value?.trim() || 'noise';
            }
            if (has('insulation')) payload.insulation = num('item-insulation') ?? 0;
            if (has('armor') || has('clothing')) payload.defense = num('item-defense') ?? 0;
            if (has('weapon')) {
                payload.damage = document.getElementById('item-damage')?.value?.trim() || 0;
                payload.damage_skill = str('item-damage-skill');
                const dtype = document.getElementById('item-damage-type')?.value;
                if (dtype) payload.damage_type = dtype;
                const stunChance = num('item-stun-chance');
                const stunDuration = num('item-stun-duration');
                if (stunChance) payload.stun_chance = stunChance;
                if (stunDuration) payload.stun_duration = stunDuration;
            }
            if (has('resistance')) {
                const resistances = {};
                (document.getElementById('item-resistances')?.value || '').split(',').forEach(pair => {
                    const parts = pair.split(':').map(s => s.trim());
                    if (parts.length === 2 && parts[0] && parts[1]) {
                        const val = parseInt(parts[1]);
                        if (!isNaN(val)) resistances[parts[0]] = val;
                    }
                });
                if (Object.keys(resistances).length) payload.resistances = resistances;
            }
            return payload;
        } else if (type === 'connection') {
            const needsOpenCheckbox = document.getElementById('conn-needs-open');
            const needsOpen = needsOpenCheckbox?.checked ? {
                enabled: true,
                skill: document.getElementById('conn-needs-skill')?.value || 'Athletics',
                dc: parseInt(document.getElementById('conn-needs-dc')?.value) || 15
            } : { enabled: false, skill: 'Athletics', dc: 15 };
            const triggersRaw = document.getElementById('conn-triggers-json')?.value;
            let triggers = [];
            if (triggersRaw) { try { triggers = JSON.parse(triggersRaw); } catch { triggers = []; } }
            return {
                room1: document.getElementById('conn-roomA')?.value,
                room2: document.getElementById('conn-roomB')?.value,
                dir1: document.getElementById('conn-dir1')?.value,
                dir2: document.getElementById('conn-dir2')?.value,
                state: document.getElementById('conn-state')?.value || 'open',
                description: document.getElementById('conn-desc')?.value || '',
                way_id: document.getElementById('conn-id')?.value || '',
                pass_message: document.getElementById('conn-pass-msg')?.value || '',
                auto_close: document.getElementById('conn-auto-close')?.checked || false,
                see_through: document.getElementById('conn-see-through')?.checked || false,
                needs_open: needsOpen,
                tags: this._tagMSConn ? this._tagMSConn.getValue() : [],
                triggers: triggers,
                view_from_a: document.getElementById('conn-view-from-a')?.value || '',
                view_from_b: document.getElementById('conn-view-from-b')?.value || ''
            };
        }
        return null;
    },

    /** Apply AI-generated item data to the form fields (called by generateWithAI). */
    _applyItemAIData(data) {
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ''; };
        set('item-name', data.name);
        set('item-desc', data.description);
        set('item-uses', data.uses ?? -1);
        set('item-weight', data.weight ?? 0.1);
        const stateEl = document.getElementById('item-state');
        if (stateEl) stateEl.value = data.current_state || 'normal';
        if (this._tagMSItem && data.tags) {
            const tags = Array.isArray(data.tags) ? data.tags : String(data.tags).split(',').map(t => t.trim()).filter(Boolean);
            this._tagMSItem.setValue(tags);
            this._syncMechChips(tags);
        }
        // Equip slots → chips
        document.querySelectorAll('#item-slot-chips .slot-chk').forEach(chk => {
            chk.checked = Array.isArray(data.equip_slots) && data.equip_slots.includes(chk.dataset.slot);
            chk.closest('.chip-toggle').classList.toggle('on', chk.checked);
        });
        // Mechanical fields
        set('item-light-level', data.light_level || 'dim');
        set('item-target-temp', data.target_temperature ?? '');
        set('item-heating-rate', data.heating_rate ?? '');
        set('item-sound-level', data.sound_level ?? '');
        set('item-sound-pattern', data.sound_pattern ?? '');
        set('item-insulation', data.insulation || '');
        set('item-defense', data.defense || '');
        set('item-damage', data.damage || '');
        set('item-damage-skill', data.damage_skill || 'Athletics');
        set('item-damage-type', data.damage_type || '');
        set('item-stun-chance', data.stun_chance ?? '');
        set('item-stun-duration', data.stun_duration ?? '');
        set('item-resistances', data.resistances ? Object.entries(data.resistances).map(([k, v]) => `${k}:${v}`).join(', ') : '');
        if (data.triggers) set('item-triggers-json', JSON.stringify(data.triggers, null, 2));
        this._updateMechRows();
    }
};
