/**
 * InspectorWayViewConnections — Connection editing for way inspector
 * Extracted from way-view.js for modularity.
 */
window.InspectorWayViewConnections = (() => {
    const C = {};

    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
    const esc = InspectorHelpers.esc;

    const OPPOSITE_CARDINAL = {
        north: 'south', south: 'north',
        east: 'west', west: 'east',
        northeast: 'southwest', southwest: 'northeast',
        northwest: 'southeast', southeast: 'northwest',
        up: 'down', down: 'up'
    };

    C._updateCardinal = function(edgeSource, wayId, oppositeSource, cardinal) {
        const rev = OPPOSITE_CARDINAL[cardinal] || '';
        const updates = [
            ApiClient.updateEdge(edgeSource, wayId, { old_type: 'connection', properties: { cardinal: cardinal || '' } }),
        ];
        if (rev) {
            updates.push(
                ApiClient.updateEdge(oppositeSource, wayId, { old_type: 'connection', properties: { cardinal: rev } })
            );
        }
        Promise.all(updates).then(() => worldState.fetch()).then(() => {
            if (window.graphManager && graphManager._cardinalLayout) {
                graphManager._lastSig = '';
                graphManager.loadGraphData();
            }
        });
    };

    C._parseConnections = function(connEdges, nodeId) {
        const roomNodes = worldState.graph?.nodes || {};
        const wayNode = roomNodes[nodeId];
        const props = wayNode?.properties || {};

        const areaToWay = [];
        const seen = new Set();
        connEdges.forEach(edge => {
            if (edge.target === nodeId && !seen.has(edge.source.toLowerCase())) {
                seen.add(edge.source.toLowerCase());
                areaToWay.push(edge);
            }
        });

        const edgeDir = (id) => {
            const hit = connEdges.find(e =>
                e.target === nodeId && e.source.toLowerCase() === id.toLowerCase());
            return hit?.properties?.direction || '';
        };

        let roomAId = '', roomBId = '';
        let roomAName = '', roomBName = '';
        const fromName = props.area_from || '';
        const toName = props.area_to || '';
        const nameToId = {};
        Object.values(roomNodes).forEach(n => {
            if (n.type === 'area') nameToId[String(n.name || '').toLowerCase()] = n.id;
        });
        const fromId = nameToId[fromName.toLowerCase()];
        const toId = nameToId[toName.toLowerCase()];
        const areaIds = areaToWay.map(e => e.source.toLowerCase());
        if (fromId && toId && areaIds.includes(fromId.toLowerCase()) && areaIds.includes(toId.toLowerCase())) {
            roomAId = fromId;
            roomBId = toId;
        } else if (areaToWay.length) {
            roomAId = areaToWay[0].source;
            if (areaToWay[1]) roomBId = areaToWay[1].source;
        }

        const roomADir = roomAId ? edgeDir(roomAId) : '';
        const roomBDir = roomBId ? edgeDir(roomBId) : '';

        roomAName = roomNodes[roomAId]?.name || roomAId;
        roomBName = roomNodes[roomBId]?.name || roomBId;

        return { roomAId, roomAName, roomADir, roomBId, roomBName, roomBDir };
    };

    C._renderVisibleItemSelect = function(sourceAreaId, wayId, targetAreaName, selectedItems) {
        const items = worldState.getItemsInArea(targetAreaName) || [];
        const selected = new Set((selectedItems || []).map(name => String(name).toLowerCase()));
        if (!items.length) {
            return `<div style="font-size:10px;color:var(--text-muted);">No items in ${esc(targetAreaName)}</div>`;
        }
        const size = Math.min(5, Math.max(2, items.length));
        const options = items.map(item => {
            const name = item.name || '';
            const isSelected = selected.has(String(name).toLowerCase());
            return `<option value="${esc(name)}" ${isSelected ? 'selected' : ''}>${esc(name)}</option>`;
        }).join('');
        return `<select multiple size="${size}" style="width:100%;font-size:10px;"
            onchange="InspectorWayView._saveVisibleItems('${esc(sourceAreaId)}','${esc(wayId)}',this)">${options}</select>`;
    };

    C._saveVisibleItems = function(sourceId, wayId, selectEl) {
        const visible_items = Array.from(selectEl.selectedOptions).map(opt => opt.value);
        api.updateEdge(sourceId, wayId, { old_type: 'connection', properties: { visible_items } })
            .then(() => worldState.fetch());
    };

    C._saveAllowSeeCharacters = function(sourceId, wayId, checked) {
        api.updateEdge(sourceId, wayId, { old_type: 'connection', properties: { allow_see_characters: !!checked } })
            .then(() => worldState.fetch());
    };

    C._renderConnections = function(connEdges, connInfo, nodeId, escapedId) {
        const { roomAId, roomAName, roomADir, roomBId, roomBName, roomBDir } = connInfo;

        const roomNodes = worldState.graph?.nodes || {};
        const roomNameMap = {};
        Object.entries(roomNodes).forEach(([nodeIdKey, node]) => {
            if (node.type === 'area') {
                roomNameMap[node.name || nodeIdKey] = nodeIdKey;
            }
        });

        const roomOptions = Object.keys(roomNameMap).sort().map(areaName =>
            `<option value="${esc(areaName)}">${esc(areaName)}</option>`
        ).join('');

        const roomAreaNames = Object.keys(roomNameMap).sort();
        const areaOptionsFor = (selectedName) => roomAreaNames.map(areaName =>
            htmlTag`<option value=${areaName} ?selected=${areaName === selectedName}>${areaName}</option>`
        );

        if (!roomAId || !roomBId) return '';

        const roomAEdge = connEdges.find(edge => edge.source.toLowerCase() === roomAId.toLowerCase() && edge.target.toLowerCase() === nodeId.toLowerCase());
        const roomBEdge = connEdges.find(edge => edge.source.toLowerCase() === roomBId.toLowerCase() && edge.target.toLowerCase() === nodeId.toLowerCase());
        const viewAB = roomAEdge?.properties?.visible_in_direction || '';
        const viewBA = roomBEdge?.properties?.visible_in_direction || '';
        const allowSeeAB = !!roomAEdge?.properties?.allow_see_characters;
        const allowSeeBA = !!roomBEdge?.properties?.allow_see_characters;
        const visibleItemsAB = roomAEdge?.properties?.visible_items || [];
        const visibleItemsBA = roomBEdge?.properties?.visible_items || [];
        const cardinalAB = roomAEdge?.properties?.cardinal || '';
        const cardinalBA = roomBEdge?.properties?.cardinal || '';
        const escA = esc(roomAName);
        const escB = esc(roomBName);

        return `
            <div class="inspector-section">
                <h3>🔗 Connections</h3>
                <div style="font-size:12px;display:flex;flex-direction:column;gap:4px;margin-bottom:8px;">
                    <div><span style="color:var(--text-dim);">Side A:</span> ${escA} <span style="color:var(--text-muted);font-size:10px;">(from this area: "${esc(roomADir)}")</span></div>
                    <div><span style="color:var(--text-dim);">Side B:</span> ${escB} <span style="color:var(--text-muted);font-size:10px;">(from this area: "${esc(roomBDir)}")</span></div>
                </div>
                <div class="field"><label>View when open (from ${escA} → ${escB})</label>
                    <textarea rows="2" placeholder="What you see looking from ${escA} toward ${escB}…" onchange="api.updateEdge('${esc(roomAId)}','${escapedId}',{old_type:'connection',properties:{visible_in_direction:this.value}}).then(()=>worldState.fetch())">${esc(viewAB)}</textarea>
                </div>
                <div class="field" style="margin-top:2px;">
                    <label style="display:flex;align-items:center;gap:6px;font-size:10px;cursor:pointer;">
                        <input type="checkbox" ${allowSeeAB ? 'checked' : ''}
                            onchange="InspectorWayView._saveAllowSeeCharacters('${esc(roomAId)}','${escapedId}',this.checked)">
                        Show characters visible in ${escB}
                    </label>
                </div>
                <div class="field">
                    <label style="font-size:10px;">Visible items in ${escB} (Ctrl+click to select)</label>
                    ${C._renderVisibleItemSelect(roomAId, nodeId, roomBName, visibleItemsAB)}
                </div>
                <div class="field"><label>View when open (from ${escB} → ${escA})</label>
                    <textarea rows="2" placeholder="What you see looking from ${escB} toward ${escA}…" onchange="api.updateEdge('${esc(roomBId)}','${escapedId}',{old_type:'connection',properties:{visible_in_direction:this.value}}).then(()=>worldState.fetch())">${esc(viewBA)}</textarea>
                </div>
                <div class="field" style="margin-top:2px;">
                    <label style="display:flex;align-items:center;gap:6px;font-size:10px;cursor:pointer;">
                        <input type="checkbox" ${allowSeeBA ? 'checked' : ''}
                            onchange="InspectorWayView._saveAllowSeeCharacters('${esc(roomBId)}','${escapedId}',this.checked)">
                        Show characters visible in ${escA}
                    </label>
                </div>
                <div class="field">
                    <label style="font-size:10px;">Visible items in ${escA} (Ctrl+click to select)</label>
                    ${C._renderVisibleItemSelect(roomBId, nodeId, roomAName, visibleItemsBA)}
                </div>
                <div class="field"><label>Cardinal (A→B) for map layout</label>
                    ${window.InspectorWayView._renderCompassSelector('conn-a', escapedId, cardinalAB)}
                    <input type="hidden" id="way-side-conn-a-cardinal-${escapedId}" value="${cardinalAB}" onchange="InspectorWayView._updateCardinal('${esc(roomAId)}','${escapedId}','${esc(roomBId)}',this.value)">
                </div>
                <div class="field"><label>Cardinal (B→A) for map layout</label>
                    ${window.InspectorWayView._renderCompassSelector('conn-b', escapedId, cardinalBA)}
                    <input type="hidden" id="way-side-conn-b-cardinal-${escapedId}" value="${cardinalBA}" onchange="InspectorWayView._updateCardinal('${esc(roomBId)}','${escapedId}','${esc(roomAId)}',this.value)">
                </div>
                <div style="border-top:1px solid var(--border-light);padding-top:6px;margin-top:4px;">
                    <div class="field"><label>Area A</label>
                        <select id="way-reconn-a">${areaOptionsFor(roomAName)}</select>
                    </div>
                    <div class="field"><label>Command from A → B <span class="section-hint">(go ___)</span></label>
                        <input type="text" id="way-reconn-dir1" value="${esc(roomADir)}" style="width:100%;padding:4px 8px;font-size:12px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);" onchange="var v=this.value,w='${escapedId}',a='${esc(roomAId)}';Promise.all([api.updateEdge(a,w,{old_type:'connection',properties:{direction:v}}),api.updateEdge(w,a,{old_type:'connection',properties:{direction:v}})]).then(()=>worldState.fetch())">
                    </div>
                    <div class="field"><label>Area B</label>
                        <select id="way-reconn-b">${areaOptionsFor(roomBName)}</select>
                    </div>
                    <div class="field"><label>Command from B → A <span class="section-hint">(go ___)</span></label>
                        <input type="text" id="way-reconn-dir2" value="${esc(roomBDir)}" style="width:100%;padding:4px 8px;font-size:12px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);" onchange="var v=this.value,w='${escapedId}',b='${esc(roomBId)}';Promise.all([api.updateEdge(b,w,{old_type:'connection',properties:{direction:v}}),api.updateEdge(w,b,{old_type:'connection',properties:{direction:v}})]).then(()=>worldState.fetch())">
                    </div>
                    <button class="btn btn-sm btn-blue" onclick="InspectorWayView._reconnectDoor('${escapedId}')" style="margin-top:4px;">🔄 Reconnect</button>
                </div>
            </div>`;
    };

    C._reconnectDoor = async function(wayId) {
        const roomASelect = document.getElementById('way-reconn-a');
        const roomBSelect = document.getElementById('way-reconn-b');
        const dir1Input = document.getElementById('way-reconn-dir1');
        const dir2Input = document.getElementById('way-reconn-dir2');
        if (!roomASelect || !roomBSelect) return;

        const roomAName = roomASelect.value;
        const roomBName = roomBSelect.value;
        if (!roomAName || !roomBName) return;
        if (roomAName === roomBName) { toastInfo('Cannot connect a way to itself.'); return; }

        const roomNodes = worldState.graph?.nodes || {};
        let roomAId = '', roomBId = '';
        Object.entries(roomNodes).forEach(([nodeId, node]) => {
            if (node.type === 'area') {
                if (node.name === roomAName) roomAId = nodeId;
                if (node.name === roomBName) roomBId = nodeId;
            }
        });
        if (!roomAId || !roomBId) { toastError('Could not find area nodes.'); return; }

        const dir1 = dir1Input?.value?.trim() || '';
        const dir2 = dir2Input?.value?.trim() || '';

        await ApiClient.reconnectDoor(wayId, roomAId, roomBId, dir1, dir2);
        worldState.fetch().then(() => {
            if (window.VW?.inspector) window.VW.inspector.showNode(wayId);
        });
    };

    return C;
})();
