/**
 * ApiClient — Backend HTTP calls for the VirtualWorld engine
 *
 * @module api — the single HTTP client for every UI → engine call
 * @contributes ApiClientImpl.* (actions, graph CRUD, items, saves, scenario ops) + runAction
 * @powers every button/panel that talks to the Flask engine, and the graph's data fetches
 * @relates used by world-state, graph, inspector, item library, agent-engine, main
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// Declared as `ApiClientImpl` and published onto `window` at the bottom of this
// file: `static/js/types/globals.d.ts` already declares a global `const ApiClient`
// (and a global `const api`) so unconverted consumers typecheck, and a top-level
// `class ApiClient` would collide with it. The runtime globals are unchanged.
class ApiClientImpl {
    /**
     * Never let a raw server error reach the UI (task-444 Phase 4).
     *
     * The command bar logs `data.error` straight to the event stream, and the
     * default Flask 500 body is a traceback. Both a JSON `{error: "Traceback
     * (most recent call last)..."}` and a non-JSON body would otherwise be shown
     * to the player. A short status message is the readable thing to surface.
     */
    static _errorMessage(resp: Response, data: ApiResult | null): string {
        const raw = (data && typeof data.error === 'string') ? data.error : '';
        if (raw && !/\bTraceback\b|File "\S/.test(raw)) return raw;
        const status = `${resp.status}${resp.statusText ? ' ' + resp.statusText : ''}`;
        return `Request failed (${status})`;
    }

    /** Generic POST helper */
    static async post(url: string, payload?: unknown): Promise<ApiResult> {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            return { ...data, error: ApiClientImpl._errorMessage(resp, data), http_status: resp.status };
        }
        return data;
    }

    /**
     * Apply a list of graph ops as ONE atomic batch request + ONE undo snapshot.
     * op shape: { type: 'create_node'|'attach'|'detach'|'delete_node'|'update_node', payload: {...} }
     * See routes/graph_ops.py _apply_batch_op for payloads. Returns { status, applied, errors }.
     */
    static async batchGraph(ops: unknown[]): Promise<ApiResult> {
        return this.post('/api/graph/batch', { ops });
    }

    /** Generic GET helper */
    static async get(url: string): Promise<ApiResult> {
        const resp = await fetch(url);
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            return { ...data, error: ApiClientImpl._errorMessage(resp, data), http_status: resp.status };
        }
        return data;
    }

    /**
     * Declare a soak order for a character (task-481): they run on a policy for
     * the span instead of taking attended turns.
     */
    static async declareSoak(payload: unknown): Promise<ApiResult> {
        return this.post('/api/world/soak', payload);
    }

    /** Drop a character's soak order (defaults to the active character). */
    static async cancelSoak(charName: string | null = null): Promise<ApiResult> {
        const query = charName ? '?character=' + encodeURIComponent(charName) : '';
        const resp = await fetch('/api/world/soak' + query, { method: 'DELETE' });
        return resp.json().catch(() => ({}));
    }

    /** Status-condition catalog (for the inspector's condition editor) */
    static async conditionsCatalog(): Promise<ApiResult> {
        return this.get('/api/conditions');
    }

    /** POST with callback (for legacy compatibility) */
    static postCallback(url: string, payload: unknown, callback?: (res: ApiResult) => void): void {
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(res => {
            if (res.error) { toastError("Error: " + res.error); }
            else if (callback) callback(res);
            else worldState.fetch();
        })
        .catch(err => console.error('[apiPost] fetch error:', err));
    }

    /** Game actions */
    static async action(command: string, charName?: string, opts?: { enforceSlots?: boolean }): Promise<ApiResult> {
        const body: { command: string; character?: string; enforce_slots?: boolean } = { command };
        if (charName) body.character = charName;
        if (opts?.enforceSlots) body.enforce_slots = true;
        return this.post('/api/action', body);
    }

    /** Autocomplete candidate options for verb & prefix (task-6) */
    static async getAutocomplete(verb: string, prefix = '', charName: string | null = null): Promise<ApiResult> {
        const body: { verb: string; prefix: string; character?: string } = { verb, prefix };
        if (charName) body.character = charName;
        return this.post('/api/autocomplete', body);
    }

    /** Scene snapshot for the human turn panel (task-333 Phase 1) */
    static async getScene(playerName: string): Promise<ApiResult> {
        return this.get('/api/scene/' + encodeURIComponent(playerName));
    }

    /** Reset world to initial state */
    static async resetWorld(): Promise<ApiResult> {
        const resp = await fetch('/api/reset', { method: 'POST' });
        return resp.json();
    }

    /** Undo the last snapshot (e.g. restore state deleted by reset) */
    static async undo(): Promise<ApiResult> {
        return this.post('/api/undo', {});
    }

    /** Redo a previously undone state */
    static async redo(): Promise<ApiResult> {
        return this.post('/api/redo', {});
    }

    /** Narrative emote */
    static async emote(actor: string, emoteText: string): Promise<ApiResult> {
        return this.post('/api/emote', { actor, emote: emoteText });
    }

    /** Set active player */
    static async setActivePlayer(name: string): Promise<ApiResult> {
        return this.post('/api/players/active', { name });
    }

    /** Create character */
    static async createCharacter(name: string): Promise<ApiResult> {
        return this.post('/api/players', { name });
    }

    /** Delete character */
    static async deleteCharacter(name: string): Promise<ApiResult> {
        const resp = await fetch('/api/players/' + encodeURIComponent(name), { method: 'DELETE' });
        return resp.json();
    }

    /** Kill character (set HP=0, state=dead, spawn body) */
    static async killCharacter(name: string): Promise<ApiResult> {
        const resp = await fetch('/api/players/' + encodeURIComponent(name) + '/kill', { method: 'POST' });
        return resp.json();
    }

    /** Update character personality/rename */
    static async updateCharacter(name: string, data: unknown): Promise<ApiResult> {
        const resp = await fetch('/api/players/' + encodeURIComponent(name), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return resp.json();
    }

    static async importPlayer(charData: unknown): Promise<ApiResult> {
        const resp = await fetch('/api/players/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(charData)
        });
        return resp.json();
    }

    // --- Player Movement & Speech ---

    static async movePlayerToRoom(name: string, area: string): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/move`, { area });
    }

    static async playerSpeak(name: string, text: string, area?: string): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/speak`, { text, area });
    }

    // --- Build API ---

    static async createRoom(data: unknown): Promise<ApiResult> {
        return this.post('/api/build/area', data);
    }

    static async createItem(data: unknown): Promise<ApiResult> {
        return this.post('/api/build/item', data);
    }

    static async connectRooms(data: unknown): Promise<ApiResult> {
        return this.post('/api/build/connect', data);
    }

    static async placeItemFromLibrary(target: { type: string; id: string; name: string }, itemId: string): Promise<ApiResult> {
        const payload: Record<string, unknown> = {};
        if (target.type === 'container') payload.container = target.id;
        else if (target.type === 'character') payload.character = target.id;
        else payload.area = target.name;
        return this.post(`/api/library/items/${encodeURIComponent(itemId)}/place`, payload);
    }

    // --- Graph API ---

    static async getGraphNodes(): Promise<ApiResult> {
        const resp = await fetch('/api/graph/nodes');
        return resp.json();
    }

    static async getGraphEdges(): Promise<ApiResult> {
        const resp = await fetch('/api/graph/edges');
        return resp.json();
    }

    /** World scope cards. `flat=true` returns every scope depth-first with a
     *  `depth` field, for the graph view's scope picker (task-397). */
    static async getWorldScopes(flat = false): Promise<ApiResult> {
        const resp = await fetch(`/api/world/scopes${flat ? '?flat=1' : ''}`);
        return resp.json();
    }

    /** One scope's vis-loadable subgraph ({nodes, edges}) — the graph view
     *  loads this instead of the whole world when a scope is selected.
     *  Level-scoped by default (own areas only); pass `descendants` for the
     *  whole subtree. */
    static async getScopeSubgraph(scopeId: string, includeItems = true, descendants = false): Promise<ApiResult> {
        const resp = await fetch(
            `/api/world/scopes/${encodeURIComponent(scopeId)}/subgraph`
            + `?include_items=${includeItems ? 1 : 0}&descendants=${descendants ? 1 : 0}`);
        if (!resp.ok) throw new Error(`scope subgraph failed: ${resp.status}`);
        return resp.json();
    }

    /** One scope's painted grid payload ({scope, grid, layers, reference, …}).
     *  Used by the graph background's "fit to painted grid" action. */
    static async getWorldGrid(scopeId: string): Promise<ApiResult> {
        const resp = await fetch(`/api/world/scopes/${encodeURIComponent(scopeId)}/grid`);
        if (!resp.ok) throw new Error(`scope grid failed: ${resp.status}`);
        return resp.json();
    }

    /** Persist a scope's map-layout offset (cell units) — the graph canvas zone
     *  drag (task-523). Pass `reset: true` (and no x/y) to return the zone to
     *  its painted position. Returns `{status, id, map_offset}`. */
    static async setScopeOffset(scopeId: string, offset: { x?: number; y?: number; reset?: boolean } = {}): Promise<ApiResult> {
        const resp = await fetch(`/api/world/scopes/${encodeURIComponent(scopeId)}/offset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(offset && offset.reset
                ? { reset: true }
                : { x: Number(offset.x) || 0, y: Number(offset.y) || 0 })
        });
        if (!resp.ok) throw new Error(`scope offset failed: ${resp.status}`);
        return resp.json();
    }

    static async updateNode(nodeId: string, data: unknown): Promise<boolean> {
        const resp = await fetch(`/api/graph/node/${encodeURIComponent(nodeId)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return resp.ok;
    }

    /** Reassign areas to a scope — **membership only** (task-539).
     *
     * This is deliberately not `updateNode({properties: {world_scope_id}})`:
     * membership also has to move in the manifest's `area_ids` mirror, and a
     * multi-selection has to land as one undo step. `add`/`remove` are arrays;
     * leaving a scope releases any cell the area was parked on there, while a cell
     * it holds in the target scope is kept. */
    static async setScopeAreas(scopeId: string, add: string[] = [], remove: string[] = []): Promise<ApiResult> {
        const resp = await fetch(`/api/world/scopes/${encodeURIComponent(scopeId)}/areas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ add, remove })
        });
        const data = await resp.json().catch(() => null);
        if (!resp.ok) throw new Error((data && data.error) || `scope areas failed: ${resp.status}`);
        return data;
    }

    /** Duplicate an area / item / way / character — one atomic write on the
     *  backend. `includeChildren=false` clones only the node (+ triggers),
     *  skipping its attached items. */
    static async duplicateNode(nodeId: string, includeChildren = true): Promise<ApiResult> {
        const resp = await fetch('/api/graph/duplicate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: nodeId, include_children: !!includeChildren })
        });
        return resp.json();
    }

    static async uploadNodeImage(nodeId: string, file: File, kind = 'full', expression = 'neutral'): Promise<ApiResult> {
        const form = new FormData();
        form.append('file', file);
        form.append('kind', kind);
        form.append('expression', expression);
        const resp = await fetch(`/api/graph/node/${encodeURIComponent(nodeId)}/image`, {
            method: 'POST',
            body: form
        });
        return resp.json();
    }

    /** Remove one expression-pack image slot (kind + expression). */
    static async removeExpressionImage(nodeId: string, kind = 'full', expression = 'neutral'): Promise<ApiResult> {
        const resp = await fetch(`/api/graph/node/${encodeURIComponent(nodeId)}/image/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ kind, expression })
        });
        return resp.json();
    }

    static async removeNodeImage(nodeId: string): Promise<boolean> {
        return ApiClientImpl.updateNode(nodeId, { properties: { image: null } });
    }

    /** Upload the graph's background map; returns { image: '/static/images/backgrounds/…' }. */
    static async uploadBackgroundImage(file: File): Promise<ApiResult> {
        const form = new FormData();
        form.append('file', file);
        const resp = await fetch('/api/graph/background/image', { method: 'POST', body: form });
        return resp.json();
    }

    /** Persist the background map's path + transform on the world (scenario-level). */
    static async saveGraphBackground(background: unknown): Promise<ApiResult> {
        return ApiClientImpl.post('/api/graph/background', background);
    }

    static async renameNode(nodeId: string, newId: string): Promise<ApiResult> {
        return ApiClientImpl.post(`/api/graph/node/${encodeURIComponent(nodeId)}/rename`, { new_id: newId });
    }

    static async moveItemToRoom(nodeId: string, area?: string, container?: string, character?: string, targetType?: string, targetId?: string, relation?: string): Promise<ApiResult> {
        const payload: Record<string, unknown> = {};
        if (targetType && targetId) {
            payload.target_type = targetType;
            payload.target_id = targetId;
            if (relation) payload.relation = relation;
        } else {
            if (area) payload.area = area;
            if (container) payload.container = container;
            if (character) payload.character = character;
        }
        return ApiClientImpl.post(`/api/graph/item/${encodeURIComponent(nodeId)}/move`, payload);
    }

    static async deleteNode(nodeId: string): Promise<ApiResult> {
        const resp = await fetch(`/api/graph/node/${encodeURIComponent(nodeId)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async updateEdge(source: string, target: string, data: Record<string, unknown>): Promise<ApiResult> {
        return this.post('/api/graph/edge/update', { source, target, ...data });
    }

    static async deleteEdge(source: string, target: string, type: string): Promise<ApiResult> {
        const resp = await fetch('/api/graph/edge', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, target, type })
        });
        return resp.json();
    }

    static async flipEdge(source: string, target: string, type: string): Promise<ApiResult> {
        return this.post('/api/graph/edge/flip', { source, target, type });
    }

    static async createNode(data: unknown): Promise<ApiResult> {
        return this.post('/api/graph/node', data);
    }

    static async createEdge(source: string, target: string, type: string, properties: Record<string, unknown> = {}): Promise<ApiResult> {
        return this.post('/api/graph/edge', { source, target, type, properties });
    }

    // --- Item Registry (Library) API ---

    static async getLibraryItems(): Promise<ApiResult> {
        const resp = await fetch('/api/library/items');
        return resp.json();
    }

    static async saveLibraryItem(payload: unknown): Promise<ApiResult> {
        const resp = await fetch('/api/library/items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return resp.json();
    }

    static async deleteLibraryItem(id: string): Promise<ApiResult> {
        const resp = await fetch(`/api/library/items/${encodeURIComponent(id)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async refreshFromLibrary(nodeId: string, sections?: string[], templateId?: string, entries?: Record<string, unknown>): Promise<ApiResult> {
        const body: Record<string, unknown> = { node_id: nodeId };
        if (sections) body.sections = sections;
        if (templateId) body.template_id = templateId;
        if (entries && Object.keys(entries).length) body.entries = entries;
        return this.post('/api/library/refresh-to-world', body);
    }

    /**
     * Unbind a node from its library template. The node keeps its current data —
     * this only removes the link, so a hand-fixed copy is no longer overwritten
     * by the next refresh (task-289/317).
     * @param {string} nodeId
     * @returns {Promise<object>} report: status, was_linked, template_id
     */
    static async breakTemplateLink(nodeId: string): Promise<ApiResult> {
        return this.post('/api/library/break-template-link', { node_id: nodeId });
    }

    static async refreshWayFromLibrary(nodeId: string, sections?: string[]): Promise<ApiResult> {
        const body: Record<string, unknown> = { node_id: nodeId };
        if (sections) body.sections = sections;
        return this.post('/api/library/refresh-to-world', body);
    }

    // --- Character Registry API ---

    static async saveCharacterToRegistry(charId: string, data: unknown): Promise<ApiResult> {
        const resp = await fetch('/api/library/characters', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: charId, data })
        });
        return resp.json();
    }

    static async getCharactersFromLibrary(): Promise<ApiResult> {
        const resp = await fetch('/api/library/characters');
        return resp.json();
    }

    // --- Unified Library API ---

    static async getLibraryEntities(): Promise<ApiResult> {
        const resp = await fetch('/api/library/entities');
        return resp.json();
    }

    static async getLibraryType(type: string): Promise<ApiResult> {
        const resp = await fetch(`/api/library/${encodeURIComponent(type)}`);
        return resp.json();
    }

    /** Fetch multiple registries in one round-trip. @param {string[]} types */
    static async getLibraryTypes(types: string[]): Promise<ApiResult> {
        const q = types && types.length ? `?types=${encodeURIComponent(types.join(','))}` : '';
        const resp = await fetch(`/api/library/all${q}`);
        return resp.json();
    }

    static async saveLibraryType(type: string, payload: unknown): Promise<ApiResult> {
        const resp = await fetch(`/api/library/${encodeURIComponent(type)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return resp.json();
    }

    static async deleteLibraryType(type: string, id: string): Promise<ApiResult> {
        const resp = await fetch(`/api/library/${encodeURIComponent(type)}/${encodeURIComponent(id)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async importCharacterFromLibrary(charId: string, options: Record<string, unknown> = {}): Promise<ApiResult> {
        return this.post(`/api/library/import/character/${encodeURIComponent(charId)}`, options);
    }

    static async importRoomFromLibrary(roomId: string, options: Record<string, unknown> = {}): Promise<ApiResult> {
        return this.post(`/api/library/import/area/${encodeURIComponent(roomId)}`, options);
    }

    static async importWayFromLibrary(wayId: string, options: Record<string, unknown> = {}): Promise<ApiResult> {
        return this.post(`/api/library/import/way/${encodeURIComponent(wayId)}`, options);
    }

    /** Reconnect a way to another pair of areas (POST /api/graph/way/reconnect). */
    static async reconnectWays(wayId: string, roomA: string, roomB: string, dirA = '', dirB = ''): Promise<ApiResult> {
        return this.post('/api/graph/way/reconnect', { way_id: wayId, area_a: roomA, area_b: roomB, dir_a: dirA, dir_b: dirB });
    }

    // --- World Save/Load ---

    static async saveWorld(): Promise<ApiResult> {
        const resp = await fetch('/api/save');
        return resp.json();
    }

    static async loadWorld(data: unknown): Promise<ApiResult> {
        return this.post('/api/load', data);
    }

    // --- Turn System ---

    static async applyTurn(): Promise<void> {
        await fetch('/api/turn/apply', { method: 'POST' });
    }

    static async clearTurnEvents(): Promise<void> {
        await fetch('/api/turn/clear', { method: 'POST' });
    }

    // --- Ghost Mode ---

    static async getGhostMode(): Promise<ApiResult> {
        const resp = await fetch('/api/settings/ghost_mode');
        return resp.json();
    }

    static async setGhostMode(enabled: boolean): Promise<ApiResult> {
        return this.post('/api/settings/ghost_mode', { ghost_mode: enabled });
    }

    // --- Mature Content (task-206) ---

    static async getMatureContent(): Promise<ApiResult> {
        const resp = await fetch('/api/settings/mature_content');
        return resp.json();
    }

    static async setMatureContent(enabled: boolean): Promise<ApiResult> {
        return this.post('/api/settings/mature_content', { mature_content: enabled });
    }

    // --- Auto-Generate Descriptions ---

    static async setAutoGenerateDescriptions(enabled: boolean): Promise<ApiResult> {
        return this.post('/api/settings/auto_generate_descriptions', { auto_generate_descriptions: enabled });
    }

    // --- World Lore API ---

    static async getWorldLore(): Promise<ApiResult> {
        const resp = await fetch('/api/world/lore');
        return resp.json();
    }

    static async setWorldLore(lore: unknown): Promise<ApiResult> {
        return this.post('/api/world/lore', { lore });
    }

    static async addWorldLoreEntry(entry: unknown): Promise<ApiResult> {
        return this.post('/api/world/lore/entry', entry);
    }

    static async updateWorldLoreEntry(entryId: string, data: unknown): Promise<ApiResult> {
        return this.post(`/api/world/lore/entry/${encodeURIComponent(entryId)}`, data);
    }

    static async deleteWorldLoreEntry(entryId: string): Promise<ApiResult> {
        const resp = await fetch(`/api/world/lore/entry/${encodeURIComponent(entryId)}`, { method: 'DELETE' });
        return resp.json();
    }

    // --- Per-Character Memory API ---

    static async getPlayerMemories(name: string): Promise<ApiResult> {
        const resp = await fetch(`/api/players/${encodeURIComponent(name)}/memories`);
        return resp.json();
    }

    static async setPlayerMemories(name: string, memories: unknown): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories`, { memories });
    }

    static async addPlayerMemory(name: string, entry: unknown): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/entry`, entry);
    }

    static async deletePlayerMemory(name: string, entryId: string): Promise<ApiResult> {
        const resp = await fetch(`/api/players/${encodeURIComponent(name)}/memories/entry/${encodeURIComponent(entryId)}`, { method: 'DELETE' });
        return resp.json();
    }

    static async updatePlayerMemory(name: string, entryId: string, data: unknown): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/entry/${encodeURIComponent(entryId)}`, data);
    }

    static async clearPlayerMemories(name: string): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/clear`, {});
    }

    static async suppressPlayerMemory(name: string, data: unknown): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/suppress`, data);
    }

    static async unblockPlayerMemory(name: string, data: unknown): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/unblock`, data);
    }

    static async clearExpiredSuppressions(name: string, currentTick: number): Promise<ApiResult> {
        return this.post(`/api/players/${encodeURIComponent(name)}/memories/clear-expired`, { current_tick: currentTick });
    }

    static async getAreaDescription(): Promise<ApiResult> {
        const resp = await fetch('/api/area/description');
        return resp.json();
    }

    // --- Save/Load Game & Scenario ---

    /** Save a new named snapshot, or overwrite an existing slot via `slot`. */
    static async saveGame(name: string, slot?: string): Promise<ApiResult> {
        const body: { name: string; slot?: string } = { name };
        if (slot) body.slot = slot;
        return this.post('/api/save-game', body);
    }

    static async listSaveGames(): Promise<ApiResult> {
        const resp = await fetch('/api/save-games');
        return resp.json();
    }

    static async loadGame(filename: string): Promise<ApiResult> {
        return this.post(`/api/load-game/${encodeURIComponent(filename)}`);
    }

    static async deleteSaveGame(filename: string): Promise<ApiResult> {
        const resp = await fetch(`/api/save-game/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        return resp.json();
    }

    /** Delete every user save in one request; the autosave slot is kept unless
     *  `includeAutosave` is true (bug-42). */
    static async deleteAllSaveGames(includeAutosave = false): Promise<ApiResult> {
        return this.post('/api/save-games/delete-all', { include_autosave: !!includeAutosave });
    }

    static async renameSaveGame(filename: string, name: string): Promise<ApiResult> {
        return this.post(`/api/save-game/${encodeURIComponent(filename)}/rename`, { name });
    }

    static async saveScenario(name: string): Promise<ApiResult> {
        return this.post('/api/save-scenario', { name });
    }
}

// Singleton — published under both names consumers use. See the note on the
// class declaration for why these are assignments rather than top-level consts.
const globals = window as unknown as { ApiClient: typeof ApiClientImpl; api: typeof ApiClientImpl };
globals.ApiClient = ApiClientImpl;
globals.api = ApiClientImpl;

/** Run a game action and log the result to the event stream, then refresh state. */
(window as unknown as { runAction(cmd: string, charName?: string, opts?: { enforceSlots?: boolean }): Promise<void> }).runAction =
async function(cmd: string, charName?: string, opts?: { enforceSlots?: boolean }) {
    const body: { command: string; character?: string; enforce_slots?: boolean } = { command: cmd };
    if (charName) body.character = charName;
    if (opts?.enforceSlots) body.enforce_slots = true;
    const resp = await fetch('/api/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });
    const data = await resp.json();
    if (data?.output) events.log(data.output, 'system-msg');
    await worldState.fetch();
    // Auto-generate equipment description after a SUCCESSFUL equip/unequip.
    // /api/action reports `success` so a failed wear/remove (e.g. "can't be
    // equipped") doesn't rewrite the appearance.
    const cmdLower = cmd.trim().toLowerCase();
    if (data.success === true && config.autoGenerateDescriptions && (cmdLower.startsWith('wear ') || cmdLower.startsWith('remove ') || cmdLower.startsWith('unequip '))) {
        const char = charName || worldState.activePlayer;
        const agentView = (window as unknown as {
            InspectorAgentView?: { _generateDescription?(name: string): Promise<unknown> };
        }).InspectorAgentView;
        if (char && agentView?._generateDescription) {
            agentView._generateDescription(char).catch(() => {});
        }
    }
};

// Type declarations sit below the first value statement on purpose: TypeScript
// drops a file's leading JSDoc when the first statement is type-only, which
// would strip the `@module` header `tools/js_module_index.py` reads.
type ApiResult = Record<string, any>;