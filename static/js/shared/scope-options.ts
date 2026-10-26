/**
 * scope-options.js — build the world-scope picker's option tree.
 *
 * Extracted from graph-manager.js (task-627) so it can be unit-tested without
 * loading the whole GraphManager into the test sandbox, and so the hierarchy is
 * expressed structurally instead of as invisible whitespace.
 *
 * @module shared/scope-options — the scope picker's nesting rules
 * @contributes `window.ScopeOptions`: `populate(sel, scopes, make)` renders a
 *   parent-before-child scope list as real `<optgroup>` nesting
 * @powers the `#graph-scope-filter` dropdown in the graph toolbar
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
'use strict';

/**
 * Render a scope list into a <select> as a real tree.
 *
 * task-627: this used to flatten the hierarchy into one row per scope with the
 * depth expressed as leading non-breaking spaces ("\u00A0".repeat(depth * 2) +
 * name), so a player had to count invisible characters to tell a zone from a
 * sub-zone. A <select> supports genuine nesting through <optgroup>, which is
 * announced as a group and collapses on its own.
 *
 * Scopes arrive parent-before-child (task-531 keeps `parent_id` for exactly
 * this), so a stack of open groups is enough: pop back to the requested depth,
 * then append into that depth's group.
 *
 * @param {object}   sel     the <select> to populate (left otherwise untouched,
 *                           so the caller keeps ownership of the whole-world row)
 * @param {Array}    scopes  scope summaries, each {id, name, depth}
 * @param {Function} [make]  (tagName) => element factory; defaults to
 *                           document.createElement. Injected by the tests.
 * @returns {number} how m*FIX* scopes were rendered
 */
function populate(sel: ElementLike, scopes: ScopeOptionsScopeSummary[] | null | undefined, make?: ElementFactory) {
    const create: ElementFactory = make || ((tag: string) => document.createElement(tag) as unknown as ElementLike);
    const stack: ElementLike[] = [];   // stack[d] = the group currently open at depth d
    const list = scopes || [];
    for (const scope of list) {
        const opt = create('option');
        opt.value = scope.id as string;
        opt.textContent = scope.name as string;
        const depth = Math.max(0, scope.depth || 0);
        stack.length = Math.min(stack.length, depth);   // close deeper branches
        if (depth === 0) {
            sel.appendChild(opt);
            continue;
        }
        if (!stack[depth - 1]) {
            const group = create('optgroup');
            group.label = (depth === 1) ? 'Zones' : 'Sub-zones';
            (stack[depth - 2] || sel).appendChild(group);
            stack[depth - 1] = group;
        }
        stack[depth - 1].appendChild(opt);
    }
    return list.length;
}

/**
 * Normalise the scope list from EITHER shape the API can return.
 *
 * `/api/world/scopes?flat=1` (what the picker calls, via
 * `ApiClient.getWorldScopes(true)`) answers `{scopes: [{id, name, depth,
 * parent_id, map_offset}]}` -- already flat and already carrying `depth`.
 *
 * `/api/world/scopes` (the default) answers a NESTED tree under `children` with
 * no `depth` *FIX*where, and mixes nested objects at the root with bare id
 * strings one level down.
 *
 * The flat form is returned untouched. The nested form is walked into the same
 * shape so callers never have to know which endpoint they were handed.
 *
 * A note on how this was got wrong once: the first version only read
 * `payload.children`, on the strength of curling the non-flat endpoint by hand.
 * The picker calls the flat one, so it received an empty list and the scope
 * picker rendered nothing. Both shapes are handled now, and the unit tests pin
 * them separately.
 *
 * @param {object} payload a parsed /api/world/scopes response
 * @returns {Array} flat summaries, each {id, name, depth, parent_id, ...rest}
 */
