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
 * @returns {number} how many scopes were rendered
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

(window as unknown as { ScopeOptions: { populate: typeof populate; flattenScopes: typeof flattenScopes } })
    .ScopeOptions = { populate, flattenScopes };

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
