/**
 * @module graph/relative-layout — derive where nodes sit from their relations
 * @contributes window.GraphRelativeLayout.{parentOf, layoutPositions, apply, attach}
 * @powers items, characters and triggers following the area/container/holder they belong to
 * @relates reads worldState.graph edges + graphManager._graphNodesObj; moves nodes on graphManager.network
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 *
 * Positions are a **function of the graph**, never a saved snapshot. An item
 * renders on a ring around whatever holds it (an area, a container, a carried
 * bag, a wearer); a logic_trigger sits on its host; a way sits between its two
 * rooms. Because the relation *is* the position:
 *
 *  - picking an item up and carrying it 300 rooms away moves its node with the
 *    carrier, with no per-node bookkeeping;
 *  - a reload re-derives the same layout, so there is nothing to lose;
 *  - the area nodes stay the only world coordinates (physics/settling/free
 *    dragging), and everything else is held relative to them.
 *
 * Children are placed and held (`fixed`, physics off) so global central gravity
 * can never drag them to the middle; areas keep physics so they still spread.
 */

window.GraphRelativeLayout = {
    // Relation -> which end is the child, in priority order. Holding beats
    // geography: being *carried* outranks being *in* the room you left the bag
    // in. `in` alone has no reliable direction in the data (it is stored both
    // `Backpack -> Ink` and `fireplace -> living_room`), so for `in` the end
    // nearer the area roots is the parent.
    PARENT_RULES: [
        { type: 'carrying', child: 'source' },  // item -> carrier
        { type: 'equipped', child: 'source' },  // item -> wearer
        { type: 'at', child: 'source' },        // item -> area it stands in
        { type: 'in', child: null },            // mixed: the shallower end is the parent
        { type: 'triggers', child: 'target' },  // host -> trigger
    ],
    RELATION_TYPES: new Set(['carrying', 'equipped', 'at', 'in', 'triggers']),

    // Ring radius per depth below the parent node.
    RADII: [0, 130, 88, 62],
    // Extra radius for crowded parents (triggers love a way or an item).
    CROWD_STEP: 46,
    CROWD_AT: 8,

    _edges() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const edges = g._graphEdgesArr;
        if (Array.isArray(edges) && edges.length) return edges;
        return (typeof worldState !== 'undefined' && worldState?.graph?.edges) || [];
    },

    _nodes() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        if (g._graphNodesObj && Object.keys(g._graphNodesObj).length) return g._graphNodesObj;
        return (typeof worldState !== 'undefined' && worldState?.graph?.nodes) || {};
    },

    /**
     * Hops from the nearest area, over the relation edges (direction ignored).
     * The roots are the areas: everything that hangs off one is placed, and a
     * relation island with no area in it (or a container cycle) simply has no
     * depth and is left to physics.
     */
    _depths(nodes, edges) {
        if (this._depthCache && this._depthCache.nodes === nodes && this._depthCache.edges === edges) {
            return this._depthCache.map;
        }
        const adjacency = new Map();
        const link = (a, b) => {
            if (!adjacency.has(a)) adjacency.set(a, []);
            adjacency.get(a).push(b);
        };
        for (const edge of edges || []) {
            if (!edge || !this.RELATION_TYPES.has(edge.type)) continue;
            if (!nodes[edge.source] || !nodes[edge.target]) continue;
            link(edge.source, edge.target);
            link(edge.target, edge.source);
        }
        const map = new Map();
        const queue = Object.keys(nodes).filter((id) => nodes[id] && nodes[id].type === 'area');
        for (const id of queue) map.set(id, 0);
        for (let head = 0; head < queue.length; head++) {
            const current = queue[head];
            for (const next of adjacency.get(current) || []) {
                if (map.has(next)) continue;
                map.set(next, map.get(current) + 1);
                queue.push(next);
            }
        }
        this._depthCache = { nodes, edges, map };
        return map;
    },

    /** Tie-break when both ends of a relation are equally deep. */
    _rank(node) {
        if (!node) return 0;
        if (node.type === 'area') return 3;
        if (node.type === 'character') return 2;
        return 1;
    },

    /**
     * The node some node hangs off, or null for an area (a root), a way (placed
     * between its rooms) and anything with no relation reaching an area.
     */
    parentOf(nodeId, edges, nodes) {
        edges = edges || this._edges();
        nodes = nodes || this._nodes();
        const self = nodes[nodeId];
        if (self && (self.type === 'area' || self.type === 'way')) return null;

        const depths = this._depths(nodes, edges);
        const mine = depths.get(nodeId);

        for (const rule of this.PARENT_RULES) {
            let best = null;
            let bestDepth = Infinity;
            for (const edge of edges) {
                if (!edge || edge.type !== rule.type) continue;
                let other = null;
                if (rule.child === 'source') {
                    if (edge.source !== nodeId) continue;
                    other = edge.target;
                } else if (rule.child === 'target') {
                    if (edge.target !== nodeId) continue;
                    other = edge.source;
                } else {
                    other = edge.source === nodeId ? edge.target
                        : (edge.target === nodeId ? edge.source : null);
                }
                if (!other || !nodes[other] || other === nodeId) continue;
                const depth = depths.get(other);
                if (rule.child === null) {
                    // `in` has no trustworthy direction, so the end nearer the
                    // area roots is the parent. Only something shallower can be
                    // a parent, which also keeps a two-node container cycle
                    // parentless instead of each holding the other.
                    if (depth === undefined || (mine !== undefined && depth >= mine)) continue;
                }
                const sortDepth = depth === undefined ? Infinity : depth;
                if (sortDepth < bestDepth || (sortDepth === bestDepth && this._rank(nodes[other]) > this._rank(nodes[best]))) {
                    best = other;
                    bestDepth = sortDepth;
                }
            }
            if (best) return best;
        }
        return null;
    },

    /** Ways are the meeting point of the rooms they connect: `{x, y}` or null. */
    wayMidpoint(nodeId, edges, positions, nodes) {
        edges = edges || this._edges();
        positions = positions || {};
        nodes = nodes || this._nodes();
        const rooms = [];
        for (const edge of edges) {
            if (!edge || edge.type !== 'connection') continue;
            const other = edge.source === nodeId ? edge.target : (edge.target === nodeId ? edge.source : null);
            if (!other || !nodes[other] || nodes[other].type !== 'area') continue;
            const pos = positions[other];
            if (pos) rooms.push(pos);
        }
        if (!rooms.length) return null;
        return {
            x: rooms.reduce((sum, p) => sum + p.x, 0) / rooms.length,
            y: rooms.reduce((sum, p) => sum + p.y, 0) / rooms.length,
        };
    },

    /**
     * Every non-area node's derived position, given the current area positions.
     * Pure and cycle-safe: same inputs -> same output, and sibling order is
     * sorted by id so a layout never jitters between loads. Areas come back at
     * their given position (they are the roots everything else hangs off).
     */
    layoutPositions(nodes, edges, positions) {
        nodes = nodes || this._nodes();
        edges = edges || this._edges();
        positions = positions || {};

        const ids = Object.keys(nodes).sort();
        const parents = {};
        for (const id of ids) {
            if (nodes[id] && nodes[id].type === 'area') continue;
            parents[id] = this.parentOf(id, edges, nodes);
        }

        // Depth from the root, walking up with a visited set so a container
        // cycle is an orphan (left to physics) rather than an infinite loop.
        // Ways count as roots here: they are placed at their rooms' midpoint.
        const depths = {};
        const depthOf = (id) => {
            if (depths[id] !== undefined) return depths[id];
            const seen = new Set();
            let hops = 0, current = id;
            while (current && nodes[current] && nodes[current].type !== 'area'
                    && nodes[current].type !== 'way') {
                if (seen.has(current)) { depths[id] = Infinity; return Infinity; }
                seen.add(current);
                current = parents[current];
                hops++;
            }
            if (!current || !nodes[current]) { depths[id] = Infinity; return Infinity; }
            depths[id] = hops;
            return hops;
        };

        const out = {};
        for (const id of ids) {
            if (nodes[id] && nodes[id].type === 'area') {
                const pos = positions[id];
                if (pos && Number.isFinite(pos.x) && Number.isFinite(pos.y)) out[id] = { x: pos.x, y: pos.y };
            }
        }

        // Children grouped under their parent, in a stable order.
        const children = {};
        for (const id of ids) {
            const parent = parents[id];
            if (!parent || !nodes[parent]) continue;
            (children[parent] = children[parent] || []).push(id);
        }

        // Ways are the meeting point of the rooms they connect, not a ring, and
        // they come first so a trigger hosted by a way has somewhere to sit.
        for (const id of ids) {
            if (!nodes[id] || nodes[id].type !== 'way') continue;
            const mid = this.wayMidpoint(id, edges, positions, nodes);
            if (mid) out[id] = mid;
        }

        // Top-down: a parent is always placed before the things hanging off it.
        const placeable = ids
            .filter((id) => nodes[id] && nodes[id].type !== 'area' && nodes[id].type !== 'way')
            .filter((id) => depthOf(id) !== Infinity)
            .sort((a, b) => depthOf(a) - depthOf(b) || (a < b ? -1 : 1));

        for (const id of placeable) {
            const parent = parents[id];
            const parentPos = parent ? out[parent] : null;
            if (!parentPos) continue;
            const siblings = children[parent] || [id];
            const index = Math.max(0, siblings.indexOf(id));
            const count = siblings.length;
            const depth = Math.max(1, depthOf(id));
            const base = this.RADII[Math.min(depth, this.RADII.length - 1)];
            const radius = base + Math.max(0, Math.ceil(count / this.CROWD_AT) - 1) * this.CROWD_STEP;
            const angle = (2 * Math.PI * index) / Math.max(1, count) - Math.PI / 2;
            out[id] = {
                x: parentPos.x + radius * Math.cos(angle),
                y: parentPos.y + radius * Math.sin(angle),
            };
        }
        return out;
    },

    /**
     * Apply the derived layout to the live network. Areas are left alone
     * (physics/settling/free dragging); everything else is moved onto its
     * parent's ring and held there.
     *
     * @returns {number} how many nodes were placed
     */
    apply() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const network = g.network;
        if (!network || !network.body?.data?.nodes) return 0;
        const nodes = this._nodes();
        if (!Object.keys(nodes).length) return 0;

        // Positions of the nodes that already exist, hidden ones included:
        // getPositions() drops filtered-out nodes, and a child must still be
        // placed when its parent is not currently visible.
        let current = {};
        try {
            const body = network.body?.nodes || {};
            for (const [id, n] of Object.entries(body)) {
                if (n && Number.isFinite(n.x) && Number.isFinite(n.y)) current[id] = { x: n.x, y: n.y };
            }
        } catch (err) { /* fall through to getPositions */ }
        if (!Object.keys(current).length) {
            try { current = network.getPositions() || {}; } catch (err) { return 0; }
        }
        const derived = this.layoutPositions(nodes, this._edges(), current);

        const updates = [];
        for (const [id, pos] of Object.entries(derived)) {
            const node = nodes[id];
            if (!node || node.type === 'area') continue;
            if (!Number.isFinite(pos.x) || !Number.isFinite(pos.y)) continue;
            updates.push({ id, x: pos.x, y: pos.y, fixed: { x: true, y: true }, physics: false });
        }
        if (updates.length) {
            try { network.body.data.nodes.update(updates); } catch (err) { /* ignore */ }
        }
        return updates.length;
    },

    /** Follow area movement: re-derive after settling and after any drag. */
    attach(network) {
        if (!network || network._relativeLayoutAttached) return;
        network._relativeLayoutAttached = true;
        network.on('stabilizationIterationsDone', () => this.apply());
        network.on('dragEnd', (params) => {
            if (params && params.nodes && params.nodes.length) this.apply();
        });
    },
};
