/**
 * prompt-builder/turn-prompts.js - Phase prompt builders (observe/decide/react).
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
 * @module prompt-builder/turn-prompts - the per-phase prompt builders
 * @contributes buildReaction/Observation/Decision/ResultReaction/DashFollowUp/ChainFollowUp/Retry prompts
 * @powers Narration, The human turn - the actual user messages for every agent phase (observe → decide → act → react → dash)
 * @relates stitches room-context + context-sections + schema-fragments; consumed by agent-engine
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 *
 * ---------------------------------------------------------------------------
 * PHASE MAP - what each phase outputs and who consumes it downstream.
 * (This is the thing you're usually reconstructing by reading four functions
 * - kept here as a standing reference.)
 *
 *   Phase      | Output fields                              | Consumed by
 *   -----------|----------------------------------------------|--------------------------------------
 *   reaction   | action,item,target,speech,volume,emote,       action-executor.js, memory-store.js
 *              | (memory if config.endOfTurnMemory)
 *   react      | inner_monologue,speech,volume,emote,memory     action-executor.js, memory-store.js
 *   dash       | action,target OR action:"wait"                 action-executor.js (mid-sprint chain)
 * ---------------------------------------------------------------------------
 *
 * RESOLVED (2026-09-20) - "reaction" phase memory: `includeMemory` used to add
 * the "memory" field to the JSON schema while never explaining how to fill it.
 * It is now wired, and OPT-IN: memory is normally written at the START of a
 * character's turn, so end-of-turn memory requires Settings → "End-of-turn
 * memory" (`config.endOfTurnMemory`). Off by default.
 *
 * REMOVED (2026-09-20): `buildObservationPrompt` and `buildDecisionPrompt` were
 * dead exports - defined, exported, and never called. The live turn-start call is
 * `buildReactionPrompt`, which covers both think and decide (see task-350). Both
 * builders and their exports were deleted; `git log` has them if the phase split
 * is ever revived.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    // Types declared inside the IIFE body so the file's first statement stays a
    // value declaration - moving them above would make the leading @module JSDoc
    // type-only and drop it from the emitted .js (see tools/ts_convert.py header_survived).
    interface RoomContextParts {
        tickHead?: string;
        preamble?: string;
        appearance?: string;
        carrying?: string;
        leadIn?: string;
        roomBody?: string;
        exits?: string;
        items?: string;
        people?: string;
        availableActions?: string;
        witnessed?: string;
        conversation?: string;
        plan?: string;
        extraNote?: string;
    }
    interface PlayerData {
        name?: string;
        state?: string;
        traits?: Record<string, unknown>;
        personality?: string;
        activity?: unknown;
        grappled_by?: unknown;
    }

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
    function assembleMessageHead(parts: RoomContextParts, stateBlock: string, memoryNL: string) {
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

    function _summaryLine(text: string) {
        // N7: RECENTLY must be a one-line summary - the previous action's full
        // output (room prose + exits) duplicates the current observation block
        // on every call. First line only; the important part is the outcome.
        const lines = String(text || '').split('\n').map(s => s.trim()).filter(Boolean);
        if (!lines.length) return '';
        // task-479: a dice breakdown must survive even when it is not the first
        // line. Otherwise the model narrates the outcome ("You fail to climb")
        // with no idea what was rolled, and cannot explain it. Keep the first
        // line as the outcome and prepend the check line.
        const check = lines.find(l => /^\[(Skill Check|Save|Check|Grab)\b/.test(l));
        if (check && check !== lines[0]) return `${check} - ${lines[0]}`;
        return lines[0];
    }

    /**
     * Build the reaction prompt (non-reactive mode) - a combined think/say/do prompt.
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
    function buildReactionPrompt(player: PlayerData, parts: RoomContextParts, vitalsNL: string, emotionNL: string, relationshipNL: string, memoryNL: string, lastResult: string, includeMemory = false, includeFeelings = false) {
        const last = lastResult
            ? `\n\n=== RECENTLY ===\n${_summaryLine(lastResult)}`
            : '\n\n=== START ===\nThis is your first moment in this world. What do you think, say, and do?';

        const ctx = { phase: 'reaction', vitalsNL, emotionNL, relationshipNL, memoryNL };
        const context = PromptBuilder.buildContextBlock(player, ctx,
            ['perceived', 'vitals', 'encumbrance', 'emotion', 'insanity', 'trait', 'size', 'activity', 'grappled', 'slots', 'mosiac', 'ghost', 'dead']);

        // End-of-turn memory is OPTIONAL (memories normally come at turn START).
        const wantMemory = includeMemory && config.endOfTurnMemory === true;
        const memoryInstruction = wantMemory ? PromptBuilder.MEMORY_INSTRUCTION_REACT : '';

        const schemaFields = ['inner_monologue', 'action_use_on', 'speech', 'volume', 'emote'];
        if (includeFeelings) schemaFields.push('emotion_toward', 'learned_names');
        if (wantMemory) schemaFields.push('memory', 'emotion_toward', 'learned_names');

        // Fix #7: explicit budget guard in decide phase (includeMemory=false, includeFeelings=true)
        const isDecidePhase = !wantMemory && includeFeelings;
        const budgetGuard = isDecidePhase
            ? '\n\n=== BUDGET CHECK ===\nBefore choosing an action, verify the === ACTIONS LEFT THIS TURN === line in your context. If it says "major 0", you CANNOT use major actions (go, dash, examine, take, use, eat, drink, attack, etc.). You MUST choose a minor/free action, speak, or "wait". Violating this wastes your turn.'
            : '';

        const head = PromptBuilder.assembleMessageHead(parts, context, memoryNL);

        return `${head}${last}${budgetGuard}

First, think about what's happening around you (inner_monologue). Then decide what you do, what you say out loud, and your body language (emote) - all in ONE response. The action will be executed by the system and its result comes back in the next message - do not assume the outcome of your action in your inner monologue or speech.${memoryInstruction}

Follow the standing ACTION, SPEECH & VOLUME, and JSON rules in your system prompt.
Your context's === AVAILABLE ACTIONS === lists verbs currently available beyond your surroundings.

Respond with ONLY a single raw JSON object matching this schema:
${PromptBuilder.buildJsonExample(schemaFields)}`;
    }

    /**
     * Build the result reaction prompt (reactive mode, react phase) - respond to action outcome.
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
     * @param {string} saidThisTurn - What the character already said this turn (decide phase), if *FIX*
     * @returns {string} Result reaction prompt string
     */
    function buildResultReactionPrompt(charName: string, player: PlayerData, roomContext: string, vitalsNL: string, emotionNL: string, relationshipNL: string, inner: string, action: string, actionResult: string, memoryNL: string, saidThisTurn: string) {
        // WHAT HAPPENED must include what the agent already SAID this turn
        // (decide phase) - otherwise the react LLM, a fresh call with no memory
        // of its own earlier speech, invents a different answer and the
        // character contradicts itself (e.g. changing its favorite color).
        const happenedLines = [];
        if (saidThisTurn) happenedLines.push(`You said: "${saidThisTurn}"`);
        if (action) happenedLines.push(`Your action: ${action}`);
        if (actionResult) happenedLines.push(PromptBuilder.frameSelfSpeech(charName, actionResult));
        const whatHappened = happenedLines.length ? happenedLines.join('\n') : 'Nothing happened.';

        const ctx = { phase: 'react', vitalsNL, emotionNL, relationshipNL, memoryNL };
        const context = PromptBuilder.buildContextBlock(player, ctx,
            ['perceived', 'vitals', 'encumbrance', 'emotion', 'insanity', 'trait', 'activity', 'slots', 'ghost', 'dead']);

        // task-XXX: the react call is a fresh 2-message conversation (no decide
        // replay), so the persona must ride in THIS message - the model has no
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
This is the REACT phase: by default you react SILENTLY - keep it to inner_monologue and emote. Speak out loud ONLY if the situation genuinely calls for it (someone addressed you directly, something alarming or unexpected happened). Do not advance to your next planned action here - that happens next turn.
A moment has just passed - your own action barely completed. The people around you have NOT had time to react or reply yet; their silence or stillness right now means they simply haven't responded, not that they ignored you. Do not infer long stretches of time from one instant. React to what actually happened to you in this single moment.
CRITICAL: If your action was rejected or failed, your reaction must acknowledge the failure - never describe the action as if it succeeded. A blocked kitchen attempt is not a visit; a refused door is not open.
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
     * grab→approach/release. One quick decision - no speech/emote/memory.
     * @param {string} charName - Character name
     * @param {string} roomContext - Pre-built area context string
     * @param {string} resultText - Result text of the source action
     * @param {string} sourceVerb - The verb that just succeeded (dash/lead/grab)
     * @param {string[]} allowedVerbs - Follow-up verbs the chain allows
     * @returns {string} Follow-up prompt string
     */
    function buildChainFollowUpPrompt(charName: string, roomContext: string, resultText: string, sourceVerb: string, allowedVerbs: string[]) {
        const verbs = (allowedVerbs && allowedVerbs.length) ? allowedVerbs.join(', ') : 'go';
        return `${roomContext}

=== CHAIN FOLLOW-UP ===
You just ${sourceVerb} - ${resultText}

You may chain ONE immediate follow-up action before your turn ends: ${verbs}.
Pick an exit or target from the context above (go/approach), release a grapple, or respond with "wait".
This is a quick decision - no speech, no emote, no memory.
Respond ONLY raw JSON, every field shown (null what you don't need):
${PromptBuilder.buildJsonExample(['full_action'])}`;
    }

    /** @deprecated Use buildChainFollowUpPrompt (dash is one CHAIN_RULES family). */
    function buildDashFollowUpPrompt(charName: string, roomContext: string, dashResult: string) {
        return buildChainFollowUpPrompt(charName, roomContext, dashResult, 'dashed', ['go', 'wait']);
    }

    /**
     * Build a phone conversation turn from the same Player identity and state
     * context used by the standard agent. The communication field is an action
     * adapter; it does not define another character or memory model.
     */
    function buildCommunicationPrompt(player: PlayerData, memoryNL: string, channels: unknown[], knownCharacters: string[], theme = 'live_social') {
        const charName = String(player?.name || '');
        const isTownBoard = theme === 'town_board';
        const persona = player?.personality
            ? `You are ${charName}. Personality: ${player.personality}`
            : `You are ${charName}.`;
        const context = PromptBuilder.buildContextBlock(player, { phase: 'communication' },
            ['emotion', 'insanity', 'trait', 'mosiac', 'dead']);
        const availableChannels = (Array.isArray(channels) ? channels : [])
            .filter((channel: *FIX*) => !isTownBoard || channel?.kind !== 'group');
        const channelLines = availableChannels.map((channel: *FIX*) => {
            const unread = Number(channel?.unread_count || 0);
            const members = Array.isArray(channel?.members) ? channel.members.join(', ') : '';
            if (isTownBoard) {
                const noun = channel?.kind === 'public' ? 'posts' : 'letters';
                const medium = channel?.kind === 'public' ? 'town notice board' : 'private letter';
                return `- ${channel.id} (${medium}; ${channel.name}; ${unread} new ${noun}${members ? `; members: ${members}` : ''})`;
            }
            return `- ${channel.id} (${channel.kind}; ${channel.name}; ${unread} unread${members ? `; members: ${members}` : ''})`;
        }).join('\n') || '- No conversations are available.';
        const names = (Array.isArray(knownCharacters) ? knownCharacters : [])
            .map(name => String(name || '').trim()).filter(Boolean).join(', ');
        const heading = isTownBoard ? '=== TOWN BOARD AND LETTERS ===' : '=== PHONE CONVERSATIONS ===';
        const contextLine = isTownBoard
            ? 'You use The Commons as a town notice board and private letters. The board is public; letters are direct conversations. Delivery is immediate inside The Commons; do not invent physical delivery, devices, or travel. Message text is hidden until you explicitly choose read_chat.'
            : 'You are using the same phone as this character. The list contains only conversations you can access. Message text is hidden until you explicitly choose read_chat.';
        const actions = isTownBoard
            ? 'Available tools: read_chat to read posts or letters, send_chat to add a public post or reply to a private letter, start_dm to open a private letter exchange with one existing character and send its first letter, and remember to save something worth retaining. Group conversations are unavailable.'
            : 'Available tools: read_chat to read a conversation, send_chat to post to one you belong to, start_dm to open a direct conversation with one character whose name you know and send its first message, start_group to create a private group with a name and invitees whose names you know, and remember to save something worth retaining.';
        return `${persona}
=== YOUR STATE ===
${String(context || '').trim()}
${String(memoryNL || '').trim()}

${heading}
${contextLine} Use only the conversation ids shown below.
${channelLines}

=== COMMUNICATION TURN ===
${actions} You may call zero or more tools. Make one call at a time. After a read_chat result, consider what you want to do next; replying is optional, not expected. Stop by returning no tool call when you are done or want to stay quiet. Do not take physical world actions on this turn. Never claim to have read messages unless read_chat returns them. Keep the character's established personality and memories.
Characters whose names you know and may contact: ${names || 'none'}

Use tool calls for all communication. Plain response text is private thought only and ends the turn; it never sends a message.`;
    }

    /**
     * Invalid-action auto-retry prompt (task-361): feed back the failed action
     * and its reason, direct a different choice. Same-turn, ONE retry - the
     * character's own context prompts already describe the room; this only
     * needs the failure and the instruction, so it reuses the decide schema
     * through the normal parser.
     * @param {string} failedAction - The action string that was rejected/failed
     * @param {string} failedResult - The result/error text the engine returned
     * @returns {string} Retry prompt string
     */
    function buildRetryPrompt(failedAction: string, failedResult: string) {
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
        buildRetryPrompt,
        buildCommunicationPrompt,
        summaryLine: _summaryLine,
    });
})();
