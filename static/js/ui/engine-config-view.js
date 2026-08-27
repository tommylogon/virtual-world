/**
 * engine-config-view.js — "Engine Config" settings tab (task-304)
 *
 * Renders the tunable engine constants (sound / heat / light) as a live,
 * lit-html-rendered editor backed by GET/POST /api/settings/engine_config.
 * The schema + values come from the backend, so adding a new key to
 * engine/runtime_config.py automatically shows up here — no HTML to touch.
 *
 * Dependencies:
 *   - window.Lit (lit-html bootstrap, deferred module — safe to reference lazy)
 *   - Global toast helpers (toastInfo, toastError from ui-helpers.js)
 */
window.EngineConfigView = (() => {
    'use strict';

    const tag = (strings, ...values) => window.Lit.html(strings, ...values);

    let _state = {
        values: {},
        schema: {},
        sections: {},
    };

    /**
     * Load values + schema from the backend, then render into #tab-engine-config.
     */
    async function load() {
        const container = document.getElementById('tab-engine-config');
        if (!container) return;
        try {
            const resp = await fetch('/api/settings/engine_config');
            const data = await resp.json();
            _state.values = data.values || {};
            _state.schema = data.schema || {};
            _state.sections = data.sections || {};
        } catch (err) {
            _state.values = {};
            _state.schema = {};
            _state.sections = {};
        }
        render(container);
    }

    /**
     * Render the whole editor. Called on open and after every successful POST
     * so the numeric inputs reflect the persisted (server-coerced) values.
     */
    function render(container) {
        if (!window.Lit || !container) return;

        const sections = Object.keys(_state.sections);
        const sectionRows = (key) => {
            const meta = _state.schema[key];
            if (meta.type === 'bool') {
                return tag`<div class="engine-config-row" style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);">
                    <label for="engine-config-${key}" style="flex:1;font-size:11px;color:var(--text);">${meta.label || key}</label>
                    <input id="engine-config-${key}"
                        type="checkbox"
                        ?checked="${_state.values[key]}"
                        data-key="${key}"
                        style="width:auto;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:4px 6px;font-size:11px;">
                </div>`;
            }
            return tag`<div class="engine-config-row" style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);">
                <label for="engine-config-${key}" style="flex:1;font-size:11px;color:var(--text);">${meta.label || key}</label>
                <input id="engine-config-${key}"
                    type="number"
                    step="${meta.type === 'float' ? '0.01' : '1'}"
                    value="${_state.values[key]}"
                    data-key="${key}"
                    style="width:110px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:4px 6px;font-size:11px;">
            </div>`;
        };

        const groups = sections.map((section) => {
            const keys = Object.keys(_state.schema).filter((k) => _state.schema[k].section === section);
            const rows = keys.map(sectionRows);
            return tag`<div class="settings-group">
                <div class="settings-group-title"><span class="group-icon">⚙️</span> ${section[0].toUpperCase() + section.slice(1)}</div>
                <div class="field-hint" style="margin-bottom:4px;">${_state.sections[section]}</div>
                ${rows}
            </div>`;
        });

        const hasContent = sections.length > 0;
        const actions = hasContent
            ? tag`<div style="display:flex;gap:8px;margin-top:12px;">
                  <button class="btn btn-green" @click=${applyEngine}>💾 Apply</button>
                  <button class="btn btn-secondary" @click=${resetToDefaults}>↩️ Reset to defaults</button>
              </div>`
            : tag`<div style="padding:12px;color:var(--text-dim);font-size:12px;">Couldn't load engine config. Is the server running?</div>`;

        window.Lit.render(tag`
            ${groups}
            ${actions}
        `, container);
    }

    /**
     * Read all inputs in the tab, POST the merged values, re-render with the
     * server's coerced response so the fields show what actually applied.
     */
    async function applyEngine() {
        const container = document.getElementById('tab-engine-config');
        if (!container) return;
        const inputs = container.querySelectorAll('input[data-key]');
        const payload = {};
        for (const input of inputs) {
            const raw = input.value.trim();
            const meta = _state.schema[input.dataset.key];
            if (meta && meta.type === 'bool') {
                payload[input.dataset.key] = input.checked;
            } else if (meta && meta.type === 'float') {
                payload[input.dataset.key] = parseFloat(raw);
            } else if (raw !== '') {
                payload[input.dataset.key] = parseInt(raw, 10);
            }
        }
        try {
            const resp = await fetch('/api/settings/engine_config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ values: payload }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Failed to save');
            _state.values = data.values || {};
            if (window.toastInfo) toastInfo('Engine config applied ✔');
            render(container);
        } catch (err) {
            if (window.toastError) toastError('Engine config failed: ' + err.message);
        }
    }

    async function resetToDefaults() {
        const container = document.getElementById('tab-engine-config');
        if (!container) return;
        try {
            const resp = await fetch('/api/settings/engine_config/reset', { method: 'POST' });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'HTTP error');
            _state.values = data.values || {};
            if (window.toastInfo) toastInfo('Engine config reset to defaults ↪');
            render(container);
        } catch (err) {
            if (window.toastError) toastError('Engine reset failed: ' + err.message);
        }
    }

    return {
        load,
    };
})();