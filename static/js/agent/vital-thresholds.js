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

    return {
        CRITICAL,
        WARNING,
        BLADDER_URGENT,
        BLADDER_WARN,
        BLADDER_MILD,
        SANITY_SHATTERED,

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