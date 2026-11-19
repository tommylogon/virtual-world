/**
 * plan-tracker.js — Plan state ownership and step tracking
 *
 * Owns all per-character plan state:
 *   - plan array, tick, progress, failure map
 *   - step success/failure tracking
 *   - replan eligibility check
 *
 * Replaces the inline `_plans`, `_planTick`, `_planProgress`, `_planFailures`
 * maps and `_trackPlanStep` / `_shouldReplan` methods that previously lived
 * in agent-engine.js.
 *
 * Load BEFORE agent-engine.js.
 *
 * @module agent/plan-tracker — plan state ownership
 * @contributes PlanTracker: plan array, step progress, failure map, replan eligibility
 * @powers "am I still on plan?" — the replan trigger and the (CURRENT) plan marker
 * @relates owns state that used to be inline in agent-engine; read by prompt-builder hasPlan/context-sections
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

(window as unknown as { PlanTracker: unknown }).PlanTracker = (() => {
    'use strict';

    const plans: Record<string, string[]> = {};
    const planTick: Record<string, number> = {};
    const planProgress: Record<string, number> = {};
    const planFailures: Record<string, Record<string, number>> = {};
    const activePursuitId: Record<string, string> = {};
    // task-92: last critical-needs signature + tick of the replan it triggered,
    // so a lingering critical need re-nudges every 5 turns instead of every turn.
    const lastCriticalSet: Record<string, string> = {};
    const lastCriticalReplanTick: Record<string, number> = {};
    // task-185: stop-word list for step tracking — the old >2 char filter passed
    // "the", so any action containing "the" completed any step containing "the".
    const STOP_WORDS = new Set(['the', 'a', 'an', 'to', 'of', 'and', 'or', 'at', 'in', 'on', 'for', 'with', 'is', 'are', 'was', 'it', 'its', "it's"]);

    function getPlan(charName: string) {
        return plans[charName] || [];
    }

    function setPlan(charName: string, steps: string[], turnNumber: number) {
        plans[charName] = steps;
        // task-185: record the TURN clock (shouldReplan compares against
        // turnNumber) — storing time_ticks was a mixed-unit bug that broke
        // plan-age checks across engine re-inits.
        planTick[charName] = Number.isInteger(turnNumber) ? turnNumber : 0;
        planProgress[charName] = 0;
        planFailures[charName] = {};
    }

    function getProgress(charName: string) {
        return planProgress[charName] || 0;
    }

    /** Failure counts per step index (task-185: prompt builders read via PlanTracker now). */
    function getFailures(charName: string) {
        return planFailures[charName] || {};
    }

    /** Advance or block the current plan step based on backend success flag. */
    function trackStep(charName: string, executedAction: string, _resultText: unknown, succeeded: unknown) {
        const plan = plans[charName];
        if (!plan || !plan.length) return;
        const idx = planProgress[charName] || 0;
        if (idx >= plan.length) return;
        const step = plan[idx];
        if (succeeded === false) {
            planFailures[charName] = planFailures[charName] || {};
            const fails = (planFailures[charName][idx] || 0) + 1;
            planFailures[charName][idx] = fails;
            if (fails === 3) {
                events.log(`🚫 ${charName} plan step blocked after ${fails} failures: "${step}"`, 'system-msg');
            }
            return;
        }
        const actionNorm = (executedAction || '').toLowerCase().trim();
        const stepNorm = String(step ?? '').toLowerCase();
        const stepWords = stepNorm.split(/\s+/).filter((w: string) => w && !STOP_WORDS.has(w));
        const actionWords = actionNorm.split(/\s+/).filter((w: string) => w && !STOP_WORDS.has(w));
        // task-185: an action WITH a target must match a non-action step word too —
        // "approach the order counter" must not complete "approach the round the
        // corner to oak lane" on the shared action alone. Bare-action actions
        // (look, wait, rest, ...) still advance on the action match.
        const bareAction = actionWords.length <= 1;
        const overlap = stepNorm.includes(actionNorm) || actionNorm.includes(stepNorm)
            || (bareAction
                ? actionWords.some((w: string) => stepWords.includes(w))
                : actionWords.slice(1).some((w: string) => stepWords.includes(w)));
        if (overlap) {
            planProgress[charName] = idx + 1;
            planFailures[charName] = planFailures[charName] || {};
            planFailures[charName][idx] = 0;
        }
    }

    /**
     * Check whether the character needs a fresh plan.
     * task-185: returns a human-readable REASON string (consumed by the
     * task-340 crisis log line) or null when the current plan is still fine.
     * Side effects unchanged.
     */
    function shouldReplan(charName: string, turnNumber: number, threatAlert: unknown, vitals: any): string | null {
        if (threatAlert) return 'threat detected';
        // Needs-driven replanning (task-92): fire when needs CROSS into critical
        // territory, then re-nudge at most every 5 turns while still critical.
        // Without the crossing gate a starving character would regenerate their
        // plan every single turn (plan churn + token burn).
        const needs = criticalNeeds(vitals);
        if (needs.length) {
            const signature = needs.join('|');
            const lastSignature = lastCriticalSet[charName] || '';
            const lastTick = lastCriticalReplanTick[charName];
            if (signature !== lastSignature || (turnNumber - (lastTick ?? -999)) >= 5) {
                lastCriticalSet[charName] = signature;
                lastCriticalReplanTick[charName] = turnNumber;
                return needs[0];
            }
            return null;
        }
        lastCriticalSet[charName] = '';
        const plan = plans[charName];
        if (!plan || !plan.length) return 'no plan';
        const idx = planProgress[charName] || 0;
        if (idx >= plan.length) return 'plan completed';
        if (!activePursuitId[charName] && (turnNumber - (planTick[charName] || 0)) >= 10) return 'plan aged out';
        const stepFails = (planFailures[charName] || {})[idx] || 0;
        if (stepFails >= 3) return 'current step failed repeatedly';
        return null;
    }

    /**
     * Vitals currently past their critical threshold, as human-readable labels
     * (task-92). Boundaries come from VitalThresholds (task-322 R5) — Bladder
     * is inverted vs the others: high = urgent.
     * @param {Object} vitals - Character vitals object (Capitalized keys)
     * @returns {string[]} e.g. ["exhaustion — rest or sleep", "hunger — eat"]
     */
    function criticalNeeds(vitals: any): string[] {
        if (!vitals) return [];
        const labels: Record<string, string> = {
            Energy: 'exhaustion — you need to rest or sleep',
            Hunger: 'hunger — you need to eat',
            Thirst: 'thirst — you need to drink',
            Sanity: 'fracturing sanity — you need safety or calm',
            Social: 'crushing loneliness — you need company',
            Bladder: 'a bursting bladder — you need a bathroom'
        };
        const out: string[] = [];
        // VitalThresholds (agent/vital-thresholds.js) is a window singleton that
        // is not declared in static/js/types/globals.d.ts, hence the local cast.
        const thresholds = (window as unknown as {
            VitalThresholds: { isCritical(key: string, values: any): boolean };
        }).VitalThresholds;
        for (const key of Object.keys(labels)) {
            if (thresholds.isCritical(key, vitals[key])) out.push(labels[key]);
        }
        return out;
    }

    function reset(charName: string) {
        delete plans[charName];
        delete planTick[charName];
        delete planProgress[charName];
        delete planFailures[charName];
        delete activePursuitId[charName];
        delete lastCriticalSet[charName];
        delete lastCriticalReplanTick[charName];
    }

    function resetAll() {
        for (const key of Object.keys(plans)) reset(key);
    }

    /** Format previous plan issues for the plan-generation prompt. */
    function previousPlanIssues(charName: string): string {
        const plan = plans[charName];
        if (!plan?.length) return '';
        const progress = planProgress[charName] || 0;
        const failures = planFailures[charName] || {};
        const parts: string[] = [];
        for (let i = 0; i < plan.length; i++) {
            if (i < progress && !(failures[i] >= 3)) {
                parts.push(`"${plan[i]}" (done)`);
            } else if (failures[i] >= 3) {
                parts.push(`"${plan[i]}" (FAILED ${failures[i]} times — do NOT repeat; find an alternative or pursue a different goal)`);
            }
        }
        if (!parts.length) return '';
        return `\n=== PREVIOUS PLAN ===\nYour previous plan: ${parts.join('; ')}.\nDo not re-attempt steps marked FAILED.`;
    }

    function _stepToString(step: any): string {
        if (!step) return '';
        if (typeof step === 'string') return step;
        const kind = String(step.kind || step.act || '').toLowerCase().trim();
        const area = step.to || step.area || '';
        const spec = step.spec || step.item || step.target || '';
        if (kind === 'travel' || kind === 'go') {
            return area ? `go ${area}` : 'go';
        }
        if (kind === 'take') {
            return spec ? `take ${spec}` : 'take';
        }
        if (kind === 'drop') {
            return spec ? `drop ${spec}` : 'drop';
        }
        if (kind === 'use' || kind === 'use_on') {
            return step.target ? `use ${spec} on ${step.target}` : (spec ? `use ${spec}` : 'use');
        }
        if (kind === 'wait') {
            return 'wait';
        }
        const text = step.text || step.description || '';
        if (text) return text;
        return `${kind} ${spec || area}`.trim();
    }

    function seedFromPlayer(charName: string, player: any, turnNumber: number = 0): boolean {
        if (!player) return false;
        const pursuit = player.active_pursuit;
        const plan = player.plan;
        const rawSteps = plan?.steps || pursuit?.steps;
        if (!rawSteps || !Array.isArray(rawSteps) || !rawSteps.length) return false;

        const pId = String(pursuit?.assignment_id || plan?.assignment_id || pursuit?.label || plan?.label || 'active_pursuit');
        const currentPId = activePursuitId[charName];

        if (!plans[charName] || !plans[charName].length || currentPId !== pId) {
            const steps = rawSteps.map(_stepToString).filter(Boolean);
            if (!steps.length) return false;
            setPlan(charName, steps, turnNumber);
            activePursuitId[charName] = pId;
            if (typeof plan?.index === 'number' && plan.index >= 0 && plan.index <= steps.length) {
                planProgress[charName] = plan.index;
            }
            return true;
        }
        return false;
    }

    function getActivePursuitId(charName: string): string | null {
        return activePursuitId[charName] || null;
    }

    return {
        getPlan,
        setPlan,
        getProgress,
        getFailures,
        trackStep,
        shouldReplan,
        criticalNeeds,
        reset,
        resetAll,
        previousPlanIssues,
        seedFromPlayer,
        getActivePursuitId
    };
})();

