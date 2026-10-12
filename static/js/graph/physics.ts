/**
 * @module graph/physics — the one owner of the graph physics policy
 * @contributes window.GraphPhysics: policy state, shouldRun/reason, nodePinned, apply, pause/resume, setUserEnabled, setLocked
 * @powers Graph settings — a single decision for whether the solver runs, its transient windows, and the user toggle
 * @relates reads graphManager._physicsEnabled/_cardinalLayout and config.graphLayoutMode; writes graphManager.network physics options; fed by GraphBackground's lock
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 *
 * Why this module exists (task-765)
 * ---------------------------------
 * "Should the solver run?" used to be decided in five places from six inputs,
 * written into one shared boolean by nine call sites, and pushed to vis through
 * fourteen calls plus two bypasses. That is why a toolbar toggle could be undone
 * by a reload, why bug-534's re-enable had no owner, and why the Map layout
 * shipped its own hardcoded physics block.
 *
 * This module is that owner. It holds the policy inputs, exposes ONE pure
 * decision (`shouldRun`), and is the ONE place that pushes `physics` onto the
 * network (`apply`). Callers stop passing booleans:
 *   - a persistent input (the user's on/off, the lock) is set on the state;
 *   - a transient (a load/placement/kick window) calls `pause()` / `resume()`.
 * The node-count valve and the layout/overlay gates are read here too, so the
 * toolbar, the load path and the inspector cannot disagree about physics.
 */

/** The policy inputs. Each has exactly one writer elsewhere; this module reads them. */
interface GraphPhysicsState {
    userEnabled: boolean;
    layout: string;      // 'graph' | 'map' | 'levels'
    overlay: string;     // 'none' | 'light' | 'heat' | 'sound' | 'trigger' | 'cardinal'
    locked: boolean;     // the 🔒 node-layout lock (GraphBackground owns it)
    overNodeLimit: boolean;
    paused: boolean;     // a transient load/placement/kick window is open
}

/** Shape the toolbar's honest-affordance rules consume. */
interface GraphPhysicsAvailability {
    enabled: boolean;
    reason: string;
}

