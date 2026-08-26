/**
 * InspectorLore — World lore editor (view, add, edit, delete lore entries)
 * task-216: renders a lit-html TemplateResult via InspectorPanel instead of
 * writing #inspector-panel directly. Inline on* handlers are real @click
 * closures; interpolated values are auto-escaped by lit-html, so the old
 * `esc()` dance is gone.
 */

window.InspectorLore = (() => {
    const L = {};

    // Lazy tag: classic scripts parse before the deferred lit-bootstrap module
    // runs, so window.Lit only exists when a view actually renders.
    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

    /**
     * Show the World Lore view in the inspector panel
     */
    L.showWorldLore = function() {
        if (window.VW?.inspector) {
            window.VW.inspector._currentView = { type: 'world_lore' };
        }
        L.renderWorldLore();
    };

    /**
     * Render the World Lore view through InspectorPanel
     */
    L.renderWorldLore = async function() {
        let lore = [];
        try {
            const res = await ApiClient.getWorldLore();
            lore = res.lore || [];
        } catch (e) {
            lore = [];
        }

        const catColors = { geography:'#3fb950', history:'#58a6ff', factions:'#e3b341', characters:'#f0883e', magic:'#bc8cff', religion:'#f85149', general:'#8b949e' };

        const entries = (lore.length > 0)
            ? lore.map((entry, idx) => {
                const id = entry.id || `lore_${idx}`;
                const cat = entry.category || 'general';
                const color = catColors[cat] || '#8b949e';
                const tagsChip = entry.tags?.length
                    ? htmlTag`<div style="margin-top:4px;font-size:10px;color:var(--text-dim);">🏷️ ${entry.tags.join(', ')}</div>`
                    : null;
                return htmlTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:8px;margin-bottom:6px;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:4px;">
                        <div style="flex:1;min-width:0;">
                            <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
                                <span class="tag-badge" style="background:${color}22;color:${color};border:1px solid ${color};font-size:9px;">${cat}</span>
                                <strong style="font-size:12px;">${entry.title || 'Untitled'}</strong>
                                <span style="font-size:10px;color:var(--text-muted);">⭐ ${entry.importance ?? 3}</span>
                            </div>
                            <div style="margin-top:4px;font-size:11px;color:var(--text);">${entry.content || ''}</div>
                            ${tagsChip}
                        </div>
                        <div style="display:flex;gap:2px;flex-shrink:0;">
                            <button class="btn btn-sm" @click=${() => L.editLoreEntry(id)} style="font-size:9px;padding:1px 4px;" title="Edit">✏️</button>
                            <button class="btn btn-sm btn-red" @click=${() => L.deleteLoreEntry(id)} style="font-size:9px;padding:1px 4px;" title="Delete">🗑</button>
                        </div>
                    </div>
                    <div style="font-size:9px;color:var(--text-dim);margin-top:4px;">ID: ${id} · ${events.tickToTime(entry.tick_created ?? 0)} · ${entry.source || 'manual'}</div>
                </div>`;
            })
            : [htmlTag`<div style="font-size:12px;color:var(--text-muted);padding:12px;text-align:center;">No world lore yet. Add entries to define your world's setting, history, and factions.</div>`];

        window.InspectorPanel.render(htmlTag`
            <div class="inspector-header">
                <span class="inspector-type-badge" style="background:#8a6e3b;">🌍 World</span>
                <h2>World Lore</h2>
                <button class="btn btn-sm btn-ghost" @click=${() => hideInspectorPanel()}>✕</button>
            </div>
            <div class="inspector-section">
                <div style="display:flex;gap:4px;margin-bottom:8px;">
                    <button class="btn btn-sm btn-blue" @click=${() => L.addLoreEntry()}>+ Add Lore Entry</button>
                    <button class="btn btn-sm btn-red" @click=${() => { if (confirm('Delete ALL lore entries?')) { ApiClient.setWorldLore([]).then(() => L.renderWorldLore()); } }}>🗑 Clear All</button>
                </div>
                <div id="lore-list" style="max-height:calc(100vh - 200px);overflow-y:auto;">
                    ${entries}
                </div>
            </div>
        `);
    };

    /**
     * Open the lore editor for a new entry
     */
    L.addLoreEntry = function() {
        L.showLoreEditor(null);
    };

    /**
     * Open the lore editor for an existing entry
     * @param {string} entryId - Lore entry ID
     */
    L.editLoreEntry = function(entryId) {
        L.showLoreEditor(entryId);
    };

    /**
     * Show a modal for adding or editing a lore entry
     * @param {string|null} entryId - Lore entry ID (null for new)
     */
    L.showLoreEditor = async function(entryId) {
        let existing = null;
        if (entryId) {
            try {
                const res = await ApiClient.getWorldLore();
                existing = (res.lore || []).find(e => e.id === entryId);
            } catch (e) {}
        }
        const categories = ['general','geography','history','characters','factions','magic','religion','culture','bestiary'];
        const catOpts = categories.map(c => `<option value="${c}" ${existing?.category === c ? 'selected' : ''}>${c}</option>`).join('');

        const overlay = htmlTag`<div class="modal-overlay" id="lore-editor-modal">
            <div class="modal-content" style="max-width:550px;">
                <h3>${existing ? '✏️ Edit Lore Entry' : '➕ Add Lore Entry'}</h3>
                <label style="font-size:11px;">Title</label>
                <input type="text" id="lore-editor-title" value="${existing ? existing.title : ''}" style="width:100%;font-size:11px;" placeholder="e.g. The Kingdom of Rocheveron">
                <label style="font-size:11px;margin-top:8px;">Content</label>
                <textarea id="lore-editor-content" rows="5" style="width:100%;font-size:11px;" placeholder="Describe this lore entry...">${existing ? existing.content : ''}</textarea>
                <div style="display:flex;gap:8px;margin:8px 0;flex-wrap:wrap;">
                    <div style="flex:1;min-width:100px;">
                        <label style="font-size:10px;">Category</label>
                        <select id="lore-editor-category" style="width:100%;font-size:11px;">${window.Lit.unsafeHTML(catOpts)}</select>
                    </div>
                    <div style="width:70px;">
                        <label style="font-size:10px;">Importance (1-5)</label>
                        <input type="number" id="lore-editor-importance" min="1" max="5" value="${existing?.importance ?? 3}" style="width:100%;font-size:11px;">
                    </div>
                    <div style="flex:2;min-width:120px;">
                        <label style="font-size:10px;">Tags (comma-separated)</label>
                        <input type="text" id="lore-editor-tags" value="${existing?.tags ? existing.tags.join(', ') : ''}" style="width:100%;font-size:11px;" placeholder="character:King_Aldric, location:Rocheveron">
                    </div>
                </div>
                <div style="display:flex;gap:4px;justify-content:flex-end;">
                    <button class="btn btn-sm btn-ghost" @click=${() => L._closeLoreEditor()}>Cancel</button>
                    <button class="btn btn-sm btn-green" @click=${() => L.saveLoreEntry(entryId || '')}>💾 Save</button>
                </div>
            </div>
        </div>`;

        // Render into a dedicated container appended to body — never render into
        // document.body itself (lit would own the whole app).
        const container = document.createElement('div');
        container.id = 'lore-editor-container';
        document.body.appendChild(container);
        window.Lit.render(overlay, container);
    };

    L._closeLoreEditor = function() {
        const container = document.getElementById('lore-editor-container');
        if (container) container.remove();
    };

    /**
     * Save a lore entry from the editor modal
     * @param {string} entryId - Lore entry ID (empty string for new)
     */
    L.saveLoreEntry = async function(entryId) {
        const title = document.getElementById('lore-editor-title')?.value?.trim();
        const content = document.getElementById('lore-editor-content')?.value?.trim();
        if (!title || !content) return;
        const category = document.getElementById('lore-editor-category')?.value || 'general';
        const importance = parseInt(document.getElementById('lore-editor-importance')?.value) || 3;
        const tagsRaw = document.getElementById('lore-editor-tags')?.value || '';
        const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);

        try {
            if (entryId) {
                await ApiClient.updateWorldLoreEntry(entryId, { title, content, category, importance, tags });
            } else {
                await ApiClient.addWorldLoreEntry({ title, content, category, importance, tags });
            }
            L._closeLoreEditor();
            L.renderWorldLore();
        } catch (e) {
            console.error('Failed to save lore entry:', e);
        }
    };

    /**
     * Delete a lore entry
     * @param {string} entryId - Lore entry ID to delete
     */
    L.deleteLoreEntry = async function(entryId) {
        if (!entryId) return;
        try {
            await ApiClient.deleteWorldLoreEntry(entryId);
            L.renderWorldLore();
        } catch (e) {
            console.error('Failed to delete lore entry:', e);
        }
    };

    return L;
})();