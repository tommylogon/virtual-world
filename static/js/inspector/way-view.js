/**
 * InspectorWayView — Way inspector (showWay, reconnectDoor)
 * Extracted from inspector.js for modularity.
 * task-216: renders lit-html TemplateResults through InspectorPanel (single panel owner).
 */
window.InspectorWayView = (() => {
    const wayView = {};

    // Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
    const esc = InspectorHelpers.esc;

    const STATE_OPTIONS = ['open', 'closed', 'locked', 'blocked', 'broken', 'hidden'];
    const SKILL_OPTIONS = ['Athletics', 'Acrobatics', 'Stealth', 'Perception', 'Investigation',
        'Survival', 'Persuasion', 'Performance', 'Medicine', 'Arcana', 'Intimidation', 'Lockpicking'
    ];
    const CARDINAL_OPTIONS = [
        { value: '', label: '— Not set —' },
        { value: 'north', label: 'North (N)' },
        { value: 'northeast', label: 'Northeast (NE)' },
        { value: 'east', label: 'East (E)' },
        { value: 'southeast', label: 'Southeast (SE)' },
        { value: 'south', label: 'South (S)' },
        { value: 'southwest', label: 'Southwest (SW)' },
        { value: 'west', label: 'West (W)' },
        { value: 'northwest', label: 'Northwest (NW)' },
        { value: 'up', label: 'Up (U)' },
        { value: 'down', label: 'Down (D)' },
    ];
    const OPPOSITE_CARDINAL = {
        north: 'south', south: 'north',
        east: 'west', west: 'east',
        northeast: 'southwest', southwest: 'northeast',
        northwest: 'southeast', southeast: 'northwest',
        up: 'down', down: 'up'
    };

    wayView._renderLockToggle = function(field, lockedFields, escapedId) {
        return InspectorHelpers.renderLockToggle(field, lockedFields, escapedId);
    };

    wayView._toggleFieldLock = function(nodeId, field) {
        return InspectorHelpers.toggleFieldLock(nodeId, field);
    };

    wayView._getLockedFields = function(props) {
        return InspectorHelpers.getLockedFields(props);
    };

    const COMPASS_LAYOUT = [
        [{ value: 'northwest', label: '↖ NW' }, { value: 'north', label: '↑ N' }, { value: 'northeast', label: '↗ NE' }],
        [{ value: 'west', label: '← W' }, { value: '', label: '✕ Clear' }, { value: 'east', label: '→ E' }],
        [{ value: 'southwest', label: '↙ SW' }, { value: 'south', label: '↓ S' }, { value: 'southeast', label: '↘ SE' }],
    ];

    // Radial compass layout (8 directions + clear)
    const RADIAL_COMPASS = [
        { value: 'north', label: 'N', angle: 0 },
        { value: 'northeast', label: 'NE', angle: 45 },
        { value: 'east', label: 'E', angle: 90 },
        { value: 'southeast', label: 'SE', angle: 135 },
        { value: 'south', label: 'S', angle: 180 },
        { value: 'southwest', label: 'SW', angle: 225 },
        { value: 'west', label: 'W', angle: 270 },
        { value: 'northwest', label: 'NW', angle: 315 },
    ];

    wayView._renderCompassSelector = function(prefix, escapedId, cardinal) {
        const radius = 55;
        const centerX = 65;
        const centerY = 65;
        const btnSize = 36;

        let buttonsHtml = '';
        RADIAL_COMPASS.forEach(dir => {
            const rad = (dir.angle - 90) * Math.PI / 180;
            const x = centerX + radius * Math.cos(rad) - btnSize / 2;
            const y = centerY + radius * Math.sin(rad) - btnSize / 2;
            const isSelected = cardinal === dir.value;
            buttonsHtml += `<div class="compass-radial-btn" data-cardinal="${dir.value}" onclick="InspectorWayView._selectCompassDirection('${prefix}','${escapedId}',this.dataset.cardinal)"
                style="position:absolute;left:${x}px;top:${y}px;width:${btnSize}px;height:${btnSize}px;border-radius:50%;background:${isSelected ? 'var(--accent)' : 'var(--bg-input)'};color:${isSelected ? '#fff' : 'var(--text)'};border:2px solid ${isSelected ? 'var(--accent)' : 'var(--border)'};cursor:pointer;font-size:11px;font-weight:600;display:flex;align-items:center;justify-content:center;transition:all 0.15s;"
                title="${dir.value}">${dir.label}</div>`;
        });

        const clearStyle = !cardinal ? 'background:var(--red);color:#fff;border-color:var(--red);' : '';
        buttonsHtml += `<div class="compass-radial-btn" data-cardinal="" onclick="InspectorWayView._selectCompassDirection('${prefix}','${escapedId}',this.dataset.cardinal)"
            style="position:absolute;left:${centerX - btnSize / 2}px;top:${centerY - btnSize / 2}px;width:${btnSize}px;height:${btnSize}px;border-radius:50%;background:${clearStyle || 'var(--bg-input)'};color:${clearStyle || 'var(--text)'};border:2px solid ${clearStyle ? 'var(--red)' : 'var(--border)'};cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;transition:all 0.15s;"
            title="Clear direction">✕</div>`;

        return `<div style="position:relative;width:130px;height:130px;display:inline-block;">
            <svg width="130" height="130" style="position:absolute;top:0;left:0;pointer-events:none;">
                <circle cx="65" cy="65" r="${radius}" fill="none" stroke="var(--border)" stroke-width="1" stroke-dasharray="4,4"/>
                <line x1="65" y1="10" x2="65" y2="20" stroke="var(--text-muted)" stroke-width="1"/>
                <line x1="65" y1="110" x2="65" y2="120" stroke="var(--text-muted)" stroke-width="1"/>
                <line x1="10" y1="65" x2="20" y2="65" stroke="var(--text-muted)" stroke-width="1"/>
                <line x1="110" y1="65" x2="120" y2="65" stroke="var(--text-muted)" stroke-width="1"/>
            </svg>
            ${buttonsHtml}
        </div>`;
    };

    wayView._selectCompassDirection = function(prefix, escapedId, cardinal) {
        const sel = document.getElementById(`way-side-${prefix}-cardinal-${escapedId}`);
        if (sel) sel.value = cardinal;
        const container = sel?.closest('.inspector-section') || sel?.parentElement;
        if (container) {
            container.querySelectorAll('.compass-radial-btn').forEach(btn => {
                const isActive = btn.dataset.cardinal === cardinal;
                btn.style.background = isActive ? 'var(--accent)' : 'var(--bg-input)';
                btn.style.color = isActive ? '#fff' : 'var(--text)';
                btn.style.borderColor = isActive ? 'var(--accent)' : 'var(--border)';
            });
        }
        if (sel && sel.onchange) sel.dispatchEvent(new Event('change'));
    };

    // ─── Tab state ───
    let _activeWayTab = 'Passage';
    const WAY_TABS = ['Passage', 'Behavior', 'Tags & More', 'Triggers'];

    wayView._renderWayTabNav = function() {
        return htmlTag`<div class="inspector-tabs" style="display:flex;border-bottom:2px solid var(--border);background:var(--bg-card);padding:0 8px;gap:2px;">
            ${WAY_TABS.map(tabName => htmlTag`<div class="inspector-tab" data-tab-btn=${tabName} @click=${() => wayView._switchWayTab(tabName)} style="padding:6px 12px;font-size:11px;cursor:pointer;border-bottom:2px solid ${_activeWayTab === tabName ? 'var(--accent)' : 'transparent'};color:${_activeWayTab === tabName ? 'var(--accent)' : 'var(--text-dim)'};font-weight:${_activeWayTab === tabName ? '600' : '400'};">${tabName}</div>`)}
        </div>`;
    };

    wayView._switchWayTab = function(tabName) {
        _activeWayTab = tabName;
        document.querySelectorAll('.inspector-tab').forEach(el => {
            const on = el.dataset.tabBtn === tabName;
            el.style.borderBottomColor = on ? 'var(--accent)' : 'transparent';
            el.style.color = on ? 'var(--accent)' : 'var(--text-dim)';
            el.style.fontWeight = on ? '600' : '400';
        });
        document.querySelectorAll('#inspector-panel [data-tab]').forEach(el => {
            el.style.display = el.dataset.tab === tabName ? '' : 'none';
        });
    };

    wayView._renderParametersSection = function(props, nodeId) {
        const params = props.parameters || {};
        const paramKeys = Object.keys(params);
        return htmlTag`<div class="inspector-section"><h3>📐 Parameters <span class="section-hint">(key-value pairs for {param:&lt;key&gt;} in descriptions/triggers)</span></h3>
            <div id="params-list-${nodeId}" style="margin-bottom:4px;">
                ${paramKeys.map((key) => htmlTag`<div style="display:flex;gap:4px;align-items:center;margin-bottom:3px;">
                    <input type="text" .value=${key} style="flex:2;font-size:11px;padding:2px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);"
                        @change=${(ev) => InspectorHelpers.updateParamKey(nodeId, key, ev.target.value)} placeholder="key">
                    <input type="text" .value=${String(params[key])} style="flex:3;font-size:11px;padding:2px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);"
                        @change=${(ev) => InspectorHelpers.updateParamValue(nodeId, key, ev.target.value)} placeholder="value">
                    <button class="btn btn-sm btn-ghost" @click=${() => InspectorHelpers.removeParam(nodeId, key)} style="padding:0 6px;font-size:14px;line-height:1;">✕</button>
                </div>`)}
            </div>
            <div style="display:flex;gap:4px;">
                <input type="text" id="param-key-${nodeId}" placeholder="key" style="flex:2;font-size:11px;padding:2px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);">
                <input type="text" id="param-val-${nodeId}" placeholder="value" style="flex:3;font-size:11px;padding:2px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);">
                <button class="btn btn-sm btn-blue" @click=${() => InspectorHelpers.addParam(nodeId)}>➕</button>
            </div>
        </div>`;
    };

    wayView._updateCardinal = function(edgeSource, wayId, oppositeSource, cardinal) {
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

    wayView._refreshParamPreview = function(wayId) {
        const previewEl = document.getElementById(`way-param-preview-${wayId}`);
        if (!previewEl) return;
        const descEl = document.getElementById(`way-passage-desc-${wayId}`);
        const node = worldState.getNode(wayId);
        const params = node?.properties?.parameters || {};
        const text = descEl?.value ?? node?.properties?.description ?? '';
        const block = InspectorHelpers.renderParamPreviewBlock(text, params);
        previewEl.innerHTML = block.replace(/^<div class="way-param-preview"[^>]*>/, '').replace(/<\/div>\s*$/, '');
    };

    wayView._renderUnifiedPassage = function(nodeId, escapedId, graphNode, props, connInfo) {
        const { roomAId, roomAName, roomADir, roomBId, roomBName, roomBDir } = connInfo;
        const state = props.current_state || 'closed';
        const sides = typeof WayAuthoring !== 'undefined' ? WayAuthoring.getWaySides(nodeId) : [];
        const sideA = sides.find(s => s.areaId === roomAId) || sides[0] || {};
        const sideB = sides.find(s => s.areaId === roomBId) || sides[1] || {};

        const renderSide = (prefix, areaName, areaId, cmd, view, cardinal, targetName, visibleItems, allowSee) => {
            if (!areaId) return '';
            const escArea = esc(areaName);
            const escTarget = esc(targetName || '?');
            const items = worldState.getItemsInArea(targetName) || [];
            const selected = new Set((visibleItems || []).map(n => String(n).toLowerCase()));
            const itemOptions = items.length
                ? items.map(item => {
                    const iname = item.name || '';
                    return `<option value="${esc(iname)}" ${selected.has(String(iname).toLowerCase()) ? 'selected' : ''}>${esc(iname)}</option>`;
                }).join('')
                : `<option disabled>No items in ${escTarget}</option>`;
            return `
            <div class="inspector-section way-passage-side" style="border-top:2px solid var(--border);margin-top:4px;padding-top:8px;">
                <h3 style="font-size:12px;margin-bottom:6px;">FROM ${escArea}</h3>
                <div class="field">
                    <label>Command <span class="section-hint">(go ___)</span></label>
                    <input type="text" id="way-side-${prefix}-cmd-${escapedId}" value="${esc(cmd)}" style="width:100%;font-size:11px;">
                </div>
                <div class="field">
                    <label>View when open (from this area)</label>
                    <textarea id="way-side-${prefix}-view-${escapedId}" rows="2" style="width:100%;font-size:11px;">${esc(view)}</textarea>
                    <div class="section-hint">Injected into look/agent prompts when the way is open or see-through.</div>
                </div>
                <div class="field">
                    <label>Cardinal for map layout</label>
                    ${wayView._renderCompassSelector(prefix, escapedId, cardinal)}
                    <input type="hidden" id="way-side-${prefix}-cardinal-${escapedId}" value="${cardinal}" onchange="if ('${roomAId || ''}' && '${roomBId || ''}') { const opp = '${roomAId}' === '${esc(areaId)}' ? '${roomBId}' : '${roomAId}'; InspectorWayView._updateCardinal('${esc(areaId)}', '${escapedId}', opp, this.value); }">
                </div>
                <div class="field">
                    <label style="display:flex;align-items:center;gap:6px;font-size:10px;cursor:pointer;">
                        <input type="checkbox" id="way-side-${prefix}-see-chars-${escapedId}" ${allowSee ? 'checked' : ''}>
                        Show characters visible in ${escTarget}
                    </label>
                </div>
                <div class="field">
                    <label style="font-size:10px;">Visible items in ${escTarget}</label>
                    <select multiple id="way-side-${prefix}-items-${escapedId}" size="3" style="width:100%;font-size:10px;">${itemOptions}</select>
                </div>
            </div>`;
        };

        const closedPreview = InspectorHelpers.resolveWayParams(props.description || '', props.parameters || {});
        const sanityHtml = typeof WayAuthoring !== 'undefined' ? WayAuthoring.renderSanityWarnings(graphNode) : '';

        let reconnectHtml = '';
        if (roomAId && roomBId) {
            const roomNodes = worldState.graph?.nodes || {};
            const roomNameMap = {};
            Object.entries(roomNodes).forEach(([nid, node]) => {
                if (node.type === 'area') roomNameMap[node.name || nid] = nid;
            });
            const roomOptions = Object.keys(roomNameMap).sort().map(areaName =>
                `<option value="${esc(areaName)}">${esc(areaName)}</option>`
            ).join('');
            reconnectHtml = `
            <div style="border-top:1px solid var(--border-light);padding-top:8px;margin-top:8px;">
                <h3 style="font-size:11px;color:var(--text-dim);">Reconnect areas</h3>
                <div class="field"><label>Area A</label>
                    <select id="way-reconn-a">${roomOptions.replace(`value="${esc(roomAName)}"`, `value="${esc(roomAName)}" selected`)}</select>
                </div>
                <div class="field"><label>Area B</label>
                    <select id="way-reconn-b">${roomOptions.replace(`value="${esc(roomBName)}"`, `value="${esc(roomBName)}" selected`)}</select>
                </div>
                <button class="btn btn-sm btn-blue" onclick="InspectorWayView._reconnectDoor('${escapedId}')" style="margin-top:4px;">🔄 Reconnect</button>
            </div>`;
        }

        const sideAHtml = renderSide('a', roomAName, roomAId, roomADir, sideA.viewWhenOpen || '', sideA.cardinal || '', roomBName, sideA.visibleItems, sideA.allowSeeCharacters);
        const sideBHtml = renderSide('b', roomBName, roomBId, roomBDir, sideB.viewWhenOpen || '', sideB.cardinal || '', roomAName, sideB.visibleItems, sideB.allowSeeCharacters);

        return htmlTag`
            <div class="inspector-section" style="background:var(--bg-inset);border-radius:6px;margin-bottom:8px;">
                <h3 style="font-size:11px;">PREVIEW</h3>
                <div class="section-hint" style="margin-bottom:6px;">What players/agents see from ${esc(roomAName || 'side A')} — updates after Save.</div>
                <div style="font-size:10px;color:var(--text-dim);">Closed glance:</div>
                <div style="font-size:10px;margin-bottom:6px;">${esc(closedPreview || '(empty)')}</div>
                <div style="font-size:10px;color:var(--text-dim);">Open glance:</div>
                <div style="font-size:10px;">${esc(sideA.viewWhenOpen || '(auto from target area)')}</div>
            </div>
            <div class="inspector-section">
                <h3>SHARED PASSAGE</h3>
                <div class="field">
                    <label style="display:flex;align-items:center;gap:4px;">${wayView._renderLockToggle('current_state', wayView._getLockedFields(props), escapedId)} State</label>
                    <select id="way-passage-state-${escapedId}">
                        ${STATE_OPTIONS.map(opt => htmlTag`<option value=${opt} ?selected=${state === opt}>${opt}</option>`)}
                    </select>
                </div>
                <div class="field">
                    <label style="display:flex;align-items:center;gap:4px;">${wayView._renderLockToggle('requires', wayView._getLockedFields(props), escapedId)} Required movement verb</label>
                    <select id="way-passage-requires-${escapedId}">
                        <option value="" ?selected=${!props.requires || props.requires === 'none'}>None (walk through — go)</option>
                        <option value="crawl" ?selected=${props.requires === 'crawl'}>Crawl (go auto-crawls)</option>
                        <option value="climb" ?selected=${props.requires === 'climb'}>Climb (climb &lt;dir&gt;)</option>
                        <option value="jump" ?selected=${props.requires === 'jump'}>Jump (jump &lt;dir&gt;)</option>
                    </select>
                </div>
                <div class="field">
                    <label style="display:flex;align-items:center;gap:4px;">${wayView._renderLockToggle('description', wayView._getLockedFields(props), escapedId)} Appearance when closed/locked/blocked</label>
                    <textarea id="way-passage-desc-${escapedId}" rows="4"
                        @input=${() => wayView._refreshParamPreview(escapedId)}
                        placeholder="What players see when the way is not open…">${esc(props.description || '')}</textarea>
                    <div class="section-hint">Shown in look/examine and agent room context when closed.</div>
                    <div id="way-param-preview-${escapedId}">${window.Lit.unsafeHTML(InspectorHelpers.renderParamPreviewBlock(props.description || '', props.parameters || {}))}</div>
                </div>
                <div class="field">
                    <label style="display:flex;align-items:center;gap:4px;">${wayView._renderLockToggle('pass_message', wayView._getLockedFields(props), escapedId)} On traverse narration</label>
                    <textarea id="way-passage-pass-msg-${escapedId}" rows="2">${esc(props.pass_message || '')}</textarea>
                </div>
                <div class="field" style="display:flex;flex-wrap:wrap;gap:12px;margin-top:4px;">
                    <label style="display:flex;align-items:center;gap:4px;font-size:11px;cursor:pointer;">
                        <input type="checkbox" id="way-passage-one-way-${escapedId}" ?checked=${!!props.one_way}> ➡️ One-way
                    </label>
                    <label style="display:flex;align-items:center;gap:4px;font-size:11px;cursor:pointer;">
                        <input type="checkbox" id="way-passage-see-through-${escapedId}" ?checked=${!!props.see_through}> 👁 See-through
                    </label>
                    <label style="display:flex;align-items:center;gap:4px;font-size:11px;cursor:pointer;">
                        <input type="checkbox" id="way-passage-auto-close-${escapedId}" ?checked=${!!props.auto_close}> 🔄 Auto-close
                    </label>
                    <label style="display:flex;align-items:center;gap:4px;font-size:11px;cursor:pointer;">
                        <input type="checkbox" id="way-passage-prevent-close-${escapedId}" ?checked=${!!props.prevent_close}> 🔒 Prevent closing (open passage)
                    </label>
                </div>
                <div class="section-hint">Jump/climb/crawl passages are always uncloseable. <b>Prevent closing</b> extends that to any way — the state can then only be changed by triggers.</div>
                ${wayView._renderParametersSection(props, escapedId)}
                ${sanityHtml ? window.Lit.unsafeHTML(sanityHtml) : ''}
            </div>
            ${sideAHtml ? window.Lit.unsafeHTML(sideAHtml) : ''}
            ${sideBHtml ? window.Lit.unsafeHTML(sideBHtml) : ''}
            ${reconnectHtml ? window.Lit.unsafeHTML(reconnectHtml) : ''}
            <div style="padding:8px 0;">
                <button class="btn btn-sm btn-green" style="width:100%;" @click=${() => wayView.saveWayPassage(escapedId)}>💾 Save way</button>
                <div class="section-hint" style="margin-top:4px;text-align:center;">Saves way node + both connection sides in one step.</div>
            </div>`;
    };

    wayView.saveWayPassage = async function(wayId) {
        const node = worldState.getNode(wayId);
        if (!node) return;
        const connEdges = (worldState.graph?.edges || []).filter(edge =>
            edge.type === 'connection'
            && (String(edge.source).toLowerCase() === wayId.toLowerCase() || String(edge.target).toLowerCase() === wayId.toLowerCase())
        );
        const connInfo = wayView._parseConnections(connEdges, wayId);
        const { roomAId, roomBId } = connInfo;
        const props = node.properties || {};
        const nodePatch = {
            description: document.getElementById(`way-passage-desc-${wayId}`)?.value ?? props.description ?? '',
            current_state: document.getElementById(`way-passage-state-${wayId}`)?.value ?? props.current_state ?? 'closed',
            pass_message: document.getElementById(`way-passage-pass-msg-${wayId}`)?.value ?? props.pass_message ?? '',
            requires: document.getElementById(`way-passage-requires-${wayId}`)?.value ?? props.requires ?? '',
            one_way: !!document.getElementById(`way-passage-one-way-${wayId}`)?.checked,
            see_through: !!document.getElementById(`way-passage-see-through-${wayId}`)?.checked,
            auto_close: !!document.getElementById(`way-passage-auto-close-${wayId}`)?.checked,
            prevent_close: !!document.getElementById(`way-passage-prevent-close-${wayId}`)?.checked,
        };
        const edgeUpdates = [];
        const saveSide = (prefix, areaId) => {
            if (!areaId) return;
            const cmd = document.getElementById(`way-side-${prefix}-cmd-${wayId}`)?.value?.trim() || '';
            const view = document.getElementById(`way-side-${prefix}-view-${wayId}`)?.value ?? '';
            const cardinal = document.getElementById(`way-side-${prefix}-cardinal-${wayId}`)?.value || '';
            const allowSee = !!document.getElementById(`way-side-${prefix}-see-chars-${wayId}`)?.checked;
            const itemsEl = document.getElementById(`way-side-${prefix}-items-${wayId}`);
            const visible_items = itemsEl ? Array.from(itemsEl.selectedOptions).map(opt => opt.value) : [];
            edgeUpdates.push(
                api.updateEdge(areaId, wayId, {
                    old_type: 'connection',
                    properties: { direction: cmd, visible_in_direction: view, cardinal, allow_see_characters: allowSee, visible_items },
                }),
                api.updateEdge(wayId, areaId, { old_type: 'connection', properties: { direction: cmd } })
            );
            if (cardinal && roomAId && roomBId) {
                const oppositeId = areaId === roomAId ? roomBId : roomAId;
                const rev = OPPOSITE_CARDINAL[cardinal] || '';
                if (rev) {
                    edgeUpdates.push(api.updateEdge(oppositeId, wayId, { old_type: 'connection', properties: { cardinal: rev } }));
                }
            }
        };
        saveSide('a', roomAId);
        saveSide('b', roomBId);
        try {
            await api.updateNode(wayId, { properties: nodePatch });
            await Promise.all(edgeUpdates);
            await worldState.fetch();
            if (window.graphManager && graphManager._cardinalLayout) {
                graphManager._lastSig = '';
                graphManager.loadGraphData();
            }
            if (window.VW?.inspector) VW.inspector.showNode(wayId);
            events.log('Way passage saved.', 'system-msg');
        } catch (err) {
            console.error(err);
            events.log('Failed to save way passage: ' + err.message, 'error-msg');
        }
    };

    /**
     * Render the full way inspector panel
     * @param {string} nodeId - Graph node ID
     * @param {object} graphNode - Graph node data
     */
    wayView.showWay = function(nodeId, graphNode) {
        const name = graphNode.name;
        const props = graphNode.properties || {};
        const state = props.current_state || 'closed';
        const tags = props.tags || [];
        const escapedId = nodeId.replace(/'/g, "\\'");
        const lockedFields = wayView._getLockedFields(props);
        const nothing = window.Lit.nothing;

        // Find connection edges
        const edges = worldState.graph?.edges || [];
        const nodeIdLower = String(nodeId).toLowerCase();
        const connEdges = edges.filter(edge => edge.type === 'connection' && (String(edge.source).toLowerCase() === nodeIdLower || String(edge.target).toLowerCase() === nodeIdLower));

        // Parse area connections
        const connectionInfo = wayView._parseConnections(connEdges, nodeId);
        const passageHtml = wayView._renderUnifiedPassage(nodeId, escapedId, graphNode, props, connectionInfo);
        const showTab = (tabName) => _activeWayTab === tabName ? '' : 'display:none;';

        // needs_open handlers read the sibling skill/DC inputs, so they need a ref to this render
        const saveNeedsOpen = (ev) => {
            const enabled = ev.target.checked;
            const skillEl = document.getElementById(`way-needs-skill-${nodeId}`);
            const dcEl = document.getElementById(`way-needs-dc-${nodeId}`);
            const skill = skillEl?.value || 'Athletics';
            const dc = parseInt(dcEl?.value) || 15;
            const configEl = document.getElementById(`way-needs-config-${nodeId}`);
            if (configEl) configEl.style.display = enabled ? 'flex' : 'none';
            api.updateNode(nodeId, { properties: { needs_open: { enabled, skill, dc } } }).then(() => worldState.fetch());
        };
        const saveNeedsOpenField = (field) => (ev) => {
            const existing = worldState.getNode(nodeId)?.properties?.needs_open || {};
            const patch = { ...existing };
            patch[field] = field === 'dc' ? (parseInt(ev.target.value) || 15) : ev.target.value;
            api.updateNode(nodeId, { properties: { needs_open: patch } }).then(() => worldState.fetch());
        };

        const template = htmlTag`
            <div class="inspector-header">
                <span class="inspector-type-badge" style="background:#4ec9b0">🚪 Way</span>
                <div style="flex:1;display:flex;flex-direction:column;">
                    <h2 style="margin:0;font-size:16px;"><input type="text" .value=${name} @change=${(ev) => api.updateNode(nodeId, { name: ev.target.value }).then(() => worldState.fetch())} style="font-size:1em;background:transparent;border:1px solid var(--border);color:inherit;width:100%;"></h2>
                    <div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                        <div style="display:flex;gap:2px;align-items:center;">
                            <input type="text" .value=${nodeId} @change=${(ev) => InspectorHelpers.renameNode(nodeId, ev.target.value)} style="font-size:10px;padding:1px 4px;background:transparent;border:1px solid transparent;color:var(--text-muted);width:100%;cursor:text;" title="Change node ID (lowercase, no spaces)">
                            <button class="btn btn-sm btn-ghost" @click=${() => InspectorHelpers.syncIdFromName(nodeId, name)} title="Sync ID from name">🔄</button>
                        </div>
                    </div>
                </div>
                <button class="btn btn-sm btn-ghost" @click=${() => hideInspectorPanel()}>✕</button>
            </div>
            ${wayView._renderWayTabNav()}
            ${window.Lit.unsafeHTML(window.InspectorHelpers.renderImageSection(nodeId, props))}
            <div data-tab="Passage" style=${showTab('Passage')}>
            ${passageHtml}
                <div style="display:flex;gap:4px;margin:4px 16px 8px;">
                    <button class="btn btn-sm" id="improve-way-btn" @click=${() => wayView.improveWayWithAI(nodeId)} style="white-space:nowrap;background:#2a6a3a;border-color:#3a9a5a;color:#7cff9c;">✨ Improve appearance</button>
                </div>
            </div>
            <div data-tab="Behavior" style=${showTab('Behavior')}>
                <div class="inspector-section">
                    <h3 style="display:flex;align-items:center;gap:4px;">🚪 Way Behavior</h3>
                    <div class="section-hint" style="margin-bottom:8px;">Movement verb, state, and traverse narration live on the Passage tab.</div>
                    <div class="field" style="display:flex;align-items:center;gap:8px;">
                        <input type="checkbox" id="way-needs-open-${nodeId}" ?checked=${!!props.needs_open?.enabled}
                            @change=${saveNeedsOpen}>
                        <label for="way-needs-open-${nodeId}" style="font-size:11px;cursor:pointer;">🔒 Needs skill check to open</label>
                        ${wayView._renderLockToggle('needs_open', lockedFields, nodeId)}
                    </div>
                    <div id="way-needs-config-${nodeId}" style="display:${props.needs_open?.enabled ? 'flex' : 'none'};gap:8px;margin-left:24px;margin-bottom:8px;">
                        <div class="field" style="flex:1;"><label style="font-size:10px;">Skill</label>
                            <select id="way-needs-skill-${nodeId}" style="font-size:10px;" @change=${saveNeedsOpenField('skill')}>
                                ${SKILL_OPTIONS.map(skillName => htmlTag`<option value=${skillName} ?selected=${(props.needs_open?.skill || 'Athletics') === skillName}>${skillName}</option>`)}
                            </select>
                        </div>
                        <div class="field" style="flex:0 0 60px;"><label style="font-size:10px;">DC</label>
                            <input type="number" id="way-needs-dc-${nodeId}" .value=${props.needs_open?.dc || 15} min="5" max="30" style="width:50px;font-size:10px;" @change=${saveNeedsOpenField('dc')}>
                        </div>
                    </div>
                    <div class="field" style="display:flex;align-items:center;gap:8px;">
                        <label for="way-jump-dc-${nodeId}" style="font-size:11px;flex:0 0 auto;">🏃 Jump DC</label>
                        <input type="number" id="way-jump-dc-${nodeId}" .value=${props.jump_dc || 12} min="5" max="30" style="width:60px;font-size:10px;"
                            @change=${(ev) => api.updateNode(nodeId, { properties: { jump_dc: parseInt(ev.target.value) || 12 } }).then(() => worldState.fetch())}>
                        <span style="font-size:9px;color:var(--text-muted);">Athletics DC for jump (fails → on_fail_jump)</span>
                    </div>
                    <div class="field" style="display:flex;align-items:center;gap:8px;">
                        <label for="way-climb-dc-${nodeId}" style="font-size:11px;flex:0 0 auto;">🧗 Climb DC</label>
                        <input type="number" id="way-climb-dc-${nodeId}" .value=${props.climb_dc || 12} min="5" max="30" style="width:60px;font-size:10px;"
                            @change=${(ev) => api.updateNode(nodeId, { properties: { climb_dc: parseInt(ev.target.value) || 12 } }).then(() => worldState.fetch())}>
                        <span style="font-size:9px;color:var(--text-muted);">Athletics DC for climb (fails → on_fail_climb)</span>
                    </div>
                    <div class="field" style="display:flex;align-items:center;gap:8px;">
                        <label for="way-max-size-${nodeId}" style="font-size:11px;flex:0 0 auto;">📏 Max size through</label>
                        <select id="way-max-size-${nodeId}" style="flex:1;font-size:10px;"
                            @change=${(ev) => api.updateNode(nodeId, { properties: { max_size: ev.target.value } }).then(() => worldState.fetch())}>
                            <option value="" ?selected=${!props.max_size || props.max_size === 'none'}>Any size (no limit)</option>
                            ${['tiny', 'small', 'normal', 'huge', 'giant', 'titanic'].map(sizeName => htmlTag`<option value=${sizeName} ?selected=${props.max_size === sizeName}>${sizeName}</option>`)}
                        </select>
                    </div>
                    <div class="field"><label style="display:flex;align-items:center;gap:4px;">${wayView._renderLockToggle('sound_barrier', wayView._getLockedFields(props), escapedId)} 🔇 Sound Barrier</label>
                        <input type="number" .value=${props.sound_barrier ?? ''} min="0" step="0.25" style="width:70px;font-size:11px;" @change=${(ev) => { const v = parseFloat(ev.target.value); api.updateNode(nodeId, { properties: { sound_barrier: isNaN(v) ? '' : v } }).then(() => worldState.fetch()); }} placeholder="default">
                        <span style="font-size:9px;color:var(--text-muted);margin-left:4px;">Blocks this much penetration when closed/blocked/locked (blank = Engine Config defaults)</span>
                    </div>
                    <div class="field"><label style="display:flex;align-items:center;gap:4px;">${wayView._renderLockToggle('edge_length', wayView._getLockedFields(props), escapedId)} Edge Length</label>
                        <input type="number" .value=${props.edge_length || ''} min="20" max="500" step="5" style="width:80px;font-size:11px;" @change=${(ev) => api.updateNode(nodeId, { properties: { edge_length: parseInt(ev.target.value) || '' } }).then(() => worldState.fetch())} placeholder="auto">
                        <span style="font-size:9px;color:var(--text-muted);margin-left:4px;">Graph spring length override (20-500)</span>
                    </div>
                </div>
                ${window.InspectorHelpers.graphGravityControl(nodeId, props)}
            </div>
            <div data-tab="Tags & More" style=${showTab('Tags & More')}>
                <div class="inspector-section">
                    <h3 style="display:flex;align-items:center;gap:4px;">🏷️ Tags ${wayView._renderLockToggle('tags', lockedFields, escapedId)}</h3>
                    <div id="way-tag-multiselect-${escapedId}" style="position:relative;"></div>
                </div>
                ${window.InspectorHelpers.renderAliasesSection(nodeId, props.aliases)}
            </div>
            <div data-tab="Triggers" style=${showTab('Triggers')}>
                ${window.InspectorTriggers.buildTriggersHtml(nodeId, props.locked_fields || [])}
            </div>
            <div style="display:flex;gap:6px;padding:8px 16px;flex-wrap:wrap;">
                <button class="btn btn-sm btn-green" @click=${() => wayView._saveToLibrary(nodeId)}>💾 Save to Library</button>
                ${window.InspectorTemplateSync ? window.Lit.unsafeHTML(window.InspectorTemplateSync.renderTemplateRow('way', nodeId, props)) : ''}
                <button class="btn btn-sm btn-blue" @click=${() => wayView._refreshFromLibrary(nodeId)}>🔄 Refresh from Library</button>
                <button class="btn btn-sm btn-red" @click=${() => graphManager._deleteNode(nodeId)}>🗑 Delete Way</button>
            </div>
        `;

        InspectorPanel.render(template);

        // Init TagMultiselect for way tags (render is synchronous, so the container exists).
        const tagContainer = document.getElementById(`way-tag-multiselect-${escapedId}`);
        if (tagContainer && typeof TagMultiselect !== 'undefined') {
            new TagMultiselect(tagContainer, {
                tags: tags,
                appliesTo: 'areas',
                allowNew: true,
                placeholder: 'Search or create tags...',
                onChange: (newTags) => {
                    api.updateNode(nodeId, { properties: { tags: newTags } }).then(() => worldState.fetch());
                }
            });
        }
        if (window.InspectorTemplateSync) {
            window.InspectorTemplateSync.populateSelector('way', nodeId);
        }
    };

    /**
     * Parse connection edges to extract area A/B info.
     * Prefers the way's area_from/area_to props when they resolve to areas
     * among the connection edges — stale edges from an old connect (3+ areas
     * wired to one way) would otherwise surface the wrong pair as side A/B.
     * @param {Array} connEdges - Connection edges
     * @param {string} nodeId - Way node ID
     * @returns {{roomAId:string, roomAName:string, roomADir:string, roomBId:string, roomBName:string, roomBDir:string}}
     */
    wayView._parseConnections = function(connEdges, nodeId) {
        const roomNodes = worldState.graph?.nodes || {};
        const wayNode = roomNodes[nodeId];
        const props = wayNode?.properties || {};

        // Collect the distinct area→way edges (canonical direction carriers).
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
        // Prefer area_from / area_to props (the intended pair).
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

        // Resolve area names from node IDs
        roomAName = roomNodes[roomAId]?.name || roomAId;
        roomBName = roomNodes[roomBId]?.name || roomBId;

        return { roomAId, roomAName, roomADir, roomBId, roomBName, roomBDir };
    };

    wayView._renderVisibleItemSelect = function(sourceAreaId, wayId, targetAreaName, selectedItems) {
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

    wayView._saveVisibleItems = function(sourceId, wayId, selectEl) {
        const visible_items = Array.from(selectEl.selectedOptions).map(opt => opt.value);
        api.updateEdge(sourceId, wayId, { old_type: 'connection', properties: { visible_items } })
            .then(() => worldState.fetch());
    };

    wayView._saveAllowSeeCharacters = function(sourceId, wayId, checked) {
        api.updateEdge(sourceId, wayId, { old_type: 'connection', properties: { allow_see_characters: !!checked } })
            .then(() => worldState.fetch());
    };

    /**
     * Build the connections section as a lit template (incl. reconnect controls)
     * @param {Array} connEdges - Connection edges
     * @param {object} connInfo - Parsed connection info from _parseConnections
     * @param {string} nodeId - Way node ID
     * @param {string} escapedId - HTML-escaped node ID
     * @returns {string} HTML for the connections section
     */
    wayView._renderConnections = function(connEdges, connInfo, nodeId, escapedId) {
        const { roomAId, roomAName, roomADir, roomBId, roomBName, roomBDir } = connInfo;

        // Build area name → node ID map
        const roomNodes = worldState.graph?.nodes || {};
        const roomNameMap = {};
        Object.entries(roomNodes).forEach(([nodeIdKey, node]) => {
            if (node.type === 'area') {
                roomNameMap[node.name || nodeIdKey] = nodeIdKey;
            }
        });

        // Build area dropdown options
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
                    ${wayView._renderVisibleItemSelect(roomAId, nodeId, roomBName, visibleItemsAB)}
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
                    ${wayView._renderVisibleItemSelect(roomBId, nodeId, roomAName, visibleItemsBA)}
                </div>
                <div class="field"><label>Cardinal (A→B) for map layout</label>
                    ${wayView._renderCompassSelector('conn-a', escapedId, cardinalAB)}
                    <input type="hidden" id="way-side-conn-a-cardinal-${escapedId}" value="${cardinalAB}" onchange="InspectorWayView._updateCardinal('${esc(roomAId)}','${escapedId}','${esc(roomBId)}',this.value)">
                </div>
                <div class="field"><label>Cardinal (B→A) for map layout</label>
                    ${wayView._renderCompassSelector('conn-b', escapedId, cardinalBA)}
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

    /**
     * Reconnect a way to different rooms
     * @param {string} wayId - Way node ID
     */
    wayView._reconnectDoor = async function(wayId) {
        const roomASelect = document.getElementById('way-reconn-a');
        const roomBSelect = document.getElementById('way-reconn-b');
        const dir1Input = document.getElementById('way-reconn-dir1');
        const dir2Input = document.getElementById('way-reconn-dir2');
        if (!roomASelect || !roomBSelect) return;

        const roomAName = roomASelect.value;
        const roomBName = roomBSelect.value;
        if (!roomAName || !roomBName) return;
        if (roomAName === roomBName) { toastInfo('Cannot connect a way to itself.'); return; }

        // Resolve area names to node IDs
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

    // ── Library Save ──────────────────────────────────────────────────

    wayView._extractTriggersFromEdges = function(nodeId) {
        const triggers = [];
        if (!worldState.graph?.edges) return triggers;
        for (const edge of worldState.graph.edges) {
            if (edge.source !== nodeId || edge.type !== 'triggers') continue;
            const ep = edge.properties || {};
            const effects = ep.effects?.length > 0
                ? ep.effects
                : (ep.effect_type
                    ? [{ type: ep.effect_type, params: ep.effect_params || {} }]
                    : []);
            let conditions = ep.conditions || {};
            if (Array.isArray(conditions) || !conditions.operator) {
                const logic = ep.conditions_logic || 'and';
                conditions = Array.isArray(conditions) && conditions.length > 0
                    ? { operator: logic, conditions }
                    : {};
            }
            triggers.push({
                trigger_type: ep.trigger_type || 'on_examine',
                effects,
                target_name: ep.target_name || '',
                target_state: ep.target_state || '',
                conditions,
                success_message: ep.success_message || '',
                fail_message: ep.fail_message || ''
            });
        }
        return triggers;
    };

    wayView._saveToLibrary = async function(nodeId) {
        const node = worldState.getNode(nodeId);
        if (!node || node.type !== 'way') {
            events.log('Cannot save: not a way node.', 'error-msg');
            return;
        }
        const props = node.properties || {};
        const name = node.name || 'Unnamed Way';
        const wayId = name.toLowerCase().replace(/[^a-z0-9_]+/g, '_');
        const triggers = wayView._extractTriggersFromEdges(nodeId);

        const payload = {
            id: wayId,
            name,
            description: props.description || '',
            current_state: props.current_state || 'closed',
                    pass_message: props.pass_message || '',
                    edge_length: props.edge_length || '',
                    sound_barrier: props.sound_barrier ?? '',
                    needs_open: props.needs_open || {},
            auto_close: !!props.auto_close,
            see_through: !!props.see_through,
            one_way: !!props.one_way,
            requires: props.requires || '',
            max_size: props.max_size || '',
            prevent_close: !!props.prevent_close,
            tags: props.tags || [],
            parameters: props.parameters || {},
            triggers
        };

        // Check if library entry already exists
        let existing = {};
        try {
            const libData = await ApiClient.getLibraryType('ways');
            if (libData[wayId]) existing = libData[wayId];
        } catch (e) { /* ignore */ }

        const hasExisting = Object.keys(existing).length > 0;

        if (!hasExisting) {
            const res = await ApiClient.saveLibraryType('ways', payload);
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            events.log(`Saved "${name}" to library.`, 'system-msg');
            return;
        }

        // Conflict — show DiffModal
        const sections = [
            { key: 'name', label: 'Name' },
            { key: 'description', label: 'Description' },
            { key: 'current_state', label: 'State' },
            { key: 'pass_message', label: 'Pass Message' },
            { key: 'needs_open', label: 'Needs Open' },
            { key: 'auto_close', label: 'Auto Close' },
            { key: 'see_through', label: 'See Through' },
            { key: 'sound_barrier', label: 'Sound Barrier' },
            { key: 'tags', label: 'Tags' },
            { key: 'triggers', label: 'Triggers' }
        ];

        const result = await DiffModal.show(existing, payload, sections, {
            title: 'Save Way to Library',
            name
        });

        if (!result) return; // cancelled

        if (result.action === 'update') {
            // Only update selected sections
            const merged = { ...existing };
            for (const key of result.sections) {
                merged[key] = payload[key];
            }
            const res = await ApiClient.saveLibraryType('ways', { id: wayId, data: merged });
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            events.log(`Updated "${name}" in library.`, 'system-msg');
        } else if (result.action === 'duplicate') {
            const dupePayload = { ...payload, id: result.id, name: result.name };
            const merged = { ...dupePayload };
            if (result.sections) {
                for (const key of result.sections) {
                    merged[key] = dupePayload[key];
                }
            }
            const res = await ApiClient.saveLibraryType('ways', { id: result.id, data: merged });
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            events.log(`Saved "${result.name}" as duplicate to library.`, 'system-msg');
        }
    };

    wayView._refreshFromLibrary = async function(nodeId) {
        const node = worldState.getNode(nodeId);
        if (!node || node.type !== 'way') {
            toastInfo('No library_id — cannot refresh.');
            return;
        }
        const props = node.properties || {};
        const name = node.name || 'Unnamed Way';
        const wayId = name.toLowerCase().replace(/[^a-z0-9_]+/g, '_');
        const triggers = wayView._extractTriggersFromEdges(nodeId);

        const currentPayload = {
            name,
            description: props.description || '',
            current_state: props.current_state || 'closed',
            pass_message: props.pass_message || '',
            edge_length: props.edge_length || '',
            sound_barrier: props.sound_barrier ?? '',
            needs_open: props.needs_open || {},
            auto_close: !!props.auto_close,
            see_through: !!props.see_through,
            one_way: !!props.one_way,
            requires: props.requires || '',
            max_size: props.max_size || '',
            prevent_close: !!props.prevent_close,
            tags: props.tags || [],
            parameters: props.parameters || {},
            triggers
        };

        let libEntry = {};
        try {
            const libData = await ApiClient.getLibraryType('ways');
            libEntry = libData[wayId] || {};
        } catch (e) { /* ignore */ }

        if (!Object.keys(libEntry).length) {
            toastInfo('No library entry found for this way. Save to library first.');
            return;
        }

        const sections = [
            { key: 'name', label: 'Name' },
            { key: 'description', label: 'Description' },
            { key: 'current_state', label: 'State' },
            { key: 'pass_message', label: 'Pass Message' },
            { key: 'needs_open', label: 'Needs Open' },
            { key: 'auto_close', label: 'Auto Close' },
            { key: 'see_through', label: 'See Through' },
            { key: 'one_way', label: 'One Way' },
            { key: 'requires', label: 'Requires' },
                { key: 'max_size', label: 'Max Size' },
                { key: 'edge_length', label: 'Edge Length' },
                { key: 'sound_barrier', label: 'Sound Barrier' },
                { key: 'tags', label: 'Tags' },
            { key: 'parameters', label: 'Parameters' },
            { key: 'triggers', label: 'Triggers' }
        ];

        const result = await DiffModal.show(libEntry, currentPayload, sections, {
            title: 'Refresh Way from Library',
            name,
            direction: 'to-world'
        });

        if (!result || !result.sections.length) return;

        const data = await ApiClient.refreshWayFromLibrary(nodeId, result.sections);
        if (data.error) { toastError(data.error); return; }
        await worldState.fetch();
        if (window.VW?.inspector) window.VW.inspector.showNode(nodeId);
        events.log(`Refreshed "${name}" from library: ${data.applied?.join(', ')}`, 'system-msg');
    };

    wayView.improveWayWithAI = async function(nodeId) {
        const system = `You are a procedural way enhancer for a text adventure game. A "way" is a door, passage, or path between two areas. The way data schema supports:

PROPERTIES: current_state (open/closed/locked/blocked/broken/hidden), pass_message (text shown when passing through), needs_open (object with enabled boolean, skill name, and dc number), auto_close (boolean), see_through (boolean), one_way (boolean), requires (passage mode: empty/crawl/climb/jump), max_size (largest size that fits through: empty/tiny/small/normal/huge/giant/titanic), sound_barrier (optional number: how much speech penetration this door blocks when closed/blocked/locked — 1 = normal door, 2 = vault-thick, omit for default), edge_length (number 20-500 for graph layout)

OUTPUT FORMAT: Respond with ONLY raw JSON. No markdown, no code fences, just JSON.`;

        const buildPrompt = (node, lockedFields) => {
            const name = node.name || '';
            const props = node.properties || {};
            const description = props.description || '';
            const promptLines = [`Way Name: ${name}`];
            if (!lockedFields.includes('description')) promptLines.push(`Description: ${description}`);
            promptLines.push('');
            promptLines.push('Current properties:');
            if (!lockedFields.includes('current_state')) promptLines.push(`- current_state: ${props.current_state || 'closed'}`);
            if (!lockedFields.includes('pass_message')) promptLines.push(`- pass_message: ${props.pass_message || ''}`);
            if (!lockedFields.includes('needs_open')) promptLines.push(`- needs_open: ${JSON.stringify(props.needs_open || {})}`);
            if (!lockedFields.includes('auto_close')) promptLines.push(`- auto_close: ${!!props.auto_close}`);
            if (!lockedFields.includes('see_through')) promptLines.push(`- see_through: ${!!props.see_through}`);
            if (!lockedFields.includes('one_way')) promptLines.push(`- one_way: ${!!props.one_way}`);
            if (!lockedFields.includes('requires')) promptLines.push(`- requires: ${props.requires || 'none'}`);
            if (!lockedFields.includes('max_size')) promptLines.push(`- max_size: ${props.max_size || 'none'}`);
            if (!lockedFields.includes('edge_length')) promptLines.push(`- edge_length: ${props.edge_length || 'auto'}`);
            if (!lockedFields.includes('tags')) promptLines.push(`- tags: ${(props.tags || []).join(', ')}`);
            if (!lockedFields.includes('parameters')) promptLines.push(`- parameters: ${JSON.stringify(props.parameters || {})}`);

            promptLines.push('');
            promptLines.push('Improve this way\'s description and properties. Make the description richer and more atmospheric — describe how the way looks, feels, sounds. Suggest appropriate state, pass messages, skill checks, passage requirements (requires: crawl/climb/jump if the passage physically demands it), size limits (max_size for tight gaps), and behavior flags that match the mood. Return the full way as JSON with name, description, current_state, pass_message, needs_open, auto_close, see_through, one_way, requires, max_size, edge_length, tags, and parameters fields.');
            return promptLines.join('\n');
        };

        const apply = (parsed, node, lockedFields, update) => {
            if (parsed.name) update.name = parsed.name;
            const props = node.properties || {};
            const propUpdate = {};
            if (parsed.description !== undefined && !lockedFields.includes('description')) propUpdate.description = parsed.description;
            if (parsed.current_state !== undefined && !lockedFields.includes('current_state')) propUpdate.current_state = parsed.current_state;
            if (parsed.pass_message !== undefined && !lockedFields.includes('pass_message')) propUpdate.pass_message = parsed.pass_message;
            if (parsed.needs_open && !lockedFields.includes('needs_open')) propUpdate.needs_open = parsed.needs_open;
            if (parsed.auto_close !== undefined && !lockedFields.includes('auto_close')) propUpdate.auto_close = !!parsed.auto_close;
            if (parsed.see_through !== undefined && !lockedFields.includes('see_through')) propUpdate.see_through = !!parsed.see_through;
            if (parsed.one_way !== undefined && !lockedFields.includes('one_way')) propUpdate.one_way = !!parsed.one_way;
            if (parsed.requires !== undefined && !lockedFields.includes('requires')) propUpdate.requires = ['crawl', 'climb', 'jump'].includes(parsed.requires) ? parsed.requires : '';
            if (parsed.max_size !== undefined && !lockedFields.includes('max_size')) propUpdate.max_size = ['tiny', 'small', 'normal', 'huge', 'giant', 'titanic'].includes(parsed.max_size) ? parsed.max_size : '';
            if (parsed.edge_length !== undefined && !lockedFields.includes('edge_length')) propUpdate.edge_length = parsed.edge_length;
            if (parsed.tags && !lockedFields.includes('tags')) {
                propUpdate.tags = Array.isArray(parsed.tags) ? parsed.tags : parsed.tags.split(',').map(t => t.trim());
            }
            if (parsed.parameters && !lockedFields.includes('parameters')) {
                propUpdate.parameters = parsed.parameters;
            }
            if (Object.keys(propUpdate).length > 0) update.properties = propUpdate;
        };

        await InspectorHelpers.improveWithAI(nodeId, { btnId: 'improve-way-btn', system, buildPrompt, apply });
    };

    // Register the template-sync pattern for ways.
    if (window.InspectorTemplateSync) {
        window.InspectorTemplateSync.register('way', {
            title: 'Refresh Way from Library',
            buildWorldPayload(nodeId) {
                const node = worldState.getNode(nodeId);
                if (!node) return null;
                const props = node.properties || {};
                return {
                    name: node.name || '',
                    description: props.description || '',
                    current_state: props.current_state || 'closed',
            pass_message: props.pass_message || '',
            edge_length: props.edge_length || '',
            sound_barrier: props.sound_barrier ?? '',
            needs_open: props.needs_open || {},
            auto_close: !!props.auto_close,
            see_through: !!props.see_through,
            one_way: !!props.one_way,
            requires: props.requires || '',
            max_size: props.max_size || '',
            prevent_close: !!props.prevent_close,
            tags: props.tags || [],
                    parameters: props.parameters || {},
                    triggers: wayView._extractTriggersFromEdges(nodeId),
                };
            },
            sections: [
                { key: 'name', label: 'Name' },
                { key: 'description', label: 'Description' },
                { key: 'current_state', label: 'State' },
                { key: 'pass_message', label: 'Pass Message' },
                { key: 'needs_open', label: 'Needs Open' },
                { key: 'auto_close', label: 'Auto Close' },
                { key: 'see_through', label: 'See Through' },
                { key: 'one_way', label: 'One Way' },
                { key: 'prevent_close', label: 'Prevent Closing' },
                { key: 'requires', label: 'Requires' },
                { key: 'max_size', label: 'Max Size' },
                { key: 'edge_length', label: 'Edge Length' },
                { key: 'sound_barrier', label: 'Sound Barrier' },
                { key: 'tags', label: 'Tags' },
                { key: 'parameters', label: 'Parameters' },
                { key: 'triggers', label: 'Triggers' },
            ],
        });
    }

    return wayView;
})();
