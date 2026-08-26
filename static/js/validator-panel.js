/**
 * ValidatorPanel — Trigger validation panel in the left sidebar.
 *
 * Fetches GET /api/triggers/validate and lists every broken trigger
 * reference in the world. Each issue row has a clickable jump button that
 * opens the owner node (inspector + graph focus) so you can fix it in place.
 *
 * Exposed as `VW.validatorPanel` and `window.ValidatorPanel` (for onclick).
 */
(() => {
    const validatorPanelTag = (strings, ...values) => window.Lit.html(strings, ...values);
    const SEV_COLORS = { error: '#f85149', warning: '#e3b341', info: '#8b949e' };
    const SEV_ICONS = { error: '✕', warning: '⚠', info: 'ℹ' };

    let _timer = null;

    class ValidatorPanel {
        constructor() {
            this._lastIssues = [];
            if (window.appEvents) {
                appEvents.on('state:updated', () => this._scheduleRefresh());
            }
            document.addEventListener('DOMContentLoaded', () => this.refresh());
        }

        /** Debounce auto-refresh so rapid state updates don't spam the backend. */
        _scheduleRefresh(delay = 2000) {
            if (_timer) clearTimeout(_timer);
            _timer = setTimeout(() => this.refresh(), delay);
        }

        async fetchIssues(nodeId = '') {
            const url = nodeId
                ? `/api/triggers/validate?node_id=${encodeURIComponent(nodeId)}`
                : '/api/triggers/validate';
            try {
                const resp = await fetch(url);
                const data = await resp.json();
                return data.issues || [];
            } catch (e) {
                console.warn('[ValidatorPanel] fetch failed:', e);
                return [];
            }
        }

        async refresh() {
            const issues = await this.fetchIssues();
            this._lastIssues = issues;
            this.render(issues);
        }

        /** Validate just one node's triggers (used by the inspector). */
        async validateNode(nodeId) {
            return this.fetchIssues(nodeId);
        }

        /** Fetch + render a single node's issues into *containerEl* (inline). */
        async validateNodeInline(nodeId, containerEl) {
            if (!containerEl) return;
            containerEl.style.display = 'block';
            window.Lit.render(validatorPanelTag`<div class="alert-empty">Scanning…</div>`, containerEl);
            const issues = await this.fetchIssues(nodeId);
            if (issues.length === 0) {
                window.Lit.render(validatorPanelTag`<div class="alert-empty">No broken references ✅</div>`, containerEl);
                return;
            }
            this.render(issues, containerEl);
        }

        jumpTo(nodeId) {
            try {
                graphManager.showNodeAndFocus(nodeId);
            } catch (e) {
                try {
                    if (window.VW?.inspector) VW.inspector.showNode(nodeId);
                } catch (_) { /* node gone — nothing to open */ }
            }
        }

        render(issues, targetEl = null) {
            const listEl = targetEl || document.getElementById('validator-list');
            if (!listEl) return;

            const countEl = document.getElementById('validator-count');
            const errors = issues.filter(i => i.severity === 'error').length;
            const warnings = issues.filter(i => i.severity === 'warning').length;
            if (countEl && !targetEl) {
                countEl.textContent = issues.length
                    ? `${issues.length} (${errors} err · ${warnings} warn)`
                    : '';
                countEl.style.color = errors ? '#f85149' : (warnings ? '#e3b341' : '#3fb950');
            }

            if (issues.length === 0) {
                window.Lit.render(validatorPanelTag`<div class="alert-empty">No broken triggers ✅</div>`, listEl);
                return;
            }

            const rows = issues.map(issue => {
                const sev = issue.severity || 'info';
                const color = SEV_COLORS[sev] || SEV_COLORS.info;
                const icon = SEV_ICONS[sev] || SEV_ICONS.info;
                const nodeId = issue.source_node_id || issue.target_node_id;
                const jump = nodeId
                    ? validatorPanelTag`<button class="validator-jump" title="Open node: ${nodeId}"
                         @click=${() => this.jumpTo(nodeId)}>🔍</button>`
                    : '';
                return validatorPanelTag`<div class="validator-item" data-code=${issue.code}>
                    <span class="validator-sev" style="background:${color};" title=${sev}></span>
                    <span class="validator-msg">${icon} ${issue.message}</span>
                    ${jump}
                </div>`;
            });
            window.Lit.render(validatorPanelTag`${rows}`, listEl);
        }
    }

    window.ValidatorPanel = new ValidatorPanel();
    window.VW = window.VW || {};
    VW.validatorPanel = window.ValidatorPanel;
})();
