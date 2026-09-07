/**
 * TriggerSuggestDiff — review/merge UI for suggested triggers.
 *
 * When "⚡ Suggest" (heuristic) or "✨ Suggest (AI)" proposes triggers for a
 * node that already has some, we don't want a blind "overwrite everything?"
 * prompt. This module:
 *   1. Compares each planned trigger against what already exists (by
 *      trigger_type + effect intent).
 *   2. Classifies rows:
 *        keep     — an existing trigger already covers the suggestion
 *                   (e.g. a food item with an on_eat Hunger adjust) → no-op.
 *        add      — no existing trigger of that type → create it.
 *        conflict — same trigger type, materially different payload → you
 *                   choose per row: keep existing / use suggested / skip both.
 *   3. Renders a card-based diff modal so you decide per-trigger, per-row.
 *
 * Pure UI/decision helper — no engine calls.
 */
window.TriggerSuggestDiff = (() => {
    const GREEN = 'var(--green, #2e9e5b)';
    const BLUE = 'var(--blue, #3b82f6)';
    const ORANGE = 'var(--orange, #e8890c)';
    const RED = 'var(--red, #e5484d)';

    function escapeHtml(s) {
        return String(s ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    }

    /** Normalize a single effect's "intent" for comparison. */
    function effectKey(e) {
        const p = e?.params || {};
        if (e?.type === 'adjust_vital') return `adjust_vital:${String(p.stat || '')}`;
        if (e?.type === 'save') return `save:${String(p.stat || p.skill || '')}`;
        if (e?.type === 'apply_condition') return `apply_condition:${String(p.condition || '')}`;
        if (e?.type === 'set_state') return `set_state:${String(p.state || '')}`;
        if (e?.type === 'message') return 'message';
        return String(e?.type || '');
    }

    /**
     * Does an existing trigger already cover a suggested one?
     * Same trigger_type AND the suggestion's effect intents are all present in
     * the existing effects (amounts/messages may differ — that's an author's
     * choice to keep). Message-only suggestions are covered by anything, since
     * the engine plays existing messages just fine.
     */
    function covered(existing, suggested) {
        if (!existing || !suggested) return false;
        const sugKeys = (suggested.effects || []).map(effectKey);
        const exKeys = new Set((existing.effects || []).map(effectKey));
        if (sugKeys.length === 0) return false;
        // A message suggestion is "covered" if we already have anything real.
        if (sugKeys.length === 1 && sugKeys[0] === 'message') return exKeys.size > 0;
        return sugKeys.every(k => exKeys.has(k));
    }

    /**
     * Classify a planned trigger set against existing triggers.
     * @param {Array} existing        - [{ trigger_type, effects, ... }]
     * @param {Array} plannedTypes    - ordered trigger_type strings
     * @param {Array} suggestedTriggers - [{ trigger_type, effects, ... }]
     * @returns {Array} rows of { type, status, existing, suggested }
     */
    function diff(existing, plannedTypes, suggestedTriggers) {
        const rows = [];
        const suggestedByType = new Map(suggestedTriggers.map(t => [t.trigger_type, t]));
        const existingByType = new Map();
        for (const ex of existing || []) {
            const k = Array.isArray(ex.trigger_type) ? ex.trigger_type.join(',') : String(ex.trigger_type || '');
            if (k) existingByType.set(k, ex);
        }
        for (const type of plannedTypes) {
            const sug = suggestedByType.get(type);
            const ex = existingByType.get(type);
            let status;
            if (ex && sug && covered(ex, sug)) status = 'keep';
            else if (ex && sug) status = 'conflict';
            else if (sug) status = 'add';
            else continue;
            rows.push({ type, status, existing: ex, suggested: sug });
        }
        return rows;
    }

    /** One-line description of a trigger (kept for backward-compat callers). */
    function describe(t) {
        if (!t) return '';
        return (t.effects || []).map(effectLine).join(' · ') || 'no effects';
    }

    /** Render one effect as a short readable line. */
    function effectLine(e) {
        const p = e?.params || {};
        switch (e?.type) {
            case 'adjust_vital': {
                const amt = Number(p.amount) || 0;
                return `${p.stat || 'vital'} ${amt > 0 ? '+' : ''}${amt}`;
            }
            case 'save': return `Save ${p.stat || p.skill || '?'} (DC ${p.dc ?? '?'})`;
            case 'apply_condition': return `Apply ${p.condition}`;
            case 'set_state': return `state → ${p.state}`;
            case 'message': return `“${String(p.message || p.success_message || '').slice(0, 80)}”`;
            default: return String(e?.type || '?');
        }
    }

    function effectsHtml(t) {
        return (t?.effects || []).map(e => {
            const p = e?.params || {};
            let color = 'var(--text)';
            if (e?.type === 'adjust_vital') color = (Number(p.amount) || 0) < 0 ? RED : GREEN;
            return `<div style="display:flex;gap:7px;align-items:baseline;font-size:11px;line-height:1.7;">
                <span style="color:var(--text-dim);flex-shrink:0;">•</span>
                <span style="color:${color};">${escapeHtml(effectLine(e))}</span>
            </div>`;
        }).join('');
    }

    function statusMeta(status) {
        if (status === 'keep') return { label: '✓ Already covered', color: GREEN, icon: '✓' };
        if (status === 'add') return { label: 'New', color: BLUE, icon: '＋' };
        return { label: 'Changes found', color: ORANGE, icon: '⚠' };
    }

    function badge(status) {
        const m = statusMeta(status);
        return `<span style="display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;letter-spacing:.3px;color:${m.color};border:1px solid ${m.color}55;background:${m.color}14;border-radius:10px;padding:2px 8px;white-space:nowrap;">${m.icon} ${m.label}</span>`;
    }

    function summaryHtml(rows) {
        const counts = { keep: 0, add: 0, conflict: 0 };
        rows.forEach(r => { if (counts[r.status] != null) counts[r.status]++; });
        const parts = [];
        if (counts.add) parts.push(`<b style="color:${BLUE};">${counts.add} new</b>`);
        if (counts.conflict) parts.push(`<b style="color:${ORANGE};">${counts.conflict} conflict${counts.conflict === 1 ? '' : 's'}</b>`);
        if (counts.keep) parts.push(`<span style="color:var(--text-muted);">${counts.keep} already covered</span>`);
        if (!parts.length) parts.push('<span style="color:var(--text-muted);">nothing to change</span>');
        return `<div style="display:flex;gap:14px;font-size:11px;margin-top:8px;flex-wrap:wrap;">${parts.map(p => `<span>${p}</span>`).join('')}</div>`;
    }

    /**
     * Build one trigger card: header (type + status badge), effect blocks for
     * existing/suggested, and the per-row choice pills when applicable.
     */
    function buildRow(row, i, opts) {
        const card = document.createElement('div');
        const accent = statusMeta(row.status).color;
        card.style.cssText = `border:1px solid var(--border);border-left:3px solid ${accent};border-radius:8px;padding:10px 12px;background:var(--bg-inset);`;

        const head = document.createElement('div');
        head.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;';
        head.innerHTML = `<div style="font-family:var(--font-mono);font-size:12px;font-weight:700;text-transform:uppercase;">${escapeHtml(row.type)}</div>${badge(row.status)}`;
        card.appendChild(head);

        if (row.status === 'keep') {
            const line = document.createElement('div');
            line.style.cssText = 'font-size:11px;color:var(--text-muted);margin-top:6px;';
            line.innerHTML = `An existing <b>${escapeHtml(row.type)}</b> trigger already does this — it will be <b style="color:${GREEN};">kept as-is</b>.`;
            card.appendChild(line);
        } else {
            if (row.existing && row.status === 'conflict') {
                card.appendChild(blockHtml('Currently', row.existing, 'var(--text-muted)', 'var(--bg-panel)'));
            }
            if (row.suggested) {
                card.appendChild(blockHtml(row.status === 'conflict' ? 'Suggested' : 'Will add', row.suggested, BLUE, 'var(--bg-panel)'));
            }
            card.appendChild(choicePills(row, i));
        }
        return card;
    }

    function blockHtml(label, trigger, color, bg) {
        const el = document.createElement('div');
        el.style.cssText = `margin-top:8px;border:1px solid var(--border-light);border-radius:6px;padding:7px 10px;background:${bg};`;
        el.innerHTML = `<div style="font-size:9px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:${color};margin-bottom:2px;">${escapeHtml(label)}</div>${effectsHtml(trigger)}${renderMetaLines(trigger)}`;
        return el;
    }

    function renderMetaLines(t) {
        let out = '';
        if (t?.conditions && t.conditions.length) {
            out += `<div style="font-size:10px;color:var(--text-dim);margin-top:3px;">only if: ${escapeHtml(t.conditions.map(c => `${c.type} = ${c.value}`).join(', '))}</div>`;
        }
        if (t?.fail_message) {
            out += `<div style="font-size:10px;color:var(--text-dim);margin-top:2px;">on fail: “${escapeHtml(String(t.fail_message).slice(0, 80))}”</div>`;
        }
        return out;
    }

    /** Pill-style radio group for one row. */
    function choicePills(row, i) {
        const wrap = document.createElement('div');
        wrap.style.cssText = 'margin-top:10px;padding-top:9px;border-top:1px dashed var(--border-light);display:flex;flex-wrap:wrap;gap:6px;align-items:center;';
        wrap.dataset.row = String(i);

        const choices = row.status === 'add'
            ? [
                { value: 'add', label: 'Add this trigger', default: true },
                { value: 'skip', label: 'Skip' },
            ]
            : [
                { value: 'keep', label: 'Keep existing', default: true },
                { value: 'replace', label: 'Use suggested' },
                { value: 'skip', label: 'Skip both' },
            ];

        choices.forEach(ch => {
            const pill = document.createElement('label');
            pill.className = 'tsd-pill';
            pill.dataset.value = ch.value;
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = `tsd-choice-${i}`;
            input.value = ch.value;
            if (ch.default) input.checked = true;
            const span = document.createElement('span');
            span.textContent = ch.label;
            pill.appendChild(input);
            pill.appendChild(span);
            wrap.appendChild(pill);
            if (ch.default) pill.classList.add('tsd-on');
        });
        return wrap;
    }

    function collect(panel, rows) {
        const result = { keep: [], replace: [], add: [] };
        const keepTypes = new Set();
        rows.forEach((row, i) => {
            let choice = row.status;
            if (row.status === 'add' || row.status === 'conflict') {
                const sel = panel.querySelector(`input[name="tsd-choice-${i}"]:checked`);
                if (sel) choice = sel.value;
            }
            if (choice === 'keep' || choice === 'replace') keepTypes.add(row.type);
            if (choice === 'replace') result.replace.push({ type: row.type, data: row.suggested });
            if (choice === 'add') result.add.push({ type: row.type, data: row.suggested });
        });
        result.keep = Array.from(keepTypes);
        return result;
    }

    function countChanges(result) {
        return result.replace.length + result.add.length;
    }

    /**
     * Show the diff modal.
     * @param {object} opts - { title, subtitle, rows, onApply, onCancel }
     *   rows from diff(); onApply(result) with { keep:[], replace:[], add:[] };
     *   replace items are { type, data } (data = the suggested trigger);
     *   add items are { type, data } too.
     * @returns {HTMLElement} the overlay
     */
    function show(opts) {
        const rows = opts.rows || [];
        const panel = document.createElement('div');
        panel.style.cssText = 'background:var(--bg-panel);border:1px solid var(--border);border-radius:10px;width:94%;max-width:780px;max-height:86vh;display:flex;flex-direction:column;box-shadow:0 14px 48px rgba(0,0,0,.55);';

        const style = document.createElement('style');
        style.textContent = `
            .tsd-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border:1px solid var(--border);border-radius:14px;cursor:pointer;font-size:11px;color:var(--text);background:var(--bg-input);user-select:none;transition:border-color .12s,background .12s;}
            .tsd-pill input{display:none;}
            .tsd-pill.tsd-on{border-color:var(--accent,#3b82f6);background:color-mix(in srgb, var(--accent,#3b82f6) 14%, transparent);color:var(--text);}
            .tsd-pill:hover{border-color:var(--accent,#3b82f6);}
        `;
        panel.appendChild(style);

        // Header
        const header = document.createElement('div');
        header.style.cssText = 'padding:14px 16px 10px;border-bottom:1px solid var(--border-light);flex-shrink:0;';
        header.innerHTML = `
            <div style="font-size:14px;font-weight:700;">${escapeHtml(opts.title || 'Review suggested triggers')}</div>
            ${opts.subtitle ? `<div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${escapeHtml(opts.subtitle)}</div>` : ''}
            ${summaryHtml(rows)}
        `;
        panel.appendChild(header);

        // Body
        const body = document.createElement('div');
        body.style.cssText = 'padding:12px 16px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:10px;';
        if (!rows.length) {
            body.innerHTML = '<div style="font-size:12px;color:var(--text-muted);">Everything planned is already covered — nothing to change.</div>';
        } else {
            rows.forEach((row, i) => body.appendChild(buildRow(row, i)));
        }
        panel.appendChild(body);

        // Footer
        const footer = document.createElement('div');
        footer.style.cssText = 'padding:12px 16px;border-top:1px solid var(--border-light);display:flex;align-items:center;gap:8px;flex-shrink:0;';
        const summary = document.createElement('span');
        summary.style.cssText = 'margin-right:auto;font-size:11px;color:var(--text-muted);';
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn btn-sm';
        cancelBtn.textContent = 'Cancel';
        const applyBtn = document.createElement('button');
        applyBtn.className = 'btn btn-sm btn-blue';
        footer.appendChild(summary);
        footer.appendChild(cancelBtn);
        footer.appendChild(applyBtn);
        panel.appendChild(footer);

        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:10000;display:flex;align-items:center;justify-content:center;padding:16px;';
        overlay.appendChild(panel);

        // Live footer update as choices change.
        const refresh = () => {
            const result = collect(panel, rows);
            const n = countChanges(result);
            if (n === 0) {
                summary.textContent = 'No changes to apply.';
                applyBtn.textContent = 'Done';
                applyBtn.disabled = rows.some(r => r.status === 'conflict' || r.status === 'add');
            } else {
                summary.textContent = `${n} trigger${n === 1 ? '' : 's'} will be changed.`;
                applyBtn.textContent = `Apply ${n} change${n === 1 ? '' : 's'}`;
                applyBtn.disabled = false;
            }
            panel.querySelectorAll('.tsd-pill').forEach(p => p.classList.toggle('tsd-on', !!p.querySelector('input:checked')));
        };

        panel.addEventListener('change', refresh);
        refresh();

        const close = () => { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); };
        cancelBtn.onclick = () => { close(); if (opts.onCancel) opts.onCancel(); };
        applyBtn.onclick = () => {
            close();
            if (opts.onApply) opts.onApply(collect(panel, rows));
        };
        const onKey = (e) => { if (e.key === 'Escape') { close(); if (opts.onCancel) opts.onCancel(); } };
        document.addEventListener('keydown', onKey);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) { close(); if (opts.onCancel) opts.onCancel(); } });
        overlay._cleanup = () => document.removeEventListener('keydown', onKey);

        document.body.appendChild(overlay);
        return overlay;
    }

    /**
     * Merge a diff result into an existing trigger array (item-library form).
     * Semantics per trigger type (the modal's per-row choice):
     *   keep  → existing trigger stays untouched;
     *   replace → the suggested trigger replaces the existing one;
     *   add   → the suggested trigger is appended (no prior entry);
     *   skip both → the existing trigger is dropped and nothing is added.
     * @param {Array} existing - current trigger objects
     * @param {object} result  - { keep:[], replace:[{type,data}], add:[{type,data}] }
     * @returns {Array} merged trigger objects
     */
    function merge(existing, result) {
        const keepSet = new Set(result.keep || []);
        const replaceByType = new Map((result.replace || []).map(r => [r.type, r.data]));
        const addByType = new Map((result.add || []).map(r => [r.type, r.data]));
        const out = [];
        const done = new Set();

        for (const ex of existing || []) {
            const k = Array.isArray(ex.trigger_type) ? ex.trigger_type.join(',') : String(ex.trigger_type || '');
            if (replaceByType.has(k)) {
                if (!done.has(k)) { out.push(replaceByType.get(k)); done.add(k); }
                continue;
            }
            if (addByType.has(k)) continue; // prior entry of an "add" type doesn't exist, but be safe
            if (keepSet.has(k)) {
                if (!done.has(k)) { out.push(ex); done.add(k); }
                continue;
            }
            // skip both → dropped
        }
        for (const { type, data } of result.add || []) {
            if (done.has(type)) continue;
            out.push(data);
            done.add(type);
        }
        return out;
    }

    return { diff, covered, describe, show, merge };
})();