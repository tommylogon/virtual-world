/**
 * known-by.js — Character knowledge authoring (shared inspector component).
 *
 * A character's `known` list holds refs to runtime entities:
 *   - items / ways: graph node ids ("item_flask", "way_secret_passage")
 *   - areas: the area name, its node id, or an "area_<slug>" id-guess
 *   - characters: the name, "player_<slug>", or "character_<slug>"
 *
 * Game-facing effects (engine.room_perception + prompt builder): known hidden
 * ways/items become visible, known people are never masked as strangers, and
 * known areas reveal their hidden exits. Authoring UI: the Knowledge section
 * in the character inspector's Advanced tab — "Manage" opens a modal that
 * lists every runtime entity grouped by category (items / characters / areas /
 * ways) with per-category select-all, search, and stale-ref cleanup. The
 * per-entity "Known by" panel remains only on the character inspector.
 *
 * Load AFTER world-state, BEFORE inspector views.
 */

window.KnownBySection = (() => {
    'use strict';

    const slug = (s) => String(s || '').toLowerCase().replace(/\s+/g, '_');

    /** All refs the `known` list may use for a character. */
    function charRefs(name) {
        const n = String(name || '');
        const s = slug(n);
        return [...new Set([n, 'player_' + s, 'character_' + s])].filter(Boolean);
    }

    /** All refs the `known` list may use for an area (name / node id / slug). */
    function areaRefs(name, nodeId) {
        const n = String(name || '');
        const id = nodeId ? String(nodeId) : '';
        return [...new Set([n, id, 'area_' + slug(n)])].filter(Boolean);
    }

    /** The canonical ref a character's `known` list uses for THIS entity. */
    function refFor(kind, id, name) {
        if (kind === 'character') return 'player_' + slug(name || id);
        return String(id || '');
    }

    /**
     * Gather every runtime entity grouped by category.
     * Each entity: { key, refs: [..aliases], label, hidden }.
     */
    function collectEntities() {
        const out = { item: [], way: [], area: [], character: [] };
        const nodes = (worldState && worldState.graph && worldState.graph.nodes) || {};
        const areaNodeId = {};
        for (const [id, node] of Object.entries(nodes)) {
            if (!node || !node.type) continue;
            if (node.type === 'item') {
                out.item.push({
                    key: 'item::' + String(id),
                    refs: [String(id)],
                    label: node.name || String(id),
                    hidden: node.properties?.current_state === 'hidden'
                });
            } else if (node.type === 'way') {
                out.way.push({
                    key: 'way::' + String(id),
                    refs: [String(id)],
                    label: node.name || String(id),
                    hidden: node.properties?.current_state === 'hidden'
                });
            } else if (node.type === 'area') {
                const nm = String(node.name || id);
                areaNodeId[nm] = String(id);
                out.area.push({
                    key: 'area::' + nm,
                    refs: areaRefs(nm, String(id)),
                    label: nm,
                    hidden: false
                });
            } else if (node.type === 'character') {
                const nm = String(node.name || id);
                out.character.push({
                    key: 'character::' + nm,
                    refs: charRefs(nm),
                    label: nm,
                    hidden: false
                });
            }
        }
        // Areas / characters that live outside the graph (or graph-less states).
        for (const name of Object.keys((worldState && worldState.players) || {})) {
            out.character.push({
                key: 'character::' + name,
                refs: charRefs(name),
                label: name,
                hidden: false
            });
        }
        for (const name of Object.keys((worldState && worldState.areas) || {})) {
            out.area.push({
                key: 'area::' + name,
                refs: areaRefs(name, areaNodeId[name] || ''),
                label: name,
                hidden: false
            });
        }
        // Dedupe + sort by label.
        for (const cat of Object.keys(out)) {
            const seen = new Set();
            out[cat] = out[cat].filter(e => seen.has(e.key) ? false : (seen.add(e.key), true));
            out[cat].sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }));
        }
        return out;
    }

    /** Map every alias ref → its owning entity. */
    function buildMaps(entities) {
        const entityByRef = new Map();
        for (const cat of Object.keys(entities)) {
            for (const ent of entities[cat]) {
                for (const r of ent.refs) entityByRef.set(String(r), ent);
            }
        }
        return { entityByRef };
    }

    /**
     * "Knowledge" modal for ONE character: browse every runtime entity by
     * category, toggle what they know, search, select-all/none, clear stale
     * refs. Every change saves immediately through updateCharacter(known).
     */
    function openKnowledgeModal(charName) {
        if (!worldState || !worldState.players || !worldState.players[charName]) return;
        const entities = collectEntities();
        const { entityByRef } = buildMaps(entities);
        const state = {
            cat: 'item',
            search: '',
            known: new Set((worldState.players[charName].known || []).map(String))
        };
        const CATS = [
            { key: 'item', icon: '\u{1F4E6}', title: 'Items' },
            { key: 'character', icon: '\u{1F464}', title: 'Characters' },
            { key: 'area', icon: '\u{1F3E0}', title: 'Areas' },
            { key: 'way', icon: '\u{1F6AA}', title: 'Ways' }
        ];
        const catIcon = (key) => (CATS.find(c => c.key === key) || {}).icon || '•';

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        const box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:16px;width:480px;max-height:85vh;display:flex;flex-direction:column;gap:8px;';
        overlay.appendChild(box);
        document.body.appendChild(overlay);

        // Header
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
        const title = document.createElement('h3');
        title.style.cssText = 'margin:0;font-size:14px;';
        title.textContent = '\u{1F9E0} Knowledge — ' + charName;
        const close = document.createElement('button');
        close.className = 'btn btn-sm';
        close.textContent = '\u2715';
        close.title = 'Close';
        close.onclick = () => overlay.remove();
        header.appendChild(title);
        header.appendChild(close);
        box.appendChild(header);

        const hint = document.createElement('div');
        hint.style.cssText = 'font-size:10px;color:var(--text-muted);';
        hint.textContent = 'What this character knows from the start: hidden ways/items become visible, people are never masked, and known areas reveal their hidden exits. Saves immediately.';
        box.appendChild(hint);

        // Search
        const search = document.createElement('input');
        search.type = 'text';
        search.placeholder = 'Search this category...';
        search.style.cssText = 'width:100%;font-size:11px;padding:5px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:6px;';
        search.oninput = () => { state.search = search.value.toLowerCase(); renderList(); };
        box.appendChild(search);

        // Category tabs
        const tabs = document.createElement('div');
        tabs.style.cssText = 'display:flex;gap:4px;flex-wrap:wrap;';
        box.appendChild(tabs);

        // All / None + count
        const controlRow = document.createElement('div');
        controlRow.style.cssText = 'display:flex;justify-content:space-between;align-items:center;font-size:10px;color:var(--text-dim);';
        const allBtn = document.createElement('button');
        allBtn.className = 'btn btn-sm';
        allBtn.textContent = '✓ All';
        allBtn.style.cssText = 'font-size:10px;';
        const noneBtn = document.createElement('button');
        noneBtn.className = 'btn btn-sm';
        noneBtn.textContent = '✕ None';
        noneBtn.style.cssText = 'font-size:10px;';
        const controls = document.createElement('div');
        controls.style.cssText = 'display:flex;gap:4px;';
        controls.appendChild(allBtn);
        controls.appendChild(noneBtn);
        const countSpan = document.createElement('span');
        controlRow.appendChild(controls);
        controlRow.appendChild(countSpan);
        box.appendChild(controlRow);

        // Rows
        const rows = document.createElement('div');
        rows.style.cssText = 'max-height:40vh;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:4px;';
        box.appendChild(rows);

        // Footer
        const footer = document.createElement('div');
        footer.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
        const staleSpan = document.createElement('span');
        staleSpan.style.cssText = 'font-size:10px;color:#d29922;display:flex;align-items:center;gap:6px;';
        const doneBtn = document.createElement('button');
        doneBtn.className = 'btn btn-sm btn-blue';
        doneBtn.textContent = 'Done';
        doneBtn.onclick = () => overlay.remove();
        footer.appendChild(staleSpan);
        footer.appendChild(doneBtn);
        box.appendChild(footer);

        const entityKnown = (ent) => ent.refs.some(r => state.known.has(String(r)));

        const commit = () =>
            ApiClient.updateCharacter(charName, { known: [...state.known] })
                .then(() => worldState.fetch())
                .catch((err) => console.error('[knowledge-modal] save failed:', err));

        const setEntity = (ent, on) => {
            if (on) {
                for (const r of ent.refs) state.known.add(String(r));
            } else {
                for (const r of ent.refs) state.known.delete(String(r));
            }
            commit().then(updateCounts);
        };

        function renderTabs() {
            tabs.textContent = '';
            for (const c of CATS) {
                const list = entities[c.key];
                const knownCount = list.filter(entityKnown).length;
                const b = document.createElement('button');
                b.className = 'btn btn-sm' + (state.cat === c.key ? ' btn-blue' : '');
                b.style.cssText = 'font-size:10px;padding:2px 8px;';
                b.textContent = `${c.icon} ${c.title} (${list.length} \u00b7 ${knownCount})`;
                b.onclick = () => { state.cat = c.key; renderTabs(); renderList(); updateCounts(); };
                tabs.appendChild(b);
            }
        }

        function renderList() {
            rows.textContent = '';
            const list = entities[state.cat].filter(e => !state.search || e.label.toLowerCase().includes(state.search));
            if (!list.length) {
                const empty = document.createElement('div');
                empty.style.cssText = 'font-size:11px;color:var(--text-muted);padding:8px;';
                empty.textContent = state.search ? 'Nothing matches your search.' : `No ${state.cat}s in this world yet.`;
                rows.appendChild(empty);
                return;
            }
            for (const ent of list) {
                const row = document.createElement('label');
                row.style.cssText = 'display:flex;align-items:center;gap:6px;padding:3px 4px;cursor:pointer;font-size:12px;border-radius:4px;';
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.checked = entityKnown(ent);
                cb.onchange = () => setEntity(ent, cb.checked);
                const icon = document.createElement('span');
                icon.textContent = catIcon(state.cat);
                const span = document.createElement('span');
                span.textContent = ent.label;
                span.style.cssText = ent.hidden ? 'color:var(--text-dim);' : '';
                row.appendChild(cb);
                row.appendChild(icon);
                row.appendChild(span);
                if (ent.hidden) {
                    const sub = document.createElement('span');
                    sub.textContent = '(hidden)';
                    sub.style.cssText = 'color:var(--text-muted);font-size:10px;';
                    row.appendChild(sub);
                }
                rows.appendChild(row);
            }
        }

        function updateCounts() {
            renderTabs();
            const knownNow = [...state.known];
            const stale = knownNow.filter(r => !entityByRef.has(String(r)));
            staleSpan.textContent = '';
            if (stale.length) {
                staleSpan.textContent = `\u26a0 ${stale.length} ref${stale.length === 1 ? '' : 's'} not found `;
                const clearStale = document.createElement('button');
                clearStale.className = 'btn btn-sm';
                clearStale.style.cssText = 'font-size:10px;';
                clearStale.textContent = '✕ Clear';
                clearStale.title = 'Remove refs that no longer point at anything';
                clearStale.onclick = () => {
                    for (const r of stale) state.known.delete(String(r));
                    commit().then(updateCounts);
                };
                staleSpan.appendChild(clearStale);
            }
            const catList = entities[state.cat];
            countSpan.textContent = `${catList.length} ${state.cat}s in world \u00b7 ${catList.filter(entityKnown).length} known`;
        }

        allBtn.onclick = async () => {
            for (const ent of entities[state.cat]) {
                for (const r of ent.refs) state.known.add(String(r));
            }
            await commit();
            updateCounts();
            renderList();
        };
        noneBtn.onclick = async () => {
            for (const ent of entities[state.cat]) {
                for (const r of ent.refs) state.known.delete(String(r));
            }
            await commit();
            updateCounts();
            renderList();
        };

        renderTabs();
        renderList();
        updateCounts();
        setTimeout(() => search.focus(), 50);
    }

    /**
     * Chips of everything THIS character knows (with ✕ to remove), grouped
     * and de-duplicated by real entity labels. Used in the Advanced tab.
     */
    function buildKnownChips(charName) {
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;';
        const list = ((worldState.players?.[charName]?.known) || []).map(String);
        if (!list.length) {
            const none = document.createElement('span');
            none.style.cssText = 'font-size:10px;color:var(--text-muted);';
            none.textContent = 'nothing authored yet — runtime discovery still works.';
            wrap.appendChild(none);
            return wrap;
        }
        const entities = collectEntities();
        const { entityByRef } = buildMaps(entities);
        const seen = new Set();
        for (const ref of list) {
            const ent = entityByRef.get(ref);
            const key = ent ? ent.key : 'stale::' + ref;
            if (seen.has(key)) continue;
            seen.add(key);
            const chip = document.createElement('span');
            chip.style.cssText = 'font-size:10px;color:var(--text-dim);background:var(--bg-input);border:1px solid var(--border);border-radius:999px;padding:1px 8px;';
            chip.textContent = ent ? (ent.hidden ? '\u{1F512} ' + ent.label : ent.label) : ref;
            chip.title = ent ? 'Known from the start' : 'stale ref — no longer points at anything';
            const x = document.createElement('button');
            x.textContent = '\u2715';
            x.style.cssText = 'margin-left:5px;border:none;background:none;color:var(--text-dim);cursor:pointer;font-size:10px;';
            x.title = 'Stop knowing this';
            x.onclick = () => {
                const remove = new Set((ent ? ent.refs : [ref]).map(String));
                const next = list.filter(r => !remove.has(String(r)));
                ApiClient.updateCharacter(charName, { known: next })
                    .then(() => worldState.fetch())
                    .catch(() => {});
            };
            chip.appendChild(x);
            wrap.appendChild(chip);
        }
        return wrap;
    }

    /**
     * "Known by" checkbox list — who knows THIS character. Returns a DOM
     * element. Only used on the character inspector now.
     */
    function build(kind, id, label) {
        const wrap = document.createElement('div');
        wrap.className = 'inspector-section';
        // Marker so consumers can purge stale copies before appending a fresh
        // one — the inspector re-renders on every worldState.fetch() poll and
        // manually-appended children survive Lit re-renders.
        wrap.dataset.knownBy = '1';
        const h = document.createElement('h3');
        h.textContent = '\u{1F9E0} Known by';
        wrap.appendChild(h);
        const hint = document.createElement('div');
        hint.style.cssText = 'font-size:10px;color:var(--text-muted);margin-bottom:6px;';
        hint.textContent = 'Who already knows this character from the start. Manage what THEY know in the Advanced tab \u2192 Knowledge.';
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

    return { openKnowledgeModal, buildKnownChips, build, collectEntities, refFor, slug };
})();
