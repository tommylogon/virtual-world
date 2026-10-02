/**
 * agent-state.js — Agent turn eligibility and state tracking
 *
 * @module agent/agent-state — turn eligibility + abort machinery
 * @contributes AgentState: can-act checks (busy/unconscious/resting/simple_npc/manual) and cancel flags
 * @powers Activities & states — skipping characters who cannot act, and clean cancellation mid-turn
 * @relates consulted by agent-engine on every step; loaded before it
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
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
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const AgentState = (() => {
    'use strict';

    const resting: Record<string, boolean> = {};
    const unconscious: Record<string, boolean> = {};

    function isBusy(charName: string, lastResult: string | null | undefined, player: AgentPlayer | null | undefined): boolean {
        if (player) {
            const busyStates = new Set(['busy', 'unconscious']);
            if (busyStates.has(String(player.state))) { resting[charName] = true; return true; }
            const busyActivities = new Set(['sleeping', 'resting', 'waiting', 'meditating', 'bathing', 'sitting', 'lying down']);
            if (busyActivities.has(String(player.activity?.type))) { resting[charName] = true; return true; }
        }
        if (resting[charName]) { resting[charName] = false; return false; }
        if (String(lastResult || '').toLowerCase().includes('you rest')) { resting[charName] = true; return true; }
        return false;
    }

    function markUnconscious(charName: string, player: AgentPlayer | null | undefined, state: unknown, worldState: unknown): { message?: string; wasJustSet: boolean } {
        if (!unconscious[charName]) {
            unconscious[charName] = true;
            const timer = Number(player?.state_timer || 0);
            const msg = `💤 ${charName} is unconscious — cannot act. ${timer > 0 ? timer + ' ticks until waking...' : ''}`;
            return { message: msg, wasJustSet: true };
        }
        return { wasJustSet: false };
    }

    function clearUnconscious(charName: string, player: AgentPlayer | null | undefined): string | null {
        if (unconscious[charName]) {
            unconscious[charName] = false;
            return `🌅 ${charName} regains consciousness.`;
        }
        return null;
    }

    function isUnconscious(charName: string): boolean {
        return !!unconscious[charName];
    }

    return {
        isBusy,
        markUnconscious,
        clearUnconscious,
        isUnconscious
    };
})();

(window as unknown as { AgentState: typeof AgentState }).AgentState = AgentState;

// Declared below the first value statement on purpose: TypeScript drops a
// file's leading JSDoc block when the first statement is type-only, which would
// strip the `@module` header tools/js_module_index.py reads.
interface AgentPlayer {
    state?: unknown;
    state_timer?: unknown;
    activity?: { type?: unknown } | null;
    [key: string]: unknown;
}
