/**
 * ValidatorPanel — World Issues triage panel (task-393).
 *
 * Fetches GET /api/triggers/validate and turns the flat issue wall into a
 * triage tool:
 *   • Group by NODE (one expandable row per way/item/area) or by CODE
 *     (one row per issue class, so "254 issues" visibly collapses to a few
 *     piles like way_missing_cardinal ×58, empty_trigger ×24).
 *   • Per-row actions: 🔍 jump, ⚙ quick-fix (info mechanical), 🧹 remove
 *     empty trigger stubs, 🚫/🔓 dismiss / restore (writes ignored_issues into
 *     the node — survives reloads, expires if the node is edited again).
 *   • "Fix all" for mechanical info nudges (one batch, one undo).
 *   • Scrollable list + sticky count + a derived per-node progress bar
 *     ("done" = no actionable issues on the node).
 *
 * Exposed as `VW.validatorPanel` and `window.ValidatorPanel` (for onclick).
 */
(() => {
    const validatorPanelTag = (strings, ...values) => window.Lit.html(strings, ...values);
    const SEV_COLORS = { error: '#f85149', warning: '#e3b341', info: '#8b949e' };
    const SEV_ICONS = { error: '✕', warning: '⚠', info: 'ℹ' };
    const SEV_NAME = { error: 'error', warning: 'warning', info: 'info' };
    const SEV_ORDER = { error: 0, warning: 1, info: 2 };

    const CODE_LABELS = {
        empty_trigger: 'empty trigger',
        orphan_trigger_edge: 'orphan trigger edge',
        dangling_trigger_edge: 'dangling trigger edge',
        trigger_edge_wrong_target_type: 'trigger → wrong target type',
        stale_trigger_copy: 'stale trigger copy',
        missing_effect_item: 'effect spawns missing item',
        way_missing_pass_message: 'way: no pass message',
        way_missing_cardinal: 'way: no cardinal direction',
        way_missing_view_direction: 'way: no view direction',
        mechanical_tag_missing_props: 'missing mechanical property',
        library_mismatch: 'drifted from library',
    };
    const friendly = (code) => CODE_LABELS[code] || code.replace(/_/g, ' ');

    let _timer = null;

    class ValidatorPanel {
        constructor() {
            this._lastIssues = [];
            this._mode = localStorage.getItem('vp-group') || 'node';
            this._showIgnored = localStorage.getItem('vp-show-ignored') === '1';
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

        _nodeLabel(nodeId) {
            try {
                const n = worldState.getNode(nodeId);
                return n?.name || nodeId;
            } catch (e) { return nodeId; }
        }

        _nodeIgnored(nodeId) {
            try {
                const n = worldState.getNode(nodeId);
                return (n?.properties?.ignored_issues) || [];
            } catch (e) { return []; }
        }

        /** Dismiss (ignore=true) or restore (ignore=false) a code on a node. */
        async setIgnore(nodeId, code, ignore) {
            if (!nodeId || !code) return;
            try {
                await ApiClient.post('/api/triggers/ignore', { node_id: nodeId, code, ignore });
            } catch (e) {
                console.warn('[ValidatorPanel] ignore toggle failed:', e);
            }
            worldState.fetch && worldState.fetch();
            this.refresh();
        }

        /**
         * Remove a node's empty logic_trigger stubs (triggers with no effects)
         * as ONE batch so a single Undo reverts it. Also clears them from any
         * dismiss list, since the problem vanishes.
         */
        async removeEmptyTriggers(nodeId) {
            if (!nodeId) return;
            try {
                const edges = (worldState?.graph?.edges) || [];
                const nodes = worldState?.graph?.nodes || {};
                const empties = edges.filter(e =>
                    String(e.source).toLowerCase() === String(nodeId).toLowerCase() &&
                    e.type === 'triggers'
                ).map(e => e.target).filter(tid => {
                    const tn = nodes[tid];
                    if (!tn || tn.type !== 'logic_trigger') return false;
                    const props = tn.properties || {};
                    return !(props.effects && props.effects.length) && !(props.conditions && Object.keys(props.conditions).length);
                });
                if (!empties.length) { this.refresh(); return; }
                const ops = empties.map(id => ({ type: 'delete_node', payload: { node_id: id } }));
                await ApiClient.batchGraph(ops);
            } catch (e) {
                console.warn('[ValidatorPanel] remove-empty failed:', e);
            }
            worldState.fetch && worldState.fetch();
            this.refresh();
        }

        /**
         * Quick-fix for info-level mechanical issues: write the engine's
         * default values (light_level→'dim', target_temperature→30,
         * heating_rate→0.5) onto the node so the nudge clears itself.
         */
        async quickFix(nodeId) {
            if (!nodeId) return;
            const node = worldState.getNode(nodeId);
            const props = (node && node.properties) || {};
            const patch = {};
            if (!props.light_level) patch.light_level = 'dim';
            if (!props.target_temperature) patch.target_temperature = 30;
            if (!props.heating_rate) patch.heating_rate = 0.5;
            if (!Object.keys(patch).length) { this.refresh(); return; }
            const ok = await ApiClient.updateNode(nodeId, { properties: patch });
            if (ok) {
                worldState.fetch && worldState.fetch();
            } else {
                console.warn('[ValidatorPanel] quick-fix save failed for', nodeId);
            }
            this.refresh();
        }

        /**
         * Way-orientation triage (task-395 rework):
         *   1. CLEAN — remove any values our OLD bulk-fill invented ("north"
         *      cardinals, templated pass_message / visible_in_direction) so a
         *      "fixed" way isn't holding false data. Exact-string match only —
         *      author text is untouched.
         *   2. WRITE — run the existing per-way AI improve (the same ✨ Improve
         *      feature the way inspector uses) across the missing-field ways.
         *      AI drafts are opened per-way for review; nothing is auto-applied
         *      here for the whole batch.
         */
        async fixAllWayOrientation() {
            // 1. Clean mints from the earlier implementation.
            try {
                await ApiClient.batchGraph([{ type: 'clear_way_fix_fields', payload: {} }]);
            } catch (e) {
                console.warn('[ValidatorPanel] way-cleaning batch failed:', e);
            }
            // 2. Reuse the way-inspector's AI improve for the missing-field ways.
            if (typeof window.InspectorWayView?.improveWayWithAI === 'function') {
                const nodes = [...new Set(
                    this._lastIssues
                        .filter(i => i.code === 'way_missing_pass_message' ||
                                     i.code === 'way_missing_cardinal' ||
                                     i.code === 'way_missing_view_direction')
                        .map(i => i.source_node_id).filter(Boolean)
                )];
                if (nodes.length) {
                    const first = nodes.shift();
                    events.log(`🧭 Drafting way flavor for ${nodes.length + 1} ways with AI (one at a time, review & Apply each)…`, 'system-msg');
                    window.InspectorWayView.improveWayWithAI(first);
                    // The AI improve is per-node + interactive; we open the top
                    // one and leave the rest for the panel's next 🔍 pass rather
                    // than queueing blind writes.
                }
            }
            worldState.fetch && worldState.fetch();
            this.refresh();
        }

        /** Batch quick-fix every node behind the given code (one undo). */
        async fixAll(code) {
            const nodes = [...new Set(
                this._lastIssues.filter(i => i.code === code).map(i => i.source_node_id).filter(Boolean)
            )];
            if (!nodes.length) return;
            const ops = [];
            for (const nodeId of nodes) {
                const node = worldState.getNode(nodeId);
                const props = (node && node.properties) || {};
                const patch = {};
                if (!props.light_level) patch.light_level = 'dim';
                if (!props.target_temperature) patch.target_temperature = 30;
                if (!props.heating_rate) patch.heating_rate = 0.5;
                if (Object.keys(patch).length) {
                    ops.push({ type: 'update_node', payload: { node_id: nodeId, patch: { properties: patch } } });
                }
            }
            if (ops.length) {
                try { await ApiClient.batchGraph(ops); }
                catch (e) { console.warn('[ValidatorPanel] fix-all failed:', e); }
            }
            worldState.fetch && worldState.fetch();
            this.refresh();
        }

        setGroupMode(mode) {
            this._mode = mode;
            localStorage.setItem('vp-group', mode);
            this.render(this._lastIssues);
        }

        setShowIgnored() {
            this._showIgnored = !this._showIgnored;
            localStorage.setItem('vp-show-ignored', this._showIgnored ? '1' : '0');
            this.render(this._lastIssues);
        }

        // ── Grouping ───────────────────────────────────────────────────

        _groupByNode(issues) {
            const map = new Map();
            for (const issue of issues) {
                const id = issue.source_node_id || '??';
                if (!map.has(id)) map.set(id, { nodeId: id, issues: [] });
                map.get(id).issues.push(issue);
            }
            return Array.from(map.values()).sort((a, b) =>
                this._worst(b.issues) - this._worst(a.issues));
        }

        _groupByCode(issues) {
            const map = new Map();
            for (const issue of issues) {
                const code = issue.code || '?';
                if (!map.has(code)) map.set(code, { code, issues: [] });
                map.get(code).issues.push(issue);
            }
            return Array.from(map.values()).sort((a, b) =>
                this._worst(b.issues) - this._worst(a.issues));
        }

        _worst(issues) {
            let w = 9;
            for (const i of issues) {
                const s = SEV_ORDER[i.severity] ?? 9;
                if (s < w) w = s;
            }
            return w;
        }

        // ── Rendering ──────────────────────────────────────────────────

        render(issues, targetEl = null) {
            const listEl = targetEl || document.getElementById('validator-list');
            if (!listEl) return;

            // The list must scroll — the panel header stays pinned.
            listEl.style.maxHeight = '45vh';
            listEl.style.overflowY = 'auto';

            const countEl = document.getElementById('validator-count');
            const errors = issues.filter(i => i.severity === 'error').length;
            const warnings = issues.filter(i => i.severity === 'warning').length;
            if (countEl && !targetEl) {
                countEl.textContent = issues.length
                    ? `${issues.length} (${errors} err · ${warnings} warn)`
                    : '';
                countEl.style.color = errors ? '#f85149' : (warnings ? '#e3b341' : '#3fb950');
            }

            if (targetEl) {
                // Inline (inspector) rendering — keep the flat one-line list.
                const flat = issues.map(issue => this._flatRow(issue, targetEl)).join('');
                window.Lit.render(validatorPanelTag`${window.Lit.unsafeHTML(flat)}`, listEl);
                return;
            }

            const top = window.Lit.unsafeHTML(
                this._toolbarHtml(issues) + (issues.length ? this._progressHtml(issues) : '')
            );
            let body = '';
            if (issues.length === 0) {
                body = `<div class="alert-empty">No broken triggers ✅</div>`;
            } else if (this._mode === 'code') {
                const groups = this._groupByCode(issues);
                body = groups.map(g => this._codeGroupHtml(g)).join('');
            } else {
                const groups = this._groupByNode(issues);
                body = groups.map(g => this._nodeGroupHtml(g)).join('');
            }
            window.Lit.render(validatorPanelTag`${top}${window.Lit.unsafeHTML(body)}`, listEl);
        }

        _toolbarHtml(issues) {
            return `<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:10px;margin:2px 0 6px;">
                <span style="color:var(--text-muted);">Group:</span>
                <button class="btn btn-sm ${this._mode === 'node' ? 'btn-blue' : ''}" style="font-size:9px;padding:1px 7px;" onclick="ValidatorPanel.setGroupMode('node')">By node</button>
                <button class="btn btn-sm ${this._mode === 'code' ? 'btn-blue' : ''}" style="font-size:9px;padding:1px 7px;" onclick="ValidatorPanel.setGroupMode('code')">By code</button>
                <label style="display:inline-flex;align-items:center;gap:3px;font-size:9px;color:var(--text-muted);cursor:pointer;margin-left:2px;">
                    <input type="checkbox" style="margin:0;" ${this._showIgnored ? 'checked' : ''} onchange="ValidatorPanel.setShowIgnored()"> show dismissed
                </label>
            </div>`;
        }

        _progressHtml(issues) {
            // Derived world progress — recomputed from live graph + live issues,
            // so it can't drift. Audited = every item/way/area node; clean = one
            // with no undismissed issue. Fixing a node moves it from unresolved
            // to clean automatically.
            let audited = 0;
            const unresolved = new Set();
            const nodes = (worldState && worldState.graph && worldState.graph.nodes) || {};
            for (const issue of issues) {
                if (issue.source_node_id) unresolved.add(issue.source_node_id);
            }
            for (const n of Object.values(nodes)) {
                if (n && (n.type === 'item' || n.type === 'way' || n.type === 'area')) audited++;
            }
            const clean = Math.max(0, audited - unresolved.size);
            const pct = audited ? Math.round((clean / audited) * 100) : 100;
            const tone = unresolved.size ? (pct < 50 ? '#e3b341' : '#8b949e') : '#3fb950';
            return `<div style="display:flex;align-items:center;gap:6px;font-size:9px;color:var(--text-muted);margin:2px 0 2px;" title="Derived: of ${audited} audited item/way/area nodes, ${clean} have no undismissed issues.">
                <span>${issues.length} issue${issues.length === 1 ? '' : 's'} · ${unresolved.size} node${unresolved.size === 1 ? '' : 's'} touched</span>
                <div style="flex:1;height:5px;background:var(--bg-inset);border-radius:2px;overflow:hidden;">
                    <div style="width:${pct}%;height:100%;background:${tone};"></div>
                </div>
                <span>${clean}/${audited} clean</span>
            </div>`;
        }

        _sevDot(issue) {
            const color = SEV_COLORS[issue.severity] || SEV_COLORS.info;
            return `<span class="validator-sev" style="background:${color};" title="${SEV_NAME[issue.severity] || issue.severity}"></span>`;
        }

        _actionsHtml(issue, sourceNodeId) {
            const nodeId = sourceNodeId || issue.source_node_id;
            const out = [];
            if (nodeId) {
                out.push(`<button class="validator-jump" title="Open node: ${nodeId}" onclick="ValidatorPanel.jumpTo('${String(nodeId).replace(/'/g, "\\'")}')">🔍</button>`);
            }
            const quickFix = (issue.code === 'mechanical_tag_missing_props' && issue.severity === 'info' && nodeId);
            if (quickFix) {
                out.push(`<button class="validator-jump" title="Set engine defaults (Dim / 30°C / 0.5° per tick) and clear this note" onclick="ValidatorPanel.quickFix('${String(nodeId).replace(/'/g, "\\'")}')">⚙</button>`);
            }
            const removeEmpty = (issue.code === 'empty_trigger' && nodeId);
            if (removeEmpty) {
                out.push(`<button class="validator-jump" title="Remove all empty trigger stubs on this node" onclick="ValidatorPanel.removeEmptyTriggers('${String(nodeId).replace(/'/g, "\\'")}')">🧹</button>`);
            }
            return out.join('');
        }

        _dismissButtons(nodeId, code) {
            if (!nodeId || !code) return '';
            const ignored = this._nodeIgnored(nodeId);
            if (ignored.includes(code)) {
                return `<button class="validator-jump" title="Restore this issue (no longer dismissed)" onclick="ValidatorPanel.setIgnore('${String(nodeId).replace(/'/g, "\\'")}','${String(code).replace(/'/g, "\\'")}',false)">🔓</button>`;
            }
            return `<button class="validator-jump" title="Dismiss this issue on this node (survives reloads; resets if you edit the node)" onclick="ValidatorPanel.setIgnore('${String(nodeId).replace(/'/g, "\\'")}','${String(code).replace(/'/g, "\\'")}',true)">🚫</button>`;
        }

        _flatRow(issue, scopeEl) {
            const nodeId = issue.source_node_id;
            const icon = SEV_ICONS[issue.severity] || 'ℹ';
            return `<div class="validator-item" data-code="${issue.code}">
                <span class="validator-sev" style="background:${SEV_COLORS[issue.severity] || SEV_COLORS.info};" title="${SEV_NAME[issue.severity] || issue.severity}"></span>
                <span class="validator-msg">${icon} ${issue.message}</span>
                ${this._actionsHtml(issue, nodeId)}
            </div>`;
        }

        _nodeGroupHtml(group) {
            const { nodeId, issues } = group;
            const worst = this._worst(issues);
            const worstSev = { 0: 'error', 1: 'warning', 2: 'info' }[worst] || 'info';
            const icon = SEV_ICONS[worstSev];
            const label = this._nodeLabel(nodeId);
            const rows = issues.map(issue => {
                const icon2 = SEV_ICONS[issue.severity] || 'ℹ';
                return `<div class="validator-item" data-code="${issue.code}" style="padding-left:8px;">
                    <span class="validator-sev" style="background:${SEV_COLORS[issue.severity] || SEV_COLORS.info};" title="${SEV_NAME[issue.severity] || issue.severity}"></span>
                    <span class="validator-msg">${icon2} ${issue.message}</span>
                    ${this._dismissButtons(nodeId, issue.code)}
                    ${this._actionsHtml(issue, nodeId)}
                </div>`;
            }).join('');
            return `<details class="validator-group" ${issues.length === 1 ? 'open' : ''} style="margin-bottom:2px;border-bottom:1px solid var(--border-light);">
                <summary style="font-size:10px;color:var(--text);cursor:pointer;display:flex;align-items:center;gap:6px;">
                    <span class="validator-sev" style="background:${SEV_COLORS[worstSev]};" title="${worstSev}"></span>
                    <span style="font-weight:600;color:${SEV_COLORS[worstSev]};">${icon}</span>
                    <span style="flex:1;word-break:break-all;">${label}</span>
                    <span style="font-size:9px;color:var(--text-muted);">${issues.length} issue${issues.length === 1 ? '' : 's'}</span>
                    <span style="font-size:9px;color:var(--text-dim);">▾</span>
                </summary>
                ${rows}
            </details>`;
        }

        _codeGroupHtml(group) {
            const { code, issues } = group;
            const worst = this._worst(issues);
            const worstSev = { 0: 'error', 1: 'warning', 2: 'info' }[worst] || 'info';
            const nodeIds = [...new Set(issues.map(i => i.source_node_id).filter(Boolean))];
            const rows = issues.map(issue => {
                const nodeId = issue.source_node_id;
                const icon = SEV_ICONS[issue.severity] || 'ℹ';
                return `<div class="validator-item" data-code="${code}" style="padding-left:8px;">
                    <span class="validator-sev" style="background:${SEV_COLORS[issue.severity] || SEV_COLORS.info};" title="${SEV_NAME[issue.severity] || issue.severity}"></span>
                    <span class="validator-msg">${icon} <span style="font-weight:600;">${this._nodeLabel(nodeId)}</span> — ${issue.message}</span>
                    ${this._dismissButtons(nodeId, code)}
                    ${this._actionsHtml(issue, nodeId)}
                </div>`;
            }).join('');
            const wayFixAll = ['way_missing_pass_message', 'way_missing_cardinal', 'way_missing_view_direction'].includes(code) && nodeIds.length;
            const fixAll = wayFixAll
                ? `<button class="validator-jump" title="Clean AI-minted placeholders, then draft missing pass/view/cardinal flavor with AI (review per way)" onclick="ValidatorPanel.fixAllWayOrientation()">✨ AI-write ways</button>`
                : (code === 'mechanical_tag_missing_props' && issues.some(i => i.severity === 'info') && nodeIds.length)
                ? `<button class="validator-jump" title="Apply engine defaults on all ${nodeIds.length} nodes (one undo)" onclick="ValidatorPanel.fixAll('${code}')">⚡ Fix all</button>`
                : '';
            return `<details class="validator-group" style="margin-bottom:2px;border-bottom:1px solid var(--border-light);">
                <summary style="font-size:10px;color:var(--text);cursor:pointer;display:flex;align-items:center;gap:6px;">
                    <span class="validator-sev" style="background:${SEV_COLORS[worstSev]};" title="${worstSev}"></span>
                    <span style="font-weight:600;color:${SEV_COLORS[worstSev]};">${SEV_ICONS[worstSev]} ${friendly(code)}</span>
                    <span style="flex:1;"></span>
                    <span style="font-size:9px;color:var(--text-muted);">×${issues.length}</span>
                    <span style="font-size:9px;color:var(--text-dim);">▾</span>
                </summary>
                ${fixAll}
                ${rows}
            </details>`;
        }
    }

    window.ValidatorPanel = new ValidatorPanel();
    window.VW = window.VW || {};
    VW.validatorPanel = window.ValidatorPanel;
})();