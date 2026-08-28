/**
 * LibraryBrowser — Unified library browser for all entity types
 *
 * Provides tabbed browsing of Items, Characters, Rooms, Traits,
 * Conditions, and Behaviours with list + editor for each type.
 *
 * Items tab delegates to the existing ItemLibrary class.
 * Other tabs use inline editors defined here.
 */

// Lazy tag: classic scripts parse before the deferred lit-bootstrap module
// runs, so window.Lit only exists when a view actually renders.
const libraryBrowserHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
// Search helpers (keyword + tag + fuzzy) for the library browser.
function wordBoundary(text, token) {
    if (!text || !token) return false;
    var re = new RegExp("(^|\\W)" + token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "($|\\W)");
    return re.test(text);
}

function fuzzyRatio(a, b) {
    if (!a || !b) return 0;
    // Levenshtein distance -> 1 - dist/maxLen, so close spellings rank.
    var m = a.length, n = b.length;
    if (m === 0) return n === 0 ? 1 : 0;
    if (n === 0) return 0;
    var dp = [];
    for (var i = 0; i <= m; i++) { dp[i] = [i]; }
    for (var j = 0; j <= n; j++) { dp[0][j] = j; }
    for (var i2 = 1; i2 <= m; i2++) {
        for (var j2 = 1; j2 <= n; j2++) {
            var cost = a[i2 - 1] === b[j2 - 1] ? 0 : 1;
            dp[i2][j2] = Math.min(dp[i2 - 1][j2] + 1, dp[i2][j2 - 1] + 1, dp[i2 - 1][j2 - 1] + cost);
        }
    }
    return 1 - dp[m][n] / Math.max(m, n);
}


class LibraryBrowser {
    constructor() {
        this.currentTab = 'items';
        this.data = {
            items: {},
            characters: {},
            areas: {},
            traits: {},
            conditions: {},
            behaviours: {},
            tags: {},
            ways: {}
        };
        this.selectedId = { items: null, characters: null, areas: null, traits: null, conditions: null, behaviours: null, tags: null, ways: null };
        this._editingNew = { characters: false, areas: false, traits: false, conditions: false, behaviours: false, tags: false, ways: false };
        this._tagMS = null;
    }

    // ── Open / Close / Tab Switching ─────────────────────────────────

    async open(initialTab) {
        await this.refreshAll();
        itemLib.data = this.data.items;
        if (initialTab && initialTab !== 'items') {
            this.switchTab(initialTab);
        } else {
            this.switchTab('items');
        }
        document.getElementById('library-modal').style.display = 'flex';
    }

    close() {
        document.getElementById('library-modal').style.display = 'none';
        this.currentTab = 'items';
    }

    switchTab(tab) {
        this.currentTab = tab;
        document.querySelectorAll('.lib-tab').forEach(el => el.classList.toggle('selected', el.dataset.tab === tab));
        document.querySelectorAll('.lib-tab-pane').forEach(el => el.classList.toggle('active', el.id === `lib-pane-${tab}`));

        if (tab === 'items') {
            itemLib.open();
        } else {
            this.renderList(tab);
            this._showEditorEmpty(tab);
        }
    }

    async refreshAll() {
        const types = ['items', 'characters', 'areas', 'ways', 'traits', 'conditions', 'behaviours', 'tags'];
        const results = await Promise.all(types.map(t =>
            ApiClient.getLibraryType(t).catch(() => ({}))
        ));
        types.forEach((t, i) => { this.data[t] = results[i]; });
    }

    async refreshType(type) {
        try {
            this.data[type] = await ApiClient.getLibraryType(type);
        } catch (e) {
            this.data[type] = {};
        }
    }

    // ── Filter / Search ──────────────────────────────────────────────

    filterList(type) {
        this.renderList(type);
    }

    // ── Generic List Rendering ───────────────────────────────────────

