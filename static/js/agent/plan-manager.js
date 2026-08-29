/**
 * plan-manager.js — Plan generation and status checking for character agents
 *
 * Handles LLM-driven multi-step plan generation for characters and
 * plan existence checks. Plans guide character behavior over multiple turns.
 *
 * Usage: PlanManager.generate(charName)
 *        PlanManager.hasPlan(charName)
 *
 * Load this AFTER agent-engine.js in index.html (references VW.agent).
 */

window.PlanManager = (() => {
    'use strict';

    /**
     * Check whether the given config requires an API key.
     * Local endpoints (localhost, 127.0.0.1) are assumed keyless.
     * @param {Object} cfg - Configuration object with .apiBase
     * @returns {boolean} True if an API key is required
     */
    function _needsKey(cfg) {
        return !cfg.apiBase?.includes('localhost') && !cfg.apiBase?.includes('127.0.0.1');
    }

    /**
     * One-line summary of the previous action result (N7). The full result can
     * be a move dump (room prose + exits) that duplicates the observation the
     * plan prompt already contains — first line only carries the outcome.
     */
    function _summaryLine(text) {
        const lines = String(text || '').split('\n').map(s => s.trim()).filter(Boolean);
        return lines[0] || '';
    }

    /**
     * Generate a multi-step plan for a character using the LLM.
     *
     * Builds a prompt from the character's current state, area context,
     * vitals, emotions, relationships, memories, and world knowledge.
     * The LLM responds with a JSON array of 3-5 plan steps.
     *
     * @param {string} charName - Character name to generate a plan for
     * @returns {Promise<string[]>} Array of up to 5 plan step strings, or empty on failure
     */
    async function generate(charName) {
        if (!charName || (!config.apiKey && _needsKey(config)) || !config.model) return [];
        try {
            const state = worldState?.data;
            const player = state?.players?.[charName];
            if (!player) return [];

            const currentArea = state?.areas?.[player.current_area] || null;
            const roomContext = PromptBuilder.buildRoomContext(state, charName, player, currentArea, false);
            const vitals = PromptBuilder.describeVitals(player);
            const emotion = PromptBuilder.buildEmotionContext(player);
            const memories = await PromptBuilder.buildMemoryContext(charName);
            const lastThought = events.getCharacterState(charName)?.lastThought || '';
            const lastResult = config.lastActionResult?.[charName] || '';

            // Threat detection — check for hostile actors in the same room
            const allPlyrs = state?.players || {};
            const areaPlayers = state?.players_in_area || [];
            const threatsInRoom = [];
            for (const person of areaPlayers) {
                if (person.name === charName) continue;
                const other = allPlyrs[person.name];
                if (!other) continue;
                if (other.state === 'hidden' || other.state === 'stealthed') continue;
                const rel = other.relationships?.[charName]?.closeness;
                if (other.traits?.hostile || (rel !== undefined && rel < -20)) {
                    threatsInRoom.push(person.name);
                }
            }
            const threatNote = threatsInRoom.length > 0
                ? `\n?? THREAT WARNING: ${threatsInRoom.join(', ')} ${threatsInRoom.length > 1 ? 'are' : 'is'} hostile to you and in this room. Your plan MUST address this threat first — flee, hide, fight, or warn others. Do NOT plan exploration or item examination while a threat is active.`
                : '';

            // task-92: critical vitals force the plan to address them first.
            const criticalNeedsList = PlanTracker.criticalNeeds(player?.vitals);
            const needsNote = criticalNeedsList.length > 0
                ? `\n\n=== CRITICAL NEEDS ===\nYou are suffering from: ${criticalNeedsList.join('; ')}.\nPRIORITIZE the most urgent need FIRST — the plan should address it before exploration or conversation. A short detour toward another goal is fine ONLY if you return to the urgent need immediately after. Don't let curiosity or a side-task stand between you and the pressing need.`
                : '';

            const prompt = `${roomContext}

=== YOUR STATE ===
${vitals || 'No urgent physical needs.'}${emotion}${threatNote}${needsNote}

${memories || ''}
${lastResult ? `\n=== RECENTLY ===\n${_summaryLine(lastResult)}` : ''}

${lastThought ? `=== YOUR THOUGHTS ===\n${lastThought}\n\n` : ''}${_previousPlanIssues(charName)}

Create a practical 3-5 step plan based only on the information above.
- Only name items, people, places, exits, and facts that appear in the current world or memories.
- Do not invent props, characters, clues, areas, or events.
- Treat the Items list as the only objects that can be directly interacted with. If more information is needed, plan to look, examine a listed item, speak to a person present, or use a visible exit.
- Account for immediate survival needs, active threats in the room, and the character's current condition.
- Plans are suggestions — if something changes (a threat appears, someone attacks, a new person arrives), the plan may no longer apply. Re-evaluate before acting.

Respond ONLY with a raw JSON array of strings: ["step 1", "step 2"]`;

            const response = await llmClient.chat([{ role: 'user', content: prompt }], { temperature: 0.7, max_tokens: 200, streaming: false, label: 'plan' });
            if (!response) return [];
            let cleaned = repairJSON(response);
            const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
            if (codeBlockMatch) cleaned = codeBlockMatch[1].trim();
            const parsed = JSON.parse(cleaned);
            if (Array.isArray(parsed)) {
                const steps = parsed.filter(step => typeof step === 'string').slice(0, 5);
                if (steps.length > 0) return steps;
            }
            if (Array.isArray(parsed) && typeof parsed[0] === 'object' && parsed[0] !== null) {
                const steps = parsed.map(entry => entry.examine || entry.action || entry.step || '').filter(Boolean).slice(0, 5);
                if (steps.length > 0) return steps;
            }
            return [];
        } catch (error) {
            return [];
        }
    }

    /**
     * Collect what the previous plan accomplished/failed at, so regeneration
     * does not repeat steps that already failed 3+ times.
     */
    function _previousPlanIssues(charName) {
        const plan = PlanTracker.getPlan(charName);
        if (!plan.length) return '';
        const progress = PlanTracker.getProgress(charName);
        const fullPlan = PlanTracker.getPlan(charName);
        const parts = [];
        for (let i = 0; i < fullPlan.length; i++) {
            if (i < progress) {
                parts.push(`"${fullPlan[i]}" (done)`);
            } else {
                parts.push(`"${fullPlan[i]}" (available)`);
            }
        }
        if (!parts.length) return '';
        return `\n=== PREVIOUS PLAN ===\nYour previous plan: ${parts.join('; ')}.\nContinue from where you left off.`;
    }

    /**
     * Check whether a character has an active plan with remaining steps.
     * @param {string} charName - Character name
     * @returns {boolean} True if a plan exists and has uncompleted steps
     */
    function hasPlan(charName) {
        return PlanTracker.getPlan(charName).length > 0;
    }

    return {
        generate,
        hasPlan
    };
})();

