/**
 * stream-control-mode.js — character control mode cycling (task-340)
 *
 * Extracted from event-stream.js for size compliance; lives on the events
 * API because the UI invokes it from the stream/roster surfaces.
 * Loaded BEFORE event-stream.js.
 */
class StreamControlMode {
    constructor(bus) {
        this._bus = bus;
        this._autonomy = {};
    }

    isAutonomous(charName) {
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
    getControlMode(charName) {
        const player = worldState.players?.[charName];
        if (player?.simple_npc) return 'npc';
        if (!this.isAutonomous(charName)) return 'human';
        return 'llm';
    }

    /** Cycle a character through Human → LLM → NPC → Human and apply the backend changes. */
    cycleControlMode(charName) {
        const order = ['human', 'llm', 'npc'];
        const current = this.getControlMode(charName);
        const next = order[(order.indexOf(current) + 1) % order.length];
        const label = { human: 'HUMAN-controlled', llm: 'LLM-controlled', npc: 'NPC-controlled' }[next];
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
            events.log(`Failed to switch ${charName}: ${err.message}`, 'error-msg');
        });
    }
}