    renderList(type) {
        const idMap = {
            items: 'item-lib-list', characters: 'lib-char-list', areas: 'lib-area-list',
            traits: 'lib-trait-list', conditions: 'lib-cond-list', behaviours: 'lib-beh-list',
            tags: 'lib-tag-list', ways: 'lib-way-list'
        };
        const countMap = {
            items: 'lib-item-count', characters: 'lib-char-count', areas: 'lib-area-count',
            traits: 'lib-trait-count', conditions: 'lib-cond-count', behaviours: 'lib-beh-count',
            tags: 'lib-tag-count', ways: 'lib-way-count'
        };
        const searchMap = {
            items: 'item-lib-search', characters: 'lib-char-search', areas: 'lib-area-search',
            traits: 'lib-trait-search', conditions: 'lib-cond-search', behaviours: 'lib-beh-search',
            tags: 'lib-tag-search', ways: 'lib-way-search'
        };

        const listEl = document.getElementById(idMap[type]);
        const countEl = document.getElementById(countMap[type]);
        const searchEl = document.getElementById(searchMap[type]);
        if (!listEl) return;

        const filter = (searchEl?.value || '').trim().toLowerCase();
        const entries = Object.entries(this.data[type] || {});
        let filtered = entries;
        if (filter) {
            // Multi-strategy: keyword (name/desc), tags, and fuzzy name match,
            // ranked so the best hits float to the top instead of a plain
            // substring include.
            const tokens = filter.split(/\s+/).filter(Boolean);
            const scored = entries.map(([id, entry]) => {
                const name = String(entry.name || id || '').toLowerCase();
                const desc = String(entry.description || '').toLowerCase();
                const tags = (Array.isArray(entry.tags) ? entry.tags : []).map(t => String(t).toLowerCase());
                let s = 0;
                if (name.includes(filter)) s += 6;
                else if (desc.includes(filter)) s += 3;
                tokens.forEach(t => {
                    if (wordBoundary(name, t)) s += 3;
                    else if (wordBoundary(desc, t)) s += 1;
                    if (tags.some(tag => tag.includes(t))) s += 4;
                });
                const fr = fuzzyRatio(name, filter);
                if (s === 0 && fr >= 0.6) s += Math.round(fr * 6);
                return { id, entry, s };
            }).filter(x => x.s > 0).sort((a, b) => b.s - a.s || (a.entry.name || a.id).localeCompare(b.entry.name || b.id));
            filtered = scored.map(x => [x.id, x.entry]);
        } else {
            filtered = entries.sort((a, b) => (a[1].name || a[0]).localeCompare(b[1].name || b[0]));
        }

        const selected = this.selectedId[type];
        countEl.textContent = filtered.length === entries.length
            ? `${entries.length} entr${entries.length !== 1 ? 'ies' : 'y'}`
            : `${filtered.length} / ${entries.length}`;

        if (filtered.length === 0) {
            window.Lit.render(libraryBrowserHtmlTag`<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">No ${type} found.</div>`, listEl);
            return;
        }

        const typeIcons = { items: '📦', characters: '🧍', areas: '🏠', ways: '🚪', traits: '🏷️', conditions: '💊', behaviours: '🤖', tags: '🏷️' };
        const icon = typeIcons[type] || '📄';

        const rows = filtered.map(([id, entry]) => {
            const sel = id === selected;
            const name = entry.name || id;
            const desc = entry.description || '';
            const itemClass = 'agent-item' + (sel ? ' selected' : '');
            const itemStyle = `cursor:pointer;padding:5px 10px;border-left:3px solid var(--accent);${sel ? 'background:var(--bg-inset);' : ''}`;
            return libraryBrowserHtmlTag`
                <div class=${itemClass} @click=${() => VW.libraryBrowser.selectEntry(type, id)} style=${itemStyle}>
                    <span style="font-size:14px;margin-right:4px;">${icon}</span>
                    <div style="flex:1;min-width:0;">
                        <div class="agent-name" style="font-size:12px;font-weight:600;">${name}</div>
                        <div style="font-size:10px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${desc}</div>
                    </div>
                </div>`;
        });
        window.Lit.render(libraryBrowserHtmlTag`${rows}`, listEl);
    }

    // ── New Entry ────────────────────────────────────────────────────

    newEntry(type) {
        this.selectedId[type] = '__new__';
        this._editingNew[type] = true;
        this.renderList(type);
        const editors = this._getEditorConfigs();
        const config = editors[type];
        if (config) {
            const defaults = {};
            config.fields.forEach(f => { defaults[f.key] = f.default !== undefined ? f.default : ''; });
            this._renderEditor(type, defaults, true);
        }
    }

    // ── Select Entry ─────────────────────────────────────────────────

    selectEntry(type, id) {
        this.selectedId[type] = id;
        this._editingNew[type] = false;
        this.renderList(type);
        const entry = this.data[type]?.[id];
        if (entry) {
            this._renderEditor(type, entry, false);
        } else {
            this._showEditorEmpty(type);
        }
    }

    // ── Editor Configurations ────────────────────────────────────────

