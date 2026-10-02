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
 * @module graph/overlays — the ambient visual overlays
 * @contributes GraphOverlays: light/heat/sound/trigger/cardinal recolouring + cached computeAmbientLight
 * @powers Light, The map — the graph's overlay modes and their legends
 * @relates driven by GraphNetwork.applyOverlay; reads worldState + area environments
 * @docs docs/virtualWorld/Environment/Light System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
interface OverlaysWindowSurface { GraphOverlays: GraphOverlaysApi }

// The overlay object references itself (`overlays.lightToInt` etc. inside
// `computeAmbientLight`), so it is built as a local const and stamped on window
// afterwards — a `window.GraphOverlays =` assignment has no binding to refer to.
// IIFE, not a top-level const: the overlay object references itself
// (`overlays.lightToInt` inside `computeAmbientLight`), and a top-level
// `const overlays` would be a global lexical binding colliding at parse
// time with any other script declaring that name. Scoping it to the arrow
// function keeps every self-reference working; the property is assigned once.
// Named overlays rather than GraphOverlays: globals.d.ts already declares a
// bare `declare const GraphOverlays`, and a same-named local is a redeclaration.
(window as unknown as { GraphOverlays: GraphOverlaysApi }).GraphOverlays = (() => {
    const overlays: GraphOverlaysApi = {
    // Cache for computeAmbientLight(), keyed on the change-detection signature.
    _lightCache: null,
    _lightCacheSig: '',

    /**
     * The environment block for an area, resolved by **node id**.
     *
     * Every overlay used to read `worldState.areas[node.label]`, but `label` is
     * the *display* label: NodeBadges decorates it with emoji (🌑 for a dark
     * area, ⚡ for a trigger, 🏢 for a floor) and the label LOD blanks it to `''`
     * on a dense map. So on the very maps where the overlay matters, the lookup
     * missed and light/heat/sound all fell back to the same default colour —
     * the "four overlays render identically" defect (task-642).
     *
     * The id is the identity; the name is only how the environment is keyed in
     * the state payload. Read the graph node's own `properties.environment`
     * first (that is the live copy the engine mutates), then the state `areas`
     * record by the node's real name.
     *
     * @param {string} nodeId
     * @returns {Object} environment dict, `{}` when the area has none
     */
    areaEnvironment(nodeId: string): EnvironmentDict {
        const gm = ((typeof graphManager !== 'undefined' && graphManager) || null) as GraphManagerLike | null;
        const raw = (gm && gm._graphNodesObj && gm._graphNodesObj[nodeId]) || null;
        const props = (raw && raw.properties) || {};
        if (props.environment && typeof props.environment === 'object') {
            return props.environment;
        }
        const name = raw && raw.name;
        const rooms = ((typeof worldState !== 'undefined' && worldState)
            ? (worldState.areas || {}) : {}) as Record<string, { environment?: EnvironmentDict }>;
        const byName = name ? rooms[name] : null;
        if (byName && byName.environment && typeof byName.environment === 'object') {
            return byName.environment;
        }
        const graphNode = ((typeof worldState !== 'undefined' && worldState && worldState.graph
            && worldState.graph.nodes && worldState.graph.nodes[nodeId]) || null) as GraphNode | null;
        const graphEnv = graphNode && graphNode.properties && graphNode.properties.environment;
        return (graphEnv && typeof graphEnv === 'object') ? graphEnv : {};
    },

    /** Light level enum → numeric value (mirrors engine/lighting.py) */
    lightToInt(raw: unknown): number {
        if (raw === undefined || raw === null) return 80;
        if (typeof raw === 'number') return Math.max(0, Math.min(100, raw));
        const mapping: Record<string, number> = { pitch_black: 10, dim: 30, normal: 55, bright: 80, blinding: 95 };
        return mapping[String(raw)] || 80;
    },

    /** Light level → color palette */
    lightColors(level: number): ColorPair {
        if (level <= 20) return { background: '#0a0a0a', border: '#333333' };
        if (level <= 40) return { background: '#16162a', border: '#4a4a7e' };
        if (level <= 70) return { background: '#1e2430', border: '#58a6ff' };
        if (level <= 90) return { background: '#3a3518', border: '#e3b341' };
        return { background: '#4a4020', border: '#ffffff' };
    },

    /** Temperature (°C) → color palette */
    heatColors(temp: unknown): ColorPair {
        const c = temp as number;
        if (temp === undefined || temp === null) return { background: '#2d333b', border: '#58a6ff' };
        if (c <= -20) return { background: '#0a0a2e', border: '#6e9eff' };
        if (c <= -5) return { background: '#101840', border: '#7eb8ff' };
        if (c <= 5) return { background: '#182050', border: '#8ec8ff' };
        if (c <= 15) return { background: '#1a2840', border: '#58a6ff' };
        if (c <= 25) return { background: '#2d333b', border: '#58a6ff' };
        if (c <= 35) return { background: '#3a2a18', border: '#e3b341' };
        if (c <= 45) return { background: '#4a2818', border: '#f0883e' };
        return { background: '#4a1010', border: '#f85149' };
    },

    /** Noise level → color palette */
    noiseColors(noise: unknown): ColorPair {
        if (!noise) return { background: '#2d333b', border: '#58a6ff' };
        const nl = String(noise).toLowerCase();
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
    computeAmbientLight(): Record<string, AmbientLight> {
        const nodes = graphManager.network?.body?.data?.nodes as VisDataSet | undefined;
        if (!nodes) return {};
        const edges = (worldState.graph?.edges || []) as WorldEdge[];
        const allNodes = (worldState.graph?.nodes || {}) as Record<string, GraphNode>;

        // Cheap change-detection signature over the inputs this function reads
        // (node state, edge presence, and each area's light/temp/noise env). Only
        // recompute when one of them shifts.
        const areaEnv = (worldState.areas || {}) as Record<string, { environment?: EnvironmentDict }>;
        const envTags = Object.entries(areaEnv).map(([name, area]) =>
            `${name}:${area?.environment?.light}|${area?.environment?.temperature}|${area?.environment?.noise}`
        );
        const sig = JSON.stringify([
            Object.keys(allNodes).length + Object.keys(areaEnv).length,
            edges.length,
            Object.entries(allNodes).map(([id]) =>
                `${id}:${allNodes[id].properties?.current_state || ''}`),
            envTags
        ]);
        if (this._lightCacheSig === sig && this._lightCache) return this._lightCache;
        this._lightCacheSig = sig;

        const lighting: Record<string, AmbientLight> = {};
        const areaNodes: Array<{ id: string; name?: string; own: number }> = [];
        const wayNodes: Record<string, OverlaysVisNode> = {};
        const areaItemContrib: Record<string, number> = {};

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
                    areaItemContrib[targetId] += overlays.lightToInt(srcNode.properties.light_level);
                }
            } else if (srcNode.type === 'character') {
                for (const ce of edges) {
                    if (ce.type !== 'carrying' && ce.type !== 'equipped' && ce.type !== 'known') continue;
                    if (ce.target !== srcNode.id) continue;
                    const itemNode = allNodes[ce.source];
                    if (itemNode?.type === 'item' &&
                        itemNode.properties?.current_state === 'lit' &&
                        (itemNode.properties?.tags || []).includes('light_source')) {
                        areaItemContrib[targetId] += overlays.lightToInt(itemNode.properties.light_level);
                    }
                }
            }
        }

        nodes.forEach((n: OverlaysVisNode) => {
            if (n.group === 'area') {
                const env = overlays.areaEnvironment(n.id);
                const itemLight = Math.min(100, areaItemContrib[n.id] || 0);
                const own = Math.min(100, overlays.lightToInt(env.light) + itemLight);
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
            const doorNode = allNodes[way.id];
            const state = doorNode?.properties?.current_state;
            const seeThrough = doorNode?.properties?.see_through;
            if (state !== 'open' && !seeThrough) continue;
            const edge2 = edges.find((e: WorldEdge) =>
                e.type === 'connection' && e.source === edge.target && e.target !== edge.source
            ) || edges.find((e: WorldEdge) =>
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
    applyLightOverlay(): void {
        const nodes = graphManager.network?.body?.data?.nodes as VisDataSet | undefined;
        if (!nodes) return;
        const lighting = overlays.computeAmbientLight();
        const updates: NodeUpdate[] = [];
        nodes.forEach((node: OverlaysVisNode) => {
            if (node.group === 'area') {
                const l = lighting[node.id];
                const level = l ? l.total : 80;
                updates.push({ id: node.id, color: overlays.lightColors(level) });
            } else if (node.group === 'item') {
                const nodeData = (worldState.graph?.nodes || {})[node.id] as GraphNode | undefined;
                const state = nodeData?.properties?.current_state;
                if (state === 'lit') {
                    updates.push({ id: node.id, color: { background: '#3d2a0a', border: '#f0883e' } });
                }
            }
        });
        nodes.update(updates);
    },

    /** Apply the Heat overlay — color areas by temperature with propagation. */
    applyHeatOverlay(): void {
        const nodes = graphManager.network?.body?.data?.nodes as VisDataSet | undefined;
        if (!nodes) return;
        const updates: NodeUpdate[] = [];
        nodes.forEach((node: OverlaysVisNode) => {
            if (node.group === 'area') {
                const temp = overlays.areaEnvironment(node.id).temperature;
                updates.push({ id: node.id, color: overlays.heatColors(temp) });
            } else if (node.group === 'item') {
                const nodeData = (worldState.graph?.nodes || {})[node.id] as GraphNode | undefined;
                const state = nodeData?.properties?.current_state;
                if (state === 'lit') {
                    updates.push({ id: node.id, color: { background: '#4a2818', border: '#f0883e' } });
                }
            }
        });
        nodes.update(updates);
    },

    /** Apply the Sound overlay — color areas by noise level with propagation. */
    applySoundOverlay(): void {
        const nodes = graphManager.network?.body?.data?.nodes as VisDataSet | undefined;
        if (!nodes) return;
        const updates: NodeUpdate[] = [];
        nodes.forEach((node: OverlaysVisNode) => {
            if (node.group === 'area') {
                const noise = overlays.areaEnvironment(node.id).noise;
                updates.push({ id: node.id, color: overlays.noiseColors(noise) });
            }
        });
        nodes.update(updates);
    },

    /** Apply the Trigger overlay — highlight trigger sources/targets, dim others. */
    applyTriggerOverlay(): void {
        const nodes = graphManager.network?.body?.data?.nodes as VisDataSet | undefined;
        const edges = graphManager.network?.body?.data?.edges as VisDataSet | undefined;
        if (!nodes || !edges) return;

        const triggerNodeIds = new Set<string>();
        const worldEdges = (worldState.graph?.edges || []) as WorldEdge[];
        for (const edge of worldEdges) {
            if (edge.type === 'triggers') {
                triggerNodeIds.add(edge.source);
                triggerNodeIds.add(edge.target);
            }
        }
        const nodeUpdates: NodeUpdate[] = [];
        nodes.forEach((node: OverlaysVisNode) => {
            const isTrigger = triggerNodeIds.has(node.id);
            nodeUpdates.push({
                id: node.id,
                opacity: isTrigger ? 1.0 : 0.2,
                color: isTrigger ? undefined : { background: '#1a1a1a', border: '#333' }
            });
        });
        nodes.update(nodeUpdates);

        const worldEdgeMap: Record<string, WorldEdge> = {};
        for (const edge of worldEdges) {
            worldEdgeMap[`${edge.source}|${edge.target}|${edge.type}`] = edge;
        }
        const edgeUpdates: EdgeUpdate[] = [];
        edges.forEach((edge: VisEdge) => {
            const lookup = worldEdgeMap[`${edge.from}|${edge.to}|${edge.type || 'connection'}`]
                || worldEdgeMap[`${edge.from}|${edge.to}|connection`];
            const isTrigger = lookup?.type === 'triggers';
            edgeUpdates.push({
                id: edge.id,
                color: isTrigger ? { color: '#bc8cff', highlight: '#bc8cff' } : { color: '#30363d', highlight: '#30363d' },
                dashes: isTrigger ? false : true,
                width: isTrigger ? 2 : 0.5,
                opacity: isTrigger ? 1.0 : 0.15,
                label: isTrigger ? ((lookup?.properties?.description as string) || 'triggers') : ''
            });
        });
        edges.update(edgeUpdates);
    },

    /** Apply the Cardinal overlay — label ways with cardinal direction. */
    applyCardinalOverlay(): void {
        const nodes = graphManager.network?.body?.data?.nodes as VisDataSet | undefined;
        if (!nodes) return;
        const updates: NodeUpdate[] = [];
        nodes.forEach((node: OverlaysVisNode) => {
            if (node.group !== 'way') return;
            const nodeData = (worldState.graph?.nodes || {})[node.id] as GraphNode | undefined;
            const props = nodeData?.properties || {};
            const cardinal = props.cardinal || '';
            const dirEmoji: Record<string, string> = { north:'⬆N', south:'⬇S', east:'➡E', west:'⬅W',
                northeast:'⬈NE', northwest:'⬉NW', southeast:'⬊SE', southwest:'⬋SW',
                up:'⬆U', down:'⬇D' };
            const label = dirEmoji[String(cardinal).toLowerCase()] || cardinal || '?';
            updates.push({
                id: node.id,
                label: `${label}\n${nodeData?.name || node.id}`,
                color: { background: '#1a3a2a', border: '#4ec9b0' }
            });
        });
        nodes.update(updates);
    }
};
    return overlays;
})();

/* ── types ──
 * Declared at the BOTTOM deliberately. tsc drops a file's leading JSDoc when
 * the first statement is type-only, and tools/js_module_index.py reads
 * `@module` out of the EMITTED .js — so an `interface` above the first value
 * declaration would silently strip the module contract. */

/** A node's environment block: light level, temperature, noise. */
interface EnvironmentDict {
    light?: number | string;
    temperature?: number | string;
    noise?: string;
    [key: string]: unknown;
}

/** A background/border colour pair, as vis.js expects it. */
interface ColorPair {
    background: string;
    border: string;
}

/** The ambient-light entry computeAmbientLight() produces per area. */
interface AmbientLight {
    own: number;
    spill: number;
    total: number;
}

/** The world-graph node properties the overlays read. */
interface GraphNode {
    id?: string;
    name?: string;
    type?: string;
    label?: string;
    group?: string;
    properties?: {
        current_state?: string;
        environment?: EnvironmentDict;
        tags?: string[];
        light_level?: number | string;
        see_through?: boolean;
        cardinal?: string;
        [key: string]: unknown;
    };
}

/** A world-graph edge, keyed by source/target/type. */
interface WorldEdge {
    type?: string;
    source: string;
    target: string;
    properties?: { description?: string; [key: string]: unknown };
}

/** The graphManager surface the overlays reach for. */
interface GraphManagerLike {
    _graphNodesObj?: Record<string, GraphNode>;
}

/** A vis.js node as this module reads it. */
interface OverlaysVisNode {
    id: string;
    label?: string;
    group?: string;
}

/** A vis.js edge as this module reads it (from/to, not source/target). */
interface VisEdge {
    id: string;
    from: string;
    to: string;
    type?: string;
}

/** The vis.js DataSet surface: forEach + update, with no DOM. */
interface VisDataSet {
    forEach(callback: (item: never) => void): void;
    update(items: Array<Record<string, unknown>>): void;
}

/** One entry of a vis.js `nodes.update([...])` batch. */
interface NodeUpdate {
    [key: string]: unknown;
    id: string;
    color?: ColorPair | undefined;
    opacity?: number;
    label?: string;
}

/** One entry of a vis.js `edges.update([...])` batch. */
interface EdgeUpdate {
    [key: string]: unknown;
    id: string;
    color: { color: string; highlight: string };
    dashes: boolean;
    width: number;
    opacity: number;
    label: string;
}

/** The GraphOverlays surface published on window. */
interface GraphOverlaysApi {
    _lightCache: Record<string, AmbientLight> | null;
    _lightCacheSig: string;
    areaEnvironment(nodeId: string): EnvironmentDict;
    lightToInt(raw: unknown): number;
    lightColors(level: number): ColorPair;
    heatColors(temp: unknown): ColorPair;
    noiseColors(noise: unknown): ColorPair;
    computeAmbientLight(): Record<string, AmbientLight>;
    applyLightOverlay(): void;
    applyHeatOverlay(): void;
    applySoundOverlay(): void;
    applyTriggerOverlay(): void;
    applyCardinalOverlay(): void;
}
