/**
 * InspectorBehaviors — Simple NPC behavior editor
 * task-216: renders lit-html templates via InspectorPanel / window.Lit.render.
 * The editor modal and action cards are TemplateResults with @click handlers;
 * inline on* attribute handlers are gone.
 */

window.InspectorBehaviors = (() => {
    const B = {};

    // Lazy tag: classic scripts parse before the deferred lit-bootstrap module
    // runs, so window.Lit only exists when a view actually renders.
    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

    /**
     * Get available behavior action types with their parameter schemas
     * @returns {Array<{value:string, label:string, params:string[]}>}
     */
    B.BEHAVIOR_ACTION_TYPES = function() {
        return [
            { value: 'message', label: '💬 Message', params: ['text'] },
            { value: 'speak', label: '🗣️ Speak', params: ['text'] },
            { value: 'set_npc_state', label: '🎭 Set NPC State', params: ['state'] },
            { value: 'damage', label: '💥 Damage', params: ['amount', 'damage_target'] },
            { value: 'heal', label: '❤️ Heal', params: ['amount', 'heal_stat', 'heal_target'] },
            { value: 'set_environment', label: '🌡️ Set Environment', params: ['env_stat', 'env_amount', 'env_area'] },
            { value: 'spawn_item', label: '📦 Spawn Item', params: ['spawn_id', 'spawn_name', 'spawn_desc'] },
            { value: 'spawn_character', label: '🧑 Spawn Character', params: ['spawn_char_id', 'spawn_char_name', 'spawn_char_area'] },
            { value: 'teleport', label: '🌀 Teleport', params: ['teleport_area', 'teleport_target'] },
            { value: 'go', label: '🚶 Go / Move', params: ['go_mode', 'go_area', 'go_areas'] },
            { value: 'llm_respond', label: '🤖 LLM Respond', params: ['llm_instructions', 'llm_fallback', 'llm_max_words'] }
        ];
    };

    /**
     * Get available behavior condition types with their parameter schemas
     * @returns {Array<{value:string, label:string, params:string[]}>}
     */
    B.BEHAVIOR_CONDITION_TYPES = function() {
        return [
            { value: 'none', label: '— No Condition —', params: [] },
            { value: 'eq', label: 'Equals (=)', params: ['cond_target', 'cond_value'] },
            { value: 'has_item', label: 'Has Item', params: ['cond_item', 'cond_item_target'] },
            { value: 'has_trait', label: 'Has Trait', params: ['cond_trait'] },
            { value: 'has_tag', label: 'Has Tag', params: ['cond_tag'] },
            { value: 'in_area', label: 'In Area', params: ['cond_area', 'cond_in_area_target'] },
            { value: 'random_chance', label: 'Random Chance', params: ['cond_chance'] },
            { value: 'tick_since_state', label: 'Ticks Since State', params: ['cond_min_ticks'] },
            { value: 'proximity', label: 'Proximity', params: ['cond_max_areas'] }
        ];
    };

    /**
     * Add a new behavior to a character and open the editor
     * @param {string} charName - Character name
     */
    B.addBehavior = function(charName) {
        const player = worldState.players[charName];
        if (!player) return;
        if (!Array.isArray(player.behaviors)) player.behaviors = [];
        player.behaviors.push({ trigger: 'on_tick', interval: 1, priority: 0, conditions: {}, actions: [{ type: 'message', text: '' }] });
        B.editBehavior(charName, player.behaviors.length - 1);
    };

    /**
     * Delete a behavior from a character
     * @param {string} charName - Character name
     * @param {number} index - Behavior index
     */
    B.deleteBehavior = function(charName, index) {
        const player = worldState.players[charName];
        if (!player || !Array.isArray(player.behaviors)) return;
        if (!confirm('Delete this behavior?')) return;
        player.behaviors.splice(index, 1);
        ApiClient.updateCharacter(charName, { behaviors: player.behaviors }).then(() => {
            if (window.VW?.inspector) window.VW.inspector._reRender();
        });
    };

    /**
     * Build an action card lit-template for the behavior editor
     * @param {number} behIndex - Behavior index
     * @param {number} actIndex - Action index within the behavior
     * @param {object} action - Action data object
     * @returns {TemplateResult}
     */
    B.buildBehaviorActionCard = function(behIndex, actIndex, action) {
        const actOpts = B.BEHAVIOR_ACTION_TYPES().map(a =>
            htmlTag`<option value=${a.value} ?selected=${a.value === action.type}>${a.label}</option>`
        );

        const text = action.text || '';
        const state = action.state || '';
        const amount = action.amount !== undefined ? action.amount : 5;
        const damageTarget = action.target || 'player';
        const healStat = action.stat || 'HP';
        const healTarget = action.target || 'self';
        const envStat = action.stat || 'temperature';
        const envAmount = action.amount !== undefined ? action.amount : 0;
        const envRoom = action.area || '';
        const spawnId = action.item_id || '';
        const spawnName = action.name || '';
        const spawnDesc = action.description || '';
        const spawnCharId = action.character_id || '';
        const spawnCharName = action.display_name || '';
        const spawnCharArea = action.area || '';
        const teleportRoom = action.area || '';
        const teleportTarget = action.target || 'player';
        const goMode = action.mode || 'goto';
        const goArea = action.area || action.room || '';
        const goAreas = action.areas || '';

        const show = (types) => types.split(',').includes(action.type);

        return htmlTag`
            <div class="beh-action-card" style="background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;padding:8px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <select class="beh-act-type" style="flex:1;font-size:11px;" @change=${(e) => B.toggleActionFields(e.target, behIndex)}>
                        ${actOpts}
                    </select>
                    <button class="btn btn-sm btn-red" @click=${(e) => B.removeBehaviorAction(e.target, behIndex)} style="font-size:10px;margin-left:4px;">✕</button>
                </div>
                <div class="beh-act-params" data-cfg="${behIndex}:${actIndex}">
                    <div class="field beh-act-field" data-act="message,speak" style="display:${show('message,speak') ? 'block' : 'none'};">
                        <label>${action.type === 'speak' ? 'Speech Text' : 'Message Text'}</label>
                        <input type="text" class="beh-act-text" .value=${text} style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="set_npc_state" style="display:${show('set_npc_state') ? 'block' : 'none'};">
                        <label>New State</label>
                        <input type="text" class="beh-act-state" .value=${state} placeholder="idle, curious, angry..." style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="damage,heal" style="display:${show('damage,heal') ? 'block' : 'none'};">
                        <label>Amount</label>
                        <input type="number" class="beh-act-amount" .value=${amount} min="0" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="damage" style="display:${show('damage') ? 'block' : 'none'};">
                        <label>Target</label>
                        <select class="beh-act-target" style="width:100%;">
                            <option value="player" ?selected=${damageTarget === 'player'}>Player</option>
                            <option value="self" ?selected=${damageTarget === 'self'}>Self (NPC)</option>
                        </select>
                    </div>
                    <div class="field beh-act-field" data-act="heal" style="display:${show('heal') ? 'block' : 'none'};">
                        <label>Stat</label>
                        <select class="beh-act-stat" style="width:100%;">
                            <option value="HP" ?selected=${healStat === 'HP'}>HP</option>
                            <option value="Energy" ?selected=${healStat === 'Energy'}>Energy</option>
                            <option value="Hunger" ?selected=${healStat === 'Hunger'}>Hunger</option>
                            <option value="Thirst" ?selected=${healStat === 'Thirst'}>Thirst</option>
                            <option value="Hygiene" ?selected=${healStat === 'Hygiene'}>Hygiene</option>
                            <option value="Social" ?selected=${healStat === 'Social'}>Social</option>
                            <option value="Bladder" ?selected=${healStat === 'Bladder'}>Bladder</option>
                            <option value="Sanity" ?selected=${healStat === 'Sanity'}>Sanity</option>
                            <option value="Entertainment" ?selected=${healStat === 'Entertainment'}>Entertainment</option>
                        </select>
                    </div>
                    <div class="field beh-act-field" data-act="heal" style="display:${show('heal') ? 'block' : 'none'};">
                        <label>Target</label>
                        <select class="beh-act-target" style="width:100%;">
                            <option value="self" ?selected=${healTarget === 'self'}>Self (NPC)</option>
                            <option value="player" ?selected=${healTarget === 'player'}>Player</option>
                        </select>
                    </div>
                    <div class="field beh-act-field" data-act="set_environment" style="display:${show('set_environment') ? 'block' : 'none'};">
                        <label>Stat to Change</label>
                        <select class="beh-act-stat" style="width:100%;">
                            <option value="temperature" ?selected=${envStat === 'temperature'}>Temperature</option>
                            <option value="light" ?selected=${envStat === 'light'}>Light</option>
                        </select>
                    </div>
                    <div class="field beh-act-field" data-act="set_environment" style="display:${show('set_environment') ? 'block' : 'none'};">
                        <label>Amount (change by)</label>
                        <input type="number" class="beh-act-amount" .value=${envAmount} style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="set_environment" style="display:${show('set_environment') ? 'block' : 'none'};">
                        <label>Area (leave empty for NPC's current area)</label>
                        <input type="text" class="beh-act-area" .value=${envRoom} placeholder="e.g. Kitchen" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="spawn_item" style="display:${show('spawn_item') ? 'block' : 'none'};">
                        <label>Item ID</label>
                        <input type="text" class="beh-act-spawn-id" .value=${spawnId} placeholder="rusty_key" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="spawn_item" style="display:${show('spawn_item') ? 'block' : 'none'};">
                        <label>Item Name</label>
                        <input type="text" class="beh-act-spawn-name" .value=${spawnName} placeholder="Rusty Key" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="spawn_item" style="display:${show('spawn_item') ? 'block' : 'none'};">
                        <label>Description</label>
                        <input type="text" class="beh-act-spawn-desc" .value=${spawnDesc} placeholder="An old rusty key..." style="width:100%;">
                    </div>
<div class="field beh-act-field" data-act="spawn_character" style="display:${show('spawn_character') ? 'block' : 'none'};">
                        <label>Character ID</label>
                        <input type="text" class="beh-act-spawn-char-id" .value=${spawnCharId} placeholder="Miki" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="spawn_character" style="display:${show('spawn_character') ? 'block' : 'none'};">
                        <label>Display Name (optional)</label>
                        <input type="text" class="beh-act-spawn-char-name" .value=${spawnCharName} placeholder="Miki the Merchant" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="spawn_character" style="display:${show('spawn_character') ? 'block' : 'none'};">
                        <label>Area (blank = NPC's current area)</label>
                        <input type="text" class="beh-act-spawn-char-area" .value=${spawnCharArea} placeholder="Kitchen" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="teleport" style="display:${show('teleport') ? 'block' : 'none'};">
                        <label>Target Area</label>
                        <input type="text" class="beh-act-area" .value=${teleportRoom} placeholder="Basement" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="teleport" style="display:${show('teleport') ? 'block' : 'none'};">
                        <label>Target</label>
                        <select class="beh-act-target" style="width:100%;">
                            <option value="player" ?selected=${teleportTarget === 'player'}>Player</option>
                            <option value="self" ?selected=${teleportTarget === 'self'}>Self (NPC)</option>
                        </select>
                    </div>
<div class="field beh-act-field" data-act="go" style="display:${show('go') ? 'block' : 'none'};">
                        <label>Movement Mode</label>
                        <select class="beh-act-go-mode" style="width:100%;" @change=${(e) => B.toggleGoModeFields(e.target)}>
                            <option value="goto" ?selected=${goMode === 'goto'}>Goto — pathfind toward area (one step)</option>
                            <option value="random" ?selected=${goMode === 'random'}>Random — pick an open exit</option>
                            <option value="patrol" ?selected=${goMode === 'patrol'}>Patrol — cycle through area list</option>
                        </select>
                    </div>
                    <div class="field beh-act-field beh-act-go-goto" data-act="go" style="display:${action.type === 'go' && goMode !== 'patrol' && goMode !== 'random' ? 'block' : 'none'};">
                        <label>Target Area</label>
                        <input type="text" class="beh-act-area" .value=${goArea} placeholder="e.g. Kitchen" style="width:100%;">
                    </div>
                    <div class="field beh-act-field beh-act-go-patrol" data-act="go" style="display:${action.type === 'go' && goMode === 'patrol' ? 'block' : 'none'};">
                        <label>Patrol Areas (comma-separated)</label>
                        <input type="text" class="beh-act-areas" .value=${goAreas} placeholder="Kitchen, Cellar, Living Room" style="width:100%;">
                    </div>
                </div>
            </div>`;
    };

    /**
     * Open the behavior editor modal for a character's behavior
     * @param {string} charName - Character name
     * @param {number} index - Behavior index
     */
    B.editBehavior = function(charName, index) {
        const player = worldState.players[charName];
        if (!player || !Array.isArray(player.behaviors)) return;
        const behavior = player.behaviors[index];
        if (!behavior) return;

        const escName = charName.replace(/'/g, "\\'");
        const b = behavior;

        const existing = document.getElementById('behavior-modal');
        if (existing) existing.remove();

        // Build condition form
        const cond = b.conditions || {};
        const isCompound = cond.operator ? true : false;
        const condType = isCompound ? 'compound' : (cond.type || 'none');

        const condOpts = B.BEHAVIOR_CONDITION_TYPES().map(c =>
            htmlTag`<option value=${c.value} ?selected=${condType === c.value}>${c.label}</option>`
        );

        const condValue = cond.value || '';
        const condTarget = cond.target || '';
        const condItem = cond.item || '';
        const condItemTarget = cond.target || 'player';
        const condRoom = cond.area || '';
        const condInRoomTarget = cond.target || 'npc';
        const condChance = cond.chance !== undefined ? cond.chance : 0.5;
        const condMinTicks = cond.min_ticks || 0;
        const condMaxRooms = cond.max_areas || 0;
        const compoundOperator = cond.operator || 'and';
        const compoundConditions = cond.conditions || [];

        // Build action cards
        const actions = b.actions || [];
        const actionCards = actions.map((a, ai) => B.buildBehaviorActionCard(index, ai, a));

        const overlay = htmlTag`
            <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:540px;max-height:85vh;overflow-y:auto;">
                <h3 style="margin:0 0 12px 0;">🤖 Edit Behavior</h3>

                <div class="field">
                    <label>Trigger Type</label>
                    <select id="beh-trigger-${index}" style="width:100%;">
                        <option value="on_tick" ?selected=${b.trigger==='on_tick'}>Every N ticks</option>
                        <option value="on_player_enter_area" ?selected=${b.trigger==='on_player_enter_area'}>Player enters area</option>
                        <option value="on_player_leave_area" ?selected=${b.trigger==='on_player_leave_area'}>Player leaves area</option>
                        <option value="on_item_taken" ?selected=${b.trigger==='on_item_taken'}>Player takes item</option>
                        <option value="on_speech_heard" ?selected=${b.trigger==='on_speech_heard'}>Speech heard</option>
                        <option value="on_combat" ?selected=${b.trigger==='on_combat'}>Combat occurs</option>
                        <option value="on_state_changed" ?selected=${b.trigger==='on_state_changed'}>State changed</option>
                    </select>
                </div>

                <div style="display:flex;gap:8px;">
                    <div class="field" style="flex:1;"><label>Interval (ticks)</label>
                        <input type="number" id="beh-interval-${index}" .value=${b.interval||1} min="1" style="width:100%;">
                    </div>
                    <div class="field" style="flex:1;"><label>Priority</label>
                        <input type="number" id="beh-priority-${index}" .value=${b.priority||0} style="width:100%;">
                    </div>
                </div>

                <div style="border-top:1px solid var(--border);padding-top:12px;margin-top:12px;">
                    <h3 style="font-size:12px;margin:0 0 8px 0;color:var(--pink);">🧩 Conditions</h3>

                    <div class="field">
                        <label>Condition Mode</label>
                        <select id="beh-cond-mode-${index}" style="width:100%;" @change=${() => B.toggleConditionMode(index)}>
                            <option value="simple" ?selected=${!isCompound}>Simple (single condition)</option>
                            <option value="compound" ?selected=${isCompound}>Compound (and/or/not)</option>
                        </select>
                    </div>

                    <div id="beh-cond-simple-${index}" style="display:${!isCompound ? 'block' : 'none'};">
                        <div class="field"><label>Condition Type</label>
                            <select id="beh-cond-type-${index}" style="width:100%;" @change=${() => B.toggleBehaviorConditionFields(index)}>
                                ${condOpts}
                            </select>
                        </div>
                        <div id="beh-cond-fields-${index}">
                            <div class="field beh-cond-field" data-cond="eq,has_item" style="display:${condType === 'eq' || condType === 'has_item' ? 'block' : 'none'};">
                                <label id="beh-cond-target-label-${index}">${condType === 'has_item' ? 'Item Name' : 'Target Field'}</label>
                                <input type="text" id="beh-cond-target-${index}" .value=${condType === 'has_item' ? (condItem || '') : (condTarget || '')} style="width:100%;">
                            </div>
                            <div class="field beh-cond-field" data-cond="eq" style="display:${condType === 'eq' ? 'block' : 'none'};">
                                <label>Expected Value</label>
                                <input type="text" id="beh-cond-value-${index}" .value=${condValue} style="width:100%;">
                            </div>
                            <div class="field beh-cond-field" data-cond="has_trait,has_tag" style="display:${condType === 'has_trait' || condType === 'has_tag' ? 'block' : 'none'};">
                                <label>${condType === 'has_trait' ? 'Trait ID' : 'Tag'}</label>
                                <input type="text" id="beh-cond-value-${index}" .value=${condValue} placeholder="${condType === 'has_trait' ? 'dark_vision, hardy...' : 'vampire, faction:guard...'}" style="width:100%;">
                            </div>
                            <div class="field beh-cond-field" data-cond="has_item,in_area" style="display:${condType === 'has_item' || condType === 'in_area' ? 'block' : 'none'};">
                                <label>Target</label>
                                <select id="beh-cond-target-select-${index}" style="width:100%;">
                                    <option value="player" ?selected=${(condType === 'has_item' ? condItemTarget : condInRoomTarget) === 'player'}>Player</option>
                                    <option value="npc" ?selected=${(condType === 'has_item' ? condItemTarget : condInRoomTarget) === 'npc'}>NPC (self)</option>
                                </select>
                            </div>
                            <div class="field beh-cond-field" data-cond="in_area" style="display:${condType === 'in_area' ? 'block' : 'none'};">
                                <label>Area Name</label>
                                <input type="text" id="beh-cond-area-${index}" .value=${condRoom} style="width:100%;">
                            </div>
                            <div class="field beh-cond-field" data-cond="random_chance" style="display:${condType === 'random_chance' ? 'block' : 'none'};">
                                <label>Chance (0.0 - 1.0)</label>
                                <input type="number" id="beh-cond-chance-${index}" .value=${condChance} min="0" max="1" step="0.05" style="width:100%;">
                            </div>
                            <div class="field beh-cond-field" data-cond="tick_since_state" style="display:${condType === 'tick_since_state' ? 'block' : 'none'};">
                                <label>Minimum Ticks</label>
                                <input type="number" id="beh-cond-min-ticks-${index}" .value=${condMinTicks} min="0" style="width:100%;">
                            </div>
                            <div class="field beh-cond-field" data-cond="proximity" style="display:${condType === 'proximity' ? 'block' : 'none'};">
                                <label>Max Rooms Away (0 = same area)</label>
                                <input type="number" id="beh-cond-max-rooms-${index}" .value=${condMaxRooms} min="0" style="width:100%;">
                            </div>
                        </div>
                    </div>

                    <div id="beh-cond-compound-${index}" style="display:${isCompound ? 'block' : 'none'};">
                        <div class="field"><label>Operator</label>
                            <select id="beh-cond-operator-${index}" style="width:100%;">
                                <option value="and" ?selected=${compoundOperator === 'and'}>AND (all must match)</option>
                                <option value="or" ?selected=${compoundOperator === 'or'}>OR (any can match)</option>
                                <option value="not" ?selected=${compoundOperator === 'not'}>NOT (invert)</option>
                            </select>
                        </div>
                        <div class="field"><label>Sub-Conditions (JSON array)</label>
                            <textarea id="beh-cond-json-${index}" rows="3" style="width:100%;font-size:11px;">${JSON.stringify(isCompound ? compoundConditions : [], null, 2)}</textarea>
                            <div style="font-size:10px;color:var(--text-muted);margin-top:2px;">Each sub-condition: {"type":"eq","target":"npc_state","value":"idle"}</div>
                        </div>
                    </div>
                </div>

                <div style="border-top:1px solid var(--border);padding-top:12px;margin-top:12px;">
                    <h3 style="font-size:12px;margin:0 0 8px 0;color:var(--orange);">⚡ Actions
                        <button class="btn btn-sm btn-blue" @click=${() => B.addBehaviorAction(index)} style="float:right;">➕ Add</button>
                    </h3>
                    <div id="beh-actions-list-${index}">
                        ${actionCards.length ? actionCards : htmlTag`<div style="font-size:11px;color:var(--text-muted);padding:8px;text-align:center;">No actions. Click + Add to add one.</div>`}
                    </div>
                </div>

                <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end;border-top:1px solid var(--border);padding-top:12px;">
<button class="btn btn-sm" @click=${() => B.openGraphEditor(charName)} style="font-size:10px;margin-top:3px;">🧩 Graph</button>
                    <div style="flex:1;"></div>
                    <button class="btn" @click=${() => B._closeBehaviorEditor()}>Cancel</button>
                    <button class="btn btn-green" @click=${() => B.saveBehavior(charName, index)}>✅ Save</button>
                </div>
            </div>`;

        const container = document.createElement('div');
        container.id = 'behavior-modal';
        container.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
        document.body.appendChild(container);
        window.Lit.render(overlay, container);
        B.toggleBehaviorConditionFields(index);
    };

    B._closeBehaviorEditor = function() {
        const modal = document.getElementById('behavior-modal');
        if (modal) modal.remove();
    };

    /**
     * Add an action card to the behavior editor
     * @param {number} behIndex - Behavior index
     */
    B.addBehaviorAction = function(behIndex) {
        const actionsList = document.getElementById(`beh-actions-list-${behIndex}`);
        if (!actionsList) return;
        const card = B.buildBehaviorActionCard(behIndex, Date.now(), { type: 'message', text: '' });
        const emptyMsg = actionsList.querySelector('div[style*="text-align:center"]');
        if (emptyMsg) emptyMsg.remove();
        const wrapper = document.createElement('div');
        window.Lit.render(card, wrapper);
        actionsList.appendChild(wrapper.firstElementChild);
    };

    /**
     * Remove an action card from the behavior editor
     * @param {HTMLElement} btn - The remove button element
     * @param {number} behIndex - Behavior index
     */
    B.removeBehaviorAction = function(btn, behIndex) {
        const cards = document.querySelectorAll(`#beh-actions-list-${behIndex} .beh-action-card`);
        if (cards.length <= 1) return;
        btn.closest('.beh-action-card')?.remove();
    };

    /**
     * Toggle between simple and compound condition modes
     * @param {number} behIndex - Behavior index
     */
    B.toggleConditionMode = function(behIndex) {
        const mode = document.getElementById(`beh-cond-mode-${behIndex}`)?.value;
        const simple = document.getElementById(`beh-cond-simple-${behIndex}`);
        const compound = document.getElementById(`beh-cond-compound-${behIndex}`);
        if (simple) simple.style.display = mode === 'simple' ? 'block' : 'none';
        if (compound) compound.style.display = mode === 'compound' ? 'block' : 'none';
    };

    /**
     * Toggle condition fields display based on selected condition type
     * @param {number} behIndex - Behavior index
     */
    B.toggleBehaviorConditionFields = function(behIndex) {
        const condType = document.getElementById(`beh-cond-type-${behIndex}`)?.value || 'none';
        document.querySelectorAll(`#beh-cond-fields-${behIndex} .beh-cond-field`).forEach(el => {
            el.style.display = 'none';
        });
        document.querySelectorAll(`#beh-cond-fields-${behIndex} .beh-cond-field[data-cond*="${condType}"]`).forEach(el => {
            el.style.display = 'block';
        });
        const targetLabel = document.getElementById(`beh-cond-target-label-${behIndex}`);
        if (targetLabel) {
            if (condType === 'has_item') targetLabel.textContent = 'Item Name';
            else targetLabel.textContent = 'Target Field (e.g. npc_state)';
        }
    };

    B.toggleGoModeFields = function(selectEl) {
        const card = selectEl.closest('.beh-action-card');
        if (!card) return;
        const mode = selectEl.value;
        const gotoField = card.querySelector('.beh-act-go-goto');
        const patrolField = card.querySelector('.beh-act-go-patrol');
        if (gotoField) gotoField.style.display = mode === 'goto' ? 'block' : 'none';
        if (patrolField) patrolField.style.display = mode === 'patrol' ? 'block' : 'none';
    };

    /**
     * Toggle action fields display based on selected action type
     * @param {HTMLElement} selectEl - The action type select element
     * @param {number} behIndex - Behavior index
     */
    B.toggleActionFields = function(selectEl, behIndex) {
        const card = selectEl.closest('.beh-action-card');
        if (!card) return;
        const actType = selectEl.value;
        card.querySelectorAll('.beh-act-field').forEach(el => {
            el.style.display = 'none';
        });
        card.querySelectorAll(`.beh-act-field[data-act*="${actType}"]`).forEach(el => {
            el.style.display = 'block';
        });
        if (actType === 'go') {
            const modeSelect = card.querySelector('.beh-act-go-mode');
            if (modeSelect) B.toggleGoModeFields(modeSelect);
        }
    };

    /**
     * Save a behavior from the editor modal
     * @param {string} charName - Character name
     * @param {number} index - Behavior index
     */
    B.saveBehavior = function(charName, index) {
        const player = worldState.players[charName];
        if (!player || !Array.isArray(player.behaviors)) return;
        const behavior = player.behaviors[index];
        if (!behavior) return;

        behavior.trigger = document.getElementById(`beh-trigger-${index}`)?.value || 'on_tick';
        behavior.interval = parseInt(document.getElementById(`beh-interval-${index}`)?.value) || 1;
        behavior.priority = parseInt(document.getElementById(`beh-priority-${index}`)?.value) || 0;

        // Build conditions
        const condMode = document.getElementById(`beh-cond-mode-${index}`)?.value || 'simple';
        if (condMode === 'compound') {
            const operator = document.getElementById(`beh-cond-operator-${index}`)?.value || 'and';
            try {
                const subConditions = JSON.parse(document.getElementById(`beh-cond-json-${index}`)?.value || '[]');
                if (subConditions.length > 0) {
                    behavior.conditions = { operator, conditions: subConditions };
                } else {
                    behavior.conditions = {};
                }
            } catch (e) {
                toastError('Invalid sub-conditions JSON');
                return;
            }
        } else {
            const condType = document.getElementById(`beh-cond-type-${index}`)?.value || 'none';
            if (condType === 'none') {
                behavior.conditions = {};
            } else {
                const cond = { type: condType };
                if (condType === 'eq') {
                    cond.target = document.getElementById(`beh-cond-target-${index}`)?.value || '';
                    cond.value = document.getElementById(`beh-cond-value-${index}`)?.value || '';
                } else if (condType === 'has_trait' || condType === 'has_tag') {
                    cond.value = document.getElementById(`beh-cond-value-${index}`)?.value || '';
                } else if (condType === 'has_item') {
                    cond.item = document.getElementById(`beh-cond-target-${index}`)?.value || '';
                    cond.target = document.getElementById(`beh-cond-target-select-${index}`)?.value || 'player';
                } else if (condType === 'in_area') {
                    cond.area = document.getElementById(`beh-cond-area-${index}`)?.value || '';
                    cond.target = document.getElementById(`beh-cond-target-select-${index}`)?.value || 'npc';
                } else if (condType === 'random_chance') {
                    cond.chance = parseFloat(document.getElementById(`beh-cond-chance-${index}`)?.value) || 0.5;
                } else if (condType === 'tick_since_state') {
                    cond.min_ticks = parseInt(document.getElementById(`beh-cond-min-ticks-${index}`)?.value) || 0;
                } else if (condType === 'proximity') {
                    cond.max_areas = parseInt(document.getElementById(`beh-cond-max-rooms-${index}`)?.value) || 0;
                }
                behavior.conditions = cond;
            }
        }

        // Build actions
        const actionCards = document.querySelectorAll(`#beh-actions-list-${index} .beh-action-card`);
        const actions = [];
        actionCards.forEach((card) => {
            const typeSelect = card.querySelector('.beh-act-type');
            if (!typeSelect) return;
            const actType = typeSelect.value;
            const action = { type: actType };

            if (actType === 'message' || actType === 'speak') {
                const textInput = card.querySelector('.beh-act-text');
                action.text = textInput?.value || '';
            } else if (actType === 'set_npc_state') {
                const stateInput = card.querySelector('.beh-act-state');
                action.state = stateInput?.value || 'idle';
            } else if (actType === 'damage') {
                const amountInput = card.querySelector('.beh-act-amount');
                action.amount = parseInt(amountInput?.value) || 5;
                const targetSelect = card.querySelector('.beh-act-target');
                action.target = targetSelect?.value || 'player';
            } else if (actType === 'heal') {
                const amountInput = card.querySelector('.beh-act-amount');
                action.amount = parseInt(amountInput?.value) || 10;
                const statSelect = card.querySelector('.beh-act-stat');
                action.stat = statSelect?.value || 'HP';
                const targetSelect = card.querySelector('.beh-act-target');
                action.target = targetSelect?.value || 'self';
            } else if (actType === 'set_environment') {
                const statSelect = card.querySelector('.beh-act-stat');
                action.stat = statSelect?.value || 'temperature';
                const amountInput = card.querySelector('.beh-act-amount');
                action.amount = parseInt(amountInput?.value) || 0;
                const roomInput = card.querySelector('.beh-act-area');
                action.area = roomInput?.value || '';
            } else if (actType === 'spawn_item') {
                const idInput = card.querySelector('.beh-act-spawn-id');
                action.item_id = idInput?.value || '';
                const nameInput = card.querySelector('.beh-act-spawn-name');
                action.name = nameInput?.value || '';
                const descInput = card.querySelector('.beh-act-spawn-desc');
                action.description = descInput?.value || '';
            } else if (actType === 'spawn_character') {
                const charIdInput = card.querySelector('.beh-act-spawn-char-id');
                action.character_id = charIdInput?.value || '';
                const charNameInput = card.querySelector('.beh-act-spawn-char-name');
                action.display_name = charNameInput?.value || '';
                const charAreaInput = card.querySelector('.beh-act-spawn-char-area');
                action.area = charAreaInput?.value || '';
            } else if (actType === 'teleport') {
                const roomInput = card.querySelector('.beh-act-area');
                action.area = roomInput?.value || '';
                const targetSelect = card.querySelector('.beh-act-target');
                action.target = targetSelect?.value || 'player';
            } else if (actType === 'go') {
                const modeSelect = card.querySelector('.beh-act-go-mode');
                action.mode = modeSelect?.value || 'goto';
                if (action.mode === 'patrol') {
                    action.areas = card.querySelector('.beh-act-areas')?.value || '';
                } else if (action.mode === 'goto') {
                    action.area = card.querySelector('.beh-act-area')?.value || '';
                }
            }

            actions.push(action);
        });
        behavior.actions = actions;

        ApiClient.updateCharacter(charName, { behaviors: player.behaviors }).then(() => {
            B._closeBehaviorEditor();
            if (window.VW?.inspector) window.VW.inspector._reRender();
        });
    };

    /**
     * Open the behavior graph editor for a character (all behaviors at once).
     * @param {string} charName - Character name
     */
    B.openGraphEditor = function(charName) {
        const player = worldState.players[charName];
        if (!player) return;
        const behaviors = Array.isArray(player.behaviors) ? player.behaviors : [];
        const graph = (typeof TriggerGraph !== 'undefined' && TriggerGraph.behaviorsToGraph)
            ? TriggerGraph.behaviorsToGraph(behaviors)
            : { nodes: [], wires: [] };

        TriggerGraph.show({
            mode: 'behavior',
            graph,
            onSave: async (newGraph) => {
                const compiled = TriggerGraph.compileToBehaviors(newGraph);
                await ApiClient.updateCharacter(charName, { behaviors: compiled });
                if (window.VW?.inspector) window.VW.inspector._reRender();
            }
        });
    };

    return B;
})();