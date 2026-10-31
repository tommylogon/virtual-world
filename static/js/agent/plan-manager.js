"use strict";
/**
 * plan-manager.js - Plan generation and status checking for character agents
 *
 * Handles LLM-driven multi-step plan generation for characters and
 * plan existence checks. Plans guide character behavior over multiple turns.
 *
 * Usage: PlanManager.generate(charName)
 *        PlanManager.hasPlan(charName)
 *
 * Load this AFTER agent-engine.js in index.html (references VW.agent).
 *
 * @module agent/plan-manager - LLM plan generation
 * @contributes PlanManager.generate() (multi-step plan via the LLM) + hasPlan()
 * @powers NPC behaviour - the plan an agent follows across turns
 * @relates stores into PlanTracker; the plan text feeds the decide prompt's PLAN FOLLOW
 * @relates task-700: steps are TYPED and grounded through PlanGrounding before
 *       acceptance - prose steps referencing flavor text ("use hanging meat")
 *       are rejected at plan time, not burned as failed actions in the world.
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const PlanManager = (() => {
    'use strict';
    /**
     * `window.StructuredFormats` (shared/structured-formats.js) is not declared in
     * types/globals.d.ts, so it is read through a local cast rather than edited
     * into the shared hub.
     */
    function _structuredFormats() {
        return window.StructuredFormats;
    }
    /** `repairJSON` (shared/json-utils.js) is a bare global function, not on Window. */
    function _repairJSON(text) {
        const fn = globalThis.repairJSON;
        return fn ? fn(text) : text;
    }
    function _planGrounding() {
        return window.PlanGrounding;
    }
    /**
     * Check whether the given config requires an API key.
     * Local endpoints (localhost, 127.0.0.1) are assumed keyless.
     * @param cfg - Configuration object with .apiBase
     * @returns True if an API key is required
     */
    function _needsKey(cfg) {
        return !cfg.apiBase?.includes('localhost') && !cfg.apiBase?.includes('127.0.0.1');
    }
    /**
     * One-line summary of the previous action result (N7). The full result can
     * be a move dump (room prose + exits) that duplicates the observation the
     * plan prompt already contains - first line only carries the outcome.
     */
    function _summaryLine(text) {
        const lines = String(text || '').split('\n').map(s => s.trim()).filter(Boolean);
        return lines[0] || '';
    }
    /**
     * Build the repair prompt for a plan with rejected steps.
     *
     * The repair contract is CONSTRAINED: keep the steps that already
     * grounded, replace only the rejected ones. The old prompt said "Keep
     * grounded steps unchanged" without ever SHOWING which steps those were,
     * so the model had nothing to keep and routinely returned a completely
     * different plan - the character walked away from a verified step
     * (approach the dining room) and got "take lighter / go west passage"
     * instead. The prompt now lists every step with its index and status.
     */
    function _buildRepairPrompt(grounding, originalSteps, grounded, rejections, facts) {
        const reasonByIndex = new Map();
        for (const r of rejections)
            reasonByIndex.set(r.index, r.reason);
        const lines = originalSteps.map((step, i) => {
            const reason = reasonByIndex.get(i);
            const rendered = grounding.render(step);
            return reason
                ? `${i + 1}. [REJECTED] ${rendered}  <- ${reason}`
                : `${i + 1}. [KEEP] ${rendered}`;
        });
        return `
=== GROUNDING REJECTIONS ===
${rejections.length} of your ${originalSteps.length} steps name things that do not exist here. Your plan, step by step:

${lines.join('\n')}

RULES for the corrected plan:
- Reproduce every [KEEP] step EXACTLY as written, in the same position. Do not reword it, reorder it, or drop it.
- Replace ONLY the [REJECTED] steps, one for one, with steps that use the FACTS below.
- Keep the same number of steps, in the same order.
- Do not invent objects. A room description is not proof that an object exists.
- PATHS (doors, exits) are the target of go / approach / open / close. ITEMS are the target of take / use / search / examine. PEOPLE are the target of speak / give / attack.

FACTS you may reference: interactables here: ${facts.areaItems.join(', ') || '(none)'}; carrying: ${facts.carried.join(', ') || '(nothing)'}; people here: ${facts.people.join(', ') || '(nobody)'}; paths: ${facts.exits.join(', ') || '(none)'}; known areas: ${facts.knownAreas.join(', ') || '(none)'}.
Respond ONLY with the corrected {"steps": [...]} array.`;
    }
    /**
     * Merge a repaired plan with the steps that already grounded.
     *
     * The repair contract is "keep the good steps, replace only the rejected
     * ones". A model that ignores that must not be able to throw away a step
     * that was already verified: the originally-grounded steps are restored at
     * their original positions and the repaired steps fill the gaps. The
     * merged plan is re-grounded end to end before it is accepted.
     */
    function _mergeWithPreserved(repairedGrounded, originalSteps, originalGrounded, grounding, facts, areaName) {
        if (!originalSteps.length) {
            return repairedGrounded.map((g) => ({ step: g.step, text: g.text }));
        }
        const okByIndex = new Map();
        for (const g of originalGrounded)
            okByIndex.set(g.index, { step: g.step, text: g.text });
        const repairedByIndex = new Map();
        for (const g of repairedGrounded)
            repairedByIndex.set(g.index, { step: g.step, text: g.text });
        const usedRepaired = new Set();
        const merged = [];
        for (let i = 0; i < originalSteps.length; i++) {
            const ok = okByIndex.get(i);
            if (ok) {
                // Restore the verified step verbatim - the repair may not
                // reword a step that already grounds. The position is taken,
                // so whatever the repair put here is consumed (and must not
                // be appended again as an extra step).
                merged.push(ok);
                usedRepaired.add(i);
                continue;
            }
            // This position was rejected: the repaired step that occupies it
            // is the intended replacement.
            const atSameIndex = repairedByIndex.get(i);
            if (atSameIndex) {
                merged.push(atSameIndex);
                usedRepaired.add(i);
                continue;
            }
            // Otherwise take the first unused repaired step that grounds.
            let picked = null;
            for (const g of repairedGrounded) {
                if (usedRepaired.has(g.index))
                    continue;
                picked = { step: g.step, text: g.text };
                usedRepaired.add(g.index);
                break;
            }
            // No replacement grounds: the position is dropped rather than
            // filled with an unverified step.
            if (picked)
                merged.push(picked);
        }
        // Repaired steps BEYOND the original count are appended, capped at 5.
        // A repaired step at an original position was either restored over or
        // already used as that position's replacement.
        for (const g of repairedGrounded) {
            if (usedRepaired.has(g.index))
                continue;
            if (g.index < originalSteps.length)
                continue;
            if (merged.length >= 5)
                break;
            merged.push({ step: g.step, text: g.text });
        }
        // Final validation: the whole merged plan must ground.
        const validated = grounding.ground(merged.map((m) => m.step), facts, areaName);
        return validated.grounded.map((g) => ({ step: g.step, text: g.text }));
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
        if (!charName || (!config.apiKey && _needsKey(config)) || !config.model)
            return [];
        try {
            const state = worldState?.data;
            const player = state?.players?.[charName];
            if (!player)
                return [];
            const currentArea = state?.areas?.[player.current_area] || null;
            const roomContext = PromptBuilder.buildRoomContext(state, charName, player, currentArea, false);
            const vitals = PromptBuilder.describeVitals(player, state, charName);
            const emotion = PromptBuilder.buildEmotionContext(player);
            const memories = await PromptBuilder.buildMemoryContext(charName);
            const lastThought = events.getCharacterState(charName)?.lastThought || '';
            const lastActionResults = (config.lastActionResult || {});
            const lastResult = lastActionResults[charName] || '';
            // Threat detection - check for hostile actors in the same room
            const allPlyrs = state?.players || {};
            const areaPlayers = state?.players_in_area || [];
            const threatsInRoom = [];
            for (const person of areaPlayers) {
                if (person.name === charName)
                    continue;
                const other = allPlyrs[person.name];
                if (!other)
                    continue;
                if (other.state === 'hidden' || other.state === 'stealthed')
                    continue;
                const rel = other.relationships?.[charName]?.closeness;
                if (other.traits?.hostile || (rel !== undefined && rel < -20)) {
                    threatsInRoom.push(person.name);
                }
            }
            const threatNote = threatsInRoom.length > 0
                ? `\n?? THREAT WARNING: ${threatsInRoom.join(', ')} ${threatsInRoom.length > 1 ? 'are' : 'is'} hostile to you and in this room. Your plan MUST address this threat first - flee, hide, fight, or warn others. Do NOT plan exploration or item examination while a threat is active.`
                : '';
            // task-92: critical vitals force the plan to address them first.
            // Maslow's hierarchy of needs: physiological needs (hunger, thirst,
            // sleep, safety) are the base of the pyramid and MUST be satisfied
            // before the character can focus on exploration, investigation, or
            // social goals. A plan that starts with "search the library" while
            // the character is starving is wrong, however interesting the
            // search is.
            const criticalNeedsList = PlanTracker.criticalNeeds(player?.vitals);
            // BUT a slasher/undead character doesn't have physiological needs -
            // the engine skips their vital decay entirely, so telling the
            // Butcher to "eat your food" first is a distraction from the
            // murder. Filter those needs out for horror/undead traits.
            const pTraits = player?.traits || {};
            const pTags = Array.isArray(player?.tags) ? player.tags : [];
            const noPhysNeeds = pTraits.is_slasher === true
                || pTraits.undead === true
                || pTraits.no_physiological_needs === true
                || pTags.includes('undead')
                || pTags.includes('ghost');
            const filteredNeeds = noPhysNeeds
                ? criticalNeedsList.filter((n) => !/^hunger|thirst|sleep/i.test(n))
                : criticalNeedsList;
            const maslowNote = filteredNeeds.length > 0
                ? `\n\n=== CRITICAL NEEDS (MASLOW - address these FIRST) ===\nYou are suffering from: ${filteredNeeds.join('; ')}.\n\nThese are PHYSIOLOGICAL needs - the base of Maslow's hierarchy. They outrank every other goal: safety, exploration, investigation, and social connection can wait. Build the FIRST step of your plan around satisfying the most urgent need (eat your food, drink your water, find shelter, rest).\n\nA short detour toward another goal is fine ONLY if you return to the urgent need immediately after. Don't let curiosity or a side-task stand between you and the pressing need.`
                : '';
            const grounding = _planGrounding();
            const areaName = currentArea?.name || player?.current_area || '';
            const facts = grounding && grounding.collectFacts(charName, state, player, areaName);
            const prompt = `${roomContext}

=== YOUR STATE ===
${vitals || 'No urgent physical needs.'}${emotion}${threatNote}${maslowNote}

${memories || ''}
${lastResult ? `\n=== RECENTLY ===\n${_summaryLine(lastResult)}` : ''}

${lastThought ? `=== YOUR THOUGHTS ===\n${lastThought}\n\n` : ''}${_previousPlanIssues(charName)}

Create a practical 3-5 step plan based only on the information above.
- Every step is an object: {"act": "...", "item": ..., "target": ..., "text": ..., "note": ..., "area": ..., "until": ...}
- "act" is one of: ${grounding ? [...grounding.ACTS].join(', ') : 'go, take, use, examine, speak, wait'}.
- TARGET TYPES - every "item"/"target" must name a thing that exists, and the TYPE decides where it comes from:
  * PATHS (the doors/exits listed under "paths") are the target of go, dash, approach, open, close.
  * ITEMS (the "Items that catch your attention" list) are the target of take, use, eat, drink, search, examine, drop.
  * PEOPLE (the "People here" list) are the target of speak, give, attack, grab, steal.
  * AREAS you know are the target of go.
- CRITICAL: "take" is ONLY for items on the ground/in the room - NOT for items you already carry. If you already carry an item, use "use", "examine", or "drop" instead. Do not plan "take" for carried items.
- Room-description scenery is NOT an interactable. A dining table you can see described is not an item you can search - only things on the Items list are. To look in another room, "go" there first, then "look" to see what that room actually lists, then act on those.
- "speak" steps carry the line in "text". "perform" steps describe a sustained activity in "note" (cook, mine, drill) and may carry "until" (e.g. "ore x5", "dusk") and "duration" (game minutes).
- Account for immediate survival needs, active threats in the room, and the character's current condition.
- Plans are suggestions - if something changes (a threat appears, someone attacks, a new person arrives), the plan may no longer apply. Re-evaluate before acting.

Respond ONLY with a JSON object: {"steps": [{"act": "take", "item": "dried meat"}, {"act": "go", "target": "west passage"}]}`;
            if (!grounding || !facts) {
                // Grounding module unavailable - legacy prose contract as fallback.
                const response = await llmClient.chat([{ role: 'user', content: prompt }], { temperature: 0.7, streaming: false, label: 'plan', max_tokens: Math.max(window.config?.maxTokens || 2048, 4096), reasoningEffort: 'low', responseFormat: _structuredFormats()?.plan, actor: charName, requestId: `plan-${charName}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` });
                return _legacySteps(response);
            }
            // task-700: typed steps, grounded before acceptance. One bounded
            // re-composition: rejected steps return their failed preconditions
            // (with the fact list) to the LLM once; whatever still does not
            // ground is dropped, never executed.
            let groundingBlock = '';
            let originalSteps = [];
            let originalGrounded = [];
            for (let attempt = 0; attempt < 2; attempt++) {
                // max_tokens 560: a live run truncated a typed re-composition
                // mid-JSON at 300 and the turn ran planless.
                const response = await llmClient.chat([{ role: 'user', content: prompt + groundingBlock }], { temperature: 0.7, streaming: false, label: 'plan', max_tokens: Math.max(window.config?.maxTokens || 2048, 4096), reasoningEffort: 'low', responseFormat: _structuredFormats()?.plan, actor: charName, requestId: `plan-repair-${charName}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` });
                if (!response)
                    return [];
                let cleaned = _repairJSON(response);
                const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
                if (codeBlockMatch)
                    cleaned = codeBlockMatch[1].trim();
                let parsed = null;
                try {
                    parsed = JSON.parse(cleaned);
                }
                catch {
                    parsed = null;
                }
                // Truncated response: keep the complete step objects rather
                // than losing the whole plan (a live run died mid-object and
                // Rikka executed her turn with no plan at all). Salvage reads
                // the RAW response: repairJSON strips quotes from truncated
                // JSON ({"act":,"x"}), which makes the salvaged chunks
                // unparseable too.
                const salvaged = parsed ? [] : _salvageTypedSteps(response || '');
                const rawSteps = salvaged.length ? salvaged
                    : (Array.isArray(parsed) ? parsed
                        : (Array.isArray(parsed?.steps) ? parsed.steps : null));
                if (!Array.isArray(rawSteps) || !rawSteps.length)
                    return [];
                // Legacy prose contract ({"steps": ["..."]}) - accepted as fallback.
                const legacy = rawSteps.filter((s) => typeof s === 'string');
                const typed = rawSteps.filter((s) => s && typeof s === 'object');
                if (legacy.length && !typed.length)
                    return legacy.slice(0, 5);
                if (!typed.length)
                    return [];
                const steps = typed.slice(0, 5);
                const result = grounding.ground(steps, facts, areaName);
                if (attempt === 0) {
                    originalSteps = steps;
                    originalGrounded = result.grounded;
                    if (!result.rejections.length) {
                        return result.grounded.map((g) => g.text);
                    }
                    for (const r of result.rejections) {
                        events.log(`🧭 ${charName} plan step ungrounded: "${grounding.render(r.step)}" - ${r.reason}`, 'system-msg');
                    }
                    groundingBlock = _buildRepairPrompt(grounding, steps, result.grounded, result.rejections, facts);
                    continue;
                }
                // Attempt 1: a repaired plan. Merge it with the steps that
                // already grounded so a repair can never throw away a
                // verified step, and revalidate the whole plan.
                for (const r of result.rejections) {
                    events.log(`🧭 ${charName} repaired plan step still ungrounded: "${grounding.render(r.step)}" - ${r.reason}`, 'system-msg');
                }
                const merged = _mergeWithPreserved(result.grounded, originalSteps, originalGrounded, grounding, facts, areaName);
                if (merged.length) {
                    return merged.map((m) => m.text);
                }
                if (result.grounded.length) {
                    return result.grounded.map((g) => g.text);
                }
                return [];
            }
            return [];
        }
        catch (error) {
            return [];
        }
    }
    /**
     * Legacy parse (pre-task-700 prose contract): {"steps": ["..."]}, a raw
     * array, or the old object-array variant. Kept as the fallback path when
     * the grounding module is unavailable.
     */
    function _legacySteps(response) {
        if (!response)
            return [];
        let cleaned = _repairJSON(response);
        const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
        if (codeBlockMatch)
            cleaned = codeBlockMatch[1].trim();
        let parsed;
        try {
            parsed = JSON.parse(cleaned);
        }
        catch {
            return [];
        }
        const arr = Array.isArray(parsed) ? parsed
            : (Array.isArray(parsed?.steps) ? parsed.steps : null);
        if (!Array.isArray(arr))
            return [];
        const steps = arr.filter((s) => typeof s === 'string').slice(0, 5);
        if (steps.length > 0)
            return steps;
        if (typeof arr[0] === 'object' && arr[0] !== null) {
            const objs = arr.map((e) => e.examine || e.action || e.step || '').filter(Boolean).slice(0, 5);
            if (objs.length)
                return objs;
        }
        return [];
    }
    /**
     * Salvage typed steps from a TRUNCATED plan response: pull the complete
     * flat objects out of a half-written {"steps":[...]} and return them. A
     * live run (kraktooth, Rikka) hit max_tokens mid-string and the whole
     * plan was lost, leaving the character to act with no plan at all.
     */
    function _salvageTypedSteps(cleaned) {
        const out = [];
        const objs = cleaned.match(/\{[^{}]*\}/g) || [];
        for (const chunk of objs) {
            try {
                const obj = JSON.parse(chunk);
                if (obj && typeof obj === 'object' && obj.act)
                    out.push(obj);
                else if (obj && Array.isArray(obj.steps)) {
                    for (const s of obj.steps)
                        if (s && typeof s === 'object' && s.act)
                            out.push(s);
                }
            }
            catch {
                // incomplete trailing object - skip it
            }
        }
        return out.slice(0, 5);
    }
    /**
     * Collect what the previous plan accomplished/failed at, so regeneration
     * does not repeat steps that already failed 3+ times.
     */
    function _previousPlanIssues(charName) {
        const plan = PlanTracker.getPlan(charName);
        if (!plan.length)
            return '';
        const progress = PlanTracker.getProgress(charName);
        const fullPlan = PlanTracker.getPlan(charName);
        // Fix 3: discard steps that reference the wrong area or have failed 3+ times.
        const state = worldState?.data;
        const player = state?.players?.[charName];
        const currentArea = player?.current_area || '';
        const parts = [];
        for (let i = 0; i < fullPlan.length; i++) {
            const stepText = String(fullPlan[i] || '');
            const failures = PlanTracker.getFailures(charName);
            const stepFails = (failures[i] || 0);
            // Skip steps that clearly reference a different area (stale location).
            const areaMatch = stepText.toLowerCase();
            const isStaleLocation = currentArea && areaMatch.length > 0 && !areaMatch.includes(currentArea.toLowerCase()) && (areaMatch.includes('go') || areaMatch.includes('approach') || areaMatch.includes('enter'));
            if (stepFails >= 3) {
                parts.push(`"${stepText}" (FAILED ${stepFails} times - discarded; find an alternative)`);
            }
            else if (i < progress) {
                parts.push(`"${stepText}" (done)`);
            }
            else if (isStaleLocation && i >= progress) {
                parts.push(`"${stepText}" (stale - current area is ${currentArea}; discard or replace)`);
            }
            else {
                parts.push(`"${stepText}" (available)`);
            }
        }
        if (!parts.length)
            return '';
        return `\n=== PREVIOUS PLAN ===\nYour previous plan: ${parts.join('; ')}.\nRe-evaluate: discard stale or failed steps; continue only from verified, current-area steps.`;
    }
    /**
     * Check whether a character has an active plan with remaining steps.
     * @param charName - Character name
     * @returns True if a plan exists and has uncompleted steps
     */
    function hasPlan(charName) {
        return PlanTracker.getPlan(charName).length > 0;
    }
    return {
        generate,
        hasPlan,
        // Exposed for the unit tests: the repair contract (keep the good
        // steps, replace only the rejected ones) is a mechanism worth pinning.
        _buildRepairPrompt,
        _mergeWithPreserved,
    };
})();
window.PlanManager = PlanManager;
