/**
 * turn-you-strip.js — the "You" strip for the human turn panel
 * (task-333 full redesign): vitals bars, visible condition chips,
 * carrying/wearing chips with context menus, activity chip with stop,
 * and the collapsible "what you know" (recent memories).
 *
 * Data comes from GET /api/scene/<char> → scene.you. Menu buttons only
 * FILL THE DRAFT via handlers.onDraft — nothing submits from here.
 *
 * Load AFTER turn-scene-view.js (shares its context-menu helper),
 * BEFORE human-turn-composer.js.
 */

window.TurnYouStrip = (() => {
    'use strict';

    const STYLE_ID = 'tys-styles';

    function ensureStyles() {
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            .htc-you { border-top:1px solid #333a45; background:#171a21; padding:9px 16px; }
            .htc-you-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
            .htc-you-row + .htc-you-row { margin-top:7px; }
            .tys-label { font-size:10px; text-transform:uppercase; letter-spacing:1px; color:#5b6570; }
            .tys-vital { display:flex; align-items:center; gap:5px; font-size:11.5px; color:#9aa3b2; }
            .tys-bar { width:56px; height:6px; background:#1d2330; border-radius:3px; overflow:hidden; }
            .tys-bar i { display:block; height:100%; border-radius:3px; }
            .tys-cond { font-size:11px; color:#ffb37a; background:#241a10; border:1px solid #40301c;
                        border-radius:999px; padding:2px 9px; }
            .tys-inv { font-size:11.5px; padding:3px 10px; background:#262b35; border:1px solid #333a45;
                       border-radius:999px; color:#c4ccd6; cursor:pointer; }
            .tys-inv:hover { border-color:#c96a46; color:#ffd9c9; background:#20161a; }
            .tys-dur { font-size:9px; color:#8b95a1; margin-left:5px; text-transform:uppercase; letter-spacing:.5px; }
            .tys-load { font-size:10.5px; color:#9aa3b2; border:1px solid #333a45; border-radius:999px;
                        padding:2px 9px; }
            .tys-load-warn { color:#ffd28f; border-color:#4a3a1c; background:#201a10; }
            .tys-load-bad { color:#ff7a7a; border-color:#4a2020; background:#1f1112; }
            .tys-activity { cursor:pointer; color:#ffd28f; }
            .tys-known-toggle { background:none; border:0; color:#6b7686; font-size:11.5px; cursor:pointer; margin-left:auto; }
            .htc-you .tys-known { font-size:12px; color:#8b95a1; margin-top:7px; line-height:1.5;
                                  border-left:2px solid #2a303b; padding-left:10px; display:grid; gap:5px; }
        `;
        document.head.appendChild(style);
    }

    function el(tag, cls, text) {
        const node = document.createElement(tag);
        if (cls) node.className = cls;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    // Preferred display order; any vitals outside this list render after
    // it (task-342: the strip shows ALL vitals, not a hardcoded six).
    const VITAL_ORDER = ['HP', 'Energy', 'Hunger', 'Thirst', 'Hygiene', 'Bladder',
                         'Temperature', 'Sanity', 'Social', 'Entertainment', 'Mana'];

    function orderedVitals(vitals) {
        const keys = Object.keys(vitals || {})
            .filter(k => !k.startsWith('Max_'));
        const head = VITAL_ORDER.filter(k => keys.includes(k));
        return head.concat(keys.filter(k => !head.includes(k)).sort());
    }

    function vitalBar(vitals, key, charName) {
        const raw = vitals[key];
        const pct = window.VitalColor.percent(vitals, key);
        const suffix = window.VitalColor.suffix(key);
        const wrap = el('span', 'tys-vital');
        wrap.style.cursor = 'pointer';
        const _val = Math.round(Number(raw) || 0);
        // Human natural language on hover — the same describeVital() prose the
        // agent prompts use ("You are hungry. Your stomach feels empty.") plus
        // a one-line "what this vital does" (task-129). Rendered as a styled
        // free-look card (same hover pattern as the scene's item/way chips)
        // instead of the slow native title tooltip.
        const _nl = (window.PromptBuilder?.describeVital?.(vitals, key) || '').trim();
        const _why = window.VitalThresholds?.explain?.(key) || '';
        if (window.TurnSceneView?.attachHover) {
            window.TurnSceneView.attachHover(wrap, () => wrap, () => ({
                title: `${key} ${_val}${suffix}`,
                body: [_why, _nl || 'no pressing need here.'].filter(Boolean).join('\n'),
                foot: 'click for details',
            }));
        }
        wrap.appendChild(el('span', null, key));
        const bar = el('span', 'tys-bar');
        const fill = el('i');
        fill.style.width = pct.toFixed(0) + '%';
        fill.style.background = window.VitalColor.bar(vitals, key);
        bar.appendChild(fill);
        wrap.appendChild(bar);
        wrap.appendChild(el('span', null, `${Math.round(Number(raw) || 0)}${suffix}`));
        // task-342: click opens the same vital detail modal as the inspector
        wrap.addEventListener('click', () => {
            if (typeof window.openVitalModal === 'function' && charName) {
                window.openVitalModal(charName, key);
            }
        });
        return wrap;
    }

    // Natural-language durability label from uses/max_uses (task-161) —
    // humans read "worn", never "3/10".
    function durabilityLabel(item) {
        const maxUses = parseInt(item.max_uses, 10) || 0;
        const uses = parseInt(item.uses ?? -1, 10);
        if (maxUses <= 0 || uses < 0) return '';
        const ratio = uses / maxUses;
        if (uses <= 0) return 'broken';
        if (ratio <= 0.25) return 'about to break';
        if (ratio <= 0.5) return 'battered';
        if (ratio <= 0.9) return 'worn';
        return 'pristine';
    }

    // Natural-language carry-load chip for row 1 (task-156 presentation) —
    // same tier words the agent prompt uses.
    function loadChip(you) {
        const load = you.carry_load;
        if (!load) return null;
        const ratio = load.ratio || 0;
        let label = '';
        let cls = 'tys-load';
        if (ratio >= 1.0) { label = 'cannot carry more'; cls += ' tys-load-bad'; }
        else if (ratio >= 0.8) { label = 'carrying your limit'; cls += ' tys-load-bad'; }
        else if (ratio >= 0.5) { label = 'heavily loaded'; cls += ' tys-load-warn'; }
        else if (ratio >= 0.25) { label = 'light load'; }
        else { label = 'barely carrying anything'; }
        const chip = el('span', cls, `⚖️ ${label}`);
        if (window.TurnSceneView?.attachHover) {
            window.TurnSceneView.attachHover(chip, () => chip, () => ({
                title: 'Carry load',
                body: `You're ${label}. You can stow or drop things (stow <item>) to lighten up.`,
                foot: '',
            }));
        }
        return chip;
    }

    function invButtons(kind, items, handlers) {
        const buttons = [];
        for (const item of items || []) {
            const actions = Array.isArray(item.actions) ? item.actions : [];
            buttons.push({
                label: `Examine ${item.name}`,
                run: () => ({ action: 'examine', item: item.name, target: '' }),
            });
            if (kind === 'carried') {
                if (actions.includes('use')) {
                    buttons.push({ label: `Use ${item.name}`,
                        run: () => ({ action: 'use', item: item.name, target: '' }) });
                }
                if (actions.includes('eat') || actions.includes('food')) {
                    buttons.push({ label: `Eat ${item.name}`,
                        run: () => ({ action: 'eat', item: item.name, target: '' }) });
                }
                if (actions.includes('drink')) {
                    buttons.push({ label: `Drink ${item.name}`,
                        run: () => ({ action: 'drink', item: item.name, target: '' }) });
                }
                buttons.push({ label: `Drop ${item.name}`, danger: true,
                    run: () => ({ action: 'drop', item: item.name, target: '' }) });
            } else {
                buttons.push({ label: `Remove ${item.name}${item.slot ? ` (${item.slot})` : ''}`,
                    run: () => ({ action: 'remove', item: item.name, target: '' }) });
            }
        }
        return buttons;
    }

    /**
     * Render the strip into *host*.
     * handlers: { onDraft(parts), menu(x, y, title, buttons) }
     */
    function render(host, you, handlers) {
        ensureStyles();
        host.textContent = '';
        host.className = 'htc-you';
        if (!you) return;

        // row 1 — vitals + conditions + activity
        const row1 = el('div', 'htc-you-row');
        row1.appendChild(el('span', 'tys-label', 'You'));
        const vitals = you.vitals || {};
        for (const key of orderedVitals(vitals)) {
            row1.appendChild(vitalBar(vitals, key, you.name));
        }
        for (const cond of you.conditions || []) {
            const label = String(cond).replace(/_/g, ' ');
            row1.appendChild(el('span', 'tys-cond', label));
        }
        const activity = you.activity;
        if (activity && activity.type) {
            const dur = activity.duration_ticks ? ` · ${activity.elapsed_ticks || 0}/${activity.duration_ticks}m` : '';
            const chip = el('button', 'tys-inv tys-activity',
                            `⏸ ${activity.type}${dur} ✕`);
            chip.title = 'active activity — the turn queue skips you while it lasts';
            chip.addEventListener('click', () => handlers.onDraft({ action: 'wake', item: '', target: '' }));
            row1.appendChild(chip);
        }
        const loadChipEl = loadChip(you);
        if (loadChipEl) row1.appendChild(loadChipEl);
        host.appendChild(row1);

        // row 2 — carrying / wearing / known toggle
        const row2 = el('div', 'htc-you-row');
        row2.appendChild(el('span', 'tys-label', 'Carrying'));
        // Free-look hover on inventory chips (same card as the scene's ways/
        // items): you always know your own gear, so no darkness degradation.
        const lookScene = { area: { dark: false } };
        const attachLookHover = (chip, item) => {
            if (!window.TurnSceneView?.attachHover || !window.TurnSceneView?.lookLines) return;
            window.TurnSceneView.attachHover(
                chip, () => chip,
                () => window.TurnSceneView.lookLines(lookScene, 'item', item));
        };
        const carried = you.carrying || [];
        for (const item of carried) {
            const chip = el('button', 'tys-inv', item.name);
            const dur = durabilityLabel(item);
            if (dur) {
                const tag = el('span', 'tys-dur', dur);
                chip.appendChild(tag);
            }
            attachLookHover(chip, item);
            chip.addEventListener('click', (e) =>
                handlers.menu(e.clientX, e.clientY, item.name,
                              invButtons('carried', [item], handlers)));
            row2.appendChild(chip);
        }
        if (!carried.length) row2.appendChild(el('span', 'tys-label', '—'));
        const wearLabel = el('span', 'tys-label');
        wearLabel.style.marginLeft = '10px';
        wearLabel.textContent = 'Wearing';
        row2.appendChild(wearLabel);
        const worn = you.wearing || [];
        for (const item of worn) {
            const chip = el('button', 'tys-inv', item.name);
            const dur = durabilityLabel(item);
            if (dur) {
                const tag = el('span', 'tys-dur', dur);
                chip.appendChild(tag);
            }
            attachLookHover(chip, item);
            chip.addEventListener('click', (e) =>
                handlers.menu(e.clientX, e.clientY, item.name,
                              invButtons('worn', [item], handlers)));
            row2.appendChild(chip);
        }
        if (!worn.length) row2.appendChild(el('span', 'tys-label', '—'));
        const knownBtn = el('button', 'tys-known-toggle', '▸ what you know');
        let knownOpen = false;
        let knownBox = null;
        knownBtn.addEventListener('click', () => {
            knownOpen = !knownOpen;
            knownBtn.textContent = knownOpen ? '▾ what you know' : '▸ what you know';
            if (knownOpen) {
                knownBox = el('div', 'tys-known');
                const memories = you.recent_memories || [];
                if (!memories.length) knownBox.appendChild(el('div', null, 'nothing worth noting yet.'));
                for (const memory of memories) knownBox.appendChild(el('div', null, memory));
                host.appendChild(knownBox);
            } else if (knownBox) {
                knownBox.remove();
                knownBox = null;
            }
        });
        row2.appendChild(knownBtn);
        host.appendChild(row2);
    }

    return { render };
})();