function flattenScopes(payload?: ScopePayload | null): ScopeOptionsScopeSummary[] {
    if (!payload) return [];
    // Already flat (and already carrying `depth`) -- use it as it stands.
    if (Array.isArray(payload.scopes)) return (payload.scopes as ScopeOptionsScopeSummary[]).slice();
    if (!Array.isArray(payload.children)) return [];

    const out: ScopeOptionsScopeSummary[] = [];
    const seen = new Set<unknown>();
    const walk = (nodes: unknown[], depth: number, parentId: string | null) => {
        for (const raw of nodes) {
            if (typeof raw === 'string') {
                // Bare id: the API declined to inline the node again, so we have
                // no name for it. Keep the scope reachable rather than dropping it.
                if (!seen.has(raw)) {
                    seen.add(raw);
                    out.push({ id: raw, name: raw, depth, parent_id: parentId });
                }
                continue;
            }
            const node = raw as NestedScopeNode;
            if (!node || node.id === undefined || seen.has(node.id)) continue;
            seen.add(node.id);
            const d = node.depth != null ? node.depth : depth;
            out.push(Object.assign({}, node, {
                depth: d,
                parent_id: node.parent_id != null ? node.parent_id : (parentId || null),
            }) as ScopeOptionsScopeSummary);
            walk(node.children as unknown[], d + 1, node.id);
        }
    };
    walk(payload.children, 0, null);
    return out;
}

/**
 * The scope a node belongs to, resolved from the graph itself.
 *
 * A node declares its own scope in `properties.world_scope_id` (areas and
 * hand-placed things) or `properties.generated.scope_id` (compiled/generated
 * nodes) — the same two keys `graph.py` `_declared_scope` reads. A node with
 * neither (a character, a free-floating library item) is scope-less and is
 * located by walking the spatial edges UP from it to the area that contains it
 * and on to whichever ancestor declares a scope.
 *
 * This is the client mirror of `WorldGraph.scope_owners()` (task-582/583). It
 * exists here rather than calling the backend because `/api/state` already
 * ships the whole-world nodes and edges, so a selection can resolve its scope
 * with zero round-trips.
 *
 * @param {string} nodeId  the node to locate
 * @param {object|Map} nodes  whole-world nodes, id → node (a plain dict as
 *                            `/api/state` returns, or a Map)
 * @param {Array} edges    whole-world edges, each {source, target, type}
 * @returns {string|null} the owning scope id, or null when the node declares
 *                        no scope and has no spatial path to one
 */
function resolveScopeForNode(
    nodeId: string,
    nodes?: Record<string, ScopeNodeData> | Map<string, ScopeNodeData> | null,
    edges?: ScopeEdgeData[] | null
): string | null {
    if (!nodeId || !nodes) return null;
    const getNode = (id: string): ScopeNodeData | null => {
        if (nodes instanceof Map) return nodes.get(id) || null;
        return (nodes as Record<string, ScopeNodeData>)[id] || null;
    };
    const parent = _spatialParents(nodes, edges);
    const seen = new Set<string>();
    let cur: string | null = String(nodeId);
    // Bounded, and cycle-safe twice over: `seen` refuses a repeat, and the hop
    // cap stops a hand-authored cycle from spinning. The deepest chain measured
    // in a real scenario is 4 (item in a container in an area); 12 is slack.
    for (let hop = 0; cur && hop < 12; hop++) {
        if (seen.has(cur)) return null;
        seen.add(cur);
        const own = nodeScopeId(getNode(cur));
        if (own) return String(own);
        cur = parent.get(cur) || null;
    }
    return null;
}

/**
 * The scope a single node declares for itself, or null.
 *
 * The canonical read of `properties.world_scope_id` then
 * `properties.generated.scope_id` — the same two keys `graph.py`
 * `_declared_scope` reads on the backend. `GraphLayoutEngine.nodeScopeId`
 * delegates here so the rule has one home; this module is `shared/` and the
 * layout engine is `graph/`, so a graph→shared read is the right direction.
 *
 * @param {object} node  a graph node ({properties} is what is read)
 * @returns {*} the declared scope id, or null when the node declares none
 */
function nodeScopeId(node: ScopeNodeData | null): string | null {
    const props = (node && node.properties) || {};
    if (props.world_scope_id) return props.world_scope_id;
    const generated = props.generated;
    if (generated && generated.scope_id) return generated.scope_id;
    return null;
}

/**
 * The best spatial parent per node: for each node, the container reachable by
 * the highest-priority preposition it has. `at` is weaker than `in` (a
 * character can be `at` a landmark and `in` an area at once), so a node keeps
 * the strongest relation. The one builder both `resolveScopeForNode` (which
 * walks it) and `spatialParentOf` (which reports one hop) read.
 *
 * @returns {Map<string,string>} child id -> parent id
 */
