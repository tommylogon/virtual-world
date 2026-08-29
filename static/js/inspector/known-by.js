/**
 * known-by.js — "Known by" authoring control (shared inspector component).
 *
 * Any node (way / item / area / character) can be flagged as KNOWN to any
 * character. The character's `known` list holds entity refs:
 *   - ways/items/areas: graph node ids ("way_secret_passage", ...)
 *   - characters: "player_<slug>" (or the raw name)
 * Game-facing effects (engine.room_perception + prompt builder): known hidden
 * ways visible, known hidden items visible, known people unmasked, known
 * areas' connected ways treated as discovered. Authors toggle checkboxes here;
 * saves through the player update route.
 * Load AFTER world-state, BEFORE inspector views.
 */

window.KnownBySection = (() => {
    'use strict';

    const slug = (s) => String(s || '').toLowerCase().replace(/\s+/g, '_');

    /** The ref a character's `known` list uses for THIS entity. */
    function refFor(kind, id, name) {
        if (kind === 'character') return 'player_' + slug(name || id);
        return String(id || '');
    }

    /**
     * "Known by" checkbox list. Returns a DOM element.
     * @param {string} kind - 'way' | 'item' | 'area' | 'character'
     * @param {string} id - graph node id (or the character's node id for kind char)
     * @param {string} label - entity display name (used for character refs)
     */
    function build(kind, id, label) {
        const wrap = document.createElement('div');
        wrap.className = 'inspector-section';
        const h = document.createElement('h3');
        h.textContent = '🧠 Known by';
        wrap.appendChild(h);
        const hint = document.createElement('div');
        hint.style.cssText = 'font-size:10px;color:var(--text-muted);margin-bottom:6px;';
        hint.textContent = 'Who already knows this from the start. Everything hidden stays hidden from everyone else until they discover or learn it.';
        wrap.appendChild(hint);

        const players = worldState.players || {};
        const names = Object.keys(players).sort();
        const box = document.createElement('div');
        box.style.cssText = 'display:flex;flex-direction:column;gap:3px;max-height:170px;overflow-y:auto;font-size:12px;';
        if (!names.length) {
            box.textContent = 'no characters yet.';
            wrap.appendChild(box);
            return wrap;
        }
        const ref = refFor(kind, id, label);
        for (const name of names) {
            const row = document.createElement('label');
            row.style.cssText = 'display:flex;align-items:center;gap:6px;cursor:pointer;';
            const input = document.createElement('input');
            input.type = 'checkbox';
            const knownList = new Set((worldState.players[name]?.known || []).map(String));
            input.checked = knownList.has(ref);
            const span = document.createElement('span');
            span.textContent = name;
            input.addEventListener('change', () => {
                const cur = new Set((worldState.players[name]?.known || []).map(String));
                if (input.checked) cur.add(ref); else cur.delete(ref);
                ApiClient.updateCharacter(name, { known: [...cur] })
                    .then(() => worldState.fetch())
                    .catch(() => { input.checked = !input.checked; });
            });
            row.appendChild(input);
            row.appendChild(span);
            box.appendChild(row);
        }
        wrap.appendChild(box);
        return wrap;
    }

    /** Read-only chips: everything THIS character knows (their own list). */
    function buildOwnKnown(charName) {
        const wrap = document.createElement('div');
        wrap.className = 'inspector-section';
        const h = document.createElement('h3');
        h.textContent = '🧠 Knows about';
        wrap.appendChild(h);
        const list = worldState.players?.[charName]?.known || [];
        const chipsBox = document.createElement('div');
        chipsBox.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;';
        if (!list.length) {
            chipsBox.textContent = 'nothing authored yet — runtime discovery still works.';
        } else {
            for (const ref of list.map(String)) {
                const chip = document.createElement('span');
                chip.textContent = ref;
                chip.title = 'ref — click ✕ to remove';
                chip.style.cssText = 'font-size:10px;color:var(--text-dim);background:var(--bg-input);border:1px solid var(--border);border-radius:999px;padding:1px 8px;';
                const x = document.createElement('button');
                x.textContent = '✕';
                x.style.cssText = 'margin-left:5px;border:none;background:none;color:var(--text-dim);cursor:pointer;font-size:10px;';
                x.title = 'Stop knowing this';
                x.addEventListener('click', () => {
                    const next = list.map(String).filter(r => r !== ref);
                    ApiClient.updateCharacter(charName, { known: next }).then(() => worldState.fetch());
                });
                chip.appendChild(x);
                chipsBox.appendChild(chip);
            }
        }
        wrap.appendChild(chipsBox);
        return wrap;
    }

    return { build, buildOwnKnown, refFor, slug };
})();
