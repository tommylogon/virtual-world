/**
 * InspectorMemory — Character memory management (structured memories, flat world knowledge)
 * Extracted from inspector.js for modularity.
 */

window.InspectorMemory = (() => {
    const M = {};

    // Rich memory-emotion vocabulary, grouped for the picker. Multiple emotions
    // may be attached to one memory (stored as memory_emotions: [{label,intensity}]).
    const EMOTION_GROUPS = [
        { label: 'Core', items: ['neutral','happy','sad','angry','afraid','surprised','disgusted'] },
        { label: 'Warm / Social', items: ['affectionate','hopeful','grateful','proud','amused','loved','admiring','excited'] },
        { label: 'Anxious / Tense', items: ['anxious','nervous','worried','uneasy','spooked','unnerved','restless','dread','paranoid'] },
        { label: 'Arousal / Desire', items: ['aroused','eager','hungry','craving','curious','mischievous'] },
        { label: 'Down / Heavy', items: ['lonely','ashamed','guilty','embarrassed','wistful','melancholic','hollow','tired','bored'] },
        { label: 'Calm / Content', items: ['calm','content','peaceful','relieved','satisfied','quiet','safe'] },
        { label: 'Determined / Bold', items: ['determined','brave','resolute','defiant','focused'] },
        { label: 'Jealous / Bitter', items: ['jealous','envious','frustrated','resentful','bitter'] }
    ];

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
                const memEmotions = Array.isArray(m.memory_emotions) && m.memory_emotions.length
                    ? m.memory_emotions
                    : (m.emotion && m.emotion.label ? [m.emotion] : []);
                const emoHtml = memEmotions.length
                    ? `<div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:4px;">${memEmotions.map(e => `<span style="font-size:9px;padding:1px 6px;border-radius:8px;background:var(--bg-input);border:1px solid var(--border);color:#e0a33c;">${String(e.label || '').toLowerCase()}${e.intensity ? ' · ' + e.intensity : ''}</span>`).join('')}</div>`
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
                            ${emoHtml}
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
                <button class="btn btn-sm btn-green" onclick="InspectorMemory.generateMemory('${escName}')" title="Write a first-person seed memory via the LLM">✨ Gen Memory</button>
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
        const nothing = window.Lit.nothing;
        const esc = InspectorHelpers.esc;
        const escName = charName.replace(/'/g, "\\'");
        const currentTick = VW?.state?.tick ?? 0;

        const types = ['observation','conversation','location','event','thought','reflection','discovery','combat','speech','reaction','item','exploration','action','failure','success'];
        const typeOpts = types.map(t => htmlTag`<option value=${t} ?selected=${existing?.type === t}>${t}</option>`);

        const tick = existing?.tick ?? currentTick;
        const preTicks = tick < 0 ? -tick : 0;

        const emo = (existing && existing.emotion && typeof existing.emotion === 'object') ? existing.emotion : null;
        const emoLbl = emo?.label || 'neutral';
        const emoInt = emo?.intensity || 0;
        const emoOptions = ['neutral','happy','sad','afraid','angry','envious','affectionate','disgusted'];
        const emoOpts = emoOptions.map(l => htmlTag`<option value=${l} ?selected=${emoLbl === l}>${l}</option>`);

        const embedEnabled = !!(window.EmbeddingClient && window.EmbeddingClient.configured());
        const salience = existing?.salience_override || 0;

        const modal = htmlTag`<div class="modal-content memedit-modal">
            <div class="modal-header" style="border-bottom:none;padding:16px 20px 6px;">
                <h3 style="font-size:15px;font-weight:700;">${existing ? '✏️ Edit Memory' : '➕ Add Memory'}</h3>
            </div>
            <div style="padding:0 20px 16px;">
                <div class="memedit-section">
                    <div class="memedit-section-title">📝 Content</div>
                    <label style="font-size:11px;">Content</label>
                    <textarea id="mem-editor-content" rows="3" class="memedit-textarea" style="min-height:74px;">${existing ? existing.text : ''}</textarea>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">🏷️ Classification</div>
                    <div class="memedit-grid">
                        <div class="memedit-field" style="flex:1.4;">
                            <label>Type</label>
                            <select id="mem-editor-type">${typeOpts}</select>
                        </div>
                        <div class="memedit-field" style="flex:.8;">
                            <label>Importance (1-10)</label>
                            <input type="number" id="mem-editor-importance" min="1" max="10" value="${existing?.importance ?? 5}">
                        </div>
                        <div class="memedit-field" style="flex:.8;">
                            <label>Tick</label>
                            <input type="number" id="mem-editor-tick" value="${tick}">
                            <div class="memedit-hint">negative = before start</div>
                        </div>
                        <div class="memedit-field" style="flex:.95;">
                            <label>Turns before start</label>
                            <input type="number" id="mem-editor-prestart" min="0" value="${preTicks}" placeholder="0">
                            <div class="memedit-hint">simulate pre-scenario age</div>
                        </div>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">🌐 Context</div>
                    <div class="memedit-grid">
                        <div class="memedit-field">
                            <label>Source</label>
                            <input type="text" id="mem-editor-source" value="${existing ? esc(existing.source || 'auto') : 'auto'}" placeholder="auto / manual / trigger">
                        </div>
                        <div class="memedit-field">
                            <label>Location</label>
                            <input type="text" id="mem-editor-location" value="${existing ? existing.location || '' : ''}" placeholder="Area name">
                        </div>
                        <div class="memedit-field" style="flex:.7;">
                            <label>Salience (0-10)</label>
                            <input type="number" id="mem-editor-salience" min="0" max="10" value="${salience}" placeholder="0">
                            <div class="memedit-hint">recall boost</div>
                        </div>
                    </div>
                    <div class="memedit-field">
                        <label>Entity references (areas / items / characters)</label>
                        <div id="mem-editor-entities" class="memedit-entitybox"></div>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">😊 Emotions (multiple)</div>
                    <div class="memedit-field">
                        <label>Attached emotions</label>
                        <div id="mem-editor-emotions" class="memedit-entitybox"></div>
                    </div>
                    <div class="memedit-field">
                        <label>Tags</label>
                        <div id="mem-editor-tags" style="background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:6px;"></div>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">🧠 Semantic</div>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                        <span style="font-size:11px;color:var(--text-muted);">Semantic memory:</span>
                        <span id="mem-editor-embed-status" class="memedit-status" style="color:${embedEnabled ? '#4caf50' : '#9aa4b2'};">${embedEnabled ? 'configured' : 'disabled'}</span>
                        ${existing ? htmlTag`<button class="btn btn-sm" id="mem-editor-embed-btn" style="font-size:10px;">🧠 Generate Embedding</button>` : nothing}
                    </div>
                    ${existing && existing.suppressions && existing.suppressions.length
                        ? htmlTag`<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:8px;">
                            <span style="font-size:11px;color:var(--text-muted);">Suppressions:</span>
                            <span style="font-size:10px;color:#e05555;">🚫 Blocked (${existing.suppressions.length})</span>
                            <button class="btn btn-sm" onclick="InspectorMemory.unblockMemory('${escName}','${existing.id}');document.getElementById('mem-editor-modal')?.remove();" style="font-size:10px;">🔓 Unblock</button>
                          </div>`
                        : nothing}
                </div>
            </div>
            <div class="memedit-foot">
                <button class="btn btn-sm btn-ghost" @click=${() => M._closeMemoryEditor()}>Cancel</button>
                <button class="btn btn-sm btn-green" @click=${() => M.saveMemory(charName, entryId || '')}>💾 Save</button>
            </div>
        </div>`;
        const container = document.createElement('div');
        container.className = 'modal-overlay';
        container.id = 'mem-editor-modal';
        document.body.appendChild(container);
        window.Lit.render(modal, container);

        // Tag multiselect
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

        // Entity-reference multiselect
        M._entitySelected = new Set((existing?.entity_ids || []).filter(Boolean));
        const entEl = document.getElementById('mem-editor-entities');
        if (entEl) M._attachEntitySelector(entEl);

        // Multi-emotion picker
        const emoEl = document.getElementById('mem-editor-emotions');
        if (emoEl) {
            const initial = Array.isArray(existing?.memory_emotions)
                ? existing.memory_emotions
                : (existing?.emotion ? [existing.emotion] : []);
            M._attachEmotionSelector(emoEl, initial);
        }

        // Embedding button (existing memories only)
        const embedBtn = container.querySelector('#mem-editor-embed-btn');
        if (embedBtn) {
            embedBtn.addEventListener('click', () => {
                const status = container.querySelector('#mem-editor-embed-status');
                const text = container.querySelector('#mem-editor-content')?.value || '';
                status.textContent = 'embedding…'; status.style.color = '#9aa4b2';
                M._embedForEntry(charName, existing.id, text).then(ok => {
                    status.textContent = ok ? '✓ embedding saved' : '✗ embed failed';
                    status.style.color = ok ? '#4caf50' : '#e05555';
                });
            });
        }
    };

    /**
     * Build a searchable multi-select of world entities (areas / items /
     * characters) and bind it to M._entitySelected. The selected ids become the
     * memory's entity_ids.
     */
    M._attachEntitySelector = function(container) {
        const nodes = worldState.graph?.nodes || {};
        const opts = [];
        for (const id in nodes) {
            const n = nodes[id];
            if (!n || !n.name) continue;
            opts.push({ id, name: n.name, type: n.type });
        }
        for (const cname in (worldState.players || {})) {
            const cid = 'player_' + cname.toLowerCase().replace(/\s+/g, '_');
            if (!opts.some(o => o.id === cid)) opts.push({ id: cid, name: cname, type: 'character' });
        }
        opts.sort((a, b) => a.name.localeCompare(b.name));

        container.innerHTML = '';
        container.classList.add('memedit-entitybox');
        const input = document.createElement('input');
        input.className = 'memedit-search';
        input.placeholder = 'Search entities...';
        const list = document.createElement('div');
        list.className = 'memedit-entitylist';
        const typeIcon = (t) => ({area:'🗺️',item:'📦',way:'🚪',character:'🧑'}[t] || '•') + ' ';
        const selectedChips = document.createElement('div');
        selectedChips.className = 'memedit-chips';

        function renderChips() {
            const names = opts().filter(o => M._entitySelected.has(o.id)).map(o => o.name);
            selectedChips.textContent = names.length ? 'Linked: ' + names.join(', ') : 'None linked yet';
        }
        function ops() { return opts.filter(o => !input.value || o.name.toLowerCase().includes(input.value.toLowerCase())); }
        function render() {
            list.innerHTML = '';
            const matches = ops();
            if (matches.length === 0) { list.textContent = 'No matches.'; return; }
            matches.forEach(o => {
                const row = document.createElement('label');
                row.className = 'memedit-entityrow';
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.checked = M._entitySelected.has(o.id);
                cb.addEventListener('change', () => {
                    if (cb.checked) M._entitySelected.add(o.id); else M._entitySelected.delete(o.id);
                    renderChips();
                });
                const txt = document.createElement('span');
                txt.textContent = typeIcon(o.type) + o.name + ' (' + o.type + ')';
                row.append(cb, txt);
                list.appendChild(row);
            });
        }
        input.addEventListener('input', render);
        container.append(selectedChips, input, list);
        renderChips();
        render();
    };

    M._closeMemoryEditor = function() {
        const modal = document.getElementById('mem-editor-modal');
        if (modal) modal.remove();
    };

    /**
     * Embed the given text and upsert the vector for <char>::<id>. Returns a
     * promise resolving true on success / false on failure or disabled.
     */
    M._embedForEntry = function(charName, entryId, text) {
        if (!entryId || !window.EmbeddingClient?.configured()) return Promise.resolve(false);
        return EmbeddingClient.embed(text).then(vector => {
            if (!vector) return false;
            return fetch('/api/memory/embeddings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    items: [{ key: `${charName}::${entryId}`, vector }],
                    model: config.embedModel,
                    dims: vector.length
                })
            }).then(r => r.ok).catch(() => false);
        }).catch(() => false);
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
        const prestart = parseInt(document.getElementById('mem-editor-prestart')?.value) || 0;
        const tickInput = parseInt(document.getElementById('mem-editor-tick')?.value) || 0;
        // "Turns before start" wins: a value > 0 places the memory before the
        // scenario (negative tick); otherwise the raw tick field is used.
        const tick = prestart > 0 ? -prestart : tickInput;
        const location = document.getElementById('mem-editor-location')?.value || '';
        const source = document.getElementById('mem-editor-source')?.value || 'auto';
        const salience = parseInt(document.getElementById('mem-editor-salience')?.value) || 0;
        const emotions = Array.isArray(M._emoSelected)
            ? M._emoSelected.filter(e => e && e.label && e.label !== 'neutral')
            : [];
        const tags = M._tagSelect ? M._tagSelect.getValue() : (M._tagSelectTags || []);
        const entity_ids = M._entitySelected ? Array.from(M._entitySelected) : [];

        const payload = { text: content, type, importance, tick, location, source, tags, salience_override: salience, force: true };
        if (entity_ids.length) payload.entity_ids = entity_ids;
        if (emotions.length) {
            payload.memory_emotions = emotions;
            payload.emotion = emotions[0]; // primary single, for backward compatibility
        }

        const done = (data) => {
            M._closeMemoryEditor();
            const id = (data && data.entry && data.entry.id) || (data && data.id) || entryId;
            if (id) M._embedForEntry(charName, id, content);
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        };

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

    // --- Memory Generator (first-person seed memories) ---

    /**
     * Open the memory-generator modal. The user describes the kind of memory
     * (a food memory, a nightmare, a dream…) and the LLM writes it in the
     * character's first-person voice as a standalone seed — not tied to the
     * current scene, area, or scenario.
     */
    M.generateMemory = function(charName) {
        const player = worldState.players?.[charName];
        if (!player) return;
        const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
        const esc = InspectorHelpers.esc;
        const types = ['memory','observation','conversation','location','thought','dream','reflection'];
        const typeOpts = types.map(t => htmlTag`<option value=${t} ?selected=${t === 'memory'}>${t}</option>`);
        const emoOptions = ['neutral','happy','sad','afraid','angry','envious','affectionate','disgusted'];
        const emoOpts = emoOptions.map(l => htmlTag`<option value=${l}>${l}</option>`);

        const modal = htmlTag`<div class="modal-content memedit-modal">
            <div class="modal-header" style="border-bottom:none;padding:16px 20px 6px;">
                <h3 style="font-size:15px;font-weight:700;">✨ Generate Memory</h3>
            </div>
            <div style="padding:0 20px 16px;">
                <div class="memedit-section">
                    <div class="memedit-section-title">💡 Idea</div>
                    <p style="font-size:11px;color:var(--text-muted);line-height:1.5;margin:0 0 8px;">Describe the kind of memory you want. It's written in ${charName}'s first-person voice as a standalone seed — not tied to the current scene, area, or scenario.</p>
                    <label style="font-size:11px;">What kind of memory?</label>
                    <textarea id="mem-gen-prompt" rows="2" class="memedit-textarea" style="min-height:56px;" placeholder="e.g. a fond food memory, a recurring nightmare, a dream, a childhood scar, a kept secret..."></textarea>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px;">
                        <button class="btn btn-sm btn-blue" id="mem-gen-run">✨ Generate</button>
                        <span id="mem-gen-status" class="memedit-status">&nbsp;</span>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">🏷️ Options</div>
                    <div class="memedit-grid">
                        <div class="memedit-field" style="flex:1.2;">
                            <label>Type</label>
                            <select id="mem-gen-type">${typeOpts}</select>
                        </div>
                        <div class="memedit-field" style="flex:.8;">
                            <label>Importance (1-10)</label>
                            <input type="number" id="mem-gen-importance" min="1" max="10" value="5">
                        </div>
                    </div>
                    <div class="memedit-field">
                        <label>Attached emotions (multiple)</label>
                        <div id="mem-gen-emotions" class="memedit-entitybox"></div>
                    </div>
                    <div class="memedit-field">
                        <label>Tags (single-word concepts, auto- or hand-edited)</label>
                        <div id="mem-gen-tags" style="background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:6px;"></div>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">📝 Memory preview (editable)</div>
                    <textarea id="mem-gen-result" rows="4" class="memedit-textarea" style="min-height:96px;" placeholder="Generate to draft the memory here, then edit and save."></textarea>
                </div>
            </div>
            <div class="memedit-foot">
                <button class="btn btn-sm btn-ghost" @click=${() => M._closeMemoryEditor()}>Cancel</button>
                <button class="btn btn-sm btn-green" id="mem-gen-save">💾 Save as Memory</button>
            </div>
        </div>`;
        const container = document.createElement('div');
        container.className = 'modal-overlay';
        container.id = 'mem-editor-modal';
        document.body.appendChild(container);
        window.Lit.render(modal, container);
        M._gen = { charName };
        const genEmoEl = container.querySelector('#mem-gen-emotions');
        if (genEmoEl) M._attachEmotionSelector(genEmoEl, []);
        const genTagsEl = container.querySelector('#mem-gen-tags');
        if (genTagsEl && window.TagMultiselect) {
            M._genTagSelect = new TagMultiselect(genTagsEl, {
                tags: [],
                placeholder: 'Search or create tags...',
                allowNew: true,
                onChange: (tags) => { M._genTagSelectTags = tags; }
            });
        }
        container.querySelector('#mem-gen-run').addEventListener('click', () => M._runMemoryGeneration());
        container.querySelector('#mem-gen-save').addEventListener('click', () => M._saveGeneratedMemory());
    };

    /** Build the identity block (personality + appearance) used to frame the
     *  character's voice for the generator. */
    M._identityBlock = function(charName) {
        const player = worldState.players?.[charName] || {};
        let b = 'You are ' + charName + '.';
        if (player.personality) b += ' Personality: ' + String(player.personality).trim();
        if (player.description) b += ' Appearance: ' + String(player.description).trim();
        return b + ' You are authoring your own past memories.';
    };

    M._buildSeedPrompt = function(charName, theme) {
        // Curated emotion vocabulary (from the picker groups) so the model can
        // emit labels that round-trip into the editable picker; custom allowed.
        const vocab = [...new Set(EMOTION_GROUPS.flatMap(g => g.items).filter(l => l !== 'neutral'))];
        const vocabStr = vocab.join(', ');
        return 'Write a short first-person memory for ' + charName + ' about: ' + theme + '.\n'
            + 'Rules:\n'
            + '1) Speak in first person, in ' + charName + '\'s authentic voice and personality.\n'
            + '2) It is a standalone seed memory — do NOT reference any current location, scene, '
            + 'other characters, or in-world events; it may take place anywhere, at any time.\n'
            + '3) Vivid and specific but brief (1-3 sentences, under ~40 words).\n'
            + '4) Return ONLY a JSON object — no code fence, no labels, no preamble — shaped as:\n'
            + '   {"text":"<the memory>","importance":<1-10>,"tags":["<tag>",...],"emotions":[{"label":"<emotion>","intensity":<1-10>},...]}\n'
            + '   - "text": the memory, written in first person.\n'
            + '   - "importance": how significant this memory is to ' + charName + ' (10 = life-changing, 1 = trivial).\n'
            + '   - "tags": 1-3 single-word conceptual category words (e.g. fear, trust, shame, longing) — never names, items, or places.\n'
            + '   - "emotions": the feelings this memory carries, each as {"label": "...", "intensity": <1-10>}. Use labels from this vocabulary when one fits: ' + vocabStr + '. You may invent a label if none fits. Use [] if the memory carries no clear feeling. This is always an ARRAY.';
    };

    /** Parse a model-returned seed-memory JSON object. Tolerates code fences,
     *  surrounding prose, and trailing commas. Returns null if no JSON found. */
    M._parseSeedJson = function(raw) {
        if (!raw) return null;
        let s = String(raw).trim();
        const fence = s.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
        if (fence) s = fence[1].trim();
        const objMatch = s.match(/\{[\s\S]*\}/);
        if (!objMatch) return null;
        s = objMatch[0];
        s = s.replace(/,\s*([}\]])/g, '$1'); // tolerate trailing commas
        try { return JSON.parse(s); } catch (e) { return null; }
    };

    M._runMemoryGeneration = async function() {
        const charName = M._gen && M._gen.charName;
        const container = document.getElementById('mem-editor-modal');
        if (!charName || !container) return;
        const status = container.querySelector('#mem-gen-status');
        const result = container.querySelector('#mem-gen-result');
        const impInput = container.querySelector('#mem-gen-importance');
        const theme = container.querySelector('#mem-gen-prompt')?.value?.trim();
        if (!theme) {
            status.textContent = 'Enter a theme first.'; status.style.color = '#e0a33c'; return;
        }
        if (!window.VW?.llm) {
            status.textContent = 'LLM client unavailable.'; status.style.color = '#e05555'; return;
        }
        status.textContent = 'generating…'; status.style.color = '#9aa4b2';
        try {
            const text = await VW.llm.chat([
                { role: 'system', content: M._identityBlock(charName) },
                { role: 'user', content: M._buildSeedPrompt(charName, theme) }
            ], { streaming: false, max_tokens: config.maxTokens || 256 });
            const raw = String(text || '').trim();
            const parsed = M._parseSeedJson(raw);
            // Always keep the text editable; prefer the parsed .text, else the raw.
            const memText = (parsed && parsed.text)
                ? String(parsed.text).trim()
                : raw.replace(/^["'`]+|["'`]+$/g, '').trim();
            if (!memText) {
                status.textContent = 'No memory returned.'; status.style.color = '#e05555'; return;
            }
            result.value = memText;
            if (parsed) {
                const imp = parseInt(parsed.importance, 10);
                if (impInput && !isNaN(imp)) impInput.value = String(Math.max(1, Math.min(10, imp)));
                const tags = Array.isArray(parsed.tags)
                    ? parsed.tags.filter(Boolean).map(t => String(t).toLowerCase())
                    : [];
                if (M._genTagSelect) M._genTagSelect.setValue(tags);
                const emotions = (Array.isArray(parsed.emotions) ? parsed.emotions : [])
                    .filter(e => e && e.label)
                    .map(e => ({ label: String(e.label).toLowerCase(), intensity: Math.max(1, Math.min(10, parseInt(e.intensity, 10) || 5)) }));
                const genEmoEl = container.querySelector('#mem-gen-emotions');
                if (genEmoEl) M._attachEmotionSelector(genEmoEl, emotions);
                status.textContent = '✓ drafted (parsed)'; status.style.color = '#4caf50';
            } else {
                status.textContent = '✓ drafted (text only — LLM didn\u2019t return JSON)'; status.style.color = '#e0a33c';
            }
        } catch (e) {
            status.textContent = '✗ ' + (e.message || e); status.style.color = '#e05555';
        }
    };

    M._saveGeneratedMemory = function() {
        const charName = M._gen && M._gen.charName;
        const container = document.getElementById('mem-editor-modal');
        if (!charName || !container) return;
        const content = container.querySelector('#mem-gen-result')?.value?.trim();
        if (!content) return;
        const type = container.querySelector('#mem-gen-type')?.value || 'memory';
        const importance = parseInt(container.querySelector('#mem-gen-importance')?.value) || 5;
        const emotions = Array.isArray(M._emoSelected)
            ? M._emoSelected.filter(e => e && e.label && e.label !== 'neutral')
            : [];
        const tags = M._genTagSelect ? M._genTagSelect.getValue() : (M._genTagSelectTags || []);
        const payload = { text: content, type, importance, tick: 0, source: 'manual', location: '', tags, force: true };
        if (emotions.length) {
            payload.memory_emotions = emotions;
            payload.emotion = emotions[0]; // primary single, for backward compatibility
        }

        const done = (data) => {
            M._closeMemoryEditor();
            const id = (data && data.entry && data.entry.id) || (data && data.id);
            if (id && window.EmbeddingClient?.configured()) M._embedForEntry(charName, id, content);
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        };
        ApiClient.addPlayerMemory(charName, payload).then(done);
    };

    /**
     * Build a multi-emotion picker bound to M._emoSelected (array of
     * {label,intensity}). Supports many emotions per memory.
     */
    M._attachEmotionSelector = function(container, initial) {
        M._emoSelected = (Array.isArray(initial) ? initial : []).filter(e => e && e.label);
        container.innerHTML = '';
        container.classList.add('memedit-entitybox');

        const bar = document.createElement('div');
        bar.style.cssText = 'display:flex;gap:6px;align-items:center;padding:6px;border-bottom:1px solid var(--border);flex-wrap:wrap;';
        const sel = document.createElement('select');
        sel.style.cssText = 'flex:1;min-width:140px;font-size:11px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;';
        EMOTION_GROUPS.forEach(g => {
            const og = document.createElement('optgroup');
            og.label = g.label;
            g.items.forEach(name => {
                const o = document.createElement('option');
                o.value = name; o.textContent = name;
                if (M._emoSelected.some(e => e.label === name)) o.selected = true;
                og.appendChild(o);
            });
            sel.appendChild(og);
        });
        const int = document.createElement('input');
        int.type = 'number'; int.min = 1; int.max = 10; int.value = 5;
        int.style.cssText = 'width:56px;font-size:11px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;';
        int.title = 'Intensity (1-10)';
        const cust = document.createElement('input');
        cust.type = 'text';
        cust.placeholder = 'or type a custom label…';
        cust.style.cssText = 'flex:1;min-width:110px;font-size:11px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;';
        cust.title = 'Add an emotion label not in the list (e.g. an agent-invented one)';
        const addBtn = document.createElement('button');
        addBtn.className = 'btn btn-sm btn-blue';
        addBtn.style.fontSize = '10px';
        addBtn.textContent = '➕ Add';
        addBtn.addEventListener('click', () => {
            const label = (cust.value || '').trim() || sel.value;
            if (!label) return;
            const intensity = Math.max(1, Math.min(10, parseInt(int.value) || 5));
            const found = M._emoSelected.find(e => e.label === label);
            if (found) found.intensity = intensity; else M._emoSelected.push({ label, intensity });
            cust.value = '';
            render();
        });
        cust.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); addBtn.click(); } });
        bar.append(sel, cust, int, addBtn);

        const chips = document.createElement('div');
        chips.style.cssText = 'padding:6px;display:flex;flex-wrap:wrap;gap:6px;max-height:120px;overflow-y:auto;';

        function render() {
            chips.innerHTML = '';
            if (M._emoSelected.length === 0) {
                const none = document.createElement('div');
                none.textContent = 'No emotions selected. Pick and add.';
                none.style.cssText = 'font-size:10px;color:var(--text-muted);';
                chips.appendChild(none);
                return;
            }
            M._emoSelected.forEach((e, idx) => {
                const chip = document.createElement('div');
                chip.style.cssText = 'display:flex;gap:4px;align-items:center;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:16px;padding:2px 8px;';
                const lbl = document.createElement('span');
                lbl.textContent = e.label;
                const iv = document.createElement('input');
                iv.type = 'number'; iv.min = 1; iv.max = 10; iv.value = e.intensity || 5;
                iv.style.cssText = 'width:40px;font-size:10px;padding:1px 3px;background:var(--bg-inset);color:var(--text);border:1px solid var(--border);border-radius:4px;';
                iv.addEventListener('change', () => {
                    M._emoSelected[idx].intensity = Math.max(1, Math.min(10, parseInt(iv.value) || 5));
                });
                const rm = document.createElement('button');
                rm.textContent = '×';
                rm.style.cssText = 'border:none;background:none;color:var(--text-muted);cursor:pointer;font-size:12px;line-height:1;';
                rm.addEventListener('click', () => { M._emoSelected.splice(idx, 1); render(); });
                chip.append(lbl, iv, rm);
                chips.appendChild(chip);
            });
        }
        render();
        container.append(bar, chips);
    };

    return M;
})();
