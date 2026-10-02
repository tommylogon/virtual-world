/**
 * stream-control-mode.js — character control mode cycling (task-340)
 *
 * Extracted from event-stream.js for size compliance; lives on the events
 * API because the UI invokes it from the stream/roster surfaces.
 * Loaded BEFORE event-stream.js.
 *
 * @module stream/control-mode — character control mode cycling
 * @contributes StreamControlMode: cycle avatar / agent / observer control for a character
 * @powers Event stream — switching who you are controlling from the stream and roster surfaces
 * @relates lives on the events API; loaded before event-stream.js
 * @docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
class StreamControlMode {
    _bus: unknown;
    _autonomy: Record<string, boolean>;

    constructor(bus: unknown) {
        this._bus = bus;
        this._autonomy = {};
    }

    isAutonomous(charName: string): boolean {
        if (this._autonomy[charName] === undefined) {
            // Seed from backend so a human (autonomy False) survives reloads
            // and stays human instead of reverting to LLM-driving (task-244).
            const stored = worldState.players?.[charName]?.autonomy;
            this._autonomy[charName] = stored === undefined ? true : Boolean(stored);
        }
        return this._autonomy[charName];
    }

    /**
     * Resolve the control mode for a character:
     *   'npc'   — simple_npc (scripted behaviors, backend tick drives them)
     *   'human' — autonomy off (engine skips them — the human drives via commands)
     *   'llm'   — autonomous non-NPC (agent engine drives them)
     */
    getControlMode(charName: string): 'npc' | 'human' | 'llm' {
        const player = worldState.players?.[charName];
        if (player?.simple_npc) return 'npc';
        if (!this.isAutonomous(charName)) return 'human';
        return 'llm';
    }

    /** Cycle a character through Human → LLM → NPC → Human and apply the backend changes. */
    cycleControlMode(charName: string): void {
        const order = ['human', 'llm', 'npc'];
        const current = this.getControlMode(charName);
        const next = order[(order.indexOf(current) + 1) % order.length];
        const modeLabels: Record<string, string> = {
            human: 'HUMAN-controlled', llm: 'LLM-controlled', npc: 'NPC-controlled'
        };
        const label = modeLabels[next];
        let simpleNpc = false;
        let autonomy = true;
        let makeActive = false;
        if (next === 'human') {
            autonomy = false;
            makeActive = true;
        } else if (next === 'npc') {
            simpleNpc = true;
        }
        ApiClient.updateCharacter(charName, { simple_npc: simpleNpc, autonomy: autonomy }).then(async () => {
            this._autonomy[charName] = autonomy;
            if (makeActive) {
                config.controllingPlayer = charName;
            }
            // Refetch + re-render for ALL modes so the mode badge actually updates.
            const freshState = await worldState.fetch();
            if (freshState && worldState.data) VW?.ui?.renderAll?.(freshState);
            events.log(`${charName} → ${label}`, 'system-msg');
        }).catch(err => {
            events.log(`Failed to switch ${charName}: ${err instanceof Error ? err.message : String(err)}`, 'error-msg');
        });
    }
}
