"use strict";
/**
 * GraphScopeTree — the scope hierarchy as a tree, beside the graph (task-397 step 4).
 *
 * The graph workspace could already *load* one world scope at a time and already
 * showed a breadcrumb of where you are (task-531), but the way you got there was
 * a flat `<select>` with the names indented by depth. That reads as a list, not a
 * hierarchy: a world with three towns under a county looked like six unrelated
 * entries, and nothing said how big a scope was or whether it had been built yet.
 *
 * This module turns the one payload the server already sends — the flat
 * `GET /api/world/scopes?flat=1` list, which carries `parent_id` and `depth` per
 * scope — into a collapsible tree. No new endpoint, and no per-scope request.
 *
 * The rules live in pure functions (`buildTree`, `visibleRows`, `toggleCollapsed`,
 * `rowLabel`) so they are unit-tested in tools/unit/test_graph_scope_tree.js
 * instead of only being verifiable by eye in a browser. The DOM half is a thin
 * render over those.
 *
 * Two honesty rules, both of which are about not inventing structure:
 *   - A scope card reports what the manifest says. An `unmade` scope shows as
 *     unmade, and its counts are the ones the server computed — the tree never
 *     implies a scope contains areas it does not have.
 *   - There is no Generate button here. Generating a scope is task-398's recipe
 *     flow and lives in the WorldPainter; a card that offered one would be a
 *     promise the graph cannot keep.
 *
 * @module graph/scope-tree — the world scope hierarchy as a collapsible tree
 * @contributes GraphScopeTree: tree/rows/labels from the flat scope list, and the panel that renders them
 * @powers the graph workspace scope panel — click a card to load that scope, expand to walk into it
 * @relates driven by graph-manager (the flat scope list and setScopeFilter); pairs with GraphToolbar's scope breadcrumb
 * @docs docs/virtualWorld/World Building/Graph System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.GraphScopeTree = (function () {
    'use strict';
    const WHOLE_WORLD = ''; // the sentinel the picker already uses for "no scope"
    // ── pure rules ──────────────────────────────────────────────────────
    /**
     * Nest a flat scope list into a tree.
     *
     * Prefers `parent_id`, because that is the manifest's own statement about the
     * hierarchy and survives a list that arrives in any order. A scope whose parent
     * is not in the list (or names itself, or sits in a parent cycle) is attached
     * to the root rather than dropped — an author who created a child before its
     * parent should still see the child.
     *
     * @param {Array<object>} scopes flat summaries from `?flat=1`
     * @returns {{id: string, children: Array}} synthetic root holding the top level
     */
    function buildTree(scopes) {
        const root = { id: null, name: 'Whole world', children: [] };
        const nodes = new Map();
        for (const scope of scopes || []) {
            if (!scope || !scope.id || nodes.has(scope.id))
                continue;
            nodes.set(scope.id, {
                id: scope.id,
                name: scope.name || scope.id,
                kind: scope.kind || '',
                state: scope.state || 'materialized',
                parentId: scope.parent_id || null,
                areaCount: scope.area_count || 0,
                characterCount: scope.character_count || 0,
                itemCount: scope.item_count || 0,
                hasCharacter: !!scope.has_character,
                children: [],
            });
        }
        // Second pass, so a child may appear before its parent in the list. The
        // node's `children` is built only here and never reset afterwards —
        // resetting it per scope would wipe children attached by an earlier
        // iteration and make the tree depend on the list's order.
        for (const scope of scopes || []) {
            const node = scope && nodes.get(scope.id);
            if (!node || node.placed)
                continue;
            node.placed = true;
            const parentId = node.parentId;
            if (!parentId || !nodes.has(parentId) || reaches(nodes, parentId, node.id)) {
                root.children.push(node);
            }
            else {
                nodes.get(parentId).children.push(node);
            }
        }
        return root;
    }
    /** Would following `fromId`'s parent links ever arrive back at `targetId`? */
    function reaches(nodes, fromId, targetId) {
        const seen = new Set();
        let current = fromId;
        while (current && !seen.has(current)) {
            if (current === targetId)
                return true;
            seen.add(current);
            const node = nodes.get(current);
            const parentId = node && node.parentId;
            current = parentId && nodes.has(parentId) ? parentId : null;
        }
        return false;
    }
    /**
     * Collapse a tree into the rows a panel should draw.
     *
     * Pure, so the panel's open/closed behaviour is testable without a DOM. A
     * collapsed scope still contributes its own row — collapsing hides what is
     * inside, never the scope itself, or the tree would lose the selected card.
     *
     * @param {object} tree from `buildTree`
     * @param {Set<string>} [collapsed] scope ids whose children are hidden
     * @param {string} [selectedId] the loaded scope, marked in the output
     * @returns {Array<object>} rows, parents before children
     */
    function visibleRows(tree, collapsed, selectedId) {
        const hidden = collapsed || new Set();
        const rows = [];
        const walked = new Set();
        (function walk(node, depth) {
            if (node.id === null) {
                // The synthetic root is not a card: its children are the top level.
                for (const child of node.children)
                    walk(child, 0);
                return;
            }
            // Belt and braces: `buildTree` already breaks cycles, so a card
            // appearing twice means the manifest is malformed, and hanging the
            // panel is the one outcome that cannot be recovered from.
            if (walked.has(node.id))
                return;
            walked.add(node.id);
            const hasChildren = node.children.length > 0;
            const isCollapsed = hasChildren && hidden.has(node.id);
            rows.push({
                id: node.id,
                name: node.name,
                kind: node.kind,
                state: node.state,
                depth,
                hasChildren,
                collapsed: isCollapsed,
                selected: node.id === selectedId,
                unmade: node.state === 'unmade',
                areaCount: node.areaCount,
                characterCount: node.characterCount,
                itemCount: node.itemCount,
                hasCharacter: node.hasCharacter,
            });
            if (isCollapsed)
                return;
            for (const child of node.children)
                walk(child, depth + 1);
        })(tree || { id: null, children: [] }, 0);
        return rows;
    }
    /**
     * Toggle one scope's collapsed state, returning a new Set.
     *
     * A new Set rather than a mutation: the panel re-renders from the result, and
     * a caller holding the old set should not see it change underneath.
     */
    function toggleCollapsed(collapsed, id) {
        const next = new Set(collapsed || []);
        if (!id)
            return next;
        if (next.has(id))
            next.delete(id);
        else
            next.add(id);
        return next;
    }
    /**
     * The one-line text of a scope card: name, then what the manifest says it holds.
     *
     * "unmade" is spelled out rather than left to an empty count, because an
     * unmade scope with zero areas and a materialized scope with zero areas are
     * different facts and the panel has to distinguish them.
     */
    function rowLabel(row) {
        if (!row)
            return '';
        const counts = [];
        // task-615: 'unmade' is a materialisation state, not a claim about contents,
        // and the two come apart -- 'goblin_camp' is state:'unmade' while holding
        // 21 areas and 10 characters present. Keying the row off 'unmade' rendered
        // it as 'not built' on a line that also said '10 here now'.
        if (row.areaCount)
            counts.push(row.areaCount + ' ' + plural(row.areaCount, 'area'));
        if (row.itemCount)
            counts.push(row.itemCount + ' ' + plural(row.itemCount, 'item'));
        if (row.unmade)
            counts.push(counts.length ? 'unmade' : 'not built');
        if (row.hasCharacter) {
            // "here now" is invariant in number — one person is also "here now".
            counts.push(`${row.characterCount} here now`);
        }
        return `${row.name} — ${counts.join(' · ')}`;
    }
    function plural(n, noun) {
        return n === 1 ? noun : `${noun}s`;
    }
    // ── the panel ───────────────────────────────────────────────────────
    function panel() {
        return document.getElementById('scope-tree');
    }
    /**
     * Put the host at the top of the Outline tab, above the area rows (task-592).
     *
     * The host is a *sibling* of `#outline-container` rather than a child of it,
     * because `renderOutlinePanel` hands that container to Lit, and Lit replaces
     * its children wholesale — a host nested inside would be destroyed on every
     * outline paint and the scope tree would blink out each time the state
     * updated. Sibling order does the job and survives the re-render.
     *
     * @returns {boolean} true when the host was placed and drawn
     */
    function mountInOutline() {
        const container = document.getElementById('outline-container');
        const pane = container && container.closest('.left-tab-pane');
        if (!container || !pane)
            return false;
        let host = panel();
        if (!host) {
            host = document.createElement('nav');
            host.id = 'scope-tree';
            host.className = 'scope-tree';
            host.setAttribute('aria-label', 'World scope hierarchy');
            pane.insertBefore(host, container);
        }
        else if (host.nextElementSibling !== container) {
            pane.insertBefore(host, container);
        }
        render();
        return true;
    }
    /**
     * Redraw the panel from the graph manager's flat scope list.
     *
     * Silent no-op when the panel is not on the page, so this is safe to call from
     * the same places that already call `loadScopeFilterOptions`.
     *
     * @param {Array<object>} [scopes] defaults to the graph manager's copy
     * @param {string} [selectedId] defaults to the loaded scope
     */
    function render(scopes, selectedId) {
        const host = panel();
        if (!host)
            return;
        const gm = window.graphManager;
        const list = scopes || (gm && gm._scopeSummaries) || [];
        const selected = selectedId !== undefined
            ? selectedId
            : (gm && gm._scopeFilter) || WHOLE_WORLD;
        const rows = visibleRows(buildTree(list), state.collapsed, selected);
        host.innerHTML = '';
        const whole = document.createElement('button');
        whole.type = 'button';
        whole.className = 'scope-tree-row scope-tree-whole'
            + (selected === WHOLE_WORLD ? ' selected' : '');
        whole.title = 'Show every area, way and character in the world';
        whole.textContent = '🌍 Whole world';
        whole.addEventListener('click', () => load(WHOLE_WORLD));
        host.appendChild(whole);
        for (const row of rows) {
            host.appendChild(rowElement(row, selected));
        }
        host.hidden = false;
    }
    function rowElement(row, selected) {
        const el = document.createElement('div');
        el.className = 'scope-tree-row'
            + (row.selected ? ' selected' : '')
            + (row.unmade ? ' unmade' : '')
            + (row.hasCharacter ? ' occupied' : '');
        el.style.paddingLeft = `${8 + row.depth * 14}px`;
        const twist = document.createElement('button');
        twist.type = 'button';
        twist.className = 'scope-tree-twist';
        if (row.hasChildren) {
            twist.textContent = row.collapsed ? '▸' : '▾';
            twist.title = row.collapsed ? 'Show what is inside' : 'Hide what is inside';
            twist.setAttribute('aria-expanded', row.collapsed ? 'false' : 'true');
            twist.addEventListener('click', (ev) => {
                ev.stopPropagation();
                state.collapsed = toggleCollapsed(state.collapsed, row.id);
                render();
            });
        }
        else {
            // Keeps the label aligned without offering a control that does nothing.
            twist.textContent = '·';
            twist.classList.add('leaf');
            twist.setAttribute('aria-hidden', 'true');
            twist.tabIndex = -1;
        }
        el.appendChild(twist);
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'scope-tree-card';
        card.dataset.scopeId = row.id;
        card.setAttribute('aria-current', row.selected ? 'true' : 'false');
        card.textContent = rowLabel(row);
        card.title = row.unmade
            ? `${row.name} — nothing is built here yet`
            : `${row.name} — ${row.areaCount} area(s), ${row.itemCount} item(s)`;
        card.addEventListener('click', () => load(row.id));
        el.appendChild(card);
        // A scope with nothing built in it is the one row where the reader cannot
        // act, because building a scope is the WorldPainter's ⚙ Generate and the
        // graph cannot do it (see this module's header). So the row offers the
        // honest jump rather than a button it cannot keep: open *that scope* in
        // the painter. A Generate button here would be a promise the graph does not
        // make; a link to where the button is, is one it can keep (task-592).
        if (row.unmade) {
            const jump = document.createElement('button');
            jump.type = 'button';
            jump.className = 'scope-tree-jump';
            jump.textContent = '🖌 Paint';
            jump.title = `Open ${row.name} in the WorldPainter to paint and `
                + 'generate it';
            jump.addEventListener('click', (ev) => {
                ev.stopPropagation();
                if (window.VW && VW.worldPainter
                    && typeof VW.worldPainter.open === 'function') {
                    VW.worldPainter.open(row.id);
                }
            });
            el.appendChild(jump);
        }
        return el;
    }
    function load(scopeId) {
        // Go through the toolbar's entry point when it is there: it is the one
        // place that also keeps the flat picker's value in step, and two ways to
        // change the loaded scope is how they drift apart.
        if (window.GraphToolbar
            && typeof GraphToolbar.loadScope === 'function') {
            GraphToolbar.loadScope(scopeId || WHOLE_WORLD);
            return;
        }
        if (window.graphManager
            && typeof graphManager.setScopeFilter === 'function') {
            graphManager.setScopeFilter(scopeId || null);
        }
    }
    const state = { collapsed: new Set() };
    return {
        buildTree,
        visibleRows,
        toggleCollapsed,
        rowLabel,
        render,
        mountInOutline,
        WHOLE_WORLD,
        _internals: { plural, load, state },
    };
})();
