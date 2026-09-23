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

    // Children are packed into a tight block beside their parent rather than
    // spread on a wide halo: a room's contents should read as one cluster, not
    // overlap the neighbouring room. Items go below (clear of the parent's own
    // label box), characters right, triggers tucked to the left, and nested
    // contents pack tighter still. Spacing is sized for a short label.
    CLUSTER: {
        item: { dx: 52, dy: 26, cols: 3, ox: 0, oy: 58 },
        character: { dx: 40, dy: 34, cols: 1, ox: 74, oy: -20 },
        logic_trigger: { dx: 26, dy: 20, cols: 2, ox: -78, oy: -20 },
        default: { dx: 44, dy: 26, cols: 3, ox: 40, oy: 46 },
    },
    // Nested contents (an item inside a container) scale the block down.
    NESTED_SCALE: 0.72,
    // Children stay dynamic: they hold a *relative* offset from their parent and
    // that offset is re-applied as the parent moves, so a dragged room carries
    // its contents while global central gravity can never stretch a child away
    // (or drag it to the middle). Corrected every frame the simulation draws,
    // with a timer as the floor for a settled network that stops redrawing.
    FOLLOW_MS: 30,
    FOLLOW_EPSILON: 0.5,

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

    /** Parent of every node, cached by graph identity (the leash runs per frame). */
    _parents(nodes, edges) {
        if (this._parentCache && this._parentCache.nodes === nodes && this._parentCache.edges === edges) {
            return this._parentCache.map;
        }
        const map = {};
        for (const id of Object.keys(nodes)) map[id] = this.parentOf(id, edges, nodes);
        this._parentCache = { nodes, edges, map };
        return map;
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
        const parents = this._parents(nodes, edges);

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
            const node = nodes[id] || {};
            const siblings = (children[parent] || [id]).filter((child) => {
                const c = nodes[child];
                return c && this._slotFor(c) === this._slotFor(node);
            });
            const index = Math.max(0, siblings.indexOf(id));
            const count = Math.max(1, siblings.length);
            out[id] = this.clusterPosition(parentPos, index, count, node, Math.max(1, depthOf(id)));
        }
        return out;
    },

    /** Which block a node packs into (its own row: items, characters, triggers). */
    _slotFor(node) {
        if (!node) return 'default';
        return this.CLUSTER[node.type] ? node.type : 'default';
    },

    /**
     * Where the *n*-th of *count* same-kind children of a parent sits: a tight
     * grid block offset to one side of the parent, wrapping into rows.
     */
    clusterPosition(parentPos, index, count, node, depth) {
        const spec = this.CLUSTER[this._slotFor(node)];
        const scale = depth >= 2 ? this.NESTED_SCALE : 1;
        const dx = spec.dx * scale;
        const dy = spec.dy * scale;
        const cols = Math.max(1, Math.min(spec.cols, count));
        const rows = Math.ceil(count / cols);
        const col = index % cols;
        const row = Math.floor(index / cols);
        const blockWidth = (cols - 1) * dx;
        const blockHeight = (rows - 1) * dy;
        return {
            x: parentPos.x + spec.ox * scale - blockWidth / 2 + col * dx,
            y: parentPos.y + spec.oy * scale - blockHeight / 2 + row * dy,
        };
    },

    /**
     * Seed the derived layout: put every child in its parent's block and leave
     * it to the physics. Children are **not** pinned — they settle, jostle and
     * stay draggable — the leash in `enforce()` is what stops them leaving.
     *
     * @returns {number} how many nodes were placed
     */
    apply() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const network = g.network;
        if (!network || !network.body?.data?.nodes) return 0;
        const nodes = this._nodes();
        if (!Object.keys(nodes).length) return 0;

        const current = this._positions(network);
        if (!Object.keys(current).length) return 0;
        const derived = this.layoutPositions(nodes, this._edges(), current);
        const parents = this._parents(nodes, this._edges());

        // Keep each child's offset from its parent. An existing offset is kept,
        // so a nudge the player made is not thrown away and a reload restores the
        // arrangement rather than re-clustering from scratch.
        if (!this._offsets) this._offsets = {};
        const updates = [];
        for (const [id, pos] of Object.entries(derived)) {
            const node = nodes[id];
            if (!node || node.type === 'area' || node.type === 'way') continue;
            if (!Number.isFinite(pos.x) || !Number.isFinite(pos.y)) continue;
            const parent = parents[id];
            const parentPos = parent ? derived[parent] : null;
            if (!this._offsets[id] && parentPos) {
                this._offsets[id] = { dx: pos.x - parentPos.x, dy: pos.y - parentPos.y };
            }
            const offset = this._offsets[id];
            const target = offset && parentPos
                ? { x: parentPos.x + offset.dx, y: parentPos.y + offset.dy }
                : pos;
            // Dynamic: no `fixed`, physics stays on — the follow pass is what
            // keeps them with their parent.
            updates.push({ id, x: target.x, y: target.y, fixed: false, physics: true });
        }
        if (updates.length) {
            try { network.body.data.nodes.update(updates); } catch (err) { /* ignore */ }
        }
        return updates.length;
    },

    /** Live positions, hidden nodes included (`getPositions()` drops them). */
    _positions(network) {
        const out = {};
        try {
            const body = network.body?.nodes || {};
            for (const [id, n] of Object.entries(body)) {
                if (n && Number.isFinite(n.x) && Number.isFinite(n.y)) out[id] = { x: n.x, y: n.y };
            }
        } catch (err) { /* fall through */ }
        if (!Object.keys(out).length) {
            try { return network.getPositions() || {}; } catch (err) { return {}; }
        }
        return out;
    },

    /**
     * Re-apply every child's offset against its parent's live position. This is
     * what makes a room's contents follow it (physics moves the room, they track
     * it) without ever letting a child drift off on its own. Runs on a timer
     * because a settled vis network stops redrawing, so frame events are not
     * enough.
     *
     * @returns {number} how many children were re-placed
     */
    follow() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const network = g.network;
        if (!network || !network.body?.nodes || !this._offsets) return 0;
        const nodes = this._nodes();
        const parents = this._parents(nodes, this._edges());
        const positions = this._positions(network);
        const dragging = this._dragging || new Set();
        let moved = 0;

        // Shallowest first, updating the local map as we go, so a nested child
        // (oil inside a lamp inside a room) resolves against the place its parent
        // just moved to rather than the stale position of this pass.
        const depthOf = (id) => {
            let depth = 0, current = parents[id];
            const seen = new Set();
            while (current && !seen.has(current)) {
                seen.add(current);
                depth++;
                current = parents[current];
            }
            return depth;
        };
        const ordered = Object.keys(this._offsets)
            .filter((id) => nodes[id])
            .sort((a, b) => depthOf(a) - depthOf(b) || (a < b ? -1 : 1));

        for (const id of ordered) {
            if (dragging.has(id)) continue;
            const offset = this._offsets[id];
            if (!offset) continue;
            const parent = parents[id];
            const parentPos = parent ? positions[parent] : null;
            if (!parentPos) continue;
            const x = parentPos.x + offset.dx;
            const y = parentPos.y + offset.dy;
            const now = positions[id];
            if (now && Math.abs(now.x - x) <= this.FOLLOW_EPSILON && Math.abs(now.y - y) <= this.FOLLOW_EPSILON) {
                continue;
            }
            try {
                network.moveNode(id, x, y);
                positions[id] = { x, y };
                moved++;
            } catch (err) { /* ignore */ }
        }
        this.lastFollowed = moved;
        return moved;
    },

    /**
     * A child that was dragged keeps its new place: its offset is recomputed from
     * where it was dropped, so the player can arrange a room's contents by hand
     * and they still follow the room afterwards.
     */
    rememberDrop(ids) {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const network = g.network;
        if (!network || !this._offsets) return;
        const nodes = this._nodes();
        const parents = this._parents(nodes, this._edges());
        const positions = this._positions(network);
        for (const id of ids || []) {
            const node = nodes[id];
            if (!node || node.type === 'area' || node.type === 'way') continue;
            const parent = parents[id];
            const parentPos = parent ? positions[parent] : null;
            const pos = positions[id];
            if (!parentPos || !pos) continue;
            this._offsets[id] = { dx: pos.x - parentPos.x, dy: pos.y - parentPos.y };
        }
    },

    /**
     * Follow the room: dragEnd re-seeds the blocks (and remembers any child the
     * player moved); the timer keeps children on their parent's pattern while
     * physics runs so nothing is stretched across the map.
     */
    attach(network) {
        if (!network || network._relativeLayoutAttached) return;
        network._relativeLayoutAttached = true;
        this._dragging = new Set();
        network.on('stabilizationIterationsDone', () => this.apply());
        network.on('dragStart', (params) => {
            for (const id of (params && params.nodes) || []) this._dragging.add(id);
        });
        network.on('dragEnd', (params) => {
            const dragged = (params && params.nodes) || [];
            for (const id of dragged) this._dragging.delete(id);
            if (dragged.length) this.rememberDrop(dragged);
        });
        // Every drawn frame while the simulation is active, so the offset wins
        // against central gravity instead of being tugged off between timer ticks.
        network.on('afterDrawing', () => this.follow());
        if (typeof setInterval === 'function' && !this._followTimer) {
            this._followTimer = setInterval(() => this.follow(), this.FOLLOW_MS);
        }
    },
};
