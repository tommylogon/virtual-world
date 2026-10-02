/**
 * GraphTreeView — world outline tree for the left panel
 * Provides an interactive tree/outline inspector for rooms, exits, items, and players.
 * Clicking an area, item, way, or player moves the camera to that node and opens
 * the inspector. References the global graphManager singleton.
 *
 * @module graph/tree-view — the left-panel world outline
 * @contributes GraphTreeView: interactive tree of rooms, exits, items, and players
 * @powers clicking through the world outline to move the camera and open the inspector
 * @relates reads worldState; drives graphManager camera + VW.inspector
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

// Locals for cross-module globals not yet in static/js/types/globals.d.ts.
// `graphManager` and `worldState` ARE declared there, but as bare consts (any),
// which is not enough here: this module reaches `graphManager._scopeFilter`
// and indexes `worldState.areas`, so it reads them through a local shape.
interface TreeViewWindowSurface {
    GraphTreeView: unknown;
    graphManager: GraphManagerLike;
    GraphScopeTree: {
        mountInOutline: () => void;
        buildTree: (scopes: TreeViewScopeSummary[]) => unknown;
        visibleRows: (tree: unknown, expanded: Set<string>, selected: string | null) => ScopeRow[];
}
    selectAgent?: (name: string) => void;
};

// Lazy lit-html tag: window.Lit is only available at call time (deferred module
// bootstrap), not at parse time. Unique per file so top-level consts never collide.
const treeViewHtmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);

// Round temperature for display — kills float drift artifacts like
// -10.452438125°C that propagation can leave in stored values.
const treeViewFormatTemp = (v: unknown): string => (v == null ? '?' : (Math.round(Number(v) * 10) / 10) + '°C');

/** Select a character in the world — published by the character/spectator layer. */
// IIFE, not a top-level const: the object references itself, and a
// top-level `const treeViewApi` would be a global lexical binding that
// collides at parse time with any other script declaring that name.
(window as unknown as { GraphTreeView: GraphTreeViewApi }).GraphTreeView = (() => {
    const treeViewApi: GraphTreeViewApi = {
    /**
     * Build clickable item spans for a room. Clicking an item focuses the
     * camera on it and opens the item inspector. Items come from
     * worldState.getItemsInArea() (direct + spatial + container contents),
     * each with a graph node id.
     */
    _renderItems(items: ItemSummary[]): unknown {
        if (!items || !items.length) return window.Lit.nothing;
        const spanNodes: unknown[] = [];
        items.forEach((itemData: ItemSummary) => {
            const itemId = itemData.id || '';
            const itemName = itemData.name || itemData.id || '?';
            const desc = itemData.description || itemData.properties?.description || '';
            if (spanNodes.length) spanNodes.push(treeViewHtmlTag`, `);
            spanNodes.push(treeViewHtmlTag`
                    <span class="vtree-item" title=${desc || window.Lit.nothing} @click=${itemId ? () => graphManager.showNodeAndFocus(itemId) : window.Lit.nothing}>${itemName}</span>`);
        });
        return treeViewHtmlTag`<div class="vtree-child"><span class="vtree-desc-icon">📦</span>${spanNodes}</div>`;
    },

    /**
     * Renders the world outline into a left-panel container.
     * Shows all rooms sorted with their environment data, exits (clickable to
     * focus the way node), items (clickable), and players present (clickable).
     * Replaces the container contents on each render.
     *
     * @param {HTMLElement} container - The DOM element to render the outline into
     */
    renderOutlinePanel(container: HTMLElement): void {
        if (!container || !worldState.data) return;
        const rooms = Object.keys(worldState.areas || {}).sort();
        const players = Object.entries(worldState.players || {}) as Array<[string, PlayerData]>;
        // A scope filter is on, so these areas are a scope's, not the world's, and
        // the heading must say so — otherwise "53 areas" reads as the size of the
        // world when it is the size of one scope (task-592).
        const gm = (window as unknown as TreeViewWindowSurface).graphManager;
        const scopedTo = String((gm && gm._scopeFilter) || '');
        const scopedName = (gm && gm._scopeSummaries || [])
            .find((s: TreeViewScopeSummary) => s && s.id === scopedTo);
        const scopeNote = scopedTo
            ? ` — in ${(scopedName && scopedName.name) || scopedTo}`
            : '';
        const playerRoomMap: Record<string, string[]> = {};
        players.forEach(([playerName, playerData]: [string, PlayerData]) => {
            const currentArea = playerData.current_area;
            if (currentArea) {
                if (!playerRoomMap[currentArea]) playerRoomMap[currentArea] = [];
                playerRoomMap[currentArea].push(playerName);
            }
        });
        const roomFragments = rooms.map((areaName: string, roomIndex: number) => {
            const area = (worldState.areas as Record<string, AreaData>)[areaName];
            const env = area.environment || {};
            const temp = treeViewFormatTemp(env.temperature);
            const light = env.light != null ? env.light : '?';
            const air = env.air || '?';
            const desc = area.description || '';
            const descShort = desc.length > 120 ? desc + '...' : desc;
            const exits = Object.entries(area.exits || {});
            const items = worldState.getItemsInArea(areaName) as ItemSummary[];
            const here = playerRoomMap[areaName] || [];
            const uid = `ovt-${roomIndex}`;

            const childFragments: unknown[] = [];

            if (desc) {
                let descContent;
                if (desc.length > 120) {
                    descContent = treeViewHtmlTag`<span id="${uid}-d" class="vtree-desc-short">${descShort}</span><span id="${uid}-df" style="display:none">${desc}</span> <span class="vtree-more" @click=${() => graphManager._toggleDesc(uid)}>more</span>`;
                } else {
                    descContent = treeViewHtmlTag`<span>${desc}</span>`;
                }
                childFragments.push(treeViewHtmlTag`<div class="vtree-child"><span class="vtree-desc-icon">📝</span>${descContent}</div>`);
            }

            if (exits.length) {
                const exitNodes: unknown[] = [];
                exits.forEach(([direction, exitData]: [string, unknown]) => {
                    const exit = (typeof exitData === 'object' && exitData !== null ? exitData : {}) as ExitData;
                    const target = typeof exitData === 'object' ? (exit.target || exit.targetAreaName || exit.targetAreaId || '?') : exitData;
                    const wayId = typeof exitData === 'object' ? (exit.way_id || '') : '';
                    const hasWay = Boolean(wayId);
                    const clickHandler = wayId ? () => graphManager.showNodeAndFocus(wayId) : window.Lit.nothing;
                    if (exitNodes.length) exitNodes.push(treeViewHtmlTag`, `);
                    exitNodes.push(treeViewHtmlTag`
                        <span class="vtree-exit" title=${hasWay ? 'Inspect way' : window.Lit.nothing} style=${hasWay ? 'cursor:pointer;' : window.Lit.nothing} @click=${clickHandler}>${direction} → ${target}</span>`);
                });
                childFragments.push(treeViewHtmlTag`<div class="vtree-child"><span class="vtree-desc-icon">🚪</span>${exitNodes}</div>`);
            }

            if (items.length) childFragments.push(this._renderItems(items));

            if (here.length) {
                const playerNodes: unknown[] = [];
                here.forEach((playerName: string) => {
                    if (playerNodes.length) playerNodes.push(treeViewHtmlTag`, `);
                    playerNodes.push(treeViewHtmlTag`<span class="vtree-player" @click=${() => (window as unknown as TreeViewWindowSurface).selectAgent?.(playerName)}>${playerName}</span>`);
                });
                childFragments.push(treeViewHtmlTag`<div class="vtree-child"><span class="vtree-desc-icon">👤</span>${playerNodes}</div>`);
            }

            return treeViewHtmlTag`
                <div class="vtree-node">
                <div class="vtree-toggle" @click=${() => graphManager._toggleTree(uid)}>▶</div>
                <span class="vtree-label" @click=${() => graphManager._selectRoom(areaName)}>🏠 ${areaName}</span>
                <span class="vtree-badge">${temp} · ${light} lux · ${air}</span>
                <div id="${uid}" class="vtree-children" style="display:none">${childFragments}</div>
                </div>`;
        });

        window.Lit.render(treeViewHtmlTag`
            <div style="font-size:12px;font-weight:600;color:var(--text-dim);margin-bottom:8px;padding:8px 8px 0;">📍 ${rooms.length} areas${scopeNote} · 👤 ${players.length} characters <button class="btn btn-sm btn-ghost" @click=${() => treeViewApi.copyOutlineTree()} style="margin-left:8px;" title="Copy outline to clipboard">📋</button></div>
            <div class="vtree" style="padding:4px 8px;">${roomFragments}</div>`, container);

        // The scope hierarchy sits ABOVE this list (task-592), so the world reads
        // as one tree. It is re-placed and re-rendered here rather than once at
        // load because Lit has just replaced the container's children, and the
        // host is a sibling of that container — see `GraphScopeTree.mountInOutline`.
        if ((window as unknown as TreeViewWindowSurface).GraphScopeTree && typeof (window as unknown as TreeViewWindowSurface).GraphScopeTree.mountInOutline === 'function') {
            (window as unknown as TreeViewWindowSurface).GraphScopeTree.mountInOutline();
        }
    },

    /**
     * Copies the outline tree data as formatted plain text to the clipboard.
     */
    copyOutlineTree(): void {
        if (!worldState.data) return;
        const rooms = Object.keys(worldState.areas || {}).sort();
        const players = Object.entries(worldState.players || {}) as Array<[string, PlayerData]>;
        const playerRoomMap: Record<string, string[]> = {};
        players.forEach(([playerName, playerData]: [string, PlayerData]) => {
            const currentArea = playerData.current_area;
            if (currentArea) {
                if (!playerRoomMap[currentArea]) playerRoomMap[currentArea] = [];
                playerRoomMap[currentArea].push(playerName);
            }
        });
        const areaBlock = (areaName: string): string => {
            const area = (worldState.areas as Record<string, AreaData>)[areaName];
            const env = area.environment || {};
            const temp = treeViewFormatTemp(env.temperature);
            const light = env.light != null ? env.light : '?';
            const air = env.air || '?';
            let text = `   📍 ${areaName}  (${temp} · ${light} lux · ${air})\n`;
            if (area.description) text += `      ${area.description.replace(/\n/g, ' ')}\n`;
            const exits = Object.entries(area.exits || {});
            if (exits.length) text += `      🚪 ${exits.map(([direction, exitData]: [string, unknown]) => {
                const exit = (typeof exitData === 'object' && exitData !== null ? exitData : {}) as ExitData;
                const target = typeof exitData === 'object' ? (exit.target || exit.targetAreaName || exit.targetAreaId || '?') : exitData;
                return `${direction} → ${target}`;
            }).join(', ')}\n`;
            const items = worldState.getItemsInArea(areaName) as ItemSummary[];
            if (items.length) text += `      📦 ${items.map((itemData: ItemSummary) => itemData.name || itemData.id || '?').join(', ')}\n`;
            const here = playerRoomMap[areaName] || [];
            if (here.length) text += `      👤 ${here.join(', ')}\n`;
            return text;
        };

        // The **whole** hierarchy, not just the areas (task-592). Copying areas
        // alone silently drops the two levels above them, so a pasted outline of a
        // five-scope world would read as one flat room list with no indication of
        // which scope any of it was in.
        let text = `Virtual World — ${rooms.length} areas, ${players.length} characters\n\n`;
        const scopes = ((window as unknown as TreeViewWindowSurface).graphManager && (window as unknown as TreeViewWindowSurface).graphManager._scopeSummaries) || [];
        if (scopes.length && (window as unknown as TreeViewWindowSurface).GraphScopeTree) {
            const scopeTree = (window as unknown as TreeViewWindowSurface).GraphScopeTree;
            const tree = scopeTree.buildTree!(scopes);
            const rows = scopeTree.visibleRows!(tree, new Set<string>(), null);
            rows.forEach((row: ScopeRow) => {
                const pad = '  '.repeat(Math.max(0, row.depth));
                text += `${pad}🗺 ${row.name}`
            // task-615: same fix as GraphScopeTree.rowLabel -- "unmade" is a
            // materialisation state, not a statement about contents. Keying the
            // whole row off it rendered goblin_camp (state 'unmade', 21 areas,
            // 10 present) as "not built".
            + (row.unmade
                ? (row.areaCount || row.itemCount
                    ? ` — ${row.areaCount} area(s), ${row.itemCount} item(s), unmade`
                    : ' — not built')
                : ` — ${row.areaCount} area(s), ${row.itemCount} item(s)`)
                    + '\n';
            });
            text += '\n';
        }
        rooms.forEach((areaName: string) => { text += areaBlock(areaName) + '\n'; });
        navigator.clipboard.writeText(text).catch(() => {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
textarea.remove();
        });
    },
};
        return treeViewApi;
    })();

