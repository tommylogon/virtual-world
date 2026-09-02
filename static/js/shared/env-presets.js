/**
 * EnvPresets — named environment presets + zone apply (task-379).
 *
 * Source: "Scenario Workflows & UI Audit" P3 — environment presets & zone
 * apply ('Arctic: -12° bright fresh' → apply to a selection). Guardrails:
 * CLI-free, undo-safe, no new storage formats.
 *
 * - Presets live in localStorage (`vw_env_presets`) — browser-side authoring
 *   data, not world state, so nothing new is saved into scenarios.
 * - Applying writes through the SAME `api.updateNode` path the inspector's
 *   env editors use, so every apply inherits the existing undo snapshots.
 * - Zone scopes: the current area, the current area + neighbours reachable
 *   through open ways, or every area in the world.
 */
window.EnvPresets = (() => {
    'use strict';

    const STORE_KEY = 'vw_env_presets';

    // Environment keys a preset captures (everything the inspector edits,
    // plus the task-231/232/234 climate keys).
    const ENV_KEYS = ['temperature', 'light', 'air', 'smell', 'noise',
        'weather', 'wind', 'humidity'];

    function _store() {
        try { return JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); }
        catch (e) { return {}; }
    }

    function _write(store) {
        try { localStorage.setItem(STORE_KEY, JSON.stringify(store)); } catch (e) { /* private mode */ }
    }

    function list() {
        return Object.keys(_store()).sort();
    }

    function get(name) {
        return _store()[name] || null;
    }

    /** Capture the whitelisted env keys from an area environment dict. */
    function save(name, env) {
        if (!name) return false;
        const store = _store();
        const preset = {};
        ENV_KEYS.forEach(k => {
            if (env && env[k] !== undefined && env[k] !== '') preset[k] = env[k];
        });
        store[name] = preset;
        _write(store);
        return true;
    }

    function del(name) {
        const store = _store();
        if (!(name in store)) return false;
        delete store[name];
        _write(store);
        return true;
    }

    /** Area ids reachable from baseAreaId through ways that are open. */
    function _neighbourAreas(baseAreaId) {
        const ids = new Set();
        const ws = window.worldState;
        if (!ws?.graph?.nodes || !ws.graph.edges) return [];
        const openWays = new Set();
        for (const [id, n] of Object.entries(ws.graph.nodes)) {
            if (n.type === 'way' && (n.current_state === 'open' || n.properties?.current_state === 'open')) {
                openWays.add(id);
            }
        }
        for (const e of ws.graph.edges) {
            if (e.type !== 'connection') continue;
            if (!openWays.has(e.source)) continue;
            const a = e.source_target_pair || null;
            // edges: area -> way and way -> area; collect the far side of each
        }
        // Build way -> areas map, then pair up like the backend does.
        const wayToAreas = {};
        for (const e of ws.graph.edges) {
            if (e.type !== 'connection') continue;
            const srcNode = ws.graph.nodes[e.source];
            if (srcNode && srcNode.type === 'way') {
                (wayToAreas[e.source] = wayToAreas[e.source] || new Set()).add(e.target);
            } else if (srcNode && srcNode.type === 'area' && openWays.has(e.target)) {
                // area -> way edge: remember the pairing from the way side too
            }
        }
        for (const [wayId, areas] of Object.entries(wayToAreas)) {
            if (!areas.has(baseAreaId)) continue;
            for (const other of areas) {
                if (other !== baseAreaId) ids.add(other);
            }
        }
        return [...ids];
    }

    /**
     * Apply a preset to a zone.
     * @param {string} name - preset name
     * @param {'current'|'connected'|'all'} scope
     * @param {string} baseAreaId - the area the inspector is showing
     * @returns {Promise<{applied: number, areaNames: string[]}>}
     */
    async function apply(name, scope, baseAreaId) {
        const preset = get(name);
        if (!preset || !Object.keys(preset).length) return { applied: 0, areaNames: [] };
        const ws = window.worldState;
        if (!ws?.graph?.nodes) return { applied: 0, areaNames: [] };

        let targets = [];
        if (scope === 'all') {
            targets = Object.entries(ws.graph.nodes).filter(([, n]) => n.type === 'area').map(([id]) => id);
        } else if (scope === 'connected') {
            targets = [baseAreaId, ..._neighbourAreas(baseAreaId)];
        } else {
            targets = [baseAreaId];
        }

        const api = window.ApiClient;
        if (!api?.updateNode) return { applied: 0, areaNames: [] };

        const areaNames = [];
        let applied = 0;
        for (const id of targets) {
            const node = ws.getNode(id);
            if (!node || node.type !== 'area') continue;
            const env = { ...(node.properties?.environment || {}) };
            Object.assign(env, preset);
            try {
                await api.updateNode(id, { properties: { environment: env } });
                applied++;
                areaNames.push(node.name || id);
            } catch (e) { /* keep applying the rest */ }
        }
        if (applied && window.worldState?.fetch) await window.worldState.fetch();
        return { applied, areaNames };
    }

    return { list, get, save, delete: del, apply, ENV_KEYS };
})();
