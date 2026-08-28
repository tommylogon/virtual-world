/**
 * emote-picker.js — reusable, searchable, categorized emote quick-pick.
 *
 * A standalone window.EmotePicker that renders a search box + chip grid into
 * any container and calls a callback when an emote is picked. Shared by the
 * human turn composer (and available to lift into a standalone panel later —
 * anytime-emote / emote browser).
 *
 * Emotes are bare verb phrases, never including a character name (see
 * schema-fragments.js EMOTE_RULES), so anything picked here is engine-valid.
 *
 * API:
 *   EmotePicker.open(container, { onPick(emote) })
 *   EmotePicker.close(container)
 *   EmotePicker.toggle(container, opts)
 *   EmotePicker.setCatalog(catalog)   // optional override, e.g. from library
 *
 * Uses window.Lit at call time only (deferred module bootstrap); load after
 * the lit-html shim, before any consumer that mounts it.
 */
window.EmotePicker = (() => {
    'use strict';

    const STYLE_ID = 'emote-picker-styles';

    let _catalog = [
        { cat: 'neutral',  items: ['glances around the room', 'shifts their weight', 'watches you carefully', 'stares into the distance'] },
        { cat: 'movement', items: ['sneaks closer', 'steps back', 'moves toward the door', 'leans in close', 'paces anxiously', 'stops short'] },
        { cat: 'social',   items: ['nods slowly', 'shakes their head', 'offers a small smile', 'gives a warm handshake', 'crosses their arms', 'raises an eyebrow'] },
        { cat: 'comfort',  items: ['rests a hand on their shoulder', 'gives a reassuring pat', 'offers a gentle hug', 'runs a hand through their hair', 'lets out a soft sigh'] },
        { cat: 'unease',   items: ['fidgets with their hands', 'bites their lip', 'glances over their shoulder', 'wrings their hands', 'takes a shaky breath', 'rubs the back of their neck'] },
        { cat: 'hostile',  items: ['bares their teeth', 'clenches their fists', 'drops into a defensive stance', 'draws themselves up tall', 'eyes the newcomer warily'] },
        { cat: 'polite',   items: ['inclines their head politely', 'touches their brow in a small bow', 'offers their hand', 'holds the door open for you'] },
        { cat: 'focus',    items: ['leans forward for a closer look', 'squints at the object', 'runs a finger along the surface', 'steps aside to let you see'] },
        { cat: 'warmth',   items: ['brushes a stray lock behind their ear', 'offers a playful grin', 'tilts their head with a soft laugh', 'lets their gaze linger'] },
        { cat: 'hands',    items: ['holds out the item', 'places the object in your hand', 'sets the key on the table', 'nods toward the door'] },
    ];

    function ensureStyles() {
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = [
            '.ep-q { width:100%; background:#141820; border:1px solid #2a303b; color:#e6e8ee; border-radius:7px; padding:6px 9px; font-size:12px; outline:none; color-scheme:dark; box-sizing:border-box; }',
            '.ep-q:focus { border-color:#4f9cf9; }',
            '.ep-list { max-height:240px; overflow-y:auto; margin-top:6px; }',
            '.ep-group { margin-bottom:7px; }',
            '.ep-cat { font-size:10px; text-transform:uppercase; letter-spacing:1px; color:#6b7686; margin-bottom:4px; }',
            '.ep-grid { display:flex; flex-wrap:wrap; gap:5px; }',
            '.ep-chip { background:#1d212a; border:1px solid #2a303b; color:#c6cdd6; border-radius:999px; padding:4px 10px; font-size:11.5px; cursor:pointer; }',
            '.ep-chip:hover { border-color:#4f9cf9; color:#fff; background:#232833; }',
            '.ep-none { font-size:11px; color:#6b7686; padding:6px 2px; }',
        ].join(String.fromCharCode(10));
        document.head.appendChild(style);
    }

    const html = (s, ...v) => window.Lit.html(s, ...v);

    function renderList(list, filter) {
        if (!list) return;
        const f = (filter || '').trim().toLowerCase();
        const groups = _catalog.map(g => {
            const items = f ? g.items.filter(i => i.toLowerCase().includes(f)) : g.items;
            if (!items.length) return null;
            return html`<div class="ep-group"><div class="ep-cat">${g.cat}</div><div class="ep-grid">${items.map(it => html`<button type="button" class="ep-chip" data-emote=${it}>${it}</button>`)}</div></div>`;
        }).filter(Boolean);
        window.Lit.render(html`${groups.length ? groups : html`<div class="ep-none">no emotes match</div>`}`, list);
    }

    function open(container, opts = {}) {
        if (!container) return;
        ensureStyles();
        const onPick = opts.onPick;
        window.Lit.render(html`
            <input class="ep-q" type="text" placeholder="search emotes…" autocomplete="off">
            <div class="ep-list"></div>` , container);
        const q = container.querySelector('.ep-q');
        const list = container.querySelector('.ep-list');
        renderList(list, '');
        q.oninput = () => renderList(list, q.value);
        q.onkeydown = (e) => { if (e.key === 'Escape') { e.preventDefault(); close(container); } };
        container.onclick = (e) => {
            const chip = e.target.closest('.ep-chip');
            if (chip) {
                const emote = chip.dataset.emote;
                if (onPick) onPick(emote);
                close(container);
            }
        };
        container._emoteOnPick = onPick;
        container.classList.add('open');
        q.focus();
    }

    function close(container) {
        if (!container) return;
        container.classList.remove('open');
        container.onclick = null;
        container._emoteOnPick = null;
    }

    function toggle(container, opts) {
        if (container && container.classList.contains('open')) close(container);
        else open(container, opts);
    }

    function setCatalog(catalog) {
        if (Array.isArray(catalog) && catalog.length) _catalog = catalog;
    }

    return { open, close, toggle, setCatalog, renderList, get catalog() { return _catalog; } };
})();
