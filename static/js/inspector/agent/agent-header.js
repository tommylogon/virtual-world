/**
 * InspectorAgentHeader — header, status row, emotion selector, vitals
 * Extracted from agent-view.js for modularity.
 */

window.InspectorAgentHeader = (() => {
    const H = {};

    const EMOTION_ICONS = { happy: '😊', sad: '😢', angry: '😠', afraid: '😨', surprised: '😲', disgusted: '🤢', neutral: '😐' };
    const STAT_LABELS = { STR: '\u{1F4AA} Strength', DEX: '\u{1F938} Dexterity', CON: '\u{1F6E1}\uFE0F Constitution', INT: '\u{1F9E0} Intelligence', WIS: '\u{1F441}\uFE0F Wisdom', CHA: '\u{1F4AC} Charisma' };
    const SKILL_LIST = ['Athletics', 'Acrobatics', 'Stealth', 'Perception', 'Investigation', 'Survival', 'Persuasion', 'Performance', 'Medicine', 'Arcana', 'Intimidation', 'Lockpicking'];

    const esc = InspectorHelpers.esc;

    function vitalBarColor(vitalName, value) {
        return window.VitalColor.bar({ [vitalName]: value }, vitalName);
    }

    H.renderAgentHeader = function(agentName, player, color, characterNode) {
        const tick = worldState.tick;
        const nodeId = characterNode ? characterNode[0] : '';
        const escapedNodeId = nodeId.replace(/'/g, "\\'");
        return `<div class="inspector-header">
            <span class="inspector-type-badge" style="background:${color}">🧍 Agent</span>
            <div style="flex:1;display:flex;flex-direction:column;">
                <h2 style="margin:0;font-size:16px;"><input type="text" value="${agentName}" onchange="ApiClient.updateCharacter('${agentName.replace(/'/g, "\\'")}',{name:this.value}).then(()=>worldState.fetch())" style="font-size:1em;background:transparent;border:1px solid var(--border);color:inherit;width:100%;"></h2>
                ${nodeId ? `<div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                    <div style="display:flex;gap:2px;align-items:center;">
                        <input type="text" value="${escapedNodeId}" onchange="window.InspectorHelpers.renameNode('${escapedNodeId}',this.value)" style="font-size:10px;padding:1px 4px;background:transparent;border:1px solid transparent;color:var(--text-muted);width:100%;cursor:text;" title="Change node ID (lowercase, no spaces)">
                        <button class="btn btn-sm btn-ghost" onclick="InspectorHelpers.syncIdFromName('${escapedNodeId}','${agentName}')" title="Sync ID from name">🔄</button>
                    </div>
                </div>` : ''}
            </div>
            <span style="font-size:10px;color:var(--text-muted);margin-right:6px;">tick ${tick}</span>
            <button class="btn btn-sm btn-ghost" onclick="hideInspectorPanel()">✕</button>
        </div>`;
    };

    H.renderStatusRow = function(agentName, player, color, isAuto, escName) {
        const roomOptions = Object.keys(worldState.areas || {}).map(areaName =>
            `<option value="${areaName}" ${player.current_area === areaName ? 'selected' : ''}>${areaName}</option>`
        ).join('');
        const condColors = {
            dead: 'var(--red)', unconscious: '#e65100', paralysed: '#555',
            stunned: '#ab47bc', prone: '#8d6e63', busy: '#9e9d24',
            grappled: '#d50000', restrained: '#b71c1c', exhausted: '#ff6f00',
            sick: '#ff6f00', poisoned: '#00c853', blind: '#37474f', deaf: '#455a64',
            mute: '#546e7a', frightened: '#7b1fa2', charmed: '#f06292', awake: 'var(--green)'
        };
        const conds = (player.conditions && typeof player.conditions === 'object' && !Array.isArray(player.conditions)) ? player.conditions : {};
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
                    bits.push(`per tick: <b>${Object.entries(inst.periodic).map(([k, v]) => `${k} ${v > 0 ? '+' : ''}${v}`).join(', ')}</b>`);
                }
                if (inst.ends_on && inst.ends_on.length) bits.push(`ends on: <b>${inst.ends_on.join(', ')}</b>`);
                return `<div style="padding:2px 4px;border-left:2px solid ${color};color:var(--text-dim);display:flex;gap:8px;flex-wrap:wrap;font-size:10px;">${bits.join(' ')}</div>`;
            }).join('');
            return `<span style="position:relative;display:inline-block;font-size:9px;padding:1px 5px;border-radius:3px;background:${color}22;color:${color};border:1px solid ${color};cursor:pointer;" onclick="const pop=this.querySelector('.cond-pop'); pop.style.display = pop.style.display==='block'?'none':'block';">${label} ▾<div class="cond-pop" style="display:none;position:absolute;top:100%;left:0;z-index:99;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;padding:4px;min-width:220px;box-shadow:0 4px 12px rgba(0,0,0,0.4);">${cards}<div style="border-top:1px solid var(--border);margin-top:4px;padding-top:3px;"><span style="cursor:pointer;color:var(--red);font-size:10px;" onclick="event.stopPropagation();InspectorAgentView._removeCondition('${escName}','${cid}')">✕ Clear ${cid}</span></div></div></span>`;
        }).join(' ');

        const mode = events.getControlMode(agentName);
        const modeMeta = {
            human: { label: '👤 Human', bg: 'var(--accent)', fg: '#000', bd: 'var(--accent-dim)' },
            llm:   { label: '🤖 LLM',   bg: 'var(--bg-input)', fg: 'var(--text)', bd: 'var(--border)' },
            npc:   { label: '👾 NPC',   bg: 'var(--bg-input)', fg: 'var(--text-muted)', bd: 'var(--border)' }
        }[mode];
        return `<div style="display:flex;align-items:center;gap:8px;padding:6px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);font-size:11px;flex-wrap:wrap;">
            <span>📍</span>
            <select id="player-room" name="area" onchange="ApiClient.updateCharacter('${escName}',{current_area:this.value}).then(()=>worldState.fetch())" style="font-size:10px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:1px 4px;max-width:100px;">
                ${roomOptions}
            </select>
            <span title="Most significant condition (derived from conditions)" style="font-size:10px;background:${player.state === 'dead' ? 'var(--red)' : 'var(--accent-dim)'};color:${player.state === 'dead' ? '#fff' : '#000'};border-radius:4px;padding:2px 8px;font-weight:600;border:1px solid var(--border);">${player.state}</span>
            ${condBadges}
            <button class="btn btn-sm" onclick="InspectorAgentView._openConditionEditor('${escName}')" title="Add a specific condition (blind, poisoned, unconscious...) with a duration, source, or level" style="font-size:10px;">➕ Add Condition</button>
            <span style="flex:1;"></span>
            <span onclick="events.cycleControlMode('${escName}')" title="Click to cycle control mode: Human → LLM → NPC" style="cursor:pointer;padding:2px 8px;border-radius:4px;font-weight:600;font-size:10px;background:${modeMeta.bg};color:${modeMeta.fg};border:1px solid ${modeMeta.bd};">${modeMeta.label}</span>
        </div>`;
    };

    H.renderEmotionSelector = function(agentName, player, escName) {
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

    H.renderVitals = function(player, agentName) {
        const vitals = player.vitals || {};
        const escAgent = (agentName || '').replace(/'/g, "\\'");
        const openModal = (vn) => `openVitalModal('${escAgent}','${vn}')`;

        const renderVital = (vitalName) => {
            if (vitals[vitalName] === undefined) return '';
            const value = vitalName === 'Temperature' ? Math.round(vitals[vitalName]) : vitals[vitalName];
            const max = vitalName === 'HP' ? (vitals.Max_HP || 100) : (vitalName === 'Temperature' ? 45 : (vitalName === 'Mana' ? (vitals.Max_Mana || 100) : 100));
            const percentage = vitalName === 'Temperature'
                ? Math.max(0, Math.min(100, ((vitals[vitalName] - 25) / 20) * 100))
                : Math.max(0, Math.min(100, (value / max) * 100));
            const barColor = vitalBarColor(vitalName, vitals[vitalName]);
            const suffix = vitalName === 'Temperature' ? '°C' : '';
            // Full hover: value + what the vital does + human natural language
            // (task-129). VitalThresholds.hoverText falls back to the raw
            // number line when unavailable.
            const tipText = (window.VitalThresholds?.hoverText?.(vitals, vitalName))
                || `${vitalName}: ${value}/${max}${suffix}`;
            return `<div style="flex:1;min-width:60px;text-align:center;cursor:pointer;" data-tippy-content="${tipText}" onclick="${openModal(vitalName)}">
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

        return `<div style="padding:8px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);">
            <div style="display:flex;gap:12px;">
                <div style="flex:1;"><div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;margin-bottom:2px;">Physical</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${physicalVitals.map(renderVital).join('')}</div></div>
                <div style="flex:1;"><div style="font-size:8px;color:var(--text-muted);text-transform:uppercase;margin-bottom:2px;">Mental</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${mentalVitals.map(renderVital).join('')}</div></div>
            </div>
            ${manaGroup}
        </div>`;
    };

    return H;
})();
