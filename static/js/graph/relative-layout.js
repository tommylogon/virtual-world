"use strict";
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
 *    dragging), and everything else starts out relative to them.
 *
 * The ring is a **seed, not a leash**. `apply()` runs it once per layout and
 * hands the node back to the solver, which is why contents can now be simulated:
 * with `centralGravity: 0` (see graph/network-manager.js) there is no global
 * field dragging a child to the middle of the graph, so an item and its room are
 * held together by their own edge spring and separated by ordinary repulsion.
 * Nothing re-places a child afterwards — the earlier 120ms follow pass snapped
 * them back onto a parent-relative offset and read as a visible stutter.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
/**
 * graph/layout-engine.js exposes more than globals.d.ts declares; read the two
 * members this module needs through a local widening so the shared declaration
 * stays untouched.
 */
function _layoutEngine() {
    return (typeof GraphLayoutEngine !== 'undefined' && GraphLayoutEngine)
        ? GraphLayoutEngine
        : null;
}
/** graph/separation.js is not declared in globals.d.ts. */
function _separation() {
    const holder = window;
    return holder.GraphSeparation || null;
}
const _GraphRelativeLayout = {
    // Relation -> which end is the child, in priority order. Holding beats
    // geography: being *carried* outranks being *in* the room you left the bag
    // in. `in` alone has no reliable direction in the data (it is stored both
    // `Backpack -> Ink` and `fireplace -> living_room`), so for `in` the end
    // nearer the area roots is the parent.
    PARENT_RULES: [
        { type: 'carrying', child: 'source' }, // item -> carrier
        { type: 'equipped', child: 'source' }, // item -> wearer
        { type: 'at', child: 'source' }, // item -> area it stands in
        { type: 'in', child: null }, // mixed: the shallower end is the parent
        { type: 'triggers', child: 'target' }, // host -> trigger
    ],
    RELATION_TYPES: new Set(['carrying', 'equipped', 'at', 'in', 'triggers']),
    // Contents ORBIT their parent: a ring around the room, radius grown to fit
    // however many things are in there (so labels do not collide), and smaller
    // rings for contents nested inside a container. Nothing is stretched away —
    // the ring is bounded.
    //
    // The "Item Edge Length" setting (its ends are labelled Hug Parent <->
    // Stretched) is the desired distance from the parent, so it scales the whole
    // ring: that is the setting the user is actually pulling when they want
    // children to hug. The count-based spacing still wins when a room is too
    // crowded for labels to fit at that distance.
    ORBIT: {
        minRadius: 130,
        maxRadius: 320,
        spacing: 92,
        nestedScale: 0.45,
        baseEdgeLength: 60,
        // Start at the top and go clockwise, so the first item clears the room's
        // own label instead of sitting on it.
        startAngle: -Math.PI / 2,
    },
    /** The orbit's current numbers, scaled by the item-edge-length setting. */
    _orbitSpec() {
        let length = this.ORBIT.baseEdgeLength;
        try {
            const cfg = (typeof config !== 'undefined' && config) || null;
            const raw = cfg && Number(cfg.graphItemEdgeLength);
            if (raw)
                length = raw;
        }
        catch (err) { /* keep the default */ }
        // The orbit is a *map* measurement when a painted grid owns the layout:
        // at the 40px default these are the numbers above, and on a 260px map the
        // ring grows with the cells so an item still reads as beside its room
        // rather than inside it (bug-53). In the graph view the map scale is 1,
        // so nothing changes there.
        let mapScale = 1;
        try {
            const engine = _layoutEngine();
            if (typeof graphManager !== 'undefined' && graphManager && graphManager._cardinalLayout === true
                && engine && engine.mapSpacing) {
                mapScale = engine.mapSpacing() / 40;
            }
        }
        catch (err) { /* keep the default */ }
        const scale = Math.max(0.25, Math.min(length / this.ORBIT.baseEdgeLength, 3.5)) * mapScale;
        return {
            length,
            scale,
            minRadius: this.ORBIT.minRadius * scale,
            maxRadius: this.ORBIT.maxRadius * scale,
            // Spacing scales too: a short "rest length" genuinely pulls a crowded
            // room tight (labels may overlap — that is what hugging means), a long
            // one spreads it out.
            spacing: this.ORBIT.spacing * scale,
        };
    },
    /**
     * Whether a node is *placed* rather than simulated: it keeps its own x/y and
     * is never repositioned. Two ways to say it — the inspector's "Physics
     * enabled" off (`central_gravity_enabled: false`) or an explicit
     * `layout_static: true` — because they are the same intent.
     */
    isStatic(node) {
        const props = (node && node.properties) || {};
        return props.central_gravity_enabled === false || props.layout_static === true;
    },
    /**
     * How a *parent* wants its contents arranged. A per-node override wins over
     * the global setting, so a room can say "my contents sit 90px out, 40px
     * apart" without changing every other room:
     *
     *   layout_child_distance  - desired distance from the parent (px)
     *   layout_child_spacing   - desired gap between its contents (px)
     *   layout_min_radius / layout_max_radius - clamp the ring
     */
    _parentSpec(parentNode) {
        const props = (parentNode && parentNode.properties) || {};
        const base = this._orbitSpec();
        const positive = (value) => (Number(value) > 0 ? Number(value) : null);
        return {
            ...base,
            distance: positive(props.layout_child_distance) || base.length,
            spacing: positive(props.layout_child_spacing) || base.spacing,
            minRadius: positive(props.layout_min_radius) || base.minRadius,
            maxRadius: positive(props.layout_max_radius) || base.maxRadius,
        };
    },
    /** A node's own desired distance from its parent, else its parent's default. */
    _childDistance(node, spec) {
        const props = (node && node.properties) || {};
        const own = Number(props.layout_distance);
        return own > 0 ? own : spec.distance;
    },
    /** True when this child's distance was asked for by name, not inherited. */
    _distanceIsExplicit(node, parentNode) {
        const props = (node && node.properties) || {};
        const parentProps = (parentNode && parentNode.properties) || {};
        return Number(props.layout_distance) > 0
            || Number(parentProps.layout_child_distance) > 0
            || Number(parentProps.layout_min_radius) > 0
            || Number(parentProps.layout_max_radius) > 0;
    },
    _edges() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const edges = g._graphEdgesArr;
        if (Array.isArray(edges) && edges.length)
            return edges;
        return (typeof worldState !== 'undefined' && worldState?.graph?.edges) || [];
    },
    _nodes() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        if (g._graphNodesObj && Object.keys(g._graphNodesObj).length)
            return g._graphNodesObj;
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
            const list = adjacency.get(a);
            if (list)
                list.push(b);
            else
                adjacency.set(a, [b]);
        };
        for (const edge of edges || []) {
            if (!edge || !edge.type || !this.RELATION_TYPES.has(edge.type))
                continue;
            const { source, target } = edge;
            if (!source || !target || !nodes[source] || !nodes[target])
                continue;
            link(source, target);
            link(target, source);
        }
        const map = new Map();
        const queue = Object.keys(nodes).filter((id) => nodes[id] && nodes[id].type === 'area');
        for (const id of queue)
            map.set(id, 0);
        for (let head = 0; head < queue.length; head++) {
            const current = queue[head];
            for (const next of adjacency.get(current) || []) {
                if (map.has(next))
                    continue;
                map.set(next, (map.get(current) ?? 0) + 1);
                queue.push(next);
            }
        }
        this._depthCache = { nodes, edges, map };
        return map;
    },
    /** Tie-break when both ends of a relation are equally deep. */
    _rank(node) {
        if (!node)
            return 0;
        if (node.type === 'area')
            return 3;
        if (node.type === 'character')
            return 2;
        return 1;
    },
    /** Parent of every node, cached by graph identity (one derive per layout). */
    _parents(nodes, edges) {
        if (this._parentCache && this._parentCache.nodes === nodes && this._parentCache.edges === edges) {
            return this._parentCache.map;
        }
        const map = {};
        for (const id of Object.keys(nodes))
            map[id] = this.parentOf(id, edges, nodes);
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
        if (self && (self.type === 'area' || self.type === 'way'))
            return null;
        const depths = this._depths(nodes, edges);
        const mine = depths.get(nodeId);
        for (const rule of this.PARENT_RULES) {
            let best = null;
            let bestDepth = Infinity;
            for (const edge of edges) {
                if (!edge || edge.type !== rule.type)
                    continue;
                let other = null;
                if (rule.child === 'source') {
                    if (edge.source !== nodeId)
                        continue;
                    other = edge.target;
                }
                else if (rule.child === 'target') {
                    if (edge.target !== nodeId)
                        continue;
                    other = edge.source;
                }
                else {
                    other = edge.source === nodeId ? edge.target
                        : (edge.target === nodeId ? edge.source : null);
                }
                if (!other || !nodes[other] || other === nodeId)
                    continue;
                const depth = depths.get(other);
                if (rule.child === null) {
                    // `in` has no trustworthy direction, so the end nearer the
                    // area roots is the parent. Only something shallower can be
                    // a parent, which also keeps a two-node container cycle
                    // parentless instead of each holding the other.
                    if (depth === undefined || (mine !== undefined && depth >= mine))
                        continue;
                }
                const sortDepth = depth === undefined ? Infinity : depth;
                if (sortDepth < bestDepth || (sortDepth === bestDepth && this._rank(nodes[other]) > this._rank(best ? nodes[best] : null))) {
                    best = other;
                    bestDepth = sortDepth;
                }
            }
            if (best)
                return best;
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
            if (!edge || edge.type !== 'connection')
                continue;
            const other = edge.source === nodeId ? edge.target : (edge.target === nodeId ? edge.source : null);
            if (!other || !nodes[other] || nodes[other].type !== 'area')
                continue;
            const pos = positions[other];
            if (pos)
                rooms.push(pos);
        }
        if (!rooms.length)
            return null;
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
            if (depths[id] !== undefined)
                return depths[id];
            const seen = new Set();
            let hops = 0, current = id;
            while (current && nodes[current] && nodes[current].type !== 'area'
                && nodes[current].type !== 'way') {
                if (seen.has(current)) {
                    depths[id] = Infinity;
                    return Infinity;
                }
                seen.add(current);
                current = parents[current];
                hops++;
            }
            if (!current || !nodes[current]) {
                depths[id] = Infinity;
                return Infinity;
            }
            depths[id] = hops;
            return hops;
        };
        const out = {};
        for (const id of ids) {
            if (nodes[id] && nodes[id].type === 'area') {
                const pos = positions[id];
                if (pos && Number.isFinite(pos.x) && Number.isFinite(pos.y))
                    out[id] = { x: pos.x, y: pos.y };
            }
        }
        // Children grouped under their parent, in a stable order.
        const children = {};
        for (const id of ids) {
            const parent = parents[id];
            if (!parent || !nodes[parent])
                continue;
            (children[parent] = children[parent] || []).push(id);
        }
        // Ways are the meeting point of the rooms they connect, not a ring, and
        // they come first so a trigger hosted by a way has somewhere to sit.
        for (const id of ids) {
            if (!nodes[id] || nodes[id].type !== 'way')
                continue;
            const mid = this.wayMidpoint(id, edges, positions, nodes);
            if (mid)
                out[id] = mid;
        }
        // Top-down: a parent is always placed before the things hanging off it.
        const placeable = ids
            .filter((id) => nodes[id] && nodes[id].type !== 'area' && nodes[id].type !== 'way')
            .filter((id) => depthOf(id) !== Infinity)
            .sort((a, b) => depthOf(a) - depthOf(b) || (a < b ? -1 : 1));
        for (const id of placeable) {
            const parent = parents[id];
            if (!parent)
                continue;
            const parentPos = out[parent];
            if (!parentPos)
                continue;
            const node = nodes[id] || {};
            const siblings = (children[parent] || [id]).filter((child) => {
                const c = nodes[child];
                return c && this._slotFor(c) === this._slotFor(node);
            });
            const index = Math.max(0, siblings.indexOf(id));
            const count = Math.max(1, siblings.length);
            out[id] = this.orbitPosition(parentPos, index, count, node, Math.max(1, depthOf(id)), nodes[parent]);
        }
        // Short-range separation (graph/separation.js): a node no edge joins is
        // pushed off its neighbours, so a crowded room's contents and a nested
        // container stop layering on top of one another. Areas and ways are the
        // anchors and never move. Off unless the setting enables it.
        const separation = _separation();
        if (separation && separation.enabled()) {
            const spec = separation.spec();
            // Restore any displaced node to the spot the orbit gave it (its
            // place on the ring), never to the parent's centre — otherwise a
            // crowded character/item is sucked onto the area it belongs to.
            spec.targets = {};
            for (const id of Object.keys(out))
                spec.targets[id] = { x: out[id].x, y: out[id].y };
            const resolved = separation.resolve(nodes, edges, out, spec);
            for (const id of Object.keys(resolved))
                out[id] = resolved[id];
        }
        return out;
    },
    /**
     * Hierarchical mode positions nodes by edge *direction*, and the stored `in`
     * edges disagree with each other (`Backpack -> Ink` vs `fireplace ->
     * living_room` — bug-44). So the level edges are oriented from the resolved
     * parent instead: the parent becomes `from`, the child `to`, and the arrow
     * keeps pointing the way the relation actually reads.
     */
    levelEdge(source, target, nodes, edges) {
        const nodesObj = nodes || this._nodes();
        const edgesArr = edges || this._edges();
        const parentOfTarget = this.parentOf(target, edgesArr, nodesObj);
        const parentOfSource = this.parentOf(source, edgesArr, nodesObj);
        if (parentOfTarget === source)
            return { from: source, to: target, flipped: false };
        if (parentOfSource === target)
            return { from: target, to: source, flipped: true };
        return { from: source, to: target, flipped: false };
    },
    /** True when the graph should let vis's hierarchical layout own positions. */
    levelsMode() {
        try {
            return (typeof config !== 'undefined' && config && config.graphLayoutMode) === 'levels';
        }
        catch (err) {
            return false;
        }
    },
    /**
     * Room-to-door edges are stored both ways round (a door is entered from both
     * rooms), which is a 2-cycle the level sort cannot order. For layout the way
     * is always the child, so the door sits below the rooms it joins.
     */
    connectionLevelEdge(source, target, nodes) {
        const nodesObj = nodes || this._nodes();
        const sourceIsWay = nodesObj[source] && nodesObj[source].type === 'way';
        const targetIsWay = nodesObj[target] && nodesObj[target].type === 'way';
        if (sourceIsWay && !targetIsWay)
            return { from: target, to: source, flipped: true };
        return { from: source, to: target, flipped: false };
    },
    /** Which arc a node sorts into, so a room's items/characters/triggers group. */
    _slotFor(node) {
        if (!node)
            return 'default';
        return node.type === 'item' || node.type === 'character' || node.type === 'logic_trigger'
            ? node.type : 'default';
    },
    /**
     * Where the *n*-th of *count* children of a parent orbits. The radius is the
     * child's own `layout_distance`, else the parent's `layout_child_distance`,
     * else the item-edge-length setting (Hug Parent <-> Stretched), grown when the
     * crowd needs more room for labels, and clamped by the parent's
     * `layout_min_radius`/`layout_max_radius`. Nested contents orbit their
     * container on a proportionally smaller ring.
     */
    orbitPosition(parentPos, index, count, node, depth, parentNode = {}) {
        const spec = this._parentSpec(parentNode);
        const nested = depth >= 2;
        const want = nested
            ? this._childDistance(node, spec) * this.ORBIT.nestedScale
            : this._childDistance(node, spec);
        const spacing = nested ? spec.spacing * this.ORBIT.nestedScale : spec.spacing;
        const needed = (Math.max(1, count) * spacing) / (2 * Math.PI);
        // An explicitly requested distance is honoured even outside the comfort
        // range: someone who says "90px" or "400px" means it (labels may overlap
        // at 90 - that is what hugging means). The range only governs the
        // automatic growth for a crowd.
        const explicit = this._distanceIsExplicit(node, parentNode);
        const floor = explicit
            ? Math.min(nested ? spec.minRadius * this.ORBIT.nestedScale : spec.minRadius, want)
            : (nested ? spec.minRadius * this.ORBIT.nestedScale : spec.minRadius);
        const ceiling = explicit
            ? Math.max(nested ? spec.maxRadius * this.ORBIT.nestedScale : spec.maxRadius, want)
            : (nested ? spec.maxRadius * this.ORBIT.nestedScale : spec.maxRadius);
        const radius = explicit
            // An asked-for distance is exact: "80px away" means 80px, even if that
            // means labels touch. Automatic growth is only for inherited distances.
            ? Math.max(want, 0)
            : Math.max(floor, Math.min(Math.max(want, needed), ceiling));
        const angle = this.ORBIT.startAngle + (2 * Math.PI * index) / Math.max(1, count);
        return {
            x: parentPos.x + radius * Math.cos(angle),
            y: parentPos.y + radius * Math.sin(angle),
        };
    },
    /**
     * Seed the derived layout: put every child in its parent's block, then hand
     * it to the solver. The child is left `physics: true` and unfixed — the ring
     * is where it *starts*, and from there its own edge spring holds it to the
     * room or carrier that holds it while repulsion sorts out its neighbours.
     *
     * @returns {number} how many nodes were placed
     */
    apply() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const network = g.network;
        if (!network || !network.body?.data?.nodes)
            return 0;
        // Hierarchical mode owns positions; a seed would fight it.
        if (this.levelsMode())
            return 0;
        const nodes = this._nodes();
        if (!Object.keys(nodes).length)
            return 0;
        const current = this._positions(network);
        if (!Object.keys(current).length)
            return 0;
        const derived = this.layoutPositions(nodes, this._edges(), current);
        const updates = [];
        for (const [id, rawPos] of Object.entries(derived)) {
            const pos = rawPos;
            const node = nodes[id];
            if (!node || node.type === 'area' || node.type === 'way')
                continue;
            // A node the user froze keeps its own place and stays out of the
            // solver — that is what "Physics enabled" off means.
            if (this.isStatic(node))
                continue;
            if (!Number.isFinite(pos.x) || !Number.isFinite(pos.y))
                continue;
            // In the solver, and not pinned: the player can still drag it, and the
            // sim keeps it beside whatever holds it.
            updates.push({ id, x: pos.x, y: pos.y, fixed: false, physics: true });
        }
        if (updates.length) {
            try {
                network.body.data.nodes.update(updates);
            }
            catch (err) { /* ignore */ }
        }
        return updates.length;
    },
    /**
     * Re-run the overlap guard over the graph as it stands — no ring re-seed,
     * no teleport. The guard's knobs (strength, range, pull) and Node size
     * (which scales the guard's radii) only take effect when this pass runs;
     * it used to be reachable solely through apply(), i.e. through a full
     * layout re-derivation on a stabilization event, so tuning them live did
     * nothing until the next rebuild. A displaced stray is reeled toward its
     * holder's *current* position — what the knob's hint promises — rather
     * than onto a fresh ring slot.
     *
     * @returns {number} how many nodes moved
     */
    resolveSeparation() {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const network = g.network;
        if (!network || !network.body?.data?.nodes)
            return 0;
        if (this.levelsMode())
            return 0;
        const separation = _separation();
        if (!separation || !separation.enabled())
            return 0;
        const nodes = this._nodes();
        if (!Object.keys(nodes).length)
            return 0;
        const edges = this._edges();
        const positions = this._positions(network);
        if (!Object.keys(positions).length)
            return 0;
        const parents = this._parents(nodes, edges);
        const spec = separation.spec();
        spec.targets = {};
        for (const id of Object.keys(positions)) {
            const parent = parents[id];
            const target = (parent && positions[parent]) ? positions[parent] : positions[id];
            spec.targets[id] = { x: target.x, y: target.y };
        }
        const resolved = separation.resolve(nodes, edges, positions, spec);
        const updates = [];
        for (const [id, pos] of Object.entries(resolved)) {
            const node = nodes[id];
            if (!node || node.type === 'area' || node.type === 'way')
                continue;
            if (this.isStatic(node))
                continue;
            if (!Number.isFinite(pos.x) || !Number.isFinite(pos.y))
                continue;
            updates.push({ id, x: pos.x, y: pos.y });
        }
        if (updates.length) {
            try {
                network.body.data.nodes.update(updates);
            }
            catch (err) { /* ignore */ }
        }
        return updates.length;
    },
    /** Drop the derived cache so the next apply() re-reads the graph. */
    /** Drop the derived caches so the next apply() re-reads the graph. */
    reseed() {
        this._depthCache = null;
        this._parentCache = null;
    },
    /** Live positions, hidden nodes included (`getPositions()` drops them). */
    _positions(network) {
        const out = {};
        try {
            const body = network.body?.nodes || {};
            for (const [id, n] of Object.entries(body)) {
                if (n && Number.isFinite(n.x) && Number.isFinite(n.y))
                    out[id] = { x: n.x, y: n.y };
            }
        }
        catch (err) { /* fall through */ }
        if (!Object.keys(out).length) {
            try {
                return network.getPositions?.() || {};
            }
            catch (err) {
                return {};
            }
        }
        return out;
    },
    /** The graph ops that would save frozen nodes' current positions. */
    frozenDropOps(ids) {
        const g = (typeof graphManager !== 'undefined' && graphManager) || {};
        const network = g.network;
        if (!network)
            return [];
        const nodes = this._nodes();
        const ops = [];
        for (const id of ids || []) {
            const props = (nodes[id] || {}).properties || {};
            if (!this.isStatic(nodes[id]))
                continue;
            // A PAINTED node's `properties.x/y` are the compiler's engine units
            // (`cell * 40`), which the map layout scales by the map pitch and
            // translates by the scope's `map_offset`. Writing a canvas position
            // over them double-converts: the next layout scales the pixels again
            // and adds the offset again, so a node that is dragged once ends up
            // further from everything on every later save. Areas were exempted
            // (bug-52); ways and characters were not, and this runs on every
            // dragEnd, which is why the creep was so easy to trigger.
            const engine = _layoutEngine();
            if (engine && typeof engine.hasPaintedCoords === 'function'
                && engine.hasPaintedCoords(props)) {
                continue;
            }
            const body = network.body?.nodes?.[id];
            if (!body || !Number.isFinite(body.x) || !Number.isFinite(body.y))
                continue;
            const bx = body.x;
            const by = body.y;
            ops.push({
                type: 'update_node',
                payload: {
                    node_id: id,
                    patch: { properties: { x: Math.round(bx * 10) / 10, y: Math.round(by * 10) / 10 } },
                },
            });
        }
        return ops;
    },
    /**
     * A frozen node that was dragged keeps its new place across reloads: its
     * position is written to the node (the same `properties.x/y` the layout lock
     * uses), because nothing else will restore it — the layout deliberately
     * leaves frozen nodes alone.
     */
    async persistFrozenDrop(ids) {
        const ops = this.frozenDropOps(ids);
        if (!ops.length)
            return 0;
        if (typeof ApiClient === 'undefined' || !ApiClient.batchGraph)
            return 0;
        try {
            await ApiClient.batchGraph(ops);
        }
        catch (err) { /* ignore — the position simply is not remembered */ }
        return ops.length;
    },
    /**
     * Seed the layout and remember where a frozen node was put.
     *
     * `stabilizationIterationsDone` is the one re-seed: vis has finished its
     * startup iterations, so the derived ring is applied over the positions the
     * solver chose and the simulation takes it from there. A drag does **not**
     * re-seed — re-deriving on every drop is what snapped a room's contents back
     * onto their ring mid-gesture; the edge springs carry them now.
     */
    attach(network) {
        if (!network || network._relativeLayoutAttached)
            return;
        network._relativeLayoutAttached = true;
        network.on('stabilizationIterationsDone', () => {
            this.apply();
        });
        network.on('dragEnd', (params) => {
            const dragged = (params && params.nodes) || [];
            if (dragged.length)
                this.persistFrozenDrop(dragged);
        });
    },
};
window.GraphRelativeLayout = _GraphRelativeLayout;
