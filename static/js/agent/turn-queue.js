/**
 * turn-queue.js — Turn queue management for turn-based agent simulation
 *
 * Manages character turn ordering (sequential, random, or initiative-based),
 * turn advancement, and turn tracking. State lives on the VW.agent instance
 * (AgentEngine) as .turnQueue, .currentTurnIndex, .turnNumber, .initiativeRolls.
 *
 * Usage: TurnQueue.initialize()
 *        TurnQueue.advance()
 *        TurnQueue.getCurrentCharacter()
 *
 * Load this AFTER agent-engine.js in index.html (references VW.agent).
 */

window.TurnQueue = (() => {
    'use strict';

    /**
     * Get a reference to the AgentEngine instance that owns turn state.
     * @returns {Object} The agent instance (with .turnQueue, .currentTurnIndex, etc.)
     */
    function _getAgent() {
        return VW?.agent || {};
    }

    /**
     * Initialize (or re-initialize) the turn queue from the current world state.
     *
     * Builds a list of all non-dead players (or all when ghostMode is on),
     * then sorts by the configured `config.turnOrder`:
     *   - 'initiative': D20 + DEX bonus, highest first
     *   - 'random': shuffled
     *   - 'sequential' (default): alphabetical
     *
     * Resets turn index and turn number to 0.
     */
    function initialize() {
        if (!worldState.players || Object.keys(worldState.players).length === 0) {
            const agent = _getAgent();
            agent.turnQueue = [];
            agent.initiativeRolls = {};
            return;
        }
        let allPlayers = Object.keys(worldState.players);
        if (!config.ghostMode) allPlayers = allPlayers.filter(charName => worldState.players[charName]?.state !== 'dead');
        const agent = _getAgent();
        agent.initiativeRolls = {};
        if (allPlayers.length === 0) {
            agent.turnQueue = [];
            agent.currentTurnIndex = 0;
            agent.turnNumber = 0;
            return;
        }
        switch (config.turnOrder) {
            case 'initiative':
                // Roll d20 + DEX bonus for each character
                const dexMap = {};
                for (const charName of allPlayers) {
                    const dex = worldState.players[charName]?.stats?.DEX || 10;
                    const bonus = Math.floor((dex - 10) / 2);
                    const roll = Math.floor(Math.random() * 20) + 1 + bonus;
                    agent.initiativeRolls[charName] = roll;
                    dexMap[charName] = roll;
                }
                agent.turnQueue = allPlayers.sort((a, b) => {
                    const diff = (dexMap[b] || 0) - (dexMap[a] || 0);
                    if (diff !== 0) return diff;
                    return a.localeCompare(b); // Alphabetical tiebreaker
                });
                break;
            case 'random':
                agent.turnQueue = allPlayers.sort(() => Math.random() - 0.5);
                break;
            default:
                agent.turnQueue = allPlayers.sort();
                break;
        }
        agent.currentTurnIndex = 0;
        agent.turnNumber = 0;
    }

    /**
     * Reconcile the queue against the current world roster.
     *
     * If the set of (non-dead) players differs from the queue, re-initialize —
     * this catches characters added (or killed) while the simulation is
     * running, which the empty-check in `initialize()` alone misses.
     * Preserves turnNumber so a roster change doesn't reset the clock.
     * @returns {boolean} True if the queue was rebuilt
     */
    function reconcile() {
        const agent = _getAgent();
        if (!config.turnBased) return false;
        if (!worldState.players || Object.keys(worldState.players).length === 0) {
            if (agent.turnQueue && agent.turnQueue.length === 0) return false;
            initialize();
            return true;
        }
        let allPlayers = Object.keys(worldState.players);
        if (!config.ghostMode) allPlayers = allPlayers.filter(charName => worldState.players[charName]?.state !== 'dead');
        const current = new Set(agent.turnQueue || []);
        const expected = new Set(allPlayers);
        if (current.size === expected.size && [...current].every(p => expected.has(p))) {
            return false;
        }
        const prevTurnNumber = agent.turnNumber || 0;
        initialize();
        agent.turnNumber = prevTurnNumber;
        return true;
    }

    /**
     * End the current turn: advance the clock and run the per-turn pipeline.
     *
     * Increments turnNumber and applies turn decay / tick effects via
     * ApiClient.applyTurn(), then clears turn events. This is what happens
     * when a full turn-based cycle wraps — and it is ALSO used directly in
     * non-turn-based mode where each stepped character counts as one turn
     * (task-241), so time advances and new-turn effects play there too.
     * The world state is refetched between applyTurn() and clearTurnEvents()
     * so fresh turn_events (simple-NPC behavior output) survive to be
     * displayed before the backend wipes them.
     */
    async function endTurn() {
        const agent = _getAgent();
        agent.turnNumber = (agent.turnNumber || 0) + 1;
        if (config.turnBased && config.turnOrder === 'random') {
            reshuffleRandom();
        }
        try {
            await ApiClient.applyTurn();
        } catch (err) {
            console.error('Turn decay failed:', err);
        }
        try {
            await worldState.fetch();
        } catch (err) {
            console.error('World state fetch after turn failed:', err);
        }
        ApiClient.clearTurnEvents().catch(err => console.error('Clear events failed:', err));
    }

    /**
     * Advance to the next character's turn, wrapping around the queue.
     *
     * When a full cycle completes (currentTurnIndex wraps back to 0),
     * ends the turn via endTurn() (clock advance + decay + event clear).
     *
     * Also updates config.controllingPlayer to the next character.
     */
    async function advance() {
        const agent = _getAgent();
        if (!agent.turnQueue || agent.turnQueue.length === 0) return;
        agent.currentTurnIndex = ((agent.currentTurnIndex || 0) + 1) % agent.turnQueue.length;
        config.controllingPlayer = getCurrentCharacter();
        if (agent.currentTurnIndex === 0) {
            await endTurn();
        }
    }

    /**
     * Get the name of the character whose turn it currently is.
     * @returns {string|null} Character name, or null if queue is empty
     */
    function getCurrentCharacter() {
        const agent = _getAgent();
        if (!agent.turnQueue || agent.turnQueue.length === 0) return null;
        return agent.turnQueue[agent.currentTurnIndex || 0];
    }

    /**
     * Re-roll every character's initiative (d20 + DEX bonus) and re-sort the
     * queue by the new rolls. Only meaningful when config.turnOrder is
     * 'initiative' — otherwise it's a no-op.
     *
     * Unlike initialize(), this preserves turnNumber and keeps the same
     * character "current" (moves the turn index to their new position).
     */
    function rerollInitiatives() {
        const agent = _getAgent();
        if (!agent.turnQueue || agent.turnQueue.length === 0) return;
        if (config.turnOrder !== 'initiative') return;
        const current = getCurrentCharacter();
        const dexMap = {};
        for (const charName of agent.turnQueue) {
            const dex = worldState.players[charName]?.stats?.DEX || 10;
            const bonus = Math.floor((dex - 10) / 2);
            const roll = Math.floor(Math.random() * 20) + 1 + bonus;
            agent.initiativeRolls[charName] = roll;
            dexMap[charName] = roll;
        }
        agent.turnQueue.sort((a, b) => {
            const diff = (dexMap[b] || 0) - (dexMap[a] || 0);
            if (diff !== 0) return diff;
            return a.localeCompare(b); // Alphabetical tiebreaker
        });
        if (current) {
            const idx = agent.turnQueue.indexOf(current);
            agent.currentTurnIndex = idx >= 0 ? idx : 0;
        }
    }

    /**
     * Re-shuffle the turn queue for 'random' order when a full round wraps
     * (task-310). The next round starts with whoever lands first, so the
     * controlling player is updated to match the new index 0.
     */
    function reshuffleRandom() {
        const agent = _getAgent();
        if (!agent.turnQueue || agent.turnQueue.length <= 1) return;
        for (let i = agent.turnQueue.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [agent.turnQueue[i], agent.turnQueue[j]] = [agent.turnQueue[j], agent.turnQueue[i]];
        }
        agent.currentTurnIndex = 0;
        config.controllingPlayer = agent.turnQueue[0];
    }

    return {
        initialize,
        reconcile,
        advance,
        endTurn,
        getCurrentCharacter,
        rerollInitiatives,
        reshuffleRandom
    };
})();
