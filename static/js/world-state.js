/**
 * WorldState — Reactive state management
 * Fetches world state from the backend and notifies listeners
 */
class WorldState {
    constructor() {
        this.data = null; // raw state from /api/state
        this._listeners = {};
        this._pollTimer = null;
        this._equipSlots = null;
    }

    /** Subscribe to state changes */
    on(event, callback) {
        if (!this._listeners[event]) this._listeners[event] = [];
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
        if (!window.events || !state.turn_events) return;
        for (const evt of state.turn_events) {
            if (!evt.area) continue;
            const roomLog = events._areaEventLog[evt.area];
            // Only add if we don't already have this event (check by tick+actor+description)
            if (!roomLog) {
                events._areaEventLog[evt.area] = [{
                    tick: evt.tick,
                    actor: evt.actor,
                    action: evt.action,
                    result: evt.description || ''
                }];
            } else {
                const exists = roomLog.some(e => e.tick === evt.tick && e.actor === evt.actor && e.action === evt.action);
                if (!exists) {
                    roomLog.push({
                        tick: evt.tick,
                        actor: evt.actor,
                        action: evt.action,
                        result: evt.description || ''
                    });
                    if (roomLog.length > 50) roomLog.shift();
                }
            }
        }
    }

    /** Fetch latest state from backend */
    async fetch() {
        try {
            const resp = await fetch('/api/state');
            const state = await resp.json();
            this.data = state;
            this._syncTurnEvents(state);
            // Rebuild the turn queue if the roster changed (new/dead characters)
            // so freshly added characters join the initiative loop mid-run.
            if (window.TurnQueue) window.TurnQueue.reconcile();
            this._emit('update', state);
            if (window.appEvents) appEvents.emit('state:updated', state);
            return state;
        } catch (e) {
            console.error('State fetch failed:', e);
            return this.data;
        }
    }

