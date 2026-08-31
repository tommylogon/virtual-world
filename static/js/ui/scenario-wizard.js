/**
 * scenario-wizard.js — "Scenario from Text" world-creation wizard.
 *
 * One premise sentence → LLM drafts a whole world in the TEMPLATE format
 * (engine/serialization_template.py): areas + environment + mirrored exits
 * + items (with tags/triggers/contents) + protagonist + supporting cast +
 * lore. The draft is reviewed card-by-card (accept / regenerate per room,
 * prune items), then applied through the existing POST /api/load path —
 * which snapshots the current world onto the undo stack and saves the draft
 * as a scenario, so ↩ Undo restores everything.
 *
 * Load AFTER shared/ai-generator.js and api.js; before the UI is used.
 */

window.ScenarioWizard = (() => {
    'use strict';

    const OPPOSITE = { north: 'south', south: 'north', east: 'west', west: 'east', up: 'down', down: 'up', in: 'out', out: 'in', left: 'right', right: 'left', inside: 'outside', outside: 'inside' };

    const SYSTEM_PROMPT = `You are a world architect for a text-based AI-agent RPG engine. Convert a scenario premise into ONE complete world draft. Respond with ONLY raw JSON — no markdown, no code fences, no commentary.

Schema (exact shape):
{
  "name": "<scenario title>",
  "player": {"name": "<protagonist>", "personality": "...", "description": "..."},
  "characters": [{"name":"...","description":"...","personality":"...","tags":["..."],"area":"<room name>"}],
  "world_lore": [{"category":"places|people|rules|history|current_events","title":"...","content":"..."}],
  "current_area": "<room name>",
  "areas": {
    "<Room Name>": {
      "description": "<vivid 2-3 sentences, second person not required>",
      "environment": {"light": 80, "temperature": 21, "air": "fresh", "smell": "neutral", "noise": "quiet"},
      "exits": {"<direction>": {"target": "<Room Name>", "state": "open", "hidden": false, "description": "<door text>"}},
      "items": [{"name":"...","description":"...","actions":"examine,take,use","current_state":"normal","hidden":false,"tags":["..."],"weight":0.5,"uses":-1}]
    }
  }
}

RULES:
- 3 to 12 rooms, 0 to 6 items per room, 1 to 5 characters, 3 to 8 lore entries.
- Every exit MUST be mirrored: if room A lists "north" -> B, room B must list "south" -> A (north<->south, east<->west, up<->down, in<->out, left<->right). No one-way exits. Non-cardinal doors get the same short label as the direction key on BOTH rooms.
- Exit "target" values must exactly match an area name. No dangling exits.
- Room names unique (case-insensitive), concrete and evocative.
- environment: light = integer 0-100 (80 = normal daylight), temperature = integer -50..50, air/smell/noise = short phrases.
- items "actions" = comma list from: examine,take,use,open,close,eat,drink,read,light,activate,equip,unequip,throw,break.
- items "current_state" = one of normal,hidden,lit,unlit,open,closed,locked,broken; hidden=true only for secrets.
- items "tags" carry mechanics when thematic: light_source, heat_source, container, food, drink, weapon, clothing, armor, magic, key...
- The protagonist goes in "player" (never in characters). Supporting cast go in "characters", each with a starting "area" that exists in areas.
- world_lore: short, writerly entries that ground the premise.
- Keep every string evocative but compact.`;

    let _overlay = null;
    let _state = null;

    // ────────────────────────── helpers ──────────────────────────

    const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

    function slugKey(s) { return String(s || '').toLowerCase().replace(/\s+/g, ' ').trim(); }

    function opposite(dir) {
        const d = String(dir || '').toLowerCase();
        return OPPOSITE[d] || d;
    }

    /** Fix the draft into a valid template: dedupe names, mirror exits, drop dangling. */
    function normalizeDraft(d) {
        const draft = JSON.parse(JSON.stringify(d || {}));
        draft.name = String(draft.name || 'Generated Scenario').slice(0, 60);
        draft.player = draft.player && typeof draft.player === 'object' ? draft.player : { name: 'Traveler', description: '' };
        draft.world_lore = Array.isArray(draft.world_lore) ? draft.world_lore.slice(0, 8) : [];
        draft.characters = Array.isArray(draft.characters) ? draft.characters.slice(0, 6) : [];
        const areas = {};
        for (const [name, area] of Object.entries(draft.areas || {})) {
            const clean = String(name || '').trim() || `Room ${Object.keys(areas).length + 1}`;
            let unique = clean;
            let n = 2;
            while (slugKey(unique) in areas) unique = `${clean} (${n++})`;
            areas[unique] = area && typeof area === 'object' ? area : {};
        }
        draft.areas = areas;

        // Mirror + validate exits.
        const areaKeys = new Set(Object.keys(areas).map(slugKey));
        for (const [name, area] of Object.entries(areas)) {
            const exits = {};
            for (const [dir, data] of Object.entries(area.exits || {})) {
                const exitData = (data && typeof data === 'object') ? data : { target: data };
                const target = String(exitData.target || '').trim();
                if (!target || !areaKeys.has(slugKey(target))) continue; // dangling
                const canonicalDir = String(dir || '').toLowerCase().trim() || 'way';
                exits[canonicalDir] = { ...exitData, target };
            }
            area.exits = exits;
        }
        for (const [name, area] of Object.entries(areas)) {
            const seen = new Set();
            for (const [dir, data] of Object.entries(area.exits || {})) {
                const key = `${slugKey(data.target)}|${dir}`;
                if (seen.has(key)) continue;
                seen.add(key);
                const targetArea = areas[data.target];
                const backDir = opposite(dir);
                const backKey = `${slugKey(name)}|${backDir}`;
                const exists = Object.values(targetArea.exits || {}).some(d => d && d.target && slugKey(d.target) === slugKey(name));
                if (!exists) {
                    targetArea.exits = targetArea.exits || {};
                    if (!Object.keys(targetArea.exits).includes(backDir)) {
                        targetArea.exits[backDir] = { target: name, state: data.state || 'open', hidden: !!data.hidden, description: data.description || '' };
                    }
                }
            }
        }
        return draft;
    }

    // ────────────────────────── UI builders ──────────────────────────

    function baseBox() {
        // Close any previous wizard overlay before stacking a new one — the
        // wizard can be re-opened/re-rendered (review ↔ input) mid-session.
        if (_overlay && _overlay.parentNode) {
            _overlay.parentNode.removeChild(_overlay);
        }
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        const box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px;width:620px;max-height:88vh;display:flex;flex-direction:column;gap:10px;';
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        return { overlay, box };
    }

    function renderInput() {
        const { overlay, box } = baseBox();
        _overlay = overlay;

        const header = document.createElement('div');
        header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
        const title = document.createElement('h3');
        title.style.cssText = 'margin:0;font-size:15px;';
        title.textContent = '✨ Scenario from Text';
        const close = document.createElement('button');
        close.className = 'btn btn-sm';
        close.textContent = '\u2715';
        close.onclick = () => closeOverlay();
        header.appendChild(title);
        header.appendChild(close);
        box.appendChild(header);

        const hint = document.createElement('div');
        hint.style.cssText = 'font-size:11px;color:var(--text-muted);';
        hint.textContent = 'Describe a world in one or two sentences. The AI drafts rooms, doors, items, characters, and lore — you review every card before anything touches the graph. Applying REPLACES the current world; ↩ Undo restores it.';
        box.appendChild(hint);

        const textarea = document.createElement('textarea');
        textarea.rows = 5;
        textarea.placeholder = 'e.g. A mountain hunting lodge cut off by a blizzard. Eight guests, one dead, an old grudge in the walls. The survivor has to find out who killed the guide before the lights go out.';
        textarea.style.cssText = 'width:100%;font-size:12px;padding:8px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:8px;resize:vertical;';
        box.appendChild(textarea);

        const nameRow = document.createElement('div');
        nameRow.style.cssText = 'display:flex;gap:8px;align-items:center;font-size:11px;color:var(--text-dim);';
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.placeholder = 'Scenario name (optional — defaults to the draft title)';
        nameInput.style.cssText = 'flex:1;font-size:11px;padding:5px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:6px;';
        nameRow.appendChild(nameInput);
        box.appendChild(nameRow);

        const actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;';
        const cancel = document.createElement('button');
        cancel.className = 'btn btn-sm';
        cancel.textContent = 'Cancel';
        cancel.onclick = () => closeOverlay();
        const gen = document.createElement('button');
        gen.className = 'btn btn-sm btn-blue';
        gen.textContent = '🪄 Draft World';
        gen.onclick = () => {
            const premise = textarea.value.trim();
            if (!premise) { gen.textContent = 'Type a premise first'; setTimeout(() => { gen.textContent = '🪄 Draft World'; }, 1200); return; }
            if (typeof AIGenerator === 'undefined' || !AIGenerator.isConfigured()) return;
            gen.disabled = true;
            gen.textContent = 'Architecting…';
            AIGenerator.generate(`Scenario premise:\n\n${premise}\n\nBuild the world draft JSON now.`, SYSTEM_PROMPT, { temperature: 0.8 })
                .then(result => {
                    if (result.success && result.data) {
                        _state = { draft: normalizeDraft(result.data), name: nameInput.value.trim() || result.data.name || 'Generated Scenario', premise, include: { rooms: {}, items: {}, chars: {}, lore: {} } };
                        try {
                            renderReview();
                        } catch (e) {
                            console.error('[scenario-wizard] review render failed:', e);
                            toastError('Draft parsed, but review failed: ' + (e.message || e));
                            renderInput();
                        }
                    } else {
                        toastError('Draft failed: ' + (result.error || 'unknown error'));
                        gen.disabled = false;
                        gen.textContent = '🪄 Draft World';
                    }
                })
                .catch(err => {
                    toastError('Draft failed: ' + (err.message || err));
                    gen.disabled = false;
                    gen.textContent = '🪄 Draft World';
                });
        };
        actions.appendChild(cancel);
        actions.appendChild(gen);
        box.appendChild(actions);

        setTimeout(() => textarea.focus(), 50);
    }

    function renderReview() {
        const { overlay, box } = baseBox();
        _overlay = overlay;
        box.style.width = '720px';

        const header = document.createElement('div');
        header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;gap:8px;';
        const title = document.createElement('h3');
        title.style.cssText = 'margin:0;font-size:15px;white-space:nowrap;';
        title.textContent = '📋 Review World Draft';
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.value = _state.name;
        nameInput.style.cssText = 'flex:1;font-size:12px;padding:5px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:6px;text-align:right;';
        nameInput.title = 'Scenario name';
        nameInput.onchange = () => { _state.name = nameInput.value.trim() || _state.name; };
        const close = document.createElement('button');
        close.className = 'btn btn-sm';
        close.textContent = '\u2715';
        close.onclick = () => closeOverlay();
        header.appendChild(title);
        header.appendChild(nameInput);
        header.appendChild(close);
        box.appendChild(header);

        const d = _state.draft;
        const roomNames = Object.keys(d.areas);
        const itemCount = roomNames.reduce((n, r) => n + (d.areas[r].items || []).length, 0);
        const stats = document.createElement('div');
        stats.style.cssText = 'font-size:10px;color:var(--text-muted);';
        stats.textContent = `🏠 ${roomNames.length} rooms · 📦 ${itemCount} items · 🧍 ${(d.characters || []).length} characters · 📖 ${(d.world_lore || []).length} lore entries — ticking a card off skips it.`;
        box.appendChild(stats);

        const list = document.createElement('div');
        list.style.cssText = 'overflow-y:auto;max-height:52vh;display:flex;flex-direction:column;gap:8px;';
        box.appendChild(list);

        // Characters
        if ((d.characters || []).length) {
            list.appendChild(renderGroup('🧍 Characters', (d.characters || []).map((c, i) => {
                const el = document.createElement('div');
                el.style.cssText = 'display:flex;gap:6px;align-items:flex-start;padding:4px 0;';
                const cb = docCheckbox(_state.include.chars, i, true, () => renderReview());
                el.appendChild(cb);
                const body = document.createElement('div');
                body.style.cssText = 'flex:1;font-size:11px;';
                body.innerHTML = `<strong>${esc(c.name || '?')}</strong> <span style="color:var(--text-dim);">— starts in ${esc(c.area || '?')}</span><br><span style="color:var(--text-dim);">${esc((c.description || '').slice(0, 160))}</span>`;
                el.appendChild(body);
                return el;
            })));
        }

        // Lore
        if ((d.world_lore || []).length) {
            list.appendChild(renderGroup('📖 World Lore', (d.world_lore || []).map((l, i) => {
                const el = document.createElement('div');
                el.style.cssText = 'display:flex;gap:6px;align-items:flex-start;padding:4px 0;';
                const cb = docCheckbox(_state.include.lore, i, true, () => renderReview());
                el.appendChild(cb);
                const body = document.createElement('div');
                body.style.cssText = 'flex:1;font-size:11px;';
                body.innerHTML = `<strong>${esc(l.title || 'untitled')}</strong> <span style="color:var(--text-dim);">[${esc(l.category || '')}]</span><br><span style="color:var(--text-dim);">${esc((l.content || '').slice(0, 180))}</span>`;
                el.appendChild(body);
                return el;
            })));
        }

        // Rooms
        roomNames.forEach((roomName, idx) => {
            const area = d.areas[roomName];
            const card = document.createElement('div');
            card.style.cssText = 'border:1px solid var(--border);border-radius:8px;padding:8px;background:rgba(255,255,255,0.02);';
            const head = document.createElement('div');
            head.style.cssText = 'display:flex;gap:6px;align-items:center;';
            head.appendChild(docCheckbox(_state.include.rooms, idx, true, () => renderReview()));
            const nameBox = document.createElement('input');
            nameBox.type = 'text';
            nameBox.value = roomName;
            nameBox.style.cssText = 'flex:1;font-size:12px;background:transparent;border:1px solid var(--border);border-radius:4px;color:inherit;padding:2px 6px;';
            nameBox.onchange = () => renameRoom(idx, nameBox.value);
            head.appendChild(nameBox);
            const regen = document.createElement('button');
            regen.className = 'btn btn-sm';
            regen.textContent = '✨ Regen';
            regen.style.cssText = 'font-size:10px;';
            regen.onclick = () => regenerateRoom(idx, card);
            head.appendChild(regen);
            card.appendChild(head);

            const env = area.environment || {};
            const badge = document.createElement('div');
            badge.style.cssText = 'font-size:10px;color:var(--text-dim);margin:4px 0;';
            badge.textContent = `🌡 ${env.temperature ?? 21}°C · 💡 ${env.light ?? 80} · ${env.air ?? 'fresh'} · ${env.smell ?? 'neutral'} · ${env.noise ?? 'quiet'}`;
            card.appendChild(badge);

            const desc = document.createElement('div');
            desc.style.cssText = 'font-size:11px;color:var(--text-dim);white-space:pre-wrap;max-height:70px;overflow-y:auto;';
            desc.textContent = area.description || '';
            card.appendChild(desc);

            const exits = Object.entries(area.exits || {});
            if (exits.length) {
                const x = document.createElement('div');
                x.style.cssText = 'font-size:10px;margin:4px 0;';
                x.innerHTML = exits.map(([dir, data]) => `<span style="margin-right:6px;">🚪 ${esc(dir)} → <strong>${esc(data && data.target)}</strong></span>`).join('');
                card.appendChild(x);
            }

            const items = area.items || [];
            if (items.length) {
                const block = document.createElement('div');
                block.style.cssText = 'margin-top:4px;';
                items.forEach((it, i) => {
                    const row = document.createElement('label');
                    row.style.cssText = 'display:flex;gap:6px;align-items:center;font-size:11px;padding:2px 0;cursor:pointer;';
                    const cb = document.createElement('input');
                    cb.type = 'checkbox';
                    const key = `${idx}::${i}`;
                    cb.checked = _state.include.items[key] !== false;
                    cb.onchange = () => { _state.include.items[key] = cb.checked; };
                    const span = document.createElement('span');
                    span.textContent = `📦 ${it.name || 'item'}${it.tags && it.tags.length ? ` [${it.tags.join(', ')}]` : ''}`;
                    row.appendChild(cb);
                    row.appendChild(span);
                    block.appendChild(row);
                });
                card.appendChild(block);
            }
            list.appendChild(card);
        });

        // Footer
        const footer = document.createElement('div');
        footer.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
        const left = document.createElement('button');
        left.className = 'btn btn-sm';
        left.textContent = '↩ Back';
        left.onclick = () => renderInput();
        const right = document.createElement('div');
        right.style.cssText = 'display:flex;gap:8px;';
        const cancel = document.createElement('button');
        cancel.className = 'btn btn-sm';
        cancel.textContent = 'Cancel';
        cancel.onclick = () => closeOverlay();
        const apply = document.createElement('button');
        apply.className = 'btn btn-sm btn-green';
        apply.textContent = '🚀 Apply World';
        apply.onclick = () => applyDraft(apply);
        right.appendChild(cancel);
        right.appendChild(apply);
        footer.appendChild(left);
        footer.appendChild(right);
        box.appendChild(footer);
    }

    function docCheckbox(container, key, defaultValue, onChange) {
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = container[key] !== false;
        cb.onchange = () => { container[key] = cb.checked; if (onChange) onChange(); };
        return cb;
    }

    function renderGroup(label, items) {
        const wrap = document.createElement('div');
        const h = document.createElement('div');
        h.style.cssText = 'font-size:11px;font-weight:600;color:var(--text-dim);margin:4px 0 2px;';
        h.textContent = label;
        wrap.appendChild(h);
        items.forEach(i => wrap.appendChild(i));
        return wrap;
    }

    function renameRoom(idx, newName) {
        const d = _state.draft;
        const names = Object.keys(d.areas);
        const oldName = names[idx];
        const clean = String(newName || oldName).trim() || oldName;
        if (clean === oldName) return;
        // Update the key and every exit target that referenced the old name.
        d.areas = Object.fromEntries(Object.entries(d.areas).map(([k, v]) => [k === oldName ? clean : k, v]));
        for (const area of Object.values(d.areas)) {
            for (const exit of Object.values(area.exits || {})) {
                if (exit && exit.target && slugKey(exit.target) === slugKey(oldName)) exit.target = clean;
            }
        }
        renderReview();
    }

    function regenerateRoom(idx, card) {
        const names = Object.keys(_state.draft.areas);
        const name = names[idx];
        const area = _state.draft.areas[name];
        const neighbors = Object.values(area.exits || {}).map(e => e.target).join(', ');
        const prompt = `Regenerate ONLY the room "${name}" (keep its identity and position, improve content).\nPremise: ${_state.premise || _state.name}\nNeighbors: ${neighbors || 'none'}\nCurrent description: ${area.description || 'none'}\nReturn ONLY the room JSON in this exact shape: {\"name\":\"...\",\"description\":\"...\",\"environment\":{\"light\":80,\"temperature\":21,\"air\":\"fresh\",\"smell\":\"neutral\",\"noise\":\"quiet\"},\"exits\":{\"<direction>\":{\"target\":\"<room>\",\"state\":\"open\",\"hidden\":false,\"description\":\"...\"}},\"items\":[...]}\nKeep verbatim: the room name and any exit target names that already exist.`;
        card.querySelectorAll('button').forEach(b => b.disabled = true);
        AIGenerator.generate(prompt, 'You refine one room of a world draft. Respond with ONLY raw JSON.', { temperature: 0.75 })
            .then(result => {
                if (!result.success || !result.data) throw new Error(result.error || 'no data');
                const room = result.data;
                if (!room || !room.name) throw new Error('missing name');
                const d = _state.draft;
                const key = room.name;
                d.areas[key] = { description: room.description || '', environment: room.environment || {}, exits: room.exits || {}, items: Array.isArray(room.items) ? room.items : [] };
                if (key !== name) {
                    for (const a of Object.values(d.areas)) {
                        for (const e of Object.values(a.exits || {})) {
                            if (e && e.target && slugKey(e.target) === slugKey(name)) e.target = key;
                        }
                    }
                }
                _state.draft = normalizeDraft(d);
                renderReview();
            })
            .catch(err => {
                toastError('Room regen failed: ' + (err.message || err));
                renderReview();
            });
    }

    function applyDraft(btn) {
        const d = _state.draft;
        const names = Object.keys(d.areas).filter((_, i) => _state.include.rooms[i] !== false);
        if (!names.length) { toastInfo('Nothing selected — tick at least one room.'); return; }
        if (!confirm(`Apply "${_state.name}"?\n\nThis REPLACES the current world (${names.length} rooms). The previous world is kept on the undo stack — use ↩ Undo (or Ctrl+Z) to restore it.`)) return;

        const out = {
            name: _state.name || 'Generated Scenario',
            player: d.player || {},
            current_area: d.current_area && names.some(n => slugKey(n) === slugKey(d.current_area)) ? d.current_area : names[0],
            characters: (d.characters || []).filter((_, i) => _state.include.chars[i] !== false),
            world_lore: (d.world_lore || []).filter((_, i) => _state.include.lore[i] !== false),
            areas: {}
        };
        names.forEach((roomName, idx) => {
            const area = d.areas[roomName];
            const items = (area.items || []).filter((_, i) => _state.include.items[`${idx}::${i}`] !== false);
            const exits = {};
            for (const [dir, data] of Object.entries(area.exits || {})) {
                if (!data || !data.target) continue;
                exits[dir] = { target: data.target, state: data.state || 'open', hidden: !!data.hidden, description: data.description || '' };
            }
            out.areas[roomName] = { description: area.description || '', environment: area.environment || {}, exits, items };
        });

        btn.disabled = true;
        btn.textContent = 'Applying…';
        out.persist = true;  // wizard builds a new scenario — write it to scenarios/
        fetch('/api/load', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(out)
        })
            .then(resp => resp.json().then(j => ({ ok: resp.ok, j })))
            .then(({ ok, j }) => {
                if (!ok) throw new Error(j.error || 'load failed');
                worldState.fetch().then(() => {
                    try { events.log(`✨ Scenario "${out.name}" applied — ${names.length} rooms from text.`, 'system-msg'); } catch (e) {}
                    closeOverlay();
                    if (typeof toastInfo === 'function') toastInfo(`World built: ${names.length} rooms. Undo (↩) restores the previous world.`);
                });
            })
            .catch(err => {
                console.error('[scenario-wizard] apply failed:', err);
                toastError('Apply failed: ' + (err.message || err));
                btn.disabled = false;
                btn.textContent = '🚀 Apply World';
            });
    }

    function closeOverlay() {
        if (_overlay && _overlay.parentNode) _overlay.parentNode.removeChild(_overlay);
        _overlay = null;
        _state = null;
    }

    return {
        open() { renderInput(); },
        _normalizeDraft: normalizeDraft
    };
})();
