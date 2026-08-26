/**
 * ItemLibraryPlacement — Item placement in rooms, containers, and characters
 * Extracted from item-library.js
 *
 * These methods operate via .call(this) where this is an ItemLibrary instance.
 * They access instance properties (this.selectedId, this._targetArea,
 * this._multiSelect, this._checkedIds, this.data)
 * and delegate methods (this.renderList(), this.close()).
 */

window.ItemLibraryPlacement = {
    /**
     * Show a target picker modal for selecting a area, container, or character.
     * @param {string} title - Modal title text
     * @returns {Promise<{type: string, name?: string, id?: string}|null>}
     */
    pickTarget(title) {
        return new Promise(resolve => {
            const rooms = Object.keys(worldState.areas || {});
            // Collect containers (items with container tag) + characters
            const containers = [];
            const characters = [];
            if (worldState.graph?.nodes) {
                for (const [nodeId, node] of Object.entries(worldState.graph.nodes)) {
                    if (node.type === 'item') {
                        const tags = node.properties?.tags || [];
                        if (tags.includes('container') || node.properties?.contents?.length > 0) {
                            containers.push({ id: nodeId, name: node.name || nodeId });
                        }
                    } else if (node.type === 'character') {
                        characters.push({ id: nodeId, name: node.name || nodeId });
                    }
                }
            }
            let tab = 'area'; // 'area' | 'container' | 'character'
            const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
            overlay.onclick = evt => { if (evt.target === overlay) { document.body.removeChild(overlay); resolve(null); } };
            const dismiss = () => { document.body.removeChild(overlay); resolve(null); };
            const list = document.createElement('div');
            list.style.cssText = 'max-height:240px;overflow-y:auto;margin-top:6px;';
            const renderList = (filterText) => {
                const f = (filterText || '').toLowerCase();
                let items = [];
                if (tab === 'area') {
                    items = (f ? rooms.filter(areaName => areaName.toLowerCase().includes(f)) : rooms).map(areaName =>
                        htmlTag`<div class="target-option" data-type="area" data-name=${areaName} style="padding:6px 10px;cursor:pointer;border-radius:4px;font-size:12px;">🏠 ${areaName}</div>`
                    );
                } else if (tab === 'container') {
                    items = (f ? containers.filter(container => container.name.toLowerCase().includes(f) || container.id.toLowerCase().includes(f)) : containers).map(container =>
                        htmlTag`<div class="target-option" data-type="container" data-id=${container.id} style="padding:6px 10px;cursor:pointer;border-radius:4px;font-size:12px;">📦 ${container.name} (${container.id})</div>`
                    );
                } else if (tab === 'character') {
                    items = (f ? characters.filter(character => character.name.toLowerCase().includes(f) || character.id.toLowerCase().includes(f)) : characters).map(character =>
                        htmlTag`<div class="target-option" data-type="character" data-id=${character.id} style="padding:6px 10px;cursor:pointer;border-radius:4px;font-size:12px;">🧑 ${character.name}</div>`
                    );
                }
                window.Lit.render(
                    items.length
                        ? htmlTag`${items}`
                        : htmlTag`<div style="padding:8px;color:var(--text-muted);font-size:11px;">No matches.</div>`,
                    list);
            };
            list.addEventListener('click', evt => {
                const opt = evt.target.closest('.target-option');
                if (opt) {
                    const type = opt.dataset.type;
                    const result = type === 'area' ? { type: 'area', name: opt.dataset.name } : { type, id: opt.dataset.id };
                    document.body.removeChild(overlay);
                    resolve(result);
                }
            });
            const input = document.createElement('input');
            input.type = 'text';
            input.placeholder = 'Search...';
            input.style.cssText = 'width:100%;padding:6px 10px;font-size:12px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);box-sizing:border-box;margin-top:6px;';
            input.oninput = () => renderList(input.value);
            input.onkeydown = evt => { if (evt.key === 'Escape') dismiss(); };
            const tabBar = document.createElement('div');
            tabBar.style.cssText = 'display:flex;gap:4px;margin-bottom:4px;';
            const tabOptions = [];
            if (rooms.length) tabOptions.push(['area', `🏠 Rooms (${rooms.length})`]);
            if (containers.length) tabOptions.push(['container', `📦 Containers (${containers.length})`]);
            if (characters.length) tabOptions.push(['character', `🧑 Characters (${characters.length})`]);
            const setTab = (tabId) => { tab = tabId; renderTabs(); renderList(input.value); };
            const renderTabs = () => {
                window.Lit.render(htmlTag`
                    ${tabOptions.map(([tabId, label]) => htmlTag`
                        <button style="flex:1;padding:4px 8px;font-size:11px;border:1px solid var(--border);border-radius:4px;background:${tab === tabId ? 'var(--accent)' : 'transparent'};color:var(--text);cursor:pointer;" @click=${() => setTab(tabId)}>${label}</button>`)}`, tabBar);
            };
            const box = document.createElement('div');
            box.style.cssText = 'background:var(--bg-panel);border:1px solid var(--border);border-radius:8px;padding:16px;min-width:300px;max-width:400px;box-shadow:0 8px 32px rgba(0,0,0,0.5);';
            box.onclick = evt => evt.stopPropagation();
            window.Lit.render(htmlTag`
                <div style="font-size:12px;font-weight:600;margin-bottom:8px;">${title}</div>
                ${tabBar}
                ${input}
                ${list}
                <div style="display:flex;gap:6px;margin-top:10px;">
                    <button class="btn btn-secondary btn-sm" style="flex:1;" @click=${dismiss}>Cancel</button>
                </div>`, box);
            overlay.appendChild(box);
            document.body.appendChild(overlay);
            renderTabs();
            setTimeout(() => input.focus(), 50);
            renderList('');
        });
    },

    /**
     * Place the currently selected item in a area.
     * Prompts the user to pick a target area if none is set.
     * @returns {Promise<void>}
     */
    async placeInRoom() {
        if (!this.selectedId || this.selectedId === '__new__') {
            toastInfo('Select a saved item first.');
            return;
        }
        let target = this._targetArea ? { type: 'area', name: this._targetArea } : null;
        if (!target) {
            target = await this._pickTarget('Place item in:');
            if (!target) return;
        }
        const res = await ApiClient.placeItemFromLibrary(target, this.selectedId);
        if (res.error) { toastError('Error: ' + res.error); return; }
        const label = target.type === 'area' ? target.name : target.id;
        events.log(`Placed "${this.selectedId}" in ${label}.`, 'system-msg');
        this._targetArea = null;
        worldState.fetch();
    },

    /**
     * Place multiple selected items (from multi-select mode) in a target area.
     * Skips items that already exist in the area by name.
     * @returns {Promise<void>}
     */
    async placeSelectedInRoom() {
        if (!this._targetArea || this._checkedIds.size === 0) {
            toastInfo('No items selected.');
            return;
        }
        const targetArea = this._targetArea.trim();
        if (!worldState.areas?.[targetArea]) {
            toastError(`Area "${targetArea}" not found.`);
            return;
        }
        const existing = new Set();
        const areaItems = worldState.getItemsInArea(targetArea);
        areaItems.forEach(item => existing.add(item.name.toLowerCase()));
        const areaData = worldState.areas[targetArea];
        if (areaData?.items) areaData.items.forEach(item => existing.add(item.name.toLowerCase()));

        let placed = 0;
        let skipped = 0;
        for (const id of this._checkedIds) {
            const itemData = this.data[id];
            const name = ((itemData?.name || id) || '').toLowerCase();
            if (existing.has(name)) { skipped++; continue; }
            const res = await ApiClient.placeItemFromLibrary({ type: 'area', name: targetArea }, id);
            if (!res.error) { placed++; existing.add(name); }
        }
        events.log(`Placed ${placed} item(s) in ${targetArea}${skipped > 0 ? ` (${skipped} skipped)` : ''}`, 'system-msg');
        this._targetArea = null;
        this._multiSelect = false;
        this._checkedIds.clear();
        worldState.fetch();
        this.close();
    },

    /**
     * Update the place button text and enabled/disabled state
     * based on current selection mode.
     */
    updatePlaceButton() {
        const btn = document.getElementById('place-items-btn');
        if (!btn) return;
        if (this._multiSelect && this._targetArea) {
            const count = this._checkedIds.size;
            btn.textContent = count > 0 ? `📌 Place Selected (${count}) in "${this._targetArea}"` : '📌 Place Selected in Area';
            btn.disabled = count === 0;
            btn.style.display = 'inline-block';
        } else {
            btn.textContent = '📌 Place in World';
            btn.disabled = false;
            btn.style.display = this.selectedId && this.selectedId !== '__new__' ? 'inline-block' : 'none';
        }
    }
};
