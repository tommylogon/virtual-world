/**
 * vital-color.js — ONE polarity-aware color/percent implementation for
 * vital bars (task-337 follow-up; shared by the inspector's agent-view
 * and the human turn composer's you-strip).
 *
 * Reads vital_polarity from the world state payload (/api/state):
 * drives (Hunger/Thirst/Bladder) invert — high value = red. Temperature
 * uses its comfort-band thresholds; Mana is static purple.
 *
 * Load AFTER world-state.js, BEFORE any consumer.
 */

window.VitalColor = (() => {
    'use strict';

    const GOOD = '#3fb950', MID = '#e3b341', BAD = '#f85149';

    /**
     * Severity tier for a vital: 'ok' | 'warn' | 'bad'.
     * Drives (Hunger/Thirst/Bladder) invert — high value = bad.
     * Thresholds roughly match the Alerts panel (ui-controller renderAlerts).
     * Used for the inspector's quiet-dim, not for bar colors.
     */
    function level(vitals, key) {
        const v = vitals || {};
        const n = Number(v[key]) || 0;
        if (key === 'Mana') return 'ok';
        if (key === 'Temperature') {
            if (n < 33 || n > 40) return 'bad';
            if (n < 35 || n > 39) return 'warn';
            return 'ok';
        }
        if (key === 'HP' && v.Max_HP) {
            const pct = (n / v.Max_HP) * 100;
            return pct <= 20 ? 'bad' : (pct <= 35 ? 'warn' : 'ok');
        }
        const isDrive = (window.worldState?.data?.vital_polarity || {})[key] === 'drive';
        if (isDrive) return n >= 85 ? 'bad' : (n >= 60 ? 'warn' : 'ok');
        return n <= 15 ? 'bad' : (n <= 30 ? 'warn' : 'ok');
    }

    function bar(vitals, key) {
        const v = vitals || {};
        const n = Number(v[key]) || 0;
        if (key === 'Mana') return '#7c5cfc';
        if (key === 'Temperature') {
            return n < 33 ? BAD : (n < 35 ? '#58a6ff' : (n <= 39 ? GOOD : (n <= 40 ? MID : BAD)));
        }
        const isDrive = (window.worldState?.data?.vital_polarity || {})[key] === 'drive';
        if (isDrive) return n > 50 ? BAD : (n > 20 ? MID : GOOD);
        return n > 50 ? GOOD : (n > 20 ? MID : BAD);
    }

    /** Fill percentage 0-100. Temperature maps the 25-45°C window. */
    function percent(vitals, key) {
        const v = vitals || {};
        const n = Number(v[key]) || 0;
        if (key === 'Temperature') {
            return Math.max(0, Math.min(100, ((n - 25) / 20) * 100));
        }
        let max = 100;
        if (key === 'HP' && v.Max_HP) max = v.Max_HP;
        if (key === 'Mana' && v.Max_Mana) max = v.Max_Mana;
        return Math.max(0, Math.min(100, (n / max) * 100));
    }

    function suffix(key) {
        return key === 'Temperature' ? '°C' : '';
    }

    return { bar, level, percent, suffix };
})();
