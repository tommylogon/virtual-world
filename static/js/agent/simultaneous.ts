/**
 * simultaneous.js — the turn-mode vocabulary and per-room grouping (task-101).
 *
 * The "turn mode" dial has five values: the three ordered modes the turn queue
 * owns (sequential / random / initiative) and two simultaneous modes where the
 * queue is ignored. "simultaneous_room" resolves rooms independently while
 * characters inside a room still act in order — simultaneous per room,
 * sequential within the room.
 *
 * Pure functions: no DOM, no agent state. config.js owns the persisted value
 * and agent-engine.js owns the loop.
 *
 * @module agent/simultaneous — turn-mode vocabulary + per-room grouping
 * @contributes VWSimultaneous: MODES, isSimultaneous(), isRoomMode(), normalizeMode(), cooldownFor(), groupByRoom(), roomCooldown(), firstReadyRoom()
 * @powers Turn queue — the "Simultaneous" and "Simultaneous per room" turn modes
 * @relates read by config.js (the dial) and agent-engine.js (the loop)
 * @docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

(window as unknown as { VWSimultaneous: unknown }).VWSimultaneous = (() => {
    'use strict';

    const MODES = Object.freeze({
        SEQUENTIAL: 'sequential',
        RANDOM: 'random',
        INITIATIVE: 'initiative',
        SIMULTANEOUS: 'simultaneous',
        SIMULTANEOUS_ROOM: 'simultaneous_room',
    });

    const ORDERED: string[] = [MODES.SEQUENTIAL, MODES.RANDOM, MODES.INITIATIVE];

    function isSimultaneous(mode: string) {
        return mode === MODES.SIMULTANEOUS || mode === MODES.SIMULTANEOUS_ROOM;
    }

    function isRoomMode(mode: string) {
        return mode === MODES.SIMULTANEOUS_ROOM;
    }

    /**
     * Normalise a stored setting into a dial value. Accepts the legacy boolean
     * string ('true' → simultaneous) so an old save keeps its behaviour.
     */
    function normalizeMode(stored: unknown, fallbackOrder?: string): string {
        if (stored === 'true' || stored === true) return MODES.SIMULTANEOUS;
        if (stored === 'simultaneous' || stored === 'simultaneous_room') return stored as string;
        if (ORDERED.includes(stored as string)) return stored as string;
        return ORDERED.includes(fallbackOrder as string) ? (fallbackOrder as string) : MODES.SEQUENTIAL;
    }

    /**
     * A character's act countdown: Social speeds it up, traits and exhaustion
     * slow it down. Returns a countdown in ticks (3–15).
     */
    function cooldownFor(player?: PlayerLike | null) {
        if (!player) return 8;
        const traits: Record<string, unknown> = player.traits || {};
        let c = 8 + Math.round((50 - (player.vitals?.Social ?? 50)) / 25);
        if (traits.impatient) c -= 2;
        if (traits.patient) c += 2;
        if (traits.sprinter) c -= 1;
        if ((player.vitals?.Energy ?? 100) < 35) c += 1;
        return Math.max(3, Math.min(15, c));
    }

    /**
     * Autonomous, living characters grouped by area. Names within a room are
     * sorted so the room's sequential order is stable; rooms keep roster order.
     */
    function groupByRoom(players: Record<string, PlayerLike> | null | undefined, options?: GroupByRoomOptions) {
        const opts: GroupByRoomOptions = options || {};
        const isAutonomous = opts.isAutonomous || (() => true);
        const ghostMode = !!opts.ghostMode;
        const rooms: Record<string, string[]> = {};
        for (const name of Object.keys(players || {})) {
            const p = (players as Record<string, PlayerLike>)[name];
            if (!p || !isAutonomous(name)) continue;
            if (p.state === 'dead' && !ghostMode) continue;
            const area = p.current_area || '';
            (rooms[area] || (rooms[area] = [])).push(name);
        }
        for (const area of Object.keys(rooms)) rooms[area].sort();
        return rooms;
    }

    /** A room's cadence is set by its fastest member (minimum countdown). */
    function roomCooldown(names: string[] | null | undefined, players: Record<string, PlayerLike> | null | undefined) {
        if (!names || !names.length) return 8;
        let fastest = Infinity;
        for (const name of names) {
            fastest = Math.min(fastest, cooldownFor(players ? players[name] : null));
        }
        return Number.isFinite(fastest) ? fastest : 8;
    }

    /** The first room whose countdown has elapsed, or null when none is ready. */
    function firstReadyRoom(rooms: Record<string, unknown> | null | undefined, countdowns: Record<string, number> | null | undefined): string | null {
        for (const area of Object.keys(rooms || {})) {
            const remaining = (countdowns || {})[area];
            if (remaining === undefined || remaining <= 0) return area;
        }
        return null;
    }

    /** Decrement every countdown by one, never below zero. */
    function tickCountdowns(countdowns: Record<string, number> | null | undefined) {
        for (const key of Object.keys(countdowns || {})) {
            const c = countdowns as Record<string, number>;
            if (c[key] > 0) c[key] -= 1;
        }
    }

    return {
        MODES,
        ORDERED,
        isSimultaneous,
        isRoomMode,
        normalizeMode,
        cooldownFor,
        groupByRoom,
        roomCooldown,
        firstReadyRoom,
        tickCountdowns,
    };
})();


// NOTE: these shape declarations sit AFTER the first value statement on purpose.
// A leading `interface`/`type` makes TypeScript drop the file's leading JSDoc
// block from the emitted .js, and tools/js_module_index.py reads the `@module`
// tag out of that emitted .js.
interface PlayerLike {
    traits?: Record<string, unknown>;
    vitals?: Record<string, number>;
    state?: string;
    current_area?: string;
}

interface GroupByRoomOptions {
    isAutonomous?: (name: string) => boolean;
    ghostMode?: boolean;
}
