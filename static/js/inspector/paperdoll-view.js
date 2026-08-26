/**
 * InspectorPaperdoll — Paperdoll view and equipment context menus
 * Extracted from inspector.js for modularity.
 */

window.InspectorPaperdoll = (() => {
    const P = {};

    // Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
    // Used only for the small popups/modals/pickers that render into standalone
    // containers (not the shared inspector panel string template).
    const paperdollTag = (strings, ...values) => window.Lit.html(strings, ...values);

    // Grid slot definitions for the paperdoll
    const GRID_SLOTS = [
        { area:'head', slot:'head' },
        { area:'neck', slot:'neck' },
        { area:'larm', slot:'arms' },
        { area:'torso', slot:'torso' },
        { area:'rarm', slot:'arms' },
        { area:'lhand', slot:'hands' },
        { area:'waist', slot:'waist' },
        { area:'rhand', slot:'hands' },
        { area:'hand_l', slot:'hand_left' },
        { area:'legs', slot:'legs' },
        { area:'hand_r', slot:'hand_right' },
        { area:'back', slot:'back' },
        { area:'feet', slot:'feet' },
    ];

    const SLOT_LABELS = { head:'Head', neck:'Neck', arms:'Arms', torso:'Torso', hands:'Hands', legs:'Legs', feet:'Feet', back:'Back', waist:'Waist', hand_left:'L.Held', hand_right:'R.Held', accessory:'Accessory' };

    // Map each paperdoll area to the body regions (engine/body_parts.py) that
    // occupy it, so clicking a spot on the doll inspects that body part.
    const AREA_TO_REGIONS = {
        head: ['head', 'face', 'cheeks', 'lips'],
        neck: ['neck'],
        larm: ['arm_left'],
        torso: ['torso', 'breast_left', 'breast_right', 'nipple_left', 'nipple_right'],
        rarm: ['arm_right'],
        lhand: ['hand_left'],
        waist: ['genitals', 'balls'],
        rhand: ['hand_right'],
        hand_l: ['hand_left'],
        legs: ['leg_left', 'leg_right'],
        hand_r: ['hand_right'],
        back: ['back'],
        feet: ['foot_left', 'foot_right'],
    };

    /**
     * Build the paperdoll (equipment) HTML content — shown at the top of the
     * Inventory tab. No outer data-tab wrapper: the caller hosts it.
     * @param {string} agentName - Character name
     * @param {object} player - Player data from worldState
     * @param {function} esc - HTML escaping function for attribute values
     * @param {string} escName - HTML-escaped agent name (single quotes escaped)
     * @returns {string} HTML for the paperdoll block
     */
    P.renderPaperdollEquipmentHtml = function(agentName, player, esc, escName) {
        let html = '';
        const equipped = player.equipped || {};
        const carryWeight = parseFloat(player.current_carry_weight) || 0;
        const carryCapacity = parseFloat(player.max_carry_capacity) || 100;
        const carryRatio = carryCapacity > 0 ? Math.min(carryWeight / carryCapacity, 1) : 0;
        const carryPercent = (carryRatio * 100).toFixed(0);
        let carryColor = 'var(--green)';
        if (carryRatio >= 0.8) carryColor = 'var(--red)';
        else if (carryRatio >= 0.5) carryColor = 'var(--yellow)';
        html += `<div class="inspector-section"><h3>🧠 Equipment</h3>
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">
                ⚖️ Carry Load: <strong>${carryWeight.toFixed(1)} / ${carryCapacity.toFixed(1)} kg</strong> (${carryPercent}%)
            </div>
            <div style="width:100%;height:8px;background:var(--bg-inset);border-radius:4px;overflow:hidden;margin-bottom:6px;">
                <div style="width:${carryPercent}%;height:100%;background:${carryColor};border-radius:4px;transition:width 0.2s;"></div>
            </div>
            <div class="paperdoll">`;

        const nameForNode = (id) => (worldState.getNode(id)?.name || id);
        const playerConditions = player.conditions || {};
const regionName = (regionId) => (player.body_region_names?.[regionId] || regionId.replace(/_/g, ' '));
        const regionStatus = (regionId) => {
            const bs = player.body_state?.[regionId] || {};
            const injuredInstances = (playerConditions.injured || []).filter(i => i.body_part === regionId);
            const bleedingInstances = (playerConditions.bleeding || []).filter(i => i.body_part === regionId);
            const exposed = player.region_exposed?.[regionId] !== false;
            return {
                sensitivity: parseFloat(bs.sensitivity) ?? 0,
                injured: injuredInstances,
                bleeding: bleedingInstances,
                exposed,
            };
        };
        for (const gs of GRID_SLOTS) {
            const rawStack = equipped[gs.slot] || [];
            const realIds = rawStack.filter(i => i && !String(i).startsWith('__'));
            const filled = realIds.length > 0;
            const names = realIds.map(nameForNode);
            const outerName = filled ? names[names.length - 1] : null;
            const innerNames = filled ? names.slice(0, -1) : [];
            const outerId = filled ? realIds[realIds.length - 1] : null;
            const outerNode = outerId ? worldState.getNodeByIdentifier(outerId) : null;
            const slotClick = filled ? `InspectorPaperdoll.showSlotModal('${escName}','${gs.slot}')` : '';
            const regions = AREA_TO_REGIONS[gs.area] || [];
            const regionData = regions.map(r => ({ id: r, ...regionStatus(r) }));
            const regionBadges = regionData.filter(r => r.injured.length > 0 || r.bleeding.length > 0);
            const regionBadgeHtml = regionBadges.length > 0
                ? `<div class="paperdoll-body-badge" title="${esc(regionBadges.map(r => (r.bleeding.length ? '🩸' : '🤕') + ' ' + regionName(r.id)).join(', '))}">${regionBadges.length > 1 ? regionBadges.length : (regionBadges[0].bleeding.length ? '🩸' : '🤕')}</div>`
                : '';
            html += `<div class="paperdoll-slot${filled ? ' filled' : ''}" data-area="${gs.area}"${filled ? ` onclick="${slotClick}" oncontextmenu="InspectorPaperdoll.showPaperdollContextMenu(event,'${escName}','${gs.slot}')"` : ''}>
                <div class="paperdoll-slot-label">${SLOT_LABELS[gs.slot] || gs.slot}</div>
                <div class="paperdoll-body-btn" onclick="event.stopPropagation();InspectorPaperdoll.showBodyRegionModal('${escName}','${gs.area}')" title="Inspect body regions">🩺</div>
                ${regionBadgeHtml}`;
            if (filled) {
                html += `<div class="paperdoll-slot-item">${esc(outerName)}</div>`;
                if (innerNames.length > 0) {
                    const visibleInner = innerNames.slice(-2);
                    const hiddenCount = innerNames.length - visibleInner.length;
                    visibleInner.forEach(name => {
                        html += `<div style="font-size:7px;color:var(--text-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:85%;line-height:1.3;">↳ ${esc(name)}</div>`;
                    });
                    const innerData = JSON.stringify(realIds.slice(0, -1)).replace(/'/g, '&#39;');
                    const badgeText = hiddenCount > 0 ? `+${hiddenCount} more` : '📋 layers';
                    html += `<div class="paperdoll-slot-stack-badge" onclick="event.stopPropagation();InspectorPaperdoll.showStackPopup(this,'${escName}','${gs.slot}')" data-inner='${innerData}'>${badgeText}</div>`;
                }
            } else {
                html += `<div class="paperdoll-slot-empty">—</div>`;
            }
            html += `<div class="paperdoll-slot-actions">
                <button class="btn btn-sm btn-blue" onclick="InspectorPaperdoll.showEquipPicker('${escName}','${gs.slot}')" title="Equip ${SLOT_LABELS[gs.slot]}">+</button>
                ${filled ? `<button class="btn btn-sm" onclick="runAction('unequip ${gs.slot}', '${escName}')" title="Unequip">✕</button>` : ''}
            </div></div>`;
        }
        html += `</div>`;  // end paperdoll

        // Accessory slots
        const accStack = equipped.accessory || [];
        const accItems = accStack.filter(i => i && !String(i).startsWith('__'));
        if (accItems.length > 0) {
            html += `<div class="paperdoll-accessory">`;
            html += `<div style="font-size:8px;font-weight:600;text-transform:uppercase;color:var(--text-dim);margin-bottom:4px;cursor:pointer;text-align:center;" onclick="InspectorPaperdoll.showSlotModal('${escName}','accessory')">Accessories (${accItems.length})</div>`;
            accItems.forEach(item => {
                html += `<div class="paperdoll-accessory-item">
                    <span style="font-size:9px;cursor:pointer;" onclick="InspectorPaperdoll.showSlotModal('${escName}','accessory')">${esc(item)}</span>
                    <button class="btn btn-sm" onclick="event.stopPropagation();runAction('unequip ${item}', '${escName}')" title="Unequip" style="font-size:7px;padding:0 4px;">✕</button>
                </div>`;
            });
            html += `</div>`;
        } else {
            html += `<div style="font-size:8px;color:var(--text-dim);margin-top:4px;text-align:center;">Accessories: none</div>`;
        }
        // Equip from inventory button
        html += `<button class="btn btn-sm btn-blue" onclick="InspectorPaperdoll.showEquipPicker('${escName}','all')" style="width:100%;margin-top:6px;font-size:9px;">+ Equip from Inventory</button>`;
        // Equipment narrative display
        const equipNarrative = player.equipment_narrative || '';
        if (equipNarrative) {
            html += `<div style="margin-top:6px;font-size:10px;color:var(--text-dim);font-style:italic;padding:6px 8px;background:var(--bg-inset);border-radius:4px;">${esc(equipNarrative)}</div>`;
        }
        html += `</div>`;
        return html;
    };

    /**
     * Show a popup with inner layers for a stacked equipment slot
     * @param {HTMLElement} badgeEl - The badge element that was clicked
     * @param {string} charName - Character name
     * @param {string} slot - Equipment slot name
     */
    P.showStackPopup = function(badgeEl, charName, slot) {
        const innerIds = JSON.parse(badgeEl.dataset.inner);
        const getName = (id) => (worldState.getNodeByIdentifier(id)?.name || id);
        const existing = document.querySelector('.paperdoll-stack-popup');
        if (existing) existing.remove();

        const rows = innerIds.map((id) => {
            const itemName = getName(id);
            return paperdollTag`<div style="display:flex;justify-content:space-between;align-items:center;padding:2px 0;border-bottom:1px solid var(--border);">
                <span style="font-size:11px;">${itemName}</span>
                <button class="btn btn-sm" @click=${() => runAction(`unequip ${itemName.replace(/'/g, "\\'")}`, charName).then(() => document.querySelector('.paperdoll-stack-popup')?.remove())} style="font-size:8px;padding:1px 6px;color:var(--red);" title="Unequip">✕</button>
            </div>`;
        });

        const popup = document.createElement('div');
        popup.className = 'paperdoll-stack-popup';
        window.Lit.render(paperdollTag`
            <div style="font-weight:600;margin-bottom:4px;font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;">${slot} — inner layers</div>
            ${rows}
        `, popup);
        document.body.appendChild(popup);

        const rect = badgeEl.getBoundingClientRect();
        const popupWidth = Math.min(200, window.innerWidth - 16);
        popup.style.width = popupWidth + 'px';
        let left = Math.min(rect.left, window.innerWidth - popupWidth - 8);
        if (left < 8) left = 8;
        popup.style.left = left + 'px';
        popup.style.top = (rect.bottom + 4) + 'px';

        const dismiss = (e) => {
            if (!popup.contains(e.target) && e.target !== badgeEl) {
                popup.remove();
                document.removeEventListener('click', dismiss);
            }
        };
        setTimeout(() => document.addEventListener('click', dismiss), 10);
    };

    /**
     * Show a modal with full layer stack details for an equipment slot
     * @param {string} charName - Character name
     * @param {string} slot - Equipment slot name
     */
    P.showSlotModal = async function(charName, slot) {
        const player = worldState.players[charName];
        if (!player) return;
        const stack = player.equipped?.[slot] || [];
        const realIds = stack.filter(i => i && !String(i).startsWith('__'));
        if (realIds.length === 0) {
            toastInfo(`Nothing equipped in ${SLOT_LABELS[slot] || slot}.`);
            return;
        }

        const equipSlots = await worldState.fetchEquipSlots();
        const slotConfig = equipSlots[slot] || { max_depth: 5 };
        const maxDepth = slotConfig.max_depth;
        const maxDepthDisplay = maxDepth === null || maxDepth === undefined ? '∞' : maxDepth;
        const slotLabel = SLOT_LABELS[slot] || slot;

        const getItemBonuses = (nodeProps) => {
            const tags = (nodeProps.tags || []).map(t => String(t).toLowerCase());
            const isArmor = tags.some(t => t === 'armor' || t === 'clothing');
            const isWeapon = tags.includes('weapon');
            const isResistance = tags.includes('resistance');
            return {
                defense: isArmor ? (parseInt(nodeProps.defense) || 0) : 0,
                insulation: parseInt(nodeProps.insulation) || 0,
                damage: isWeapon ? (nodeProps.damage || 0) : 0,
                damage_dice: isWeapon ? (nodeProps.damage_dice || null) : null,
                damage_type: isWeapon ? (nodeProps.damage_type || null) : null,
                resistances: isResistance ? (nodeProps.resistances || {}) : {},
                weight: parseFloat(nodeProps.weight) || 0,
            };
        };

        const formatDamage = (dmg, dice) => {
            if (dice && dice[0] > 0) {
                const flat = dice[2] ? `+${dice[2]}` : '';
                return `${dice[0]}d${dice[1]}${flat}`;
            }
            return dmg ? String(dmg) : '0';
        };

        const layers = realIds.map((id, idx) => {
            const node = worldState.getNodeByIdentifier(id);
            const name = node?.name || id;
            const props = node?.properties || {};
            const bonuses = getItemBonuses(props);
            return { id, name, props, bonuses, depth: idx + 1 };
        });

        const totals = layers.reduce((acc, layer) => {
            acc.defense += layer.bonuses.defense;
            acc.insulation += layer.bonuses.insulation;
            acc.weight += layer.bonuses.weight;
            for (const [dtype, val] of Object.entries(layer.bonuses.resistances)) {
                acc.resistances[dtype] = Math.max(acc.resistances[dtype] || 0, parseInt(val) || 0);
            }
            if (layer.bonuses.damage) {
                const currentBest = acc.bestDamage || { damage: 0, dice: [0, 0, 0] };
                const thisDice = layer.bonuses.damage_dice || [0, 0, parseInt(layer.bonuses.damage) || 0];
                if (thisDice[0] > currentBest.dice[0] || (thisDice[0] === currentBest.dice[0] && thisDice[1] > currentBest.dice[1])) {
                    acc.bestDamage = { damage: layer.bonuses.damage, dice: thisDice, type: layer.bonuses.damage_type };
                }
            }
            return acc;
        }, { defense: 0, insulation: 0, weight: 0, resistances: {}, bestDamage: null });

        const esc = s => String(s || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        const escName = s => String(s || '').replace(/'/g, "\\'");

        let html = `<div style="font-weight:600;font-size:14px;margin-bottom:8px;display:flex;align-items:center;gap:8px;">
            <span>🎽 ${slotLabel}</span>
            <span style="font-size:11px;color:var(--text-dim);font-weight:400;">${realIds.length} / ${maxDepthDisplay}</span>
        </div>`;

        html += `<div style="margin-bottom:12px;">`;
        layers.slice().reverse().forEach((layer, revIdx) => {
            const layerNum = layers.length - revIdx;
            const isOuter = revIdx === 0;
            const isInner = revIdx === layers.length - 1;
            html += `<div style="padding:8px;margin-bottom:6px;background:var(--bg-inset);border-radius:6px;border:1px solid var(--border);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-size:12px;font-weight:500;cursor:pointer;color:var(--accent);" onclick="this.closest('.modal-overlay').remove();VW.inspector.showNode('${esc(layer.id)}')">${esc(layer.name)}</span>
                    <span style="font-size:9px;color:var(--text-dim);">Layer ${layer.depth}/${layers.length}</span>
                </div>
                <div style="font-size:10px;color:var(--text-muted);margin-bottom:6px;">${esc(layer.props.description || '').substring(0, 80)}${(layer.props.description || '').length > 80 ? '...' : ''}</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;font-size:10px;">
                    ${layer.bonuses.defense ? `<span>🛡️ +${layer.bonuses.defense}</span>` : ''}
                    ${layer.bonuses.insulation ? `<span>🌡️ ${layer.bonuses.insulation > 0 ? '+' : ''}${layer.bonuses.insulation}°C</span>` : ''}
                    ${layer.bonuses.damage ? `<span>⚔️ ${formatDamage(layer.bonuses.damage, layer.bonuses.damage_dice)}</span>` : ''}
                    ${layer.bonuses.weight ? `<span>⚖️ ${layer.bonuses.weight.toFixed(1)}kg</span>` : ''}
                    ${Object.entries(layer.bonuses.resistances).map(([k, v]) => `<span>⚡ ${k}: ${v}</span>`).join('')}
                </div>
                <div style="display:flex;gap:4px;margin-top:6px;">
                    <button class="btn btn-sm" onclick="runAction('unequip ${escName(layer.name)}', '${esc(charName)}').then(()=>{this.closest('.modal-overlay')?.remove();worldState.fetch();})" style="font-size:9px;padding:2px 8px;" title="Unequip">✕ Unequip</button>
                    ${!isOuter ? `<button class="btn btn-sm" onclick="InspectorPaperdoll._moveLayer('${esc(charName)}','${slot}',${layer.depth - 1},1);this.closest('.modal-overlay')?.remove();" style="font-size:9px;padding:2px 8px;" title="Move outward">↑</button>` : ''}
                    ${!isInner ? `<button class="btn btn-sm" onclick="InspectorPaperdoll._moveLayer('${esc(charName)}','${slot}',${layer.depth - 1},-1);this.closest('.modal-overlay')?.remove();" style="font-size:9px;padding:2px 8px;" title="Move inward">↓</button>` : ''}
                </div>
            </div>`;
        });
        html += `</div>`;

        html += `<div style="padding:8px;background:var(--bg-inset);border-radius:6px;margin-bottom:12px;font-size:11px;">
            <div style="font-weight:600;margin-bottom:4px;">Totals</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;">
                ${totals.defense ? `<span>🛡️ +${totals.defense} Defense</span>` : ''}
                ${totals.insulation ? `<span>🌡️ ${totals.insulation > 0 ? '+' : ''}${totals.insulation}°C Insulation</span>` : ''}
                ${totals.weight ? `<span>⚖️ ${totals.weight.toFixed(1)}kg Total</span>` : ''}
                ${totals.bestDamage ? `<span>⚔️ ${formatDamage(totals.bestDamage.damage, totals.bestDamage.dice)}${totals.bestDamage.type ? ` ${totals.bestDamage.type}` : ''}</span>` : ''}
                ${Object.entries(totals.resistances).map(([k, v]) => `<span>⚡ ${k}: ${v}</span>`).join('')}
            </div>
        </div>`;

        html += `<div style="display:flex;gap:6px;">
            <button class="btn btn-sm btn-blue" onclick="this.closest('.modal-overlay').remove();InspectorPaperdoll.showEquipPicker('${esc(charName)}','${slot}')" style="flex:1;">+ Equip</button>
            <button class="btn btn-sm" onclick="runAction('unequip ${slot}', '${esc(charName)}').then(()=>{this.closest('.modal-overlay')?.remove();worldState.fetch();})" style="flex:1;color:var(--red);">✕ Unequip All</button>
        </div>`;

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        window.Lit.render(paperdollTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:400px;max-height:80vh;overflow-y:auto;">
            ${window.Lit.unsafeHTML(html)}
            <button class="btn btn-sm btn-ghost" @click=${(e) => e.currentTarget.closest('.modal-overlay').remove()} style="width:100%;margin-top:8px;">Close</button>
        </div>`, modal);
        document.body.appendChild(modal);
    };

    /**
     * Show a modal with body-region status for a paperdoll area
     * @param {string} charName - Character name
     * @param {string} area - Paperdoll area id (maps to AREA_TO_REGIONS)
     */
    P.showBodyRegionModal = function(charName, area) {
        const player = worldState.players[charName];
        if (!player) return;
        const regions = AREA_TO_REGIONS[area] || [];
        if (regions.length === 0) {
            toastInfo('No body regions mapped to that spot.');
            return;
        }
        const playerConditions = player.conditions || {};
        const esc = InspectorHelpers.esc;
        const escName = s => String(s || '').replace(/'/g, "\\'");

        const bodyState = player.body_state || {};
        const regionName = (regionId) => (player.body_region_names?.[regionId] || regionId.replace(/_/g, ' '));
        let html = `<div style="font-weight:600;font-size:14px;margin-bottom:8px;">🩺 ${charName} — Body Regions</div>`;
        for (const regionId of regions) {
            const label = regionName(regionId);
            const bs = bodyState[regionId] || {};
            const injuredInstances = (playerConditions.injured || []).filter(i => i.body_part === regionId);
            const bleedingInstances = (playerConditions.bleeding || []).filter(i => i.body_part === regionId);
            const exposed = player.region_exposed?.[regionId] !== false;
            const sensitivity = bs.sensitivity !== undefined ? parseFloat(bs.sensitivity).toFixed(2) : '—';
            const injuryLevel = bs.injury ?? (injuredInstances.length ? Math.max(...injuredInstances.map(i => i.level || 1)) : null);
            const statusChips = [];
            if (injuredInstances.length) statusChips.push(`<span style="color:var(--yellow);">🤕 Injured Lv${Math.max(...injuredInstances.map(i => i.level || 1))}</span>`);
            if (bleedingInstances.length) statusChips.push(`<span style="color:var(--red);">🩸 Bleeding</span>`);
            if (!exposed) statusChips.push(`<span style="color:var(--text-dim);">🛡️ Covered</span>`);
            if (statusChips.length === 0) statusChips.push(`<span style="color:var(--text-dim);">Healthy</span>`);

            html += `<div style="padding:8px;margin-bottom:6px;background:var(--bg-inset);border-radius:6px;border:1px solid var(--border);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-size:12px;font-weight:500;text-transform:capitalize;">${esc(label)}</span>
                    <span style="font-size:9px;color:var(--text-dim);">sens ${sensitivity}</span>
                </div>
                <div style="font-size:10px;color:var(--text-muted);">
                    Sensitivity: <strong>${sensitivity}</strong> · Injury: <strong>${injuryLevel ?? '—'}</strong>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;font-size:10px;margin-top:4px;">${statusChips.join('')}</div>
            </div>`;
        }

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        window.Lit.render(paperdollTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:360px;max-height:80vh;overflow-y:auto;">
            ${window.Lit.unsafeHTML(html)}
            <button class="btn btn-sm btn-ghost" @click=${(e) => e.currentTarget.closest('.modal-overlay').remove()} style="width:100%;margin-top:8px;">Close</button>
        </div>`, modal);
        document.body.appendChild(modal);
    };

    /**
     * Move a layer up or down in the equipment stack (client-side reorder)
     * @param {string} charName - Character name
     * @param {string} slot - Equipment slot name
     * @param {number} fromIndex - Current index in stack (0-based)
     * @param {number} direction - +1 to move outward, -1 to move inward
     */
    P._moveLayer = function(charName, slot, fromIndex, direction) {
        const player = worldState.players[charName];
        if (!player) return;
        const stack = player.equipped[slot] || [];
        const realIds = stack.filter(i => i && !String(i).startsWith('__'));
        const toIndex = fromIndex + direction;
        if (toIndex < 0 || toIndex >= realIds.length) return;
        const temp = realIds[fromIndex];
        realIds[fromIndex] = realIds[toIndex];
        realIds[toIndex] = temp;
        player.equipped[slot] = realIds;
        worldState.fetch();
    };

    /**
     * Show a picker modal to equip an item from inventory to a slot
     * @param {string} charName - Character name
     * @param {string} slot - Equipment slot name (or 'all')
     */
    P.showEquipPicker = async function(charName, slot) {
        const inventory = worldState.getInventory(charName);
        const equipped = worldState.players[charName]?.equipped || {};
        const equippedIds = new Set();
        for (const stack of Object.values(equipped)) {
            for (const i of stack) if (i && !String(i).startsWith('__')) equippedIds.add(i);
        }
        const equippable = inventory.filter(n => {
            const node = worldState.getNodeByIdentifier(n);
            const slots = node?.properties?.equip_slots || [];
            return slots.includes(slot) && !equippedIds.has(node?.id || n);
        });
        if (equippable.length === 0) {
            toastInfo(`No items in inventory that can be equipped to ${slot}.`);
            return;
        }
        const picker = document.createElement('div');
        picker.className = 'modal-overlay';
        picker.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
        const slotItems = equippable.map(n => paperdollTag`<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid var(--border);cursor:pointer;" @click=${(e) => { e.currentTarget.closest('.modal-overlay').remove(); runAction(`wear ${n}`, charName); }}>
            📦 ${n} <span style="font-size:10px;color:var(--accent);">Equip</span>
        </div>`);
        window.Lit.render(paperdollTag`<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;width:300px;">
            <h3 style="margin:0 0 12px 0;">Equip to ${slot}</h3>
            ${slotItems}
            <button class="btn btn-sm" @click=${(e) => e.currentTarget.closest('.modal-overlay').remove()} style="margin-top:8px;width:100%;">Cancel</button>
        </div>`, picker);
        document.body.appendChild(picker);
    };

    /**
     * Show a context menu for a paperdoll equipment slot
     * @param {Event} event - Right-click event
     * @param {string} charName - Character name
     * @param {string} slot - Equipment slot name
     */
    P.showPaperdollContextMenu = function(event, charName, slot) {
        const esc = InspectorHelpers.esc;
        const player = worldState.players[charName];
        const stack = player?.equipped?.[slot] || [];
        const realIds = stack.filter(i => i && !String(i).startsWith('__'));
        if (realIds.length === 0) return;
        const outerId = realIds[realIds.length - 1];
        const outerNode = worldState.getNodeByIdentifier(outerId);
        const outerName = outerNode?.name || outerId;
        const props = outerNode?.properties || {};
        const isContainer = (props.tags || []).some(t => String(t).toLowerCase() === 'container');
        let items = `<div class="context-menu-header" style="padding:6px 12px;font-size:10px;color:var(--text-dim);border-bottom:1px solid var(--border-light);text-transform:uppercase;letter-spacing:0.5px;">🎽 ${SLOT_LABELS[slot]||slot} · ${esc(outerName)}</div>`;
        const safeId = outerId.replace(/'/g, "\\'");
        items += `<div class="context-menu-item" onclick="VW.inspector.showNode('${safeId}');document.getElementById('context-menu').style.display='none'">🔍 Inspect</div>`;
        if (isContainer) {
            items += `<div class="context-menu-item" onclick="VW.inspector.showNode('${safeId}');document.getElementById('context-menu').style.display='none'">📂 Open Container</div>`;
        }
        items += `<div class="context-menu-item" onclick="runAction('unequip ${slot}', '${charName.replace(/'/g, "\\'")}');document.getElementById('context-menu').style.display='none'">✕ Unequip</div>`;
        // Call the shared context menu display
        if (window.VW?.inspector) {
            window.VW.inspector._showContextMenu(event, items);
        }
    };

    /**
     * Show a context menu for an inventory item
     * @param {Event} event - Right-click event
     * @param {string} charName - Character name
     * @param {string} itemName - Item display name
     * @param {string} itemId - Item node ID
     */
    P.showInventoryContextMenu = function(event, charName, itemName, itemId) {
        const esc = InspectorHelpers.esc;
        const itemNode = worldState.getNodeByIdentifier(itemId);
        const props = itemNode?.properties || {};
        const isEquippable = (props.equip_slots || []).length > 0;
        const isContainer = (props.tags || []).some(t => String(t).toLowerCase() === 'container');
        let items = `<div class="context-menu-header" style="padding:6px 12px;font-size:10px;color:var(--text-dim);border-bottom:1px solid var(--border-light);text-transform:uppercase;letter-spacing:0.5px;">📦 ${esc(itemName)}</div>`;
        items += `<div class="context-menu-item" onclick="VW.inspector.showNode('${itemId.replace(/'/g, "\\'")}');document.getElementById('context-menu').style.display='none'">🔍 Inspect</div>`;
        if (isEquippable) {
            const safeName = itemName.replace(/'/g, "\\'");
            const escChar = charName.replace(/'/g, "\\'");
            items += `<div class="context-menu-item" onclick="runAction('wear ${safeName}', '${escChar}');document.getElementById('context-menu').style.display='none'">🎽 Equip</div>`;
        }
        if (isContainer) {
            items += `<div class="context-menu-item" onclick="VW.inspector.showNode('${itemId.replace(/'/g, "\\'")}');document.getElementById('context-menu').style.display='none'">📂 Open Container</div>`;
        }
        const safeName = itemName.replace(/'/g, "\\'");
        const escCharName = charName.replace(/'/g, "\\'");
        items += `<div class="context-menu-item" onclick="InspectorAgentView._showContainerPicker('${escCharName}','${safeName}','${itemId.replace(/'/g, "\\'")}');document.getElementById('context-menu').style.display='none'">📥 Put in container...</div>`;
        items += `<div class="context-menu-item" onclick="runAction('drop ${safeName}', '${escCharName}');document.getElementById('context-menu').style.display='none'">✕ Drop</div>`;
        if (window.VW?.inspector) {
            window.VW.inspector._showContextMenu(event, items);
        }
    };

    return P;
})();
