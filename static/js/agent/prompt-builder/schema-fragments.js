/**
 * prompt-builder/schema-fragments.js — Shared instructional text + JSON
 * schema fragments used across the turn-prompt builders and system prompt.
 *
 * Load this file BEFORE turn-prompts.js and system-prompt.js.
 *
 * The EMOTE_RULES_* blocks intentionally differ between phases — e.g. the
 * REACT variant references "you HAVE seen the outcome," which only makes
 * sense after an action resolves. They're kept as separate named constants
 * (rather than merged into one "generic" version) so each variant is easy to
 * find and edit without accidentally changing a different phase's wording.
 *
 * FLAG — probable copy/paste drift, not an intentional difference:
 * MEMORY_INSTRUCTION_REACTION says "not a recap"; MEMORY_INSTRUCTION_REACT
 * says "not a recap of the room". Left as two constants pending a decision —
 * search this file for "FLAG:" to find it. If it should be one string, just
 * delete one constant and repoint its usage in turn-prompts.js.
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    const MEMORY_INSTRUCTION_REACTION =
        `
memory is your subjective 1-3 sentence memory based on what just happened — your takeaway, not a recap. Set its importance 1-10 (10 = life-changing). Threats, secrets, discoveries, and meaningful people rank high. Add 1-3 single-word tags (fear, trust, mystery) — never names, items, or places. If the memory is about a specific person, add "emotions": {"who":"<what you call them>","why":"<one short line>","data":{...}} where "data" keys are one of fear, affection, disgust, anger, trust, envy, familiarity, respect, closeness, each a small value -5..+5 telling how this changed how you feel toward THAT person (+ = more of it). A scary encounter: {"fear":2,"affection":-3}. Omit "emotions" when the memory is not about someone.`;

    // FLAG: differs from MEMORY_INSTRUCTION_REACTION only by "of the room" — see file header.
    const MEMORY_INSTRUCTION_REACT =
        `
memory is your subjective 1-3 sentence memory based on what just happened — your takeaway, not a recap of the room. Set its importance 1-10 (10 = life-changing). Threats, secrets, discoveries, and meaningful people rank high. Add 1-3 single-word tags (fear, trust, mystery) — never names, items, or places. If the memory is about a specific person, add "emotions": {"who":"<what you call them>","why":"<one short line>","data":{...}} where "data" keys are one of fear, affection, disgust, anger, trust, envy, familiarity, respect, closeness, each a small value -5..+5 telling how this changed how you feel toward THAT person (+ = more of it). A scary encounter: {"fear":2,"affection":-3}. Omit "emotions" when the memory is not about someone.`;

    const EMOTE_RULES_REACTION =
        `emote is body language — HOW you do something, or something you do to yourself or someone else (a kiss, a handshake, running a hand through your hair, reaching for the key). It shows the gesture and intention, never the outcome: if someone high-fives you, respond in kind or not — but you cannot claim your action succeeded before the system resolves it.`;

    const EMOTE_RULES_DECIDE =
        `Emote is body language — HOW you do something, or something you do to yourself or someone else (a kiss, a handshake, running a hand through your hair, reaching for the key). It describes the gesture and intention, never the outcome — you cannot claim an action succeeded in your emote. If you want the result of an action, take the action: reach for the key with an emote, but use "take" to actually pick it up. If someone high-fives you, respond in kind or not — your choice.`;

    const EMOTE_RULES_REACT =
        `Emote is body language — HOW you do something, or something you do to yourself or someone else (a kiss, a handshake, wincing, running a hand through your hair). In this REACT phase you HAVE seen the outcome, so your emote may reflect it (wincing from a hit, beaming after a success) — but never invent a new outcome; respond to what actually happened.`;

    const EMOTE_RULES_SYSTEM =
        `emote is body language — HOW you do something, or something you do to yourself or someone else (a kiss, a handshake, running a hand through your hair, reaching for the key). It shows the gesture and intention, never the outcome — the system resolves what actually happens. If you want the result of an action, take the action: reach for the key with an emote, but use "take" to actually pick it up. If you want to GRAB, PULL, or DRAG someone, use the "grab" action (they may resist with a save) — never narrate grabbing another character in your emote. If you are being held, use "escape" to break free. Write emotes as bare verb phrases (e.g. "lean in close", "bite your lip", "glance at the door") — never include your own character name.`;

    /**
     * JSON example-field fragments, keyed by name. Each builder picks an
     * ordered list of keys instead of hand-typing the schema string, so a
     * schema change (e.g. adding a field inside "memory") happens in one
     * place and can't drift out of sync between phases by accident.
     */
    const JSON_FIELDS = {
        inner_monologue: '"inner_monologue":"..."',
        action_use_on: '"action":"use_on","item":"...","target":"..."',
        speech: '"speech":"..."',
        volume: '"volume":"say"',
        emote: '"emote":"..."',
        memory: '"memory":{"text":"...","importance":7,"tags":["..."]}',
        memory_emotions: '"memory":{"text":"...","importance":7,"emotions":{"who":"the man","why":"he blocked my way","data":{"fear":2,"affection":-4,"disgust":1,"anger":1}}}',
        emotion: '"emotion":{"label":"afraid","intensity":6,"toward":"..."}',
        learned_names: '"learned_names":["Rosa"]',
        emotion_toward: '"emotion":{"label":"unsettled","intensity":6,"toward":"the man"}',
        action_simple: '"action":"...","speech":"...","volume":"say","emote":"..."',
        dash_go: '"action":"go","target":"<exit name from the exits above>"',
        dash_wait: '"action":"wait"',
        silent_action: '"action":"wait"',
    };

    /** Build a pretty-printed JSON example string from ordered JSON_FIELDS keys. */
    function buildJsonExample(fieldKeys) {
        const pairs = fieldKeys.map(k => JSON_FIELDS[k]).filter(Boolean);
        const lines = pairs.map((p, i) => {
            const comma = i < pairs.length - 1 ? ',' : '';
            return '    ' + p + comma;
        });
        return '{\n' + lines.join('\n') + '\n}';
    }

    Object.assign(window.PromptBuilder, {
        MEMORY_INSTRUCTION_REACTION,
        MEMORY_INSTRUCTION_REACT,
        EMOTE_RULES_REACTION,
        EMOTE_RULES_DECIDE,
        EMOTE_RULES_REACT,
        EMOTE_RULES_SYSTEM,
        JSON_FIELDS,
        buildJsonExample,
    });
})();
