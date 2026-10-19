"use strict";
/**
 * WorldState - Reactive state management
 * Fetches world state from the backend and notifies listeners
 *
 * @module world-state - reactive cache of the server's `/api/state` payload
 * @contributes the `worldState` singleton: data, fetch/poll, getNode/players/areas helpers; the `/api/events` live feed (external edits + streamed world-advance ticks)
 * @powers every panel's view of the world (graph, inspector, agent list, turn panel)
 * @relates fetches via api.js and the `/api/events` SSE stream; emits `state:updated`
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
class WorldState {
    constructor() {
        this.data = null; // raw state from /api/state
        this.runtimeData = null;
        this._runtimeFocus = [];
        this._runtimeInflight = null;
        this._runtimeRefetchRequested = false;
        this._runtimeRequestIds = [];
        this._runtimeGeneration = 0;
        this._listeners = {};
        this._pollTimer = null;
        this._equipSlots = null;
        this._inflight = null;
        this._refetchRequested = false;
    }
    /** Subscribe to state changes */
    on(event, callback) {
        if (!this._listeners[event])
            this._listeners[event] = [];
        this._listeners[event].push(callback);
        if (event === 'update' && this.data) {
            callback(this.data); // Immediately notify if we have data
        }
    }
    _emit(event, data) {
        const subs = this._listeners[event] || [];
        subs.forEach(cb => cb(data));
    }
    /** Sync backend turn events into the frontend area event log */
    _syncTurnEvents(state) {
        if (!window.events || !state.turn_events)
            return;
        for (const evt of state.turn_events) {
            if (!evt.area)
                continue;
            const roomLog = events._areaEventLog[evt.area];
            // Only add if we don't already have this event (check by tick+actor+description)
            if (!roomLog) {
                events._areaEventLog[evt.area] = [{
                        tick: evt.tick,
                        actor: evt.actor,
                        action: evt.action,
                        result: evt.description || ''
                    }];
            }
            else {
                const exists = roomLog.some((e) => e.tick === evt.tick && e.actor === evt.actor && e.action === evt.action);
                if (!exists) {
                    roomLog.push({
                        tick: evt.tick,
                        actor: evt.actor,
                        action: evt.action,
                        result: evt.description || ''
                    });
                    if (roomLog.length > 50)
                        roomLog.shift();
                }
            }
        }
    }
    /** Fetch latest state from backend.
     * @param lite - when true, fetch the trimmed lite payload first, then
     *               kick off a background full fetch. The initial render
     *               uses the lite payload; the full payload replaces it
     *               when it arrives.
     */
    async fetch(lite = false) {
        // While a live character turn owns runtime focus, every state refresh
        // must use that character's current scope. Do not let secondary callers
        // (or an SSE-triggered refresh) fall back to the whole-world endpoint.
        if (this._runtimeFocus.length)
            return this.fetchRuntime();
        // Coalesce concurrent fetches into one. app.py broadcasts `world_changed`
        // for EVERY mutating /api/ call, so the SSE (connectLiveEdits) refetches
        // state AND the call site often fetches again - two full /api/state
        // downloads for a single edit (14 MB on a large world). While one fetch
        // is in flight a second request joins it; if a change landed during it,
        // callers wait for one trailing fetch rather than reading stale state.
        if (this._inflight) {
            this._refetchRequested = true;
            return this._inflight;
        }
        let fetchedFullState = !lite;
        this._inflight = (async () => {
            let state;
            let fetchLite = lite;
            do {
                this._refetchRequested = false;
                state = await this._fetchNow(fetchLite);
                if (!fetchLite)
                    fetchedFullState = true;
                fetchLite = false;
            } while (this._refetchRequested);
            return state;
        })();
        try {
            return await this._inflight;
        }
        finally {
            this._inflight = null;
            if (!fetchedFullState) {
                void this.fetch(false);
            }
        }
    }
    /** Set the live-turn working set; an empty list restores global refreshes. */
    setRuntimeFocus(characterIds) {
        const ids = [...new Set(characterIds.filter(Boolean))].sort();
        if (ids.length === this._runtimeFocus.length
            && ids.every((id, index) => id === this._runtimeFocus[index]))
            return;
        this._runtimeFocus = ids;
        this._runtimeGeneration += 1;
        this.runtimeData = null;
    }
    setRuntimeFocusForCharacter(name) {
        const id = name ? this.players?.[name]?.id : null;
        this.setRuntimeFocus(id ? [id] : []);
    }
    /** Fetch a character-scoped projection without mutating the global cache. */
    async fetchRuntime(characterIds = this._runtimeFocus) {
        const ids = [...new Set(characterIds.filter(Boolean))].sort();
        if (!ids.length)
            throw new Error('A focused runtime snapshot requires a character ID.');
        this._runtimeRequestIds = ids;
        if (this._runtimeInflight) {
            this._runtimeRefetchRequested = true;
            return this._runtimeInflight;
        }
        this._runtimeInflight = (async () => {
            let state;
            do {
                this._runtimeRefetchRequested = false;
                const requestIds = this._runtimeRequestIds;
                const generation = this._runtimeGeneration;
                const query = requestIds.map(id => `character_id=${encodeURIComponent(id)}`).join('&');
                const response = await fetch(`/api/runtime/state?${query}`);
                state = await response.json();
                if (!response.ok || state?.snapshot_type !== 'character_runtime') {
                    throw new Error(state?.error || `Runtime state request failed (${response.status}).`);
                }
                if (generation === this._runtimeGeneration) {
                    this.runtimeData = state;
                    this.applyRuntimeSnapshot(state);
                    this._emit('runtime:update', state);
                    const bus = window.appEvents;
                    if (bus)
                        bus.emit('runtime:updated', state);
                }
            } while (this._runtimeRefetchRequested);
            return state;
        })();
        try {
            return await this._runtimeInflight;
        }
        finally {
            this._runtimeInflight = null;
        }
    }
    runtimePlayer(name) {
        if (this._runtimeFocus.length) {
            return this.runtimeData?.players?.[name] || null;
        }
        return this.runtimeData?.players?.[name] || this.data?.players?.[name] || null;
    }
    /** Patch the global/editor cache with the focused projection without refetching the world. */
    applyRuntimeSnapshot(snapshot) {
        const global = this.data;
        if (!global || snapshot?.snapshot_type !== 'character_runtime')
            return false;
        const graph = global.graph || (global.graph = { nodes: {}, edges: [] });
        graph.nodes ||= {};
        graph.edges ||= [];
        const runtimeNodes = snapshot.graph?.nodes || {};
        const runtimeNodeIds = new Set(Object.keys(runtimeNodes));
        const playerNodeIds = new Set(Object.values(snapshot.player_node_ids || {}));
        Object.assign(graph.nodes, runtimeNodes);
        const edgeKey = (edge) => JSON.stringify([
            edge.source, edge.target, edge.type, edge.properties || {}
        ]);
        const edges = new Map();
        for (const edge of graph.edges) {
            const replaceScopedEdge = runtimeNodeIds.has(edge.source)
                && runtimeNodeIds.has(edge.target);
            const replacePlayerLocation = playerNodeIds.has(edge.source) && edge.type === 'in';
            if (!replaceScopedEdge && !replacePlayerLocation)
                edges.set(edgeKey(edge), edge);
        }
        for (const edge of snapshot.graph?.edges || [])
            edges.set(edgeKey(edge), edge);
        graph.edges = [...edges.values()];
        global.players ||= {};
        Object.assign(global.players, snapshot.players || {});
        global.areas_by_id ||= {};
        global.areas ||= {};
        for (const [areaId, area] of Object.entries(snapshot.areas_by_id || {})) {
            const previous = global.areas_by_id[areaId];
            if (previous?.name && global.areas[previous.name]?.id === areaId) {
                delete global.areas[previous.name];
            }
            global.areas_by_id[areaId] = area;
            if (area?.name)
                global.areas[area.name] = area;
        }
        for (const key of [
            'active_player', 'game_time', 'time_ticks', 'time_per_tick_minutes',
            'turn_number', 'game_day', 'game_month', 'game_year', 'mature_content',
            'scenario_ended', '_restart_requested'
        ]) {
            if (Object.prototype.hasOwnProperty.call(snapshot, key))
                global[key] = snapshot[key];
        }
        if (Object.prototype.hasOwnProperty.call(snapshot, 'turn_events')) {
            global.turn_events = snapshot.turn_events;
        }
        this._syncTurnEvents(snapshot);
        this._emit('update', global);
        const bus = window.appEvents;
        if (bus)
            bus.emit('state:updated', global);
        return true;
    }
    async _fetchNow(lite) {
        try {
            const url = lite ? '/api/state?lite=1' : '/api/state';
            const resp = await fetch(url);
            const state = await resp.json();
            this.data = state;
            if (state && typeof state === 'object') {
                const scName = (typeof state._scenario_name === 'string' && state._scenario_name.trim()) ? state._scenario_name.trim() : '';
                if (typeof document !== 'undefined' && document.body) {
                    document.body.dataset.scenarioName = scName;
                    const nameText = document.getElementById('scenario-name-text');
                    if (nameText) {
                        nameText.textContent = scName || 'unnamed';
                    }
                }
            }
            this._syncTurnEvents(state);
            // Rebuild the turn queue if the roster changed (new/dead characters)
            // so freshly added characters join the initiative loop mid-run.
            const tq = window.TurnQueue;
            if (tq)
                tq.reconcile();
            this._emit('update', state);
            const bus = window.appEvents;
            if (bus)
                bus.emit('state:updated', state);
            return state;
        }
        catch (e) {
            console.error('State fetch failed:', e);
            return this.data;
        }
    }
    /**
     * Start polling for spectator mode.
     *
     * Spectator-only, and gated on the `spectator-mode` checkbox (which ships
     * UNCHECKED): main.ts calls this only from SaveLoadView.toggleSpectator().
     * It is NOT the graph's update path - see the `/api/events` stream below,
     * which opens unconditionally and fires `worldState.fetch()` on every
     * `world_changed` even with spectator OFF. Do not reason about graph
     * updates from the spectator checkbox alone.
     */
    startPolling(intervalMs = 1500) {
        this.stopPolling();
        // A full /api/state build can take seconds on a large world. Without a
        // guard the 1.5s interval stacks requests faster than they finish, so the
        // server is always mid-serialization and every refresh feels hung. Skip a
        // tick while the previous fetch is still in flight instead.
        let inFlight = false;
        this._pollTimer = setInterval(() => {
            // The agent loop already pushes UI updates via renderAll while running.
            // Polling /api/state on top of that doubles the stream and re-triggers
            // the whole inspector/lens render cascade - skip it while running.
            // `config` is a top-level const lexical global - window.config is
            // always undefined (would make this guard dead code).
            if (typeof config !== 'undefined' && config.running)
                return;
            if (inFlight)
                return;
            inFlight = true;
            Promise.resolve(this.fetch()).finally(() => { inFlight = false; });
        }, intervalMs);
    }
    stopPolling() {
        if (this._pollTimer) {
            clearInterval(this._pollTimer);
            this._pollTimer = null;
        }
    }
    /** Accessors for current state */
    get areas() { return this.data?.areas || {}; }
    get players() { return this.data?.players || {}; }
    get activePlayer() { return this.data?.active_player || null; }
    get currentArea() { return this.data?.current_area || null; }
    get tick() { return this.data?.time_ticks || 0; }
    get gameTime() { return this.data?.game_time || ''; }
    get graph() { return this.data?.graph || null; }
    get turnEvents() { return this.data?.turn_events || []; }
    get playersInRoom() { return this.data?.players_in_area || []; }
    get itemRegistry() { return this.data?.item_registry || {}; }
    get ways() { return this.data?.ways || {}; }
    get equipSlots() { return this._equipSlots || {}; }
    /** Fetch equipment slot configuration from backend */
    async fetchEquipSlots() {
        if (this._equipSlots)
            return this._equipSlots;
        try {
            const resp = await fetch('/api/settings/equip_slots');
            const data = await resp.json();
            this._equipSlots = data.equip_slots || {};
            return this._equipSlots;
        }
        catch (e) {
            console.error('Equip slots fetch failed:', e);
            return {};
        }
    }
    /** Graph node lookup helper - case-insensitive (ids are always lowercase) */
    getNode(id) {
        const key = String(id).toLowerCase();
        const nodes = this.graph?.nodes;
        if (nodes) {
            if (nodes[id])
                return nodes[id];
            if (nodes[key])
                return nodes[key];
        }
        const gm = window.graphManager;
        const gmObj = gm?._graphNodesObj;
        if (gmObj) {
            if (gmObj[id])
                return gmObj[id];
            if (gmObj[key])
                return gmObj[key];
        }
        if (gm?.nodes) {
            return gm.nodes.get(id) || gm.nodes.get(key) || null;
        }
        return null;
    }
    /** Find the parent node of a trigger node via the triggers edge */
    _findTriggerParent(triggerId) {
        if (!this.graph?.edges)
            return null;
        const tid = String(triggerId).toLowerCase();
        for (const edge of this.graph.edges) {
            if (edge.type !== 'triggers')
                continue;
            if (String(edge.target).toLowerCase() === tid)
                return edge.source;
            if (String(edge.source).toLowerCase() === tid)
                return edge.target;
        }
        return null;
    }
    /** Find the triggers edge object for a given trigger node ID */
    _findTriggerEdge(triggerId) {
        if (!this.graph?.edges)
            return null;
        const tid = String(triggerId).toLowerCase();
        for (const edge of this.graph.edges) {
            if (edge.type !== 'triggers')
                continue;
            if (String(edge.target).toLowerCase() === tid || String(edge.source).toLowerCase() === tid)
                return edge;
        }
        return null;
    }
    /**
     * True when *charName* already knows *targetName*'s identity.
     *
     * A relationship record means they've shared space, but the record is
     * stamped `first_sighting: true` by the backend on the first meeting and
     * only cleared on the NEXT encounter - so the name stays hidden for the
     * rest of the first-sighting turn, matching area_description.py's rule.
     */
    hasMet(charName, targetName) {
        const player = this.data?.players?.[charName];
        const rel = player?.relationships?.[targetName];
        if (!rel || rel.closeness === undefined)
            return false;
        return !rel.first_sighting;
    }
    getNodesByType(type) {
        const result = [];
        if (!this.graph?.nodes)
            return result;
        for (const [id, node] of Object.entries(this.graph.nodes)) {
            if (node.type === type)
                result.push({ id, ...node });
        }
        return result;
    }
    /** Get character inventory from graph - optionally filter by edge types */
    getInventory(charName, edgeTypes) {
        const charNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        const types = edgeTypes || ['carrying', 'equipped', 'known'];
        const inventory = [];
        const seenIds = new Set();
        for (const edge of this.graph?.edges || []) {
            if (edge.target === charNodeId && types.includes(edge.type)) {
                if (seenIds.has(edge.source))
                    continue;
                seenIds.add(edge.source);
                const itemNode = this.getNode(edge.source);
                if (itemNode && itemNode.type === 'item') {
                    inventory.push(itemNode.name);
                }
            }
        }
        return inventory;
    }
    /**
     * Character's item node **ids** by edge type - the id-based sibling of
     * `getInventory`, which returns display names.
     *
     * Use this for anything that has to *identify* or compare items. Names are
     * not identity: three mages can each know a "Fireball", a camp can hold two
     * items called "Bag", and `getInventory` collapses them into one string. A
     * caller that compares names will both wrongly hide a distinct item and
     * wrongly offer one that is already held.
     *
     * @param {string} charName
     * @param {string[]} [edgeTypes] defaults to carrying, equipped and known
     * @returns {string[]} node ids, in edge order, deduplicated by id
     */
    getInventoryIds(charName, edgeTypes) {
        const charNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        const types = edgeTypes || ['carrying', 'equipped', 'known'];
        const ids = [];
        const seen = new Set();
        for (const edge of this.graph?.edges || []) {
            if (edge.target !== charNodeId || !types.includes(edge.type))
                continue;
            if (seen.has(edge.source))
                continue;
            seen.add(edge.source);
            const itemNode = this.getNode(edge.source);
            if (itemNode && itemNode.type === 'item')
                ids.push(edge.source);
        }
        return ids;
    }
    /** Look up a node by its identifier (name or ID) */
    getNodeByIdentifier(name) {
        if (!this.graph?.nodes)
            return null;
        // First try exact ID match
        for (const [id, node] of Object.entries(this.graph.nodes)) {
            if (id === name || node.name === name) {
                return { id, ...node };
            }
        }
        return null;
    }
    /** Get items in a area from graph */
    getItemsInArea(areaName) {
        const items = [];
        // Resolve the actual area node id by name - ids may differ in case
        // from the derived id (e.g. "Task 3 - main area" vs "area_Task_3_-_main_area"),
        // which used to make every item in such areas invisible.
        let areaId = null;
        for (const [nodeId, node] of Object.entries(this.graph?.nodes || {})) {
            if (node.type === 'area' && (node.name === areaName || nodeId === areaName)) {
                areaId = nodeId;
                break;
            }
        }
        if (!areaId)
            areaId = `area_${areaName.toLowerCase().replace(/\s+/g, '_')}`;
        const candidates = [areaId];
        const areaEdgeTypes = ['in'];
        const pushItem = (edgeSource, node) => {
            if (node && node.type === 'item' && node.properties?.current_state !== 'hidden' && !items.some(item => item.id === edgeSource)) {
                items.push({ id: edgeSource, name: node.name, properties: node.properties });
            }
        };
        // Directly placed items (in the area) - these are also the anchors that
        // spatially-placed items hang off of.
        const anchorIds = new Set();
        for (const edge of this.graph?.edges || []) {
            if (candidates.includes(edge.target) && areaEdgeTypes.includes(edge.type)) {
                const itemNode = this.getNode(edge.source);
                pushItem(edge.source, itemNode);
                anchorIds.add(edge.source);
            }
        }
        // Spatially placed items (on/under/behind/beside/at) - attached to the
        // area itself or to a surface that is in the area, so they are present
        // and visible like any other item.
        const spatialTypes = ['on', 'under', 'behind', 'beside', 'at'];
        const anchors = new Set([...anchorIds, areaId]);
        for (const edge of this.graph?.edges || []) {
            if (spatialTypes.includes(edge.type) && anchors.has(edge.target)) {
                const itemNode = this.getNode(edge.source);
                pushItem(edge.source, itemNode);
            }
        }
        // Also include items inside containers in the area, at ANY depth and
        // behind the same state gate the engine applies (task-493). This used
        // to be one flat level that only skipped `locked`, so a prompt could
        // list a battery in a `closed` cabinet, miss a part three levels down,
        // and disagree with the engine about both. window.ItemContainment is
        // the one walk; the engine's engine/item_reach.py is the other half.
        for (const container of [...items]) {
            const containerNode = this.getNode(container.id);
            if (!containerNode || containerNode.type !== 'item')
                continue;
            const contained = (window.ItemContainment).collectReachable([container.id], {
                getNode: (id) => this.getNode(id),
                edges: this.graph?.edges || [],
            });
            for (const inner of contained) {
                if (inner.depth === 0)
                    continue; // the container itself
                if (!items.some(item => item.id === inner.id)) {
                    items.push({ id: inner.id, name: inner.name, properties: inner.properties });
                }
            }
        }
        return items;
    }
}
// Singleton
window.worldState = new WorldState();
// ── Live world-edit push (EventSource) ──────────────────────────────
// The server broadcasts a `world_changed` event over /api/events for every
// mutating API call - including edits made by external agents through the MCP
// server. Refetch world state in real time so those edits appear in the GUI
// without a manual refresh, and log a thin line when a non-local editor acted.
// Runs immediately (no `load` race) and lets the browser auto-reconnect.
//
// SPECTATOR-INDEPENDENT: unlike the 1.5s poll in startPolling() - which runs
// only while the spectator checkbox is ticked (it ships unchecked) - this
// stream is NOT gated on spectator mode. It fires on every world edit
// regardless, so a graph update can arrive with spectator off. This is the
// path an external editor / MCP edit takes into the GUI.
(function connectLiveEdits() {
    if (typeof EventSource === 'undefined')
        return;
    let es = null;
    function refresh() {
        if (!window.worldState)
            return;
        if (window.worldState._runtimeFocus?.length) {
            void window.worldState.fetchRuntime().catch((error) => {
                const message = error instanceof Error ? error.message : String(error);
                console.error('Focused runtime state refresh failed:', error);
                if (typeof events !== 'undefined') {
                    events.log(`Focused runtime state refresh failed: ${message}`, 'error-msg');
                }
            });
            return;
        }
        void window.worldState.fetch();
    }
    // task-861: a world advance streams one frame per tick while its own POST is
    // still in flight. Those rows go to the event stream and NOWHERE else: there is
    // deliberately no state fetch on this path, because a refresh costs ~9 MB and
    // ~5 s (measured), and clock and graph must keep their single source of truth in
    // the authoritative `world_changed` fetch below.
    let streaming = false;
    function onWorldTick(ev) {
        if (typeof events === 'undefined' || !Array.isArray(ev.events))
            return;
        if (!streaming) {
            streaming = true;
            events.log('⏩ Fast-forwarding the world - everyone soaks, nobody acts...', 'system-msg');
        }
        for (const e of ev.events) {
            const text = String(e.description || '').trim();
            if (!text)
                continue;
            // `__system__` is engine chatter, not a character's act: leave it unattributed
            // so it lands in the World lane instead of whoever's card is open.
            const actor = e.actor && e.actor !== '__system__' ? String(e.actor) : undefined;
            events.log(text, 'msg-action', {}, actor);
        }
        if (ev.truncated) {
            events.log(`⏩ tick ${ev.tick}: more happened than this frame carried; the rest lands with the world state.`, 'system-msg');
        }
    }
    try {
        es = new EventSource('/api/events');
        es.onmessage = function (msg) {
            let ev;
            try {
                ev = JSON.parse(msg.data);
            }
            catch (e) {
                return;
            }
            if (!ev)
                return;
            if (ev.type === 'world_tick') {
                onWorldTick(ev);
                return;
            }
            if (ev.type !== 'world_changed')
                return;
            if (streaming) {
                streaming = false;
                if (typeof events !== 'undefined')
                    events.log('⏩ Fast-forward complete.', 'system-msg');
            }
            refresh();
            // task-384: re-emit on the event bus so the per-edit undo feed
            // (EditFeed) can render without opening its own EventSource.
            const bus = window.appEvents;
            if (bus)
                bus.emit('world:changed', ev);
            const editor = ev.editor && ev.editor !== 'app' ? ev.editor : '';
            if (editor && typeof events !== 'undefined') {
                events.log('World edited by ' + editor + ' - ' + (ev.method || '') + ' ' + (ev.path || ''), 'system-msg');
            }
        };
        // Do not close on error - the browser reconnects the EventSource itself.
        es.onerror = function () { };
    }
    catch (e) { /* keep the GUI safe if the stream is unavailable */ }
})();
