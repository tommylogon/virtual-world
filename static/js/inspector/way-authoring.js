/**
 * WayAuthoring — shared helpers for way inspector, area exits, graph tooltips, agent lens.
 */
window.WayAuthoring = (() => {
    const WA = {};

    const esc = (s) => (typeof InspectorHelpers !== 'undefined' ? InspectorHelpers.esc(s) : String(s || ''));

    WA.STATE_STYLE = {
        open: { icon: '🟢', color: 'var(--green)', label: 'open' },
        closed: { icon: '🟡', color: 'var(--yellow)', label: 'closed' },
        locked: { icon: '🔴', color: 'var(--red)', label: 'locked' },
        hidden: { icon: '⚫', color: 'var(--text-muted)', label: 'hidden' },
        blocked: { icon: '⛔', color: 'var(--orange)', label: 'blocked' },
        broken: { icon: '💥', color: 'var(--orange)', label: 'broken' },
    };

    WA.REQUIRES_LABEL = {
        crawl: { emoji: '🐛', label: 'crawl', hint: 'go auto-crawls' },
        climb: { emoji: '🧗', label: 'climb', hint: 'climb <dir>' },
        jump: { emoji: '🦘', label: 'jump', hint: 'jump <dir>' },
    };

    /** @returns {{ areaId, areaName, command, viewWhenOpen, cardinal, targetAreaName, edge }[]} */
    WA.getWaySides = function(wayId) {
        const edges = worldState.graph?.edges || [];
        const nodes = worldState.graph?.nodes || {};
        const wayLower = String(wayId).toLowerCase();
        const sides = [];

        edges.filter(e => e.type === 'connection' && String(e.target).toLowerCase() === wayLower)
            .forEach(edge => {
                const areaNode = nodes[edge.source];
                if (!areaNode || areaNode.type !== 'area') return;
                const areaName = areaNode.name || edge.source;
                const returnEdge = edges.find(e =>
                    e.type === 'connection'
                    && String(e.source).toLowerCase() === wayLower
                    && String(e.target).toLowerCase() === String(edge.source).toLowerCase()
                );
                let targetAreaName = '?';
                const otherAreaEdge = edges.find(e =>
                    e.type === 'connection'
                    && String(e.target).toLowerCase() === wayLower
                    && String(e.source).toLowerCase() !== String(edge.source).toLowerCase()
                );
                if (otherAreaEdge) {
                    const otherNode = nodes[otherAreaEdge.source];
                    targetAreaName = otherNode?.name || otherAreaEdge.source;
                }
                sides.push({
                    areaId: edge.source,
                    areaName,
                    command: edge.properties?.direction || '',
                    viewWhenOpen: edge.properties?.visible_in_direction || '',
                    cardinal: edge.properties?.cardinal || '',
                    allowSeeCharacters: !!edge.properties?.allow_see_characters,
                    visibleItems: edge.properties?.visible_items || [],
                    targetAreaName,
                    edge,
                    returnEdge,
                });
            });
        return sides.sort((a, b) => a.areaName.localeCompare(b.areaName));
    };

    WA.getWayAreaPair = function(wayId) {
        const sides = WA.getWaySides(wayId);
        return {
            from: sides[0]?.areaName || null,
            to: sides[1]?.areaName || sides[0]?.targetAreaName || null,
            sides,
        };
    };

    WA.movementHint = function(wayNode, command) {
        if (!wayNode) return '';
        const req = (wayNode.properties?.requires || '').toLowerCase();
        if (!req || req === 'none') return '';
        const meta = WA.REQUIRES_LABEL[req];
        if (!meta) return '';
        const cmd = command || '<dir>';
        if (req === 'crawl') return ` (${meta.label}: go ${cmd} auto-crawls)`;
        return ` (${meta.label}: ${meta.hint.replace('<dir>', cmd)})`;
    };

    WA.collectExitBadges = function(exitData, wayNode) {
        const badges = [];
        const wayId = exitData?.way_id || wayNode?.id || '';
        const state = exitData?.state || wayNode?.properties?.current_state || 'closed';
        const stateStyle = WA.STATE_STYLE[state] || { icon: '❓', color: 'var(--text-muted)', label: state };

        badges.push({
            kind: 'state',
            emoji: stateStyle.icon,
            title: `Way state: ${stateStyle.label}`,
            wayId,
        });

        if (wayNode) {
            const req = (wayNode.properties?.requires || '').toLowerCase();
            if (WA.REQUIRES_LABEL[req]) {
                const meta = WA.REQUIRES_LABEL[req];
                badges.push({
                    kind: 'movement',
                    emoji: meta.emoji,
                    title: `Requires ${meta.label} (${meta.hint})`,
                    wayId,
                });
            }
            const tags = (wayNode.properties?.tags || []).slice(0, 2);
            tags.forEach(tag => {
                badges.push({
                    kind: 'tag',
                    emoji: '🏷',
                    title: `Tag: ${tag}`,
                    label: tag,
                    wayId,
                });
            });
            const params = wayNode.properties?.parameters || {};
            const rawDesc = exitData?.description || wayNode.properties?.description || '';
            if (/\{param:/.test(rawDesc)) {
                const resolved = InspectorHelpers.resolveWayParams(rawDesc, params);
                const unresolved = InspectorHelpers.unresolvedParamKeys(rawDesc, params);
                badges.push({
                    kind: 'param',
                    emoji: unresolved.length ? '⚠' : '📝',
                    title: unresolved.length
                        ? `Unresolved params: ${unresolved.join(', ')}`
                        : `Resolved: ${resolved.substring(0, 80)}${resolved.length > 80 ? '…' : ''}`,
                    preview: resolved,
                    wayId,
                });
            }
        }
        return badges;
    };

    WA.renderBadgeRow = function(badges, wayId) {
        const extra = badges.filter(b => b.kind !== 'state');
        if (!extra.length) return '';
        const escWay = esc(wayId).replace(/'/g, "\\'");
        return `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;align-items:center;">
            <span style="font-size:9px;color:var(--text-muted);">Also:</span>
            ${extra.map(b => {
                let label = b.emoji;
                if (b.kind === 'tag') label += ` ${esc(b.label)}`;
                else if (b.kind === 'movement') label += ` ${esc(b.title.replace(/^Requires /, ''))}`;
                else if (b.kind === 'param') label += ' param preview';
                const title = esc(b.title);
                return `<button type="button" class="btn btn-sm btn-ghost way-exit-badge"
                    title="${title} — click to open way inspector"
                    style="font-size:10px;padding:1px 6px;line-height:1.4;cursor:pointer;"
                    onclick="VW.inspector.showNode('${escWay}')">${label}</button>`;
            }).join('')}
        </div>`;
    };

    WA.tagSanityWarnings = function(wayNode) {
        if (!wayNode) return [];
        const props = wayNode.properties || {};
        const warnings = [];
        const req = (props.requires || '').toLowerCase();
        const tags = (props.tags || []).map(t => String(t).toLowerCase());
        const state = props.current_state || 'closed';

        if (req === 'jump' && tags.includes('clearance')) {
            warnings.push('clearance tag on a jump passage — usually belongs on a door, not a jump pit');
        }
        if (req === 'climb' && tags.includes('clearance')) {
            warnings.push('clearance tag on a climb passage — double-check this is intentional');
        }
        if (state === 'locked' && !tags.length) {
            const triggerEdges = (worldState.graph?.edges || []).filter(e =>
                e.type === 'triggers' && (e.source === wayNode.id || e.target === wayNode.id)
            );
            if (!triggerEdges.length && !(props.triggers || []).length) {
                warnings.push('locked way has no tags and no visible unlock trigger (heuristic)');
            }
        }
        const desc = props.description || '';
        const missing = InspectorHelpers.unresolvedParamKeys(desc, props.parameters || {});
        if (missing.length) {
            warnings.push(`description references missing parameters: ${missing.join(', ')}`);
        }
        return warnings;
    };

    WA.renderSanityWarnings = function(wayNode) {
        const warnings = WA.tagSanityWarnings(wayNode);
        if (!warnings.length) return '';
        return `<div class="way-sanity-warnings" style="margin-top:6px;padding:6px 8px;background:#3a2a1022;border:1px solid var(--orange);border-radius:4px;font-size:10px;color:var(--orange);">
            ${warnings.map(w => `<div>⚠ ${esc(w)}</div>`).join('')}
        </div>`;
    };

    WA._findNode = function(nodesObj, id) {
        if (!nodesObj || !id) return null;
        if (nodesObj[id]) return nodesObj[id];
        const key = Object.keys(nodesObj).find(k => k.toLowerCase() === String(id).toLowerCase());
        return key ? nodesObj[key] : null;
    };

    WA._findEdge = function(edgesArr, source, target, type = 'connection') {
        return (edgesArr || []).find(e => e.type === type
            && String(e.source).toLowerCase() === String(source).toLowerCase()
            && String(e.target).toLowerCase() === String(target).toLowerCase());
    };

    /**
     * Tooltip for a single collapsed vis edge (area↔way shows one bidirectional line;
     * command/view come from the area→way edge for the area on this link).
     */
    WA.buildEdgeTooltipForVis = function(fromId, toId, nodesObj, edgesArr) {
        const fromNode = WA._findNode(nodesObj, fromId);
        const toNode = WA._findNode(nodesObj, toId);
        if (!fromNode || !toNode) return null;

        let areaNode, wayNode, areaId, wayId;
        if (fromNode.type === 'area' && toNode.type === 'way') {
            areaNode = fromNode; wayNode = toNode; areaId = fromId; wayId = toId;
        } else if (fromNode.type === 'way' && toNode.type === 'area') {
            areaNode = toNode; wayNode = fromNode; areaId = toId; wayId = fromId;
        } else {
            return null;
        }

        const areaToWay = WA._findEdge(edgesArr, areaId, wayId);
        const wayToArea = WA._findEdge(edgesArr, wayId, areaId);
        const props = wayNode.properties || {};
        const areaName = areaNode.name || areaId;
        const wayName = wayNode.name || wayId;

        let targetAreaName = '?';
        (edgesArr || []).forEach(e => {
            if (e.type !== 'connection') return;
            if (String(e.target).toLowerCase() !== String(wayId).toLowerCase()) return;
            if (String(e.source).toLowerCase() === String(areaId).toLowerCase()) return;
            const other = WA._findNode(nodesObj, e.source);
            if (other?.type === 'area') targetAreaName = other.name || e.source;
        });

        const command = areaToWay?.properties?.direction || wayToArea?.properties?.direction || '?';
        const view = areaToWay?.properties?.visible_in_direction || '';
        const state = props.current_state || 'closed';
        const req = (props.requires || '').toLowerCase();
        const reqMeta = WA.REQUIRES_LABEL[req];
        const movement = reqMeta ? `${reqMeta.label} (${reqMeta.hint})` : 'go (default)';
        const tags = (props.tags || []).join(', ') || '—';
        const viewSnippet = view ? (view.length > 80 ? view.substring(0, 80) + '…' : view) : '—';

        const plain = [
            `🔗 ${areaName} ↔ ${wayName}`,
            `Command (from ${areaName}): go "${command}" → ${targetAreaName}`,
            `Way state: ${state}`,
            `Movement: ${movement}`,
            `Tags: ${tags}`,
            `View when open: "${viewSnippet}"`,
        ].join('\n');

        let html = '<div style="font-size:10px;min-width:200px;line-height:1.45;">';
        html += `<div style="font-weight:600;margin-bottom:4px;">🔗 ${esc(areaName)} ↔ ${esc(wayName)}</div>`;
        html += `<div style="font-size:9px;color:var(--text-muted);margin-bottom:4px;">One graph edge — area→way + return path collapsed</div>`;
        html += `<div><span style="color:var(--text-dim);">Command (from ${esc(areaName)}):</span> go "${esc(command)}" → ${esc(targetAreaName)}</div>`;
        html += `<div><span style="color:var(--text-dim);">Way state:</span> ${esc(state)}</div>`;
        html += `<div><span style="color:var(--text-dim);">Movement:</span> ${esc(movement)}</div>`;
        html += `<div><span style="color:var(--text-dim);">Tags:</span> ${esc(tags)}</div>`;
        html += `<div style="margin-top:4px;color:var(--text-muted);"><span style="color:var(--text-dim);">View when open:</span> "${esc(viewSnippet)}"</div>`;
        html += '</div>';
        return { html, plain };
    };

    /** @deprecated use buildEdgeTooltipForVis */
    WA.buildConnectionEdgeTooltip = function(edgeData) {
        const nodesObj = graphManager?._graphNodesObj || worldState.graph?.nodes || {};
        const edgesArr = graphManager?._graphEdgesArr || worldState.graph?.edges || [];
        if (!edgeData) return null;
        const tip = WA.buildEdgeTooltipForVis(edgeData.source, edgeData.target, nodesObj, edgesArr);
        return tip?.html || null;
    };

    WA.enhanceWayNodeTooltip = function(nodeData, baseHtml) {
        const pair = WA.getWayAreaPair(nodeData.id);
        let extra = '';
        if (pair.from || pair.to) {
            extra += `<div style="margin:2px 0;">📍 ${esc(pair.from || '?')} ↔ ${esc(pair.to || '?')}</div>`;
        }
        const tags = nodeData.properties?.tags || [];
        if (tags.length) {
            extra += `<div style="margin:2px 0;">🏷️ ${esc(tags.join(', '))}</div>`;
        }
        if (!extra) return baseHtml;
        const insertAt = baseHtml.lastIndexOf('</div>');
        if (insertAt === -1) return baseHtml + extra;
        return baseHtml.slice(0, insertAt) + extra + baseHtml.slice(insertAt);
    };

    return WA;
})();
