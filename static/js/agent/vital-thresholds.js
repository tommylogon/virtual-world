/**
 * vital-thresholds.js — the ONE source for vitals tier boundaries (task-322 R5).
 *
 * Before this, "what counts as critical" was hardcoded in three places
 * (describeVitals prose tiers, tick_manager need-messages, plan-tracker
 * criticalNeeds) and could drift. Prose stays local to each consumer; the
 * NUMBERS live here.
 *
 * Load BEFORE character-state.js and plan-tracker.js.
 */

window.VitalThresholds = (() => {
    'use strict';

    // Vitals where LOW = urgent (0-100 scales).
    const CRITICAL = 25;   // replan fires (task-92); strongest warning prose
    const WARNING = 50;    // mild "getting hungry/tired" prose tier

    // DRIVE vitals are INVERTED like Bladder: they RISE toward 100 and max
    // out at the deadly/urgent end (Hunger/Thirst flipped 2026-08-23,
    // task-337). Bladder: 0 = relieved, 100 = about to burst.
    const BLADDER_URGENT = 90;
    const BLADDER_WARN = 75;
    const BLADDER_MILD = 65;
    const DRIVE_URGENT = 90;
    const DRIVE_WARN = 75;
    const DRIVE_MILD = 50;

    // Sanity has extra granularity (progressive insanity tiers).
    const SANITY_SHATTERED = 10;

    // ── Hover explanations (task-129) ─────────────────────────────────
    // "What does this vital do" one-liners for the inspector / turn-panel
    // tooltips. Polarity-aware; the human NL prose still comes from
    // PromptBuilder.describeVital (loaded later — called lazily).
    const EXPLAIN = {
        HP: 'hit points — at 0 you die.',
        Energy: 'drains with activity — rest or sleep to recover.',
        Hunger: 'a drive — it fills over time; eat before it maxes at 100.',
        Thirst: 'a drive — it fills over time; drink before it maxes at 100.',
        Bladder: 'fills over time; find a bathroom before 100.',
        Sanity: 'drains in isolation and darkness; at 0 you take damage.',
        Social: 'drains alone, refills with company.',
        Hygiene: 'drains with grime — wash up.',
        Entertainment: 'drains with monotony — seek something new.',
        Temperature: 'comfort band 35-37°C — below is hypothermia, above is heat stroke.',
        Mana: 'spent casting — rest to recover.',
    };

    function explain(key) {
        return EXPLAIN[key] || 'one of your vitals — click for details.';
    }

    function _isDriveKey(key) { return key === 'Hunger' || key === 'Thirst' || key === 'Bladder'; }
    function _isBandKey(key) { return key === 'Temperature'; }

    /** Healthy-state line used when describeVital has no prose for the band. */
    function healthyLine(key) {
        if (_isBandKey(key)) return 'within the comfort band (35-37°C).';
        if (_isDriveKey(key)) return 'satisfied — no pressing need right now.';
        return 'feeling fine — no pressing need right now.';
    }

    /**
     * Full hover text for a vital: "Hunger: 9/100" + what the vital does +
     * the natural-language prose (or a healthy-state line). The inspector and
     * human turn panel both use this — describeVital only speaks when a vital
     * is past a tier (nothing at Hunger 9), so the explanation + healthy line
     * close that gap.
     */
    function hoverText(vitals, key) {
        if (!vitals || vitals[key] === undefined || vitals[key] === null) return '';
        const isTemp = key === 'Temperature';
        const max = key === 'HP' ? (vitals.Max_HP || 100)
            : isTemp ? 45
            : key === 'Mana' ? (vitals.Max_Mana || 100)
            : 100;
        const suffix = isTemp ? '°C' : '';
        const display = isTemp ? Math.round(Number(vitals[key])) : Number(vitals[key]);
        const nl = (window.PromptBuilder?.describeVital?.(vitals, key) || '').trim();
        const lines = [`${key}: ${display}/${max}${suffix}`, explain(key)];
        lines.push(nl || healthyLine(key));
        return lines.join('\n');
    }

    return {
        CRITICAL,
        WARNING,
        BLADDER_URGENT,
        BLADDER_WARN,
        BLADDER_MILD,
        SANITY_SHATTERED,

        explain,
        healthyLine,
        hoverText,

        /** True when the vital is past its critical threshold (task-92). */
        isCritical(key, value) {
            if (value === undefined || value === null) return false;
            switch (key) {
                case 'Bladder': return value >= BLADDER_URGENT;
                case 'Hunger':
                case 'Thirst':
                    // drives: high = urgent (flipped task-337)
                    return value >= DRIVE_URGENT;
                case 'Energy':
                case 'Sanity':
                case 'Social':
                    return value <= CRITICAL;
                default: return false;
            }
        }
    };
})();