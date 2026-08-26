/**
 * InspectorMemory — Character memory management (structured memories, flat world knowledge)
 * Extracted from inspector.js for modularity.
 */

window.InspectorMemory = (() => {
    const M = {};

    M.renderMemoriesHtml = function(agentName, player, escName, esc) {
        let html = `<div class="inspector-section" id="memory-section-${escName}">
            <h3>🧠 Memories</h3>
            <input type="text" id="mem-filter-${escName}" placeholder="Filter memories..."
                style="width:100%;font-size:10px;padding:3px 6px;margin-bottom:4px;box-sizing:border-box;"
                oninput="InspectorMemory.filterMemories('${escName}', this.value)">
            <div id="memory-list-${escName}" style="max-height:300px;overflow-y:auto;margin-bottom:4px;">`;
        const memories = player.memories || [];
        const memIcon = (t) => ({observation:'👁️',discovery:'💡',conversation:'💬',item:'📦',combat:'⚔️',exploration:'🗺️',failure:'⚠️',success:'✅',reflection:'🔄',action:'▶️',speech:'💬',thought:'🤔',reaction:'💭',location:'📍'}[t]||'📝');
        const impColor = (i) => i >= 8 ? '#e05555' : i >= 6 ? '#e0a33c' : i >= 4 ? '#4caf50' : '#888';
        const currentTick = VW?.state?.tick ?? 0;
        if (memories.length > 0) {
            const sorted = [...memories].reverse();
            sorted.forEach((m) => {
                const tick = m.tick ?? 0;
                const imp = m.importance ?? 5;
                const loc = m.location || '';
                const tags = Array.isArray(m.tags) ? m.tags.filter(Boolean) : [];
                const suppressions = Array.isArray(m.suppressions) ? m.suppressions : [];
                const isSuppressed = suppressions.length > 0;
                const salience = m.salience_override || 0;
                const source = m.source || 'auto';
                const tagHtml = tags.length
                    ? `<div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:4px;">${tags.map(t => `<span style="font-size:9px;padding:1px 6px;border-radius:8px;background:var(--bg-input);border:1px solid var(--border);color:var(--text-muted);">#${String(t).toLowerCase()}</span>`).join('')}</div>`
                    : '';
                const sourceLabel = source === 'manual' ? '<span style="font-size:9px;color:var(--accent);border:1px solid var(--accent);border-radius:8px;padding:0 5px;margin-left:4px;">SEED</span>' : `<span style="font-size:9px;color:var(--text-muted);border:1px solid var(--border);border-radius:8px;padding:0 5px;margin-left:4px;">src:${esc(source)}</span>`;
                const suppressBadge = isSuppressed ? `<span style="font-size:9px;color:#e05555;border:1px solid #e05555;border-radius:8px;padding:0 5px;margin-left:4px;">🚫 SUPPRESSED</span>` : '';
                const salienceBadge = salience > 0 ? `<span style="font-size:9px;color:#4caf50;border:1px solid #4caf50;border-radius:8px;padding:0 5px;margin-left:4px;">⚡ salience ${salience}</span>` : '';
                const opacity = isSuppressed ? 'opacity:0.5;' : '';
                html += `<div class="memory-entry" data-text="${esc((m.text||'').toLowerCase())}" data-tags="${esc((tags||[]).join(',').toLowerCase())}" style="background:var(--bg-card);border:1px solid var(--border);border-left:3px solid ${isSuppressed ? '#888' : impColor(imp)};border-radius:6px;padding:7px;margin-bottom:5px;font-size:11px;${opacity}">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;">
                        <div style="flex:1;min-width:0;">
                            <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
                                <span style="color:var(--text-dim);font-size:10px;">[${events.tickToTime(tick)}]</span>
                                <span style="font-size:10px;font-weight:600;">${memIcon(m.type)} ${m.type}</span>
                                ${sourceLabel}
                                ${suppressBadge}
                                ${salienceBadge}
                                <span style="font-size:10px;color:${isSuppressed ? '#888' : impColor(imp)};font-weight:600;margin-left:auto;">⭐ ${imp}</span>
                            </div>
                            <div style="margin-top:3px;line-height:1.4;">${m.text || ''}</div>
                            ${tagHtml}
                            ${loc ? `<span style="font-size:10px;color:var(--text-muted);">📍 ${loc}</span>` : ''}
                        </div>
                        <div style="display:flex;gap:2px;flex-shrink:0;flex-direction:column;align-items:flex-end;">
                            <div style="display:flex;gap:2px;">
                                <button class="btn btn-sm" onclick="InspectorMemory.editMemory('${escName}','${m.id||''}')" style="font-size:9px;padding:1px 4px;" title="Edit">✏️</button>
                                ${isSuppressed
                                    ? `<button class="btn btn-sm" onclick="InspectorMemory.unblockMemory('${escName}','${m.id||''}')" style="font-size:9px;padding:1px 4px;color:#4caf50;" title="Unblock">🔓</button>`
                                    : `<button class="btn btn-sm" onclick="InspectorMemory.suppressMemory('${escName}','${m.id||''}')" style="font-size:9px;padding:1px 4px;color:#e0a33c;" title="Suppress">🚫</button>`
                                }
                                <button class="btn btn-sm btn-red" onclick="InspectorMemory.deleteMemory('${escName}','${m.id||''}')" style="font-size:9px;padding:1px 4px;" title="Delete">🗑</button>
                            </div>
                        </div>
                    </div>
                </div>`;
            });
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No memories recorded yet.</div>`;
        }
        html += `</div>
            <div style="display:flex;gap:4px;flex-wrap:wrap;">
                <button class="btn btn-sm btn-blue" onclick="InspectorMemory.addMemory('${escName}')">+ Add Memory</button>
                <button class="btn btn-sm btn-red" onclick="if(confirm('Clear all memories for ${escName}?')){ApiClient.clearPlayerMemories('${escName}').then(()=>{if(VW?.inspector) VW.inspector._reRender();});}">🗑 Clear All</button>
                <button class="btn btn-sm" onclick="InspectorMemory.clearExpired('${escName}')" style="font-size:9px;">🧹 Clear Expired</button>
            </div>
        </div>`;
        return html;
    };

    M.filterMemories = function(charName, query) {
        const list = document.getElementById(`memory-list-${charName}`);
        if (!list) return;
        const q = query.toLowerCase().trim();
        const entries = list.querySelectorAll('.memory-entry');
        entries.forEach(el => {
            const text = el.dataset.text || '';
            const tags = el.dataset.tags || '';
            const match = !q || text.includes(q) || tags.includes(q);
            el.style.display = match ? '' : 'none';
        });
    };

    M.addMemory = function(charName) {
        M.showMemoryEditor(charName, null);
    };

    M.editMemory = function(charName, entryId) {
        M.showMemoryEditor(charName, entryId);
    };

    M.suppressMemory = function(charName, entryId) {
        ApiClient.suppressPlayerMemory(charName, { tags: [], duration: 1 }).then(() => {
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        });
    };

    M.unblockMemory = function(charName, entryId) {
        ApiClient.unblockPlayerMemory(charName, {}).then(() => {
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        });
    };

    M.clearExpired = function(charName) {
        const currentTick = VW?.state?.tick ?? 0;
        ApiClient.clearExpiredSuppressions(charName, currentTick).then(() => {
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        });
    };

    M.showMemoryEditor = function(charName, entryId) {
        const player = worldState.players?.[charName];
        if (!player) return;
        const memories = player.memories || [];
        const existing = entryId ? memories.find(m => m.id === entryId) : null;
        const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
        const esc = InspectorHelpers.esc;
        const escName = charName.replace(/'/g, "\\'");
        const currentTick = VW?.state?.tick ?? 0;

        const types = ['observation','conversation','location','event','thought','reflection','discovery','combat','speech','reaction'];
        const typeOpts = types.map(t => htmlTag`<option value=${t} ?selected=${existing?.type === t}>${t}</option>`);

        const modal = htmlTag`<div class="modal-content" style="max-width:520px;">
            <h3>${existing ? '✏️ Edit Memory' : '➕ Add Memory'}</h3>
            <label style="font-size:11px;">Content</label>
            <textarea id="mem-editor-content" rows="3" style="width:100%;font-size:11px;">${existing ? existing.text : ''}</textarea>
            <div style="display:flex;gap:8px;margin:8px 0;flex-wrap:wrap;">
                <div style="flex:1;min-width:80px;">
                    <label style="font-size:10px;">Type</label>
                    <select id="mem-editor-type" style="width:100%;font-size:11px;">${typeOpts}</select>
                </div>
                <div style="width:70px;">
                    <label style="font-size:10px;">Importance (1-10)</label>
                    <input type="number" id="mem-editor-importance" min="1" max="10" value="${existing?.importance ?? 5}" style="width:100%;font-size:11px;">
                </div>
                <div style="width:70px;">
                    <label style="font-size:10px;">Tick</label>
                    <input type="number" id="mem-editor-tick" value="${existing?.tick ?? currentTick}" style="width:100%;font-size:11px;">
                </div>
            </div>
            <div style="display:flex;gap:8px;margin:8px 0;flex-wrap:wrap;">
                <div style="flex:1;min-width:120px;">
                    <label style="font-size:10px;">Source</label>
                    <input type="text" id="mem-editor-source" value="${existing ? esc(existing.source || 'auto') : 'auto'}" style="width:100%;font-size:11px;" placeholder="auto / manual / trigger">
                </div>
                <div style="flex:1;min-width:120px;">
                    <label style="font-size:10px;">Location</label>
                    <input type="text" id="mem-editor-location" value="${existing ? existing.location || '' : ''}" style="width:100%;font-size:11px;" placeholder="Area name">
                </div>
            </div>
            <label style="font-size:10px;">Tags</label>
            <div id="mem-editor-tags"></div>
            ${existing ? `<div style="margin-top:8px;display:flex;gap:6px;align-items:center;">
                <span style="font-size:10px;color:var(--text-muted);">Suppressions:</span>
                <span style="font-size:10px;color:${(existing.suppressions && existing.suppressions.length) ? '#e05555' : '#4caf50'};">
                    ${(existing.suppressions && existing.suppressions.length) ? '🚫 Blocked (' + existing.suppressions.length + ')' : 'None'}
                </span>
                ${(existing.suppressions && existing.suppressions.length) ? `<button class="btn btn-sm" onclick="InspectorMemory.unblockMemory('${escName}','${existing.id}');this.closest('.modal-overlay').remove();" style="font-size:9px;">🔓 Unblock</button>` : ''}
            </div>` : ''}
            <div style="display:flex;gap:4px;justify-content:flex-end;margin-top:10px;">
                <button class="btn btn-sm btn-ghost" @click=${() => M._closeMemoryEditor()}>Cancel</button>
                <button class="btn btn-sm btn-green" @click=${() => M.saveMemory(charName, entryId || '')}>💾 Save</button>
            </div>
        </div>`;
const container = document.createElement('div');
        container.className = 'modal-overlay';
        container.id = 'mem-editor-modal';
        document.body.appendChild(container);
        window.Lit.render(modal, container);
        if (window.TagMultiselect) {
            const tagsEl = document.getElementById('mem-editor-tags');
            if (tagsEl) {
                M._tagSelect = new TagMultiselect(tagsEl, {
                    tags: Array.isArray(existing?.tags) ? existing.tags : [],
                    placeholder: 'Search or create tags...',
                    allowNew: true,
                    onChange: (tags) => { M._tagSelectTags = tags; }
                });
            }
        }
    };

M._closeMemoryEditor = function() {
        const modal = document.getElementById('mem-editor-modal');
        if (modal) modal.remove();
    };

    /**
     * Save a memory from the editor modal
     * @param {string} charName - Character name
     * @param {string} entryId - Memory entry ID (empty string for new)
     */
    M.saveMemory = function(charName, entryId) {
        const content = document.getElementById('mem-editor-content')?.value?.trim();
        if (!content) return;
        const type = document.getElementById('mem-editor-type')?.value || 'observation';
        const importance = parseInt(document.getElementById('mem-editor-importance')?.value) || 5;
        const tick = parseInt(document.getElementById('mem-editor-tick')?.value) || 0;
        const location = document.getElementById('mem-editor-location')?.value || '';
        const source = document.getElementById('mem-editor-source')?.value || 'auto';
        const tags = M._tagSelect ? M._tagSelect.getValue() : (M._tagSelectTags || []);

        const done = () => {
            M._closeMemoryEditor();
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        };

        const payload = { text: content, type, importance, tick, location, tags, source };

        if (entryId) {
            ApiClient.updatePlayerMemory(charName, entryId, payload).then(done);
        } else {
            ApiClient.addPlayerMemory(charName, payload).then(done);
        }
    };

    M.deleteMemory = function(charName, entryId) {
        if (!entryId) {
            console.warn('[InspectorMemory] deleteMemory called without entryId for', charName);
            return;
        }
        ApiClient.deletePlayerMemory(charName, entryId).then(() => {
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        });
    };

    return M;
})();
