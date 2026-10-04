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
 *
 * @module agent/plan-manager — LLM plan generation
 * @contributes PlanManager.generate() (multi-step plan via the LLM) + hasPlan()
 * @powers NPC behaviour — the plan an agent follows across turns
 * @relates stores into PlanTracker; the plan text feeds the decide prompt's PLAN FOLLOW
 * @relates task-700: steps are TYPED and grounded through PlanGrounding before
 *       acceptance — prose steps referencing flavor text ("use hanging meat")
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
    function _structuredFormats(): { plan?: unknown } | undefined {
        return (window as unknown as { StructuredFormats?: { plan?: unknown } }).StructuredFormats;
    }

    /** `repairJSON` (shared/json-utils.js) is a bare global function, not on Window. */
    function _repairJSON(text: string): string {
        const fn = (globalThis as unknown as { repairJSON?: (t: string) => string }).repairJSON;
        return fn ? fn(text) : text;
    }

    /** PlanGrounding (agent/plan-grounding.js) — task-700's grounding validator. */
    interface PlanGroundingApi {
        ACTS: Set<string>;
        collectFacts(charName: string, state: any, player: any, areaName: string): {
            areaItems: string[]; carried: string[]; people: string[];
            exits: string[]; knownAreas: string[];
        };
        ground(steps: any[], facts: any, areaName: string): {
            grounded: Array<{ step: any; text: string }>;
            rejections: Array<{ step: any; reason: string }>;
        };
        render(step: any): string;
    }

    function _planGrounding(): PlanGroundingApi | undefined {
        return (window as unknown as { PlanGrounding?: PlanGroundingApi }).PlanGrounding;
    }

    /**
     * Check whether the given config requires an API key.
     * Local endpoints (localhost, 127.0.0.1) are assumed keyless.
     * @param cfg - Configuration object with .apiBase
     * @returns True if an API key is required
     */
    function _needsKey(cfg: { apiBase?: string }): boolean {
        return !cfg.apiBase?.includes('localhost') && !cfg.apiBase?.includes('127.0.0.1');
    }

    /**
     * One-line summary of the previous action result (N7). The full result can
     * be a move dump (room prose + exits) that duplicates the observation the
     * plan prompt already contains — first line only carries the outcome.
     */
    function _summaryLine(text: unknown): string {
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
    async function generate(charName: string): Promise<string[]> {
        if (!charName || (!config.apiKey && _needsKey(config)) || !config.model) return [];
        try {
            const state = worldState?.data;
            const player = state?.players?.[charName];
            if (!player) return [];

            const currentArea = state?.areas?.[player.current_area] || null;
            const roomContext = PromptBuilder.buildRoomContext(state, charName, player, currentArea, false);
            const vitals = PromptBuilder.describeVitals(player, state, charName);
            const emotion = PromptBuilder.buildEmotionContext(player);
            const memories = await PromptBuilder.buildMemoryContext(charName);
            const lastThought = events.getCharacterState(charName)?.lastThought || '';
            const lastActionResults = (config.lastActionResult || {}) as Record<string, string>;
            const lastResult = lastActionResults[charName] || '';

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
            // Maslow's hierarchy of needs: physiological needs (hunger, thirst,
            // sleep, safety) are the base of the pyramid and MUST be satisfied
            // before the character can focus on exploration, investigation, or
            // social goals. A plan that starts with "search the library" while
            // the character is starving is wrong, however interesting the
            // search is.
            const criticalNeedsList = PlanTracker.criticalNeeds(player?.vitals);
            // BUT a slasher/undead character doesn't have physiological needs —
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
                ? criticalNeedsList.filter((n: string) => !/^hunger|thirst|sleep/i.test(n))
                : criticalNeedsList;
            const maslowNote = filteredNeeds.length > 0
                ? `\n\n=== CRITICAL NEEDS (MASLOW — address these FIRST) ===\nYou are suffering from: ${filteredNeeds.join('; ')}.\n\nThese are PHYSIOLOGICAL needs — the base of Maslow's hierarchy. They outrank every other goal: safety, exploration, investigation, and social connection can wait. Build the FIRST step of your plan around satisfying the most urgent need (eat your food, drink your water, find shelter, rest).\n\nA short detour toward another goal is fine ONLY if you return to the urgent need immediately after. Don't let curiosity or a side-task stand between you and the pressing need.`
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
- GROUNDING: every "item"/"target" MUST come from the Items list, the paths list, People here, or your Carrying/Wearing list — or be an area you are in or know. Room-description scenery that is not a listed Item is NOT interactable; a step referencing it will be REJECTED.
- "speak" steps carry the line in "text". "perform" steps describe a sustained activity in "note" (cook, mine, drill) and may carry "until" (e.g. "ore x5", "dusk") and "duration" (game minutes).
- Account for immediate survival needs, active threats in the room, and the character's current condition.
- Plans are suggestions — if something changes (a threat appears, someone attacks, a new person arrives), the plan may no longer apply. Re-evaluate before acting.

Respond ONLY with a JSON object: {"steps": [{"act": "take", "item": "dried meat"}, {"act": "go", "target": "west passage"}]}`;

            if (!grounding || !facts) {
                // Grounding module unavailable — legacy prose contract as fallback.
                const response = await llmClient.chat([{ role: 'user', content: prompt }], { temperature: 0.7, max_tokens: 560, streaming: false, label: 'plan', responseFormat: _structuredFormats()?.plan });
                return _legacySteps(response);
            }

            // task-700: typed steps, grounded before acceptance. One bounded
            // re-composition: rejected steps return their failed preconditions
            // (with the fact list) to the LLM once; whatever still does not
            // ground is dropped, never executed.
            let groundingBlock = '';
            for (let attempt = 0; attempt < 2; attempt++) {
                // max_tokens 560: a live run truncated a typed re-composition
                // mid-JSON at 300 and the turn ran planless.
                const response = await llmClient.chat([{ role: 'user', content: prompt + groundingBlock }], { temperature: 0.7, max_tokens: 560, streaming: false, label: 'plan', responseFormat: _structuredFormats()?.plan });
                if (!response) return [];
                let cleaned = _repairJSON(response);
                const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
                if (codeBlockMatch) cleaned = codeBlockMatch[1].trim();
                let parsed: any = null;
                try {
                    parsed = JSON.parse(cleaned);
                } catch {
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
                if (!Array.isArray(rawSteps) || !rawSteps.length) return [];

                // Legacy prose contract ({"steps": ["..."]}) — accepted as fallback.
                const legacy = rawSteps.filter((s: unknown) => typeof s === 'string') as string[];
                const typed = rawSteps.filter((s: unknown) => s && typeof s === 'object') as any[];
                if (legacy.length && !typed.length) return legacy.slice(0, 5);
                if (!typed.length) return [];

                const { grounded, rejections } = grounding.ground(typed.slice(0, 5), facts, areaName);
                if (!rejections.length) {
                    return grounded.map((g: { text: string }) => g.text);
                }
                for (const r of rejections) {
                    events.log(`🧭 ${charName} plan step ungrounded: "${grounding.render(r.step)}" — ${r.reason}`, 'system-msg');
                }
                if (attempt === 0) {
                    groundingBlock = `\n\n=== GROUNDING REJECTIONS ===
The following steps were REJECTED because they reference things that do not exist as interactables:
${rejections.map((r: { step: any; reason: string }) => `- "${grounding.render(r.step)}" — ${r.reason}`).join('\n')}

FACTS you may reference: interactables here: ${facts.areaItems.join(', ') || '(none)'}; carrying: ${facts.carried.join(', ') || '(nothing)'}; people here: ${facts.people.join(', ') || '(nobody)'}; paths: ${facts.exits.join(', ') || '(none)'}; known areas: ${facts.knownAreas.join(', ') || '(none)'}.
Re-compose the rejected steps from these facts (or replace them with steps that ground). Keep grounded steps unchanged.`;
                    continue;
                }
                // Second attempt still ungrounded: keep what grounded, drop the rest.
                if (grounded.length) return grounded.map((g: { text: string }) => g.text);
                return [];
            }
            return [];
        } catch (error) {
            return [];
        }
    }

    /**
     * Legacy parse (pre-task-700 prose contract): {"steps": ["..."]}, a raw
     * array, or the old object-array variant. Kept as the fallback path when
     * the grounding module is unavailable.
     */
    function _legacySteps(response: string | null): string[] {
        if (!response) return [];
        let cleaned = _repairJSON(response);
        const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
        if (codeBlockMatch) cleaned = codeBlockMatch[1].trim();
        let parsed: any;
        try {
            parsed = JSON.parse(cleaned);
        } catch {
            return [];
        }
        const arr = Array.isArray(parsed) ? parsed
            : (Array.isArray(parsed?.steps) ? parsed.steps : null);
        if (!Array.isArray(arr)) return [];
        const steps = arr.filter((s: unknown) => typeof s === 'string').slice(0, 5);
        if (steps.length > 0) return steps as string[];
        if (typeof arr[0] === 'object' && arr[0] !== null) {
            const objs = (arr as any[]).map((e: any) => e.examine || e.action || e.step || '').filter(Boolean).slice(0, 5);
            if (objs.length) return objs as string[];
        }
        return [];
    }

    /**
     * Salvage typed steps from a TRUNCATED plan response: pull the complete
     * flat objects out of a half-written {"steps":[...]} and return them. A
     * live run (kraktooth, Rikka) hit max_tokens mid-string and the whole
     * plan was lost, leaving the character to act with no plan at all.
     */
    function _salvageTypedSteps(cleaned: string): any[] {
        const out: any[] = [];
        const objs = cleaned.match(/\{[^{}]*\}/g) || [];
        for (const chunk of objs) {
            try {
                const obj = JSON.parse(chunk);
                if (obj && typeof obj === 'object' && obj.act) out.push(obj);
                else if (obj && Array.isArray(obj.steps)) {
                    for (const s of obj.steps) if (s && typeof s === 'object' && s.act) out.push(s);
                }
            } catch {
                // incomplete trailing object — skip it
            }
        }
        return out.slice(0, 5);
    }

    /**
     * Collect what the previous plan accomplished/failed at, so regeneration
     * does not repeat steps that already failed 3+ times.
     */
    function _previousPlanIssues(charName: string): string {
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
     * @param charName - Character name
     * @returns True if a plan exists and has uncompleted steps
     */
    function hasPlan(charName: string): boolean {
        return PlanTracker.getPlan(charName).length > 0;
    }

    return {
        generate,
        hasPlan
    };
})();
(window as unknown as { PlanManager: typeof PlanManager }).PlanManager = PlanManager;

