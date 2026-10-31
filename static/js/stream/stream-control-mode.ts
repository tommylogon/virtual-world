/**
 * stream-control-mode.js - character control mode cycling (task-340, task-728)
 *
 * Extracted from event-stream.js for size compliance; lives on the events
 * API because the UI invokes it from the stream/roster surfaces.
 * Loaded BEFORE event-stream.js.
 *
 * @module stream/control-mode - character control mode cycling
 * @contributes StreamControlMode: cycle avatar / agent / observer control for a character
 * @powers Event stream - switching who you are controlling from the stream and roster surfaces
 * @relates lives on the events API; loaded before event-stream.js
 * @docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
class StreamControlMode {
    _bus: unknown;
    _autonomy: Record<string, boolean | string>;

    constructor(bus: unknown) {
        this._bus = bus;
        this._autonomy = {};
    }

    isAutonomous(charName: string): boolean {
        if (this._autonomy[charName] === undefined) {
            // Seed from backend so a human (autonomy False) survives reloads
            // and stays human instead of reverting to LLM-driving (task-244).
            const stored = worldState.players?.[charName]?.autonomy;
            this._autonomy[charName] = stored === undefined ? true : (stored === 'directed' ? 'directed' : Boolean(stored));
        }
        return this._autonomy[charName] !== false;
    }

    /**
     * Resolve the control mode for a character:
     *   'npc'      - simple_npc (scripted behaviors, backend tick drives them)
     *   'human'    - autonomy off (engine skips them - the human drives via commands)
     *   'directed' - autonomy directed (LLM drafts turn, director reviews and edits before commit)
     *   'llm'      - autonomous non-NPC (agent engine drives them)
     */
    getControlMode(charName: string): 'npc' | 'human' | 'llm' | 'directed' {
        const player = worldState.players?.[charName];
        if (player?.controller && ['npc', 'human', 'llm', 'directed'].includes(player.controller)) {
            return player.controller as 'npc' | 'human' | 'llm' | 'directed';
        }
        if (player?.simple_npc) return 'npc';
        const autonomyVal = this._autonomy[charName] !== undefined
            ? this._autonomy[charName]
            : player?.autonomy;
        if (autonomyVal === 'directed') return 'directed';
        if (autonomyVal === false) return 'human';
        return 'llm';
    }

    /**
     * One vocabulary for the four control modes, for every surface that shows
     * one (agent list, inspector header, graph node badges).
     *
     * 👾 is the scripted NPC (no LLM turn at all), 🤖 the LLM agent that decides
     * each turn, 👤 the human you drive yourself, 🎬 directed mode where the LLM
     * drafts each turn and the director reviews before it acts.
     */
    controlBadge(mode: string): { emoji: string; label: string; title: string } {
        if (mode === 'human') {
            return { emoji: '👤', label: 'Human', title: 'Human-controlled - the engine skips them and you act' };
        }
        if (mode === 'directed') {
            return { emoji: '🎬', label: 'Directed', title: 'Directed mode - LLM drafts the turn, director reviews and edits before commit' };
        }
        if (mode === 'npc') {
            return { emoji: '👾', label: 'NPC', title: 'Scripted NPC - simple_npc, no LLM turn' };
        }
        return { emoji: '🤖', label: 'LLM', title: 'LLM agent - the agent engine decides each turn' };
    }

    /** Cycle a character through Human -> Directed -> LLM -> NPC -> Human and apply the backend changes. */
    cycleControlMode(charName: string): void {
        const order: Array<'human' | 'directed' | 'llm' | 'npc'> = ['human', 'directed', 'llm', 'npc'];
        const current = this.getControlMode(charName);
        const next = order[(order.indexOf(current) + 1) % order.length];
        const modeLabels: Record<string, string> = {
            human: 'HUMAN-controlled', directed: 'DIRECTED-mode', llm: 'LLM-controlled', npc: 'NPC-controlled'
        };
        const label = modeLabels[next];
        let simpleNpc = false;
        let autonomy: boolean | string = true;
        let makeActive = false;
        const previousActive = config.controllingPlayer;
        if (next === 'human') {
            autonomy = false;
            makeActive = true;
        } else if (next === 'directed') {
            autonomy = 'directed';
        } else if (next === 'npc') {
            simpleNpc = true;
        }
        if (makeActive) {
            config.controllingPlayer = charName;
            worldState.setRuntimeFocusForCharacter(charName);
        }
        ApiClient.updateCharacter(charName, {
            controller: next,
            simple_npc: simpleNpc,
            autonomy: autonomy
        }).then(async () => {
            this._autonomy[charName] = autonomy;
            if (worldState.players?.[charName]) {
                worldState.players[charName].controller = next;
                worldState.players[charName].simple_npc = simpleNpc;
                worldState.players[charName].autonomy = autonomy;
            }
            // Refetch + re-render for ALL modes so the mode badge actually updates.
            const freshState = await worldState.fetch();
            if (freshState && worldState.data) VW?.ui?.renderAll?.(freshState);
            events.log(`${charName} -> ${label}`, 'system-msg');
        }).catch(err => {
            if (makeActive && config.controllingPlayer === charName) {
                config.controllingPlayer = previousActive;
                worldState.setRuntimeFocusForCharacter(previousActive);
            }
            events.log(`Failed to switch ${charName}: ${err instanceof Error ? err.message : String(err)}`, 'error-msg');
        });
    }
}
