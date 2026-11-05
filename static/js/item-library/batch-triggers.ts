/**
 * ItemLibraryBatchTriggers - Batch trigger generation for selected library items (task-509).
 *
 * Runs the offline heuristic (ItemLibraryTriggerSuggester) or AI (TriggerSuggestAI)
 * across N selected items, reviews proposed changes in TriggerSuggestDiff,
 * respects already-authored triggers unless "replace existing" is checked,
 * and writes merged triggers to the library on Apply.
 *
 * @module item-library/batch-triggers - batch trigger generation for library items
 * @contributes ItemLibraryBatchTriggers: batch suggest, review diff, save to library
 * @powers "⚡ Suggest triggers (N)" and "✨ Suggest (AI) (N)" in the library
 * @relates uses item-library/consumable-triggers + shared/trigger-suggest-diff + item-library
 * @docs docs/virtualWorld/Library System/Library System Overview.md
 */

// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

(window as unknown as { ItemLibraryBatchTriggers: ItemLibraryBatchTriggersApi }).ItemLibraryBatchTriggers = {
    prepareItemFields(item: LibraryItemLike): Record<string, any> {
        let actions: string[] = [];
        if (Array.isArray(item.actions)) {
            actions = item.actions.map((a: unknown) => String(a).trim()).filter(Boolean);
        } else if (typeof item.actions === 'string') {
            actions = item.actions.split(',').map((s: string) => s.trim()).filter(Boolean);
        }
        let tags: string[] = [];
        if (Array.isArray(item.tags)) {
            tags = item.tags.map((t: unknown) => String(t).trim()).filter(Boolean);
        }
        const usesRaw = parseInt(String(item.uses ?? '-1'), 10);
        return {
            name: item.name || '',
            description: item.description || '',
            actions: actions.length ? actions : ['examine', 'take', 'use'],
            tags,
            uses: Number.isNaN(usesRaw) ? -1 : usesRaw,
            current_state: item.current_state || 'normal',
        };
    },

    toggleMultiSelect(this: ItemLibraryBatchHost): void {
        this._multiSelect = !this._multiSelect;
        if (!this._multiSelect) {
            this._checkedIds.clear();
        }
        const searchVal = (document.getElementById('item-lib-search') as HTMLInputElement | null)?.value || '';
        this.renderList(searchVal);
        this._updateBatchBar();
        this._updatePlaceButton();
    },

    selectAllFiltered(this: ItemLibraryBatchHost): void {
        const ids = this._lastFilteredIds || Object.keys(this.data || {});
        for (const id of ids) {
            this._checkedIds.add(id);
        }
        const searchVal = (document.getElementById('item-lib-search') as HTMLInputElement | null)?.value || '';
        this.renderList(searchVal);
        this._updateBatchBar();
        this._updatePlaceButton();
    },

    clearSelection(this: ItemLibraryBatchHost): void {
        this._checkedIds.clear();
        const searchVal = (document.getElementById('item-lib-search') as HTMLInputElement | null)?.value || '';
        this.renderList(searchVal);
        this._updateBatchBar();
        this._updatePlaceButton();
    },

    updateBatchBar(this: ItemLibraryBatchHost): void {
        const bar = document.getElementById('item-lib-batch-bar');
        const countSpan = document.getElementById('item-lib-batch-count');
        const heuristicBtn = document.getElementById('item-lib-batch-suggest-btn') as HTMLButtonElement | null;
        const aiBtn = document.getElementById('item-lib-batch-ai-btn') as HTMLButtonElement | null;
        const toggleBtn = document.getElementById('item-lib-select-btn') as HTMLButtonElement | null;

        if (toggleBtn) {
            if (this._multiSelect) {
                toggleBtn.classList.add('btn-primary');
                toggleBtn.textContent = '☑️ Selection Mode';
            } else {
                toggleBtn.classList.remove('btn-primary');
                toggleBtn.textContent = '☑️ Select';
            }
        }

        if (!bar) return;

        const count = this._checkedIds.size;
        if (this._multiSelect || count > 0) {
            bar.style.display = 'block';
        } else {
            bar.style.display = 'none';
            return;
        }

        if (countSpan) {
            countSpan.textContent = `${count} selected`;
        }

        if (heuristicBtn) {
            heuristicBtn.textContent = `⚡ Suggest triggers (${count})`;
            heuristicBtn.disabled = count === 0;
        }

        if (aiBtn) {
            aiBtn.textContent = `✨ Suggest (AI) (${count})`;
            aiBtn.disabled = count === 0;
        }
    },

    async runBatch(this: ItemLibraryBatchHost, opts: { useAI?: boolean; replaceExisting?: boolean }): Promise<void> {
        const selectedIds = Array.from(this._checkedIds);
        if (!selectedIds.length) {
            if (typeof toastInfo === 'function') toastInfo('No items selected.');
            return;
        }

        const replaceExisting = Boolean(opts?.replaceExisting);
        const useAI = Boolean(opts?.useAI);

        const targets: Array<{ id: string; item: LibraryItemLike }> = [];
        const skipped: Array<{ id: string; name: string }> = [];

        for (const id of selectedIds) {
            const item = this.data[id];
            if (!item) continue;
            const hasTriggers = Array.isArray(item.triggers) && item.triggers.length > 0;
            if (hasTriggers && !replaceExisting) {
                skipped.push({ id, name: item.name || id });
            } else {
                targets.push({ id, item });
            }
        }

        if (!targets.length) {
            const msg = `All ${selectedIds.length} selected item(s) already have triggers. Check "Replace existing" to overwrite.`;
            if (typeof toastInfo === 'function') toastInfo(msg);
            events.log(`⚡ Batch triggers: 0 applied · ${skipped.length} skipped (already authored) · 0 failed`, 'system-msg');
            return;
        }

        const Suggester = (window as unknown as {
            ItemLibraryTriggerSuggester?: {
                plan(fields: unknown): string[];
                generate(fields: unknown): Array<{ trigger_type: string }>;
            };
        }).ItemLibraryTriggerSuggester;

        const DiffUI = (window as unknown as {
            TriggerSuggestDiff?: {
                diff(existing: unknown, planTypes: string[], triggers: unknown[]): Array<any>;
                show(opts: unknown): HTMLElement;
                merge(existing: unknown, result: unknown): unknown[];
            };
        }).TriggerSuggestDiff;

        if (!Suggester || !DiffUI) {
            if (typeof toastError === 'function') toastError('Trigger suggester or review UI is not loaded.');
            return;
        }

        const suggestAi = (window as unknown as {
            TriggerSuggestAI?: { suggest(fields: unknown, kind: string, planTypes: string[]): Promise<Array<{ trigger_type: string }> | null> };
        }).TriggerSuggestAI;

        const allRows: Array<any> = [];
        const progressBtn = document.getElementById(useAI ? 'item-lib-batch-ai-btn' : 'item-lib-batch-suggest-btn') as HTMLButtonElement | null;
        const originalBtnText = progressBtn ? progressBtn.textContent : '';
        if (progressBtn) progressBtn.disabled = true;

        try {
            for (let idx = 0; idx < targets.length; idx++) {
                const target = targets[idx];
                const fields = (window as unknown as { ItemLibraryBatchTriggers: ItemLibraryBatchTriggersApi }).ItemLibraryBatchTriggers.prepareItemFields(target.item);
                const planTypes = Suggester.plan(fields);
                const floor = Suggester.generate(fields);

                if (progressBtn) {
                    progressBtn.textContent = `⏳ ${idx + 1}/${targets.length}: ${fields.name || target.id}`;
                }

                let suggested: Array<{ trigger_type: string }> = [];

                if (useAI && suggestAi) {
                    try {
                        const aiRes = await suggestAi.suggest(fields, 'item', planTypes);
                        if (Array.isArray(aiRes) && aiRes.length) {
                            suggested = aiRes;
                            const have = new Set(suggested.map(t => t.trigger_type));
                            for (const t of floor) {
                                if (!have.has(t.trigger_type)) {
                                    suggested.push(t);
                                    have.add(t.trigger_type);
                                }
                            }
                        } else {
                            suggested = floor;
                        }
                    } catch (e) {
                        suggested = floor;
                    }
                } else {
                    suggested = floor;
                }

                const existingTriggers = Array.isArray(target.item.triggers) ? target.item.triggers : [];
                const itemRows = DiffUI.diff(existingTriggers, planTypes, suggested);

                for (const row of itemRows) {
                    row.item_id = target.id;
                    row.item_name = target.item.name || target.id;
                    allRows.push(row);
                }
            }
        } finally {
            if (progressBtn) {
                progressBtn.disabled = false;
                progressBtn.textContent = originalBtnText;
            }
        }

        if (!allRows.length) {
            const msg = `Everything planned is already covered - nothing to change.${skipped.length ? ` (${skipped.length} skipped - already authored)` : ''}`;
            if (typeof toastInfo === 'function') toastInfo(msg);
            events.log(`⚡ Batch triggers: 0 applied · ${skipped.length} skipped (already authored) · 0 failed`, 'system-msg');
            return;
        }

        DiffUI.show({
            title: useAI ? '🤖 Review AI-suggested triggers' : '⚡ Review suggested triggers',
            subtitle: `${allRows.length} change(s) across ${targets.length} item(s)${skipped.length ? ` (${skipped.length} skipped - already authored)` : ''}.`,
            rows: allRows,
            onApply: async (result: any) => {
                const byItem = new Map<string, { replace: any[]; add: any[] }>();
                for (const r of result.replace || []) {
                    const id = r.item_id;
                    if (!id) continue;
                    if (!byItem.has(id)) byItem.set(id, { replace: [], add: [] });
                    byItem.get(id)!.replace.push(r);
                }
                for (const a of result.add || []) {
                    const id = a.item_id;
                    if (!id) continue;
                    if (!byItem.has(id)) byItem.set(id, { replace: [], add: [] });
                    byItem.get(id)!.add.push(a);
                }

                let appliedCount = 0;
                const failed: string[] = [];

                for (const target of targets) {
                    const itemChanges = byItem.get(target.id);
                    if (!itemChanges || (itemChanges.replace.length === 0 && itemChanges.add.length === 0)) {
                        continue;
                    }
                    const itemResult = {
                        keep: result.keep || [],
                        replace: itemChanges.replace,
                        add: itemChanges.add,
                    };
                    const merged = DiffUI.merge(target.item.triggers || [], itemResult);
                    const payload = {
                        ...target.item,
                        id: target.id,
                        triggers: merged,
                    };

                    try {
                        const res = await (ApiClient as any).saveLibraryItem(payload);
                        if (res && res.error) {
                            failed.push(target.id);
                        } else {
                            appliedCount++;
                        }
                    } catch (e) {
                        failed.push(target.id);
                    }
                }

                const report = `${appliedCount} applied · ${skipped.length} skipped (already authored) · ${failed.length} failed`;
                events.log(`⚡ Batch triggers: ${report}${failed.length ? ` (failed: ${failed.join(', ')})` : ''}`, 'system-msg');
                if (typeof toastSuccess === 'function' && !failed.length) {
                    toastSuccess(`Batch triggers: ${appliedCount} items updated.`);
                } else if (typeof toastError === 'function' && failed.length) {
                    toastError(`Batch triggers: ${appliedCount} applied, ${failed.length} failed.`);
                }

                await this.refresh();
                const searchVal = (document.getElementById('item-lib-search') as HTMLInputElement | null)?.value || '';
                this.renderList(searchVal);
                this._updateBatchBar();
            },
        });
    },
};

