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
            { value: 'llm_respond', label: '🤖 LLM Respond', params: ['llm_instructions', 'llm_fallback', 'llm_max_words'] },
            { value: 'add_memory', label: '🧠 Add Memory', params: ['mem_text', 'mem_importance', 'mem_tags'] },
            { value: 'set_emotion', label: '😊 Set Emotion', params: ['emotion_name', 'emotion_intensity'] },
            { value: 'set_flag', label: '🚩 Set Flag', params: ['flag_key', 'flag_value'] },
            { value: 'hide_in', label: '📦 Hide In', params: ['hide_target'] },
            { value: 'hide_behind', label: '🫣 Hide Behind', params: ['hide_target'] },
            { value: 'hide_under', label: '⬇️ Hide Under', params: ['hide_target'] },
            { value: 'unhide', label: '👋 Unhide', params: [] },
            { value: 'attack', label: '⚔️ Attack', params: ['attack_target', 'attack_weapon', 'attack_where'] },
            { value: 'throw', label: '🎯 Throw', params: ['throw_item', 'throw_target'] },
            { value: 'break', label: '💢 Break', params: ['break_item'] },
            { value: 'take', label: '🤲 Take', params: ['take_item'] },
            { value: 'drop', label: '⬇️ Drop', params: ['drop_item'] },
            { value: 'put_in', label: '📥 Put In', params: ['put_item', 'put_container'] },
            { value: 'equip', label: '🛡️ Equip', params: ['equip_item', 'equip_slot'] },
            { value: 'unequip', label: '🚫 Unequip', params: ['unequip_item', 'unequip_slot'] },
            { value: 'use', label: '🔧 Use', params: ['use_item', 'use_target'] },
            { value: 'eat', label: '🍽️ Eat', params: ['eat_item'] },
            { value: 'drink', label: '🍺 Drink', params: ['drink_item'] },
            { value: 'craft', label: '⚒️ Craft', params: ['craft_recipe'] },
            { value: 'combine', label: '🔗 Combine', params: ['combine_source', 'combine_target'] },
            { value: 'repair', label: '🔨 Repair', params: ['repair_item', 'repair_kit'] },
            { value: 'read', label: '📖 Read', params: ['read_item'] },
            { value: 'open', label: '🚪 Open', params: ['open_target'] },
            { value: 'close', label: '🚪 Close', params: ['close_target'] },
            { value: 'lock', label: '🔒 Lock', params: ['lock_target'] },
            { value: 'unlock', label: '🔓 Unlock', params: ['unlock_target'] },
            { value: 'push', label: '✋ Push/Pull', params: ['push_target', 'push_direction'] },
            { value: 'turn', label: '🔄 Turn', params: ['turn_target'] },
            { value: 'search', label: '🔍 Search', params: ['search_target'] },
            { value: 'give', label: '🎁 Give', params: ['give_item', 'give_target'] },
            { value: 'steal', label: '🤫 Steal', params: ['steal_item', 'steal_target'] },
            { value: 'follow', label: '👣 Follow', params: ['follow_target'] },
            { value: 'wait', label: '⏳ Wait', params: [] },
            { value: 'dash', label: '💨 Dash', params: ['dash_direction'] },
            { value: 'crawl', label: '🐍 Crawl', params: ['crawl_direction'] },
            { value: 'climb', label: '🧗 Climb', params: ['climb_direction'] },
            { value: 'jump', label: '🦘 Jump', params: ['jump_direction'] },
            { value: 'toggle_way', label: '🚧 Toggle Way', params: ['toggle_way_direction', 'toggle_way_action'] },
            { value: 'grab', label: '✊ Grab', params: ['grab_target'] },
            { value: 'drag', label: '🪢 Drag', params: ['drag_target', 'drag_direction'] },
            { value: 'pin', label: '📌 Pin', params: ['pin_target'] },
            { value: 'struggle', label: '💪 Struggle', params: [] },
            { value: 'escape', label: '🏃 Escape', params: [] },
            { value: 'release', label: '🤲 Release', params: ['release_target'] },
            { value: 'look', label: '👀 Look', params: [] },
            { value: 'examine', label: '🔎 Examine', params: ['examine_target'] },
            { value: 'activate', label: '⚡ Activate', params: ['activate_item'] },
            { value: 'light', label: '🔥 Light', params: ['light_item'] },
            { value: 'toggle', label: '🔘 Toggle', params: ['toggle_item'] },
            { value: 'place', label: '📌 Place', params: ['place_item', 'place_target', 'place_relation'] },
            { value: 'stow', label: '📦 Stow', params: ['stow_item'] },
            { value: 'remove', label: '🗑️ Remove', params: ['remove_item'] },
            { value: 'hold', label: '✋ Hold', params: ['hold_item'] },
            { value: 'weigh', label: '⚖️ Weigh', params: [] },
            { value: 'inventory', label: '🎒 Inventory', params: [] },
            { value: 'carry', label: '🫃 Carry', params: ['carry_item'] },
            { value: 'dress', label: '👔 Dress', params: [] },
            { value: 'strip', label: '👙 Strip', params: [] },
            { value: 'swap', label: '🔁 Swap', params: ['swap_item', 'swap_target'] },
            { value: 'adorn', label: '💎 Adorn', params: ['adorn_item', 'adorn_target'] },
            { value: 'rest', label: '😴 Rest', params: ['rest_minutes'] },
            { value: 'sleep', label: '💤 Sleep', params: ['sleep_minutes'] },
            { value: 'meditate', label: '🧘 Meditate', params: ['meditate_minutes'] },
            { value: 'bathe', label: '🛁 Bathe', params: ['bathe_target', 'bathe_minutes'] },
            { value: 'sit', label: '🪑 Sit', params: [] },
            { value: 'stand', label: '🧍 Stand', params: [] },
            { value: 'stop', label: '🛑 Stop', params: [] },
            { value: 'wake', label: '⏰ Wake', params: ['wake_target'] },
            { value: 'relieve', label: '🚽 Relieve', params: [] },
            { value: 'fumble', label: '🤲 Fumble Around', params: [] },
            { value: 'introduce', label: '🤝 Introduce', params: ['introduce_target'] },
            { value: 'beg', label: '🥺 Beg', params: ['beg_target'] },
            { value: 'demand', label: '😠 Demand', params: ['demand_target'] },
            { value: 'bribe', label: '💰 Bribe', params: ['bribe_target', 'bribe_item'] },
            { value: 'kiss', label: '💋 Kiss', params: ['kiss_target', 'kiss_where', 'kiss_intensity'] },
            { value: 'caress', label: '✋ Caress', params: ['caress_target', 'caress_where', 'caress_intensity'] },
            { value: 'lick', label: '👅 Lick', params: ['lick_target', 'lick_where', 'lick_intensity'] },
            { value: 'suck', label: '💦 Suck', params: ['suck_target', 'suck_where', 'suck_intensity'] },
            { value: 'bite', label: '🫷 Bite', params: ['bite_target', 'bite_where', 'bite_intensity'] },
            { value: 'tickle', label: '😂 Tickle', params: ['tickle_target', 'tickle_where', 'tickle_intensity'] },
            { value: 'embrace', label: '🫂 Embrace', params: ['embrace_target', 'embrace_where', 'embrace_intensity'] },
            { value: 'manifest', label: '👻 Manifest', params: [] },
            { value: 'vanish', label: '🌫️ Vanish', params: [] },
            { value: 'possess', label: '🎭 Possess', params: ['possess_target'] },
            { value: 'wraith_form', label: '🌑 Wraith Form', params: [] },
            { value: 'spawn_body_item', label: '💀 Spawn Body Item', params: [] },
            { value: 'teach', label: '📚 Teach', params: ['teach_target', 'teach_subject'] },
            { value: 'cook', label: '🍳 Cook', params: ['cook_recipe'] },
            { value: 'push_through', label: '🚶 Push Through', params: ['push_through_direction'] },
            { value: 'block', label: '🧱 Block', params: ['block_target'] },
            { value: 'help', label: '❓ Help', params: [] },
            { value: 'commands', label: '📋 Commands', params: [] },
            { value: 'who', label: '👤 Who', params: [] },
            { value: 'time', label: '🕐 Time', params: [] },
            { value: 'score', label: '📊 Score', params: [] },
            { value: 'map', label: '🗺️ Map', params: [] },
            { value: 'save', label: '💾 Save', params: [] },
            { value: 'quit', label: '🚪 Quit', params: [] },
            { value: 'version', label: 'ℹ️ Version', params: [] },
            { value: 'approach', label: '🚶 Approach', params: ['approach_target'] },
            { value: 'traverse', label: '🌉 Traverse', params: ['traverse_target'] },
            { value: 'emote', label: '🎭 Emote', params: ['emote_text'] },
            { value: 'carve', label: '🗿 Carve', params: ['carve_target', 'carve_text'] },
            { value: 'gulp_down', label: '🥤 Gulp Down', params: ['gulp_item'] },
            { value: 'pinch', label: '🤏 Pinch', params: ['pinch_target', 'pinch_where', 'pinch_intensity'] },
            { value: 'drop_all', label: '🗑️ Drop All', params: [] },
            { value: 'take_all', label: '📥 Take All', params: [] },
            { value: 'lie_down', label: '🛏️ Lie Down', params: [] }
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
            { value: 'proximity', label: 'Proximity', params: ['cond_max_areas'] },
            { value: 'npc_emotion_is', label: 'NPC Emotion Is', params: ['emotion_name', 'emotion_operator', 'emotion_value'] },
            { value: 'npc_is_hidden', label: 'NPC Is Hidden', params: ['hidden_value'] },
            { value: 'character_has_tag', label: 'Character Has Tag', params: ['char_tag', 'char_tag_target'] }
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
        const memText = action.text || '';
        const memImportance = action.importance !== undefined ? action.importance : 5;
        const memTags = action.tags || '';
        const emotionName = action.emotion || 'neutral';
        const emotionIntensity = action.intensity !== undefined ? action.intensity : 0.5;
        const flagKey = action.key || '';
        const flagValue = action.value !== undefined ? action.value : true;
        const hideTarget = action.target || '';
        const attackTarget = action.target || '';
        const attackWeapon = action.weapon || '';
        const attackWhere = action.where || '';
        const throwItem = action.item || '';
        const throwTarget = action.target || '';
        const breakItem = action.item || '';
        const takeItem = action.item || '';
        const dropItem = action.item || '';
        const putItem = action.item || '';
        const putContainer = action.container || '';
        const equipItem = action.item || '';
        const equipSlot = action.slot || '';
        const unequipItem = action.item || '';
        const unequipSlot = action.slot || '';
        const useItem = action.item || '';
        const useTarget = action.target || '';
        const eatItem = action.item || '';
        const drinkItem = action.item || '';
        const craftRecipe = action.recipe || '';
        const combineSource = action.source || '';
        const combineTarget = action.target || '';
        const repairItem = action.item || '';
        const repairKit = action.kit || '';
        const readItem = action.item || '';
        const openTarget = action.target || '';
        const closeTarget = action.target || '';
        const lockTarget = action.target || '';
        const unlockTarget = action.target || '';
        const pushTarget = action.target || '';
        const pushDirection = action.direction || '';
        const turnTarget = action.target || '';
        const searchTarget = action.target || '';
        const giveItem = action.item || '';
        const giveTarget = action.target || '';
        const stealItem = action.item || '';
        const stealTarget = action.target || '';
        const followTarget = action.target || '';
        const dashDirection = action.direction || '';
        const crawlDirection = action.direction || '';
        const climbDirection = action.direction || '';
        const jumpDirection = action.direction || '';
        const toggleWayDirection = action.direction || '';
        const toggleWayAction = action.way_action || 'open';
        const grabTarget = action.target || '';
        const dragTarget = action.target || '';
        const dragDirection = action.direction || '';
        const pinTarget = action.target || '';
        const releaseTarget = action.target || '';
        const examineTarget = action.target || '';
        const placeItem = action.item || '';
        const placeTarget = action.target || '';
        const placeRelation = action.relation || 'on';
        const removeItem = action.item || '';
        const holdItem = action.item || '';
        const carryItem = action.item || '';
        const weighItem = action.item || '';
        const inventoryItem = action.item || '';
        const swapItem = action.item || '';
        const swapTarget = action.target || '';
        const adornItem = action.item || '';
        const adornTarget = action.target || '';
        const restMinutes = action.minutes !== undefined ? action.minutes : 10;
        const sleepMinutes = action.minutes !== undefined ? action.minutes : 60;
        const meditateMinutes = action.minutes !== undefined ? action.minutes : 10;
        const batheTarget = action.target || '';
        const batheMinutes = action.minutes !== undefined ? action.minutes : 10;
        const wakeTarget = action.target || '';
        const introduceTarget = action.target || '';
        const begTarget = action.target || '';
        const demandTarget = action.target || '';
        const bribeTarget = action.target || '';
        const bribeItem = action.item || '';
        const kissTarget = action.target || '';
        const kissWhere = action.where || '';
        const kissIntensity = action.intensity || 'normal';
        const caressTarget = action.target || '';
        const caressWhere = action.where || '';
        const caressIntensity = action.intensity || 'normal';
        const lickTarget = action.target || '';
        const lickWhere = action.where || '';
        const lickIntensity = action.intensity || 'normal';
        const suckTarget = action.target || '';
        const suckWhere = action.where || '';
        const suckIntensity = action.intensity || 'normal';
        const biteTarget = action.target || '';
        const biteWhere = action.where || '';
        const biteIntensity = action.intensity || 'normal';
        const tickleTarget = action.target || '';
        const tickleWhere = action.where || '';
        const tickleIntensity = action.intensity || 'normal';
        const embraceTarget = action.target || '';
        const embraceWhere = action.where || '';
        const embraceIntensity = action.intensity || 'normal';
        const possessTarget = action.target || '';
        const teachTarget = action.target || '';
        const teachSubject = action.subject || '';
        const cookRecipe = action.recipe || '';
        const pushThroughDirection = action.direction || '';
        const blockTarget = action.target || '';
        const approachTarget = action.target || '';
        const traverseTarget = action.target || '';
        const emoteText = action.text || '';
        const carveTarget = action.target || '';
        const carveText = action.text || '';
        const gulpItem = action.item || '';
        const pinchTarget = action.target || '';
        const pinchWhere = action.where || '';
        const pinchIntensity = action.intensity || 'normal';

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
                    <div class="field beh-act-field" data-act="add_memory" style="display:${show('add_memory') ? 'block' : 'none'};">
                        <label>Memory Text</label>
                        <input type="text" class="beh-act-mem-text" .value=${memText} placeholder="I saw the guard drop the key..." style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="add_memory" style="display:${show('add_memory') ? 'block' : 'none'};">
                        <label>Importance (1-10)</label>
                        <input type="number" class="beh-act-mem-importance" .value=${memImportance} min="1" max="10" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="add_memory" style="display:${show('add_memory') ? 'block' : 'none'};">
                        <label>Tags (comma-separated)</label>
                        <input type="text" class="beh-act-mem-tags" .value=${memTags} placeholder="guard, key, door" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="set_emotion" style="display:${show('set_emotion') ? 'block' : 'none'};">
                        <label>Emotion</label>
                        <select class="beh-act-emotion-name" style="width:100%;">
                            <option value="neutral" ?selected=${emotionName === 'neutral'}>neutral</option>
                            <option value="happy" ?selected=${emotionName === 'happy'}>happy</option>
                            <option value="sad" ?selected=${emotionName === 'sad'}>sad</option>
                            <option value="angry" ?selected=${emotionName === 'angry'}>angry</option>
                            <option value="afraid" ?selected=${emotionName === 'afraid'}>afraid</option>
                            <option value="surprised" ?selected=${emotionName === 'surprised'}>surprised</option>
                            <option value="disgusted" ?selected=${emotionName === 'disgusted'}>disgusted</option>
                        </select>
                    </div>
                    <div class="field beh-act-field" data-act="set_emotion" style="display:${show('set_emotion') ? 'block' : 'none'};">
                        <label>Intensity (0.0 - 1.0)</label>
                        <input type="number" class="beh-act-emotion-intensity" .value=${emotionIntensity} min="0" max="1" step="0.1" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="set_flag" style="display:${show('set_flag') ? 'block' : 'none'};">
                        <label>Flag Key</label>
                        <input type="text" class="beh-act-flag-key" .value=${flagKey} placeholder="alert, fleeing, guarding..." style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="set_flag" style="display:${show('set_flag') ? 'block' : 'none'};">
                        <label>Value</label>
                        <input type="text" class="beh-act-flag-value" .value=${flagValue} placeholder="true" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="hide_in,hide_behind,hide_under" style="display:${show('hide_in,hide_behind,hide_under') ? 'block' : 'none'};">
                        <label>Target Item ID (must have "hideable" tag)</label>
                        <input type="text" class="beh-act-hide-target" .value=${hideTarget} placeholder="item_chest" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="attack" style="display:${show('attack') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-attack-target" .value=${attackTarget} placeholder="goblin" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="attack" style="display:${show('attack') ? 'block' : 'none'};">
                        <label>Weapon (optional)</label>
                        <input type="text" class="beh-act-attack-weapon" .value=${attackWeapon} placeholder="sword" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="attack" style="display:${show('attack') ? 'block' : 'none'};">
                        <label>Body Part (optional)</label>
                        <input type="text" class="beh-act-attack-where" .value=${attackWhere} placeholder="head, torso..." style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="throw" style="display:${show('throw') ? 'block' : 'none'};">
                        <label>Item to Throw</label>
                        <input type="text" class="beh-act-throw-item" .value=${throwItem} placeholder="knife" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="throw" style="display:${show('throw') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-throw-target" .value=${throwTarget} placeholder="goblin" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="break" style="display:${show('break') ? 'block' : 'none'};">
                        <label>Item to Break</label>
                        <input type="text" class="beh-act-break-item" .value=${breakItem} placeholder="bottle" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="take" style="display:${show('take') ? 'block' : 'none'};">
                        <label>Item to Take</label>
                        <input type="text" class="beh-act-take-item" .value=${takeItem} placeholder="apple" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="drop" style="display:${show('drop') ? 'block' : 'none'};">
                        <label>Item to Drop</label>
                        <input type="text" class="beh-act-drop-item" .value=${dropItem} placeholder="sword" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="put_in" style="display:${show('put_in') ? 'block' : 'none'};">
                        <label>Item</label>
                        <input type="text" class="beh-act-put-item" .value=${putItem} placeholder="gem" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="put_in" style="display:${show('put_in') ? 'block' : 'none'};">
                        <label>Container</label>
                        <input type="text" class="beh-act-put-container" .value=${putContainer} placeholder="chest" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="equip" style="display:${show('equip') ? 'block' : 'none'};">
                        <label>Item to Equip</label>
                        <input type="text" class="beh-act-equip-item" .value=${equipItem} placeholder="helmet" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="equip" style="display:${show('equip') ? 'block' : 'none'};">
                        <label>Slot (optional)</label>
                        <input type="text" class="beh-act-equip-slot" .value=${equipSlot} placeholder="head, torso, hands..." style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="unequip" style="display:${show('unequip') ? 'block' : 'none'};">
                        <label>Item or Slot</label>
                        <input type="text" class="beh-act-unequip-item" .value=${unequipItem || unequipSlot} placeholder="helmet or head" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="use" style="display:${show('use') ? 'block' : 'none'};">
                        <label>Item to Use</label>
                        <input type="text" class="beh-act-use-item" .value=${useItem} placeholder="key" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="use" style="display:${show('use') ? 'block' : 'none'};">
                        <label>Target (optional)</label>
                        <input type="text" class="beh-act-use-target" .value=${useTarget} placeholder="door" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="eat" style="display:${show('eat') ? 'block' : 'none'};">
                        <label>Food Item</label>
                        <input type="text" class="beh-act-eat-item" .value=${eatItem} placeholder="bread" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="drink" style="display:${show('drink') ? 'block' : 'none'};">
                        <label>Drink Item</label>
                        <input type="text" class="beh-act-drink-item" .value=${drinkItem} placeholder="potion" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="craft" style="display:${show('craft') ? 'block' : 'none'};">
                        <label>Recipe Name</label>
                        <input type="text" class="beh-act-craft-recipe" .value=${craftRecipe} placeholder="campfire" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="combine" style="display:${show('combine') ? 'block' : 'none'};">
                        <label>Source Item</label>
                        <input type="text" class="beh-act-combine-source" .value=${combineSource} placeholder="cloth" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="combine" style="display:${show('combine') ? 'block' : 'none'};">
                        <label>Target Item</label>
                        <input type="text" class="beh-act-combine-target" .value=${combineTarget} placeholder="stick" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="repair" style="display:${show('repair') ? 'block' : 'none'};">
                        <label>Item to Repair</label>
                        <input type="text" class="beh-act-repair-item" .value=${repairItem} placeholder="armor" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="repair" style="display:${show('repair') ? 'block' : 'none'};">
                        <label>Repair Kit (optional)</label>
                        <input type="text" class="beh-act-repair-kit" .value=${repairKit} placeholder="repair_kit" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="read" style="display:${show('read') ? 'block' : 'none'};">
                        <label>Item to Read</label>
                        <input type="text" class="beh-act-read-item" .value=${readItem} placeholder="letter" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="open" style="display:${show('open') ? 'block' : 'none'};">
                        <label>Target to Open</label>
                        <input type="text" class="beh-act-open-target" .value=${openTarget} placeholder="door" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="close" style="display:${show('close') ? 'block' : 'none'};">
                        <label>Target to Close</label>
                        <input type="text" class="beh-act-close-target" .value=${closeTarget} placeholder="door" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="lock" style="display:${show('lock') ? 'block' : 'none'};">
                        <label>Target to Lock</label>
                        <input type="text" class="beh-act-lock-target" .value=${lockTarget} placeholder="door" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="unlock" style="display:${show('unlock') ? 'block' : 'none'};">
                        <label>Target to Unlock</label>
                        <input type="text" class="beh-act-unlock-target" .value=${unlockTarget} placeholder="door" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="push" style="display:${show('push') ? 'block' : 'none'};">
                        <label>Target to Push/Pull</label>
                        <input type="text" class="beh-act-push-target" .value=${pushTarget} placeholder="boulder" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="push" style="display:${show('push') ? 'block' : 'none'};">
                        <label>Direction (optional)</label>
                        <input type="text" class="beh-act-push-direction" .value=${pushDirection} placeholder="north" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="turn" style="display:${show('turn') ? 'block' : 'none'};">
                        <label>Target to Turn</label>
                        <input type="text" class="beh-act-turn-target" .value=${turnTarget} placeholder="wheel" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="search" style="display:${show('search') ? 'block' : 'none'};">
                        <label>Target to Search</label>
                        <input type="text" class="beh-act-search-target" .value=${searchTarget} placeholder="desk" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="give" style="display:${show('give') ? 'block' : 'none'};">
                        <label>Item to Give</label>
                        <input type="text" class="beh-act-give-item" .value=${giveItem} placeholder="apple" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="give" style="display:${show('give') ? 'block' : 'none'};">
                        <label>Recipient</label>
                        <input type="text" class="beh-act-give-target" .value=${giveTarget} placeholder="bob" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="steal" style="display:${show('steal') ? 'block' : 'none'};">
                        <label>Item to Steal</label>
                        <input type="text" class="beh-act-steal-item" .value=${stealItem} placeholder="coin" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="steal" style="display:${show('steal') ? 'block' : 'none'};">
                        <label>Victim</label>
                        <input type="text" class="beh-act-steal-target" .value=${stealTarget} placeholder="merchant" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="follow" style="display:${show('follow') ? 'block' : 'none'};">
                        <label>Target to Follow</label>
                        <input type="text" class="beh-act-follow-target" .value=${followTarget} placeholder="player" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="dash,crawl,climb,jump" style="display:${show('dash,crawl,climb,jump') ? 'block' : 'none'};">
                        <label>Direction</label>
                        <input type="text" class="beh-act-dash-dir" .value=${dashDirection || crawlDirection || climbDirection || jumpDirection || ''} placeholder="north" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="toggle_way" style="display:${show('toggle_way') ? 'block' : 'none'};">
                        <label>Direction</label>
                        <input type="text" class="beh-act-toggle-dir" .value=${toggleWayDirection || ''} placeholder="north" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="toggle_way" style="display:${show('toggle_way') ? 'block' : 'none'};">
                        <label>Action</label>
                        <select class="beh-act-toggle-action" style="width:100%;">
                            <option value="open" ?selected=${toggleWayAction === 'open'}>Open</option>
                            <option value="close" ?selected=${toggleWayAction === 'close'}>Close</option>
                        </select>
                    </div>
                    <div class="field beh-act-field" data-act="grab,pin,release,drag" style="display:${show('grab,pin,release,drag') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-grab-target" .value=${grabTarget || pinTarget || releaseTarget || dragTarget || ''} placeholder="character" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="drag" style="display:${show('drag') ? 'block' : 'none'};">
                        <label>Direction</label>
                        <input type="text" class="beh-act-drag-dir" .value=${dragDirection || ''} placeholder="north" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="examine" style="display:${show('examine') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-examine-target" .value=${examineTarget || ''} placeholder="item name" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="place" style="display:${show('place') ? 'block' : 'none'};">
                        <label>Item</label>
                        <input type="text" class="beh-act-place-item" .value=${placeItem || ''} placeholder="apple" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="place" style="display:${show('place') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-place-target" .value=${placeTarget || ''} placeholder="table" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="place" style="display:${show('place') ? 'block' : 'none'};">
                        <label>Relation</label>
                        <select class="beh-act-place-relation" style="width:100%;">
                            <option value="on" ?selected=${placeRelation === 'on'}>on</option>
                            <option value="in" ?selected=${placeRelation === 'in'}>in</option>
                            <option value="under" ?selected=${placeRelation === 'under'}>under</option>
                            <option value="behind" ?selected=${placeRelation === 'behind'}>behind</option>
                            <option value="beside" ?selected=${placeRelation === 'beside'}>beside</option>
                        </select>
                    </div>
                    <div class="field beh-act-field" data-act="remove" style="display:${show('remove') ? 'block' : 'none'};">
                        <label>Item or Slot</label>
                        <input type="text" class="beh-act-remove-item" .value=${removeItem || ''} placeholder="helmet or head" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="hold,weigh,inventory,carry" style="display:${show('hold,weigh,inventory,carry') ? 'block' : 'none'};">
                        <label>Item</label>
                        <input type="text" class="beh-act-hold-item" .value=${holdItem || weighItem || inventoryItem || carryItem || ''} placeholder="item name" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="swap" style="display:${show('swap') ? 'block' : 'none'};">
                        <label>New Item</label>
                        <input type="text" class="beh-act-swap-item" .value=${swapItem || ''} placeholder="new helmet" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="swap" style="display:${show('swap') ? 'block' : 'none'};">
                        <label>Old Item/Slot</label>
                        <input type="text" class="beh-act-swap-target" .value=${swapTarget || ''} placeholder="old helmet or head" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="adorn" style="display:${show('adorn') ? 'block' : 'none'};">
                        <label>Item</label>
                        <input type="text" class="beh-act-adorn-item" .value=${adornItem || ''} placeholder="pin" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="adorn" style="display:${show('adorn') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-adorn-target" .value=${adornTarget || ''} placeholder="cloak" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="rest,sleep,meditate" style="display:${show('rest,sleep,meditate') ? 'block' : 'none'};">
                        <label>Minutes</label>
                        <input type="number" class="beh-act-rest-min" .value=${restMinutes || sleepMinutes || meditateMinutes || 10} min="1" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="bathe" style="display:${show('bathe') ? 'block' : 'none'};">
                        <label>Target (optional)</label>
                        <input type="text" class="beh-act-bathe-target" .value=${batheTarget || ''} placeholder="bath" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="bathe" style="display:${show('bathe') ? 'block' : 'none'};">
                        <label>Minutes</label>
                        <input type="number" class="beh-act-bathe-min" .value=${batheMinutes || 10} min="1" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="wake" style="display:${show('wake') ? 'block' : 'none'};">
                        <label>Target (blank = self)</label>
                        <input type="text" class="beh-act-wake-target" .value=${wakeTarget || ''} placeholder="self or character name" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="introduce,beg,demand,bribe" style="display:${show('introduce,beg,demand,bribe') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-social-target" .value=${introduceTarget || begTarget || demandTarget || bribeTarget || ''} placeholder="character" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="bribe" style="display:${show('bribe') ? 'block' : 'none'};">
                        <label>Item</label>
                        <input type="text" class="beh-act-bribe-item" .value=${bribeItem || ''} placeholder="coin" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="kiss,caress,lick,suck,bite,tickle,embrace" style="display:${show('kiss,caress,lick,suck,bite,tickle,embrace') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-intimacy-target" .value=${kissTarget || caressTarget || lickTarget || suckTarget || biteTarget || tickleTarget || embraceTarget || ''} placeholder="character" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="kiss,caress,lick,suck,bite,tickle,embrace" style="display:${show('kiss,caress,lick,suck,bite,tickle,embrace') ? 'block' : 'none'};">
                        <label>Where</label>
                        <input type="text" class="beh-act-intimacy-where" .value=${kissWhere || caressWhere || lickWhere || suckWhere || biteWhere || tickleWhere || embraceWhere || ''} placeholder="neck, lips..." style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="kiss,caress,lick,suck,bite,tickle,embrace" style="display:${show('kiss,caress,lick,suck,bite,tickle,embrace') ? 'block' : 'none'};">
                        <label>Intensity</label>
                        <select class="beh-act-intimacy-intensity" style="width:100%;">
                            <option value="soft" ?selected=${kissIntensity === 'soft'}>soft</option>
                            <option value="gentle" ?selected=${kissIntensity === 'gentle'}>gentle</option>
                            <option value="normal" ?selected=${kissIntensity === 'normal' || !kissIntensity}>normal</option>
                            <option value="firm" ?selected=${kissIntensity === 'firm'}>firm</option>
                            <option value="rough" ?selected=${kissIntensity === 'rough'}>rough</option>
                            <option value="hard" ?selected=${kissIntensity === 'hard'}>hard</option>
                        </select>
                    </div>
                    <div class="field beh-act-field" data-act="possess" style="display:${show('possess') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-possess-target" .value=${possessTarget || ''} placeholder="character or item" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="teach" style="display:${show('teach') ? 'block' : 'none'};">
                        <label>Student</label>
                        <input type="text" class="beh-act-teach-target" .value=${teachTarget || ''} placeholder="apprentice" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="teach" style="display:${show('teach') ? 'block' : 'none'};">
                        <label>Subject / Recipe</label>
                        <input type="text" class="beh-act-teach-subject" .value=${teachSubject || ''} placeholder="campfire" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="push_through,block" style="display:${show('push_through,block') ? 'block' : 'none'};">
                        <label>Direction / Target</label>
                        <input type="text" class="beh-act-block-target" .value=${pushThroughDirection || blockTarget || ''} placeholder="north or door" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="approach" style="display:${show('approach') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-approach-target" .value=${approachTarget || ''} placeholder="character" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="traverse" style="display:${show('traverse') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-traverse-target" .value=${traverseTarget || ''} placeholder="chasm" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="emote" style="display:${show('emote') ? 'block' : 'none'};">
                        <label>Emote Text</label>
                        <input type="text" class="beh-act-emote-text" .value=${emoteText || ''} placeholder="raises an eyebrow" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="carve" style="display:${show('carve') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-carve-target" .value=${carveTarget || ''} placeholder="wood" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="carve" style="display:${show('carve') ? 'block' : 'none'};">
                        <label>Text</label>
                        <input type="text" class="beh-act-carve-text" .value=${carveText || ''} placeholder="X marks the spot" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="gulp_down" style="display:${show('gulp_down') ? 'block' : 'none'};">
                        <label>Item</label>
                        <input type="text" class="beh-act-gulp-item" .value=${gulpItem || ''} placeholder="potion" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="pinch" style="display:${show('pinch') ? 'block' : 'none'};">
                        <label>Target</label>
                        <input type="text" class="beh-act-pinch-target" .value=${pinchTarget || ''} placeholder="character" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="pinch" style="display:${show('pinch') ? 'block' : 'none'};">
                        <label>Where</label>
                        <input type="text" class="beh-act-pinch-where" .value=${pinchWhere || ''} placeholder="cheek" style="width:100%;">
                    </div>
                    <div class="field beh-act-field" data-act="pinch" style="display:${show('pinch') ? 'block' : 'none'};">
                        <label>Intensity</label>
                        <select class="beh-act-pinch-intensity" style="width:100%;">
                            <option value="soft" ?selected=${pinchIntensity === 'soft'}>soft</option>
                            <option value="gentle" ?selected=${pinchIntensity === 'gentle'}>gentle</option>
                            <option value="normal" ?selected=${pinchIntensity === 'normal' || !pinchIntensity}>normal</option>
                            <option value="firm" ?selected=${pinchIntensity === 'firm'}>firm</option>
                            <option value="rough" ?selected=${pinchIntensity === 'rough'}>rough</option>
                            <option value="hard" ?selected=${pinchIntensity === 'hard'}>hard</option>
                        </select>
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
                             <div class="field beh-cond-field" data-cond="npc_emotion_is" style="display:${condType === 'npc_emotion_is' ? 'block' : 'none'};">
                                 <label>Emotion Name</label>
                                 <select id="beh-cond-emotion-name-${index}" style="width:100%;">
                                     <option value="neutral" ?selected=${cond.emotion === 'neutral'}>neutral</option>
                                     <option value="happy" ?selected=${cond.emotion === 'happy'}>happy</option>
                                     <option value="sad" ?selected=${cond.emotion === 'sad'}>sad</option>
                                     <option value="angry" ?selected=${cond.emotion === 'angry'}>angry</option>
                                     <option value="afraid" ?selected=${cond.emotion === 'afraid'}>afraid</option>
                                     <option value="surprised" ?selected=${cond.emotion === 'surprised'}>surprised</option>
                                     <option value="disgusted" ?selected=${cond.emotion === 'disgusted'}>disgusted</option>
                                 </select>
                             </div>
                             <div class="field beh-cond-field" data-cond="npc_emotion_is" style="display:${condType === 'npc_emotion_is' ? 'block' : 'none'};">
                                 <label>Operator</label>
                                 <select id="beh-cond-emotion-op-${index}" style="width:100%;">
                                     <option value="eq" ?selected=${cond.operator === 'eq'}>equals (name match)</option>
                                     <option value="gt" ?selected=${cond.operator === 'gt'}>intensity &gt;</option>
                                     <option value="gte" ?selected=${cond.operator === 'gte'}>intensity &gt;=</option>
                                     <option value="lt" ?selected=${cond.operator === 'lt'}>intensity &lt;</option>
                                     <option value="lte" ?selected=${cond.operator === 'lte'}>intensity &lt;=</option>
                                 </select>
                             </div>
                             <div class="field beh-cond-field" data-cond="npc_emotion_is" style="display:${condType === 'npc_emotion_is' ? 'block' : 'none'};">
                                 <label>Intensity Threshold</label>
                                 <input type="number" id="beh-cond-emotion-value-${index}" .value=${cond.value !== undefined ? cond.value : 0} min="0" max="1" step="0.1" style="width:100%;">
                             </div>
                             <div class="field beh-cond-field" data-cond="npc_is_hidden" style="display:${condType === 'npc_is_hidden' ? 'block' : 'none'};">
                                 <label>Should Be Hidden?</label>
                                 <select id="beh-cond-hidden-value-${index}" style="width:100%;">
                                     <option value="true" ?selected=${cond.value !== false}>Yes, hidden</option>
                                     <option value="false" ?selected=${cond.value === false}>No, visible</option>
                                 </select>
                             </div>
                             <div class="field beh-cond-field" data-cond="character_has_tag" style="display:${condType === 'character_has_tag' ? 'block' : 'none'};">
                                 <label>Tag</label>
                                 <input type="text" id="beh-cond-char-tag-${index}" .value=${cond.tag || ''} placeholder="vampire, faction:guard..." style="width:100%;">
                             </div>
                             <div class="field beh-cond-field" data-cond="character_has_tag" style="display:${condType === 'character_has_tag' ? 'block' : 'none'};">
                                 <label>Target</label>
                                 <select id="beh-cond-char-tag-target-${index}" style="width:100%;">
                                     <option value="self" ?selected=${!cond.target || cond.target === 'self'}>NPC (self)</option>
                                     <option value="player" ?selected=${cond.target === 'player'}>Player</option>
                                     <option value="triggering" ?selected=${cond.target === 'triggering'}>Triggering character</option>
                                 </select>
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
                 } else if (condType === 'npc_emotion_is') {
                     cond.emotion = document.getElementById(`beh-cond-emotion-name-${index}`)?.value || 'neutral';
                     cond.operator = document.getElementById(`beh-cond-emotion-op-${index}`)?.value || 'eq';
                     cond.value = parseFloat(document.getElementById(`beh-cond-emotion-value-${index}`)?.value) || 0;
                 } else if (condType === 'npc_is_hidden') {
                     cond.value = document.getElementById(`beh-cond-hidden-value-${index}`)?.value !== 'false';
                 } else if (condType === 'character_has_tag') {
                     cond.tag = document.getElementById(`beh-cond-char-tag-${index}`)?.value || '';
                     cond.target = document.getElementById(`beh-cond-char-tag-target-${index}`)?.value || 'self';
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
             } else if (actType === 'add_memory') {
                 action.text = card.querySelector('.beh-act-mem-text')?.value || '';
                 action.importance = parseInt(card.querySelector('.beh-act-mem-importance')?.value) || 5;
                 const tagsRaw = card.querySelector('.beh-act-mem-tags')?.value || '';
                 action.tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];
             } else if (actType === 'set_emotion') {
                 action.emotion = card.querySelector('.beh-act-emotion-name')?.value || 'neutral';
                 action.intensity = parseFloat(card.querySelector('.beh-act-emotion-intensity')?.value) || 0.5;
             } else if (actType === 'set_flag') {
                 action.key = card.querySelector('.beh-act-flag-key')?.value || '';
                 action.value = card.querySelector('.beh-act-flag-value')?.value || 'true';
                 if (action.value === 'true') action.value = true;
                 else if (action.value === 'false') action.value = false;
              } else if (actType === 'hide_in' || actType === 'hide_behind' || actType === 'hide_under') {
                  action.target = card.querySelector('.beh-act-hide-target')?.value || '';
              } else if (actType === 'attack') {
                  action.target = card.querySelector('.beh-act-attack-target')?.value || '';
                  action.weapon = card.querySelector('.beh-act-attack-weapon')?.value || '';
                  action.where = card.querySelector('.beh-act-attack-where')?.value || '';
              } else if (actType === 'throw') {
                  action.item = card.querySelector('.beh-act-throw-item')?.value || '';
                  action.target = card.querySelector('.beh-act-throw-target')?.value || '';
              } else if (actType === 'break') {
                  action.item = card.querySelector('.beh-act-break-item')?.value || '';
              } else if (actType === 'take') {
                  action.item = card.querySelector('.beh-act-take-item')?.value || '';
              } else if (actType === 'drop') {
                  action.item = card.querySelector('.beh-act-drop-item')?.value || '';
              } else if (actType === 'put_in') {
                  action.item = card.querySelector('.beh-act-put-item')?.value || '';
                  action.container = card.querySelector('.beh-act-put-container')?.value || '';
              } else if (actType === 'equip') {
                  action.item = card.querySelector('.beh-act-equip-item')?.value || '';
                  action.slot = card.querySelector('.beh-act-equip-slot')?.value || '';
              } else if (actType === 'unequip') {
                  action.item = card.querySelector('.beh-act-unequip-item')?.value || '';
                  action.slot = action.item;
              } else if (actType === 'use') {
                  action.item = card.querySelector('.beh-act-use-item')?.value || '';
                  action.target = card.querySelector('.beh-act-use-target')?.value || '';
              } else if (actType === 'eat') {
                  action.item = card.querySelector('.beh-act-eat-item')?.value || '';
              } else if (actType === 'drink') {
                  action.item = card.querySelector('.beh-act-drink-item')?.value || '';
              } else if (actType === 'craft') {
                  action.recipe = card.querySelector('.beh-act-craft-recipe')?.value || '';
              } else if (actType === 'combine') {
                  action.source = card.querySelector('.beh-act-combine-source')?.value || '';
                  action.target = card.querySelector('.beh-act-combine-target')?.value || '';
              } else if (actType === 'repair') {
                  action.item = card.querySelector('.beh-act-repair-item')?.value || '';
                  action.kit = card.querySelector('.beh-act-repair-kit')?.value || '';
              } else if (actType === 'read') {
                  action.item = card.querySelector('.beh-act-read-item')?.value || '';
              } else if (actType === 'open') {
                  action.target = card.querySelector('.beh-act-open-target')?.value || '';
              } else if (actType === 'close') {
                  action.target = card.querySelector('.beh-act-close-target')?.value || '';
              } else if (actType === 'lock') {
                  action.target = card.querySelector('.beh-act-lock-target')?.value || '';
              } else if (actType === 'unlock') {
                  action.target = card.querySelector('.beh-act-unlock-target')?.value || '';
              } else if (actType === 'push') {
                  action.target = card.querySelector('.beh-act-push-target')?.value || '';
                  action.direction = card.querySelector('.beh-act-push-direction')?.value || '';
              } else if (actType === 'turn') {
                  action.target = card.querySelector('.beh-act-turn-target')?.value || '';
              } else if (actType === 'search') {
                  action.target = card.querySelector('.beh-act-search-target')?.value || '';
              } else if (actType === 'give') {
                  action.item = card.querySelector('.beh-act-give-item')?.value || '';
                  action.target = card.querySelector('.beh-act-give-target')?.value || '';
              } else if (actType === 'steal') {
                  action.item = card.querySelector('.beh-act-steal-item')?.value || '';
                  action.target = card.querySelector('.beh-act-steal-target')?.value || '';
              } else if (actType === 'follow') {
                  action.target = card.querySelector('.beh-act-follow-target')?.value || '';
              } else if (actType === 'dash') {
                  action.direction = card.querySelector('.beh-act-dash-dir')?.value || '';
              } else if (actType === 'crawl') {
                  action.direction = card.querySelector('.beh-act-dash-dir')?.value || '';
              } else if (actType === 'climb') {
                  action.direction = card.querySelector('.beh-act-dash-dir')?.value || '';
              } else if (actType === 'jump') {
                  action.direction = card.querySelector('.beh-act-dash-dir')?.value || '';
              } else if (actType === 'toggle_way') {
                  action.direction = card.querySelector('.beh-act-toggle-dir')?.value || '';
                  action.way_action = card.querySelector('.beh-act-toggle-action')?.value || 'open';
              } else if (actType === 'grab' || actType === 'pin' || actType === 'release') {
                  action.target = card.querySelector('.beh-act-grab-target')?.value || '';
              } else if (actType === 'drag') {
                  action.target = card.querySelector('.beh-act-grab-target')?.value || '';
                  action.direction = card.querySelector('.beh-act-drag-dir')?.value || '';
              } else if (actType === 'examine') {
                  action.target = card.querySelector('.beh-act-examine-target')?.value || '';
              } else if (actType === 'place') {
                  action.item = card.querySelector('.beh-act-place-item')?.value || '';
                  action.target = card.querySelector('.beh-act-place-target')?.value || '';
                  action.relation = card.querySelector('.beh-act-place-relation')?.value || 'on';
              } else if (actType === 'remove') {
                  action.item = card.querySelector('.beh-act-remove-item')?.value || '';
              } else if (actType === 'hold' || actType === 'weigh' || actType === 'inventory' || actType === 'carry') {
                  action.item = card.querySelector('.beh-act-hold-item')?.value || '';
              } else if (actType === 'swap') {
                  action.item = card.querySelector('.beh-act-swap-item')?.value || '';
                  action.target = card.querySelector('.beh-act-swap-target')?.value || '';
              } else if (actType === 'adorn') {
                  action.item = card.querySelector('.beh-act-adorn-item')?.value || '';
                  action.target = card.querySelector('.beh-act-adorn-target')?.value || '';
              } else if (actType === 'rest' || actType === 'sleep' || actType === 'meditate') {
                  action.minutes = parseInt(card.querySelector('.beh-act-rest-min')?.value) || 10;
              } else if (actType === 'bathe') {
                  action.target = card.querySelector('.beh-act-bathe-target')?.value || '';
                  action.minutes = parseInt(card.querySelector('.beh-act-bathe-min')?.value) || 10;
              } else if (actType === 'wake') {
                  action.target = card.querySelector('.beh-act-wake-target')?.value || '';
              } else if (actType === 'introduce' || actType === 'beg' || actType === 'demand') {
                  action.target = card.querySelector('.beh-act-social-target')?.value || '';
              } else if (actType === 'bribe') {
                  action.target = card.querySelector('.beh-act-social-target')?.value || '';
                  action.item = card.querySelector('.beh-act-bribe-item')?.value || '';
              } else if (actType === 'kiss' || actType === 'caress' || actType === 'lick' || actType === 'suck' || actType === 'bite' || actType === 'tickle' || actType === 'embrace') {
                  action.target = card.querySelector('.beh-act-intimacy-target')?.value || '';
                  action.where = card.querySelector('.beh-act-intimacy-where')?.value || '';
                  action.intensity = card.querySelector('.beh-act-intimacy-intensity')?.value || 'normal';
              } else if (actType === 'possess') {
                  action.target = card.querySelector('.beh-act-possess-target')?.value || '';
              } else if (actType === 'teach') {
                  action.target = card.querySelector('.beh-act-teach-target')?.value || '';
                  action.subject = card.querySelector('.beh-act-teach-subject')?.value || '';
              } else if (actType === 'cook') {
                  action.recipe = card.querySelector('.beh-act-cook-recipe')?.value || '';
              } else if (actType === 'push_through' || actType === 'block') {
                  action.direction = action.target = card.querySelector('.beh-act-block-target')?.value || '';
              } else if (actType === 'approach') {
                  action.target = card.querySelector('.beh-act-approach-target')?.value || '';
              } else if (actType === 'traverse') {
                  action.target = card.querySelector('.beh-act-traverse-target')?.value || '';
              } else if (actType === 'emote') {
                  action.text = card.querySelector('.beh-act-emote-text')?.value || '';
              } else if (actType === 'carve') {
                  action.target = card.querySelector('.beh-act-carve-target')?.value || '';
                  action.text = card.querySelector('.beh-act-carve-text')?.value || '';
              } else if (actType === 'gulp_down') {
                  action.item = card.querySelector('.beh-act-gulp-item')?.value || '';
              } else if (actType === 'pinch') {
                  action.target = card.querySelector('.beh-act-pinch-target')?.value || '';
                  action.where = card.querySelector('.beh-act-pinch-where')?.value || '';
                  action.intensity = card.querySelector('.beh-act-pinch-intensity')?.value || 'normal';
              }
              // 'unhide', 'wait', 'manifest', 'vanish', 'wraith_form', 'spawn_body_item', 'help', 'commands', 'who', 'time', 'score', 'map', 'save', 'quit', 'version', 'struggle', 'escape', 'fumble', 'listen', 'read', 'light', 'activate', 'toggle', 'drop_all', 'take_all', 'lie_down' need no extra params or use existing fields

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