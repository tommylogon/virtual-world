/**
 * InspectorAgentView — Full agent inspector (showAgent + all agent-related methods)
 *
 * @module inspector/agent-view — the full character inspector
 * @contributes InspectorAgentView: Inventory/Bio/Images/Advanced tabs, paperdoll, traits, relationships, memories
 * @powers clicking a character to inspect and edit them, their timeline, and export
 * @relates uses inspector/helpers + paperdoll-view + memory-view + behaviors-view
 * @docs docs/virtualWorld/UI & Settings/Inspector Panels.md
 * Extracted from inspector.js for modularity.
 * Tabs: Inventory (paperdoll on top + gear below), Bio (personality, appearance,
 * stats/skills/traits, interest + fear tags, relationships, memories), Images
 * (Expression Pack + sheet splitter), Advanced (graph physics, behaviors,
 * timeline, save/export).
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

/**
 * Collaborators reached as bare globals or through `window` that are not in
 * globals.d.ts. Declared locally (or cast locally) so this file does not reach
 * into the shared ambient declaration that other lanes are editing.
 */
declare const ui: { getAgentColor(name: string): string; [key: string]: any };
declare const TagMultiselect: new (el: HTMLElement, opts: Record<string, any>) => unknown;
declare function reinitChoices(el: Element): void;
declare function runAction(command: string, charName: string): void;
declare function toastSuccess(message: string): void;
declare function toastWarning(message: string): void;
declare const agent: { getDisplayHistory(agentName: string): any[]; [key: string]: any };
declare const AIGenerator: { isConfigured(): boolean; [key: string]: any };
type AVWin = { [key: string]: any };