    /** Start polling for spectator mode */
    startPolling(intervalMs = 1500) {
        this.stopPolling();
        this._pollTimer = setInterval(() => {
            // The agent loop already pushes UI updates via renderAll while running.
            // Polling /api/state on top of that doubles the stream and re-triggers
            // the whole inspector/lens render cascade — skip it while running.
            if (window.config && config.running) return;
            this.fetch();
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
    get areas() { return this.data?.areas || {}; }
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
        if (this._equipSlots) return this._equipSlots;
        try {
            const resp = await fetch('/api/settings/equip_slots');
            const data = await resp.json();
            this._equipSlots = data.equip_slots || {};
            return this._equipSlots;
        } catch (e) {
            console.error('Equip slots fetch failed:', e);
            return {};
        }
    }

    /** Graph node lookup helper — case-insensitive (ids are always lowercase) */
    getNode(id) {
        if (!this.graph?.nodes) return null;
        if (this.graph.nodes[id]) return this.graph.nodes[id];
        const key = String(id).toLowerCase();
        return this.graph.nodes[key] || null;
    }

    /** Find the parent node of a trigger node via the triggers edge */
    _findTriggerParent(triggerId) {
        if (!this.graph?.edges) return null;
        const tid = String(triggerId).toLowerCase();
        for (const edge of this.graph.edges) {
            if (edge.type !== 'triggers') continue;
            if (String(edge.target).toLowerCase() === tid) return edge.source;
            if (String(edge.source).toLowerCase() === tid) return edge.target;
        }
        return null;
    }

    /** Find the triggers edge object for a given trigger node ID */
    _findTriggerEdge(triggerId) {
        if (!this.graph?.edges) return null;
        const tid = String(triggerId).toLowerCase();
        for (const edge of this.graph.edges) {
            if (edge.type !== 'triggers') continue;
            if (String(edge.target).toLowerCase() === tid || String(edge.source).toLowerCase() === tid) return edge;
        }
        return null;
    }

    /**
     * True when *charName* already knows *targetName*'s identity.
     *
     * A relationship record means they've shared space, but the record is
     * stamped `first_sighting: true` by the backend on the first meeting and
     * only cleared on the NEXT encounter — so the name stays hidden for the
     * rest of the first-sighting turn, matching area_description.py's rule.
     */
    hasMet(charName, targetName) {
        const player = this.data?.players?.[charName];
        const rel = player?.relationships?.[targetName];
        if (!rel || rel.closeness === undefined) return false;
        return !rel.first_sighting;
    }

    getNodesByType(type) {
        const result = [];
        if (!this.graph?.nodes) return result;
        for (const [id, node] of Object.entries(this.graph.nodes)) {
            if (node.type === type) result.push({ id, ...node });
        }
        return result;
    }

    /** Get character inventory from graph — optionally filter by edge types */
    getInventory(charName, edgeTypes) {
        const charNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        const types = edgeTypes || ['carrying', 'equipped'];
        const inventory = [];
        const seenIds = new Set();
        for (const edge of this.graph?.edges || []) {
            if (edge.target === charNodeId && types.includes(edge.type)) {
                if (seenIds.has(edge.source)) continue;
                seenIds.add(edge.source);
                const itemNode = this.getNode(edge.source);
                if (itemNode && itemNode.type === 'item') {
                    inventory.push(itemNode.name);
                }
            }
        }
        return inventory;
    }

    /** Look up a node by its identifier (name or ID) */
    getNodeByIdentifier(name) {
        if (!this.graph?.nodes) return null;
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
        // Resolve the actual area node id by name — ids may differ in case
        // from the derived id (e.g. "Task 3 - main area" vs "area_Task_3_-_main_area"),
        // which used to make every item in such areas invisible.
        let areaId = null;
        for (const [nodeId, node] of Object.entries(this.graph?.nodes || {})) {
            if (node.type === 'area' && (node.name === areaName || nodeId === areaName)) {
                areaId = nodeId;
                break;
            }
        }
        if (!areaId) areaId = `area_${areaName.toLowerCase().replace(/\s+/g, '_')}`;
        const candidates = [areaId];
        const areaEdgeTypes = ['in'];
        const pushItem = (edgeSource, node) => {
            if (node && node.type === 'item' && node.properties?.current_state !== 'hidden' && !items.some(item => item.id === edgeSource)) {
                items.push({ id: edgeSource, name: node.name, properties: node.properties });
            }
        };
        // Directly placed items (in the area) — these are also the anchors that
        // spatially-placed items hang off of.
        const anchorIds = new Set();
        for (const edge of this.graph?.edges || []) {
            if (candidates.includes(edge.target) && areaEdgeTypes.includes(edge.type)) {
                const itemNode = this.getNode(edge.source);
                pushItem(edge.source, itemNode);
                anchorIds.add(edge.source);
            }
        }
        // Spatially placed items (on/under/behind/beside/at) — attached to the
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
        // Also include items inside containers in the area (revealed after examine)
        for (const container of [...items]) {
            const containerNode = this.getNode(container.id);
            if (!containerNode || containerNode.type !== 'item') continue;
            if (containerNode.properties?.current_state === 'locked') continue;
            const containerEdgeTypes = ['in'];
            for (const innerEdge of this.graph?.edges || []) {
                if (innerEdge.target === containerNode.id && containerEdgeTypes.includes(innerEdge.type)) {
                    const innerItem = this.getNode(innerEdge.source);
                    if (innerItem && innerItem.type === 'item' && innerItem.properties?.current_state !== 'hidden') {
                        if (!items.some(item => item.id === innerEdge.source)) {
                            items.push({ id: innerEdge.source, name: innerItem.name, properties: innerItem.properties });
                        }
                    }
                }
            }
        }
        return items;
    }
}

// Singleton
const worldState = new WorldState();
window.worldState = worldState;

// ── Live world-edit push (EventSource) ──────────────────────────────
// The server broadcasts a `world_changed` event over /api/events for every
// mutating API call — including edits made by external agents through the MCP
// server. Refetch world state in real time so those edits appear in the GUI
// without a manual refresh, and log a thin line when a non-local editor acted.
// Runs immediately (no `load` race) and lets the browser auto-reconnect.
(function connectLiveEdits() {
  if (typeof EventSource === 'undefined') return;
  let es = null;
  function refresh() {
    if (window.worldState) window.worldState.fetch();
  }
  try {
    es = new EventSource('/api/events');
    es.onmessage = function (msg) {
      let ev;
      try { ev = JSON.parse(msg.data); } catch (e) { return; }
      if (!ev || ev.type !== 'world_changed') return;
      refresh();
      const editor = ev.editor && ev.editor !== 'app' ? ev.editor : '';
      if (editor && typeof events !== 'undefined') {
        events.log('World edited by ' + editor + ' — ' + (ev.method || '') + ' ' + (ev.path || ''), 'system-msg');
      }
    };
    // Do not close on error — the browser reconnects the EventSource itself.
    es.onerror = function () { /* auto-reconnect */ };
  } catch (e) { /* keep the GUI safe if the stream is unavailable */ }
})();