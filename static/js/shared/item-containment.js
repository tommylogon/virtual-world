/**
 * item-containment.js — ONE rule for what a character can see inside things.
 *
 * @module shared/item-containment — the single item-containment walk
 * @contributes `window.ItemContainment`: sealed/hidden predicates, any-depth
 *   `walkContents`, and a reachability-ordered `collectReachable`
 * @powers Take / drop / give — the item listings in world-state.js and
 *   agent/prompt-builder/room-context.js
 * @relates mirrors `engine/item_reach.py` (`_CLOSED_STATES`, `_is_hidden`,
 *   `_is_open`, `_visible_ordered`) — the client half of that rule
 * @docs docs/virtualWorld/Items & Inventory/Items Overview.md
 *
 * Why this exists: every renderer that re-implemented "what is inside this?"
 * drifted. The engine walks any depth and honours container state; the client
 * walked ONE level and checked almost nothing, so a prompt could list a battery
 * inside a locked cabinet, or a part three levels down, or nothing at all
 * depending on which code path ran. This is the one walk, so the two agree by
 * construction rather than by review.
 *
 * The rules, from `engine/item_reach.py`:
 *   - a `hidden` node is pruned entirely, and so is everything inside it;
 *   - a node that is `closed`/`locked`/`sealed` (or has `locked: true`) is
 *     still listed — the box is there — but its contents are sealed away;
 *   - otherwise descend, to any depth.
 */
window.ItemContainment = (() => {
    'use strict';

    /** States that seal a container's contents away (the node stays visible). */
    const CLOSED_STATES = ['closed', 'locked', 'sealed'];

    const norm = (value) => String(value ?? '').trim().toLowerCase();

    /** Hidden per engine convention: `current_state == 'hidden'`. The boolean
     *  `hidden:` property is deliberately ignored — visibility filters across
     *  the engine only honour the state machine. */
    const isHidden = (node) => norm(node?.properties?.current_state) === 'hidden';

    const isOpen = (node) => {
        if (node?.properties?.locked) return false;
        return !CLOSED_STATES.includes(norm(node?.properties?.current_state));
    };

    /**
     * Every item `in` `parentId`, recursively, honouring the rules above.
     * Returns `[{ id, name, properties, depth, parentId }]` in walk order.
     * `maxDepth` of Infinity is the default; a cycle is safe.
     *
     * The gate on `parentId` itself is applied HERE, not left to the caller:
     * every call site would otherwise have to remember to check, and one that
     * forgets silently lists the inside of a locked cabinet — which is the
     * exact bug this module exists to end.
     */
    function walkContents(parentId, options = {}) {
        const { getNode, edges, maxDepth = Infinity } = options;
        const parent = getNode(parentId);
        if (parent && (!isOpen(parent) || isHidden(parent))) return [];
        const out = [];
        const seen = new Set([parentId]);

        const walk = (id, depth) => {
            if (depth > maxDepth) return;
            for (const edge of edges || []) {
                if (edge.type !== 'in' || edge.target !== id) continue;
                const node = getNode(edge.source);
                if (!node || node.type !== 'item' || seen.has(node.id)) continue;
                seen.add(node.id);
                if (isHidden(node)) continue;   // pruned, subtree and all
                out.push({ id: node.id, name: node.name, properties: node.properties, depth, parentId: id });
                if (isOpen(node)) walk(node.id, depth + 1);
            }
        };
        // Children start at depth 1, so a child is never confused with the node
        // it is inside. `collectReachable` puts its roots at depth 0 and this
        // walks straight into it, which is what makes `depth` mean the same
        // thing in both entry points.
        walk(parentId, 1);
        return out;
    }

    /**
     * The engine's `_visible_ordered` rule, for a set of roots (carried items,
     * the area). Roots are always listed — holding a sealed safe still shows
     * the safe — and their contents follow the same rules.
     */
    function collectReachable(rootIds, options = {}) {
        const { getNode } = options;
        const out = [];
        const seen = new Set();
        for (const rootId of rootIds || []) {
            const root = getNode(rootId);
            if (!root || root.type !== 'item' || seen.has(rootId)) continue;
            seen.add(rootId);
            if (!isHidden(root)) {
                out.push({ id: root.id, name: root.name, properties: root.properties, depth: 0, parentId: null });
            }
            for (const child of walkContents(rootId, options)) {
                if (seen.has(child.id)) continue;
                seen.add(child.id);
                out.push(child);
            }
        }
        return out;
    }

    return { CLOSED_STATES, isHidden, isOpen, walkContents, collectReachable };
})();