window.GraphPhysics = {
    /** Transient suppression while the load/placement window is open. */
    _paused: false,
    /** The node-layout lock — one input, one writer (GraphBackground feeds it). */
    _locked: false,

    /**
     * Read the live policy inputs from their owners. Nothing here writes them;
     * the sources are graphManager (user pref + active layout + view mode),
     * GraphNetwork (the node-count valve) and this module's own lock/pause flags.
     *
     * @returns {GraphPhysicsState}
     */
    readState(): GraphPhysicsState {
        const gm: any = (typeof graphManager !== 'undefined' && graphManager) || null;
        const cfg: any = (typeof config !== 'undefined' && config) || {};
        let overNodeLimit = false;
        try {
            overNodeLimit = !!(GraphNetwork && (GraphNetwork as any).nodesOverPhysicsLimit
                && (GraphNetwork as any).nodesOverPhysicsLimit());
        } catch (e) { /* no network yet — not over any limit */ }
        const layout = gm && typeof gm.activeLayout === 'function'
            ? gm.activeLayout()
            : (cfg.graphLayoutMode === 'levels' ? 'levels' : (gm && gm._cardinalLayout ? 'map' : 'graph'));
        // `_viewMode` is the canonical overlay selector (set by setViewMode);
        // `_overlayMode` is the lower-level field applyOverlay writes. Either
        // saying "an overlay is on" is enough.
        let overlay = 'none';
        if (gm) {
            if (gm._viewMode && gm._viewMode !== 'graph') overlay = gm._viewMode;
            else if (gm._overlayMode && gm._overlayMode !== 'structural') overlay = gm._overlayMode;
        }
        return {
            userEnabled: !!(gm && gm._physicsEnabled),
            layout,
            overlay,
            locked: GraphPhysics._locked === true,
            overNodeLimit,
            paused: GraphPhysics._paused === true
        };
    },

    /**
     * The one decision. Pure over a state object (unit-tested in
     * tools/unit/test_graph_physics.js). Any gate that says "positions are not
     * the solver's to move" wins; otherwise the user's own choice decides.
     *
     * @param {Partial<GraphPhysicsState>} [state]
     * @returns {boolean}
     */
    shouldRun(state?: Partial<GraphPhysicsState>): boolean {
        const s: Partial<GraphPhysicsState> = state || {};
        if (s.userEnabled === false) return false;
        if (s.layout === 'levels') return false;
        if (s.overlay && s.overlay !== 'none') return false;
        if (s.locked) return false;
        if (s.overNodeLimit) return false;
        if (s.paused) return false;
        return true;
    },

    /**
     * Why the solver is not running, for a tooltip. '' when it is running.
     *
     * @param {Partial<GraphPhysicsState>} [state]
     * @returns {string}
     */
    reason(state?: Partial<GraphPhysicsState>): string {
        const s: Partial<GraphPhysicsState> = state || {};
        if (s.userEnabled === false) return 'Physics is switched off.';
        if (s.layout === 'levels') return 'Hierarchical owns node positions — physics is off until you pick Graph or Map.';
        if (s.overlay && s.overlay !== 'none') return 'An overlay recolors the canvas and holds positions while it is on.';
        if (s.locked) return 'The node layout is locked — unlock it to let the solver run.';
        if (s.overNodeLimit) return 'This world is above the physics node limit; positions come from the painted grid or a saved layout.';
        return '';
    },

    /**
     * Availability + reason, in the shape the toolbar's rule consumes, so the
     * bar and the solver read the same policy instead of re-deciding it.
     *
     * @param {Partial<GraphPhysicsState>} [state]
     * @returns {GraphPhysicsAvailability}
     */
    availability(state?: Partial<GraphPhysicsState>): GraphPhysicsAvailability {
        const s: Partial<GraphPhysicsState> = state || {};
        const blocked = s.layout === 'levels'
            || (!!s.overlay && s.overlay !== 'none')
            || !!s.locked
            || !!s.overNodeLimit;
        return { enabled: !blocked, reason: GraphPhysics.reason(s) };
    },

    /**
     * The per-node rule: is this node's position fixed by the author or the
     * paint, so the solver must not move it? (moved from GraphNetwork.isNodePinned,
     * task-766 — the node level of the same "who owns positions" decision.)
     *
     * @param {Object} nodeData
     * @returns {boolean} true = hold this node in place
     */
    nodePinned(nodeData: any): boolean {
        const props = (nodeData && nodeData.properties) || {};
        // An explicit "on" is an opt-in override and wins even over a painted
        // coordinate, so the author keeps control (task-766).
        if (props.central_gravity_enabled === true) return false;
        if (props.central_gravity_enabled === false || props.layout_static === true) return true;
        // A painted cell coordinate pins the node in every layout (task-766).
        const cell = props.cell;
        if (cell && Number.isFinite(Number(cell.x)) && Number.isFinite(Number(cell.y))) {
            const le = (window as any).GraphLayoutEngine;
            if (le && typeof le.gridPosition === 'function' && le.gridPosition(cell)) return true;
        }
        const rl = (window as any).GraphRelativeLayout;
        if (rl && typeof rl.isStatic === 'function') {
            try { return rl.isStatic(nodeData); } catch (e) { /* fall through */ }
        }
        return false;
    },

    /**
     * Write each node's LIVE physics-body position into the DataSet, so a later
     * solver re-seed (a pause, a stabilization) rebuilds the body from where the
     * nodes actually are rather than from the coordinate the DataSet was loaded
     * with. One batched update — never one call per node, which redraws the whole
     * graph per node.
     */
    _snapshotBodyToDataset(): void {
        const gm: any = (typeof graphManager !== 'undefined' && graphManager) || null;
        const nodesDS = gm && gm.network && gm.network.body && gm.network.body.data
            && gm.network.body.data.nodes;
        const body = gm && gm.network && gm.network.body && gm.network.body.nodes;
        if (!nodesDS || !body) return;
        const updates: Array<{ id: string; x: number; y: number }> = [];
        for (const id of Object.keys(body)) {
            const b = body[id];
            if (b && Number.isFinite(b.x) && Number.isFinite(b.y)) {
                updates.push({ id, x: b.x as number, y: b.y as number });
                (window as unknown as { GraphNetwork?: { _posTrace?(...a: any[]): void } }).GraphNetwork?._posTrace?.('physics._snapshotBodyToDataset', id, b.x, b.y);
            }
        }
        if (updates.length) {
            try { nodesDS.update(updates); } catch (e) { /* ignore */ }
        }
    },

    /**
     * The ONE writer. Compute the decision and push it onto the network. Every
     * former `applyModePhysics(enabled)` site now lands here.
     */
    apply(): void {
        const gm: any = (typeof graphManager !== 'undefined' && graphManager) || null;
        if (!gm || !gm.network || !gm.network.setOptions) return;
        const run = GraphPhysics.shouldRun(GraphPhysics.readState());
        if (!run) {
            // Freeze exactly where the nodes ARE — but ONLY for a real pause.
            // During a load, GraphPhysics.pause() holds the solver off
            // transiently while the placement passes are still running; writing
            // the DataSet then captures HALF-PLACED body positions, and the grid
            // placement reads them back, so the map lands off its background art.
            // `_paused` is exactly that transient window (pause() sets it,
            // resume() clears it); a user pause never sets it.
            if (!GraphPhysics._paused) GraphPhysics._snapshotBodyToDataset();
            // Disable WITHOUT resending the solver block. Changing a solver
            // option in the same setOptions() call makes vis.js re-initialise
            // the force solver, which re-runs it from the seeded positions — so
            // "pause" appeared to teleport every node back to where it was
            // loaded instead of freezing it where it had settled. Halting is
            // just `enabled: false` plus an explicit stop.
            gm.network.setOptions({ physics: { enabled: false } });
            try { gm.network.stopSimulation(); } catch (e) { /* already stopped */ }
            return;
        }
        const cfg: any = (typeof config !== 'undefined' && config) || {};
        const solver = cfg.graphSolver || 'forceAtlas2Based';
        const centralGravity = (GraphNetwork as any).centralGravityFor
            ? (GraphNetwork as any).centralGravityFor()
            : 0;
        gm.network.setOptions({ physics: { enabled: true, [solver]: { centralGravity } } });
        try { gm.network.startSimulation(); } catch (e) { /* already running */ }
    },

    /** Transient: hold the solver off for the load/placement window. */
    pause(): void {
        GraphPhysics._paused = true;
        GraphPhysics.apply();
    },

    /** Transient: release the window; the policy decides the real state. */
    resume(): void {
        GraphPhysics._paused = false;
        GraphPhysics.apply();
    },

    /**
     * The user's own choice (the ⏸ Physics button). The ONLY writer of
     * `graphManager._physicsEnabled`, and it persists immediately, so a reload
     * that reads the config before the first load honours it (task-765).
     *
     * @param {boolean} enabled
     */
    setUserEnabled(enabled: boolean): void {
        const gm: any = (typeof graphManager !== 'undefined' && graphManager) || null;
        if (gm) gm._physicsEnabled = !!enabled;
        GraphPhysics.apply();
        if ((window as any).GraphToolbar) (window as any).GraphToolbar.syncAll();
        if (gm && typeof gm._saveGraphConfigKey === 'function') {
            gm._saveGraphConfigKey('graph.physics_enabled', !!enabled);
        }
    },

    /** Flip the user's choice. */
    toggleUserEnabled(): void {
        const gm: any = (typeof graphManager !== 'undefined' && graphManager) || null;
        GraphPhysics.setUserEnabled(!(gm && gm._physicsEnabled));
    },

    /**
     * Feed the node-layout lock (GraphBackground owns the state; this is input,
     * not a second copy of it).
     *
     * @param {boolean} locked
     */
    setLocked(locked: boolean): void {
        GraphPhysics._locked = !!locked;
        GraphPhysics.apply();
        // The lock decides whether the Physics button can do anything, so the
        // affordance must follow it exactly as it follows the user's own toggle
        // (setUserEnabled). Without this the lock lands during load — after the
        // toolbar's initial paint — and the button keeps offering a resume that
        // the solver will refuse (bug-542).
        if ((window as any).GraphToolbar) (window as any).GraphToolbar.syncAll();
    }
};
