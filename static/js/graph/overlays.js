/**
 * GraphOverlays — the ambient visualisation overlays for the graph.
 *
 * Extracted from the network-manager monolith. Each overlay recolors the
 * nodes/edges in the live vis.js dataset based on area environment (light,
 * heat, sound), trigger edges, or cardinal layout. The leaf functions keep
 * identical color/label behaviour to the originals; `computeAmbientLight` is
 * now CACHED against a cheap signature of the world state because it walks
 * every edge per lit item — the main perf hot-spot in the old monolithic
 * version.
 *
 * @module GraphOverlays
 */
window.GraphOverlays = {

    /** Light level enum → numeric value (mirrors engine/lighting.py) */
    lightToInt(raw) {
        if (raw === undefined || raw === null) return 80;
        if (typeof raw === 'number') return Math.max(0, Math.min(100, raw));
        const mapping = { pitch_black: 10, dim: 30, normal: 55, bright: 80, blinding: 95 };
        return mapping[raw] || 80;
    },

    /** Light level → color palette */
    lightColors(level) {
        if (level <= 20) return { background: '#0a0a0a', border: '#333333' };
        if (level <= 40) return { background: '#16162a', border: '#4a4a7e' };
        if (level <= 70) return { background: '#1e2430', border: '#58a6ff' };
        if (level <= 90) return { background: '#3a3518', border: '#e3b341' };
        return { background: '#4a4020', border: '#ffffff' };
    },

    /** Temperature (°C) → color palette */
    heatColors(temp) {
        if (temp === undefined || temp === null) return { background: '#2d333b', border: '#58a6ff' };
        if (temp <= -20) return { background: '#0a0a2e', border: '#6e9eff' };
        if (temp <= -5) return { background: '#101840', border: '#7eb8ff' };
        if (temp <= 5) return { background: '#182050', border: '#8ec8ff' };
        if (temp <= 15) return { background: '#1a2840', border: '#58a6ff' };
        if (temp <= 25) return { background: '#2d333b', border: '#58a6ff' };
        if (temp <= 35) return { background: '#3a2a18', border: '#e3b341' };
        if (temp <= 45) return { background: '#4a2818', border: '#f0883e' };
        return { background: '#4a1010', border: '#f85149' };
    },

    /** Noise level → color palette */
    noiseColors(noise) {
        if (!noise) return { background: '#2d333b', border: '#58a6ff' };
        const nl = noise.toLowerCase();
        if (nl === 'silent') return { background: '#0a0a0a', border: '#333' };
        if (nl === 'quiet') return { background: '#121220', border: '#4a4a7e' };
        if (nl === 'moderate' || nl === 'normal') return { background: '#2d333b', border: '#58a6ff' };
        if (nl === 'loud') return { background: '#3a2a18', border: '#e3b341' };
        if (nl === 'deafening') return { background: '#4a1010', border: '#f85149' };
        return { background: '#2d333b', border: '#58a6ff' };
    },

    /**
     * Build a map of area node ID → ambient light (with spill from adjacent
     * lit areas). Visual-only — duplicates engine/lighting.py:get_ambient_light.
     * Cached: the result is keyed on a signature of the world graph + area
     * environments, so repeated overlay applies only recompute when the world
     * actually changed (killing the old per-tick O(E·N) walk).
     *
     * @returns {{}} area node id → { own, spill, total }
     */
    computeAmbientLight() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes) return {};
        const edges = worldState.graph?.edges || [];
        const allNodes = worldState.graph?.nodes || {};

        // Cheap change-detection signature over the inputs this function reads
        // (node state, edge presence, and each area's light/temp/noise env). Only
        // recompute when one of them shifts.
        const envTags = Object.entries(worldState.areas || {}).map(([name, area]) =>
            `${name}:${area?.environment?.light}|${area?.environment?.temperature}|${area?.environment?.noise}`
        );
        const sig = JSON.stringify([
            Object.keys(allNodes).length + Object.keys(worldState.areas || {}).length,
            edges.length,
            Object.entries(allNodes).map(([id]) =>
                `${id}:${allNodes[id].properties?.current_state || ''}`),
            envTags
        ]);
        if (this._lightCacheSig === sig && this._lightCache) return this._lightCache;
        this._lightCacheSig = sig;

        const lighting = {};
        const areaNodes = [];
        const wayNodes = {};
        const areaItemContrib = {};

        // Scan lit items in each area
        for (const edge of edges) {
            if (edge.type !== 'in') continue;
            const targetId = edge.target;
            if (!areaItemContrib[targetId]) areaItemContrib[targetId] = 0;
            const srcNode = allNodes[edge.source];
            if (!srcNode) continue;
            if (srcNode.type === 'item') {
                if (srcNode.properties?.current_state === 'lit' &&
                    (srcNode.properties?.tags || []).includes('light_source')) {
                    areaItemContrib[targetId] += GraphOverlays.lightToInt(srcNode.properties.light_level);
                }
            } else if (srcNode.type === 'character') {
                for (const ce of edges) {
                    if (ce.type !== 'carrying' && ce.type !== 'equipped') continue;
                    if (ce.target !== srcNode.id) continue;
                    const itemNode = allNodes[ce.source];
                    if (itemNode?.type === 'item' &&
                        itemNode.properties?.current_state === 'lit' &&
                        (itemNode.properties?.tags || []).includes('light_source')) {
                        areaItemContrib[targetId] += GraphOverlays.lightToInt(itemNode.properties.light_level);
                    }
                }
            }
        }

        nodes.forEach(n => {
            if (n.group === 'area') {
                const room = worldState.areas?.[n.label];
                const env = room?.environment || {};
                const itemLight = Math.min(100, areaItemContrib[n.id] || 0);
                const own = Math.min(100, GraphOverlays.lightToInt(env.light) + itemLight);
                areaNodes.push({ id: n.id, name: n.label, own });
                lighting[n.id] = { own, spill: 0, total: own };
            } else if (n.group === 'way') {
                wayNodes[n.id] = n;
            }
        });

        for (const edge of edges) {
            if (edge.type !== 'connection') continue;
            const way = wayNodes[edge.target];
            if (!way) continue;
            const doorNode = worldState.graph?.nodes?.[way.id];
            const state = doorNode?.properties?.current_state;
            const seeThrough = doorNode?.properties?.see_through;
            if (state !== 'open' && !seeThrough) continue;
            const edge2 = edges.find(e =>
                e.type === 'connection' && e.source === edge.target && e.target !== edge.source
            ) || edges.find(e =>
                e.type === 'connection' && e.target === edge.target && e.source !== edge.source
            );
            if (!edge2) continue;
            const otherId = edge2.source === edge.target ? edge2.target : edge2.source;
            if (lighting[edge.source] && lighting[otherId]) {
                const brighter = Math.max(lighting[edge.source].total, lighting[otherId].total);
                const darker = lighting[edge.source].total < lighting[otherId].total ? lighting[edge.source] : lighting[otherId];
                const spill = Math.max(0, Math.floor(brighter * 0.5));
                if (spill > darker.spill) {
                    darker.spill = spill;
                    darker.total = Math.max(darker.own, spill);
                }
            }
        }

        this._lightCache = lighting;
        return lighting;
    },

    /** Apply the Light overlay — color areas by ambient light with spill. */
    applyLightOverlay() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes) return;
        const lighting = GraphOverlays.computeAmbientLight();
        const updates = [];
        nodes.forEach(node => {
            if (node.group === 'area') {
                const l = lighting[node.id];
                const level = l ? l.total : 80;
                updates.push({ id: node.id, color: GraphOverlays.lightColors(level) });
            } else if (node.group === 'item') {
                const nodeData = worldState.graph?.nodes?.[node.id];
                const state = nodeData?.properties?.current_state;
                if (state === 'lit') {
                    updates.push({ id: node.id, color: { background: '#3d2a0a', border: '#f0883e' } });
                }
            }
        });
        nodes.update(updates);
    },

    /** Apply the Heat overlay — color areas by temperature with propagation. */
    applyHeatOverlay() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes) return;
        const updates = [];
        nodes.forEach(node => {
            if (node.group === 'area') {
                const room = worldState.areas?.[node.label];
                const env = room?.environment || {};
                const temp = env.temperature;
                updates.push({ id: node.id, color: GraphOverlays.heatColors(temp) });
            } else if (node.group === 'item') {
                const nodeData = worldState.graph?.nodes?.[node.id];
                const state = nodeData?.properties?.current_state;
                if (state === 'lit') {
                    updates.push({ id: node.id, color: { background: '#4a2818', border: '#f0883e' } });
                }
            }
        });
        nodes.update(updates);
    },

    /** Apply the Sound overlay — color areas by noise level with propagation. */
    applySoundOverlay() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes) return;
        const updates = [];
        nodes.forEach(node => {
            if (node.group === 'area') {
                const room = worldState.areas?.[node.label];
                const env = room?.environment || {};
                updates.push({ id: node.id, color: GraphOverlays.noiseColors(env.noise) });
            }
        });
        nodes.update(updates);
    },

    /** Apply the Trigger overlay — highlight trigger sources/targets, dim others. */
    applyTriggerOverlay() {
        const nodes = graphManager.network?.body?.data?.nodes;
        const edges = graphManager.network?.body?.data?.edges;
        if (!nodes || !edges) return;

        const triggerNodeIds = new Set();
        const worldEdges = worldState.graph?.edges || [];
        for (const edge of worldEdges) {
            if (edge.type === 'triggers') {
                triggerNodeIds.add(edge.source);
                triggerNodeIds.add(edge.target);
            }
        }
        const nodeUpdates = [];
        nodes.forEach(node => {
            const isTrigger = triggerNodeIds.has(node.id);
            nodeUpdates.push({
                id: node.id,
                opacity: isTrigger ? 1.0 : 0.2,
                color: isTrigger ? undefined : { background: '#1a1a1a', border: '#333' }
            });
        });
        nodes.update(nodeUpdates);

        const worldEdgeMap = {};
        for (const edge of worldEdges) {
            worldEdgeMap[`${edge.source}|${edge.target}|${edge.type}`] = edge;
        }
        const edgeUpdates = [];
        edges.forEach(edge => {
            const lookup = worldEdgeMap[`${edge.from}|${edge.to}|${edge.type || 'connection'}`]
                || worldEdgeMap[`${edge.from}|${edge.to}|connection`];
            const isTrigger = lookup?.type === 'triggers';
            edgeUpdates.push({
                id: edge.id,
                color: isTrigger ? { color: '#bc8cff', highlight: '#bc8cff' } : { color: '#30363d', highlight: '#30363d' },
                dashes: isTrigger ? false : true,
                width: isTrigger ? 2 : 0.5,
                opacity: isTrigger ? 1.0 : 0.15,
                label: isTrigger ? (lookup?.properties?.description || 'triggers') : ''
            });
        });
        edges.update(edgeUpdates);
    },

    /** Apply the Cardinal overlay — label ways with cardinal direction. */
    applyCardinalOverlay() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes) return;
        const updates = [];
        nodes.forEach(node => {
            if (node.group !== 'way') return;
            const nodeData = worldState.graph?.nodes?.[node.id];
            const props = nodeData?.properties || {};
            const cardinal = props.cardinal || '';
            const dirEmoji = { north:'⬆N', south:'⬇S', east:'➡E', west:'⬅W',
                northeast:'⬈NE', northwest:'⬉NW', southeast:'⬊SE', southwest:'⬋SW',
                up:'⬆U', down:'⬇D' };
            const label = dirEmoji[cardinal.toLowerCase()] || cardinal || '?';
            updates.push({
                id: node.id,
                label: `${label}\n${nodeData?.name || node.id}`,
                color: { background: '#1a3a2a', border: '#4ec9b0' }
            });
        });
        nodes.update(updates);
    }
};