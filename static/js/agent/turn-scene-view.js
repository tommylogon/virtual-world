/**
 * turn-scene-view.js — scene-first view for the human turn panel
 * (task-333 Phase 1)
 *
 * Fetches GET /api/scene/<char> and renders clickable chips for the area,
 * people, things and ways out. Hover = free look (a preview card — no turn
 * cost); click = a context menu whose entries FILL THE DRAFT via onDraft()
 * — nothing is ever submitted from here (compose-then-commit).
 *
 * Way menus follow the v2.7 mockup rules: labels stay clean, and hidden
 * aspects (locked / needs force) appear only through the backend's per-player
 * discovered flags (set by examining the way or failing to go through it).
 * Darkness: when scene.area.dark is true the chips degrade client-side.
 *
 * Load AFTER api.js, BEFORE human-turn-composer.js.
 */

window.TurnSceneView = (() => {
    'use strict';

    const STYLE_ID = 'tsv-styles';

    function ensureStyles() {
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            #htc-scene { padding:10px 16px 4px; border-bottom:1px solid #333a45; }
            #htc-scene .tsv-desc { color:#9aa3b2; font-style:italic; line-height:1.5; margin:2px 0 10px; font-size:12.5px; }
            .tsv-zone { margin-bottom:9px; }
            .tsv-zlabel { font-size:10px; text-transform:uppercase; letter-spacing:1.2px; color:#6b7686; margin-bottom:5px; }
            .tsv-chips { display:flex; flex-wrap:wrap; gap:6px; }
            .tsv-chip { display:inline-flex; align-items:center; gap:5px; padding:4px 10px;
                        background:#262b35; border:1px solid #333a45; border-radius:999px;
                        color:#dfe3ea; font-size:12px; cursor:pointer; transition:all .15s; position:relative; }
            .tsv-chip:hover { border-color:#4f9cf9; background:#1d2733; transform:translateY(-1px); }
            .tsv-chip.tsv-exit { color:#8fd3c7; border-color:#2a4a44; }
            .tsv-chip.tsv-exit:hover { border-color:#3fae94; background:#152825; }
            .tsv-chip.tsv-person { color:#eec9ff; border-color:#3d2b52; }
            .tsv-chip.tsv-person:hover { border-color:#a86ee0; background:#241a33; }
            .tsv-chip .tsv-em { font-size:11px; color:#78828e; font-style:italic; }
            .tsv-chip.tsv-shut::before { content:'●'; color:#c96a46; font-size:7px; margin-right:-1px; }
            .tsv-hint { font-size:10.5px; color:#5b6570; margin-top:3px; }

            /* darkness degradation */
            #htc-scene.tsv-dark .tsv-chips { opacity:.45; }
            #htc-scene.tsv-dark .tsv-desc { color:#5b6570; }

            /* free-look hover card */
            .tsv-hovercard { position:fixed; z-index:1300; width:290px; background:#1a1f27;
                             border:1px solid #3a4350; border-radius:10px; padding:9px 11px;
                             box-shadow:0 14px 34px rgba(0,0,0,.75); pointer-events:none; }
            .tsv-hovercard .tsv-ht { font-size:12px; color:#e8edf2; font-weight:600; }
            .tsv-hovercard .tsv-hb { font-size:12px; color:#98a3ae; line-height:1.5; padding-top:4px; white-space:pre-wrap; }
            .tsv-hovercard .tsv-hf { font-size:10px; color:#57c98f; padding-top:5px; letter-spacing:.5px; }

            /* context menu */
            .tsv-scrim { position:fixed; inset:0; z-index:1390; }
            .tsv-ctx { position:fixed; z-index:1400; background:#1a1f27; border:1px solid #333b47;
                       border-radius:10px; padding:4px; min-width:200px; max-height:60vh; overflow-y:auto;
                       box-shadow:0 12px 30px rgba(0,0,0,.7); }
            .tsv-ctx-title { font-size:10.5px; color:#6b7686; padding:5px 9px 3px; text-transform:uppercase; letter-spacing:1px; }
            .tsv-ctx button { display:block; width:100%; text-align:left; background:none; border:0;
                              color:#d5dde5; padding:6px 9px; border-radius:6px; font-size:12.5px; cursor:pointer; }
            .tsv-ctx button:hover:not(:disabled) { background:rgba(79,156,249,.22); }
            .tsv-ctx button:disabled { color:#55606c; cursor:not-allowed; }
            .tsv-ctx button .why { float:right; font-size:10.5px; color:#55606c; max-width:120px; padding-left:8px; }
            .tsv-ctx button.tsv-danger { color:#ff9d9d; }
            .tsv-ctx button.tsv-danger:hover:not(:disabled) { background:rgba(201,58,58,.25); }
            .tsv-ctx button.tsv-back { color:#8b95a1; font-size:11.5px; border-bottom:1px solid #232932; border-radius:0; }
        `;
        document.head.appendChild(style);
    }

    function el(tagName, className, text) {
        const node = document.createElement(tagName);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    /** Draft payload → composer fields. parts: {action,item,target} */
    function draftParts(parts) {
        return {
            action: parts.action || '',
            item: parts.item || '',
            target: parts.target || '',
        };
    }

    /**
     * Legacy data stores the literal "none" for walk-through ways (the
     * engine's movement.py special-cases it). Return '' for none-like
     * values so the panel never gates Go/Open on them.
     */
    function requiresGate(way) {
        const req = String(way.requires || '').trim().toLowerCase();
        return (req && !['none', 'nothing', 'no'].includes(req)) ? way.requires : '';
    }

    // ── menu builders ────────────────────────────────────────────────

    function buildItemMenu(entry) {
        // Backend contract: TriggerSystem._get_available_actions entries
        // ({action,label,enabled,reason}) already encode state gates.
        const actions = Array.isArray(entry.available_actions) ? entry.available_actions : [];
        const menus = [];
        menus.push({ label: `Examine ${entry.name}`, run: () => draftParts({ action: 'examine', item: entry.name }) });
        for (const a of actions) {
            if (a.action === 'examine') continue;
            menus.push({
                label: a.label || a.action,
                enabled: a.enabled !== false,
                reason: a.reason || '',
                run: () => draftParts({ action: a.action === 'toggle' ? 'toggle' : a.action, item: entry.name }),
                danger: a.action === 'drop',
            });
        }
        return menus;
    }

    function buildWayMenu(way, conditions) {
        const grappled = (conditions || []).some(c => String(c).toLowerCase().includes('grappl'));
        const requires = requiresGate(way);
        const closed = way.state !== 'open';
        const dirText = way.direction || '';
        const destText = way.to ? `${dirText} → ${way.to}` : dirText;
        const menus = [{ label: `Examine ${way.name}`, run: () => draftParts({ action: 'examine', item: way.name }) }];
        if (requires) {
            menus.push({ label: `Go ${destText}`, enabled: false, reason: `requires ${requires}` });
        } else if (grappled) {
            menus.push({ label: `Go ${destText}`, enabled: false, reason: 'something holds you back' });
        } else if (way.state === 'locked') {
            // state only reported locked once discovered (backend flag)
            menus.push({ label: `Go ${dirText}`, enabled: false, reason: 'locked' });
        } else if (way.state === 'blocked') {
            menus.push({ label: `Go ${dirText}`, enabled: false, reason: 'blocked' });
        } else {
            menus.push({ label: `Go ${destText}`, run: () => draftParts({ action: 'go', item: dirText }) });
        }
        if (!requires && closed && !['locked', 'blocked'].includes(way.state)) {
            menus.push({ label: `Open ${way.name}`, run: () => draftParts({ action: 'open', item: way.name }) });
        }
        if (!closed && !requires) {
            menus.push({ label: `Close ${way.name}`, run: () => draftParts({ action: 'close', item: way.name }) });
        }
        return menus;
    }

    function buildPersonMenu(person) {
        // Meeting is sighting-based (task-154): looking at the room registers
        // the acquaintance — the name reveals on the NEXT scene render. No
        // introduction action exists or is needed; Talk just focuses say.
        const menus = [
            { label: 'Talk to', talkFocus: true },
        ];
        // Examine resolves real names, aliases, AND descriptive labels
        // (matching.py _match_character_name tiers) — the masked stranger
        // label drafts fine and resolves server-side.
        menus.push({
            label: `Examine ${person.display_name}`,
            run: () => draftParts({ action: 'examine', target: person.display_name }),
        });
        menus.push({
            label: `Attack ${person.display_name}`,
            danger: true,
            run: () => draftParts({ action: 'attack', target: person.display_name }),
        });
        return menus;
    }

    // ── hover look cards (free look) ─────────────────────────────────

    function lookLines(scene, kind, obj) {
        if (scene.area.dark && kind !== 'area') {
            return { title: '…something', body: 'too dark to make out much.', foot: 'free look · no turn cost' };
        }
        if (kind === 'area') {
            return {
                title: obj.display_name || obj.name,
                body: obj.desc + (obj.dark ? '\n\nthe light here is poor.' : ''),
                foot: 'free look · no turn cost',
            };
        }
        if (kind === 'exit') {
            const bits = [`${obj.direction}${obj.to ? ' → ' + obj.to : ''}`];
            if (obj.state === 'locked') bits.push('locked');
            else if (obj.state === 'blocked') bits.push('blocked');
            else if (obj.state !== 'open') bits.push('closed');
            let body = [obj.desc, bits.join(' · ')].filter(Boolean).join('\n');
            if (obj.visible_in_direction) body += `\n\nthrough it you can see: ${obj.visible_in_direction}`;
            else if (obj.see_through && obj.to) body += `\n\nthrough it: the ${obj.to}, faintly.`;
            if (obj.needs_force_known) body += '\n\nclearly stuck — opening it will take muscle.';
            if (obj.known_locked) body += '\n\nlocked.';
            const reqText = requiresGate(obj);
            if (reqText) body += `\n\ngetting through needs ${reqText}.`;
            if (obj.auto_close) body += '\n\nit swings shut behind people.';
            return { title: obj.name, body, foot: 'free look · no turn cost' };
        }
        if (kind === 'person') {
            let body = obj.desc;
            if (obj.tags.length) body += `\n\n(${obj.tags.join(', ')})`;
            let foot = 'free look · no turn cost';
            if (!obj.name) {
                foot = obj.met
                    ? 'recognized — but you don\'t know their name yet'
                    : 'a stranger — you don\'t know their name yet';
            }
            return { title: obj.display_name, body, foot };
        }
        // scene item
        const stateBit = ['open'].includes(obj.state) ? ' · open' : '';
        return {
            title: `${obj.name}${stateBit}`,
            body: obj.desc,
            foot: 'free look · no turn cost',
        };
    }

    // ── render ───────────────────────────────────────────────────────

    function attachHover(host, getPos, getContent) {
        const card = el('div', 'tsv-hovercard');
        card.style.display = 'none';
        document.body.appendChild(card);
        const show = (e) => {
            const content = getContent();
            if (!content) return;
            card.textContent = '';
            card.appendChild(el('div', 'tsv-ht', content.title));
            card.appendChild(el('div', 'tsv-hb', content.body));
            card.appendChild(el('div', 'tsv-hf', content.foot));
            const r = getPos(e).getBoundingClientRect();
            card.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 306)) + 'px';
            card.style.top = Math.min(r.bottom + 6, window.innerHeight - 160) + 'px';
            card.style.display = 'block';
        };
        const hide = () => { card.style.display = 'none'; };
        host.addEventListener('mouseenter', show);
        host.addEventListener('mouseleave', hide);
        host.addEventListener('click', hide);
        return hide;
    }

    function openMenu(x, y, title, buttons, onDraft, onTalkFocus) {
        closeMenu();
        const scrim = el('div', 'tsv-scrim');
        scrim.addEventListener('click', closeMenu);
        const box = el('div', 'tsv-ctx');
        box.appendChild(el('div', 'tsv-ctx-title', title));
        for (const b of buttons) {
            const btn = el('button');
            if (b.danger) btn.classList.add('tsv-danger');
            if (b.talkFocus) btn.classList.add('tsv-back');
            btn.appendChild(document.createTextNode(b.label));
            if (b.reason) btn.appendChild(el('span', 'why', '— ' + b.reason));
            btn.disabled = b.enabled === false;
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                closeMenu();
                if (b.enabled === false) return;
                if (b.talkFocus) { if (onTalkFocus) onTalkFocus(); return; }
                if (typeof b.run === 'function' && onDraft) onDraft(b.run());
            });
            box.appendChild(btn);
        }
        box.style.left = Math.max(8, Math.min(x, window.innerWidth - 240)) + 'px';
        box.style.top = Math.min(y, window.innerHeight - 260) + 'px';
        document.body.appendChild(scrim);
        document.body.appendChild(box);
        _menuCleanup = () => { scrim.remove(); box.remove(); };
    }

    let _menuCleanup = null;
    function closeMenu() {
        if (_menuCleanup) { _menuCleanup(); _menuCleanup = null; }
    }

    /**
     * Fetch the raw scene payload (the composer also uses it for the
     * autocomplete datalist and meta line).
     */
    async function fetch(charName) {
        // NOTE: ApiClient is a top-level class (global binding, not a
        // window property) — reference it bare, like the rest of the app.
        return ApiClient.getScene(charName);
    }

    /** Render a fetched scene payload into *host*. */
    function renderScene(host, scene, handlers) {
        ensureStyles();
        closeMenu();
        host.textContent = '';
        host.className = '';
        const dark = !!(scene.area && scene.area.dark);
        if (dark) host.classList.add('tsv-dark');

        const chipClick = (e, title, buttons) =>
            openMenu(e.clientX, Math.min(e.clientY, window.innerHeight - 260),
                     title, buttons, handlers.onDraft, handlers.onTalkFocus);

        // area header chip + description
        const areaRow = el('div', 'tsv-zone');
        const areaBtn = el('button', 'tsv-chip tsv-area',
                           '📍 ' + (scene.area.display_name || scene.area.name));
        areaBtn.addEventListener('click', (e) => chipClick(e, scene.area.name, [
            { label: 'Examine the room', run: () => draftParts({ action: 'examine', item: 'room' }) },
            { label: 'Look around', run: () => draftParts({ action: 'look' }) },
            { label: 'Listen', run: () => draftParts({ action: 'listen' }) },
        ]));
        attachHover(areaBtn, () => areaBtn,
                    () => lookLines(scene, 'area', Object.assign({}, scene.area, { dark })));
        areaRow.appendChild(areaBtn);
        host.appendChild(areaRow);

        const desc = el('p', 'tsv-desc',
                        dark ? 'shapes in the gloom — details are lost.' : (scene.area.desc || ''));
        if (desc.textContent) host.appendChild(desc);

        const zone = (label) => {
            const z = el('div', 'tsv-zone');
            z.appendChild(el('div', 'tsv-zlabel', label));
            const chips = el('div', 'tsv-chips');
            z.appendChild(chips);
            host.appendChild(z);
            return chips;
        };

        const mkChip = (parent, cls, labelText, onClick, hoverContent) => {
            const chip = el('button', 'tsv-chip' + (cls ? ' ' + cls : ''), labelText);
            chip.addEventListener('click', onClick);
            if (hoverContent) attachHover(chip, () => chip, hoverContent);
            parent.appendChild(chip);
            return chip;
        };

        // people
        const peopleChips = zone('People here');
        if (!scene.people.length) peopleChips.appendChild(el('span', 'tsv-hint', 'nobody.'));
        for (const p of scene.people) {
            const chip = mkChip(peopleChips, 'tsv-person', p.display_name,
                (e) => chipClick(e, p.display_name, buildPersonMenu(p)),
                () => lookLines(scene, 'person', p));
            chip.title = '';
        }

        // items
        const itemChips = zone('Things you can see');
        if (!scene.items.length) itemChips.appendChild(el('span', 'tsv-hint', 'nothing of note.'));
        for (const item of scene.items) {
            const label = dark ? 'something' : item.name;
            mkChip(itemChips, '', label,
                (e) => chipClick(e, item.name, buildItemMenu(item)),
                () => lookLines(scene, 'item', item));
        }

        // ways
        const wayChips = zone('Ways out');
        if (!scene.ways.length) wayChips.appendChild(el('span', 'tsv-hint', 'no ways out.'));
        for (const way of scene.ways) {
            const shut = way.state !== 'open' && !way.see_through;
            const markers =
                (way.state === 'locked' ? ' 🔒' : '') +
                (way.state === 'blocked' ? ' ⛔' : '') +
                (requiresGate(way) ? ' ⛰' : '');
            const em = el('span', 'tsv-em', `${way.direction}${markers}`);
            const chip = el('button', 'tsv-chip tsv-exit' + (shut ? ' tsv-shut' : ''));
            chip.appendChild(document.createTextNode((dark ? 'a way' : way.name) + ' '));
            chip.appendChild(em);
            chip.addEventListener('click', (e) =>
                chipClick(e, way.name, buildWayMenu(way, scene.you.conditions)));
            attachHover(chip, () => chip, () => lookLines(scene, 'exit', way));
            wayChips.appendChild(chip);
        }

        host.appendChild(el('div', 'tsv-hint',
            'hover = free look · click = what you can do with it · picks fill the draft, nothing fires until Act'));
    }

    /** Convenience wrapper: fetch + renderScene, with inline error note. */
    async function render(charName, host, handlers) {
        let scene;
        try {
            scene = await fetch(charName);
        } catch (err) {
            ensureStyles();
            host.textContent = '';
            host.className = '';
            host.appendChild(el('div', 'tsv-hint', `scene unavailable (${err.message})`));
            return;
        }
        if (!scene || scene.error) {
            ensureStyles();
            host.textContent = '';
            host.className = '';
            host.appendChild(el('div', 'tsv-hint',
                `scene unavailable (${(scene && scene.error) || 'unknown'})`));
            return;
        }
        renderScene(host, scene, handlers);
    }

    /** Shared context-menu entry point (the You strip uses it too). */
    function menu(x, y, title, buttons, onDraft) {
        openMenu(x, y, title, buttons, onDraft, null);
    }

    return { render, renderScene, fetch, menu };
})();
