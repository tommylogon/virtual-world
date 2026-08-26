/**
 * threat-detector.js — Room threat analysis for character agents
 *
 * Scans the current area for hostile actors and returns a formatted
 * threat alert string to prepend to the DECIDE prompt, or null if safe.
 *
 * Load AFTER agent/agent-state.js, BEFORE agent-engine.js.
 */

window.ThreatDetector = (() => {
    'use strict';

    function getThreatAlert(charName, player, currentArea, turnEvents) {
        const areaPlayers = worldState.data?.players_in_area || [];
        const allPlayers = worldState.data?.players || {};
        const threats = [];

        for (const person of areaPlayers) {
            if (person.name === charName) continue;
            const otherPlayer = allPlayers[person.name];
            if (!otherPlayer) continue;

            if (otherPlayer.state === 'hidden' || otherPlayer.state === 'stealthed') continue;

            const hasMet = worldState.hasMet(charName, person.name);
            const threatName = hasMet ? person.name
                : (otherPlayer.description?.split(/[.,;]/)[0]?.trim() || 'A hostile figure');

            if (otherPlayer.traits?.hostile) {
                threats.push(threatName);
                continue;
            }

            const theirRelToMe = otherPlayer.relationships?.[charName]?.closeness;
            if (theirRelToMe !== undefined && theirRelToMe < -20) {
                threats.push(threatName);
                continue;
            }

            const justAttacked = (turnEvents || []).some(
                turnEvent => turnEvent.actor === person.name && turnEvent.action === 'attack'
            );
            if (justAttacked) {
                threats.push(threatName);
                continue;
            }
        }

        if (threats.length === 0) return null;

        return `⚠️ IMMEDIATE DANGER: ${threats.join(', ')} ${threats.length > 1 ? 'are' : 'is'} in this room and hostile toward you. ` +
               `Your current plan is INVALID. You MUST flee, hide, fight, or warn others NOW. ` +
               `Do NOT examine items, explore doors, or follow your previous plan while a threat is present.`;
    }

    return { getThreatAlert };
})();
