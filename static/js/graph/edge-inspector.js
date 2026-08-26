const EdgeInspector = (() => {
    // Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

    const findWorldEdges = (fromId, toId) => {
        if (!worldState.graph?.edges) return [];
        return worldState.graph.edges.filter(e => e.source === fromId && e.target === toId);
    };

    // Re-render after a mutation so props added/deleted show up immediately.
    const refresh = (edge) => worldState.fetch().then(() => render(edge));

    const render = (edge) => {
        const fromNode = graphManager.nodes.get(edge.from);
        const toNode = graphManager.nodes.get(edge.to);
        const fromId = fromNode?.id || edge.from;
        const toId = toNode?.id || edge.to;
        let rawType = edge.type || 'connection';

        // Resolve the exact edge type against world state: the viewer edge now
        // carries a type, but verify it against an edge matching BOTH
        // endpoints so an area-edge collapsed pair or a stale vis edge never
        // resolves to a wrong old_type (which makes update_edge 404).
        if (worldState.graph?.edges) {
            const both = worldState.graph.edges.filter(e => e.source === edge.from && e.target === edge.to);
            const exact = both.find(e => e.type === rawType);
            if (!exact && both.length > 0) rawType = both[0].type || 'connection';
        }

        const cfg = EdgeTypes.getConfig(rawType);
        const displayLabel = edge.label || edge.type || 'connection';
        const fromName = fromNode?.name || edge.from;
        const toName = toNode?.name || edge.to;

        const typeOptions = Object.entries(EdgeTypes.ALL).map(([key, t]) =>
            htmlTag`<option value=${key} ?selected=${rawType === key}>${t.icon} ${t.label}</option>`
        );

        // Props list read from worldState edges so saved changes are reflected.
        const edges = findWorldEdges(fromId, toId);
        const propRows = [];
        if (edges.length === 0) {
            propRows.push(htmlTag`<div style="color:var(--text-muted);font-size:10px;">No properties</div>`);
        }
        edges.forEach((edgeItem, idx) => {
            const props = edgeItem.properties || {};
            const keys = Object.keys(props);
            if (keys.length === 0) {
                propRows.push(htmlTag`<div style="color:var(--text-muted);font-size:10px;margin:2px 0;">Edge ${idx + 1}: no properties</div>`);
                return;
            }
            propRows.push(htmlTag`<div style="font-size:9px;color:var(--text-dim);margin:4px 0 2px;">Edge ${idx + 1}</div>`);
            keys.forEach(key => {
                const val = typeof props[key] === 'object' ? JSON.stringify(props[key]) : String(props[key]);
                propRows.push(htmlTag`
                    <div style="display:flex;gap:4px;align-items:center;margin:2px 0;">
                        <input type="text" value=${key} disabled style="width:35%;font-size:10px;background:var(--bg-inset);border:1px solid var(--border);border-radius:3px;padding:2px 4px;color:var(--text-muted);">
                        <input type="text" value=${val} @change=${(ev) => graphManager._saveEdgeProperty(fromId, toId, key, ev.target.value)} style="flex:1;font-size:10px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;padding:2px 4px;">
                        <button class="btn btn-sm btn-red" @click=${() => graphManager._deleteEdgeProperty(fromId, toId, key).then(() => refresh(edge))} style="font-size:9px;padding:1px 4px;">✕</button>
                    </div>`);
            });
        });

        const template = htmlTag`
            <div class="inspector-header animate__animated animate__fadeIn">
                <span class="inspector-type-badge" style="background:${cfg.color}">${cfg.icon} Edge</span>
                <h2 style="margin:0;font-size:14px;"><span style="color:${cfg.color}">${displayLabel}</span></h2>
                <button class="btn btn-sm btn-ghost" @click=${() => hideInspectorPanel()}>✕</button>
            </div>
            <div class="inspector-section animate__animated animate__fadeIn animate__delay-1s">
                <div class="relationship-item" style="cursor:pointer;" @click=${() => VW.inspector.showNode(fromId)}>
                    🧩 ${fromName} <span style="color:var(--text-muted);font-size:10px;">(${fromNode?.type})</span>
                </div>
                <div class="relationship-item" style="cursor:pointer;" @click=${() => VW.inspector.showNode(toId)}>
                    → 🧩 ${toName} <span style="color:var(--text-muted);font-size:10px;">(${toNode?.type})</span>
                </div>
            </div>
            <div class="inspector-section animate__animated animate__fadeIn animate__delay-1s">
                <label style="font-size:10px;font-weight:600;">Edge Type</label>
                <select id="edge-type-select" style="width:100%;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;" @change=${(ev) => graphManager._changeEdgeType(fromId, toId, rawType, ev.target.value)}>
                    ${typeOptions}
                </select>
            </div>
            <div class="inspector-section" id="edge-props-section">
                <label style="font-size:10px;font-weight:600;">Properties</label>
                <div id="edge-props-list" style="font-size:11px;">${propRows}</div>
                <button class="btn btn-sm" @click=${() => graphManager._addEdgeProperty(fromId, toId, rawType).then(() => refresh(edge))} style="font-size:10px;margin-top:4px;">+ Add Property</button>
            </div>
            <div style="padding:0 16px 8px;display:flex;gap:6px;">
                <button class="btn btn-sm btn-red" @click=${() => graphManager._deleteEdge(fromId, toId, rawType)}>🗑️ Delete Edge</button>
            </div>`;

        window.InspectorPanel.render(template);
    };

    return { render, renderEdgeInspector: render };
})();

window.EdgeInspector = EdgeInspector;