    _getEditorConfigs() {
        return {
            characters: {
                fields: [
                    { key: 'name', label: 'Name', type: 'text', default: '' },
                    { key: 'personality', label: 'Personality', type: 'textarea', default: '' },
                    { key: 'description', label: 'Description', type: 'textarea', default: '' },
                    { key: 'current_area', label: 'Default Area', type: 'text', default: '' },
                    { key: 'behaviors', label: 'Behaviours (JSON array)', type: 'textarea', default: '[]' },
                    { key: 'tags', label: 'Tags', type: 'tagmultiselect', default: [] },
                    { key: 'npc_behavior', label: 'NPC Behavior', type: 'select', options: ['wander', 'still', 'patrol', 'flee', 'guard'], default: 'wander' },
                    { key: 'simple_npc', label: 'Simple NPC', type: 'checkbox', default: false },
                ]
            },
            areas: {
                fields: [
                    { key: 'name', label: 'Name', type: 'text', default: '' },
                    { key: 'description', label: 'Description', type: 'textarea', default: '' },
                    { key: 'tags', label: 'Tags', type: 'tagmultiselect', default: [] },
                    { key: 'items', label: 'Item IDs (comma-separated)', type: 'text', default: '' },
                ]
            },
            traits: {
                fields: [
                    { key: 'name', label: 'Name', type: 'text', default: '' },
                    { key: 'description', label: 'Description', type: 'textarea', default: '' },
                    { key: 'category', label: 'Category', type: 'select', options: ['physical', 'mental', 'social', 'combat', 'exploration', 'custom'], default: 'custom' },
                    { key: 'effects', label: 'Effects (JSON)', type: 'textarea', default: '{}' },
                    { key: 'grants_conditions', label: 'Grants Conditions (JSON)', type: 'textarea', default: '[]' },
                    { key: 'conflicts', label: 'Conflicts (comma-separated)', type: 'text', default: '' },
                    { key: 'behavior_prompt', label: 'Behavior Prompt', type: 'textarea', default: '' },
                ]
            },
            conditions: {
                fields: [
                    { key: 'name', label: 'Name', type: 'text', default: '' },
                    { key: 'description', label: 'Description', type: 'textarea', default: '' },
                    { key: 'duration', label: 'Duration (ticks)', type: 'number', default: 5 },
                    { key: 'severity', label: 'Severity (1-5)', type: 'number', default: 1 },
                    { key: 'effects', label: 'Stat Effects (JSON)', type: 'textarea', default: '{}' },
                ]
            },
            behaviours: {
                fields: [
                    { key: 'name', label: 'Name', type: 'text', default: '' },
                    { key: 'description', label: 'Description', type: 'textarea', default: '' },
                    { key: 'pattern', label: 'Pattern', type: 'select', options: ['wander', 'still', 'patrol', 'flee', 'guard', 'follow', 'flee_from', 'investigate'], default: 'wander' },
                    { key: 'config', label: 'Config (JSON)', type: 'textarea', default: '{}' },
                ]
            },
            ways: {
                sections: [
                    { key: 'name', label: 'Name' },
                    { key: 'description', label: 'Description' },
                    { key: 'current_state', label: 'State' },
                    { key: 'pass_message', label: 'Pass Message' },
                    { key: 'requires', label: 'Requires' },
                    { key: 'max_size', label: 'Max Size' },
                    { key: 'jump_dc', label: 'Jump DC' },
                    { key: 'climb_dc', label: 'Climb DC' },
                    { key: 'auto_close', label: 'Auto Close' },
                    { key: 'see_through', label: 'See Through' },
                    { key: 'one_way', label: 'One Way' },
                    { key: 'prevent_close', label: 'Prevent Closing' },
                    { key: 'edge_length', label: 'Edge Length' },
                    { key: 'needs_open', label: 'Needs Open' },
                    { key: 'parameters', label: 'Parameters' },
                    { key: 'triggers', label: 'Triggers' },
                    { key: 'tags', label: 'Tags' },
                ],
                fields: [
                    { key: 'name', label: 'Name', type: 'text', default: '' },
                    { key: 'description', label: 'Description', type: 'textarea', default: '' },
                    { key: 'current_state', label: 'Default State', type: 'select', options: ['open', 'closed', 'locked', 'blocked', 'broken', 'hidden'], default: 'closed' },
                    { key: 'pass_message', label: 'On Traverse Narration', type: 'textarea', default: '' },
                    { key: 'requires', label: 'Required Movement Verb', type: 'select', options: ['', 'crawl', 'climb', 'jump'], default: '' },
                    { key: 'max_size', label: 'Max Size Through', type: 'select', options: ['', 'tiny', 'small', 'normal', 'huge', 'giant', 'titanic'], default: '' },
                    { key: 'jump_dc', label: 'Jump DC', type: 'number', default: 12 },
                    { key: 'climb_dc', label: 'Climb DC', type: 'number', default: 12 },
                    { key: 'auto_close', label: 'Auto-close', type: 'checkbox', default: false },
                    { key: 'see_through', label: 'See-through', type: 'checkbox', default: false },
                    { key: 'one_way', label: 'One-way', type: 'checkbox', default: false },
                    { key: 'prevent_close', label: 'Prevent Closing', type: 'checkbox', default: false },
                    { key: 'edge_length', label: 'Edge Length (20-500)', type: 'number', default: '' },
                    { key: 'needs_open', label: 'Needs Open (JSON)', type: 'json', default: {} },
                    { key: 'parameters', label: 'Parameters (JSON)', type: 'json', default: {} },
                    { key: 'triggers', label: 'Triggers (JSON)', type: 'json', default: [] },
                    { key: 'tags', label: 'Tags', type: 'tagmultiselect', default: [] },
                ]
            },
            tags: {
                fields: [
                    { key: 'name', label: 'Name', type: 'text', default: '' },
                    { key: 'description', label: 'Description', type: 'textarea', default: '' },
                    { key: 'category', label: 'Category', type: 'select', options: ['physical', 'essence', 'environment', 'faction', 'state', 'character', 'custom'], default: 'custom' },
                    { key: 'color', label: 'Color (hex)', type: 'text', default: '#888888' },
                    { key: 'icon', label: 'Icon (emoji)', type: 'text', default: '🏷️' },
                    { key: 'applies_to', label: 'Applies To (comma-separated)', type: 'text', default: 'items' },
                    { key: 'examples', label: 'Examples (comma-separated)', type: 'text', default: '' },
                ]
            }
        };
    }

    // ── Render Editor ────────────────────────────────────────────────

