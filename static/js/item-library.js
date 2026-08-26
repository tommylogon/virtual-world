/**
 * ItemLibrary — Item library CRUD, editor, AI generation, and area placement
 * With trigger conditions, rename effect, container contents, and multi-spawn
 */
const itemLibraryHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

class ItemLibrary {
    constructor() {
        this.data = {};
        this.selectedId = null;
        this._targetArea = null;
        this._multiSelect = false;
        this._checkedIds = new Set();
    }

    static _slug(name) {
        return (name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '');
    }

    static ACTION_OPTIONS = [
        'examine', 'take', 'use', 'open', 'close',
        'eat', 'drink', 'read', 'light', 'activate',
        'equip', 'unequip', 'throw', 'break',
        'drop'
    ];

    static get TRIGGER_TYPES() { return window.TriggerTypes?.TRIGGER_TYPES || []; }
    static get CONDITION_TYPES() { return window.TriggerTypes?.CONDITION_TYPES || []; }
    static get EFFECT_TYPES() { return window.TriggerTypes?.EFFECT_TYPES || []; }

    async refresh() {
        this.data = await ApiClient.getLibraryItems();
    }

    // --- Open/Close ---

    async open() {
        if (Object.keys(this.data).length === 0) await this.refresh();
        this.selectedId = null;
        this._multiSelect = false;
        this._checkedIds.clear();
        document.getElementById('library-modal').style.display = 'flex';
        const emptyEditor = document.getElementById('item-lib-editor');
        window.Lit.render(itemLibraryHtmlTag`
            <div class="inspector-empty" style="min-height:200px;">
                <div class="inspector-empty-icon">📦</div>
                <p>Select or create an item</p>
            </div>`, emptyEditor);
        this._updatePlaceButton();
        this.renderList('');
    }

    openForRoom(areaName) {
        this._targetArea = areaName;
        this._multiSelect = true;
        this._checkedIds.clear();
        if (VW?.libraryBrowser) VW.libraryBrowser.switchTab('items');
        this.open();
        this._multiSelect = true;
        this.renderList('');
        this._updatePlaceButton();
        events.log(`Select items to place in "${areaName}" (check the ones you want)`, 'system-msg');
    }

    close() {
        document.getElementById('library-modal').style.display = 'none';
        this.selectedId = null;
        this._targetArea = null;
        this._multiSelect = false;
        this._checkedIds.clear();
    }

    // --- List rendering ---

    _getItemType(item) {
        const tags = item.tags || [];
        const contents = item.contents || [];
        if (tags.includes('weapon')) return 'weapon';
        if (tags.includes('resistance')) return 'armor';
        if (tags.includes('armor') || tags.includes('clothing')) return 'armor';
        if (tags.includes('container') || contents.length > 0) return 'container';
        if (tags.includes('key')) return 'key';
        if (tags.includes('potion') || tags.includes('food') || tags.includes('drink')) return 'consumable';
        if (tags.includes('book') || tags.includes('letter') || tags.includes('note') || tags.includes('document')) return 'document';
        if (tags.includes('tool')) return 'tool';
        if (tags.includes('light') || tags.includes('light_source')) return 'light';
        if (tags.includes('quest') || tags.includes('quest_item')) return 'quest';
        if (tags.includes('junk') || tags.includes('trash')) return 'junk';
        if (tags.includes('jewelry') || tags.includes('gem') || tags.includes('valuable')) return 'valuable';
        return 'misc';
    }

    _getTypeIcon(type) {
        const icons = { weapon: '⚔️', armor: '🛡️', container: '📦', key: '🔑', consumable: '🧪', document: '📜', tool: '🔧', light: '🕯️', quest: '⭐', junk: '🗑️', valuable: '💎', misc: '📦' };
        return icons[type] || '📦';
    }

    _getTypeColor(type) {
        const colors = { weapon: '#f85149', armor: '#58a6ff', container: '#3fb950', key: '#d29922', consumable: '#bc8cff', document: '#f778ba', tool: '#e3b341', light: '#e3b341', quest: '#f778ba', junk: '#6e7681', valuable: '#d29922', misc: '#8b949e' };
        return colors[type] || '#8b949e';
    }

    renderList(filter) {
        const listEl = document.getElementById('item-lib-list');
        if (!listEl) return;
        const entries = Object.entries(this.data);
        let filtered = entries;
        if (filter) {
            const f = filter.toLowerCase();
            filtered = entries.filter(([id, item]) =>
                (item.name || id).toLowerCase().includes(f) ||
                (item.description || '').toLowerCase().includes(f) ||
                (item.tags || []).some(t => t.toLowerCase().includes(f))
            );
        }
        // Apply sort
        const sortBy = document.getElementById('lib-sort')?.value || 'name';
        if (sortBy === 'name') {
            filtered.sort((a, b) => (a[1].name || a[0]).localeCompare(b[1].name || b[0]));
        } else if (sortBy === 'type') {
            filtered.sort((a, b) => this._getItemType(a[1]).localeCompare(this._getItemType(b[1])));
        }
        // Update count
        const countEl = document.getElementById('lib-item-count');
        if (countEl) countEl.textContent = filtered.length === entries.length
            ? `${entries.length} item${entries.length !== 1 ? 's' : ''}`
            : `${filtered.length} / ${entries.length} items`;

        if (filtered.length === 0) {
            window.Lit.render(itemLibraryHtmlTag`
                <div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">No items found.</div>`, listEl);
            return;
        }
        const rows = [];
        for (const [id, item] of filtered) {
            const sel = id === this.selectedId;
            const name = item.name || id;
            const desc = (item.description || '');
            const tags = item.tags || [];
            const itemType = this._getItemType(item);
            const typeIcon = this._getTypeIcon(itemType);
            const typeColor = this._getTypeColor(itemType);
            const triggerCount = (item.triggers || []).length;
            const contents = item.contents || [];

            const badges = [];
            if (tags.length > 0) {
                tags.slice(0, 2).forEach(t => {
                    badges.push(itemLibraryHtmlTag`<span style="font-size:8px;padding:1px 5px;border-radius:3px;background:var(--bg-hover);color:var(--text-muted);border:1px solid var(--border);white-space:nowrap;">${t}</span>`);
                });
            }
            if (triggerCount > 0) badges.push(itemLibraryHtmlTag`<span style="font-size:8px;padding:1px 5px;border-radius:3px;background:rgba(227,179,65,0.15);color:var(--orange);border:1px solid rgba(227,179,65,0.3);white-space:nowrap;">⚡${triggerCount}</span>`);
            if (contents.length > 0) badges.push(itemLibraryHtmlTag`<span style="font-size:8px;padding:1px 5px;border-radius:3px;background:rgba(63,185,80,0.15);color:var(--green);border:1px solid rgba(63,185,80,0.3);white-space:nowrap;">📦${contents.length}</span>`);
            const badgeHtml = badges.length > 0 ? itemLibraryHtmlTag`<div style="display:flex;gap:3px;flex-wrap:wrap;margin-top:3px;">${badges}</div>` : '';

            if (this._multiSelect) {
                const checked = this._checkedIds.has(id);
                rows.push(itemLibraryHtmlTag`<div class="agent-item" style="cursor:pointer;padding:5px 10px;border-left:3px solid ${typeColor};" @click=${() => VW.itemLib._toggleCheck(id)}>
                    <input type="checkbox" ?checked=${checked} style="margin-right:6px;cursor:pointer;" @click=${(e) => { e.stopPropagation(); VW.itemLib._toggleCheck(id); }}>
                    <span style="font-size:14px;margin-right:4px;">${typeIcon}</span>
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:4px;">
                            <span class="agent-name" style="font-size:12px;font-weight:600;">${name}</span>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${desc}${desc ? '...' : ''}</div>
                        ${badgeHtml}
                    </div>
                </div>`);
            } else {
                rows.push(itemLibraryHtmlTag`<div class="agent-item ${sel ? 'selected' : ''}" @click=${() => VW.itemLib.select(id)} style="cursor:pointer;padding:5px 10px;border-left:3px solid ${typeColor};${sel ? 'background:var(--bg-inset);' : ''}">
                    <span style="font-size:14px;margin-right:4px;">${typeIcon}</span>
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:4px;">
                            <span class="agent-name" style="font-size:12px;font-weight:600;">${name}</span>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${desc}${desc ? '...' : ''}</div>
                        ${badgeHtml}
                    </div>
                </div>`);
            }
        }
        window.Lit.render(itemLibraryHtmlTag`${rows}`, listEl);
        this._updatePlaceButton();
    }

