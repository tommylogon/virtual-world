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
 *
 * @module shared/vital-color — polarity-aware vital bar colours
 * @contributes VitalColor: colour + percent for a vital (drives invert, Temperature band, Mana purple)
 * @powers the vital bars in the inspector and the human turn panel's You strip
 * @relates reads vital_polarity from /api/state
 * @docs docs/virtualWorld/Characters/Vitals System.md
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
        const values = vitals || {};
        const value = Number(values[key]) || 0;
        if (key === 'Mana') return 'ok';
        if (key === 'Temperature') {
            if (value < 33 || value > 40) return 'bad';
            if (value < 35 || value > 39) return 'warn';
            return 'ok';
        }
        if (key === 'HP' && values.Max_HP) {
            const pct = (value / values.Max_HP) * 100;
            return pct <= 20 ? 'bad' : (pct <= 35 ? 'warn' : 'ok');
        }
        const isDrive = (window.worldState?.data?.vital_polarity || {})[key] === 'drive';
        if (isDrive) return value >= 85 ? 'bad' : (value >= 60 ? 'warn' : 'ok');
        return value <= 15 ? 'bad' : (value <= 30 ? 'warn' : 'ok');
    }

    function bar(vitals, key) {
        const values = vitals || {};
        const value = Number(values[key]) || 0;
        if (key === 'Mana') return '#7c5cfc';
        if (key === 'Temperature') {
            return value < 33 ? BAD : (value < 35 ? '#58a6ff' : (value <= 39 ? GOOD : (value <= 40 ? MID : BAD)));
        }
        const isDrive = (window.worldState?.data?.vital_polarity || {})[key] === 'drive';
        if (isDrive) return value > 50 ? BAD : (value > 20 ? MID : GOOD);
        return value > 50 ? GOOD : (value > 20 ? MID : BAD);
    }

    /** Fill percentage 0-100. Temperature maps the 25-45°C window. */
    function percent(vitals, key) {
        const values = vitals || {};
        const value = Number(values[key]) || 0;
        if (key === 'Temperature') {
            return Math.max(0, Math.min(100, ((value - 25) / 20) * 100));
        }
        let max = 100;
        if (key === 'HP' && values.Max_HP) max = values.Max_HP;
        if (key === 'Mana' && values.Max_Mana) max = values.Max_Mana;
        return Math.max(0, Math.min(100, (value / max) * 100));
    }

    function suffix(key) {
        return key === 'Temperature' ? '°C' : '';
    }

    return { bar, level, percent, suffix };
})();
