/**
 * stream-control-mode.js - character control mode cycling (task-340, task-728, task-933)
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
    _autoDraft: Record<string, boolean>;

    constructor(bus: unknown) {
        this._bus = bus;
        this._autonomy = {};
        this._autoDraft = {};
        try {
            const raw = typeof localStorage !== 'undefined' ? localStorage.getItem('vw_director_autodraft') : null;
            if (raw) {
                const parsed = JSON.parse(raw);
                if (parsed && typeof parsed === 'object') {
                    this._autoDraft = parsed;
                }
            }
        } catch (e) {}
    }

    isAutoDraft(charName: string): boolean {
        if (this._autoDraft[charName] === undefined) {
            const player = worldState.players?.[charName];
            if (player?.autonomy === 'directed' || player?.controller === 'directed') {
                return true;
            }
        }
        return Boolean(this._autoDraft[charName]);
    }

    setAutoDraft(charName: string, enabled: boolean): void {
        this._autoDraft[charName] = Boolean(enabled);
        try {
            if (typeof localStorage !== 'undefined') {
                localStorage.setItem('vw_director_autodraft', JSON.stringify(this._autoDraft));
            }
        } catch (e) {}
    }

    isAutonomous(charName: string): boolean {
        const mode = this.getControlMode(charName);
        return mode === 'llm' || mode === 'npc';
    }

    /**
     * Resolve the control mode for a character:
     *   'human'    - manual control via Turn Composer (with optional Director AI auto-draft)
     *   'llm'      - autonomous LLM agent drives turns
     *   'npc'      - scripted rule-based NPC (simple_npc, zero LLM calls)
     *   'paused'   - frozen / inert (excluded from turn queue and simulation ticks)
     *   'directed' - backward-compatible alias that maps to 'human' + autoDraft
     */
    getControlMode(charName: string): 'npc' | 'human' | 'llm' | 'paused' | 'directed' {
        const player = worldState.players?.[charName];
        const ctrl = String(player?.controller || '').toLowerCase();
        if (ctrl === 'paused' || ctrl === 'inert' || (player?.simple_npc === true && (this._autonomy[charName] === false || player?.autonomy === false))) {
            return 'paused';
        }
        if (ctrl === 'human') return 'human';
        if (ctrl === 'npc' || ctrl === 'simple') return 'npc';
        if (ctrl === 'llm' || ctrl === 'agent') return 'llm';
        if (ctrl === 'directed') {
            if (this._autoDraft[charName] === undefined) this._autoDraft[charName] = true;
            return 'human';
        }
        if (player?.simple_npc) {
            return (this._autonomy[charName] === false || player?.autonomy === false) ? 'paused' : 'npc';
        }
        const autonomyVal = this._autonomy[charName] !== undefined
            ? this._autonomy[charName]
            : player?.autonomy;
        if (autonomyVal === 'directed') {
            if (this._autoDraft[charName] === undefined) this._autoDraft[charName] = true;
            return 'human';
        }
        if (autonomyVal === false) return 'human';
        return 'llm';
    }

    /**
     * One vocabulary for the four control modes, for every surface that shows
     * one (agent list, inspector header, graph node badges).
     */
    controlBadge(mode: string): { emoji: string; label: string; title: string } {
        if (mode === 'human') {
            return { emoji: '👤', label: 'Human', title: 'Human-controlled - you act via the Turn Composer (with optional Director AI draft)' };
        }
        if (mode === 'directed') {
            return { emoji: '🎬', label: 'Directed', title: 'Directed mode - Human Turn Composer with Auto-draft enabled' };
        }
        if (mode === 'npc') {
            return { emoji: '🤖', label: 'NPC', title: 'Scripted NPC - rule-based autonomy, zero LLM calls' };
        }
        if (mode === 'paused' || mode === 'inert') {
            return { emoji: '⏸️', label: 'Paused', title: 'Paused (Inert) - frozen, excluded from turn queue and simulation ticks' };
        }
        return { emoji: '🧠', label: 'LLM', title: 'LLM Agent - autonomous AI decides each turn' };
    }

    /** Set a character's control mode directly and persist to backend. */
    setControlMode(charName: string, nextMode: 'human' | 'llm' | 'npc' | 'paused' | 'directed'): Promise<void> {
        if (nextMode === 'directed') {
            this.setAutoDraft(charName, true);
        }
        const next: 'human' | 'llm' | 'npc' | 'paused' = nextMode === 'directed' ? 'human' : nextMode;
        const modeSpec: Record<'human' | 'llm' | 'npc' | 'paused', {
            payload: { controller: string; simple_npc: boolean; autonomy: boolean };
            makeActive: boolean;
            label: string;
        }> = {
            human:  { payload: { controller: 'human',  simple_npc: false, autonomy: false }, makeActive: true,  label: 'HUMAN-controlled' },
            llm:    { payload: { controller: 'agent',  simple_npc: false, autonomy: true  }, makeActive: false, label: 'LLM-controlled' },
            npc:    { payload: { controller: 'simple', simple_npc: true,  autonomy: true  }, makeActive: false, label: 'NPC-controlled' },
            paused: { payload: { controller: 'inert',  simple_npc: true,  autonomy: false }, makeActive: false, label: 'PAUSED (inert)' }
        };
        const spec = modeSpec[next] || modeSpec.llm;
        const { payload, makeActive, label } = spec;
        const previousActive = config.controllingPlayer;
        this._autonomy[charName] = payload.autonomy;
        if (makeActive) {
            config.controllingPlayer = charName;
            worldState.setRuntimeFocusForCharacter(charName);
        }
        return ApiClient.updateCharacter(charName, payload).then(async () => {
            if (worldState.players?.[charName]) {
                worldState.players[charName].controller = payload.controller;
                worldState.players[charName].simple_npc = payload.simple_npc;
                worldState.players[charName].autonomy = payload.autonomy;
            }
            (window as any).TurnQueue?.reconcile?.();
            await worldState.fetch();
            (window as any).TurnQueue?.reconcile?.();
            if (worldState.data) VW?.ui?.renderAll?.(worldState.data);
            events.log(`${charName} -> ${label}`, 'system-msg');
        }).catch(err => {
            if (makeActive && config.controllingPlayer === charName) {
                config.controllingPlayer = previousActive;
                worldState.setRuntimeFocusForCharacter(previousActive);
            }
            events.log(`Failed to switch ${charName}: ${err instanceof Error ? err.message : String(err)}`, 'error-msg');
        });
    }

    /** Open a compact floating menu to pick the character's controller mode directly. */
    openControlModeMenu(charName: string, anchorEl?: HTMLElement | EventTarget | null): void {
        if (typeof document === 'undefined') return;
        const existing = document.getElementById('vw-control-mode-menu');
        if (existing) existing.remove();

        const current = this.getControlMode(charName);
        const menu = document.createElement('div');
        menu.id = 'vw-control-mode-menu';
        menu.style.cssText = 'background: var(--bg-card, #161b22); border: 1px solid var(--border, #30363d); border-radius: 6px; padding: 4px; z-index: 10000; box-shadow: 0 8px 24px rgba(0,0,0,0.5); min-width: 220px; position: fixed; font-family: inherit;';

        const header = document.createElement('div');
        header.style.cssText = 'padding: 4px 8px; font-size: 10px; font-weight: 600; color: var(--text-muted, #8b949e); border-bottom: 1px solid var(--border, #30363d); margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;';
        header.textContent = `Controller: ${charName}`;
        menu.appendChild(header);

        const options: Array<{ mode: 'human' | 'llm' | 'npc' | 'paused'; emoji: string; label: string; desc: string }> = [
            { mode: 'human',  emoji: '👤', label: 'Human',  desc: 'Manual + Director AI assist' },
            { mode: 'llm',    emoji: '🧠', label: 'LLM',    desc: 'Autonomous AI agent' },
            { mode: 'npc',    emoji: '🤖', label: 'NPC',    desc: 'Rule-based scripted NPC' },
            { mode: 'paused', emoji: '⏸️', label: 'Paused', desc: 'Frozen - skips turns & ticks' }
        ];

        const cleanup = () => {
            menu.remove();
            document.removeEventListener('mousedown', onDocClick, true);
            document.removeEventListener('keydown', onKeyDown, true);
        };

        for (const opt of options) {
            const isCurrent = current === opt.mode || (current === 'directed' && opt.mode === 'human');
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.setAttribute('data-mode', opt.mode);
            btn.style.cssText = `display: flex; align-items: center; gap: 8px; width: 100%; text-align: left; padding: 6px 8px; border: 0; border-radius: 4px; cursor: pointer; background: ${isCurrent ? 'var(--bg-input, #21262d)' : 'transparent'}; color: var(--text, #c9d1d9); font-size: 11px;`;
            btn.onmouseenter = () => { btn.style.background = 'var(--bg-input, #21262d)'; };
            btn.onmouseleave = () => { btn.style.background = isCurrent ? 'var(--bg-input, #21262d)' : 'transparent'; };

            const iconSpan = document.createElement('span');
            iconSpan.style.cssText = 'font-size: 14px; width: 18px; text-align: center;';
            iconSpan.textContent = opt.emoji;

            const textWrap = document.createElement('span');
            textWrap.style.cssText = 'display: flex; flex-direction: column; flex: 1; line-height: 1.25;';
            const titleSpan = document.createElement('span');
            titleSpan.style.cssText = 'font-weight: 600; font-size: 11px;';
            titleSpan.textContent = opt.label;
            const descSpan = document.createElement('span');
            descSpan.style.cssText = 'font-size: 9.5px; color: var(--text-muted, #8b949e);';
            descSpan.textContent = opt.desc;
            textWrap.appendChild(titleSpan);
            textWrap.appendChild(descSpan);

            const checkSpan = document.createElement('span');
            checkSpan.style.cssText = 'font-size: 11px; color: var(--accent, #58a6ff); font-weight: 700; min-width: 14px; text-align: right;';
            checkSpan.textContent = isCurrent ? '✓' : '';

            btn.appendChild(iconSpan);
            btn.appendChild(textWrap);
            btn.appendChild(checkSpan);

            btn.onclick = (ev) => {
                ev.stopPropagation();
                cleanup();
                this.setControlMode(charName, opt.mode);
            };
            menu.appendChild(btn);
        }

        document.body.appendChild(menu);

        let left = 120;
        let top = 120;
        if (anchorEl && typeof (anchorEl as HTMLElement).getBoundingClientRect === 'function') {
            const rect = (anchorEl as HTMLElement).getBoundingClientRect();
            left = rect.left;
            top = rect.bottom + 4;
        }
        const menuRect = menu.getBoundingClientRect();
        const vw = window.innerWidth || 1024;
        const vh = window.innerHeight || 768;
        if (left + menuRect.width > vw - 8) left = Math.max(8, vw - menuRect.width - 8);
        if (top + menuRect.height > vh - 8) top = Math.max(8, top - menuRect.height - 28);
        menu.style.left = `${Math.round(left)}px`;
        menu.style.top = `${Math.round(top)}px`;

        const onDocClick = (ev: MouseEvent) => {
            if (!menu.contains(ev.target as Node)) {
                cleanup();
            }
        };
        const onKeyDown = (ev: KeyboardEvent) => {
            if (ev.key === 'Escape') {
                cleanup();
            }
        };
        setTimeout(() => {
            document.addEventListener('mousedown', onDocClick, true);
            document.addEventListener('keydown', onKeyDown, true);
        }, 0);
    }

    /** Cycle a character through Human -> LLM -> NPC -> Paused -> Human (or open the selector menu if an anchor is provided). */
    cycleControlMode(charName: string, anchorEl?: HTMLElement | EventTarget | null): void {
        if (anchorEl && typeof document !== 'undefined' && typeof (anchorEl as any).getBoundingClientRect === 'function') {
            this.openControlModeMenu(charName, anchorEl);
            return;
        }
        const order: Array<'human' | 'llm' | 'npc' | 'paused'> = ['human', 'llm', 'npc', 'paused'];
        const current = this.getControlMode(charName);
        const normalized = current === 'directed' ? 'human' : current;
        const idx = order.indexOf(normalized);
        const next = order[(idx + 1) % order.length];
        this.setControlMode(charName, next);
    }
}