    _renderEditor(type, data, isNew) {
        const editorId = {
            characters: 'lib-char-editor', areas: 'lib-area-editor',
            traits: 'lib-trait-editor', conditions: 'lib-cond-editor',
            behaviours: 'lib-beh-editor', tags: 'lib-tag-editor',
            ways: 'lib-way-editor'
        }[type];
        const editor = document.getElementById(editorId);
        if (!editor) return;

        const configs = this._getEditorConfigs();
        const config = configs[type];
        if (!config) return;

        const typeIcons = { items: '📦', characters: '🧍', areas: '🏠', ways: '🚪', traits: '🏷️', conditions: '💊', behaviours: '🤖', tags: '🏷️' };
        const icon = typeIcons[type] || '📄';

        const fieldsHtml = config.fields.map(f => {
            const val = data[f.key] !== undefined ? data[f.key] : f.default;
            if (f.type === 'textarea') {
                return libraryBrowserHtmlTag`<div class="field"><label style="font-size:10px;">${f.label}</label><textarea id="lib-ed-${f.key}" rows="3" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);padding:4px 8px;font-size:11px;font-family:inherit;resize:vertical;">${val}</textarea></div>`;
            } else if (f.type === 'json') {
                const jsonVal = typeof val === 'string' ? val : JSON.stringify(val ?? f.default, null, 2);
                return libraryBrowserHtmlTag`<div class="field"><label style="font-size:10px;">${f.label}</label><textarea id="lib-ed-${f.key}" rows="3" spellcheck="false" style="width:100%;font-family:monospace;font-size:10px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);padding:4px 8px;resize:vertical;">${jsonVal}</textarea></div>`;
            } else if (f.type === 'select') {
                let opts = (f.options || []).slice();
                if (type === 'tags' && f.key === 'category' && this.data?.tags) {
                    const seen = new Set(opts);
                    for (const t of Object.values(this.data.tags)) {
                        if (t?.category && !seen.has(t.category)) { seen.add(t.category); opts.push(t.category); }
                    }
                    opts.sort((a, b) => a.localeCompare(b));
                }
                const optRows = opts.map(o => libraryBrowserHtmlTag`<option value=${o} ?selected=${val === o}>${o}</option>`);
                return libraryBrowserHtmlTag`<div class="field"><label style="font-size:10px;">${f.label}</label><select id="lib-ed-${f.key}" style="width:100%;font-size:11px;">${optRows}</select></div>`;
            } else if (f.type === 'checkbox') {
                return libraryBrowserHtmlTag`<label style="display:flex;align-items:center;gap:6px;font-size:11px;margin-top:4px;"><input type="checkbox" id="lib-ed-${f.key}" ?checked=${!!val}> ${f.label}</label>`;
            } else if (f.type === 'number') {
                return libraryBrowserHtmlTag`<div class="field"><label style="font-size:10px;">${f.label}</label><input type="number" id="lib-ed-${f.key}" .value=${val} style="width:100%;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);padding:4px 8px;"></div>`;
            } else if (f.type === 'tagmultiselect') {
                return libraryBrowserHtmlTag`<div class="field"><label style="font-size:10px;">${f.label}</label><div id="lib-ed-${f.key}" style="position:relative;"></div></div>`;
            } else {
                return libraryBrowserHtmlTag`<div class="field"><label style="font-size:10px;">${f.label}</label><input type="text" id="lib-ed-${f.key}" .value=${val} style="width:100%;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);padding:4px 8px;"></div>`;
            }
        });

        const id = this.selectedId[type] || '__new__';
        const typeLabel = type.charAt(0).toUpperCase() + type.slice(1);
        const heading = isNew ? `Create New ${typeLabel}` : `Edit ${typeLabel}`;
        const deleteButton = !isNew
            ? libraryBrowserHtmlTag`<button class="btn btn-sm btn-ghost" @click=${() => VW.libraryBrowser.deleteEntry(type)} style="font-size:11px;color:var(--red);">🗑️</button>`
            : window.Lit.nothing;
        window.Lit.render(libraryBrowserHtmlTag`
            <div class="inspector-section" style="padding:10px 16px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <h3 style="margin:0;font-size:13px;font-weight:700;">${icon} ${heading}</h3>
                    ${deleteButton}
                </div>
                <div class="field"><label style="font-size:10px;">ID (filename)</label><input type="text" id="lib-ed-id" .value=${isNew ? '' : id} placeholder="unique_id" style="width:100%;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);padding:4px 8px;">
                <div style="font-size:9px;color:var(--text-muted);">Use lowercase, no spaces. E.g. "brave_knight". Editing the ID of an existing entry renames it.</div></div>
                ${fieldsHtml}
            </div>`, editor);
        this._initTagMultiselect(type, data);
    }

    _initTagMultiselect(type, data) {
        if (type !== 'characters' && type !== 'areas' && type !== 'ways') return;
        const container = document.getElementById('lib-ed-tags');
        if (!container || typeof TagMultiselect === 'undefined') return;
        if (this._tagMS) { this._tagMS.destroy(); }
        const raw = data && data.tags !== undefined ? data.tags : [];
        const tagArray = Array.isArray(raw) ? raw :
            (typeof raw === 'string' && raw ? raw.split(',').map(s => s.trim()).filter(Boolean) : []);
        this._tagMS = new TagMultiselect(container, {
            tags: tagArray,
            appliesTo: type === 'characters' ? 'characters' : (type === 'ways' ? 'ways' : 'areas'),
            allowNew: true,
            placeholder: 'Search or create tags...'
        });
    }

    _showEditorEmpty(type) {
        const editorId = {
            characters: 'lib-char-editor', areas: 'lib-area-editor',
            traits: 'lib-trait-editor', conditions: 'lib-cond-editor',
            behaviours: 'lib-beh-editor', tags: 'lib-tag-editor',
            ways: 'lib-way-editor'
        }[type];
        const editor = document.getElementById(editorId);
        if (!editor) return;
        const icons = { characters: '🧍', areas: '🏠', ways: '🚪', traits: '🏷️', conditions: '💊', behaviours: '🤖', tags: '🏷️' };
        const labels = { characters: 'character', areas: 'area', ways: 'way', traits: 'trait', conditions: 'condition', behaviours: 'behaviour', tags: 'tag' };
        window.Lit.render(libraryBrowserHtmlTag`
            <div class="inspector-empty" style="min-height:200px;">
                <div class="inspector-empty-icon">${icons[type] || '📄'}</div>
                <p>Select or create a ${labels[type] || type}</p>
            </div>`, editor);
    }

