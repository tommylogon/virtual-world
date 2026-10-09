/**
 * GraphNetwork — vis.js network setup and management for the graph
 * Handles vis.Network initialization, options building, data loading,
 * tooltip building, physics toggling, legend rendering, and node filtering.
 * Extracted from graph-manager.js. References the global graphManager singleton.
 *
 * @module graph/network-manager — vis.js Network construction and data loading
 * @contributes GraphNetwork: options, loadGraphData, applyVisibility, legend/tags, node configs
 * @powers Graph canvas — the graph canvas itself — layout physics, filtering, tooltips, node badges
 * @relates driven by graph-manager; collaborators in static/js/graph/*
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.


/**
 * The vis-network UMD bundle is loaded by a <script> tag and is already declared
 * in static/js/types/globals.d.ts.
 */

/**
 * This module publishes itself as `window.GraphNetwork` and then calls back into
 * that same object (`GraphNetwork.buildOptions()`, `GraphNetwork.applyVisibility()`
 * and friends) from inside a dozen of its own methods. The self-reference is
 * declared here so those calls resolve without a hand-written copy of the ~60
 * member surface, which would be a second thing to keep in sync with the literal
 * below. Per-member contracts belong in static/js/types/globals.d.ts.
 */
type NetworkApi = { [key: string]: any };

/**
 * `GraphLayoutEngine` is declared in globals.d.ts with the surface its *other*
 * callers use. These members are called only from here, so they are added
 * through a local intersection rather than by editing the shared declaration.
 */
type LayoutEngineExtra = typeof GraphLayoutEngine & {
    applyCardinalLayout(...args: any[]): any;
    autoMapSpacing(nodes: any, viewSize?: { w: number; h: number }): number | null;
};

/** Published by graph/edge-types.js (also window.EdgeTypes); not in globals.d.ts. */

/** Feature-detected collaborators; published by graph/relative-layout.js and friends. */
type RelLayoutWin = {
    GraphRelativeLayout?: {
        attach(network: any): void;
        reseed(): void;
        apply(): void;
        resolveSeparation?(): number;
        levelEdge(source: any, target: any, nodesObj: any, edgesArr: any): any;
        connectionLevelEdge(source: any, target: any, nodesObj: any): any;
    };
    // Present-but-possibly-absent is correct for the *modules* here (separate
    // script tags, and graph-relative-layout is optional). The METHOD is not
    // optional: `reconcileAllForGapChange?()` is the optional-member contract that
    // let commit 6fd774b8 delete it and leave this call site a silent no-op.
    GraphBackground?: { reconcileAllForGapChange(): void };
    GraphToolbar?: { syncAll(): void };
    NLEditorGhosts?: { clear(): void; [key: string]: any };
    CharacterArt?: {
        avatarFor(props: unknown, emotionKey: string): string;
        emotionKeyForName(name: string): string;
    };
};

// Lazy lit-html tag: window.Lit is only available at call time (deferred module
// bootstrap), not at parse time. Unique per file so top-level consts never collide.
const networkManagerHtmlTag = (strings: TemplateStringsArray, ...values: unknown[]): any => window.Lit.html(strings, ...values);

// Item → parent attachment edge types: the child points AT its parent
// (salt --[on]--> table, top --[equipped]--> char). These springs render
// shorter so attached items cluster around the node that holds them.
const GRAPH_ATTACH_EDGE_TYPES = new Set(['in', 'on', 'under', 'behind', 'beside', 'at', 'carrying', 'equipped', 'known']);

/**
 * How wide an edge label may get before it wraps (task-558).
 *
 * Wide enough that the labels people actually write — "west", "enter the inn",
 * "climb down the mine shaft" — stay on one line, so nothing that reads well
 * today starts reading differently. Narrow enough that a runaway label (an
 * `unlocks` edge carrying a whole `properties.description`) wraps instead of
 * running across half the canvas.
 */
const EDGE_LABEL_WRAP = 160;

/**
 * Edge length from the label *as it will be drawn*, not as it was written.
 *
 * This is the part of task-558 that is not one line. The old formula multiplied
 * the raw character count by a per-character width, which is right for one line
 * and wrong for three: the same 60 characters spread over three lines are a much
 * narrower block and need a much shorter edge, and a formula that cannot see the
 * line count either stretches the layout or lets a wrapped label collide with the
 * nodes at either end. So the label is wrapped *here* — the same wrap, at the same
 * width, that vis will draw — and the edge is sized from the widest line plus a
 * line of height for each extra one.
 */
function _labelEdgeLength(label: unknown): number {
    const text = String(label || '').trim();
    if (!text) return 45;
    const lines = _wrapLabel(text, EDGE_LABEL_WRAP);
    const widest = lines.reduce((n, line) => Math.max(n, line.length), 0);
    const CHAR = 3.2;                 // the old per-character estimate, kept
    const LINE = 9;                   // one line of 8px label plus its leading
    return Math.min(130, Math.max(45, 35 + widest * CHAR + (lines.length - 1) * LINE));
}

/**
 * Break a label into the lines vis will draw: on spaces, greedy. A single word
 * longer than the wrap width is left as one line — a long id or URL has no spaces
 * to break on, and cutting it mid-word would make it unusable.
 */
function _wrapLabel(text: unknown, maxWidth: number): string[] {
    const words = String(text).split(/\s+/).filter(Boolean);
    if (!words.length) return [''];
    const maxChars = Math.max(1, Math.floor(maxWidth / 3.2));
    const lines: string[] = [];
    let current = '';
    words.forEach((word) => {
        if (!current) { current = word; return; }
        if (current.length + 1 + word.length <= maxChars) {
            current = `${current} ${word}`;
        } else {
            lines.push(current);
            current = word;
        }
    });
    if (current) lines.push(current);
    return lines;
}

/**
 * The opening of a prose label, whole sentences only, never more than *maxLines*
 * lines (task-558).
 *
 * Cutting a description mid-sentence to fit is worse than ending it early: "the
 * key is warm and it" tells the reader nothing, while "The key is warm from the
 * pocket." is a label that means what it says. When the prose is one long sentence
 * with no break to be had, the *character* budget takes over, because an
 * edge-sized canvas cannot show it all and a truncated-but-complete-looking label
 * that goes quiet at the cap is still worse than an ellipsis.
 */
function _firstSentence(text: unknown, maxLines: number): string {
    const body = String(text || '').trim();
    if (!body) return '';
    const maxChars = Math.floor(maxLines * (EDGE_LABEL_WRAP / 3.2));
    const sentences = body.match(/[^.!?]+[.!?]+/g);
    if (sentences) {
        let out = '';
        sentences.forEach((s) => {
            if (out.length && `${out} ${s}`.trim().length > maxChars) return;
            out = `${out} ${s}`.trim();
        });
        if (out.length >= body.replace(/\s*$/, '').length) return out;
        return `${out.replace(/[\s.]+$/, '')}…`;
    }
    return body.length <= maxChars ? body : `${body.slice(0, maxChars - 1).trimEnd()}…`;
}

