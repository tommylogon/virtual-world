/**

 * LibraryBrowser — Unified library browser for all entity types

 *

 * Provides tabbed browsing of Items, Characters, Rooms, Traits,

 * Conditions, and Behaviours with list + editor for each type.

 *

 * Items tab delegates to the existing ItemLibrary class.

 * Other tabs use inline editors defined here.

 *

 * @module library-browser — the unified library browser

 * @contributes LibraryBrowser: tabbed Items/Characters/Rooms/Traits/Conditions/Behaviours browsing + editors, and the Vocabulary tab for compiler vocabularies (task-589)

 * @powers the 📚 Library modal (the Items tab delegates to ItemLibrary)

 * @relates uses api + storage; inline editors for the non-item tabs

 * @docs docs/virtualWorld/Library System/Library System Overview.md

 */

// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.



// Lazy tag: classic scripts parse before the deferred lit-bootstrap module

// runs, so window.Lit only exists when a view actually renders.

const libraryBrowserHtmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);

// Search helpers (keyword + tag + fuzzy) for the library browser.

function wordBoundary(text: string | null | undefined, token: string | null | undefined): boolean {

    if (!text || !token) return false;

    var re = new RegExp("(^|\\W)" + token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "($|\\W)");

    return re.test(text);

}



// Type declarations sit below the first value statement on purpose: TypeScript

// drops a file's leading JSDoc when the first statement is type-only, which

// would strip the `@module` header `tools/js_module_index.py` reads.



// `ApiClient` has no ambient declaration for the library endpoints, so they

// are reached through this one local alias rather than a cast at every call.

const LibraryApi = ApiClient as unknown as {

    getLibraryType(type: string): Promise<Record<string, LibraryEntry>>;

    saveLibraryType(type: string, payload: unknown): Promise<{ error?: string }>;

    deleteLibraryType(type: string, id: string): Promise<{ error?: string }>;

    listVocabulary(type: string): Promise<{ entries?: Array<{ id: string; name?: string; record?: unknown }>; error?: string }>;

    saveVocabulary(type: string, id: string, record: unknown): Promise<{ error?: string; problems?: string[] }>;

    deleteVocabulary(type: string, id: string): Promise<{ error?: string }>;

    importCharacterFromLibrary(id: string, opts: { area: string; active: boolean }): Promise<{ error?: string; player?: string }>;

    importRoomFromLibrary(id: string, opts: { name: string }): Promise<{ error?: string; area?: string }>;

    importWayFromLibrary(id: string, opts: { area_from: string; area_to: string; dir_from: string; dir_to: string }): Promise<{ error?: string; way?: string }>;

};



const DiffModalTyped = DiffModal as DiffModalStatic;



/**

 * The item-library singleton, resolved lazily. `itemLib` is a top-level

 * `const` in item-library.js — a global *lexical* binding, not a window

 * property — and the copy to `VW.itemLib` in main.js runs after this file

 * loads, so a load-time snapshot (`window.itemLib`) was always undefined and

 * every open() died on it with "itemLibRef is undefined".

 */

function itemLibRef(): { data: Record<string, LibraryEntry>; open(): void } | undefined {

    const w = window as unknown as { itemLib?: unknown; VW?: { itemLib?: unknown } };

    return (w.VW?.itemLib ?? w.itemLib) as { data: Record<string, LibraryEntry>; open(): void } | undefined;

}



// ItemLibraryPlacement is declared once in globals.d.ts, generated from

// item-library/placement.js. A local `const` alias here both redeclared it

// (TS2451) and gave item-library.ts a narrower type than the real API.



type LibraryTab = 'items' | 'characters' | 'areas' | 'ways' | 'traits' | 'conditions' | 'behaviours' | 'tags' | 'recipes' | 'pursuit_templates' | 'vocabulary';



interface LibraryEntry {

    id?: string;

    name?: string;

    description?: string;

    category?: string;

    tags?: unknown;

    [key: string]: unknown;

}



interface EditorField {

    key: string;

    label: string;

    type?: string;

    default?: unknown;

    options?: string[];

}



interface EditorSection {

    key: string;

    label: string;

    perEntry?: boolean;

}



interface EditorConfig {

    fields: EditorField[];

    sections?: EditorSection[];

}



interface DiffModalResult {

    action?: string;

    id?: string;

    name?: string;

    sections?: string[];

    entries?: Record<string, Record<string, boolean>>;

}



interface DiffModalStatic {

    show(base: unknown, incoming: unknown, sections: unknown, opts: { title: string; name: string }): Promise<DiffModalResult | null>;

    applyEntrySelection(existing: unknown, incoming: unknown, selection: unknown): unknown;

}



interface TagMultiselectInstance {

    destroy(): void;

    getValue(): string[];

}



const EDITOR_IDS: Record<string, string> = {

    characters: 'lib-char-editor', areas: 'lib-area-editor',

    traits: 'lib-trait-editor', conditions: 'lib-cond-editor',

    behaviours: 'lib-beh-editor', tags: 'lib-tag-editor',

    ways: 'lib-way-editor', recipes: 'lib-recipe-editor',

    pursuit_templates: 'lib-pursuit-editor',

};



