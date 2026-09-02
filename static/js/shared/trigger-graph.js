/**
 * TriggerGraph — Node-based visual trigger editor (ComfyUI-style).
 *
 * Usage:
 *   TriggerGraph.show({ mode: 'trigger'|'behavior', graph: {nodes, wires}, onSave: (graph) => {} });
 *
 * Graph format:
 *   { nodes: [{ id, type, x, y, w, props, _expanded }], wires: [{ id, from: [nodeId, socket], to: [nodeId, socket] }] }
 *
 * Node types (mode = 'trigger'):
 *   trigger    — entry point (trigger_type) — output socket on right
 *   condition  — branch (condition_type) — input left, output_yes bottom, output_no bottom-right
 *   effect     — action (effect_type) — input left, output right
 *
 * Node types (mode = 'behavior'):
 *   behavior   — top-level container (trigger/interval/priority) — output right
 *   condition  — shared branch node (full condition coverage) — input left, yes/no bottom
 *   action     — behavior action (action_type, flat dict) — input left, output right
 *   state      — set_npc_state action rendered distinctly — input left, output right
 */
// Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
const triggerGraphTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.TriggerGraph = (() => {
    const TG = {};

    // ─── Socket layout per node type ───
    // Sockets on nodes: inputs on LEFT, outputs on RIGHT, YES/NO on BOTTOM
    const NODE_DEFS = {
        trigger: {
            label: '⚡ Trigger', color: '#e3b341',
            summary: (p) => (Array.isArray(p.trigger_type) ? p.trigger_type.join(', ') : (p.trigger_type || 'on_use')),
            sockets: [
                { id: 'output', side: 'right', label: '→', color: '#e3b341' }
            ],
            fields: (p) => {
                const types = Array.isArray(p.trigger_type) ? p.trigger_type : [p.trigger_type || 'on_use'];
                // Full catalog from the shared registry (same list the form editor uses).
                const catalog = window.TriggerTypes?.TRIGGER_TYPES || [
                    'on_use','on_take','on_drop','on_examine','on_tick','on_use_on','on_equip','on_unequip',
                    'on_toggle_on','on_toggle_off','on_depleted','on_open','on_close','on_state_enter','on_state_exit',
                    'on_fail_jump','on_fail_climb'
                ];
                const all = [...new Set([...types, ...catalog])];
                return `
                <div class="tg-field-row"><label>Type (Ctrl+click = multi)</label>
                    <select class="tg-field" data-key="trigger_type" multiple size="5" onchange="TriggerGraph._onFieldChange(this)">${all.map(t => `<option value="${t}" ${types.includes(t)?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</select>
                </div>
                <div class="tg-field-row" style="display:${types.includes('on_use_on')?'':'none'}"><label>Target Tag</label>
                    <input class="tg-field" data-key="target_tag" value="${p.target_tag||''}" placeholder="oil_lamp, key_item, etc" list="tg-tags" onchange="TriggerGraph._onFieldChange(this)">
                </div>
                <div class="tg-field-row" style="display:${(types.includes('on_state_enter')||types.includes('on_state_exit'))?'':'none'}"><label>Target State</label>
                    <input class="tg-field" data-key="target_state" value="${p.target_state||''}" placeholder="lit, open..." list="tg-node-states" onchange="TriggerGraph._onFieldChange(this)">
                </div>
            `;
            }
        },
        condition: {
            label: '❓ Condition', color: '#f85149',
            summary: (p) => `${p.condition_type||'?'}${p.value ? ' = '+p.value : ''}`,
            sockets: [
                { id: 'input', side: 'left', label: '↓', color: '#f85149' },
                { id: 'output_yes', side: 'bottom', label: '✓', color: '#3fb950' },
                { id: 'output_no', side: 'bottom', label: '✗', color: '#f85149' }
            ],
            fields: (p) => {
                const ct = p.condition_type || 'area_temp';
                const showVal = ['area_temp','vital','uses_reached','uses_above','random_chance','state_equals','has_trait','has_tag','time_of_day','weather'].includes(ct);
                const showSkill = ['skill_check','save_throw'].includes(ct);
                const showComp = ['area_temp','vital','vital_above','vital_below'].includes(ct);
                const showStat = ['vital','vital_above','vital_below'].includes(ct);
                const showItem = ct === 'is_equipped';
                const showState = ct === 'state_equals';
                const showTarget = ['save_throw','has_trait','has_tag','vital','vital_above','vital_below','is_equipped','area_temp'].includes(ct);
                return `
                <div class="tg-field-row"><label>Type</label>
                    <select class="tg-field" data-key="condition_type" onchange="TriggerGraph._onFieldChange(this);TriggerGraph._rerenderNode('${'NODEID'}')">${[
                        ['⚙️ General', ['eq','random_chance','state_equals','time_of_day','speech_matches','skill_check','save_throw','tick_since_state']],
                        ['🧍 Character', ['vital','vital_above','vital_below','has_trait']],
                        ['📦 Item', ['has_item','has_items','is_equipped','uses_reached','uses_above','item_relationship']],
                        ['🌍 Area / Environment', ['area_temp','temperature_below','temperature_above','in_area','proximity','weather','area_has_status']],
                        ['🧠 NPC (behaviors)', ['npc_emotion_is','npc_is_hidden','character_has_tag']],
                    ].map(([g, list]) => `<optgroup label="${g}">${list.map(t => `<option value="${t}" ${ct===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</optgroup>`).join('')}</select>
                </div>
                <div class="tg-cond-eq" style="display:${ct==='eq'?'':'none'}">
                    <div class="tg-field-row"><label>Target Key</label><input class="tg-field" data-key="target" value="${p.target||'npc_state'}" placeholder="npc_state, npc_area..." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Value</label><input class="tg-field" data-key="value" value="${p.value||''}" list="${(p.target||'npc_state')==='npc_state'?'tg-npc-states':''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-inarea" style="display:${ct==='in_area'?'':'none'}">
                    <div class="tg-field-row"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label>
                        <select class="tg-field" data-key="target" onchange="TriggerGraph._onFieldChange(this)"><option value="npc" ${(p.target||'npc')==='npc'?'selected':''}>NPC</option><option value="player" ${p.target==='player'?'selected':''}>Player</option></select>
                    </div>
                </div>
                <div class="tg-cond-ticks" style="display:${ct==='tick_since_state'?'':'none'}">
                    <div class="tg-field-row"><label>Min Ticks</label><input class="tg-field" data-key="min_ticks" type="number" value="${p.min_ticks ?? 0}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-prox" style="display:${ct==='proximity'?'':'none'}">
                    <div class="tg-field-row"><label>Max Areas</label><input class="tg-field" data-key="max_areas" type="number" value="${p.max_areas ?? 0}" placeholder="0 = same area" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-areastat" style="display:${ct==='area_has_status'?'':'none'}">
                    <div class="tg-field-row"><label>Status</label><select class="tg-field" data-key="status_type" onchange="TriggerGraph._onFieldChange(this)">${['on_fire','flooded','poison_gas','smoke','blessed','darkness_magic'].map(s => `<option value="${s}" ${p.status_type===s?'selected':''}>${s}</option>`).join('')}</select></div>
                    <div class="tg-field-row"><label>Area (blank = current)</label><input class="tg-field" data-key="target" value="${p.target||''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-itemrel" style="display:${ct==='item_relationship'?'':'none'}">
                    <div class="tg-field-row"><label>Relation</label>
                        <select class="tg-field" data-key="relation" onchange="TriggerGraph._onFieldChange(this)">${['in','on','under','behind','beside','at'].map(r => `<option value="${r}" ${(p.relation||'in')===r?'selected':''}>${r}</option>`).join('')}</select>
                    </div>
                    <div class="tg-field-row"><label>Target Node</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="node_id (item is IN/ON this)" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-emotion" style="display:${ct==='npc_emotion_is'?'':'none'}">
                    <div class="tg-field-row"><label>Emotion</label><input class="tg-field" data-key="emotion" value="${p.emotion||''}" placeholder="curious, angry, fearful..." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Operator</label>
                        <select class="tg-field" data-key="operator" onchange="TriggerGraph._onFieldChange(this)">${['eq','gt','gte','lt','lte'].map(o => `<option value="${o}" ${(p.operator||'eq')===o?'selected':''}>${o}</option>`).join('')}</select>
                    </div>
                    <div class="tg-field-row"><label>Value</label><input class="tg-field" data-key="value" value="${p.value!==undefined&&p.value!==''?p.value:''}" placeholder="0-1 intensity" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-hidden" style="display:${ct==='npc_is_hidden'?'':'none'}">
                    <div class="tg-field-row"><label>Hidden</label>
                        <select class="tg-field" data-key="value" onchange="TriggerGraph._onFieldChange(this)"><option value="true" ${(p.value===true||p.value==='true')?'selected':''}>True</option><option value="false" ${(!p.value||p.value==='false')?'selected':''}>False</option></select>
                    </div>
                </div>
                <div class="tg-cond-chartag" style="display:${ct==='character_has_tag'?'':'none'}">
                    <div class="tg-field-row"><label>Tag</label><input class="tg-field" data-key="tag" value="${p.tag||''}" placeholder="hostile, stealthy..." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label>
                        <select class="tg-field" data-key="target" onchange="TriggerGraph._onFieldChange(this)"><option value="self" ${(p.target||'self')==='self'?'selected':''}>Self (NPC)</option><option value="player" ${p.target==='player'?'selected':''}>Player</option><option value="triggering" ${p.target==='triggering'?'selected':''}>Triggering character</option></select>
                    </div>
                </div>
                <div class="tg-cond-val" style="display:${showVal?'':'none'}">
                    <div class="tg-field-row"><label>Value</label><input class="tg-field" data-key="value" value="${p.value||''}" list="${ct==='has_trait'?'tg-traits':ct==='has_tag'?'tg-tags':ct==='weather'?'tg-weather':''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-comp" style="display:${showComp?'':'none'}">
                    <div class="tg-field-row"><label>Comparator</label>
                        <select class="tg-field" data-key="operator" onchange="TriggerGraph._onFieldChange(this)">${['lt','le','eq','ge','gt'].map(o => `<option value="${o}" ${(p.operator||'lt')===o?'selected':''}>${o}</option>`).join('')}</select>
                    </div>
                </div>
                <div class="tg-cond-stat" style="display:${showStat?'':'none'}">
                    <div class="tg-field-row"><label>Vital</label><input class="tg-field" data-key="stat" value="${p.stat||'HP'}" placeholder="HP, Energy..." list="tg-vitals" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-item" style="display:${showItem?'':'none'}">
                    <div class="tg-field-row"><label>Item</label><input class="tg-field" data-key="item" value="${p.item||''}" placeholder="torch, key..." list="tg-items" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-skill" style="display:${showSkill?'':'none'}">
                    <div class="tg-field-row"><label>${ct==='save_throw'?'Stat / Skill':'Skill'}</label><input class="tg-field" data-key="skill" value="${p.skill||(ct==='save_throw'?'DEX':'Athletics')}" list="tg-skills" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>DC</label><input class="tg-field" data-key="dc" type="number" value="${p.dc||(ct==='save_throw'?12:10)}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-state" style="display:${showState?'':'none'}">
                    <div class="tg-field-row"><label>Node</label><input class="tg-field" data-key="node" value="${p.node||p.target||''}" placeholder="node_id" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="value" value="${p.value||''}" placeholder="on, open..." list="tg-node-states" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-target" style="display:${showTarget?'':'none'}">
                    <div class="tg-field-row"><label>Target</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="blank = self" list="tg-char-list" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>`;
            }
        },
        effect: {
            label: '⚡ Effect', color: '#58a6ff',
            summary: (p) => `${p.effect_type||'?'}${p.message ? ': "'+p.message.substring(0,25)+'"' : ''}`,
            sockets: [
                { id: 'input', side: 'left', label: '→', color: '#58a6ff' },
                { id: 'output', side: 'right', label: '→', color: '#58a6ff' }
            ],
            fields: (p) => {
                const et = p.effect_type || 'message';
                const GROUPS = [
                    ['⚙️ General', [['message','💬 Show Message'],['destroy_self','💥 Destroy Self'],['save','🎲 Save Gate (fear/hazard)'],['give_item','🎁 Give Item'],['set_state','🔧 Set State'],['set_hidden','👻 Set Hidden/Visible'],['end_scenario','🏁 End Scenario'],['restart_scenario','🔄 Restart Scenario'],['teleport','🌀 Teleport'],['rename','✏️ Rename'],['add_tag','🏷️ Add Tag'],['remove_tag','🏷️ Remove Tag'],['set_parameter','🔑 Set Parameter'],['adjust_parameter','🔢 Adjust Parameter'],['schedule_trigger','⏳ Schedule Trigger'],['llm_respond','🤖 LLM Response'],['set_time','🕐 Set Time'],['set_date','📅 Set Date']]],
                    ['🌦️ Weather / Forecast', [['set_weather','🌧️ Set Weather'],['forecast_override','🌩️ Forecast Override'],['adjust_forecast','🌡️ Adjust Forecast'],['apply_area_status','🔥 Apply Area Status'],['clear_area_status','🧹 Clear Area Status'],['set_wet','💧 Set Wet']]],
                    ['🧍 Character', [['damage','💔 Deal Damage'],['heal','❤️ Heal'],['spawn_character','🧑 Spawn Character'],['adjust_vital','📊 Adjust Vital'],['apply_trait','⭐ Apply Trait'],['remove_trait','⭐ Remove Trait'],['apply_condition','🩸 Apply Condition'],['remove_condition','🩹 Remove Condition'],['surface_memory','🧠 Surface Memory'],['suppress_memory','🚫 Suppress Memory'],['unblock_memory','🔓 Unblock Memory']]],
                    ['📦 Item', [['spawn_item','📦 Spawn Item'],['remove_item','🗑️ Remove Item'],['consume_item','🍽️ Consume Item'],['adjust_uses','🔢 Adjust Uses'],['set_description','📝 Set Description'],['append_description','📝 Append Description']]],
                    ['🌍 Area / Environment', [['set_environment','🌡️ Set Environment'],['adjust_environment','🌡️ Adjust Environment (+/-)'],['scry','🔭 Scry (distant view)'],['spawn_area','🏠 Spawn Area']]],
                    ['🚪 Way', [['unlock_way','🔓 Unlock Way'],['spawn_way','🚪 Spawn Way'],['set_way_target','🔀 Set Way Target'],['set_way_view','👁 Set Way View']]],
                ];
                const known = GROUPS.flatMap(([, list]) => list.map(([v]) => v));
                const opts = GROUPS.map(([g, list]) => `<optgroup label="${g}">${list.map(([v, l]) => `<option value="${v}" ${et===v?'selected':''}>${l}</option>`).join('')}</optgroup>`).join('');
                const unknownOpt = known.includes(et) ? '' : `<option value="${et}" selected>${et}</option>`;
                const saveBranch = (side, title) => `
                    <div class="tg-field-row"><label>${title}</label>
                        <select class="tg-field" data-key="${side}_type" onchange="TriggerGraph._onFieldChange(this);TriggerGraph._rerenderNode('${'NODEID'}')">
                            ${['none','message','apply_condition','damage'].map(t => `<option value="${t}" ${(p[side+'_type']||'none')===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}
                        </select>
                    </div>
                    <div class="tg-field-row" style="display:${(p[side+'_type']||'none')==='message'?'':'none'}"><label>Message</label><input class="tg-field" data-key="${side}_msg" value="${p[side+'_msg']||''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div style="display:${(p[side+'_type']||'none')==='apply_condition'?'':'none'};padding-left:6px;">
                        <div class="tg-field-row"><label>Condition</label><input class="tg-field" data-key="${side}_cond" value="${p[side+'_cond']||''}" list="tg-condition-list" placeholder="frightened, poisoned..." onchange="TriggerGraph._onFieldChange(this)"></div>
                        <div class="tg-field-row"><label>Duration</label><input class="tg-field" data-key="${side}_dur" type="number" value="${p[side+'_dur']!==undefined?p[side+'_dur']:''}" placeholder="blank = default" onchange="TriggerGraph._onFieldChange(this)"></div>
                        <div class="tg-field-row"><label>Source</label><input class="tg-field" data-key="${side}_src" value="${p[side+'_src']||''}" placeholder="source label" onchange="TriggerGraph._onFieldChange(this)"></div>
                        <div class="tg-field-row"><label>Source type</label>
                            <select class="tg-field" data-key="${side}_src_type" onchange="TriggerGraph._onFieldChange(this)"><option value="" ${!p[side+'_src_type']?'selected':''}>— none —</option>${['way','area','item','character'].map(t => `<option value="${t}" ${p[side+'_src_type']===t?'selected':''}>${t}</option>`).join('')}</select>
                        </div>
                    </div>
                    <div class="tg-field-row" style="display:${(p[side+'_type']||'none')==='damage'?'':'none'}"><label>Damage</label><input class="tg-field" data-key="${side}_dmg" type="number" value="${p[side+'_dmg']!==undefined?p[side+'_dmg']:5}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Advanced JSON (${side === 'succ' ? 'on_success' : 'on_fail'} array)</label><textarea class="tg-field" data-key="${side}_json" rows="2" placeholder='[{"type":"message","params":{"message":"..."}}]' onchange="TriggerGraph._onFieldChange(this)">${p[side+'_json']?(typeof p[side+'_json']==='string'?p[side+'_json']:JSON.stringify(p[side+'_json'])):''}</textarea></div>`;
                return `
                <div class="tg-field-row"><label>Type</label>
                    <select class="tg-field" data-key="effect_type" onchange="TriggerGraph._onFieldChange(this);TriggerGraph._rerenderNode('${'NODEID'}')">${unknownOpt}${opts}</select>
                </div>
                <div class="tg-eff-save" style="display:${et==='save'?'':'none'}">
                    <div class="tg-field-row"><label>Roll</label>
                        <select class="tg-field" data-key="save_mode" onchange="TriggerGraph._onFieldChange(this);TriggerGraph._rerenderNode('${'NODEID'}')"><option value="stat" ${(p.save_mode||'stat')==='stat'?'selected':''}>Ability</option><option value="skill" ${p.save_mode==='skill'?'selected':''}>Skill</option></select>
                    </div>
                    <div class="tg-field-row" style="display:${(p.save_mode||'stat')==='stat'?'':'none'}"><label>Stat</label>
                        <select class="tg-field" data-key="save_stat" onchange="TriggerGraph._onFieldChange(this)">${['STR','DEX','CON','INT','WIS','CHA'].map(s => `<option value="${s}" ${(p.save_stat||'WIS')===s?'selected':''}>${s}</option>`).join('')}</select>
                    </div>
                    <div class="tg-field-row" style="display:${p.save_mode==='skill'?'':'none'}"><label>Skill</label><input class="tg-field" data-key="save_skill" value="${p.save_skill||'Athletics'}" list="tg-skills" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>DC</label><input class="tg-field" data-key="save_dc" type="number" value="${p.save_dc!==undefined?p.save_dc:12}" min="1" max="30" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ${saveBranch('succ', 'On success')}
                    ${saveBranch('fail', 'On fail')}
                </div>
                <div class="tg-eff-hint" style="display:${['destroy_self','end_scenario','restart_scenario'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><div style="font-size:9px;color:var(--text-muted);">${et==='destroy_self'?'Removes the triggering item from the world.':et==='end_scenario'?'Ends the game (victory/defeat screen).':'Restarts the scenario from the beginning.'}</div></div>
                </div>
                <div class="tg-eff-settime" style="display:${et==='set_time'?'':'none'}">
                    <div class="tg-field-row"><label>Time (HH:MM or hour)</label><input class="tg-field" data-key="time" value="${p.time || (p.hour !== undefined ? p.hour : '')}" placeholder="14:30" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-setdate" style="display:${et==='set_date'?'':'none'}">
                    <div class="tg-field-row"><label>Day / Month / Year</label><div style="display:flex;gap:4px;">
                        <input class="tg-field" data-key="day" type="number" value="${p.day ?? ''}" placeholder="day" onchange="TriggerGraph._onFieldChange(this)">
                        <input class="tg-field" data-key="month" type="number" value="${p.month ?? ''}" placeholder="month" onchange="TriggerGraph._onFieldChange(this)">
                        <input class="tg-field" data-key="year" type="number" value="${p.year ?? ''}" placeholder="year" onchange="TriggerGraph._onFieldChange(this)">
                    </div></div>
                </div>
                <div class="tg-eff-setweather" style="display:${et==='set_weather'?'':'none'}">
                    <div class="tg-field-row"><label>Weather</label><select class="tg-field" data-key="weather" onchange="TriggerGraph._onFieldChange(this)">${['clear','cloudy','windy','rainy','stormy','foggy','snowy'].map(w => `<option value="${w}" ${p.weather===w?'selected':''}>${w}</option>`).join('')}</select></div>
                    <div class="tg-field-row"><label>Duration (ticks)</label><input class="tg-field" data-key="duration_ticks" type="number" value="${p.duration_ticks ?? ''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-fcast" style="display:${et==='forecast_override'?'':'none'}">
                    <div class="tg-field-row"><label>Weather</label><select class="tg-field" data-key="weather" onchange="TriggerGraph._onFieldChange(this)"><option value="" ${!p.weather?'selected':''}>— keep —</option>${['clear','cloudy','windy','rainy','stormy','foggy','snowy'].map(w => `<option value="${w}" ${p.weather===w?'selected':''}>${w}</option>`).join('')}</select></div>
                    <div class="tg-field-row"><label>Wind</label><select class="tg-field" data-key="wind" onchange="TriggerGraph._onFieldChange(this)"><option value="" ${!p.wind?'selected':''}>— keep —</option>${['none','breeze','wind','gale','storm','hurricane'].map(w => `<option value="${w}" ${p.wind===w?'selected':''}>${w}</option>`).join('')}</select></div>
                    <div class="tg-field-row"><label>Temp mod (°C)</label><input class="tg-field" data-key="temperature_mod" type="number" value="${p.temperature_mod ?? ''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Duration (ticks)</label><input class="tg-field" data-key="duration_ticks" type="number" value="${p.duration_ticks ?? ''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target (blank = global)</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="global / area id" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Blood moon</label><input type="checkbox" data-key="blood_moon" ${p.blood_moon===true?'checked':''} onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-fcastadj" style="display:${et==='adjust_forecast'?'':'none'}">
                    <div class="tg-field-row"><label>Temp mod delta</label><input class="tg-field" data-key="temperature_mod_delta" type="number" value="${p.temperature_mod_delta ?? ''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Light mod delta</label><input class="tg-field" data-key="light_mod_delta" type="number" value="${p.light_mod_delta ?? ''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Duration (ticks)</label><input class="tg-field" data-key="duration_ticks" type="number" value="${p.duration_ticks ?? ''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-astat" style="display:${['apply_area_status','clear_area_status'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Area (blank = current)</label><input class="tg-field" data-key="target" value="${p.target||''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Status</label><select class="tg-field" data-key="status_type" onchange="TriggerGraph._onFieldChange(this)">${['on_fire','flooded','poison_gas','smoke','blessed','darkness_magic'].map(s => `<option value="${s}" ${p.status_type===s?'selected':''}>${s}</option>`).join('')}</select></div>
                    ${et==='apply_area_status' ? `<div class="tg-field-row"><label>Severity (1-5)</label><input class="tg-field" data-key="severity" type="number" value="${p.severity ?? 1}" min="1" max="5" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Duration (ticks)</label><input class="tg-field" data-key="duration" type="number" value="${p.duration ?? ''}" onchange="TriggerGraph._onFieldChange(this)"></div>` : ''}
                </div>
                <div class="tg-eff-setwet" style="display:${et==='set_wet'?'':'none'}">
                    <div class="tg-field-row"><label>Wet</label><select class="tg-field" data-key="wet" onchange="TriggerGraph._onFieldChange(this)"><option value="true" ${p.wet!==false?'selected':''}>Soak</option><option value="false" ${p.wet===false?'selected':''}>Dry</option></select></div>
                    <div class="tg-field-row"><label>Item node (blank = equipped)</label><input class="tg-field" data-key="node_id" value="${p.node_id||''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-tag" style="display:${['add_tag','remove_tag'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Tag</label><input class="tg-field" data-key="tag" value="${p.tag||''}" placeholder="flammable" list="tg-tags" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Node</label><input class="tg-field" data-key="node_id" value="${p.node_id||'self'}" placeholder="self or node_id" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Message (optional)</label><input class="tg-field" data-key="message" value="${p.message||''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-trait" style="display:${['apply_trait','remove_trait'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Trait</label><input class="tg-field" data-key="trait" value="${p.trait||''}" placeholder="dark_vision, hardy, allergic..." list="tg-traits" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label><input class="tg-field" data-key="target" value="${p.target||'self'}" list="tg-char-list" placeholder="self or character name" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='apply_trait'?'':'none'}"><label>Param</label><input class="tg-field" data-key="param" value="${p.param!==undefined?p.param:'true'}" placeholder="true or value" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-condition" style="display:${['apply_condition','remove_condition'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Condition</label><input class="tg-field" data-key="condition" value="${p.condition||''}" list="tg-condition-list" placeholder="poisoned, blind, exhausted..." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label>
                        <select class="tg-field" data-key="target_by" onchange="TriggerGraph._onFieldChange(this);TriggerGraph._rerenderNode('${'NODEID'}')">
                            <option value="self" ${!(p.target_by)&&(p.target==='self'||!p.target)?'selected':''}>Self (actor)</option>
                            <option value="all_in_area" ${p.target_by==='all_in_area'?'selected':''}>All characters in area</option>
                            <option value="name" ${p.target_by==='name'?'selected':''}>By name</option>
                            <option value="tag" ${p.target_by==='tag'?'selected':''}>By tag</option>
                            <option value="trait" ${p.target_by==='trait'?'selected':''}>By trait</option>
                            <option value="type" ${p.target_by==='type'?'selected':''}>By type</option>
                        </select>
                    </div>
                    <div class="tg-field-row" style="display:${(p.target_by&&p.target_by!=='self'&&p.target_by!=='all_in_area')||(!p.target_by&&p.target&&p.target!=='self')?'':'none'}"><label>${p.target_by==='tag'?'Tag':p.target_by==='trait'?'Trait':p.target_by==='type'?'Type (item/character/way/area)':'Name'}</label><input class="tg-field" data-key="${p.target_by?'target_value':'target'}" value="${p.target_by?(p.target_value||''):(p.target||'')}" list="${p.target_by==='name'?'tg-char-list':p.target_by==='tag'?'tg-tags':p.target_by==='trait'?'tg-traits':''}" placeholder="${p.target_by==='tag'?'vampire, wolf...':p.target_by==='trait'?'hostile, dark_vision...':p.target_by==='type'?'character, item...':'name'}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Duration</label><input class="tg-field" data-key="duration" type="number" value="${p.duration!==undefined?p.duration:''}" placeholder="blank = default" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Source</label><input class="tg-field" data-key="source" value="${p.source||''}" placeholder="poisoned wine..." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Per-tick drain (0 = use catalog default)</label>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 6px;">
                            ${['HP','Energy','Hunger','Thirst','Hygiene','Social','Bladder','Sanity','Entertainment','Temperature'].map(v =>
                                `<label style="display:flex;align-items:center;gap:4px;font-size:9px;justify-content:space-between;">
                                    <span style="flex:1;">${v}</span>
                                    <input type="number" step="any" class="tg-periodic-${v}" value="${p.periodic?.[v] !== undefined ? p.periodic[v] : 0}" style="width:48px;font-size:10px;" onchange="TriggerGraph._onFieldChange(this)">
                                </label>`
                            ).join('')}
                        </div>
                    </div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Symptoms (JSON by ticks left)</label><textarea class="tg-field" data-key="symptoms" rows="2" placeholder='{"8":"a queasy twist...","1":"everything spins"}' onchange="TriggerGraph._onFieldChange(this)">${p.symptoms?JSON.stringify(p.symptoms):''}</textarea></div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Extras (JSON)</label><textarea class="tg-field" data-key="extra_conditions" rows="2" placeholder='[{"condition":"blind","duration":3}]' onchange="TriggerGraph._onFieldChange(this)">${p.extra_conditions?JSON.stringify(p.extra_conditions):''}</textarea></div>
                </div>
                <div class="tg-eff-msg" style="display:${et==='message'?'':'none'}">
                    <div class="tg-field-row"><label>Message</label><textarea class="tg-field" data-key="message" rows="2" onchange="TriggerGraph._onFieldChange(this)">${p.message||''}</textarea></div>
                    <div class="tg-field-row"><label>Success</label><input class="tg-field" data-key="success_message" value="${p.success_message||''}" placeholder="optional" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Fail</label><input class="tg-field" data-key="fail_message" value="${p.fail_message||''}" placeholder="optional" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-spawn" style="display:${['spawn_item','give_item','spawn_character'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>${et==='spawn_character'?'Character ID':'Item ID'}</label><input class="tg-field" data-key="${et==='spawn_character'?'character_id':'item_id'}" value="${p[et==='spawn_character'?'character_id':'item_id']||''}" placeholder="${et==='spawn_character'?'character_id':'item_id'}" list="${et==='spawn_character'?'tg-char-ids':'tg-items'}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='give_item'?'none':''}"><label>Display Name</label><input class="tg-field" data-key="display_name" value="${p.display_name||''}" placeholder="optional" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ${et==='spawn_item' ? `<div class="tg-field-row"><label>Place into</label>
                        <select class="tg-field" data-key="into" onchange="TriggerGraph._onFieldChange(this)"><option value="area" ${(p.into||'area')==='area'?'selected':''}>Current area</option><option value="container" ${p.into==='container'?'selected':''}>This container (self)</option></select>
                    </div>` : ''}
                    ${et==='spawn_item' ? `<div class="tg-field-row"><label>Capture</label>
                        <select class="tg-field" data-key="capture" onchange="TriggerGraph._onFieldChange(this)"><option value="" ${!p.capture?'selected':''}>— none —</option><option value="speech" ${p.capture==='speech'?'selected':''}>Recent speech (recorder)</option><option value="sight" ${p.capture==='sight'?'selected':''}>Recent sights (camera)</option></select>
                    </div>` : ''}
                    ${et==='spawn_character' ? `<div class="tg-field-row"><label>Area (blank=current)</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>` : ''}
                    ${et==='spawn_character' ? `<div class="tg-field-row"><label>Message (supports {character_name})</label><input class="tg-field" data-key="message" value="${p.message||''}" placeholder="{character_name} arrives!" onchange="TriggerGraph._onFieldChange(this)"></div>` : ''}
                </div>
                <div class="tg-eff-give" style="display:${et==='give_item'?'':'none'}">
                    <div class="tg-field-row"><label>Target</label><input class="tg-field" data-key="target" value="${p.target||'self'}" list="tg-char-list" placeholder="self, target, or character name" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Message</label><input class="tg-field" data-key="message" value="${p.message||''}" placeholder="optional (supports {target_name})" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-remove" style="display:${et==='remove_item'?'':'none'}">
                    <div class="tg-field-row"><label>Item ID</label><input class="tg-field" data-key="item_id" value="${p.item_id||''}" placeholder="item_key" list="tg-items" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-consume" style="display:${et==='consume_item'?'':'none'}">
                    <div class="tg-field-row"><label>Item ID</label><input class="tg-field" data-key="item_id" value="${p.item_id||''}" placeholder="item_key" list="tg-items" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label><input class="tg-field" data-key="target" value="${p.target||'self'}" list="tg-char-list" placeholder="self or character name" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-rename" style="display:${et==='rename'?'':'none'}">
                    <div class="tg-field-row"><label>New Name</label><input class="tg-field" data-key="name" value="${p.name||''}" placeholder="Empty Bottle" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-uses" style="display:${et==='adjust_uses'?'':'none'}">
                    <div class="tg-field-row"><label>Delta (+/-)</label><input class="tg-field" data-key="delta" type="number" value="${p.delta ?? -1}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target Node</label><input class="tg-field" data-key="node_id" value="${p.node_id||'self'}" placeholder="self or node_id" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-desc" style="display:${['set_description','append_description'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Target Node</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="blank = self" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ${et==='set_description' ? `<div class="tg-field-row"><label>New Description</label><textarea class="tg-field" data-key="value" rows="2" onchange="TriggerGraph._onFieldChange(this)">${p.value||''}</textarea></div>` : ''}
                    ${et==='append_description' ? `<div class="tg-field-row"><label>Text to Append</label><textarea class="tg-field" data-key="text" rows="2" onchange="TriggerGraph._onFieldChange(this)">${p.text||''}</textarea></div>` : ''}
                </div>
                <div class="tg-eff-sched" style="display:${et==='schedule_trigger'?'':'none'}">
                    <div class="tg-field-row"><label>Delay (ticks)</label><input class="tg-field" data-key="delay_ticks" type="number" value="${p.delay_ticks ?? 3}" min="1" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target (blank = this item)</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="cursed_ring" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><div style="font-size:9px;color:var(--text-muted);">Fires the target's <b>on_delayed</b> trigger.</div></div>
                </div>
                <div class="tg-eff-env-set" style="display:${et==='set_environment'?'':'none'}">
                    <div class="tg-field-row"><label>Target Node (blank = current)</label><input class="tg-field" data-key="target_node" value="${p.target_node||''}" placeholder="area_id or blank" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Light</label>
                        <select class="tg-field" data-key="light" onchange="TriggerGraph._onFieldChange(this)"><option value="" ${!p.light?'selected':''}>— Keep —</option>${['pitch_black','dim','normal','bright','blinding'].map(l => `<option value="${l}" ${p.light===l?'selected':''}>${l}</option>`).join('')}</select>
                    </div>
                    <div class="tg-field-row"><label>Temp °C</label><input class="tg-field" data-key="temperature" type="number" value="${p.temperature??''}" min="-50" max="100" placeholder="e.g. 25" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Air</label>
                        <select class="tg-field" data-key="air" onchange="TriggerGraph._onFieldChange(this)"><option value="" ${!p.air?'selected':''}>— Keep —</option>${['fresh','stale','humid','toxic','smoky','fragrant'].map(a => `<option value="${a}" ${p.air===a?'selected':''}>${a}</option>`).join('')}</select>
                    </div>
                    <div class="tg-field-row"><label>Smell</label><input class="tg-field" data-key="smell" value="${p.smell||''}" placeholder="musty, floral..." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Noise</label>
                        <select class="tg-field" data-key="noise" onchange="TriggerGraph._onFieldChange(this)"><option value="" ${!p.noise?'selected':''}>— Keep —</option>${['quiet','dripping','humming','windy','loud','chaotic','silent'].map(n => `<option value="${n}" ${p.noise===n?'selected':''}>${n}</option>`).join('')}</select>
                    </div>
                </div>
                <div class="tg-eff-env-adj" style="display:${et==='adjust_environment'?'':'none'}">
                    <div class="tg-field-row"><label>Temperature (+/-)</label><input class="tg-field" data-key="temperature" type="number" value="${p.temperature||''}" placeholder="5 or -3" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Light (+/-)</label><input class="tg-field" data-key="light" type="number" value="${p.light||''}" placeholder="10 or -20" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-state" style="display:${['set_state','set_hidden'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Node</label><input class="tg-field" data-key="node_id" value="${p.node_id||'self'}" placeholder="self" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-eff-state-val" style="display:${et==='set_state'?'':'none'}">
                        <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="state" value="${p.state||''}" list="tg-node-states" onchange="TriggerGraph._onFieldChange(this)"></div>
                    </div>
                    <div class="tg-eff-hidden-val" style="display:${et==='set_hidden'?'':'none'}">
                        <div class="tg-field-row"><label>Hidden</label><select class="tg-field" data-key="hidden" onchange="TriggerGraph._onFieldChange(this)"><option value="true" ${(p.hidden===true||p.hidden==='true')?'selected':''}>True</option><option value="false" ${(!p.hidden||p.hidden==='false')?'selected':''}>False</option></select></div>
                    </div>
                </div>
                <div class="tg-eff-vital" style="display:${['adjust_vital','damage','heal'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Amount</label><input class="tg-field" data-key="amount" type="number" value="${p.amount??(et==='damage'?5:et==='heal'?10:'')}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ${et!=='damage' ? `<div class="tg-field-row"><label>Stat</label><input class="tg-field" data-key="stat" value="${p.stat||'HP'}" list="tg-vitals" onchange="TriggerGraph._onFieldChange(this)"></div>` : ''}
                    <div class="tg-field-row"><label>Target</label>
                        <select class="tg-field" data-key="target" onchange="TriggerGraph._onFieldChange(this)"><option value="self" ${(p.target||'self')==='self'?'selected':''}>Self</option><option value="other" ${p.target==='other'?'selected':''}>Other</option></select>
                    </div>
                </div>
                <div class="tg-eff-tp" style="display:${et==='teleport'?'':'none'}">
                    <div class="tg-field-row"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-way" style="display:${et==='unlock_way'?'':'none'}">
                    <div class="tg-field-row"><label>Way ID</label><input class="tg-field" data-key="way_id" value="${p.way_id||''}" placeholder="Search ways..." list="tg-ways" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-wayops" style="display:${['spawn_way','set_way_target','set_way_view'].includes(et)?'':'none'}">
                    ${et==='spawn_way' ? `
                    <div class="tg-field-row"><label>From Area</label><input class="tg-field" data-key="area_from" value="${p.area_from||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target Area</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Direction</label><input class="tg-field" data-key="direction" value="${p.direction||''}" placeholder="north" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="state" value="${p.state||''}" placeholder="open, closed..." list="tg-node-states" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ` : ''}
                    ${et==='set_way_target' ? `
                    <div class="tg-field-row"><label>Way ID</label><input class="tg-field" data-key="way_id" value="${p.way_id||''}" placeholder="Search ways..." list="tg-ways" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>New Target Area</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ` : ''}
                    ${et==='set_way_view' ? `
                    <div class="tg-field-row"><label>Way ID</label><input class="tg-field" data-key="way_id" value="${p.way_id||''}" placeholder="Search ways..." list="tg-ways" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>See Through</label><select class="tg-field" data-key="see_through" onchange="TriggerGraph._onFieldChange(this)"><option value="true" ${(p.see_through===true||p.see_through==='true')?'selected':''}>True</option><option value="false" ${(!p.see_through||p.see_through==='false')?'selected':''}>False</option></select></div>
                    <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="state" value="${p.state||''}" placeholder="open, closed..." list="tg-node-states" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ` : ''}
                </div>
                <div class="tg-eff-area-spawn" style="display:${et==='spawn_area'?'':'none'}">
                    <div class="tg-field-row"><label>Area Name</label><input class="tg-field" data-key="name" value="${p.name||''}" placeholder="hidden_vault" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-llm" style="display:${et==='llm_respond'?'':'none'}">
                    <div class="tg-field-row"><label>Instructions (persona prompt)</label><textarea class="tg-field" data-key="instructions" rows="3" placeholder="You are a grumpy magic mirror. Be brief." onchange="TriggerGraph._onFieldChange(this)">${p.instructions||''}</textarea></div>
                    <div class="tg-field-row"><label>Fallback message</label><input class="tg-field" data-key="fallback_message" value="${p.fallback_message||''}" placeholder="The mirror remains silent." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Max words</label><input class="tg-field" data-key="max_words" type="number" value="${p.max_words ?? 40}" min="5" max="200" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Cooldown seconds (empty = 30)</label><input class="tg-field" data-key="cooldown" type="number" value="${p.cooldown ?? ''}" min="0" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Speaker name (empty = node name)</label><input class="tg-field" data-key="name" value="${p.name||''}" placeholder="e.g. The Magic Mirror" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-scry" style="display:${et==='scry'?'':'none'}">
                    <div class="tg-field-row"><label>Target area</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="Kitchen, Taco Bell..." list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Lead-in message</label><input class="tg-field" data-key="message" value="${p.message||''}" placeholder="You peer into the distance..." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Fail message</label><input class="tg-field" data-key="fail_message" value="${p.fail_message||''}" placeholder="The vision shows nothing." onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-mem" style="display:${['surface_memory','suppress_memory','unblock_memory'].includes(et)?'':'none'}">
                    ${et!=='suppress_memory' ? `<div class="tg-field-row"><label>Tags (comma-sep)</label><input class="tg-field" data-key="tags" value="${p.tags||''}" placeholder="guard, key..." onchange="TriggerGraph._onFieldChange(this)"></div>` : ''}
                    ${et==='surface_memory' ? `<div class="tg-field-row"><label>Salience boost</label><input class="tg-field" data-key="salience_boost" type="number" value="${p.salience_boost ?? ''}" step="any" placeholder="e.g. 2" onchange="TriggerGraph._onFieldChange(this)"></div>` : ''}
                    ${et==='suppress_memory' ? `<div class="tg-field-row"><label>Keywords (comma-sep)</label><input class="tg-field" data-key="keywords" value="${p.keywords||''}" placeholder="rat, cellar..." onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Duration (ticks)</label><input class="tg-field" data-key="duration" type="number" value="${p.duration ?? ''}" placeholder="blank = forever" onchange="TriggerGraph._onFieldChange(this)"></div>` : ''}
                </div>`;
            }
        },
        behavior: {
            label: '🧠 Behavior', color: '#e3b341',
            summary: (p) => `pri:${p.priority ?? 1} · ${p.trigger || 'on_tick'}${p.interval > 1 ? ' ×'+p.interval : ''}`,
            sockets: [
                { id: 'output', side: 'right', label: '→', color: '#e3b341' }
            ],
            fields: (p) => `
                <div class="tg-field-row"><label>Trigger</label>
                    <select class="tg-field" data-key="trigger" onchange="TriggerGraph._onFieldChange(this);TriggerGraph._rerenderNode('${'NODEID'}')">${[
                        'on_tick','on_player_enter_area','on_player_leave_area','on_item_taken','on_speech_heard','on_combat','on_state_changed'
                    ].map(t => `<option value="${t}" ${(p.trigger||'on_tick')===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</select>
                </div>
                <div class="tg-field-row"><label>Priority</label><input class="tg-field" data-key="priority" type="number" value="${p.priority ?? 1}" onchange="TriggerGraph._onFieldChange(this)"></div>
                <div class="tg-field-row"><label>Interval</label><input class="tg-field" data-key="interval" type="number" min="1" value="${p.interval ?? 1}" onchange="TriggerGraph._onFieldChange(this)"></div>
            `
        },
        action: {
            label: '🛠 Action', color: '#58a6ff',
            summary: (p) => `${p.action_type || 'message'}${p.state ? ' → '+p.state : ''}${p.text && p.action_type !== 'message' ? ': "'+String(p.text).substring(0,25)+'"' : ''}`,
            sockets: [
                { id: 'input', side: 'left', label: '→', color: '#58a6ff' },
                { id: 'output', side: 'right', label: '→', color: '#58a6ff' }
            ],
            fields: (p) => {
                const at = p.action_type || 'message';
                return `
                <div class="tg-field-row"><label>Type</label>
                    <select class="tg-field" data-key="action_type" onchange="TriggerGraph._onFieldChange(this);TriggerGraph._rerenderNode('${'NODEID'}')">${[
                        'message','speak','set_npc_state','damage','heal','set_environment','spawn_item','spawn_character','teleport','go','llm_respond'
                    ].map(t => `<option value="${t}" ${at===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</select>
                </div>
                <div class="tg-beh-text" style="display:${['message','speak'].includes(at)?'':'none'}">
                    <div class="tg-field-row"><label>Text</label><textarea class="tg-field" data-key="text" rows="2" onchange="TriggerGraph._onFieldChange(this)">${p.text||''}</textarea></div>
                </div>
                <div class="tg-beh-state" style="display:${at==='set_npc_state'?'':'none'}">
                    <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="state" value="${p.state||''}" placeholder="idle, curious, angry..." list="tg-npc-states" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-beh-llm" style="display:${at==='llm_respond'?'':'none'}">
                    <div class="tg-field-row"><label>Instructions (persona prompt)</label><textarea class="tg-field" data-key="instructions" rows="2" onchange="TriggerGraph._onFieldChange(this)">${p.instructions||''}</textarea></div>
                    <div class="tg-field-row"><label>Fallback message</label><input class="tg-field" data-key="fallback_message" value="${p.fallback_message||''}" placeholder="Kept quiet when it cannot answer" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-beh-damage" style="display:${['damage','heal'].includes(at)?'':'none'}">
                    <div class="tg-field-row"><label>${at==='damage'?'Damage':'Heal'} Amount</label><input class="tg-field" data-key="amount" type="number" value="${p.amount ?? (at==='damage'?5:10)}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>${at==='damage'?'Target':'Stat'}</label>
                        ${at==='damage'
                            ? `<select class="tg-field" data-key="target" onchange="TriggerGraph._onFieldChange(this)"><option value="player" ${(p.target||'player')==='player'?'selected':''}>Player</option><option value="self" ${p.target==='self'?'selected':''}>Self</option></select>`
                            : `<select class="tg-field" data-key="stat" onchange="TriggerGraph._onFieldChange(this)">${['HP','Energy','Hunger','Thirst','Hygiene','Social','Bladder','Sanity'].map(v=>`<option value="${v}" ${(p.stat||'HP')===v?'selected':''}>${v}</option>`).join('')}</select>`}
                    </div>
                    <div class="tg-field-row" style="display:${at==='heal'?'':'none'}"><label>Heal Target</label><select class="tg-field" data-key="target" onchange="TriggerGraph._onFieldChange(this)"><option value="self" ${(p.target||'self')==='self'?'selected':''}>Self</option><option value="player" ${p.target==='player'?'selected':''}>Player</option></select></div>
                </div>
                <div class="tg-beh-env" style="display:${at==='set_environment'?'':'none'}">
                    <div class="tg-field-row"><label>Stat</label><input class="tg-field" data-key="stat" value="${p.stat||'temperature'}" placeholder="temperature, light..." list="tg-env-stats" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Delta</label><input class="tg-field" data-key="amount" type="number" value="${p.amount ?? 0}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="blank = current" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>
                <div class="tg-beh-spawn" style="display:${['spawn_item','spawn_character'].includes(at)?'':'none'}">
                    ${at==='spawn_item' ? `
                    <div class="tg-field-row"><label>Item ID</label><input class="tg-field" data-key="item_id" value="${p.item_id||''}" placeholder="library id" list="tg-items" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Display Name</label><input class="tg-field" data-key="name" value="${p.name||''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Description</label><input class="tg-field" data-key="description" value="${p.description||''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ` : at==='spawn_character' ? `
                    <div class="tg-field-row"><label>Character ID</label><input class="tg-field" data-key="character_id" value="${p.character_id||''}" placeholder="library id" list="tg-char-ids" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Display Name</label><input class="tg-field" data-key="name" value="${p.name||p.display_name||''}" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Area (blank=current)</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                    ` : ''}
                </div>
                <div class="tg-beh-tp" style="display:${at==='teleport'?'':'none'}">
                    <div class="tg-field-row"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label><select class="tg-field" data-key="target" onchange="TriggerGraph._onFieldChange(this)"><option value="player" ${(p.target||'player')==='player'?'selected':''}>Player</option><option value="self" ${p.target==='self'?'selected':''}>Self</option></select></div>
                </div>
                <div class="tg-beh-go" style="display:${at==='go'?'':'none'}">
                    <div class="tg-field-row"><label>Mode</label>
                        <select class="tg-field" data-key="mode" onchange="TriggerGraph._onFieldChange(this);TriggerGraph._rerenderNode('${'NODEID'}')">
                            <option value="goto" ${(p.mode||'goto')==='goto'?'selected':''}>Go to area</option>
                            <option value="patrol" ${p.mode==='patrol'?'selected':''}>Patrol areas</option>
                        </select>
                    </div>
                    <div class="tg-field-row" style="display:${(p.mode||'goto')==='goto'?'':'none'}"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" list="tg-areas" onchange="TriggerGraph._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${p.mode==='patrol'?'':'none'}"><label>Areas (comma-sep)</label><input class="tg-field" data-key="areas" value="${p.areas||''}" placeholder="kitchen, garden, hall" onchange="TriggerGraph._onFieldChange(this)"></div>
                </div>`;
            }
        },
        state: {
            label: '🎭 State', color: '#bc8cff',
            summary: (p) => `set_npc_state → ${p.state || 'idle'}`,
            sockets: [
                { id: 'input', side: 'left', label: '→', color: '#bc8cff' },
                { id: 'output', side: 'right', label: '→', color: '#bc8cff' }
            ],
            fields: (p) => `
                <div class="tg-field-row" style="color:#bc8cff;font-size:10px;margin-bottom:4px;">State boundary</div>
                <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="state" value="${p.state||''}" placeholder="idle, curious, fleeing..." list="tg-npc-states" onchange="TriggerGraph._onFieldChange(this)"></div>
            `
        }
    };

    // ─── State ───
    let _state = { nodes: {}, wires: {}, nodeIdCounter: 0, wireIdCounter: 0 };
    let _mode = 'trigger';
    let _onSave = null;
    let _selectedNode = null;
    let _dragWire = null;
    let _dragNode = null;
    let _nextZ = 1;
    let _contextMenu = null;
    let _contextSearch = '';
    let _contextItemId = '';
    let _sourceNodeId = '';
    let _editorBridge = null;

    // ─── Viewport (pan / zoom) ───
    // All interaction math happens in WORLD coordinates. The only place screen
    // space exists is #tg-canvas (the untransformed viewport); #tg-world holds
    // nodes + wires and carries the single transform: world*k + (x, y).
    const TG_ZOOM_MIN = 0.25, TG_ZOOM_MAX = 2.0, TG_GRID = 26;
    let _vp = { x: 0, y: 0, k: 1 };
    let _pan = null;
    let _spacePan = false;
    let _contextWorldPos = { x: 0, y: 0 };
    let _vpSaveTimer = null;

    // Seed id counters past the highest loaded n#/w# so new nodes/wires never
    // reuse an existing id (which would silently replace that node/wire).
    function _seedCounters(state) {
        for (const id of Object.keys(state.nodes)) {
            const m = /^n(\d+)$/.exec(id);
            if (m) state.nodeIdCounter = Math.max(state.nodeIdCounter, +m[1] + 1);
        }
        for (const id of Object.keys(state.wires)) {
            const m = /^w(\d+)$/.exec(id);
            if (m) state.wireIdCounter = Math.max(state.wireIdCounter, +m[1] + 1);
        }
    }

    function _conditionToGraphProps(cond) {
        if (!cond || !cond.type) return { condition_type: 'skill_check', skill: 'Athletics', dc: 10 };
        const t = cond.type;
        const props = { condition_type: t };
        const numeric = ['area_temp', 'vital', 'vital_above', 'vital_below', 'uses_reached', 'uses_above', 'temperature_below', 'temperature_above'];
        if (['skill_check', 'save_throw'].includes(t)) props.dc = cond.dc || (t === 'save_throw' ? 12 : 10);
        if (numeric.includes(t)) props.operator = cond.operator || 'lt';
        if (t === 'eq') { if (cond.target) props.target = cond.target; if (cond.value != null) props.value = String(cond.value); }
        else if (t === 'in_area') { if (cond.area) props.area = cond.area; if (cond.target) props.target = cond.target; }
        else if (t === 'tick_since_state') props.min_ticks = cond.min_ticks ?? 0;
        else if (t === 'proximity') props.max_areas = cond.max_areas ?? 0;
        else if (t === 'has_item') { if (cond.item) props.item = cond.item; if (cond.target) props.target = cond.target; }
        else if (t === 'has_trait' || t === 'has_tag') { if (cond.value != null) props.value = String(cond.value); }
        else if (t === 'area_has_status') { if (cond.status_type) props.status_type = cond.status_type; if (cond.target) props.target = cond.target; }
        else if (t === 'item_relationship') { if (cond.relation) props.relation = cond.relation; if (cond.direction) props.direction = cond.direction; if (cond.target) props.target = cond.target; }
        else if (t === 'npc_emotion_is') { if (cond.emotion) props.emotion = cond.emotion; if (cond.operator) props.operator = cond.operator; if (cond.value != null) props.value = String(cond.value); }
        else if (t === 'npc_is_hidden') { props.value = String(cond.value !== false); }
        else if (t === 'character_has_tag') { if (cond.tag) props.tag = cond.tag; if (cond.target) props.target = cond.target; }
        else { if (cond.value != null) props.value = String(cond.value); if (cond.target) props.target = cond.target; }
        return props;
    }

    TG.triggerToGraph = function(triggerDef) {
        const t = triggerDef || {};
        const nodes = [];
        const wires = [];
        let nodeId = 0;
        const types = Array.isArray(t.trigger_type) ? t.trigger_type : [t.trigger_type || 'on_use'];
        const tnode = `n${nodeId++}`;
        nodes.push({
            id: tnode, type: 'trigger', x: 50, y: 50,
            props: {
                trigger_type: types,
                target_tag: t.target_name || t.target_tag || '',
                target_state: t.target_state || '',
            },
        });

        let conditions = t.conditions || [];
        if (typeof conditions === 'object' && !Array.isArray(conditions) && conditions.operator) {
            conditions = conditions.conditions || [];
        }
        if (!Array.isArray(conditions)) conditions = [];

        const effects = t.effects || [];
        let attachFrom = [tnode, 'output'];

        if (conditions.length > 0) {
            const cnode = `n${nodeId++}`;
            nodes.push({
                id: cnode, type: 'condition', x: 50, y: 180,
                props: _conditionToGraphProps(conditions[0]),
            });
            wires.push({ id: `w${wires.length}`, from: attachFrom, to: [cnode, 'input'] });
            attachFrom = [cnode, 'output_yes'];
        }

        for (let i = 0; i < effects.length; i++) {
            const eff = effects[i];
            const enode = `n${nodeId++}`;
            nodes.push({
                id: enode, type: 'effect',
                x: 50 + (conditions.length ? 220 : 0),
                y: 180 + i * 120,
                props: { effect_type: eff.type || 'message', ...(eff.params || {}) },
            });
            wires.push({ id: `w${wires.length}`, from: attachFrom, to: [enode, 'input'] });
            if (effects.length > 1 && i < effects.length - 1) {
                attachFrom = [enode, 'output'];
            }
        }

        return { nodes, wires };
    };

    TG.engineToFormData = function(compiled) {
        if (!compiled) {
            return {
                effects: [{ type: 'message', params: {} }],
                conditions: {},
            };
        }
        return {
            trigger_type: compiled.trigger_type,
            effects: compiled.effects || [{ type: 'message', params: {} }],
            conditions: compiled.conditions || {},
            target_name: compiled.target_name || '',
            target_state: compiled.target_state || '',
            fail_message: compiled.fail_message || '',
        };
    };

    function _compiledTrigger() {
        const graph = _serializeGraph();
        return TG.compileToEngine(graph);
    }

    function _renderTestResultHtml(res, triggerType) {
        const rows = (res.conditions || []).map(c =>
            triggerGraphTag`<div style="display:flex;gap:6px;align-items:center;">
                <span style="color:${c.passed ? 'var(--green)' : 'var(--red)'};font-weight:600;">${c.passed ? '✓' : '✕'}</span>
                <span>${String(c.condition || '(none)')}</span>
            </div>`
        );
        const outputs = (res.outputs || []).map(o =>
            triggerGraphTag`<div style="padding-left:8px;color:var(--text-secondary);">${String(o)}</div>`
        );
        return triggerGraphTag`
            <div style="font-weight:600;margin-bottom:4px;">🧪 Trigger Test</div>
            <div>Type: ${String(triggerType || '(none)')}</div>
            <div style="margin-top:4px;color:${res.conditions_pass ? 'var(--green)' : 'var(--red)'};">Conditions: ${res.conditions_pass ? 'PASS' : 'FAIL'}</div>
            ${rows.length ? rows : triggerGraphTag`<div style="color:var(--text-muted);">(no conditions)</div>`}
            <div style="margin-top:4px;font-weight:600;">Would run:</div>
            ${outputs.length ? outputs : triggerGraphTag`<div style="color:var(--text-muted);">(no effects)</div>`}`;
    }

    function _renderValidateResultHtml(issues) {
        if (!issues.length) {
            return triggerGraphTag`<div style="color:var(--green);">✓ No validation issues.</div>`;
        }
        return issues.map(issue => {
            const color = issue.severity === 'error' ? 'var(--red)'
                : issue.severity === 'warning' ? 'var(--yellow)' : 'var(--text-muted)';
            return triggerGraphTag`<div style="color:${color};margin-bottom:2px;">[${issue.severity}] ${String(issue.message || '')}</div>`;
        });
    }

    async function _onTestClick() {
        const panel = document.getElementById('tg-test-panel');
        if (!panel) return;
        const compiled = _compiledTrigger();
        if (!compiled) {
            panel.style.display = 'block';
            window.Lit.render(triggerGraphTag`<div style="color:var(--red);">Add a trigger node first.</div>`, panel);
            return;
        }
        panel.style.display = 'block';
        window.Lit.render(triggerGraphTag`<span style="color:var(--text-muted);">Testing…</span>`, panel);
        const triggerType = Array.isArray(compiled.trigger_type)
            ? compiled.trigger_type[0]
            : compiled.trigger_type;
        const payload = {
            trigger: compiled,
            dry_run: true,
            context: {},
        };
        if (_contextItemId) payload.item_id = _contextItemId;
        try {
            const resp = await fetch('/api/triggers/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const res = await resp.json();
            if (res.error) throw new Error(res.error);
            window.Lit.render(triggerGraphTag`${_renderTestResultHtml(res, triggerType)}`, panel);
        } catch (e) {
            window.Lit.render(triggerGraphTag`<div style="color:var(--red);">Test failed: ${String(e.message || e)}</div>`, panel);
        }
    }
    TG._onTestClick = _onTestClick;

    async function _validateCompiled(compiled) {
        const payload = {
            trigger: compiled,
            source_node_id: _sourceNodeId || _contextItemId || '',
        };
        const resp = await fetch('/api/triggers/validate-definition', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const res = await resp.json();
        if (res.error) throw new Error(res.error);
        return res.issues || [];
    }

    async function _onValidateClick() {
        const panel = document.getElementById('tg-test-panel');
        if (!panel) return;
        const compiled = _compiledTrigger();
        if (!compiled) {
            panel.style.display = 'block';
            window.Lit.render(triggerGraphTag`<div style="color:var(--red);">Add a trigger node first.</div>`, panel);
            return;
        }
        panel.style.display = 'block';
        window.Lit.render(triggerGraphTag`<span style="color:var(--text-muted);">Validating…</span>`, panel);
        try {
            const issues = await _validateCompiled(compiled);
            window.Lit.render(triggerGraphTag`${_renderValidateResultHtml(issues)}`, panel);
        } catch (e) {
            window.Lit.render(triggerGraphTag`<div style="color:var(--red);">Validate failed: ${String(e.message || e)}</div>`, panel);
        }
    }
    TG._onValidateClick = _onValidateClick;

    function _openFormEditor() {
        const compiled = _compiledTrigger();
        if (!compiled || !_editorBridge) {
            if (typeof toastInfo === 'function') toastInfo('Form editor bridge not available here.');
            return;
        }
        const formData = {
            ...TG.engineToFormData(compiled),
            name: _editorBridge.initialName || '',
            success_message: _editorBridge.success_message || '',
            fail_message: compiled.fail_message || _editorBridge.fail_message || '',
        };
        const bridge = { ..._editorBridge };
        _close();
        if (typeof TriggerEditor === 'undefined') return;
        TriggerEditor.show({
            ...bridge,
            initialData: formData,
            onOpenGraph: true,
        });
    }
    TG._openFormEditor = _openFormEditor;

    // ─── Public API ───

    TG.show = function(options) {
        _mode = options.mode === 'behavior' ? 'behavior' : 'trigger';
        _state = { nodes: {}, wires: {}, nodeIdCounter: 0, wireIdCounter: 0 };
        _selectedNode = null; _dragWire = null; _dragNode = null;
        _onSave = options.onSave || null;
        _contextItemId = options.contextItemId || '';
        _sourceNodeId = options.sourceNodeId || options.contextItemId || '';
        _editorBridge = options.editorBridge || null;

        if (options.graph) {
            for (const n of (options.graph.nodes || [])) {
                const id = n.id || `n${_state.nodeIdCounter++}`;
                _state.nodes[id] = { ...n, id, _expanded: true };
            }
            for (const w of (options.graph.wires || [])) {
                const id = w.id || `w${_state.wireIdCounter++}`;
                _state.wires[id] = { ...w, id };
            }
            _seedCounters(_state);
        }

        _renderModal();
        _rerenderCanvas();
        // Restore this mode's last viewport when it still shows this graph;
        // otherwise fit (first open, freshly loaded blueprint, moved nodes).
        // Either way the viewport moves AFTER _rerenderCanvas drew the wires
        // against the stale leftover transform — redraw them against the final one.
        const savedVp = _loadViewport();
        if (savedVp) {
            _vp = savedVp;
            _applyViewport(false);
            if (!_viewportShowsNodes()) _fitView(false);
        } else {
            _fitView(false);
        }
        _rerenderWires();
    };

    TG._onFieldChange = function(el) {
        const nodeDiv = el.closest('.tg-node');
        if (!nodeDiv) return;
        const nid = nodeDiv.dataset.nodeId;
        const node = _state.nodes[nid];
        if (!node) return;
        if ([...el.classList].some(c => c.startsWith('tg-periodic-'))) {
            // Periodic drain form: collect non-zero vitals into props.periodic.
            const drain = {};
            ['HP','Energy','Hunger','Thirst','Hygiene','Social','Bladder','Sanity','Entertainment','Temperature'].forEach(v => {
                const inp = nodeDiv.querySelector(`.tg-periodic-${v}`);
                if (!inp) return;
                const val = parseFloat(inp.value);
                if (!isNaN(val) && val !== 0) drain[v] = val;
            });
            if (Object.keys(drain).length > 0) node.props.periodic = drain;
            else delete node.props.periodic;
            return;
        }
        if (el.multiple && el.selectedOptions) {
            // Multi-selects (e.g. trigger types) store an array.
            node.props[el.dataset.key] = Array.from(el.selectedOptions).map(o => o.value);
            return;
        }
        if (el.type === 'checkbox') {
            node.props[el.dataset.key] = el.checked;
            return;
        }
        node.props[el.dataset.key] = el.type === 'number' ? parseFloat(el.value) || 0 : el.value;
    };

    TG._onTriggerTypeChange = function(select) {
        const nodeDiv = select.closest('.tg-node');
        if (!nodeDiv) return;
        const nid = nodeDiv.dataset.nodeId;
        const node = _state.nodes[nid];
        if (!node) return;
        TG._rerenderNode(nid);
    };

    TG._rerenderNode = function(nid) {
        const node = _state.nodes[nid];
        if (!node) return;
        const oldEl = document.querySelector(`.tg-node[data-node-id="${nid}"]`);
        if (oldEl) oldEl.remove();
        if (!_worldEl()) return;
        _renderNode(node);
        _rerenderWires();
    };

    // ─── Modal ───

    function _renderModal() {
        const existing = document.getElementById('tg-modal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'tg-modal';
        modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;background:var(--bg-canvas,#111126);display:flex;flex-direction:column;';

        const toolbar = document.createElement('div');
        toolbar.style.cssText = 'height:36px;background:var(--bg-card,#1e1e2e);border-bottom:1px solid var(--border,#333);display:flex;align-items:center;gap:4px;padding:0 8px;flex-shrink:0;';
        window.Lit.render(triggerGraphTag`
            <span style="font-weight:600;font-size:12px;margin-right:12px;color:#e3b341;">${_mode === 'behavior' ? '🧠 Behavior Graph' : '🔀 Trigger Graph'}</span>
            <button class="btn btn-sm btn-ghost" @click=${() => TriggerGraph._openFormEditor()} style="font-size:10px;display:${_editorBridge && _mode !== 'behavior' ? 'inline-block' : 'none'};" id="tg-form-btn">📝 Form</button>
            <div style="flex:1;"></div>
            <span style="font-size:10px;color:var(--text-muted);margin-right:8px;">Scroll = zoom · drag canvas = pan · right-click = add · Del = delete</span>
            <button class="btn btn-sm btn-purple" @click=${() => TriggerGraph._onTestClick()} style="font-size:10px;display:${_mode === 'behavior' ? 'none' : ''};">▶ Test</button>
            <button class="btn btn-sm btn-yellow" @click=${() => TriggerGraph._onValidateClick()} style="font-size:10px;display:${_mode === 'behavior' ? 'none' : ''};">⚠ Validate</button>
            <button class="btn btn-sm btn-ghost" @click=${() => TriggerGraph._fitView()} style="font-size:10px;">⊞ Fit</button>
            <button class="btn btn-sm btn-purple" @click=${() => TriggerGraph._toggleStatePanel()} style="font-size:10px;display:${_mode === 'behavior' ? '' : 'none'};">🗺 States</button>
            <button class="btn btn-sm btn-yellow" @click=${() => TriggerGraph._saveBlueprint()} style="font-size:10px;">💾 Blueprint</button>
            <button class="btn btn-sm" @click=${() => TriggerGraph._exportBlueprint()} style="font-size:10px;">⬇️ Export</button>
            <button class="btn btn-sm" @click=${() => TriggerGraph._loadBlueprint()} style="font-size:10px;">📂 Load</button>
            <button class="btn btn-sm btn-green" @click=${() => TriggerGraph._saveGraph()} style="font-size:10px;">✅ ${_mode === 'behavior' ? 'Save Behaviors' : 'Apply'}</button>
            <button class="btn btn-sm btn-ghost" @click=${() => TriggerGraph._close()} style="font-size:10px;">✕</button>
        `, toolbar);

        const testPanel = document.createElement('div');
        testPanel.id = 'tg-test-panel';
        testPanel.style.cssText = 'display:none;max-height:120px;overflow-y:auto;padding:6px 10px;font-size:11px;background:var(--bg-inset);border-bottom:1px solid var(--border);flex-shrink:0;';

        // Shared stylesheet (injected once): selection, viewport, cursors.
        if (!document.getElementById('tg-style')) {
            const st = document.createElement('style');
            st.id = 'tg-style';
            st.textContent = `
                .tg-node { position:absolute; z-index:3; background:var(--bg-card,#1e1e2e); border:2px solid var(--border,#333); border-radius:10px; font-size:11px; color:var(--text,#ccc); transition:box-shadow .15s, border-color .15s; }
                .tg-node.tg-sel { z-index:10; border-color:var(--tg-c,#e3b341); box-shadow:0 0 20px var(--tg-glow,rgba(227,179,65,.2)), 0 4px 16px rgba(0,0,0,.4); }
                #tg-world { position:absolute; top:0; left:0; width:100%; height:100%; transform-origin:0 0; }
                #tg-world.tg-anim { transition:transform .28s cubic-bezier(.22,.61,.36,1); }
                #tg-canvas { cursor:default; }
                #tg-canvas.tg-space { cursor:grab; }
                #tg-canvas.tg-panning { cursor:grabbing !important; }
            `;
            document.head.appendChild(st);
        }

        const canvas = document.createElement('div');
        canvas.id = 'tg-canvas';
        canvas.style.cssText = `position:absolute;top:0;left:0;right:0;bottom:0;overflow:hidden;background-color:var(--bg-canvas,#111126);background-image:radial-gradient(circle, rgba(255,255,255,0.13) 4%, transparent 5%);`;

        // #tg-world carries the single pan/zoom transform; nodes and wires live in
        // world coordinates inside it, so the browser applies the math once per frame.
        const world = document.createElement('div');
        world.id = 'tg-world';

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.id = 'tg-svg';
        // overflow:visible lets wires extend past the viewport-sized SVG box in
        // world coordinates (negative coords, far nodes) without a giant SVG.
        svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:2;overflow:visible;';
        world.appendChild(svg);
        canvas.appendChild(world);

        const statePanel = document.createElement('div');
        statePanel.id = 'tg-state-panel';
        statePanel.style.cssText = `display:none;width:240px;border-left:1px solid var(--border,#333);background:var(--bg-inset,#161625);overflow-y:auto;font-size:11px;padding:8px;position:absolute;top:0;right:0;bottom:0;z-index:5;`;

        // Zoom controls — bottom-left, away from the state panel on the right.
        const zoomCtl = document.createElement('div');
        zoomCtl.id = 'tg-zoomctl';
        zoomCtl.style.cssText = 'position:absolute;left:10px;bottom:10px;z-index:20;display:flex;align-items:center;gap:2px;background:var(--bg-card,#1e1e2e);border:1px solid var(--border,#333);border-radius:8px;padding:2px 6px;box-shadow:0 4px 12px rgba(0,0,0,.35);';
        window.Lit.render(triggerGraphTag`
            <button class="btn btn-sm btn-ghost" @click=${() => TriggerGraph._zoomCentered(1 / 1.25)} style="font-size:13px;padding:1px 8px;" title="Zoom out (-)">−</button>
            <span id="tg-zoom-badge" @click=${() => TriggerGraph._resetZoom()} title="Reset zoom to 100%" style="font-size:10px;color:var(--text-muted);min-width:38px;text-align:center;cursor:pointer;">100%</span>
            <button class="btn btn-sm btn-ghost" @click=${() => TriggerGraph._zoomCentered(1.25)} style="font-size:13px;padding:1px 8px;" title="Zoom in (+)">+</button>
            <button class="btn btn-sm btn-ghost" @click=${() => TriggerGraph._fitView()} style="font-size:10px;" title="Fit graph (F)">⤢ Fit</button>
        `, zoomCtl);

        const bodyRow = document.createElement('div');
        bodyRow.style.cssText = 'flex:1;position:relative;min-height:0;';
        bodyRow.appendChild(canvas);
        bodyRow.appendChild(statePanel);
        bodyRow.appendChild(zoomCtl);

        modal.appendChild(toolbar);
        modal.appendChild(testPanel);
        modal.appendChild(bodyRow);
        document.body.appendChild(modal);

        // Shared datalists: node fields stay free-text but get type-ahead from
        // world state + libraries. Refreshed every open so new content shows.
        const fillDl = (id, values) => {
            let dl = document.getElementById(id);
            if (!dl) { dl = document.createElement('datalist'); dl.id = id; document.body.appendChild(dl); }
            dl.innerHTML = '';
            (values || []).forEach(v => {
                const o = document.createElement('option');
                if (Array.isArray(v)) { o.value = v[0]; o.label = v[1]; o.textContent = v[1]; }
                else o.value = v;
                dl.appendChild(o);
            });
            return dl;
        };
        const tgPlayers = (typeof worldState !== 'undefined' && worldState?.players) ? Object.keys(worldState.players) : [];
        fillDl('tg-char-list', tgPlayers);
        fillDl('tg-condition-list', ['awake','dead','unconscious','paralysed','stunned','grappled','restrained','prone','busy',
             'exhausted','sick','poisoned','blind','deaf','mute','frightened','charmed']);
        fillDl('tg-areas', Object.keys(worldState?.areas || {}));
        fillDl('tg-items', Object.entries(worldState?.graph?.nodes || {}).filter(([, n]) => n.type === 'item').map(([id]) => id));
        fillDl('tg-ways', Object.entries(worldState?.graph?.nodes || {}).filter(([, n]) => n.type === 'way').map(([id, n]) => [id, n.name || id]));
        fillDl('tg-node-states', ['on','off','open','closed','locked','unlocked','lit','unlit','broken','pristine','activated','deactivated','hidden','visible']);
        fillDl('tg-npc-states', ['idle','curious','alert','angry','hostile','hunting','fleeing','hiding','sleeping','eating','working','following','talking','waiting','patrolling']);
        fillDl('tg-vitals', ['HP','Energy','Hunger','Thirst','Hygiene','Social','Bladder','Sanity','Entertainment','Temperature']);
        fillDl('tg-skills', ['STR','DEX','CON','INT','WIS','CHA','Athletics','Acrobatics','Stealth','Perception','Survival','Persuasion','Investigation']);
        fillDl('tg-env-stats', ['temperature','light']);
        fillDl('tg-weather', ['clear','cloudy','fog','rain','storm','snow','windy']);
        fillDl('tg-char-ids', []);
        fillDl('tg-traits', []);
        fillDl('tg-tags', []);
        // Library-backed lists load async (same pattern as the form editor).
        if (typeof ApiClient !== 'undefined' && ApiClient.getLibraryType) {
            [['characters', 'tg-char-ids'], ['traits', 'tg-traits'], ['tags', 'tg-tags'], ['items', 'tg-items']].forEach(async ([type, id]) => {
                try {
                    const lib = await ApiClient.getLibraryType(type);
                    const dl = document.getElementById(id);
                    if (!dl || !lib) return;
                    Object.keys(lib).forEach(key => {
                        if (![...dl.children].some(o => o.value === key)) {
                            const o = document.createElement('option'); o.value = key; dl.appendChild(o);
                        }
                    });
                } catch (e) { /* library optional */ }
            });
        }

        canvas.addEventListener('contextmenu', _onCanvasContextMenu);
        canvas.addEventListener('mousedown', _onCanvasMouseDown);
        canvas.addEventListener('wheel', _onCanvasWheel, { passive: false });
        document.addEventListener('keydown', _onKeyDown);
        document.addEventListener('keyup', _onKeyUp);
    }

    function _close() {
        const m = document.getElementById('tg-modal');
        if (m) m.remove();
        document.removeEventListener('keydown', _onKeyDown);
        document.removeEventListener('keyup', _onKeyUp);
        document.removeEventListener('mousemove', _onDocMouseMove);
        document.removeEventListener('mouseup', _onDocMouseUp);
        _flushViewport();
        _pan = null; _dragWire = null; _dragNode = null; _spacePan = false;
        _onSave = null;
        _contextItemId = '';
        _sourceNodeId = '';
        _editorBridge = null;
    }
    TG._close = _close;

    // ─── State summary sidebar (behavior mode) ───

    function _collectBehaviorStates() {
        const states = {};
        const graph = _serializeGraph();
        for (const bnode of graph.nodes.filter(n => n.type === 'behavior')) {
            const bw = (graph.wires || []).find(w => w.from[0] === bnode.id && (w.from[1] === 'output' || w.from[1] === 'right'));
            if (!bw) continue;
            const traced = _traceBehavior(bw.to[0], graph.wires, graph.nodes);
            const entry = { transitions: [], priority: graph.nodes.length }; // filled below
            for (const act of traced.actions) {
                if (act.type === 'set_npc_state') {
                    entry.transitions.push(act.state || 'idle');
                }
            }
            states[bnode.id] = {
                trigger: bnode.props.trigger || 'on_tick',
                to: entry.transitions,
                priority: parseInt(bnode.props.priority) || 1,
            };
        }
        return states;
    }

    function _renderStatePanel() {
        const panel = document.getElementById('tg-state-panel');
        if (!panel) return;
        const states = _collectBehaviorStates();
        const entries = Object.values(states);
        if (entries.length === 0) {
            window.Lit.render(triggerGraphTag`<div style="font-size:10px;color:var(--text-muted);">No state transitions found.<br><br>Add a 🎭 State node (set_npc_state) inside a behavior to trace it here.</div>`, panel);
            return;
        }
        const toSet = new Set();
        entries.forEach(e => e.to.forEach(s => toSet.add(s)));
        window.Lit.render(triggerGraphTag`
            <div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:6px;">🎭 States discovered</div>
            ${Array.from(toSet).sort().map(s =>
                triggerGraphTag`<div style="padding:4px 6px;margin:2px 0;border:1px solid #bc8cff55;border-radius:5px;color:#bc8cff;background:#bc8cff11;"><span style="font-weight:600;">${s}</span></div>`
            )}
            <div style="font-size:10px;font-weight:600;color:var(--text-dim);margin:10px 0 4px;">Transitions (behavior → state)</div>
            ${entries.map(e =>
                triggerGraphTag`<div style="padding:3px 6px;border-left:3px solid #e3b341;margin:2px 0;color:var(--text,#ccc);">${e.trigger}${e.to.length ? triggerGraphTag` → ${e.to.map(s => triggerGraphTag`<span style="color:#bc8cff;">${s}</span>`)}` : triggerGraphTag` <span style="color:var(--text-muted);">(no set_npc_state)</span>`}</div>`
            )}
        `, panel);
    }
    TG._renderStatePanel = _renderStatePanel;

    function _toggleStatePanel() {
        const panel = document.getElementById('tg-state-panel');
        if (!panel) return;
        const showing = panel.style.display !== 'none';
        panel.style.display = showing ? 'none' : 'block';
        if (!showing) _renderStatePanel();
    }
    TG._toggleStatePanel = _toggleStatePanel;

    // ─── Node management ───

    function _addNode(type, x, y) {
        let id = `n${_state.nodeIdCounter++}`;
        while (_state.nodes[id]) id = `n${_state.nodeIdCounter++}`;
        const now = Date.now();
        _state.nodes[id] = {
            id, type,
            x: x != null ? x : 80 + (now % 400),
            y: y != null ? y : 60 + ((now * 7) % 400),
            w: 260, _expanded: true,
            props: type === 'trigger' ? { trigger_type: 'on_use' } :
                    type === 'condition' ? { condition_type: 'area_temp', value: '' } :
                    type === 'behavior' ? { trigger: 'on_tick', priority: 1, interval: 1 } :
                    type === 'state' ? { state: '' } :
                    type === 'action' ? { action_type: 'message', text: '' } :
                    { effect_type: 'message', message: '' }
        };
        _rerenderCanvas();
        _setSelected(id);
    }
    TG._addNode = _addNode;

    function _deleteNode(id) {
        if (!_state.nodes[id]) return;
        for (const wid of Object.keys(_state.wires)) {
            const w = _state.wires[wid];
            if (w.from[0] === id || w.to[0] === id) delete _state.wires[wid];
        }
        delete _state.nodes[id];
        if (_selectedNode === id) _selectedNode = null;
        _rerenderCanvas();
    }

    // ─── Viewport: pan / zoom / fit / grid ───

    function _canvasEl() { return document.getElementById('tg-canvas'); }

    function _worldEl() { return document.getElementById('tg-world'); }

    function _screenToWorld(clientX, clientY) {
        const c = _canvasEl();
        if (!c) return { x: 0, y: 0 };
        const r = c.getBoundingClientRect();
        return { x: (clientX - r.left - _vp.x) / _vp.k, y: (clientY - r.top - _vp.y) / _vp.k };
    }

    function _applyViewport(animate) {
        const w = _worldEl();
        if (!w) return;
        w.classList.toggle('tg-anim', !!animate);
        w.style.transform = `translate(${_vp.x}px, ${_vp.y}px) scale(${_vp.k})`;
        const c = _canvasEl();
        if (c) {
            // Dot grid lives on the viewport and is moved/scaled to match the
            // world transform, so it always reads as graph coordinates.
            const g = TG_GRID * _vp.k;
            c.style.backgroundSize = `${g}px ${g}px`;
            c.style.backgroundPosition = `${_vp.x}px ${_vp.y}px`;
        }
        const badge = document.getElementById('tg-zoom-badge');
        if (badge) badge.textContent = Math.round(_vp.k * 100) + '%';
        _saveViewport();
    }

    function _setZoomAt(clientX, clientY, factor, animate) {
        const k2 = Math.min(TG_ZOOM_MAX, Math.max(TG_ZOOM_MIN, _vp.k * factor));
        if (k2 === _vp.k) return;
        const c = _canvasEl();
        if (!c) return;
        const r = c.getBoundingClientRect();
        const mx = clientX - r.left, my = clientY - r.top;
        // Keep the world point under the cursor anchored while the scale changes.
        _vp.x = mx - (mx - _vp.x) * (k2 / _vp.k);
        _vp.y = my - (my - _vp.y) * (k2 / _vp.k);
        _vp.k = k2;
        _applyViewport(animate);
    }

    function _zoomCentered(factor) {
        const c = _canvasEl();
        if (!c) return;
        const r = c.getBoundingClientRect();
        _setZoomAt(r.left + c.clientWidth / 2, r.top + c.clientHeight / 2, factor, true);
    }
    TG._zoomCentered = _zoomCentered;

    function _resetZoom() {
        const c = _canvasEl();
        if (!c) return;
        const r = c.getBoundingClientRect();
        _setZoomAt(r.left + c.clientWidth / 2, r.top + c.clientHeight / 2, 1 / _vp.k, true);
    }
    TG._resetZoom = _resetZoom;

    function _fitView(animate = true) {
        const c = _canvasEl();
        if (!c) return;
        const ns = Object.values(_state.nodes);
        if (!ns.length) { _vp = { x: 0, y: 0, k: 1 }; _applyViewport(animate); return; }
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const n of ns) {
            const el = document.querySelector(`.tg-node[data-node-id="${n.id}"]`);
            const w = el ? el.offsetWidth : (n.w || 260);
            const h = el ? el.offsetHeight : 160;
            if (n.x - 20 < minX) minX = n.x - 20;
            if (n.y - 20 < minY) minY = n.y - 20;
            if (n.x + w + 20 > maxX) maxX = n.x + w + 20;
            if (n.y + h + 20 > maxY) maxY = n.y + h + 20;
        }
        const pad = 40;
        const k = Math.min((c.clientWidth - pad * 2) / (maxX - minX), (c.clientHeight - pad * 2) / (maxY - minY), 1);
        _vp.k = Math.max(TG_ZOOM_MIN, k);
        _vp.x = (c.clientWidth - (maxX - minX) * _vp.k) / 2 - minX * _vp.k;
        _vp.y = (c.clientHeight - (maxY - minY) * _vp.k) / 2 - minY * _vp.k;
        _applyViewport(animate);
        // Wires are world-space paths computed against the live viewport — after
        // the view changed, redraw them or they're offset by the pan/zoom delta.
        _rerenderWires();
    }
    TG._fitView = _fitView;

    // A saved viewport is only reused if it actually shows part of the current
    // graph — otherwise (different blueprint, moved nodes) fall back to Fit.
    function _viewportShowsNodes() {
        const c = _canvasEl();
        if (!c) return false;
        const margin = 120;
        return Object.values(_state.nodes).some(n => {
            const sx = n.x * _vp.k + _vp.x, sy = n.y * _vp.k + _vp.y;
            return sx > -margin && sx < c.clientWidth + margin && sy > -margin && sy < c.clientHeight + margin;
        });
    }

    function _vpStoreKey() { return 'vw_tg_viewport_' + _mode; }

    function _saveViewport() {
        clearTimeout(_vpSaveTimer);
        _vpSaveTimer = setTimeout(() => {
            try { localStorage.setItem(_vpStoreKey(), JSON.stringify(_vp)); } catch (e) {}
        }, 300);
    }

    function _flushViewport() {
        clearTimeout(_vpSaveTimer);
        try { localStorage.setItem(_vpStoreKey(), JSON.stringify(_vp)); } catch (e) {}
    }

    function _loadViewport() {
        try {
            const v = JSON.parse(localStorage.getItem(_vpStoreKey()) || 'null');
            if (!v || typeof v.k !== 'number') return null;
            return { x: +v.x || 0, y: +v.y || 0, k: Math.min(TG_ZOOM_MAX, Math.max(TG_ZOOM_MIN, v.k)) };
        } catch (e) { return null; }
    }

    // ─── Canvas rendering ───

    function _rerenderCanvas() {
        const world = _worldEl();
        if (!world) return;
        for (const el of world.querySelectorAll('.tg-node')) el.remove();
        for (const node of Object.values(_state.nodes)) _renderNode(node);
        _rerenderWires();
        const sp = document.getElementById('tg-state-panel');
        if (sp && sp.style.display !== 'none') _renderStatePanel();
    }

    // Selection is a class toggle — rebuilding all node DOM on every click ate
    // focus, scroll positions and most of the frame budget.
    function _setSelected(nid) {
        if (_selectedNode === nid) return;
        const prev = _selectedNode;
        _selectedNode = nid;
        if (prev) {
            const prevEl = document.querySelector(`.tg-node[data-node-id="${prev}"]`);
            if (prevEl) prevEl.classList.remove('tg-sel');
        }
        if (nid) {
            const el = document.querySelector(`.tg-node[data-node-id="${nid}"]`);
            if (el) el.classList.add('tg-sel');
        }
    }

    function _renderNode(node) {
        const def = NODE_DEFS[node.type];
        if (!def) return;
        const world = _worldEl();
        if (!world) return;
        const fieldsHtml = def.fields(node.props).replace(/'NODEID'/g, `'${node.id}'`);

        const div = document.createElement('div');
        div.className = 'tg-node' + (node.id === _selectedNode ? ' tg-sel' : '');
        div.dataset.nodeId = node.id;
        div.style.cssText = `
            left:${node.x}px; top:${node.y}px; width:${node.w||260}px;
            --tg-c:${def.color}; --tg-glow:${def.color}33;
        `;

        // Header
        const hdr = document.createElement('div');
        hdr.style.cssText = `
            padding:7px 12px 6px 12px; border-radius:8px 8px 0 0;
            background:${def.color}18; border-bottom:1px solid ${def.color}33;
            display:flex; justify-content:space-between; align-items:center;
            cursor:grab; user-select:none;
        `;
        window.Lit.render(triggerGraphTag`<strong style="color:${def.color};font-size:12px;">${def.label}</strong>
            <span style="font-size:9px;color:var(--text-muted);">${node.id}</span>`, hdr);
        div.appendChild(hdr);

        // Body — inline fields
        const body = document.createElement('div');
        body.style.cssText = 'padding:6px 10px 10px 10px;';
        window.Lit.render(triggerGraphTag`${window.Lit.unsafeHTML(fieldsHtml)}`, body);
        div.appendChild(body);

        // Sockets. Condition branch layout: ✓ YES exits the RIGHT edge (the flow
        // continues sideways, left→right), ✗ NO drops from the bottom — labeled
        // so the branches are tellable apart at a glance, no hovering needed.
        for (const sock of def.sockets) {
            const dot = document.createElement('div');
            dot.className = 'tg-socket';
            dot.dataset.nodeId = node.id;
            dot.dataset.socketId = sock.id;

            let posStyles = '';
            if (sock.id === 'output_yes') posStyles = `right:-8px;top:30%;transform:translateY(-50%);`;
            else if (sock.id === 'output_no') posStyles = `bottom:-8px;left:50%;transform:translateX(-50%);`;
            else if (sock.side === 'left') posStyles = `left:-8px;top:50%;transform:translateY(-50%);`;
            else if (sock.side === 'right') posStyles = `right:-8px;top:50%;transform:translateY(-50%);`;
            else if (sock.side === 'bottom') posStyles = `bottom:-8px;left:50%;transform:translateX(-50%);`;

            dot.style.cssText = `
                position:absolute; ${posStyles}
                width:16px; height:16px; border-radius:50%;
                background:${sock.color || '#888'}; border:3px solid var(--bg-card,#1e1e2e);
                cursor:crosshair; z-index:6;
                box-shadow:0 0 4px rgba(0,0,0,0.5);
            `;
            dot.title = sock.id === 'output_yes' ? '✓ Pass — continues sideways'
                : sock.id === 'output_no' ? '✗ Fail — drops below' : sock.label;
            dot.addEventListener('mousedown', (e) => { e.stopPropagation(); _startWireDrag(node.id, sock.id, e); });
            div.appendChild(dot);
            if (sock.id === 'output_yes' || sock.id === 'output_no') {
                const isYes = sock.id === 'output_yes';
                const label = document.createElement('span');
                label.style.cssText = isYes
                    ? 'position:absolute;left:calc(100% + 12px);top:30%;transform:translateY(-50%);color:#3fb950;font-size:9px;font-weight:600;pointer-events:none;white-space:nowrap;'
                    : 'position:absolute;left:50%;top:calc(100% + 10px);transform:translateX(-50%);color:#f85149;font-size:9px;font-weight:600;pointer-events:none;white-space:nowrap;';
                label.textContent = isYes ? '✓ yes' : '✗ no';
                div.appendChild(label);
            }
        }

        div.addEventListener('mousedown', (e) => {
            if (e.button === 1) { e.preventDefault(); _startPan(e); return; }
            if (e.button !== 0) return;
            if (e.target.closest('.tg-socket') || e.target.closest('select') || e.target.closest('input') || e.target.closest('textarea')) return;
            _setSelected(node.id);
            _startNodeDrag(node.id, e);
        });

        div.addEventListener('dblclick', () => _setSelected(node.id));

        world.appendChild(div);
    }

    // ─── Wires ───

    function _rerenderWires() {
        const svg = document.getElementById('tg-svg');
        if (!svg) return;
        while (svg.firstChild) svg.removeChild(svg.firstChild);
        for (const w of Object.values(_state.wires)) _drawWire(svg, w);
        if (_dragWire) _drawTempWire(svg);
    }

    function _getSocketEl(nodeId, socketId) {
        return document.querySelector(`.tg-socket[data-node-id="${nodeId}"][data-socket-id="${socketId}"]`);
    }

    // Socket position in WORLD coordinates — the SVG draws in world space, so
    // wires stay glued to sockets at any pan/zoom with no re-math on view changes.
    function _getSocketWorldPos(nodeId, socketId) {
        const el = _getSocketEl(nodeId, socketId);
        const canvas = _canvasEl();
        if (!el || !canvas) return null;
        const er = el.getBoundingClientRect();
        const cr = canvas.getBoundingClientRect();
        return {
            x: (er.left - cr.left - _vp.x + er.width / 2) / _vp.k,
            y: (er.top - cr.top - _vp.y + er.height / 2) / _vp.k,
        };
    }

    function _drawWire(svg, wire) {
        const fp = _getSocketWorldPos(wire.from[0], wire.from[1]);
        const tp = _getSocketWorldPos(wire.to[0], wire.to[1]);
        if (!fp || !tp) return;
        const fromNode = _state.nodes[wire.from[0]];
        const sockDef = fromNode && NODE_DEFS[fromNode.type]?.sockets.find(s => s.id === wire.from[1]);
        const dx = Math.max(30, Math.abs(tp.x - fp.x) * 0.5);
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', `M${fp.x},${fp.y} C${fp.x+dx},${fp.y} ${tp.x-dx},${tp.y} ${tp.x},${tp.y}`);
        // Wire inherits the source socket's color: YES branches read green,
        // NO branches red, trigger/behavior gold, actions blue.
        path.setAttribute('stroke', sockDef?.color || '#58a6ff');
        path.setAttribute('stroke-width', '2.5');
        path.setAttribute('fill', 'none');
        path.setAttribute('opacity', '0.8');
        svg.appendChild(path);
    }

    function _drawTempWire(svg) {
        const fp = _getSocketWorldPos(_dragWire.from[0], _dragWire.from[1]);
        if (!fp) return;
        const dx = Math.max(30, Math.abs(_dragWire.mx - fp.x) * 0.5);
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', `M${fp.x},${fp.y} C${fp.x+dx},${fp.y} ${_dragWire.mx-dx},${_dragWire.my} ${_dragWire.mx},${_dragWire.my}`);
        path.setAttribute('stroke', '#e3b341');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke-dasharray', '6,4');
        path.setAttribute('opacity', '0.9');
        svg.appendChild(path);
    }

    // ─── Gesture handlers (document-scoped while a drag/pan is active, so fast
    // ─── mouse movement and releases outside the canvas can't strand a drag) ───

    function _beginGesture() {
        document.addEventListener('mousemove', _onDocMouseMove);
        document.addEventListener('mouseup', _onDocMouseUp);
    }

    function _startPan(e) {
        _pan = { sx: e.clientX, sy: e.clientY, ox: _vp.x, oy: _vp.y };
        const c = _canvasEl();
        if (c) c.classList.add('tg-panning');
        _beginGesture();
    }

    function _startWireDrag(nid, sid, e) {
        const p = _screenToWorld(e.clientX, e.clientY);
        _dragWire = { from: [nid, sid], mx: p.x, my: p.y };
        e.preventDefault();
        e.stopPropagation();
        _beginGesture();
    }

    function _startNodeDrag(nid, e) {
        const n = _state.nodes[nid];
        if (!n) return;
        _dragNode = { nid, sx: n.x, sy: n.y, mx: e.clientX, my: e.clientY };
        const el = e.currentTarget;
        if (el) el.style.zIndex = _nextZ++;
        e.preventDefault();
        _beginGesture();
    }

    function _onCanvasMouseDown(e) {
        _hideContextMenu();
        // Middle-mouse or space+drag pans from anywhere on the canvas.
        if (e.button === 1 || _spacePan) {
            e.preventDefault();
            _startPan(e);
            return;
        }
        if (e.target.id === 'tg-canvas' || e.target.id === 'tg-world' || e.target.id === 'tg-svg') {
            _setSelected(null);
            _startPan(e); // empty-canvas drag pans; a plain click just deselects
        }
    }

    function _onCanvasWheel(e) {
        e.preventDefault();
        // Exponential factor keeps trackpad deltas and mouse notches feeling even.
        _setZoomAt(e.clientX, e.clientY, Math.pow(1.0015, -e.deltaY), false);
    }

    function _onDocMouseMove(e) {
        if (_pan) {
            _vp.x = _pan.ox + e.clientX - _pan.sx;
            _vp.y = _pan.oy + e.clientY - _pan.sy;
            _applyViewport(false);
            return;
        }
        if (_dragWire) {
            const p = _screenToWorld(e.clientX, e.clientY);
            _dragWire.mx = p.x; _dragWire.my = p.y;
            _rerenderWires();
            return;
        }
        if (_dragNode) {
            const n = _state.nodes[_dragNode.nid];
            if (n) {
                // Screen delta → world delta, so the node tracks the cursor 1:1 at any zoom.
                n.x = _dragNode.sx + (e.clientX - _dragNode.mx) / _vp.k;
                n.y = _dragNode.sy + (e.clientY - _dragNode.my) / _vp.k;
                const el = document.querySelector(`.tg-node[data-node-id="${_dragNode.nid}"]`);
                if (el) { el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; }
                _rerenderWires();
            }
        }
    }

    function _onDocMouseUp(e) {
        document.removeEventListener('mousemove', _onDocMouseMove);
        document.removeEventListener('mouseup', _onDocMouseUp);
        if (_pan) {
            _pan = null;
            const c = _canvasEl();
            if (c) c.classList.remove('tg-panning');
        }
        if (_dragWire) {
            const t = document.elementFromPoint(e.clientX, e.clientY);
            if (t && t.classList.contains('tg-socket')) {
                const tnid = t.dataset.nodeId, tsid = t.dataset.socketId;
                const snid = _dragWire.from[0], ssid = _dragWire.from[1];
                const tDef = NODE_DEFS[_state.nodes[tnid]?.type];
                const sDef = NODE_DEFS[_state.nodes[snid]?.type];
                const tSock = tDef?.sockets.find(s => s.id === tsid);
                const sSock = sDef?.sockets.find(s => s.id === ssid);
                if (tSock && sSock && tSock.side !== sSock.side && tsid !== ssid && tnid !== snid) {
                    let wid = `w${_state.wireIdCounter++}`;
                    while (_state.wires[wid]) wid = `w${_state.wireIdCounter++}`;
                    _state.wires[wid] = { id: wid, from: [snid, ssid], to: [tnid, tsid] };
                }
            }
            _dragWire = null; _rerenderWires();
        }
        _dragNode = null;
    }

    function _onKeyUp(e) {
        if (e.key === ' ') {
            _spacePan = false;
            const c = _canvasEl();
            if (c) c.classList.remove('tg-space');
        }
    }

    function _onKeyDown(e) {
        const tag = (e.target?.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target?.isContentEditable) return;
        if ((e.key === 'Delete' || e.key === 'Backspace') && _selectedNode) {
            _deleteNode(_selectedNode); e.preventDefault();
        }
        if (e.key === 'Escape') { _hideContextMenu(); _close(); }
        if (e.key === 'f' || e.key === 'F') { _fitView(true); e.preventDefault(); }
        if (e.key === '+' || e.key === '=') { _zoomCentered(1.25); e.preventDefault(); }
        if (e.key === '-' || e.key === '_') { _zoomCentered(1 / 1.25); e.preventDefault(); }
        if (e.key === ' ' && tag !== 'button') {
            if (!_spacePan) {
                _spacePan = true;
                const c = _canvasEl();
                if (c) c.classList.add('tg-space');
            }
            e.preventDefault();
        }
    }

    // ─── Context menu (right-click) ───

    function _onCanvasContextMenu(e) {
        e.preventDefault();
        if (e.target.id !== 'tg-canvas' && e.target.id !== 'tg-world' && e.target.id !== 'tg-svg') return;
        if (!_canvasEl()) return;
        // Store WORLD coords so nodes spawn exactly where the user clicked, at any zoom.
        _contextWorldPos = _screenToWorld(e.clientX, e.clientY);

        _hideContextMenu();
        _contextSearch = '';

        const menu = document.createElement('div');
        menu.id = 'tg-context-menu';
        menu.style.cssText = `
            position:fixed; left:${e.clientX}px; top:${e.clientY}px; z-index:10001;
            background:var(--bg-card,#1e1e2e); border:1px solid var(--border,#444);
            border-radius:8px; padding:4px; min-width:200px;
            box-shadow:0 8px 24px rgba(0,0,0,0.5);
        `;
        _contextMenu = menu;

        // Search input
        const search = document.createElement('input');
        search.id = 'tg-cm-search';
        search.type = 'text';
        search.placeholder = '🔍 Search nodes...';
        search.style.cssText = 'width:100%;padding:6px 8px;border:1px solid var(--border,#444);border-radius:4px;background:var(--bg-input,#222);color:var(--text,#ccc);font-size:11px;box-sizing:border-box;outline:none;';
        search.addEventListener('input', _filterContextMenu);
        search.addEventListener('keydown', (ev) => { ev.stopPropagation(); if (ev.key === 'Escape') _hideContextMenu(); });
        menu.appendChild(search);

        const list = document.createElement('div');
        list.id = 'tg-cm-list';
        list.style.cssText = 'margin-top:4px;max-height:240px;overflow-y:auto;';
        menu.appendChild(list);

        _renderContextList(list);

        document.body.appendChild(menu);
        setTimeout(() => search.focus(), 50);
    }

    function _renderContextList(list) {
        const items = _mode === 'behavior' ? [
            { type: 'behavior', label: '🧠 Behavior', desc: 'Top-level rule (trigger, priority, interval)' },
            { type: 'condition', label: '❓ Condition', desc: 'Branch with YES/NO (state, item, proximity...)' },
            { type: 'action', label: '🛠 Action', desc: 'Behavior action (speak, go, damage...)' },
            { type: 'state', label: '🎭 State', desc: 'set_npc_state — explicit state transition' }
        ] : [
            { type: 'trigger', label: '⚡ Trigger', desc: 'Entry point (on_use, on_take...)' },
            { type: 'condition', label: '❓ Condition', desc: 'Branch with YES/NO (temp, skill...)' },
            { type: 'effect', label: '⚡ Effect', desc: 'Action (message, spawn, adjust...)' }
        ];
        const q = _contextSearch.toLowerCase();
        const filtered = items.filter(i => !q || i.label.toLowerCase().includes(q) || i.desc.toLowerCase().includes(q) || i.type.includes(q));
        const edgeColor = (t) => t === 'trigger' || t === 'behavior' ? '#e3b341' : t === 'condition' ? '#f85149' : t === 'state' ? '#bc8cff' : '#58a6ff';
        window.Lit.render(triggerGraphTag`
            ${filtered.length > 0 ? filtered.map(i => triggerGraphTag`
                <div class="tg-cm-item" data-type=${i.type} style="padding:6px 8px;border-radius:4px;cursor:pointer;display:flex;flex-direction:column;gap:1px;border-left:3px solid ${edgeColor(i.type)};" @mouseover=${(e) => e.currentTarget.style.background='var(--bg-hover,#2a2a3e)'} @mouseout=${(e) => e.currentTarget.style.background='transparent'} @mousedown=${(e) => { e.stopPropagation(); TriggerGraph._addNode(i.type, _contextWorldPos.x, _contextWorldPos.y); TriggerGraph._hideContextMenu(); }}>
                    <span style="font-size:12px;font-weight:500;">${i.label}</span>
                    <span style="font-size:9px;color:var(--text-muted);">${i.desc}</span>
                </div>
            `) : triggerGraphTag`<div style="padding:8px;color:var(--text-muted);font-size:11px;text-align:center;">No matches</div>`}
        `, list);
    }

    function _filterContextMenu() {
        _contextSearch = document.getElementById('tg-cm-search')?.value || '';
        const list = document.getElementById('tg-cm-list');
        if (list) _renderContextList(list);
    }

    function _hideContextMenu() {
        if (_contextMenu) { _contextMenu.remove(); _contextMenu = null; }
    }
    TG._hideContextMenu = _hideContextMenu;

    // ─── Serialization ───

    function _serializeGraph() {
        return {
            nodes: Object.values(_state.nodes).map(n => ({ id: n.id, type: n.type, x: n.x, y: n.y, w: n.w, props: { ...n.props } })),
            wires: Object.values(_state.wires).map(w => ({ id: w.id, from: w.from, to: w.to }))
        };
    }

    async function _saveGraph() {
        const g = _serializeGraph();
        const isBehavior = _mode === 'behavior';
        if (isBehavior) {
            const hasBehavior = Object.values(_state.nodes).some(n => n.type === 'behavior');
            if (!hasBehavior) {
                if (typeof toastInfo === 'function') toastInfo('Add a Behavior node before saving.');
                else alert('Add a Behavior node before saving.');
                return;
            }
            if (_onSave) _onSave(g);
            _close();
            return;
        }
        const compiled = TG.compileToEngine(g);
        if (!compiled) {
            alert('Add a trigger node before applying.');
            return;
        }
        try {
            const issues = await _validateCompiled(compiled);
            const errors = issues.filter(i => i.severity === 'error');
            const panel = document.getElementById('tg-test-panel');
            if (panel) {
                panel.style.display = 'block';
                window.Lit.render(triggerGraphTag`${_renderValidateResultHtml(issues)}`, panel);
            }
            if (errors.length && !confirm(`Found ${errors.length} validation error(s). Apply anyway?`)) {
                return;
            }
        } catch (e) {
            if (!confirm(`Validation check failed (${e.message}). Apply anyway?`)) return;
        }
        if (_onSave) _onSave(g);
        _close();
    }
    TG._saveGraph = _saveGraph;

    function _saveBlueprint() {
        const g = _serializeGraph();
        const name = prompt('Blueprint name:', 'my_trigger') || 'untitled';
        const desc = prompt('Description:', '') || '';
        const bp = { name, description: desc, graph: g };
        const id = name.replace(/[^a-z0-9_]+/g, '_').toLowerCase();
        fetch('/api/library/triggers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, data: bp })
        }).then(r => r.json()).then(res => {
            if (res.error) alert('Save failed: ' + res.error);
            else alert('💾 Blueprint saved to library as "' + name + '".');
        }).catch(err => alert('Save failed: ' + err.message));
    }
    TG._saveBlueprint = _saveBlueprint;

    function _exportBlueprint() {
        const g = _serializeGraph();
        const name = prompt('Blueprint name:', 'my_trigger') || 'untitled';
        const desc = prompt('Description:', '') || '';
        const bp = { name, description: desc, graph: g };
        const blob = new Blob([JSON.stringify(bp, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `trigger_${name.replace(/[^a-z0-9_]+/g, '_')}.json`;
        a.click();
        URL.revokeObjectURL(a.href);
    }
    TG._exportBlueprint = _exportBlueprint;

    function _applyBlueprint(bp) {
        if (!bp.graph) throw new Error('Invalid blueprint');
        _state = { nodes: {}, wires: {}, nodeIdCounter: 0, wireIdCounter: 0 };
        for (const n of (bp.graph.nodes || [])) {
            const id = n.id || `n${_state.nodeIdCounter++}`;
            _state.nodes[id] = { ...n, id, _expanded: true };
        }
        for (const w of (bp.graph.wires || [])) {
            const id = w.id || `w${_state.wireIdCounter++}`;
            _state.wires[id] = { ...w, id };
        }
        _seedCounters(_state);
        _selectedNode = null; _rerenderCanvas();
        _fitView(true);
    }

    function _loadBlueprint() {
        fetch('/api/library/triggers')
            .then(r => r.json())
            .then(library => {
                const entries = Object.entries(library || {});
                if (entries.length === 0) {
                    if (confirm('No blueprints in the library yet. Import a .json file instead?')) _importBlueprintFile();
                    return;
                }
                const modal = document.createElement('div');
                modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:10000;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:14px;min-width:320px;max-height:70vh;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.5);';
                const rows = entries.map(([id, bp]) => {
                    const n = bp?.name || id;
                    const d = bp?.description || '';
                    return triggerGraphTag`<div style="padding:6px 8px;margin:2px 0;border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:11px;" @click=${() => TriggerGraph._pickBlueprint(id)}>📐 <b>${n}</b><div style="color:var(--text-muted);font-size:10px;">${d || id}</div></div>`;
                });
                window.Lit.render(triggerGraphTag`<div style="font-weight:600;font-size:12px;margin-bottom:8px;color:#e3b341;">📂 Load Blueprint</div>${rows}<div style="margin-top:8px;display:flex;gap:6px;"><button class="btn btn-sm" @click=${() => TriggerGraph._importBlueprintFile()} style="font-size:10px;">⬆️ Import file…</button><button class="btn btn-sm btn-ghost" @click=${(e) => e.currentTarget.closest('div').remove()} style="font-size:10px;">Close</button></div>`, modal);
                document.body.appendChild(modal);
                window.addEventListener('click', function h(ev) {
                    if (ev.target === modal) { modal.remove(); window.removeEventListener('click', h); }
                });
            })
            .catch(err => alert('Could not load blueprints: ' + err.message));
    }
    TG._loadBlueprint = _loadBlueprint;

    TG._pickBlueprint = function(id) {
        fetch('/api/library/triggers')
            .then(r => r.json())
            .then(library => {
                const bp = library[id];
                if (!bp) throw new Error('Blueprint not found');
                _applyBlueprint(bp);
                document.querySelectorAll('#tg-modal + div, body > div').forEach(d => { if (d && d.style && d.style.zIndex === '10000') d.remove(); });
            })
            .catch(err => alert('Failed: ' + err.message));
    };

    function _importBlueprintFile() {
        const inp = document.createElement('input');
        inp.type = 'file'; inp.accept = '.json';
        inp.onchange = async (e) => {
            const file = e.target.files[0]; if (!file) return;
            try {
                const text = await file.text();
                _applyBlueprint(JSON.parse(text));
                document.querySelectorAll('body > div').forEach(d => { if (d && d.style && d.style.zIndex === '10000') d.remove(); });
            } catch (err) { alert('Failed: ' + err.message); }
        };
        inp.click();
    }
    TG._importBlueprintFile = _importBlueprintFile;

    // ─── Engine compilation (behaviors) ───

    function _buildActionFromNode(node) {
        const p = node.props || {};
        if (node.type === 'state') {
            return { type: 'set_npc_state', state: p.state || 'idle' };
        }
        const a = { type: p.action_type || 'message' };
        const at = a.type;
        if (at === 'message' || at === 'speak') a.text = p.text || '';
        else if (at === 'set_npc_state') a.state = p.state || 'idle';
        else if (at === 'damage' || at === 'heal') {
            a.amount = parseInt(p.amount) || (at === 'damage' ? 5 : 10);
            if (at === 'heal') { a.stat = p.stat || 'HP'; a.target = p.target || 'self'; }
            else a.target = p.target || 'player';
        }
        else if (at === 'set_environment') { a.stat = p.stat || 'temperature'; a.amount = parseInt(p.amount) || 0; if (p.area) a.area = p.area; }
        else if (at === 'spawn_item') {
            if (p.item_id) a.item_id = p.item_id;
            if (p.name) a.name = p.name;
            if (p.description) a.description = p.description;
        }
        else if (at === 'spawn_character') {
            if (p.character_id) a.character_id = p.character_id;
            if (p.name) a.display_name = p.name;
            if (p.area) a.area = p.area;
            if (p.message) a.message = p.message;
        }
        else if (at === 'teleport') { if (p.area) a.area = p.area; a.target = p.target || 'player'; }
        else if (at === 'go') {
            a.mode = p.mode || 'goto';
            if (a.mode === 'goto') a.area = p.area || '';
            else a.areas = p.areas || '';
        }
        return a;
    }

    /** Trace behavior node graph into conditions + flat actions. */
    function _traceBehavior(nid, wires, nodes) {
        const node = nodes.find(n => n.id === nid);
        if (!node) return { conditions: [], actions: [] };
        if (node.type === 'condition') {
            const conds = [_buildConditionFromNode(node)];
            const yw = wires.find(w => w.from[0] === nid && w.from[1] === 'output_yes');
            const yes = yw ? _traceBehavior(yw.to[0], wires, nodes) : { conditions: [], actions: [] };
            let actions = yes.actions;
            let conditions = [...conds, ...yes.conditions];
            const nw = wires.find(w => w.from[0] === nid && w.from[1] === 'output_no');
            if (nw) {
                const no = _traceBehavior(nw.to[0], wires, nodes);
                // NO branch only carries actions; there's no else in the behavior model, so
                // we don't fold NO actions into the YES path. Kept for structural parity.
            }
            return { conditions, actions };
        }
        if (node.type === 'action' || node.type === 'state') {
            const act = _buildActionFromNode(node);
            const nw = wires.find(w => w.from[0] === nid && (w.from[1] === 'output' || w.from[1] === 'right'));
            const next = nw ? _traceBehavior(nw.to[0], wires, nodes) : { conditions: [], actions: [] };
            return { conditions: next.conditions, actions: [act, ...next.actions] };
        }
        return { conditions: [], actions: [] };
    }

    /** Compile a behavior-mode graph into the engine behavior array. */
    TG.compileToBehaviors = function(graph) {
        if (!graph?.nodes) return [];
        let behaviorNodes = graph.nodes.filter(n => n.type === 'behavior');
        // Priority comes from vertical position: top = highest priority (matches the
        // drag-to-reorder behavior). Two nodes with identical y keep their order.
        behaviorNodes = behaviorNodes.sort((a, b) => (a.y ?? 0) - (b.y ?? 0));
        const count = behaviorNodes.length;
        const behaviors = behaviorNodes.map((bnode, rank) => {
            const bw = (graph.wires || []).find(w => w.from[0] === bnode.id && (w.from[1] === 'output' || w.from[1] === 'right'));
            let traced = { conditions: [], actions: [] };
            if (bw) traced = _traceBehavior(bw.to[0], graph.wires, graph.nodes);
            const conditions = traced.conditions.length > 0
                ? (traced.conditions.length === 1 ? traced.conditions[0] : { operator: 'and', conditions: traced.conditions })
                : {};
            const behavior = {
                trigger: bnode.props.trigger || 'on_tick',
                interval: parseInt(bnode.props.interval) || 1,
                priority: count - rank,
                conditions,
                actions: traced.actions.length ? traced.actions : [{ type: 'message', text: '' }]
            };
            return behavior;
        });
        // Stable order: highest priority first (mirrors engine sort in npc_behaviors.py)
        behaviors.sort((a, b) => b.priority - a.priority);
        return behaviors;
    };

    /** Convert an engine behavior array into a behavior-mode graph.
     * Layout: priority-ordered row-major grid, one block per behavior —
     * [behavior] → [conditions column] → [actions column] — with per-block
     * heights so chains never overlap the next behavior. compileToBehaviors
     * derives priority from Y (ties keep load order), so the grid preserves it. */
    TG.behaviorsToGraph = function(behaviors) {
        const list = Array.isArray(behaviors) ? behaviors : [];
        const sorted = [...list].sort((a, b) => (b.priority ?? 1) - (a.priority ?? 1));
        const nodes = [];
        const wires = [];
        let nodeId = 0;
        const COLS = Math.min(3, Math.max(1, Math.ceil(Math.sqrt(sorted.length))));
        // CHAIN_DY 150 clears the tallest nodes (action cards with 2-row textareas).
        const CELL_W = 920, BASE_H = 70, CHAIN_DY = 150, ROW_GAP = 50;
        let rowY = 40, rowH = 0, col = 0;
        sorted.forEach((b) => {
            let conditions = b.conditions || {};
            if (conditions && typeof conditions === 'object' && !Array.isArray(conditions) && (conditions.operator || (conditions.type && conditions.type !== 'none'))) {
                conditions = conditions.conditions && conditions.conditions.length ? conditions.conditions : (conditions.type ? [conditions] : []);
            }
            if (!Array.isArray(conditions)) conditions = [];
            const actions = b.actions || [];
            const chainLen = Math.max(1, conditions.length, actions.length);
            const blockH = BASE_H + chainLen * CHAIN_DY;

            if (col >= COLS) { col = 0; rowY += rowH + ROW_GAP; rowH = 0; }
            const bx = 40 + col * CELL_W;
            const by = rowY;
            col++;
            rowH = Math.max(rowH, blockH);

            const bnode = `n${nodeId++}`;
            nodes.push({
                id: bnode, type: 'behavior', x: bx, y: by,
                props: { trigger: b.trigger || 'on_tick', priority: b.priority ?? 1, interval: b.interval ?? 1 }
            });
            let from = [bnode, 'output'];
            conditions.forEach((c, ci) => {
                const cnode = `n${nodeId++}`;
                nodes.push({ id: cnode, type: 'condition', x: bx + 300, y: by + BASE_H + ci * CHAIN_DY, props: _conditionToGraphProps(c) });
                wires.push({ id: `w${wires.length}`, from, to: [cnode, 'input'] });
                from = [cnode, 'output_yes'];
            });
            actions.forEach((act, ai) => {
                const anode = `n${nodeId++}`;
                const isState = act.type === 'set_npc_state';
                nodes.push({
                    id: anode, type: isState ? 'state' : 'action',
                    x: bx + 580, y: by + BASE_H + ai * CHAIN_DY,
                    props: isState ? { state: act.state || '' } : (() => {
                        const flat = Object.fromEntries(Object.entries(act).filter(([k]) => k !== 'type'));
                        return { action_type: act.type || 'message', ...flat };
                    })()
                });
                wires.push({ id: `w${wires.length}`, from, to: [anode, 'input'] });
                if (actions.length > 1 && ai < actions.length - 1) from = [anode, 'output'];
            });
        });
        return { nodes, wires };
    };

    // ─── Engine compilation (triggers) ───

    function _buildConditionFromNode(node) {
        const cond = { type: node.props.condition_type || 'skill_check' };
        const p = node.props;
        if (cond.type === 'skill_check') {
            cond.skill = p.skill || 'Athletics';
            cond.dc = parseInt(p.dc) || 10;
        } else if (cond.type === 'save_throw') {
            cond.stat = p.skill || 'DEX';
            cond.dc = parseInt(p.dc) || 12;
            cond.target = p.target || 'self';
        } else if (cond.type === 'state_equals') {
            cond.target = p.target || 'self';
            cond.value = p.value || '';
        } else if (cond.type === 'eq') {
            cond.target = p.target || 'npc_state';
            cond.value = p.value || '';
        } else if (cond.type === 'in_area') {
            cond.area = p.area || '';
            cond.target = p.target || 'npc';
        } else if (cond.type === 'tick_since_state') {
            cond.min_ticks = parseInt(p.min_ticks) || 0;
        } else if (cond.type === 'proximity') {
            cond.max_areas = parseInt(p.max_areas) || 0;
        } else if (cond.type === 'random_chance') {
            cond.chance = p.chance !== undefined ? parseFloat(p.chance) : (p.value !== undefined && p.value !== '' ? parseFloat(p.value) : 0.5);
        } else if (['area_temp', 'vital', 'vital_above', 'vital_below'].includes(cond.type)) {
            cond.operator = p.operator || 'lt';
            cond.value = p.value !== undefined && p.value !== '' ? p.value : '';
            if (p.stat) cond.stat = p.stat;
            if (p.target) cond.target = p.target;
        } else if (cond.type === 'is_equipped') {
            cond.item = p.item || p.value || '';
            if (p.target) cond.target = p.target;
        } else if (cond.type === 'area_has_status') {
            cond.status_type = p.status_type || p.value || '';
            if (p.target) cond.target = p.target;
        } else if (cond.type === 'item_relationship') {
            cond.relation = p.relation || 'in';
            if (p.direction) cond.direction = p.direction;
            if (p.target) cond.target = p.target;
        } else if (cond.type === 'npc_emotion_is') {
            cond.emotion = p.emotion || '';
            cond.operator = p.operator || 'eq';
            if (p.value !== undefined && p.value !== '') cond.value = p.value;
        } else if (cond.type === 'npc_is_hidden') {
            cond.value = (p.value === true || p.value === 'true');
        } else if (cond.type === 'character_has_tag') {
            cond.tag = p.tag || p.value || '';
            cond.target = p.target || 'self';
        } else {
            if (p.value !== undefined && p.value !== '') cond.value = p.value;
            if (p.target) cond.target = p.target;
            if (p.skill) cond.skill = p.skill;
            if (p.dc) cond.dc = parseInt(p.dc);
            if (p.item) cond.item = p.item;
            if (p.operator) cond.operator = p.operator;
            if (p.stat) cond.stat = p.stat;
        }
        return cond;
    }

    TG.compileToEngine = function(graph) {
        if (!graph?.nodes) return null;
        const triggerNode = graph.nodes.find(n => n.type === 'trigger');
        if (!triggerNode) return null;
        const tt = triggerNode.props.trigger_type || 'on_use';
        const tw = (graph.wires || []).find(w => w.from[0] === triggerNode.id && (w.from[1] === 'output' || w.from[1] === 'right'));
        if (!tw) {
            const empty = { trigger_type: tt, effects: [{ type: 'message', params: { message: '' } }], conditions: {} };
            if (triggerNode.props.target_tag) empty.target_name = triggerNode.props.target_tag;
            return empty;
        }
        const traced = _traceGraph(tw.to[0], graph.wires, graph.nodes);
        const condTree = traced.conditions.length > 0 ? { operator: 'and', conditions: traced.conditions } : {};
        const result = {
            trigger_type: tt,
            effects: traced.effects.length ? traced.effects : [{ type: 'message', params: { message: '' } }],
            conditions: condTree
        };
        if (triggerNode.props.target_tag) result.target_name = triggerNode.props.target_tag;
        if (triggerNode.props.target_state) result.target_state = triggerNode.props.target_state;
        if (traced.fail_message) result.fail_message = traced.fail_message;
        return result;
    };

    /** Mirror the form editor's _collectData: convert a graph node's flat props
     * into engine-effect params (save gates → on_success/on_fail arrays, target_by
     * normalization, boolean coercions, empty strings dropped, JSON textareas parsed). */
    function _normalizeEffectParams(type, params) {
        const p = { ...params };
        delete p.effect_type;

        // Advanced JSON textareas (apply_condition symptoms/extras, save branches).
        ['symptoms', 'extra_conditions', 'succ_json', 'fail_json'].forEach(k => {
            if (typeof p[k] === 'string') {
                const s = p[k].trim();
                if (!s) { delete p[k]; return; }
                try { p[k] = JSON.parse(s); } catch (e) { delete p[k]; }
            }
        });

        if (type === 'save') {
            const branch = (side) => {
                // Advanced JSON wins; pre-existing imported arrays are preserved.
                if (Array.isArray(p[side === 'succ' ? 'on_success' : 'on_fail']) && p[side + '_json'] === undefined && p[side + '_type'] === undefined) {
                    return p[side === 'succ' ? 'on_success' : 'on_fail'];
                }
                const j = typeof p[side + '_json'] === 'object' ? p[side + '_json'] : undefined;
                if (Array.isArray(j)) return j;
                const t = p[side + '_type'] || 'none';
                if (t === 'none') return [];
                if (t === 'message') return p[side + '_msg'] ? [{ type: 'message', params: { message: p[side + '_msg'] } }] : [];
                if (t === 'apply_condition') {
                    const bp = { condition: p[side + '_cond'] || '', target: 'self' };
                    if (p[side + '_dur'] !== undefined && p[side + '_dur'] !== '') bp.duration = parseInt(p[side + '_dur']) || 0;
                    if (p[side + '_src']) bp.source = p[side + '_src'];
                    if (p[side + '_src_type']) bp.source_type = p[side + '_src_type'];
                    return [{ type: 'apply_condition', params: bp }];
                }
                if (t === 'damage') return [{ type: 'damage', params: { amount: parseInt(p[side + '_dmg']) || 5, target: 'self' } }];
                return [];
            };
            const out = { dc: parseInt(p.save_dc) || 12, on_success: branch('succ'), on_fail: branch('fail') };
            if (p.save_mode === 'skill') out.skill = p.save_skill || 'Athletics';
            else out.stat = p.save_stat || 'WIS';
            // An imported graph that already carries full save params (and no flat
            // editor fields) round-trips untouched.
            if (p.save_dc === undefined && Array.isArray(p.on_success)) {
                return { ...p };
            }
            return out;
        }

        if (type === 'apply_condition' || type === 'remove_condition') {
            const by = p.target_by;
            if (!by || by === 'self') {
                p.target = 'self';
                delete p.target_by; delete p.target_value;
            } else if (by === 'all_in_area') {
                delete p.target_value; delete p.target;
            } else {
                p.target_value = p.target_value ?? p.target ?? '';
                delete p.target;
            }
        }
        if (type === 'set_hidden' || type === 'set_way_view') {
            if (p.hidden !== undefined) p.hidden = (p.hidden === true || p.hidden === 'true');
            if (p.see_through !== undefined) p.see_through = (p.see_through === true || p.see_through === 'true');
        }
        if (type === 'apply_trait' && (p.param === 'true' || p.param === 'false' || p.param === '')) {
            p.param = p.param === 'false' ? false : true;
        }
        if (type === 'spawn_item' && p.into === 'area') delete p.into;

        // The form never serializes empty-string params — mirror that.
        Object.keys(p).forEach(k => { if (p[k] === '' || p[k] === undefined) delete p[k]; });
        return p;
    }

    function _traceGraph(nid, wires, nodes) {
        const node = nodes.find(n => n.id === nid);
        if (!node) return { effects: [], conditions: [], fail_message: '' };
        if (node.type === 'condition') {
            const conds = [_buildConditionFromNode(node)];
            const yw = wires.find(w => w.from[0] === nid && w.from[1] === 'output_yes');
            const nw = wires.find(w => w.from[0] === nid && w.from[1] === 'output_no');
            const ye = yw ? _traceGraph(yw.to[0], wires, nodes) : { effects: [], conditions: [], fail_message: '' };
            let failMessage = '';
            if (nw) {
                const ne = _traceGraph(nw.to[0], wires, nodes);
                const msgEff = ne.effects.find(e => e.type === 'message');
                if (msgEff?.params?.message) failMessage = msgEff.params.message;
            }
            return {
                effects: ye.effects,
                conditions: [...conds, ...ye.conditions],
                fail_message: failMessage || ye.fail_message || ''
            };
        }
        if (node.type === 'effect') {
            const eff = { type: node.props.effect_type || 'message', params: _normalizeEffectParams(node.props.effect_type || 'message', node.props) };
            const nw = wires.find(w => w.from[0] === nid && (w.from[1] === 'output' || w.from[1] === 'right'));
            const next = nw ? _traceGraph(nw.to[0], wires, nodes) : { effects: [], conditions: [], fail_message: '' };
            return {
                effects: [eff, ...next.effects],
                conditions: next.conditions,
                fail_message: next.fail_message
            };
        }
        return { effects: [], conditions: [], fail_message: '' };
    }

    return TG;
})();
