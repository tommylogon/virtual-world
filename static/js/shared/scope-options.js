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
 * @returns {number} how many scopes were rendered
 */
function populate(sel, scopes, make) {
    const create = make || ((tag) => document.createElement(tag));
    const stack = [];   // stack[d] = the group currently open at depth d
    const list = scopes || [];
    for (const scope of list) {
        const opt = create('option');
        opt.value = scope.id;
        opt.textContent = scope.name;
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
 * no `depth` anywhere, and mixes nested objects at the root with bare id
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
function flattenScopes(payload) {
    if (!payload) return [];
    // Already flat (and already carrying `depth`) -- use it as it stands.
    if (Array.isArray(payload.scopes)) return payload.scopes.slice();
    if (!Array.isArray(payload.children)) return [];

    const out = [];
    const seen = new Set();
    const walk = (nodes, depth, parentId) => {
        for (const node of nodes) {
            if (typeof node === 'string') {
                // Bare id: the API declined to inline the node again, so we have
                // no name for it. Keep the scope reachable rather than dropping it.
                if (!seen.has(node)) {
                    seen.add(node);
                    out.push({ id: node, name: node, depth, parent_id: parentId });
                }
                continue;
            }
            if (!node || node.id === undefined || seen.has(node.id)) continue;
            seen.add(node.id);
            const d = node.depth != null ? node.depth : depth;
            out.push(Object.assign({}, node, {
                depth: d,
                parent_id: node.parent_id != null ? node.parent_id : (parentId || null),
            }));
            walk(node.children, d + 1, node.id);
        }
    };
    walk(payload.children, 0, null);
    return out;
}

window.ScopeOptions = { populate, flattenScopes };
