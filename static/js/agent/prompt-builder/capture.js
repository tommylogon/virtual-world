"use strict";
/**
 * prompt-builder/capture.js - capture the exact turn prompt a character sees.
 *
 * One capture path for every surface that needs "the prompt the simulation
 * would send right now": the Benchmark Lab page (/bench) and the in-app
 * benchmark harness. The calls below are the SAME calls agent-engine.js makes
 * at the start of a character's turn (think-decide phase), in the same order,
 * with the same arguments. That is the whole point: a benchmark that sends a
 * hand-written approximation measures the approximation, not the game.
 *
 * Order matters and mirrors agent-engine.js:
 *   room parts -> vitals -> emotion -> relationships -> memory -> system -> user
 *
 * The memory block is fetched with `{ report: true }` (the live turn's mode),
 * not `{ preview: true }`: a preview skips the semantic recall path, so the
 * captured prompt would differ from the one the model actually receives in
 * play. Side effect: recalling reinforces the memories it returns, exactly as
 * a live turn does.
 *
 * Exports merge into window.PromptBuilder.
 *
 * @module prompt-builder/capture - capture a character's live turn prompt
 * @contributes captureTurnPrompt
 * @powers Developer Tooling, Benchmarks - the prompt the Benchmark Lab sends to every model
 * @relates stitches room-context + character-state + memory-context + turn-prompts; mirrors agent-engine's turn start
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';
    /**
     * Build the system + user messages for one character's turn.
     * @param {string} charName - Character name as it appears in worldState.data.players
     * @param {CaptureOptions} [options] - Overrides for the state and the turn flavour
     * @returns {Promise<CaptureResult>} The captured prompt and the pieces it was built from
     */
    async function captureTurnPrompt(charName, options = {}) {
        const name = String(charName || '').trim();
        if (!name)
            throw new Error('captureTurnPrompt: no character name given');
        const state = options.state || window.worldState?.data || worldState?.data;
        if (!state)
            throw new Error('captureTurnPrompt: no world state loaded (worldState.data is empty)');
        const player = state.players?.[name];
        if (!player)
            throw new Error(`captureTurnPrompt: no player data for "${name}"`);
        // The character's OWN area, not state.current_area: that one is the
        // server's single active-player view, so it points at the wrong room
        // for every other character (bug-565). buildRoomContextParts resolves
        // it again for callers that pass the wrong area.
        const areaName = String(player.current_area || state.current_area || '');
        const currentArea = (areaName && state.areas?.[areaName]) || null;
        const roomParts = PromptBuilder.buildRoomContextParts(state, name, player, currentArea);
        const vitalsNL = PromptBuilder.describeVitals(player, state, name);
        const emotionNL = PromptBuilder.buildEmotionContext(player);
        const relationshipNL = PromptBuilder.buildRelationshipContext(player, name);
        const memoryNL = await PromptBuilder.buildMemoryContext(name, { report: true });
        const systemPrompt = PromptBuilder.buildCharacterSystemPrompt(name, player, config.softMaxTokens);
        const userPrompt = PromptBuilder.buildReactionPrompt(player, roomParts, vitalsNL, emotionNL, relationshipNL, memoryNL, options.lastResult || '', options.includeMemory === true, options.includeFeelings !== false);
        return { charName: name, player, currentArea, roomParts, systemPrompt, userPrompt };
    }
    Object.assign(window.PromptBuilder, { captureTurnPrompt });
})();
