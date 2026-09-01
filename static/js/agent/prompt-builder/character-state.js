/**
 * prompt-builder/character-state.js — Character state context builders.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). Builds the
 * "=== YOUR STATE ===" fragments: vitals, emotion, relationship, insanity,
 * trait behavior, size, perceived condition, and the plan context. Exports
 * merge into window.PromptBuilder — see helpers.js header for the pattern.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    /**
     * Natural-language encumbrance context (task-156 presentation): the agent
     * should know its load is heavy BEFORE it tries to move — no raw numbers
     * (those stay in the inspectors). Mirrors movement.py's tiers:
     * <50% silent, 50-80% noticeable, 80-100% heavy + no dash, >=100% blocked.
     * @param {Object} player - Player data object
     * @returns {string} Encumbrance context line, or '' when unloaded
     */
    function buildEncumbranceContext(player) {
        if (!player) return '';
        const current = parseFloat(player.current_carry_weight);
        const capacity = parseFloat(player.max_carry_capacity);
        if (isNaN(current) || isNaN(capacity) || capacity <= 0) return '';
        const ratio = current / capacity;
        if (ratio >= 1.0) return '\n⚠️ You are carrying far more than you can bear — you cannot move until you drop or stow something.';
        if (ratio >= 0.8) return '\nYou are carrying about as much as you can manage — moving is exhausting and you cannot dash.';
        if (ratio >= 0.5) return '\nYour load is starting to drag on you — moving costs noticeably more energy.';
        return '';
    }

    /**
     * Build emotion context for a character.
     * Returns a string describing their current emotional state if it's non-neutral.
     * @param {Object} player - Player data object
     * @returns {string} Emotion description string or empty string
     */
    function buildEmotionContext(player) {
        // Task-96: multi-dimensional affect map — the backend renders the
        // first-person band phrases (single source of truth in
        // engine/emotion.py) and ships them as `emotions_description`.
        if (typeof player?.emotions_description === 'string' && player.emotions_description) {
            return `\nMood: ${player.emotions_description}`;
        }
        // Legacy single-slot fallback for old saves.
        if (!player?.emotion?.description || player.emotion.current === 'neutral' || (player.emotion.intensity || 0) < 0.1) return '';
        return `\n${player.emotion.description}`;
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
     * Inline relationship label for the "People here" list — the type with an
     * article ("a close friend"), no score. Returns '' when there is no
     * relationship record for the other person (strangers get no label).
     * @param {Object} player - Player data object
     * @param {string} otherName - The other person's name
     * @returns {string} e.g. "a close friend", or empty string
     */
    // Article handling for a relationship label — "a close friend" but
    // "an inseparable" (vowel-initial names). Keeps prompt text grammatical.
    function withArticle(name) {
        return /^[aeiou]/i.test(name) ? `an ${name}` : `a ${name}`;
    }

    function buildRelationshipLabel(player, otherName) {
        if (!player?.relationships || !otherName) return '';
        const relationshipObj = player.relationships[otherName];
        if (!relationshipObj || relationshipObj.closeness === undefined) return '';
        // N5: near-zero closeness is not a relationship worth labeling —
        // "a neutral" rendered as garbage; silence reads better ("the woman",
        // no label). The behavioral guidance line still applies separately.
        if (Math.abs(relationshipObj.closeness) <= 10) return '';
        return withArticle(relationshipTypeName(relationshipObj.closeness));
    }

    /**
     * Build relationship context showing the character's relationships with others in the area.
     * @param {Object} player - Player data object
     * @param {string} charName - Character name (to exclude self)
     * @returns {string} Formatted relationship string or empty string
     */
    function buildRelationshipContext(player, charName) {
        if (!player?.relationships) return '';
        const others = worldState?.data?.players_in_area?.filter(other => other.name !== charName) || [];
        if (others.length === 0) return '';
        return '\n' + others.map(other => {
            const relationshipObj = player.relationships[other.name];
            const allPlayers = worldState?.data?.players || {};
            const otherDesc = allPlayers[other.name]?.description || '';
            const anon = PromptBuilder.anonymousName(charName, other.name, otherDesc);
            if (!relationshipObj) return `${charName} hasn't met ${anon}`;
            const closeness = relationshipObj.closeness;
            // task-350: when a derived read exists (experience-driven trust/
            // fear/consent), surface its summary + role instead of just the raw
            // closeness label. Falls back to the closeness guidance below.
            if (relationshipObj.summary && relationshipObj.role) {
                const read = relationshipObj.summary;
                const sign = (relationshipObj.consent !== undefined && relationshipObj.consent <= -0.3) ? ' (you would pull away)' : (relationshipObj.consent >= 0.3 ? ' (you would let them close)' : '');
                return `${charName} reads ${anon} as ${relationshipObj.role}: ${read}${sign}`;
            }
            // task-94: closeness gates behavior, not just decoration — each
            // tier carries a short directive for how to act toward them.
            return `${charName} considers ${anon} ${withArticle(relationshipTypeName(closeness))} (${closeness}/100) — ${relationshipGuidance(closeness)}`;
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
        if (closeness <= -75) return 'you despise them; drive them off, refuse any help, show open hostility';
        if (closeness <= -50) return 'you want them gone; refuse help, keep replies hostile or silent';
        if (closeness <= -25) return 'keep interactions cold and minimal; never turn your back on them';
        if (closeness < 0) return 'you keep your guard up; brief, wary replies';
        if (closeness === 0) return 'you have no strong feelings; polite, indifferent';
        if (closeness <= 25) return 'polite but reserved; courtesy without warmth';
        if (closeness <= 50) return 'you are friendly; chat openly and help when asked';
        if (closeness <= 75) return 'you are glad they are here; engage warmly, share news, watch out for them';
        return 'you trust them completely; prioritize their safety, share secrets, stay close';
    }

    /**
     * Build insanity context for a character based on their Sanity vitals.
     * Returns progressively more STRESSED descriptions as Sanity decreases.
     * Task-328: base sanity is a stress/composure curve — no horror/madness
     * nouns (shadows, dark corners, reality bending). Delusions, paranoia and
     * madness belongs to named conditions (poisoned/drugged/cursed), which
     * carry their own symptom text.
     * @param {Object} player - Player data object
     * @returns {string} Insanity context string or empty string
     */
    function buildInsanityContext(player) {
        if (!player?.vitals?.Sanity) return '';
        const sanityScore = player.vitals.Sanity;
        const tiers = [
            { max: 10, instructions: '=== YOUR MIND ===\nBarely holding it together. Every decision feels heavier than it should, and you keep second-guessing yourself.' },
            { max: 25, instructions: '=== YOUR MIND ===\nNerves frayed raw. You flinch at small sounds and snap at small annoyances — your composure is shot.' },
            { max: 50, instructions: '=== YOUR MIND ===\nYou feel strained and irritable. Patience is thin and everything grates on your nerves.' },
            { max: 75, instructions: '=== YOUR MIND ===\nA low hum of unease you can\'t quite shake. You keep double-checking things.' }
        ];
        for (const tier of tiers) {
            if (sanityScore < tier.max) return '\n' + tier.instructions;
        }
        return '';
    }

    /**
     * Build trait behavior hints for a character.
     * @param {Object} player - Player data object
     * @returns {string} Trait behavior context string or empty string
     */
    function buildTraitBehaviorContext(player) {
        if (!player) return '';
        const traitHints = [];
        // Trait schema v2: data-driven behavior_prompt lines from the backend
        for (const prompt of (player.trait_behavior || []).filter(Boolean)) {
            traitHints.push(prompt);
        }
        // Legacy hardcoded hints for exploration traits without a behavior_prompt
        const t = player.traits || {};
        if (t.impatient) traitHints.push('You are impatient — you act quickly without overthinking.');
        if (t.patient) traitHints.push('You are patient — you can tolerate waiting and rarely act impulsively.');
        if (t.curious) traitHints.push('You are curious — drawn to examine things and explore unfamiliar places.');
        if (t.adventurous) traitHints.push('You are adventurous — willing to take risks to seek new experiences.');
        if (t.homebody) traitHints.push('You are a homebody — you prefer familiar surroundings and are reluctant to leave.');
        if (t.wanderlust) traitHints.push('You have wanderlust — you feel restless staying in one place too long and prefer to keep moving.');
        return traitHints.length ? '\n' + traitHints.join('\n') : '';
    }

    /**
     * Build the size context for a character based on their size trait.
     * @param {Object} player - Player data object
     * @returns {string} Size context string or empty string
     */
    function buildSizeContext(player) {
        if (!player?.traits) return '';
        const sizeId = Object.keys(player.traits).find(k => k.startsWith('size_'));
        if (!sizeId) return '';
        const sizes = { tiny: 'tiny', small: 'small', normal: 'normal-sized', huge: 'huge', giant: 'giant', titanic: 'titanic' };
        const label = sizes[sizeId.slice(5)] || '';
        if (!label) return '';
        return `\nSize: You are ${label}. Some passages are too tight for you (crawl or find another way), and climb/jump attempts may fail.`;
    }

    /**
     * Perceived condition lines — symptoms/descriptions, never raw ids.
     * Hidden conditions (poisoned/sick/charmed) only reveal what their
     * progression-keyed symptoms let the character feel.
     */
    function buildPerceivedState(player) {
        const perceived = (player && player.perceived_conditions) || [];
        if (perceived.length) return '\nCondition: ' + perceived.join('; ') + '.';
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
        if (!state) return null;
        const areaName = player?.current_area || state.current_area || '';
        const area = (state.areas && state.areas[areaName]) || null;
        const others = (state.players_in_area || [])
            .filter(p => p && p.name && String(p.name) !== String(charName));
        const present = new Set(others.map(o => String(o.name).toLowerCase()));
        const hearing = player?.recent_hearing || [];
        // Someone present has spoken to/near the character recently.
        const inConversation = hearing.some(h =>
            h && h.type !== 'sound_source' && present.has(String(h.speaker || '').toLowerCase()));
        // A line aimed directly at the character (name/pronoun), not room noise.
        const addressed = hearing.some(h => {
            if (!h || h.type === 'sound_source') return false;
            const t = PromptBuilder.classifySpeechType(h.text, charName, player);
            return t === 'addressed_to_you' || t === 'to_you';
        });
        let areaItems = [];
        if (areaName && typeof worldState?.getItemsInArea === 'function') {
            try { areaItems = worldState.getItemsInArea(areaName) || []; } catch (e) { /* ignore */ }
        }
        const tagsOf = (it) => {
            const t = it.properties?.tags;
            return Array.isArray(t) ? t.map(String) : String(t || '').split(',').map(s => s.trim().toLowerCase());
        };
        const actionsOf = (it) => {
            const a = it.properties?.actions;
            return Array.isArray(a) ? a.map(String) : String(a || '').split(',').map(s => s.trim().toLowerCase());
        };
        const foodish = areaItems.filter(it =>
            tagsOf(it).includes('food') || actionsOf(it).includes('eat'));
        const drinkish = areaItems.filter(it =>
            tagsOf(it).includes('drink') || actionsOf(it).includes('drink'));
        return {
            company: others.length,
            alone: others.length === 0,
            inConversation,
            addressed,
            noise: String(area?.environment?.noise || '').toLowerCase(),
            areaTags: Array.isArray(area?.tags) ? area.tags : [],
            foodVisible: foodish.length > 0,
            drinkVisible: drinkish.length > 0
        };
    }

    /**
     * Natural-language description for a SINGLE vital (task-337).
     * Handles inverted (drive) polarity for Hunger/Thirst/Bladder —
     * high value = urgent for drives, low value = urgent for reserves.
     * @param {Object} vitals - Player vitals object (Capitalized keys)
     * @param {string} key - Vital name (e.g. 'Hunger', 'Energy')
     * @param {Object} [scene] - Optional scene facts from _vitalsScene (task-327)
     * @returns {string} First-person NL description, or '' if healthy/undefined
     */
    function describeVital(vitals, key, scene) {
        if (!vitals || vitals[key] === undefined || vitals[key] === null) return '';
        const T = window.VitalThresholds;
        const v = Number(vitals[key]) || 0;
        switch (key) {
            case 'Energy':
                if (v <= 0) return 'You are collapsing from exhaustion — your legs buckle and your vision blurs.';
                if (v < T.CRITICAL) return 'You are exhausted. Every movement feels heavy.';
                if (v < T.WARNING) return 'You are getting tired. A yawn escapes you.';
                return '';
            // drives (task-337): high value = urgent, 0 = satisfied
            case 'Hunger':
                if (v >= 100) return 'You are starving — your stomach is a hollow knot of pain.';
                if (v > T.WARNING) {
                    if (scene?.foodVisible) return 'You are very hungry. Your stomach growls loudly — the food nearby is all you can think about.';
                    return 'You are very hungry. Your stomach growls loudly.';
                }
                if (v > T.CRITICAL) {
                    if (scene?.foodVisible) return 'You are hungry. The food you can see is all you can think about.';
                    return 'You are hungry. Your stomach feels empty.';
                }
                return '';
            case 'Thirst':
                if (v >= 100) return 'You are dying of thirst — your throat is cracked and dry as ash.';
                if (v > T.WARNING) {
                    if (scene?.drinkVisible) return 'You are very thirsty. Your tongue sticks to the roof of your mouth — the drink nearby is all you can think about.';
                    return 'You are very thirsty. Your tongue sticks to the roof of your mouth.';
                }
                if (v > T.CRITICAL) {
                    if (scene?.drinkVisible) return 'You are thirsty. The drink you can see is all you can think about.';
                    return 'You are thirsty. Your throat feels dry.';
                }
                return '';
            case 'Hygiene':
                if (v < T.CRITICAL) return 'You are filthy — grime and sweat cling to your skin.';
                if (v < T.WARNING) return 'You are dirty. Your clothes smell of sweat and exertion.';
                return '';
            case 'Social':
                // Context-aware (task-327): isolation wording must not contradict
                // an occupied room, a conversation, or a noisy scene.
                // task-353 §5: behavioral gate flags steer the LLM's action
                // choices, not just narration.
                if (v < T.CRITICAL) {
                    const base = (scene && !scene.alone)
                        ? 'The loneliness is crushing even with people around — it feels like no one is truly there with you.'
                        : 'The loneliness is crushing. You desperately wish someone was here.';
                    return base + ' [social_need: desperate][social_breakdown: your mind is fraying from isolation]';
                }
                if (v < T.WARNING) {
                    let base = '';
                    if (scene && scene.addressed) base = 'You hang on their words a little too much.';
                    else if (scene && !scene.alone) base = 'Being around people feels harder than it should today.';
                    else if (scene && scene.noise && scene.noise !== 'quiet' && scene.noise !== 'silence' && scene.noise !== 'silent') base = 'You feel cut off from everyone even as the noise hums around you.';
                    else base = 'You feel isolated. The silence presses in around you.';
                    return base + ' [social_need: desperate: find people, speak, connect]';
                }
                if (v < T.WARNING) {
                    return 'You are getting lonely. [social_need: moderate: consider speaking to someone]';
                }
                return '';
            case 'Bladder':
                if (v >= T.BLADDER_URGENT) return 'You are about to burst — you desperately need a bathroom.';
                if (v >= T.BLADDER_WARN) return 'Your bladder is uncomfortably full. You shift your weight.';
                if (v >= T.BLADDER_MILD) return 'You could use a bathroom soon. A mild pressure builds.';
                return '';
            case 'Sanity':
                // Task-328: neutral stress curve — composure erosion, never
                // madness/horror imagery (that belongs to named conditions).
                if (v < T.SANITY_SHATTERED) return 'Barely holding it together. Every decision feels heavier than it should, and you keep second-guessing yourself.';
                if (v < T.CRITICAL) return 'Nerves frayed raw. You flinch at small sounds and snap at small annoyances.';
                if (v < T.WARNING) return 'You feel strained and irritable. Patience is thin and everything grates.';
                if (v < 75) return 'A creeping sense that something is off, even if you can\'t name it.';
                return '';
            case 'Entertainment':
                if (v < 10) return 'You\'re desperate for stimulation. Staying in place any longer is unbearable. Take action — go, examine, or use.';
                if (v < 25) return 'You\'re bored. Routine feels stifling. You\'re drawn to try something different — anything to break the monotony.';
                if (v < 50) return 'You\'re starting to get bored. Consider doing something new or going somewhere else.';
                return '';
            case 'Temperature':
                if (v < 33) return 'You are shivering uncontrollably — hypothermia is setting in. Your fingers are numb.';
                if (v < 35) return 'You are shivering violently from the cold. Your teeth chatter.';
                if (v < 36) return 'You are cold and shivering. A chill runs through you.';
                if (v > 42) return 'The heat is overwhelming — you are about to collapse. The world swims before your eyes.';
                if (v > 40) return 'You are dangerously overheated. Sweat pours down your face.';
                if (v > 38) return 'You are feeling very hot. You wipe sweat from your brow.';
                return '';
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
     * @param {Object} [state] - /api/state payload — optional scene context
     *   for context-aware prose (task-327; bare calls use the old wording)
     * @param {string} [charName] - Character name, used for scene context
     * @returns {string} Natural language description of vitals or empty string
     */
    function describeVitals(player, state, charName) {
        if (!player?.vitals) return '';
        const vitalsData = player.vitals;
        const scene = _vitalsScene(state, charName, player);
        const order = ['Energy', 'Hunger', 'Thirst', 'Hygiene', 'Social', 'Bladder',
                       'Sanity', 'Entertainment', 'Temperature'];
        const parts = [];
        for (const key of order) {
            if (vitalsData[key] !== undefined) {
                const desc = describeVital(vitalsData, key, scene);
                if (desc) parts.push(desc);
            }
        }
        for (const key of Object.keys(vitalsData)) {
            if (key.startsWith('Max_') || order.includes(key)) continue;
            const desc = describeVital(vitalsData, key, scene);
            if (desc) parts.push(desc);
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
            if (player.conditions.satisfied) lines.push('A deep, warm satisfaction settles over you.');
            else {
                if (player.conditions.overstimulated) lines.push('Every nerve is raw — even light touch is almost too much.');
                if (player.conditions.frantic) lines.push('You need release so badly it is hard to think.');
                else if (player.conditions.highly_aroused) lines.push('You are aching with need, barely in control.');
                else if (player.conditions.aroused) lines.push('Your body hums with want; your thoughts keep drifting.');
                else if (player.conditions.warming_up) lines.push('A slow warmth is building in you.');
            }
            if (player.conditions.nipple_hard) lines.push('Your nipples are stiff and sensitive against the fabric.');
            if (player.conditions.wetness) lines.push('You are wet — your body is making itself obvious.');
            if (lines.length) out = (out ? out + ' ' : '') + lines.join(' ');
        }
        return out;
    }

    /**
     * Build the plan context string for a character, showing their current plan steps.
     * @param {string} charName - Character name
     * @returns {string} Formatted plan string or empty string
     */
    function buildPlanContext(charName) {
        const agentPlans = window.VW?.agent?._plans;
        const plan = agentPlans?.[charName];
        if (plan?.length) {
            const progress = window.VW?.agent?._planProgress?.[charName] || 0;
            const failures = window.VW?.agent?._planFailures?.[charName] || {};
            const lines = plan.map((step, stepIndex) => {
                if (stepIndex < progress) return `${stepIndex + 1}. ${step} (done)`;
                if (stepIndex === progress) return `${stepIndex + 1}. ${step} (CURRENT)`;
                return `${stepIndex + 1}. ${step}`;
            });
            let out = '\n=== YOUR PLAN ===\n' + lines.join('\n');
            const blocked = Object.entries(failures)
                .filter(([stepIndex]) => Number(stepIndex) < progress)
                .map(([, count]) => count);
            const hasBlocked = blocked.length > 0 && blocked.some(c => c >= 3);
            if (hasBlocked && plan[progress]) {
                out += `\n⚠️ Your current step "${plan[progress]}" has failed repeatedly — it may not be achievable. If so, move on to another goal.`;
            }
            return out;
        }
        return '';
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
        buildPlanContext
    });
})();