function _spatialParents(
    nodes: Record<string, ScopeNodeData> | Map<string, ScopeNodeData> | null,
    edges?: ScopeEdgeData[] | null
): Map<string, string> {
    const parent = new Map<string, string>();
    const bestRank = new Map<string, number>();
    const has = (id: string): boolean => {
        if (nodes instanceof Map) return nodes.has(id);
        return !!nodes && Object.prototype.hasOwnProperty.call(nodes, id);
    };
    for (const e of (edges || [])) {
        const rank = SPATIAL_EDGE_TYPES.indexOf(String(e.type));
        if (rank < 0) continue;
        const src = String(e.source);
        const tgt = String(e.target);
        if (src === tgt) continue;
        if (!has(src) || !has(tgt)) continue;
        const prev = bestRank.get(src);
        if (prev === undefined || rank < prev) {
            bestRank.set(src, rank);
            parent.set(src, tgt);
        }
    }
    return parent;
}

/**
 * The node that directly holds *nodeId* by a spatial preposition (`in`/`on`/
 * `under`/`behind`/`at`), or null. The local frame a node sits in, for a
 * position readout — see `graphManager.debugNodePosition`.
 */
function spatialParentOf(
    nodeId: string,
    nodes: Record<string, ScopeNodeData> | Map<string, ScopeNodeData> | null,
    edges?: ScopeEdgeData[] | null
): string | null {
    if (!nodeId) return null;
    return _spatialParents(nodes, edges).get(String(nodeId)) || null;
}

// The spatial prepositions that place one node inside another, best first.
// `in`/`on`/`under`/`behind` are containment; `at` is "standing at a landmark"
// (a character `at` a bookshelf or a way) and is only trusted when nothing
// stronger exists.
//
// Deliberately EXCLUDED, with why each is not a place relation:
//   - `beside`     character→character adjacency, not containment; two
//                  characters beside each other can straddle an area boundary.
//   - `carrying`,  item→character possession. The direction is not even
//     `equipped`   consistent in the data (both item→char and char→item occur),
//                  so walking it can resolve a character's scope via an item.
//   - `connection` the generic structural edge (area↔way), not a place.
//   - `triggers`,  attachment and knowledge, not location.
//     `known`
const SPATIAL_EDGE_TYPES = ['in', 'on', 'under', 'behind', 'at'];

(window as unknown as {
    ScopeOptions: {
        populate: typeof populate;
        flattenScopes: typeof flattenScopes;
        resolveScopeForNode: typeof resolveScopeForNode;
        spatialParentOf: typeof spatialParentOf;
        nodeScopeId: typeof nodeScopeId;
    };
}).ScopeOptions = { populate, flattenScopes, resolveScopeForNode, spatialParentOf, nodeScopeId };

// NOTE: these shape declarations sit AFTER the first value statement on purpose.
// A leading `interface`/`type` makes TypeScript drop the file's leading JSDoc
// block from the emitted .js, and tools/js_module_index.py reads the `@module`
// tag out of that emitted .js.
type ElementFactory = (tag: string) => ElementLike;

/**
 * The minimum surface populate() needs. Deliberately structural rather than
 * HTMLSelectElement: the unit tests inject fake elements, and a real <select>
 * satisfies this shape.
 */
interface ElementLike {
    label: string;
    value: string;
    textContent: string;
    appendChild(child: ElementLike): ElementLike;
}

interface ScopeOptionsScopeSummary {
    id?: string;
    name?: string;
    depth?: number;
    parent_id?: string | null;
}

interface NestedScopeNode {
    id?: string;
    depth?: number | null;
    parent_id?: string | null;
    children?: unknown[];
}

interface ScopePayload {
    scopes?: unknown;
    children?: unknown;
}

/** The slice of a graph node the scope readers touch. */
interface ScopeNodeData {
    properties?: {
        world_scope_id?: string | null;
        generated?: { scope_id?: string | null } | null;
    } | null;
}

/** The slice of a graph edge resolveScopeForNode reads. */
interface ScopeEdgeData {
    source?: string;
    target?: string;
    type?: string;
}