function fuzzyRatio(a: string, b: string): number {

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

    // Declared here rather than inferred from the constructor so `strict` sees

    // the instance shape; the constructor below still assigns all of them.

    currentTab!: LibraryTab;

    data!: Record<LibraryTab, Record<string, LibraryEntry>>;

    selectedId!: Record<LibraryTab, string | null>;

    _editingNew!: Record<string, boolean>;

    _tagMS: TagMultiselectInstance | null;

    // Compiler vocabulary (task-589): biomes/features, browsed and edited here

    // but never materialized (no "place in world").

    _vocabType = 'biomes';

    _vocabEntries: Array<{ id: string; record: Record<string, unknown> }> = [];

    _vocabSelected: string | null = null;



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

            ways: {},

            recipes: {},

            pursuit_templates: {},

            vocabulary: {}

        };

        this.selectedId = { items: null, characters: null, areas: null, traits: null, conditions: null, behaviours: null, tags: null, ways: null, recipes: null, pursuit_templates: null, vocabulary: null };

        this._editingNew = { characters: false, areas: false, traits: false, conditions: false, behaviours: false, tags: false, ways: false, recipes: false, pursuit_templates: false };

        this._tagMS = null;

    }



    // ── Open / Close / Tab Switching ─────────────────────────────────



    async open(initialTab?: string) {

        await this.refreshAll();

        const lib = itemLibRef();

        if (lib) lib.data = this.data.items;

        if (initialTab && initialTab !== 'items') {

            this.switchTab(initialTab as LibraryTab);

        } else {

            this.switchTab('items');

        }

        (document.getElementById('library-modal') as HTMLElement).style.display = 'flex';

    }



    close() {

        (document.getElementById('library-modal') as HTMLElement).style.display = 'none';

        this.currentTab = 'items';

    }



    switchTab(tab: LibraryTab) {

        this.currentTab = tab;

        document.querySelectorAll('.lib-tab').forEach((el: Element) =>

            el.classList.toggle('selected', (el as HTMLElement).dataset.tab === tab));

        document.querySelectorAll('.lib-tab-pane').forEach(el => el.classList.toggle('active', el.id === `lib-pane-${tab}`));



        if (tab === 'items') {

            itemLibRef()?.open();

        } else if (tab === 'vocabulary') {

            this.loadVocabulary();

        } else {

            this.renderList(tab);

            this._showEditorEmpty(tab);

        }

    }



    // ── Compiler vocabulary (task-589) ───────────────────────────────

    // A biome/feature is read by the compiler and never materialized, so this

    // tab lists and edits them with no "place in world" action. It reads the

    // same `/api/vocabulary/...` the WorldPainter derives from — no second read

    // path, no second copy.



    async loadVocabulary(type?: string): Promise<void> {

        this._vocabType = String(type || 'biomes');

        const res = await LibraryApi.listVocabulary(this._vocabType).catch(() => ({ entries: [] as Array<{ id: string; record?: unknown }> }));

        this._vocabEntries = (res.entries || []).map(e => ({

            id: e.id,

            record: (e.record || {}) as Record<string, unknown>,

        }));

        this._vocabSelected = this._vocabEntries.length ? this._vocabEntries[0].id : null;

        this.renderVocabulary();

    }



    renderVocabulary(): void {

        const root = document.getElementById('lib-vocab-root');

        if (!root) return;

        root.textContent = '';

        const mk = <K extends keyof HTMLElementTagNameMap>(tag: K, text?: string, css?: string): HTMLElementTagNameMap[K] => {

            const el = document.createElement(tag);

            if (text != null) el.textContent = text;

            if (css) el.setAttribute('style', css);

            return el;

        };



        const bar = mk('div');

        bar.setAttribute('style', 'display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap;');

        bar.appendChild(mk('span', 'Vocabulary:', 'font-size:12px;color:var(--text-muted,#999);'));

        const typeSel = mk('select');

        typeSel.setAttribute('data-role', 'lib-vocab-type');

        typeSel.setAttribute('style', 'padding:3px;border-radius:5px;');

        ['biomes', 'features', 'resource_distribution', 'hostile_distribution', 'floor_plans', 'hazards'].forEach(v => {

            const o = mk('option', v);

            o.value = v;

            if (v === this._vocabType) o.selected = true;

            typeSel.appendChild(o);

        });

        typeSel.addEventListener('change', () => { void this.loadVocabulary(typeSel.value); });

        bar.appendChild(typeSel);

        const newBtn = mk('button', '➕ New');

        newBtn.setAttribute('style', 'cursor:pointer;padding:3px 8px;border-radius:5px;');

        newBtn.addEventListener('click', async () => {

            const promptRes = await (window as any).Dialog?.prompt?.({
                title: 'New Entry ID',
                fields: [{ key: 'id', label: 'ID (lowercase letters, digits, underscore)', placeholder: 'new_entry_id' }]
            });
            const id = promptRes?.id?.trim();

            if (!id) return;

            if (!/^[a-z0-9_]+$/.test(id)) { toastError('id must be lowercase letters, digits or underscore'); return; }

            const defaults: Record<string, Record<string, unknown>> = {

                biomes: { name: id, terrain: 'forest', tags: ['forest'], surface: 'grass', descriptions: [''] },

                features: { name: id, tags: ['road'], descriptions: [''] },

                resource_distribution: { id, name: id, biome_tags: [], location_tags: [], item_tags: [], weight: 1, conditions: {} },

                hostile_distribution: { id, name: id, biome_tags: [], location_tags: [], kind: 'predator', base_chance: 0.01, per_area_from_settlement: 0, max_chance: 0.1, conditions: {} },

                floor_plans: { label: id, storeys: 1, legend: { '=': 'wall', ' ': 'door' }, plan: ['=  =', '=  =', '===='] },

                hazards: { name: id, ability: 'STR', dc: { '1': 8, '10': 15, '20': 22 }, on_fail: { conditions: [], tags: [] }, message_success: '', message_fail: '' },

            };

            this._vocabEntries.push({ id, record: defaults[this._vocabType] || {} });

            this._vocabSelected = id;

            this.renderVocabulary();

        });

        bar.appendChild(newBtn);

        bar.appendChild(mk('span', 'Compiler vocabulary — no “place in world” action.',

            'font-size:11px;color:var(--text-muted,#999);margin-left:auto;'));

        root.appendChild(bar);



        const split = mk('div');

        split.setAttribute('style', 'display:flex;gap:10px;align-items:flex-start;');

        const list = mk('div');

        list.setAttribute('style', 'min-width:180px;max-height:60vh;overflow:auto;border:1px solid var(--border,#3a3a44);border-radius:6px;padding:2px;');

        this._vocabEntries.forEach(e => {

            const b = mk('button', e.id);

            b.setAttribute('data-role', 'lib-vocab-entry');

            b.setAttribute('data-id', e.id);

            b.setAttribute('style', 'display:block;width:100%;text-align:left;padding:4px 8px;font-size:12px;border:0;cursor:pointer;'

                + (e.id === this._vocabSelected ? 'background:#2d4a6b;color:#cfe;' : 'background:transparent;color:var(--text,#ddd);'));

            b.addEventListener('click', () => { this._vocabSelected = e.id; this.renderVocabulary(); });

            list.appendChild(b);

        });

        split.appendChild(list);



        const editor = mk('div');

        editor.setAttribute('style', 'flex:1;display:flex;flex-direction:column;gap:6px;');

        const cur = this._vocabEntries.find(e => e.id === this._vocabSelected);

        if (cur) {

            const ta = mk('textarea');

            ta.setAttribute('data-role', 'lib-vocab-json');

            ta.setAttribute('style', 'width:100%;min-width:360px;min-height:320px;font-family:monospace;font-size:12px;background:var(--bg-input,#1e1e24);color:var(--text,#ddd);border:1px solid var(--border,#444);border-radius:6px;padding:6px;');

            ta.value = JSON.stringify(cur.record, null, 2);

            editor.appendChild(ta);

            const row = mk('div');

            row.setAttribute('style', 'display:flex;gap:8px;');

            const save = mk('button', '💾 Save');

            save.setAttribute('data-role', 'lib-vocab-save');

            save.setAttribute('style', 'cursor:pointer;padding:4px 10px;border-radius:5px;');

            save.addEventListener('click', () => {

                let rec: unknown;

                try { rec = JSON.parse(ta.value); } catch (err) { toastError('Invalid JSON: ' + (err as Error).message); return; }

                void LibraryApi.saveVocabulary(this._vocabType, cur.id, rec).then(res => {

                    if (res && res.error) {

                        toastError('Save refused: ' + res.error + (res.problems?.length ? ' - ' + res.problems.join(', ') : ''));

                        return;

                    }

                    void this.loadVocabulary(this._vocabType);

                });

            });

            row.appendChild(save);

            const del = mk('button', '🗑️ Delete');

            del.setAttribute('data-role', 'lib-vocab-delete');

            del.setAttribute('style', 'cursor:pointer;padding:4px 10px;border-radius:5px;color:var(--red,#e66);');

            del.addEventListener('click', async () => {

                const ok = await (window as any).Dialog?.confirm?.({
                    title: `Delete ${this._vocabType}`,
                    message: `Delete ${this._vocabType} "${cur.id}"?`,
                    danger: true
                });
                if (!ok) return;

                void LibraryApi.deleteVocabulary(this._vocabType, cur.id).then(res => {

                    if (res && res.error) { toastError(res.error); return; }

                    void this.loadVocabulary(this._vocabType);

                });

            });

            row.appendChild(del);

            editor.appendChild(row);

        } else {

            editor.appendChild(mk('div', 'No entry selected.', 'color:var(--text-muted,#999);font-size:12px;'));

        }

        split.appendChild(editor);

        root.appendChild(split);

    }



    async refreshAll() {

        const types: LibraryTab[] = ['items', 'characters', 'areas', 'ways', 'traits', 'conditions', 'behaviours', 'tags', 'recipes', 'pursuit_templates'];

        const results = await Promise.all(types.map(t =>

            LibraryApi.getLibraryType(t).catch(() => ({}))

        ));

        types.forEach((t, i) => { this.data[t] = results[i]; });

    }



    async refreshType(type: LibraryTab) {

        try {

            this.data[type] = await LibraryApi.getLibraryType(type);

        } catch (e) {

            this.data[type] = {};

        }

    }



    // ── Filter / Search ──────────────────────────────────────────────



    filterList(type: LibraryTab) {

        this.renderList(type);

    }



    // ── Generic List Rendering ───────────────────────────────────────



    renderList(type: LibraryTab) {

        const idMap = {

            items: 'item-lib-list', characters: 'lib-char-list', areas: 'lib-area-list',

            traits: 'lib-trait-list', conditions: 'lib-cond-list', behaviours: 'lib-beh-list',

            tags: 'lib-tag-list', ways: 'lib-way-list', recipes: 'lib-recipe-list',

            pursuit_templates: 'lib-pursuit-list'

        };

        const countMap = {

            items: 'lib-item-count', characters: 'lib-char-count', areas: 'lib-area-count',

            traits: 'lib-trait-count', conditions: 'lib-cond-count', behaviours: 'lib-beh-count',

            tags: 'lib-tag-count', ways: 'lib-way-count', recipes: 'lib-recipe-count',

            pursuit_templates: 'lib-pursuit-count'

        };

        const searchMap = {

            items: 'item-lib-search', characters: 'lib-char-search', areas: 'lib-area-search',

            traits: 'lib-trait-search', conditions: 'lib-cond-search', behaviours: 'lib-beh-search',

            tags: 'lib-tag-search', ways: 'lib-way-search', recipes: 'lib-recipe-search',

            pursuit_templates: 'lib-pursuit-search'

        };



        const listEl = document.getElementById(idMap[type as keyof typeof idMap]);

        const countEl = document.getElementById(countMap[type as keyof typeof countMap]) as HTMLElement | null;

        const searchEl = document.getElementById(searchMap[type as keyof typeof searchMap]) as HTMLInputElement | null;

        if (!listEl || !countEl) return;



        const filter = (searchEl?.value || '').trim().toLowerCase();

        const entries = Object.entries(this.data[type] || {});

        let filtered = entries;

        if (filter) {

            // Multi-strategy: keyword (name/desc), tags, and fuzzy name match,

            // ranked so the best hits float to the top instead of a plain

            // substring include.

            const tokens = filter.split(/\s+/).filter(Boolean);

            const scored = entries.map(([id, entry]: [string, LibraryEntry]) => {

                const name = String(entry.name || id || '').toLowerCase();

                const desc = String(entry.description || '').toLowerCase();

                const tags = (Array.isArray(entry.tags) ? entry.tags : []).map((t: unknown) => String(t).toLowerCase());

                let s = 0;

                if (name.includes(filter)) s += 6;

                else if (desc.includes(filter)) s += 3;

                tokens.forEach((t: string) => {

                    if (wordBoundary(name, t)) s += 3;

                    else if (wordBoundary(desc, t)) s += 1;

                    if (tags.some((tag: string) => tag.includes(t))) s += 4;

                });

                const fr = fuzzyRatio(name, filter);

                if (s === 0 && fr >= 0.6) s += Math.round(fr * 6);

                return { id, entry, s };

            }).filter(x => x.s > 0).sort((a, b) => b.s - a.s || String(a.entry.name || a.id).localeCompare(String(b.entry.name || b.id)));

            filtered = scored.map(x => [x.id, x.entry]);

        } else {

            filtered = entries.sort((a: [string, LibraryEntry], b: [string, LibraryEntry]) =>

                String(a[1].name || a[0]).localeCompare(String(b[1].name || b[0])));

        }



        const selected = this.selectedId[type];

        countEl.textContent = filtered.length === entries.length

            ? `${entries.length} entr${entries.length !== 1 ? 'ies' : 'y'}`

            : `${filtered.length} / ${entries.length}`;



        if (filtered.length === 0) {

            window.Lit.render(libraryBrowserHtmlTag`<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">No ${type} found.</div>`, listEl);

            return;

        }



        const typeIcons: Record<string, string> = { items: '📦', characters: '🧍', areas: '🏠', ways: '🚪', traits: '🏷️', conditions: '💊', behaviours: '🤖', tags: '🏷️', recipes: '🧾', pursuit_templates: '🧭' };

        const icon = typeIcons[type] || '📄';



        const rows = filtered.map(([id, entry]: [string, LibraryEntry]) => {

            const sel = id === selected;

            const name = entry.name || id;

            const desc = entry.description || '';

            const itemClass = 'agent-item' + (sel ? ' selected' : '');

            const itemStyle = `cursor:pointer;padding:5px 10px;border-left:3px solid var(--accent);${sel ? 'background:var(--bg-inset);' : ''}`;

            // Task-842: recipe rows carry the outcome ladder (crit →

            // success → fail → crit-fail, fail items named) plus

            // inventory checkmarks per ingredient (✓ in library).

            const extra = type === 'recipes' ? this._recipeRowExtra(entry as unknown as Record<string, unknown>) : '';

            return libraryBrowserHtmlTag`

                <div class=${itemClass} @click=${() => (VW as unknown as { libraryBrowser: LibraryBrowser }).libraryBrowser.selectEntry(type, id)} style=${itemStyle}>

                    <span style="font-size:14px;margin-right:4px;">${icon}</span>

                    <div style="flex:1;min-width:0;">

                        <div class="agent-name" style="font-size:12px;font-weight:600;">${name}</div>

                        <div style="font-size:10px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${desc}</div>

                        ${extra}

                    </div>

                </div>`;

        });

        window.Lit.render(libraryBrowserHtmlTag`${rows}`, listEl);

    }



    // ── New Entry ────────────────────────────────────────────────────



    /**

     * Task-842: one-line outcome ladder + ingredient checkmarks for a

     * recipe row. Checkmarks read the loaded items registry (✓ known

     * id, ✗ missing) — browse-time signal only; the gate is authoritative.

     */

    _recipeRowExtra(entry: Record<string, unknown>): unknown {

        const items = (this.data && (this.data as Record<string, unknown>).items) || {};

        const known = new Set<string>();

        for (const [key, val] of Object.entries(items as Record<string, unknown>)) {

            known.add(key.toLowerCase());

            const nm = (val as Record<string, unknown>)?.name;

            if (typeof nm === 'string') known.add(nm.toLowerCase());

        }

        const ingredients = Array.isArray(entry.ingredients) ? entry.ingredients : [];

        const ing = (ingredients as Array<Record<string, unknown>>).map((inp) => {

            const item = String(inp.item || '');

            const ok = known.has(item.toLowerCase());

            return `<span title="${ok ? 'in library' : 'missing from library'}" style="color:${ok ? '#3fb950' : '#f85149'};">${ok ? '✓' : '✗'}${item || '?'}</span>`;

        }).join(' ');

        const outcomes = (entry.outcomes || {}) as Record<string, unknown>;

        const tierItem = (tier: string) => {

            const outs = ((outcomes[tier] || {}) as Record<string, unknown>).outputs;

            const list = Array.isArray(outs) ? outs : [];

            return list.map((o) => String((o as Record<string, unknown>).item || '')).filter(Boolean).join('+') || '—';

        };

        const skill = (entry.skill_check || {}) as Record<string, unknown>;

        const ladder = `★${tierItem('crit_success')} → ✓${tierItem('success')} → ✗${tierItem('fail')} → ✗✗${tierItem('crit_fail')}`;

        const meta = `${skill.skill ? `${skill.skill} ${skill.dc ?? 10}` : ''}${entry.duration_min ? ` · ${entry.duration_min}m` : ''}`;

        return libraryBrowserHtmlTag`<div style="font-size:9.5px;color:var(--text-muted);margin-top:2px;">${ladder}${meta ? ` · ${meta}` : ''}</div>

            <div style="font-size:9.5px;margin-top:1px;">${ing}</div>`;

    }



    newEntry(type: LibraryTab) {

        this.selectedId[type] = '__new__';

        this._editingNew[type] = true;

        this.renderList(type);

        const editors = this._getEditorConfigs();

        const config = editors[type];

        if (config) {

            const defaults: Record<string, unknown> = {};

            config.fields.forEach((f: EditorField) => { defaults[f.key] = f.default !== undefined ? f.default : ''; });

            this._renderEditor(type, defaults, true);

        }

    }



    // ── Select Entry ─────────────────────────────────────────────────



    selectEntry(type: LibraryTab, id: string) {

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



    _getEditorConfigs(): Partial<Record<LibraryTab, EditorConfig>> {

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

            },

            recipes: {

                fields: [

                    { key: 'name', label: 'Name', type: 'text', default: '' },

                    { key: 'description', label: 'Description', type: 'textarea', default: '' },

                    { key: 'ingredients', label: 'Ingredients (JSON)', type: 'json', default: [] },

                    { key: 'conditions', label: 'Conditions (JSON)', type: 'json', default: [] },

                    { key: 'duration_min', label: 'Duration (minutes)', type: 'number', default: 10 },

                    { key: 'skill_check', label: 'Skill Check (JSON)', type: 'json', default: {} },

                    { key: 'outputs', label: 'Success Outputs (JSON)', type: 'json', default: [] },

                    { key: 'outcomes', label: 'Outcomes (JSON, four tiers)', type: 'json', default: {} },

                    { key: 'learned_by', label: 'Learned By (JSON)', type: 'json', default: ['global'] },

                    { key: 'discoverable', label: 'Discoverable', type: 'checkbox', default: true },

                ]

            },

            pursuit_templates: {

                fields: [

                    { key: 'name', label: 'Name', type: 'text', default: '' },

                    { key: 'purpose', label: 'Purpose (what this undertaking is for)', type: 'textarea', default: '' },

                    { key: 'parameters', label: 'Parameters (JSON: area / item_spec / item_id / tag_list names a binding must fill)', type: 'json', default: {} },

                    { key: 'requirements', label: 'Requirements (JSON condition leaves)', type: 'json', default: [] },

                    { key: 'supplies', label: 'Supplies (JSON item specs)', type: 'json', default: [] },

                    { key: 'timing', label: 'Timing (JSON: hours / season / weather / moon / date / sun / daylight)', type: 'json', default: {} },

                    { key: 'steps', label: 'Steps (JSON typed plan: travel / take / drop / activity / wait)', type: 'json', default: [] },

                    { key: 'progress', label: 'Progress checks (JSON)', type: 'json', default: [] },

                    { key: 'stop_conditions', label: 'Stop conditions (JSON)', type: 'json', default: [] },

                    { key: 'duration', label: 'Duration (JSON)', type: 'json', default: {} },

                    { key: 'recipe', label: 'Recipe reference (JSON)', type: 'json', default: {} },

                    { key: 'tags', label: 'Tags (JSON list)', type: 'json', default: [] },

                ]

            }

        };

    }



    // ── Render Editor ────────────────────────────────────────────────



    _renderEditor(type: LibraryTab, data: Record<string, unknown>, isNew: boolean) {

        const editorId = (EDITOR_IDS as Record<string, string>)[type];

        const editor = document.getElementById(editorId);

        if (!editor) return;



        const configs = this._getEditorConfigs();

        const config = configs[type];

        if (!config) return;



        const typeIcons: Record<string, string> = { items: '📦', characters: '🧍', areas: '🏠', ways: '🚪', traits: '🏷️', conditions: '💊', behaviours: '🤖', tags: '🏷️', recipes: '🧾', pursuit_templates: '🧭' };

        const icon = typeIcons[type] || '📄';



        const fieldsHtml = config.fields.map((f: EditorField) => {

            const val = data[f.key] !== undefined ? data[f.key] : f.default;

            if (f.type === 'textarea') {

                return libraryBrowserHtmlTag`<div class="field"><label style="font-size:10px;">${f.label}</label><textarea id="lib-ed-${f.key}" rows="3" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);padding:4px 8px;font-size:11px;font-family:inherit;resize:vertical;">${val}</textarea></div>`;

            } else if (f.type === 'json') {

                const jsonVal = typeof val === 'string' ? val : JSON.stringify(val ?? f.default, null, 2);

                return libraryBrowserHtmlTag`<div class="field"><label style="font-size:10px;">${f.label}</label><textarea id="lib-ed-${f.key}" rows="3" spellcheck="false" style="width:100%;font-family:monospace;font-size:10px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);padding:4px 8px;resize:vertical;">${jsonVal}</textarea></div>`;

            } else if (f.type === 'select') {

                let opts: string[] = (f.options || []).slice();

                if (type === 'tags' && f.key === 'category' && this.data?.tags) {

                    const seen = new Set<string>(opts);

                    for (const t of Object.values(this.data.tags) as LibraryEntry[]) {

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

            ? libraryBrowserHtmlTag`<button class="btn btn-sm btn-ghost" @click=${() => (VW as unknown as { libraryBrowser: LibraryBrowser }).libraryBrowser.deleteEntry(type)} style="font-size:11px;color:var(--red);">🗑️</button>`

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



    _initTagMultiselect(type: LibraryTab, data: Record<string, unknown>) {

        if (type !== 'characters' && type !== 'areas' && type !== 'ways') return;

        const container = document.getElementById('lib-ed-tags');

        if (!container) return;

        const TagMultiselectCtor = (window as unknown as {

            TagMultiselect?: new (el: HTMLElement, opts: Record<string, unknown>) => TagMultiselectInstance;

        }).TagMultiselect;

        if (typeof TagMultiselectCtor === 'undefined') return;

        if (this._tagMS) { this._tagMS.destroy(); }

        const raw = data && data.tags !== undefined ? data.tags : [];

        const tagArray: string[] = Array.isArray(raw) ? raw as string[] :

            (typeof raw === 'string' && raw ? raw.split(',').map((s: string) => s.trim()).filter(Boolean) : []);

        this._tagMS = new TagMultiselectCtor(container, {

            tags: tagArray,

            appliesTo: type === 'characters' ? 'characters' : (type === 'ways' ? 'ways' : 'areas'),

            allowNew: true,

            placeholder: 'Search or create tags...'

        });

    }



    _showEditorEmpty(type: LibraryTab) {

        const editorId = (EDITOR_IDS as Record<string, string>)[type];

        const editor = document.getElementById(editorId);

        if (!editor) return;

        const icons: Record<string, string> = { characters: '🧍', areas: '🏠', ways: '🚪', traits: '🏷️', conditions: '💊', behaviours: '🤖', tags: '🏷️', recipes: '🧾', pursuit_templates: '🧭' };

        const labels: Record<string, string> = { characters: 'character', areas: 'area', ways: 'way', traits: 'trait', conditions: 'condition', behaviours: 'behaviour', tags: 'tag', recipes: 'recipe', pursuit_templates: 'pursuit template' };

        window.Lit.render(libraryBrowserHtmlTag`

            <div class="inspector-empty" style="min-height:200px;">

                <div class="inspector-empty-icon">${icons[type] || '📄'}</div>

                <p>Select or create a ${labels[type] || type}</p>

            </div>`, editor);

    }



    // ── Save Entry ───────────────────────────────────────────────────



    _buildSectionsForType(type: LibraryTab) {

        const config = this._getEditorConfigs()[type];

        if (!config) return [];

        if (config.sections) return config.sections;

        return config.fields.map((f: EditorField) => ({ key: f.key, label: f.label }));

    }



    async saveEntry(type: LibraryTab) {

        const id = ((document.getElementById('lib-ed-id') as HTMLInputElement | null)?.value || '').trim();

        if (!id) { toastInfo('ID is required.'); return; }



        const configs = this._getEditorConfigs();

        const config = configs[type];

        if (!config) return;



        const payload: Record<string, any> = { id };

        for (const f of config.fields) {

            const el = document.getElementById(`lib-ed-${f.key}`) as (HTMLInputElement & HTMLTextAreaElement & HTMLSelectElement) | null;

            if (!el) continue;

            if (f.type === 'checkbox') {

                payload[f.key] = (el as HTMLInputElement).checked;

            } else if (f.type === 'number') {

                payload[f.key] = parseFloat((el as HTMLInputElement).value) || f.default;

            } else if (f.type === 'json') {

                const raw = (el as HTMLTextAreaElement).value.trim();

                if (!raw) { payload[f.key] = f.default; continue; }

                try {

                    payload[f.key] = JSON.parse(raw);

                } catch (e) {

                    toastError(`Invalid JSON in "${f.label}": ${(e as Error).message}`);

                    return;

                }

            } else if (f.type === 'tagmultiselect') {

                payload[f.key] = this._tagMS ? this._tagMS.getValue() : [];

            } else {

                payload[f.key] = (el as HTMLInputElement).value;

            }

        }

        // Convert comma-separated fields to arrays for tag format

        if (type === 'tags') {

            if (typeof payload.applies_to === 'string') payload.applies_to = payload.applies_to.split(',').map((s: string) => s.trim()).filter(Boolean);

            if (typeof payload.examples === 'string') payload.examples = payload.examples.split(',').map((s: string) => s.trim()).filter(Boolean);

        }



        const oldId = this.selectedId[type] && this.selectedId[type] !== '__new__' ? this.selectedId[type] : null;

        const renamed = oldId && oldId !== id;



        let libData: Record<string, LibraryEntry> = this.data[type] || {};

        try { libData = await LibraryApi.getLibraryType(type); } catch (e) { /* ignore */ }



        const libEntry = (oldId && libData[oldId]) || libData[id] || null;



        if (!libEntry) {

            const res = await LibraryApi.saveLibraryType(type, payload);

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

            const merged: Record<string, any> = { ...libEntry, id };

            for (const key of result.sections) {

                merged[key] = payload[key];

            }

            const res = await LibraryApi.saveLibraryType(type, merged);

            if (res.error) { toastError('Error: ' + res.error); return; }

            events.log(`Updated "${merged.name || id}" in library.`, 'system-msg');

            if (renamed) {

                await LibraryApi.deleteLibraryType(type, oldId as string);

                events.log(`Renamed "${oldId}" → "${id}".`, 'system-msg');

            }

        } else if (result.action === 'duplicate') {

            const dupePayload = { ...payload, id: result.id, name: result.name };

            const res = await LibraryApi.saveLibraryType(type, dupePayload);

            if (res.error) { toastError('Error: ' + res.error); return; }

            events.log(`Saved "${result.name}" as duplicate to library.`, 'system-msg');

        }



        await this._finishSave(type, id);

    }



    async _finishSave(type: LibraryTab, id: string) {

        await this.refreshType(type);

        this.selectedId[type] = id;

        this.renderList(type);

        this.selectEntry(type, id);

    }



    async deleteEntry(type: LibraryTab) {

        const id = this.selectedId[type];

        if (!id || id === '__new__') return;
        const ok = await (window as any).Dialog?.confirm?.({
            title: 'Delete Library Entry',
            message: `Delete "${id}" from library?`,
            danger: true
        });
        if (!ok) return;

        const res = await LibraryApi.deleteLibraryType(type, id);

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

        const target = await (ItemLibraryPlacement as { pickTarget(title: string, opts: { tabs: string[] }): Promise<{ type: string; name?: string; id: string } | null> })

            .pickTarget(`Place "${entry.name || id}" in:`, { tabs: ['area'] });

        if (!target) return;

        const area = target.type === 'area' ? (target.name as string) : target.id;



        const res = await LibraryApi.importCharacterFromLibrary(id, { area, active: true });

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

        const promptRes = await (window as any).Dialog?.prompt?.({
            title: 'Import Area',
            fields: [{ key: 'name', label: 'Area Name', value: entry.name || id }]
        });
        const newName = promptRes?.name?.trim();

        if (!newName) return;



        const res = await LibraryApi.importRoomFromLibrary(id, { name: newName });

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



        // Pick the two areas the way connects via the target picker (bug-538).

        // The picker lists areas by their displayed names in a searchable dialog.

        const picker = (window as unknown as {

            ItemLibraryPlacement?: {

                pickTarget(title: string, options?: { tabs?: string[] }): Promise<{ type: string; name?: string; id?: string } | null>;

            };

        }).ItemLibraryPlacement;



        let fromName: string | null = null;

        let toName: string | null = null;



        if (picker?.pickTarget) {

            const fromTarget = await picker.pickTarget(`Import way "${entry.name || id}" - Connect FROM area:`, { tabs: ['area'] });

            if (!fromTarget) return;

            fromName = fromTarget.name || fromTarget.id || null;

            if (!fromName) return;



            const toTarget = await picker.pickTarget(`Import way "${entry.name || id}" - Connect TO area:`, { tabs: ['area'] });

            if (!toTarget) return;

            toName = toTarget.name || toTarget.id || null;

            if (!toName) return;

        } else if (VW?.dialog?.prompt) {

            const fromRes = await VW.dialog.prompt({

                title: `Import way "${entry.name || id}"`,

                message: 'Connect FROM area name:',

            });

            if (!fromRes || !fromRes.value) return;

            fromName = fromRes.value.trim();



            const toRes = await VW.dialog.prompt({

                title: `Import way "${entry.name || id}"`,

                message: 'Connect TO area name:',

            });

            if (!toRes || !toRes.value) return;

            toName = toRes.value.trim();

        } else {

            const fromP = await (window as any).Dialog?.prompt?.({
                title: `Import way "${entry.name || id}"`,
                fields: [{ key: 'from', label: 'Connect FROM area name', placeholder: '' }]
            });
            if (!fromP?.from?.trim()) return;
            fromName = fromP.from.trim();

            const toP = await (window as any).Dialog?.prompt?.({
                title: `Import way "${entry.name || id}"`,
                fields: [{ key: 'to', label: 'Connect TO area name', placeholder: '' }]
            });
            if (!toP?.to?.trim()) return;
            toName = toP.to.trim();

        }



        if (!fromName || !toName) return;



        let dirFrom = 'out';

        let dirTo = 'out';

        if (VW?.dialog?.prompt) {

            const dirFromRes = await VW.dialog.prompt({

                title: 'Way direction',

                message: `Direction FROM ${fromName} (e.g. east):`,

                defaultValue: 'out',

            });

            if (dirFromRes === null) return;

            dirFrom = (dirFromRes.value && dirFromRes.value.trim()) || 'out';



            const dirToRes = await VW.dialog.prompt({

                title: 'Way direction',

                message: `Direction FROM ${toName} (e.g. west):`,

                defaultValue: 'out',

            });

            if (dirToRes === null) return;

            dirTo = (dirToRes.value && dirToRes.value.trim()) || 'out';

        } else {

            const dfP = await (window as any).Dialog?.prompt?.({
                title: 'Way direction',
                fields: [{ key: 'dir', label: `Direction FROM ${fromName}`, value: 'out' }]
            });
            if (!dfP) return;
            dirFrom = dfP.dir?.trim() || 'out';

            const dtP = await (window as any).Dialog?.prompt?.({
                title: 'Way direction',
                fields: [{ key: 'dir', label: `Direction FROM ${toName}`, value: 'out' }]
            });
            if (!dtP) return;
            dirTo = dtP.dir?.trim() || 'out';

        }



        const res = await LibraryApi.importWayFromLibrary(id, { area_from: fromName, area_to: toName, dir_from: dirFrom, dir_to: dirTo });

        if (res.error) { toastError('Error: ' + res.error); return; }

        events.log(`Imported way "${res.way}" into the world.`, 'system-msg');

        worldState.fetch();

    }



    // ── Save World Character to Library ──────────────────────────────



    _buildCharacterPayload(charName: string) {

        // Delegate to the canonical inspector builder so save/export/library

        // all produce the same shape (no data loss on any path).

        const agentView = (window as unknown as {

            InspectorAgentView?: { _buildCharacterCard?(name: string): Record<string, unknown> | null };

        }).InspectorAgentView;

        if (agentView?._buildCharacterCard) {

            return agentView._buildCharacterCard(charName);

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

    _applyLibrarySelection(base: Record<string, any> | null, incoming: Record<string, any>, result: DiffModalResult) {

        const merged: Record<string, any> = { ...(base || {}), id: incoming.id || incoming.name || (base && base.id) };

        (result.sections || []).forEach((key: string) => {

            merged[key] = incoming[key];

        });

        if (result.entries) {

            for (const key of Object.keys(result.entries)) {

                if ((result.sections || []).includes(key)) continue;

                merged[key] = DiffModalTyped.applyEntrySelection(merged[key], incoming[key], result.entries[key]);

            }

        }

        return merged;

    }



    async saveWorldToCharacter() {

        const players = Object.keys(worldState.players || {});

        if (players.length === 0) { toastInfo('No characters in the world.'); return; }

        const promptRes = await (window as any).Dialog?.prompt?.({
            title: 'Save Character to Library',
            message: `Available characters: ${players.join(', ')}`,
            fields: [{ key: 'name', label: 'Character Name', value: players[0] }]
        });
        const charName = promptRes?.name?.trim();

        if (!charName || !players.includes(charName)) return;



        const charCard = this._buildCharacterPayload(charName);

        if (!charCard) return;



        await this._saveCharacterWithDiffModal(charName, charCard);

    }



    /** Save a specific character to the library (no prompt). Used by WorldSync. */

    async saveCharacterByName(charName: string) {

        if (!charName) return;

        const charCard = this._buildCharacterPayload(charName);

        if (!charCard) { toastError(`Could not build library payload for character "${charName}".`); return; }

        await this._saveCharacterWithDiffModal(charName, charCard);

    }



    async _saveCharacterWithDiffModal(charName: string, charCard: Record<string, any>) {

        let libEntry: Record<string, any> | null = null;

        try {

            const libData = await LibraryApi.getLibraryType('characters');

            libEntry = libData[charName] || null;

        } catch (e) { /* ignore */ }



        if (!libEntry) {

            const res = await LibraryApi.saveLibraryType('characters', { id: charName, ...charCard });

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

            const res = await LibraryApi.saveLibraryType('characters', merged);

            if (res.error) { toastError('Error: ' + res.error); return; }

            events.log(`Character "${charName}" updated in library.`, 'system-msg');

        } else if (result.action === 'duplicate') {

            const dupePayload = { id: result.id, name: result.name, ...charCard };

            const res = await LibraryApi.saveLibraryType('characters', dupePayload);

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

                const res = await LibraryApi.saveLibraryType('characters', { id: charName, ...charCard });

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

                const res = await LibraryApi.saveLibraryType('characters', merged);

                if (!res.error) updated++;

                else errors++;

            } else if (result.action === 'duplicate') {

                const dupePayload = { id: result.id, name: result.name, ...charCard };

                const res = await LibraryApi.saveLibraryType('characters', dupePayload);

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



    _buildAreaPayload(areaName: string) {

        const areaData = worldState.areas?.[areaName];

        if (!areaData) return null;



        const graphNodes = worldState.graph?.nodes || {};

        const graphEdges = worldState.graph?.edges || [];

        const areaNodeId = `area_${areaName.toLowerCase().replace(/\s+/g, '_')}`;

        const graphNode = graphNodes[areaNodeId];

        const props = graphNode?.properties || {};

        const env = props.environment || areaData.environment || {};



        const items: Record<string, unknown>[] = [];

        for (const edge of graphEdges as Array<Record<string, any>>) {

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



        const exits: Record<string, unknown>[] = [];

        const rawExits: Record<string, any> = areaData.exits || {};

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



        const triggers: Record<string, unknown>[] = [];

        for (const edge of graphEdges as Array<Record<string, any>>) {

            if (edge.source !== areaNodeId) continue;

            if (edge.type !== 'triggers') continue;

            const edgeProps = edge.properties || {};

            const effects = edgeProps.effects?.length > 0

                ? edgeProps.effects

                : (edgeProps.effect_type ? [{ type: edgeProps.effect_type, params: edgeProps.effect_params || {} }] : []);

            let conditions: any = edgeProps.conditions || {};

            if (Array.isArray(conditions) || !conditions.operator) {

                const logic = edgeProps.conditions_logic || 'and';

                if (Array.isArray(conditions) && conditions.length > 0) {

                    conditions = { operator: logic, conditions };

                } else {

                    conditions = {};

                }

            }

            triggers.push({

                trigger_type: edgeProps.trigger_type || 'on_enter',

                effects,

                target_name: edgeProps.target_name || '',

                target_state: edgeProps.target_state || '',

                conditions,

                success_message: edgeProps.success_message || '',

                fail_message: edgeProps.fail_message || ''

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

        } as Record<string, unknown>;

    }



    async saveWorldToArea() {

        const areaNames = Object.keys(worldState.areas || {});

        if (areaNames.length === 0) { toastInfo('No areas in the world.'); return; }

        const promptRes = await (window as any).Dialog?.prompt?.({
            title: 'Save Area to Library',
            message: `Available areas: ${areaNames.join(', ')}`,
            fields: [{ key: 'name', label: 'Area Name', value: areaNames[0] }]
        });
        const areaName = promptRes?.name?.trim();

        if (!areaName || !areaNames.includes(areaName)) return;



        const payload = this._buildAreaPayload(areaName);

        if (!payload) return;



        await this._saveAreaWithDiffModal(areaName, payload);

    }



    /**

     * Save a specific world area by name to the areas library (no prompt).

     * @param {string} areaName - Area name as shown in the graph/inspector.

     */

    async saveAreaByName(areaName: string) {

        if (!areaName) return;

        const payload = this._buildAreaPayload(areaName);

        if (!payload) { toastError(`Could not build library payload for area "${areaName}".`); return; }

        await this._saveAreaWithDiffModal(areaName, payload);

    }



    async _saveAreaWithDiffModal(areaName: string, areaPayload: Record<string, any>) {

        const areaId = areaName.toLowerCase().replace(/[^a-z0-9_]+/g, '_');

        let libEntry: Record<string, any> | null = null;

        try {

            const libData = await LibraryApi.getLibraryType('areas');

            libEntry = libData[areaId] || null;

        } catch (e) { /* ignore */ }



        if (!libEntry) {

            const res = await LibraryApi.saveLibraryType('areas', { id: areaId, ...areaPayload });

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

            const merged: Record<string, any> = { ...libEntry, id: areaId };

            for (const key of result.sections) {

                merged[key] = areaPayload[key];

            }

            const res = await LibraryApi.saveLibraryType('areas', merged);

            if (res.error) { toastError('Error: ' + res.error); return; }

            events.log(`Area "${areaName}" updated in library.`, 'system-msg');

        } else if (result.action === 'duplicate') {

            const dupePayload: Record<string, any> = { id: result.id, name: result.name, ...areaPayload };

            const res = await LibraryApi.saveLibraryType('areas', dupePayload);

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

                const res = await LibraryApi.saveLibraryType('areas', { id: areaId, ...areaPayload });

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

                const merged: Record<string, any> = { ...libEntry, id: areaId };

                for (const key of result.sections) {

                    merged[key] = areaPayload[key];

                }

                const res = await LibraryApi.saveLibraryType('areas', merged);

                if (!res.error) updated++;

                else errors++;

            } else if (result.action === 'duplicate') {

                const dupePayload: Record<string, any> = { id: result.id, name: result.name, ...areaPayload };

                const res = await LibraryApi.saveLibraryType('areas', dupePayload);

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
(window as unknown as { LibraryBrowser: typeof LibraryBrowser; libraryBrowser: LibraryBrowser }).LibraryBrowser = LibraryBrowser;
(window as unknown as { libraryBrowser: LibraryBrowser }).libraryBrowser = libraryBrowser;



