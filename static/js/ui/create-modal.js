/**
 * Create Modal — opens the modal for creating rooms, items, and connections.
 * Used by graph-manager add buttons and the legacy openCreateModal() wrapper.
 */
// Lazy tag: classic scripts parse before the deferred lit-bootstrap module
// runs, so window.Lit only exists when this module actually renders.
const createModalHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

const CreateModal = {
    /** Open the create modal for a given entity type with a submit callback. */
    open(type, onSubmit) {
        const modal = document.getElementById('create-modal');
        const title = document.getElementById('create-modal-title');
        const body = document.getElementById('create-modal-body');
        if (!modal || !body) return;

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
                    placeholder: 'Search or create tags...'
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

    _buildRoomForm() {
        return createModalHtmlTag`<div style="display:flex;gap:4px;margin-bottom:8px;">
            <input type="text" id="ai-prompt" placeholder="AI prompt..." style="flex:1;font-size:11px;">
            <button class="btn btn-sm btn-purple" @click=${() => generateWithAI('area')} style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">🤖 Generate</button>
            <button class="btn btn-sm" @click=${() => VW._previewPrompt('area')} title="Preview and edit prompt" style="background:var(--bg-inset);border-color:var(--border);">👁️</button>
        </div>
        <label>Area Name</label><input type="text" id="area-name" placeholder="e.g. Library">
        <label>Description</label><textarea id="area-desc" rows="2" placeholder="A dusty area..."></textarea>
        <label>Light</label><select id="area-light"><option value="pitch_black">Pitch Black</option><option value="dim">Dim</option><option value="normal" selected>Normal</option><option value="bright">Bright</option><option value="blinding">Blinding</option></select>
        <label>Temperature</label><input type="number" id="area-temp" value="21">
        <label>Air</label><select id="area-air"><option>fresh</option><option>stale</option><option>humid</option><option>toxic</option></select>
        <label>Smell</label><input type="text" id="area-smell" placeholder="musty, floral...">
        <label>Noise</label><input type="text" id="area-noise" placeholder="quiet, dripping...">
        <label>Tags</label><div id="area-tags" style="position:relative;"></div>
        <label style="font-size:10px;margin-top:4px;"><input type="checkbox" id="gen-use-context" checked> 🧠 Use world context</label>`;
    },

    _buildItemForm() {
        const roomOptions = Object.keys(worldState.areas || {}).map(area => `<option value="${area}">${area}</option>`).join('');
        const containerItems = Object.values(worldState.graph?.nodes || {}).filter(node => node.type === 'item').sort((a,b) => (a.name||a.id).localeCompare(b.name||b.id));
        const containerOptions = containerItems.map(node => `<option value="${node.id}">${node.name || node.id}</option>`).join('');
        const characters = Object.values(worldState.graph?.nodes || {}).filter(node => node.type === 'character').sort((a,b) => (a.name||a.id).localeCompare(b.name||b.id));
        const characterOptions = characters.map(node => `<option value="${node.id}">${node.name || node.id}</option>`).join('');
        const actionOptions = ['examine','take','use','open','close','eat','drink','read','light','activate','equip','unequip','throw','break']
            .map(action => createModalHtmlTag`<label style="font-size:10px;"><input type="checkbox" class="act-chk" value="${action}" ?checked=${['examine','take','use'].includes(action)}> ${action}</label>`);
        const equipOptions = ['head','neck','torso','arms','hands','legs','feet','back','waist','accessory','hand_left','hand_right']
            .map(s => createModalHtmlTag`<option value="${s}">${s}</option>`);
        return createModalHtmlTag`<div style="display:flex;gap:4px;margin-bottom:8px;">
            <input type="text" id="ai-prompt" placeholder="AI prompt..." style="flex:1;font-size:11px;">
            <button class="btn btn-sm btn-purple" @click=${() => generateWithAI('item')} style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">🤖 Generate</button>
            <button class="btn btn-sm" @click=${() => VW._previewPrompt('item')} title="Preview and edit prompt" style="background:var(--bg-inset);border-color:var(--border);">👁️</button>
        </div>
        <div style="margin-bottom:6px;">
            <label style="font-size:10px;font-weight:600;display:block;margin-bottom:2px;">Place In</label>
            <div style="display:flex;gap:4px;">
                <label style="font-size:10px;display:flex;align-items:center;gap:2px;cursor:pointer;"><input type="radio" name="item-target-type" value="area" checked @change=${() => VW._toggleItemTargetType()}> 🏠 Area</label>
                <label style="font-size:10px;display:flex;align-items:center;gap:2px;cursor:pointer;"><input type="radio" name="item-target-type" value="container" @change=${() => VW._toggleItemTargetType()}> 📦 Container</label>
                <label style="font-size:10px;display:flex;align-items:center;gap:2px;cursor:pointer;"><input type="radio" name="item-target-type" value="character" @change=${() => VW._toggleItemTargetType()}> 🧍 Character</label>
            </div>
            <select id="item-target-area" style="width:100%;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">${window.Lit.unsafeHTML(roomOptions)}</select>
            <select id="item-target-container" style="display:none;width:100%;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">${window.Lit.unsafeHTML(containerOptions || '<option value="">No container items available</option>')}</select>
            <select id="item-target-character" style="display:none;width:100%;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">${window.Lit.unsafeHTML(characterOptions || '<option value="">No characters available</option>')}</select>
        </div>
        <label>Item Name</label><input type="text" id="item-name">
        <label>Description</label><textarea id="item-desc" rows="2"></textarea>
        <label>Actions</label><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:2px;">${actionOptions}</div>
        <label>Uses</label><input type="number" id="item-uses" value="-1">
        <label>Weight</label><input type="number" id="item-weight" step="0.1" value="0.1">
        <label>State</label>
        <select id="item-state">
            <option value="normal">Normal</option>
            <option value="hidden">Hidden</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
            <option value="locked">Locked</option>
            <option value="lit">Lit</option>
            <option value="unlit">Unlit</option>
            <option value="broken">Broken</option>
        </select>
        <div class="field" style="margin-top:4px;"><label style="font-size:10px;">Equip Slots (select one or more)</label>
            <select multiple id="item-equip-slots" style="width:100%;font-size:11px;min-height:60px;">
                ${equipOptions}
            </select>
        </div>
        <label>Tags</label><div id="item-tags" style="position:relative;"></div>
        <details style="margin-top:6px;font-size:10px;">
            <summary style="cursor:pointer;color:var(--accent);">⚡ Triggers (optional)</summary>
            <textarea id="item-triggers-json" rows="3" placeholder='[{"trigger_type":"on_use","effect_type":"message","effect_params":{"message":"..."}}]' style="width:100%;font-size:10px;margin-top:4px;"></textarea>
            <div style="font-size:9px;color:var(--text-muted);">JSON array. Edit later in the library editor.</div>
        </details>
        <div style="margin-top:6px;"><label style="font-size:10px;"><input type="checkbox" id="item-is-container" @change=${(e) => document.getElementById('item-contents-section').style.display = e.target.checked ? 'block' : 'none'}> 📦 Container (contains items)</label></div>
        <div id="item-contents-section" style="display:none;margin-top:4px;">
            <label style="font-size:10px;">Contents JSON</label>
            <textarea id="item-contents-json" rows="2" placeholder='[{"name":"Apple","description":"A red apple","actions":"examine,take,eat"}]' style="width:100%;font-size:10px;"></textarea>
            <div style="font-size:9px;color:var(--text-muted);">Define items inside this container as JSON array.</div>
        </div>
        <label style="font-size:10px;margin-top:4px;"><input type="checkbox" id="gen-use-context" checked> 🧠 Use world context</label>`;
    },

    _buildConnectionForm() {
        const roomOptions = Object.keys(worldState.areas || {}).map(area => `<option value="${area}">${area}</option>`).join('');
        const skillOptions = ['Athletics','Acrobatics','Stealth','Perception','Investigation','Survival','Persuasion','Performance','Medicine','Arcana','Intimidation','Lockpicking']
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
            const contentsRaw = document.getElementById('item-contents-json')?.value;
            let contents = [];
            if (contentsRaw) { try { contents = JSON.parse(contentsRaw); } catch { contents = []; } }
            const targetType = document.querySelector('input[name="item-target-type"]:checked')?.value || 'area';
            return {
                area: targetType === 'area' ? document.getElementById('item-target-area')?.value : '',
                container: targetType === 'container' ? document.getElementById('item-target-container')?.value : '',
                character: targetType === 'character' ? document.getElementById('item-target-character')?.value : '',
                name: document.getElementById('item-name')?.value,
                description: document.getElementById('item-desc')?.value,
                actions: Array.from(document.querySelectorAll('.act-chk:checked')).map(checkbox => checkbox.value).join(','),
                uses: parseInt(document.getElementById('item-uses')?.value),
                weight: parseFloat(document.getElementById('item-weight')?.value),
                current_state: document.getElementById('item-state')?.value || 'normal',
                equip_slots: (() => { const el = document.getElementById('item-equip-slots'); return el ? Array.from(el.selectedOptions).map(o => o.value) : [] })(),
                tags: this._tagMSItem ? this._tagMSItem.getValue() : [],
                contents: contents,
                triggers: (() => { try { return JSON.parse(document.getElementById('item-triggers-json')?.value || '[]'); } catch { return []; } })()
            };
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
    }
};
