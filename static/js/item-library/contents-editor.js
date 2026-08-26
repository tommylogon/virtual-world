/**
 * ItemLibraryContents — Container contents editor for library items
 * Extracted from item-library.js
 *
 * These methods operate via .call(this) where this is an ItemLibrary instance.
 * They access instance properties (this.data) for populating autocomplete options.
 */

// Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
const itemLibraryContentsHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.ItemLibraryContents = {
    /**
     * Render the contents list for a container as a lit template.
     *
     * All consumers (this file, item-library.js editor, ai-generation.js)
     * render lit TemplateResults now, so this returns a TemplateResult.
     * @param {Array} contents - Array of content item objects {id, name} or strings
     * @returns {TemplateResult} lit-html template
     */
    renderContentsSection(contents) {
        const items = contents || [];
        if (items.length === 0) {
            return itemLibraryContentsHtmlTag`<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No contained items. Add items that should be inside this container.</div>`;
        }
        const rows = items.map((contentItem, idx) => {
            const itemLabel = typeof contentItem === 'string' ? contentItem : (contentItem.name || contentItem.id);
            const itemId = typeof contentItem === 'string' ? contentItem : contentItem.id;
            const libEntry = this.data?.[itemId];
            const w = (typeof contentItem === 'object' && contentItem.weight != null)
                ? parseFloat(contentItem.weight)
                : (libEntry?.weight ?? null);
            const weightBadge = (w != null && !isNaN(w))
                ? itemLibraryContentsHtmlTag`<span style="font-size:9px;color:var(--text-dim);white-space:nowrap;">⚖️ ${w} kg</span>`
                : window.Lit.nothing;
            return itemLibraryContentsHtmlTag`<div style="display:flex;align-items:center;gap:4px;padding:4px 8px;background:var(--bg-inset);border-radius:4px;margin-bottom:3px;border-left:3px solid var(--green);">
                <span style="flex:1;font-size:11px;">📦 ${itemLabel}</span>
                ${weightBadge}
                <button class="btn btn-sm btn-ghost" @click=${() => VW.itemLib._removeContent(idx)} style="font-size:9px;color:var(--red);">✕</button>
            </div>`;
        });
        const total = items.reduce((sum, contentItem) => {
            const itemId = typeof contentItem === 'string' ? contentItem : contentItem.id;
            const w = (typeof contentItem === 'object' && contentItem.weight != null)
                ? parseFloat(contentItem.weight)
                : (this.data?.[itemId]?.weight ?? 0);
            return sum + (isNaN(w) ? 0 : w);
        }, 0);
        return itemLibraryContentsHtmlTag`${rows}
            <div style="display:flex;justify-content:flex-end;font-size:10px;color:var(--text-dim);padding:2px 2px 0;">⚖️ Total: ${total.toFixed(1)} kg</div>`;
    },

    /**
     * Remove a content item from the container contents array by index.
     * @param {number} idx - Index to remove
     */
    removeContent(idx) {
        const field = document.getElementById('lib-item-contents');
        const contents = JSON.parse(field.value || '[]');
        contents.splice(idx, 1);
        field.value = JSON.stringify(contents);
        const listEl = document.getElementById('lib-contents-list');
        if (listEl) window.Lit.render(this.renderContentsSection(contents), listEl);
    },

    /**
     * Show a modal UI for adding a new item to the container contents.
     * Shows a datalist of existing library items for autocomplete.
     */
    addContentUi() {
        // Get available library item names for autocomplete
        const itemOptions = Object.entries(this.data).map(([id, item]) =>
            itemLibraryContentsHtmlTag`<option value=${id}>${item.name || id}</option>`
        );

        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
        window.Lit.render(itemLibraryContentsHtmlTag`
            <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:380px;">
                <h3 style="margin:0 0 12px;">📦 Add Contained Item</h3>
                <div class="field"><label>Item ID (from library or type new)</label>
                    <input type="text" id="content-item-id" placeholder="rusty_key" list="content-item-list" style="width:100%;">
                    <datalist id="content-item-list">${itemOptions}</datalist>
                </div>
                <div class="field"><label>Display Name (optional)</label>
                    <input type="text" id="content-item-name" placeholder="Rusty Key" style="width:100%;">
                </div>
                <div style="display:flex;gap:6px;margin-top:12px;">
                    <button class="btn btn-green btn-sm" @click=${(e) => VW.itemLib._saveContent(e.target)}>✅ Add</button>
                    <button class="btn btn-sm btn-ghost" @click=${(e) => e.currentTarget.closest('[style*="fixed"]')?.remove()}>Cancel</button>
                </div>
            </div>`, overlay);
        document.body.appendChild(overlay);
    },

    /**
     * Save a new content item from the "add content" overlay form.
     * Reads the form fields and appends to the contents array.
     * @param {HTMLElement} btn - The "Add" button that was clicked
     */
    saveContent(btn) {
        const overlay = btn.closest('[style*="fixed"]');
        const itemId = document.getElementById('content-item-id').value.trim();
        if (!itemId) { toastInfo('Item ID is required.'); return; }
        const itemName = document.getElementById('content-item-name').value.trim() || itemId;

        const field = document.getElementById('lib-item-contents');
        const contents = JSON.parse(field.value || '[]');
        contents.push({ id: itemId, name: itemName });
        field.value = JSON.stringify(contents);

        const listEl = document.getElementById('lib-contents-list');
        if (listEl) window.Lit.render(this.renderContentsSection(contents), listEl);
        overlay.remove();
        events.log(`Added "${itemName}" to container contents.`, 'system-msg');
    }
};