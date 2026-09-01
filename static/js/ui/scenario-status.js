/**
 * scenario-status.js — scenario source status chip + one-click Commit.
 *
 * Top-bar chip next to the scenario name: "📦 <scenario>" plus — when the
 * live world has drifted from its scenario source — an amber "●" dot and
 * two buttons:
 *   💾 Commit → POST /api/scenario/commit (writes live world into the
 *               data/scenarios/<name>.json source; Restart keeps your work)
 *   🌀 Restart → the existing restartScenario() confirm flow
 *
 * Dirty tracking is a server-side counter (edit_seq vs commit_seq) — the
 * chip polls /api/scenario/status on state updates, debounced.
 */

window.ScenarioStatus = (() => {
    'use strict';

    let _timer = null;
    let _busy = false;

    const chip = () => document.getElementById('scenario-status-chip');

    async function refresh() {
        if (_busy) return;
        const node = chip();
        if (!node) return;
        let st = null;
        try {
            const resp = await fetch('/api/scenario/status');
            st = await resp.json();
        } catch (e) {
            return; // older server — chip stays quiet
        }
        node.textContent = '';
        const icon = document.createElement('span');
        icon.textContent = '📦';
        icon.style.cssText = 'color:var(--text-dim);';
        icon.title = st.source ? ('Scenario source: ' + st.source) : 'No scenario source yet';
        node.appendChild(icon);

        if (!st.dirty) return;

        const dot = document.createElement('span');
        dot.textContent = '●';
        dot.style.cssText = 'color:#e3b341;';
        dot.title = 'Unsaved changes since the scenario source was loaded/committed';
        node.appendChild(dot);

        const commit = document.createElement('button');
        commit.className = 'btn btn-sm btn-green';
        commit.textContent = '💾 Commit';
        commit.style.cssText = 'font-size:10px;padding:1px 8px;';
        commit.dataset.role = 'scenario-commit';
        commit.onclick = () => commitScenario();
        node.appendChild(commit);
        // (Restart lives in the toolbar — one Restart button; the chip only
        // shows status + Commit.)
    }

    async function commitScenario() {
        if (_busy) return;
        _busy = true;
        const node = chip();
        try {
            const resp = await fetch('/api/scenario/commit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await resp.json();
            if (data.error) throw new Error(data.error);
            if (typeof toastInfo === 'function') {
                toastInfo(`Committed to scenario "${data.name}".`);
            }
            try { events.log(`💾 Scenario "${data.name}" committed.`, 'system-msg'); } catch (e) {}
            try {
                const nameText = document.getElementById('scenario-name-text');
                if (nameText && data.name) nameText.textContent = data.name;
                document.body.dataset.scenarioName = data.name;
            } catch (e) {}
            await refresh();
        } catch (e) {
            console.error('[scenario-status] commit failed:', e);
            if (typeof toastError === 'function') toastError('Commit failed: ' + (e.message || e));
        } finally {
            _busy = false;
        }
    }

    function scheduleRefresh() {
        if (_timer) clearTimeout(_timer);
        _timer = setTimeout(() => refresh(), 1200);
    }

    if (window.appEvents) {
        appEvents.on('state:updated', scheduleRefresh);
    }
    document.addEventListener('DOMContentLoaded', () => refresh());

    return { refresh, commit: commitScenario };
})();
