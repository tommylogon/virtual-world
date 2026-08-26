/**
 * GraphTooltips — rich hover tooltips for graph nodes and edges.
 *
 * Extracted from the network-manager monolith. Builds plain-text and HTML
 * tooltip content per node type and binds tippy instances to node DOM + a
 * manual-follow edge-hover tooltip. Reads the shared `graphManager` and
 * `worldState` globals lazily (resolved at call time), so load order against
 * graph-manager.js doesn't matter.
 *
 * @module GraphTooltips
 */
window.GraphTooltips = {

    /**
     * Builds a plain-text tooltip string for a graph node.
     * Shows different information depending on node type (area, item, way, character).
     *
     * @param {Object} nodeData - The node data object
     * @returns {string} Tooltip text
     */
    buildTooltip(nodeData) {
        // vis-network UMD doesn't support HTML in tooltips — use plain text
        let tip = nodeData.name || nodeData.id;
        const player = worldState.players?.[nodeData.name];
        if (nodeData.type === 'character' && player) {
            const vitals = player.vitals || {};
            const area = player.current_area || '?';
            const hpPct = vitals.HP && vitals.Max_HP ? Math.round((vitals.HP / vitals.Max_HP) * 100) : '?';
            tip += `\n📍 ${area}\n❤️ HP ${vitals.HP||'?'} (${hpPct}%)\n⚡ Energy ${vitals.Energy||'?'}`;
        } else if (nodeData.type === 'area') {
            const area = worldState.areas?.[nodeData.name];
            if (area) {
                const items = area.items?.length || 0;
                const playersHere = Object.entries(worldState.players || {}).filter(([, playerData]) => playerData.current_area === nodeData.name).map(([playerName]) => playerName);
                tip += `\n📦 ${items} items\n🧍 ${playersHere.join(', ') || 'no one here'}`;
            }
            const areaTags = nodeData.properties?.tags || [];
            if (areaTags.length > 0) tip += `\n🏷️ ${areaTags.join(', ')}`;
        } else if (nodeData.type === 'item') {
            const props = nodeData.properties || {};
            const desc = (props.description || '');
            tip += `\n📦 ${desc || 'Item'}`;
            const itemState = props.current_state || 'normal';
            tip += `\n📌 ${itemState}`;
            const tags = props.tags || [];
            if (tags.length > 0) tip += `\n🏷️ ${tags.join(', ')}`;
        } else if (nodeData.type === 'character') {
            const charTags = nodeData.properties?.tags || [];
            if (charTags.length > 0) tip += `\n🏷️ ${charTags.join(', ')}`;
        } else if (nodeData.type === 'way') {
            tip += `\n🚪 ${nodeData.properties?.current_state || '?'}`;
            if (nodeData.properties?.one_way) tip += '\n➡️ One-way (blue border)';
            if (typeof WayAuthoring !== 'undefined') {
                const pair = WayAuthoring.getWayAreaPair(nodeData.id);
                if (pair.from || pair.to) tip += `\n📍 ${pair.from || '?'} ↔ ${pair.to || '?'}`;
                const tags = nodeData.properties?.tags || [];
                if (tags.length) tip += `\n🏷️ ${tags.join(', ')}`;
            }
        }
        if (typeof NodeBadges !== 'undefined' && nodeData.type !== 'logic_trigger') {
            const traitLines = NodeBadges.traitTooltipLines(nodeData);
            if (traitLines.length) tip += `\n${traitLines.join('\n')}`;
        }
        if (nodeData.properties?.central_gravity_enabled === false) {
            tip += '\nGraph gravity disabled (position locked)';
        }
        return tip;
    },

    _escHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    },

    buildTooltipHtml(nodeData) {
        const props = nodeData.properties || {};
        const esc = GraphTooltips._escHtml;
        let html = '<div style="font-size:11px;min-width:180px;">';
        html += '<div style="font-weight:600;margin-bottom:4px;color:var(--accent);">' + esc(nodeData.name || nodeData.id) + '</div>';
        html += '<div style="color:var(--text-dim);font-size:9px;margin-bottom:6px;">ID: ' + esc(nodeData.id) + ' · Type: ' + esc(nodeData.type) + '</div>';

        if (nodeData.type === 'area') {
            const area = worldState.areas?.[nodeData.name];
            if (area) {
                const items = area.items?.length || 0;
                const playersHere = Object.entries(worldState.players || {}).filter(([, pd]) => pd.current_area === nodeData.name).map(([pn]) => pn);
                html += '<div style="margin:2px 0;">📦 Items: ' + items + '</div>';
                html += '<div style="margin:2px 0;">🧍 Here: ' + (playersHere.join(', ') || 'none') + '</div>';
            }
            const areaTags = props.tags || [];
            if (areaTags.length > 0) html += '<div style="margin:2px 0;">🏷️ ' + esc(areaTags.join(', ')) + '</div>';
        } else if (nodeData.type === 'item') {
            const desc = props.description || '';
            if (desc) html += '<div style="margin:2px 0;color:var(--text-muted);">' + esc(desc.substring(0, 80)) + (desc.length > 80 ? '...' : '') + '</div>';
            html += '<div style="margin:2px 0;">📌 State: ' + esc(props.current_state || 'normal') + '</div>';
            const tags = props.tags || [];
            if (tags.length > 0) html += '<div style="margin:2px 0;">🏷️ ' + esc(tags.join(', ')) + '</div>';
        } else if (nodeData.type === 'way') {
            html += '<div style="margin:2px 0;">🚪 State: ' + esc(props.current_state || '?') + '</div>';
            if (props.one_way) html += '<div style="margin:2px 0;">➡️ One-way (blue border)</div>';
            if (typeof WayAuthoring !== 'undefined') {
                html = WayAuthoring.enhanceWayNodeTooltip(nodeData, html);
            }
        } else if (nodeData.type === 'character') {
            const player = worldState.players?.[nodeData.name];
            if (player) {
                const vitals = player.vitals || {};
                const hpPct = vitals.HP && vitals.Max_HP ? Math.round((vitals.HP / vitals.Max_HP) * 100) : '?';
                html += '<div style="margin:2px 0;">❤️ HP: ' + (vitals.HP || '?') + ' (' + hpPct + '%)</div>';
                html += '<div style="margin:2px 0;">⚡ Energy: ' + (vitals.Energy || '?') + '</div>';
                html += '<div style="margin:2px 0;">📍 ' + esc(player.current_area || '?') + '</div>';
            }
            const charTags = props.tags || [];
            if (charTags.length > 0) html += '<div style="margin:2px 0;">🏷️ ' + esc(charTags.join(', ')) + '</div>';
        } else if (nodeData.type === 'logic_trigger') {
            const tType = props.trigger_type || props.trigger_types || '?';
            html += '<div style="margin:2px 0;">⚡ Type: ' + esc(Array.isArray(tType) ? tType.join('+') : tType) + '</div>';
            const effects = props.effects || [];
            if (effects.length > 0) {
                html += '<div style="margin:2px 0;color:var(--text-muted);">Effects:</div>';
                effects.slice(0, 3).forEach((eff, i) => {
                    const effType = esc(eff.type || '?');
                    const msg = (eff.params?.success_message || eff.params?.message || '');
                    html += '<div style="margin:1px 0 1px 8px;font-size:10px;">• ' + effType + (msg ? ': ' + esc(msg.substring(0, 60)) + (msg.length > 60 ? '...' : '') : '') + '</div>';
                });
                if (effects.length > 3) html += '<div style="font-size:9px;color:var(--text-dim);">+' + (effects.length - 3) + ' more</div>';
            }
            const conditions = props.conditions || [];
            if (conditions.length > 0) {
                html += '<div style="margin:2px 0;color:var(--text-muted);">Conditions: ' + conditions.length + '</div>';
            }
        }
        if (nodeData.type !== 'logic_trigger' && typeof NodeBadges !== 'undefined') {
            NodeBadges.traitTooltipLines(nodeData).forEach(line => {
                html += '<div style="margin:2px 0;">' + esc(line) + '</div>';
            });
        }
        html += '</div>';
        return html;
    },

    /** Find a raw graph edge between two node ids (case-insensitive). */
    findGraphEdge(fromId, toId) {
        const edgesArr = graphManager._graphEdgesArr || worldState.graph?.edges || [];
        return edgesArr.find(e =>
            String(e.source).toLowerCase() === String(fromId).toLowerCase()
            && String(e.target).toLowerCase() === String(toId).toLowerCase()
        ) || null;
    },

    /** Bind the hover-follow edge tooltip (tippy) once. */
    bindEdgeHoverTooltips() {
        if (!graphManager.network || graphManager._edgeHoverBound) return;
        graphManager._edgeHoverBound = true;

        graphManager.network.on('hoverEdge', (params) => {
            if (typeof tippy === 'undefined') return;
            const visEdge = graphManager.network.body?.data?.edges?.get(params.edge);
            if (!visEdge) return;
            const html = graphManager._edgeTooltipHtml?.[`${visEdge.from}|${visEdge.to}`];
            if (!html) return;

            if (graphManager._edgeHoverTippy) {
                graphManager._edgeHoverTippy.destroy();
                graphManager._edgeHoverTippy = null;
            }

            const event = params.event;
            try {
                graphManager._edgeHoverTippy = tippy(document.createElement('div'), {
                    content: html,
                    allowHTML: true,
                    placement: 'top',
                    arrow: true,
                    animation: 'shift-away',
                    duration: [150, 100],
                    maxWidth: 300,
                    theme: 'light-border',
                    trigger: 'manual',
                    showOnCreate: true,
                    appendTo: () => document.body,
                    getReferenceClientRect: () => ({
                        width: 0,
                        height: 0,
                        top: event.clientY,
                        bottom: event.clientY,
                        left: event.clientX,
                        right: event.clientX,
                    }),
                });
                graphManager._edgeHoverTippy.popper.setAttribute('data-graph-tooltip', '1');
            } catch (e) { /* ignore */ }
        });

        graphManager.network.on('blurEdge', () => {
            if (graphManager._edgeHoverTippy) {
                graphManager._edgeHoverTippy.destroy();
                graphManager._edgeHoverTippy = null;
            }
        });
    },

    /** Attach per-node tippy tooltips (destroying any prior ones first). */
    attachNodeTooltips() {
        if (typeof tippy === 'undefined') return;
        if (!graphManager.network) return;

        const existing = document.querySelectorAll('.tippy-box[data-graph-tooltip]');
        existing.forEach(el => { const inst = tippy.getInstance(el); if (inst) inst.destroy(); });

        if (graphManager.network.body && graphManager.network.body.nodes) {
            Object.entries(graphManager.network.body.nodes).forEach(([nodeId, nodeObj]) => {
                const dom = nodeObj && nodeObj.dom;
                if (!dom) return;
                const nodeData = graphManager.nodes.get(nodeId);
                if (!nodeData) return;
                const html = GraphTooltips.buildTooltipHtml(nodeData);
                if (!html) return;
                try {
                    tippy(dom, {
                        content: html,
                        allowHTML: true,
                        placement: 'top',
                        arrow: true,
                        animation: 'shift-away',
                        duration: [200, 150],
                        maxWidth: 300,
                        delay: [200, 0],
                        theme: 'light-border',
                        onCreate(instance) {
                            instance.popper.setAttribute('data-graph-tooltip', '1');
                        }
                    });
                } catch (e) { /* ignore */ }
            });
        }
    }
};