(window as unknown as { GraphNetwork: NetworkApi }).GraphNetwork = {
    /**
     * Initializes the vis.js Network on the graph container element.
     * Creates the legend overlay, sets up click/context event handlers,
     * and loads the initial graph data.
     */
    async init() {
        const container = document.getElementById('graph-container');
        if (!container) return;

        const options = GraphNetwork.buildOptions();
        graphManager.network = new vis.Network(container, { nodes: [], edges: [] }, options);
        if ((window as unknown as RelLayoutWin).GraphRelativeLayout) (window as unknown as RelLayoutWin).GraphRelativeLayout!.attach(graphManager.network);

        // Create legend overlay (after vis.js so it doesn't get cleared)
        graphManager._legendEl = document.createElement('div');
        graphManager._legendEl.className = 'graph-legend';
        window.Lit.render(networkManagerHtmlTag`${window.Lit.unsafeHTML(GraphNetwork.buildLegendHTML())}`, graphManager._legendEl);
        graphManager._legendVisible = false;
        graphManager._legendEl.style.display = 'none';
        container.appendChild(graphManager._legendEl);

        // Create tag filter overlay (colored tag indicators + click-to-filter)
        graphManager._tagPanelEl = document.createElement('div');
        graphManager._tagPanelEl.className = 'graph-legend graph-tag-panel';
        window.Lit.render(networkManagerHtmlTag`<div class="graph-legend-inner"><div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">🏷️ Tags</div></div>`, graphManager._tagPanelEl);
        graphManager._tagPanelVisible = false;
        graphManager._tagPanelEl.style.display = 'none';
        graphManager._tagFilter = null;
        graphManager._tagLibrary = null;
        container.appendChild(graphManager._tagPanelEl);
        GraphNetwork.ensureTagLibrary();

        graphManager.network.on("click", (params: any) => GraphEventHandlers.onClick(params));
        graphManager.network.on("doubleClick", (params: any) => GraphEventHandlers.onDoubleClick(params));
        GraphNetwork._syncLayoutButton && GraphNetwork._syncLayoutButton();
        graphManager.network.on("oncontext", (params: any) => GraphEventHandlers.onContext(params));
        GraphNetwork._bindEdgeHoverTooltips();

        // Label LOD: re-decide which names to draw when the zoom settles.
        let labelZoomTimer: ReturnType<typeof setTimeout> | null = null;
        graphManager.network.on("zoom", () => {
            if (labelZoomTimer) clearTimeout(labelZoomTimer);
            labelZoomTimer = setTimeout(() => GraphNetwork.applyNodeLabelVisibility(), 140);
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && graphManager._pendingConnection) {
                graphManager.cancelPendingConnection();
            }
        });

        // Scope offsets must be known before the first layout, or a moved zone
        // would render at its painted position until the next reload (task-523).
        await graphManager.loadScopeFilterOptions();
        await GraphNetwork.loadGraphData();
        setTimeout(() => GraphNetwork.fitView(), 100);
    },

    /**
     * The central gravity the *current* layout wants.
     *
     * centralGravity is a global field applied to every node on every solver
     * iteration, and vis exposes it as one graph-wide number with no per-node
     * control, so the only way to change it per mode is to push a new value on
     * every switch. The rule lives here so the switches cannot disagree:
     *
     *  - **graph** (the free force layout): ON. It is what holds a component
     *    that is not edge-connected to the rest of the world near the middle
     *    instead of letting it drift off.
     *  - **map**: 0. The painted lattice *is* the map — areas are pinned to
     *    their cells — so a pull toward the canvas origin fights the art. With it
     *    off, a room's contents are held by their own `in` edge spring.
     *  - **levels**: 0. vis's hierarchical layout owns positions and forces
     *    physics off, so this is never read; it is set anyway so that switching
     *    back does not inherit a number chosen for a layout that was not running.
     *
     * @param {string} [layout] - 'graph'|'map'|'levels'; defaults to the live one
     * @returns {number}
     */
    centralGravityFor(layout?: string): number {
        const gm = (typeof graphManager !== 'undefined' && graphManager) || null;
        const current = layout || (gm && typeof gm.activeLayout === 'function'
            ? gm.activeLayout()
            : (gm && gm._levelsMode && gm._levelsMode() ? 'levels' : (gm && gm._cardinalLayout ? 'map' : 'graph')));
        if (current === 'map' || current === 'levels') return 0;
        // Per solver, because the two formulations are not on the same scale
        // (barnesHut's historical default is 0.3, forceAtlas2's is 0.005).
        return ((config || ({} as ConfigManager)).graphSolver || 'forceAtlas2Based') === 'barnesHut' ? 0.3 : 0.05;
    },

    /**
     * The one place a layout switch pushes solver settings.
     *
     * Every mode change needs `physics.enabled` to follow, and now `centralGravity`
     * with it — which is why the scattered `setOptions({physics:{enabled}})` calls
     * come through here rather than each re-deciding. (This area has already been
     * bitten once: four silent re-enablers had to be fixed when Levels was added.)
     *
     * @param {boolean} enabled - whether the solver should run
     */
    applyModePhysics(enabled: boolean): void {
        const gm = (typeof graphManager !== 'undefined' && graphManager) || null;
        if (!gm || !gm.network || !gm.network.setOptions) return;
        const cfg = config || ({} as ConfigManager);
        const solver = cfg.graphSolver || 'forceAtlas2Based';
        gm.network.setOptions({
            physics: {
                enabled: !!enabled,
                [solver as string]: { centralGravity: GraphNetwork.centralGravityFor() }
            }
        });
    },

    /**
     * Builds and returns the vis.js options object with physics, interaction,
     * manipulation, and group styling configuration.
     *
     * @returns {Object} vis.js Network options
     */
    buildOptions() {
        // `config` is a top-level const (lexical global) — NEVER window.config
        // (which is always undefined and made every slider a silent no-op).
        const cfg = config || ({} as ConfigManager);
        const solver = cfg.graphSolver || 'forceAtlas2Based';
        // Hierarchical mode: vis places every node by relation level, so physics
        // is off and each parent sits a level above its children (task-485).
        const levels = (cfg.graphLayoutMode || 'free') === 'levels';
        // The solver's spring length is a world-relative distance, so on a painted
        // map it has to follow the pitch: at 40px a 100px spring is a short hop,
        // and on a 260px map the same spring is a 5x-too-short leash, so the
        // solver stretches every edge across the canvas instead of settling the
        // loose nodes next to the rooms they belong to (bug-53). An explicit
        // `graphSpringLength` is the author's own number and always wins.
        const mapK = GraphNetwork.mapSizeScale();
        const spring = (fallback: number) => (cfg.graphSpringLength != null
            ? cfg.graphSpringLength : Math.round(fallback * mapK));
        // Cell-relative mark sizes for a painted map (the map view and Levels keep
        // their original pixel sizes).
        const marks = (GraphNetwork as any)._markSizes();
        // centralGravity follows the layout (see centralGravityFor): ON in the free
        // graph layout, 0 for Map and Levels. The map-mode numbers below are the
        // balance measured with it off — with no central pull, repulsion is the
        // only thing pushing, and the old forceAtlas2 numbers (repulsion -40,
        // spring 0.02) lost it: a measured cold load ran away at +4069px of width
        // per 12s and left contents a median 888px from the room that holds them.
        // Weaker repulsion and a stiffer spring put them back beside their rooms
        // (median 147px, p90 258px). Measured on kraktooth_goblin_camp, 638 nodes.
        const gravity = GraphNetwork.centralGravityFor();
        const physicsBase = solver === 'barnesHut'
            ? { barnesHut: { gravitationalConstant: cfg.graphGravitationalConstant ?? -3000, centralGravity: gravity, springLength: spring(120), springConstant: cfg.graphSpringConstant ?? 0.04, damping: cfg.graphDamping ?? 0.09 } }
            : { forceAtlas2Based: { gravitationalConstant: cfg.graphGravitationalConstant ?? -8, centralGravity: gravity, springLength: spring(120), springConstant: cfg.graphSpringConstant ?? 0.1, damping: cfg.graphDamping ?? 0.4 } };
        return {
            physics: {
                enabled: !levels, solver,
                ...physicsBase,
                stabilization: { iterations: 100, fit: false }
            },
            interaction: { hover: true, tooltipDelay: 200, multiselect: false },
            edges: {
                font: { multi: 'html' },
                arrows: cfg.graphArrows !== false ? { to: { enabled: true, scaleFactor: 0.5 } } : { to: { enabled: false } },
                width: cfg.graphEdgeWidth || 1
            },
            layout: levels
                ? {
                    hierarchical: {
                        enabled: true,
                        direction: 'UD',
                        sortMethod: 'directed',
                        levelSeparation: 150,
                        nodeSpacing: 110,
                        treeSpacing: 170,
                        blockShifting: true,
                        edgeMinimization: true,
                        parentCentralization: true,
                        shakeTowards: 'roots'
                    }
                }
                : {
                    // Explicitly off: vis merges options, so switching back to
                    // free would otherwise leave the hierarchical engine enabled.
                    hierarchical: { enabled: false },
                    improvedLayout: cfg.graphImprovedLayout === true
                },
            manipulation: {
                enabled: true, initiallyActive: false,
                addNode: (data: any, callback: any) => GraphEventHandlers.onAddNode(data, callback),
                addEdge: (data: any, callback: any) => GraphEventHandlers.onAddEdge(data, callback)
            },
            groups: {
            // NOTE: `shape` is deliberately NOT set on groups. vis-network's
            // group options override a node's own `shape`, so an image node
            // (shape: circularImage) was silently drawn as its group shape and
            // the image never appeared. Shapes are assigned per node in
            // buildNodeConfig instead; groups keep color/font/size only.
            //
            // On a painted map the sizes are fixed px (`marks`, task-748); the
            // graph view and Levels keep their original fixed pixel sizes. Fonts
            // take the fixed map size in Map, their original size elsewhere.
            area: { color: { background: '#2d333b', border: '#58a6ff' }, font: { color: '#c9d1d9', size: marks.areaFont }, borderWidth: 2, margin: { top: marks.areaPadY, bottom: marks.areaPadY, left: marks.areaPad, right: marks.areaPad } },
            item: { color: { background: '#3d2e1a', border: '#e3b341' }, font: { color: '#e3b341', size: marks.itemFont }, size: marks.itemSize, borderWidth: 1 },
            way: { color: { background: '#1a3a2a', border: '#4ec9b0' }, font: { color: '#4ec9b0', size: marks.wayFont }, size: marks.waySize, borderWidth: 1 },
            character: { color: { background: '#2a1a3d', border: '#bc8cff' }, font: { color: '#bc8cff', size: marks.charFont }, size: marks.charSize, borderWidth: 2 }
            }
        };
    },

    /**
     * The map pitch relative to the default 40px cell, and **only** in the Map
     * layout (1 in the graph view and Levels). Used where a distance must follow
     * the cell - the solver's spring length - not for mark sizes, which are fixed
     * px (`_markSizes()`, task-748).
     */
    mapSizeScale() {
        if (!graphManager || graphManager._cardinalLayout !== true) return 1;
        const pitch = (typeof GraphLayoutEngine !== 'undefined'
            && (GraphLayoutEngine as unknown as { mapSpacing?: () => number }).mapSpacing)
            ? (GraphLayoutEngine as unknown as { mapSpacing: () => number }).mapSpacing() : 40;
        return pitch / 40;
    },

    /**
     * Drawn size of each mark on a painted map, in fixed px
     * (`GraphLayoutEngine.MAP_MARK_PX`). Returns the original fixed pixel sizes
     * outside the Map layout, so the graph view and Levels are untouched. The
     * Node-size slider multiplies the shapes and card padding, never the font, so
     * labels keep a readable size while marks grow under them. Fixed, not
     * pitch-scaled: the pitch is derived *from* these now (task-748).
     */
    _markSizes() {
        const ns = GraphNetwork.nodeSizeScale();
        const inMap = !!graphManager && graphManager._cardinalLayout === true;
        const LE: any = typeof GraphLayoutEngine !== 'undefined' ? GraphLayoutEngine : null;
        if (inMap && LE && LE.markSize && LE.markFontPx && LE.markCardPad) {
            const font = LE.markFontPx();
            const pad = LE.markCardPad() * ns;
            return {
                areaFont: font, areaPad: pad, areaPadY: pad,
                itemFont: font * 0.8, itemSize: LE.markSize('item') * ns,
                wayFont: font * 0.8, waySize: LE.markSize('way') * ns,
                charFont: font, charSize: LE.markSize('character') * ns,
            };
        }
        return {
            areaFont: 14, areaPad: 27 * ns, areaPadY: 21 * ns,
            itemFont: 12, itemSize: 18 * ns,
            wayFont: 14, waySize: 14 * ns,
            charFont: 14, charSize: 24 * ns,
        };
    },

    /**
     * The user's Node size multiplier (⚙ Tune → Look): multiplies the drawn
     * size of item/way/character nodes and area card padding. Clamped to the
     * slider's range; 1 everywhere when unset, so nothing changes by default.
     * The separation pass multiplies its type radii by the same value, so a
     * bigger node is granted correspondingly more room. Font sizes deliberately
     * stay on `mapSizeScale()` only — labels keep a readable size while shapes
     * grow under it.
     */
    nodeSizeScale(): number {
        const n = Number(typeof config !== 'undefined' && config ? config.graphNodeScale : NaN);
        if (!Number.isFinite(n) || n <= 0) return 1;
        return Math.max(0.5, Math.min(n, 2));
    },

    /**
     * Adopt the mark-envelope pitch (task-748), unless the user has taken the
     * pitch into their own hands (task-526).
     *
     * Runs at the top of every graph load, *before* anything reads the pitch: the
     * lattice and the background art are both derived from it, so a pitch settled
     * afterwards would leave them disagreeing. Returns true when the pitch moved,
     * so the caller can re-fit the art (which is positioned in px).
     *
     * The override is a stored flag, not a comparison against the last value: a
     * user who deliberately sits at 40px/cell must keep 40px/cell on every load,
     * and a scope switch must not silently re-derive it out from under them.
     */
    applyAutoMapSpacing(nodesObj: any): boolean {
        if (!graphManager || graphManager._cardinalLayout !== true) return false;
        if (graphManager._mapSpacingAuto === false) return false;
        if (typeof config === 'undefined' || !config) return false;
        let next: number;
        try {
            next = (GraphLayoutEngine as unknown as { autoMapSpacing(nodes: any): number }).autoMapSpacing(nodesObj);
        } catch (err) {
            return false;
        }
        if (!next) return false;
        const current = Number(config.graphMapSpacing);
        if (Number.isFinite(current) && Math.round(current) === next) return false;
        config.graphMapSpacing = next;
        // Deliberately not persisted: this is a derived default, so the stored
        // value stays "whatever the user last chose" and the flag stays the truth
        // about whether they chose one.
        if (graphManager._syncMapSpacingButton) graphManager._syncMapSpacingButton();
        const background = (window as unknown as RelLayoutWin).GraphBackground;
        if (background) {
            // The art is positioned in px from this same pitch, so it has to move
            // with it — for *every* mounted reference, because the whole-world view
            // has no single grid and the ordinary per-scope reconcile stops there.
            // Not `fitToPaintedGrid`: that persists the world, and this is a load
            // path. Not awaited — a grid fetch per scope must not stall the layout.
            // Guarded on the module only: a `typeof … === 'function'` guard here is
            // what let commit 6fd774b8 delete `reconcileAllForGapChange` and leave
            // this call site silently doing nothing (task-526).
            try { void background.reconcileAllForGapChange(); } catch (err) { /* ignore */ }
        }
        return true;
    },

    /**
     * Apply the user's physics/appearance settings to the live network.
     *
     * Default (tuning a graph that is already on screen): hand the new force
     * parameters to the running simulation via setOptions() and wake the
     * solver — vis.js freezes it after its initial stabilization, so without
     * startSimulation() setOptions alone never moves a node. Nodes keep their
     * positions and settle under the new forces, and the camera never moves.
     * Measured against the old behavior: it blanked the load signature,
     * refetched the whole dataset, reseeded the rings and re-stabilized on
     * every slider tick, and the async rebuild re-fit the camera ~1s later —
     * tuning physics felt like the graph reloading under the user.
     *
     * `rebuild` (a Levels/Free switch, which changes WHAT is laid out rather
     * than how it settles) keeps the old full re-derivation: reload the
     * dataset, reseed the ring caches so the seed re-applies on
     * stabilizationIterationsDone, restabilize. The camera reset is wanted
     * there — a different layout is a different view.
     *
     * Children are held by their own edge springs ("a seed, not a leash" —
     * graph/relative-layout.ts), so a changed Item Edge Length re-orbits them
     * by simulation in the default path; no reseed needed.
     *
     * @param {boolean} [rebuild] - re-derive the layout from data (mode switches)
     */
    /** Snapshot of the arrangement knobs (edge lengths + guard) last applied. */
    _lastArrangement: '',

    /**
     * Restamp per-edge rest lengths in place. Edge lengths live in the dataset
     * (connections size to their labels or a per-way `edge_length`; attachments
     * use Contents length), so a changed Contents length reaches the solver only
     * when the dataset is rebuilt. The live edge options carry the drawn length,
     * so update them directly; the dataset is refetched from the server on the
     * next rebuild anyway.
     *
     * @returns {number} how many edges were restamped
     */
    refreshEdgeLengths(): number {
        const gm = (typeof graphManager !== 'undefined' && graphManager) || null;
        if (!gm || !gm.network || !gm.network.body) return 0;
        const body = gm.network.body;
        const itemLen = (typeof config !== 'undefined' && config && Number(config.graphItemEdgeLength)) || 35;
        let updated = 0;
        for (const eid of body.edgeIndices) {
            const edge = body.edges[eid];
            if (!edge || !edge.options) continue;
            const type = String(edge.options.type || '');
            if (!GRAPH_ATTACH_EDGE_TYPES.has(type) && type !== 'triggers' && type !== 'grappled') continue;
            if (Number(edge.options.length) === itemLen) continue;
            try { edge.setOptions({ length: itemLen }); updated++; } catch (err) { /* ignore */ }
        }
        return updated;
    },

    applyGraphSettings(rebuild = false) {
        if (!graphManager.network) return;
        const levelsOn = ((typeof config !== 'undefined' && config && config.graphLayoutMode) || 'free') === 'levels';
        graphManager._physicsEnabled = !levelsOn;
        graphManager.network.setOptions(GraphNetwork.buildOptions());
        if (!levelsOn && graphManager._physicsEnabled) {
            try {
                graphManager.network.startSimulation();
            } catch (err) { /* ignore — already running */ }
        }
        if (!rebuild) {
            // Edge rest lengths and the overlap guard live outside the solver's
            // options: lengths are stamped per edge in the dataset (attachments
            // from Contents length, connections from their labels or a per-way
            // edge_length), and the guard runs once per layout pass. The full
            // rebuild this path replaced refreshed them as a side effect —
            // re-derive them here whenever a knob that feeds them moved, or
            // dragging Contents length / the guard knobs does nothing until the
            // next data reload (measured: attachment distances never moved).
            const arrangement = [
                config && (config as Record<string, unknown>).graphItemEdgeLength,
                config && (config as Record<string, unknown>).graphRepelEnabled,
                config && (config as Record<string, unknown>).graphRepelStrength,
                config && (config as Record<string, unknown>).graphRepelMin,
                config && (config as Record<string, unknown>).graphRepelMax,
                config && (config as Record<string, unknown>).graphRepelPull,
                config && (config as Record<string, unknown>).graphNodeScale,
            ].join('|');
            if (arrangement !== GraphNetwork._lastArrangement) {
                GraphNetwork._lastArrangement = arrangement;
                try { GraphNetwork.refreshEdgeLengths(); } catch (err) { /* ignore */ }
                const rel = (window as unknown as RelLayoutWin).GraphRelativeLayout;
                if (rel && typeof rel.resolveSeparation === 'function') {
                    try { rel.resolveSeparation(); } catch (err) { /* ignore */ }
                }
            }
            if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncAll();
            return;
        }
        if ((window as unknown as RelLayoutWin).GraphRelativeLayout && !levelsOn) (window as unknown as RelLayoutWin).GraphRelativeLayout!.reseed();
        GraphNetwork.loadGraphData();
        // Hierarchical layout places every node itself, so there is nothing to
        // simulate — and stabilize() would turn the solver back on and undo it.
        if (levelsOn) {
            GraphNetwork._syncLayoutButton();
            if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncAll();
            return;
        }
        // Re-run the simulation with the new force parameters. After the
        // initial stabilization vis.js freezes the network (physics.stabilized
        // = true), so setOptions() alone never moves a node — explicitly
        // re-stabilize so slider changes actually reshape the layout.
        try {
            graphManager.network.stabilize(200);
        } catch (err) { /* ignore — settings apply on the next reload */ }
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncAll();
    },

    /**
     * Fetches node and edge data from the API and updates the vis.js network.
     * Includes a signature-based deduplication to skip redundant reloads,
     * preserves node positions when possible, and applies cardinal layout
     * or search filters as needed.
     */
    async loadGraphData() {
        if (!graphManager.network) return;
        try {
            // A selected scope loads only that scope's slice (areas + ways +
            // characters, items optional); without one the whole world loads.
            // Loading one scope at a time is what keeps a densely painted
            // WorldPainter world from freezing the canvas — the browser never
            // receives nodes outside the scope (task-397 step 3 / task-400).
            const scopeId = graphManager._scopeFilter || null;
            let nodesObj, edgesArr;
            if (scopeId) {
                try {
                    const sub = await (ApiClient as unknown as { getScopeSubgraph(id: string, withAreas: boolean): Promise<any> }).getScopeSubgraph(scopeId, true);
                    nodesObj = sub.nodes || {};
                    edgesArr = sub.edges || [];
                } catch (err) {
                    // Stale selection (e.g. after a scenario load): drop it and
                    // fall back to the whole world rather than showing nothing.
                    graphManager._scopeFilter = null;
                    const sel = document.getElementById('graph-scope-filter') as HTMLSelectElement | null;
                    if (sel) sel.value = '';
                    nodesObj = await (ApiClient as unknown as { getGraphNodes(): Promise<any> }).getGraphNodes();
                    edgesArr = await (ApiClient as unknown as { getGraphEdges(): Promise<any> }).getGraphEdges();
                }
            } else {
                nodesObj = await (ApiClient as unknown as { getGraphNodes(): Promise<any> }).getGraphNodes();
                edgesArr = await (ApiClient as unknown as { getGraphEdges(): Promise<any> }).getGraphEdges();
            }

            // Skip reload if graph structure hasn't changed (avoids jitter on tick updates).
            // The signature must include the RESOLVED character avatar (current
            // emotion -> profile), not just `properties.image`: an emotion change
            // or a profile-only upload leaves `image` untouched, and a stale
            // signature would then keep the node on the previous face.
            const nodeSig = Object.entries(nodesObj)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([id, nodeData]: [string, any]) => {
                    const avatar = (window as unknown as RelLayoutWin).CharacterArt
                        ? (window as unknown as RelLayoutWin).CharacterArt!.avatarFor(nodeData.properties, (window as unknown as RelLayoutWin).CharacterArt!.emotionKeyForName(nodeData.name))
                        : (nodeData.properties?.image || '');
                    return `${id}:${nodeData.type}:${nodeData.properties?.current_state || ''}:${nodeData.properties?.central_gravity_enabled !== false}:${avatar}`;
                })
                .join('|');
            const edgeSig = edgesArr
                .map((edgeObj: any) => `${edgeObj.source}:${edgeObj.target}:${edgeObj.type}:${edgeObj.properties?.description || ''}`)
                .sort()
                .join('|');
            const sig = `${graphManager._scopeFilter || '*'}|${nodeSig}|${edgeSig}`;
            if (sig === graphManager._lastSig) return;
            graphManager._lastSig = sig;

            // Preserve node positions before reload
            let savedPositions = {};
            try { savedPositions = graphManager.network.getPositions(); } catch (err) { /* ignore */ }

            // Preserve the camera too. vis.js setData() emits initPhysics, and the
            // physics engine (re)stabilization ends in a View.fit() that snaps the
            // viewport to the fit-all position/scale — destroying the user's zoom
            // and pan on every reload. Only restore once the network has data; the
            // very first load keeps the fitView() in init().
            let savedView = null;
            try {
                if (graphManager.network.body?.data?.nodes?.length > 0) {
                    savedView = {
                        position: graphManager.network.getViewPosition(),
                        scale: graphManager.network.getScale()
                    };
                }
            } catch (err) { /* ignore */ }

            graphManager.nodes.clear();
            graphManager._revealedItemIds = new Map();
            graphManager._revealedAreaIds.clear();
            // A new node set invalidates the label LOD decision + cache.
            graphManager._nodeLabelsShown = null;
            graphManager._labelCache = null;
            const visNodes = [];
            const visEdges = [];
            graphManager._graphNodesObj = nodesObj;
            graphManager._graphEdgesArr = edgesArr;
            graphManager._edgeTooltipHtml = {};

            // Decide the map pitch before anything reads it: node sizes, the
            // lattice and the background art are all derived from it, so a pitch
            // settled afterwards would leave them disagreeing (task-526).
            try { this.applyAutoMapSpacing(nodesObj); } catch (err) { /* keep the current pitch */ }
            // The stepper reads the effective pitch and whether it is derived, and
            // the menu says so when the map is drawing dots — both cheap DOM writes
            // that must be told the truth on every load, not only when it moves.
            if (graphManager._syncMapSpacingButton) graphManager._syncMapSpacingButton();

            // Visibility (floor filter, inhabited-areas, items/triggers toggles,
            // revealed areas/items, search) is applied in place later by
            // applyVisibility(), so toggles never need a full setData() rebuild
            // (which was causing zoom/pan loss + jitter). Build every node here.

            for (const id in nodesObj) {
                const nodeData = nodesObj[id];
                graphManager.nodes.set(id, nodeData);
                visNodes.push(this.buildNodeConfig(nodeData));
            }

            const renderedConnectionPairs = new Set<string>();

            // Node-type lookup for endpoint-aware edge suppression.
            const nodeTypeById: Record<string, string> = {};
            for (const id in nodesObj) nodeTypeById[id] = nodesObj[id] && nodesObj[id].type;

            // The backend emits both a carrying and an equipped edge to the same
            // item↔character pair. Track equipped pairs so the redundant carrying
            // edge is suppressed.
            const equippedPairs = new Set<string>();
            for (const e of edgesArr) {
                if (EdgeTypes.resolve(e.type || 'connection') === 'equipped') {
                    equippedPairs.add([e.source, e.target].sort().join('|'));
                }
            }

            for (const edgeObj of edgesArr) {
                const rawType = edgeObj.type || 'connection';
                const edgeType = EdgeTypes.resolve(rawType);
                const style = edgeObj.properties?.style || {};

                // Never draw a "connection" edge between a character and an item —
                // the backend sometimes emits one alongside carrying/equipped.
                if (edgeType === 'connection') {
                    const st = nodeTypeById[edgeObj.source];
                    const tt = nodeTypeById[edgeObj.target];
                    if ((st === 'character' && tt === 'item') || (st === 'item' && tt === 'character')) continue;
                }
                // An equipped item is not separately "carrying" — drop the duplicate.
                if (edgeType === 'carrying') {
                    const pairKey = [edgeObj.source, edgeObj.target].sort().join('|');
                    if (equippedPairs.has(pairKey)) continue;
                }
                const typeCfg = EdgeTypes.getConfig(edgeType);
                let defaultColor = typeCfg.color;
                let defaultDashes = edgeType === 'unlocks';

                let edgeLabel = '';
                if (graphManager._showEdgeLabels) {
                    edgeLabel = edgeType;
                } else if (edgeType === 'unlocks') {
                    // A whole `properties.description` is arbitrary-length
                    // author-written prose, which is the one label that cannot be
                    // trusted to be short (task-558). Three lines is what fits the
                    // edge without pushing its ends apart; the full text stays on
                    // the hover tooltip that is already built for this edge.
                    edgeLabel = _firstSentence(
                        edgeObj.properties?.description || 'unlocks', 3);
                }

                // Collapse bidirectional connection pairs into a single visual edge
                if (edgeType === 'connection') {
                    const pairKey = [edgeObj.source, edgeObj.target].sort().join('|');
                    if (renderedConnectionPairs.has(pairKey)) continue;
                    renderedConnectionPairs.add(pairKey);
                    const otherEdges = edgesArr.filter((e: any) =>
                        e.type === 'connection' &&
                        ((e.source === edgeObj.target && e.target === edgeObj.source) ||
                         (e.source === edgeObj.source && e.target === edgeObj.target))
                    );
                    if (otherEdges.length > 1) {
                        const dirs = otherEdges.map((e: any) => e.properties?.direction).filter(Boolean);
                        edgeLabel = (graphManager._showEdgeLabels ? '↔ ' : '') + dirs.join(' ↔ ');
                    }
                }

                if (typeof WayAuthoring !== 'undefined') {
                    const tip = WayAuthoring.buildEdgeTooltipForVis(edgeObj.source, edgeObj.target, nodesObj, edgesArr);
                    if (tip) {
                        graphManager._edgeTooltipHtml[`${edgeObj.source}|${edgeObj.target}`] = tip.html;
                    }
                }

                // Attachment edges (item -> its parent, or a trigger -> its host)
                // get short springs so a child settles next to its parent rather
                // than floating at the global length. Children are in the solver
                // and that short spring is the only thing keeping them local
                // (there is no central gravity to fight).
                const isAttachment = GRAPH_ATTACH_EDGE_TYPES.has(edgeType)
                    || edgeType === 'triggers' || edgeType === 'grappled';

                // In hierarchical mode a relation edge is the level link: orient
                // it parent -> child from the resolved relations rather than the
                // stored direction, which is inconsistent for `in` (bug-44).
                const levelsMode = ((typeof config !== 'undefined' && config && config.graphLayoutMode) || 'free') === 'levels';
                const levelsPlan = (levelsMode && (window as unknown as RelLayoutWin).GraphRelativeLayout)
                    ? (isAttachment
                        ? (window as unknown as RelLayoutWin).GraphRelativeLayout!.levelEdge(edgeObj.source, edgeObj.target, nodesObj, edgesArr)
                        : (edgeType === 'connection'
                            ? (window as unknown as RelLayoutWin).GraphRelativeLayout!.connectionLevelEdge(edgeObj.source, edgeObj.target, nodesObj)
                            : null))
                    : null;

                let edgeLength = undefined;
                if (edgeType === 'connection') {
                    const targetNode = nodesObj[edgeObj.target];
                    const sourceNode = nodesObj[edgeObj.source];
                    const wayNode = targetNode?.type === 'way' ? targetNode : sourceNode?.type === 'way' ? sourceNode : null;
                    if (wayNode) {
                        const len = wayNode.properties?.edge_length;
                        if (len && len > 0) edgeLength = len;
                    }
                    // Dynamic default: a connection edge is only as long as its
                    // labels need. A short name ("west") stays tight; a long one
                    // ("northwest passage") gets room — so edges stop being
                    // stretched to the global spring length. A per-way
                    // `edge_length` property still wins.
                    if (!edgeLength) {
                        // Size to the label actually drawn along the edge: an
                        // unlabelled edge can be short, a long one needs room.
                        // Capped so a two-sided label can't stretch the layout.
                        edgeLength = _labelEdgeLength(edgeLabel);
                    }
                } else if (isAttachment) {
                    const len = (config || ({} as ConfigManager)).graphItemEdgeLength || 35;
                    edgeLength = len;
                }
                visEdges.push({
                    from: (levelsPlan && levelsPlan.from) || edgeObj.source,
                    to: (levelsPlan && levelsPlan.to) || edgeObj.target,
                    type: edgeType,
                    label: edgeLabel,
                    length: edgeLength,
                    // Hierarchical levels come from direction, so a relation
                    // stored child -> parent is flipped for layout and the arrow
                    // is flipped back to keep reading the right way (task-485).
                    arrows: (levelsPlan && levelsPlan.flipped)
                        ? (edgeType === 'connection' ? 'from,to' : 'from')
                        : (edgeType === 'connection' ? 'from,to' : (style.arrows || 'to')),
                    dashes: style.dashes !== undefined ? style.dashes : defaultDashes,
                    color: { color: style.color || defaultColor, highlight: '#4ec9b0' },
                    font: { color: style.color || defaultColor, size: graphManager._edgeLabelSize || 8, align: 'horizontal', strokeWidth: 2, strokeColor: '#0d1117', background: 'rgba(13,17,23,0.85)' },
                    // Edge labels are drawn on a canvas, so they wrap by **width**
                    // and not by the reader: `widthConstraint` breaks a long label
                    // onto more lines instead of letting it run off the edge (task-558).
                    // Edges only — a way *node*'s name is a node label, and growing
                    // the node box for it collides with the map layout's margins.
                    widthConstraint: { maximum: EDGE_LABEL_WRAP },
                    width: style.width || 1,
                    smooth: isAttachment ? false : undefined
                });
            }
            // Disable physics during data swap to avoid jitter
            const levelsOn = ((typeof config !== 'undefined' && config && config.graphLayoutMode) || 'free') === 'levels';
            const wasPhysics = graphManager._physicsEnabled && !levelsOn;
            GraphNetwork.applyModePhysics(false);
            graphManager.network.setData({ nodes: visNodes, edges: visEdges });
            // Restore positions only for nodes that still exist
            const newNodeIds = new Set(visNodes.map(nodeConfig => nodeConfig.id));
            for (const [id, pos] of Object.entries(savedPositions) as [string, { x: number; y: number }][]) {
                if (!newNodeIds.has(id)) continue;
                graphManager.network.moveNode(id, pos.x, pos.y);
            }
            // Apply cardinal-based area layout only in MAP mode: the Map tab
            // (`_cardinalLayout`). In the graph view nodes are placed by hand
            // (restored from `properties.x/y`), so auto-anchoring areas, ways
            // and loose nodes there moved a way the user had just positioned.
            // Not in hierarchical mode either: that layout owns every position.
            // The "way directions" overlay deliberately does NOT count as map
            // mode any more — it only labels ways (task-530), so picking it must
            // never rearrange the canvas behind the user's back.
            const mapMode = graphManager._cardinalLayout === true;
            // `worldState.areas` is a legacy per-area map that a generated
            // scope may not populate; the layout itself handles that (the
            // cardinal path no-ops on an empty map), and the painted-grid path
            // reads only `nodesObj`, so don't gate map mode on it.
            let layoutKind = null;
            if (!levelsOn && mapMode) {
                layoutKind = (GraphLayoutEngine as LayoutEngineExtra).applyCardinalLayout(nodesObj);
            }
            // A painted grid owns every position, so the toolbar must show
            // physics as unavailable rather than offering a toggle that the
            // next reload silently undoes.
            graphManager._paintedGridLayout = layoutKind === 'grid';


        // Items, characters and triggers sit relative to whatever holds them,
        // derived fresh each load (task-485) — never a saved snapshot, so a
        // carried item follows its carrier. This must run in Map mode too: a
        // painted grid places areas and ways, but items/characters have no
        // painted coords and would otherwise pile up at the origin, fanning
        // their edges across the map (the follow timer sleeps itself when
        // physics is off, so there is no steady-state cost to leave it on).
        if ((window as unknown as RelLayoutWin).GraphRelativeLayout) {
            try { (window as unknown as RelLayoutWin).GraphRelativeLayout!.apply(); } catch (err) { /* ignore */ }
        }


            // Physics follows the user's choice, in Map mode too. The grid layout
            // turns the solver off only to place the lattice; the preference is
            // restored below, so a painted scope with physics on simulates after
            // every reload instead of being silently frozen. Consequence, by
            // design: nodes drift off the painted cells, and the map art (which is
            // positioned to that lattice) stops lining up with them. Locking the
            // node layout (🔒 in the background menu) still wins over both.
            // To go back to the old behaviour, restore `layoutKind !== 'grid'`.
            if (wasPhysics) {
                graphManager._physicsEnabled = true;
                GraphNetwork.applyModePhysics(true);
            }

            // Put the camera back where the user had it (setData's internal
            // stabilization re-fit it to the whole graph; positions were restored
            // above, now the viewport too).
            if (savedView) {
                try {
                    graphManager.network.moveTo({
                        position: savedView.position,
                        scale: savedView.scale,
                        animation: false
                    });
                } catch (err) { /* ignore */ }
            }

            // Apply visibility in place (floor filter, inhabited areas, items,
            // triggers, revealed nodes, and active search). Reuses the dataset we
            // just built so no second rebuild happens here.
            GraphNetwork.applyVisibility();

            // Attach rich tippy tooltips to nodes and edges
            GraphNetwork._attachTippyTooltips();

            // Re-apply trait + tag label decorations (tag library may load async)
            GraphNetwork._applyNodeLabelDecorations();

            // Now that labels are decorated, apply the zoom-LOD decision.
            GraphNetwork.applyNodeLabelVisibility(true);

            // Refresh floor picker options from areas now present
            graphManager.refreshFloorOptions();

            // Re-apply live NL-editor ghost previews (staged ops) after the
            // setData() rebuild wipes the dataset's extra nodes/edges.
            if ((window as unknown as RelLayoutWin).NLEditorGhosts?.refresh) {
                try { (window as unknown as RelLayoutWin).NLEditorGhosts!.refresh(); } catch (err) { /* ignore */ }
            }

            // Snapshot the structural styles BEFORE any overlay recolours them,
            // so switching overlays can reset in place (task-642). Without this
            // a trigger overlay's dim-everything (opacity 0.2, grey) stayed under
            // the next overlay and made heat/sound/light read alike.
            GraphNetwork._captureBaseStyles();
            // Re-render overlay views (map/outline) if active
            if (graphManager._viewMode !== 'graph') graphManager._renderCurrentView();
            // The toolbar's loaded-node stat reads _graphNodesObj, so repaint it
            // only now that the new dataset is in place (task-530).
            if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncAll();
        } catch (err) {
            console.warn("Graph API unavailable:", err);
        }
    },

    /**
     * Computes the set of node ids that should be visible right now based on
     * all active graph filters. See GraphProjector.computeVisibleNodeIds.
     *
     * @returns {Set<string>} ids of currently-visible nodes
     */
    _computeVisibleNodeIds() {
        return GraphProjector.computeVisibleNodeIds(
            graphManager._graphNodesObj || {},
            graphManager._graphEdgesArr || [],
            GraphProjector._viewState()
        );
    },

    /**
     * Applies the current visibility state to the live vis.js dataset in place.
     * Hides nodes via the `hidden` flag and hides edges whose endpoints are not
     * both visible. Called by toggles and filters instead of a full rebuild, so
     * zoom/pan and physics survive — the core fix for the laggy reloads.
     */
    applyVisibility() {
        const visibleIds = GraphNetwork._computeVisibleNodeIds();
        GraphProjector.applyVisibility(graphManager.network, visibleIds);
    },

    /**
     * Should node names be drawn right now?
     *
     * One rule: a name is worth drawing when a **cell** is big enough on screen
     * to hold it — `pitch × zoom >= graphLabelMinCellPx` (default 14px) — plus the
     * manual toggle. The old count gate (hide every name over
     * `graphLabelMaxNodes` until the raw network scale passed `graphLabelMinScale`
     * 0.6) measured the wrong thing: on a high-pitch map the raw scale sits near
     * zero however large the cells are, so the names never came back while
     * zooming (bug-528).
     */
    _nodeLabelPolicy() {
        if (!graphManager._showNodeLabels) return false;
        // A tiny non-map graph always shows its names.
        const total = Object.keys(graphManager._graphNodesObj || {}).length;
        if (!graphManager._cardinalLayout && total <= 400) return true;
        const LE: any = typeof GraphLayoutEngine !== 'undefined' ? GraphLayoutEngine : null;
        const pitch = LE && LE.mapSpacing ? LE.mapSpacing() : 40;
        let zoom = 1;
        try { zoom = graphManager.network.getScale(); } catch (err) { /* ignore */ }
        const cellPx = pitch * (Number.isFinite(zoom) && zoom > 0 ? zoom : 1);
        const minCellPx = Number((typeof config !== 'undefined' && config && config.graphLabelMinCellPx)) || 14;
        return cellPx >= minCellPx;
    },

    /**
     * Apply the label policy in one DataSet pass — only when the decision
     * changes, so zooming does not re-write 1k nodes every frame. Decorated
     * labels are cached while hidden and restored verbatim.
     */
    applyNodeLabelVisibility(force?: boolean): void {
        if (!graphManager.network) return;
        const nodesDS = graphManager.network.body && graphManager.network.body.data
            && graphManager.network.body.data.nodes;
        if (!nodesDS) return;
        const show = GraphNetwork._nodeLabelPolicy();
        if (!force && show === graphManager._nodeLabelsShown) return;
        graphManager._nodeLabelsShown = show;
        const src = graphManager._graphNodesObj || {};
        const updates = [];
        if (!show) {
            if (!graphManager._labelCache) {
                graphManager._labelCache = {};
                for (const id in src) {
                    const datum = nodesDS.get(id);
                    if (datum) graphManager._labelCache[id] = datum.label || '';
                }
            }
            for (const id in src) if (nodesDS.get(id)) updates.push({ id, label: '' });
        } else if (graphManager._labelCache) {
            for (const [id, label] of Object.entries(graphManager._labelCache)) {
                if (nodesDS.get(id)) updates.push({ id, label });
            }
            graphManager._labelCache = null;
        }
        if (updates.length) {
            nodesDS.update(updates);
            graphManager.network.redraw();
        }
        // The zoom LOD never changes the toggle itself: the button shows the
        // manual preference, the LOD is a rendering decision.
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncToggles();
    },

    /**
     * Builds a plain-text tooltip string for a graph node.
     * Shows different information depending on node type (area, item, way, character).
     *
     * @param {Object} nodeData - The node data object
     * @returns {string} Tooltip text
     */
    /** @deprecated Use GraphTooltips.buildTooltip */
    buildTooltip(nodeData: any): string {
        return GraphTooltips.buildTooltip(nodeData);
    },

    /** @deprecated Use GraphTooltips._escHtml */
    _escHtml(s: unknown): string {
        return GraphTooltips._escHtml(s);
    },

    /** @deprecated Use GraphTooltips.buildTooltipHtml */
    buildTooltipHtml(nodeData: any): string {
        return GraphTooltips.buildTooltipHtml(nodeData);
    },

    /** @deprecated Use GraphTooltips.bindEdgeHoverTooltips */
    _bindEdgeHoverTooltips() {
        return GraphTooltips.bindEdgeHoverTooltips();
    },

    /** @deprecated Use GraphTooltips.findGraphEdge */
    _findGraphEdge(fromId: string, toId: string): any {
        return GraphTooltips.findGraphEdge(fromId, toId);
    },

    /** @deprecated Use GraphTooltips.attachNodeTooltips */
    _attachTippyTooltips() {
        return GraphTooltips.attachNodeTooltips();
    },

    /**
     * Fits the network view to show all nodes with animation.
     */
    fitView() {
        graphManager.network.fit({ animation: true });
    },

    /**
     * Toggle vis's hierarchical (level) layout against the free physics layout
     * (task-485). Levels needs no per-frame work: the layout engine places every
     * node from the relation levels, so nothing drifts and nothing is stretched.
     * The button keeps a fixed label; GraphToolbar paints the state.
     */
    toggleLayoutMode() {
        const cfg: Record<string, unknown> = (typeof config !== 'undefined' && config) || {};
        cfg.graphLayoutMode = (cfg.graphLayoutMode as string) === 'levels' ? 'free' : 'levels';
        GraphNetwork._syncLayoutButton();
        // A mode switch changes what is laid out, not just how it settles —
        // the full re-derivation, not the in-place tuning path.
        GraphNetwork.applyGraphSettings(true);
        if ((cfg as { save?: () => void }).save) { try { (cfg as { save: () => void }).save(); } catch (err) { /* ignore */ } }
    },

    _syncLayoutButton() {
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncLayout();
    },
    /**
     * Toggles physics simulation on/off for the vis.js network. The button's
     * label is fixed ("⏸ Physics") and its state is aria-pressed; the toolbar
     * disables it with a reason when a layout or overlay owns positions.
     */
    togglePhysics() {
        graphManager._physicsEnabled = !graphManager._physicsEnabled;
        GraphNetwork.applyModePhysics(graphManager._physicsEnabled);
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncAll();
    },

    /**
     * Toggles the graph legend overlay visibility. The legend also has its own
     * ✕ (GraphToolbar.closeLegend); both go through the same flag so the View ▾
     * toggle and the panel can never disagree.
     */
    toggleLegend() {
        if (!graphManager._legendEl) return;
        graphManager._legendVisible = !graphManager._legendVisible;
        graphManager._legendEl.style.display = graphManager._legendVisible ? 'block' : 'none';
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncToggles();
    },

    toggleTriggers() {
        graphManager._showTriggers = !graphManager._showTriggers;
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncToggles();
        GraphNetwork.applyVisibility();
    },

    /**
     * Toggle node image thumbnails on the graph. Persists the preference so it
     * survives reloads. Requires node `image` properties (see the inspector
     * image widget / upload endpoint); nodes without an image keep their
     * normal shape.
     */
    toggleImages() {
        graphManager._showImages = !graphManager._showImages;
        try {
            localStorage.setItem('vw_graphShowImages', graphManager._showImages ? '1' : '0');
        } catch (e) { /* ignore */ }
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncToggles();
        graphManager._lastSig = '';
        GraphNetwork.loadGraphData();
    },

    toggleItems() {
        graphManager._showItems = !graphManager._showItems;
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncToggles();
        if (graphManager._showItems) {
            this.hideRevealedItems();
        }
        GraphNetwork.applyVisibility();
    },

    toggleInhabitedAreas() {
        graphManager._showOnlyInhabitedAreas = !graphManager._showOnlyInhabitedAreas;
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncToggles();
        if (!graphManager._showOnlyInhabitedAreas) {
            graphManager._revealedAreaIds.clear();
        }
        GraphNetwork.applyVisibility();
    },

    revealAreasForWay(wayId: string): void {
        if (!graphManager._showOnlyInhabitedAreas) return;
        const edgesArr = graphManager._graphEdgesArr || [];
        const connectedAreas = new Set();
        for (const edgeObj of edgesArr) {
            if (edgeObj.type !== 'connection') continue;
            if (edgeObj.source === wayId) connectedAreas.add(edgeObj.target);
            if (edgeObj.target === wayId) connectedAreas.add(edgeObj.source);
        }
        let changed = false;
        for (const areaId of connectedAreas) {
            if (!graphManager._revealedAreaIds.has(areaId)) {
                graphManager._revealedAreaIds.add(areaId);
                changed = true;
            }
        }
        if (changed) {
            GraphNetwork.applyVisibility();
        }
    },

    hideRevealedAreas() {
        if (graphManager._revealedAreaIds.size === 0) return;
        graphManager._revealedAreaIds.clear();
        GraphNetwork.applyVisibility();
    },

    /**
     * Builds a vis.js node config object for a node from its raw graph data.
     * Centralized so reveal-on-click can reuse the same label/tooltip/color
     * styling the main load path uses.
     *
     * @param {Object} nodeData - raw node data from the graph
     * @returns {Object} vis.js node configuration
     */
    buildNodeConfig(nodeData: any): any {
        const nodeConfig: Record<string, any> = {
            id: nodeData.id,
            label: typeof NodeBadges !== 'undefined'
                ? NodeBadges.formatLabel(nodeData, GraphNetwork._tagMetaFor(nodeData))
                : `${nodeData.name || nodeData.id}`,
            group: nodeData.type,
            // tippy renders the rich HTML tooltip on hoverNode; only fall back
            // to vis-network's native (plain-text) title when tippy is absent,
            // so the two never show at once.
            title: typeof tippy === 'undefined' ? GraphNetwork.buildTooltip(nodeData) : undefined,
            // The solver has no central gravity (see buildOptions), so a node in
            // it is held by its own edges rather than dragged to the middle. This
            // flag is therefore a straight "simulate this node or pin it": the
            // inspector's Physics-enabled off, or an explicit layout_static
            // (task-485). Off applies to every node type.
            physics: nodeData.properties?.central_gravity_enabled !== false
                && nodeData.properties?.layout_static !== true,
            // Per-node shape (groups no longer define shape — see options.groups).
            // The image branch below overrides this with circularImage.
            shape: ({ area: 'box', item: 'diamond', way: 'triangle', character: 'ellipse' } as Record<string, string>)[nodeData.type] || 'ellipse'
        };

        // On a painted map a card is capped at a fixed width so a wide name wraps
        // instead of overlapping its neighbour (task-748; the old pitch threshold
        // that swapped cards for dots, `mapCompact`/`mapDotSize`, is gone). Only
        // the Map layout caps; the graph view keeps natural card width.
        const inMap = !!graphManager && graphManager._cardinalLayout === true;
        const LE: any = typeof GraphLayoutEngine !== 'undefined' ? GraphLayoutEngine : null;
        if (inMap && LE && LE.markCardMax && nodeData.type === 'area') {
            nodeConfig.widthConstraint = { maximum: LE.markCardMax() * GraphNetwork.nodeSizeScale() };
        }

        // Seed the position: a painted node from its cell × pitch (the map frame),
        // a hand-placed node from its saved canvas x/y. `_gridUpdates` re-places
        // painted nodes on load anyway; seeding from the cell avoids a one-frame
        // jump from the compiler's `cell × 40` copy.
        const seedCell = nodeData.properties?.cell;
        if (inMap && LE && LE.gridPosition
                && seedCell && Number.isFinite(Number(seedCell.x)) && Number.isFinite(Number(seedCell.y))) {
            const seeded = LE.gridPosition(seedCell);
            if (seeded) { nodeConfig.x = seeded.x; nodeConfig.y = seeded.y; }
        } else if (typeof nodeData.properties?.x === 'number' && typeof nodeData.properties?.y === 'number') {
            // Saved layout: a node whose x/y were persisted to the world
            // (right-click → 🗺 → 💾 Save layout) loads back in place instead of
            // being freshly simulated. Whether it then HOLDS is the physics lock.
            nodeConfig.x = nodeData.properties.x;
            nodeConfig.y = nodeData.properties.y;
        }

        // Way nodes: color by state
        if (nodeData.type === 'way') {
            const state = (nodeData.properties?.current_state || 'closed').toLowerCase();
            if (state === 'open') {
                nodeConfig.color = { background: '#1a3a2a', border: '#3fb950' };
            } else if (state === 'closed') {
                nodeConfig.color = { background: '#2d3a1a', border: '#e3b341' };
            } else if (state === 'locked') {
                nodeConfig.color = { background: '#3a1a1a', border: '#f85149' };
            } else if (state === 'hidden') {
                nodeConfig.color = { background: '#1a1a2a', border: '#6e7681' };
            } else if (state === 'blocked') {
                nodeConfig.color = { background: '#3a2a1a', border: '#f0883e' };
            } else if (state === 'broken') {
                nodeConfig.color = { background: '#3a1a1a', border: '#f85149' };
            }
            if (nodeData.properties?.one_way) {
                nodeConfig.color = nodeConfig.color || { background: '#1a3a2a', border: '#4ec9b0' };
                nodeConfig.color.border = '#58a6ff';
            }
        }

        // Item nodes: color by state
        if (nodeData.type === 'item') {
            const state = (nodeData.properties?.current_state || 'normal').toLowerCase();
            if (state === 'lit') {
                nodeConfig.color = { background: '#3d2a0a', border: '#f0883e' };
            } else if (state === 'broken') {
                nodeConfig.color = { background: '#2d2d2d', border: '#6e7681' };
            } else if (state === 'depleted') {
                nodeConfig.color = { background: '#2d251a', border: '#8b7355' };
            }
        }

        // Node image mode (task-249): when enabled and the node carries art,
        // render it as a circular thumbnail instead of the plain colored shape.
        // The label stays so names remain readable; the rich tooltip still
        // carries the full details. Character nodes show their CURRENT-emotion
        // profile via CharacterArt (falling back to neutral/profile_image/image);
        // other node types fall through to their plain `image`. Nodes without
        // any art keep their normal group shape/color.
        const nodeAvatar = (window as unknown as RelLayoutWin).CharacterArt
            ? (window as unknown as RelLayoutWin).CharacterArt!.avatarFor(nodeData.properties, (window as unknown as RelLayoutWin).CharacterArt!.emotionKeyForName(nodeData.name))
            : (nodeData.properties?.image || '');
        if (graphManager._showImages && nodeAvatar) {
            nodeConfig.shape = 'circularImage';
            nodeConfig.image = nodeAvatar;
            nodeConfig.size = (({ area: 45, character: 28, item: 24, way: 22 } as Record<string, number>)[nodeData.type] || 24)
                * GraphNetwork.nodeSizeScale();
            nodeConfig.borderWidth = 2;
            // Clip the art to the circle and keep a visible state-colored border
            // rather than letting the image's own bounds set the node size.
            nodeConfig.shapeProperties = { useBorderWithImage: true, useImageSize: false };
        }

        return nodeConfig;
    },

    /**
     * Reveals the items directly connected to a node, used when items are
     * hidden. Clicking an area shows its items, a character shows carried +
     * equipped items, and an item shows its container contents. Siblings stay
     * open when drilling into a child; switching to a different parent clears
     * the previous parent's revealed items.
     *
     * @param {string} nodeId - id of the clicked node
     */
    revealItemsForNode(nodeId: string): void {
        if (graphManager._showItems) return; // items already visible
        const edgesArr = graphManager._graphEdgesArr || [];
        const revealed = new Set();
        for (const edgeObj of edgesArr) {
            const type = EdgeTypes.resolve(edgeObj.type || 'connection');
            if (type === 'connection' || type === 'unlocks' || type === 'triggers' || type === 'requires') continue;
            if (edgeObj.target !== nodeId) continue;
            const itemNodeData = graphManager.nodes.get(edgeObj.source);
            if (!itemNodeData || itemNodeData.type !== 'item') continue;
            revealed.add(edgeObj.source);
        }
        if (revealed.size === 0) return;

        // If nodeId is already a revealed item we're drilling into a child;
        // otherwise this is a new parent branch and we clear the previous set.
        let isDrillingIntoChild = false;
        for (const childSet of graphManager._revealedItemIds.values()) {
            if (childSet.has(nodeId)) {
                isDrillingIntoChild = true;
                break;
            }
        }
        if (!isDrillingIntoChild) {
            this.hideRevealedItems();
        }

        // Only track items not already revealed under some parent. The nodes
        // themselves are already in the dataset (built for the whole graph);
        // applyVisibility() unhides them and their edges in place.
        let added = false;
        for (const id of revealed) {
            let alreadyRevealed = false;
            for (const childSet of graphManager._revealedItemIds.values()) {
                if (childSet.has(id)) {
                    alreadyRevealed = true;
                    break;
                }
            }
            if (!alreadyRevealed) added = true;
        }
        if (added) {
            graphManager._revealedItemIds.set(nodeId, revealed);
            GraphNetwork.applyVisibility();
        }
    },

    /**
     * Removes any temporarily revealed item nodes from the network.
     */
    hideRevealedItems() {
        if (!graphManager._revealedItemIds || graphManager._revealedItemIds.size === 0) return;
        graphManager._revealedItemIds = new Map();
        GraphNetwork.applyVisibility();
    },

    /**
     * Legend panel chrome: title + a ✕. Every legend body (structural and the
     * per-overlay ones) is wrapped in it, so the panel is always closable —
     * task-530: it used to force itself open on every overlay change with no
     * way back except a menu item two clicks away.
     * @param {string} title - panel heading
     * @param {string} [body] - rows; omit for the default structural rows
     * @returns {string} legend HTML
     */
    legendChrome(title: string, body: string): any {
        const rows = body === undefined ? GraphNetwork.buildLegendRows() : body;
        return `<div class="graph-legend-inner">
            <div class="graph-legend-head">
                <span>${title}</span>
                <button class="graph-legend-close" data-legend-close type="button" title="Close the legend" aria-label="Close the legend">✕</button>
            </div>
            ${rows}
        </div>`;
    },

    /**
     * Builds and returns the HTML content for the graph legend.
     * Shows node type colors and state color mappings.
     *
     * @returns {string} Legend HTML string
     */
    buildLegendHTML() {
        return GraphNetwork.legendChrome('📖 Legend');
    },

    /** The structural legend's rows (everything that is not the panel chrome). */
    buildLegendRows() {
        return `
            <div class="legend-row"><span class="legend-swatch" style="background:#2d333b;border:2px solid #58a6ff;"></span> Area</div>
            <div class="legend-row"><span class="legend-swatch legend-diamond" style="background:#3d2e1a;border:2px solid #e3b341;"></span> Item</div>
            <div class="legend-row"><span class="legend-swatch legend-triangle" style="background:#1a3a2a;border:2px solid #4ec9b0;"></span> Way</div>
            <div class="legend-row"><span class="legend-swatch legend-ellipse" style="background:#2a1a3d;border:2px solid #bc8cff;"></span> Character</div>
            <div style="font-size:9px;color:var(--text-muted);margin:4px 0 2px;">Way states:</div>
            <div class="legend-row"><span class="legend-swatch" style="background:#3a1a1a;border:2px solid #f85149;"></span><span style="font-size:9px;"> locked · broken</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#1a3a1a;border:2px solid #3fb950;"></span><span style="font-size:9px;"> open</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#2d3a1a;border:2px solid #e3b341;"></span><span style="font-size:9px;"> closed</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#1a3a1a;border:2px solid #58a6ff;"></span><span style="font-size:9px;"> one-way (blue border)</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#3a2a1a;border:2px solid #f0883e;"></span><span style="font-size:9px;"> blocked</span></div>
            <div style="font-size:9px;color:var(--text-muted);margin:4px 0 2px;">Item states:</div>
            <div class="legend-row"><span class="legend-swatch" style="background:#3d2a0a;border:2px solid #f0883e;"></span><span style="font-size:9px;"> lit</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#2d2d2d;border:2px solid #6e7681;"></span><span style="font-size:9px;"> broken</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#2d251a;border:2px solid #8b7355;"></span><span style="font-size:9px;"> depleted</span></div>
            ${typeof NodeBadges !== 'undefined' ? NodeBadges.legendHtml() : ''}`;
    },

    // ──────────────────────────────────────────────
    //  TAG INDICATORS & FILTER
    // ──────────────────────────────────────────────

    /**
     * Load the tag library (GET /api/tags/search with no query returns all
     * tags) and cache it as {id: {id, name, icon, color}}. Re-applies node
     * label decorations once loaded.
     */
    ensureTagLibrary() {
        if (graphManager._tagLibrary) {
            GraphNetwork._applyNodeLabelDecorations();
            return;
        }
        fetch('/api/tags/search')
            .then(r => r.json())
            .then((tags: any[]) => {
                const byId: Record<string, any> = {};
                (tags || []).forEach((t: any) => { byId[t.id] = t; });
                graphManager._tagLibrary = byId;
                GraphNetwork._applyNodeLabelDecorations();
                if (graphManager._tagPanelVisible) GraphNetwork.renderTagPanel();
            })
            .catch(() => { graphManager._tagLibrary = {}; });
    },

    /**
     * Return {icon, color} for a node's tags, preferring library entries and
     * falling back to a deterministic hash color for unknown tags.
     */
    _tagMetaFor(nodeData: any): any[] {
        const props = nodeData.properties || {};
        let tags = props.tags || [];
        if (typeof tags === 'string') tags = tags.split(',').map(t => t.trim()).filter(Boolean);
        if (!Array.isArray(tags) || tags.length === 0) return [];
        const lib = graphManager._tagLibrary || {};
        const hashColor = (s: string): string => {
            let h = 0;
            for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
            return '#' + ((h % 0xffffff)).toString(16).padStart(6, '0');
        };
        return tags.map(tag => {
            const entry = lib[tag];
            return { tag, icon: entry?.icon || '🏷️', color: entry?.color || hashColor(tag) };
        });
    },

    /**
     * Apply trait badges + tag icons to node labels as visual indicators.
     */
    _applyNodeLabelDecorations() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes || typeof NodeBadges === 'undefined') return;
        nodes.forEach((node: any) => {
            const nodeData = graphManager.nodes.get(node.id);
            if (!nodeData) return;
            const label = NodeBadges.formatLabel(nodeData, GraphNetwork._tagMetaFor(nodeData));
            if (node.label !== label) nodes.update({ id: node.id, label, decoratedLabel: true });
        });
    },

    /** @deprecated Use _applyNodeLabelDecorations */
    _applyTagIconsToLabels() {
        GraphNetwork._applyNodeLabelDecorations();
    },

    /**
     * Toggle the tag filter panel visibility.
     */
    toggleTagPanel() {
        if (!graphManager._tagPanelEl) return;
        graphManager._tagPanelVisible = !graphManager._tagPanelVisible;
        graphManager._tagPanelEl.style.display = graphManager._tagPanelVisible ? 'block' : 'none';
        if (graphManager._tagPanelVisible) GraphNetwork.renderTagPanel();
    },

    /**
     * Render the tag filter panel: one clickable row per tag used in the
     * world, showing its color dot, icon, name, and node count.
     */
    renderTagPanel() {
        if (!graphManager._tagPanelEl) return;
        const lib = graphManager._tagLibrary || {};
        const counts: Record<string, number> = {};
        const metaById: Record<string, any> = {};
        graphManager.nodes.forEach((nodeData: any) => {
            GraphNetwork._tagMetaFor(nodeData).forEach((m: any) => {
                if (!metaById[m.tag]) metaById[m.tag] = m;
                counts[m.tag] = (counts[m.tag] || 0) + 1;
            });
        });
        const entries = Object.keys(counts).sort();
        const inner = [networkManagerHtmlTag`<div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">🏷️ Tags <span style="color:var(--text-muted);font-weight:400;">(click to filter)</span></div>`];
        if (graphManager._tagFilter) {
            inner.push(networkManagerHtmlTag`<div class="tag-filter-row tag-filter-active" data-tag="" @click=${() => GraphNetwork.setTagFilter('')}>✕ Clear filter</div>`);
        }
        entries.forEach((tag: string) => {
            const m = metaById[tag];
            const active = graphManager._tagFilter === tag;
            inner.push(networkManagerHtmlTag`
                <div class="tag-filter-row ${active ? 'tag-filter-active' : ''}" data-tag="${tag}" @click=${() => GraphNetwork.setTagFilter(tag)}>
                    <span class="legend-swatch" style="background:${m.color};"></span> ${m.icon} ${m.name || tag} <span style="color:var(--text-muted);">(${counts[tag]})</span>
                </div>`);
        });
        window.Lit.render(networkManagerHtmlTag`<div class="graph-legend-inner">${inner}</div>`, graphManager._tagPanelEl);
    },

    /**
     * Set the active tag filter and re-apply node visibility. Empty string
     * clears the filter.
     */
    setTagFilter(tagId: string | null): void {
        graphManager._tagFilter = tagId || null;
        GraphNetwork.applyTagFilter();
        GraphNetwork.renderTagPanel();
    },

    /**
     * Apply the active tag filter: matching nodes stay at full opacity with a
     * highlighted border, others are dimmed.
     */
    applyTagFilter() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes) return;
        const filter = graphManager._tagFilter;
        nodes.forEach((node: any) => {
            const nodeData = graphManager.nodes.get(node.id);
            let match = !filter;
            if (nodeData && filter) {
                match = GraphNetwork._tagMetaFor(nodeData).some((m: any) => m.tag === filter);
            }
            const opacity = match ? 1.0 : 0.15;
            if (node.opacity !== opacity) nodes.update({ id: node.id, opacity });
        });
    },

    /**
     * Applies a search filter to graph nodes by hiding non-matching nodes
     * and edges. Only nodes whose labels contain the query stay visible;
     * edges remain visible if at least one endpoint matches.
     *
     * @param {string} query - The search query string
     */
    /** @deprecated Use GraphFocus.applyFilter */
    applyFilter(query: string): void {
        return GraphFocus.applyFilter(query);
    },

    /** @deprecated Use GraphFocus.settleSearch */
    settleSearch() {
        return GraphFocus.settleSearch();
    },

    /** @deprecated Use GraphFocus._fitToSearchMatches */
    _fitToSearchMatches() {
        return GraphFocus._fitToSearchMatches();
    },

    /** @deprecated Use GraphFocus._kickClusterPhysics */
    _kickClusterPhysics() {
        return GraphFocus._kickClusterPhysics();
    },

    /** @deprecated Use GraphFocus.filterNodes */
    filterNodes(query: string): void {
        return GraphFocus.filterNodes(query);
    },

    // ──────────────────────────────────────────────
    //  GRAPH VIEW OVERLAYS
    // ──────────────────────────────────────────────

    /** @deprecated Use GraphOverlays.lightToInt */
    _lightToInt(raw: unknown): number {
        return GraphOverlays.lightToInt(raw);
    },

    /** @deprecated Use GraphOverlays.lightColors */
    _lightColors(level: number): string {
        return GraphOverlays.lightColors(level);
    },

    /** @deprecated Use GraphOverlays.heatColors */
    _heatColors(temp: number): string {
        return GraphOverlays.heatColors(temp);
    },

    /** @deprecated Use GraphOverlays.noiseColors */
    _noiseColors(noise: number): string {
        return GraphOverlays.noiseColors(noise);
    },

    /**
     * Legacy alias for the cached ambient-light table. See
     * GraphOverlays.computeAmbientLight (now change-cached: only recomputes
     * when the world graph / area environments actually change, so repeated
     * overlay applies don't re-walk every edge per lit item).
     */
    _computeAmbientLight() {
        return GraphOverlays.computeAmbientLight();
    },

    /**
     * Apply the Light overlay — color areas by ambient light with spill.
     */
    _applyLightOverlay() {
        GraphOverlays.applyLightOverlay();
        GraphNetwork._updateOverlayLegend('light', GraphOverlays.computeAmbientLight());
    },

    /**
     * Apply the Heat overlay — color areas by temperature with propagation.
     */
    _applyHeatOverlay() {
        GraphOverlays.applyHeatOverlay();
        GraphNetwork._updateOverlayLegend('heat');
    },

    /**
     * Apply the Sound overlay — color areas by noise level with propagation.
     */
    _applySoundOverlay() {
        GraphOverlays.applySoundOverlay();
        GraphNetwork._updateOverlayLegend('sound');
    },

    /**
     * Apply the Trigger overlay — highlight trigger sources/targets, dim others.
     */
    _applyTriggerOverlay() {
        GraphOverlays.applyTriggerOverlay();
        GraphNetwork._updateOverlayLegend('trigger');
    },

    /**
     * Apply the Cardinal overlay — label ways with cardinal direction.
     */
    _applyCardinalOverlay() {
        GraphOverlays.applyCardinalOverlay();
        GraphNetwork._updateOverlayLegend('cardinal');
    },

    /**
     * Clear overlay styles and restore default structural view.
     */
    _clearOverlay() {
        graphManager._lastSig = '';
        GraphNetwork.applyModePhysics(false);
        GraphNetwork.loadGraphData();
        const levelsOn = ((typeof config !== 'undefined' && config && config.graphLayoutMode) || 'free') === 'levels';
        if (graphManager._physicsEnabled && !levelsOn) {
            GraphNetwork.applyModePhysics(true);
        }
    },

    /**
     * Update the legend for the current overlay view.
     *
     * The panel is updated IN PLACE and never opened here: it used to force
     * itself open on every overlay change — including on the way back to the
     * structural view — and had no close affordance at all (task-530). Open it
     * from View ▾ ▸ Legend, or close it with its own ✕.
     */
    _updateOverlayLegend(mode: string, extraData?: unknown): void {
        if (!graphManager._legendEl) return;
        let title = null;
        let rows = '';
        if (mode === 'structural') {
            return;   // the structural legend is already in the panel
        } else if (mode === 'light') {
            title = '💡 Light Overlay';
            rows = `
                <div class="legend-row"><span class="legend-swatch" style="background:#0a0a0a;border:1px solid #333;"></span> pitch black 0-20</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#16162a;border:1px solid #4a4a7e;"></span> dim 21-40</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#1e2430;border:1px solid #58a6ff;"></span> normal 41-70</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#3a3518;border:1px solid #e3b341;"></span> bright 71-90</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#4a4020;border:1px solid #fff;"></span> blinding 91-100</div>
                <div class="legend-row" style="margin-top:4px;"><span class="legend-swatch" style="background:#3d2a0a;border:1px solid #f0883e;"></span><span style="font-size:9px;"> lit item</span></div>`;
        } else if (mode === 'heat') {
            title = '🌡️ Heat Overlay';
            rows = `
                <div class="legend-row"><span class="legend-swatch" style="background:#0a0a2e;border:1px solid #6e9eff;"></span> ≤ -20°C freezing</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#101840;border:1px solid #7eb8ff;"></span> -5°C cold</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#1a2840;border:1px solid #58a6ff;"></span> 15°C cool</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#2d333b;border:1px solid #58a6ff;"></span> 25°C comfortable</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#3a2a18;border:1px solid #e3b341;"></span> 35°C warm</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#4a2818;border:1px solid #f0883e;"></span> 45°C hot</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#4a1010;border:1px solid #f85149;"></span> ≥ 50°C blazing</div>
                <div class="legend-row" style="margin-top:4px;"><span class="legend-swatch" style="background:#4a2818;border:1px solid #f0883e;"></span><span style="font-size:9px;"> heat source</span></div>`;
        } else if (mode === 'sound') {
            title = '🔊 Sound Overlay';
            rows = `
                <div class="legend-row"><span class="legend-swatch" style="background:#0a0a0a;border:1px solid #333;"></span> silent</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#121220;border:1px solid #4a4a7e;"></span> quiet</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#2d333b;border:1px solid #58a6ff;"></span> moderate</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#3a2a18;border:1px solid #e3b341;"></span> loud</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#4a1010;border:1px solid #f85149;"></span> deafening</div>`;
        } else if (mode === 'trigger') {
            title = '⚡ Trigger Overlay';
            rows = `
                <div class="legend-row"><span class="legend-swatch" style="background:#2d333b;border:2px solid #bc8cff;"></span> trigger node</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#1a1a1a;border:1px solid #333;"></span> non-trigger node</div>
                <div class="legend-row"><span style="color:#bc8cff;font-size:14px;">━─▶</span> trigger edge</div>
                <div class="legend-row"><span style="color:#30363d;font-size:14px;">──▶</span> normal edge</div>`;
        } else if (mode === 'cardinal') {
            title = '🧭 Way directions';
            rows = `
                <div style="font-size:9px;color:var(--text-muted);">Ways labeled with their direction</div>
                <div style="font-size:9px;color:var(--text-muted);">N S E W NE NW SE SW U D</div>
                <div style="font-size:9px;color:var(--text-muted);margin-top:4px;">A label overlay — it does not rearrange anything</div>`;
        }
        if (!title) return;
        window.Lit.render(networkManagerHtmlTag`${window.Lit.unsafeHTML(GraphNetwork.legendChrome(title, rows))}`, graphManager._legendEl);
        // In place only: the panel keeps whatever visibility the user chose.
        if ((window as unknown as RelLayoutWin).GraphToolbar) GraphToolbar.syncToggles();
    },

    /**
     * Snapshot every rendered node/edge's structural style.
     *
     * Taken once per data load, after label decorations + LOD have settled but
     * before the active overlay recolours anything, so `resetOverlayStyles()`
     * can undo an overlay without a full `loadGraphData()` rebuild (which would
     * refit the camera and re-run layout) — the reason switching overlays used
     * to stack colours (task-642).
     */
    _captureBaseStyles() {
        const data = graphManager.network && graphManager.network.body
            && graphManager.network.body.data;
        if (!data) return;
        const nodeStyles: Record<string, any> = {};
        if (data.nodes) {
            data.nodes.forEach((node: any) => {
                nodeStyles[node.id] = { color: node.color, label: node.label, opacity: 1 };
            });
        }
        const edgeStyles: Record<string, any> = {};
        if (data.edges) {
            data.edges.forEach((edge: any) => {
                edgeStyles[edge.id] = {
                    color: edge.color, dashes: edge.dashes, width: edge.width,
                    label: edge.label, opacity: 1,
                };
            });
        }
        graphManager._baseNodeStyles = nodeStyles;
        graphManager._baseEdgeStyles = edgeStyles;
    },

    /** Restore the styles snapshotted by `_captureBaseStyles`. */
    resetOverlayStyles() {
        const data = graphManager.network && graphManager.network.body
            && graphManager.network.body.data;
        if (!data) return;
        const baseNodes = graphManager._baseNodeStyles;
        if (baseNodes && data.nodes) {
            const updates: any[] = [];
            data.nodes.forEach((node: any) => {
                const s = baseNodes[node.id];
                if (s) updates.push({ id: node.id, color: s.color, label: s.label, opacity: 1 });
            });
            if (updates.length) data.nodes.update(updates);
        }
        const baseEdges = graphManager._baseEdgeStyles;
        if (baseEdges && data.edges) {
            const updates: any[] = [];
            data.edges.forEach((edge: any) => {
                const s = baseEdges[edge.id];
                if (s) updates.push({
                    id: edge.id, color: s.color, dashes: s.dashes,
                    width: s.width, label: s.label, opacity: 1,
                });
            });
            if (updates.length) data.edges.update(updates);
        }
        // A label overlay (cardinal) rewrites names, so re-apply the LOD
        // decision or a reset map is left showing the previous overlay's labels.
        GraphNetwork.applyNodeLabelVisibility(true);
    },

    /**
     * Apply a named overlay to the graph.
     * @param {string} mode - 'light' | 'heat' | 'sound' | 'trigger' | 'cardinal' | 'structural'
     */
    applyOverlay(mode: string): void {
        if (!graphManager.network) { console.warn('Graph not initialized'); return; }
        GraphNetwork.applyModePhysics(false);
        graphManager._overlayMode = mode;

        if (mode === 'structural') {
            GraphNetwork._clearOverlay();
            return;
        }

        // Each overlay starts from the structural styles, never from the last
        // overlay's recolour (task-642).
        GraphNetwork.resetOverlayStyles();

        const t0 = performance.now();
        try {
            switch (mode) {
                case 'light': GraphNetwork._applyLightOverlay(); break;
                case 'heat': GraphNetwork._applyHeatOverlay(); break;
                case 'sound': GraphNetwork._applySoundOverlay(); break;
                case 'trigger': GraphNetwork._applyTriggerOverlay(); break;
                case 'cardinal': GraphNetwork._applyCardinalOverlay(); break;
            }
            const dt = Math.round(performance.now() - t0);
            const overlayNames: Record<string, string> = { light:'Light', heat:'Heat', sound:'Sound', trigger:'Trigger', cardinal:'Cardinal' };
            events.log(`📊 ${overlayNames[mode] || mode} overlay applied (${dt}ms)`, 'system-msg');
        } catch (err) {
            console.error('Overlay error:', err);
            events.log(`⚠️ Overlay "${mode}" failed: ${(err as Error).message}`, 'error-msg');
            GraphNetwork._clearOverlay();
        }
    }
};
