/**
 * prompt-builder/turn-prompts.js — Phase prompt builders (observe/decide/react).
 *
 * The highest-level layer: stitches room context + character-state fragments
 * (from context-sections.js) into the final LLM-facing prompts for each turn
 * phase. Exports merge into window.PromptBuilder.
 *
 * Load order: context-sections.js and schema-fragments.js must load BEFORE
 * this file.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 *
 * @module prompt-builder/turn-prompts — the per-phase prompt builders
 * @contributes buildReaction/Observation/Decision/ResultReaction/DashFollowUp/ChainFollowUp/Retry prompts
 * @powers the actual user messages for every agent phase (observe → decide → act → react → dash)
 * @relates stitches room-context + context-sections + schema-fragments; consumed by agent-engine
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 *
 * ---------------------------------------------------------------------------
 * PHASE MAP — what each phase outputs and who consumes it downstream.
 * (This is the thing you're usually reconstructing by reading four functions
 * — kept here as a standing reference.)
 *
 *   Phase      | Output fields                              | Consumed by
 *   -----------|----------------------------------------------|--------------------------------------
 *   reaction   | action,item,target,speech,volume,emote,       action-executor.js, memory-store.js
 *              | (memory if config.endOfTurnMemory)
 *   react      | inner_monologue,speech,volume,emote,memory     action-executor.js, memory-store.js
 *   dash       | action,target OR action:"wait"                 action-executor.js (mid-sprint chain)
 * ---------------------------------------------------------------------------
 *
 * RESOLVED (2026-09-20) — "reaction" phase memory: `includeMemory` used to add
 * the "memory" field to the JSON schema while never explaining how to fill it.
 * It is now wired, and OPT-IN: memory is normally written at the START of a
 * character's turn, so end-of-turn memory requires Settings → "End-of-turn
 * memory" (`config.endOfTurnMemory`). Off by default.
 *
 * REMOVED (2026-09-20): `buildObservationPrompt` and `buildDecisionPrompt` were
 * dead exports — defined, exported, and never called. The live turn-start call is
 * `buildReactionPrompt`, which covers both think and decide (see task-350). Both
 * builders and their exports were deleted; `git log` has them if the phase split
 * is ever revived.
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    /**
     * Assemble the shared user-message head in the NEW section order:
     * tick → personality → === YOUR STATE === → === I REMEMBER === →
     * appearance → carrying → room → exits → items → people →
     * available actions → witnessed → plan. `memoryNL` carries its own
     * "=== I REMEMBER ===" header (from buildMemoryContext).
     * @param {Object} parts - buildRoomContextParts result
     * @param {string} stateBlock - Content for the "=== YOUR STATE ===" block
     * @param {string} memoryNL - Memory context string (own header already included)
     * @returns {string} Assembled head text
     */
    function assembleMessageHead(parts, stateBlock, memoryNL) {
        const blocks = [
            parts.tickHead,
            parts.preamble,
            `=== YOUR STATE ===\n${String(stateBlock || '').trim()}`,
            String(memoryNL || '').trim(),
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
            parts.extraNote,
        ];
        return blocks.map(block => String(block || '').trim()).filter(Boolean).join('\n\n');
    }

    function _summaryLine(text) {
        // N7: RECENTLY must be a one-line summary — the previous action's full
        // output (room prose + exits) duplicates the current observation block
        // on every call. First line only; the important part is the outcome.
        const lines = String(text || '').split('\n').map(s => s.trim()).filter(Boolean);
        return lines[0] || '';
    }

    /**
     * Build the reaction prompt (non-reactive mode) — a combined think/say/do prompt.
     * This is the "single phase" mode where the character thinks, speaks, and acts in one LLM call.
     * @param {Object} player - Player data object
     * @param {Object} parts - Room context parts (buildRoomContextParts result)
     * @param {string} vitalsNL - Natural language vitals description
     * @param {string} emotionNL - Emotion context string
     * @param {string} relationshipNL - Relationship context string (relationships now live in the People list)
     * @param {string} memoryNL - Memory context string
     * @param {string} lastResult - Last action result text
     * @param {boolean} [includeMemory=false] - Whether to ask for a memory object in the response
     * @returns {string} Reaction prompt string
     */
    function buildReactionPrompt(player, parts, vitalsNL, emotionNL, relationshipNL, memoryNL, lastResult, includeMemory = false, includeFeelings = false) {
        const last = lastResult
            ? `\n\n=== RECENTLY ===\n${_summaryLine(lastResult)}`
            : '\n\n=== START ===\nThis is your first moment in this world. What do you think, say, and do?';

        const ctx = { phase: 'reaction', vitalsNL, emotionNL, relationshipNL, memoryNL };
        const context = PromptBuilder.buildContextBlock(player, ctx,
            ['perceived', 'vitals', 'encumbrance', 'emotion', 'insanity', 'trait', 'size', 'activity', 'grappled', 'ghost', 'dead']);

        // End-of-turn memory is OPTIONAL (memories normally come at turn START).
        const wantMemory = includeMemory && config.endOfTurnMemory === true;
        const memoryInstruction = wantMemory ? PromptBuilder.MEMORY_INSTRUCTION_REACT : '';

        const schemaFields = ['inner_monologue', 'action_use_on', 'speech', 'volume', 'emote'];
        if (includeFeelings) schemaFields.push('emotion_toward', 'learned_names');
        if (wantMemory) schemaFields.push('memory', 'emotion_toward', 'learned_names');

        const head = PromptBuilder.assembleMessageHead(parts, context, memoryNL);

        return `${head}${last}

First, think about what's happening around you (inner_monologue). Then decide what you do, what you say out loud, and your body language (emote) — all in ONE response. The action will be executed by the system and its result comes back in the next message — do not assume the outcome of your action in your inner monologue or speech.
${PromptBuilder.EMOTE_RULES_REACTION}${memoryInstruction}

Follow the ACTION STRUCTURE and SPEECH & VOLUME rules above in the system prompt — action/item/target fields, speech in "speech" with its volume in "volume", emote as a field on any action.
Your context's === AVAILABLE ACTIONS === section lists the actions you can take beyond what your surroundings already offer — use those verbs and act on what it names.

Respond ONLY raw JSON. Put a comma between every field. Do NOT repeat the same key twice.
Examples:
${PromptBuilder.buildJsonExample(schemaFields)}
If you say nothing but still emote:
{"inner_monologue":"...","action":"wait","speech":null,"volume":null,"item":null,"target":null,"emote":"shivers and hugs their shoulders","memory":null,"emotion":null,"learned_names":[]}
If you have no emote, omit it:
{"inner_monologue":"...","action":"look","target":"the archway","speech":null,"volume":null,"item":null,"emote":null,"memory":null,"emotion":null,"learned_names":[]}`;
    }

    /**
     * Build the result reaction prompt (reactive mode, react phase) — respond to action outcome.
     * The character processes what happened after taking an action.
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {string} roomContext - Pre-built area context string
     * @param {string} vitalsNL - Natural language vitals description
     * @param {string} emotionNL - Emotion context string
     * @param {string} relationshipNL - Relationship context string
     * @param {string} inner - Inner monologue from observation phase
     * @param {string} action - The action that was taken
     * @param {string} actionResult - The result text of the action
     * @param {string} memoryNL - Memory context string
     * @param {string} saidThisTurn - What the character already said this turn (decide phase), if any
     * @returns {string} Result reaction prompt string
     */
    function buildResultReactionPrompt(charName, player, roomContext, vitalsNL, emotionNL, relationshipNL, inner, action, actionResult, memoryNL, saidThisTurn) {
        // WHAT HAPPENED must include what the agent already SAID this turn
        // (decide phase) — otherwise the react LLM, a fresh call with no memory
        // of its own earlier speech, invents a different answer and the
        // character contradicts itself (e.g. changing its favorite color).
        const happenedLines = [];
        if (saidThisTurn) happenedLines.push(`You said: "${saidThisTurn}"`);
        if (action) happenedLines.push(`Your action: ${action}`);
        if (actionResult) happenedLines.push(PromptBuilder.frameSelfSpeech(charName, actionResult));
        const whatHappened = happenedLines.length ? happenedLines.join('\n') : 'Nothing happened.';

        const ctx = { phase: 'react', vitalsNL, emotionNL, relationshipNL, memoryNL };
        const context = PromptBuilder.buildContextBlock(player, ctx,
            ['perceived', 'vitals', 'encumbrance', 'emotion', 'insanity', 'trait', 'activity', 'ghost', 'dead']);

        // task-XXX: the react call is a fresh 2-message conversation (no decide
        // replay), so the persona must ride in THIS message — the model has no
        // other source for voice and identity.
        const persona = player?.personality
            ? `You are ${charName}. Personality: ${player.personality}`
            : '';
        const headBlocks = [
            persona,
            String(roomContext || '').trim(),
            `=== YOUR STATE ===\n${String(context || '').trim()}`,
            String(memoryNL || '').trim(),
        ];
        const head = headBlocks.filter(Boolean).join('\n\n');

        return `${head}\n\n=== WHAT HAPPENED ===\n${whatHappened}

Based on the outcome of your action, how do you react to it? 
How do you process this? What goes through your mind now?
This is the REACT phase: by default you react SILENTLY — keep it to inner_monologue and emote. Speak out loud ONLY if the situation genuinely calls for it (someone addressed you directly, something alarming or unexpected happened). Do not advance to your next planned action here — that happens next turn.
A moment has just passed — your own action barely completed. The people around you have NOT had time to react or reply yet; their silence or stillness right now means they simply haven't responded, not that they ignored you. Do not infer long stretches of time from one instant. React to what actually happened to you in this single moment.
CRITICAL: In the REACT phase you MUST NOT include "action" or "item" fields. React ONLY via inner_monologue, emote, speech, and memory. Do not attempt to take new actions.
If you do speak, put your line in the "speech" field and its volume in "volume" (see SPEECH & VOLUME rules in the system prompt).
${PromptBuilder.EMOTE_RULES_REACT}

${PromptBuilder.MEMORY_INSTRUCTION_REACT}

Respond ONLY raw JSON. Put a comma between every field. Do NOT repeat the same key twice.
If you speak:
${PromptBuilder.buildJsonExample(['inner_monologue', 'speech', 'volume', 'emote', 'memory', 'emotion_toward', 'learned_names'])}
If you stay silent but emote:
{"inner_monologue":"...","speech":null,"volume":null,"emote":"...","memory":null,"emotion":null,"learned_names":[]}
If you have nothing to react with:
{"inner_monologue":"...","speech":null,"volume":null,"emote":null,"memory":null,"emotion":null,"learned_names":[]}`;
    }

    /**
     * Build the chained follow-up prompt after an action with a CHAIN_RULES
     * entry (task-104): dash→go (the original), lead→go/approach/release,
     * grab→approach/release. One quick decision — no speech/emote/memory.
     * @param {string} charName - Character name
     * @param {string} roomContext - Pre-built area context string
     * @param {string} resultText - Result text of the source action
     * @param {string} sourceVerb - The verb that just succeeded (dash/lead/grab)
     * @param {string[]} allowedVerbs - Follow-up verbs the chain allows
     * @returns {string} Follow-up prompt string
     */
    function buildChainFollowUpPrompt(charName, roomContext, resultText, sourceVerb, allowedVerbs) {
        const verbs = (allowedVerbs && allowedVerbs.length) ? allowedVerbs.join(', ') : 'go';
        return `${roomContext}

=== CHAIN FOLLOW-UP ===
You just ${sourceVerb} — ${resultText}

You may chain ONE immediate follow-up action before your turn ends: ${verbs}.
Pick an exit or target from the context above (go/approach), release a grapple, or respond with "wait".
This is a quick decision — no speech, no emote, no memory.
Respond ONLY raw JSON, every field shown (null what you don't need):
${PromptBuilder.buildJsonExample(['full_action'])}`;
    }

    /** @deprecated Use buildChainFollowUpPrompt (dash is one CHAIN_RULES family). */
    function buildDashFollowUpPrompt(charName, roomContext, dashResult) {
        return buildChainFollowUpPrompt(charName, roomContext, dashResult, 'dashed', ['go', 'wait']);
    }

    /**
     * Invalid-action auto-retry prompt (task-361): feed back the failed action
     * and its reason, direct a different choice. Same-turn, ONE retry — the
     * character's own context prompts already describe the room; this only
     * needs the failure and the instruction, so it reuses the decide schema
     * through the normal parser.
     * @param {string} failedAction - The action string that was rejected/failed
     * @param {string} failedResult - The result/error text the engine returned
     * @returns {string} Retry prompt string
     */
    function buildRetryPrompt(failedAction, failedResult) {
        return 'Your previous action was not performed.\n'
            + `Attempted: "${failedAction}"\n`
            + `Reason: ${String(failedResult || '').trim()}\n\n`
            + 'Choose a different action instead. Do not repeat the failed action. '
            + 'If the same goal is reachable through another verb or target, use that; '
            + 'otherwise pick something else you can do right now. '
            + 'Keep the same JSON schema as a normal decision, with only action/item/target fields';
    }

    Object.assign(window.PromptBuilder, {
        assembleMessageHead,
        buildReactionPrompt,
        buildResultReactionPrompt,
        buildDashFollowUpPrompt,
        buildChainFollowUpPrompt,
        buildRetryPrompt
    });
})();
