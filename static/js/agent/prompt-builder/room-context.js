/**
 * prompt-builder/room-context.js — Area/room context assembler.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). The "assembler"
 * that pulls together lighting, items, exits, people, events into the area
 * context string that starts every user message. Exports merge into
 * window.PromptBuilder.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    function buildCharacterPreamble(charName, player) {
        if (!player || !player.personality) return '';
        const fixNewlines = (s) => (s || '').replace(/\\n/g, '\n');
        const personality = fixNewlines(player.personality).trim();
        if (!personality) return '';
        return `You are ${charName}. Personality: ${personality}`;
    }

    function normalizeVisibleItems(raw) {
        if (raw == null) return [];
        if (Array.isArray(raw)) return raw.map(name => String(name).trim()).filter(Boolean);
        const text = String(raw).trim();
        return text ? [text] : [];
    }

    function collectItemsInAreaByNames(areaName, allowedNames) {
        const allowed = new Set(normalizeVisibleItems(allowedNames).map(name => name.toLowerCase()));
        if (!allowed.size) return [];
        return worldState.getItemsInArea(areaName)
            .filter(item => allowed.has(String(item.name || '').toLowerCase()))
            .map(item => item.name);
    }

    function buildBeyondSuffix(state, charName, exitData, targetAreaName, doorNode) {
        const allowChars = !!exitData.allow_see_characters;
        const visibleItems = normalizeVisibleItems(exitData.visible_items);
        if (!allowChars && !visibleItems.length) return '';
        const wayState = exitData.state || 'closed';
        const seeThrough = !!doorNode?.properties?.see_through;
        if (wayState !== 'open' && !seeThrough) return '';

        const parts = [];
        if (allowChars && targetAreaName) {
            const allPlayers = state.players || {};
            Object.entries(allPlayers).forEach(([name, pdata]) => {
                if (name === charName || pdata.current_area !== targetAreaName) return;
                const desc = pdata.description || '';
                const displayName = PromptBuilder.anonymousName(charName, name, desc);
                if (pdata.activity) {
                    parts.push(`${displayName} (${PromptBuilder.describeActivity(pdata.activity)})`);
                } else if (pdata.state && pdata.state !== 'awake') {
                    parts.push(`${displayName} (${pdata.state})`);
                } else {
                    parts.push(displayName);
                }
            });
        }
        if (visibleItems.length && targetAreaName) {
            collectItemsInAreaByNames(targetAreaName, visibleItems).forEach(name => {
                parts.push(`the ${name}`);
            });
        }
        if (!parts.length) return '';
        return ` Beyond you can see: ${parts.join(', ')}.`;
    }

    function resolveAreaNode(areaName) {
        if (!areaName) return null;
        for (const [nodeId, node] of Object.entries(worldState.graph?.nodes || {})) {
            if (node.type === 'area' && (node.name === areaName || nodeId === areaName)) {
                return { id: nodeId, ...node };
            }
        }
        return worldState.getNodeByIdentifier(areaName);
    }

    function getContainedItems(parentItemId) {
        const out = [];
        for (const edge of worldState.graph?.edges || []) {
            if (edge.type === 'in' && edge.target === parentItemId) {
                const node = worldState.getNode(edge.source);
                if (node && node.type === 'item') {
                    out.push({ id: node.id, name: node.name, properties: node.properties });
                }
            }
        }
        return out;
    }

    /**
     * Build the full area context as NAMED PARTS for a character — tick head,
     * personality preamble, appearance, carrying, room lead-in/body, exits,
     * items, people (with inline relationship labels), available actions,
     * witnessed events, and plan. The turn-prompt builders re-order these
     * parts so the state/memory blocks sit at the top (see turn-prompts.js),
     * while `buildRoomContext` assembles them in the new order for standalone
     * use (human turns, narration, lens previews).
     * @param {Object} state - Full world state data
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {Object} currentArea - Current area data object
     * @param {boolean|Object} [includePlanOrOptions=true] - boolean legacy flag, or
     *   `{ includePlan, agentFraming }`. When `agentFraming` is false (area/way/item
     *   lens), omits tick, personality, inventory, and plan — room content only.
     * @returns {Object} Named parts (agentFraming) OR { agentFraming:false, authoringText }
     */
    function buildRoomContextParts(state, charName, player, currentArea, includePlanOrOptions = true) {
        let includePlan = true;
        let agentFraming = true;
        if (typeof includePlanOrOptions === 'object' && includePlanOrOptions !== null) {
            includePlan = includePlanOrOptions.includePlan !== false;
            agentFraming = includePlanOrOptions.agentFraming !== false;
        } else {
            includePlan = includePlanOrOptions !== false;
        }
        const light = currentArea?.ambient_light ?? currentArea?.environment?.light ?? 50;
        const level = PromptBuilder.lightToLevel(light);
        // Check for dark_vision trait
        const traits = player?.traits || {};
        const hasDarkVision = traits.dark_vision === true || traits.darkvision === true;
        // Blind characters are effectively pitch-black regardless of light — their
        // observation is rebuilt from sound/smell/touch, not sight (they aren't told
        // to "pretend"; the visual data is simply not presented to them).
        const isBlind = !!(player?.conditions?.blind);
        let warn = '', items = '';
        const areaItems = currentArea?.name ? worldState.getItemsInArea(currentArea.name) : [];
        const relationMap = PromptBuilder.buildRelationMap(areaItems);
        // Prepend a spatial relation ("on the table is a ...") for items that
        // sit on/under/behind/beside/inside another item in the area.
        const relateItem = (roomItem) => {
            const rel = relationMap[roomItem.id];
            if (rel) return `${rel.prep} the ${rel.anchorName} is ${PromptBuilder.indefiniteArticle(roomItem.name)} ${roomItem.name}`;
            return roomItem.name;
        };
        // Rich item listing — full descriptions in good light (like the backend
        // area narration used to provide), names only in dim/dark conditions.
        // Each item carries a [bracket] of its allowed actions so the agent sees
        // what it can do with it at a glance.
        const itemBracket = (roomItem) => PromptBuilder.formatActionBrackets(PromptBuilder.computeItemActions(roomItem, player));
        const fmtItems = (list, withDescriptions) => {
            if (list.length === 0) return '';
            if (!withDescriptions) return list.map(roomItem => `${relateItem(roomItem)} ${itemBracket(roomItem)}`.trim()).join(', ');
            return list.map(roomItem => {
                const desc = String(roomItem.properties?.description || '').trim();
                const label = relateItem(roomItem);
                const bracket = itemBracket(roomItem);
                const head = bracket ? `${label} ${bracket}` : label;
                return desc ? `- ${head}: ${desc}` : `- ${head}`;
            }).join('\n');
        };
        // Interest-based attention: items matching the character's interest_tags
        // (exact tag +2, keyword-in-name +1) surface first, then everything else,
        // each ordered by weight (bigger = easier to see). Examined/taken items
        // drop off the attention list entirely — their facts live in the
        // investigation notes. Capped at ATTENTION_MAX; no truncation, just a
        // natural trailing line.
        const interestTags = (player?.interest_tags || []).map(tag => String(tag).toLowerCase().trim()).filter(Boolean);
        const discoveredItems = new Set((player?.discovered_items || []).map(name => String(name).toLowerCase().trim()));
        const attentionScore = (roomItem) => {
            const name = String(roomItem.name || '').toLowerCase();
            const itemTags = (roomItem.properties?.tags || []).map(tag => String(tag).toLowerCase().trim());
            let score = 0;
            for (const tag of interestTags) {
                if (itemTags.includes(tag)) score += 2;
                else if (name.includes(tag)) score += 1;
            }
            return score;
        };
        const itemWeight = (roomItem) => parseFloat(roomItem.properties?.weight) || 0;
        const ATTENTION_MAX = 15;
        // Build the attention list from unexamined, non-hidden items.
        const buildAttention = (roomItems, withDescriptions) => {
            const unexamined = roomItems.filter(roomItem => !discoveredItems.has(String(roomItem.name).toLowerCase().trim()));
            if (unexamined.length === 0) return '';
            const byAttention = (a, b) => attentionScore(b) - attentionScore(a) || itemWeight(b) - itemWeight(a);
            const attention = [...unexamined].sort(byAttention).slice(0, ATTENTION_MAX);
            const listLines = fmtItems(attention, withDescriptions);
            const hasMore = unexamined.length > attention.length;
            const trailer = hasMore
                ? 'There are more items around that you can look for.'
                : 'and noting else that catch your attention right now.';
            return `${listLines}\n${trailer}`;
        };
        if (isBlind) {
            warn = '⚠️ BLIND — It is pitch black to you no matter the light. You navigate by sound, smell, and touch. Fumble or search the area to locate things, listen to hear beyond your reach, and moving blind is risky without a cane or a guide.';
            const known = areaItems.filter(roomItem =>
                discoveredItems.has(String(roomItem.name || '').toLowerCase().trim())
                && roomItem.properties?.current_state !== 'hidden'
            );
            items = known.length ? known.map(roomItem => `${relateItem(roomItem)} ${itemBracket(roomItem)}`.trim()).join(', ') : '';
        } else if (hasDarkVision) {
            items = buildAttention(areaItems.filter(roomItem => roomItem.properties?.current_state !== 'hidden'), false);
        } else if (level === 'pitch_black') {
            warn = '⚠️ PITCH BLACK — You cannot see anything. Try to go back to a brighter area or use a light source.';
        } else if (level === 'dim') {
            items = buildAttention(areaItems.filter(roomItem => roomItem.properties?.current_state !== 'hidden' && (roomItem.properties?.weight||1)>=3), false);
            warn = '⚠️ Dim light — only large objects visible. Fine actions limited. Use a light source or move to a brighter area.';
        } else {
            items = buildAttention(areaItems.filter(roomItem => roomItem.properties?.current_state !== 'hidden'), true);
        }
        const exitLines = [];
        const movementSuffix = (doorNode, handle) => {
            if (typeof WayAuthoring !== 'undefined') {
                return WayAuthoring.movementHint(doorNode, handle);
            }
            const req = (doorNode?.properties?.requires || '').toLowerCase();
            if (req === 'crawl') return ` (crawl: go ${handle} auto-crawls)`;
            if (req === 'climb') return ` (climb: climb ${handle})`;
            if (req === 'jump') return ` (jump: jump ${handle})`;
            return '';
        };
        const areaNode = resolveAreaNode(currentArea?.name);
        const areaProps = areaNode?.properties || currentArea?.properties || {};
        const areaTags = (areaProps.tags || []).map(tag => String(tag).toLowerCase().trim());
        const isTransitArea = !!areaProps.transit
            || areaTags.includes('transit')
            || areaTags.includes('passage');
        const atWayId = player?.at_way_id
            || state.players?.[charName]?.at_way_id
            || null;
        const transitRoles = (() => {
            if (!isTransitArea || !atWayId || !currentArea?.exits) return null;
            const visible = Object.entries(currentArea.exits).filter(([, exitData]) => !exitData.hidden);
            if (visible.length < 2) return null;
            const back = visible.find(([, exitData]) => exitData.way_id === atWayId);
            if (!back) return null;
            const forward = visible.filter(([, exitData]) => exitData.way_id !== atWayId);
            if (forward.length !== 1) return null;
            return { backWayId: atWayId, forwardWayId: forward[0][1].way_id };
        })();
        const spatialPositionSuffix = (person) => {
            const pos = person?.spatial_position;
            if (pos?.target_name && pos?.relation) {
                const label = pos.target_name;
                switch (pos.relation) {
                    case 'on': return ` on the ${label}`;
                    case 'under': return ` under the ${label}`;
                    case 'behind': return ` behind the ${label}`;
                    case 'beside': return ` beside the ${label}`;
                    default: return ` at the ${label}`;
                }
            }
            if (!person?.at_way_id || !currentArea?.exits) return '';
            for (const [dir, exitData] of Object.entries(currentArea.exits)) {
                if (exitData.way_id !== person.at_way_id) continue;
                const doorNode = worldState.getNode(person.at_way_id);
                const handle = PromptBuilder.wayHandle({ ...exitData, label: dir }, doorNode, currentArea?.name);
                return ` at the ${handle}`;
            }
            return ' at the door';
        };
        if (currentArea?.exits) {
            for (const [dir, exitData] of Object.entries(currentArea.exits)) {
                if (exitData.hidden) continue;
                const doorNode = worldState.getNode(exitData.way_id);
                let handle = PromptBuilder.wayHandle({ ...exitData, label: dir }, doorNode, currentArea?.name);
                if (transitRoles) {
                    if (exitData.way_id === transitRoles.backWayId) handle = 'back';
                    else if (exitData.way_id === transitRoles.forwardWayId) handle = 'forward';
                }
                if (isBlind) {
                    // Blind characters sense a way by sound/draft, not by seeing it;
                    // traversing it blind is risky unless they have a cane or are led.
                    exitLines.push(`To the ${handle} — you sense an opening that way by sound and moving air. Going through blind is risky; a cane or a guide helps.`);
                    continue;
                }
                if (!doorNode) { exitLines.push(`To the ${dir}: ${exitData.target||'(unknown)'}`); continue; }
                const wayState = exitData.state || 'closed';
                const seeThrough = !!doorNode.properties?.see_through;
                const beyondSuffix = buildBeyondSuffix(state, charName, exitData, exitData.target, doorNode);
                const moveHint = movementSuffix(doorNode, handle);
                const preventClose = !!doorNode.properties?.prevent_close;
                if (wayState === 'open') {
                    const viewDirection = exitData.visible_in_direction || '';
                    const doorTags = (doorNode.properties?.tags || []).map(t => String(t).toLowerCase().trim());
                    const openWord = doorTags.includes('exterior') || doorTags.includes('natural') ? 'is clear' : 'is open';
                    const closeHint = preventClose ? '' : ' or close it';
                    const actionHint = ` (you can go, dash, examine${closeHint})`;
                    if (viewDirection) {
                        exitLines.push(`[${handle}] ${openWord} — ${viewDirection}${beyondSuffix}${moveHint}${actionHint}`);
                    } else {
                        const targetArea = resolveAreaNode(exitData.target);
                        const clues = [];
                        if (targetArea?.properties?.environment) {
                            const targetEnv = targetArea.properties.environment;
                            const lightValue = parseInt(targetEnv.light) || 50;
                            if (lightValue <= 20) clues.push('pitch dark');
                            else if (lightValue <= 40) clues.push('dimly lit');
                            else if (lightValue >= 90) clues.push('brightly lit');
                            const noiseLevel = targetEnv.noise||'';
                            if (noiseLevel && !['quiet','silence','silent'].includes(noiseLevel)) clues.push(`${noiseLevel} audible`);
                            const temperatureValue = parseInt(targetEnv.temperature)||21;
                            if (temperatureValue >= 35) clues.push('very hot');
                            else if (temperatureValue >= 30) clues.push('hot');
                            else if (temperatureValue >= 25) clues.push('warm');
                            else if (temperatureValue >= 18) clues.push('pleasant');
                            else if (temperatureValue >= 12) clues.push('cool');
                            else if (temperatureValue >= 5) clues.push('chilly');
                            else if (temperatureValue >= 0) clues.push('cold');
                            else clues.push('freezing');
                        }
                        const clueString = clues.length ? ` (${clues.join(', ')})` : '';
                        exitLines.push(`To the ${handle}, the ${exitData.target} is visible beyond${clueString}.${beyondSuffix}${moveHint}${actionHint}`);
                    }
                } else {
                    const viewDirection = exitData.visible_in_direction || '';
                    const doorRawDescription = exitData.description || doorNode.properties?.description || `A way here.`;
                    const doorDescription = typeof InspectorHelpers?.resolveWayParams === 'function'
                        ? InspectorHelpers.resolveWayParams(doorRawDescription, doorNode.properties?.parameters || {})
                        : doorRawDescription;
                    if (seeThrough && viewDirection) {
                        exitLines.push(`[${handle}] is closed — through it you can see ${viewDirection}${beyondSuffix}${moveHint}`);
                    } else if (beyondSuffix && seeThrough) {
                        exitLines.push(`[${handle}] ${doorDescription} It is currently closed.${beyondSuffix}${moveHint}`);
                    } else {
                        exitLines.push(`[${handle}] ${doorDescription} It is currently closed.${moveHint}`);
                    }
                }
            }
        }
        const exitsStr = exitLines.length ? '\nFrom where you stand, you can see the following paths:\n' + exitLines.join('\n') : '\n(no visible exits)';
        // Carrying line with per-item action brackets (drop/use/wear/examine...).
        const carriedItems = PromptBuilder.carriedItemNodes(charName);
        const wornItems = carriedItems.filter(c => c.equipped);
        const notWornItems = carriedItems.filter(c => !c.equipped);
        const buildItemTree = (items, equipped) => {
            const lines = [];
            for (const c of items) {
                const b = PromptBuilder.formatActionBrackets(PromptBuilder.computeItemActions({ id: c.id, name: c.name, properties: c.properties }, player, { equipped }));
                lines.push(`${c.name} ${b}`.trim());
                const contained = getContainedItems(c.id);
                for (const ci of contained) {
                    const cb = PromptBuilder.formatActionBrackets(PromptBuilder.computeItemActions({ id: ci.id, name: ci.name, properties: ci.properties }, player, { equipped: false }));
                    lines.push(`    ${ci.name} ${cb}`.trim());
                }
            }
            return lines;
        };
        const wornStr = wornItems.length
            ? `Wearing:\n${buildItemTree(wornItems, true).join(',\n')}`
            : '';
        const carryStr = notWornItems.length
            ? `Carrying:\n${buildItemTree(notWornItems, false).join(',\n')}`
            : '';
        const invStr = [wornStr, carryStr].filter(Boolean).join('\n');
        const appearanceDesc = player?.description || '';
        const equipStr = appearanceDesc ? `Your appearance: ${PromptBuilder.secondPersonDesc(appearanceDesc)}` : '';
        const others = state.players_in_area || [];
        const allPlayers = state.players || {};
        let peopleStr = '';
        if (others.length > 0) {
            const peopleLines = others.map(person => {
                let desc = person.description || '';
                if (isBlind) {
                    desc = `You can hear them nearby — ${desc.split('.')[0]}.`;
                } else if (level === 'pitch_black') {
                    desc = `You can hear them nearby — ${desc.split('.')[0]}.`;
                } else if (level === 'dim') {
                    desc = `A vague shape in the gloom — ${desc.split('.')[0]}.`;
                } else {
                    // First impression: the first sentence is the highlight of
                    // what you see at a glance — the rest comes from examining.
                    desc = desc.split('.')[0].trim() + (desc.includes('.') ? '.' : '');
                }
                const isMet = worldState.hasMet(charName, person.name);
                // Anonymize strangers — hide the database name if character hasn't met them
                const displayName = PromptBuilder.anonymousName(charName, person.name, desc);
                // The short label (the man) is just a handle — what someone looks like
                // is how you perceive them, met or not, so keep the description for both.
                const descSuffix = desc ? ` — ${desc}` : '';
                const actSuffix = person.activity ? ` (${PromptBuilder.describeActivity(person.activity)})` : '';
                const atSuffix = spatialPositionSuffix(person);
                // Relationship type inline ("a close friend") when known; strangers get no label.
                const relLabel = PromptBuilder.buildRelationshipLabel(player, person.name);
                const relPart = relLabel ? ` - ${relLabel} - ` : ' ';
                return `  - ${displayName}${relPart}(${person.state})${actSuffix}${atSuffix}${descSuffix}`;
            });
            peopleStr = '\nPeople here:\n' + peopleLines.join('\n');
        } else {
            peopleStr = '\nYou see no one else here.';
        }
        let witnessedEvents = '';
        const witnessedLines = [];

        // Include recent_hearing for cross-room sound propagation
        const recentHearing = player?.recent_hearing || [];
        const heardSpeech = recentHearing.filter(h => h.type !== 'sound_source' && h.speaker !== charName).slice(-5);
        // Sound sources (alarms, ringing phones) propagate too — characters should perceive them
        const heardSounds = recentHearing.filter(h => h.type === 'sound_source').slice(-3);

        // Dedupe seen speech so a line isn't shown both as a local event and as heard speech
        const seenSpeechKeys = new Set();
        // Plain lowercase texts seen so far (for contains-match dedupe — a heard
        // echo like "hello lyrie!" is often nested inside a narrated local event).
        const seenSpeechTexts = [];

        // Local events from turn_events (same area, other actors). A blind character
        // only hears others' actions that make sound — visual ones are withheld.
        const recentEvents = (state.turn_events || []).filter(evt => evt.area === currentArea?.name && evt.actor !== charName && (!isBlind || evt.action === 'speak'));
        recentEvents.slice(-10).forEach(evt => {
            const actorDesc = allPlayers[evt.actor]?.description || '';
            const anon = PromptBuilder.anonymousName(charName, evt.actor, actorDesc);
            let line = `[${anon}] ${evt.description}`;
            // Salience-mark direct speech so the character notices lines aimed at them.
            if (evt.action === 'speak' && evt.description) {
                const textMatch = evt.description.match(/said: "(.+)"/);
                if (textMatch) {
                    const spoken = textMatch[1].toLowerCase();
                    seenSpeechKeys.add(`${evt.actor}|${spoken}`);
                    seenSpeechTexts.push(spoken);
                    line = PromptBuilder.markSpeechLine(line, textMatch[1], charName, player);
                }
            }
            witnessedLines.push(line);
        });

        // Heard speech from other rooms — skip any already shown as local events
        heardSpeech.forEach(h => {
            const heardText = String(h.text || '');
            const dedupeKey = `${h.speaker}|${heardText.toLowerCase()}`;
            if (seenSpeechKeys.has(dedupeKey)) return;
            // Contains-match: the heard echo is often a fragment of a narrated
            // local event (e.g. ...say "hello lyrie! i'm miki!"...), so collapse
            // those rather than render the same greeting twice.
            const heardLower = heardText.toLowerCase();
            const contained = seenSpeechTexts.some(seen =>
                heardLower && (heardLower.includes(seen) || seen.includes(heardLower)));
            if (contained) return;
            seenSpeechKeys.add(dedupeKey);
            seenSpeechTexts.push(heardLower);
            // Voice-based label — the listener can't see the speaker's body
            const anon = PromptBuilder.voiceLabel(charName, h.speaker);
            const direction = h.heard_from ? ` from the ${h.heard_from}` : '';
            let line = `[Heard${direction}] ${anon} said: "${h.text}"`;
            line = PromptBuilder.markSpeechLine(line, h.text, charName, player);
            witnessedLines.push(line);
        });

        // Heard sound sources (alarms, ringing phones, etc.) from this or adjacent areas
        heardSounds.forEach(h => {
            const pattern = h.sound_pattern || 'a sound';
            const sourceName = h.source_item ? ` from the ${h.source_item}` : '';
            const direction = h.heard_from ? ` from the ${h.heard_from}` : '';
            witnessedLines.push(`[Heard${direction}${sourceName}] ${pattern}.`);
        });

        // Fallback: frontend room event log
        if (witnessedLines.length === 0) {
            const roomEvents = events.getAreaEvents(currentArea?.name || '').filter(evt => evt.actor !== charName).slice(-8);
            roomEvents.forEach(evt => {
                const actorDesc = allPlayers[evt.actor]?.description || '';
                const anon = PromptBuilder.anonymousName(charName, evt.actor, actorDesc);
                witnessedLines.push(`[${evt.tick}] ${anon} ${evt.action}`);
            });
        }

        // Always render the WITNESSED header — placeholder when nothing to report
        witnessedEvents = witnessedLines.length > 0
            ? '\n\n=== WITNESSED ===\n' + witnessedLines.join('\n')
            : '\n\n=== WITNESSED ===\nNothing unusual happened while you were looking.';
        // Build narrative lead-in — use feels_like from backend state if available
        const feelsLike = player?.feels_like ?? currentArea?.environment?.temperature;
        const tempFeel = feelsLike != null
            ? (feelsLike >= 35 ? 'very hot' : feelsLike >= 30 ? 'hot' : feelsLike >= 25 ? 'warm' : feelsLike >= 18 ? 'pleasant' : feelsLike >= 12 ? 'cool' : feelsLike >= 5 ? 'chilly' : feelsLike >= 0 ? 'cold' : feelsLike >= -10 ? 'freezing' : feelsLike >= -25 ? 'bitterly cold' : 'arctic')
            : '';
        const lightFeel = level === 'pitch_black' ? 'pitch dark'
            : level === 'dim' ? 'dimly lit'
            : level === 'normal' ? 'well lit'
            : level === 'bright' ? 'bright'
            : level === 'blinding' ? 'blindingly bright'
            : '';
        const smellNote = currentArea?.environment?.smell ? ` The air smells of ${currentArea.environment.smell}.` : '';
        let leadIn;
        if (isBlind) {
            const soundNote = currentArea?.environment?.noise ? ` You hear ${currentArea.environment.noise}.` : '';
            leadIn = `You are in the ${currentArea?.name || '(none)'}, though you cannot see it — it is pitch black to you. It feels ${tempFeel}.${smellNote}${soundNote}`;
        } else {
            leadIn = `You are currently in the ${currentArea?.name || '(none)'}. It is ${lightFeel} and ${tempFeel}.${smellNote}`;
        }

        const preamble = buildCharacterPreamble(charName, player);

        const tickNum = window.VW?.state?.tick ?? 0;

        const bodyDesc = isBlind
            ? '(You cannot see the room. What you know of it comes only from sound, smell, and touch.)'
            : (currentArea?.description || '');
        const itemHeader = isBlind ? 'Things you\'ve touched or found:' : 'Items that catch your attention:';
        const noItemsLine = isBlind
            ? "Things you've located: none yet — try fumble or search."
            : "Items that catch your attention: (nothing you haven't already examined)";

        const body = `${bodyDesc}
${warn ? `\n${warn}` : ''}
${items ? `${itemHeader}\n` + items : noItemsLine}
${peopleStr}${exitsStr}${witnessedEvents ? `${witnessedEvents}` : ''}`;

        if (!agentFraming) {
            const envLine = `${currentArea?.name || 'Area'} — ${lightFeel}, ${tempFeel}.${smellNote}`;
            return { agentFraming: false, authoringText: `${envLine}\n\n${body.trim()}` };
        }

        const availableActions = PromptBuilder.buildAvailableActionsBlock(state, charName, player, currentArea);

        const itemsBlock = items ? `${itemHeader}\n` + items : noItemsLine;
        const roomBody = `${bodyDesc}${warn ? `\n${warn}` : ''}`;

return {
            agentFraming: true,
            tickHead: `[Tick ${tickNum}]`,
            preamble,
            appearance: equipStr,
            carrying: invStr,
            leadIn,
            roomBody,
            items: itemsBlock,
            people: peopleStr,
            exits: exitsStr,
            availableActions,
            witnessed: witnessedEvents || '',
            conversation: PromptBuilder.buildConversationInstinct(player, charName),
            plan: includePlan ? PromptBuilder.buildPlanContext(charName) : '',
        };
    }

    /**
     * Build the full area context string for a character — assembled from
     * buildRoomContextParts in the new section order (tick, personality,
     * appearance, carrying, room, exits, items, people, actions, witnessed,
     * plan). Used by standalone callers (human turns, narration, lens
     * previews); the agent turn-prompt builders use the parts directly so the
     * state/memory blocks can be inserted at the top.
     * @param {Object} state - Full world state data
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {Object} currentArea - Current area data object
     * @param {boolean|Object} [includePlanOrOptions=true] - boolean legacy flag, or
     *   `{ includePlan, agentFraming }`. When `agentFraming` is false (area/way/item
     *   lens), omits tick, personality, inventory, and plan — room content only.
     * @returns {string} Formatted area context string
     */
    function buildRoomContext(state, charName, player, currentArea, includePlanOrOptions = true) {
        const parts = buildRoomContextParts(state, charName, player, currentArea, includePlanOrOptions);
        if (!parts.agentFraming) return parts.authoringText;
        const blocks = [
            parts.tickHead,
            parts.preamble,
            parts.appearance,
            parts.carrying,
            parts.leadIn,
            parts.roomBody,
            parts.exits,
            parts.items,
            parts.people,
            parts.availableActions,
            parts.witnessed,
            parts.conversation,
            parts.plan,
        ];
        return blocks.map(block => String(block || '').trim()).filter(Boolean).join('\n\n');
    }

    /**
     * Build a narrated area context (async — may call the LLM for narration).
     * Falls back to the standard area context if narration mode is off.
     * @param {Object} state - Full world state data
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {Object} currentArea - Current area data object
     * @returns {Promise<string>} Narrated or standard area context string
     */
    async function buildNarratedRoomContext(state, charName, player, currentArea) {
        const narrationMode = narrationUI?.getMode();
        let contextString = buildRoomContext(state, charName, player, currentArea);
        if (narrationMode && narrationMode !== 'none') {
            try {
                const items = currentArea?.name ? worldState.getItemsInArea(currentArea.name) : [];
                const contextObject = { areaName: currentArea?.name || '', description: currentArea?.description || '', items: items.filter(item => item.properties?.current_state !== 'hidden').map(item => item.name) || [], characters: state.players_in_area?.map(person => person.name).filter(name => name !== charName) || [], exits: currentArea ? Object.keys(currentArea.exits || {}).join(', ') : '' };
                const narratedDescription = await narrationUI.getNarratedRoomContext(contextObject, charName);
                if (narratedDescription) { contextString = contextString.replace(/^Description: .*/m, `Description: ${narratedDescription}`); try { await ApiClient.playerSpeak(charName, `*${narratedDescription}*`, currentArea?.name); } catch(innerError) {} }
            } catch(error) {}
        }
        return contextString;
    }

    Object.assign(window.PromptBuilder, {
        buildCharacterPreamble,
        buildRoomContext,
        buildRoomContextParts,
        buildNarratedRoomContext
    });
})();
