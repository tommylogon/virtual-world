/**
 * @module graph/separation — keep nearby nodes from overlapping
 * @contributes window.GraphSeparation.{enabled, spec, radiusOf, resolve}
 * @powers item/character nodes pushing apart unless an edge already joins them
 * @relates used by graph/relative-layout on load and while contents follow their parent
 * @docs docs/virtualWorld/World Building/Graph System.md
 *
 * The global solver is deliberately NOT used for contents (task-485): vis's
 * `centralGravity` is a graph-wide field, so a child left in the solver is
 * dragged toward the middle of the whole graph however stiff its edge is.
 *
 * This module is the bounded alternative: a short-range relaxation. Two nodes
 * closer than `min` push apart; a pair further than `max` is ignored entirely;
 * and a pair joined by ANY edge is exempt, because a container and its contents
 * (or an item and its carrier) are meant to sit together. A uniform grid keys
 * nodes by `max`-sized cells, so only nearby pairs are ever compared and the
 * whole pass is ~linear in the node count.
 *
 * It never moves an area or a way (those are the world's coordinates and are
 * owned by physics / the map layout) nor a node the user froze.
 */
window.GraphSeparation = {
    // Floor for the settings; a pair is pushed apart to `max(min, r1 + r2)`,
    // where the radii approximate the node plus its label so long names get
    // room. `max` is also the grid cell size, so it bounds the search. `pull`
    // is the per-iteration restoring force back toward a node's own layout
    // target (its ring spot), applied only to nodes repulsion actually
    // displaced, so a spread-out node is reeled back rather than every room's
    // ring shrinking.
    DEFAULTS: { min: 55, max: 220, strength: 0.6, iterations: 6, pull: 0.12 },

    /** The `config` singleton, or null in a bare test sandbox. */
    _config() {
        try {
            return (typeof config !== 'undefined' && config) || null;
        } catch (err) {
            return null;
        }
    },

    /**
     * Off unless the setting says on. The default is chosen in `config.js`
     * (`graph_repel_enabled`), so a sandbox with no config — the unit tests —
     * leaves the deterministic orbit layout exactly as task-485 defined it.
     */
    enabled() {
        const cfg = this._config();
        return !!(cfg && cfg.graphRepelEnabled === true);
    },

    _positive(value, fallback) {
        const n = Number(value);
        return Number.isFinite(n) && n > 0 ? n : fallback;
    },

    /** The resolved knobs, with `max` forced to clear the repel distance. */
    spec() {
        const cfg = this._config() || {};
        const min = this._positive(cfg.graphRepelMin, this.DEFAULTS.min);
        let max = this._positive(cfg.graphRepelMax, this.DEFAULTS.max);
        if (max < min * 2) max = min * 2;
        let strength = Number(cfg.graphRepelStrength);
        if (!Number.isFinite(strength) || strength <= 0) strength = this.DEFAULTS.strength;
        strength = Math.max(0.05, Math.min(strength, 1));
        let pull = Number(cfg.graphRepelPull);
        if (!Number.isFinite(pull) || pull < 0) pull = this.DEFAULTS.pull;
        pull = Math.min(pull, 0.6);
        return { min, max, strength, iterations: this.DEFAULTS.iterations, pull };
    },

    /**
     * How much space a node wants, in px. The type base is the drawn shape; the
     * label term grows with the name so two long labels are pushed further apart
     * than two short ones. Capped so a single verbose name cannot fling a
     * neighbourhood around.
     */
    radiusOf(node) {
        const type = (node && node.type) || 'item';
        const base = { area: 46, character: 30, item: 24, way: 20 }[type] || 22;
        const name = String((node && node.name) || (node && node.label) || '');
        return base + Math.min(46, name.length * 1.7);
    },

    /** Areas and ways are the world's anchors; a frozen node keeps its place. */
    _movable(node) {
        if (!node) return false;
        if (node.type === 'area' || node.type === 'way') return false;
        const props = node.properties || {};
        return props.central_gravity_enabled !== false && props.layout_static !== true;
    },

    _pairKey(a, b) {
        return a < b ? `${a}\u0000${b}` : `${b}\u0000${a}`;
    },

    /** Every edge's endpoints, so a connected pair is never pushed apart. */
    _connectedPairs(edges) {
        const set = new Set();
        for (const edge of edges || []) {
            if (!edge || !edge.source || !edge.target) continue;
            set.add(this._pairKey(edge.source, edge.target));
        }
        return set;
    },

    /** Bucket node ids into `cell`-sized grid cells for neighbour lookup. */
    _grid(positions, ids, cell) {
        const grid = new Map();
        for (const id of ids) {
            const p = positions[id];
            const key = `${Math.floor(p.x / cell)},${Math.floor(p.y / cell)}`;
            let bucket = grid.get(key);
            if (!bucket) { bucket = []; grid.set(key, bucket); }
            bucket.push(id);
        }
        return grid;
    },

    /**
     * Relax overlapping nodes apart. Pure: returns a new `{id: {x, y}}` map and
     * never mutates the input. Deterministic — ids are walked in sorted order
     * and coincident nodes split along a fixed axis — so the same graph always
     * lays out the same way.
     *
     * @param {Object} nodes - nodes by id (needs `type`/`name`/`properties`)
     * @param {Array} edges - every edge (any type exempts its pair)
     * @param {Object} positions - current `{id: {x, y}}` to relax
     * @param {Object} [spec] - override for `spec()`; `spec.targets` (id ->
     *   `{x, y}`) enables the restoring pull back toward each node's own place
     * @returns {Object} adjusted positions for every node it was given
     */
    resolve(nodes, edges, positions, spec) {
        spec = spec || this.spec();
        const source = positions || {};
        const targets = spec.targets || null;
        const pull = (targets && Number(spec.pull) > 0) ? Number(spec.pull) : 0;
        const ids = Object.keys(source)
            .filter((id) => nodes[id] && source[id]
                && Number.isFinite(source[id].x) && Number.isFinite(source[id].y))
            .sort();
        const out = {};
        for (const id of ids) out[id] = { x: source[id].x, y: source[id].y };
        if (ids.length < 2) return out;

        const connected = this._connectedPairs(edges);
        const movable = {};
        const radius = {};
        const start = {};
        for (const id of ids) {
            movable[id] = this._movable(nodes[id]);
            radius[id] = this.radiusOf(nodes[id]);
            start[id] = { x: out[id].x, y: out[id].y };
        }

        const cell = Math.max(1, spec.max);
        for (let iter = 0; iter < spec.iterations; iter++) {
            const grid = this._grid(out, ids, cell);
            const disp = {};
            for (const id of ids) disp[id] = { x: 0, y: 0 };
            const pushed = new Set();
            let any = false;

            for (const id of ids) {
                const cx = Math.floor(out[id].x / cell);
                const cy = Math.floor(out[id].y / cell);
                for (let gx = cx - 1; gx <= cx + 1; gx++) {
                    for (let gy = cy - 1; gy <= cy + 1; gy++) {
                        const bucket = grid.get(`${gx},${gy}`);
                        if (!bucket) continue;
                        for (const other of bucket) {
                            // `other > id` visits each pair exactly once.
                            if (other <= id) continue;
                            if (connected.has(this._pairKey(id, other))) continue;
                            const dx = out[other].x - out[id].x;
                            const dy = out[other].y - out[id].y;
                            const dist2 = dx * dx + dy * dy;
                            if (dist2 > spec.max * spec.max) continue;
                            const dist = Math.sqrt(dist2);
                            const threshold = Math.max(spec.min, radius[id] + radius[other]);
                            if (dist >= threshold) continue;
                            const wa = movable[id] ? 1 : 0;
                            const wb = movable[other] ? 1 : 0;
                            const wsum = wa + wb;
                            if (!wsum) continue;
                            let nx, ny;
                            if (dist < 1e-6) { nx = 1; ny = 0; }
                            else { nx = dx / dist; ny = dy / dist; }
                            const push = (threshold - dist) * spec.strength;
                            if (wa) {
                                disp[id].x -= nx * push * wa / wsum;
                                disp[id].y -= ny * push * wa / wsum;
                            }
                            if (wb) {
                                disp[other].x += nx * push * wb / wsum;
                                disp[other].y += ny * push * wb / wsum;
                            }
                            pushed.add(id);
                            pushed.add(other);
                            any = true;
                        }
                    }
                }
            }
            // Restore a displaced node to its own place: what repulsion spread
            // out, the pull reels back in. The target is where the layout meant
            // the node to sit (its spot on the ring), NOT the parent's centre —
            // pulling toward the centre would suck a crowded node onto its
            // parent. Only touched nodes feel it, so an untroubled node never
            // moves.
            if (pull && pushed.size) {
                for (const id of pushed) {
                    if (!movable[id]) continue;
                    const target = targets[id];
                    if (!target) continue;
                    disp[id].x += (target.x - out[id].x) * pull;
                    disp[id].y += (target.y - out[id].y) * pull;
                }
            }
            if (!any) break;
            for (const id of ids) {
                if (!movable[id]) continue;
                const mag = Math.hypot(disp[id].x, disp[id].y);
                if (mag < 0.01) continue;
                // A pile resolves over several iterations instead of jumping.
                const k = mag > spec.min ? spec.min / mag : 1;
                out[id].x += disp[id].x * k;
                out[id].y += disp[id].y * k;
            }
        }

        // A hard cap on how far one node may be shoved, so a dense pile cannot
        // run away and blow up the whole layout.
        for (const id of ids) {
            const ddx = out[id].x - start[id].x;
            const ddy = out[id].y - start[id].y;
            const mag = Math.hypot(ddx, ddy);
            if (mag > spec.max) {
                const k = spec.max / mag;
                out[id].x = start[id].x + ddx * k;
                out[id].y = start[id].y + ddy * k;
            }
        }
        return out;
    },
};
