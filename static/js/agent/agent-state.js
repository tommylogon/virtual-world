/**
 * agent-state.js — Agent turn eligibility and state tracking
 *
 * Determines whether a character can act this turn based on:
 * - Busy/unconscious/resting state
 * - NPC simple_npc flag
 * - Manual mode / no selection
 *
 * Also owns the cancel/abort machinery shared across turn phases.
 *
 * Load BEFORE agent-engine.js.
 */

window.AgentState = (() => {
    'use strict';

    const resting = {};
    const unconscious = {};

    function isBusy(charName, lastResult, player) {
        if (player) {
            const busyStates = new Set(['busy', 'unconscious']);
            if (busyStates.has(player.state)) { resting[charName] = true; return true; }
            const busyActivities = new Set(['sleeping', 'resting', 'waiting', 'meditating', 'bathing', 'sitting', 'lying down']);
            if (busyActivities.has(player.activity?.type)) { resting[charName] = true; return true; }
        }
        if (resting[charName]) { resting[charName] = false; return false; }
        if ((lastResult || '').toLowerCase().includes('you rest')) { resting[charName] = true; return true; }
        return false;
    }

    function markUnconscious(charName, player, state, worldState) {
        if (!unconscious[charName]) {
            unconscious[charName] = true;
            const timer = player?.state_timer || 0;
            const msg = `💤 ${charName} is unconscious — cannot act. ${timer > 0 ? timer + ' ticks until waking...' : ''}`;
            return { message: msg, wasJustSet: true };
        }
        return { wasJustSet: false };
    }

    function clearUnconscious(charName, player) {
        if (unconscious[charName]) {
            unconscious[charName] = false;
            return `🌅 ${charName} regains consciousness.`;
        }
        return null;
    }

    function isUnconscious(charName) {
        return !!unconscious[charName];
    }

    return {
        isBusy,
        markUnconscious,
        clearUnconscious,
        isUnconscious
    };
})();
