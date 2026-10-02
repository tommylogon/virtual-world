/**
 * sim-round.js — round-completion bookkeeping for simultaneous modes (task-533)
 *
 * @module agent/sim-round — round-completion bookkeeping for the simultaneous modes
 * @contributes VWSimRound: participants(), isComplete(), markResolved(), pendingFor()
 * @powers Turn queue — whether a simultaneous round has finished and the world may advance
 * @relates used by agent-engine; the cadence helper is agent/simultaneous
 * @docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
 *
 * Pure roster/set arithmetic, deliberately free of DOM and engine state so it can
 * be unit tested. AgentEngine owns the mutable `_simRound` Set and the side effect
 * (`TurnQueue.endTurn()`); everything decidable lives here.
 *
 * ## Why a round needs completing at all
 *
 * A simultaneous mode used to step characters without ever closing a round, so
 * `endTurn()` was never called and `tick_turn()` never ran. The world did not
 * merely lose a clock: no vitals decay, no background simulation, no soak
 * orders, no item ticks, no turn triggers. Nothing happened.
 *
 * ## The human is a participant
 *
 * Not an exemption. Everyone alive owes the round a turn, human included, so a
 * slow player stalls the world — the same contract turn-based mode already has.
 * The human is prompted last, and `endSimRound()` lets them pass. There is
 * deliberately no idle timeout: the world advances when the player says so.
 *
 * `ghostMode` decides whether dead characters still participate. Default false
 * (dead means out), matching the turn queue's own filter.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const VWSimRound = (() => {
    'use strict';

    /**
     * Everyone whose turn counts toward a round: the living characters, human
     * and autonomous alike.
     *
     * @param {Object} players  - roster keyed by name
     * @param {Object} [opts]
     * @param {boolean} [opts.ghostMode] - dead characters still participate
     * @returns {string[]} names, stable order
     */
    function participants(
        players: Record<string, { state?: string } | undefined>,
        opts?: { ghostMode?: boolean },
    ): string[] {
        const o = opts || {};
        const ghost = !!o.ghostMode;
        return Object.keys(players || {}).filter(name => {
            const p = players[name];
            if (!p) return false;
            return p.state !== 'dead' || ghost;
        });
    }

    /**
     * Is every participant marked resolved?
     *
     * An empty roster is NOT complete: there is nobody to advance for, and
     * closing on it would spin the world forward on every loop iteration.
     *
     * @param {string[]} roster - participants
     * @param {Set<string>|Array<string>} resolved
     * @returns {boolean}
     */
    function isComplete(roster: string[], resolved: Set<string> | string[]): boolean {
        if (!roster || roster.length === 0) return false;
        const done = resolved instanceof Set
            ? resolved
            : new Set(resolved || []);
        return roster.every(name => done.has(name));
    }

    /**
     * Who is still owed a turn.
     * @param {string[]} roster
     * @param {Set<string>|Array<string>} resolved
     * @returns {string[]}
     */
    function pendingFor(roster: string[], resolved: Set<string> | string[]): string[] {
        const done = resolved instanceof Set
            ? resolved
            : new Set(resolved || []);
        return (roster || []).filter(name => !done.has(name));
    }

    /**
     * Mark a character resolved, tolerating an uninitialised set.
     * @param {Set<string>} set - mutated in place
     * @param {string} name
     * @returns {Set<string>} the same set
     */
    function markResolved(set: Set<string>, name: string): Set<string> {
        if (!name) return set;
        if (!set || typeof set.add !== 'function') return set;
        set.add(name);
        return set;
    }

    return { participants, isComplete, pendingFor, markResolved };
})();

(window as unknown as { VWSimRound: typeof VWSimRound }).VWSimRound = VWSimRound;
