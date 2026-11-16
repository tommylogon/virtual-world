"use strict";
/**
 * WorldSync - unified "Sync World → Library" list.
 *
 * Lists every item, way, area, and character in the world with a per-entity
 * status badge (new / diff / synced). Clicking an entity routes to the existing
 * single-entity save flow, which shows the DiffModal with Skip / Update /
 * Create-New actions.
 *
 * Matches entities by `library_id` first, then by name-derived slug, then by
 * display name.
 *
 * @module world-sync - the "Sync World → Library" list
 * @contributes WorldSync: per-entity status (new/diff/synced) + routing into the single-entity save flow + refresh() after a world edit
 * @powers promoting world edits back into the library as templates
 * @relates matches by library_id → name slug → display name; DiffModal via the save flow
 * @docs docs/virtualWorld/Library System/Library 2.0 - Unified Library Design.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const worldSyncTag = (strings, ...values) => window.Lit.html(strings, ...values);
class WorldSync {
    constructor() {
        this.cache = {};
        this.entities = [];
        this.groups = [];
        this.filter = 'all';
        this.showGenerated = false;
        this.showUnchanged = false;
        this._lastBatchBackup = null;
    }
    /**
     * Re-read the library and re-render WITHOUT opening the modal.
     * Four call sites (inspector/area-view, graph-manager, structures,
     * worldpainter) call `worldSync.refresh()` after a world edit - one of them
     * unguarded, which is how a live run produced "Scope change failed:
     * window.worldSync.refresh is not a function" after a scope change that had
     * already succeeded. The method never existed; the three guarded callers
     * were silently doing nothing. This is that method.
     */
    async refresh() {
        this.cache = {};
        const data = await ApiClient.getLibraryTypes(['items', 'ways', 'areas', 'characters']);
        this.cache.items = data.items || {};
        this.cache.ways = data.ways || {};
        this.cache.areas = data.areas || {};
        this.cache.characters = data.characters || {};
        this.entities = this._collect();
        this.groups = this._group();
        this._renderSummary();
        this._renderList();
    }
    async open() {
        await this.refresh();
        const modal = document.getElementById('world-sync-modal');
        if (modal)
            modal.style.display = 'flex';
    }
    close() {
        const el = document.getElementById('world-sync-modal');
        if (el)
            el.style.display = 'none';
    }
    setFilter(f) {
        this.filter = f;
        document.querySelectorAll('#world-sync-modal .lib-tab').forEach(el => {
            el.classList.toggle('selected', el.dataset.syncFilter === f);
        });
        this._renderSummary();
        this._renderList();
    }
    toggleShowGenerated() {
        this.showGenerated = !this.showGenerated;
        this._renderSummary();
        this._renderList();
    }
    toggleShowUnchanged() {
        this.showUnchanged = !this.showUnchanged;
        this._renderSummary();
        this._renderList();
    }
    // ── Collection ───────────────────────────────────────────────────
    _slug(name) {
        return (name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_');
    }
    _findLibraryMatch(type, worldPayload) {
        const lib = this.cache[type] || {};
        const name = String(worldPayload.name || '');
        const candidates = [
            worldPayload.library_id,
            worldPayload.id,
            this._slug(name)
        ].filter(Boolean);
        for (const c of candidates) {
            if (lib[c])
                return { id: c, entry: lib[c] };
        }
        // name-based fallback
        const nameLower = name.toLowerCase();
        for (const [id, entry] of Object.entries(lib)) {
            if (String(entry.name || '').toLowerCase() === nameLower) {
                return { id, entry: entry };
            }
        }
        return null;
    }
    _collect() {
        const nodes = worldState.graph?.nodes || {};
        // bug-526: procedurally generated areas carry `cell` (the painter's grid
        // cell), so Sync All can recognise and skip them. Generated items/ways
        // are recognised by a `worldpainter` provenance marker once stamped at
        // generation time (there is none today).
        this._generatedAreaNames = new Set();
        for (const node of Object.values(nodes)) {
            if (node && node.type === 'area' && node.properties
                && (node.properties.cell != null || node.properties.generated != null || node.properties.source === 'worldpainter') && node.name) {
                this._generatedAreaNames.add(node.name);
            }
        }
        const items = [];
        const ways = [];
        for (const [nodeId, node] of Object.entries(nodes)) {
            if (node.type === 'item')
                items.push({ nodeId, node });
            else if (node.type === 'way')
                ways.push({ nodeId, node });
        }
        const areas = Object.keys(worldState.areas || {}).map((name) => ({ name }));
        const characters = Object.keys(worldState.players || {}).map((name) => ({ name }));
        this._nested = [];
        const out = [];
        for (const { nodeId, node } of items) {
            const e = this._buildItem(nodeId, node);
            if (e)
                out.push(e);
        }
        // Nested contained items that are their own graph nodes also get a standalone
        // entry so they're synced to the library as reusable items (box-of-cards case).
        const seenNested = new Set();
        for (const n of this._nested) {
            if (seenNested.has(n.nodeId || ''))
                continue;
            seenNested.add(n.nodeId || '');
            out.push(n);
        }
        for (const { nodeId, node } of ways)
            out.push(this._buildWay(nodeId, node));
        for (const { name } of areas) {
            const a = this._buildArea(name);
            if (a)
                out.push(a);
        }
        for (const { name } of characters) {
            const c = this._buildCharacter(name);
            if (c)
                out.push(c);
        }
        // Dedupe by type+nodeId/name
        const seen = new Set();
        return out.filter(e => {
            const key = `${e.type}:${e.nodeId || e.name}`;
            if (!e || seen.has(key))
                return false;
            seen.add(key);
            return true;
        });
    }
    /**
     * Collapse entities into template groups. Item *instances* of the same
     * template (12 wild_berries, N painter-spawned bushes) become ONE row so a
     * batch is a handful of decisions, not hundreds. Ways/areas/characters are
     * distinct places/people and stay one row each. A group's status is the
     * worst of its members; it is `generated` only when every member is.
     */
    _group() {
        const byKey = new Map();
        for (const e of this.entities) {
            const key = e.type === 'item'
                ? 'item:' + String(e.payload.library_id || this._slug(String(e.payload.name || '')))
                : `${e.type}:${e.nodeId || e.name || ''}`;
            const arr = byKey.get(key);
            if (arr)
                arr.push(e);
            else
                byKey.set(key, [e]);
        }
        const out = [];
        for (const [key, members] of byKey) {
            const generated = members.every((m) => m.generated);
            // Prefer an authored member as the template source for a mixed group.
            const representative = members.find((m) => !m.generated) || members[0];
            const status = members.some((m) => m.status === 'diff') ? 'diff'
                : members.some((m) => m.status === 'new') ? 'new'
                    : 'synced';
            out.push({
                type: representative.type,
                key,
                label: representative.type === 'area' || representative.type === 'character'
                    ? (representative.name || '')
                    : (representative.payload.name || representative.nodeId || ''),
                count: members.length,
                status,
                generated,
                syncFailed: members.some((m) => m.syncFailed),
                representative,
                members,
            });
        }
        return out;
    }
    _buildItem(nodeId, node, depth = 0, seen = null) {
        const built = itemLib._buildWorldItemPayload(nodeId);
        if (!built)
            return null;
        const payload = built.payload;
        // Restore linkage hints for matching (not written to the library entry).
        const props = node.properties || {};
        if (props.library_id)
            payload.library_id = props.library_id;
        // Contained items that are their own graph nodes also get a standalone entry
        // so they're synced to the library as reusable items (box-of-cards case).
        if (depth === 0) {
            for (const nestedId of built.nested) {
                const n = worldState.getNode(nestedId);
                if (n && n.type === 'item')
                    this._nested.push(this._buildItem(nestedId, n, depth + 1));
            }
        }
        const match = this._findLibraryMatch('items', payload);
        const status = match ? (jsonDeepEqual(match.entry, this._clean(payload)) ? 'synced' : 'diff') : 'new';
        const generated = !!(props.generated ||
            props.source === 'worldpainter' ||
            (props.provenance && (props.provenance.generated || props.provenance.source === 'worldpainter' || props.provenance.recipe_id)));
        return { type: 'item', nodeId, payload, match, status, generated };
    }
    _buildWay(nodeId, node) {
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
            triggers: itemLib._extractTriggersFromNode(nodeId)
        };
        const match = this._findLibraryMatch('ways', payload);
        const status = match ? (jsonDeepEqual(match.entry, this._clean(payload)) ? 'synced' : 'diff') : 'new';
        const generated = !!(props.generated ||
            props.source === 'worldpainter' ||
            props.cell != null ||
            (props.provenance && (props.provenance.generated || props.provenance.source === 'worldpainter')));
        return { type: 'way', nodeId, payload, match, status, generated };
    }
    _buildArea(name) {
        const payload = libraryBrowser._buildAreaPayload(name);
        if (!payload)
            return null;
        const match = this._findLibraryMatch('areas', payload);
        const status = match ? (jsonDeepEqual(match.entry, this._clean(payload)) ? 'synced' : 'diff') : 'new';
        const generated = this._generatedAreaNames?.has(name) || false;
        return { type: 'area', name, payload, match, status, generated };
    }
    _buildCharacter(name) {
        const payload = libraryBrowser._buildCharacterPayload(name);
        if (!payload)
            return null;
        const match = this._findLibraryMatch('characters', payload);
        const status = match ? (jsonDeepEqual(match.entry, this._clean(payload)) ? 'synced' : 'diff') : 'new';
        return { type: 'character', name, payload, match, status };
    }
    // Drop id/library_id so comparison is about content, not linkage key.
    _clean(payload) {
        const c = { ...payload };
        delete c.id;
        delete c.library_id;
        return c;
    }
    // ── Opening an entity → existing DiffModal flow ─────────────────
    openEntity(entity) {
        if (entity.type === 'item' && entity.nodeId)
            return itemLib.saveWorldItem(entity.nodeId);
        if (entity.type === 'way')
            return InspectorWayView._saveToLibrary(entity.nodeId);
        if (entity.type === 'area' && entity.name)
            return libraryBrowser.saveAreaByName(entity.name);
        if (entity.type === 'character')
            return libraryBrowser.saveCharacterByName(entity.name);
    }
    openEntityByIndex(idx) {
        const list = this.groups.filter(g => this.filter === 'all' || g.type === this.filter);
        const g = list[idx];
        if (g)
            return this.openEntity(g.representative);
    }
    /**
     * Batch-sync every entity in the ACTIVE TAB that is new or differs, WITHOUT
     * showing the DiffModal. New entities are created; differing ones silently
     * overwrite their matched library entry. Already-synced entities are left
     * untouched. Generated entities are skipped (bug-526: procedurally painted
     * areas carry a grid `cell`; generated items/ways carry a provenance marker).
     * After the batch, saved entities flip to "synced ✓" in the list and any
     * failures stay marked.
     */
    async syncAll() {
        const inTab = (t) => {
            if (this.filter === 'all')
                return true;
            return t.replace(/s$/, '') === this.filter.replace(/s$/, '');
        };
        const groups = this.groups.filter(g => inTab(g.type));
        const pending = groups.filter(g => (g.status === 'new' || g.status === 'diff') && !g.generated);
        const skipped = groups.filter(g => (g.status === 'new' || g.status === 'diff') && g.generated).length;
        if (pending.length === 0) {
            toastInfo(skipped
                ? `Nothing to sync here (${skipped} generated entit${skipped === 1 ? 'y' : 'ies'} skipped).`
                : 'Everything is already in sync with the library.');
            return;
        }
        const diffCount = pending.filter(g => g.status === 'diff').length;
        if (diffCount > 0) {
            const confirmed = typeof window.Dialog?.confirm === 'function'
                ? await window.Dialog.confirm({
                    title: 'Overwrite Library Entries',
                    message: `Syncing will overwrite ${diffCount} existing library entr${diffCount === 1 ? 'y' : 'ies'}. Continue?`,
                    confirmLabel: 'Overwrite',
                    danger: true,
                })
                : true;
            if (!confirmed)
                return;
        }
        // Backup current library matches for undo before applying changes
        const backup = [];
        for (const g of pending) {
            const e = g.representative;
            const id = e.type === 'item' ? (e.match?.id || (e.payload.name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_'))
                : e.type === 'way' ? (e.match?.id || e.payload.id)
                    : e.type === 'area' ? (e.match?.id || (e.name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_'))
                        : (e.match?.id || e.name || '');
            const oldEntry = e.match?.entry ? JSON.parse(JSON.stringify(e.match.entry)) : null;
            backup.push({ type: e.type, id, oldEntry });
        }
        this._lastBatchBackup = backup;
        let updated = 0, failed = 0;
        for (const g of pending) {
            try {
                const res = await this._silentSave(g.representative);
                if (res && res.error)
                    throw new Error(res.error);
                g.members.forEach((m) => { m.status = 'synced'; m.syncFailed = false; });
                g.status = 'synced';
                updated++;
            }
            catch (err) {
                g.syncFailed = true;
                g.members.forEach((m) => { m.syncFailed = true; });
                failed++;
                console.error('syncAll failed for ' + (g.representative.nodeId || g.label || g.type), err);
            }
        }
        this._renderSummary();
        this._renderList();
        if (failed === 0) {
            toastInfo(`Synced ${updated} entit${updated === 1 ? 'y' : 'ies'} to library.`
                + (skipped ? ` Skipped ${skipped} generated.` : ''));
        }
        else {
            toastError(`Synced ${updated}, ${failed} failed.`
                + (skipped ? ` Skipped ${skipped} generated.` : ''));
        }
    }
    /**
     * Sync one template group individually to the library.
     */
    async syncGroup(g) {
        const e = g.representative;
        const id = e.type === 'item' ? (e.match?.id || (e.payload.name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_'))
            : e.type === 'way' ? (e.match?.id || e.payload.id)
                : e.type === 'area' ? (e.match?.id || (e.name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_'))
                    : (e.match?.id || e.name || '');
        const oldEntry = e.match?.entry ? JSON.parse(JSON.stringify(e.match.entry)) : null;
        this._lastBatchBackup = [{ type: e.type, id, oldEntry }];
        try {
            const res = await this._silentSave(e);
            if (res && res.error)
                throw new Error(res.error);
            g.members.forEach((m) => { m.status = 'synced'; m.syncFailed = false; });
            g.status = 'synced';
            toastInfo(`Synced ${g.label} to library.`);
        }
        catch (err) {
            g.syncFailed = true;
            g.members.forEach((m) => { m.syncFailed = true; });
            toastError(`Sync failed for ${g.label}: ${err?.message || err}`);
        }
        this._renderSummary();
        this._renderList();
    }
    /**
     * Restore the library entries that were modified during the last batch or individual sync.
     */
    async undoLastSync() {
        if (!this._lastBatchBackup || this._lastBatchBackup.length === 0) {
            toastInfo('No sync batch to undo.');
            return;
        }
        const backup = this._lastBatchBackup;
        this._lastBatchBackup = null;
        let reverted = 0;
        for (const item of backup) {
            if (item.oldEntry) {
                if (item.type === 'item') {
                    await ApiClient.saveLibraryItem({ id: item.id, ...item.oldEntry });
                }
                else {
                    const plural = item.type === 'way' ? 'ways' : item.type === 'area' ? 'areas' : 'characters';
                    await ApiClient.saveLibraryType(plural, { id: item.id, ...item.oldEntry });
                }
                reverted++;
            }
        }
        await this.refresh();
        toastInfo(`Undid sync batch: restored ${reverted} library entr${reverted === 1 ? 'y' : 'ies'}.`);
    }
    // True for values that should be treated as "no data" - empty string,
    // empty array, empty object, or null/undefined. A library field holding
    // real data must never be overwritten by one of these from the world copy.
    _isEmpty(value) {
        if (value === null || value === undefined)
            return true;
        if (typeof value === 'string')
            return value.trim() === '';
        if (Array.isArray(value))
            return value.length === 0;
        if (typeof value === 'object')
            return Object.keys(value).length === 0;
        return false;
    }
    // Merge the world payload over the matched library entry, but never let an
    // empty world value erase data the library already has. Non-empty world
    // values still win (the world is authoritative for fields it actually has).
    _mergeEntry(libEntry, worldPayload) {
        const out = { ...libEntry };
        for (const [key, value] of Object.entries(worldPayload)) {
            if (this._isEmpty(value) && !this._isEmpty(out[key]))
                continue;
            out[key] = value;
        }
        return out;
    }
    /**
     * Push one entity's world payload to the library, overwriting any existing
     * entry. No DiffModal - this is the "just do it" bulk path.
     */
    async _silentSave(e) {
        if (e.type === 'item') {
            const id = e.match?.id || (e.payload.name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_');
            const entry = e.match?.entry ? this._mergeEntry(e.match.entry, e.payload) : e.payload;
            return ApiClient.saveLibraryItem({ id, name: e.payload.name, ...entry });
        }
        if (e.type === 'way') {
            const id = e.match?.id || e.payload.id;
            const entry = e.match?.entry ? this._mergeEntry(e.match.entry, e.payload) : e.payload;
            return ApiClient.saveLibraryType('ways', { id, ...entry });
        }
        if (e.type === 'area') {
            const id = e.match?.id || (e.name || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_');
            const entry = e.match?.entry ? this._mergeEntry(e.match.entry, e.payload) : e.payload;
            return ApiClient.saveLibraryType('areas', { id, ...entry });
        }
        if (e.type === 'character') {
            const id = e.match?.id || e.name;
            const entry = e.match?.entry ? this._mergeEntry(e.match.entry, e.payload) : e.payload;
            return ApiClient.saveLibraryType('characters', { id, ...entry });
        }
        return null;
    }
    // Read-only section-by-section Library → World comparison for one entity.
    viewDiffByIndex(idx) {
        const list = this.groups.filter(g => this.filter === 'all' || g.type === this.filter);
        const e = list[idx]?.representative;
        if (!e || !e.match)
            return;
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
            title: 'Diff - ' + (e.payload.name || e.name || e.nodeId),
            name: e.match.id,
            readOnly: true
        });
    }
    // ── Render ──────────────────────────────────────────────────────
    _typeMeta(type) {
        return {
            item: { icon: '📦', label: 'Item' },
            way: { icon: '🚪', label: 'Way' },
            area: { icon: '🏠', label: 'Area' },
            character: { icon: '🧍', label: 'Character' }
        }[type] || {};
    }
    _renderSummary() {
        const inTab = (t) => {
            if (this.filter === 'all')
                return true;
            return t.replace(/s$/, '') === this.filter.replace(/s$/, '');
        };
        const tabGroups = this.groups.filter(g => inTab(g.type));
        const counts = { all: tabGroups.length, new: 0, diff: 0, synced: 0, generated: 0 };
        for (const g of tabGroups) {
            if (counts[g.status] !== undefined)
                counts[g.status]++;
            if (g.generated)
                counts.generated++;
        }
        const pending = tabGroups.filter(g => (g.status === 'new' || g.status === 'diff') && !g.generated);
        const willNew = pending.filter(g => g.status === 'new').length;
        const willDiff = pending.filter(g => g.status === 'diff').length;
        const willSkipGen = tabGroups.filter(g => (g.status === 'new' || g.status === 'diff') && g.generated).length;
        const undoBtn = document.getElementById('world-sync-undo-btn');
        if (undoBtn)
            undoBtn.style.display = (this._lastBatchBackup && this._lastBatchBackup.length > 0) ? 'inline-block' : 'none';
        const el = document.getElementById('world-sync-summary');
        if (!el)
            return;
        window.Lit.render(worldSyncTag `
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
                <div>
                    <span style="color:var(--text);font-weight:600;">${counts.all} groups</span>
                    - <span style="color:#3fb950;">${counts.new} new</span>
                    · <span style="color:#e3b341;">${counts.diff} different</span>
                    · <span style="color:var(--text-muted);">${counts.synced} synced</span>
                    · <span style="color:#58a6ff;">${counts.generated} generated</span>
                </div>
                <div style="display:flex;align-items:center;gap:12px;font-size:11px;">
                    <label style="cursor:pointer;display:inline-flex;align-items:center;gap:4px;">
                        <input type="checkbox" .checked=${this.showGenerated} @change=${() => VW.worldSync.toggleShowGenerated()}>
                        Show generated (${counts.generated})
                    </label>
                    <label style="cursor:pointer;display:inline-flex;align-items:center;gap:4px;">
                        <input type="checkbox" .checked=${this.showUnchanged} @change=${() => VW.worldSync.toggleShowUnchanged()}>
                        Show unchanged (${counts.synced})
                    </label>
                </div>
            </div>
            <div style="margin-top:4px;font-size:10px;color:var(--text-dim);">
                Sync All in this view would create ${willNew} new, overwrite ${willDiff} different (skip ${willSkipGen} generated, ${counts.synced} in sync).
            </div>`, el);
    }
    _renderList() {
        const el = document.getElementById('world-sync-list');
        if (!el)
            return;
        const inTab = (t) => {
            if (this.filter === 'all')
                return true;
            return t.replace(/s$/, '') === this.filter.replace(/s$/, '');
        };
        const list = this.groups
            .filter(g => inTab(g.type))
            .filter(g => {
            if (!this.showGenerated && g.generated)
                return false;
            if (!this.showUnchanged && g.status === 'synced')
                return false;
            return true;
        });
        if (list.length === 0) {
            window.Lit.render(worldSyncTag `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">No entities to review in current filter.</div>`, el);
            return;
        }
        window.Lit.render(worldSyncTag `${list.map((g, listIdx) => {
            const m = this._typeMeta(g.type);
            const rep = g.representative;
            const label = g.count > 1 ? `${g.label} ×${g.count}` : g.label;
            const sub = g.type === 'item' || g.type === 'way'
                ? (rep.payload.description || rep.nodeId)
                : (this.cache[g.type + 's']?.[rep.match?.id || ''] ? `library: ${rep.match?.id}` : 'not in library');
            const badge = g.syncFailed
                ? worldSyncTag `<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(248,81,73,0.15);color:#f85149;border:1px solid rgba(248,81,73,0.3);white-space:nowrap;">sync failed</span>`
                : g.status === 'new'
                    ? worldSyncTag `<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(63,185,80,0.15);color:#3fb950;border:1px solid rgba(63,185,80,0.3);white-space:nowrap;">new</span>`
                    : g.status === 'diff'
                        ? worldSyncTag `<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(227,179,65,0.15);color:#e3b341;border:1px solid rgba(227,179,65,0.3);white-space:nowrap;">differs</span>`
                        : worldSyncTag `<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(139,148,158,0.15);color:var(--text-muted);border:1px solid var(--border);white-space:nowrap;">synced ✓</span>`;
            const genBadge = g.generated
                ? worldSyncTag `<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:rgba(88,166,255,0.12);color:#58a6ff;border:1px solid rgba(88,166,255,0.3);white-space:nowrap;">generated</span>`
                : '';
            const diffBtn = rep.match
                ? worldSyncTag `<button class="btn btn-sm" style="flex-shrink:0;" @click=${(ev) => { ev.stopPropagation(); VW.worldSync.viewDiffByIndex(listIdx); }}>diff</button>`
                : '';
            const syncBtn = (g.status === 'new' || g.status === 'diff')
                ? worldSyncTag `<button class="btn btn-sm btn-green" style="flex-shrink:0;margin-left:4px;" @click=${(ev) => { ev.stopPropagation(); VW.worldSync.syncGroup(g); }}>⬇ sync</button>`
                : '';
            return worldSyncTag `<div class="agent-item" style="cursor:pointer;padding:5px 10px;border-left:3px solid var(--border);" @click=${() => VW.worldSync.openEntityByIndex(listIdx)}>
                <span style="font-size:13px;margin-right:4px;">${m.icon}</span>
                <div style="flex:1;min-width:0;">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <span class="agent-name" style="font-size:12px;font-weight:600;">${label}</span>
                        ${badge}${genBadge}
                    </div>
                    <div style="font-size:10px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${sub}</div>
                </div>
                <div style="display:flex;align-items:center;gap:4px;">
                    ${diffBtn}
                    ${syncBtn}
                </div>
            </div>`;
        })}`, el);
    }
}
const worldSync = new WorldSync();
window.worldSync = worldSync;
window.WorldSync = WorldSync;
if (typeof window.VW === 'object' && window.VW) {
    window.VW.worldSync = worldSync;
}