    _toggleCheck(id) {
        if (this._checkedIds.has(id)) this._checkedIds.delete(id);
        else this._checkedIds.add(id);
        this.renderList(document.getElementById('item-lib-search')?.value || '');
    }

    _updatePlaceButton() { return ItemLibraryPlacement.updatePlaceButton.call(this); }

    filter() {
        this.renderList(document.getElementById('item-lib-search')?.value || '');
    }

    select(id) {
        if (this._multiSelect) return;
        this.selectedId = id;
        this.renderList(document.getElementById('item-lib-search')?.value || '');
        this.showEditor(this.data[id] || {});
    }

    newItem() {
        this.selectedId = '__new__';
        this.renderList(document.getElementById('item-lib-search')?.value || '');
        this.showEditor({ 
            name: '', description: '', actions: 'examine,take,use', 
            uses: -1, weight: 0.1, current_state: 'normal', tags: [], triggers: [], contents: []
        });
    }

    // --- Container Contents Editor ---

    _renderContentsSection(contents) { return ItemLibraryContents.renderContentsSection.call(this, contents); }

    _removeContent(idx) { return ItemLibraryContents.removeContent.call(this, idx); }

    _addContentUi() { return ItemLibraryContents.addContentUi.call(this); }

    _saveContent(btn) { return ItemLibraryContents.saveContent.call(this, btn); }

    // --- Editor ---

    _toggleTriggers() {
        const list = document.getElementById('lib-trigger-list');
        const icon = document.getElementById('lib-trigger-toggle-icon');
        if (!list) return;
        const isOpen = list.style.display !== 'none';
        list.style.display = isOpen ? 'none' : 'block';
        if (icon) icon.textContent = isOpen ? '▶' : '▼';
    }

