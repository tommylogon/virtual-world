"use strict";
/**
 * threat-detector.js - Room threat analysis for character agents
 *
 * Scans the current area for hostile or armed actors, attributes event targets
 * (actor -> target), accounts for observer relationship affinity toward armed
 * or intervening allies, and recognizes disarm/drop/throw/release de-escalation.
 * Returns a formatted threat alert string to prepend to the DECIDE/PLAN prompt,
 * or null if safe.
 *
 * Load AFTER agent/agent-state.js, BEFORE agent-engine.js.
 *
 * @module agent/threat-detector - room threat scan
 * @contributes ThreatDetector: target-, weapon-, and disarm-aware threat scan -> alert string (or null when safe)
 * @powers NPC behaviour, Attack / grapple / disarm - the threat warning prepended to DECIDE and PLAN prompts
 * @relates reads worldState + agent-state; used by agent-engine, plan-manager, and character-state
 * @docs docs/virtualWorld/Characters/NPC Behavior System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const ThreatDetector = (() => {
    'use strict';
    const HOSTILE_TURN_ACTIONS = new Set(['combat', 'attack', 'disarm']);
    const DEESCALATION_ACTIONS = new Set([
        'drop', 'throw', 'release', 'stow', 'unequip', 'holster', 'sheathe',
    ]);
    const WEAPON_KEYWORD_PATTERN = new RegExp('\\b(' +
        [
            'weapon', 'gun', 'pistol', 'revolver', 'rifle', 'shotgun', 'firearm',
            'handgun', 'carbine', 'smg', 'musket', 'blaster',
            'knife', 'knives', 'dagger', 'blade', 'sword', 'rapier', 'saber',
            'sabre', 'katana', 'machete', 'cleaver', 'scalpel', 'shiv', 'razor',
            'axe', 'hatchet', 'tomahawk', 'halberd', 'scythe', 'spear', 'lance',
            'pike', 'harpoon', 'trident',
            'club', 'baton', 'cudgel', 'mace', 'flail', 'morningstar', 'warhammer',
            'sledgehammer', 'hammer', 'crowbar', 'chainsaw', 'bat', 'brass knuckles',
            'bow', 'crossbow', 'grenade', 'bomb', 'dynamite', 'explosive', 'molotov',
            'taser', 'stun gun', 'letter opener', 'letter_opener', 'poison',
        ].join('|') +
        ')\\b', 'i');
    const WEAPON_NODE_TAGS = new Set([
        'weapon', 'firearm', 'ranged', 'melee', 'explosive', 'hazard', 'lethal', 'sharp',
    ]);
    function isHostileTurnAction(action) {
        return typeof action === 'string' && HOSTILE_TURN_ACTIONS.has(action.trim().toLowerCase());
    }
    function isDeescalationAction(action) {
        return typeof action === 'string' && DEESCALATION_ACTIONS.has(action.trim().toLowerCase());
    }
    function _lookupItemNode(itemName, stateData) {
        if (!itemName)
            return null;
        const clean = itemName.trim();
        const ws = typeof worldState !== 'undefined' ? worldState : null;
        if (typeof ws?.getNodeByIdentifier === 'function') {
            try {
                const n = ws.getNodeByIdentifier(clean);
                if (n)
                    return n;
            }
            catch { /* ignore */ }
        }
        if (typeof ws?.getNode === 'function') {
            try {
                const n = ws.getNode(clean) || ws.getNode('item_' + clean.toLowerCase().replace(/\s+/g, '_'));
                if (n)
                    return n;
            }
            catch { /* ignore */ }
        }
        const stateItems = stateData?.items;
        if (stateItems && typeof stateItems === 'object') {
            if (stateItems[clean])
                return stateItems[clean];
            const lower = clean.toLowerCase();
            for (const [k, v] of Object.entries(stateItems)) {
                if (k.toLowerCase() === lower || String(v?.name || '').toLowerCase() === lower) {
                    return v;
                }
            }
        }
        const graphNodes = ws?.graph?.nodes;
        if (graphNodes && typeof graphNodes === 'object') {
            const lower = clean.toLowerCase();
            for (const node of Object.values(graphNodes)) {
                if (node && node.type === 'item' && String(node.name || '').toLowerCase() === lower) {
                    return node;
                }
            }
        }
        return null;
    }
    function isWeaponOrHazard(itemName, stateData) {
        if (typeof itemName !== 'string' || !itemName.trim())
            return false;
        const normalized = itemName.trim().replace(/_/g, ' ');
        if (WEAPON_KEYWORD_PATTERN.test(normalized) || WEAPON_KEYWORD_PATTERN.test(itemName.trim())) {
            return true;
        }
        const node = _lookupItemNode(itemName, stateData);
        const props = node?.properties || node;
        if (props && typeof props === 'object') {
            if (props.damage || props.action === 'attack')
                return true;
            const rawTags = props.tags;
            const tags = Array.isArray(rawTags)
                ? rawTags.map((t) => String(t).trim().toLowerCase())
                : (typeof rawTags === 'string' ? rawTags.split(',').map((t) => t.trim().toLowerCase()) : []);
            if (tags.some(t => WEAPON_NODE_TAGS.has(t)))
                return true;
        }
        return false;
    }
    function resolveEventTarget(turnEvent, knownNames) {
        if (!turnEvent)
            return null;
        if (typeof turnEvent.target === 'string' && turnEvent.target.trim()) {
            return turnEvent.target.trim();
        }
        const desc = typeof turnEvent.description === 'string' ? turnEvent.description.trim() : '';
        if (!desc)
            return null;
        const actor = String(turnEvent.actor || '').trim();
        if (Array.isArray(knownNames) && knownNames.length > 0) {
            const candidates = knownNames
                .map(n => String(n || '').trim())
                .filter(n => n && n.toLowerCase() !== actor.toLowerCase())
                .sort((a, b) => b.length - a.length);
            for (const candidate of candidates) {
                const escaped = candidate.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const re = new RegExp(`\\b${escaped}\\b`, 'i');
                if (re.test(desc)) {
                    return candidate;
                }
            }
        }
        const patterns = [
            /\b(?:disarmed|disarm|tried to disarm)\b.+?\bfrom\s+([A-Z][a-zA-Z0-9_-]*(?:\s+[A-Z][a-zA-Z0-9_-]*)?)/,
            /\b(?:attacks|cuts|punches|lunges at|strikes|hits|shoots|stabs|slashes|grabs|disarms|threatens|aims at)\s+([A-Z][a-zA-Z0-9_-]*(?:\s+[A-Z][a-zA-Z0-9_-]*)?)/,
            /\b(?:swings|lunges|fires|shoots|throws|stabs|slashes|aims)\b.+?\b(?:at|toward|against)\s+([A-Z][a-zA-Z0-9_-]*(?:\s+[A-Z][a-zA-Z0-9_-]*)?)/,
            /\bused\b.+?\bon\s+([A-Z][a-zA-Z0-9_-]*(?:\s+[A-Z][a-zA-Z0-9_-]*)?)/,
        ];
        for (const pattern of patterns) {
            const m = desc.match(pattern);
            if (m && m[1] && m[1].toLowerCase() !== actor.toLowerCase()) {
                return m[1].trim();
            }
        }
        return null;
    }
    function _extractDisarmedItem(evt) {
        if (typeof evt.item === 'string' && evt.item.trim())
            return evt.item.trim();
        const desc = String(evt.description || '');
        const m = desc.match(/\b(?:disarmed|disarm)\s+(?:the\s+)?(.+?)\s+from\s+/i);
        return m && m[1] ? m[1].trim() : null;
    }
    function _extractDeescalatedItem(evt) {
        if (typeof evt.item === 'string' && evt.item.trim())
            return evt.item.trim();
        const desc = String(evt.description || '');
        const m = desc.match(/\b(?:dropped|drops|threw|throws|released|releases|stowed|stows|holstered|sheathed|unequipped)\s+(?:the\s+|their\s+|a\s+|an\s+)?([a-zA-Z0-9_ -]+?)(?:\s+(?:on|onto|into|across|to|in|aside|away)\b|[.,!]|$)/i);
        return m && m[1] ? m[1].trim() : null;
    }
    function _isFailedDisarm(evt) {
        if (evt.outcome && String(evt.outcome).toLowerCase() === 'failed')
            return true;
        if (evt.outcome && String(evt.outcome).toLowerCase() === 'fail')
            return true;
        const desc = String(evt.description || '');
        return /\b(?:failed|fail|tried to disarm|keeps their grip|but .*? keeps)\b/i.test(desc);
    }
    function _resolveEquippedItemName(rawId, stateData) {
        const str = String(rawId || '').trim();
        if (!str)
            return '';
        const cleanId = str.startsWith('__multi_slot_') ? str.slice('__multi_slot_'.length) : str;
        if (cleanId.startsWith('__'))
            return '';
        const node = _lookupItemNode(cleanId, stateData);
        if (node && typeof node.name === 'string' && node.name.trim()) {
            return node.name.trim();
        }
        return cleanId
            .replace(/\s*\(two-handed\)$/i, '')
            .replace(/\s*\(part of a full-body suit\)$/i, '')
            .replace(/^item_/, '')
            .replace(/_/g, ' ')
            .trim();
    }
    function _getRawVisibleItems(person, otherPlayer, stateData) {
        const held = [];
        const worn = [];
        const addUnique = (arr, val) => {
            const clean = val.replace(/\s*\(two-handed\)$/i, '').trim();
            if (clean && !arr.some(x => x.toLowerCase() === clean.toLowerCase())) {
                arr.push(clean);
            }
        };
        if (Array.isArray(person.holding)) {
            for (const item of person.holding) {
                if (item)
                    addUnique(held, String(item));
            }
        }
        else if (Array.isArray(otherPlayer?.holding)) {
            for (const item of otherPlayer.holding) {
                if (item)
                    addUnique(held, String(item));
            }
        }
        else {
            const equippedSource = person.equipped ?? otherPlayer?.equipped;
            if (Array.isArray(equippedSource)) {
                for (const item of equippedSource) {
                    const resolved = _resolveEquippedItemName(item, stateData);
                    if (resolved)
                        addUnique(held, resolved);
                }
            }
            else if (equippedSource && typeof equippedSource === 'object') {
                const handSlots = ['hand_left', 'hand_right', 'main_hand', 'off_hand', 'weapon'];
                for (const [slot, val] of Object.entries(equippedSource)) {
                    const list = Array.isArray(val) ? val : (val ? [val] : []);
                    for (const entry of list) {
                        const resolved = _resolveEquippedItemName(entry, stateData);
                        if (!resolved)
                            continue;
                        if (handSlots.includes(slot))
                            addUnique(held, resolved);
                        else
                            addUnique(worn, resolved);
                    }
                }
            }
        }
        const wearingSource = Array.isArray(person.wearing)
            ? person.wearing
            : (Array.isArray(otherPlayer?.wearing) ? otherPlayer.wearing : []);
        for (const item of wearingSource) {
            if (item)
                addUnique(worn, String(item));
        }
        return { held, worn };
    }
    function _checkObserverAffinity(charName, observerPlayer, personName, otherPlayer) {
        const myRel = charName && observerPlayer?.relationships ? observerPlayer.relationships[personName] : undefined;
        const theirRel = charName && otherPlayer?.relationships ? otherPlayer.relationships[charName] : undefined;
        const myCloseness = typeof myRel?.closeness === 'number' ? myRel.closeness : undefined;
        const theirCloseness = typeof theirRel?.closeness === 'number' ? theirRel.closeness : undefined;
        const relLabel = `${myRel?.label || ''} ${theirRel?.label || ''}`.toLowerCase();
        const hasNegativeCloseness = (myCloseness !== undefined && myCloseness < 0) ||
            (theirCloseness !== undefined && theirCloseness < 0);
        const isHostileAffinity = (theirCloseness !== undefined && theirCloseness < -20) ||
            (myCloseness !== undefined && myCloseness < -20) ||
            /\b(enemy|nemesis|hostile|hatred)\b/.test(relLabel);
        const hasPositiveTrust = (myCloseness !== undefined && myCloseness > 0) ||
            (theirCloseness !== undefined && theirCloseness > 0) ||
            /\b(ally|friend|partner|companion|trusted)\b/.test(relLabel);
        const isAlly = !otherPlayer?.traits?.hostile && !hasNegativeCloseness && hasPositiveTrust;
        return { isAlly, isHostileAffinity };
    }
    function evaluateRoom(charName, turnEvents, stateData, observerOverride) {
        const wsData = typeof worldState !== 'undefined' ? worldState.data : undefined;
        const data = stateData || wsData || {};
        const areaPlayers = data.players_in_area || [];
        const allPlayers = data.players || {};
        const events = turnEvents ?? data.turn_events ?? [];
        const observerPlayer = (charName ? allPlayers[charName] : undefined) || observerOverride || undefined;
        const knownNamesSet = new Set();
        if (charName)
            knownNamesSet.add(charName);
        for (const p of areaPlayers) {
            if (p?.name)
                knownNamesSet.add(p.name);
        }
        for (const k of Object.keys(allPlayers)) {
            if (k)
                knownNamesSet.add(k);
        }
        const knownNames = Array.from(knownNamesSet);
        // Pre-pass over turnEvents in chronological order
        const disarmedTargetInfo = new Map();
        const caughtByDisarmer = new Map();
        const actorDeescalations = new Map();
        const actorCalmEvents = new Map();
        const hostileEventsByActor = new Map();
        events.forEach((evt, idx) => {
            if (!evt)
                return;
            const actor = String(evt.actor || '').trim();
            const action = String(evt.action || '').trim().toLowerCase();
            if (!actor || !action)
                return;
            const target = resolveEventTarget(evt, knownNames);
            if (action === 'disarm') {
                const failed = _isFailedDisarm(evt);
                const item = _extractDisarmedItem(evt);
                const desc = String(evt.description || '');
                const caught = !failed && (evt.caught === true || /\bcatching it\b/i.test(desc));
                if (!failed && target) {
                    disarmedTargetInfo.set(target, { index: idx, by: actor, item, caught });
                    if (caught) {
                        caughtByDisarmer.set(actor, { index: idx, item, from: target });
                    }
                }
                const list = hostileEventsByActor.get(actor) || [];
                list.push({
                    index: idx,
                    actor,
                    action,
                    target,
                    item,
                    failedDisarm: failed,
                    description: desc,
                });
                hostileEventsByActor.set(actor, list);
                return;
            }
            if (isDeescalationAction(action)) {
                const item = _extractDeescalatedItem(evt);
                const list = actorDeescalations.get(actor) || [];
                list.push({ index: idx, action, item });
                actorDeescalations.set(actor, list);
                return;
            }
            if (isHostileTurnAction(action)) {
                const list = hostileEventsByActor.get(actor) || [];
                list.push({
                    index: idx,
                    actor,
                    action,
                    target,
                    item: typeof evt.item === 'string' ? evt.item : null,
                    failedDisarm: false,
                    description: String(evt.description || ''),
                });
                hostileEventsByActor.set(actor, list);
                return;
            }
            actorCalmEvents.set(actor, idx);
        });
        const threats = [];
        const threatDetails = [];
        const allyContext = [];
        const deescalated = [];
        const INCAPACITATED_STATES = new Set(['hidden', 'stealthed', 'dead', 'unconscious', 'sleeping']);
        for (const person of areaPlayers) {
            if (!person?.name || String(person.name) === String(charName))
                continue;
            const otherPlayer = allPlayers[person.name] || person;
            if (!otherPlayer)
                continue;
            const pState = String(otherPlayer.state || person.state || '').toLowerCase();
            if (INCAPACITATED_STATES.has(pState))
                continue;
            const hasMet = typeof worldState !== 'undefined' && typeof worldState?.hasMet === 'function'
                ? worldState.hasMet(charName, person.name)
                : true;
            const threatName = hasMet
                ? person.name
                : (otherPlayer.description?.split(/[.,;]/)[0]?.trim() || 'A hostile figure');
            const { isAlly, isHostileAffinity } = _checkObserverAffinity(charName, observerPlayer, person.name, otherPlayer);
            const actorHostile = hostileEventsByActor.get(person.name) || [];
            const attacksOnMe = actorHostile.filter(e => e.target === charName || e.target === null);
            const attacksOnOthers = actorHostile.filter(e => e.action !== 'disarm' && e.target !== null && e.target !== charName);
            const disarmsOnOthers = actorHostile.filter(e => e.action === 'disarm' && e.target !== null && e.target !== charName);
            const lastHostileAttackIdx = [...attacksOnMe, ...attacksOnOthers].reduce((max, e) => Math.max(max, e.index), -1);
            const lastDisarmOtherIdx = disarmsOnOthers.reduce((max, e) => Math.max(max, e.index), -1);
            const disarmInfo = disarmedTargetInfo.get(person.name);
            const deescList = actorDeescalations.get(person.name) || [];
            const lastOwnDeescIdx = deescList.reduce((max, d) => Math.max(max, d.index), -1);
            const lastDeescalateIdx = Math.max(disarmInfo ? disarmInfo.index : -1, lastOwnDeescIdx);
            // Compute visibly held weapons after accounting for any disarm/drop/throw/release this turn
            const { held, worn } = _getRawVisibleItems(person, otherPlayer, data);
            let currentHeld = [...held];
            const caughtInfo = caughtByDisarmer.get(person.name);
            if (caughtInfo?.item && !currentHeld.some(h => h.toLowerCase() === caughtInfo.item.toLowerCase())) {
                currentHeld.push(caughtInfo.item);
            }
            if (disarmInfo && disarmInfo.index >= lastHostileAttackIdx) {
                if (disarmInfo.item) {
                    const disarmedLower = disarmInfo.item.toLowerCase();
                    currentHeld = currentHeld.filter(h => !h.toLowerCase().includes(disarmedLower) && !disarmedLower.includes(h.toLowerCase()));
                }
                else {
                    currentHeld = [];
                }
            }
            for (const deesc of deescList) {
                if (deesc.item) {
                    const dropLower = deesc.item.toLowerCase();
                    currentHeld = currentHeld.filter(h => !h.toLowerCase().includes(dropLower) && !dropLower.includes(h.toLowerCase()));
                }
                else {
                    currentHeld = [];
                }
            }
            const heldWeapons = currentHeld.filter(item => isWeaponOrHazard(item, data));
            const wornWeapons = worn.filter(item => isWeaponOrHazard(item, data));
            const visibleWeapons = [...heldWeapons];
            for (const w of wornWeapons) {
                if (!visibleWeapons.some(v => v.toLowerCase() === w.toLowerCase())) {
                    visibleWeapons.push(w);
                }
            }
            const isArmed = visibleWeapons.length > 0;
            const wasNeutralizedOrDeescalated = lastDeescalateIdx >= 0 && lastDeescalateIdx >= lastHostileAttackIdx;
            // 1. Trusted ally handling: an ally with positive closeness holding a weapon
            //    or disarming/fighting a third-party aggressor is not hostile toward charName.
            const directlyAttackedObserver = attacksOnMe.some(e => e.target === charName);
            if (isAlly && !directlyAttackedObserver) {
                const allyDroppedAfterDisarm = lastOwnDeescIdx >= 0 && lastOwnDeescIdx >= lastDisarmOtherIdx;
                if (disarmsOnOthers.length > 0 && !allyDroppedAfterDisarm) {
                    const lastDisarm = disarmsOnOthers[disarmsOnOthers.length - 1];
                    allyContext.push({
                        name: threatName,
                        rawName: person.name,
                        kind: 'disarmed_aggressor',
                        target: lastDisarm.target,
                        item: lastDisarm.item,
                        weapons: visibleWeapons,
                    });
                }
                else if (isArmed && !allyDroppedAfterDisarm) {
                    allyContext.push({
                        name: threatName,
                        rawName: person.name,
                        kind: 'holding_weapon',
                        weapons: visibleWeapons,
                    });
                }
                else if (attacksOnOthers.length > 0 && !wasNeutralizedOrDeescalated) {
                    const lastDef = attacksOnOthers[attacksOnOthers.length - 1];
                    allyContext.push({
                        name: threatName,
                        rawName: person.name,
                        kind: 'defending',
                        target: lastDef.target,
                        weapons: visibleWeapons,
                    });
                }
                continue;
            }
            // 2. Non-hostile third-party disarm: someone disarming a third party (target !== charName)
            //    without attacking anyone is performing a restraint/intervention action, not attacking charName.
            if (disarmsOnOthers.length > 0 &&
                attacksOnMe.length === 0 &&
                attacksOnOthers.length === 0 &&
                !otherPlayer.traits?.hostile &&
                !isHostileAffinity) {
                const allyDroppedAfterDisarm = lastOwnDeescIdx >= 0 && lastOwnDeescIdx >= lastDisarmOtherIdx;
                if (!allyDroppedAfterDisarm) {
                    const lastDisarm = disarmsOnOthers[disarmsOnOthers.length - 1];
                    allyContext.push({
                        name: threatName,
                        rawName: person.name,
                        kind: 'disarmed_aggressor',
                        target: lastDisarm.target,
                        item: lastDisarm.item,
                        weapons: visibleWeapons,
                    });
                }
                continue;
            }
            // 3. De-escalation: if this actor was disarmed or dropped/threw/released their weapon
            //    at or after their last hostile action and is no longer visibly armed, clear immediate danger.
            if (wasNeutralizedOrDeescalated && !isArmed) {
                deescalated.push(threatName);
                continue;
            }
            // 4. Direct attack (or untargeted attack/disarm) against charName this turn
            if (attacksOnMe.length > 0 && !wasNeutralizedOrDeescalated) {
                threats.push(threatName);
                threatDetails.push({
                    name: threatName,
                    rawName: person.name,
                    reason: 'attacking_you',
                    weapons: visibleWeapons,
                    target: charName,
                });
                continue;
            }
            // 5. Third-party attack against another character in the room
            if (attacksOnOthers.length > 0 && !wasNeutralizedOrDeescalated) {
                const lastOtherAtk = attacksOnOthers[attacksOnOthers.length - 1];
                threats.push(threatName);
                threatDetails.push({
                    name: threatName,
                    rawName: person.name,
                    reason: 'attacking_other',
                    weapons: visibleWeapons,
                    target: lastOtherAtk.target,
                });
                continue;
            }
            // 6. Visibly held weapon/hazard on a non-ally
            if (isArmed) {
                threats.push(threatName);
                threatDetails.push({
                    name: threatName,
                    rawName: person.name,
                    reason: (otherPlayer.traits?.hostile || isHostileAffinity) ? 'armed_hostile' : 'armed',
                    weapons: visibleWeapons,
                });
                continue;
            }
            // 7. Explicitly hostile trait (e.g. slasher/monster), unless unarmed on a calm post-resolution turn
            const explicitlyUnarmed = Array.isArray(person.holding) && person.holding.length === 0;
            const hasOnlyCalmEventsThisTurn = actorCalmEvents.has(person.name) &&
                attacksOnMe.length === 0 &&
                attacksOnOthers.length === 0;
            if (otherPlayer.traits?.hostile) {
                if (explicitlyUnarmed && hasOnlyCalmEventsThisTurn) {
                    deescalated.push(threatName);
                    continue;
                }
                threats.push(threatName);
                threatDetails.push({
                    name: threatName,
                    rawName: person.name,
                    reason: 'trait_hostile',
                    weapons: [],
                });
                continue;
            }
            // 8. Negative closeness alone without a weapon, hostile trait, or violent action
            //    only escalates if the character's current activity is overtly violent.
            const activityText = String(person.activity || otherPlayer.activity || '');
            if (isHostileAffinity && /\b(?:attack|aim|brandish|stab|shoot|strangl|chok)\w*/i.test(activityText)) {
                threats.push(threatName);
                threatDetails.push({
                    name: threatName,
                    rawName: person.name,
                    reason: 'attacking_you',
                    weapons: [],
                    target: charName,
                });
            }
        }
        return { threats, threatDetails, allyContext, deescalated };
    }
    function _formatAllyContextInline(allyContext) {
        if (!allyContext.length)
            return '';
        const parts = allyContext.map(a => {
            if (a.kind === 'disarmed_aggressor') {
                const itemPart = a.item ? ` of ${a.item}` : '';
                const holdPart = a.weapons.length > 0 ? ` and is holding ${a.weapons.join(', ')}` : '';
                return `Your ally ${a.name} disarmed ${a.target || 'the aggressor'}${itemPart}${holdPart} (not hostile toward you).`;
            }
            if (a.kind === 'holding_weapon') {
                return `Your ally ${a.name} is holding ${a.weapons.join(', ')} (not hostile toward you).`;
            }
            const wepPart = a.weapons.length > 0 ? ` with ${a.weapons.join(', ')}` : '';
            return `Your ally ${a.name} is intervening against ${a.target || 'the threat'}${wepPart} (not hostile toward you).`;
        });
        return ' ' + parts.join(' ');
    }
    function getThreats(charName, turnEvents, stateData) {
        return evaluateRoom(charName, turnEvents, stateData).threats;
    }
    function _observerHasWeapon(observer, stateData) {
        if (!observer)
            return false;
        const holding = Array.isArray(observer.holding) ? observer.holding : [];
        const eq = Array.isArray(observer.equipped)
            ? observer.equipped
            : (observer.equipped && typeof observer.equipped === 'object' ? Object.values(observer.equipped) : []);
        const itemsMap = (stateData?.items && typeof stateData.items === 'object') ? stateData.items : {};
        return [...holding, ...eq].some(entry => {
            const label = typeof entry === 'string' ? entry : String(entry?.name || entry?.id || '');
            if (WEAPON_KEYWORD_PATTERN.test(label))
                return true;
            const node = itemsMap[label];
            const tags = Array.isArray(node?.properties?.tags) ? node.properties.tags : [];
            return tags.some((t) => WEAPON_NODE_TAGS.has(String(t).toLowerCase()));
        });
    }
    function buildGradedThreatDirective(observer, threatDetails, stateData, category = 'direct') {
        const traits = (observer?.traits && typeof observer.traits === 'object') ? observer.traits : {};
        const conds = (observer?.conditions && typeof observer.conditions === 'object')
            ? observer.conditions
            : {};
        const flags = (observer?.flags && typeof observer.flags === 'object')
            ? observer.flags
            : {};
        const rels = observer?.relationships || {};
        const isFrozen = Boolean(flags.frozen_by_fear || conds.stunned);
        const isFrightened = Boolean(conds.frightened);
        const isCowardly = Boolean(traits.cowardly || traits.timid || traits.jittery || traits.nervous);
        const isBrave = Boolean(traits.brave || traits.fearless || traits.stoic);
        const isProtective = Boolean(traits.protective);
        const isCalm = Boolean(traits.calm);
        const isHostile = Boolean(traits.hostile);
        const isArmedObserver = _observerHasWeapon(observer, stateData);
        const caresForTarget = threatDetails.some(t => {
            if (!t.target)
                return false;
            const rel = rels[t.target];
            const closeness = typeof rel?.closeness === 'number' ? rel.closeness : 0;
            return closeness >= 40;
        });
        if (isFrozen) {
            return 'SHOCK / HESITATION: Sudden danger locks your muscles for a beat. React honestly to the jolt - hesitate, catch your breath, or drop into cover rather than executing a calm multi-step plan.';
        }
        if (isFrightened || isCowardly) {
            return 'POSTURE [EVADE]: Fear spikes hard. Prioritize cover, fleeing, hiding, or keeping distance unless cornered into self-defense.';
        }
        if (isHostile) {
            return 'POSTURE [CONFRONT]: Hostile tension in the room. Decide on your own terms whether to strike, disarm, intimidate, or reposition.';
        }
        if (isProtective || caresForTarget || (isBrave && isArmedObserver)) {
            const allyHint = caresForTarget ? ' Someone you care about is at risk.' : '';
            return `POSTURE [STAND / INTERVENE]:${allyHint} Stay sharp - weigh stepping in, disarming, shielding them, or calling for help rather than panicking blindly.`;
        }
        if (isCalm || isBrave) {
            const capNote = isArmedObserver ? 'You are armed' : 'You are unarmed';
            return `POSTURE [ASSESS]: ${capNote}. Keep your head clear - weigh de-escalation, keeping watch, taking cover, or stepping back.`;
        }
        if (category === 'armed_posture') {
            return 'POSTURE [WARINESS]: Weapons are out. Stay alert - avoid reckless errands while gauging intent, keeping distance, disarming, or preparing to flee.';
        }
        const capNote = isArmedObserver ? 'You are armed' : 'You are unarmed';
        return `POSTURE [CAUTIOUS]: ${capNote}. Respond naturally to the danger - weigh fleeing, hiding, taking cover, warning others, or intervening if you have leverage.`;
    }
    function getThreatAlert(charName, player, currentArea, turnEvents, stateData) {
        void currentArea;
        const observerPlayer = (player && typeof player === 'object')
            ? player
            : (stateData?.players?.[charName] || null);
        const evalResult = evaluateRoom(charName, turnEvents, stateData, observerPlayer);
        const { threatDetails, allyContext } = evalResult;
        if (threatDetails.length === 0) {
            if (allyContext.length > 0) {
                return `⚠️ THREAT CONTEXT:${_formatAllyContextInline(allyContext)}`;
            }
            return null;
        }
        const directThreats = threatDetails.filter(t => t.reason === 'attacking_you' || t.reason === 'armed_hostile' || t.reason === 'trait_hostile');
        const armedPostureThreats = threatDetails.filter(t => t.reason === 'armed');
        const thirdPartyThreats = threatDetails.filter(t => t.reason === 'attacking_other');
        const allyInline = _formatAllyContextInline(allyContext);
        // Only third-party attacks (aggressor -> bystander, not targeting charName)
        if (directThreats.length === 0 && armedPostureThreats.length === 0 && thirdPartyThreats.length > 0) {
            const clauses = thirdPartyThreats.map(t => {
                const wep = t.weapons.length > 0 ? ` (armed with ${t.weapons.join(', ')})` : '';
                return `${t.name}${wep} is attacking ${t.target}`;
            });
            const targets = Array.from(new Set(thirdPartyThreats.map(t => t.target).filter(Boolean))).join(', ');
            const directive = buildGradedThreatDirective(observerPlayer, threatDetails, stateData, 'third_party');
            return `⚠️ IMMEDIATE DANGER: ${clauses.join('; ')} in this room (targeting ${targets}, not directly attacking you).${allyInline} ${directive}`;
        }
        // Only visibly armed posture (no direct attack yet and not trait_hostile/hostile affinity)
        if (directThreats.length === 0 && thirdPartyThreats.length === 0 && armedPostureThreats.length > 0) {
            const labels = armedPostureThreats.map(t => `${t.name} (holding ${t.weapons.join(', ')})`);
            const verb = labels.length > 1 ? 'are' : 'is';
            const directive = buildGradedThreatDirective(observerPlayer, threatDetails, stateData, 'armed_posture');
            return `⚠️ IMMEDIATE DANGER: ${labels.join(', ')} ${verb} visibly armed in this room.${allyInline} ${directive}`;
        }
        // Direct hostility (or mixed direct + armed/third-party)
        const labels = threatDetails.map(t => {
            const wep = t.weapons.length > 0 ? ` (armed with ${t.weapons.join(', ')})` : '';
            if (t.reason === 'attacking_other' && t.target) {
                return `${t.name}${wep} (attacking ${t.target})`;
            }
            return `${t.name}${wep}`;
        });
        const verb = labels.length > 1 ? 'are' : 'is';
        const directive = buildGradedThreatDirective(observerPlayer, threatDetails, stateData, 'direct');
        return `⚠️ IMMEDIATE DANGER: ${labels.join(', ')} ${verb} in this room and hostile toward you.${allyInline} ${directive}`;
    }
    return {
        getThreatAlert,
        getThreats,
        evaluateRoom,
        buildGradedThreatDirective,
        isHostileTurnAction,
        isDeescalationAction,
        isWeaponOrHazard,
        resolveEventTarget,
    };
})();
window.ThreatDetector = ThreatDetector;
