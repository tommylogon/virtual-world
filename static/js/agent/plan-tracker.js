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
 */

window.PlanTracker = (() => {
    'use strict';

    const plans = {};
    const planTick = {};
    const planProgress = {};
    const planFailures = {};
    // task-92: last critical-needs signature + tick of the replan it triggered,
    // so a lingering critical need re-nudges every 5 turns instead of every turn.
    const lastCriticalSet = {};
    const lastCriticalReplanTick = {};

    function getPlan(charName) {
        return plans[charName] || [];
    }

    function setPlan(charName, steps) {
        plans[charName] = steps;
        planTick[charName] = worldState.data?.time_ticks || 0;
        planProgress[charName] = 0;
        planFailures[charName] = {};
    }

    function getProgress(charName) {
        return planProgress[charName] || 0;
    }

    /** Advance or block the current plan step based on backend success flag. */
    function trackStep(charName, executedAction, resultText, succeeded) {
        const plan = plans[charName];
        if (!plan || !plan.length) return;
        const idx = planProgress[charName] || 0;
        if (idx >= plan.length) return;
        const step = plan[idx];
        if (succeeded === false) {
            planFailures[charName] = planFailures[charName] || {};
            const fails = (planFailures[charName][idx] || 0) + 1;
            planFailures[charName][idx] = fails;
            if (fails >= 3) {
                planProgress[charName] = idx + 1;
                planFailures[charName][idx] = 0;
                events.log(`🚫 ${charName} plan step blocked after ${fails} failures: "${step}"`, 'system-msg');
            }
            return;
        }
        const actionNorm = (executedAction || '').toLowerCase();
        const stepNorm = String(step ?? '').toLowerCase();
        const stepWords = stepNorm.split(/\s+/).filter(w => w.length > 2);
        const actionWords = actionNorm.split(/\s+/).filter(w => w.length > 2);
        const overlap = stepWords.some(w => actionWords.includes(w)) || stepNorm.includes(actionNorm) || actionNorm.includes(stepNorm);
        if (overlap) {
            planProgress[charName] = idx + 1;
            planFailures[charName] = planFailures[charName] || {};
            planFailures[charName][idx] = 0;
        }
    }

    /** Check whether the character needs a fresh plan. */
    function shouldReplan(charName, turnNumber, threatAlert, vitals) {
        if (threatAlert) return true;
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
                return true;
            }
            return false;
        }
        lastCriticalSet[charName] = '';
        if (!plans[charName] || (turnNumber - (planTick[charName] || 0)) >= 10) return true;
        const idx = planProgress[charName] || 0;
        const stepFails = (planFailures[charName] || {})[idx] || 0;
        if (stepFails >= 3) return true;
        return false;
    }

    /**
     * Vitals currently past their critical threshold, as human-readable labels
     * (task-92). Boundaries come from VitalThresholds (task-322 R5) — Bladder
     * is inverted vs the others: high = urgent.
     * @param {Object} vitals - Character vitals object (Capitalized keys)
     * @returns {string[]} e.g. ["exhaustion — rest or sleep", "hunger — eat"]
     */
    function criticalNeeds(vitals) {
        if (!vitals) return [];
        const labels = {
            Energy: 'exhaustion — you need to rest or sleep',
            Hunger: 'hunger — you need to eat',
            Thirst: 'thirst — you need to drink',
            Sanity: 'fracturing sanity — you need safety or calm',
            Social: 'crushing loneliness — you need company',
            Bladder: 'a bursting bladder — you need a bathroom'
        };
        const out = [];
        for (const key of Object.keys(labels)) {
            if (VitalThresholds.isCritical(key, vitals[key])) out.push(labels[key]);
        }
        return out;
    }

    function reset(charName) {
        delete plans[charName];
        delete planTick[charName];
        delete planProgress[charName];
        delete planFailures[charName];
        delete lastCriticalSet[charName];
        delete lastCriticalReplanTick[charName];
    }

    function resetAll() {
        for (const key of Object.keys(plans)) reset(key);
    }

    /** Format previous plan issues for the plan-generation prompt. */
    function previousPlanIssues(charName) {
        const plan = plans[charName];
        if (!plan?.length) return '';
        const progress = planProgress[charName] || 0;
        const failures = planFailures[charName] || {};
        const parts = [];
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

    return {
        getPlan,
        setPlan,
        getProgress,
        trackStep,
        shouldReplan,
        criticalNeeds,
        reset,
        resetAll,
        previousPlanIssues
    };
})();
