/**
 * WorldSync — unified "Sync World → Library" list.
 *
 * Lists every item, way, area, and character in the world with a per-entity
 * status badge (new / diff / synced). Clicking an entity routes to the existing
 * single-entity save flow, which shows the DiffModal with Skip / Update /
 * Create-New actions.
 *
 * Matches entities by `library_id` first, then by name-derived slug, then by
 * display name.
 *
 * @module world-sync — the "Sync World → Library" list
 * @contributes WorldSync: per-entity status (new/diff/synced) + routing into the single-entity save flow
 * @powers promoting world edits back into the library as templates
 * @relates matches by library_id → name slug → display name; DiffModal via the save flow
 * @docs docs/virtualWorld/Library System/Library 2.0 - Unified Library Design.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const worldSyncTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);

// These two are cross-module singletons that are NOT declared in
// static/js/types/globals.d.ts (shared hub; not editable from a conversion
// lane). `declare` emits nothing, so runtime resolution is unchanged:
// itemLib / libraryBrowser are script-level `const`s, jsonDeepEqual is a
// script-level function declaration.


/**
 * The library API surface WorldSync uses; globals.d.ts lists only 9 wrappers.
 * A type alias rather than a helper function, because a top-level `function`
 * in a classic script is a global lexical binding and can collide with another
 * file's declaration. Casting inline reads `ApiClient` at call time, exactly as
 * the original did.
 */
type LibraryApi = {
    getLibraryTypes(types: string[]): Promise<Record<string, Record<string, LibraryEntry>>>;
    saveLibraryItem(entry: Record<string, unknown>): Promise<{ error?: string } | null>;
    saveLibraryType(type: string, entry: Record<string, unknown>): Promise<{ error?: string } | null>;
};

class WorldSync {
    /** Library entries per type, keyed by library id. */
    declare cache: Record<string, Record<string, LibraryEntry>>;
    /** One row per syncable entity, with its library match + status. */
    declare entities: SyncEntity[];
    /** Active tab: 'all' | 'item' | 'way' | 'area' | 'character'. */
    declare filter: string;
    /** Scratch list filled by _buildItem for contained-but-real graph nodes. */
    declare _nested: Array<SyncEntity | null>;

    constructor() {
        this.cache = {};
        this.entities = [];
        this.filter = 'all';
    }

    async open() {
        this.cache = {};
        const data = await (ApiClient as unknown as LibraryApi).getLibraryTypes(['items', 'ways', 'areas', 'characters']);
        this.cache.items = data.items || {};
        this.cache.ways = data.ways || {};
        this.cache.areas = data.areas || {};
        this.cache.characters = data.characters || {};
        this.entities = this._collect();
        this._renderSummary();
        this._renderList();
        const modal = document.getElementById('world-sync-modal');
        if (modal) modal.style.display = 'flex';
    }

    close() {
        const el = document.getElementById('world-sync-modal');
        if (el) el.style.display = 'none';
    }

    setFilter(f: string) {
        this.filter = f;
        document.querySelectorAll<HTMLElement>('#world-sync-modal .lib-tab').forEach(el => {
            el.classList.toggle('selected', el.dataset.syncFilter === f);
        });
        this._renderList();
    }

    // ── Collection ───────────────────────────────────────────────────

