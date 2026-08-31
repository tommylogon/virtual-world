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
            summary: (p) => p.trigger_type || 'on_use',
            sockets: [
                { id: 'output', side: 'right', label: '→', color: '#e3b341' }
            ],
            fields: (p) => `
                <div class="tg-field-row"><label>Type</label>
                    <select class="tg-field" data-key="trigger_type" onchange="TG._onFieldChange(this);TG._onTriggerTypeChange(this)">${[
                        'on_use','on_take','on_drop','on_examine','on_tick',
                        'on_equip','on_unequip','on_use_on','on_toggle_on','on_toggle_off','on_depleted',
                        'on_open','on_close','on_state_enter','on_state_exit',
                        'on_fail_jump','on_fail_climb'
                    ].map(t => `<option value="${t}" ${(p.trigger_type||'on_use')===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</select>
                </div>
                <div class="tg-field-row" style="display:${p.trigger_type==='on_use_on'?'':'none'}"><label>Target Tag</label>
                    <input class="tg-field" data-key="target_tag" value="${p.target_tag||''}" placeholder="oil_lamp, key_item, etc" onchange="TG._onFieldChange(this)">
                </div>
            `
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
                    <select class="tg-field" data-key="condition_type" onchange="TG._onFieldChange(this);TG._rerenderNode('${'NODEID'}')">${[
                        'eq','has_item','has_items','has_trait','has_tag','in_area','tick_since_state','proximity','random_chance',
                        'area_temp','vital','is_equipped','uses_reached','uses_above','skill_check','save_throw','state_equals','time_of_day','weather','speech_matches'
                    ].map(t => `<option value="${t}" ${ct===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</select>
                </div>
                <div class="tg-cond-eq" style="display:${ct==='eq'?'':'none'}">
                    <div class="tg-field-row"><label>Target Key</label><input class="tg-field" data-key="target" value="${p.target||'npc_state'}" placeholder="npc_state, npc_area..." onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Value</label><input class="tg-field" data-key="value" value="${p.value||''}" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-inarea" style="display:${ct==='in_area'?'':'none'}">
                    <div class="tg-field-row"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label>
                        <select class="tg-field" data-key="target" onchange="TG._onFieldChange(this)"><option value="npc" ${(p.target||'npc')==='npc'?'selected':''}>NPC</option><option value="player" ${p.target==='player'?'selected':''}>Player</option></select>
                    </div>
                </div>
                <div class="tg-cond-ticks" style="display:${ct==='tick_since_state'?'':'none'}">
                    <div class="tg-field-row"><label>Min Ticks</label><input class="tg-field" data-key="min_ticks" type="number" value="${p.min_ticks ?? 0}" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-prox" style="display:${ct==='proximity'?'':'none'}">
                    <div class="tg-field-row"><label>Max Areas</label><input class="tg-field" data-key="max_areas" type="number" value="${p.max_areas ?? 0}" placeholder="0 = same area" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-val" style="display:${showVal?'':'none'}">
                    <div class="tg-field-row"><label>Value</label><input class="tg-field" data-key="value" value="${p.value||''}" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-comp" style="display:${showComp?'':'none'}">
                    <div class="tg-field-row"><label>Comparator</label>
                        <select class="tg-field" data-key="operator" onchange="TG._onFieldChange(this)">${['lt','le','eq','ge','gt'].map(o => `<option value="${o}" ${(p.operator||'lt')===o?'selected':''}>${o}</option>`).join('')}</select>
                    </div>
                </div>
                <div class="tg-cond-stat" style="display:${showStat?'':'none'}">
                    <div class="tg-field-row"><label>Vital</label><input class="tg-field" data-key="stat" value="${p.stat||'HP'}" placeholder="HP, Energy..." onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-item" style="display:${showItem?'':'none'}">
                    <div class="tg-field-row"><label>Item</label><input class="tg-field" data-key="item" value="${p.item||''}" placeholder="torch, key..." onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-skill" style="display:${showSkill?'':'none'}">
                    <div class="tg-field-row"><label>${ct==='save_throw'?'Stat / Skill':'Skill'}</label><input class="tg-field" data-key="skill" value="${p.skill||(ct==='save_throw'?'DEX':'Athletics')}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>DC</label><input class="tg-field" data-key="dc" type="number" value="${p.dc||(ct==='save_throw'?12:10)}" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-state" style="display:${showState?'':'none'}">
                    <div class="tg-field-row"><label>Node</label><input class="tg-field" data-key="node" value="${p.node||p.target||''}" placeholder="node_id" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="value" value="${p.value||''}" placeholder="on, open..." onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-cond-target" style="display:${showTarget?'':'none'}">
                    <div class="tg-field-row"><label>Target</label><input class="tg-field" data-key="target" value="${p.target||''}" placeholder="blank = self" onchange="TG._onFieldChange(this)"></div>
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
                return `
                <div class="tg-field-row"><label>Type</label>
                    <select class="tg-field" data-key="effect_type" onchange="TG._onFieldChange(this);TG._rerenderNode('${'NODEID'}')">${[
                        'message','save','spawn_item','spawn_character','give_item','adjust_environment','set_environment',
                        'set_state','set_hidden','adjust_vital','damage','heal','teleport','rename','remove_item',
                        'adjust_uses','reduce_uses','add_tag','remove_tag','apply_trait','remove_trait',
                        'apply_condition','remove_condition'
                    ].map(t => `<option value="${t}" ${et===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</select>
                </div>
                <div class="tg-eff-tag" style="display:${['add_tag','remove_tag'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Tag</label><input class="tg-field" data-key="tag" value="${p.tag||''}" placeholder="flammable" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Node</label><input class="tg-field" data-key="node_id" value="${p.node_id||'self'}" placeholder="self or node_id" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-trait" style="display:${['apply_trait','remove_trait'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Trait</label><input class="tg-field" data-key="trait" value="${p.trait||''}" placeholder="dark_vision, hardy, allergic..." onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label><input class="tg-field" data-key="target" value="${p.target||'self'}" list="tg-char-list" placeholder="self or character name" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='apply_trait'?'':'none'}"><label>Param</label><input class="tg-field" data-key="param" value="${p.param!==undefined?p.param:'true'}" placeholder="true or value" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-condition" style="display:${['apply_condition','remove_condition'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Condition</label><input class="tg-field" data-key="condition" value="${p.condition||''}" list="tg-condition-list" placeholder="poisoned, blind, exhausted..." onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label>
                        <select class="tg-field" data-key="target_by" onchange="TG._onFieldChange(this);TG._rerenderNode('${'NODEID'}')">
                            <option value="self" ${!(p.target_by)&&(p.target==='self'||!p.target)?'selected':''}>Self (actor)</option>
                            <option value="all_in_area" ${p.target_by==='all_in_area'?'selected':''}>All characters in area</option>
                            <option value="name" ${p.target_by==='name'?'selected':''}>By name</option>
                            <option value="tag" ${p.target_by==='tag'?'selected':''}>By tag</option>
                            <option value="trait" ${p.target_by==='trait'?'selected':''}>By trait</option>
                            <option value="type" ${p.target_by==='type'?'selected':''}>By type</option>
                        </select>
                    </div>
                    <div class="tg-field-row" style="display:${(p.target_by&&p.target_by!=='self'&&p.target_by!=='all_in_area')||(!p.target_by&&p.target&&p.target!=='self')?'':'none'}"><label>${p.target_by==='tag'?'Tag':p.target_by==='trait'?'Trait':p.target_by==='type'?'Type (item/character/way/area)':'Name'}</label><input class="tg-field" data-key="${p.target_by?'target_value':'target'}" value="${p.target_by?(p.target_value||''):(p.target||'')}" placeholder="${p.target_by==='tag'?'vampire, wolf...':p.target_by==='trait'?'hostile, dark_vision...':p.target_by==='type'?'character, item...':'name'}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Duration</label><input class="tg-field" data-key="duration" type="number" value="${p.duration!==undefined?p.duration:''}" placeholder="blank = default" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Source</label><input class="tg-field" data-key="source" value="${p.source||''}" placeholder="poisoned wine..." onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Per-tick drain (0 = use catalog default)</label>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 6px;">
                            ${['HP','Energy','Hunger','Thirst','Hygiene','Social','Bladder','Sanity','Entertainment','Temperature'].map(v =>
                                `<label style="display:flex;align-items:center;gap:4px;font-size:9px;justify-content:space-between;">
                                    <span style="flex:1;">${v}</span>
                                    <input type="number" step="any" class="tg-periodic-${v}" value="${p.periodic?.[v] !== undefined ? p.periodic[v] : 0}" style="width:48px;font-size:10px;" onchange="TG._onFieldChange(this)">
                                </label>`
                            ).join('')}
                        </div>
                    </div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Symptoms (JSON by ticks left)</label><textarea class="tg-field" data-key="symptoms" rows="2" placeholder='{"8":"a queasy twist...","1":"everything spins"}' onchange="TG._onFieldChange(this)">${p.symptoms?JSON.stringify(p.symptoms):''}</textarea></div>
                    <div class="tg-field-row" style="display:${et==='apply_condition'?'':'none'}"><label>Extras (JSON)</label><textarea class="tg-field" data-key="extra_conditions" rows="2" placeholder='[{"condition":"blind","duration":3}]' onchange="TG._onFieldChange(this)">${p.extra_conditions?JSON.stringify(p.extra_conditions):''}</textarea></div>
                </div>
                <div class="tg-eff-msg" style="display:${et==='message'?'':'none'}">
                    <div class="tg-field-row"><label>Message</label><textarea class="tg-field" data-key="message" rows="2" onchange="TG._onFieldChange(this)">${p.message||''}</textarea></div>
                    <div class="tg-field-row"><label>Success</label><input class="tg-field" data-key="success_message" value="${p.success_message||''}" placeholder="optional" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Fail</label><input class="tg-field" data-key="fail_message" value="${p.fail_message||''}" placeholder="optional" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-spawn" style="display:${['spawn_item','give_item','spawn_character'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>${et==='spawn_character'?'Character ID':'Item ID'}</label><input class="tg-field" data-key="${et==='spawn_character'?'character_id':'item_id'}" value="${p[et==='spawn_character'?'character_id':'item_id']||''}" placeholder="${et==='spawn_character'?'character_id':'item_id'}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Display Name</label><input class="tg-field" data-key="name" value="${p.name||''}" placeholder="optional" onchange="TG._onFieldChange(this)"></div>
                    ${et==='spawn_character' ? `<div class="tg-field-row"><label>Area (blank=current)</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" onchange="TG._onFieldChange(this)"></div>` : ''}
                    ${et==='spawn_character' ? `<div class="tg-field-row"><label>Message (supports {character_name})</label><input class="tg-field" data-key="message" value="${p.message||''}" placeholder="{character_name} arrives!" onchange="TG._onFieldChange(this)"></div>` : ''}
                </div>
                <div class="tg-eff-give" style="display:${et==='give_item'?'':'none'}">
                    <div class="tg-field-row"><label>Target</label><input class="tg-field" data-key="target" value="${p.target||'self'}" list="tg-char-list" placeholder="self, target, or character name" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Message</label><input class="tg-field" data-key="message" value="${p.message||''}" placeholder="optional (supports {target_name})" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-env" style="display:${['adjust_environment','set_environment'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Temp</label><input class="tg-field" data-key="temperature" type="number" value="${p.temperature||''}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Light</label><input class="tg-field" data-key="light" type="number" value="${p.light||''}" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-state" style="display:${['set_state','set_hidden'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Node</label><input class="tg-field" data-key="node_id" value="${p.node_id||'self'}" placeholder="self" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-eff-state-val" style="display:${et==='set_state'?'':'none'}">
                        <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="state" value="${p.state||''}" onchange="TG._onFieldChange(this)"></div>
                    </div>
                    <div class="tg-eff-hidden-val" style="display:${et==='set_hidden'?'':'none'}">
                        <div class="tg-field-row"><label>Hidden</label><select class="tg-field" data-key="hidden" onchange="TG._onFieldChange(this)"><option value="true" ${(p.hidden===true||p.hidden==='true')?'selected':''}>True</option><option value="false" ${(!p.hidden||p.hidden==='false')?'selected':''}>False</option></select></div>
                    </div>
                </div>
                <div class="tg-eff-vital" style="display:${['adjust_vital','damage','heal'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>Stat</label><input class="tg-field" data-key="stat" value="${p.stat||'HP'}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Amount</label><input class="tg-field" data-key="amount" type="number" value="${p.amount||''}" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-tp" style="display:${et==='teleport'?'':'none'}">
                    <div class="tg-field-row"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-eff-uses" style="display:${['adjust_uses','reduce_uses'].includes(et)?'':'none'}">
                    <div class="tg-field-row"><label>${et==='adjust_uses'?'Delta':'Amount'}</label><input class="tg-field" data-key="${et==='adjust_uses'?'delta':'amount'}" type="number" value="${et==='adjust_uses'?p.delta||'':p.amount||''}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target Node</label><input class="tg-field" data-key="node_id" value="${p.node_id||'self'}" placeholder="self or node_id" onchange="TG._onFieldChange(this)"></div>
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
                    <select class="tg-field" data-key="trigger" onchange="TG._onFieldChange(this);TG._rerenderNode('${'NODEID'}')">${[
                        'on_tick','on_player_enter_area','on_player_leave_area','on_item_taken','on_speech_heard','on_combat','on_state_changed'
                    ].map(t => `<option value="${t}" ${(p.trigger||'on_tick')===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</select>
                </div>
                <div class="tg-field-row"><label>Priority</label><input class="tg-field" data-key="priority" type="number" value="${p.priority ?? 1}" onchange="TG._onFieldChange(this)"></div>
                <div class="tg-field-row"><label>Interval</label><input class="tg-field" data-key="interval" type="number" min="1" value="${p.interval ?? 1}" onchange="TG._onFieldChange(this)"></div>
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
                    <select class="tg-field" data-key="action_type" onchange="TG._onFieldChange(this);TG._rerenderNode('${'NODEID'}')">${[
                        'message','speak','set_npc_state','damage','heal','set_environment','spawn_item','spawn_character','teleport','go','llm_respond'
                    ].map(t => `<option value="${t}" ${at===t?'selected':''}>${t.replace(/_/g,' ')}</option>`).join('')}</select>
                </div>
                <div class="tg-beh-text" style="display:${['message','speak'].includes(at)?'':'none'}">
                    <div class="tg-field-row"><label>Text</label><textarea class="tg-field" data-key="text" rows="2" onchange="TG._onFieldChange(this)">${p.text||''}</textarea></div>
                </div>
                <div class="tg-beh-state" style="display:${at==='set_npc_state'?'':'none'}">
                    <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="state" value="${p.state||''}" placeholder="idle, curious, angry..." onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-beh-llm" style="display:${at==='llm_respond'?'':'none'}">
                    <div class="tg-field-row"><label>Instructions (persona prompt)</label><textarea class="tg-field" data-key="instructions" rows="2" onchange="TG._onFieldChange(this)">${p.instructions||''}</textarea></div>
                    <div class="tg-field-row"><label>Fallback message</label><input class="tg-field" data-key="fallback_message" value="${p.fallback_message||''}" placeholder="Kept quiet when it cannot answer" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-beh-damage" style="display:${['damage','heal'].includes(at)?'':'none'}">
                    <div class="tg-field-row"><label>${at==='damage'?'Damage':'Heal'} Amount</label><input class="tg-field" data-key="amount" type="number" value="${p.amount ?? (at==='damage'?5:10)}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>${at==='damage'?'Target':'Stat'}</label>
                        ${at==='damage'
                            ? `<select class="tg-field" data-key="target" onchange="TG._onFieldChange(this)"><option value="player" ${(p.target||'player')==='player'?'selected':''}>Player</option><option value="self" ${p.target==='self'?'selected':''}>Self</option></select>`
                            : `<select class="tg-field" data-key="stat" onchange="TG._onFieldChange(this)">${['HP','Energy','Hunger','Thirst','Hygiene','Social','Bladder','Sanity'].map(v=>`<option value="${v}" ${(p.stat||'HP')===v?'selected':''}>${v}</option>`).join('')}</select>`}
                    </div>
                    <div class="tg-field-row" style="display:${at==='heal'?'':'none'}"><label>Heal Target</label><select class="tg-field" data-key="target" onchange="TG._onFieldChange(this)"><option value="self" ${(p.target||'self')==='self'?'selected':''}>Self</option><option value="player" ${p.target==='player'?'selected':''}>Player</option></select></div>
                </div>
                <div class="tg-beh-env" style="display:${at==='set_environment'?'':'none'}">
                    <div class="tg-field-row"><label>Stat</label><input class="tg-field" data-key="stat" value="${p.stat||'temperature'}" placeholder="temperature, light..." onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Delta</label><input class="tg-field" data-key="amount" type="number" value="${p.amount ?? 0}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="blank = current" onchange="TG._onFieldChange(this)"></div>
                </div>
                <div class="tg-beh-spawn" style="display:${['spawn_item','spawn_character'].includes(at)?'':'none'}">
                    ${at==='spawn_item' ? `
                    <div class="tg-field-row"><label>Item ID</label><input class="tg-field" data-key="item_id" value="${p.item_id||''}" placeholder="library id" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Display Name</label><input class="tg-field" data-key="name" value="${p.name||''}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Description</label><input class="tg-field" data-key="description" value="${p.description||''}" onchange="TG._onFieldChange(this)"></div>
                    ` : at==='spawn_character' ? `
                    <div class="tg-field-row"><label>Character ID</label><input class="tg-field" data-key="character_id" value="${p.character_id||''}" placeholder="library id" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Display Name</label><input class="tg-field" data-key="name" value="${p.name||p.display_name||''}" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Area (blank=current)</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" onchange="TG._onFieldChange(this)"></div>
                    ` : ''}
                </div>
                <div class="tg-beh-tp" style="display:${at==='teleport'?'':'none'}">
                    <div class="tg-field-row"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row"><label>Target</label><select class="tg-field" data-key="target" onchange="TG._onFieldChange(this)"><option value="player" ${(p.target||'player')==='player'?'selected':''}>Player</option><option value="self" ${p.target==='self'?'selected':''}>Self</option></select></div>
                </div>
                <div class="tg-beh-go" style="display:${at==='go'?'':'none'}">
                    <div class="tg-field-row"><label>Mode</label>
                        <select class="tg-field" data-key="mode" onchange="TG._onFieldChange(this);TG._rerenderNode('${'NODEID'}')">
                            <option value="goto" ${(p.mode||'goto')==='goto'?'selected':''}>Go to area</option>
                            <option value="patrol" ${p.mode==='patrol'?'selected':''}>Patrol areas</option>
                        </select>
                    </div>
                    <div class="tg-field-row" style="display:${(p.mode||'goto')==='goto'?'':'none'}"><label>Area</label><input class="tg-field" data-key="area" value="${p.area||''}" placeholder="area_name" onchange="TG._onFieldChange(this)"></div>
                    <div class="tg-field-row" style="display:${p.mode==='patrol'?'':'none'}"><label>Areas (comma-sep)</label><input class="tg-field" data-key="areas" value="${p.areas||''}" placeholder="kitchen, garden, hall" onchange="TG._onFieldChange(this)"></div>
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
                <div class="tg-field-row"><label>State</label><input class="tg-field" data-key="state" value="${p.state||''}" placeholder="idle, curious, fleeing..." onchange="TG._onFieldChange(this)"></div>
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
        else if (['has_trait', 'has_tag'].includes(t) && cond.value != null) props.value = String(cond.value);
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
                trigger_type: types[0] || 'on_use',
                target_tag: t.target_name || t.target_tag || '',
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
        }

        _renderModal();
        _rerenderCanvas();
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
        const canvas = document.getElementById('tg-canvas');
        if (!canvas) return;
        _renderNode(canvas, node);
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
            <span style="font-size:10px;color:var(--text-muted);margin-right:8px;">Right-click canvas · Del to delete</span>
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

        const canvas = document.createElement('div');
        canvas.id = 'tg-canvas';
        canvas.style.cssText = 'flex:1;position:relative;overflow:hidden;';

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.id = 'tg-svg';
        svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:2;';
        canvas.appendChild(svg);

        const statePanel = document.createElement('div');
        statePanel.id = 'tg-state-panel';
        statePanel.style.cssText = `display:none;width:240px;flex-shrink:0;border-left:1px solid var(--border,#333);background:var(--bg-inset,#161625);overflow-y:auto;font-size:11px;padding:8px;`;

        // Body row wraps the canvas + (collapsible) state summary sidebar
        const bodyRow = document.createElement('div');
        bodyRow.style.cssText = 'flex:1;position:relative;min-height:0;';
        canvas.style.position = 'absolute;';
        // canvas must fill the row; place state panel absolutely on the right when shown
        canvas.style.cssText += ';position:absolute;top:0;left:0;right:0;bottom:0;overflow:hidden;';
        statePanel.style.position = 'absolute';
        statePanel.style.top = '0';
        statePanel.style.right = '0';
        statePanel.style.bottom = '0';
        statePanel.style.zIndex = '5';
        bodyRow.appendChild(canvas);
        bodyRow.appendChild(statePanel);

        modal.appendChild(toolbar);
        modal.appendChild(testPanel);
        modal.appendChild(bodyRow);
        document.body.appendChild(modal);

        // Character datalist for target fields (apply_trait/remove_trait, condition targets)
        if (!document.getElementById('tg-char-list')) {
            const dl = document.createElement('datalist');
            dl.id = 'tg-char-list';
            const chars = (typeof worldState !== 'undefined' && worldState?.players) ? Object.keys(worldState.players) : [];
            chars.forEach(name => {
                const o = document.createElement('option'); o.value = name; dl.appendChild(o);
            });
            document.body.appendChild(dl);
        }
        // Condition id datalist for apply_condition/remove_condition effects
        if (!document.getElementById('tg-condition-list')) {
            const dl = document.createElement('datalist');
            dl.id = 'tg-condition-list';
            ['awake','dead','unconscious','paralysed','stunned','grappled','restrained','prone','busy',
             'exhausted','sick','poisoned','blind','deaf','mute','frightened','charmed'].forEach(c => {
                const o = document.createElement('option'); o.value = c; dl.appendChild(o);
            });
            document.body.appendChild(dl);
        }

        canvas.addEventListener('contextmenu', _onCanvasContextMenu);
        canvas.addEventListener('mousedown', _onCanvasMouseDown);
        canvas.addEventListener('mousemove', _onCanvasMouseMove);
        canvas.addEventListener('mouseup', _onCanvasMouseUp);
        document.addEventListener('keydown', _onKeyDown);
        window.addEventListener('resize', _rerenderWires);
    }

    function _close() {
        const m = document.getElementById('tg-modal');
        if (m) m.remove();
        document.removeEventListener('keydown', _onKeyDown);
        window.removeEventListener('resize', _rerenderWires);
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
        const id = `n${_state.nodeIdCounter++}`;
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
        _selectedNode = id;
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

    function _fitView() {
        const ns = Object.values(_state.nodes);
        if (!ns.length) return;
        const c = document.getElementById('tg-canvas'); if (!c) return;
        const cw = c.clientWidth, ch = c.clientHeight;
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const n of ns) {
            if (n.x - 50 < minX) minX = n.x - 50;
            if (n.y - 20 < minY) minY = n.y - 20;
            if (n.x + 310 > maxX) maxX = n.x + 310;
            if (n.y + 200 > maxY) maxY = n.y + 200;
        }
        const bw = maxX - minX, bh = maxY - minY, pad = 30;
        const scale = Math.min((cw - pad * 2) / bw, (ch - pad * 2) / bh, 1);
        c.style.transform = `translate(${(cw - bw * scale) / 2 - minX * scale}px, ${(ch - bh * scale) / 2 - minY * scale}px) scale(${scale})`;
        c.style.transformOrigin = '0 0';
    }
    TG._fitView = _fitView;

    // ─── Canvas rendering ───

    function _rerenderCanvas() {
        const canvas = document.getElementById('tg-canvas');
        if (!canvas) return;
        for (const el of canvas.querySelectorAll('.tg-node')) el.remove();
        for (const node of Object.values(_state.nodes)) _renderNode(canvas, node);
        _rerenderWires();
        const sp = document.getElementById('tg-state-panel');
        if (sp && sp.style.display !== 'none') _renderStatePanel();
    }

    function _renderNode(canvas, node) {
        const def = NODE_DEFS[node.type];
        if (!def) return;
        const isSel = _selectedNode === node.id;
        const fieldsHtml = def.fields(node.props).replace(/'NODEID'/g, node.id);

        const div = document.createElement('div');
        div.className = 'tg-node';
        div.dataset.nodeId = node.id;
        div.style.cssText = `
            position:absolute; left:${node.x}px; top:${node.y}px; z-index:${isSel ? 10 : 3};
            background:var(--bg-card,#1e1e2e);
            border:2px solid ${isSel ? def.color : 'var(--border,#333)'};
            border-radius:10px; width:${node.w||260}px;
            box-shadow:${isSel ? `0 0 20px ${def.color}33, 0 4px 16px rgba(0,0,0,0.4)` : '0 2px 8px rgba(0,0,0,0.3)'};
            font-size:11px; color:var(--text,#ccc);
            transition:box-shadow 0.15s;
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

        // Sockets
        for (const sock of def.sockets) {
            const dot = document.createElement('div');
            dot.className = 'tg-socket';
            dot.dataset.nodeId = node.id;
            dot.dataset.socketId = sock.id;

            let posStyles = '';
            if (sock.side === 'left') posStyles = `left:-8px;top:50%;transform:translateY(-50%);`;
            else if (sock.side === 'right') posStyles = `right:-8px;top:50%;transform:translateY(-50%);`;
            else if (sock.side === 'bottom') {
                if (sock.id === 'output_yes') posStyles = `bottom:-8px;left:45%;transform:translateX(-50%);`;
                else posStyles = `bottom:-8px;left:55%;transform:translateX(-50%);`;
            }

            dot.style.cssText = `
                position:absolute; ${posStyles}
                width:16px; height:16px; border-radius:50%;
                background:${sock.color || '#888'}; border:3px solid var(--bg-card,#1e1e2e);
                cursor:crosshair; z-index:6;
                box-shadow:0 0 4px rgba(0,0,0,0.5);
            `;
            dot.title = sock.label;
            dot.addEventListener('mousedown', (e) => { e.stopPropagation(); _startWireDrag(node.id, sock.id, e); });
            div.appendChild(dot);
        }

        div.addEventListener('mousedown', (e) => {
            if (e.target.closest('.tg-socket') || e.target.closest('select') || e.target.closest('input') || e.target.closest('textarea')) return;
            _selectedNode = node.id;
            _rerenderCanvas();
            _startNodeDrag(node.id, e);
        });

        div.addEventListener('dblclick', () => {
            _selectedNode = node.id;
            _rerenderCanvas();
        });

        canvas.appendChild(div);
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

    function _getSocketCenter(el) {
        if (!el) return null;
        const canvas = document.getElementById('tg-canvas');
        if (!canvas) return null;
        const er = el.getBoundingClientRect();
        const cr = canvas.getBoundingClientRect();
        return { x: er.left - cr.left + er.width / 2, y: er.top - cr.top + er.height / 2 };
    }

    function _drawWire(svg, wire) {
        const fromEl = _getSocketEl(wire.from[0], wire.from[1]);
        const toEl = _getSocketEl(wire.to[0], wire.to[1]);
        const fp = fromEl ? _getSocketCenter(fromEl) : null;
        const tp = toEl ? _getSocketCenter(toEl) : null;
        if (!fp || !tp) return;
        const dx = Math.abs(tp.x - fp.x) * 0.6;
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', `M${fp.x},${fp.y} C${fp.x+dx},${fp.y} ${tp.x-dx},${tp.y} ${tp.x},${tp.y}`);
        path.setAttribute('stroke', '#58a6ff');
        path.setAttribute('stroke-width', '2.5');
        path.setAttribute('fill', 'none');
        path.setAttribute('opacity', '0.8');
        svg.appendChild(path);
    }

    function _drawTempWire(svg) {
        const fromEl = _getSocketEl(_dragWire.from[0], _dragWire.from[1]);
        const fp = fromEl ? _getSocketCenter(fromEl) : null;
        if (!fp) return;
        const dx = Math.abs(_dragWire.mx - fp.x) * 0.6;
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', `M${fp.x},${fp.y} C${fp.x+dx},${fp.y} ${_dragWire.mx-dx},${_dragWire.my} ${_dragWire.mx},${_dragWire.my}`);
        path.setAttribute('stroke', '#e3b341');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke-dasharray', '6,4');
        path.setAttribute('opacity', '0.9');
        svg.appendChild(path);
    }

    // ─── Drag handlers ───

    function _startWireDrag(nid, sid, e) {
        const canvas = document.getElementById('tg-canvas');
        if (!canvas) return;
        const r = canvas.getBoundingClientRect();
        _dragWire = { from: [nid, sid], mx: e.clientX - r.left, my: e.clientY - r.top };
        e.preventDefault();
    }

    function _startNodeDrag(nid, e) {
        const n = _state.nodes[nid];
        if (!n) return;
        _dragNode = { nid, sx: n.x, sy: n.y, mx: e.clientX, my: e.clientY };
        const el = e.currentTarget;
        el.style.zIndex = _nextZ++;
        e.preventDefault();
    }

    function _onCanvasMouseDown(e) {
        _hideContextMenu();
        if (e.target.id === 'tg-canvas' || e.target.id === 'tg-svg') {
            _selectedNode = null;
            _rerenderCanvas();
        }
    }

    function _onCanvasMouseMove(e) {
        const canvas = document.getElementById('tg-canvas');
        if (!canvas) return;
        const r = canvas.getBoundingClientRect();
        const mx = e.clientX - r.left, my = e.clientY - r.top;

        if (_dragWire) {
            _dragWire.mx = mx; _dragWire.my = my;
            _rerenderWires(); return;
        }
        if (_dragNode) {
            const n = _state.nodes[_dragNode.nid];
            if (n) {
                n.x = _dragNode.sx + e.clientX - _dragNode.mx;
                n.y = _dragNode.sy + e.clientY - _dragNode.my;
                const el = document.querySelector(`.tg-node[data-node-id="${_dragNode.nid}"]`);
                if (el) { el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; }
                _rerenderWires();
            }
        }
    }

    function _onCanvasMouseUp(e) {
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
                    const wid = `w${_state.wireIdCounter++}`;
                    _state.wires[wid] = { id: wid, from: [snid, ssid], to: [tnid, tsid] };
                }
            }
            _dragWire = null; _rerenderWires();
        }
        _dragNode = null;
    }

    function _onKeyDown(e) {
        const tag = (e.target?.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target?.isContentEditable) return;
        if ((e.key === 'Delete' || e.key === 'Backspace') && _selectedNode) {
            _deleteNode(_selectedNode); e.preventDefault();
        }
        if (e.key === 'Escape') { _hideContextMenu(); _close(); }
    }

    // ─── Context menu (right-click) ───

    function _onCanvasContextMenu(e) {
        e.preventDefault();
        if (e.target.id !== 'tg-canvas' && e.target.id !== 'tg-svg') return;
        const canvas = document.getElementById('tg-canvas');
        if (!canvas) return;
        const r = canvas.getBoundingClientRect();
        const cx = e.clientX - r.left, cy = e.clientY - r.top;

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

        _renderContextList(list, cx, cy);

        document.body.appendChild(menu);
        setTimeout(() => search.focus(), 50);
    }

    function _renderContextList(list, cx, cy) {
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
                <div class="tg-cm-item" data-type=${i.type} style="padding:6px 8px;border-radius:4px;cursor:pointer;display:flex;flex-direction:column;gap:1px;border-left:3px solid ${edgeColor(i.type)};" @mouseover=${(e) => e.currentTarget.style.background='var(--bg-hover,#2a2a3e)'} @mouseout=${(e) => e.currentTarget.style.background='transparent'} @mousedown=${(e) => { e.stopPropagation(); TriggerGraph._addNode(i.type, cx, cy); TriggerGraph._hideContextMenu(); }}>
                    <span style="font-size:12px;font-weight:500;">${i.label}</span>
                    <span style="font-size:9px;color:var(--text-muted);">${i.desc}</span>
                </div>
            `) : triggerGraphTag`<div style="padding:8px;color:var(--text-muted);font-size:11px;text-align:center;">No matches</div>`}
        `, list);
    }

    function _filterContextMenu() {
        _contextSearch = document.getElementById('tg-cm-search')?.value || '';
        const list = document.getElementById('tg-cm-list');
        if (list) _renderContextList(list, 0, 0);
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
        _selectedNode = null; _rerenderCanvas();
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

    /** Convert an engine behavior array into a behavior-mode graph. */
    TG.behaviorsToGraph = function(behaviors) {
        const list = Array.isArray(behaviors) ? behaviors : [];
        // Highest priority first = stacked top-to-bottom (matches compileToBehaviors
        // deriving priority from Y position).
        const sorted = [...list].sort((a, b) => (b.priority ?? 1) - (a.priority ?? 1));
        const nodes = [];
        const wires = [];
        let nodeId = 0;
        sorted.forEach((b, bi) => {
            const sortKey = (b.priority ?? 1);
            const bnode = `n${nodeId++}`;
            nodes.push({
                id: bnode, type: 'behavior', x: 50, y: 40 + bi * 180,
                props: { trigger: b.trigger || 'on_tick', priority: sortKey, interval: b.interval ?? 1 }
            });
            let conditions = b.conditions || {};
            if (conditions && typeof conditions === 'object' && !Array.isArray(conditions) && (conditions.operator || (conditions.type && conditions.type !== 'none'))) {
                conditions = conditions.conditions && conditions.conditions.length ? conditions.conditions : (conditions.type ? [conditions] : []);
            }
            if (!Array.isArray(conditions)) conditions = [];
            const actions = b.actions || [];
            let from = [bnode, 'output'];
            let y = 96 + bi * 180;

            if (conditions.length > 0) {
                const numConds = conditions.length;
                for (let ci = 0; ci < numConds; ci++) {
                    const cnode = `n${nodeId++}`;
                    nodes.push({ id: cnode, type: 'condition', x: 300, y: y, props: _conditionToGraphProps(conditions[ci]) });
                    wires.push({ id: `w${wires.length}`, from, to: [cnode, 'input'] });
                    from = [cnode, 'output_yes'];
                    y += 120;
                }
            }
            for (let i = 0; i < actions.length; i++) {
                const act = actions[i];
                const anode = `n${nodeId++}`;
                const isState = act.type === 'set_npc_state';
                nodes.push({
                    id: anode, type: isState ? 'state' : 'action',
                    x: 300 + (conditions.length ? 220 : 0),
                    y: y + i * 120,
                    props: isState ? { state: act.state || '' } : (() => {
                        const flat = Object.fromEntries(Object.entries(act).filter(([k]) => k !== 'type'));
                        return { action_type: act.type || 'message', ...flat };
                    })()
                });
                wires.push({ id: `w${wires.length}`, from, to: [anode, 'input'] });
                if (actions.length > 1 && i < actions.length - 1) from = [anode, 'output'];
            }
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
        if (traced.fail_message) result.fail_message = traced.fail_message;
        return result;
    };

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
            const eff = { type: node.props.effect_type || 'message', params: { ...node.props } };
            delete eff.params.effect_type;
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
