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
        return closeness <= -75 ? 'mortal enemy' : closeness <= -50 ? 'enemy' : closeness <= -25 ? 'rival' : closeness < 0 ? 'unfriendly' : closeness === 0 ? 'neutral' : closeness <= 25 ? 'acquaintance' : closeness <= 50 ? 'friend' : closeness <= 75 ? 'close friend' : 'inseparable friend';
    }

    /**
     * Inline relationship label for the "People here" list — the type with an
     * article ("a close friend"), no score. Returns '' when there is no
     * relationship record for the other person (strangers get no label).
     * @param {Object} player - Player data object
     * @param {string} otherName - The other person's name
     * @returns {string} e.g. "a close friend", or empty string
     */
    function buildRelationshipLabel(player, otherName) {
        if (!player?.relationships || !otherName) return '';
        const relationshipObj = player.relationships[otherName];
        if (!relationshipObj || relationshipObj.closeness === undefined) return '';
        return `a ${relationshipTypeName(relationshipObj.closeness)}`;
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
            // task-94: closeness gates behavior, not just decoration — each
            // tier carries a short directive for how to act toward them.
            return `${charName} considers ${anon} a ${relationshipTypeName(closeness)} (${closeness}/100) — ${relationshipGuidance(closeness)}`;
        }).join('\n');
    }

    /**
     * Behavioral directive for a closeness score (task-94). Short on purpose:
     * one clause per present character, injected into every phase prompt.
     * @param {number} closeness - -100..100
     * @returns {string} Imperative guidance clause
     */
    function relationshipGuidance(closeness) {
        if (closeness <= -50) return 'you want them gone; refuse help, keep replies hostile or silent';
        if (closeness <= -25) return 'keep interactions cold and minimal; never turn your back on them';
        if (closeness < 0) return 'you keep your guard up; brief, wary replies';
        if (closeness <= 25) return 'polite but reserved; courtesy without warmth';
        if (closeness <= 50) return 'you are friendly; chat openly and help when asked';
        if (closeness <= 75) return 'you are glad they are here; engage warmly, share news, watch out for them';
        return 'you trust them completely; prioritize their safety, share secrets, stay close';
    }

    /**
     * Build insanity context for a character based on their Sanity vitals.
     * Returns progressively more disturbing descriptions as Sanity decreases.
     * @param {Object} player - Player data object
     * @returns {string} Insanity context string or empty string
     */
    function buildInsanityContext(player) {
        if (!player?.vitals?.Sanity) return '';
        const sanityScore = player.vitals.Sanity;
        const tiers = [
            { max: 10, instructions: '=== YOUR MIND ===\nYour sanity has shattered. Reality bends and fractures around you. You are consumed by frenzy — you trust no one, everything is a threat, and violence feels natural. Your perception of the world is deeply distorted.' },
            { max: 25, instructions: '=== YOUR MIND ===\nYour mind is fracturing. Paranoia and rage cloud your thoughts. You suspect others are plotting against you. Your emotions are volatile — anger surges without warning and you struggle to think clearly.' },
            { max: 50, instructions: '=== YOUR MIND ===\nYou feel strained and irritable. Small annoyations feel unbearable and you find yourself snapping at others. Patience is thin and the world feels hostile.' },
            { max: 75, instructions: '=== YOUR MIND ===\nA persistent sense of unease hangs over you. The dark corners of every area feel threatening. You are jumpy and distrustful.' }
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
     * Describe a character's current vital stats in natural language.
     * Covers Energy, Hunger, Thirst, Hygiene, Social, Bladder, Sanity,
     * Entertainment, and Temperature.
     * @param {Object} player - Player data object with vitals
     * @returns {string} Natural language description of vitals or empty string
     */
    function describeVitals(player) {
        if (!player?.vitals) return '';
        const vitalsData = player.vitals;
        const parts = [];
        // Tier boundaries come from VitalThresholds (task-322 R5) — the single
        // source shared with plan-tracker's criticalNeeds. The `<= 0` collapse
        // tiers are mechanical zero-states, not tunable thresholds.
        const T = window.VitalThresholds;

        // Energy
        if (vitalsData.Energy !== undefined && vitalsData.Energy <= 0) parts.push('You are collapsing from exhaustion — your legs buckle and your vision blurs.');
        else if (vitalsData.Energy !== undefined && vitalsData.Energy < T.CRITICAL) parts.push('You are exhausted. Every movement feels heavy.');
        else if (vitalsData.Energy !== undefined && vitalsData.Energy < T.WARNING) parts.push('You are getting tired. A yawn escapes you.');

        // Hunger — DRIVE: rises toward 100 (starving at max)
        if (vitalsData.Hunger !== undefined && vitalsData.Hunger >= 100) parts.push('You are starving — your stomach is a hollow knot of pain.');
        else if (vitalsData.Hunger !== undefined && vitalsData.Hunger > T.CRITICAL) parts.push('You are very hungry. Your stomach growls loudly.');
        else if (vitalsData.Hunger !== undefined && vitalsData.Hunger > T.WARNING) parts.push('You are hungry. Your stomach feels empty.');

        // Thirst — DRIVE: rises toward 100 (dehydrated at max)
        if (vitalsData.Thirst !== undefined && vitalsData.Thirst >= 100) parts.push('You are dying of thirst — your throat is cracked and dry as ash.');
        else if (vitalsData.Thirst !== undefined && vitalsData.Thirst > T.CRITICAL) parts.push('You are very thirsty. Your tongue sticks to the roof of your mouth.');
        else if (vitalsData.Thirst !== undefined && vitalsData.Thirst > T.WARNING) parts.push('You are thirsty. Your throat feels dry.');

        // Hygiene
        if (vitalsData.Hygiene !== undefined && vitalsData.Hygiene < T.CRITICAL) parts.push('You are filthy — grime and sweat cling to your skin.');
        else if (vitalsData.Hygiene !== undefined && vitalsData.Hygiene < T.WARNING) parts.push('You are dirty. Your clothes smell of sweat and exertion.');

        // Social
        if (vitalsData.Social !== undefined && vitalsData.Social < T.CRITICAL) parts.push('The loneliness is crushing. You desperately wish someone was here.');
        else if (vitalsData.Social !== undefined && vitalsData.Social < T.WARNING) parts.push('You feel isolated. The silence presses in around you.');

        // Bladder: 0 = empty (relieved), 100 = full (about to burst)
        if (vitalsData.Bladder !== undefined && vitalsData.Bladder >= T.BLADDER_URGENT) parts.push('You are about to burst — you desperately need a bathroom.');
        else if (vitalsData.Bladder !== undefined && vitalsData.Bladder >= T.BLADDER_WARN) parts.push('Your bladder is uncomfortably full. You shift your weight.');
        else if (vitalsData.Bladder !== undefined && vitalsData.Bladder >= T.BLADDER_MILD) parts.push('You could use a bathroom soon. A mild pressure builds.');

        // Sanity — progressive insanity tiers
        if (vitalsData.Sanity !== undefined && vitalsData.Sanity < T.SANITY_SHATTERED) parts.push('REALITY IS COLLAPSING — you can no longer trust what you see. Paranoia and frenzy consume you.');
        else if (vitalsData.Sanity !== undefined && vitalsData.Sanity < T.CRITICAL) parts.push('Your mind is fracturing. Rage simmers beneath the surface and you suspect everyone is against you.');
        else if (vitalsData.Sanity !== undefined && vitalsData.Sanity < T.WARNING) parts.push('You feel strained and irritable. Everything grates on your nerves.');
        else if (vitalsData.Sanity !== undefined && vitalsData.Sanity < 75) parts.push('A sense of unease lingers. The shadows seem to watch you.');

        // Entertainment — low levels drive novelty-seeking behavior
        if (vitalsData.Entertainment !== undefined && vitalsData.Entertainment < 10) parts.push('You\'re desperate for stimulation. Staying in place any longer is unbearable. Take action — go, examine, or use.');
        else if (vitalsData.Entertainment !== undefined && vitalsData.Entertainment < 25) parts.push('You\'re bored. Routine feels stifling. You\'re drawn to try something different — anything to break the monotony.');
        else if (vitalsData.Entertainment !== undefined && vitalsData.Entertainment < 50) parts.push('You\'re starting to get bored. Consider doing something new or going somewhere else.');

        // Temperature
        if (vitalsData.Temperature !== undefined) {
            if (vitalsData.Temperature < 33) parts.push('You are shivering uncontrollably — hypothermia is setting in. Your fingers are numb.');
            else if (vitalsData.Temperature < 35) parts.push('You are shivering violently from the cold. Your teeth chatter.');
            else if (vitalsData.Temperature < 36) parts.push('You are cold and shivering. A chill runs through you.');
            else if (vitalsData.Temperature > 42) parts.push('The heat is overwhelming — you are about to collapse. The world swims before your eyes.');
            else if (vitalsData.Temperature > 40) parts.push('You are dangerously overheated. Sweat pours down your face.');
            else if (vitalsData.Temperature > 38) parts.push('You are feeling very hot. You wipe sweat from your brow.');
        }

        if (parts.length === 0) return 'You feel fine — no pressing needs right now.';
        return parts.join(' ');
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
        buildTraitBehaviorContext,
        buildSizeContext,
        buildPerceivedState,
        describeVitals,
        buildPlanContext
    });
})();