/* ── types ──
 * Declared at the BOTTOM deliberately. tsc drops a file's leading JSDoc when
 * the first statement is type-only, and tools/js_module_index.py reads
 * `@module` out of the EMITTED .js — so an `interface` above the first value
 * declaration would silently strip the module contract. */

/** An item row as worldState.getItemsInArea() returns it. */
interface ItemSummary {
    id?: string;
    name?: string;
    description?: string;
    properties?: { description?: string };
}

/** A player row as worldState.players holds it. */
interface PlayerData {
    current_area?: string;
}

/** The environment block on an area. */
interface AreaEnvironment {
    temperature?: number | string;
    light?: number | string;
    air?: string;
}

/** An area's exit entry; the value is either a target name or an object. */
interface ExitData {
    target?: string;
    targetAreaName?: string;
    targetAreaId?: string;
    way_id?: string;
}

/** An area row from worldState.areas. */
interface AreaData {
    description?: string;
    environment?: AreaEnvironment;
    exits?: Record<string, unknown>;
}

/** A scope row as GraphScopeTree projects it. */
interface TreeViewScopeSummary {
    id: string;
    name?: string;
}

/** One row of the flattened scope tree. */
interface ScopeRow {
    depth: number;
    name: string;
    areaCount?: number;
    itemCount?: number;
    unmade?: boolean;
}

/** The graphManager surface this module drives. */
interface GraphManagerLike {
    _scopeFilter?: string;
    _scopeSummaries?: TreeViewScopeSummary[];
    showNodeAndFocus?(id: string): void;
    _toggleDesc?(id: string): void;
    _toggleTree?(id: string): void;
    _selectRoom?(name: string): void;
}

/** The GraphTreeView surface published on window. */
interface GraphTreeViewApi {
    _renderItems(items: ItemSummary[]): unknown;
    renderOutlinePanel(container: HTMLElement): void;
    copyOutlineTree(): void;
}
