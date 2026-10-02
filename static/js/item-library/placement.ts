/**
 * ItemLibraryPlacement — Item placement in rooms, containers, and characters
 * Extracted from item-library.js
 *
 * These methods operate via .call(this) where this is an ItemLibrary instance.
 * They access instance properties (this.selectedId, this._targetArea,
 * this._multiSelect, this._checkedIds, this.data)
 * and delegate methods (this.renderList(), this.close()).
 *
 * @module item-library/placement — placing library items into the world
 * @contributes ItemLibraryPlacement (mixed into ItemLibrary): place into rooms/containers/characters, multi-spawn
 * @powers moving selected library items into the live world
 * @relates runs on an ItemLibrary instance; calls the item placement APIs
 * @docs docs/virtualWorld/Items & Inventory/Items Overview.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

// `placeItemFromLibrary` is a real ApiClient method (api.js) that globals.d.ts
// does not declare; reached through a cast so this file compiles alone.

(window as unknown as { ItemLibraryPlacement: ItemLibraryPlacementApi }).ItemLibraryPlacement = {
    /**
     * Show a target picker modal for selecting a area, container, or character.
     * @param {string} title - Modal title text
     * @param {Object} [options] - { tabs: ['area'] } restricts the visible tabs
     * @returns {Promise<{type: string, name?: string, id?: string}|null>}
     */
    pickTarget(title: string, options: PickTargetOptions = {}): Promise<PlacementTarget | null> {
        const allowedTabs = Array.isArray(options?.tabs) ? options.tabs as string[] : null;
        return new Promise<PlacementTarget | null>(resolve => {
            const rooms = Object.keys(worldState.areas || {});
            // Collect containers (items with container tag) + characters
            const containers: NamedId[] = [];
            const characters: NamedId[] = [];
            if (worldState.graph?.nodes) {
                for (const [nodeId, rawNode] of Object.entries(worldState.graph.nodes as Record<string, unknown>)) {
                    const node = rawNode as GraphNodeLike;
                    if (node.type === 'item') {
                        const tags = node.properties?.tags || [];
                        if (tags.includes('container') || (node.properties?.contents?.length ?? 0) > 0) {
                            containers.push({ id: nodeId, name: node.name || nodeId });
                        }
                    } else if (node.type === 'character') {
                        characters.push({ id: nodeId, name: node.name || nodeId });
                    }
                }
            }
            let tab = 'area'; // 'area' | 'container' | 'character'
            const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
            overlay.onclick = (evt: MouseEvent) => { if (evt.target === overlay) { document.body.removeChild(overlay); resolve(null); } };
            const dismiss = () => { document.body.removeChild(overlay); resolve(null); };
            const list = document.createElement('div');
            list.style.cssText = 'max-height:240px;overflow-y:auto;margin-top:6px;';
            const renderList = (filterText: string) => {
                const f = (filterText || '').toLowerCase();
                let items: unknown[] = [];
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
            list.addEventListener('click', (evt: Event) => {
                const opt = (evt.target as Element | null)?.closest<HTMLElement>('.target-option');
                if (opt) {
                    const type = opt.dataset.type as string;
                    const result: PlacementTarget = type === 'area'
                        ? { type: 'area', name: opt.dataset.name as string }
                        : { type, id: opt.dataset.id as string };
                    document.body.removeChild(overlay);
                    resolve(result);
                }
            });
            const input = document.createElement('input');
            input.type = 'text';
            input.placeholder = 'Search...';
            input.style.cssText = 'width:100%;padding:6px 10px;font-size:12px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);box-sizing:border-box;margin-top:6px;';
            input.oninput = () => renderList(input.value);
            input.onkeydown = (evt: KeyboardEvent) => { if (evt.key === 'Escape') dismiss(); };
            const tabBar = document.createElement('div');
            tabBar.style.cssText = 'display:flex;gap:4px;margin-bottom:4px;';
            const tabOptions: Array<[string, string]> = [];
            const show = (t: string) => !allowedTabs || allowedTabs.includes(t);
            if (show('area') && rooms.length) tabOptions.push(['area', `🏠 Rooms (${rooms.length})`]);
            if (show('container') && containers.length) tabOptions.push(['container', `📦 Containers (${containers.length})`]);
            if (show('character') && characters.length) tabOptions.push(['character', `🧑 Characters (${characters.length})`]);
            if (!tabOptions.some(([t]) => t === tab)) tab = tabOptions[0]?.[0] || 'area';
            const setTab = (tabId: string) => { tab = tabId; renderTabs(); renderList(input.value); };
            const renderTabs = () => {
                window.Lit.render(htmlTag`
                    ${tabOptions.map(([tabId, label]) => htmlTag`
                        <button style="flex:1;padding:4px 8px;font-size:11px;border:1px solid var(--border);border-radius:4px;background:${tab === tabId ? 'var(--accent)' : 'transparent'};color:var(--text);cursor:pointer;" @click=${() => setTab(tabId)}>${label}</button>`)}`, tabBar);
            };
            const box = document.createElement('div');
            box.style.cssText = 'background:var(--bg-panel);border:1px solid var(--border);border-radius:8px;padding:16px;min-width:300px;max-width:400px;box-shadow:0 8px 32px rgba(0,0,0,0.5);';
            box.onclick = (evt: MouseEvent) => evt.stopPropagation();
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
    async placeInRoom(this: ItemLibraryPlacementHost): Promise<void> {
        if (!this.selectedId || this.selectedId === '__new__') {
            toastInfo('Select a saved item first.');
            return;
        }
        let target: PlacementTarget | null = this._targetArea ? { type: 'area', name: this._targetArea } : null;
        if (!target) {
            target = await this._pickTarget('Place item in:');
            if (!target) return;
        }
        const res = await (ApiClient as unknown as {
            placeItemFromLibrary(target: PlacementTarget, itemId: string): Promise<{ error?: string }>;
        }).placeItemFromLibrary(target, this.selectedId);
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
    async placeSelectedInRoom(this: ItemLibraryPlacementHost): Promise<void> {
        if (!this._targetArea || this._checkedIds.size === 0) {
            toastInfo('No items selected.');
            return;
        }
        const targetArea = this._targetArea.trim();
        if (!worldState.areas?.[targetArea]) {
            toastError(`Area "${targetArea}" not found.`);
            return;
        }
        const existing = new Set<string>();
        const areaItems = worldState.getItemsInArea(targetArea) as Array<{ name: string }>;
        areaItems.forEach((item: { name: string }) => existing.add(item.name.toLowerCase()));
        const areaData = worldState.areas[targetArea];
        if (areaData?.items) (areaData.items as Array<{ name: string }>).forEach((item: { name: string }) => existing.add(item.name.toLowerCase()));

        let placed = 0;
        let skipped = 0;
        for (const id of this._checkedIds) {
            const itemData = this.data[id];
            const name = ((itemData?.name || id) || '').toLowerCase();
            if (existing.has(name)) { skipped++; continue; }
            const res = await (ApiClient as unknown as {
            placeItemFromLibrary(target: PlacementTarget, itemId: string): Promise<{ error?: string }>;
        }).placeItemFromLibrary({ type: 'area', name: targetArea }, id);
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
    updatePlaceButton(this: ItemLibraryPlacementHost): void {
        const btn = document.getElementById('place-items-btn') as HTMLButtonElement | null;
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

/*
 * Type declarations live below the first value statement on purpose: TypeScript
 * drops a file's leading JSDoc block when the first statement is type-only, and
 * `tools/js_module_index.py` reads `@module` out of the emitted `.js`.
 */

interface PickTargetOptions {
    tabs?: string[];
}

/** What a target picker resolved to: an area by name, or a node by id. */
interface PlacementTarget {
    type: string;
    name?: string;
    id?: string;
}

interface NamedId {
    id: string;
    name: string;
}

/** The graph node fields the container/character scan actually reads. */
interface GraphNodeLike {
    type?: string;
    name?: string;
    properties?: {
        tags?: string[];
        contents?: unknown[];
    } | null;
}

/** The ItemLibrary instance these methods are mixed onto. */
interface ItemLibraryPlacementHost {
    selectedId: string | null;
    _targetArea: string | null;
    _multiSelect: boolean;
    _checkedIds: Set<string>;
    data: Record<string, { name?: string } | undefined>;
    _pickTarget(title: string, options?: PickTargetOptions): Promise<PlacementTarget | null>;
    close(): void;
}

interface ItemLibraryPlacementApi {
    pickTarget(title: string, options?: PickTargetOptions): Promise<PlacementTarget | null>;
    placeInRoom(): Promise<void>;
    placeSelectedInRoom(): Promise<void>;
    updatePlaceButton(): void;
}
