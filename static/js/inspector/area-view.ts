/**
 * InspectorAreaView — Area inspector (showArea, improveRoomWithAI, environment editing)
 * Extracted from inspector.js for modularity.
 * task-216: renders lit-html TemplateResults through InspectorPanel (single panel owner).
 *
 * @module inspector/area-view — the area (room) inspector
 * @contributes InspectorAreaView: description/environment/light/noise editing, scope membership, AI room improvement
 * @powers Node inspectors, Look around — inspecting and editing a room, its scope membership and its exits
 * @relates renders through InspectorPanel; uses inspector/helpers + way-authoring; scope list via api.getWorldScopes
 * @docs docs/virtualWorld/World Building/Rooms & Areas.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

interface InspectorAreaViewWindowSurface { InspectorAreaView: unknown }
(window as unknown as InspectorAreaViewWindowSurface).InspectorAreaView = (() => {
    const RV = {} as AreaViewApi;

    // Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
    const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]): unknown =>
        (window as unknown as AreaViewWindow).Lit.html(strings, ...values);

    /**
     * event-stream.js declares `class EventBus` at the top level of a classic
     * script, so it is reachable as a bare global lexical binding and NOT as
     * `window.EventBus`. globals.d.ts does not declare it, and a local
     * `declare const` would collide with the real binding (TS2451), so this
     * reads it bare under a scoped @ts-ignore. Resolved per call, never cached
     * at load, so it behaves exactly as the direct reference did.
     */
    /**
     * library-browser.js declares `const libraryBrowser` at the top level of a
     * classic script, so it is a global lexical binding and NOT a window
     * property. Read it bare, exactly as the code always has, under a scoped
     * @ts-ignore. Note the guard at its only call site tests
     * `window.libraryBrowser`, which is therefore always falsy — that is
     * pre-existing behaviour and is preserved here rather than "fixed".
     */
    function libraryBrowserRef(): LibraryBrowserApi {
        // @ts-ignore -- global lexical binding from library-browser.js
        return libraryBrowser;
    }

    function eventBus(): EventBusStatics {
        // @ts-ignore -- global lexical class binding from event-stream.js
        return EventBus;
    }

    /**
     * Render the full area inspector panel
     * @param {string} nodeId - Graph node ID
     * @param {object} graphNode - Graph node data
     */
    RV.showArea = function(nodeId: string, graphNode: AreaViewGraphNode) {
        const name = graphNode.name as string;
        const props = graphNode.properties || {};
        const description = props.description || '';
        const env = props.environment || {};

        // Resolve actual graph node ID
        let actualNodeId = nodeId;
        if (!worldState.getNode(nodeId) && worldState.graph?.nodes) {
            const found = (Object.entries(worldState.graph.nodes) as Array<[string, AreaViewGraphNode]>)
                .find(([, node]) => node.type === 'area' && node.name === name);
            if (found) actualNodeId = found[0];
        }

        // Exits — authoring view includes hidden/undiscovered ways; the
        // gameplay-filtered list stays available as `exits` for reference.
        const areaData = worldState.areas?.[name];
        const exits = areaData?.exits_authoring || areaData?.exits || {};
        const exitEntries = Object.entries(exits);

        // Agents here
        const agentsHere = (Object.entries(worldState.players || {}) as Array<[string, { current_area?: string }]>)
            .filter(([, player]) => player.current_area === name);

        // Area Event Log
        const roomEvents = events.getAreaEvents(name);

        // Area tags
        const areaTags = (Array.isArray(props.tags) ? props.tags : []) as string[];

        // Items in area
        const items = worldState.getItemsInArea(name);

        const template = htmlTag`
            ${RV._renderRoomHeader(name, actualNodeId)}
            ${RV._renderDescriptionSection(description, actualNodeId)}
            ${RV._renderEnvironmentSection(env, actualNodeId)}
            ${RV._renderFloorSection(props, actualNodeId)}
            ${RV._renderScopeSection(props, actualNodeId)}
            ${(window as unknown as AreaViewWindow).InspectorHelpers.graphGravityControl(actualNodeId, props)}

            <div class="inspector-section"><h3>🚪 Exits <span class="section-hint">(${exitEntries.length} found)</span></h3>
                <div style="display:flex;flex-direction:column;gap:4px;">
                    ${exitEntries.length > 0
                        ? (exitEntries as Array<[string, AreaViewExitData]>).map(([exitName, exitData]) => RV._renderExitItem(exitName, exitData, actualNodeId))
                        : htmlTag`<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No exits from this area.</div>`}
                </div>
            </div>

            <div class="inspector-section"><h3>📦 Actions</h3>
                <div style="font-size:11px;color:var(--text-muted);padding:4px 0;">Use 📚 Item Library in the toolbar to add items.</div>
            </div>

            ${(window as unknown as AreaViewWindow).InspectorTriggers ? (window as unknown as AreaViewWindow).InspectorTriggers.buildTriggersHtml(actualNodeId, props.locked_fields || []) : (window as unknown as AreaViewWindow).Lit.nothing}

            <div class="inspector-section"><h3>🧍 Agents</h3>
                ${agentsHere.length > 0
                    ? agentsHere.map(([agentName]) => htmlTag`
                        <div class="relationship-item" @click=${() => VW.inspector.showAgent(agentName)}>
                            <span class="rel-node">${agentName}</span>
                        </div>`)
                    : htmlTag`<div style="font-size:11px;color:var(--text-muted);">No agents</div>`}
            </div>

            <div class="inspector-section"><h3>📜 Area Event Log <span class="section-hint">(who did what)</span></h3>
                <div class="area-event-log" style="max-height:240px;overflow-y:auto;font-size:11px;">
                    ${roomEvents.length > 0
                        ? (roomEvents as AreaEvent[]).map((evt: AreaEvent) => {
                            const icon = eventBus().getActionIcon(evt);
                            const color = eventBus().getActionColor(evt);
                            const resultPreview = (evt.result || '');
                            return htmlTag`<div class="area-event-entry" style="padding:4px 8px;border-bottom:1px solid var(--border-light);display:flex;align-items:flex-start;gap:6px;">
                                <span style="flex-shrink:0;color:var(--text-muted);font-size:9px;">[${events.tickToTime(evt.tick)}]</span>
                                <span style="flex-shrink:0;">${icon}</span>
                                <span style="flex-shrink:0;font-weight:600;color:${color};">${evt.actor}</span>
                                <div style="flex:1;min-width:0;">
                                    ${evt.action ? htmlTag`<div style="color:var(--accent);font-family:var(--font-mono);font-size:10px;">${evt.action}</div>` : (window as unknown as AreaViewWindow).Lit.nothing}
                                    ${resultPreview ? htmlTag`<div style="color:var(--text-dim);font-size:10px;">→ ${resultPreview}${(evt.result as string).length > 100 ? '...' : ''}</div>` : (window as unknown as AreaViewWindow).Lit.nothing}
                                </div>
                            </div>`;
                        })
                        : htmlTag`<div style="padding:8px;color:var(--text-muted);">No events recorded in this area yet. Events appear as characters take actions, speak, or affect the environment.</div>`}
                </div>
            </div>

            <div class="inspector-section"><h3>🏷️ Tags</h3>
                <div id="tag-multiselect-area-${actualNodeId}"></div>
                <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">Tag an area <code>exterior</code> to make it an infinite heat reservoir.</div>
            </div>

            ${InspectorHelpers.renderAliasesSection(actualNodeId, props.aliases)}

            <div class="inspector-section"><h3>📦 Items</h3>
                ${items.length > 0
                    ? (items as Array<{ id: string; name: string; properties?: { current_state?: string } }>).map((item) => htmlTag`
                        <div class="relationship-item" @click=${() => VW.inspector.showNode(item.id)}>
                            <span class="rel-node">${item.properties?.current_state === 'locked' ? '🔒 ' : '📦 '}${item.name}</span>
                        </div>`)
                     : htmlTag`<div style="font-size:11px;color:var(--text-muted);">No items</div>`}
            </div>

            ${(window as unknown as AreaViewWindow).InspectorTemplateSync ? (window as unknown as AreaViewWindow).Lit.unsafeHTML((window as unknown as AreaViewWindow).InspectorTemplateSync.renderTemplateRow('area', actualNodeId, props)) : ''}
        `;

        (window as unknown as AreaViewWindow).InspectorPanel.render(template);

        // task-173: live "sounds heard here" readout (engine-sourced).
        const soundsEl = document.getElementById(`room-sounds-${actualNodeId}`);
        if (soundsEl) {
            RV._fillAreaSounds(soundsEl, actualNodeId);
        }

        if ((window as unknown as AreaViewWindow).InspectorTemplateSync) {
            (window as unknown as AreaViewWindow).InspectorTemplateSync.populateSelector('area', actualNodeId);
        }

        RV._fillScopeSelect(actualNodeId, props.world_scope_id || '');

        if ((window as unknown as AreaViewWindow).events) events.setAreaFilter(name);

        // Initialize TagMultiselect for area tags (render is synchronous, so the
        // container exists by now).
        const tagContainer = document.getElementById(`tag-multiselect-area-${actualNodeId}`);
        if (tagContainer && typeof (window as unknown as AreaViewWindow).TagMultiselect !== 'undefined') {
            new (window as unknown as AreaViewWindow).TagMultiselect(tagContainer, {
                tags: areaTags,
                appliesTo: 'areas',
                allowNew: true,
                placeholder: 'Search or create tags...',
                onChange: (newTags: string[]) => {
                    api.updateNode(actualNodeId, { properties: { tags: newTags } }).then(() => worldState.fetch());
                }
            });
        }
    };

    /**
     * Render the area header (badge, editable name, node ID, close button)
     * @param {string} name - Area display name
     * @param {string} actualNodeId - Graph node ID
     * @returns {TemplateResult}
     */
    RV._renderRoomHeader = function(name: string, actualNodeId: string): TemplateResult {
        return htmlTag`<div class="inspector-header">
            <span class="inspector-type-badge" style="background:#58a6ff">🏠 Area</span>
            <div style="flex:1;display:flex;flex-direction:column;">
                <h2 style="margin:0;font-size:16px;"><input type="text" .value=${name} @change=${(ev: Event) => api.updateNode(actualNodeId, { name: (ev.target as HTMLInputElement).value }).then(() => worldState.fetch())} style="font-size:1em;background:transparent;border:1px solid var(--border);color:inherit;width:100%;"></h2>
                <div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                    <div style="display:flex;gap:2px;align-items:center;">
                        ${InspectorHelpers.isGeneratedNode(actualNodeId)
                            ? htmlTag`<span style="font-size:10px;color:var(--text-muted);flex:1;min-width:0;" title="Generated node id — owned by the world compiler; it is regenerated on recompile and cannot be renamed">${actualNodeId}</span>`
                            : htmlTag`<input type="text" .value=${actualNodeId} @change=${(ev: Event) => InspectorHelpers.renameNode(actualNodeId, (ev.target as HTMLInputElement).value)} style="font-size:10px;padding:1px 4px;background:transparent;border:1px solid transparent;color:var(--text-muted);flex:1;min-width:0;cursor:text;" title="Change node ID (lowercase, no spaces)">
                                <button class="btn btn-sm btn-ghost" @click=${() => InspectorHelpers.syncIdFromName(actualNodeId, name)} title="Sync ID from name">🔄</button>`}
                    </div>
                </div>
            </div>
            <button class="btn btn-sm btn-ghost" data-populate-area=${actualNodeId} @click=${() => RV.populateArea(actualNodeId)} title="Populate this area with fitting furniture and items from the library by its domain tags" style="font-size:10px;">🪄 Populate</button>
                    <button class="btn btn-sm btn-ghost" @click=${() => libraryBrowserRef().saveAreaByName(name)} title="Save this area to library" style="font-size:10px;">📚 Save to Library</button>
            <button class="btn btn-sm btn-ghost" @click=${() => graphManager._duplicateNode(actualNodeId)} title="Duplicate this area with its items, contents and triggers" style="font-size:10px;">📋 Duplicate</button>
            <button class="btn btn-sm btn-ghost" @click=${() => (window as unknown as AreaViewWindow).hideInspectorPanel()}>✕</button>
        </div>`;
    };

    /**
     * Render the description section with AI improve button
     * @param {string} description - Area description text
     * @param {string} actualNodeId - Graph node ID
     * @returns {TemplateResult}
     */
    RV._renderDescriptionSection = function(description: string, actualNodeId: string): TemplateResult {
        return htmlTag`<div class="inspector-section"><h3>Description</h3>
            <textarea rows="2" style="width:100%;padding:4px 8px;font-size:12px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);font-family:var(--font);resize:vertical;min-height:40px;"
                .value=${description}
                @change=${(ev: Event) => api.updateNode(actualNodeId, { properties: { description: (ev.target as HTMLTextAreaElement).value } }).then(() => worldState.fetch())}></textarea>
            <div style="display:flex;gap:4px;margin-top:4px;">
                <button class="btn btn-sm" id="improve-area-btn" @click=${() => RV.improveRoomWithAI(actualNodeId)} style="white-space:nowrap;background:#2a6a3a;border-color:#3a9a5a;color:#7cff9c;">✨ Improve</button>
            </div></div>`;
    };

    /**
     * Render the environment section (light, temperature, air, smell, noise)
     * @param {object} env - Environment properties
     * @param {string} actualNodeId - Graph node ID
     * @returns {TemplateResult}
     */
    RV._renderEnvironmentSection = function(env: AreaEnv, actualNodeId: string): TemplateResult {
        // `light` is numeric (0-100) in some areas and an enum word in others —
        // both are valid and `engine/lighting.py`'s get_light_int reads either.
        // A select could only show the enum half, and a numeric 80 selected no
        // option at all (silently showing "pitch black"). A text field with the
        // presets as suggestions round-trips both (task-640).
        const lightValue = env.light ?? 'normal';
        const lightPresets = ['pitch_black', 'dim', 'normal', 'bright', 'blinding'];

        const airValue = env.air || 'fresh';
        const airOptions = ['fresh', 'stale', 'humid', 'toxic', 'smoky', 'fragrant'].map(airName =>
            htmlTag`<option value=${airName} ?selected=${airValue === airName}>${airName.charAt(0).toUpperCase() + airName.slice(1)}</option>`
        );

        // `noise` is free text in the data ("busy", "dripping water"), so a
        // closed select loses what is there and cannot represent it. Suggestions
        // cover both the engine's mechanical vocabulary (silent/quiet/normal/
        // loud/chaotic — engine/sound.py `_noise_levels`) and the descriptive
        // words already authored (task-640).
        const noiseValue = env.noise || 'quiet';
        const noisePresets = ['silent', 'quiet', 'normal', 'loud', 'chaotic', 'dripping', 'humming', 'windy'];

        // The world forecast drives daylight and the top-bar sky; an area's own
        // weather drives only that area's prose (engine/area_description.py:459).
        // They are independent, and the editor used to show the area value with
        // no sign of the world one, so "clear" here read as if it contradicted the
        // header's "overcast". Surface the world value (task-640).
        let worldWeather = 'clear';
        try {
            const data = (typeof worldState !== 'undefined' && worldState && worldState.data) || {};
            // Use the sky widget's own resolver so the hint and the top bar can
            // never disagree; fall back to the same precedence inline.
            if ((window as unknown as AreaViewWindow).SkyScape && typeof (window as unknown as AreaViewWindow).SkyScape.effectiveWeather === 'function') {
                worldWeather = (window as unknown as AreaViewWindow).SkyScape.effectiveWeather(data) || 'clear';
            } else {
                const override = data.forecast_override && data.forecast_override.weather;
                const entries = (data.forecast_schedule && data.forecast_schedule.entries) || [];
                worldWeather = override || (entries.length ? entries[0].weather : '') || 'clear';
            }
        } catch (error) { /* keep the default */ }

return htmlTag`<div class="inspector-section"><h3>🌡️ Environment</h3>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Light</label>
                <input type="text" id="room-light" list="room-light-presets" .value=${lightValue} style="flex:1;font-size:11px;" title="A number 0–100 or a preset word — the engine reads either" @change=${(ev: Event) => RV._updateEnvLight(actualNodeId, (ev.target as HTMLInputElement).value)}>
                <datalist id="room-light-presets">${lightPresets.map(lightName => htmlTag`<option value=${lightName}></option>`)}</datalist>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Temp °C</label>
                <input type="number" min="-50" max="100" step="0.1" .value=${Math.round((env.temperature ?? 21) * 10) / 10} style="flex:1;" @change=${(ev: Event) => RV._updateEnv(actualNodeId, 'temperature', Math.round(parseFloat((ev.target as HTMLInputElement).value) * 10) / 10)}>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Air</label>
                <select id="room-air" @change=${(ev: Event) => RV._updateEnv(actualNodeId, 'air', (ev.target as HTMLInputElement).value)} style="flex:1;">${airOptions}</select>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Smell</label>
                <input type="text" .value=${env.smell || 'neutral'} style="flex:1;font-size:11px;" @change=${(ev: Event) => RV._updateEnv(actualNodeId, 'smell', (ev.target as HTMLInputElement).value || 'neutral')}>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Noise</label>
                <input type="text" list="room-noise-presets" .value=${noiseValue} style="flex:1;font-size:11px;" title="Free text for the prose. The mechanics read silent, quiet, normal, loud, chaotic." @change=${(ev: Event) => RV._updateEnv(actualNodeId, 'noise', (ev.target as HTMLInputElement).value)}>
                <datalist id="room-noise-presets">${noisePresets.map(noiseName => htmlTag`<option value=${noiseName}></option>`)}</datalist>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Weather</label>
                <select @change=${(ev: Event) => RV._updateEnv(actualNodeId, 'weather', (ev.target as HTMLInputElement).value)} style="flex:1;">
                    ${['', 'clear', 'cloudy', 'windy', 'rainy', 'stormy', 'foggy', 'snowy'].map(w =>
                        htmlTag`<option value=${w} ?selected=${(env.weather || '') === w}>${w === '' ? '— none (no weather line) —' : w}</option>`)}
                </select>
                <span style="font-size:10px;color:var(--text-muted);white-space:nowrap;" title="This area's weather drives its prose only. The world forecast (top bar) drives daylight and the sky; it is a separate field and is not overridden here.">world: ${worldWeather}</span>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Wind</label>
                <select @change=${(ev: Event) => RV._updateEnv(actualNodeId, 'wind', (ev.target as HTMLInputElement).value)} style="flex:1;">
                    ${['none', 'breeze', 'wind', 'gale', 'storm', 'hurricane'].map(w =>
                        htmlTag`<option value=${w} ?selected=${(env.wind || 'none') === w}>${w}</option>`)}
                </select>
            </div>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">Humidity</label>
                <select @change=${(ev: Event) => RV._updateEnv(actualNodeId, 'humidity', (ev.target as HTMLInputElement).value)} style="flex:1;">
                    ${['dry', 'humid', 'wet', 'flooding'].map(h =>
                        htmlTag`<option value=${h} ?selected=${(env.humidity || 'dry') === h}>${h}</option>`)}
                </select>
            </div>
            ${RV._renderEnvPresetRow(env, actualNodeId)}
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <label style="min-width:50px;">🔊 Sounds</label>
                <span id="room-sounds-${actualNodeId}" style="flex:1;font-size:11px;color:var(--text-muted);">…</span>
            </div>
        </div>`;
    };

    /**
     * task-379: environment presets — save the current env as a named preset,
     * apply a preset to this area / area + open-way neighbours / all areas.
     * Presets live in localStorage; applies go through api.updateNode so the
     * existing undo snapshots cover them.
     */
    RV._renderEnvPresetRow = function(env: AreaEnv, actualNodeId: string): TemplateResult {
        const presets = (window as unknown as AreaViewWindow).EnvPresets ? (window as unknown as AreaViewWindow).EnvPresets.list() : [];
        const options = presets.length
            ? presets.map(name => htmlTag`<option value=${name}>${name}</option>`)
            : htmlTag`<option value="">— no presets saved —</option>`;
        return htmlTag`<div class="field" style="border-top:1px dashed var(--border);padding-top:8px;margin-top:8px;">
            <label style="font-size:10px;color:var(--text-muted);">🧴 Presets</label>
            <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
                <select id="env-preset-select" style="flex:1;min-width:110px;font-size:11px;">${options}</select>
                <button class="btn btn-sm btn-blue" title="Apply the selected preset"
                    @click=${() => RV._applyEnvPreset(actualNodeId)}>▶ Apply</button>
                <button class="btn btn-sm" title="Save this area's environment as a preset"
                    @click=${() => RV._saveEnvPreset(env)}>💾 Save</button>
                <button class="btn btn-sm btn-ghost" title="Delete the selected preset"
                    @click=${() => RV._deleteEnvPreset()}>🗑</button>
            </div>
            <div style="display:flex;gap:4px;align-items:center;margin-top:4px;">
                <label style="font-size:9px;color:var(--text-muted);">Apply to</label>
                <select id="env-preset-scope" style="flex:1;font-size:10px;">
                    <option value="current">This area</option>
                    <option value="connected">Area + connected (open ways)</option>
                    <option value="all">All areas</option>
                </select>
            </div>
        </div>`;
    };

    RV._saveEnvPreset = function(env: AreaEnv): void {
        if (!(window as unknown as AreaViewWindow).EnvPresets) return;
        const name = prompt('Preset name:', 'Arctic: -12° bright fresh');
        if (!name) return;
        (window as unknown as AreaViewWindow).EnvPresets.save(name.trim(), env);
        if ((window as unknown as AreaViewWindow).VW?.inspector) (window as unknown as AreaViewWindow).VW.inspector._reRender();
    };

    RV._deleteEnvPreset = function(): void {
        if (!(window as unknown as AreaViewWindow).EnvPresets) return;
        const sel = document.getElementById('env-preset-select');
        const name = (sel as HTMLSelectElement | null)?.value;
        if (!name) return;
        if (!confirm(`Delete preset "${name}"?`)) return;
        (window as unknown as AreaViewWindow).EnvPresets.delete(name);
        if ((window as unknown as AreaViewWindow).VW?.inspector) (window as unknown as AreaViewWindow).VW.inspector._reRender();
    };

    RV._applyEnvPreset = async function(actualNodeId: string): Promise<void> {
        if (!(window as unknown as AreaViewWindow).EnvPresets) return;
        const name = (document.getElementById('env-preset-select') as HTMLSelectElement | null)?.value;
        const scope = (document.getElementById('env-preset-scope') as HTMLSelectElement | null)?.value || 'current';
        if (!name) return;
        const result = await (window as unknown as AreaViewWindow).EnvPresets.apply(name, scope, actualNodeId);
        if (!result.applied) return;
        const label = result.areaNames.slice(0, 3).join(', ') + (result.areaNames.length > 3 ? ` +${result.areaNames.length - 3}` : '');
        if (typeof toastInfo === 'function') toastInfo(`Preset "${name}" applied to ${result.applied} area(s): ${label}`);
    };

    /**
     * task-173: fill the 🔊 Sounds readout from the engine (active sound
     * sources in this area — level + pattern, like the graph overlay).
     * @param {HTMLElement} el - Target span
     * @param {string} areaId - Graph node id of the area
     */
    RV._fillAreaSounds = function(el: HTMLElement, areaId: string): void {
        el.textContent = '…';
        fetch(`/api/areas/${encodeURIComponent(areaId)}/sounds`)
            .then(r => (r.ok ? r.json() : { sounds: [] }))
            .then(data => {
                const sounds = data.sounds || [];
                if (!sounds.length) { el.textContent = 'quiet — no active sound sources.'; return; }
                const levelWord: Record<number, string> = { 1: 'nearby', 2: 'loud', 3: 'carrying' };
                el.textContent = (sounds as AreaSound[]).map((s: AreaSound) =>
                    `${s.pattern}${s.name ? ` (${s.name})` : ''}` +
                    (levelWord[s.level!] ? ` — ${levelWord[s.level!]}` : '')
                ).join(' · ');
            })
            .catch(() => { el.textContent = '—'; });
    };

    /**
     * Render the floor section
     *
     * `floor` is a **storey index**: 0 is the ground plane, 1 one storey up, -1
     * one down, and it is deliberately *unbounded* — three stacked rooms, the
     * bottom of a lake, an 80-storey tower, a hole to hell at -900. So there is
     * no min/max on the input (a clamp to ±10 quietly caps a skyscraper at ten
     * floors); the browser's own number spinner is enough. A non-numeric value
     * is a save written before the material moved to `surface`, and reads as
     * ground. The ground *material* is shown under it, read from
     * `properties.surface` — which is where the WorldPainter compiler puts it.
     *
     * @param {object} props - Node properties
     * @param {string} actualNodeId - Graph node id
     * @returns {TemplateResult}
     */
    RV._renderFloorSection = function(props: NodeProps, actualNodeId: string): TemplateResult {
        const raw = props.floor ?? 0;
        const parsed = Number(raw);
        const floorValue = Number.isFinite(parsed) ? Math.round(parsed) : 0;
        const label = floorValue === 0 ? 'Ground'
            : (floorValue > 0 ? `Floor ${floorValue}` : `Floor ${floorValue} (below)`);
        return htmlTag`<div class="inspector-section"><h3>🏗️ Floor</h3>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <input type="number" step="1" .value=${floorValue} style="flex:1;" @change=${(ev: Event) => api.updateNode(actualNodeId, { properties: { floor: parseInt((ev.target as HTMLInputElement).value, 10) || 0 } }).then(() => worldState.fetch())}>
                <span style="font-size:10px;color:var(--text-muted);">${label}</span>
            </div>
            <div style="font-size:10px;color:var(--text-muted);margin-top:4px;">
                Storey: 0 is ground, 1 one up, -1 one down — no upper or lower limit.
            </div>
            ${props.surface ? htmlTag`<div style="font-size:10px;color:var(--text-muted);margin-top:2px;">
                Standing on: ${String(props.surface).replace(/_/g, ' ')}
            </div>` : ''}
        </div>`;
    };

    /**
     * Render the scope-membership section (task-539).
     *
     * `world_scope_id` *is* membership — the WorldPainter and the graph's scope
     * views read nothing else — so it belongs here, next to the area, instead of
     * being something you can only change by parking the area on a painted cell
     * (which is placement, a different thing). Map placement is shown in the same
     * section so the two are read as one fact rather than two hidden ones.
     *
     * @param {object} props - Node properties
     * @param {string} actualNodeId - Graph node ID
     * @returns {TemplateResult}
     */
    RV._renderScopeSection = function(props: NodeProps, actualNodeId: string): TemplateResult {
        const cell = props.cell || null;
        const placement = cell ? `cell (${cell.x},${cell.y})` : null;
        return htmlTag`<div class="inspector-section"><h3>🗺️ Scope</h3>
            <div class="field" style="display:flex;align-items:center;gap:8px;">
                <select id="area-scope-${actualNodeId}" style="flex:1;"
                    title="Which scope this area belongs to. Membership decides what
                           each scope's view lists — it is not the same as putting the
                           area on a painted cell.">
                    <option value="">loading scopes…</option>
                </select>
            </div>
            <div style="font-size:9px;color:var(--text-muted);margin-top:3px;">
                ${placement
                    ? htmlTag`On the map at ${placement} — <button class="btn btn-sm btn-ghost" style="font-size:9px;" @click=${() => RV._openInPainter(actualNodeId, props)}>open in WorldPainter</button>`
                    : 'Not placed on any painted cell. Membership alone decides which scope lists it.'}
            </div>
        </div>`;
    };

    /**
     * Populate the scope select once the scope list arrives (task-539). The
     * options come from the server, so a new scope needs no front-end change.
     */
    RV._fillScopeSelect = function(actualNodeId: string, currentScopeId: string): void {
        const sel = document.getElementById(`area-scope-${actualNodeId}`);
        if (!sel) return;
        api.getWorldScopes(true).then((data: { scopes?: ScopeOption[] }) => {
            // The world may have changed under the panel; re-render is cheap and
            // the element is gone if the author moved on.
            const live = document.getElementById(`area-scope-${actualNodeId}`);
            if (!live) return;
            const scopes = (data && data.scopes) || [];
            live.innerHTML = '';
            const none = document.createElement('option');
            none.value = '';
            none.textContent = '— no scope —';
            live.appendChild(none);
            (scopes as ScopeOption[]).forEach((s) => {
                const opt = document.createElement('option');
                opt.value = s.id;
                // `depth` comes from flat_scopes' depth-first walk, so a nested
                // scope reads as a child of the one above it.
                opt.textContent = `${'  '.repeat(s.depth || 0)}${s.name}`;
                if (s.id === currentScopeId) opt.selected = true;
                live.appendChild(opt);
            });
            if (currentScopeId && !(scopes as ScopeOption[]).some((s) => s.id === currentScopeId)) {
                // A scope id with no record (hand-edited data) still has to be
                // visible as the current value, or the select would lie.
                const orphan = document.createElement('option');
                orphan.value = currentScopeId;
                orphan.textContent = `${currentScopeId} (missing)`;
                orphan.selected = true;
                live.appendChild(orphan);
            }
            const nameOf = (id?: string) => {
                const hit = (scopes as ScopeOption[]).find((s) => s.id === id);
                return hit ? hit.name : (id || 'its scope');
            };
            live.addEventListener('change', async (ev: Event) => {
                const target = (ev.target as HTMLSelectElement).value;
                const previous = currentScopeId;
                if (target === previous) return;
                try {
                    // "— no scope —" has no id to post to, so the *current* scope
                    // is the route and the area goes in `remove`.
                    const routeId = target || previous;
                    if (!routeId) throw new Error('this area belongs to no scope to remove it from');
                    await api.setScopeAreas(routeId, target ? [actualNodeId] : [],
                        target ? [] : [actualNodeId]);
                    await worldState.fetch();
                    if ((window as unknown as AreaViewWindow).worldSync) (window as unknown as AreaViewWindow).worldSync.refresh();
                    // The name, not the id — the author just picked it from a list
                    // of names, and a raw id in the log reads as "nothing renamed".
                    RV._toast(target
                        ? `Moved into ${nameOf(target)}.`
                        : `Removed from ${nameOf(previous)}.`);
                    VW.inspector.showNode(actualNodeId);
                } catch (e) {
                    RV._toast(`Scope change failed: ${(e as Error)?.message || e}`, true);
                    (ev.target as HTMLSelectElement).value = previous;
                }
            });
        }).catch(() => {
            if (sel.isConnected) sel.innerHTML = '<option value="">scopes unavailable</option>';
        });
    };

    /** Open the WorldPainter on the grid cell this area is parked on (task-539). */
    RV._openInPainter = function(actualNodeId: string, props: NodeProps): void {
        const scopeId = props.world_scope_id;
        if (!scopeId || !(window as unknown as AreaViewWindow).VW || !(window as unknown as AreaViewWindow).VW.worldPainter) return;
        // `open` replaces an open painter itself, so there is nothing to close here.
        (window as unknown as AreaViewWindow).VW.worldPainter.open(scopeId, { tool: 'area', areaId: actualNodeId });
    };

    /** Status line for the scope section (no toast helper is imported here). */
    RV._toast = function(message: string, isError?: boolean): void {
        if ((window as unknown as AreaViewWindow).events && typeof (window as unknown as AreaViewWindow).events.log === 'function') {
            (window as unknown as AreaViewWindow).events.log(message, isError ? 'error' : 'system-msg');
        }
    };

    /**
     * Render a single exit/way entry in the area inspector
     * @param {string} exitName - Exit direction name
     * @param {object} exitData - Exit data object
     * @param {string} actualNodeId - Graph node ID (unused but passed for context)
     * @returns {TemplateResult}
     */
    RV._renderExitItem = function(exitName: string, exitData: AreaViewExitData, actualNodeId: string): TemplateResult {
        const state = exitData.state || 'closed';
        const wayId = exitData.way_id || '';
        let stateIcon: string, stateColor: string;
        if (state === 'open') { stateIcon = '🟢'; stateColor = 'var(--green)'; }
        else if (state === 'closed') { stateIcon = '🟡'; stateColor = 'var(--yellow)'; }
        else if (state === 'locked') { stateIcon = '🔴'; stateColor = 'var(--red)'; }
        else if (state === 'hidden') { stateIcon = '⚫'; stateColor = 'var(--text-muted)'; }
        else if (state === 'blocked') { stateIcon = '⛔'; stateColor = 'var(--orange)'; }
        else if (state === 'broken') { stateIcon = '💥'; stateColor = 'var(--orange)'; }
        else { stateIcon = '❓'; stateColor = 'var(--text-muted)'; }

        const doorNode = wayId ? worldState.getNode(wayId) : null;
        const description = exitData.description || (doorNode?.properties?.description) || '';
        const resolvedDesc = doorNode
            ? InspectorHelpers.resolveWayParams(description, doorNode.properties?.parameters || {})
            : description;
        // task-240: cardinal direction badge (map-layout data) when present.
        const cardinal = exitData.cardinal || '';
        const cardinalBadge = cardinal
            ? htmlTag`<span class="state-badge" style="font-size:9px;background:rgba(88,166,255,0.12);color:#58a6ff;border:1px solid rgba(88,166,255,0.4);padding:1px 6px;border-radius:4px;font-weight:600;" title="Map cardinal: ${cardinal}">🧭 ${cardinal}</span>`
            : (window as unknown as AreaViewWindow).Lit.nothing;
        const badges = typeof WayAuthoring !== 'undefined'
            ? WayAuthoring.collectExitBadges(exitData, doorNode).filter((b: { kind: string }) => b.kind !== 'state')
            : [];
        const badgeRow = typeof WayAuthoring !== 'undefined'
            ? WayAuthoring.renderBadgeRow(badges, wayId)
            : '';
        const movementHint = doorNode && typeof WayAuthoring !== 'undefined'
            ? WayAuthoring.movementHint(doorNode, exitName)
            : '';
        const hasParamPreview = doorNode && /\{param:/.test(description)
            && InspectorHelpers.resolveWayParams(description, doorNode.properties?.parameters || {}) !== description;

        return htmlTag`<div class="exit-item" style="padding:6px 8px;background:var(--bg-inset);border-radius:4px;border-left:3px solid ${stateColor};margin-bottom:4px;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:6px;flex:1;min-width:0;">
                    <span style="flex-shrink:0;">${stateIcon}</span>
<span style="font-weight:600;font-size:12px;">${exitName}</span>
                    <span style="font-size:10px;color:var(--text-muted);">→ ${exitData.target || '?'}${movementHint}</span>
                </div>
                <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
                    ${cardinalBadge}
                    <span class="state-badge" style="font-size:9px;background:${stateColor}22;color:${stateColor};border:1px solid ${stateColor};padding:1px 6px;border-radius:4px;font-weight:600;">${state.toUpperCase()}</span>
                </div>
            </div>
            ${badgeRow ? (window as unknown as AreaViewWindow).Lit.unsafeHTML(badgeRow) : (window as unknown as AreaViewWindow).Lit.nothing}
            ${description ? htmlTag`<div style="font-size:10px;color:var(--text-dim);margin-top:2px;" title="Appearance when closed/locked/blocked">${description}</div>` : (window as unknown as AreaViewWindow).Lit.nothing}
            ${hasParamPreview ? htmlTag`<div style="font-size:10px;color:var(--text-muted);margin-top:2px;">With parameters resolved: ${resolvedDesc}</div>` : (window as unknown as AreaViewWindow).Lit.nothing}
            <div style="display:flex;gap:4px;margin-top:4px;">
                ${wayId ? htmlTag`<button class="btn btn-sm btn-ghost" style="font-size:9px;color:var(--accent);" @click=${() => VW.inspector.showNode(wayId)}>🔍 Inspect Way</button>` : (window as unknown as AreaViewWindow).Lit.nothing}
                <button class="btn btn-sm btn-ghost" style="font-size:9px;color:var(--green);" @click=${() => (window as unknown as AreaViewWindow).toggleDoorState(exitName, 'open', wayId)}>🔓 Open</button>
                <button class="btn btn-sm btn-ghost" style="font-size:9px;color:var(--red);" @click=${() => (window as unknown as AreaViewWindow).toggleDoorState(exitName, 'close', wayId)}>🔒 Close</button>
            </div>
        </div>`;
    };

    /**
     * Update an environment property on a area node
     * @param {string} nodeId - Graph node ID
     * @param {string} key - Environment property key
     * @param {*} value - New value
     */
    RV._updateEnv = function(nodeId: string, key: string, value: unknown): void {
        const node = worldState.getNode(nodeId);
        if (!node) return;
        const env = { ...(node.properties?.environment || {}) };
        env[key] = value;
        api.updateNode(nodeId, { properties: { environment: env } }).then(() => worldState.fetch());
    };

    /**
     * Light accepts both shapes the data uses: a 0-100 number or a preset word.
     * Store a number when the author typed one, otherwise the word.
     * @param {string} nodeId
     * @param {string} raw
     */
    RV._updateEnvLight = function(nodeId: string, raw: string): void {
        const text = String(raw == null ? '' : raw).trim();
        const numeric = text !== '' && !Number.isNaN(Number(text));
        RV._updateEnv(nodeId, 'light', numeric ? Number(text) : (text || 'normal'));
    };

    /**
     * Improve area description and environment via AI
     * @param {string} nodeId - Graph node ID
     */
    RV.improveRoomWithAI = async function(nodeId: string): Promise<void> {
        const system = `You are a procedural area enhancer for a text adventure game. The area data schema supports:

ENVIRONMENT: light (0-100), temperature (C, -50 to 100), air (fresh/stale/humid/toxic/smoky/fragrant), smell (text), noise (quiet/dripping/humming/windy/loud/chaotic/silent)

OUTPUT FORMAT: Respond with ONLY raw JSON. No markdown, no code fences, just JSON.`;

        const buildPrompt = (node: AreaViewGraphNode, lockedFields: string[]) => {
            const name = node.name || '';
            const props = node.properties || {};
            const description = props.description || '';
            const env = props.environment || {};
            return `Area Name: ${name}
Description: ${description}

Current environment:
- light: ${env.light ?? 80}
- temperature: ${Math.round((env.temperature ?? 21) * 10) / 10}
- air: ${env.air || 'fresh'}
- smell: ${env.smell || 'neutral'}
- noise: ${env.noise || 'quiet'}

Improve this area's description and environment settings. Make the description much richer — paint a vivid picture with sensory details (sights, sounds, smells, textures, atmosphere). Suggest appropriate environment values that match the mood. Return the full area as JSON with name, description, and environment fields.`;
        };

        const apply = (parsed: Record<string, any>, node: AreaViewGraphNode, lockedFields: string[], update: Record<string, any>) => {
            const props = node.properties || {};
            const env = props.environment || {};
            if (parsed.name) update.name = parsed.name;
            const propUpdate: Record<string, any> = {};
            if (parsed.description !== undefined) propUpdate.description = parsed.description;
            if (parsed.environment) propUpdate.environment = { ...env, ...parsed.environment };
            if (Object.keys(propUpdate).length > 0) update.properties = propUpdate;
        };

        await InspectorHelpers.improveWithAI(nodeId, { btnId: 'improve-area-btn', id: 'area', system, buildPrompt, apply });
    };

    RV._refreshFromLibrary = async function(nodeId: string): Promise<void> {
        if (!(window as unknown as AreaViewWindow).InspectorTemplateSync) return;
        await (window as unknown as AreaViewWindow).InspectorTemplateSync.refreshFromLibrary('area', nodeId);
    };

    /**
     * Populate this area with fitting furniture/items from the library by its
     * domain tags (task-9). Refreshes world state + the inspector on success.
     * @param {string} nodeId - Area graph node ID
     */
    RV.populateArea = async function(nodeId: string): Promise<void> {
        const btn = document.querySelector(`[data-populate-area="${nodeId}"]`) as HTMLButtonElement | null;
        const original = btn ? btn.textContent : '';
        if (btn) { btn.disabled = true; btn.textContent = 'Populating…'; }
        try {
            const res = await fetch(`/api/populate/area/${encodeURIComponent(nodeId)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });
            const data = await res.json();
            if (!res.ok || data.error) {
                console.warn('Populate failed:', data.error || res.status);
            } else if (data.status === 'empty') {
                console.info('Nothing to place for this area:',
                    (data.unresolved_domains || []).join(', ') || data.notes);
            }
            if ((window as unknown as AreaViewWindow).worldState && typeof worldState.fetch === 'function') {
                await worldState.fetch();
            }
            if ((window as unknown as AreaViewWindow).VW && VW.inspector && typeof VW.inspector.showNode === 'function') {
                VW.inspector.showNode(nodeId);
            }
        } catch (err) {
            console.warn('Populate failed:', err);
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = original || '🪄 Populate'; }
        }
    };

    // Register the template-sync pattern for areas.
    if ((window as unknown as AreaViewWindow).InspectorTemplateSync) {
        (window as unknown as AreaViewWindow).InspectorTemplateSync.register('area', {
            title: 'Refresh Area from Library',
            buildWorldPayload(nodeId: string, node: AreaViewGraphNode | null) {
                const name = (node && node.name) || '';
                if (!name) return null;
                if ((window as unknown as AreaViewWindow).libraryBrowser && libraryBrowserRef()._buildAreaPayload) {
                    return libraryBrowserRef()._buildAreaPayload!(name);
                }
                const props = (node && node.properties) || {};
                return {
                    name,
                    description: props.description || '',
                    tags: props.tags || [],
                    environment: props.environment || {},
                };
            },
            sections: [
                { key: 'description', label: 'Description' },
                { key: 'tags', label: 'Tags' },
                { key: 'environment', label: 'Environment' },
                { key: 'items', label: 'Items' },
                { key: 'exits', label: 'Exits' },
                { key: 'triggers', label: 'Triggers' },
            ],
        });
    }

    return RV;
})();

// ────────────────────────── local types ──────────────────────────
// Declared after the IIFE so the leading JSDoc block stays the first thing in
// the emitted .js and `@module` remains discoverable.

/** The area inspector's public surface. `RV` is populated member by member
 *  below, so the interface is what the assignments are checked against. */
interface AreaViewApi {
    showArea(nodeId: string, graphNode: AreaViewGraphNode): void;
    improveRoomWithAI(nodeId: string): Promise<void>;
    populateArea(nodeId: string): Promise<void>;
    _renderRoomHeader(name: string, actualNodeId: string): TemplateResult;
    _renderDescriptionSection(description: string, actualNodeId: string): TemplateResult;
    _renderEnvironmentSection(env: AreaEnv, actualNodeId: string): TemplateResult;
    _renderEnvPresetRow(env: AreaEnv, actualNodeId: string): TemplateResult;
    _renderFloorSection(props: NodeProps, actualNodeId: string): TemplateResult;
    _renderScopeSection(props: NodeProps, actualNodeId: string): TemplateResult;
    _renderExitItem(exitName: string, exitData: AreaViewExitData, actualNodeId: string): TemplateResult;
    _saveEnvPreset(env: AreaEnv): void;
    _deleteEnvPreset(): void;
    _applyEnvPreset(actualNodeId: string): Promise<void>;
    _fillAreaSounds(el: HTMLElement, areaId: string): void;
    _fillScopeSelect(actualNodeId: string, currentScopeId: string): void;
    _openInPainter(actualNodeId: string, props: NodeProps): void;
    _toast(message: string, isError?: boolean): void;
    _updateEnv(nodeId: string, key: string, value: unknown): void;
    _updateEnvLight(nodeId: string, raw: string): void;
    _refreshFromLibrary(nodeId: string): Promise<void>;
}

/** A graph node as the inspector reads it. */
interface AreaViewGraphNode {
    name?: string;
    type?: string;
    properties?: NodeProps;
    [key: string]: unknown;
}

/** The `environment` sub-object of an area node's properties. */
interface AreaEnv {
    /** 0-100 number in some areas, a preset word in others; both are valid. */
    light?: string | number;
    temperature?: number;
    air?: string;
    smell?: string;
    noise?: string;
    weather?: string;
    wind?: string;
    humidity?: string;
    [key: string]: unknown;
}

/** An area node's `properties` bag, as this view reads it. */
interface NodeProps {
    description?: string;
    environment?: AreaEnv;
    tags?: unknown[];
    locked_fields?: string[];
    aliases?: unknown;
    /** Scope membership. Decides which scope's views list this area. */
    world_scope_id?: string;
    /** Painted-grid placement, which is a separate fact from membership. */
    cell?: { x: number; y: number };
    /** Storey index: 0 ground, 1 up, -1 down, deliberately unbounded. */
    floor?: number;
    /** The ground material the WorldPainter compiler writes. */
    surface?: string;
    [key: string]: unknown;
}

/** One authored way, as the area inspector lists it. */
interface AreaViewExitData {
    state?: string;
    way_id?: string;
    description?: string;
    target?: string;
    /** Map-layout cardinal, distinct from the exit's own name. */
    cardinal?: string;
    [key: string]: unknown;
}

/** One row of the scope select, from GET /api/world/scopes. */
interface ScopeOption {
    id: string;
    name: string;
    /** Depth-first index from flat_scopes, so nesting indents. */
    depth?: number;
}

/** One entry of the area event log. */
interface AreaEvent {
    tick?: number;
    actor?: string;
    action?: string;
    result?: string;
    [key: string]: unknown;
}

/** One active sound source from GET /api/areas/<id>/sounds. */
interface AreaSound {
    name?: string;
    /** 1 nearby, 2 loud, 3 carrying; anything else renders unlabelled. */
    level?: number;
    pattern?: string;
    [key: string]: unknown;
}

/** The two static helpers area-view calls from event-stream.js's EventBus. */
interface EventBusStatics {
    getActionIcon(entry: unknown): string;
    getActionColor(entry: unknown): string;
}

/** shared/env-presets.js. */
interface EnvPresetsApi {
    list(): string[];
    save(name: string, env: unknown): void;
    delete(name: string): void;
    apply(name: string, scope: string, areaId: string): Promise<{ applied: number; areaNames: string[] }>;
}

/** shared/template-sync.js. */
interface AreaViewTemplateSyncApi {
    renderTemplateRow(kind: string, nodeId: string, props: unknown): string;
    populateSelector(kind: string, nodeId: string): void;
    refreshFromLibrary(kind: string, nodeId: string): Promise<unknown>;
    register(kind: string, spec: TemplateSyncSpec): void;
}

/** The registration this view hands the template-sync pattern. */
interface TemplateSyncSpec {
    title: string;
    buildWorldPayload(nodeId: string, node: AreaViewGraphNode | null): unknown;
    sections: Array<{ key: string; label: string }>;
}

/** shared/tag-multiselect.js, as constructed here. */
interface TagMultiselectCtor {
    new (container: HTMLElement, opts: {
        tags: string[];
        appliesTo: string;
        allowNew: boolean;
        placeholder: string;
        onChange: (tags: string[]) => void;
    }): unknown;
}

/** inspector/panel.js, the single owner of the inspector panel. */
interface InspectorPanelApi {
    render(template: unknown): void;
}

/**
 * Everything this view reads off `window`. `InspectorHelpers`,
 * `InspectorTriggers`, `SkyScape`, `Lit`, `VW` and `worldState` are already on
 * the declared surface in globals.d.ts; the rest are not, and are read through
 * this view rather than by editing the shared declaration file.
 */
interface AreaViewWindow {
    Lit: LitApi;
    VW: any;
    worldState: any;
    SkyScape: any;
    events: { log(message: string, level: string): void };
    InspectorHelpers: typeof InspectorHelpers;
    InspectorTriggers: typeof InspectorTriggers;
    InspectorTemplateSync: AreaViewTemplateSyncApi;
    EnvPresets: EnvPresetsApi;
    worldSync: { refresh(): void };
    libraryBrowser: unknown;
    /** Bare globals read directly rather than off window. */
    InspectorPanel: InspectorPanelApi;
    TagMultiselect: TagMultiselectCtor;
    /** main.ts: a function declaration, so it is a window property. */
    toggleDoorState(exitName: string, action: string, wayId?: string): void;
    /** graph-manager.js: a function declaration, so it is a window property. */
    hideInspectorPanel(): void;
}

/** library-browser.js, as the area view uses it. */
interface LibraryBrowserApi {
    _buildAreaPayload?(name: string): unknown;
    saveAreaByName(name: string): void;
}