(window as unknown as AVWin).InspectorAgentView = (() => {
    const AV: Record<string, any> = {};

    // Lazy tag for the PICKERS/OVERLAYS only (trait option, condition editor,
    // timeline detail, add-item/container pickers). The main agent template and
    // its deferred gravity/alias helpers stay as STRINGS via unsafeHTML (the
    // documented HEAD design) — never mix this tag into those string builds.
    const agentViewTag = (strings: TemplateStringsArray, ...values: any[]) => window.Lit.html(strings, ...values);

    // ─── Internal state ───
    let _activeTab = 'Bio';

    // Deferred renders: agent-view builds one big HTML string, so helpers that
    // return lit TemplateResults (graphGravityControl, renderAliasesSection)
    // get rendered into placeholder containers AFTER the panel render runs.
    let _deferredRenders: Array<() => void> = [];
    const _deferRender = (renderFn: () => void) => {
        _deferredRenders.push(renderFn);
    };
    const _runDeferredRenders = () => {
        const pending = _deferredRenders;
        _deferredRenders = [];
        pending.forEach(renderFn => {
            try { renderFn(); } catch (error) { console.error('[agent-view] deferred render failed:', error); }
        });
    };

    // ─── Constants ───
    const EMOTION_ICONS: Record<string, string> = { happy: '😊', sad: '😢', angry: '😠', afraid: '😨', surprised: '😲', disgusted: '🤢', neutral: '😐' };
    const STAT_LABELS = { STR: '\u{1F4AA} Strength', DEX: '\u{1F938} Dexterity', CON: '\u{1F6E1}\uFE0F Constitution', INT: '\u{1F9E0} Intelligence', WIS: '\u{1F441}\uFE0F Wisdom', CHA: '\u{1F4AC} Charisma' };
    const SKILL_LIST = ['Athletics', 'Acrobatics', 'Stealth', 'Perception', 'Investigation', 'Survival', 'Persuasion', 'Performance', 'Medicine', 'Arcana', 'Intimidation', 'Lockpicking'];
    const TABS = ['Inventory', 'Bio', 'Images', 'Advanced'];

    /**
     * HTML-escape double quotes for attribute safety
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    const esc = InspectorHelpers.esc;

    /**
     * Render the full agent inspector panel
     * @param {string} agentName - Character name
     */
    AV.showAgent = function(agentName: string) {
        const panel = document.getElementById('inspector-panel');
        if (!panel || !worldState.data) return;

        // Set current view on the Inspector singleton so _reRender() works
        if (window.VW?.inspector) {
            window.VW.inspector._currentView = { type: 'agent', name: agentName };
        }
        if ((window as unknown as AVWin).appEvents) (appEvents as Record<string, any>).emit('inspector:view', { type: 'agent', name: agentName });

        const player = worldState.players[agentName];
        if (!player) return;

        const color = ui.getAgentColor(agentName);
        const area = worldState.areas?.[player.current_area];
        const charState = events.getCharacterState(agentName);
        const isAuto = events.isAutonomous(agentName);
        const escName = agentName.replace(/'/g, "\\'");
        const characterNode = Object.entries(worldState.graph?.nodes || {} as Record<string, any>)
            .find(([, node]: [string, any]) => node.type === 'character' && node.name === agentName);

        let html = AV._renderAgentHeader(agentName, player, color, characterNode);
        html += AV._renderStatusRow(agentName, player, color, isAuto, escName);
        html += AV._renderEmotionSelector(agentName, player, escName);
        html += AV._renderVitals(player, agentName);

        // Tab navigation
        html += AV._renderTabNav(escName);

        // Inventory tab (paperdoll on top, inventory below)
        html += AV._renderInventoryTab(agentName, player, escName);

        // Bio tab (personality, appearance, stats/skills/traits, relationships, memories)
        html += AV._renderBioTab(agentName, player, charState, area, escName, isAuto, color);

        // Images tab (Expression Pack + sheet splitter) — task-512: art lives on
        // its own tab so the overview stays about who the character is.
        html += AV._renderImagesTab(agentName, player, characterNode);

        // Advanced tab (behaviors, timeline, save/export)
        html += AV._renderAdvancedTab(agentName, player, charState, escName, isAuto, characterNode);

        // The whole agent view is one big string template with inline onclick
        // handlers. Render it through InspectorPanel (single panel owner) inside
        // an unsafeHTML marker so lit never tries to diff against string content
        // and its part tracking stays intact across re-renders.
        const htmlTag = (strings: TemplateStringsArray, ...values: any[]) => window.Lit.html(strings, ...values);
        (window as unknown as AVWin).InspectorPanel.render(htmlTag`${window.Lit.unsafeHTML(html)}`);

        // Known-by authoring: who knows THIS character (the Knowledge modal
        // for what they know lives in the Advanced tab). Render into a slot
        // inside the Advanced tab so it only shows when that tab is active.
        const avWin = window as unknown as AVWin;
        if (avWin.KnownBySection) {
            const slot = document.getElementById('known-by-slot');
            if (slot) {
                slot.innerHTML = '';
                slot.appendChild(avWin.KnownBySection.build('character', player.name, player.name));
            }
        }

        // Render lit-helper TemplateResults (gravity control, aliases) that
        // couldn't be embedded in the string into their placeholder containers.
        _runDeferredRenders();

        if (avWin.InspectorTemplateSync && characterNode && characterNode[0]) {
            avWin.InspectorTemplateSync.populateSelector('character', characterNode[0]);
        }

        // Initialize TagMultiselect for character tags
        const tagContainer = document.getElementById(`tag-multiselect-agent-${escName}`);
        if (tagContainer && typeof TagMultiselect !== 'undefined') {
            new TagMultiselect(tagContainer, {
                tags: Array.isArray(player.tags) ? player.tags : [],
                appliesTo: 'characters',
                allowNew: true,
                placeholder: 'Search or create tags...',
                onChange: (newTags: any[]) => {
                    ApiClient.updateCharacter(agentName, { tags: newTags }).then(() => worldState.fetch());
                }
            });
        }

        // Initialize TagMultiselect for interest tags
        const interestTagContainer = document.getElementById(`interest-tag-multiselect-agent-${escName}`);
        if (interestTagContainer && typeof TagMultiselect !== 'undefined') {
            new TagMultiselect(interestTagContainer, {
                tags: Array.isArray(player.interest_tags) ? player.interest_tags : [],
                appliesTo: 'characters',
                allowNew: true,
                placeholder: 'e.g. magic, food, documents...',
                onChange: (newTags: any[]) => {
                    ApiClient.updateCharacter(agentName, { interest_tags: newTags }).then(() => worldState.fetch());
                }
            });
        }

        // Initialize TagMultiselect for fear tags
        const fearTagContainer = document.getElementById(`fear-tag-multiselect-agent-${escName}`);
        if (fearTagContainer && typeof TagMultiselect !== 'undefined') {
            new TagMultiselect(fearTagContainer, {
                tags: Array.isArray(player.fear_tags) ? player.fear_tags : [],
                appliesTo: 'characters',
                allowNew: true,
                placeholder: 'e.g. goblin, the dark, magic...',
                onChange: (newTags: any[]) => {
                    ApiClient.updateCharacter(agentName, { fear_tags: newTags }).then(() => worldState.fetch());
                }
            });
        }

        // Initialize Tippy tooltips
        if (typeof tippy !== 'undefined') {
            try {
                // Multi-line tips (vital hover) need pre-line whitespace —
                // tippy renders content as text, so a bare \n collapses.
                if (!document.getElementById('tippy-preline-style')) {
                    const st = document.createElement('style');
                    st.id = 'tippy-preline-style';
                    st.textContent = '[data-tippy-root] .tippy-content { white-space: pre-line; }';
                    document.head.appendChild(st);
                }
                tippy('[data-tippy-content]', { placement: 'top', arrow: true, animation: 'shift-away', duration: [200, 150], maxWidth: 250 });
            } catch (error) {}
        }
        reinitChoices(panel);

        // Relationship slider events
        AV._bindRelationshipSliders(panel, agentName);

        // Populate trait dropdown from library
        AV._populateTraitDropdown(escName);
    };

    /**
     * Render the graph physics gravity control into a placeholder container.
     * graphGravityControl returns a lit TemplateResult (not a string), so it
     * can't be string-concatenated into the agent view HTML. We defer the lit
     * render until after the panel render and inject it into a placeholder div.
     * Lives inside the Advanced tab pane; the pane is hidden with display:none
     * rather than removed, so the deferred render still finds its container.
     * @param {string} nodeId - Graph node ID
     * @param {object} props - Node properties
     * @returns {string} Placeholder HTML (filled in by _runDeferredRenders)
     */
    AV._deferredGravityControl = function(nodeId: string, props: Record<string, any> = {}) {
        const cleanId = String(nodeId ?? 'node').replace(/[^a-zA-Z0-9_-]/g, '_');
        const containerId = `agent-gravity-${cleanId}`;
        _deferRender(() => {
            const container = document.getElementById(containerId);
            if (container && window.Lit) {
                window.Lit.render((window as unknown as AVWin).InspectorHelpers.graphGravityControl(nodeId, props), container);
            }
        });
        return `<div id="${containerId}"></div>`;
    };

    /**
     * Render the aliases section into a placeholder container (lit TemplateResult
     * can't be string-concatenated into the agent view HTML).
     * @param {string} nodeId - Graph node ID
     * @param {Array|string} aliases - Current aliases
     * @returns {string} Placeholder HTML (filled in by _runDeferredRenders)
     */
    AV._deferredAliasesSection = function(nodeId: string, aliases: any = []) {
        const cleanId = String(nodeId ?? 'node').replace(/[^a-zA-Z0-9_-]/g, '_');
        const containerId = `agent-aliases-${cleanId}`;
        _deferRender(() => {
            const container = document.getElementById(containerId);
            if (container && window.Lit) {
                window.Lit.render((window as unknown as AVWin).InspectorHelpers.renderAliasesSection(nodeId, aliases), container);
            }
        });
        return `<div id="${containerId}"></div>`;
    };

    AV._populateTraitDropdown = async function(escName: string) {
        const sel = document.getElementById(`trait-add-select-${escName}`);
        if (!sel) return;
        try {
            // Session cache (60s): the inspector re-renders on every state
            // update and this dropdown is rebuilt each time.
            let traits = (window as unknown as AVWin)._traitLibrary;
            if (!traits || Date.now() - ((window as unknown as AVWin)._traitLibraryAt || 0) > 60000) {
                traits = await (ApiClient as Record<string, any>).getLibraryType('traits');
                (window as unknown as AVWin)._traitLibrary = traits;
                (window as unknown as AVWin)._traitLibraryAt = Date.now();
            }
            const current = worldState.players?.[escName === escName.replace(/'/g, "\\'") ? escName.replace(/\\'/g, "'") : escName]?.traits || {};
            // Preserve placeholder
            window.Lit.render(agentViewTag`<option value="">➕ Add trait...</option>`, sel);
            for (const [id, def] of Object.entries(traits as Record<string, any>)) {
                if (current[id] !== undefined) continue;
                const name = def.name || id;
                const cat = def.category || '';
                const opt = document.createElement('option');
                opt.value = id;
                opt.textContent = `${name}${cat ? ` (${cat})` : ''}`;
                sel.appendChild(opt);
            }
        } catch (e) {}
    };

    // ═══════════════════════════════════════════════
    //  Header / Status / Emotion / Vitals helpers
    // ═══════════════════════════════════════════════

    /**
     * Render the agent inspector header (badge, name, close button)
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {string} color - Agent color
     * @param {Array|null} characterNode - [nodeId, node] pair or null
     * @returns {string} HTML
     */
    AV._renderAgentHeader = function(agentName: string, player: any, color: string, characterNode: [string, any] | null) {
        const tick = worldState.tick;
        const nodeId = characterNode ? characterNode[0] : '';
        const escapedNodeId = nodeId.replace(/'/g, "\\'");
        return `<div class="inspector-header">
            <span class="inspector-type-badge" style="background:${color}">🧍 Agent</span>
            <div style="flex:1;display:flex;flex-direction:column;">
                <h2 style="margin:0;font-size:16px;"><input type="text" value="${agentName}" onchange="ApiClient.updateCharacter('${agentName.replace(/'/g, "\\'")}',{name:this.value}).then(()=>worldState.fetch())" style="font-size:1em;background:transparent;border:1px solid var(--border);color:inherit;width:100%;"></h2>
                ${nodeId ? ((window as unknown as AVWin).InspectorHelpers.isGeneratedNode(nodeId)
                    ? `<div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                    <div style="display:flex;gap:2px;align-items:center;">
                        <span style="font-size:10px;color:var(--text-muted);flex:1;min-width:0;" title="Generated node id — owned by the world compiler; it is regenerated on recompile and cannot be renamed">${escapedNodeId}</span>
                    </div>
                </div>`
                    : `<div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                    <div style="display:flex;gap:2px;align-items:center;">
                        <input type="text" value="${escapedNodeId}" onchange="(window as unknown as AVWin).InspectorHelpers.renameNode('${escapedNodeId}',this.value)" style="font-size:10px;padding:1px 4px;background:transparent;border:1px solid transparent;color:var(--text-muted);flex:1;min-width:0;cursor:text;" title="Change node ID (lowercase, no spaces)">
                        <button class="btn btn-sm btn-ghost" onclick="InspectorHelpers.syncIdFromName('${escapedNodeId}','${agentName}')" title="Sync ID from name">🔄</button>
                    </div>
                </div>`) : ''}
            </div>
            <span style="font-size:10px;color:var(--text-muted);margin-right:6px;">tick ${tick}</span>
            <button class="btn btn-sm btn-ghost" onclick="hideInspectorPanel()">✕</button>
        </div>`;
    };

    /**
     * Render the status row (area selector, state selector, control-mode button)
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {string} color - Agent color
     * @param {boolean} isAuto - Whether autonomous
     * @param {string} escName - HTML-escaped name
     * @returns {string} HTML
     */
    AV._renderStatusRow = function(agentName: string, player: any, color: string, isAuto: boolean, escName: string) {
        const roomOptions = Object.keys(worldState.areas || {}).map(areaName =>
            `<option value="${areaName}" ${player.current_area === areaName ? 'selected' : ''}>${areaName}</option>`
        ).join('');
        // stacked instance (4 vials of poison = 4 cards under `poisoned`).
        const condColors: Record<string, string> = {
            dead: 'var(--red)', unconscious: '#e65100', paralysed: '#555',
            stunned: '#ab47bc', prone: '#8d6e63', busy: '#9e9d24',
            grappled: '#d50000', restrained: '#b71c1c', exhausted: '#ff6f00',
            sick: '#ff6f00', poisoned: '#00c853', blind: '#37474f', deaf: '#455a64',
            mute: '#546e7a', frightened: '#7b1fa2', charmed: '#f06292', awake: 'var(--green)'
        };
        const conds = (player.conditions && typeof player.conditions === 'object' && !Array.isArray(player.conditions)) ? player.conditions : {};
        // The state badge duplicates the interactive condition chip when the
        // state IS a listed condition (e.g. "grappled") — show the chip only.
        const stateHasChip = Array.isArray(conds[player.state]) && conds[player.state].length > 0;
        const condBadges = Object.entries(conds).map(([cid, instances]) => {
            if (!Array.isArray(instances) || instances.length === 0) return '';
            const color = condColors[cid] || '#888';
            const label = `${cid}${instances.length > 1 ? ' ×' + instances.length : ''}`;
            const cards = instances.map(inst => {
                const bits = [];
                if (inst.source) bits.push(`why: <b>${inst.source}</b>`);
                bits.push(inst.duration ? `left: <b>${inst.duration}t</b>` : '<b>permanent</b>');
                if (inst.level) bits.push(`lvl <b>${inst.level}</b>`);
                if (inst.periodic && Object.keys(inst.periodic).length) {
                    bits.push(`per tick: <b>${Object.entries(inst.periodic as Record<string, number>).map(([k, v]) => `${k} ${v > 0 ? '+' : ''}${v}`).join(', ')}</b>`);
                }
                if (inst.ends_on && inst.ends_on.length) bits.push(`ends on: <b>${inst.ends_on.join(', ')}</b>`);
                return `<div style="padding:2px 4px;border-left:2px solid ${color};color:var(--text-dim);display:flex;gap:8px;flex-wrap:wrap;font-size:10px;">${bits.join(' ')}</div>`;
            }).join('');
            return `<span style="position:relative;display:inline-block;font-size:9px;padding:1px 5px;border-radius:3px;background:${color}22;color:${color};border:1px solid ${color};cursor:pointer;" onclick="const pop=this.querySelector('.cond-pop'); pop.style.display = pop.style.display==='block'?'none':'block';">${label} ▾<div class="cond-pop" style="display:none;position:absolute;top:100%;left:0;z-index:99;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;padding:4px;min-width:220px;box-shadow:0 4px 12px rgba(0,0,0,0.4);">${cards}<div style="border-top:1px solid var(--border);margin-top:4px;padding-top:3px;"><span style="cursor:pointer;color:var(--red);font-size:10px;" onclick="event.stopPropagation();InspectorAgentView._removeCondition('${escName}','${cid}')">✕ Clear ${cid}</span></div></div></span>`;
        }).join(' ');

        // Control mode: npc | human | llm
        const mode = events.getControlMode(agentName);
        const modeMeta = ({
            human: { label: '👤 Human', bg: 'var(--accent)', fg: '#000', bd: 'var(--accent-dim)' },
            llm:   { label: '🤖 LLM',   bg: 'var(--bg-input)', fg: 'var(--text)', bd: 'var(--border)' },
            npc:   { label: '👾 NPC',   bg: 'var(--bg-input)', fg: 'var(--text-muted)', bd: 'var(--border)' }
        } as Record<string, any>)[mode];
        return `<div style="display:flex;align-items:center;gap:8px;padding:6px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);font-size:11px;flex-wrap:wrap;">
            <span>📍</span>
            <select id="player-room" name="area" onchange="ApiClient.updateCharacter('${escName}',{current_area:this.value}).then(()=>worldState.fetch())" style="font-size:10px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:1px 4px;max-width:100px;">
                ${roomOptions}
            </select>
            ${stateHasChip ? '' : `<span title="Most significant condition (derived from conditions)" style="font-size:10px;background:${player.state === 'dead' ? 'var(--red)' : 'var(--accent-dim)'};color:${player.state === 'dead' ? '#fff' : '#000'};border-radius:4px;padding:2px 8px;font-weight:600;border:1px solid var(--border);">${player.state}</span>`}
            ${condBadges}
            <button class="btn btn-sm" onclick="InspectorAgentView._openConditionEditor('${escName}')" title="Add a specific condition (blind, poisoned, unconscious...) with a duration, source, or level" style="font-size:10px;">➕ Add Condition</button>
            <span style="flex:1;"></span>
            <span onclick="events.cycleControlMode('${escName}')" title="Click to cycle control mode: Human → LLM → NPC" style="cursor:pointer;padding:2px 8px;border-radius:4px;font-weight:600;font-size:10px;background:${modeMeta.bg};color:${modeMeta.fg};border:1px solid ${modeMeta.bd};">${modeMeta.label}</span>
        </div>`;
    };

    /**
     * Render the emotion selector row
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {string} escName - HTML-escaped name
     * @returns {string} HTML
     */
    AV._renderEmotionSelector = function(agentName: string, player: any, escName: string) {
        const emotion = player.emotion || { current: 'neutral', intensity: 0 };
        const emotionOptions = Object.keys(EMOTION_ICONS).map(emotionName =>
            `<option value="${emotionName}" ${emotion.current === emotionName ? 'selected' : ''}>${EMOTION_ICONS[emotionName]} ${emotionName}</option>`
        ).join('');

        return `<div style="display:flex;align-items:center;gap:8px;padding:6px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);font-size:11px;flex-wrap:wrap;">
            <span style="font-size:13px;">${EMOTION_ICONS[emotion.current] || '😐'}</span>
            <select id="player-emotion" name="emotion" onchange="ApiClient.updateCharacter('${escName}',{emotion:{current:this.value,intensity:parseFloat(document.getElementById('emotion-intensity-${escName}').value)||0}}).then(()=>worldState.fetch())" style="font-size:10px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:1px 4px;">
                ${emotionOptions}
            </select>
            <span style="font-size:10px;color:var(--text-dim);">intensity</span>
            <input type="range" id="emotion-intensity-${escName}" min="0" max="1" step="0.05" value="${emotion.intensity || 0}" style="width:60px;" oninput="document.getElementById('emotion-val-${escName}').textContent=parseFloat(this.value).toFixed(2);ApiClient.updateCharacter('${escName}',{emotion:{current:'${emotion.current}',intensity:parseFloat(this.value)}}).then(()=>worldState.fetch())">
            <span id="emotion-val-${escName}" style="min-width:30px;font-size:10px;color:var(--text-dim);">${(emotion.intensity || 0).toFixed(2)}</span>
            ${emotion.description ? `<span style="font-size:10px;color:var(--text-muted);font-style:italic;">${emotion.description}</span>` : ''}
        </div>`;
    };

    /**
     * Polarity-aware vital bar color — shared implementation
     * (static/js/shared/vital-color.js, task-337/342).
     */
    function vitalBarColor(vitalName: string, value: number) {
        return (window as unknown as AVWin).VitalColor.bar({ [vitalName]: value }, vitalName);
    }

    /**
     * Render vitals grouped into Physical and Mental
     * @param {object} player - Player data
     * @returns {string} HTML
     */
    AV._renderVitals = function(player: any, agentName: string) {
        const vitals = player.vitals || {};
        const escAgent = (agentName || '').replace(/'/g, "\\'");
        const openModal = (vn: string) => `openVitalModal('${escAgent}','${vn}')`;

        const renderVital = (vitalName: string) => {
            if (vitals[vitalName] === undefined) return '';
            const value = vitalName === 'Temperature' ? Math.round(vitals[vitalName]) : vitals[vitalName];
            const max = vitalName === 'HP' ? (vitals.Max_HP || 100) : (vitalName === 'Temperature' ? 45 : (vitalName === 'Mana' ? (vitals.Max_Mana || 100) : 100));
            const percentage = vitalName === 'Temperature'
                ? Math.max(0, Math.min(100, ((vitals[vitalName] - 25) / 20) * 100))
                : Math.max(0, Math.min(100, (value / max) * 100));
            const barColor = vitalBarColor(vitalName, vitals[vitalName]);
            const suffix = vitalName === 'Temperature' ? '°C' : '';
            // Quiet vitals: color is reserved for problems (VitalColor.level),
            // so healthy bars dim back and the troubled one pops.
            const lvl = (window as unknown as AVWin).VitalColor?.level?.(vitals, vitalName) || 'ok';
            const quiet = lvl === 'ok' ? 'opacity:0.6;' : '';
            // Full hover: value + what the vital does + human natural language
            // (task-129). VitalThresholds.hoverText falls back to the raw
            // number line when unavailable.
            const tipText = ((window as unknown as AVWin).VitalThresholds?.hoverText?.(vitals, vitalName))
                || `${vitalName}: ${value}/${max}${suffix}`;
            return `<div style="flex:1;min-width:60px;text-align:center;cursor:pointer;${quiet}" data-tippy-content="${tipText}" onclick="${openModal(vitalName)}">
                <div style="font-size:9px;text-transform:uppercase;">${vitalName}</div>
                <div style="height:4px;background:var(--bg-input);border-radius:2px;margin:2px 0;overflow:hidden;"><div style="height:100%;width:${percentage}%;background:${barColor};border-radius:2px;"></div></div>
                <div style="font-size:10px;">${value}${suffix}</div>
            </div>`;
        };

        const physicalVitals = ['HP', 'Energy', 'Hunger', 'Thirst', 'Bladder', 'Temperature'];
        const mentalVitals = ['Sanity', 'Social', 'Entertainment', 'Hygiene'];
        const manaGroup = vitals.Mana !== undefined
            ? `<div style="margin-top:4px;padding-top:4px;border-top:1px solid var(--border);">
                <div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;margin-bottom:2px;">Arcane</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${renderVital('Mana')}</div>
              </div>`
            : '';

        // task-605: size is a first-class character property, so it belongs in the
    // form next to the vitals rather than hidden in a `size_*` trait key. Two
    // things already read it -- way `max_size` passage gating and per-area
    // occupancy (task-653) -- and neither is discoverable from the UI today.
    // An empty selection means "not authored": the engine falls through to a
    // `size_*` trait if one exists, else to `normal`.
    const SIZE_TIERS = ['tiny', 'small', 'normal', 'huge', 'giant', 'titanic'];
    const currentSize = String((player && player.size) || '').trim().toLowerCase();
    const sizeOptions = SIZE_TIERS.map(function (t) {
        return '<option value="' + t + '"'
            + (t === currentSize ? ' selected' : '') + '>' + t + '</option>';
    }).join('');
    const sizeTip = 'Size: which of the six tiers this character is.'
        + '\n\n'
        + 'Way max_size gates compare against it, so a tight tunnel blocks anything bigger.'
        + '\n'
        + 'Per-area occupancy sums it, so a titanic creature needs a big area.'
        + '\n\n'
        + 'Blank falls back to a size_* trait if one exists, otherwise normal.';
    const sizeGroup = `<div style="margin-top:4px;padding-top:4px;border-top:1px solid var(--border);display:flex;align-items:center;gap:6px;">
      <div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;">Size</div>
      <select id="agent-size-select" style="flex:1;font-size:11px;padding:2px 4px;background:var(--bg-input);color:inherit;border:1px solid var(--border);border-radius:4px;"
        onchange="ApiClient.updateCharacter('${escAgent}', { size: this.value || null }).then(() => worldState.fetch())"
        data-tippy-content="${sizeTip}">
        <option value=""${currentSize ? '' : ' selected'}>&#8212; not set &#8212;</option>
        ${sizeOptions}
      </select>
    </div>`;
    return `<div style="padding:8px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);">
            <div style="display:flex;gap:12px;">
                <div style="flex:1;"><div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;margin-bottom:2px;">Physical</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${physicalVitals.map(renderVital).join('')}</div></div>
                <div style="flex:1;"><div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;margin-bottom:2px;">Mental</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${mentalVitals.map(renderVital).join('')}</div></div>
            </div>
            ${manaGroup}
    ${sizeGroup}
        </div>`;
    };

    // ═══════════════════════════════════════════════
    //  Tab navigation
    // ═══════════════════════════════════════════════

    /**
     * Render tab navigation bar
     * @param {string} escName - HTML-escaped name (unused but kept for consistency)
     * @returns {string} HTML
     */
    AV._renderTabNav = function() {
        return `<div class="inspector-tabs" style="display:flex;border-bottom:2px solid var(--border);background:var(--bg-card);padding:0 8px;gap:2px;">
            ${TABS.map(tabName => `<div class="inspector-tab" data-tab-btn="${tabName}" onclick="InspectorAgentView._switchAgentTab('${tabName}')" style="padding:6px 12px;font-size:11px;cursor:pointer;border-bottom:2px solid ${_activeTab === tabName ? 'var(--accent)' : 'transparent'};color:${_activeTab === tabName ? 'var(--accent)' : 'var(--text-dim)'};font-weight:${_activeTab === tabName ? '600' : '400'};">${tabName}</div>`).join('')}
        </div>`;
    };

    /**
     * Switch active tab and re-render
     * @param {string} tabName - Tab name to switch to
     */
    AV._switchAgentTab = function(tabName: string) {
        _activeTab = tabName;
        document.querySelectorAll<HTMLElement>('.inspector-tab').forEach(el => {
            const on = el.dataset.tabBtn === tabName;
            el.style.borderBottomColor = on ? 'var(--accent)' : 'transparent';
            el.style.color = on ? 'var(--accent)' : 'var(--text-dim)';
            el.style.fontWeight = on ? '600' : '400';
        });
        document.querySelectorAll<HTMLElement>('#inspector-panel [data-tab]').forEach(el => {
            el.style.display = el.dataset.tab === tabName ? '' : 'none';
        });
    };

    // ═══════════════════════════════════════════════
    //  Tab content renderers
    // ═══════════════════════════════════════════════

    /**
     * Render the Stats / Skills / Traits blocks (used inside the Bio tab)
     * @param {object} player - Player data
     * @param {string} escName - HTML-escaped name
     * @returns {string} HTML
     */
    AV._renderStatsBlocks = function(player: any, escName: string) {
        let html = '';

        // Stats grid
        const stats = player.stats || {};
        html += `<div class="inspector-section"><h3>\u{1F4CA} Stats</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">`;
        for (const [statKey, statLabel] of Object.entries(STAT_LABELS)) {
            const value = stats[statKey] ?? 10;
            html += `<div style="display:flex;align-items:center;gap:4px;background:var(--bg-inset);border-radius:4px;padding:4px 8px;">
                <span style="font-size:10px;flex:1;">${statLabel}</span>
                <input type="number" min="1" max="20" value="${value}" name="stat-${statKey}" style="width:48px;font-size:11px;text-align:center;"
                    onchange="var s=Object.assign({},worldState.players['${escName}']?.stats||{});s['${statKey}']=parseInt(this.value)||10;ApiClient.updateCharacter('${escName}',{stats:s}).then(()=>worldState.fetch())">
            </div>`;
        }
        html += `</div></div>`;

        // Skills
        const skills = player.skills || {};
        html += `<div class="inspector-section"><h3>\u{1F3AF} Skills</h3>
            <div id="skills-list-${escName}" style="display:flex;flex-direction:column;gap:3px;margin-bottom:6px;">`;
        if (Object.keys(skills).length > 0) {
            for (const [skillName, skillRank] of Object.entries(skills)) {
                html += `<div style="display:flex;align-items:center;gap:4px;background:var(--bg-inset);border-radius:4px;padding:3px 8px;">
                    <span style="font-size:11px;flex:1;">${skillName}</span>
                    <input type="number" min="-20" max="20" value="${skillRank}" name="skill-${skillName}" style="width:48px;font-size:11px;text-align:center;"
                        onchange="var s=Object.assign({},worldState.players['${escName}']?.skills||{});s['${skillName}']=parseInt(this.value)||0;ApiClient.updateCharacter('${escName}',{skills:s}).then(()=>worldState.fetch())">
                    <span onclick="var s=Object.assign({},worldState.players['${escName}']?.skills||{});delete s['${skillName}'];ApiClient.updateCharacter('${escName}',{skills:s}).then(()=>worldState.fetch());VW.inspector._reRender();" style="cursor:pointer;color:var(--red);font-size:12px;padding:2px;">\u2715</span>
                </div>`;
            }
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">No skills yet. Add one below.</div>`;
        }
        html += `</div>
            <div style="display:flex;gap:4px;">
                <select id="skill-add-select-${escName}" style="flex:1;font-size:11px;padding:2px 4px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">
                    ${SKILL_LIST.map(skillName => `<option value="${skillName}">${skillName}</option>`).join('')}
                </select>
                <button class="btn btn-sm btn-blue" onclick="var sel=document.getElementById('skill-add-select-${escName}');var skill=sel.value;var s=Object.assign({},worldState.players['${escName}']?.skills||{});if(!s[skill]){s[skill]=1;ApiClient.updateCharacter('${escName}',{skills:s}).then(()=>{worldState.fetch();VW.inspector._reRender();});}" style="font-size:10px;">\u2795 Add</button>
            </div>`;
        html += `</div>`;  // End skills section
        // Traits
        const traits = player.traits || {};
        html += `<div class="inspector-section"><h3>\u{1F9E0} Traits</h3>`;
        const traitKeys = Object.keys(traits);
        if (traitKeys.length > 0) {
            html += `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">`;
            for (const [traitId, traitVal] of Object.entries(traits)) {
                const displayVal = traitVal === true ? '' : `: ${traitVal}`;
                const chipDef = (window as unknown as AVWin)._traitLibrary?.[traitId] || {};
                const tip = [chipDef.behavior_prompt, chipDef.description,
                             chipDef.conflicts ? 'Conflicts: ' + chipDef.conflicts.join(', ') : '']
                            .filter(Boolean).join(' — ');
                html += `<span title="${tip}" style="display:inline-flex;align-items:center;gap:3px;font-size:10px;padding:2px 8px;border-radius:4px;background:rgba(188,140,255,0.15);color:#bc8cff;border:1px solid rgba(188,140,255,0.3);cursor:help;">
                    ${traitId}${displayVal}
                    <span onclick="var t=Object.assign({},worldState.players['${escName}']?.traits||{});delete t['${traitId}'];ApiClient.updateCharacter('${escName}',{traits:t}).then(()=>{worldState.fetch();VW.inspector._reRender();});" style="cursor:pointer;color:var(--red);margin-left:2px;font-size:12px;">\u2715</span>
                </span>`;
            }
            html += `</div>`;
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">No traits assigned.</div>`;
        }
        html += `<div style="display:flex;gap:4px;">
            <select id="trait-add-select-${escName}" style="flex:1;font-size:11px;padding:2px 4px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">
                <option value="">\u2795 Add trait...</option>
            </select>
            <button class="btn btn-sm btn-blue" onclick="InspectorAgentView._addTrait('${escName}')" style="font-size:10px;">Add</button>
        </div></div>`;

        return html;
    };

    AV._addTrait = async function(charName: string) {
        const sel = document.getElementById(`trait-add-select-${charName}`) as HTMLSelectElement | null;
        if (!sel || !sel.value) return;
        const traitId = sel.value;
        const isParametric = (window as unknown as AVWin)._traitLibrary?.[traitId]?.params;
        let value: any = true;
        if (isParametric) {
            const input = prompt(`Enter value for "${traitId}" trait:`, isParametric.default || '');
            if (input === null) return;
            value = input.trim() || true;
        }
        const t = Object.assign({}, worldState.players?.[charName]?.traits || {});
        t[traitId] = value;
        await ApiClient.updateCharacter(charName, { traits: t });
        worldState.fetch();
        VW.inspector._reRender();
    };

    /**
     * Remove a condition instance from a character via the backend.
     * @param {string} charName - Character name
     * @param {string} conditionId - Condition id to clear (e.g. "grappled")
     */
    AV._removeCondition = async function(charName: string, conditionId: string) {
        await ApiClient.updateCharacter(charName, { remove_condition: conditionId });
        worldState.fetch();
        if (VW?.inspector) VW.inspector._reRender();
        events.log(`Cleared "${conditionId}" from ${charName}`, 'system-msg');
    };

    // Cached status-condition catalog (from /api/conditions).
    AV._conditionCatalog = null;

    /**
     * Open the condition editor modal for a character, mirroring the trigger
     * editor flow. Lets the user add a specific condition (blind, poisoned,
     * unconscious, paralysed...) with a duration, source, level, ends-on, and
     * optional advanced periodic/override settings.
     * @param {string} charName - Character name
     */
    AV._openConditionEditor = async function(charName: string) {
        if (!AV._conditionCatalog) {
            try {
                const res = await (ApiClient as Record<string, any>).conditionsCatalog();
                AV._conditionCatalog = (res && res.conditions) || [];
            } catch (err) {
                AV._conditionCatalog = [];
            }
        }
        const catalog = AV._conditionCatalog;

        const esc = (s: unknown) => String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

        const grouped = (defs: any[]) => {
            const groups: Record<string, any[]> = { blocking: [], other: [] };
            (defs || []).forEach((c: any) => (c.blocks_actions ? groups.blocking : groups.other).push(c));
            const opt = (label: string, list: any[]) => list.length
                ? `<optgroup label="${label}">${list.map((c: any) => `<option value="${esc(c.value)}">${esc(c.label)}</option>`).join('')}</optgroup>`
                : '';
            return opt('🔒 Blocking', groups.blocking) + opt('✨ Other', groups.other);
        };

        const defMap: Record<string, any> = {};
        (catalog || []).forEach((c: any) => { defMap[c.value] = c; });

        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
        overlay.className = 'modal-overlay';
        window.Lit.render(agentViewTag`
            <div class="modal-window" style="width:480px;max-width:94vw;max-height:90vh;display:flex;flex-direction:column;">
                <div class="modal-head">
                    <h3 style="margin:0;font-size:14px;">🩸 Add Condition — ${charName}</h3>
                </div>
                <div style="padding:12px 16px;overflow:auto;font-size:12px;color:var(--text);">
                    <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Condition</label>
                    <select id="ce-condition" style="width:100%;">${window.Lit.unsafeHTML(grouped(catalog))}</select>
                    <div id="ce-desc" style="margin:4px 0 10px;font-size:11px;color:var(--text-muted);font-style:italic;">Select a condition to see its description.</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                        <div>
                            <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Duration (ticks)</label>
                            <input id="ce-duration" type="number" min="1" style="width:100%;" placeholder="permanent">
                            <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">Leave blank for permanent.</div>
                        </div>
                        <div>
                            <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Level</label>
                            <input id="ce-level" type="number" min="1" style="width:100%;" placeholder="—">
                            <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">e.g. exhausted 1–6.</div>
                        </div>
                    </div>
                    <div style="margin-top:8px;">
                        <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Source (optional)</label>
                        <input id="ce-source" type="text" style="width:100%;" placeholder="e.g. spider bite, betrayal, the curse">
                    </div>
                    <div style="margin-top:8px;">
                        <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Ends on (optional, comma-separated)</label>
                        <input id="ce-ends-on" type="text" style="width:100%;" placeholder="e.g. stand, duration, wake">
                    </div>
                    <details style="margin-top:8px;">
                        <summary style="cursor:pointer;font-size:11px;color:var(--accent);">Advanced (periodic / overrides)</summary>
                        <div style="margin-top:6px;">
                            <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Periodic (JSON)</label>
                            <textarea id="ce-periodic" rows="2" style="width:100%;font-family:monospace;font-size:11px;" placeholder='{"hp": -2, "Energy": -1}'></textarea>
                        </div>
                        <div style="margin-top:6px;">
                            <label style="font-size:10px;color:var(--text-dim);display:block;margin-bottom:2px;">Overrides (JSON)</label>
                            <textarea id="ce-overrides" rows="2" style="width:100%;font-family:monospace;font-size:11px;" placeholder='{"blocks_speech": true, "drops_held_items": true}'></textarea>
                        </div>
                    </details>
                </div>
                <div style="padding:12px 16px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end;">
                    <button class="btn btn-sm btn-ghost" id="ce-cancel">Cancel</button>
                    <button class="btn btn-sm btn-blue" id="ce-add">➕ Add</button>
                </div>
            </div>`, overlay);

        document.body.appendChild(overlay);
        const overlayCloser = (e: Event) => { if (e.target === overlay) overlay.remove(); };
        overlay.addEventListener('click', overlayCloser);
        overlay.querySelector<HTMLElement>('#ce-cancel')!.onclick = () => overlay.remove();
        overlay.querySelector<HTMLElement>('#ce-add')!.onclick = () => {
            const condition = (overlay.querySelector('#ce-condition') as HTMLSelectElement).value;
            if (!condition) { events.log('Pick a condition first.', 'error-msg'); return; }
            const def = defMap[condition];
            const durationRaw = (overlay.querySelector('#ce-duration') as HTMLInputElement).value;
            const duration = durationRaw === '' ? null : parseInt(durationRaw, 10);
            const levelRaw = (overlay.querySelector('#ce-level') as HTMLInputElement).value;
            const level = levelRaw === '' ? null : parseInt(levelRaw, 10);
            const source = (overlay.querySelector('#ce-source') as HTMLInputElement).value.trim() || null;
            const endsOnRaw = (overlay.querySelector('#ce-ends-on') as HTMLInputElement).value.trim();
            const endsOn = endsOnRaw ? endsOnRaw.split(',').map((s: string) => s.trim()).filter(Boolean) : null;
            const parseJson = (el: HTMLInputElement, field: string) => {
                const raw = el.value.trim();
                if (!raw) return null;
                try { return JSON.parse(raw); }
                catch (err) { events.log(`Invalid ${field} JSON — not adding.`, 'error-msg'); throw err; }
            };
            let periodic, overrides;
            try {
                periodic = parseJson(overlay.querySelector('#ce-periodic') as HTMLInputElement, 'periodic');
                overrides = parseJson(overlay.querySelector('#ce-overrides') as HTMLInputElement, 'overrides');
            } catch (err) { return; }

            const payload: Record<string, any> = { condition };
            if (duration !== null) payload.duration = duration;
            if (level !== null) payload.level = level;
            if (source) payload.source = source;
            if (endsOn) payload.ends_on = endsOn;
            if (periodic) payload.periodic = periodic;
            if (overrides) payload.overrides = overrides;
            overlay.remove();
            AV._applyCondition(charName, payload, def);
        };

        overlay.querySelector<HTMLElement>('#ce-condition')!.addEventListener('change', function (this: HTMLInputElement) {
            const def = defMap[this.value];
            const desc = overlay.querySelector<HTMLElement>('#ce-desc')!;
            const duration = overlay.querySelector<HTMLInputElement>('#ce-duration')!;
            if (def) {
                desc.textContent = def.description || 'No description on file.';
                if (def.default_duration) {
                    duration.placeholder = `default ${def.default_duration}`;
                    if (!duration.value) duration.value = def.default_duration;
                } else {
                    duration.placeholder = 'permanent';
                }
            } else {
                desc.textContent = 'Select a condition to see its description.';
            }
        });
        const first = overlay.querySelector('#ce-condition') as HTMLSelectElement;
        if (first.options.length > 1) first.selectedIndex = 0;
        first.dispatchEvent(new Event('change'));
    };

    /**
     * Apply a configured condition to a character via the backend.
     * @param {string} charName - Character name
     * @param {Object} payload - { condition, duration?, source?, level?, periodic?, ends_on?, overrides? }
     * @param {Object} [def] - Catalog entry for logging the label
     */
    AV._applyCondition = async function(charName: string, payload: Record<string, any>, def?: any) {
        try {
            await ApiClient.updateCharacter(charName, { add_condition: payload });
            const label = (def && def.label) || payload.condition;
            const durText = payload.duration ? ` for ${payload.duration}t` : '';
            events.log(`Added "${label}" to ${charName}${durText}`, 'system-msg');
        } catch (err) {
            events.log(`Failed to add condition: ${(err as Error).message}`, 'error-msg');
        }
        worldState.fetch();
        if (VW?.inspector) VW.inspector._reRender();
    };

    /**
     * Render the Bio tab content (personality, appearance, relationships, thoughts, memories, behaviors)
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {object} charState - Character state from events
     * @param {object} area - Area data
     * @param {string} escName - HTML-escaped name
     * @param {boolean} isAuto - Whether autonomous
     * @param {string} color - Agent color
     * @returns {string} HTML
     */
    AV._renderBioTab = function(agentName: string, player: any, charState: any, area: any, escName: string, isAuto: boolean, color: string) {
        const showTab = (tabName: string) => _activeTab === tabName ? '' : 'display:none;';
        const firstImpression = AV._computeFirstImpression(player);
        let html = `<div data-tab="Bio" style="${showTab('Bio')}">`;

        // Stats / Skills / Traits
        html += AV._renderStatsBlocks(player, escName);

        // Personality
        html += `<div class="inspector-section">
            <h3>🧬 Personality</h3>
            <div style="display:flex;gap:4px;margin-bottom:4px;">
                <input type="text" id="inspector-ai-prompt" placeholder="AI: e.g. 'a cowardly thief'" style="flex:1;font-size:11px;">
                <button class="btn btn-sm btn-purple" onclick="InspectorAgentView._generatePersonality('${escName}')" style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;">🤖</button>
            </div>
            <div class="field"><textarea id="inspector-personality" rows="3" style="font-size:11px;" onblur="InspectorAgentView._savePersonality('${escName}')">${player.personality}</textarea></div>
        </div>`;

        // Appearance
        html += `<div class="inspector-section">
            <h3>👤 Appearance</h3>
            <div class="field"><label style="font-size:10px;color:var(--text-muted);">Base Description (naked/baseline look)</label>
                <textarea id="inspector-base-description" rows="2" style="font-size:11px;margin-bottom:4px;" onblur="InspectorAgentView._saveDescription('${escName}')">${player.base_description || ''}</textarea></div>
            <div class="field"><label style="font-size:10px;color:var(--text-muted);">Current Description (derived from base + equipment, or manual override)</label>
                <textarea id="inspector-description" rows="3" style="font-size:11px;" oninput="InspectorAgentView._updateFirstImpression('${escName}')" onblur="InspectorAgentView._saveDescription('${escName}')">${player.description || ''}</textarea></div>
            <div style="background:var(--bg-inset);border:1px dashed var(--border);border-radius:4px;padding:4px 6px;font-size:10px;color:var(--text-muted);margin-bottom:4px;">
                <span style="font-weight:600;">First impression:</span> <span id="inspector-first-impression">${firstImpression}</span>
            </div>
            <button class="btn btn-sm" data-help="auto-description" onclick="InspectorAgentView._generateDescription('${escName}')" title="Regenerate the visible description from the base description plus worn gear. It also refreshes on its own after equip/unequip or a body-state change, so a manual edit here can be overwritten by the next equipment change.">🤖 Generate from Equipment</button>
        </div>`;

        // Relationships
        if (area) {
            const allOtherPlayers = Object.entries(worldState.players || {}).filter(([name]) => name !== agentName);
            const hasUnrelated = allOtherPlayers.some(([name]) => !player.relationships?.[name]);
            html += `<div class="inspector-section">
                <h3 style="display:flex;justify-content:space-between;align-items:center;">
                    <span>🤝 Relationships</span>
                    ${hasUnrelated ? `<select id="rel-add-select-${escName.replace(/\s+/g,'_')}" style="font-size:10px;max-width:120px;">
                        <option value="">+ Add...</option>
                        ${allOtherPlayers.filter(([name]) => !player.relationships?.[name]).map(([name]) => `<option value="${name}">${name}</option>`).join('')}
                    </select>` : ''}
                </h3>`;
            for (const [otherName] of allOtherPlayers) {
                const relationship = player.relationships?.[otherName];
                if (!relationship) continue;
                const closeness = relationship.closeness ?? 0;
                const relColor = closeness > 0 ? (closeness > 50 ? '#3fb950' : '#e3b341') : (closeness < 0 ? (closeness < -50 ? '#f85149' : '#d47766') : 'var(--text-muted)');
                const closenessDesc = closeness <= -75 ? 'mortal enemy' : closeness <= -50 ? 'enemy' : closeness <= -25 ? 'rival' : closeness < 0 ? 'unfriendly' : closeness === 0 ? 'neutral' : closeness <= 25 ? 'acquaintance' : closeness <= 50 ? 'friend' : closeness <= 75 ? 'close friend' : 'inseparable';
                html += `<div class="relationship-item-inspector" data-other="${otherName}">
                    <span style="min-width:70px;font-size:11px;font-weight:500;">${otherName}</span>
                    <input type="range" min="-100" max="100" value="${closeness}" class="rel-slider" data-agent="${agentName}" data-other="${otherName}" style="flex:1;height:4px;accent-color:${relColor};">
                    <span style="font-size:10px;color:var(--text-muted);min-width:28px;text-align:right;" class="rel-val">${closeness}</span>
                    <span style="font-size:9px;color:var(--text-dim);min-width:70px;" class="rel-label">${closenessDesc}</span>
                    <input type="text" class="rel-label-input" data-agent="${agentName}" data-other="${otherName}" value="${relationship.label || ''}" placeholder="label (e.g. mom, brother)" style="width:80px;font-size:9px;padding:1px 3px;">
                    <label title="Tick if you know their name (first_sighting=false)" style="display:flex;align-items:center;gap:2px;font-size:9px;color:var(--text-dim);cursor:pointer;">
                        <input type="checkbox" class="rel-known" data-agent="${agentName}" data-other="${otherName}" ${relationship.first_sighting ? '' : 'checked'}> name
                    </label>
                    <span onclick="InspectorAgentView._removeRelationship('${agentName}','${otherName}')" style="cursor:pointer;color:var(--red);font-size:12px;padding:0 2px;" title="Remove relationship">✕</span>
                </div>`;
            }
            if (allOtherPlayers.every(([name]) => player.relationships?.[name])) {
                html += `<div style="font-size:10px;color:var(--text-muted);padding:4px 0;">All players have a relationship entry.</div>`;
            }
            html += `</div>`;
        }

        // Tags
        const tags = player.tags || [];
        html += `<div class="inspector-section"><h3>🏷️ Tags</h3>
            <div id="tag-multiselect-agent-${escName}"></div>
        </div>`;

        // Aliases — subjective names others use to target this character
        const agentNodeId = `player_${agentName.replace(/\s+/g, '_')}`;
        const agentNode = worldState.getNode(agentNodeId);
        html += AV._deferredAliasesSection(agentNodeId, agentNode?.properties?.aliases || []);

        // bug-514: both generators are useless without a provider, so say so on
        // the button instead of letting the click vanish. `_isAiConfigured` is a
        // side-effect-free read (AIGenerator.isConfigured() toasts, which must
        // not happen on every render).
        const aiReady = AV._isAiConfigured();
        const aiTitleSuffix = aiReady
            ? ''
            : ' — No AI provider configured. Add an API key and model in Settings first.';
        const aiDisabled = aiReady ? '' : 'disabled';

        // Interest tags — what this character pays attention to in a room
        html += `<div class="inspector-section"><h3>✨ Interest Tags</h3>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">Items matching these surface in the agent's prompt. Examine/take removes them from attention.</div>
            <div id="interest-tag-multiselect-agent-${escName}"></div>
            <button class="btn btn-sm" ${aiDisabled} onclick="InspectorAgentView._generateInterestTags('${escName}')" style="font-size:10px;padding:2px 10px;margin-top:4px;" title="Ask the character's LLM to pick interest tags. It is shown the tags already in this world and the tags the library holds that the world has not used yet, and may create new ids. Your hand-placed tags are kept — picks are added.${aiTitleSuffix}">✨ Generate from Personality</button>
        </div>`;

        // Fear tags — same id vocabulary, opposite meaning. engine/fear.py
        // applies `frightened` when a co-located character, item, or area
        // presents one of these tags, so this is how a guard and a farmer end
        // up afraid of different things without a global "hostile" flag.
        html += `<div class="inspector-section"><h3>😨 Fear Tags</h3>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">Meeting a co-located character, item, or area carrying any of these tags makes this character <code>frightened</code>. Leave empty for a character nothing unsettles.</div>
            <div id="fear-tag-multiselect-agent-${escName}"></div>
            <button class="btn btn-sm" ${aiDisabled} onclick="InspectorAgentView._generateFearTags('${escName}')" style="font-size:10px;padding:2px 10px;margin-top:4px;" title="Ask the character's LLM to pick fear tags. It is shown the tags already in this world and the tags the library holds that the world has not used yet, and may create new ids — but a fear only fires on something that actually carries the tag. Your hand-placed tags are kept — picks are added.${aiTitleSuffix}">😨 Generate from Personality</button>
        </div>`;

        // Crafting (task-2): recipes this character knows + craft buttons
        const recipeList = AV._knownRecipeNames(agentName, player);
        html += `<div class="inspector-section"><h3>🧪 Recipes</h3>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">Recipes this character knows: global, skill-learned, item-learned, or discovered by first crafting.</div>`;
        if (recipeList.length) {
            html += recipeList.map((r: any) => `<div style="display:flex;align-items:center;gap:6px;padding:3px 0;font-size:11px;">
                <span style="flex:1;">🧾 ${esc(r.name)}</span>
                <button class="btn btn-sm" data-help="craft" onclick="runAction('craft ${esc(r.name)}','${escName}')" style="font-size:9px;padding:2px 8px;">Craft</button>
            </div>`).join('');
        } else {
            html += `<div style="font-size:10px;color:var(--text-dim);">None yet — create a recipe node (type: recipe) with learned_by: ["global"] (or "skill:&lt;name&gt;", "item:&lt;name&gt;", discoverable:true) to add one.</div>`;
        }
        html += `</div>`;

        // What they see
        html += `<div class="inspector-section"><h3>👁️ What I See</h3>
            <div style="font-size:12px;padding:8px 12px;background:var(--bg-inset);border-radius:6px;border-left:3px solid ${color};">`;
        if (area) {
            html += `<div>${area.description || ''}</div>`;
            const items = area.items?.map((item: any) => item.name).filter(Boolean).join(', ');
            if (items) html += `<div style="margin-top:4px;color:var(--text-dim);font-size:11px;">Items: ${items}</div>`;
            const others = Object.entries(worldState.players || {} as Record<string, any>).filter(([name, p]: [string, any]) => name !== agentName && p.current_area === player.current_area);
            if (others.length) html += `<div style="margin-top:4px;color:var(--pink);font-size:11px;">Also: ${others.map(([name]) => name).join(', ')}</div>`;
        } else {
            html += `<span style="color:var(--text-muted);">Unknown location</span>`;
        }
        html += `</div></div>`;

        // Latest Thoughts
        html += `<div class="inspector-section"><h3>💭 Latest Thoughts</h3>
            <div class="decision-trace"><div class="trace-thought">${charState.lastThought || 'No recent thoughts.'}</div>
            ${charState.lastSpeech ? `<div style="color:var(--pink);font-style:italic;margin-top:4px;">💬 "${charState.lastSpeech}"</div>` : ''}
            ${charState.lastAction ? `<div style="color:var(--accent);font-weight:500;margin-top:4px;">⚡ ${charState.lastAction}</div>` : ''}
            ${charState.lastActionResult ? `<div style="color:var(--orange);font-size:10px;margin-top:4px;">→ ${charState.lastActionResult}</div>` : ''}
        </div></div>`;

        // Plan (task-185: via PlanTracker — the old agent._plans read hit a replaced store)
        const plan = (window as unknown as AVWin).PlanTracker?.getPlan(agentName);
        if (plan && plan.length > 0) {
            html += `<div class="inspector-section"><h3>📋 Plan</h3>
                <ol style="margin:0;padding-left:20px;font-size:11px;line-height:1.7;">`;
            for (const step of plan) {
                html += `<li>${step}</li>`;
            }
            html += `</ol></div>`;
        }

        // Memories (delegated)
        html += (window as unknown as AVWin).InspectorMemory.renderMemoriesHtml(agentName, player, escName, esc);

        html += `</div>`;  // End Bio tab
        return html;
    };

    /**
     * Render the Images tab: the character Expression Pack and sheet splitter.
     * Character-only — the caller only renders this for character nodes.
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {Array|null} characterNode - [nodeId, node] for the character, if found
     * @returns {string} HTML
     */
    AV._renderImagesTab = function(agentName: string, player: any, characterNode: [string, any] | null) {
        const showTab = (tabName: string) => _activeTab === tabName ? '' : 'display:none;';
        let html = `<div data-tab="Images" style="${showTab('Images')}">`;
        if (characterNode) {
            html += (window as unknown as AVWin).InspectorHelpers.renderExpressionSection(characterNode[0], characterNode[1].properties || {});
        } else {
            html += `<div class="inspector-section"><h3>🎭 Expression Pack</h3>
                <div class="section-hint">No character node yet — art is available once this character is placed on the graph.</div></div>`;
        }
        html += `</div>`;  // End Images tab
        return html;
    };

    /**
     * Render the Inventory tab content
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {string} escName - HTML-escaped name
     * @returns {string} HTML
     */
    AV._renderInventoryTab = function(agentName: string, player: any, escName: string) {
        const showTab = (tabName: string) => _activeTab === tabName ? '' : 'display:none;';
        let html = `<div data-tab="Inventory" style="${showTab('Inventory')}">`;

        // Paperdoll / equipment on top
        html += (window as unknown as AVWin).InspectorPaperdoll.renderPaperdollEquipmentHtml(agentName, player, esc, escName);
        html += `<div style="margin:-2px 0 10px 2px;">
            <button class="btn btn-sm" data-help="autodress" onclick="InspectorAgentView._autoDress('${escName}')" style="font-size:10px;padding:2px 10px;" title="The character's LLM picks wearable pieces from the item library that suit who they are. Falls back to matching interest_tags when no LLM is configured. Never replaces worn gear.">🤖 Auto-Dress from Interests</button>
        </div>`;

        const inventory = worldState.getInventory(agentName);
        const equipped = player.equipped || {};
        const equippedItems = new Set();
        for (const stack of Object.values(equipped)) {
            for (const item of stack as any[]) {
                if (item && !String(item).startsWith('__')) equippedItems.add(item);
            }
        }
        const carried = inventory.filter((itemName: string) => !equippedItems.has(worldState.getNodeByIdentifier(itemName)?.id || itemName));

        const allGraphItems = Object.values(worldState.graph?.nodes || {} as Record<string, any>).filter((n: any) => n.type === 'item');
        const containersInInv = carried.filter((name: string) => {
            const node = worldState.getNodeByIdentifier(name);
            const tags = node?.properties?.tags || [];
            return Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container');
        });

        html += `<div class="inspector-section"><h3>🎒 Inventory <span class="section-hint">(${carried.length} carried${inventory.length > carried.length ? `, ${inventory.length - carried.length} worn` : ''}${containersInInv.length ? `, ${containersInInv.length} container` : ''})</span></h3>
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:4px;">`;
        if (carried.length > 0) {
            carried.forEach((itemName: string) => {
                const itemNode = worldState.getNodeByIdentifier(itemName);
                const itemId = itemNode?.id || itemName;
                const weight = itemNode?.properties?.weight || '';
                const slots = itemNode?.properties?.equip_slots || [];
                const tags = itemNode?.properties?.tags || [];
                const isContainer = Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container');
                const isEquippable = slots.length > 0;
                const borderStyle = isContainer ? 'border:2px solid #d29922;' : '';
                const icon = isContainer ? '📦' : '📦';
                const containerOpenBtn = isContainer ? `<button class="btn btn-sm" onclick="event.stopPropagation();VW.inspector.showNode('${itemId.replace(/'/g, "\\'")}')" style="font-size:8px;padding:1px 4px;" title="Open Container">📂</button>` : '';
                html += `<div style="background:var(--bg-inset);border-radius:4px;padding:4px 6px;text-align:center;cursor:pointer;${borderStyle}position:relative;" onclick="VW.inspector.showNode('${itemId.replace(/'/g, "\\'")}')" oncontextmenu="InspectorPaperdoll.showInventoryContextMenu(event,'${escName}','${itemName.replace(/'/g, "\\'")}','${itemId.replace(/'/g, "\\'")}')" data-tippy-content="${itemNode?.properties?.description || itemName}">
                    <div style="font-size:16px;">${icon}</div>
                    <div style="font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;${isContainer ? 'font-weight:bold;color:#d29922;' : ''}">${itemName}</div>
                    ${weight ? `<div style="font-size:8px;color:var(--text-dim);">${weight} kg</div>` : ''}
                    <div style="display:flex;gap:2px;justify-content:center;margin-top:2px;">
                        ${isEquippable ? `<button class="btn btn-sm" onclick="event.stopPropagation();runAction('wear ${itemName}', '${escName}')" style="font-size:8px;padding:1px 4px;" title="Equip">🎽</button>` : ''}
                        ${!isContainer ? `<button class="btn btn-sm" onclick="event.stopPropagation();InspectorAgentView._showContainerPicker('${escName}','${itemName.replace(/'/g, "\\'")}','${itemId.replace(/'/g, "\\'")}')" style="font-size:8px;padding:1px 4px;" title="Put in container">📥</button>` : ''}
                        ${containerOpenBtn}
                        <button class="btn btn-sm btn-red" onclick="event.stopPropagation();runAction('drop ${itemName}', '${escName}')" style="font-size:8px;padding:1px 4px;" title="Drop">✕</button>
                    </div>
                </div>`;
            });
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);padding:8px;grid-column:1/-1;text-align:center;">Nothing carried.</div>`;
        }
        html += `</div>`;

        // Container contents section — show what's inside containers inline
        const containerCandidates = [];
        for (const itemName of inventory) {
            const itemNode = worldState.getNodeByIdentifier(itemName);
            if (!itemNode) continue;
            const tags = itemNode?.properties?.tags || [];
            if (Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container'))
                containerCandidates.push(itemNode);
        }
        for (const stack of Object.values(equipped)) {
            for (const itemId of stack as any[]) {
                if (!itemId || String(itemId).startsWith('__')) continue;
                const itemNode = worldState.getNodeByIdentifier(itemId);
                if (!itemNode) continue;
                const tags = itemNode?.properties?.tags || [];
                if (Array.isArray(tags) && tags.some(tag => String(tag).toLowerCase() === 'container'))
                    if (!containerCandidates.some(existing => existing.id === itemNode.id))
                        containerCandidates.push(itemNode);
            }
        }
        const edges = worldState.graph?.edges || [];
        for (const containerNode of containerCandidates) {
            const contents = edges
                .filter((edge: any) => edge.type === 'in' && edge.target === containerNode.id)
                .map((edge: any) => ({ id: edge.source, node: worldState.getNode(edge.source) }))
                .filter((entry: any) => entry.node);
            if (contents.length === 0) continue;
            html += `<div class="inspector-section" style="margin-top:4px;"><h3>📦 ${containerNode.name} <span class="section-hint">(${contents.length} item${contents.length !== 1 ? 's' : ''})</span></h3>
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:4px;">`;
            contents.forEach(({ id: contentId, node: contentNode }: any) => {
                const safeContentId = contentId.replace(/'/g, "\\'");
                const contentName = contentNode.name;
                html += `<div style="background:var(--bg-inset);border-radius:4px;padding:4px 6px;text-align:center;cursor:pointer;border:1px solid var(--border);position:relative;" onclick="VW.inspector.showNode('${safeContentId}')" data-tippy-content="${contentNode?.properties?.description || contentName}">
                    <div style="font-size:16px;">📦</div>
                    <div style="font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${contentName}</div>
                    <div style="display:flex;gap:2px;justify-content:center;margin-top:2px;">
                        <button class="btn btn-sm btn-red" onclick="event.stopPropagation();runAction('take ${contentName}', '${escName}')" style="font-size:8px;padding:1px 4px;" title="Take from container">✕</button>
                    </div>
                </div>`;
            });
            html += `</div></div>`;
        }

        html += `
            <button class="btn btn-sm btn-blue" onclick="InspectorAgentView._showAddItemPicker('${escName}')" style="margin-top:4px;width:100%;font-size:10px;">+ Add Item to Inventory</button></div>`;

        // Known Abilities section
        const playerNodeId = `player_${escName}`;
        const knownAbilityEdges = (worldState.graph?.edges || []).filter((e: any) => e.type === 'known' && e.target === playerNodeId);
        const knownAbilities = knownAbilityEdges.map((e: any) => worldState.getNode(e.source)).filter(Boolean);
        html += `<div class="inspector-section" style="margin-top:8px;"><h3>🧠 Known Abilities <span class="section-hint">(${knownAbilities.length})</span></h3>`;
        if (knownAbilities.length === 0) {
            html += `<div style="font-size:11px;color:var(--text-muted);padding:8px;">No abilities known yet.</div>`;
        } else {
            html += `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:4px;">`;
            for (const ab of knownAbilities) {
                const safeId = ab.id.replace(/'/g, "\\'");
                const safeName = (ab.name || '').replace(/'/g, "\\'");
                html += `<div style="background:var(--bg-inset);border-radius:4px;padding:4px 6px;text-align:center;cursor:pointer;border:1px solid var(--border);position:relative;" onclick="VW.inspector.showNode('${safeId}')" data-tippy-content="${(ab.properties?.description || ab.name || '').replace(/"/g, '&quot;')}">
                    <div style="font-size:16px;">✨</div>
                    <div style="font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${ab.name || safeId}</div>
                    <div style="display:flex;gap:2px;justify-content:center;margin-top:2px;">
                        <button class="btn btn-sm btn-red" onclick="event.stopPropagation();InspectorAgentView._removeKnownAbility('${escName}', '${safeId}')" style="font-size:8px;padding:1px 4px;" title="Forget">✕</button>
                    </div>
                </div>`;
            }
            html += `</div>`;
        }
        html += `<button class="btn btn-sm btn-blue" onclick="InspectorAgentView._showAddKnownAbilityPicker('${escName}')" style="margin-top:4px;width:100%;font-size:10px;">+ Add Known Ability</button></div>`;
        html += `</div>`;  // End Inventory tab
        return html;
    };

    /**
     * Render the Advanced tab content (behaviors, timeline, conversation memory, save/export, nudge, manual command)
     * @param {string} agentName - Character name
     * @param {object} player - Player data
     * @param {object} charState - Character state from events
     * @param {string} escName - HTML-escaped name
     * @param {boolean} isAuto - Whether autonomous
     * @param {Array|null} characterNode - [nodeId, node] pair or null
     * @returns {string} HTML
     */
    AV._renderAdvancedTab = function(agentName: string, player: any, charState: any, escName: string, isAuto: boolean, characterNode: [string, any] | null) {
        const showTab = (tabName: string) => _activeTab === tabName ? '' : 'display:none;';
        let html = `<div data-tab="Advanced" style="${showTab('Advanced')}">`;

        // Graph physics — the character's own layout/physics overrides. Lives
        // here rather than in the header: it is a tuning setting, not part of
        // who the character is. Rendered once, via the deferred helper, because
        // graphGravityControl returns a lit TemplateResult.
        if (characterNode) {
            html += AV._deferredGravityControl(characterNode[0], characterNode[1].properties || {});
        }

        // Behaviors
        if (player.simple_npc && Array.isArray(player.behaviors)) {
            html += `<div class="inspector-section">
                <h3 style="display:flex;justify-content:space-between;align-items:center;">🤖 Behaviors <span style="color:var(--text-dim);font-size:10px;">(${player.behaviors.length})</span>
                    <button class="btn btn-sm" onclick="InspectorBehaviors.openGraphEditor('${escName}')" style="font-size:10px;" title="Open all behaviors in the graph editor">🧩 Graph</button>
                </h3>
                <div style="max-height:300px;overflow-y:auto;">`;
            player.behaviors.forEach((behavior: any, behaviorIndex: number) => {
                const trigger = behavior.trigger || '?';
                const conditionText = behavior.conditions ? JSON.stringify(behavior.conditions) : 'none';
                const actionText = behavior.actions ? behavior.actions.map((action: any) => action.type).join(', ') : 'none';
                html += `<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:6px;margin-bottom:4px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong>${esc(trigger)}</strong>
                        <div>
                            <button class="btn btn-sm" onclick="InspectorBehaviors.editBehavior('${escName}',${behaviorIndex})" style="font-size:10px;">✏️</button>
                            <button class="btn btn-sm btn-red" onclick="InspectorBehaviors.deleteBehavior('${escName}',${behaviorIndex})" style="font-size:10px;">🗑</button>
                        </div>
                    </div>
                    <div style="font-size:10px;color:var(--text-dim);margin-top:2px;">Conditions: ${esc(conditionText)}</div>
                    <div style="font-size:10px;color:var(--text-dim);">Actions: ${esc(actionText)}</div>
                </div>`;
            });
            html += `</div>
                <button class="btn btn-sm btn-green" onclick="InspectorBehaviors.addBehavior('${escName}')" style="margin-top:4px;width:100%;">+ Add Behavior</button>
            </div>`;
        }

        // Knowledge (what this character knows from the start — authored
        // `known` registry). Chips are lit-free DOM, filled by deferred render.
        const kbChipId = String(agentName ?? '').replace(/[^a-zA-Z0-9_-]/g, '_');
        html += `<div class="inspector-section">
            <h3 style="display:flex;justify-content:space-between;align-items:center;">🧠 Knowledge
                <button class="btn btn-sm btn-blue" onclick="KnownBySection.openKnowledgeModal('${escName}')" style="font-size:10px;" title="Select every runtime entity this character knows, grouped by category">🎛 Manage</button>
            </h3>
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:6px;">Known from the start — hidden ways/items visible, people never masked, known areas reveal hidden exits.</div>
            <div id="knowledge-chips-${kbChipId}"></div>
        </div>`;
        _deferRender(() => {
            const container = document.getElementById('knowledge-chips-' + kbChipId);
            if (container && (window as unknown as AVWin).KnownBySection) {
                container.textContent = '';
                container.appendChild((window as unknown as AVWin).KnownBySection.buildKnownChips(agentName));
            }
        });

        // Timeline
        const timeline = charState.detailedTimeline || [];
        html += `<div class="inspector-section"><h3>📜 Timeline <span class="section-hint">(click to expand)</span></h3>
            <div class="timeline-viewer" id="timeline-${escName}">`;
        if (timeline.length > 0) {
            const startIdx = Math.max(0, timeline.length - 50);
            for (let entryIndex = startIdx; entryIndex < timeline.length; entryIndex++) {
                const entry = timeline[entryIndex];
                const phase = entry.phase || 'unknown';
                const phaseIcons: Record<string, string> = { think: '💭', decide: '🎯', act: '⚡', action: '⚡', result: '→', react: '🔄', speech: '💬', observe: '👁️' };
                const phaseIcon = phaseIcons[phase] || '•';
                const phaseLabel = phase.charAt(0).toUpperCase() + phase.slice(1);

                let contentText = '';
                if (entry.thought) contentText = entry.thought;
                else if (entry.speech) contentText = `"${entry.speech}"`;
                else if (entry.action) contentText = entry.action;
                else if (entry.result) contentText = entry.result;
                else if (entry.message) contentText = entry.message;
                else contentText = phase;

                html += `<div class="timeline-entry" onclick="InspectorAgentView._showTimelineDetail('${escName}', ${entryIndex}, this)">
                    <div class="timeline-entry-header">
                        <span class="timeline-tick">[${events.tickToTime(entry.tick || 0)}]</span>
                        <span class="timeline-phase-badge timeline-phase-${phase}">${phaseIcon} ${phaseLabel}</span>
                    </div>
                    <div class="timeline-entry-content">${contentText}</div>
                </div>`;
            }
        } else {
            html += `<div style="font-size:11px;color:var(--text-muted);padding:8px;">No timeline entries yet. The timeline captures every thought, decision, action, result, and reaction as the character experiences them.</div>`;
        }
        html += `</div>
            <div id="timeline-detail-${escName}" style="display:none;"></div>
        </div>`;

        // Conversation Memory
        const chatHistory = agent.getDisplayHistory(agentName);
        html += `<div class="memory-section"><h3>🧠 Conversation Memory (${chatHistory.length} exchanges)</h3>
            <div style="max-height:300px;overflow-y:auto;font-size:11px;">`;
        if (chatHistory.length > 0) {
            for (let msgIndex = 0; msgIndex < chatHistory.length; msgIndex++) {
                const msg = chatHistory[msgIndex];
                const role = msg.role || 'unknown';
                const content = (msg.content || '');
                const roleLabel = role === 'user' ? '👤 Prompt' : '🤖 Response';
                const roleColor = role === 'user' ? 'var(--accent)' : 'var(--purple)';
                html += `<div style="padding:6px 8px;border-bottom:1px solid var(--border-light);">
                    <div style="font-size:9px;color:${roleColor};font-weight:600;margin-bottom:2px;">${roleLabel} #${msgIndex + 1}</div>
                    <div style="color:var(--text-dim);font-size:10px;max-height:40px;overflow:hidden;">${content}${content.length > 250 ? '...' : ''}</div>
                </div>`;
            }
        } else {
            html += `<div class="memory-empty">This character has no conversation history yet. History builds as the agent takes actions.</div>`;
        }
        html += `</div></div>`;

        // Save / Import to World
        html += `<div class="inspector-section" style="border-top:1px solid var(--border);padding-top:12px;">
            <h3>💾 Library</h3>
            <div style="display:flex;gap:4px;">
                <button class="btn btn-sm btn-green" onclick="InspectorAgentView._saveCharacter('${escName}')">💾 Save to Library</button>
                <button class="btn btn-sm btn-purple" onclick="InspectorAgentView._importCharacter()" style="background:#4a2a8a;border-color:#6a3aaa;color:#bc8cff;" title="Load a character JSON file into the world (no library entry needed)">📤 Import JSON → World</button>
            </div>
            <div style="display:flex;gap:4px;margin-top:6px;">
                <button class="btn btn-sm" style="background:#5a1a1a;border-color:#8a2a2a;color:#ff6b6b;" onclick="InspectorAgentView._killCharacter('${escName}')">💀 Kill</button>
                <button class="btn btn-sm" style="background:#3a1a1a;border-color:#6a2a2a;color:#ff4444;" onclick="InspectorAgentView._removeCharacter('${escName}')">🗑️ Remove</button>
            </div>
        </div>`;

        // Library template row (same pattern as item/way/area inspectors)
        if (characterNode && characterNode[0] && (window as unknown as AVWin).InspectorTemplateSync) {
            html += `<div class="inspector-section" style="border-top:1px solid var(--border);padding-top:12px;">
                <h3>📚 Library Template</h3>
                <div style="display:flex;gap:6px;flex-wrap:wrap;">
                    ${(window as unknown as AVWin).InspectorTemplateSync.renderTemplateRow('character', characterNode[0], characterNode[1].properties || {})}
                </div>
            </div>`;
        }

        // Nudge
        html += `<div class="inspector-section" style="border-top:1px solid var(--border);padding-top:12px;">
            <h3>🎯 Nudge</h3>
            <div style="display:flex;gap:4px;">
                <input type="text" id="nudge-input" placeholder="Inject a thought for ${agentName}..." style="flex:1;font-size:11px;">
                <button class="btn btn-sm btn-green" onclick="agent.nudge('${escName}', document.getElementById('nudge-input')?.value); document.getElementById('nudge-input').value='';">Send</button>
            </div>
        </div>`;

        // Manual Command
        if (!isAuto) {
            html += `<div class="inspector-section" style="border-top:1px solid var(--border);padding-top:12px;">
                <h3>✋ Manual Command</h3>
                <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">Type a command for ${agentName} to execute.</div>
                <div style="display:flex;gap:4px;">
                    <input type="text" id="manual-cmd-input" placeholder="e.g. go north, take key, speak hello..." style="flex:1;font-size:11px;" onkeypress="if(event.key==='Enter') InspectorAgentView._sendManualCommand('${escName}')">
                    <button class="btn btn-sm btn-green" onclick="InspectorAgentView._sendManualCommand('${escName}')">Send</button>
                </div>
            </div>`;
        }

        html += `<div id="known-by-slot" data-known-by-slot="1"></div>`;
        html += `</div>`;  // End Advanced tab
        return html;
    };

    // ═══════════════════════════════════════════════
    //  Helper event bindings
    // ═══════════════════════════════════════════════

    /**
     * Bind relationship slider and dropdown events after rendering
     * @param {HTMLElement} panel - The inspector panel element
     * @param {string} agentName - Character name
     */
    AV._bindRelationshipSliders = function(panel: HTMLElement, agentName: string) {
        panel.querySelectorAll<HTMLInputElement>('.rel-slider').forEach(slider => {
            slider.addEventListener('input', function(this: HTMLInputElement) {
                const value = this.value;
                const row = this.closest('.relationship-item-inspector');
                if (row) {
                    const label = row.querySelector('.rel-label');
                    const valueSpan = row.querySelector('.rel-val');
                    if (valueSpan) valueSpan.textContent = value;
                    const numericValue = parseInt(value);
                    let description = 'mortal enemy';
                    if (numericValue <= -75) description = 'mortal enemy';
                    else if (numericValue <= -50) description = 'enemy';
                    else if (numericValue <= -25) description = 'rival';
                    else if (numericValue < 0) description = 'unfriendly';
                    else if (numericValue === 0) description = 'neutral';
                    else if (numericValue <= 25) description = 'acquaintance';
                    else if (numericValue <= 50) description = 'friend';
                    else if (numericValue <= 75) description = 'close friend';
                    else description = 'inseparable';
                    if (label) label.textContent = description;
                }
            });
            slider.addEventListener('change', function(this: HTMLInputElement) {
                const agent = this.dataset.agent as string;
                const other = this.dataset.other as string;
                const value = parseInt(this.value);
                const existing = worldState.players?.[agent]?.relationships?.[other] || {};
                ApiClient.updateCharacter(agent, {
                    relationships: { [other]: { closeness: value, last_interaction_tick: worldState.data?.time_ticks || 0, interaction_count: existing.interaction_count || 0, first_sighting: existing.first_sighting ?? false } }
                }).then(() => {});
            });
        });

        // "knows their name" toggle -> sets first_sighting (false = knows).
        panel.querySelectorAll<HTMLInputElement>('.rel-known').forEach(cb => {
            cb.addEventListener('change', function(this: HTMLInputElement) {
                const agent = this.dataset.agent as string;
                const other = this.dataset.other as string;
                const knowsName = this.checked;
                const existing = worldState.players?.[agent]?.relationships?.[other] || {};
                ApiClient.updateCharacter(agent, {
                    relationships: { [other]: { closeness: existing.closeness || 0, last_interaction_tick: worldState.data?.time_ticks || 0, interaction_count: existing.interaction_count || 0, first_sighting: !knowsName } }
                }).then(() => worldState.fetch());
            });
        });

        panel.querySelectorAll<HTMLInputElement>('.rel-label-input').forEach(input => {
            input.addEventListener('change', function(this: HTMLInputElement) {
                const agent = this.dataset.agent as string;
                const other = this.dataset.other as string;
                const label = this.value.trim();
                const existing = worldState.players?.[agent]?.relationships?.[other] || {};
                ApiClient.updateCharacter(agent, {
                    relationships: { [other]: { closeness: existing.closeness || 0, last_interaction_tick: worldState.data?.time_ticks || 0, interaction_count: existing.interaction_count || 0, first_sighting: existing.first_sighting ?? false, label: label } }
                }).then(() => worldState.fetch());
            });
        });

        const addSelect = document.getElementById('rel-add-select-' + agentName.replace(/\s+/g, '_')) as HTMLSelectElement | null;
        if (addSelect) {
            addSelect.addEventListener('change', function(this: HTMLSelectElement) {
                const other = this.value;
                if (!other) return;
                this.value = '';
                ApiClient.updateCharacter(agentName, {
                    relationships: { [other]: { closeness: 0, last_interaction_tick: worldState.data?.time_ticks || 0, interaction_count: 0, first_sighting: false } }
                }).then(() => worldState.fetch().then(() => {
                    if (window.VW?.inspector) window.VW.inspector.showAgent(agentName);
                }));
            });
        }
    };

    // ═══════════════════════════════════════════════
    //  Agent action methods
    // ═══════════════════════════════════════════════

    /**
     * Send a manual command for this character via the API
     * @param {string} charName - Character name
     */
    AV._sendManualCommand = function(charName: string) {
        const input = document.getElementById('manual-cmd-input') as HTMLInputElement | null;
        const command = (input?.value || '').trim();
        if (!command) return;
        if (input) input.value = '';
        events.log(`📝 Manual command for ${charName}: ${command}`, 'system-msg');
        runAction(command, charName);
    };

    /**
     * Generate personality via AI
     * @param {string} charName - Character name
     */
    AV._generatePersonality = async function(charName: string) {
        const input = document.getElementById('inspector-ai-prompt') as HTMLTextAreaElement | null;
        const prompt = (input?.value || '').trim();
        if (!prompt) { input?.focus(); return; }
        if (!config.apiKey || !config.model) { toastInfo('Configure API key and model in Settings first.'); return; }

        (input as HTMLTextAreaElement).disabled = true;
        (input as HTMLTextAreaElement).value = 'Generating...';

        const system = 'You are a character designer. Generate a personality based on the prompt. Respond with ONLY raw JSON:\n{"personality":"Detailed character personality, fears, motivations, quirks."}';

        try {
            const resp = await llmClient.chat([
                { role: 'system', content: system },
                { role: 'user', content: prompt }
                ], { temperature: 0.9, responseFormat: (window as unknown as AVWin).StructuredFormats?.personality, label: 'inspector/generate-personality' });
            if (!resp) { toastError('No response from LLM.'); return; }

            let cleaned = resp.trim();
            const jsonMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
            if (jsonMatch) cleaned = jsonMatch[1].trim();
            else { const firstBrace = cleaned.indexOf('{'), lastBrace = cleaned.lastIndexOf('}'); if (firstBrace !== -1 && lastBrace > firstBrace) cleaned = cleaned.substring(firstBrace, lastBrace + 1); }
            const parsed = JSON.parse(cleaned);

            const personalityText = parsed.personality || 'A mysterious character.';
            const textarea = document.getElementById('inspector-personality') as HTMLTextAreaElement | null;
            if (textarea) textarea.value = personalityText;
            await ApiClient.updateCharacter(charName, { personality: personalityText });
            events.log(`AI generated personality for ${charName}`, 'system-msg');
        } catch (error) {
            console.error(error);
            toastError('AI generation failed: ' + (error as Error).message);
        } finally {
            (input as HTMLTextAreaElement).disabled = false;
            (input as HTMLTextAreaElement).value = '';
            (input as HTMLTextAreaElement).placeholder = 'AI: e.g. \'a cowardly thief\'';
        }
    };

    /**
     * Save personality from the inspector textarea
     * @param {string} charName - Character name
     */
    AV._savePersonality = function(charName: string) {
        return (window as unknown as AVWin).InspectorHelpers.savePersonality(charName);
    };

    /**
     * Grammar/voice check for LLM-generated appearance text (task-345).
     * player.description must stay THIRD person: strangers see it (examine,
     * labels) and the agent prompt converts it to second person for the owner
     * via secondPersonDesc. Catches the stored repro slips ("you is",
     * "body is who") plus any first/second-person leak — small models emit
     * both and the text becomes permanent, load-bearing prompt content.
     * @param {string} text - Generated description
     * @returns {string[]} Detected issues (empty array = clean)
     */
    AV._appearanceGrammarIssues = function(text: string): string[] {
        const issues: string[] = [];
        if (!text || !text.trim()) return issues;
        if (/\b(?:you|your|yours|you're|you've)\b/i.test(text)) issues.push('second-person pronoun (you/your)');
        if (/\b(?:I|I'm|I've|I'll|my|me)\b/i.test(text)) issues.push('first-person pronoun (I/my/me)');
        if (/\byou\s+is\b|\byou\s+was\b|\bbody\s+is\s+who\b/i.test(text)) issues.push('verb-agreement slip');
        return issues;
    };

    /**
     * One silent repair pass for flagged appearance text (task-345): re-ask
     * the LLM to fix grammar + voice in place. Returns clean text, or null
     * when it is still flagged (the caller falls back to the safe merge).
     * @param {string} text - Generated description with issues
     * @returns {Promise<string|null>} Cleaned text, or null
     */
    AV._sanitizeAppearanceGrammar = async function(text: string): Promise<string | null> {
        if (!text || AV._appearanceGrammarIssues(text).length === 0) return text;
        try {
            const repair = await llmClient.chat([
                { role: 'user', content:
                    'Fix this character appearance description.\n'
                    + 'Keep every content detail exactly as it is; correct only grammar and rewrite any '
                    + 'first-person or second-person wording ("I/my/me/you/your") into consistent THIRD person '
                    + '(she/he/they + her/his/their). Subject-verb agreement must be exact.\n'
                    + 'Output ONLY the corrected description — no commentary.\n\n'
                    + text }
                ], { temperature: 0.4, label: 'inspector/appearance-repair' });
            const fixed = (repair || '').trim();
            if (fixed && AV._appearanceGrammarIssues(fixed).length === 0) return fixed;
            return null;
        } catch (e) {
            return null;
        }
    };

    /**
     * Generate description via AI (server-side LLM or client-side fallback)
     * @param {string} charName - Character name
     */
    AV._generateDescription = async function(charName: string) {
        const player = worldState.players[charName];
        if (!player) return;
        if (!(AIGenerator as unknown as { isConfigured(): boolean }).isConfigured()) return;

        const base = player.base_description || '';
        const equipped = player.equipped || {};

        const equipLines: string[] = [];
        for (const [slotName, items] of Object.entries(equipped as Record<string, any[]>)) {
            if (items && items.length > 0) {
                const realItems = items.filter((item: any) => item && !String(item).startsWith('__'));
                if (realItems.length === 0) continue;
                const resolved = realItems.map(id => {
                    const node = worldState.getNodeByIdentifier(id);
                    if (!node) return id;
                    const desc = node.properties?.description || '';
                    return desc ? `${node.name} (${desc})` : node.name;
                });
                equipLines.push(`${slotName}: ${resolved.join(' worn under ')}`);
            }
        }
        const equipText = equipLines.length > 0 ? equipLines.join('\n') : 'Nothing worn.';

        const prompt = `Describe this character's appearance as a narrator would — vivid, natural, and specific.\n\n`
            + `CHARACTER BASELINE\n${base || '(no base description)'}\n\n`
            + `CURRENT ATTIRE\n${equipText}\n\n`
            + `Writing Directives\n`
            + `Open with a single striking sentence about their face, hair, or a defining physical feature — this is the first thing a stranger would notice. Do not lead with clothing.\n`
            + `Weave the clothing into the description naturally. Mention how each piece fits, drapes, or contrasts with their skin. Use the item descriptions as texture and detail — not as a checklist.\n`
            + `If they are nude, describe their body, posture, and how they carry themselves without flinching.\n`
            + `2-4 sentences total. No bullet points. No backstory. No personality. No internal thoughts. Only what can be seen.\n`
            + `Write in consistent third person (she/he/they + her/his/their). NEVER use "you", "your", or "I" — the character's own prompt converts this description to second person for them, so the stored text must stay third person.\n`
            + `Grammar must be exact: no "you is", no "body is who", no "she have" — subject-verb agreement only.\n`
            + `\nExamples:\n- "A wiry, olive-skinned woman with sharp cheekbones picks at her sleeve..."\n- "He is all lean bone and coltish angles at 171cm, self-conscious about his flat-chested frame."`;

        const textarea = document.getElementById('inspector-description') as HTMLTextAreaElement | null;
        if (textarea) textarea.value = 'Generating...';

        try {
            const response = await llmClient.chat([
                { role: 'user', content: prompt }
                ], { temperature: 0.7, label: 'inspector/generate-appearance' });

            if (response && response.trim()) {
                // task-345: the stored description feeds EVERY prompt forever
                // and is seen by other characters, so never persist broken
                // grammar/voice — validate, then one silent repair pass, else
                // fall through to the safe client-side merge below.
                const cleaned = await AV._sanitizeAppearanceGrammar(response.trim());
                if (cleaned) {
                    if (textarea) textarea.value = cleaned;
                    await AV._saveDescription(charName);
                    return;
                }
                if (AV._appearanceGrammarIssues(response.trim()).length > 0) {
                    events.log(`⚠️ ${charName}: generated appearance failed grammar check — using safe fallback`, 'error-msg');
                }
            }
        } catch (e) {
            // fall through to fallback
        }

        // Fallback: merge base_description + equipment client-side
        const slots: string[] = [];
        for (const [slotName, items] of Object.entries(equipped as Record<string, any[]>)) {
            if (items && items.length > 0) {
                const realItems = items.filter((item: any) => item && !String(item).startsWith('__'));
                if (realItems.length > 0) slots.push(`${slotName}: ${realItems.join(' > ')}`);
            }
        }
        let description = base;
        if (slots.length > 0) {
            description += (description ? '\n\n' : '') + 'Wearing: ' + slots.join('; ') + '.';
        }
        if (textarea) {
            textarea.value = description || 'Nothing equipped.';
            await AV._saveDescription(charName);
        }
    };

    /**
     * Compute the "first impression" label a stranger sees at a glance:
     * the tag-derived handle (the man / the woman / a girl ...) plus the
     * first sentence of the description. Mirrors prompt-builder's anonymousName.
     * @param {object} player - Player data object
     * @returns {string} First impression text
     */
    AV._computeFirstImpression = function(player: any): string {
        if (!player) return '';
        const tagMap: Record<string, string> = {
            female: 'the woman', male: 'the man', woman: 'the woman', man: 'the man',
            girl: 'a girl', boy: 'a boy', child: 'a child', animal: 'an animal'
        };
        let handle = '';
        for (const tag of (player.tags || [])) {
            const mapped = tagMap[String(tag).toLowerCase()];
            if (mapped) { handle = mapped; break; }
        }
        const desc = (player.description || player.base_description || '').trim();
        const firstSentence = desc.split('.')[0].trim() + (desc.includes('.') ? '.' : '');
        const parts = [];
        if (handle) parts.push(handle);
        if (firstSentence && firstSentence !== handle) parts.push(firstSentence);
        if (parts.length === 0) parts.push('the stranger');
        return parts.join(' — ');
    };

    /**
     * Live-update the first impression preview as the description is typed.
     * @param {string} charName - Character name
     */
    AV._updateFirstImpression = function(charName: string) {
        const ta = document.getElementById('inspector-description') as HTMLTextAreaElement | null;
        const baseTa = document.getElementById('inspector-base-description') as HTMLTextAreaElement | null;
        const player = Object.assign({}, worldState.players?.[charName] || {});
        if (ta) player.description = ta.value;
        if (baseTa) player.base_description = baseTa.value;
        const preview = document.getElementById('inspector-first-impression');
        if (preview) preview.textContent = AV._computeFirstImpression(player);
    };

    /**
     * Recipes a character knows (task-2): global / skill: / item: /
     * discovered (crafting_known). Mirrors engine/crafting.py learning rules.
     * @param {string} charName - Character name
     * @param {object} player - Player data object
     * @returns {Array} Recipe graph nodes (type === 'recipe')
     */
    AV._knownRecipeNames = function(charName: string, player: any): any[] {
        const state = worldState.data || {};
        const nodes = (state.graph?.nodes || {}) as Record<string, any>;
        const equipped = player.equipped || {};
        const carriedNames = new Set();
        const graph = worldState.data?.graph || {};
        const pid = 'player_' + charName.replace(/\s+/g, '_');
        for (const e of (graph.edges || [])) {
            if (e.target === pid && (e.type === 'carrying' || e.type === 'equipped')) {
                const n = worldState.getNode(e.source);
                if (n) carriedNames.add(String(n.name).toLowerCase());
            }
        }
        const known = (player.crafting_known || []).map(String);
        const out: any[] = [];
        for (const node of Object.values(nodes)) {
            if (node.type !== 'recipe') continue;
            const props = node.properties || {};
            const learnedBy = Array.isArray(props.learned_by) ? props.learned_by
                : (props.learned_by ? [props.learned_by] : []);
            let knows = false;
            for (const rule of learnedBy) {
                const r = String(rule || '');
                if (r === 'global') { knows = true; break; }
                if (r.startsWith('skill:')) {
                    const skill = r.slice(6);
                    if (parseInt(player.skills?.[skill], 10) >= 1) { knows = true; break; }
                }
                if (r.startsWith('item:')) {
                    const needle = r.slice(5).toLowerCase();
                    if (carriedNames.has(needle)) { knows = true; break; }
                }
            }
            if (!knows && known.includes(node.name)) knows = true;
            if (knows) out.push(node);
        }
        return out;
    };

    /**
     * Keep only picks that name a real candidate, in the model's order.
     *
     * Pure so it is unit-testable, and deliberately strict: a model asked to
     * choose from a list will sometimes invent an id or echo a display name, and
     * an unvalidated id would be posted straight to the equip endpoint. Unknown
     * ids are dropped rather than coerced, so a bad response degrades to fewer
     * items instead of a wrong outfit.
     *
     * @param {Array} pool - Candidates the model was shown
     * @param {Array} picked - Raw ids from the model
     * @returns {Array} Ids that exist in the pool, de-duplicated, order kept
     */
    AV._validateAutoDressPicks = function(pool: any[], picked: any[]): string[] {
        const valid = new Set((Array.isArray(pool) ? pool : []).map((c: any) => String(c?.lib_id ?? '')));
        const out: string[] = [];
        const seen = new Set<string>();
        for (const raw of (Array.isArray(picked) ? picked : [])) {
            const id = String(raw ?? '').trim();
            if (!id || !valid.has(id) || seen.has(id)) continue;
            seen.add(id);
            out.push(id);
        }
        return out;
    };

    /**
     * Pull the chosen ids out of a model response.
     *
     * Accepts the {"items": [...]} contract, a bare array, and the bracket
     * extraction the tag generators use, because providers disagree about
     * structured output. Returns null when nothing parseable is present, which
     * the caller treats as "fall back to the deterministic path".
     *
     * @param {string} text - Raw model output
     * @returns {Array|null} Ids, or null if unparseable
     */
    AV._parseAutoDressResponse = function(text: unknown): string[] | null {
        const raw = String(text || '').trim();
        if (!raw) return null;
        let list = null;
        try {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) list = parsed;
            else if (Array.isArray(parsed?.items)) list = parsed.items;
        } catch (e) { /* fall through to bracket extraction */ }
        if (!list) {
            const match = raw.match(/\[[^\]]*\]/);
            if (!match) return null;
            try { list = JSON.parse(match[0]); }
            catch (e) {
                list = match[0].replace(/[[\]"']/g, '').split(',').map(s => s.trim()).filter(Boolean);
            }
        }
        return list;
    };

    /**
     * Auto-dress a character (task-325, LLM selection task-660).
     *
     * The engine cannot call a model — keys live in the browser — so the flow is
     * ask the engine for a wearable pool, let the model pick from it, post the
     * ids back, and let the engine equip. With no model configured, or if the
     * call fails or returns nothing usable, this falls through to the original
     * tag-intersection path unchanged.
     *
     * The pool the model sees is deliberately WIDER than the tag filter accepts.
     * The tag filter is the reason an Eldenford blacksmith whose interests are
     * metal/tools/iron/temper came out wearing a Guiding Cane: nothing wearable
     * matched, so the generic branch shuffled the whole wardrobe pool. Judgement
     * about the person, not vocabulary overlap, is what is missing.
     *
     * @param {string} charName - Character name
     */
    AV._autoDress = async function(charName: string) {
        let libraryIds: string[] | null = null;
        let note = '';
        let pool: any[] = [];
        let context: any = null;
        try {
            const candResp = await fetch('/api/auto_dress/candidates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ character: charName }),
            });
            const cand = await candResp.json();
            pool = Array.isArray(cand?.pool) ? cand.pool : [];
            context = { personality: cand?.personality || '', description: cand?.base_description || '' };

            if (pool.length > 0 && AIGenerator.isConfigured()) {
                const listing = pool.map((c: any) =>
                    `- ${c.lib_id}  (${c.name}; tags: ${c.tags.join(', ') || 'none'}; slots: ${c.slots.join(', ')})`
                ).join('\n');
                const prompt = `You are choosing what a specific character would actually wear.

CHARACTER: ${cand.character}
${cand.personality ? `PERSONALITY\n${cand.personality}\n` : ''}${cand.base_description ? `APPEARANCE\n${cand.base_description}\n` : ''}
AVAILABLE ITEMS (id | name | tags | slots)
${listing}

Pick the pieces this specific person would wear right now: the clothes and tools that fit their work, their life, and the weather. Judge the CHARACTER, not the tag vocabulary — a shared tag is not a reason to pick something, and a strong reason to pick something overrides a missing tag.

Rules:
- Only use ids from the list above. Never invent one.
- 2 to 6 items. Fewer is better than padding.
- Include worn clothing, footwear, and headwear. Add a tool or weapon only if this person would carry it.
- Skip anything that would look absurd on this person.

Respond with ONLY a JSON object: {"items": ["apron","stained_work_shirt"]}`;

                const response = await llmClient.chat([{ role: 'user', content: prompt }],
                    { temperature: 0.6, label: 'inspector/auto-dress' });
                const picked = AV._parseAutoDressResponse(response);
                if (picked) {
                    const valid = AV._validateAutoDressPicks(pool, picked);
                    if (valid.length > 0) {
                        libraryIds = valid;
                    } else {
                        note = 'Model returned no usable item ids; used interest tags instead.';
                    }
                } else {
                    note = 'Model returned an unreadable response; used interest tags instead.';
                }
            } else if (pool.length === 0) {
                note = 'No wearable items in the library matched this area.';
            } else {
                note = 'No LLM configured; used interest tags instead.';
            }
        } catch (e) {
            note = 'LLM selection unavailable (' + (e as Error).message + '); used interest tags instead.';
        }

        try {
            // Nothing chosen yet and no reason to propose anything: just run the
            // deterministic path. Everything else goes to the modal first, so a
            // person sees the context the model read before anything is worn.
            if (libraryIds) {
                const player = worldState.players?.[charName];
                const byId = new Map<string, any>(pool.map((c: any) => [c.lib_id, c]));
                const chosen = libraryIds.map(id => byId.get(id)).filter(Boolean);
                const worn: Record<string, any[]> = {};
                for (const [slot, stack] of Object.entries(player?.equipped || {})) {
                    const names = (Array.isArray(stack) ? stack : [])
                        .filter((i: any) => i && !String(i).startsWith('__'))
                        .map((i: any) => worldState.getNodeByIdentifier(i)?.name || i);
                    if (names.length) worn[slot] = names;
                }
                const approved = await (window as unknown as AVWin).AutoDressModal.show({
                    character: charName,
                    items: chosen,
                    context,
                    worn,
                    note,
                });
                if (!approved) {
                    events?.log?.('Auto-dress cancelled; nothing was equipped.', 'system-msg');
                    return;
                }
                libraryIds = approved;
            }

            const body: Record<string, any> = { character: charName };
            if (libraryIds) body.library_ids = libraryIds;
            const resp = await fetch('/api/auto_dress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await resp.json();
            const msg = data?.output || 'Auto-dress finished.';
            toastSuccess(msg.split('\n')[0]);
            events?.log?.(msg, 'system-msg');
            if (libraryIds) {
                events?.log?.(`Auto-dress selection (${data?.selection || 'llm'}): ${libraryIds.join(', ')}`, 'system-msg');
            }
            if (note) events?.log?.(note, 'system-msg');
            await worldState.fetch();
            if (window.VW?.inspector?.showAgent) VW.inspector.showAgent(charName);
        } catch (e) {
            toastError('Auto-dress failed: ' + (e as Error).message);
        }
    };

    /**
     * Union generated picks into the tags a human already placed by hand.
     *
     * The generators ADD, they never overwrite: a tag someone typed into the
     * multiselect is authoring and the LLM has no way to know it mattered.
     * Existing entries keep their position and their spelling; only genuinely
     * new ids are appended, matched case-insensitively because the engine's
     * tag matcher (`engine/fear.py::_normalise`, the interest equivalent)
     * lowercases anyway. Pure so the mechanism is unit-testable.
     *
     * @param {Array} existing - Tags currently on the character
     * @param {Array} picked - Tags the LLM chose, already validated
     * @returns {Array} Existing tags plus the new ones, no duplicates
     */
    AV._mergeGeneratedTags = function(existing: any[], picked: any[]): string[] {
        const merged: string[] = [];
        const seen = new Set<string>();
        for (const tag of [...(Array.isArray(existing) ? existing : []), ...(Array.isArray(picked) ? picked : [])]) {
            const text = String(tag ?? '').trim();
            const key = text.toLowerCase();
            if (!key || seen.has(key)) continue;
            seen.add(key);
            merged.push(text);
        }
        return merged;
    };

    /**
     * Fold a model-supplied tag into a usable id.
     *
     * A tag the vocabulary already knows is returned UNCHANGED. That matters:
     * the real data contains ids outside [a-z0-9_-] — `faction:goblin`,
     * `held_by:goblin`, `taco bell` — and an earlier version rewrote them to
     * `faction-goblin`, offering the model ids that cannot match anything while
     * claiming they were in use. Reshaping is only safe for ids we invented.
     * @param {*} tag - Raw tag from the model
     * @param {Set<string>} [known] - Ids that already exist; passed through as-is
     * @returns {string} Normalized id, or '' if nothing usable was left
     */
    AV._normalizeGeneratedTag = function(tag: unknown, known?: Set<string>): string {
        const text = String(tag ?? '').trim().toLowerCase();
        if (!text) return '';
        if (known && known.has(text)) return text;
        return text.replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '');
    };

    /**
     * Singular forms to try when a model returns a plural.
     *
     * Strictly plural inflection, no fuzzy guessing: `tools` -> `tool`,
     * `weapons` -> `weapon`, `mechanisms` -> `mechanism`, `bodies` -> `body`.
     * A caller accepts a form only when that form exists in the vocabulary, so
     * an id with no singular (`wanderer`, `squire`) yields no candidate and
     * cannot be mangled. This is deliberately NOT difflib — the existing
     * `/api/tags/validate` matcher at cutoff 0.6 suggests `wanderer ->
     * underwear` and `fear -> footwear`, which is worse than no suggestion.
     * @param {string} id
     * @returns {string[]} Candidate singulars, most likely first
     */
    AV._singularVariants = function(id: string): string[] {
        const out: string[] = [];
        if (id.endsWith('ies')) out.push(`${id.slice(0, -3)}y`);
        if (id.endsWith('es')) out.push(id.slice(0, -2));
        if (id.endsWith('s') && !id.endsWith('ss')) out.push(id.slice(0, -1));
        return out;
    };

    /**
     * Ground one free-text concept from the model onto real tag ids.
     *
     * The model is asked for short noun phrases ("worn iron tools"), because a
     * bare id it invents is as likely to be `iron_tools` as `tool`. Resolution
     * therefore tries the whole phrase first, then each word and each word's
     * singular — so "a goblin chief" yields both ids rather than only the first.
     *
     * Deliberately no fuzzy fallback. When nothing real matches, the head noun
     * is kept as a new id and the caller reports it as carrying nothing, which
     * is a far better outcome than the alternative the repo already has:
     * `/api/tags/validate` at cutoff 0.6 suggests `wanderer -> underwear` and
     * `fear -> footwear`, silently substituting a worse tag than the one it
     * rejected.
     *
     * @param {string} concept - What the model said
     * @param {object} vocab - {live, library, known} id collections
     * @returns {Array<{id: string, status: 'live'|'library'|'new', via: string}>}
     */
    AV._resolveConcept = function(concept: string, vocab: { live: Set<string>; library: Set<string>; known: Set<string> }): any[] {
        const words = String(concept ?? '').trim().toLowerCase().split(/[\s/]+/).filter(Boolean);
        if (!words.length) return [];
        const found: any[] = [];
        // A candidate only ever becomes a tag if it is a REAL id, directly or
        // through its singular. Unmatched words are not tags: letting them be
        // would turn "worn iron tools" into `worn`, `iron` and `tools` as well.
        const push = (candidate: string) => {
            const id = AV._normalizeGeneratedTag(candidate, vocab.known);
            if (!id) return null;
            if (vocab.live.has(id)) return { id, status: 'live' };
            if (vocab.library.has(id)) return { id, status: 'library' };
            for (const form of AV._singularVariants(id)) {
                const singular = AV._normalizeGeneratedTag(form, vocab.known);
                if (vocab.live.has(singular)) return { id: singular, status: 'live' };
                if (vocab.library.has(singular)) return { id: singular, status: 'library' };
            }
            return null;
        };
        const add = (hit: any) => {
            if (hit && !found.some(f => f.id === hit.id)) found.push({ ...hit, via: concept });
        };
        add(push(words.join('-')));
        for (const word of words) add(push(word));
        if (found.length) return found;
        // Nothing real anywhere: keep the head noun so the idea is not lost, and
        // let the caller report it as carrying nothing.
        const head = AV._normalizeGeneratedTag(words[words.length - 1], vocab.known);
        return head ? [{ id: head, status: 'new', via: concept }] : [];
    };

    /**
     * Gather the tag vocabulary, as lookup sets rather than as prompt material.
     *
     * Nothing here is ever shown to the model. The ids used to be pasted into
     * the prompt as a 660-entry menu, which cost more tokens than the character
     * description and invited the model to pick ids by resemblance to the menu
     * instead of by what the character would want. Grounding is a local string
     * operation, so the vocabulary belongs on this side of the boundary.
     *
     *   live     — what a tag is matched against for the field being generated
     *              (items for interests, anything present for fears)
     *   library  — the curated tag registry: a real id, but nothing carries it
     *   known    — union of the above; ids passed through normalization intact
     *
     * Reads only. It never POSTs to /api/library/tags, which is an upsert by id
     * (see write_library_entry) and would overwrite a curated entry's
     * description/colour/icon with the generic auto-generated blob.
     *
     * @returns {Promise<{live: Set, library: Set, known: Set}>}
     */
    AV._collectTagVocabulary = async function() {
        const live = new Set<string>();
        const library = new Set<string>();
        const add = (set: Set<string>, tag: unknown) => {
            const text = String(tag ?? '').trim().toLowerCase();
            if (text) set.add(text);
        };
        // Everything present right now: character tags, trait keys (a fear
        // source is usually a person), and every node's own tags.
        for (const p of Object.values((worldState.players || {}) as Record<string, any>)) {
            for (const t of (p.tags || [])) add(live, t);
            for (const key of Object.keys(p.traits || {})) add(live, key);
        }
        for (const n of Object.values((worldState.data?.graph?.nodes || {}) as Record<string, any>)) {
            for (const t of (n.properties?.tags || [])) add(live, t);
        }
        try {
            const tags = await (await fetch('/api/tags/search')).json();
            for (const t of (Array.isArray(tags) ? tags : (tags?.tags || []))) add(library, t?.id ?? t);
        } catch (e) { /* grounding still works, everything reads as new */ }
        for (const t of live) library.delete(t);
        return { live, library, known: new Set([...live, ...library]) };
    };

    /**
     * Item tags, which are what `interest_tags` is actually matched against.
     * Kept separate from the "live" set above because a character tag is live
     * for a fear and useless for an interest.
     *
     * `/api/library/items` answers with an id-keyed OBJECT, not a list — the
     * previous generator read it as an array, silently got nothing back, and
     * fell through to its graph-node fallback, which is why the "library"
     * vocabulary it showed was never the library at all.
     * @returns {Promise<Set<string>>}
     */
    AV._collectItemTags = async function() {
        const set = new Set();
        try {
            const payload = await (await fetch('/api/library/items')).json();
            const entries = Array.isArray(payload) ? payload : Object.values(payload || {});
            for (const item of entries) {
                for (const t of (item?.tags || [])) {
                    const text = String(t).trim().toLowerCase();
                    if (text) set.add(text);
                }
            }
        } catch (e) { /* grounding degrades to 'new', nothing breaks */ }
        return set;
    };

    /**
     * Ask the character (personality + appearance as context) which tags suit
     * them, and write the picks to *field* on the character.
     *
     * Shared by the interest and fear generators; only the instruction line
     * differs. The model is shown the world and library vocabularies and is
     * explicitly allowed to invent ids outside them, so its picks are NOT
     * filtered against the vocabulary — only normalized and capped. The picks
     * are then unioned into whatever is already on the character (see
     * _mergeGeneratedTags), never replacing hand-placed tags.
     *
     * @param {object} opts
     * @param {string} opts.charName - Character name
     * @param {string} opts.field - Player field to write ('interest_tags' | 'fear_tags')
     * @param {{world: string[], library: string[]}} opts.vocabulary - Ids to suggest
     * @param {string} opts.ask - The instruction line describing what to pick
     * @param {string} opts.contextNote - What the ids are matched AGAINST. Not
     *   optional: without it the model has no idea what its picks will be tested
     *   against and answers from the personality prose instead of the mechanic.
     * @param {'world'|'library'} [opts.listOrder] - Which vocabulary to show first
     * @param {string} opts.toastPrefix - Prefix for the success/warning toasts
     * @param {number} opts.limit - Max tags to accept from the model
     * @returns {Promise<void>}
     */
    AV._generateTagsFromPersonality = async function({ charName, field, vocab, ask, contextNote, toastPrefix, limit }: { charName: string; field: string; vocab: { live: Set<string>; library: Set<string>; known: Set<string> }; ask: (prompt: string) => Promise<string>; contextNote: string; toastPrefix: string; limit: number }) {
        const player = worldState.players?.[charName];
        if (!player || !AIGenerator.isConfigured()) return;

        const personality = player.personality || '';
        const appearance = (player.description || player.base_description || '').slice(0, 600);
        // No tag menu. The model is given the character and the mechanic and
        // asked what kinds of things this person would care about, in its own
        // words. Grounding to real ids is a local operation (see _resolveConcept)
        // and does not need the model to see a 660-entry list to do it.
        const prompt = `You are ${charName}. Here is who you are:

PERSONALITY
${personality || '(none)'}

APPEARANCE
${appearance}

${contextNote}

${ask}

Name at most ${limit} of them as short, plain noun phrases - one or two words each, the everyday word for the thing ("iron tools", "coarse bread", "a good blade"), not a long compound id. Return only what you are genuinely confident about; a short list is much better than a padded one.

Respond with ONLY a JSON object: {"tags": ["iron tools","coarse bread"]}`;

        try {
            const response = await llmClient.chat([{ role: 'user', content: prompt }], { temperature: 0.5, responseFormat: (window as unknown as AVWin).StructuredFormats?.tags, label: field === 'fear_tags' ? 'inspector/generate-fear-tags' : 'inspector/generate-interest-tags' });
            const text = String(response || '').trim();
            // Structured output returns {"tags":[...]}; the old raw-array
            // contract stays accepted for the plain-prompt fallback path.
            let parsedList = null;
            try {
                const parsed = JSON.parse(text);
                parsedList = Array.isArray(parsed) ? parsed : (Array.isArray(parsed?.tags) ? parsed.tags : null);
            } catch (e) { /* fall through to regex extraction */ }
            let concepts = parsedList;
            if (!concepts) {
                const match = text.match(/\[[^\]]*\]/);
                if (!match) { toastError('The character returned no tag list.'); return; }
                try { concepts = JSON.parse(match[0]); } catch (e) {
                    concepts = match[0].replace(/[\[\]"']/g, '').split(',').map(s => s.trim()).filter(Boolean);
                }
            }

            // Ground each concept. One concept can name several real things
            // ("a goblin chief"), and the strongest match wins if the same id
            // arrives twice.
            const resolved: any[] = [];
            for (const concept of concepts) {
                for (const hit of AV._resolveConcept(concept, vocab)) {
                    const seen = resolved.find((r: any) => r.id === hit.id);
                    if (seen) { if (hit.status === 'live') seen.status = 'live'; continue; }
                    resolved.push(hit);
                }
            }
            const chosen = resolved.slice(0, limit);
            if (!chosen.length) { toastWarning('The character returned no usable tags.'); return; }

            const existing = Array.isArray(player[field]) ? player[field] : [];
            const merged = AV._mergeGeneratedTags(existing, chosen.map(c => c.id));
            const added = chosen.filter(c => !existing.some(e => String(e).toLowerCase() === c.id.toLowerCase()));
            await ApiClient.updateCharacter(charName, { [field]: merged });

            // Report what will actually work. A tag nothing carries is
            // indistinguishable from a live one in the multiselect, so the
            // split is stated at the moment it is created rather than left to
            // be discovered.
            const live = added.filter(c => c.status === 'live').map(c => c.id);
            const idle = added.filter(c => c.status !== 'live').map(c => c.id);
            const kept = merged.length - added.length;
            const parts = [`${toastPrefix}: ${added.map(c => c.id).join(', ')}`];
            if (live.length) parts.push(`${live.length} ${live.length === 1 ? 'matches' : 'match'} something here`);
            if (idle.length) parts.push(`${idle.length} nothing carries yet: ${idle.join(', ')}`);
            if (kept) parts.push(`${kept} kept`);
            toastSuccess(parts.join(' · '));
            await worldState.fetch();
            if (window.VW?.inspector?.showAgent) VW.inspector.showAgent(charName);
        } catch (e) {
            toastError(`${toastPrefix} generation failed: ${(e as Error).message}`);
        }
    };

    /**
     * Side-effect-free provider check. `AIGenerator.isConfigured()` toasts when
     * it is false, so it must not be called from render — only from a click.
     * @returns {boolean}
     */
    AV._isAiConfigured = function() {
        return !!(typeof config !== 'undefined' && config && config.apiKey && config.model);
    };

    /**
     * LLM interest-tag generator (task-325). interest_tags is matched against
     * items only — the room attention list scores an item by exact tag match or
     * by the tag appearing in the item's name (room-context.js:305-307), and
     * auto-dress scans item tags (dressing.py:62). So "live" for this field
     * means an item carries the id, which is why it collects item tags rather
     * than the world's. Picks are unioned into hand-placed tags.
     * @param {string} charName - Character name
     */
    AV._generateInterestTags = async function(charName: string) {
        // bug-514: check before the async tag/vocabulary collection, so the
        // "not configured" toast is immediate. When it lived inside
        // `_generateTagsFromPersonality` the collection could take long enough
        // that the click looked like it did nothing.
        if (!(AIGenerator as unknown as { isConfigured(): boolean }).isConfigured()) return;
        const items = await AV._collectItemTags();
        const base = await AV._collectTagVocabulary();
        const vocab = { live: items, library: base.library, known: new Set([...items, ...base.live, ...base.library]) };
        await AV._generateTagsFromPersonality({
            charName,
            field: 'interest_tags',
            vocab,
            // The whole point of the note: the field has exactly one kind of
            // consumer, and it is items. A mood or a self-description cannot
            // reach it however well it describes the person — "wary", "lonely",
            // "desperation" are not things a character is interested in.
            contextNote: 'IMPORTANT — what an interest is matched against: it surfaces a thing only when some ITEM carries that id as a tag, or has that word in its name. So name categories of STUFF this character would seek out or notice — materials, tools, food, drink, weapons, clothing, valuables, trade goods. Do NOT name feelings or descriptions of the person.',
            ask: 'Given who they are, what kinds of things would this character actually be drawn to?',
            toastPrefix: 'Interest tags',
            limit: 8
        });
    };

    /**
     * LLM fear-tag generator. fear_tags is matched against characters, areas and
     * held items (engine/fear.py::character_tags unions `tags`, trait keys and
     * the graph node's tags), so here "live" genuinely means the world
     * vocabulary — a character tag is exactly what this field wants, unlike an
     * interest. Picks are unioned into hand-placed tags.
     * @param {string} charName - Character name
     */
    AV._generateFearTags = async function(charName: string) {
        // bug-514: immediate feedback, before the async vocabulary collection.
        if (!(AIGenerator as unknown as { isConfigured(): boolean }).isConfigured()) return;
        const vocab = await AV._collectTagVocabulary();
        await AV._generateTagsFromPersonality({
            charName,
            field: 'fear_tags',
            vocab,
            contextNote: 'IMPORTANT — what a fear is matched against: it bites when a co-located CHARACTER presents that id (their tags, or their traits), when the AREA they stand in carries it, or when an item held there carries it. So name kinds of person, creature or place rather than feelings. If nothing would genuinely frighten this character, say so with an empty list.',
            ask: 'Given who they are, what would frighten this character specifically? Not what they dislike or find tedious.',
            toastPrefix: 'Fear tags',
            limit: 8
        });
    };

    /**
     * Save description and base description from inspector textareas
     * @param {string} charName - Character name
     */
    AV._saveDescription = function(charName: string) {
        return (window as unknown as AVWin).InspectorHelpers.saveDescription(charName);
    };

    /**
     * Build the canonical character library payload from live world state.
     * This is the single source of truth for saving to the library AND for
     * exporting — both must produce the same shape so exports round-trip
     * back into the library without data loss.
     *
     * `inventory` is stored as structured entries `{name, library_id, node_id}`
     * so imports can re-link items from the library (or rebuild them) instead
     * of guessing from a bare name.
     * @param {string} charName - Character name
     * @returns {object} Character card in library format
     */
    AV._buildCharacterCard = function(charName: string) {
        const player = worldState.players[charName];
        if (!player) return null;
        const charNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        const charProps = worldState.getNode(charNodeId)?.properties || {};
        const inventory = [];
        const seen = new Set();
        for (const edge of worldState.graph?.edges || []) {
            if (edge.target !== charNodeId) continue;
            if (edge.type !== 'carrying' && edge.type !== 'equipped') continue;
            if (seen.has(edge.source)) continue;
            seen.add(edge.source);
            const node = worldState.getNode(edge.source);
            if (!node || node.type !== 'item') continue;
            inventory.push({
                name: node.name,
                node_id: edge.source,
                library_id: node.properties?.library_id || null,
                properties: node.properties || {},
            });
        }
        return {
            name: charName,
            personality: player.personality || '',
            description: player.description || '',
            base_description: player.base_description || '',
            unknown_name: player.unknown_name || '',
            stats: player.stats || {},
            vitals: player.vitals || {},
            decay_rates: player.decay_rates || {},
            skills: player.skills || {},
            traits: player.traits || {},
            tags: player.tags || [],
            interest_tags: player.interest_tags || [],
            // Expression pack (profile/full body per emotion or action).
            image: charProps.image || null,
            profile_image: charProps.profile_image || null,
            expressions: charProps.expressions || {},
            state: player.state || 'awake',
            conditions: player.conditions || {},
            equipped: (() => {
                const eq: Record<string, any[]> = {};
                for (const [slot, stack] of Object.entries(player.equipped || {})) {
                    eq[slot] = (Array.isArray(stack) ? stack : []).map((id: any) => {
                        const n = worldState.getNode(id);
                        return { name: n?.name || id, node_id: id, library_id: n?.properties?.library_id || null, properties: n?.properties || {} };
                    });
                }
                return eq;
            })(),
            activity: player.activity || null,
            current_area: player.current_area,
            inventory,
            emotion: player.emotion && typeof player.emotion === 'object'
                ? player.emotion
                : { current: player.emotion || 'neutral', intensity: 0 },
            memories: player.memories || [],
            relationships: player.relationships || {},
            behaviors: player.behaviors || [],
            npc_behavior: player.npc_behavior || 'wander',
            npc_action_interval: player.npc_action_interval ?? 3,
            npc_state: player.npc_state || 'idle',
            simple_npc: player.simple_npc || false,
            recent_hearing: player.recent_hearing || [],
        };
    };

    /**
     * Save character to registry
     * @param {string} charName - Character name
     */
    AV._saveCharacter = async function(charName: string) {
        const charCard = AV._buildCharacterCard(charName);
        if (!charCard) return;

        let libEntry = null;
        try {
            const libData = await (ApiClient as Record<string, any>).getLibraryType('characters');
            libEntry = libData[charName] || null;
        } catch (e) { /* ignore */ }

        if (!libEntry) {
            const res = await (ApiClient as Record<string, any>).saveLibraryType('characters', { id: charName, ...charCard });
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            events.log(`Character "${charName}" saved to library.`, 'system-msg');
            return;
        }

        const sections = [
            { key: 'personality', label: 'Personality' },
            { key: 'description', label: 'Description' },
            { key: 'stats', label: 'Stats' },
            { key: 'skills', label: 'Skills' },
            { key: 'traits', label: 'Traits' },
            { key: 'tags', label: 'Tags' },
            { key: 'expressions', label: 'Expression Pack' },
            { key: 'image', label: 'Full-body image' },
            { key: 'profile_image', label: 'Profile image' },
            { key: 'emotion', label: 'Emotion' },
            { key: 'vitals', label: 'Vitals', perEntry: true },
            { key: 'decay_rates', label: 'Decay Rates', perEntry: true },
            { key: 'conditions', label: 'Conditions', perEntry: true },
            { key: 'equipped', label: 'Equipped', perEntry: true },
            { key: 'relationships', label: 'Relationships', perEntry: true },
            { key: 'memories', label: 'Memories', perEntry: true },
            { key: 'behaviors', label: 'Behaviours' },
            { key: 'npc_behavior', label: 'NPC Config' },
            { key: 'inventory', label: 'Items', perEntry: true }
        ];

        const result = await DiffModal.show(libEntry, charCard, sections, {
            title: 'Save Character to Library',
            name: charName
        });
        if (!result) return;

        if (result.action === 'update') {
            const merged = { ...libEntry, id: charName };
            for (const key of result.sections) {
                merged[key] = charCard[key];
            }
            const res = await (ApiClient as Record<string, any>).saveLibraryType('characters', merged);
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            events.log(`Character "${charName}" updated in library.`, 'system-msg');
        } else if (result.action === 'duplicate') {
            const dupePayload = { id: result.id, name: result.name, ...charCard };
            const res = await (ApiClient as Record<string, any>).saveLibraryType('characters', dupePayload);
            if (res.error) { events.log(`Failed to save: ${res.error}`, 'error-msg'); return; }
            events.log(`Character "${result.name}" saved as duplicate to library.`, 'system-msg');
        }
    };

    /**
     * Import character from JSON file — loads arbitrary JSON into the WORLD as
     * an active player (not the library). Distinct from "Add from Library":
     * no library entry required; sets active player and inventory edges.
     */
    AV._importCharacter = async function() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.style.display = 'none';
        document.body.appendChild(input);
        input.onchange = async () => {
            document.body.removeChild(input);
            const file = input.files?.[0];
            if (!file) return;
            try {
                const text = await file.text();
                const data = JSON.parse(text);
                if (!data.name) { events.log('Invalid character file: missing name.', 'error-msg'); return; }
                const res = await (ApiClient as Record<string, any>).importPlayer(data);
                if (res.error) { events.log(`Import failed: ${res.error}`, 'error-msg'); return; }
                events.log(`Character "${data.name}" imported!`, 'system-msg');
                await worldState.fetch();
                AV.showAgent(data.name);
            } catch (error) {
                events.log(`Import error: ${(error as Error).message}`, 'error-msg');
            }
        };
        input.click();
    };

    /**
     * Kill a character
     * @param {string} charName - Character name
     */
    AV._killCharacter = async function(charName: string) {
        if (!confirm(`Kill "${charName}"? This will set HP to 0 and state to dead.`)) return;
        const res = await (ApiClient as Record<string, any>).killCharacter(charName);
        if (res.error) { events.log(`Kill failed: ${res.error}`, 'error-msg'); return; }
        events.log(`"${charName}" has been killed.`, 'system-msg');
        await worldState.fetch();
        if (window.VW?.inspector) window.VW.inspector.showAgent(charName);
    };

    /**
     * Permanently remove a character from the world
     * @param {string} charName - Character name
     */
    AV._removeCharacter = async function(charName: string) {
        if (!confirm(`Permanently remove "${charName}" from the world? This cannot be undone.`)) return;
        const res = await (ApiClient as Record<string, any>).deleteCharacter(charName);
        if (res.error) {
            // Not a registered player (e.g. a bare character node) — fall back
            // to deleting the graph node itself so the node can always be removed.
            const nodeId = `player_${charName.replace(/\s+/g, '_')}`;
            const fallback = await (ApiClient as Record<string, any>).deleteNode(nodeId);
            if (fallback.error) {
                events.log(`Remove failed: ${res.error}`, 'error-msg');
                return;
            }
            events.log(`"${charName}" removed (bare graph node, no player state).`, 'system-msg');
            await worldState.fetch();
            if (window.VW?.inspector) window.VW.inspector.hide();
            return;
        }
        events.log(`"${charName}" has been removed from the world.`, 'system-msg');
        await worldState.fetch();
        if (window.VW?.inspector) window.VW.inspector.hide();
    };

    /**
     * Show expanded detail for a timeline entry
     * @param {string} charName - Character name
     * @param {number} entryIndex - Index of the timeline entry
     * @param {HTMLElement} entryEl - The clicked timeline entry element
     */
    AV._showTimelineDetail = function(charName: string, entryIndex: number, entryEl: HTMLElement) {
        const charState = events.getCharacterState(charName);
        const timeline = charState.detailedTimeline || [];
        if (entryIndex < 0 || entryIndex >= timeline.length) return;
        const entry = timeline[entryIndex];

        const detailContainer = document.getElementById(`timeline-detail-${charName.replace(/'/g, "\\'")}`);
        if (!detailContainer) return;

        // Toggle: if already showing this entry, hide it
        if (detailContainer.style.display !== 'none' && detailContainer.dataset.index === String(entryIndex)) {
            detailContainer.style.display = 'none';
            document.querySelectorAll('.timeline-entry.active').forEach(el => el.classList.remove('active'));
            return;
        }

        // Show active state on the clicked entry
        document.querySelectorAll('.timeline-entry.active').forEach(el => el.classList.remove('active'));
        if (entryEl) entryEl.classList.add('active');

        const phaseIcons: Record<string, string> = { think: '💭', decide: '🎯', act: '⚡', action: '⚡', result: '→', react: '🔄', speech: '💬', observe: '👁️' };
        const phase = entry.phase || 'unknown';
        const phaseIcon = phaseIcons[phase] || '•';

        const detailRows: any[] = [];
        detailRows.push(agentViewTag`<div class="timeline-detail-row">
            <span class="timeline-detail-label">Phase</span>
            <span class="timeline-detail-value">${phaseIcon} ${phase} (${events.tickToTime(entry.tick || 0)})</span>
        </div>`);

        if (entry.thought) {
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">💭 Thought</span>
                    <span class="timeline-detail-value" style="font-style:italic;color:var(--purple);">${entry.thought}</span>
                </div>`);
        }

        if (entry.speech) {
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">💬 Said</span>
                    <span class="timeline-detail-value" style="color:var(--pink);">"${entry.speech}"</span>
                </div>`);
        }

        if (entry.action) {
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">⚡ Action</span>
                    <span class="timeline-detail-value" style="color:var(--accent);font-weight:500;font-family:var(--font-mono);">${entry.action}</span>
                </div>`);
        }

        if (entry.result) {
            const isError = entry.result.toLowerCase().includes('valueerror') || entry.result.toLowerCase().includes("don't");
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">→ Result</span>
                    <span class="timeline-detail-value" style="color:${isError ? 'var(--red)' : 'var(--orange)'};">${entry.result}</span>
                </div>`);
        }

        if (entry.message) {
            detailRows.push(agentViewTag`<div class="timeline-detail-divider"></div>
                <div class="timeline-detail-row">
                    <span class="timeline-detail-label">📝 Message</span>
                    <span class="timeline-detail-value">${entry.message}</span>
                </div>`);
        }

        window.Lit.render(agentViewTag`<div class="timeline-detail">${detailRows}</div>`, detailContainer);
        detailContainer.style.display = 'block';
        detailContainer.dataset.index = String(entryIndex);
    };

    /**
     * Remove a relationship between two characters
     * @param {string} agentName - Character name
     * @param {string} otherName - Other character name
     */
    AV._removeRelationship = async function(agentName: string, otherName: string) {
        if (!agentName || !otherName) return;
        await ApiClient.updateCharacter(agentName, { relationships: { [otherName]: null } });
        worldState.fetch().then(() => {
            if (window.VW?.inspector) window.VW.inspector.showAgent(agentName);
        });
    };

    /**
     * Show a modal to pick an item to add to inventory
     * @param {string} charName - Character name
     */
    AV._showAddItemPicker = async function(charName: string) {
        // Held items are identified by ID (see getInventoryIds): a name
        // comparison hides distinct same-named items and re-offers held ones.
        const heldIds = new Set(worldState.getInventoryIds(charName));
        const playerNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        const currentArea = worldState.players[charName]?.current_area || '';

        const graphNodes = Object.entries((worldState.graph?.nodes || {}) as Record<string, any>)
            .filter(([id, node]: [string, any]) => node.type === 'item')
            .filter(([id]) => !heldIds.has(id));

        const libraryData = await (ApiClient as Record<string, any>).getLibraryItems().catch(() => ({}));
        // A library entry is "already here" when a world node records it as its
        // source (`properties.library_id`), which is identity by id rather than
        // by display name.
        const placedLibraryIds = new Set();
        for (const node of Object.values((worldState.graph?.nodes || {}) as Record<string, any>)) {
            if (node?.type !== 'item') continue;
            const libId = node.properties?.library_id;
            if (libId) placedLibraryIds.add(String(libId));
        }
        const libraryNodes = Object.entries(libraryData as Record<string, any>)
            .filter(([id]) => !placedLibraryIds.has(String(id)));

        function getItemTags(source: string, item: any, node: any) {
            const raw = source === 'graph' ? node?.properties?.tags : item?.tags || item?.properties?.tags;
            if (Array.isArray(raw)) return raw.map((t: any) => String(t).toLowerCase()).join(',');
            if (typeof raw === 'string') return raw.toLowerCase();
            return '';
        }

        function renderItem(id: string, name: string, source: string, tagsStr: string) {
            const lower = name.toLowerCase();
            const isLib = source === 'library';
            const badge = isLib ? agentViewTag`<span style="font-size:9px;color:var(--text-muted);margin-left:4px;">(library)</span>` : '';
            return agentViewTag`<div data-name=${lower} data-tags=${tagsStr} style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid var(--border);">
                <span style="font-size:11px;">📦 ${name}${badge}</span>
                <button class="btn btn-sm btn-blue" @click=${(e: any) => {
                    e.currentTarget.closest('.modal-overlay').remove();
                    if (isLib) {
                        (ApiClient as Record<string, any>).placeItemFromLibrary({ type: 'character', id: playerNodeId }, id).then(() => worldState.fetch());
                    } else {
                        fetch(`/api/graph/item/${id}/move`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ area: currentArea }) })
                            .then(r => r.json())
                            .then(() => runAction(`take ${name}`, charName));
                    }
                }}>Add</button>
            </div>`;
        }

        const allNodes = [
            ...graphNodes.map(([id, node]: [string, any]) => renderItem(id, node.name, 'graph', getItemTags('graph', null, node))),
            ...libraryNodes.map(([id, item]: [string, any]) => renderItem(id, item.name || id, 'library', getItemTags('library', item, null)))
        ];

        const picker = document.createElement('div');
        picker.className = 'modal-overlay';
        picker.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        window.Lit.render(agentViewTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:350px;max-height:80vh;overflow-y:auto;">
            <h3 style="margin:0 0 12px 0;">Add Item to Inventory</h3>
            <input type="text" id="add-item-filter" placeholder="Search items or tags..." style="width:100%;font-size:11px;padding:4px;margin-bottom:8px;" @input=${(e: any) => {
                const t = e.target.value.toLowerCase();
                e.target.nextElementSibling.querySelectorAll('[data-name]').forEach((el: any) => el.style.display = (el.getAttribute('data-name').includes(t) || (el.getAttribute('data-tags') || '').includes(t)) ? 'flex' : 'none');
            }}>
            <div style="max-height:50vh;overflow-y:auto;">
                ${allNodes}
            </div>
            <button class="btn btn-sm" @click=${(e: any) => e.currentTarget.closest('.modal-overlay').remove()} style="margin-top:8px;width:100%;">Cancel</button>
        </div>`, picker);
        document.body.appendChild(picker);
        setTimeout(() => document.getElementById('add-item-filter')?.focus(), 100);
    };

    AV._removeKnownAbility = function(charName: string, abilityId: string) {
        const playerNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        fetch(`/api/graph/edge`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: abilityId, target: playerNodeId, type: 'known' })
        }).then(() => worldState.fetch());
    };

    AV._showAddKnownAbilityPicker = function(charName: string) {
        // Identification is by ID, never by name: three characters can each know
        // a "Fireball" and a camp can hold two items called "Bag", so a name
        // comparison both hides distinct items and re-offers held ones.
        const heldIds = new Set(worldState.getInventoryIds(charName));
        // Library entries are not world nodes yet, so the id that matters is the
        // provenance link a placed node records (`properties.library_id`, the key
        // world-sync matches on first).
        const placedLibraryIds = new Set<any>();
        for (const node of Object.values((worldState.graph?.nodes || {}) as Record<string, any>)) {
            if (node?.type !== 'item') continue;
            const libId = node.properties?.library_id;
            if (libId) placedLibraryIds.add(String(libId));
        }
        const playerNodeId = `player_${charName.replace(/\s+/g, '_')}`;
        const currentArea = worldState.players[charName]?.current_area || '';
        const INTRINSIC = new Set(['spell', 'ability', 'innate', 'intrinsic', 'power']);

        const graphNodes = Object.entries((worldState.graph?.nodes || {}) as Record<string, any>)
            .filter(([id, node]: [string, any]) => {
                if (node.type !== 'item') return false;
                if (heldIds.has(id)) return false;
                const tags = (node.properties?.tags || []);
                const tagSet = Array.isArray(tags) ? tags.map((t: any) => String(t).toLowerCase()) : String(tags).toLowerCase().split(',');
                return [...tagSet].some((t: string) => INTRINSIC.has(t));
            })
            .map(([id, node]: [string, any]) => ({ id, name: node.name, tags: node.properties?.tags || [] }));

        const libraryData = (ApiClient as Record<string, any>).libraryCache?.items || {};
        const libraryNodes = Object.entries(libraryData as Record<string, any>)
            .filter(([id, item]: [string, any]) => {
                if (placedLibraryIds.has(String(id))) return false;
                const tags = item.tags || item.properties?.tags || [];
                const tagSet = Array.isArray(tags) ? tags.map((t: any) => String(t).toLowerCase()) : String(tags).toLowerCase().split(',');
                return [...tagSet].some((t: string) => INTRINSIC.has(t));
            })
            .map(([id, item]: [string, any]) => ({ id, name: item.name || id, tags: item.tags || item.properties?.tags || [] }));

        function renderItem(id: string, name: string, source: string, tagsStr: string) {
            const lower = name.toLowerCase();
            const isLib = source === 'library';
            const badge = isLib ? agentViewTag`<span style="font-size:9px;color:var(--text-muted);margin-left:4px;">(library)</span>` : '';
            return agentViewTag`<div data-name=${lower} data-tags=${tagsStr} data-node-id=${id} style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid var(--border);">
                <span style="font-size:11px;">✨ ${name}${badge}</span>
                <button class="btn btn-sm btn-blue" @click=${(e: any) => {
                    e.currentTarget.closest('.modal-overlay').remove();
                    if (isLib) {
                        // Library abilities live outside the world graph. Place the
                        // item node into the world (server creates a unique id and
                        // an EDGE_CARRYING edge), then swap the carry edge for a
                        // known-only edge so the ability is "known" without being
                        // physically carried.
                        (ApiClient as Record<string, any>).placeItemFromLibrary({ type: 'character', id: playerNodeId }, id)
                            .then(async (placed: any) => {
                                const newId = placed?.node_id;
                                if (!newId) return;
                                await fetch('/api/graph/edge', {
                                    method: 'DELETE',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ source: newId, target: playerNodeId, type: 'carrying' })
                                }).catch(() => {});
                                await fetch('/api/graph/edge', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ source: newId, target: playerNodeId, type: 'known' })
                                });
                                worldState.fetch();
                            })
                            .catch(() => worldState.fetch());
                    } else {
                        fetch('/api/graph/edge', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ source: id, target: playerNodeId, type: 'known' })
                        }).then(() => worldState.fetch());
                    }
                }}>Know</button>
            </div>`;
        }

        const allNodes = [
            ...graphNodes.map(({ id, name, tags }: any) => renderItem(id, name, 'graph', Array.isArray(tags) ? tags.join(',') : String(tags))),
            ...libraryNodes.map(({ id, name, tags }: any) => renderItem(id, name, 'library', Array.isArray(tags) ? tags.join(',') : String(tags)))
        ];

        const picker = document.createElement('div');
        picker.className = 'modal-overlay';
        picker.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        window.Lit.render(agentViewTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:350px;max-height:80vh;overflow-y:auto;">
            <h3 style="margin:0 0 12px 0;">Add Known Ability</h3>
            <input type="text" id="add-known-filter" placeholder="Search abilities or tags..." style="width:100%;font-size:11px;padding:4px;margin-bottom:8px;" @input=${(e: any) => {
                const t = e.target.value.toLowerCase();
                e.target.nextElementSibling.querySelectorAll('[data-name]').forEach((el: any) => el.style.display = (el.getAttribute('data-name').includes(t) || (el.getAttribute('data-tags') || '').includes(t)) ? 'flex' : 'none');
            }}>
            <div style="max-height:50vh;overflow-y:auto;">
                ${allNodes}
            </div>
            <button class="btn btn-sm" @click=${(e: any) => e.currentTarget.closest('.modal-overlay').remove()} style="margin-top:8px;width:100%;">Cancel</button>
        </div>`, picker);
        document.body.appendChild(picker);
        setTimeout(() => document.getElementById('add-known-filter')?.focus(), 100);
    };

    AV._showContainerPicker = function(charName: string, itemName: string, itemId: string) {
        const player = worldState.players[charName];
        const equipped = player?.equipped || {};
        // Containers are identified by node ID. Deduplicating by name merged two
        // distinct containers that happen to share one ("Bag"), and
        // `getNodeByIdentifier(name)` then resolved to whichever came first — so
        // "put in Bag" could target the wrong one.
        const candidates: Array<{ id: any; name: any }> = [];
        const seen = new Set<any>();
        const addCandidate = (nodeId: any) => {
            if (!nodeId || String(nodeId).startsWith('__')) return;
            if (seen.has(nodeId)) return;
            const node = worldState.getNode(nodeId) || worldState.getNodeByIdentifier(nodeId);
            if (!node || node.type !== 'item') return;
            const tags = node.properties?.tags || [];
            const list = Array.isArray(tags) ? tags : String(tags).toLowerCase().split(',');
            if (!list.some((tag: any) => String(tag).toLowerCase() === 'container')) return;
            seen.add(nodeId);
            candidates.push({ id: nodeId, name: node.name });
        };

        for (const nodeId of worldState.getInventoryIds(charName)) addCandidate(nodeId);
        for (const slot of Object.values(equipped)) {
            for (const nodeId of (Array.isArray(slot) ? slot : [slot])) addCandidate(nodeId);
        }
        const containers = candidates;

        const items = containers.length
            ? containers.map((c: any) => agentViewTag`<div data-name="${c.name.toLowerCase()}" data-node-id="${c.id}" style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid var(--border);">
                <span style="font-size:11px;">📦 ${c.name}</span>
                <button class="btn btn-sm btn-blue" @click=${(e: any) => { e.currentTarget.closest('.modal-overlay').remove(); runAction(`put ${itemName} in ${c.name}`, charName); }}>Put in</button>
            </div>`)
            : [agentViewTag`<div style="font-size:11px;color:var(--text-muted);padding:8px;">No containers in inventory.</div>`];


        const picker = document.createElement('div');
        picker.className = 'modal-overlay';
        picker.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        window.Lit.render(agentViewTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:350px;max-height:80vh;overflow-y:auto;">
            <h3 style="margin:0 0 12px 0;">Put ${itemName} in...</h3>
            <div style="max-height:50vh;overflow-y:auto;">
                ${items}
            </div>
            <button class="btn btn-sm" @click=${(e: any) => e.currentTarget.closest('.modal-overlay').remove()} style="margin-top:8px;width:100%;">Cancel</button>
        </div>`, picker);
        document.body.appendChild(picker);
    };

    // Register the template-sync pattern for characters. The diff only covers
    // author-editable fields — never runtime state (vitals, current_area,
    // memories, relationships, emotion, inventory, conditions, equipped).
    if ((window as unknown as AVWin).InspectorTemplateSync) {
        (window as unknown as AVWin).InspectorTemplateSync.register('character', {
            title: 'Refresh Character from Library',
            buildWorldPayload(nodeId: string, node: any) {
                const name = (node && node.name) || '';
                const player = worldState.players[name];
                if (!player) return null;
                return {
                    name,
                    personality: player.personality || '',
                    description: player.description || '',
                    base_description: player.base_description || '',
                    unknown_name: player.unknown_name || '',
                    stats: player.stats || {},
                    skills: player.skills || {},
                    traits: player.traits || {},
                    tags: player.tags || [],
                    interest_tags: player.interest_tags || [],
                    behaviors: player.behaviors || [],
                    npc_behavior: player.npc_behavior || 'wander',
                    npc_action_interval: player.npc_action_interval ?? 3,
                    npc_state: player.npc_state || 'idle',
                    simple_npc: player.simple_npc || false,
                    memories: player.memories || [],
                    relationships: player.relationships || {},
                    vitals: player.vitals || {},
                    decay_rates: player.decay_rates || {},
                    conditions: player.conditions || {},
                    equipped: player.equipped || {},
                    recent_hearing: player.recent_hearing || [],
                    activity: player.activity || null,
                    current_area: player.current_area || '',
                    emotion: (player.emotion && typeof player.emotion === 'object')
                        ? player.emotion
                        : { current: player.emotion || 'neutral', intensity: player.emotion_intensity || 0 },
                };
            },
            sections: [
                { key: 'personality', label: 'Personality' },
                { key: 'description', label: 'Description' },
                { key: 'base_description', label: 'Base Description' },
                { key: 'unknown_name', label: 'Unknown Name' },
                { key: 'stats', label: 'Stats' },
                { key: 'skills', label: 'Skills' },
                { key: 'traits', label: 'Traits' },
                { key: 'tags', label: 'Tags' },
                { key: 'interest_tags', label: 'Interest Tags' },
                { key: 'behaviors', label: 'Behaviours' },
                { key: 'npc_behavior', label: 'NPC Config' },
                { key: 'memories', label: 'Memories', perEntry: true },
                { key: 'relationships', label: 'Relationships', perEntry: true },
                { key: 'vitals', label: 'Vitals', perEntry: true },
                { key: 'decay_rates', label: 'Decay Rates', perEntry: true },
                { key: 'conditions', label: 'Conditions', perEntry: true },
                { key: 'equipped', label: 'Equipped', perEntry: true },
                { key: 'recent_hearing', label: 'Recent Hearing' },
                { key: 'activity', label: 'Activity' },
                { key: 'current_area', label: 'Current Area' },
                { key: 'emotion', label: 'Emotion' },
            ],
        });
    }

    return AV;
})();
