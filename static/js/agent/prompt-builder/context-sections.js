/**
 * prompt-builder/context-sections.js — Shared context-fragment registry.
 *
 * Single source of truth for the small pieces of text ("sections") that get
 * stitched into the "=== YOUR STATE ===" block of every turn prompt. Each
 * turn-prompt builder in turn-prompts.js picks an ORDERED LIST of section
 * keys instead of hand-concatenating template literals — so "what's included
 * in which prompt, and in what order" is a one-line array you can diff at a
 * glance, and adding a new fragment (e.g. a weather effect) means adding one
 * entry here instead of touching every builder function.
 *
 * Load this file AFTER helpers.js and character-state.js, BEFORE
 * turn-prompts.js and system-prompt.js.
 *
 * `ctx` is a small per-call bag of the strings a section might need
 * (vitalsNL, emotionNL, relationshipNL, memoryNL, phase, ...). See the top of
 * each builder in turn-prompts.js for exactly what it passes in.
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    // Ghost/dead flavor text differs slightly per phase — reaction spells out
    // the DC 15 check, decide is terse, observe/react are plain restatements.
    // Keyed by the `phase` string each builder passes in ctx.phase.
    const GHOST_TEXT = {
        reaction: 'You are a ghost. You can move and observe but physical actions require a DC 15 check.',
        observe: 'You are a ghost.',
        decide: 'Ghost: physical actions DC 15.',
        react: 'You are a ghost.',
    };
    const DEAD_TEXT = {
        reaction: 'You are dead.',
        observe: 'You are dead. You can only observe.',
        decide: 'Cannot act.',
        react: 'You are dead.',
    };

    // Plan-guidance text also differs by phase: observe just prompts
    // reflection ("how does this relate to your plan?"), decide is a
    // directive to actually follow it. Only these two phases use it — react
    // and the combined reaction prompt don't check for a plan at all.
    const PLAN_TEXT = {
        observe: '\nYou have a plan. How do your current observations relate to it?',
        decide: '\n=== PLAN FOLLOW ===\nFollow your plan. Your next action should be the next step in your plan above. Only deviate if circumstances have fundamentally changed (new threat, blocked path, discovered critical info).',
    };

    const CONTEXT_SECTIONS = {
        vitals: (p, ctx) => ctx.vitalsNL || '',
        emotion: (p, ctx) => ctx.emotionNL || '',
        insanity: (p) => PromptBuilder.buildInsanityContext(p),
        relationship: (p, ctx) => ctx.relationshipNL || '',
        trait: (p) => PromptBuilder.buildTraitBehaviorContext(p),
        size: (p) => PromptBuilder.buildSizeContext(p),
        memory: (p, ctx) => ctx.memoryNL || '',
        perceived: (p) => PromptBuilder.buildPerceivedState(p),
        activity: (p) => p.activity ? `\nActivity: ${PromptBuilder.describeActivity(p.activity)}` : '',
        grappled: (p) => p.grappled_by
            ? `\n⚠️ You are being held by ${p.grappled_by}. You can try to break free with "escape" (STR save), or go along. You cannot move on your own while held.`
            : '',
        ghost: (p, ctx) => (p.state === 'dead' && config.ghostMode) ? `\n⚠️ ${GHOST_TEXT[ctx.phase]}` : '',
        dead: (p, ctx) => (p.state === 'dead' && !config.ghostMode) ? `\n${DEAD_TEXT[ctx.phase]}` : '',
    };

    /**
     * Assemble a context block from an ordered list of section keys.
     * @param {Object} player
     * @param {Object} ctx - per-call fragments: { phase, vitalsNL, emotionNL, relationshipNL, memoryNL }
     * @param {string[]} sections - ordered CONTEXT_SECTIONS keys
     * @returns {string}
     */
    function buildContextBlock(player, ctx, sections) {
        return sections.map(key => {
            const fn = CONTEXT_SECTIONS[key];
            if (!fn) {
                console.warn(`[PromptBuilder] Unknown context section: "${key}"`);
                return '';
            }
            return fn(player, ctx);
        }).join('');
    }

    /**
     * Plan-guidance text for phases that check it (observe, decide).
     * Returns '' if the character has no active plan.
     * @param {Object} player
     * @param {'observe'|'decide'} phase
     */
    function buildPlanGuide(player, phase) {
        if (!PLAN_TEXT[phase]) {
            console.warn(`[PromptBuilder] buildPlanGuide called for phase "${phase}" with no plan text defined`);
            return '';
        }
        return PromptBuilder.hasPlan(player.name) ? PLAN_TEXT[phase] : '';
    }

    Object.assign(window.PromptBuilder, {
        CONTEXT_SECTIONS,
        buildContextBlock,
        buildPlanGuide,
    });
})();