    /** Auto-fill the ID from the name while creating a new item. */
    _autoIdFromName(input) {
        if (this.selectedId !== '__new__') return;
        const idInput = document.getElementById('lib-item-id');
        if (!idInput) return;
        const name = (input?.value || '').trim();
        const slug = name.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '');
        if (slug && !idInput.value) {
            idInput.value = slug;
        } else if (!slug) {
            idInput.value = '';
        }
    }

    _duplicateItem() {        const id = document.getElementById('lib-item-id')?.value;
        if (!id || id === '__new__') return;
        const item = this.data[id];
        if (!item) return;
        const newId = (id + '_copy').toLowerCase();
        const newName = (item.name || id) + ' (Copy)';
        document.getElementById('lib-item-id').value = newId;
        document.getElementById('lib-item-name').value = newName;
        document.getElementById('lib-item-id').removeAttribute('readonly');
        document.getElementById('lib-item-id').style.color = '';
        events.log(`Duplicated "${id}" — ready to save as "${newId}"`, 'system-msg');
    }

    _onLibItemImageFileChange(input) {
        const file = input && input.files && input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const dataUrl = e.target.result;
            document.getElementById('lib-item-image').value = dataUrl;
            const preview = document.getElementById('lib-item-image-preview');
            if (preview) {
                window.Lit.render(itemLibraryHtmlTag`<img src=${dataUrl} alt="Item image" style="max-width:120px;max-height:120px;border-radius:6px;border:1px solid var(--border);display:block;">`, preview);
            }
            const urlField = document.getElementById('lib-item-image-url');
            if (urlField) urlField.value = dataUrl;
            input.value = '';
        };
        reader.readAsDataURL(file);
    }

    _setLibItemImageFromUrl() {
        const urlField = document.getElementById('lib-item-image-url');
        const url = urlField && urlField.value.trim();
        if (!url) return;
        document.getElementById('lib-item-image').value = url;
        const preview = document.getElementById('lib-item-image-preview');
        if (preview) {
            window.Lit.render(itemLibraryHtmlTag`<img src=${url} alt="Item image" style="max-width:120px;max-height:120px;border-radius:6px;border:1px solid var(--border);display:block;">`, preview);
        }
    }

    _clearLibItemImage() {
        document.getElementById('lib-item-image').value = '';
        const preview = document.getElementById('lib-item-image-preview');
        if (preview) {
            window.Lit.render(itemLibraryHtmlTag`<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No image set.</div>`, preview);
        }
        const urlField = document.getElementById('lib-item-image-url');
        if (urlField) urlField.value = '';
    }

    _exportJSON() {
        const id = document.getElementById('lib-item-id')?.value;
        if (!id || id === '__new__') return;
        const item = this.data[id];
        if (!item) return;
        const payload = { id, ...item };
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${id}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    showEditor(item) {
        const editor = document.getElementById('item-lib-editor');
        if (!editor) return;
        const isNew = this.selectedId === '__new__';
        const tags = item.tags || [];
        if (item.two_handed && !tags.includes('two_handed')) tags.unshift('two_handed');
        if (item.container && !tags.includes('container')) tags.unshift('container');
        const itemActions = (typeof item.actions === 'string' ? item.actions.split(',') : item.actions || []).map(a => a.trim());
        const contents = item.contents || [];

        // Action checkboxes
        const actionCheckboxes = ItemLibrary.ACTION_OPTIONS.map(act =>
            itemLibraryHtmlTag`<label style="display:inline-flex;align-items:center;gap:3px;font-size:11px;padding:2px 6px;border-radius:3px;background:${itemActions.includes(act) ? 'var(--accent-dim)' : 'var(--bg-input)'};cursor:pointer;">
                <input type="checkbox" class="act-chk-lib" .value=${act} ?checked=${itemActions.includes(act)} @change=${() => VW.itemLib._updateActionsPreview()}>
                ${act}
            </label>`
        );

        // Trigger list
        const triggers = item.triggers || [];
        const triggerCount = triggers.length;
        const hasTriggers = triggerCount > 0;
        const triggerHtml = triggers.length > 0 ? triggers.map((t, idx) => {
            const effects = t.effects || [];
            const conditions = t.conditions || [];
            const condHtml = TriggerEditor._renderConditionSummary(conditions).join(' ');
            const effectNames = effects.map(e => e.type).join(', ');
            const firstParams = effects[0]?.params || {};
            const successMsg = firstParams.success_message || firstParams.message || '';
            const failMsg = firstParams.fail_message || '';
            return itemLibraryHtmlTag`<div style="padding:6px 8px;background:var(--bg-inset);border-radius:4px;margin-bottom:4px;border-left:3px solid var(--orange);">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div style="flex:1;min-width:0;">
                        <div><span style="font-weight:600;font-size:11px;">${t.trigger_type}</span> <span style="font-size:10px;color:var(--text-muted);">→ ${effectNames}</span>${window.Lit.unsafeHTML(condHtml)}</div>
                        ${successMsg ? itemLibraryHtmlTag`<div style="font-size:10px;color:var(--green);font-style:italic;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">✅ \u201C${successMsg}\u201D</div>` : ''}
                        ${failMsg ? itemLibraryHtmlTag`<div style="font-size:10px;color:var(--orange);font-style:italic;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">❌ \u201C${failMsg}\u201D</div>` : ''}
                        ${effects.length > 1 ? itemLibraryHtmlTag`<div style="font-size:9px;color:var(--text-muted);">${effects.length} effects</div>` : ''}
                    </div>
                    <button class="btn btn-sm btn-ghost" @click=${() => VW.itemLib._editTrigger(idx)} style="font-size:9px;flex-shrink:0;margin-left:4px;" title="Edit trigger">✏️</button>
                    <button class="btn btn-sm btn-ghost" @click=${() => VW.itemLib._removeTrigger(idx)} style="font-size:9px;color:var(--red);flex-shrink:0;margin-left:4px;">✕</button>
                </div>
            </div>`;
        }) : itemLibraryHtmlTag`<div style="font-size:11px;color:var(--text-muted);padding:8px 0;text-align:center;">No triggers defined. Click ✚ Add to create one.</div>`;

        const savedId = item.id || this.selectedId || '';

        window.Lit.render(itemLibraryHtmlTag`
            <div class="inspector-section" style="padding:10px 16px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <h3 style="margin:0;font-size:13px;font-weight:700;">${isNew ? '✏️ Create New Item' : '✏️ Edit Item'}</h3>
                    <div style="display:flex;gap:3px;">
                        ${!isNew ? itemLibraryHtmlTag`<button class="btn btn-sm btn-ghost" @click=${() => VW.itemLib._duplicateItem()} title="Duplicate" style="font-size:11px;">📋</button>` : ''}
                        ${!isNew ? itemLibraryHtmlTag`<button class="btn btn-sm btn-ghost" @click=${() => VW.itemLib._exportJSON()} title="Export JSON" style="font-size:11px;">📤</button>` : ''}
                        ${!isNew ? itemLibraryHtmlTag`<button class="btn btn-sm btn-ghost" @click=${() => VW.itemLib.delete(savedId)} title="Delete" style="font-size:11px;color:var(--red);">🗑️</button>` : ''}
                    </div>
                </div>
                <div style="display:flex;gap:4px;margin-bottom:4px;">
                    <input type="text" id="lib-ai-prompt" placeholder="AI prompt: e.g. 'a cursed ring'" style="flex:1;font-size:11px;">
                    <button class="btn btn-sm btn-purple" @click=${() => VW.itemLib.generateWithAI()} style="white-space:nowrap;background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">🤖 Generate</button>
                    <button class="btn btn-sm" @click=${() => VW.itemLib.previewPrompt()} title="Preview and edit prompt" style="background:var(--bg-inset);border-color:var(--border);">👁️</button>
                    <button class="btn btn-sm" id="lib-improve-btn" @click=${() => VW.itemLib.improveWithAI()} style="white-space:nowrap;background:#2a6a3a;border-color:#3a9a5a;color:#7cff9c;">✨ Improve</button>
                </div>
                <label style="font-size:10px;"><input type="checkbox" id="lib-gen-use-context" checked> 🧠 Use area context for thematically correct generation</label>
            </div>
            <div class="inspector-section" style="padding:10px 16px;border-bottom:1px solid var(--border);">
                <h3 style="font-size:11px;font-weight:600;margin:0 0 6px 0;color:var(--text-dim);display:flex;align-items:center;gap:4px;">🖼 Image</h3>
                <div id="lib-item-image-preview" style="margin-bottom:4px;">
                    ${item.image ? itemLibraryHtmlTag`<img src=${item.image} alt="Item image" style="max-width:120px;max-height:120px;border-radius:6px;border:1px solid var(--border);display:block;">` : itemLibraryHtmlTag`<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No image set.</div>`}
                </div>
                <input type="file" id="lib-item-image-file" accept="image/*" @change=${(e) => VW.itemLib._onLibItemImageFileChange(e.target)} style="font-size:10px;margin-bottom:4px;">
                <div class="field" style="display:flex;gap:4px;align-items:center;margin-top:4px;">
                    <input type="text" id="lib-item-image-url" placeholder="...or paste a base64 data URL" .value=${item.image || ''} style="flex:1;font-size:11px;">
                    <button class="btn btn-sm" @click=${() => VW.itemLib._setLibItemImageFromUrl()} style="font-size:10px;">Set</button>
                </div>
                <input type="hidden" id="lib-item-image" .value=${item.image || ''}>
                ${item.image ? itemLibraryHtmlTag`<button class="btn btn-sm btn-danger" @click=${() => VW.itemLib._clearLibItemImage()} style="margin-top:4px;font-size:10px;">🗑 Remove Image</button>` : ''}
            </div>
            <div class="inspector-section" style="padding:10px 16px;border-bottom:1px solid var(--border);">
                <h3 style="font-size:11px;font-weight:600;margin:0 0 6px 0;color:var(--text-dim);display:flex;align-items:center;gap:4px;">📝 Description</h3>
                <div class="field"><label style="font-size:10px;">ID</label><input type="text" id="lib-item-id" .value=${isNew ? '' : (item.id || this.selectedId || '')} placeholder="unique_key_name" ?readonly=${!isNew} style=${isNew ? '' : 'color:var(--text-muted);'}>
                <div style="font-size:9px;color:var(--text-muted);">Use lowercase, no spaces. E.g. "rusty_key"</div></div>
                <div class="field"><label style="font-size:10px;">Name</label><input type="text" id="lib-item-name" .value=${item.name} placeholder="Rusty Key" @input=${isNew ? (e) => VW.itemLib._autoIdFromName(e.target) : undefined}></div>
                <div class="field"><label style="font-size:10px;">Description</label><textarea id="lib-item-desc" rows="4" placeholder="A rusty old key..." style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);padding:4px 8px;font-size:11px;font-family:inherit;resize:vertical;">${item.description}</textarea></div>
                <div class="field"><label style="font-size:10px;">Tags</label><div id="lib-item-tags-container"></div></div>
            </div>
            <div class="inspector-section" style="padding:10px 16px;border-bottom:1px solid var(--border);">
                <h3 style="font-size:11px;font-weight:600;margin:0 0 6px 0;color:var(--text-dim);display:flex;align-items:center;gap:4px;">✅ Actions</h3>
                <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:4px;">
                    ${actionCheckboxes}
                </div>
                <input type="hidden" id="lib-item-actions" .value=${typeof item.actions === 'string' ? item.actions : (item.actions || []).join(',')}>
            </div>
            <div class="inspector-section" style="padding:10px 16px;border-bottom:1px solid var(--border);">
                <h3 style="font-size:11px;font-weight:600;margin:0 0 6px 0;color:var(--text-dim);display:flex;align-items:center;gap:4px;">⚙️ Properties</h3>
                <div style="display:flex;gap:8px;">
                    <div class="field" style="flex:1;"><label style="font-size:10px;">Uses</label><input type="number" id="lib-item-uses" .value=${item.uses ?? -1} style="width:100%;"></div>
                    <div class="field" style="flex:1;"><label style="font-size:10px;">Weight</label><input type="number" step="0.1" id="lib-item-weight" .value=${item.weight ?? 0.1} style="width:100%;"></div>
                </div>
                <div class="field" style="margin-top:4px;"><label style="font-size:10px;">State</label>
                    <select id="lib-item-state" style="width:100%;font-size:11px;">
                        ${['normal','lit','unlit','open','closed','locked','broken','charged','depleted'].map(s => itemLibraryHtmlTag`<option .value=${s} ?selected=${(item.current_state || 'normal') === s}>${s}</option>`)}
                    </select>
                </div>
                <div style="display:flex;gap:8px;align-items:center;margin-top:4px;">
                </div>
                <div class="field" style="margin-top:4px;"><label style="font-size:10px;">Equip Slots (select one or more)</label>
                    <select multiple class="choices-init" id="lib-item-equip-slots" style="width:100%;">
                        ${['head','neck','torso','arms','hands','legs','feet','back','waist','accessory','hand_left','hand_right'].map(s => itemLibraryHtmlTag`<option .value=${s} ?selected=${(item.equip_slots||[]).includes(s)}>${s}</option>`)}
                    </select>
                </div>
                <div id="lib-equip-bonus-defense" style="display:${tags.includes('armor') || tags.includes('clothing') ? 'flex' : 'none'};gap:8px;margin-top:4px;">
                    <div class="field" style="flex:1;"><label style="font-size:10px;">Defense (DR)</label><input type="number" id="lib-item-defense" .value=${item.defense ?? 0} min="0" style="width:100%;"></div>
                </div>
                <div id="lib-equip-bonus-damage" style="display:${tags.includes('weapon') ? 'block' : 'none'};margin-top:4px;">
                    <div class="field"><label style="font-size:10px;">Damage (e.g. "2d6+3", "1d8", or "8")</label><input type="text" id="lib-item-damage" .value=${item.damage ?? ''} placeholder="2d6+3" style="width:100%;font-size:11px;"></div>
                    <div class="field"><label style="font-size:10px;">Damage Skill</label>
                        <select id="lib-item-damage-skill" style="width:100%;font-size:11px;">
                            ${['Athletics','Acrobatics','Stealth','Perception','Investigation','Survival','Persuasion','Performance','Medicine','Arcana','Intimidation','Lockpicking'].map(s => itemLibraryHtmlTag`<option .value=${s} ?selected=${(item.damage_skill || 'Athletics') === s}>${s}</option>`)}
                        </select>
                    </div>
                    <div class="field"><label style="font-size:10px;">Damage Type</label>
                        <select id="lib-item-damage-type" style="width:100%;font-size:11px;">
                            <option .value=${''}>— None —</option>
                            ${['slashing','piercing','bludgeoning','fire','cold','toxic','magic','electric','radiant','necrotic','psychic','acid'].map(dt => itemLibraryHtmlTag`<option .value=${dt} ?selected=${(item.damage_type || '') === dt}>${dt}</option>`)}
                        </select>
                    </div>
                    <div class="field" style="display:flex;gap:8px;">
                        <div style="flex:1;"><label style="font-size:10px;">Stun Chance %</label><input type="number" id="lib-item-stun-chance" .value=${item.stun_chance ?? ''} min="0" max="100" placeholder="0" style="width:100%;"></div>
                        <div style="flex:1;"><label style="font-size:10px;">Stun Duration (turns)</label><input type="number" id="lib-item-stun-duration" .value=${item.stun_duration ?? ''} min="1" placeholder="2" style="width:100%;"></div>
                    </div>
                </div>
                <div id="lib-equip-bonus-temp" style="display:${(tags.includes('insulation') || tags.includes('environmental')) ? 'flex' : 'none'};gap:8px;margin-top:4px;">
                    <div class="field" style="flex:1;">
                        <label style="font-size:10px;">Insulation (°C shift) <span title="Positive warms (traps body heat), negative cools (wicks heat away). Stacks across items. At -12°C with insulation 14 you feel 2°C. At 35°C with same coat you feel 49°C." style="cursor:help;color:var(--text-muted);">ⓘ</span></label>
                        <input type="number" id="lib-item-insulation" .value=${item.insulation ?? ''} step="1" placeholder="+warms, -cools" style="width:100%;">
                    </div>
                </div>
                <div id="lib-equip-bonus-resists" style="display:${tags.includes('resistance') ? 'block' : 'none'};margin-top:4px;">
                    <div class="field"><label style="font-size:10px;">Resistances (format: fire:5, cold:3, magic:2)</label>
                        <input type="text" id="lib-item-resistances" .value=${item.resistances ? Object.entries(item.resistances).map(([k,v]) => `${k}:${v}`).join(', ') : ''} placeholder="fire:5, cold:3, toxic:999" style="width:100%;font-size:11px;">
                    </div>
                </div>
                <div id="lib-equip-bonus-light" style="display:${tags.includes('light_source') ? 'block' : 'none'};margin-top:4px;">
                    <div class="field"><label style="font-size:10px;">Light Level</label>
                        <select id="lib-item-light-level" style="width:100%;font-size:11px;">
                            <option .value=${'pitch_black'} ?selected=${item.light_level === 'pitch_black'}>Pitch Black</option>
                            <option .value=${'dim'} ?selected=${(!item.light_level || item.light_level === 'dim')}>Dim</option>
                            <option .value=${'normal'} ?selected=${item.light_level === 'normal'}>Normal</option>
                            <option .value=${'bright'} ?selected=${item.light_level === 'bright'}>Bright</option>
                            <option .value=${'blinding'} ?selected=${item.light_level === 'blinding'}>Blinding</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="inspector-section" style="padding:10px 16px;border-bottom:1px solid var(--border);">
                <h3 style="font-size:11px;font-weight:600;margin:0 0 6px 0;color:var(--text-dim);display:flex;align-items:center;gap:4px;">📦 Container Contents</h3>
                <div id="lib-contents-list">
                    ${this._renderContentsSection(contents)}
                </div>
                <input type="hidden" id="lib-item-contents" .value=${JSON.stringify(contents)}>
                <button class="btn btn-sm btn-blue" @click=${() => VW.itemLib._addContentUi()} style="margin-top:4px;">➕ Add Contained Item</button>
            </div>
            <div class="inspector-section" style="padding:10px 16px;border-bottom:1px solid var(--border);">
                <div style="display:flex;justify-content:space-between;align-items:center;cursor:pointer;" @click=${() => VW.itemLib._toggleTriggers()}>
                    <h3 style="font-size:11px;font-weight:600;margin:0;color:var(--text-dim);display:flex;align-items:center;gap:4px;">
                        ⚡ Triggers
                        <span id="lib-trigger-count-badge" style=${(hasTriggers ? '' : 'display:none;') + 'font-size:9px;background:rgba(227,179,65,0.2);color:var(--orange);padding:0 6px;border-radius:8px;line-height:16px;'}>${triggerCount}</span>
                    </h3>
                    <div style="display:flex;gap:3px;align-items:center;">
                        <button class="btn btn-sm" @click=${(e) => { e.stopPropagation(); VW.itemLib._openGraphEditor(); }} style="font-size:10px;padding:2px 8px;">🧩 Graph</button>
                        <button class="btn btn-sm btn-blue" @click=${(e) => { e.stopPropagation(); VW.itemLib._addTrigger(); }} style="font-size:10px;padding:2px 8px;">➕ Add</button>
                        <span id="lib-trigger-toggle-icon" style="font-size:10px;color:var(--text-muted);">${hasTriggers ? '▼' : '▶'}</span>
                    </div>
                </div>
                <div id="lib-trigger-list" style=${hasTriggers ? '' : 'display:none;'}>
                    ${triggerHtml}
                </div>
                <input type="hidden" id="lib-item-triggers" .value=${JSON.stringify(triggers)}>
            </div>
            <div style="display:flex;gap:6px;padding:10px 16px;">
                <button class="btn btn-green btn-sm" @click=${() => VW.itemLib.save()} style="flex:1;">💾 Save</button>
            </div>`, editor);
        if (typeof reinitChoices === 'function') reinitChoices(editor);
        if (this._tagMs) this._tagMs.destroy();
        const tagContainer = document.getElementById('lib-item-tags-container');
        if (tagContainer && typeof TagMultiselect !== 'undefined') {
            this._tagMs = new TagMultiselect(tagContainer, {
                tags: Array.isArray(tags) ? tags : [],
                appliesTo: 'items',
                allowNew: true,
                placeholder: 'Search or create tags...',
                onChange: (newTags) => {
                    const tagList = newTags || this._tagMs?.getValue() || [];
                    const showDefense = tagList.includes('armor') || tagList.includes('clothing');
                    const showDamage = tagList.includes('weapon');
                    const showTemp = tagList.includes('insulation') || tagList.includes('environmental');
                    const showResists = tagList.includes('resistance');
                    const showLight = tagList.includes('light_source');
                    const dEl = document.getElementById('lib-equip-bonus-defense');
                    const wEl = document.getElementById('lib-equip-bonus-damage');
                    const tEl = document.getElementById('lib-equip-bonus-temp');
                    const rEl = document.getElementById('lib-equip-bonus-resists');
                    const lEl = document.getElementById('lib-equip-bonus-light');
                    if (dEl) dEl.style.display = showDefense ? 'flex' : 'none';
                    if (wEl) wEl.style.display = showDamage ? 'block' : 'none';
                    if (tEl) tEl.style.display = showTemp ? 'flex' : 'none';
                    if (rEl) rEl.style.display = showResists ? 'block' : 'none';
                    if (lEl) lEl.style.display = showLight ? 'block' : 'none';
                }
            });
        }
    }

    _updateActionsPreview() {
        const checked = document.querySelectorAll('.act-chk-lib:checked');
        const vals = Array.from(checked).map(checkbox => checkbox.value);
        document.getElementById('lib-item-actions').value = vals.join(',');
    }

    // --- Trigger Editor ---

    _buildTargetDatalistHtml() {
        const targetOpts = [];
        const commonDirs = ['north','south','east','west','northeast','northwest','southeast','southwest','up','down'];
        for (const d of commonDirs) targetOpts.push({ value: d, label: `🚪 ${d}` });
        if (worldState?.graph?.nodes) {
            for (const [id, node] of Object.entries(worldState.graph.nodes)) {
                const lbl = node.name || id;
                if (node.type === 'way' && !targetOpts.find(o => o.value === lbl)) {
                    targetOpts.push({ value: lbl, label: `🚪 ${lbl}` });
                }
            }
        }
        if (worldState?.areas) {
            for (const area of Object.values(worldState.areas)) {
                if (area.exits) {
                    for (const [direction, exit] of Object.entries(area.exits)) {
                        if (!targetOpts.find(o => o.value === direction)) {
                            const targetName = exit.target || '';
                            targetOpts.push({ value: direction, label: `🚪 ${direction} → ${targetName}` });
                        }
                        if (exit.way_id && !targetOpts.find(o => o.value === exit.way_id)) {
                            targetOpts.push({ value: exit.way_id, label: `🚪 ${exit.way_id}` });
                        }
                    }
                }
                if (area.items) {
                    for (const item of area.items) {
                        const itemName = item.name || item.id || item;
                        if (!targetOpts.find(o => o.value === itemName)) {
                            targetOpts.push({ value: itemName, label: `📦 ${itemName}` });
                        }
                    }
                }
            }
        }
        for (const [id, it] of Object.entries(this.data)) {
            const lbl = it.name || id;
            if (!targetOpts.find(o => o.value === lbl)) {
                targetOpts.push({ value: lbl, label: `📦 ${lbl} (library)` });
            }
        }
        targetOpts.sort((a, b) => a.value.localeCompare(b.value));
        return targetOpts.map(o => `<option value="${o.value}">${o.label}</option>`).join('');
    }

    _buildItemDatalistHtml() {
        const itemOpts = new Map();
        for (const [id, it] of Object.entries(this.data)) {
            const name = it.name || id;
            if (!itemOpts.has(name)) itemOpts.set(name, { value: id, label: `📦 ${name} (library)` });
        }
        if (worldState?.graph?.nodes) {
            for (const [id, node] of Object.entries(worldState.graph.nodes)) {
                if (node.type === 'item') {
                    const name = node.name || id;
                    if (!itemOpts.has(name)) itemOpts.set(name, { value: name, label: `📦 ${name} (world)` });
                }
            }
        }
        return [...itemOpts.values()]
            .sort((a, b) => a.value.localeCompare(b.value))
            .map(o => `<option value="${o.value}">${o.label}</option>`).join('');
    }

    _addTrigger() {
        TriggerEditor.show({
            mode: 'multi',
            effectTypes: ItemLibrary.EFFECT_TYPES,
            conditionTypes: ItemLibrary.CONDITION_TYPES,
            triggerTypes: ItemLibrary.TRIGGER_TYPES,
            targetDatalistHtml: this._buildTargetDatalistHtml(),
            itemDatalistHtml: this._buildItemDatalistHtml(),
            onSave: (data) => {
                // Collect triggers from hidden field
                const currentTriggers = parseJsonSafely(document.getElementById('lib-item-triggers')?.value || '[]') || [];
                const newTrigger = {
                    trigger_type: Array.isArray(data.trigger_type) ? data.trigger_type : [data.trigger_type],
                    effects: data.effects,
                    conditions: data.conditions,
                    target_name: data.target_name || '',
                    target_state: data.target_state || '',
                    success_message: data.success_message || '',
                    fail_message: data.fail_message || ''
                };
                currentTriggers.push(newTrigger);
                document.getElementById('lib-item-triggers').value = JSON.stringify(currentTriggers);
                this._refreshEditorWithTriggers();
                events.log('Trigger added to library item.', 'system-msg');
            }
        });
    }

    _editTrigger(idx) {
        const currentTriggers = parseJsonSafely(document.getElementById('lib-item-triggers')?.value || '[]') || [];
        const existing = currentTriggers[idx];
        if (!existing) return;
        // Rebuild an effects array with params (legacy single-effect format
        // {effect_type, effect_params} → {type, params} for the editor).
        const effects = Array.isArray(existing.effects) && existing.effects.length
            ? existing.effects.map(e => ({ type: e.type || existing.effect_type || 'message', params: e.params || existing.effect_params || {} }))
            : [{ type: existing.effect_type || 'message', params: existing.effect_params || {} }];
        TriggerEditor.show({
            mode: 'multi',
            effectTypes: ItemLibrary.EFFECT_TYPES,
            conditionTypes: ItemLibrary.CONDITION_TYPES,
            triggerTypes: ItemLibrary.TRIGGER_TYPES,
            targetDatalistHtml: this._buildTargetDatalistHtml(),
            itemDatalistHtml: this._buildItemDatalistHtml(),
            initialData: {
                trigger_type: existing.trigger_type,
                effects,
                conditions: existing.conditions || [],
                target_name: existing.target_name || '',
                target_state: existing.target_state || '',
                success_message: existing.success_message || '',
                fail_message: existing.fail_message || ''
            },
            onSave: (data) => {
                currentTriggers[idx] = {
                    trigger_type: Array.isArray(data.trigger_type) ? data.trigger_type : [data.trigger_type],
                    effects: data.effects,
                    conditions: data.conditions,
                    target_name: data.target_name || '',
                    target_state: data.target_state || '',
                    success_message: data.success_message || '',
                    fail_message: data.fail_message || ''
                };
                document.getElementById('lib-item-triggers').value = JSON.stringify(currentTriggers);
                this._refreshEditorWithTriggers();
                events.log(`Trigger ${idx + 1} updated on library item.`, 'system-msg');
            }
        });
    }

    _openGraphEditor() {
        const currentTriggers = parseJsonSafely(document.getElementById('lib-item-triggers')?.value || '[]') || [];
        if (currentTriggers.length > 1 && typeof toastInfo === 'function') {
            toastInfo('Graph editor edits the first trigger only — use ✏️ for others.');
        }
        const triggerData = currentTriggers[0] || {};
        const graph = TriggerGraph.triggerToGraph(triggerData);

        const persistFormData = (data) => {
            const triggers = parseJsonSafely(document.getElementById('lib-item-triggers')?.value || '[]') || [];
            const compiled = {
                trigger_type: data.trigger_type,
                effects: data.effects,
                conditions: data.conditions,
                target_name: data.target_name || '',
                target_state: data.target_state || '',
                success_message: data.success_message || '',
                fail_message: data.fail_message || '',
            };
            if (triggers.length > 0) {
                triggers[0] = { ...triggers[0], ...compiled };
            } else {
                triggers.push(compiled);
            }
            document.getElementById('lib-item-triggers').value = JSON.stringify(triggers);
            this._refreshEditorWithTriggers();
            events.log('Trigger graph applied.', 'system-msg');
        };

        TriggerGraph.show({
            graph,
            editorBridge: {
                mode: 'multi',
                effectTypes: ItemLibrary.EFFECT_TYPES,
                conditionTypes: ItemLibrary.CONDITION_TYPES,
                triggerTypes: ItemLibrary.TRIGGER_TYPES,
                targetDatalistHtml: this._buildTargetDatalistHtml(),
                itemDatalistHtml: this._buildItemDatalistHtml(),
                initialName: triggerData.name || '',
                success_message: triggerData.success_message || '',
                fail_message: triggerData.fail_message || '',
                onSave: (data) => persistFormData(data),
            },
            onSave: (newGraph) => {
                const compiled = TriggerGraph.compileToEngine(newGraph);
                if (!compiled) return;
                persistFormData({
                    ...TriggerGraph.engineToFormData(compiled),
                    success_message: triggerData.success_message || '',
                    fail_message: compiled.fail_message || triggerData.fail_message || '',
                });
            }
        });
    }

    _removeTrigger(idx) {
        const triggersField = document.getElementById('lib-item-triggers');
        const triggers = JSON.parse(triggersField.value || '[]');
        triggers.splice(idx, 1);
        triggersField.value = JSON.stringify(triggers);
        this._refreshEditorWithTriggers();
    }

    _buildEffectDetail(effects) {
        const first = effects?.[0] || {};
        const type = first.type || 'unknown';
        const params = first.params || {};
        let detail = type;
        if (type === 'damage' && params.amount) detail += ` (${params.amount})`;
        else if (type === 'heal' && params.amount) detail += ` (${params.amount} ${params.stat || 'HP'})`;
        else if (type === 'adjust_vital') detail += ` (${params.stat||'HP'} ${params.amount > 0 ? '+' : ''}${params.amount})`;
        else if (type === 'adjust_environment') {
            const parts = [];
            if (params.temperature !== undefined) parts.push(`temp${params.temperature > 0 ? '+' : ''}${params.temperature}`);
            if (params.light !== undefined) parts.push(`light${params.light > 0 ? '+' : ''}${params.light}`);
            if (parts.length) detail += ` (${parts.join(', ')})`;
        }
        else if (type === 'spawn_item' && params.item_id) detail += ` (${params.item_id})`;
        else if (type === 'give_item' && params.item_id) detail += ` → ${params.target || 'self'}: ${params.item_id}`;
        else if (type === 'save') {
            const check = params.stat || params.skill || 'WIS';
            detail += ` (${check} DC${params.dc || 12})`;
        }
        else if ((type === 'add_tag' || type === 'remove_tag') && params.tag) detail += ` (${params.tag} → ${params.node_id || 'self'})`;
        else if (type === 'set_environment') {
            const parts = ['light','temperature','air','smell','noise'].filter(k => params[k] !== undefined).map(k => `${k}:${params[k]}`);
            if (parts.length) detail += ` (${parts.join(', ')})`;
        }
        else if (type === 'set_state' && params.state) detail += ` (${params.state})`;
        else if (type === 'teleport' && params.area) detail += ` → ${params.area}`;
        else if (type === 'unlock_way' && params.way_id) detail += ` (${params.way_id})`;
        else if (type === 'rename' && (params.name || params.new_name)) detail += ` → ${params.name || params.new_name}`;
        else if (type === 'remove_item' && params.item_id) detail += ` (${params.item_id})`;
        else if (type === 'set_description' && (params.value || params.description)) {
            const descVal = params.value || params.description || '';
            detail += ` (${descVal.substring(0, 30)}${descVal.length > 30 ? '...' : ''})`;
        }
        else if (type === 'append_description' && params.text) detail += ` +"${(params.text||'').substring(0,25)}${(params.text||'').length > 25 ? '...' : ''}"`;
        return detail;
    }

    _refreshEditorWithTriggers() {
        const triggersField = document.getElementById('lib-item-triggers');
        const triggers = JSON.parse(triggersField.value || '[]');
        const listEl = document.getElementById('lib-trigger-list');
        if (!listEl) return;

        if (triggers.length === 0) {
            window.Lit.render(itemLibraryHtmlTag`
                <div style="font-size:11px;color:var(--text-muted);padding:8px;text-align:center;">No triggers defined.</div>`, listEl);
        } else {
            window.Lit.render(itemLibraryHtmlTag`${triggers.map((t, idx) => {
                const effects = t.effects || [];
                const conditions = t.conditions || {};
                const condHtml = (TriggerEditor._renderConditionSummary(conditions) || []).join(' ');
                const effectDetail = this._buildEffectDetail(effects);
                const firstParams = effects[0]?.params || {};
                const successMsg = firstParams.success_message || firstParams.message || '';
                const failMsg = firstParams.fail_message || '';
                return itemLibraryHtmlTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:6px;margin-bottom:4px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <strong>${Array.isArray(t.trigger_type) ? t.trigger_type.join(', ') : t.trigger_type}</strong>
                    <div>
                        <button class="btn btn-sm" @click=${() => VW.itemLib._editTrigger(idx)} style="font-size:10px;">✏️</button>
                        <button class="btn btn-sm btn-red" @click=${() => VW.itemLib._removeTrigger(idx)} style="font-size:10px;">✕</button>
                    </div>
                </div>
                <div style="font-size:10px;color:var(--text-dim);margin-top:2px;">Effect: ${effectDetail}</div>
                ${successMsg ? itemLibraryHtmlTag`<div style="font-size:10px;color:var(--text-muted);">${successMsg}</div>` : ''}
                ${failMsg ? itemLibraryHtmlTag`<div style="font-size:10px;color:var(--orange);font-style:italic;">❌ ${failMsg}</div>` : ''}
                ${effects.length > 1 ? itemLibraryHtmlTag`<div style="font-size:9px;color:var(--text-muted);">${effects.length} effects</div>` : ''}
                ${condHtml ? itemLibraryHtmlTag`<div style="font-size:10px;color:var(--pink);">Condition: ${window.Lit.unsafeHTML(condHtml)}</div>` : ''}
            </div>`;
            })}`, listEl);
        }

        const badge = document.getElementById('lib-trigger-count-badge');
        if (badge) {
            badge.textContent = triggers.length;
            badge.style.display = triggers.length > 0 ? '' : 'none';
        }
        if (triggers.length > 0) {
            listEl.style.display = 'block';
            const icon = document.getElementById('lib-trigger-toggle-icon');
            if (icon) icon.textContent = '▼';
        }
    }

    // --- AI: Improve Existing Item ---

    async improveWithAI() { return ItemLibraryAI.improveWithAI.call(this); }

    // --- AI Generation ---

    async generateWithAI() { return ItemLibraryAI.generateWithAI.call(this); }

    async previewPrompt() { return ItemLibraryAI.previewPrompt.call(this); }

    _sendPreviewPrompt() { return ItemLibraryAI.sendPreviewPrompt.call(this); }

    // --- Save/Delete ---

    async save() {
        let id = document.getElementById('lib-item-id')?.value.trim();
        const name = document.getElementById('lib-item-name')?.value.trim();
        if (!id && name) {
            // Auto-generate the id from the name: lowercase, spaces→underscores.
            id = name.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '') || 'item';
            // Case-insensitive uniqueness — append a suffix if it already exists.
            const existingLower = Object.keys(this.data).map(k => k.toLowerCase());
            let candidate = id;
            let n = 2;
            while (existingLower.includes(candidate.toLowerCase())) {
                candidate = `${id}_${n++}`;
            }
            id = candidate;
            document.getElementById('lib-item-id').value = id;
        }
        if (!id) { toastInfo('Item ID is required.'); return; }

        const tags = this._tagMs ? this._tagMs.getValue() : [];

        const triggersField = document.getElementById('lib-item-triggers');
        const triggers = triggersField ? JSON.parse(triggersField.value || '[]') : [];

        const contentsField = document.getElementById('lib-item-contents');
        const contents = contentsField ? JSON.parse(contentsField.value || '[]') : [];

        const defense = parseInt(document.getElementById('lib-item-defense')?.value) || 0;
        const damage = document.getElementById('lib-item-damage')?.value?.trim() || 0;
        const damageSkill = document.getElementById('lib-item-damage-skill')?.value || undefined;
        const damageType = document.getElementById('lib-item-damage-type')?.value || undefined;
        const stunChance = parseInt(document.getElementById('lib-item-stun-chance')?.value);
        const stunDuration = parseInt(document.getElementById('lib-item-stun-duration')?.value);
        const insulation = parseInt(document.getElementById('lib-item-insulation')?.value) || 0;
        const resistsStr = document.getElementById('lib-item-resistances')?.value || '';
        const resistances = {};
        resistsStr.split(',').forEach(pair => {
            const parts = pair.split(':').map(s => s.trim());
            if (parts.length === 2 && parts[0] && parts[1]) {
                const val = parseInt(parts[1]);
                if (!isNaN(val)) resistances[parts[0]] = val;
            }
        });

        const payload = {
            id,
            name: document.getElementById('lib-item-name')?.value.trim() || id,
            description: document.getElementById('lib-item-desc')?.value || '',
            actions: document.getElementById('lib-item-actions')?.value || 'examine,take,use',
            uses: parseInt(document.getElementById('lib-item-uses')?.value) || -1,
            weight: parseFloat(document.getElementById('lib-item-weight')?.value) || 0.1,
            current_state: document.getElementById('lib-item-state')?.value || 'normal',
            light_level: document.getElementById('lib-item-light-level')?.value || 'dim',
            equip_slots: (() => { const el = document.getElementById('lib-item-equip-slots'); return el ? Array.from(el.selectedOptions).map(o => o.value) : [] })(),
            defense,
            damage,
            damage_skill: damageSkill,
            damage_type: damageType,
            stun_chance: stunChance || undefined,
            stun_duration: stunDuration || undefined,
            insulation: insulation || undefined,
            resistances: Object.keys(resistances).length > 0 ? resistances : undefined,
            tags,
            triggers,
            contents,
            image: document.getElementById('lib-item-image')?.value || undefined
        };

        const res = await ApiClient.saveLibraryItem(payload);
        if (res.error) { toastError('Error: ' + res.error); return; }
        events.log(`Saved "${payload.name}" to library.`, 'system-msg');
        await this.refresh();
        this.selectedId = id;
        this.renderList(document.getElementById('item-lib-search')?.value || '');
        this.select(id);
    }

    async delete(id) {
        if (!id || !confirm(`Delete "${id}" from library?`)) return;
        const res = await ApiClient.deleteLibraryItem(id);
        if (res.error) { toastError('Error: ' + res.error); return; }
        events.log(`Deleted "${id}".`, 'system-msg');
        this.selectedId = null;
        await this.refresh();
        this.renderList(document.getElementById('item-lib-search')?.value || '');
        const deletedEditor = document.getElementById('item-lib-editor');
        window.Lit.render(itemLibraryHtmlTag`
            <div class="inspector-empty" style="min-height:200px;">
                <div class="inspector-empty-icon">📦</div>
                <p>Item deleted.</p>
            </div>`, deletedEditor);
    }

    // --- Placement ---

    _pickTarget(title) { return ItemLibraryPlacement.pickTarget.call(this, title); }

    async placeInRoom() { return ItemLibraryPlacement.placeInRoom.call(this); }

    async placeSelectedInRoom() { return ItemLibraryPlacement.placeSelectedInRoom.call(this); }

    // --- Save World Item to Library ---

    async saveWorldItem(nodeId) {
        const node = worldState.getNode(nodeId);
        if (!node || node.type !== 'item') {
            events.log('Cannot save: not an item node.', 'error-msg');
            return;
        }
        const props = node.properties || {};
        const name = node.name || 'Unnamed Item';
        const templateSelect = document.getElementById(`item-lib-template-${nodeId}`);
        const templateId = templateSelect ? templateSelect.value : '';
        // Library id comes from the node's BACKEND id (the unique identity),
        // not the display name. Strip a leading 'item_' prefix if present so it
        // matches the registry convention (brass_key, medicine_cabinet, ...).
        // An explicit template id always wins.
        const nodeBaseId = nodeId.replace(/^item_/i, '');
        const itemId = templateId || nodeBaseId.toLowerCase().replace(/[^a-z0-9_]+/g, '_');

        let actions = 'examine,take,use';
        if (Array.isArray(props.actions)) actions = props.actions.join(',');
        else if (typeof props.actions === 'string') actions = props.actions;

        const triggers = this._extractTriggersFromEdges(nodeId);

        const built = this._buildWorldItemPayload(nodeId);
        const worldPayload = built ? built.payload : {
            name,
            description: props.description || '',
            actions,
            uses: props.uses ?? -1,
            weight: props.weight ?? 0.1,
            current_state: props.current_state || 'normal',
            light_level: props.light_level || 'dim',
            defense: props.defense ?? 0,
            damage: props.damage ?? 0,
            damage_skill: props.damage_skill || undefined,
            damage_type: props.damage_type || undefined,
            insulation: props.insulation || 0,
            resistances: props.resistances || undefined,
            tags: props.tags || [],
            triggers,
            contents: props.contents || [],
            image: props.image || undefined
        };
        const nestedIds = built ? built.nested : [];

        // Ensure contained items are also present as standalone library entries
        // (box-of-cards: the cards exist both inside the box AND as their own item).
        await this._saveNestedChildren(nestedIds);

        const locked = props.locked_fields || [];

        const rebindTemplate = async (targetId) => {
            if (!templateId || !targetId) return;
            if (props.library_id === targetId) return;
            await ApiClient.updateNode(nodeId, { properties: { library_id: targetId } });
            worldState.fetch();
        };

        // Check for existing library entry
        let libEntry = {};
        try {
            const libData = await ApiClient.getLibraryType('items');
            if (libData[itemId]) libEntry = libData[itemId];
        } catch (e) { /* ignore */ }

        const hasExisting = Object.keys(libEntry).length > 0;

        if (!hasExisting) {
            // No conflict — save directly (still respect locked_fields)
            const payload = { id: itemId };
            for (const [key, val] of Object.entries(worldPayload)) {
                payload[key] = locked.includes(key) && libEntry[key] !== undefined ? libEntry[key] : val;
            }
            const res = await ApiClient.saveLibraryItem(payload);
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            await rebindTemplate(itemId);
            events.log(`Saved "${name}" to library.`, 'system-msg');
            return;
        }

        // Conflict — show DiffModal
        const sections = [
            { key: 'name', label: 'Name' },
            { key: 'description', label: 'Description' },
            { key: 'actions', label: 'Actions' },
            { key: 'uses', label: 'Uses' },
            { key: 'weight', label: 'Weight' },
            { key: 'current_state', label: 'State' },
            { key: 'defense', label: 'Defense' },
            { key: 'damage', label: 'Damage' },
            { key: 'insulation', label: 'Insulation' },
            { key: 'resistances', label: 'Resistances' },
            { key: 'tags', label: 'Tags' },
            { key: 'triggers', label: 'Triggers' },
            { key: 'contents', label: 'Contents' }
        ];

        const result = await DiffModal.show(libEntry, worldPayload, sections, {
            title: 'Save Item to Library',
            name
        });

        if (!result) return;

        if (result.action === 'update') {
            const merged = { ...libEntry, id: itemId };
            for (const key of result.sections) {
                if (locked.includes(key) && libEntry[key] !== undefined) {
                    merged[key] = libEntry[key];
                } else {
                    merged[key] = worldPayload[key];
                }
            }
            const res = await ApiClient.saveLibraryItem(merged);
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            await rebindTemplate(itemId);
            events.log(`Updated "${name}" in library.`, 'system-msg');
        } else if (result.action === 'duplicate') {
            const dupePayload = { id: result.id, name: result.name, ...worldPayload };
            const res = await ApiClient.saveLibraryItem(dupePayload);
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            await rebindTemplate(result.id);
            events.log(`Saved "${result.name}" as duplicate to library.`, 'system-msg');
        }
    }

    // --- Add All World Items to Library ---

    async syncAllWorldItems() {
        if (!worldState.graph?.nodes) {
            events.log('No graph data available.', 'error-msg');
            return;
        }
        await this.refresh();
        const existingById = new Map();
        const existingByName = new Map();
        for (const [libId, libItem] of Object.entries(this.data)) {
            existingById.set(libId.toLowerCase(), { id: libId, item: libItem });
            const n = (libItem.name || '').toLowerCase();
            if (n) existingByName.set(n, { id: libId, item: libItem });
        }

        let added = 0, updated = 0, skipped = 0, errors = 0;
        for (const [nodeId, node] of Object.entries(worldState.graph.nodes)) {
            if (node.type !== 'item') continue;
            const name = node.name || 'Unnamed';
            const id = name.toLowerCase().replace(/[^a-z0-9_]+/g, '_');
            const p = node.properties || {};

            let actions = 'examine,take,use';
            if (Array.isArray(p.actions)) actions = p.actions.join(',');
            else if (typeof p.actions === 'string') actions = p.actions;

            const triggers = this._extractTriggersFromEdges(nodeId);

            const childBuilt = this._buildWorldItemPayload(nodeId);
            const worldItem = childBuilt ? {
                id, name,
                ...childBuilt.payload
            } : {
                id, name,
                description: p.description || '',
                actions,
                uses: p.uses ?? -1,
                weight: p.weight ?? 0.1,
                current_state: p.current_state || 'normal',
                light_level: p.light_level || 'dim',
                defense: p.defense ?? 0,
                damage: p.damage ?? 0,
                damage_skill: p.damage_skill || undefined,
                damage_type: p.damage_type || undefined,
                insulation: p.insulation || undefined,
                resistances: p.resistances || undefined,
                tags: p.tags || [],
                triggers,
                contents: p.contents || [],
                image: p.image || undefined
            };
            if (childBuilt) await this._saveNestedChildren(childBuilt.nested);

            const match = existingById.get(id) || existingByName.get(name.toLowerCase());
            if (match) {
                const libItem = match.item;
                if (!this._itemsDiffer(worldItem, libItem)) {
                    skipped++;
                    continue;
                }
                const sections = [
                    { key: 'description', label: 'Description' },
                    { key: 'actions', label: 'Actions' },
                    { key: 'uses', label: 'Uses' },
                    { key: 'weight', label: 'Weight' },
                    { key: 'current_state', label: 'State' },
                    { key: 'defense', label: 'Defense' },
                    { key: 'damage', label: 'Damage' },
                    { key: 'insulation', label: 'Insulation' },
                    { key: 'resistances', label: 'Resistances' },
                    { key: 'tags', label: 'Tags' },
                    { key: 'triggers', label: 'Triggers' },
                    { key: 'contents', label: 'Contents' },
                    { key: 'image', label: 'Image' }
                ];
                const result = await DiffModal.show(libItem, worldItem, sections, {
                    title: 'Sync Item to Library',
                    name
                });
                if (!result) { skipped++; continue; }
                if (result.action === 'update') {
                    const merged = { ...libItem, id: match.id };
                    for (const key of result.sections) {
                        merged[key] = worldItem[key];
                    }
                    const res = await ApiClient.saveLibraryItem(merged);
                    if (!res.error) updated++;
                    else errors++;
                } else if (result.action === 'duplicate') {
                    const dupePayload = { id: result.id, name: result.name, ...worldItem };
                    const res = await ApiClient.saveLibraryItem(dupePayload);
                    if (!res.error) added++;
                    else errors++;
                }
            } else {
                const res = await ApiClient.saveLibraryItem(worldItem);
                if (!res.error) { added++; }
                else errors++;
            }
        }
        let msg = `Synced ${added} added, ${updated} updated to library`;
        if (skipped > 0) msg += ` (${skipped} unchanged)`;
        if (errors > 0) msg += `, ${errors} errors`;
        events.log(msg, 'system-msg');

        if (document.getElementById('library-modal')?.style.display !== 'none') {
            await this.refresh();
            this.renderList(document.getElementById('item-lib-search')?.value || '');
        }
    }

    _extractTriggersFromEdges(nodeId) {
        const triggers = [];
        if (!worldState.graph?.edges) return triggers;
        for (const edge of worldState.graph.edges) {
            if (edge.source !== nodeId || edge.type !== 'triggers') continue;
            const edgeProperties = edge.properties || {};
            // Support both new format (effects array) and old format (effect_type + effect_params)
            const effects = edgeProperties.effects?.length > 0
                ? edgeProperties.effects
                : (edgeProperties.effect_type
                    ? [{ type: edgeProperties.effect_type, params: edgeProperties.effect_params || {} }]
                    : []);
            // Support both tree format and flat format conditions
            let conditions = edgeProperties.conditions || {};
            if (Array.isArray(conditions) || !conditions.operator) {
                const logic = edgeProperties.conditions_logic || 'and';
                if (Array.isArray(conditions) && conditions.length > 0) {
                    conditions = { operator: logic, conditions };
                } else {
                    conditions = {};
                }
            }
            triggers.push({
                trigger_type: edgeProperties.trigger_type || 'on_examine',
                effects: effects,
                target_name: edgeProperties.target_name || '',
                target_state: edgeProperties.target_state || '',
                conditions: conditions,
                success_message: edgeProperties.success_message || '',
                fail_message: edgeProperties.fail_message || ''
            });
        }
        return triggers;
    }

    /**
     * Build a canonical world→library payload for an item node, recursively
     * embedding full definitions of contained items (box-of-cards case).
     * Also returns the set of nested child nodeIds so callers can offer them
     * as standalone sync targets.
     * @returns {{payload: object, nested: string[]}}
     */
    _buildWorldItemPayload(nodeId, depth = 0, seen = null) {
        const node = worldState.getNode(nodeId);
        if (!node || node.type !== 'item') return null;
        seen = seen ? new Set(seen) : new Set();
        if (seen.has(nodeId) || depth > 8) return null;
        seen.add(nodeId);

        const props = node.properties || {};
        const name = node.name || 'Unnamed Item';
        let actions = 'examine,take,use';
        if (Array.isArray(props.actions)) actions = props.actions.join(',');
        else if (typeof props.actions === 'string') actions = props.actions;

        const nested = [];
        const contents = [];
        // Containment is canonical in the graph as `in` edges (source -in-> this).
        // We save the container's contents as library item-id REFS (graph-aligned),
        // resolving each child node back to its library_id. fall back to
        // props.contents for nodes whose contents were authored inline.
        const allEdges = worldState.graph?.edges || [];
        const edgeChildren = allEdges
            .filter(e => e.target === nodeId && e.type === 'in')
            .map(e => e.source)
            .filter(id => id && id !== nodeId);
        const contentRefs = edgeChildren.length > 0 ? edgeChildren : (props.contents || []);
        for (const c of contentRefs) {
            const childId = typeof c === 'string' ? c : (c.id || c.node_id || '');
            if (!childId) { contents.push(c); continue; }
            const childNode = worldState.getNode(childId);
            if (childNode && childNode.type === 'item' && !seen.has(childId)) {
                const childLibId = childNode.properties?.library_id || ItemLibrary._slug(childNode.name);
                contents.push(childLibId);
                nested.push(childId);
            } else {
                contents.push(c);
            }
        }

        const payload = {
            name,
            description: props.description || '',
            actions,
            uses: props.uses ?? -1,
            weight: props.weight ?? 0.1,
            current_state: props.current_state || 'normal',
            light_level: props.light_level || 'dim',
            defense: props.defense ?? 0,
            damage: props.damage ?? 0,
            damage_skill: props.damage_skill ?? undefined,
            damage_type: props.damage_type ?? undefined,
            insulation: props.insulation || 0,
            resistances: props.resistances ?? undefined,
            tags: props.tags || [],
            triggers: this._extractTriggersFromEdges(nodeId),
            contents,
            image: props.image ?? undefined
        };
        return { payload, nested: Array.from(new Set(nested)) };
    }

    /**
     * Ensure contained item graph nodes exist as their own standalone library
     * entries (recursively), so a box of cards yields both the box AND the cards.
     * @param {string[]} nestedIds - child item node ids from _buildWorldItemPayload
     */
    async _saveNestedChildren(nestedIds) {
        if (!nestedIds || nestedIds.length === 0) return;
        let libData = {};
        try { libData = await ApiClient.getLibraryType('items'); } catch (e) { /* ignore */ }
        for (const childId of nestedIds) {
            const childNode = worldState.getNode(childId);
            if (!childNode || childNode.type !== 'item') continue;
            const name = childNode.name || childId;
            const childItemId = name.toLowerCase().replace(/[^a-z0-9_]+/g, '_');
            if (libData[childItemId] || libData[childId]) continue; // already in library
            const childBuilt = this._buildWorldItemPayload(childId);
            if (!childBuilt) continue;
            await this._saveNestedChildren(childBuilt.nested);
            const entry = { id: childItemId, name, ...childBuilt.payload };
            const res = await ApiClient.saveLibraryItem(entry);
            if (!res.error) {
                events.log(`Saved contained item "${name}" to library.`, 'system-msg');
            }
        }
    }

    _itemsDiffer(worldItem, libItem) {
        const keys = ['description', 'actions', 'uses', 'weight', 'current_state', 'defense', 'damage', 'damage_skill', 'damage_type'];
        for (const k of keys) {
            if (String(worldItem[k] ?? '') !== String(libItem[k] ?? '')) return true;
        }
        const wt = (worldItem.tags || []).sort().join(',');
        const lt = (libItem.tags || []).sort().join(',');
        if (wt !== lt) return true;
        const normalizeTrigger = (t) => {
            const effects = t.effects || [];
            const conds = t.conditions || {};
            return { trigger_type: t.trigger_type, effects, success_message: t.success_message || '', fail_message: t.fail_message || '', target_name: t.target_name || '', conditions: conds };
        };
        const wt2 = JSON.stringify((worldItem.triggers || []).map(normalizeTrigger));
        const lt2 = JSON.stringify((libItem.triggers || []).map(normalizeTrigger));
        if (wt2 !== lt2) return true;
        if ((worldItem.insulation || 0) !== (libItem.insulation || 0)) return true;
        const wres = JSON.stringify(worldItem.resistances || {});
        const lres = JSON.stringify(libItem.resistances || {});
        if (wres !== lres) return true;
        if ((worldItem.image || '') !== (libItem.image || '')) return true;
        return false;
    }
}

const itemLib = new ItemLibrary();
