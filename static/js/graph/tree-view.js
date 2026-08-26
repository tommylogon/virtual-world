/**
 * GraphTreeView — world outline tree for the left panel
 * Provides an interactive tree/outline inspector for rooms, exits, items, and players.
 * Clicking an area, item, way, or player moves the camera to that node and opens
 * the inspector. References the global graphManager singleton.
 *
 * @module GraphTreeView
 */
// Lazy lit-html tag: window.Lit is only available at call time (deferred module
// bootstrap), not at parse time. Unique per file so top-level consts never collide.
const treeViewHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.GraphTreeView = {
    /**
     * Build clickable item spans for a room. Clicking an item focuses the
     * camera on it and opens the item inspector. Items come from
     * worldState.getItemsInArea() (direct + spatial + container contents),
     * each with a graph node id.
     */
    _renderItems(items) {
        if (!items || !items.length) return window.Lit.nothing;
        const spanNodes = [];
        items.forEach(itemData => {
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
    renderOutlinePanel(container) {
        if (!container || !worldState.data) return;
        const rooms = Object.keys(worldState.areas || {}).sort();
        const players = Object.entries(worldState.players || {});
        const playerRoomMap = {};
        players.forEach(([playerName, playerData]) => {
            const currentArea = playerData.current_area;
            if (currentArea) {
                if (!playerRoomMap[currentArea]) playerRoomMap[currentArea] = [];
                playerRoomMap[currentArea].push(playerName);
            }
        });
        const roomFragments = rooms.map((areaName, roomIndex) => {
            const area = worldState.areas[areaName];
            const env = area.environment || {};
            const temp = env.temperature != null ? `${env.temperature}°C` : '?';
            const light = env.light != null ? env.light : '?';
            const air = env.air || '?';
            const desc = area.description || '';
            const descShort = desc.length > 120 ? desc + '...' : desc;
            const exits = Object.entries(area.exits || {});
            const items = worldState.getItemsInArea(areaName);
            const here = playerRoomMap[areaName] || [];
            const uid = `ovt-${roomIndex}`;

            const childFragments = [];

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
                const exitNodes = [];
                exits.forEach(([direction, exitData]) => {
                    const target = typeof exitData === 'object' ? (exitData.target || exitData.targetAreaName || exitData.targetAreaId || '?') : exitData;
                    const wayId = typeof exitData === 'object' ? (exitData.way_id || '') : '';
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
                const playerNodes = [];
                here.forEach(playerName => {
                    if (playerNodes.length) playerNodes.push(treeViewHtmlTag`, `);
                    playerNodes.push(treeViewHtmlTag`<span class="vtree-player" @click=${() => selectAgent(playerName)}>${playerName}</span>`);
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
            <div style="font-size:12px;font-weight:600;color:var(--text-dim);margin-bottom:8px;padding:8px 8px 0;">🏠 ${rooms.length} rooms · 👤 ${players.length} characters <button class="btn btn-sm btn-ghost" @click=${() => GraphTreeView.copyOutlineTree()} style="margin-left:8px;" title="Copy outline to clipboard">📋</button></div>
            <div class="vtree" style="padding:4px 8px;">${roomFragments}</div>`, container);
    },

    /**
     * Copies the outline tree data as formatted plain text to the clipboard.
     */
    copyOutlineTree() {
        if (!worldState.data) return;
        const rooms = Object.keys(worldState.areas || {}).sort();
        const players = Object.entries(worldState.players || {});
        const playerRoomMap = {};
        players.forEach(([playerName, playerData]) => {
            const currentArea = playerData.current_area;
            if (currentArea) {
                if (!playerRoomMap[currentArea]) playerRoomMap[currentArea] = [];
                playerRoomMap[currentArea].push(playerName);
            }
        });
        let text = `Virtual World — ${rooms.length} rooms, ${players.length} characters\n\n`;
        rooms.forEach(areaName => {
            const area = worldState.areas[areaName];
            const env = area.environment || {};
            const temp = env.temperature != null ? env.temperature + '°C' : '?';
            const light = env.light != null ? env.light : '?';
            const air = env.air || '?';
            text += `📍 ${areaName}  (${temp} · ${light} lux · ${air})\n`;
            if (area.description) text += `   ${area.description.replace(/\n/g, ' ')}\n`;
            const exits = Object.entries(area.exits || {});
            if (exits.length) text += `   🚪 ${exits.map(([direction, exitData]) => {
                const target = typeof exitData === 'object' ? (exitData.target || exitData.targetAreaName || exitData.targetAreaId || '?') : exitData;
                return `${direction} → ${target}`;
            }).join(', ')}\n`;
            const items = worldState.getItemsInArea(areaName);
            if (items.length) text += `   📦 ${items.map(itemData => itemData.name || itemData.id || '?').join(', ')}\n`;
            const here = playerRoomMap[areaName] || [];
            if (here.length) text += `   👤 ${here.join(', ')}\n`;
            text += '\n';
        });
        navigator.clipboard.writeText(text).catch(() => {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            textarea.remove();
        });
    }
};
