"use strict";
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
window.ItemLibraryBatchTriggers = {
    prepareItemFields(item) {
        let actions = [];
        if (Array.isArray(item.actions)) {
            actions = item.actions.map((a) => String(a).trim()).filter(Boolean);
        }
        else if (typeof item.actions === 'string') {
            actions = item.actions.split(',').map((s) => s.trim()).filter(Boolean);
        }
        let tags = [];
        if (Array.isArray(item.tags)) {
            tags = item.tags.map((t) => String(t).trim()).filter(Boolean);
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
    toggleMultiSelect() {
        this._multiSelect = !this._multiSelect;
        if (!this._multiSelect) {
            this._checkedIds.clear();
        }
        const searchVal = document.getElementById('item-lib-search')?.value || '';
        this.renderList(searchVal);
        this._updateBatchBar();
        this._updatePlaceButton();
    },
    selectAllFiltered() {
        const ids = this._lastFilteredIds || Object.keys(this.data || {});
        for (const id of ids) {
            this._checkedIds.add(id);
        }
        const searchVal = document.getElementById('item-lib-search')?.value || '';
        this.renderList(searchVal);
        this._updateBatchBar();
        this._updatePlaceButton();
    },
    clearSelection() {
        this._checkedIds.clear();
        const searchVal = document.getElementById('item-lib-search')?.value || '';
        this.renderList(searchVal);
        this._updateBatchBar();
        this._updatePlaceButton();
    },
    updateBatchBar() {
        const bar = document.getElementById('item-lib-batch-bar');
        const countSpan = document.getElementById('item-lib-batch-count');
        const heuristicBtn = document.getElementById('item-lib-batch-suggest-btn');
        const aiBtn = document.getElementById('item-lib-batch-ai-btn');
        const toggleBtn = document.getElementById('item-lib-select-btn');
        if (toggleBtn) {
            if (this._multiSelect) {
                toggleBtn.classList.add('btn-primary');
                toggleBtn.textContent = '☑️ Selection Mode';
            }
            else {
                toggleBtn.classList.remove('btn-primary');
                toggleBtn.textContent = '☑️ Select';
            }
        }
        if (!bar)
            return;
        const count = this._checkedIds.size;
        if (this._multiSelect || count > 0) {
            bar.style.display = 'block';
        }
        else {
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
    async runBatch(opts) {
        const selectedIds = Array.from(this._checkedIds);
        if (!selectedIds.length) {
            if (typeof toastInfo === 'function')
                toastInfo('No items selected.');
            return;
        }
        const replaceExisting = Boolean(opts?.replaceExisting);
        const useAI = Boolean(opts?.useAI);
        const targets = [];
        const skipped = [];
        for (const id of selectedIds) {
            const item = this.data[id];
            if (!item)
                continue;
            const hasTriggers = Array.isArray(item.triggers) && item.triggers.length > 0;
            if (hasTriggers && !replaceExisting) {
                skipped.push({ id, name: item.name || id });
            }
            else {
                targets.push({ id, item });
            }
        }
        if (!targets.length) {
            const msg = `All ${selectedIds.length} selected item(s) already have triggers. Check "Replace existing" to overwrite.`;
            if (typeof toastInfo === 'function')
                toastInfo(msg);
            events.log(`⚡ Batch triggers: 0 applied · ${skipped.length} skipped (already authored) · 0 failed`, 'system-msg');
            return;
        }
        const Suggester = window.ItemLibraryTriggerSuggester;
        const DiffUI = window.TriggerSuggestDiff;
        if (!Suggester || !DiffUI) {
            if (typeof toastError === 'function')
                toastError('Trigger suggester or review UI is not loaded.');
            return;
        }
        const suggestAi = window.TriggerSuggestAI;
        const allRows = [];
        const progressBtn = document.getElementById(useAI ? 'item-lib-batch-ai-btn' : 'item-lib-batch-suggest-btn');
        const originalBtnText = progressBtn ? progressBtn.textContent : '';
        if (progressBtn)
            progressBtn.disabled = true;
        try {
            for (let idx = 0; idx < targets.length; idx++) {
                const target = targets[idx];
                const fields = window.ItemLibraryBatchTriggers.prepareItemFields(target.item);
                const planTypes = Suggester.plan(fields);
                const floor = Suggester.generate(fields);
                if (progressBtn) {
                    progressBtn.textContent = `⏳ ${idx + 1}/${targets.length}: ${fields.name || target.id}`;
                }
                let suggested = [];
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
                        }
                        else {
                            suggested = floor;
                        }
                    }
                    catch (e) {
                        suggested = floor;
                    }
                }
                else {
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
        }
        finally {
            if (progressBtn) {
                progressBtn.disabled = false;
                progressBtn.textContent = originalBtnText;
            }
        }
        if (!allRows.length) {
            const msg = `Everything planned is already covered - nothing to change.${skipped.length ? ` (${skipped.length} skipped - already authored)` : ''}`;
            if (typeof toastInfo === 'function')
                toastInfo(msg);
            events.log(`⚡ Batch triggers: 0 applied · ${skipped.length} skipped (already authored) · 0 failed`, 'system-msg');
            return;
        }
        DiffUI.show({
            title: useAI ? '🤖 Review AI-suggested triggers' : '⚡ Review suggested triggers',
            subtitle: `${allRows.length} change(s) across ${targets.length} item(s)${skipped.length ? ` (${skipped.length} skipped - already authored)` : ''}.`,
            rows: allRows,
            onApply: async (result) => {
                const byItem = new Map();
                for (const r of result.replace || []) {
                    const id = r.item_id;
                    if (!id)
                        continue;
                    if (!byItem.has(id))
                        byItem.set(id, { replace: [], add: [] });
                    byItem.get(id).replace.push(r);
                }
                for (const a of result.add || []) {
                    const id = a.item_id;
                    if (!id)
                        continue;
                    if (!byItem.has(id))
                        byItem.set(id, { replace: [], add: [] });
                    byItem.get(id).add.push(a);
                }
                let appliedCount = 0;
                const failed = [];
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
                        const res = await ApiClient.saveLibraryItem(payload);
                        if (res && res.error) {
                            failed.push(target.id);
                        }
                        else {
                            appliedCount++;
                        }
                    }
                    catch (e) {
                        failed.push(target.id);
                    }
                }
                const report = `${appliedCount} applied · ${skipped.length} skipped (already authored) · ${failed.length} failed`;
                events.log(`⚡ Batch triggers: ${report}${failed.length ? ` (failed: ${failed.join(', ')})` : ''}`, 'system-msg');
                if (typeof toastSuccess === 'function' && !failed.length) {
                    toastSuccess(`Batch triggers: ${appliedCount} items updated.`);
                }
                else if (typeof toastError === 'function' && failed.length) {
                    toastError(`Batch triggers: ${appliedCount} applied, ${failed.length} failed.`);
                }
                await this.refresh();
                const searchVal = document.getElementById('item-lib-search')?.value || '';
                this.renderList(searchVal);
                this._updateBatchBar();
            },
        });
    },
};