    // ── Save Entry ───────────────────────────────────────────────────

    _buildSectionsForType(type) {
        const config = this._getEditorConfigs()[type];
        if (!config) return [];
        if (config.sections) return config.sections;
        return config.fields.map(f => ({ key: f.key, label: f.label }));
    }

    async saveEntry(type) {
        const id = (document.getElementById('lib-ed-id')?.value || '').trim();
        if (!id) { toastInfo('ID is required.'); return; }

        const configs = this._getEditorConfigs();
        const config = configs[type];
        if (!config) return;

        const payload = { id };
        for (const f of config.fields) {
            const el = document.getElementById(`lib-ed-${f.key}`);
            if (!el) continue;
            if (f.type === 'checkbox') {
                payload[f.key] = el.checked;
            } else if (f.type === 'number') {
                payload[f.key] = parseFloat(el.value) || f.default;
            } else if (f.type === 'json') {
                const raw = el.value.trim();
                if (!raw) { payload[f.key] = f.default; continue; }
                try {
                    payload[f.key] = JSON.parse(raw);
                } catch (e) {
                    toastError(`Invalid JSON in "${f.label}": ${e.message}`);
                    return;
                }
            } else if (f.type === 'tagmultiselect') {
                payload[f.key] = this._tagMS ? this._tagMS.getValue() : [];
            } else {
                payload[f.key] = el.value;
            }
        }
        // Convert comma-separated fields to arrays for tag format
        if (type === 'tags') {
            if (typeof payload.applies_to === 'string') payload.applies_to = payload.applies_to.split(',').map(s => s.trim()).filter(Boolean);
            if (typeof payload.examples === 'string') payload.examples = payload.examples.split(',').map(s => s.trim()).filter(Boolean);
        }

        const oldId = this.selectedId[type] && this.selectedId[type] !== '__new__' ? this.selectedId[type] : null;
        const renamed = oldId && oldId !== id;

        let libData = this.data[type] || {};
        try { libData = await ApiClient.getLibraryType(type); } catch (e) { /* ignore */ }

        const libEntry = (oldId && libData[oldId]) || libData[id] || null;

        if (!libEntry) {
            const res = await ApiClient.saveLibraryType(type, payload);
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Saved "${payload.name || id}" to library.`, 'system-msg');
            await this._finishSave(type, id);
            return;
        }

        const sections = this._buildSectionsForType(type);
        const result = await DiffModal.show(libEntry, payload, sections, {
            title: `Save ${type.charAt(0).toUpperCase() + type.slice(1)} to Library`,
            name: payload.name || id
        });
        if (!result) return;

        if (result.action === 'update') {
            // Merge only the selected sections onto the existing entry so
            // untouched fields (and fields outside the editor) are preserved.
            const merged = { ...libEntry, id };
            for (const key of result.sections) {
                merged[key] = payload[key];
            }
            const res = await ApiClient.saveLibraryType(type, merged);
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Updated "${merged.name || id}" in library.`, 'system-msg');
            if (renamed) {
                await ApiClient.deleteLibraryType(type, oldId);
                events.log(`Renamed "${oldId}" → "${id}".`, 'system-msg');
            }
        } else if (result.action === 'duplicate') {
            const dupePayload = { ...payload, id: result.id, name: result.name };
            const res = await ApiClient.saveLibraryType(type, dupePayload);
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Saved "${result.name}" as duplicate to library.`, 'system-msg');
        }

        await this._finishSave(type, id);
    }

    async _finishSave(type, id) {
        await this.refreshType(type);
        this.selectedId[type] = id;
        this.renderList(type);
        this.selectEntry(type, id);
    }

    async deleteEntry(type) {
        const id = this.selectedId[type];
        if (!id || id === '__new__' || !confirm(`Delete "${id}" from library?`)) return;
        const res = await ApiClient.deleteLibraryType(type, id);
        if (res.error) { toastError('Error: ' + res.error); return; }
        events.log(`Deleted "${id}".`, 'system-msg');
        this.selectedId[type] = null;
        await this.refreshType(type);
        this.renderList(type);
        this._showEditorEmpty(type);
    }

    // ── Import Character from Library ────────────────────────────────

    async importSelectedCharacter() {
        const id = this.selectedId.characters;
        if (!id || id === '__new__') { toastInfo('Select a character first.'); return; }
        const entry = this.data.characters[id];
        if (!entry) return;
        // Use the same target-picker modal that items use (Rooms/Containers/Characters tabs).
        const target = await ItemLibraryPlacement.pickTarget(`Place "${entry.name || id}" in:`, { tabs: ['area'] });
        if (!target) return;
        const area = target.type === 'area' ? target.name : target.id;

        const res = await ApiClient.importCharacterFromLibrary(id, { area, active: true });
        if (res.error) { toastError('Error: ' + res.error); return; }
        events.log(`Imported "${res.player}" into the world.`, 'system-msg');
        worldState.fetch();
    }

    // ── Import Area from Library ─────────────────────────────────────

    async importSelectedRoom() {
        const id = this.selectedId.areas;
        if (!id || id === '__new__') { toastInfo('Select an area first.'); return; }
        const entry = this.data.areas[id];
        if (!entry) return;
        const newName = prompt(`Import area as name?`, entry.name || id);
        if (!newName || newName === null) return;

        const res = await ApiClient.importRoomFromLibrary(id, { name: newName });
        if (res.error) { toastError('Error: ' + res.error); return; }
        events.log(`Imported area "${res.area}" into the world.`, 'system-msg');
        worldState.fetch();
    }

    // ── Import Way from Library ──────────────────────────────────────

    async importSelectedWay() {
        const id = this.selectedId.ways;
        if (!id || id === '__new__') { toastInfo('Select a way first.'); return; }
        const entry = this.data.ways[id];
        if (!entry) return;
        // Pick the two areas the way connects; directions default to 'out' unless
        // the library way is already connected to existing rooms in this world.
        const fromName = prompt(`Import way "${entry.name || id}".\nConnect FROM area name:`, '');
        if (!fromName || fromName === null) return;
        const toName = prompt(`Connect TO area name:`, '');
        if (!toName || toName === null) return;
        const dirFrom = prompt(`Direction FROM ${fromName} (e.g. east):`, 'out') || 'out';
        const dirTo = prompt(`Direction FROM ${toName} (e.g. west):`, 'out') || 'out';
        const res = await ApiClient.importWayFromLibrary(id, { area_from: fromName, area_to: toName, dir_from: dirFrom, dir_to: dirTo });
        if (res.error) { toastError('Error: ' + res.error); return; }
        events.log(`Imported way "${res.way}" into the world.`, 'system-msg');
        worldState.fetch();
    }

    // ── Save World Character to Library ──────────────────────────────

    _buildCharacterPayload(charName) {
        // Delegate to the canonical inspector builder so save/export/library
        // all produce the same shape (no data loss on any path).
        if (window.InspectorAgentView?._buildCharacterCard) {
            return InspectorAgentView._buildCharacterCard(charName);
        }
        const player = worldState.players[charName];
        if (!player) return null;
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
            equipped: player.equipped || {},
            activity: player.activity || null,
            current_area: player.current_area,
            inventory: worldState.getInventory?.(charName) || [],
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
    }

    /**
     * Merge a DiffModal result onto an existing library entry. Whole-section
     * selections replace the field outright; per-entry selections (result.entries)
     * carry over only the chosen memories/items/relationships/etc. onto the
     * existing value, preserving everything else.
     */
    _applyLibrarySelection(base, incoming, result) {
        const merged = { ...(base || {}), id: incoming.id || incoming.name || (base && base.id) };
        (result.sections || []).forEach((key) => {
            merged[key] = incoming[key];
        });
        if (result.entries) {
            for (const key of Object.keys(result.entries)) {
                if ((result.sections || []).includes(key)) continue;
                merged[key] = window.DiffModal.applyEntrySelection(merged[key], incoming[key], result.entries[key]);
            }
        }
        return merged;
    }

    async saveWorldToCharacter() {
        const players = Object.keys(worldState.players || {});
        if (players.length === 0) { toastInfo('No characters in the world.'); return; }
        const charName = prompt(`Save which character to library?\nAvailable: ${players.join(', ')}`, players[0]);
        if (!charName || !players.includes(charName)) return;

        const charCard = this._buildCharacterPayload(charName);
        if (!charCard) return;

        await this._saveCharacterWithDiffModal(charName, charCard);
    }

    /** Save a specific character to the library (no prompt). Used by WorldSync. */
    async saveCharacterByName(charName) {
        if (!charName) return;
        const charCard = this._buildCharacterPayload(charName);
        if (!charCard) { toastError(`Could not build library payload for character "${charName}".`); return; }
        await this._saveCharacterWithDiffModal(charName, charCard);
    }

    async _saveCharacterWithDiffModal(charName, charCard) {
        let libEntry = null;
        try {
            const libData = await ApiClient.getLibraryType('characters');
            libEntry = libData[charName] || null;
        } catch (e) { /* ignore */ }

        if (!libEntry) {
            const res = await ApiClient.saveLibraryType('characters', { id: charName, ...charCard });
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Character "${charName}" saved to library!`, 'system-msg');
            await this.refreshType('characters');
            this.selectedId.characters = charName;
            this.renderList('characters');
            this.selectEntry('characters', charName);
            return;
        }

        const sections = [
            { key: 'personality', label: 'Personality' },
            { key: 'description', label: 'Description' },
            { key: 'stats', label: 'Stats' },
            { key: 'skills', label: 'Skills' },
            { key: 'traits', label: 'Traits' },
            { key: 'tags', label: 'Tags' },
            { key: 'emotion', label: 'Emotion' },
            { key: 'vitals', label: 'Vitals', perEntry: true },
            { key: 'decay_rates', label: 'Decay Rates', perEntry: true },
            { key: 'conditions', label: 'Conditions', perEntry: true },
            { key: 'equipped', label: 'Equipped', perEntry: true },
            { key: 'relationships', label: 'Relationships', perEntry: true },
            { key: 'memories', label: 'Memories', perEntry: true },
            { key: 'behaviors', label: 'Behaviours' },
            { key: 'npc_behavior', label: 'NPC Config' },
            { key: 'inventory', label: 'Items', perEntry: true }
        ];

        const result = await DiffModal.show(libEntry, charCard, sections, {
            title: 'Save Character to Library',
            name: charName
        });
        if (!result) return;

        if (result.action === 'update') {
            const merged = this._applyLibrarySelection(libEntry, charCard, result);
            const res = await ApiClient.saveLibraryType('characters', merged);
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Character "${charName}" updated in library.`, 'system-msg');
        } else if (result.action === 'duplicate') {
            const dupePayload = { id: result.id, name: result.name, ...charCard };
            const res = await ApiClient.saveLibraryType('characters', dupePayload);
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Character "${result.name}" saved as duplicate to library.`, 'system-msg');
        }

        await this.refreshType('characters');
        this.selectedId.characters = charName;
        this.renderList('characters');
        this.selectEntry('characters', charName);
    }

    async syncAllWorldCharacters() {
        const players = Object.keys(worldState.players || {});
        if (players.length === 0) { toastInfo('No characters in the world.'); return; }

        await this.refreshType('characters');
        const libData = this.data.characters || {};

        let added = 0, updated = 0, skipped = 0, errors = 0;
        for (const charName of players) {
            const charCard = this._buildCharacterPayload(charName);
            if (!charCard) continue;

            const libEntry = libData[charName];
            if (!libEntry) {
                const res = await ApiClient.saveLibraryType('characters', { id: charName, ...charCard });
                if (!res.error) added++;
                else errors++;
                continue;
            }

            const sections = [
                { key: 'personality', label: 'Personality' },
                { key: 'description', label: 'Description' },
                { key: 'stats', label: 'Stats' },
                { key: 'skills', label: 'Skills' },
                { key: 'traits', label: 'Traits' },
                { key: 'tags', label: 'Tags' },
                { key: 'emotion', label: 'Emotion' },
                { key: 'vitals', label: 'Vitals', perEntry: true },
                { key: 'decay_rates', label: 'Decay Rates', perEntry: true },
                { key: 'conditions', label: 'Conditions', perEntry: true },
                { key: 'equipped', label: 'Equipped', perEntry: true },
                { key: 'relationships', label: 'Relationships', perEntry: true },
                { key: 'memories', label: 'Memories', perEntry: true },
                { key: 'behaviors', label: 'Behaviours' },
                { key: 'npc_behavior', label: 'NPC Config' },
                { key: 'inventory', label: 'Items', perEntry: true }
            ];

            const result = await DiffModal.show(libEntry, charCard, sections, {
                title: 'Sync Character to Library',
                name: charName
            });
            if (!result) { skipped++; continue; }

            if (result.action === 'update') {
                const merged = this._applyLibrarySelection(libEntry, charCard, result);
                const res = await ApiClient.saveLibraryType('characters', merged);
                if (!res.error) updated++;
                else errors++;
            } else if (result.action === 'duplicate') {
                const dupePayload = { id: result.id, name: result.name, ...charCard };
                const res = await ApiClient.saveLibraryType('characters', dupePayload);
                if (!res.error) added++;
                else errors++;
            }
        }

        let msg = `Character sync: ${added} added, ${updated} updated`;
        if (skipped > 0) msg += ` (${skipped} skipped)`;
        if (errors > 0) msg += `, ${errors} errors`;
        events.log(msg, 'system-msg');

        await this.refreshType('characters');
        this.renderList('characters');
    }

    _buildAreaPayload(areaName) {
        const areaData = worldState.areas?.[areaName];
        if (!areaData) return null;

        const graphNodes = worldState.graph?.nodes || {};
        const graphEdges = worldState.graph?.edges || [];
        const areaNodeId = `area_${areaName.toLowerCase().replace(/\s+/g, '_')}`;
        const graphNode = graphNodes[areaNodeId];
        const props = graphNode?.properties || {};
        const env = props.environment || areaData.environment || {};

        const items = [];
        for (const edge of graphEdges) {
            if (edge.target !== areaNodeId && edge.target !== areaName) continue;
            if (edge.type !== 'in') continue;
            const itemNode = graphNodes[edge.source];
            if (!itemNode || itemNode.type !== 'item') continue;
            const ip = itemNode.properties || {};
            items.push({
                name: itemNode.name,
                description: ip.description || '',
                actions: ip.actions || 'examine,take,use',
                uses: ip.uses ?? -1,
                weight: ip.weight ?? 0.1,
                current_state: ip.current_state || 'normal',
                tags: ip.tags || []
            });
        }

        const exits = [];
        const rawExits = areaData.exits || {};
        for (const [dir, exitData] of Object.entries(rawExits)) {
            const target = typeof exitData === 'object'
                ? (exitData.target || exitData.targetAreaName || exitData.targetAreaId || '')
                : exitData;
            exits.push({
                direction: dir,
                target_room_hint: target,
                description: exitData.description || '',
                state: exitData.state || 'closed',
                hidden: !!exitData.hidden,
                cardinal: exitData.cardinal || dir
            });
        }

        const triggers = [];
        for (const edge of graphEdges) {
            if (edge.source !== areaNodeId) continue;
            if (edge.type !== 'triggers') continue;
            const ep = edge.properties || {};
            const effects = ep.effects?.length > 0
                ? ep.effects
                : (ep.effect_type ? [{ type: ep.effect_type, params: ep.effect_params || {} }] : []);
            let conditions = ep.conditions || {};
            if (Array.isArray(conditions) || !conditions.operator) {
                const logic = ep.conditions_logic || 'and';
                if (Array.isArray(conditions) && conditions.length > 0) {
                    conditions = { operator: logic, conditions };
                } else {
                    conditions = {};
                }
            }
            triggers.push({
                trigger_type: ep.trigger_type || 'on_enter',
                effects,
                target_name: ep.target_name || '',
                target_state: ep.target_state || '',
                conditions,
                success_message: ep.success_message || '',
                fail_message: ep.fail_message || ''
            });
        }

        return {
            name: areaName,
            description: props.description || areaData.description || '',
            tags: props.tags || areaData.tags || [],
            environment: env,
            items,
            exits,
            triggers
        };
    }

    async saveWorldToArea() {
        const areaNames = Object.keys(worldState.areas || {});
        if (areaNames.length === 0) { toastInfo('No areas in the world.'); return; }
        const areaName = prompt(`Save which area to library?\nAvailable: ${areaNames.join(', ')}`, areaNames[0]);
        if (!areaName || !areaNames.includes(areaName)) return;

        const payload = this._buildAreaPayload(areaName);
        if (!payload) return;

        await this._saveAreaWithDiffModal(areaName, payload);
    }

    /**
     * Save a specific world area by name to the areas library (no prompt).
     * @param {string} areaName - Area name as shown in the graph/inspector.
     */
    async saveAreaByName(areaName) {
        if (!areaName) return;
        const payload = this._buildAreaPayload(areaName);
        if (!payload) { toastError(`Could not build library payload for area "${areaName}".`); return; }
        await this._saveAreaWithDiffModal(areaName, payload);
    }

    async _saveAreaWithDiffModal(areaName, areaPayload) {
        const areaId = areaName.toLowerCase().replace(/[^a-z0-9_]+/g, '_');
        let libEntry = null;
        try {
            const libData = await ApiClient.getLibraryType('areas');
            libEntry = libData[areaId] || null;
        } catch (e) { /* ignore */ }

        if (!libEntry) {
            const res = await ApiClient.saveLibraryType('areas', { id: areaId, ...areaPayload });
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Area "${areaName}" saved to library!`, 'system-msg');
            await this.refreshType('areas');
            this.selectedId.areas = areaId;
            this.renderList('areas');
            this.selectEntry('areas', areaId);
            return;
        }

        const sections = [
            { key: 'description', label: 'Description' },
            { key: 'tags', label: 'Tags' },
            { key: 'environment', label: 'Environment' },
            { key: 'items', label: 'Items' },
            { key: 'exits', label: 'Exits' },
            { key: 'triggers', label: 'Triggers' }
        ];

        const result = await DiffModal.show(libEntry, areaPayload, sections, {
            title: 'Save Area to Library',
            name: areaName
        });
        if (!result) return;

        if (result.action === 'update') {
            const merged = { ...libEntry, id: areaId };
            for (const key of result.sections) {
                merged[key] = areaPayload[key];
            }
            const res = await ApiClient.saveLibraryType('areas', merged);
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Area "${areaName}" updated in library.`, 'system-msg');
        } else if (result.action === 'duplicate') {
            const dupePayload = { id: result.id, name: result.name, ...areaPayload };
            const res = await ApiClient.saveLibraryType('areas', dupePayload);
            if (res.error) { toastError('Error: ' + res.error); return; }
            events.log(`Area "${result.name}" saved as duplicate to library.`, 'system-msg');
        }

        await this.refreshType('areas');
        this.selectedId.areas = areaId;
        this.renderList('areas');
        this.selectEntry('areas', areaId);
    }

    async syncAllWorldAreas() {
        const areaNames = Object.keys(worldState.areas || {});
        if (areaNames.length === 0) { toastInfo('No areas in the world.'); return; }

        await this.refreshType('areas');
        const libData = this.data.areas || {};

        let added = 0, updated = 0, skipped = 0, errors = 0;
        for (const areaName of areaNames) {
            const areaPayload = this._buildAreaPayload(areaName);
            if (!areaPayload) continue;

            const areaId = areaName.toLowerCase().replace(/[^a-z0-9_]+/g, '_');
            const libEntry = libData[areaId];
            if (!libEntry) {
                const res = await ApiClient.saveLibraryType('areas', { id: areaId, ...areaPayload });
                if (!res.error) added++;
                else errors++;
                continue;
            }

            const sections = [
                { key: 'description', label: 'Description' },
                { key: 'tags', label: 'Tags' },
                { key: 'environment', label: 'Environment' },
                { key: 'items', label: 'Items' },
                { key: 'exits', label: 'Exits' },
                { key: 'triggers', label: 'Triggers' }
            ];

            const result = await DiffModal.show(libEntry, areaPayload, sections, {
                title: 'Sync Area to Library',
                name: areaName
            });
            if (!result) { skipped++; continue; }

            if (result.action === 'update') {
                const merged = { ...libEntry, id: areaId };
                for (const key of result.sections) {
                    merged[key] = areaPayload[key];
                }
                const res = await ApiClient.saveLibraryType('areas', merged);
                if (!res.error) updated++;
                else errors++;
            } else if (result.action === 'duplicate') {
                const dupePayload = { id: result.id, name: result.name, ...areaPayload };
                const res = await ApiClient.saveLibraryType('areas', dupePayload);
                if (!res.error) added++;
                else errors++;
            }
        }

        let msg = `Area sync: ${added} added, ${updated} updated`;
        if (skipped > 0) msg += ` (${skipped} skipped)`;
        if (errors > 0) msg += `, ${errors} errors`;
        events.log(msg, 'system-msg');

        await this.refreshType('areas');
        this.renderList('areas');
    }
}

// Singleton
const libraryBrowser = new LibraryBrowser();
