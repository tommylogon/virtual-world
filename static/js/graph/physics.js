"use strict";
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
    readState() {
        const gm = (typeof graphManager !== 'undefined' && graphManager) || null;
        const cfg = (typeof config !== 'undefined' && config) || {};
        let overNodeLimit = false;
        try {
            overNodeLimit = !!(GraphNetwork && GraphNetwork.nodesOverPhysicsLimit
                && GraphNetwork.nodesOverPhysicsLimit());
        }
        catch (e) { /* no network yet — not over any limit */ }
        const layout = gm && typeof gm.activeLayout === 'function'
            ? gm.activeLayout()
            : (cfg.graphLayoutMode === 'levels' ? 'levels' : (gm && gm._cardinalLayout ? 'map' : 'graph'));
        // `_viewMode` is the canonical overlay selector (set by setViewMode);
        // `_overlayMode` is the lower-level field applyOverlay writes. Either
        // saying "an overlay is on" is enough.
        let overlay = 'none';
        if (gm) {
            if (gm._viewMode && gm._viewMode !== 'graph')
                overlay = gm._viewMode;
            else if (gm._overlayMode && gm._overlayMode !== 'structural')
                overlay = gm._overlayMode;
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
    shouldRun(state) {
        const s = state || {};
        if (s.userEnabled === false)
            return false;
        if (s.layout === 'levels')
            return false;
        if (s.overlay && s.overlay !== 'none')
            return false;
        if (s.locked)
            return false;
        if (s.overNodeLimit)
            return false;
        if (s.paused)
            return false;
        return true;
    },
    /**
     * Why the solver is not running, for a tooltip. '' when it is running.
     *
     * @param {Partial<GraphPhysicsState>} [state]
     * @returns {string}
     */
    reason(state) {
        const s = state || {};
        if (s.userEnabled === false)
            return 'Physics is switched off.';
        if (s.layout === 'levels')
            return 'Hierarchical owns node positions — physics is off until you pick Graph or Map.';
        if (s.overlay && s.overlay !== 'none')
            return 'An overlay recolors the canvas and holds positions while it is on.';
        if (s.locked)
            return 'The node layout is locked — unlock it to let the solver run.';
        if (s.overNodeLimit)
            return 'This world is above the physics node limit; positions come from the painted grid or a saved layout.';
        return '';
    },
    /**
     * Availability + reason, in the shape the toolbar's rule consumes, so the
     * bar and the solver read the same policy instead of re-deciding it.
     *
     * @param {Partial<GraphPhysicsState>} [state]
     * @returns {GraphPhysicsAvailability}
     */
    availability(state) {
        const s = state || {};
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
    nodePinned(nodeData) {
        const props = (nodeData && nodeData.properties) || {};
        // An explicit "on" is an opt-in override and wins even over a painted
        // coordinate, so the author keeps control (task-766).
        if (props.central_gravity_enabled === true)
            return false;
        if (props.central_gravity_enabled === false || props.layout_static === true)
            return true;
        // A painted cell coordinate pins the node in every layout (task-766).
        const cell = props.cell;
        if (cell && Number.isFinite(Number(cell.x)) && Number.isFinite(Number(cell.y))) {
            const le = window.GraphLayoutEngine;
            if (le && typeof le.gridPosition === 'function' && le.gridPosition(cell))
                return true;
        }
        const rl = window.GraphRelativeLayout;
        if (rl && typeof rl.isStatic === 'function') {
            try {
                return rl.isStatic(nodeData);
            }
            catch (e) { /* fall through */ }
        }
        return false;
    },
    /**
     * The ONE writer. Compute the decision and push it onto the network. Every
     * former `applyModePhysics(enabled)` site now lands here.
     */
    apply() {
        const gm = (typeof graphManager !== 'undefined' && graphManager) || null;
        if (!gm || !gm.network || !gm.network.setOptions)
            return;
        const run = GraphPhysics.shouldRun(GraphPhysics.readState());
        if (!run) {
            // Disable WITHOUT resending the solver block. Changing a solver
            // option in the same setOptions() call makes vis.js re-initialise
            // the force solver, which re-runs it from the seeded positions — so
            // "pause" appeared to teleport every node back to where it was
            // loaded instead of freezing it where it had settled. Halting is
            // just `enabled: false` plus an explicit stop.
            gm.network.setOptions({ physics: { enabled: false } });
            try {
                gm.network.stopSimulation();
            }
            catch (e) { /* already stopped */ }
            return;
        }
        const cfg = (typeof config !== 'undefined' && config) || {};
        const solver = cfg.graphSolver || 'forceAtlas2Based';
        const centralGravity = GraphNetwork.centralGravityFor
            ? GraphNetwork.centralGravityFor()
            : 0;
        gm.network.setOptions({ physics: { enabled: true, [solver]: { centralGravity } } });
        try {
            gm.network.startSimulation();
        }
        catch (e) { /* already running */ }
    },
    /** Transient: hold the solver off for the load/placement window. */
    pause() {
        GraphPhysics._paused = true;
        GraphPhysics.apply();
    },
    /** Transient: release the window; the policy decides the real state. */
    resume() {
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
    setUserEnabled(enabled) {
        const gm = (typeof graphManager !== 'undefined' && graphManager) || null;
        if (gm)
            gm._physicsEnabled = !!enabled;
        GraphPhysics.apply();
        if (window.GraphToolbar)
            window.GraphToolbar.syncAll();
        if (gm && typeof gm._saveGraphConfigKey === 'function') {
            gm._saveGraphConfigKey('graph.physics_enabled', !!enabled);
        }
    },
    /** Flip the user's choice. */
    toggleUserEnabled() {
        const gm = (typeof graphManager !== 'undefined' && graphManager) || null;
        GraphPhysics.setUserEnabled(!(gm && gm._physicsEnabled));
    },
    /**
     * Feed the node-layout lock (GraphBackground owns the state; this is input,
     * not a second copy of it).
     *
     * @param {boolean} locked
     */
    setLocked(locked) {
        GraphPhysics._locked = !!locked;
        GraphPhysics.apply();
    }
};
