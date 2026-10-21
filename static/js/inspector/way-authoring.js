"use strict";
/**
 * WayAuthoring  -  shared helpers for way inspector, area exits, graph tooltips, agent lens.
 *
 * @module inspector/way-authoring  -  shared way/door authoring helpers
 * @contributes WayAuthoring: way naming, state, cardinal/direction helpers, vis edge tooltips
 * @powers Way authoring  -  consistent way editing across the way inspector, area exits, graph tooltips, and agent lens
 * @relates used by way-view + area-view + graph/network-manager (edge tooltips)
 * @docs docs/virtualWorld/World Building/Ways.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const WayAuthoringModule = (() => {
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
    WA.getWaySides = function (wayId) {
        const edges = worldState.graph?.edges || [];
        const nodes = worldState.graph?.nodes || {};
        const wayLower = String(wayId).toLowerCase();
        const sides = [];
        edges.filter((e) => e.type === 'connection' && String(e.target).toLowerCase() === wayLower)
            .forEach((edge) => {
            const areaNode = nodes[edge.source];
            if (!areaNode || areaNode.type !== 'area')
                return;
            const areaName = areaNode.name || edge.source;
            const returnEdge = edges.find((e) => e.type === 'connection'
                && String(e.source).toLowerCase() === wayLower
                && String(e.target).toLowerCase() === String(edge.source).toLowerCase());
            let targetAreaName = '?';
            const otherAreaEdge = edges.find((e) => e.type === 'connection'
                && String(e.target).toLowerCase() === wayLower
                && String(e.source).toLowerCase() !== String(edge.source).toLowerCase());
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
    WA.getWayAreaPair = function (wayId) {
        const sides = WA.getWaySides(wayId);
        return {
            from: sides[0]?.areaName || null,
            to: sides[1]?.areaName || sides[0]?.targetAreaName || null,
            sides,
        };
    };
    /**
     * The one place a cardinal becomes a glyph.
     *
     * Two surfaces show a way's cardinal - the area inspector's exit badge and
     * the graph's Cardinal overlay - and they used to disagree: the overlay
     * drew `⬆N`, the badge drew a generic compass plus the raw word. One map,
     * one answer.
     *
     * The vertical pair is deliberately distinct from the horizontal one:
     * `up`/`down` are not on the rotation ring (a character who climbs a ladder
     * does not end up facing north), so they get their own arrows rather than
     * borrowing the north/south ones.
     */
    WA.CARDINAL_ICON = {
        north: '⬆N', south: '⬇S', east: '➡E', west: '⬅W',
        northeast: '⬈NE', northwest: '⬉NW', southeast: '⬊SE', southwest: '⬋SW',
        up: '⤒U', down: '⤓D',
        // A scope gateway is authored with 'in' / 'out' rather than a heading
        // (engine/world_compile.py writes cardinal "in" on the way in and "out"
        // on the way back), and a few ways spell the vertical pair as
        // 'upstream' / 'downstream'. They are cardinals in the data, so they
        // get glyphs rather than falling through to the raw word.
        in: '↘IN', out: '↗OUT',
        upstream: '⤒U', downstream: '⤓D',
    };
    /**
     * The glyph for a cardinal.
     *
     * @param cardinal the cardinal word, in any case
     * @returns the glyph, or the word itself when it is not a known cardinal
     *   (an authored value the map does not know still shows what it says
     *   rather than being hidden), or '' when there is no cardinal at all.
     */
    WA.cardinalIcon = function (cardinal) {
        const word = String(cardinal ?? '').trim();
        if (!word)
            return '';
        return WA.CARDINAL_ICON[word.toLowerCase()] || word;
    };
    /**
     * The cardinal of a way, read from where it actually lives.
     *
     * A way's cardinal is a property of its *connection edge* (the
     * area-to-way edge), not of the way node: 5030 edges carry one in the
     * Kraktooth camp and 0 way nodes do. So a caller that looks at
     * `node.properties.cardinal` finds nothing and renders a placeholder.
     *
     * When the edge has no `cardinal`, the edge's `direction` is used if it is
     * itself a heading. That fallback is the engine's, not a convenience:
     * `engine/facing.py`'s `edge_cardinal()` reads `cardinal` first and falls
     * back to `direction`, and the map layout does the same
     * (`graph/layout-engine.ts`). A prose direction ("downward tunnel") is not
     * a heading, so it is left off - a way with no cardinal keeps its "?", which
     * is the honest answer and is what the World Issues validator's
     * `way_missing_cardinal` check reports.
     *
     * @param wayId the way node id
     * @returns the way's cardinal, or '' when it has none.
     */
    WA.wayCardinal = function (wayId) {
        const edges = worldState.graph?.edges || [];
        const wayLower = String(wayId).toLowerCase();
        let fallback = '';
        for (const edge of edges) {
            if (edge.type !== 'connection')
                continue;
            if (String(edge.target).toLowerCase() !== wayLower)
                continue;
            const cardinal = String(edge.properties?.cardinal || '').trim();
            if (cardinal)
                return cardinal;
            if (!fallback) {
                const direction = String(edge.properties?.direction || '').trim().toLowerCase();
                if (WA.CARDINAL_ICON[direction])
                    fallback = direction;
            }
        }
        return fallback;
    };
    WA.movementHint = function (wayNode, command) {
        if (!wayNode)
            return '';
        const req = String(wayNode.properties?.requires || '').toLowerCase();
        if (!req || req === 'none')
            return '';
        const meta = WA.REQUIRES_LABEL[req];
        if (!meta)
            return '';
        const cmd = command || '<dir>';
        if (req === 'crawl')
            return ` (${meta.label}: go ${cmd} auto-crawls)`;
        return ` (${meta.label}: ${meta.hint.replace('<dir>', cmd)})`;
    };
    WA.collectExitBadges = function (exitData, wayNode) {
        const badges = [];
        const wayId = String(exitData?.way_id || wayNode?.id || '');
        const state = String(wayNode?.properties?.current_state || exitData?.state || 'closed');
        const stateStyle = WA.STATE_STYLE[state] || { icon: '❓', color: 'var(--text-muted)', label: state };
        badges.push({
            kind: 'state',
            emoji: stateStyle.icon,
            title: `Way state: ${stateStyle.label}`,
            wayId,
        });
        if (wayNode) {
            const req = String(wayNode.properties?.requires || '').toLowerCase();
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
            tags.forEach((tag) => {
                badges.push({
                    kind: 'tag',
                    emoji: '🏷',
                    title: `Tag: ${tag}`,
                    label: tag,
                    wayId,
                });
            });
            const params = wayNode.properties?.parameters || {};
            const rawDesc = String(exitData?.description || wayNode.properties?.description || '');
            if (/\{param:/.test(rawDesc)) {
                const resolved = String(InspectorHelpers.resolveWayParams(rawDesc, params));
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
    WA.renderBadgeRow = function (badges, wayId) {
        const extra = badges.filter((b) => b.kind !== 'state');
        if (!extra.length)
            return '';
        const escWay = esc(wayId).replace(/'/g, "\\'");
        return `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;align-items:center;">
            <span style="font-size:9px;color:var(--text-muted);">Also:</span>
            ${extra.map((b) => {
            let label = b.emoji;
            if (b.kind === 'tag')
                label += ` ${esc(b.label)}`;
            else if (b.kind === 'movement')
                label += ` ${esc(b.title.replace(/^Requires /, ''))}`;
            else if (b.kind === 'param')
                label += ' param preview';
            const title = esc(b.title);
            return `<button type="button" class="btn btn-sm btn-ghost way-exit-badge"
                    title="${title}  -  click to open way inspector"
                    style="font-size:10px;padding:1px 6px;line-height:1.4;cursor:pointer;"
                    onclick="VW.inspector.showNode('${escWay}')">${label}</button>`;
        }).join('')}
        </div>`;
    };
    WA.tagSanityWarnings = function (wayNode) {
        if (!wayNode)
            return [];
        const props = wayNode.properties || {};
        const warnings = [];
        const req = String(props.requires || '').toLowerCase();
        const tags = (props.tags || []).map((t) => String(t).toLowerCase());
        const state = String(props.current_state || 'closed');
        if (req === 'jump' && tags.includes('clearance')) {
            warnings.push('clearance tag on a jump passage  -  usually belongs on a door, not a jump pit');
        }
        if (req === 'climb' && tags.includes('clearance')) {
            warnings.push('clearance tag on a climb passage  -  double-check this is intentional');
        }
        if (state === 'locked' && !tags.length) {
            const triggerEdges = (worldState.graph?.edges || []).filter((e) => e.type === 'triggers' && (e.source === wayNode.id || e.target === wayNode.id));
            if (!triggerEdges.length && !(props.triggers || []).length) {
                warnings.push('locked way has no tags and no visible unlock trigger (heuristic)');
            }
        }
        const desc = String(props.description || '');
        const missing = InspectorHelpers.unresolvedParamKeys(desc, props.parameters || {});
        if (missing.length) {
            warnings.push(`description references missing parameters: ${missing.join(', ')}`);
        }
        return warnings;
    };
    WA.renderSanityWarnings = function (wayNode) {
        const warnings = WA.tagSanityWarnings(wayNode);
        if (!warnings.length)
            return '';
        return `<div class="way-sanity-warnings" style="margin-top:6px;padding:6px 8px;background:#3a2a1022;border:1px solid var(--orange);border-radius:4px;font-size:10px;color:var(--orange);">
            ${warnings.map((w) => `<div>⚠ ${esc(w)}</div>`).join('')}
        </div>`;
    };
    WA._findNode = function (nodesObj, id) {
        if (!nodesObj || !id)
            return null;
        if (nodesObj[id])
            return nodesObj[id];
        const key = Object.keys(nodesObj).find((k) => k.toLowerCase() === String(id).toLowerCase());
        return key ? nodesObj[key] : null;
    };
    WA._findEdge = function (edgesArr, source, target, type = 'connection') {
        return (edgesArr || []).find((e) => e.type === type
            && String(e.source).toLowerCase() === String(source).toLowerCase()
            && String(e.target).toLowerCase() === String(target).toLowerCase());
    };
    /**
     * Tooltip for a single collapsed vis edge (area↔way shows one bidirectional line;
     * command/view come from the area→way edge for the area on this link).
     */
    WA.buildEdgeTooltipForVis = function (fromId, toId, nodesObj, edgesArr) {
        const fromNode = WA._findNode(nodesObj, fromId);
        const toNode = WA._findNode(nodesObj, toId);
        if (!fromNode || !toNode)
            return null;
        let areaNode, wayNode, areaId, wayId;
        if (fromNode.type === 'area' && toNode.type === 'way') {
            areaNode = fromNode;
            wayNode = toNode;
            areaId = fromId;
            wayId = toId;
        }
        else if (fromNode.type === 'way' && toNode.type === 'area') {
            areaNode = toNode;
            wayNode = fromNode;
            areaId = toId;
            wayId = fromId;
        }
        else {
            return null;
        }
        const areaToWay = WA._findEdge(edgesArr, areaId, wayId);
        const wayToArea = WA._findEdge(edgesArr, wayId, areaId);
        const props = wayNode.properties || {};
        const areaName = areaNode.name || areaId;
        const wayName = wayNode.name || wayId;
        let targetAreaName = '?';
        (edgesArr || []).forEach((e) => {
            if (e.type !== 'connection')
                return;
            if (String(e.target).toLowerCase() !== String(wayId).toLowerCase())
                return;
            if (String(e.source).toLowerCase() === String(areaId).toLowerCase())
                return;
            const other = WA._findNode(nodesObj, e.source);
            if (other?.type === 'area')
                targetAreaName = other.name || e.source;
        });
        const command = String(areaToWay?.properties?.direction || wayToArea?.properties?.direction || '?');
        const view = String(areaToWay?.properties?.visible_in_direction || '');
        const state = String(props.current_state || 'closed');
        const req = String(props.requires || '').toLowerCase();
        const reqMeta = WA.REQUIRES_LABEL[req];
        const movement = reqMeta ? `${reqMeta.label} (${reqMeta.hint})` : 'go (default)';
        const tags = (props.tags || []).join(', ') || ' - ';
        const viewSnippet = view ? (view.length > 80 ? view.substring(0, 80) + '…' : view) : ' - ';
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
        html += `<div style="font-size:9px;color:var(--text-muted);margin-bottom:4px;">One graph edge  -  area→way + return path collapsed</div>`;
        html += `<div><span style="color:var(--text-dim);">Command (from ${esc(areaName)}):</span> go "${esc(command)}" → ${esc(targetAreaName)}</div>`;
        html += `<div><span style="color:var(--text-dim);">Way state:</span> ${esc(state)}</div>`;
        html += `<div><span style="color:var(--text-dim);">Movement:</span> ${esc(movement)}</div>`;
        html += `<div><span style="color:var(--text-dim);">Tags:</span> ${esc(tags)}</div>`;
        html += `<div style="margin-top:4px;color:var(--text-muted);"><span style="color:var(--text-dim);">View when open:</span> "${esc(viewSnippet)}"</div>`;
        html += '</div>';
        return { html, plain };
    };
    /** @deprecated use buildEdgeTooltipForVis */
    WA.buildConnectionEdgeTooltip = function (edgeData) {
        const nodesObj = graphManager?._graphNodesObj || worldState.graph?.nodes || {};
        const edgesArr = graphManager?._graphEdgesArr || worldState.graph?.edges || [];
        if (!edgeData)
            return null;
        const tip = WA.buildEdgeTooltipForVis(edgeData.source, edgeData.target, nodesObj, edgesArr);
        return tip?.html || null;
    };
    WA.enhanceWayNodeTooltip = function (nodeData, baseHtml) {
        const pair = WA.getWayAreaPair(String(nodeData.id));
        let extra = '';
        if (pair.from || pair.to) {
            extra += `<div style="margin:2px 0;">📍 ${esc(pair.from || '?')} ↔ ${esc(pair.to || '?')}</div>`;
        }
        const tags = nodeData.properties?.tags || [];
        if (tags.length) {
            extra += `<div style="margin:2px 0;">🏷️ ${esc(tags.join(', '))}</div>`;
        }
        if (!extra)
            return baseHtml;
        const insertAt = baseHtml.lastIndexOf('</div>');
        if (insertAt === -1)
            return baseHtml + extra;
        return baseHtml.slice(0, insertAt) + extra + baseHtml.slice(insertAt);
    };
    return WA;
})();
window.WayAuthoring = WayAuthoringModule;
