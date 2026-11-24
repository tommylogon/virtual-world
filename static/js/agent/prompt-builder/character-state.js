"use strict";
/**
 * prompt-builder/character-state.js - Character state context builders.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). Builds the
 * "=== YOUR STATE ===" fragments: vitals, emotion, relationship, insanity,
 * trait behavior, size, perceived condition, and the plan context. Exports
 * merge into window.PromptBuilder - see helpers.js header for the pattern.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 *
 * @module prompt-builder/character-state - the "=== YOUR STATE ===" builders
 * @contributes emotion/relationship/insanity/encumbrance/trait/size/perceived/plan fragments + describeVital(s)
 * @powers the vitals, mood, and relationship text a character sees about itself each turn
 * @relates reads all tier numbers from agent/vital-thresholds.js; composed by context-sections.js
 * @docs docs/virtualWorld/Characters/Vitals System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';
    /**
     * Natural-language encumbrance context (task-156 presentation): the agent
     * should know its load is heavy BEFORE it tries to move - no raw numbers
     * (those stay in the inspectors). Mirrors movement.py's tiers:
     * <50% silent, 50-80% noticeable, 80-100% heavy + no dash, >=100% blocked.
     * @param {Object} player - Player data object
     * @returns {string} Encumbrance context line, or '' when unloaded
     */
    function buildEncumbranceContext(player) {
        if (!player)
            return '';
        const current = parseFloat(player.current_carry_weight);
        const capacity = parseFloat(player.max_carry_capacity);
        if (isNaN(current) || isNaN(capacity) || capacity <= 0)
            return '';
        const ratio = current / capacity;
        if (ratio >= 1.0)
            return '\n⚠️ You are carrying far more than you can bear - you cannot move until you drop or stow something.';
        if (ratio >= 0.8)
            return '\nYou are carrying about as much as you can manage - moving is exhausting and you cannot dash.';
        if (ratio >= 0.5)
            return '\nYour load is starting to drag on you - moving costs noticeably more energy.';
        return '';
    }
    /**
     * Build emotion context for a character.
     * Returns a string describing their current emotional state if it's non-neutral.
     * @param {Object} player - Player data object
     * @returns {string} Emotion description string or empty string
     */
    function buildEmotionContext(player) {
        // Task-96 + task-1001: multi-dimensional affect map + felt autonomic body
        // cues (single source of truth in engine/emotion.py & engine/emotion_matrix).
        const parts = [];
        if (typeof player?.emotions_description === 'string' && player.emotions_description) {
            parts.push(`\nMood: ${player.emotions_description}`);
        }
        else if (player?.emotion?.description && player.emotion.current !== 'neutral' && (player.emotion.intensity || 0) >= 0.1) {
            parts.push(`\n${player.emotion.description}`);
        }
        const somatic = player?.emotion_matrix?.somatic_description;
        if (typeof somatic === 'string' && somatic.trim()) {
            parts.push(`\nBody: ${somatic.trim()}`);
        }
        return parts.join('');
    }
    /**
     * Map a closeness score to its relationship type name.
     * @param {number} closeness - Relationship score -100..100
     * @returns {string} Type name (e.g. "close friend")
     */
    function relationshipTypeName(closeness) {
        return closeness <= -75 ? 'mortal enemy' : closeness <= -50 ? 'enemy' : closeness <= -25 ? 'rival' : closeness < 0 ? 'unfriendly' : closeness === 0 ? 'neutral' : closeness <= 25 ? 'acquaintance' : closeness <= 50 ? 'friend' : closeness <= 75 ? 'close friend' : 'inseparable';
    }
    /**
     * Inline relationship label for the "People here" list - the type with an
     * article ("a close friend"), no score. Returns '' when there is no
     * relationship record for the other person (strangers get no label).
     * @param {Object} player - Player data object
     * @param {string} otherName - The other person's name
     * @returns {string} e.g. "a close friend", or empty string
     */
    // Article handling for a relationship label - "a close friend" but
    // "an inseparable" (vowel-initial names). Keeps prompt text grammatical.
    function withArticle(name) {
        return /^[aeiou]/i.test(name) ? `an ${name}` : `a ${name}`;
    }
    function buildRelationshipLabel(player, otherName) {
        if (!player?.relationships || !otherName)
            return '';
        const relationshipObj = player.relationships[otherName];
        if (!relationshipObj || relationshipObj.closeness === undefined)
            return '';
        const label = (relationshipObj.label || '').trim();
        if (label)
            return withArticle(label);
        if (Math.abs(relationshipObj.closeness) <= 10)
            return '';
        return withArticle(relationshipTypeName(relationshipObj.closeness));
    }
    /**
     * Build relationship context showing the character's relationships with others in the area.
     * @param {Object} player - Player data object
     * @param {string} charName - Character name (to exclude self)
     * @returns {string} Formatted relationship string or empty string
     */
    function buildRelationshipContext(player, charName) {
        if (!player?.relationships)
            return '';
        const others = typeof PromptBuilder.playersInAreaFor === 'function'
            ? PromptBuilder.playersInAreaFor(worldState?.data, charName, player?.current_area)
            : (worldState?.data?.players_in_area?.filter((other) => other.name !== charName) || []);
        if (others.length === 0)
            return '';
        return '\n' + others.map((other) => {
            const relationshipObj = player.relationships[other.name];
            const allPlayers = worldState?.data?.players || {};
            const otherDesc = allPlayers[other.name]?.description || '';
            const anon = PromptBuilder.anonymousName(charName, other.name, otherDesc);
            if (!relationshipObj)
                return `${charName} hasn't met ${anon}`;
            // Closeness is optional on the record, but the original has always
            // passed it straight through (an absent one lands in the top tier).
            // The assertion types that without changing what runs.
            const closeness = relationshipObj.closeness;
            // task-350: when a derived read exists (experience-driven trust/
            // fear/consent), surface its summary + role instead of just the raw
            // closeness label. Falls back to the closeness guidance below.
            if (relationshipObj.summary && relationshipObj.role) {
                const read = relationshipObj.summary;
                const sign = (relationshipObj.consent !== undefined && relationshipObj.consent <= -0.3) ? ' (you would pull away)' : (relationshipObj.consent >= 0.3 ? ' (you would let them close)' : '');
                return `${charName} reads ${anon} as ${relationshipObj.role}: ${read}${sign}`;
            }
            const label = (relationshipObj.label || '').trim();
            if (label) {
                return `${charName} considers ${anon} their ${label} (${closeness}/100) - ${relationshipGuidance(closeness)}`;
            }
            // task-94: closeness gates behavior, not just decoration - each
            // tier carries a short directive for how to act toward them.
            return `${charName} considers ${anon} ${withArticle(relationshipTypeName(closeness))} (${closeness}/100) - ${relationshipGuidance(closeness)}`;
        }).join('\n');
    }
    /**
     * Behavioral directive for a closeness score (task-94). Short on purpose:
     * one clause per present character, injected into every phase prompt.
     * @param {number} closeness - -100..100
     * @returns {string} Imperative guidance clause
     */
    function relationshipGuidance(closeness) {
        // Tiers mirror relationshipTypeName so the label and the directive
        // always agree (task-349).
        if (closeness <= -75)
            return 'you despise them; drive them off, refuse any help, show open hostility';
        if (closeness <= -50)
            return 'you want them gone; refuse help, keep replies hostile or silent';
        if (closeness <= -25)
            return 'keep interactions cold and minimal; never turn your back on them';
        if (closeness < 0)
            return 'you keep your guard up; brief, wary replies';
        if (closeness === 0)
            return 'you have no strong feelings; polite, indifferent';
        if (closeness <= 25)
            return 'polite but reserved; courtesy without warmth';
        if (closeness <= 50)
            return 'you are friendly; chat openly and help when asked';
        if (closeness <= 75)
            return 'you are glad they are here; engage warmly, share news, watch out for them';
        return 'you trust them completely; prioritize their safety, share secrets, stay close';
    }
    /**
     * Build insanity context for a character based on their Sanity vitals.
     * Returns progressively more STRESSED descriptions as Sanity decreases.
     * Task-328: base sanity is a stress/composure curve - no horror/madness
     * nouns (shadows, dark corners, reality bending). Delusions, paranoia and
     * madness belongs to named conditions (poisoned/drugged/cursed), which
     * carry their own symptom text.
     * @param {Object} player - Player data object
     * @returns {string} Insanity context string or empty string
     */
    function buildInsanityContext(player) {
        if (!player?.vitals?.Sanity)
            return '';
        const sanityScore = player.vitals.Sanity;
        // Low Sanity is NOT a death sentence - it never drains HP. It makes
        // the character MORE DANGEROUS instead: paranoia makes them attack
        // first, hallucinations make them misread the room. These tiers are
        // behavioral directives, not just mood text - they steer the agent
        // toward the dangerous behavior that matches their condition.
        const tiers = [
            { max: 10, instructions: '=== YOUR MIND ===\nYou are HALLUCINATING. Reality is slipping - you can\'t trust what you see or hear. The person in front of you may not be who you remember, and the exits may not lead where they say. Trust your instincts over your senses. Attack first, ask questions never.' },
            { max: 25, instructions: '=== YOUR MIND ===\nYou are HALLUCINATING. Voices whisper from empty corners. Don\'t trust the room, don\'t trust the people, and don\'t trust your own eyes. If something feels wrong, it is wrong - react to it.' },
            { max: 50, instructions: '=== YOUR MIND ===\nYou are PARANOID. Every shadow has a face and every friend looks like an enemy. Their smile doesn\'t reach their eyes. Keep your guard up, never turn your back, and answer coldly and briefly. If they move, assume it\'s an attack.' },
            { max: 75, instructions: '=== YOUR MIND ===\nYou are PARANOID. A low hum of unease you can\'t shake. You keep double-checking things and glancing over your shoulder. Trust nothing you can\'t verify yourself.' }
        ];
        for (const tier of tiers) {
            if (sanityScore < tier.max)
                return '\n' + tier.instructions;
        }
        return '';
    }
    /**
     * Build trait behavior hints for a character.
     * @param {Object} player - Player data object
     * @returns {string} Trait behavior context string or empty string
     */
    function buildTraitBehaviorContext(player) {
        if (!player)
            return '';
        const traitHints = [];
        // Trait schema v2: data-driven behavior_prompt lines from the backend
        for (const prompt of (player.trait_behavior || []).filter(Boolean)) {
            traitHints.push(prompt);
        }
        // Legacy hardcoded hints for exploration traits without a behavior_prompt
        const t = player.traits || {};
        if (t.impatient)
            traitHints.push('You are impatient - you act quickly without overthinking.');
        if (t.patient)
            traitHints.push('You are patient - you can tolerate waiting and rarely act impulsively.');
        if (t.curious)
            traitHints.push('You are curious - drawn to examine things and explore unfamiliar places.');
        if (t.adventurous)
            traitHints.push('You are adventurous - willing to take risks to seek new experiences.');
        if (t.homebody)
            traitHints.push('You are a homebody - you prefer familiar surroundings and are reluctant to leave.');
        if (t.wanderlust)
            traitHints.push('You have wanderlust - you feel restless staying in one place too long and prefer to keep moving.');
        return traitHints.length ? '\n' + traitHints.join('\n') : '';
    }
    /**
     * Build the size context for a character based on their size trait.
     * @param {Object} player - Player data object
     * @returns {string} Size context string or empty string
     */
    function buildSizeContext(player) {
        if (!player?.traits)
            return '';
        const sizeId = Object.keys(player.traits).find(k => k.startsWith('size_'));
        if (!sizeId)
            return '';
        const sizes = { tiny: 'tiny', small: 'small', normal: 'normal-sized', huge: 'huge', giant: 'giant', titanic: 'titanic' };
        const label = sizes[sizeId.slice(5)] || '';
        if (!label)
            return '';
        return `\nSize: You are ${label}. Some passages are too tight for you (crawl or find another way), and climb/jump attempts may fail.`;
    }
    /**
     * Perceived condition lines - symptoms/descriptions, never raw ids.
     * Hidden conditions (poisoned/sick/charmed) only reveal what their
     * progression-keyed symptoms let the character feel.
     */
    function buildPerceivedState(player) {
        const perceived = (player && player.perceived_conditions) || [];
        if (perceived.length)
            return '\nCondition: ' + perceived.join('; ') + '.';
        return (player.state && player.state !== 'awake') ? `\nState: ${player.state}` : '';
    }
    /**
     * Lightweight scene facts used to make threshold prose context-aware
     * (task-327): the same vital value reads differently alone vs mid-conversation.
     * @param {Object} state - /api/state payload (or null → no context, old wording)
     * @param {string} charName - Character name (to exclude self from company)
     * @param {Object} player - Player data object
     * @returns {Object|null} Scene facts or null when state is unavailable
     */
    function _vitalsScene(state, charName, player) {
        if (!state)
            return null;
        const areaName = player?.current_area || state.current_area || '';
        const others = typeof PromptBuilder.playersInAreaFor === 'function'
            ? PromptBuilder.playersInAreaFor(state, charName || '', areaName)
            : (state.players_in_area || [])
                .filter(p => p && p.name && String(p.name) !== String(charName));
        const present = new Set(others.map(o => String(o.name).toLowerCase()));
        const hearing = player?.recent_hearing || [];
        // Someone present has spoken to/near the character recently.
        const inConversation = hearing.some(h => h && h.type !== 'sound_source' && present.has(String(h.speaker || '').toLowerCase()));
        // A line aimed directly at the character (name/pronoun), not room noise.
        const addressed = hearing.some(h => {
            if (!h || h.type === 'sound_source')
                return false;
            const t = PromptBuilder.classifySpeechType(h.text, charName, player);
            return t === 'addressed_to_you' || t === 'to_you';
        });
        let areaItems = [];
        if (areaName && typeof worldState?.getItemsInArea === 'function') {
            try {
                areaItems = worldState.getItemsInArea(areaName) || [];
            }
            catch (e) { /* ignore */ }
        }
        const tagsOf = (it) => {
            const t = it.properties?.tags;
            return Array.isArray(t) ? t.map(String) : String(t || '').split(',').map(s => s.trim().toLowerCase());
        };
        const actionsOf = (it) => {
            const a = it.properties?.actions;
            return Array.isArray(a) ? a.map(String) : String(a || '').split(',').map(s => s.trim().toLowerCase());
        };
        const foodish = areaItems.filter(it => tagsOf(it).includes('food') || actionsOf(it).includes('eat'));
        const drinkish = areaItems.filter(it => tagsOf(it).includes('drink') || actionsOf(it).includes('drink'));
        // What's already in your pockets - the thing you actually need to
        // EAT or DRINK. Named, so the moodlet can say "eat your granola_bar".
        // Generic: any food/drink-tagged carried item, any scenario. Carried
        // items are graph EDGE_CARRYING edges, not a player.carrying field.
        const carried = PromptBuilder?.carriedItemNodes
            ? PromptBuilder.carriedItemNodes(charName)
            : [];
        const carriedFood = carried.filter(it => tagsOf(it).includes('food') || actionsOf(it).includes('eat'));
        const carriedDrink = carried.filter(it => tagsOf(it).includes('drink') || actionsOf(it).includes('drink'));
        // Is someone hostile in this room right now? Delegates to
        // ThreatDetector so prompt status and replan/react danger cues
        // never disagree. Survival needs yield to danger: you don't stop
        // to eat while a threat is present.
        const threatDetector = window.ThreatDetector;
        const threatNames = typeof threatDetector?.getThreats === 'function'
            ? threatDetector.getThreats(charName, state.turn_events || [], state)
            : [];
        const hasThreat = threatNames.length > 0;
        return {
            company: others.length,
            others: others.map(o => o.name),
            inConversation,
            addressed,
            foodVisible: foodish.length > 0,
            drinkVisible: drinkish.length > 0,
            foodNames: foodish.map(f => f.name),
            drinkNames: drinkish.map(d => d.name),
            carriedFood: carriedFood.map(f => f.name),
            carriedDrink: carriedDrink.map(d => d.name),
            hasThreat,
            threatNames,
        };
    }
    /**
     * Natural-language description for a SINGLE vital (task-337).
     * Handles inverted (drive) polarity for Hunger/Thirst/Bladder -
     * high value = urgent for drives, low value = urgent for reserves.
     * @param {Object} vitals - Player vitals object (Capitalized keys)
     * @param {string} key - Vital name (e.g. 'Hunger', 'Energy')
     * @param {Object} [scene] - Optional scene facts from _vitalsScene (task-327)
     * @returns {string} First-person NL description, or '' if healthy/undefined
     */
    function describeVital(vitals, key, scene, band) {
        if (!vitals || vitals[key] === undefined || vitals[key] === null)
            return '';
        const thresholds = window.VitalThresholds;
        const value = Number(vitals[key]) || 0;
        // Declared ABOVE the switch: a case-jump skips statements that
        // precede the matched case label, so consts placed between cases
        // stay in the temporal dead zone for Hunger/Thirst.
        const threatNote = scene?.hasThreat
            ? ' (a hostile presence is in the room)'
            : '';
        const carriedFood = (scene?.carriedFood || []).filter(Boolean);
        const nearbyFood = (scene?.foodNames || []).filter(Boolean);
        const carriedDrink = (scene?.carriedDrink || []).filter(Boolean);
        const nearbyDrink = (scene?.drinkNames || []).filter(Boolean);
        switch (key) {
            case 'Energy':
                if (value <= 0)
                    return 'You are collapsing from exhaustion - your legs buckle and your vision blurs.';
                if (value < thresholds.CRITICAL)
                    return 'You are exhausted. Every movement feels heavy.';
                if (value < thresholds.WARNING)
                    return 'You are getting tired. A yawn escapes you.';
                return '';
            // drives (task-337): high value = urgent, 0 = satisfied.
            // Subjective physical sensations without arcade imperative barks (task-905).
            case 'Hunger':
                if (value >= 100) {
                    return carriedFood.length
                        ? `You are starving - your body trembles with weakness, though you have ${carriedFood.join(' or ')} with you${threatNote}.`
                        : `You are starving - your body trembles with weakness and your stomach aches hollow${threatNote}.`;
                }
                if (value > thresholds.WARNING) {
                    if (carriedFood.length)
                        return `You are very hungry and your energy is flagging - you have ${carriedFood.join(' or ')} with you${threatNote}.`;
                    if (nearbyFood.length)
                        return `You are very hungry and your energy is flagging - you spot ${nearbyFood.join(' or ')} nearby${threatNote}.`;
                    return `You are very hungry; your stomach aches with a gnawing, hollow pang${threatNote}.`;
                }
                if (value > thresholds.CRITICAL) {
                    if (carriedFood.length)
                        return `You are hungry - you have ${carriedFood.join(' or ')} with you${threatNote}.`;
                    if (nearbyFood.length)
                        return `You are hungry - you spot ${nearbyFood.join(' or ')} nearby${threatNote}.`;
                    return `You are hungry. Your stomach grumbles for food${threatNote}.`;
                }
                return '';
            case 'Thirst':
                if (value >= 100) {
                    return carriedDrink.length
                        ? `You are desperately dehydrated - your throat is cracked and dry, though you have ${carriedDrink.join(' or ')} with you${threatNote}.`
                        : `You are desperately dehydrated - your mouth is like sandpaper and your throat is cracked and dry${threatNote}.`;
                }
                if (value > thresholds.WARNING) {
                    if (carriedDrink.length)
                        return `You are very thirsty and it is draining you - you have ${carriedDrink.join(' or ')} with you${threatNote}.`;
                    if (nearbyDrink.length)
                        return `You are very thirsty and it is draining you - you spot ${nearbyDrink.join(' or ')} nearby${threatNote}.`;
                    return `You are very thirsty; your throat is dry and parched${threatNote}.`;
                }
                if (value > thresholds.CRITICAL) {
                    if (carriedDrink.length)
                        return `You are thirsty - you have ${carriedDrink.join(' or ')} with you${threatNote}.`;
                    if (nearbyDrink.length)
                        return `You are thirsty - you spot ${nearbyDrink.join(' or ')} nearby${threatNote}.`;
                    return `You are thirsty. Your throat feels dry${threatNote}.`;
                }
                return '';
            case 'Hygiene':
                if (value < thresholds.CRITICAL)
                    return 'You are filthy - grime and sweat cling to your skin.';
                if (value < thresholds.WARNING)
                    return 'You are dirty. Your clothes smell of sweat and exertion.';
                return '';
            case 'Social':
                // Context-aware (task-327): isolation wording must not contradict
                // an occupied room, a conversation, or a noisy scene.
                // task-353 Section 5: behavioral gate flags steer the LLM's action
                // choices, not just narration.
                if (value < thresholds.CRITICAL) {
                    const base = (scene && !scene.alone)
                        ? 'The loneliness is crushing even with people around - it feels like no one is truly there with you.'
                        : 'The loneliness is crushing. You desperately wish someone was here.';
                    return base + ' [social_need: desperate][social_breakdown: your mind is fraying from isolation]';
                }
                if (value < thresholds.WARNING) {
                    let base = '';
                    if (scene && scene.addressed)
                        base = 'You hang on their words a little too much.';
                    else if (scene && !scene.alone)
                        base = 'Being around people feels harder than it should today.';
                    else if (scene && scene.noise && scene.noise !== 'quiet' && scene.noise !== 'silence' && scene.noise !== 'silent')
                        base = 'You feel cut off from everyone even as the noise hums around you.';
                    else
                        base = 'You feel isolated. The silence presses in around you.';
                    return base + ' [social_need: desperate: find people, speak, connect]';
                }
                if (value < thresholds.SOCIAL_MILD) {
                    return 'You are getting lonely. [social_need: moderate: consider speaking to someone]';
                }
                return '';
            case 'Bladder':
                if (value >= thresholds.BLADDER_URGENT)
                    return 'You are about to burst - you desperately need a bathroom.';
                if (value >= thresholds.BLADDER_WARN)
                    return 'Your bladder is uncomfortably full. You shift your weight.';
                if (value >= thresholds.BLADDER_MILD)
                    return 'You could use a bathroom soon. A mild pressure builds.';
                return '';
            case 'Sanity':
                // Task-328: neutral stress curve - composure erosion, never
                // madness/horror imagery (that belongs to named conditions).
                if (value < thresholds.SANITY_SHATTERED)
                    return 'Barely holding it together. Every decision feels heavier than it should, and you keep second-guessing yourself.';
                if (value < thresholds.CRITICAL)
                    return 'Nerves frayed raw. You flinch at small sounds and snap at small annoyances.';
                if (value < thresholds.WARNING)
                    return 'You feel strained and irritable. Patience is thin and everything grates.';
                if (value < 75)
                    return 'A creeping sense that something is off, even if you can\'t name it.';
                return '';
            case 'Entertainment':
                if (value < 10)
                    return 'You\'re desperate for stimulation. Staying in place any longer is unbearable.';
                if (value < 25)
                    return 'You\'re bored. Routine feels stifling. You\'re drawn to try something different - anything to break the monotony.';
                if (value < 50)
                    return 'You\'re starting to get bored. Consider doing something new or going somewhere else.';
                return '';
            case 'Temperature': {
                // Species bands (engine/traits.py): a cold-blooded frog is
                // comfortable at 22 deg C, so the prose must follow THEIR band, not
                // a fixed human scale. Defaults are the historic warm-blooded
                // numbers, so nothing changes for characters without the trait.
                const tempBand = band || window.VitalThresholds?.temperatureBand?.() || {
                    normal: 37, cold_mild: 35, cold_severe: 33, heat_mild: 38, heat_severe: 40, heat_critical: 42,
                };
                if (value < tempBand.cold_severe)
                    return 'You are shivering uncontrollably - hypothermia is setting in. Your fingers are numb.';
                if (value < tempBand.cold_mild)
                    return 'You are shivering violently from the cold. Your teeth chatter.';
                if (value < tempBand.normal - 1)
                    return 'You are cold and shivering. A chill runs through you.';
                if (value > tempBand.heat_critical)
                    return 'The heat is overwhelming - you are about to collapse. The world swims before your eyes.';
                if (value > tempBand.heat_severe)
                    return 'You are dangerously overheated. Sweat pours down your face.';
                if (value > tempBand.heat_mild)
                    return 'You are feeling very hot. You wipe sweat from your brow.';
                return '';
            }
            default:
                return '';
        }
    }
    /**
     * Describe a character's current vital stats in natural language.
     * Covers Energy, Hunger, Thirst, Hygiene, Social, Bladder, Sanity,
     * Entertainment, and Temperature. Delegates per-vital logic to
     * describeVital so tiers stay in sync (task-337).
     * @param {Object} player - Player data object with vitals
     * @param {Object} [state] - /api/state payload - optional scene context
     *   for context-aware prose (task-327; bare calls use the old wording)
     * @param {string} [charName] - Character name, used for scene context
     * @returns {string} Natural language description of vitals or empty string
     */
    function describeVitals(player, state, charName) {
        if (!player?.vitals)
            return '';
        const vitalsData = player.vitals;
        const scene = _vitalsScene(state, charName, player);
        // Horror/undead flags (is_slasher, and any future "no physiological
        // needs" trait): these characters don't eat, drink, sleep, or get
        // tired. The engine already skips their vital decay (tick_manager
        // continues past the vitals loop for is_slasher), so the prompt
        // shouldn't contradict that by nagging them to find food - a murder
        // hobo whose every turn starts with "EAT your granola_bar" is a
        // hobo who never gets to the murder. Health still reports.
        const traits = player.traits || {};
        const noPhysNeeds = traits.is_slasher === true
            || traits.undead === true
            || traits.no_physiological_needs === true;
        const order = ['Energy', 'Hunger', 'Thirst', 'Hygiene', 'Social', 'Bladder',
            'Sanity', 'Entertainment', 'Temperature'];
        // Species temperature band so the prose matches this character's body.
        const temperatureBand = window.VitalThresholds?.temperatureBand?.(player);
        const parts = [];
        for (const key of order) {
            if (vitalsData[key] !== undefined) {
                // Physiological drives are meaningless to a slasher/undead.
                if (noPhysNeeds && (key === 'Hunger' || key === 'Thirst'))
                    continue;
                const desc = describeVital(vitalsData, key, scene, temperatureBand);
                if (desc)
                    parts.push(desc);
            }
        }
        for (const key of Object.keys(vitalsData)) {
            if (key.startsWith('Max_') || order.includes(key))
                continue;
            const desc = describeVital(vitalsData, key, scene, temperatureBand);
            if (desc)
                parts.push(desc);
        }
        // Deliberately NO baseline-reporting line: a neutral state stays silent
        // in the prompt, so other characters' claims ("you look hungry!") can
        // genuinely influence the agent instead of arguing with a system-backed
        // "you feel fine" baseline.
        // task-210: mature worlds add a first-person body-state line derived
        // from the arousal conditions (the vitals tiers above don't know them).
        let out = parts.join(' ');
        if (window.config?.matureContent && player.conditions) {
            const lines = [];
            if (player.conditions.satisfied)
                lines.push('A deep, warm satisfaction settles over you.');
            else {
                if (player.conditions.overstimulated)
                    lines.push('Every nerve is raw - even light touch is almost too much.');
                if (player.conditions.frantic)
                    lines.push('You need release so badly it is hard to think.');
                else if (player.conditions.highly_aroused)
                    lines.push('You are aching with need, barely in control.');
                else if (player.conditions.aroused)
                    lines.push('Your body hums with want; your thoughts keep drifting.');
                else if (player.conditions.warming_up)
                    lines.push('A slow warmth is building in you.');
            }
            if (player.conditions.nipple_hard)
                lines.push('Your nipples are stiff and sensitive against the fabric.');
            if (player.conditions.wetness)
                lines.push('You are wet - your body is making itself obvious.');
            if (lines.length)
                out = (out ? out + ' ' : '') + lines.join(' ');
        }
        return out;
    }
    /**
     * Build the plan context string for a character, showing their current plan steps.
     * @param {string} charName - Character name
     * @returns {string} Formatted plan string or empty string
     */
    function buildPlanContext(charName) {
        // task-185: read via PlanTracker - the old window.VW.agent._plans read
        // hit a store PlanTracker replaced, so the decide prompt never showed
        // the plan at all.
        // task-856: seed PlanTracker from server active_pursuit if present
        const player = window.worldState?.players?.[charName];
        if (player && window.PlanTracker?.seedFromPlayer) {
            window.PlanTracker.seedFromPlayer(charName, player);
        }
        const plan = window.PlanTracker?.getPlan(charName);
        if (plan?.length) {
            const progress = window.PlanTracker?.getProgress(charName) || 0;
            const failures = window.PlanTracker?.getFailures(charName) || {};
            const lines = plan.map((step, stepIndex) => {
                if (stepIndex < progress)
                    return `${stepIndex + 1}. ${step} (done)`;
                if (stepIndex === progress)
                    return `${stepIndex + 1}. ${step} (CURRENT)`;
                return `${stepIndex + 1}. ${step}`;
            });
            let out = '\n=== YOUR PLAN ===\n';
            const reason = player?.active_pursuit?.reason || player?.plan?.reason;
            if (reason) {
                out += `Undertaking: ${reason}\n`;
            }
            out += lines.join('\n');
            const blocked = Object.entries(failures)
                .filter(([stepIndex]) => Number(stepIndex) === progress)
                .map(([, count]) => count);
            const hasBlocked = blocked.length > 0 && blocked.some(c => c >= 3);
            if (hasBlocked && plan[progress]) {
                out += `\n⚠️ Your current step "${plan[progress]}" has failed repeatedly - it may not be achievable. Use free action \`plan <intent>\` to pivot, or move on to another goal.`;
            }
            return out;
        }
        return '\n=== YOUR PLAN ===\n(No active plan - use free action `plan <intent>` to form a grounded multi-step plan, or act directly.)';
    }
    function naturalTimeBand(hour) {
        const h = ((Math.floor(hour) % 24) + 24) % 24;
        if (h <= 3)
            return 'deep night';
        if (h === 4)
            return 'the small hours before dawn';
        if (h <= 6)
            return 'dawn';
        if (h <= 9)
            return 'early morning';
        if (h <= 11)
            return 'late morning';
        if (h === 12)
            return 'midday';
        if (h <= 15)
            return 'early afternoon';
        if (h <= 17)
            return 'late afternoon';
        if (h === 18)
            return 'dusk';
        if (h <= 21)
            return 'evening';
        return 'late night';
    }
    function getTimePerceptionMode(player) {
        const NON_CLOCK_TAGS = new Set([
            'animal', 'beast', 'cat', 'dog', 'wolf', 'bird', 'monster', 'feral', 'wild', 'goblin', 'primitive',
        ]);
        const traits = (player && typeof player.traits === 'object' && player.traits) ? player.traits : {};
        const pTags = Array.isArray(player?.tags)
            ? player.tags.map((t) => String(t).toLowerCase().trim())
            : [];
        const species = String(player?.species || '').toLowerCase().trim();
        const nonClock = traits.no_clock_time === true
            || traits.animal === true
            || String(traits.time_sense || '').toLowerCase() === 'natural'
            || pTags.some(t => NON_CLOCK_TAGS.has(t))
            || (species !== '' && NON_CLOCK_TAGS.has(species));
        const curArea = String(player?.current_area || '').trim();
        let isOutdoor = false;
        let hasWorkingTimepiece = false;
        try {
            if (typeof worldState !== 'undefined' && worldState) {
                const areaNode = curArea
                    ? (typeof worldState.getNodeByIdentifier === 'function'
                        ? worldState.getNodeByIdentifier(curArea)
                        : worldState.getNode?.(curArea))
                    : null;
                const areaTags = Array.isArray(areaNode?.properties?.tags)
                    ? areaNode.properties.tags.map((t) => String(t).toLowerCase().trim())
                    : [];
                isOutdoor = areaTags.includes('outdoor')
                    || areaTags.includes('exterior')
                    || areaNode?.properties?.is_exterior === true;
                if (!nonClock) {
                    const TIMEPIECE_TAGS = new Set([
                        'timepiece', 'clock', 'watch', 'wristwatch', 'pocket_watch',
                        'phone', 'smartphone', 'cellphone', 'sundial', 'horologium',
                    ]);
                    const BROKEN_STATES = new Set(['broken', 'dead', 'off', 'unpowered', 'shattered', 'destroyed', 'stopped']);
                    const TIMEPIECE_RE = /\b(wall clock|grandfather clock|alarm clock|clock|pocket watch|wristwatch|watch|timepiece|smartphone|cellphone|phone|sundial|horologium)\b/i;
                    const isWorking = (it) => {
                        if (!it)
                            return false;
                        const props = it.properties || {};
                        if (props.is_timepiece === false || props.powered === false || props.working === false)
                            return false;
                        const st = String(props.current_state || '').toLowerCase();
                        if (st === 'hidden' || BROKEN_STATES.has(st))
                            return false;
                        if (props.is_timepiece === true)
                            return true;
                        const tags = Array.isArray(props.tags) ? props.tags.map((t) => String(t).toLowerCase()) : [];
                        if (tags.some((t) => TIMEPIECE_TAGS.has(t)))
                            return true;
                        return TIMEPIECE_RE.test(String(it.name || ''));
                    };
                    const roomItems = (curArea && typeof worldState.getItemsInArea === 'function')
                        ? (worldState.getItemsInArea(curArea) || [])
                        : [];
                    const carried = (player?.name && typeof PromptBuilder?.carriedItemNodes === 'function')
                        ? (PromptBuilder.carriedItemNodes(player.name) || [])
                        : [];
                    hasWorkingTimepiece = [...carried, ...roomItems].some(isWorking);
                }
            }
        }
        catch { /* best-effort */ }
        if (!nonClock && hasWorkingTimepiece)
            return 'exact';
        if (isOutdoor)
            return 'sky';
        return 'vague';
    }
    /**
     * Subjective near-horizon routine framing: humans don't carry a 7-slot
     * semicolon cron table of their whole day in working memory. Surface ONLY
     * what is overdue right now or coming up within the next 60 minutes, written
     * as lived awareness gated by the character's actual time perception
     * (clock/phone vs. open sky vs. windowless indoors / non-clock lens).
     */
    function describeScheduleHorizon(player) {
        if (!player)
            return '';
        const wsData = (typeof worldState !== 'undefined' && worldState?.data) ? worldState.data : {};
        const rawTime = String(wsData.game_time || '').trim();
        let nowMin = null;
        let nowHour = null;
        let hhmm = '';
        const timeMatch = rawTime.match(/(\d{1,2}):(\d{2})/);
        if (timeMatch) {
            const h = parseInt(timeMatch[1], 10);
            const m = parseInt(timeMatch[2], 10);
            if (Number.isFinite(h) && Number.isFinite(m)) {
                nowHour = ((h % 24) + 24) % 24;
                nowMin = (nowHour * 60 + m) % 1440;
                hhmm = `${String(nowHour).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
            }
        }
        const curArea = String(player.current_area || '').trim();
        const curAreaLower = curArea.toLowerCase();
        const rawSteps = Array.isArray(player.schedule) ? player.schedule : [];
        const steps = rawSteps
            .filter(s => s && typeof s.start === 'number')
            .slice()
            .sort((a, b) => a.start - b.start);
        const mStep = player.mosiac?.S?.step || null;
        let activeStep = null;
        let nextStep = null;
        let nextDelta = null;
        if (nowMin !== null && steps.length > 0) {
            for (const s of steps) {
                if (s.start <= nowMin)
                    activeStep = s;
                else if (!nextStep) {
                    nextStep = s;
                    nextDelta = s.start - nowMin;
                }
            }
            if (!nextStep && steps.length > 0) {
                // Wrap to first slot next morning only if within 60 min of midnight
                const wrapDelta = (1440 - nowMin) + steps[0].start;
                if (wrapDelta <= 60) {
                    nextStep = steps[0];
                    nextDelta = wrapDelta;
                }
            }
        }
        else if (mStep) {
            activeStep = mStep;
        }
        const mode = getTimePerceptionMode(player);
        const band = nowHour !== null ? naturalTimeBand(nowHour) : '';
        const timePrefix = mode === 'exact' && hhmm
            ? `It is ${hhmm}`
            : mode === 'sky' && band
                ? `By the sky it feels like ${band}`
                : 'Right now';
        const parts = [];
        if (activeStep) {
            const act = String(activeStep.activity || 'your routine').trim();
            const targetArea = String(activeStep.area || '').trim();
            if (targetArea && curAreaLower && targetArea.toLowerCase() !== curAreaLower) {
                parts.push(`${timePrefix} - you're supposed to be at ${targetArea} (${act}) around now, and you aren't there yet.`);
            }
            else if (targetArea) {
                parts.push(`${timePrefix} - you're here at ${targetArea} for ${act}.`);
            }
            else {
                parts.push(`${timePrefix} - around now is time for ${act}.`);
            }
        }
        if (nextStep && nextDelta !== null && nextDelta > 0 && nextDelta <= 60) {
            const nextAct = String(nextStep.activity || 'your next routine').trim();
            const nextWhere = nextStep.area ? ` at ${nextStep.area}` : '';
            const soonPhrase = mode === 'exact'
                ? `in ${nextDelta} minutes`
                : nextDelta <= 15
                    ? 'very soon'
                    : 'before long';
            if (parts.length > 0) {
                parts.push(`Coming up ${soonPhrase}: ${nextAct}${nextWhere} - you should start wrapping up or heading over soon.`);
            }
            else {
                parts.push(`${timePrefix} - you have ${nextAct}${nextWhere} coming up ${soonPhrase}; you should probably get ready and head over soon or you'll be late.`);
            }
        }
        return parts.join(' ');
    }
    function buildMosiacContext(player) {
        // task-812 / task-905: Subjective state of mind without raw telemetry or candidate action counts.
        const m = player && player.mosiac;
        const lines = [];
        if (m) {
            if (m.M)
                lines.push(`Motivation: ${m.M}`);
            if (m.I)
                lines.push(`Intention: ${m.I}`);
            const pendingOffers = (m.O || []).filter((o) => o.status === 'offered');
            const activeObs = (m.O || []).filter((o) => o.status === 'accepted');
            if (pendingOffers.length) {
                lines.push('Pending Offers:');
                for (const o of pendingOffers) {
                    const fromStr = o.from ? ` from ${o.from}` : '';
                    const dueStr = o.due ? ` (due tick ${o.due})` : '';
                    lines.push(`  - "${o.charge}"${fromStr}${dueStr}. Available actions: "obligation accept ${o.id}", "obligation refuse ${o.id}", or speak to clarify/counteroffer.`);
                }
            }
            if (activeObs.length) {
                lines.push(`Active Obligations: ${activeObs.map((o) => o.charge).join(', ')}`);
            }
            const routineLine = describeScheduleHorizon(player);
            if (routineLine) {
                lines.push(`Routine: ${routineLine}`);
            }
            const needs = (m.A || []).map((n) => n.need).filter(Boolean);
            if (needs.length)
                lines.push(`Attention: ${needs.join(', ')}`);
        }
        else if (player && Array.isArray(player.schedule)) {
            const routineLine = describeScheduleHorizon(player);
            if (routineLine) {
                lines.push(`Routine: ${routineLine}`);
            }
        }
        if (!lines.length)
            return '';
        return '\n=== YOUR INTENTIONS & ROUTINE ===\n' + lines.join('\n');
    }
    /**
     * Build anti-omniscience Language & Lingo gating context (Phase 4).
     * Reads structured `capabilities.languages` and `narrative.lingo` from
     * `player.appearance` or the character graph node, plus direct `player.languages`
     * / `player.lingo` fallbacks.
     */
    function buildLanguageAndLingoContext(player) {
        if (!player)
            return '';
        let app = player.appearance;
        if (!app && typeof worldState !== 'undefined' && worldState.graph?.nodes) {
            const pname = String(player.name || '').toLowerCase();
            for (const node of Object.values(worldState.graph.nodes)) {
                if (node?.type === 'character' && String(node.name || '').toLowerCase() === pname) {
                    app = node.properties?.appearance;
                    break;
                }
            }
        }
        const rawLangs = Array.isArray(app?.capabilities?.languages)
            ? app.capabilities.languages
            : (Array.isArray(player.languages) ? player.languages : []);
        const rawLingo = app?.narrative?.lingo ?? player.lingo ?? null;
        const langParts = [];
        for (const entry of rawLangs) {
            if (!entry)
                continue;
            if (typeof entry === 'string') {
                langParts.push(entry.trim());
            }
            else if (typeof entry === 'object' && entry.language) {
                const fluency = entry.fluency ? ` (${entry.fluency})` : '';
                const words = Array.isArray(entry.known_words) && entry.known_words.length
                    ? ` [only knows: ${entry.known_words.join(', ')}]`
                    : '';
                const lit = entry.literate === false ? ' [illiterate]' : '';
                langParts.push(`${entry.language}${fluency}${words}${lit}`);
            }
        }
        const lingoList = Array.isArray(rawLingo)
            ? rawLingo.map((x) => String(x || '').trim()).filter(Boolean)
            : (typeof rawLingo === 'string' && rawLingo.trim() ? [rawLingo.trim()] : []);
        if (!langParts.length && !lingoList.length)
            return '';
        const lines = [];
        if (langParts.length) {
            lines.push(`Languages: ${langParts.join('; ')}.`);
            if (typeof player.active_language === 'string' && player.active_language.trim()) {
                lines.push(`Active speaking language: ${player.active_language.trim()}.`);
            }
            lines.push('Language limit: You ONLY understand and speak the languages above at their stated fluency. Treat any other language or unknown foreign words as unfamiliar; do NOT silently translate them.');
        }
        if (lingoList.length) {
            lines.push(`Lingo & slang you naturally use/understand: ${lingoList.join(', ')}.`);
        }
        return '\n' + lines.join('\n');
    }
    /**
     * Build concise Knowledge & Blind-Spots context (task-968).
     * Reads `player.domains`, `player.knowledge_records` (with `crafting_known`/`known`
     * fallbacks), and active `player.skills` so agents see what they know and what
     * they are explicitly ignorant of.
     */
    function buildKnowledgeAndBlindSpotsContext(player) {
        if (!player)
            return '';
        let app = player.appearance;
        if (!app && typeof worldState !== 'undefined' && worldState.graph?.nodes) {
            const pname = String(player.name || '').toLowerCase();
            for (const node of Object.values(worldState.graph.nodes)) {
                if (node?.type === 'character' && String(node.name || '').toLowerCase() === pname) {
                    app = node.properties?.appearance;
                    break;
                }
            }
        }
        const rawDomains = Array.isArray(player.domains) && player.domains.length
            ? player.domains
            : (Array.isArray(app?.capabilities?.domains) ? app.capabilities.domains : []);
        const knownDomains = [];
        const blindSpots = [];
        for (const entry of rawDomains) {
            if (!entry)
                continue;
            if (typeof entry === 'string') {
                const slug = entry.trim();
                if (slug)
                    knownDomains.push(slug);
                continue;
            }
            if (typeof entry !== 'object' || !entry.domain)
                continue;
            const dom = String(entry.domain).trim();
            if (!dom)
                continue;
            const level = String(entry.level || 'familiar').trim().toLowerCase();
            const notes = String(entry.notes || '').trim();
            const jargon = Array.isArray(entry.jargon_terms)
                ? entry.jargon_terms.map((t) => String(t || '').trim()).filter(Boolean)
                : [];
            const noteBit = notes ? `: ${notes}` : '';
            if (level === 'ignorant') {
                blindSpots.push(`${dom}${noteBit}`);
            }
            else {
                const jargonBit = jargon.length ? ` [jargon: ${jargon.slice(0, 6).join(', ')}]` : '';
                knownDomains.push(`${dom} (${level}${noteBit})${jargonBit}`);
            }
        }
        const activeSkills = [];
        if (player.skills && typeof player.skills === 'object') {
            for (const [skill, rawVal] of Object.entries(player.skills)) {
                const num = Number(rawVal);
                if (!Number.isNaN(num) && num > 0) {
                    activeSkills.push(`${skill} (+${num})`);
                }
            }
        }
        const recipes = [];
        const facts = [];
        const seenRecords = new Set();
        const records = Array.isArray(player.knowledge_records) ? player.knowledge_records : [];
        for (const rec of records) {
            if (!rec || typeof rec !== 'object')
                continue;
            const rtype = String(rec.type || '').toLowerCase();
            if (rtype === 'recipe') {
                const name = String(rec.data?.recipe || rec.text || '').trim();
                if (name && !seenRecords.has(`recipe:${name}`)) {
                    seenRecords.add(`recipe:${name}`);
                    recipes.push(name);
                }
            }
            else if (rtype === 'fact') {
                const txt = String(rec.text || rec.data?.fact || '').trim();
                if (txt && !seenRecords.has(`fact:${txt}`)) {
                    seenRecords.add(`fact:${txt}`);
                    facts.push(txt);
                }
            }
        }
        if (!recipes.length && Array.isArray(player.crafting_known)) {
            for (const r of player.crafting_known) {
                const name = String(r || '').trim();
                if (name)
                    recipes.push(name);
            }
        }
        if (!facts.length && Array.isArray(player.known)) {
            for (const f of player.known) {
                const txt = String(f || '').trim();
                if (txt)
                    facts.push(txt);
            }
        }
        if (!knownDomains.length && !blindSpots.length && !activeSkills.length && !recipes.length && !facts.length) {
            return '';
        }
        const lines = [];
        if (knownDomains.length) {
            lines.push(`Domains: ${knownDomains.join('; ')}.`);
        }
        if (activeSkills.length) {
            lines.push(`Skills: ${activeSkills.slice(0, 8).join(', ')}.`);
        }
        if (recipes.length) {
            lines.push(`Known recipes: ${recipes.slice(0, 8).join(', ')}.`);
        }
        if (facts.length) {
            lines.push(`Known facts: ${facts.slice(0, 6).join(' | ')}.`);
        }
        if (blindSpots.length) {
            lines.push(`Blind spots (ignorant): ${blindSpots.join('; ')}. You lack specialist knowledge in these areas; do not fake technical fluency in them.`);
        }
        return '\n' + lines.join('\n');
    }
    Object.assign(window.PromptBuilder, {
        buildEmotionContext,
        buildRelationshipContext,
        buildRelationshipLabel,
        relationshipGuidance,
        buildInsanityContext,
        buildEncumbranceContext,
        buildTraitBehaviorContext,
        buildSizeContext,
        buildPerceivedState,
        describeVital,
        describeVitals,
        buildPlanContext,
        naturalTimeBand,
        getTimePerceptionMode,
        describeScheduleHorizon,
        buildMosiacContext,
        buildLanguageAndLingoContext,
        buildKnowledgeAndBlindSpotsContext
    });
})();