/* ── types ──
 * Declared at the BOTTOM deliberately. tsc drops a file's leading JSDoc when
 * the first statement is type-only, and tools/js_module_index.py reads
 * `@module` out of the EMITTED .js - so an `interface` above the first value
 * declaration would silently strip the module contract. */

interface LibraryItemLike {
    id?: string;
    name?: string;
    description?: string;
    actions?: unknown;
    tags?: unknown;
    uses?: unknown;
    current_state?: string;
    triggers?: unknown[];
    [key: string]: unknown;
}

interface ItemLibraryBatchHost {
    data: Record<string, LibraryItemLike>;
    _multiSelect: boolean;
    _checkedIds: Set<string>;
    _lastFilteredIds?: string[];
    refresh(): Promise<void>;
    renderList(filterText?: string): void;
    _updateBatchBar(): void;
    _updatePlaceButton(): void;
}

interface ItemLibraryBatchTriggersApi {
    prepareItemFields(item: LibraryItemLike): Record<string, any>;
    toggleMultiSelect(this: ItemLibraryBatchHost): void;
    selectAllFiltered(this: ItemLibraryBatchHost): void;
    clearSelection(this: ItemLibraryBatchHost): void;
    updateBatchBar(this: ItemLibraryBatchHost): void;
    runBatch(this: ItemLibraryBatchHost, opts: { useAI?: boolean; replaceExisting?: boolean }): Promise<void>;
}
