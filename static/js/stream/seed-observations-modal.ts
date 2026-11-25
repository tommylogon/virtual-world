/**
 * seed-observations-modal.ts - Fast batch Past Observation & Event Seeder (task-1014)
 *
 * Layer 1 (instant, 0 LLM): seeds deterministic area, visible item (with tags),
 * and connected way/aspect observations across 1..N players and 1..N areas or
 * a full scope, at a single past time or staggered across past N days.
 *
 * Layer 2 (optional, parallel LLM): weaves a subjective first-person memory
 * per selected character grounded in the selected rooms, items, and ways.
 */

interface SeedObservationsOptions {
    areas?: string[];
    players?: string[];
    scope?: string;
    tick?: number | null;
    onDone?: (result: any) => void;
}

const SeedObservationsModal = (() => {
    const MODAL_ID = 'seed-observations-modal';

    function _getAreasAndScopes(): { areas: Array<{ id: string; name: string; scope: string; desc: string }>; scopes: Map<string, string[]> } {
        const ws: any = (window as any).worldState;
        const nodes: Record<string, any> = ws?.graph?.nodes || ws?.data?.graph?.nodes || {};
        const areas: Array<{ id: string; name: string; scope: string; desc: string }> = [];
        const scopes = new Map<string, string[]>();
        for (const [id, n] of Object.entries(nodes)) {
            if (!n || n.type !== 'area') continue;
            const props = n.properties || {};
            const scope = String(props.scope || props.scope_id || '').trim();
            const name = String(n.name || id);
            const desc = String(props.description || '').trim();
            areas.push({ id, name, scope, desc });
            if (scope) {
                if (!scopes.has(scope)) scopes.set(scope, []);
                scopes.get(scope)!.push(name);
            }
        }
        areas.sort((a, b) => a.name.localeCompare(b.name));
        return { areas, scopes };
    }

    function _getPlayers(): Array<{ name: string; area: string; personality: string }> {
        const ws: any = (window as any).worldState;
        const pmap: Record<string, any> = ws?.players || ws?.data?.players || {};
        return Object.entries(pmap)
            .map(([name, p]) => ({
                name,
                area: String(p?.current_area || ''),
                personality: String(p?.personality || p?.description || ''),
            }))
            .sort((a, b) => a.name.localeCompare(b.name));
    }

    function close(): void {
        document.getElementById(MODAL_ID)?.remove();
    }

    function open(opts: SeedObservationsOptions = {}): void {
        close();
        const { areas, scopes } = _getAreasAndScopes();
        const players = _getPlayers();
        const currentTick = Number((window as any).worldState?.data?.time_ticks ?? (window as any).VW?.state?.tick ?? 0) || 0;

        const selectedPlayers = new Set<string>(
            opts.players && opts.players.length
                ? opts.players
                : players.slice(0, Math.min(players.length, 4)).map((p) => p.name)
        );
        const selectedAreas = new Set<string>(opts.areas || []);
        let selectedScope = String(opts.scope || '');
        if (selectedScope && scopes.has(selectedScope)) {
            for (const an of scopes.get(selectedScope)!) selectedAreas.add(an);
        }

        const perPlayerDrafts: Record<string, { text: string; importance: number; tags: string[] }> = {};

        const overlay = document.createElement('div');
        overlay.id = MODAL_ID;
        overlay.style.cssText = 'position:fixed;inset:0;z-index:10050;background:rgba(5,8,14,0.82);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;padding:16px;';

        const card = document.createElement('div');
        card.style.cssText = 'width:clamp(680px,84vw,1120px);max-height:min(88vh,860px);background:var(--bg-card,#161b22);border:1px solid var(--border,#30363d);border-radius:10px;display:flex;flex-direction:column;overflow:hidden;color:var(--text,#e6edf3);box-shadow:0 20px 60px rgba(0,0,0,0.65);';

        // Header
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--border,#30363d);background:var(--bg-inset,#0d1117);gap:12px;';
        header.innerHTML = `
            <div>
                <div style="font-weight:700;font-size:14px;">🌱 Seed Past Observations &amp; Events</div>
                <div style="font-size:11px;color:var(--text-muted,#8b949e);margin-top:2px;">Instant deterministic area/item/way observations (0 LLM) + optional parallel voiced memories. Current tick: ${currentTick}</div>
            </div>
            <button type="button" id="seed-obs-close" class="btn btn-sm" style="font-size:12px;">✕ Close</button>
        `;

        // Body: 2 fluid columns
        const body = document.createElement('div');
        body.style.cssText = 'flex:1;min-height:0;display:grid;grid-template-columns:minmax(260px,1fr) minmax(320px,1.25fr);gap:16px;padding:14px 16px;overflow-y:auto;';

        // Left column: Who + Scope + Areas
        const leftCol = document.createElement('div');
        leftCol.style.cssText = 'display:flex;flex-direction:column;gap:12px;min-height:0;';

        // Players section
        const playersBox = document.createElement('div');
        playersBox.style.cssText = 'background:var(--bg-inset,#0d1117);border:1px solid var(--border,#30363d);border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:8px;';
        playersBox.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;">
                <span style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted,#8b949e);">Who (${players.length})</span>
                <div style="display:flex;gap:4px;">
                    <button type="button" id="seed-p-all" class="btn btn-sm" style="font-size:10px;padding:2px 6px;">All</button>
                    <button type="button" id="seed-p-scope" class="btn btn-sm" style="font-size:10px;padding:2px 6px;">In Selected Areas</button>
                    <button type="button" id="seed-p-none" class="btn btn-sm" style="font-size:10px;padding:2px 6px;">None</button>
                </div>
            </div>
            <div id="seed-player-chips" style="display:flex;flex-wrap:wrap;gap:5px;max-height:140px;overflow-y:auto;"></div>
        `;

        // Scope & Areas section
        const areasBox = document.createElement('div');
        areasBox.style.cssText = 'flex:1;min-height:200px;background:var(--bg-inset,#0d1117);border:1px solid var(--border,#30363d);border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:8px;';
        const scopeOptsHtml = ['<option value="">(Manual area selection)</option>']
            .concat(Array.from(scopes.entries()).sort((a, b) => a[0].localeCompare(b[0])).map(([s, list]) =>
                `<option value="${s.replace(/"/g, '&quot;')}" ${s === selectedScope ? 'selected' : ''}>Scope: ${s} (${list.length} areas)</option>`
            )).join('');
        areasBox.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;">
                <span style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted,#8b949e);">Where (${areas.length} areas)</span>
                <div style="display:flex;gap:4px;">
                    <button type="button" id="seed-a-all" class="btn btn-sm" style="font-size:10px;padding:2px 6px;">All</button>
                    <button type="button" id="seed-a-none" class="btn btn-sm" style="font-size:10px;padding:2px 6px;">None</button>
                </div>
            </div>
            <select id="seed-scope-select" style="width:100%;font-size:11.5px;padding:5px 8px;background:var(--bg-input,#161b22);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:5px;">
                ${scopeOptsHtml}
            </select>
            <input type="text" id="seed-area-filter" placeholder="Filter areas..." style="width:100%;font-size:11px;padding:4px 8px;background:var(--bg-input,#161b22);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:5px;">
            <div id="seed-area-list" style="flex:1;min-height:140px;overflow-y:auto;display:flex;flex-direction:column;gap:3px;"></div>
        `;
        leftCol.append(playersBox, areasBox);

        // Right column: When + Deterministic toggles + Optional Note & Parallel LLM Weave
        const rightCol = document.createElement('div');
        rightCol.style.cssText = 'display:flex;flex-direction:column;gap:12px;min-height:0;';

        // When section
        const whenBox = document.createElement('div');
        whenBox.style.cssText = 'background:var(--bg-inset,#0d1117);border:1px solid var(--border,#30363d);border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:8px;';
        whenBox.innerHTML = `
            <span style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted,#8b949e);">When (Past Timestamp)</span>
            <div style="display:flex;gap:5px;flex-wrap:wrap;" id="seed-time-presets">
                <button type="button" class="btn btn-sm" data-preset="15m" style="font-size:10.5px;">15 min ago</button>
                <button type="button" class="btn btn-sm" data-preset="1h" style="font-size:10.5px;">1 hour ago</button>
                <button type="button" class="btn btn-sm" data-preset="1d" style="font-size:10.5px;">Yesterday</button>
                <button type="button" class="btn btn-sm" data-preset="spread3" style="font-size:10.5px;">Spread past 3 days</button>
                <button type="button" class="btn btn-sm" data-preset="spread7" style="font-size:10.5px;">Spread past 7 days</button>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <label style="font-size:11px;color:var(--text-muted,#8b949e);display:flex;flex-direction:column;gap:3px;">
                    Minutes ago (single past time)
                    <input type="number" id="seed-offset-mins" value="${opts.tick != null ? Math.max(0, (currentTick - opts.tick) * 5) : 15}" min="0" style="font-size:11.5px;padding:4px 8px;background:var(--bg-input,#161b22);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:5px;">
                </label>
                <label style="font-size:11px;color:var(--text-muted,#8b949e);display:flex;flex-direction:column;gap:3px;">
                    Spread across past N days (0 = single time)
                    <input type="number" id="seed-spread-days" value="0" min="0" step="0.5" style="font-size:11.5px;padding:4px 8px;background:var(--bg-input,#161b22);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:5px;">
                </label>
            </div>
        `;

        // Deterministic observation options
        const obsBox = document.createElement('div');
        obsBox.style.cssText = 'background:var(--bg-inset,#0d1117);border:1px solid var(--border,#30363d);border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:6px;';
        obsBox.innerHTML = `
            <span style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted,#8b949e);">What to Observe (Instant, 0 LLM)</span>
            <label style="font-size:11.5px;display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="seed-opt-items" checked> Visible items in each area (with item tags)</label>
            <label style="font-size:11.5px;display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="seed-opt-ways" checked> Connected ways &amp; lock/barrier aspects (locked, blocked, jammed)</label>
            <label style="font-size:11.5px;display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="seed-opt-hidden"> Include hidden / secret ways</label>
            <label style="font-size:11.5px;display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="seed-opt-milestone"> Also add a Timeline milestone marker at this timestamp</label>
        `;

        // Optional Event Note + Parallel LLM Weave
        const noteBox = document.createElement('div');
        noteBox.style.cssText = 'flex:1;background:var(--bg-inset,#0d1117);border:1px solid var(--border,#30363d);border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:8px;';
        noteBox.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">
                <span style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted,#8b949e);">Optional Shared Note / Past Event</span>
                <button type="button" id="seed-weave-btn" class="btn btn-sm btn-blue" style="font-size:10.5px;">✨ Weave in Each Character's Voice (Parallel LLM)</button>
            </div>
            <textarea id="seed-note-text" rows="3" placeholder="Optional: e.g. 'We tried the locked front door with the skull keyhole in the foyer, heard scratching in the walls, and retreated into the library.' Leave blank for pure zero-LLM observations." style="width:100%;font-size:11.5px;padding:7px 9px;background:var(--bg-input,#161b22);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:6px;resize:vertical;"></textarea>
            <div id="seed-weave-status" style="font-size:10.5px;color:var(--text-muted,#8b949e);"></div>
            <div id="seed-weave-drafts" style="display:none;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto;"></div>
        `;

        rightCol.append(whenBox, obsBox, noteBox);
        body.append(leftCol, rightCol);

        // Footer
        const footer = document.createElement('div');
        footer.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:10px 16px;border-top:1px solid var(--border,#30363d);background:var(--bg-inset,#0d1117);gap:12px;';
        footer.innerHTML = `
            <span id="seed-summary-line" style="font-size:11.5px;color:var(--text-muted,#8b949e);"></span>
            <div style="display:flex;gap:8px;">
                <button type="button" id="seed-cancel-btn" class="btn btn-sm">Cancel</button>
                <button type="button" id="seed-apply-btn" class="btn btn-sm btn-green" style="font-weight:600;">🌱 Seed Observations</button>
            </div>
        `;

        card.append(header, body, footer);
        overlay.appendChild(card);
        document.body.appendChild(overlay);

        // Render helpers
        const renderPlayers = () => {
            const host = overlay.querySelector('#seed-player-chips') as HTMLElement;
            host.innerHTML = '';
            for (const p of players) {
                const active = selectedPlayers.has(p.name);
                const chip = document.createElement('button');
                chip.type = 'button';
                chip.textContent = p.name;
                chip.title = p.area ? `Currently in ${p.area}` : p.name;
                chip.style.cssText = active
                    ? 'font-size:11px;padding:3px 9px;border-radius:12px;border:1px solid #388bfd;background:#1f6feb44;color:#79c0ff;cursor:pointer;'
                    : 'font-size:11px;padding:3px 9px;border-radius:12px;border:1px solid var(--border,#30363d);background:var(--bg-card,#161b22);color:var(--text-muted,#8b949e);cursor:pointer;';
                chip.addEventListener('click', () => {
                    if (selectedPlayers.has(p.name)) selectedPlayers.delete(p.name);
                    else selectedPlayers.add(p.name);
                    renderPlayers();
                    updateSummary();
                });
                host.appendChild(chip);
            }
        };

        const renderAreas = () => {
            const filter = ((overlay.querySelector('#seed-area-filter') as HTMLInputElement)?.value || '').trim().toLowerCase();
            const host = overlay.querySelector('#seed-area-list') as HTMLElement;
            host.innerHTML = '';
            for (const a of areas) {
                if (filter && !a.name.toLowerCase().includes(filter) && !a.scope.toLowerCase().includes(filter)) continue;
                const row = document.createElement('label');
                row.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:11.5px;padding:3px 6px;border-radius:4px;cursor:pointer;' + (selectedAreas.has(a.name) ? 'background:#1f6feb22;' : '');
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.checked = selectedAreas.has(a.name);
                cb.addEventListener('change', () => {
                    if (cb.checked) selectedAreas.add(a.name);
                    else selectedAreas.delete(a.name);
                    renderAreas();
                    updateSummary();
                });
                const left = document.createElement('span');
                left.style.cssText = 'display:flex;align-items:center;gap:6px;';
                left.append(cb, document.createTextNode(a.name));
                const right = document.createElement('span');
                right.style.cssText = 'font-size:10px;color:var(--text-muted,#8b949e);';
                right.textContent = a.scope || '';
                row.append(left, right);
                host.appendChild(row);
            }
        };

        const renderDrafts = () => {
            const box = overlay.querySelector('#seed-weave-drafts') as HTMLElement;
            const keys = Object.keys(perPlayerDrafts);
            if (!keys.length) {
                box.style.display = 'none';
                return;
            }
            box.style.display = 'flex';
            box.innerHTML = '';
            for (const pname of keys) {
                const d = perPlayerDrafts[pname];
                const wrap = document.createElement('div');
                wrap.style.cssText = 'background:var(--bg-card,#161b22);border:1px solid var(--border,#30363d);border-radius:6px;padding:6px 8px;display:flex;flex-direction:column;gap:4px;';
                const title = document.createElement('div');
                title.style.cssText = 'font-size:10.5px;font-weight:600;color:#79c0ff;';
                title.textContent = `🗣️ ${pname} (voiced memory draft)`;
                const ta = document.createElement('textarea');
                ta.rows = 2;
                ta.value = d.text;
                ta.style.cssText = 'width:100%;font-size:11px;padding:5px 7px;background:var(--bg-input,#0d1117);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:4px;resize:vertical;';
                ta.addEventListener('input', () => { d.text = ta.value; });
                wrap.append(title, ta);
                box.appendChild(wrap);
            }
        };

        const updateSummary = () => {
            const el = overlay.querySelector('#seed-summary-line') as HTMLElement;
            const spread = Number((overlay.querySelector('#seed-spread-days') as HTMLInputElement)?.value || 0);
            const mins = Number((overlay.querySelector('#seed-offset-mins') as HTMLInputElement)?.value || 0);
            const whenTxt = spread > 0 ? `staggered over past ${spread}d` : `${mins}m ago`;
            el.textContent = `${selectedPlayers.size} character(s) · ${selectedAreas.size} area(s) · ${whenTxt}`;
        };

        // Wire controls
        overlay.querySelector('#seed-obs-close')?.addEventListener('click', close);
        overlay.querySelector('#seed-cancel-btn')?.addEventListener('click', close);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

        overlay.querySelector('#seed-p-all')?.addEventListener('click', () => {
            players.forEach((p) => selectedPlayers.add(p.name));
            renderPlayers(); updateSummary();
        });
        overlay.querySelector('#seed-p-none')?.addEventListener('click', () => {
            selectedPlayers.clear();
            renderPlayers(); updateSummary();
        });
        overlay.querySelector('#seed-p-scope')?.addEventListener('click', () => {
            selectedPlayers.clear();
            const areaLower = new Set(Array.from(selectedAreas).map((a) => a.toLowerCase()));
            for (const p of players) {
                if (areaLower.has(p.area.toLowerCase())) selectedPlayers.add(p.name);
            }
            renderPlayers(); updateSummary();
        });

        overlay.querySelector('#seed-a-all')?.addEventListener('click', () => {
            areas.forEach((a) => selectedAreas.add(a.name));
            renderAreas(); updateSummary();
        });
        overlay.querySelector('#seed-a-none')?.addEventListener('click', () => {
            selectedAreas.clear();
            renderAreas(); updateSummary();
        });
        overlay.querySelector('#seed-scope-select')?.addEventListener('change', (e) => {
            selectedScope = (e.target as HTMLSelectElement).value;
            if (selectedScope && scopes.has(selectedScope)) {
                selectedAreas.clear();
                scopes.get(selectedScope)!.forEach((an) => selectedAreas.add(an));
            }
            renderAreas(); updateSummary();
        });
        overlay.querySelector('#seed-area-filter')?.addEventListener('input', renderAreas);

        overlay.querySelectorAll('#seed-time-presets button').forEach((btn) => {
            btn.addEventListener('click', () => {
                const p = (btn as HTMLElement).dataset.preset;
                const minsEl = overlay.querySelector('#seed-offset-mins') as HTMLInputElement;
                const spreadEl = overlay.querySelector('#seed-spread-days') as HTMLInputElement;
                if (p === '15m') { minsEl.value = '15'; spreadEl.value = '0'; }
                else if (p === '1h') { minsEl.value = '60'; spreadEl.value = '0'; }
                else if (p === '1d') { minsEl.value = '1440'; spreadEl.value = '0'; }
                else if (p === 'spread3') { minsEl.value = '0'; spreadEl.value = '3'; }
                else if (p === 'spread7') { minsEl.value = '0'; spreadEl.value = '7'; }
                updateSummary();
            });
        });
        overlay.querySelector('#seed-offset-mins')?.addEventListener('input', updateSummary);
        overlay.querySelector('#seed-spread-days')?.addEventListener('input', updateSummary);

        // Optional Layer 2: Parallel LLM Voice Weave
        overlay.querySelector('#seed-weave-btn')?.addEventListener('click', async () => {
            const note = ((overlay.querySelector('#seed-note-text') as HTMLTextAreaElement)?.value || '').trim();
            const statusEl = overlay.querySelector('#seed-weave-status') as HTMLElement;
            if (!note) {
                statusEl.textContent = 'Type a 1-2 sentence event description above first.';
                return;
            }
            if (!selectedPlayers.size) {
                statusEl.textContent = 'Select at least one character first.';
                return;
            }
            const llm = (window as any).LLMClient;
            if (!llm || typeof llm.chat !== 'function') {
                statusEl.textContent = 'LLMClient not configured - you can still save the shared note directly without LLM.';
                return;
            }
            statusEl.textContent = `Weaving voiced drafts for ${selectedPlayers.size} character(s) in parallel...`;
            const areaList = Array.from(selectedAreas);
            const areaDescs = areas.filter((a) => selectedAreas.has(a.name)).slice(0, 4).map((a) => `${a.name}: ${a.desc}`).join('\n');
            const pList = Array.from(selectedPlayers);

            await Promise.all(pList.map(async (pname) => {
                const pObj = players.find((x) => x.name === pname);
                const sys = `You write a brief first-person past memory (2-3 sentences) in ${pname}'s exact voice and personality. Stay strictly grounded in the provided room(s) and event. Do not invent objects not mentioned. Return plain first-person prose only.`;
                const usr = `Character: ${pname}\nPersonality: ${pObj?.personality || ''}\nLocation(s): ${areaList.join(', ')}\n${areaDescs ? `Room details:\n${areaDescs}\n` : ''}Shared event: ${note}`;
                try {
                    const reply = await llm.chat([{ role: 'system', content: sys }, { role: 'user', content: usr }], { max_tokens: 220, temperature: 0.7 });
                    const txt = String(typeof reply === 'string' ? reply : (reply?.content || reply?.text || '')).trim();
                    if (txt) {
                        perPlayerDrafts[pname] = { text: txt, importance: 6, tags: ['backstory', 'woven'] };
                    }
                } catch (_err) {
                    perPlayerDrafts[pname] = { text: note, importance: 6, tags: ['backstory'] };
                }
            }));
            statusEl.textContent = `Ready: ${Object.keys(perPlayerDrafts).length} voiced draft(s). Edit if needed, then click Seed Observations.`;
            renderDrafts();
        });

        // Apply button
        overlay.querySelector('#seed-apply-btn')?.addEventListener('click', async () => {
            const btn = overlay.querySelector('#seed-apply-btn') as HTMLButtonElement;
            if (!selectedPlayers.size || !selectedAreas.size) {
                (window as any).VW?.ui?.setStatus?.('Select at least one character and one area.', 'error');
                return;
            }
            btn.disabled = true;
            btn.textContent = 'Seeding...';
            try {
                const spreadDays = Number((overlay.querySelector('#seed-spread-days') as HTMLInputElement)?.value || 0);
                const offsetMins = Number((overlay.querySelector('#seed-offset-mins') as HTMLInputElement)?.value || 0);
                const payload: Record<string, any> = {
                    players: Array.from(selectedPlayers),
                    areas: Array.from(selectedAreas),
                    scope: selectedScope || undefined,
                    observe_items: !!(overlay.querySelector('#seed-opt-items') as HTMLInputElement)?.checked,
                    observe_ways: !!(overlay.querySelector('#seed-opt-ways') as HTMLInputElement)?.checked,
                    include_hidden_ways: !!(overlay.querySelector('#seed-opt-hidden') as HTMLInputElement)?.checked,
                    add_timeline_milestone: !!(overlay.querySelector('#seed-opt-milestone') as HTMLInputElement)?.checked,
                    note: ((overlay.querySelector('#seed-note-text') as HTMLTextAreaElement)?.value || '').trim(),
                    per_player_notes: Object.keys(perPlayerDrafts).length ? perPlayerDrafts : undefined,
                };
                if (spreadDays > 0) payload.spread_days = spreadDays;
                else if (offsetMins > 0) payload.offset_minutes = offsetMins;

                const resp = await fetch('/api/world/seed-observations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await resp.json();
                if (!resp.ok) {
                    (window as any).VW?.ui?.setStatus?.(data?.error || 'Failed to seed observations', 'error');
                    btn.disabled = false;
                    btn.textContent = '🌱 Seed Observations';
                    return;
                }
                await (window as any).worldState?.fetch?.();
                await (window as any).TimelineBar?.refresh?.();
                (window as any).VW?.ui?.setStatus?.(
                    `Seeded ${data.players_seeded} character(s) across ${data.areas_seeded} area(s) (${data.items_seeded} items, ${data.ways_seeded} ways${data.notes_added ? `, ${data.notes_added} note(s)` : ''})`,
                    'info'
                );
                opts.onDone?.(data);
                close();
            } catch (err) {
                (window as any).VW?.ui?.setStatus?.(`Seed error: ${err}`, 'error');
                btn.disabled = false;
                btn.textContent = '🌱 Seed Observations';
            }
        });

        renderPlayers();
        renderAreas();
        updateSummary();
    }

    return { open, close };
})();

(window as any).SeedObservationsModal = SeedObservationsModal;
