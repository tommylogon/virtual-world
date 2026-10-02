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
 *
 * @module agent/turn-scene-view — scene-first chips for the turn panel
 * @contributes TurnSceneView: GET /api/scene/<char> → clickable area/people/things/ways chips + draft-filling menus
 * @powers The human turn — seeing and choosing what's around you without spending the turn (hover = free look)
 * @relates feeds human-turn-composer via onDraft; shares the context-menu helper with turn-you-strip
 * @docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

interface TurnSceneViewWindowSurface { TurnSceneView: unknown }
(window as unknown as TurnSceneViewWindowSurface).TurnSceneView = (() => {
    'use strict';

    const STYLE_ID = 'tsv-styles';

    /**
     * character-art.js is a classic-script global absent from the declared
     * Window surface. Read it lazily, never cached at load, because it may
     * not have run yet when this script first executes.
     */
    function characterArt(): TurnSceneViewArtApi | undefined {
        return (window as unknown as { CharacterArt?: TurnSceneViewArtApi }).CharacterArt;
    }

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
            /* Current-emotion profile thumbnail; click opens the big portrait. */
            .tsv-avatar { width:18px; height:18px; border-radius:50%; object-fit:cover;
                          border:1px solid #3d2b52; cursor:zoom-in; flex:none; }
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

    function el(tagName: string, className?: string, text?: string): HTMLElement {
        const node = document.createElement(tagName);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    /** Draft payload → composer fields. parts: {action,item,target} */
    function draftParts(parts: Partial<DraftParts>): DraftParts {
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
    function requiresGate(way: WayLike): string {
        const req = String(way.requires || '').trim().toLowerCase();
        return (req && !['none', 'nothing', 'no'].includes(req)) ? way.requires as string : '';
    }

    // ── menu builders ────────────────────────────────────────────────

    function buildItemMenu(entry: SceneItem): MenuButton[] {
        // Backend contract: TriggerSystem._get_available_actions entries
        // ({action,label,enabled,reason}) already encode state gates.
        const actions = Array.isArray(entry.available_actions) ? entry.available_actions : [];
        const menus: MenuButton[] = [];
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

    function buildWayMenu(way: SceneWay, conditions: string[], atWayId: string): MenuButton[] {
        const grappled = (conditions || []).some((c: string) => String(c).toLowerCase().includes('grappl'));
        const requires = requiresGate(way);
        const closed = way.state !== 'open';
        const dirText = way.direction || '';
        const destText = way.to ? `${dirText} → ${way.to}` : dirText;
        const menus: MenuButton[] = [{ label: `Examine ${way.name}`, run: () => draftParts({ action: 'examine', item: way.name }) }];
        if (atWayId !== way.way_id) {
            menus.push({ label: `Approach ${dirText || way.name}`, run: () => draftParts({ action: 'approach', item: dirText || way.name }) });
        }
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

    // task-610: the backend dispatches ~23 character-to-character verbs but
    // the person menu exposed only Talk / Examine / Attack. This mirrors the
    // full person-directed set. The menu is an affordance only — every entry
    // drafts text the server validates, exactly like the way menu. Entries
    // whose argument the menu cannot know (a steal target's inventory, a
    // name alias) are deliberately not offered; see task-610 notes.
    function buildPersonMenu(person: ScenePerson, scene: Scene): MenuButton[] {
        const you = ((scene && scene.you) || {}) as Partial<TurnSceneViewSceneYou>;
        const conditions = (you.conditions || []).map((c: unknown) => String(c).toLowerCase());
        const grappled = conditions.some((c) => c.includes('grappl'));
        const carrying = you.carrying || [];
        const abilities = you.known_abilities || [];
        // Prefer the world's own toggle (the engine gate); the client config
        // mirrors it and is used only as a fallback before state loads.
        const mature = !!(
            (window.worldState && worldState.data && worldState.data.mature_content)
            || ((window as unknown as { config?: { matureContent?: boolean } }).config?.matureContent)
        );
        const who = person.display_name;

        // Speaking to someone is two different things, so the menu offers both:
        //   · Whisper to them — directed. Only they hear it, plus anyone standing
        //     close enough to be "at" you who is a friend or better (the engine's
        //     whisper audience, engine/speech.py). Use it for a secret.
        //   · Say it aloud — undirected. Everyone in the area hears it, exactly
        //     as if you had simply spoken. This is the "the whole room can hear"
        //     option, and it is NOT addressed to this person in any way.
        const menus: MenuButton[] = [
            { label: `Whisper to ${who}`, talk: true, volume: 'whisper', target: who },
            { label: `Say aloud (everyone hears)`, talk: true, volume: 'say' },
        ];
        // Examine resolves real names, aliases, AND descriptive labels
        // (matching.py _match_character_name tiers) — the masked stranger
        // label drafts fine and resolves server-side.
        menus.push({
            label: `Examine ${who}`,
            run: () => {
                // "Big overlay on examine": examining a character shows their
                // live art (current full body, else the profile enlarged) even
                // when the draft can't be submitted (react phase).
                const artView = characterArt();
                if (artView) artView.open({ name: person.display_name, nodeId: person.id });
                return draftParts({ action: 'examine', target: person.display_name });
            },
        });
        menus.push({ label: `Attack ${who}`, danger: true, run: () => draftParts({ action: 'attack', target: who }) });
        menus.push({ label: `Grab ${who} (grapple)`, run: () => draftParts({ action: 'grab', target: who }) });
        menus.push({ label: `Lead ${who}`, run: () => draftParts({ action: 'lead', target: who }) });
        menus.push({ label: `Wake ${who}`, run: () => draftParts({ action: 'wake', target: who }) });
        if (grappled) menus.push({ label: 'Escape the grapple', run: () => draftParts({ action: 'escape' }) });
        menus.push({ label: `Release ${who}`, run: () => draftParts({ action: 'release', target: who }) });

        // Give: choose from what you are actually carrying. applyDraft joins
        // action/item/target with spaces, so the connector lives in the action
        // phrase ("give Dagger to" + "Tester"), not a separate field.
        if (carrying.length) {
            menus.push({
                label: `Give… (${carrying.length})`,
                sub: {
                    title: `Give what to ${who}?`,
                    buttons: carrying.slice(0, 20).map((item) => ({
                        label: item.name,
                        run: () => draftParts({ action: `give ${item.name} to`, target: who }),
                    })),
                },
            });
        }
        // Teach: choose from the abilities you know.
        if (abilities.length) {
            menus.push({
                label: `Teach… (${abilities.length})`,
                sub: {
                    title: `Teach what to ${who}?`,
                    buttons: abilities.slice(0, 20).map((ability) => ({
                        label: ability,
                        run: () => draftParts({ action: `teach skill:${ability} to`, target: who }),
                    })),
                },
            });
        }
        // Intimacy verbs are only valid in mature worlds (task-211); offer the
        // submenu behind the same toggle the engine gates on.
        if (mature) {
            menus.push({
                label: 'Intimacy…',
                sub: {
                    title: `Intimacy with ${who}`,
                    buttons: ['kiss', 'caress', 'lick', 'suck', 'bite', 'pinch', 'blow', 'tickle'].map((verb) => ({
                        label: verb[0].toUpperCase() + verb.slice(1),
                        run: () => draftParts({ action: verb, target: who }),
                    })),
                },
            });
        }
        return menus;
    }

    // ── hover look cards (free look) ─────────────────────────────────

    function lookLines(scene: Scene, kind: string, obj: LookTarget): LookCard {
        if (scene.area.dark && kind !== 'area') {
            return { title: '…something', body: 'too dark to make out much.', foot: 'free look · no turn cost' };
        }
        if (kind === 'area') {
            return {
                title: (obj.display_name || obj.name) as string,
                body: (obj.desc as string) + (obj.dark ? '\n\nthe light here is poor.' : ''),
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
            return { title: obj.name as string, body, foot: 'free look · no turn cost' };
        }
        if (kind === 'person') {
            let body = obj.desc as string;
            if ((obj.tags as string[]).length) body += `\n\n(${(obj.tags as string[]).join(', ')})`;
            let foot = 'free look · no turn cost';
            if (!obj.name) {
                foot = obj.met
                    ? 'recognized — but you don\'t know their name yet'
                    : 'a stranger — you don\'t know their name yet';
            }
            return { title: obj.display_name as string, body, foot };
        }
        // scene item (or carried/worn item from the You strip — desc + slot)
        const stateBit = ['open'].includes(obj.state as string) ? ' · open' : '';
        const slotBit = obj.slot ? ` · ${obj.slot} slot` : '';
        return {
            title: `${obj.name}${stateBit}${slotBit}`,
            body: obj.desc as string,
            foot: 'free look · no turn cost',
        };
    }

    // ── render ───────────────────────────────────────────────────────

    function attachHover(host: HTMLElement, getPos: (e: MouseEvent) => HTMLElement,
                         getContent: () => LookCard | null): () => void {
        const card = el('div', 'tsv-hovercard');
        card.style.display = 'none';
        document.body.appendChild(card);
        const show = (e: MouseEvent) => {
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

    function openMenu(x: number, y: number, title: string, buttons: MenuButton[],
                     onDraft?: (parts: DraftParts) => void,
                     onTalkFocus?: ((arg?: TalkFocus) => void) | null): void {
        closeMenu();
        const scrim = el('div', 'tsv-scrim');
        scrim.addEventListener('click', closeMenu);
        const box = el('div', 'tsv-ctx');
        box.appendChild(el('div', 'tsv-ctx-title', title));
        for (const b of buttons) {
            const btn = el('button') as HTMLButtonElement;
            if (b.danger) btn.classList.add('tsv-danger');
            if (b.talkFocus) btn.classList.add('tsv-back');
            btn.appendChild(document.createTextNode(b.label));
            if (b.reason) btn.appendChild(el('span', 'why', '— ' + b.reason));
            btn.disabled = b.enabled === false;
            btn.addEventListener('click', (e: MouseEvent) => {
                e.stopPropagation();
                closeMenu();
                if (b.enabled === false) return;
                // task-610: "talk" entries set the composer's speech volume
                // (and a directed-whisper target) instead of drafting a command.
                if (b.talk) { if (onTalkFocus) onTalkFocus({ volume: b.volume, target: b.target }); return; }
                // Nested menu (give/teach/intimacy): reopen at the same spot,
                // with a Back entry that rebuilds the parent list.
                if (b.sub) {
                    openMenu(x, y, b.sub.title,
                        ([{ label: '‹ back', sub: { title, buttons } }] as MenuButton[]).concat(b.sub.buttons),
                        onDraft, onTalkFocus);
                    return;
                }
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

    let _menuCleanup: (() => void) | null = null;
    function closeMenu(): void {
        if (_menuCleanup) { _menuCleanup(); _menuCleanup = null; }
    }

    /**
     * Fetch the raw scene payload (the composer also uses it for the
     * autocomplete datalist and meta line).
     */
    async function fetch(charName: string): Promise<Scene> {
        // NOTE: ApiClient is a top-level class (global binding, not a
        // window property) — reference it bare, like the rest of the app.
        return (ApiClient as unknown as { getScene(charName: string): Promise<Scene> }).getScene(charName);
    }

    /** Render a fetched scene payload into *host*. */
    function renderScene(host: HTMLElement, scene: Scene, handlers: SceneHandlers): void {
        ensureStyles();
        closeMenu();
        host.textContent = '';
        host.className = '';
        const dark = !!(scene.area && scene.area.dark);
        if (dark) host.classList.add('tsv-dark');

        const chipClick = (e: MouseEvent, title: string, buttons: MenuButton[]) =>
            openMenu(e.clientX, Math.min(e.clientY, window.innerHeight - 260),
                     title, buttons, handlers.onDraft, handlers.onTalkFocus);

        // area header chip + description
        const areaRow = el('div', 'tsv-zone');
        const areaBtn = el('button', 'tsv-chip tsv-area',
                           '📍 ' + (scene.area.display_name || scene.area.name));
        areaBtn.addEventListener('click', (e) => chipClick(e, scene.area.name as string, [
            { label: 'Examine the room', run: () => draftParts({ action: 'examine', item: 'room' }) },
            { label: 'Look around', run: () => draftParts({ action: 'look' }) },
            { label: 'Listen', run: () => draftParts({ action: 'listen' }) },
            // Focus the speech row without changing the volume — the "just let me
            // say something" affordance, kept distinct from the explicit volumes.
            { label: 'Speak…', talkFocus: true },
            { label: 'Say it to the room', talk: true, volume: 'say' },
            { label: 'Shout', talk: true, volume: 'shout' },
            { label: 'Scream', talk: true, volume: 'scream' },
        ]));
        attachHover(areaBtn, () => areaBtn,
                    () => lookLines(scene, 'area', Object.assign({}, scene.area, { dark })));
        areaRow.appendChild(areaBtn);
        host.appendChild(areaRow);

        const desc = el('p', 'tsv-desc',
                        dark ? 'shapes in the gloom — details are lost.' : (scene.area.desc || ''));
        if (desc.textContent) host.appendChild(desc);

        const zone = (label: string): HTMLElement => {
            const z = el('div', 'tsv-zone');
            z.appendChild(el('div', 'tsv-zlabel', label));
            const chips = el('div', 'tsv-chips');
            z.appendChild(chips);
            host.appendChild(z);
            return chips;
        };

        const mkChip = (parent: HTMLElement, cls: string, labelText: string,
                       onClick: (e: MouseEvent) => void,
                       hoverContent?: () => LookCard): HTMLElement => {
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
                (e) => chipClick(e, p.display_name, buildPersonMenu(p, scene)),
                () => lookLines(scene, 'person', p));
            const art = characterArt()?.artForNodeId(p.id);
            if (art && art.profile) {
                const img = document.createElement('img');
                img.className = 'tsv-avatar';
                img.src = art.profile;
                img.alt = '';
                img.addEventListener('click', (e) => {
                    e.stopPropagation();
                    characterArt()?.open({ name: p.display_name, nodeId: p.id });
                });
                chip.insertBefore(img, chip.firstChild);
            }
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
                chipClick(e, way.name, buildWayMenu(way, scene.you.conditions, scene.you.at_way_id)));
            attachHover(chip, () => chip, () => lookLines(scene, 'exit', way));
            wayChips.appendChild(chip);
        }

        host.appendChild(el('div', 'tsv-hint',
            'hover = free look · click = what you can do with it · picks fill the draft, nothing fires until Act'));
    }

    /** Convenience wrapper: fetch + renderScene, with inline error note. */
    async function render(charName: string, host: HTMLElement, handlers: SceneHandlers): Promise<void> {
        let scene: Scene;
        try {
            scene = await fetch(charName);
        } catch (err) {
            ensureStyles();
            host.textContent = '';
            host.className = '';
            host.appendChild(el('div', 'tsv-hint', `scene unavailable (${(err as Error).message})`));
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
    function menu(x: number, y: number, title: string, buttons: MenuButton[],
                 onDraft?: (parts: DraftParts) => void): void {
        openMenu(x, y, title, buttons, onDraft, null);
    }

    return { render, renderScene, fetch, menu, lookLines, attachHover, closeMenu };
})();

// ────────────────────────── local types ──────────────────────────
// Declared after the IIFE so the leading JSDoc block stays the first thing in
// the emitted .js and `@module` remains discoverable.

/** The three fields human-turn-composer reads out of a drafted command. */
interface DraftParts {
    action: string;
    item: string;
    target: string;
}

/**
 * One context-menu entry. The builders below push heterogeneous affordances
 * into one array — a draft command (`run`), a gated/no-op entry
 * (`enabled: false` + `reason`), a speech-volume entry (`talk` + `volume`),
 * a focus-only entry (`talkFocus`), and a nested submenu (`sub`) — so every
 * field is optional except the label.
 */
interface MenuButton {
    label: string;
    /** Produces the command to draft into the composer. */
    run?: () => DraftParts;
    /** `false` renders the row disabled and suppresses `run` on click. */
    enabled?: boolean;
    /** Shown right-aligned in the row; the reason it is disabled. */
    reason?: string;
    danger?: boolean;
    /** Focuses the speech row with this volume instead of drafting a command. */
    talk?: boolean;
    volume?: string;
    target?: string;
    /** Focuses the speech row without changing the volume. */
    talkFocus?: boolean;
    sub?: { title: string; buttons: MenuButton[] };
}

/** What `talk: true` entries hand to the composer's speech focus. */
interface TalkFocus {
    volume?: string;
    target?: string;
}

/** The free-look hover card: three text slots the renderer drops into divs. */
interface LookCard {
    title: string;
    body: string;
    foot: string;
}

/** Just the shape `requiresGate` reads off a way. */
interface WayLike {
    requires?: string;
    [key: string]: unknown;
}

/** One `available_actions` row from TriggerSystem._get_available_actions. */
interface AvailableAction {
    action: string;
    label?: string;
    enabled?: boolean;
    reason?: string;
}

interface SceneArea {
    display_name?: string;
    name?: string;
    desc?: string;
    dark?: boolean;
    [key: string]: unknown;
}

interface ScenePerson {
    id: string;
    display_name: string;
    /** Absent for a stranger the character has not learned the name of. */
    name?: string;
    desc: string;
    tags: string[];
    met?: boolean;
    [key: string]: unknown;
}

interface CarriedItem {
    name: string;
    [key: string]: unknown;
}

interface SceneWay {
    way_id: string;
    name: string;
    direction?: string;
    to?: string;
    state: string;
    desc?: string;
    requires?: string;
    see_through?: boolean;
    visible_in_direction?: string;
    needs_force_known?: boolean;
    known_locked?: boolean;
    auto_close?: boolean;
    [key: string]: unknown;
}

interface SceneItem {
    name: string;
    desc?: string;
    state?: string;
    slot?: string;
    available_actions?: AvailableAction[];
    [key: string]: unknown;
}

/** The "You" strip's slice of the scene: what the controlled character has. */
interface TurnSceneViewSceneYou {
    conditions: string[];
    at_way_id: string;
    carrying: CarriedItem[];
    known_abilities: string[];
    [key: string]: unknown;
}

/** The payload GET /api/scene returns for the current character. */
interface Scene {
    area: SceneArea;
    people: ScenePerson[];
    items: SceneItem[];
    ways: SceneWay[];
    you: TurnSceneViewSceneYou;
    /** Set instead of the scene when the fetch could not produce one. */
    error?: string;
    [key: string]: unknown;
}

/**
 * The union member `lookLines` actually switches over. It is deliberately one
 * permissive shape rather than a discriminated union: the `kind` string and the
 * payload arrive together from the render loop, and every field is optional
 * because each of the four branches reads a disjoint subset.
 */
interface LookTarget {
    display_name?: string;
    name?: string;
    desc?: string;
    dark?: boolean;
    direction?: string;
    to?: string;
    state?: string;
    requires?: string;
    see_through?: boolean;
    visible_in_direction?: string;
    needs_force_known?: boolean;
    known_locked?: boolean;
    auto_close?: boolean;
    tags?: string[];
    met?: boolean;
    slot?: string;
    [key: string]: unknown;
}

/** The callbacks `renderScene` uses to reach the composer. */
interface SceneHandlers {
    onDraft?: (parts: DraftParts) => void;
    onTalkFocus?: (arg?: TalkFocus) => void;
}

/** The subset of character-art.js this panel touches. */
interface TurnSceneViewArtApi {
    open(ref: { name: string; nodeId: string }): void;
    artForNodeId(nodeId: string): { profile?: string } | null;
}
