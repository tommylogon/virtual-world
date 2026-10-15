"use strict";
/**
 * @module agent/simultaneous-controls — per-character async pacing controls
 * @contributes cooldown sliders and scheduled-turn estimate in the turn panel
 * @powers configuration of simultaneous async arrivals
 * @relates agent/simultaneous, config, agent-engine
 * @docs docs/virtualWorld/dev_tasks/todo/gameplay/task-825-simultaneous-mode-v2-async-cooldown-talkativeness.md
 */
(function () {
    'use strict';
    class VWSimultaneousControls {
        static init() {
            const root = document.getElementById('sim-character-pacing');
            if (!root || root.dataset.initialized === 'true')
                return;
            root.dataset.initialized = 'true';
            root.addEventListener('input', (event) => {
                const target = event.target;
                if (!target || target.type !== 'range' || !target.dataset.character)
                    return;
                const character = target.dataset.character;
                const config = window.config;
                const mode = window.VWSimultaneous;
                const pace = mode.normalizeTalkativeness(target.value);
                config.talkativenessByCharacter[character] = pace;
                const output = root.querySelector(`[data-pace-for="${CSS.escape(character)}"]`);
                if (output)
                    output.textContent = `${pace}s`;
                window.agent?.resetSimCharacterDeadline?.(character);
                this.renderEstimate();
            });
            root.addEventListener('change', (event) => {
                const target = event.target;
                if (!target || target.type !== 'range' || !target.dataset.character)
                    return;
                window.config.setTalkativeness(target.dataset.character, target.value);
            });
            const bus = window.appEvents;
            if (bus?.on)
                bus.on('state:updated', () => this.render());
            this.render();
        }
        static render() {
            const root = document.getElementById('sim-character-pacing');
            if (!root)
                return;
            const config = window.config;
            const state = window.VW?.state?.data || window.worldState?.data;
            const mode = window.VWSimultaneous;
            const enabled = config.turnOrder === mode.MODES.SIMULTANEOUS;
            const players = state?.players || {};
            const names = Object.keys(players);
            root.hidden = !enabled || names.length === 0;
            if (!enabled || names.length === 0) {
                this.renderEstimate();
                return;
            }
            root.innerHTML = names.map(name => {
                const pace = config.getTalkativeness(name);
                const escaped = escapeHtml(name);
                return `<label class="sim-pacing-row">
                    <span class="sim-pacing-name">${escaped}</span>
                    <input type="range" min="5" max="120" step="1" value="${pace}" data-character="${escaped}" aria-label="${escaped} cooldown">
                    <output data-pace-for="${escaped}">${pace}s</output>
                </label>`;
            }).join('');
            this.renderEstimate();
        }
        static renderEstimate() {
            const estimate = document.getElementById('sim-rate-estimate');
            if (!estimate)
                return;
            const config = window.config;
            const state = window.VW?.state?.data || window.worldState?.data;
            if (config.turnOrder !== 'simultaneous' || !state?.players) {
                estimate.textContent = '';
                estimate.hidden = true;
                return;
            }
            const events = window.events;
            const active = Object.keys(state.players).filter(name => {
                const player = state.players[name];
                return player && (player.state !== 'dead' || config.ghostMode) && events?.isAutonomous?.(name);
            });
            const scheduledPerMinute = active.reduce((sum, name) => sum + 60 / config.getTalkativeness(name), 0);
            estimate.hidden = false;
            estimate.textContent = `${active.length} autonomous character${active.length === 1 ? '' : 's'} · about ${scheduledPerMinute.toFixed(1)} scheduled agent turns/min. Actual API calls vary by turn.`;
        }
    }
    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, char => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[char] || char));
    }
    window.VWSimultaneousControls = VWSimultaneousControls;
})();