    _slug(name?: string) {
        return (name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_');
    }

    _findLibraryMatch(type: string, worldPayload: Record<string, any>): LibraryMatch | null {
        const lib = this.cache[type] || {};
        const name = String(worldPayload.name || '');
        const candidates = [
            worldPayload.library_id,
            worldPayload.id,
            this._slug(name)
        ].filter(Boolean);
        for (const c of candidates) {
            if (lib[c]) return { id: c, entry: lib[c] };
        }
        // name-based fallback
        const nameLower = name.toLowerCase();
        for (const [id, entry] of Object.entries(lib)) {
            if (String((entry as LibraryEntry).name || '').toLowerCase() === nameLower) {
                return { id, entry: entry as LibraryEntry };
            }
        }
        return null;
    }

    _collect(): SyncEntity[] {
        const nodes = worldState.graph?.nodes || {};
        const items: Array<{ nodeId: string; node: any }> = [];
        const ways: Array<{ nodeId: string; node: any }> = [];
        for (const [nodeId, node] of Object.entries(nodes) as Array<[string, any]>) {
            if (node.type === 'item') items.push({ nodeId, node });
            else if (node.type === 'way') ways.push({ nodeId, node });
        }

        const areas = Object.keys(worldState.areas || {}).map((name: string) => ({ name }));
        const characters = Object.keys(worldState.players || {}).map((name: string) => ({ name }));

        this._nested = [];
        const out: SyncEntity[] = [];
        for (const { nodeId, node } of items) {
            const e = this._buildItem(nodeId, node);
            if (e) out.push(e);
        }
        // Nested contained items that are their own graph nodes also get a standalone
        // entry so they're synced to the library as reusable items (box-of-cards case).
        const seenNested = new Set<string>();
        for (const n of this._nested) {
            if (seenNested.has(n!.nodeId || '')) continue;
            seenNested.add(n!.nodeId || '');
            out.push(n!);
        }
        for (const { nodeId, node } of ways) out.push(this._buildWay(nodeId, node));
        for (const { name } of areas) {
            const a = this._buildArea(name);
            if (a) out.push(a);
        }
        for (const { name } of characters) {
            const c = this._buildCharacter(name);
            if (c) out.push(c);
        }

        // Dedupe by type+nodeId/name
        const seen = new Set<string>();
        return out.filter(e => {
            const key = `${e.type}:${e.nodeId || e.name}`;
            if (!e || seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    _buildItem(nodeId: string, node: any, depth = 0, seen: Set<string> | null = null): SyncEntity | null {
        const built = itemLib._buildWorldItemPayload(nodeId);
        if (!built) return null;
        const payload = built.payload;
        // Restore linkage hints for matching (not written to the library entry).
        const props = node.properties || {};
        if (props.library_id) payload.library_id = props.library_id;
        // Contained items that are their own graph nodes also get a standalone entry
        // so they're synced to the library as reusable items (box-of-cards case).
        if (depth === 0) {
            for (const nestedId of built.nested) {
                const n = worldState.getNode(nestedId);
                if (n && n.type === 'item') this._nested.push(this._buildItem(nestedId, n, depth + 1));
            }
        }
        const match = this._findLibraryMatch('items', payload);
        const status = match ? (jsonDeepEqual(match.entry, this._clean(payload)) ? 'synced' : 'diff') : 'new';
        return { type: 'item', nodeId, payload, match, status };
    }

    _buildWay(nodeId: string, node: any): SyncEntity {
        const props = node.properties || {};
        const name = node.name || 'Unnamed Way';
        const payload = {
            id: this._slug(name),
            library_id: props.library_id || '',
            name,
            description: props.description || '',
            current_state: props.current_state || 'closed',
            pass_message: props.pass_message || '',
            edge_length: props.edge_length || '',
            needs_open: props.needs_open || {},
            auto_close: !!props.auto_close,
            see_through: !!props.see_through,
            one_way: !!props.one_way,
            requires: props.requires || '',
            max_size: props.max_size || '',
            prevent_close: !!props.prevent_close,
            tags: props.tags || [],
            parameters: props.parameters || {},
            triggers: itemLib._extractTriggersFromEdges(nodeId)
        };
        const match = this._findLibraryMatch('ways', payload);
        const status = match ? (jsonDeepEqual(match.entry, this._clean(payload)) ? 'synced' : 'diff') : 'new';
        return { type: 'way', nodeId, payload, match, status };
    }

    _buildArea(name: string): SyncEntity | null {
        const payload = libraryBrowser._buildAreaPayload(name);
        if (!payload) return null;
        const match = this._findLibraryMatch('areas', payload);
        const status = match ? (jsonDeepEqual(match.entry, this._clean(payload)) ? 'synced' : 'diff') : 'new';
        return { type: 'area', name, payload, match, status };
    }

    _buildCharacter(name: string): SyncEntity | null {
        const payload = libraryBrowser._buildCharacterPayload(name);
        if (!payload) return null;
        const match = this._findLibraryMatch('characters', payload);
        const status = match ? (jsonDeepEqual(match.entry, this._clean(payload)) ? 'synced' : 'diff') : 'new';
        return { type: 'character', name, payload, match, status };
    }

    // Drop id/library_id so comparison is about content, not linkage key.
    _clean(payload: Record<string, any>) {
        const c = { ...payload };
        delete c.id;
        delete c.library_id;
        return c;
    }

    // ── Opening an entity → existing DiffModal flow ─────────────────

    openEntity(entity: SyncEntity) {
        if (entity.type === 'item') return itemLib.saveWorldItem(entity.nodeId);
        if (entity.type === 'way') return InspectorWayView._saveToLibrary(entity.nodeId);
        if (entity.type === 'area') return libraryBrowser.saveAreaByName(entity.name);
        if (entity.type === 'character') return libraryBrowser.saveCharacterByName(entity.name);
    }

    openEntityByIndex(idx: number) {
        const list = this.entities.filter(e => this.filter === 'all' || e.type === this.filter);
        const e = list[idx];
        if (e) return this.openEntity(e);
    }

    /**
     * Batch-sync every entity that is new or differs from the library, WITHOUT
     * showing the DiffModal. New entities are created; differing ones silently
     * overwrite their matched library entry. Already-synced entities are left
     * untouched. After the batch, saved entities flip to "synced ✓" in the list
     * and any failures stay marked.
     */
    async syncAll() {
        const pending = this.entities.filter(e => e.status === 'new' || e.status === 'diff');
        if (pending.length === 0) {
            toastInfo('Everything is already in sync with the library.');
            return;
        }
        let updated = 0, failed = 0;
        for (const e of pending) {
            try {
                const res = await this._silentSave(e);
                if (res && res.error) throw new Error(res.error);
                e.status = 'synced';
                e.syncFailed = false;
                updated++;
            } catch (err) {
                e.status = e.status === 'diff' ? 'diff' : 'new';
                e.syncFailed = true;
                failed++;
                console.error('syncAll failed for ' + (e.nodeId || e.name || e.type), err);
            }
        }
        this._renderSummary();
        this._renderList();
        if (failed === 0) {
            toastInfo(`Synced ${updated} entit${updated === 1 ? 'y' : 'ies'} to library.`);
        } else {
            toastError(`Synced ${updated}, ${failed} failed.`);
        }
    }

    // True for values that should be treated as "no data" — empty string,
    // empty array, empty object, or null/undefined. A library field holding
    // real data must never be overwritten by one of these from the world copy.
    _isEmpty(value: unknown) {
        if (value === null || value === undefined) return true;
        if (typeof value === 'string') return value.trim() === '';
        if (Array.isArray(value)) return value.length === 0;
        if (typeof value === 'object') return Object.keys(value).length === 0;
        return false;
    }

    // Merge the world payload over the matched library entry, but never let an
    // empty world value erase data the library already has. Non-empty world
    // values still win (the world is authoritative for fields it actually has).
    _mergeEntry(libEntry: Record<string, any>, worldPayload: Record<string, any>) {
        const out = { ...libEntry };
        for (const [key, value] of Object.entries(worldPayload)) {
            if (this._isEmpty(value) && !this._isEmpty(out[key])) continue;
            out[key] = value;
        }
        return out;
    }

    /**
     * Push one entity's world payload to the library, overwriting any existing
     * entry. No DiffModal — this is the "just do it" bulk path.
     */
    async _silentSave(e: SyncEntity) {
        if (e.type === 'item') {
            const id = e.match?.id || (e.payload.name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_');
            const entry = e.match?.entry ? this._mergeEntry(e.match.entry, e.payload) : e.payload;
            return (ApiClient as unknown as LibraryApi).saveLibraryItem({ id, name: e.payload.name, ...entry });
        }
        if (e.type === 'way') {
            const id = e.match?.id || e.payload.id;
            const entry = e.match?.entry ? this._mergeEntry(e.match.entry, e.payload) : e.payload;
            return (ApiClient as unknown as LibraryApi).saveLibraryType('ways', { id, ...entry });
        }
        if (e.type === 'area') {
            const id = e.match?.id || (e.name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_');
            const entry = e.match?.entry ? this._mergeEntry(e.match.entry, e.payload) : e.payload;
            return (ApiClient as unknown as LibraryApi).saveLibraryType('areas', { id, ...entry });
        }
        if (e.type === 'character') {
            const id = e.match?.id || e.name;
            const entry = e.match?.entry ? this._mergeEntry(e.match.entry, e.payload) : e.payload;
            return (ApiClient as unknown as LibraryApi).saveLibraryType('characters', { id, ...entry });
        }
        return null;
    }

    // Read-only section-by-section Library → World comparison for one entity.
    viewDiffByIndex(idx: number) {
        const list = this.entities.filter(e => this.filter === 'all' || e.type === this.filter);
        const e = list[idx];
        if (!e || !e.match) return;
        const sections = {
            item: [
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
            ],
            way: [
                { key: 'name', label: 'Name' },
                { key: 'description', label: 'Description' },
                { key: 'current_state', label: 'State' },
                { key: 'pass_message', label: 'Pass Message' },
                { key: 'needs_open', label: 'Needs Open' },
                { key: 'auto_close', label: 'Auto Close' },
                { key: 'see_through', label: 'See Through' },
                { key: 'tags', label: 'Tags' },
                { key: 'triggers', label: 'Triggers' }
            ],
            area: [
                { key: 'description', label: 'Description' },
                { key: 'tags', label: 'Tags' },
                { key: 'environment', label: 'Environment' },
                { key: 'items', label: 'Items' },
                { key: 'exits', label: 'Exits' },
                { key: 'triggers', label: 'Triggers' }
            ],
            character: [
                { key: 'personality', label: 'Personality' },
                { key: 'description', label: 'Description' },
                { key: 'stats', label: 'Stats' },
                { key: 'skills', label: 'Skills' },
                { key: 'traits', label: 'Traits' },
                { key: 'tags', label: 'Tags' },
                { key: 'emotion', label: 'Emotion' },
                { key: 'relationships', label: 'Relationships' },
                { key: 'memories', label: 'Memories' },
                { key: 'behaviors', label: 'Behaviours' },
                { key: 'npc_behavior', label: 'NPC Config' },
                { key: 'inventory', label: 'Items' }
            ]
        }[e.type] || [];
        DiffModal.show(e.match.entry, e.payload, sections, {
            title: 'Diff — ' + (e.payload.name || e.name || e.nodeId),
            name: e.match.id,
            readOnly: true
        });
    }

    // ── Render ──────────────────────────────────────────────────────

    _typeMeta(type: string): { icon?: string; label?: string } {
        return {
            item: { icon: '📦', label: 'Item' },
            way: { icon: '🚪', label: 'Way' },
            area: { icon: '🏠', label: 'Area' },
            character: { icon: '🧍', label: 'Character' }
        }[type] || {};
    }

    _renderSummary() {
        const counts: Record<string, number> = { all: 0, new: 0, diff: 0, synced: 0 };
        for (const e of this.entities) {
            counts.all++;
            if (counts[e.status] !== undefined) counts[e.status]++;
        }
        const el = document.getElementById('world-sync-summary');
        if (!el) return;
        window.Lit.render(worldSyncTag`
            <span style="color:var(--text);">${counts.all} entities</span>
            — <span style="color:#3fb950;">${counts.new} new</span>
            · <span style="color:#e3b341;">${counts.diff} different</span>
            · <span style="color:var(--text-muted);">${counts.synced} synced</span>`, el);
    }

    _renderList() {
        const el = document.getElementById('world-sync-list');
        if (!el) return;
        const list = this.entities.filter(e => this.filter === 'all' || e.type === this.filter);
        if (list.length === 0) {
            window.Lit.render(worldSyncTag`<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">No entities.</div>`, el);
            return;
        }
        window.Lit.render(worldSyncTag`${list.map((e: SyncEntity, listIdx: number) => {
            const m = this._typeMeta(e.type);
            const label = e.type === 'area' || e.type === 'character' ? e.name : (e.payload.name || e.nodeId);
            const sub = e.type === 'item' || e.type === 'way'
                ? (e.payload.description || e.nodeId)
                : (this.cache[e.type + 's']?.[e.match?.id || ''] ? `library: ${e.match?.id}` : 'not in library');
            const badge = e.syncFailed
                ? worldSyncTag`<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(248,81,73,0.15);color:#f85149;border:1px solid rgba(248,81,73,0.3);white-space:nowrap;">sync failed</span>`
                : e.status === 'new'
                    ? worldSyncTag`<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(63,185,80,0.15);color:#3fb950;border:1px solid rgba(63,185,80,0.3);white-space:nowrap;">new</span>`
                    : e.status === 'diff'
                        ? worldSyncTag`<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(227,179,65,0.15);color:#e3b341;border:1px solid rgba(227,179,65,0.3);white-space:nowrap;">differs</span>`
                        : worldSyncTag`<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(139,148,158,0.15);color:var(--text-muted);border:1px solid var(--border);white-space:nowrap;">synced ✓</span>`;
            const diffBtn = e.match
                ? worldSyncTag`<button class="btn btn-sm" style="flex-shrink:0;" @click=${(ev: Event) => { ev.stopPropagation(); VW.worldSync.viewDiffByIndex(listIdx); }}>diff</button>`
                : '';
            return worldSyncTag`<div class="agent-item" style="cursor:pointer;padding:5px 10px;border-left:3px solid var(--border);" @click=${() => VW.worldSync.openEntityByIndex(listIdx)}>
                <span style="font-size:13px;margin-right:4px;">${m.icon}</span>
                <div style="flex:1;min-width:0;">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <span class="agent-name" style="font-size:12px;font-weight:600;">${label}</span>
                        ${badge}
                    </div>
                    <div style="font-size:10px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${sub}</div>
                </div>
                ${diffBtn}
            </div>`;
        })}`, el);
    }
}

const worldSync = new WorldSync();

// NOTE: these declarations sit AFTER the first value statement on purpose. A
// leading `interface`/`type` makes TypeScript drop the file's leading JSDoc
// block from the emitted .js, and tools/js_module_index.py reads the `@module`
// tag out of that emitted .js.

interface LibraryEntry {
    name?: string;
    [key: string]: unknown;
}

interface LibraryMatch {
    id: string;
    entry: LibraryEntry;
}

/** One row of the sync list: a world entity plus its library match and status. */
interface SyncEntity {
    type: string;
    nodeId?: string;
    name?: string;
    payload: Record<string, any>;
    match: LibraryMatch | null;
    status: string;
    syncFailed?: boolean;
}

interface ItemLib {
    _buildWorldItemPayload(nodeId: string): { payload: Record<string, any>; nested: string[] } | null;
    _extractTriggersFromEdges(nodeId: string): unknown;
    saveWorldItem(nodeId?: string): unknown;
}

interface LibraryBrowser {
    _buildAreaPayload(name: string): Record<string, any> | null;
    _buildCharacterPayload(name: string): Record<string, any> | null;
    saveAreaByName(name?: string): unknown;
    saveCharacterByName(name?: string): unknown;
}

interface DiffModalApi {
    show(a: unknown, b: unknown, sections: unknown, opts?: unknown): void;
}
