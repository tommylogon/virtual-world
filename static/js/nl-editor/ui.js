"use strict";
/**
 * ui.js — User Interface components for Natural-Language Editor (task-387).
 *
 * Renders the side panel chat stream, staged ops tray, interactive clarification
 * buttons, and Cmd-L palette overlay.
 *
 * @module nl-editor/ui — the NL editor's UI components
 * @contributes NLEditorUI: chat stream, staged-ops tray, clarification buttons, Cmd-L palette
 * @powers NL editor — interacting with the natural-language editor
 * @relates renders the nl-editor panel; driven by index.js
 * @docs docs/virtualWorld/dev_tasks/done/graph/task-387-natural-language-editor-mode.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.NLEditorUI = (() => {
    'use strict';
    /** Compact token count: 4200 -> "4.2k". */
    function _k(n) {
        if (!isFinite(n))
            return '0';
        return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
    }
    class UI {
        controller;
        container;
        chatList;
        inputField;
        stagedTray;
        statusBadge;
        budgetRow;
        budgetReadout;
        _checked; // op.id -> bool (selective apply)
        constructor(controller) {
            this.controller = controller;
            this.container = null;
            this.chatList = null;
            this.inputField = null;
            this.stagedTray = null;
            this.statusBadge = null;
            this.budgetRow = null;
            this.budgetReadout = null;
            this._checked = new Map();
        }
        init(containerId = 'left-tab-nl-editor') {
            this.container = document.getElementById(containerId);
            if (!this.container)
                return;
            this.container.innerHTML = `
                <div class="nl-editor-root" style="display:flex;flex-direction:column;height:100%;font-size:12px;">
                    <style>@keyframes nl-activity-pulse{0%,100%{opacity:1}50%{opacity:.3}}</style>
                    <div class="nl-header" style="padding:8px 10px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--bg-card);">
                        <div style="font-weight:600;display:flex;align-items:center;gap:6px;">
                            <span>✨ NL Editor</span>
                            <span id="nl-activity" title="Agent activity" style="display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:600;color:var(--text-muted);"><span id="nl-activity-dot" style="font-size:11px;line-height:1;">●</span><span id="nl-activity-label">idle</span></span>
                            <span id="nl-status" class="badge" style="font-size:10px;padding:2px 6px;background:var(--bg-input);border:1px solid var(--border);">Ready</span>
                            <span id="nl-budget-readout" style="font-size:10px;color:var(--text-muted);"></span>
                        </div>
                        <div style="display:flex;gap:4px;align-items:center;">
                            <button class="btn btn-sm btn-ghost" id="nl-font-dec" title="Smaller chat text">A−</button>
                            <button class="btn btn-sm btn-ghost" id="nl-font-inc" title="Larger chat text">A+</button>
                            <button class="btn btn-sm btn-ghost" id="nl-budget-btn" title="LLM budget">⚙ Budget</button>
                            <button class="btn btn-sm btn-ghost" id="nl-reset-btn" title="Reset Chat">🔄 Reset</button>
                        </div>
                    </div>

                    <!-- Budget knobs (task-422) -->
                    <div id="nl-budget-row" style="display:none;padding:8px 10px;border-bottom:1px solid var(--border);background:var(--bg-card);font-size:11px;">
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
                            <label>Max rounds<input id="nl-budget-rounds" type="number" min="1" style="width:100%;"></label>
                            <label>Max context tokens<input id="nl-budget-tokens" type="number" min="256" style="width:100%;"></label>
                            <label>Max messages<input id="nl-budget-messages" type="number" min="1" style="width:100%;"></label>
                            <label>Recent turns kept<input id="nl-budget-recent" type="number" min="1" style="width:100%;"></label>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);margin-top:4px;">Defaults follow the active model&apos;s window; unknown models use a conservative cap.</div>
                    </div>

                    <!-- Chat stream -->
                    <div id="nl-chat-list" style="flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px;background:var(--bg-dark);"></div>

                    <!-- Clarification Options Area -->
                    <div id="nl-clarify-tray" style="display:none;padding:8px 10px;background:var(--bg-card);border-top:1px solid var(--border);border-bottom:1px solid var(--border);">
                        <div id="nl-clarify-question" style="font-weight:600;margin-bottom:6px;color:var(--primary);"></div>
                        <div id="nl-clarify-options" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
                    </div>

                    <!-- Staged Operations Tray -->
                    <div id="nl-staged-tray" style="display:none;max-height:140px;overflow-y:auto;padding:6px 10px;background:var(--bg-card);border-top:1px solid var(--border);font-size:11px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                            <span style="font-weight:600;color:var(--text-muted);">📋 Staged Operations (<span id="nl-staged-count">0</span>)</span>
                            <button class="btn btn-sm btn-ghost" id="nl-clear-staged-btn" style="font-size:10px;padding:1px 4px;">Clear All</button>
                        </div>
                        <div id="nl-staged-list" style="display:flex;flex-direction:column;gap:4px;"></div>
                    </div>

                    <!-- Input Controls & Actions -->
                    <div class="nl-footer" style="padding:8px 10px;border-top:1px solid var(--border);background:var(--bg-card);">
                        <div style="display:flex;gap:6px;margin-bottom:6px;">
                            <textarea id="nl-input" rows="2" placeholder="Describe what to add or edit... (e.g. 'Add a flickering lamp in the garden')" style="flex:1;resize:none;font-size:11px;padding:6px;border-radius:4px;border:1px solid var(--border);background:var(--bg-input);color:var(--text);"></textarea>
                            <button class="btn btn-sm btn-primary" id="nl-send-btn" style="align-self:stretch;padding:0 12px;">Send</button>
                        </div>
                        <div style="display:flex;gap:6px;justify-content:flex-end;">
                            <button class="btn btn-sm btn-ghost" id="nl-reject-btn" style="display:none;">Reject Staged</button>
                            <button class="btn btn-sm btn-primary" id="nl-apply-selected-btn" style="display:none;">Apply Selected (0)</button>
                            <button class="btn btn-sm btn-green" id="nl-apply-btn" style="display:none;background:var(--green,#2e7d32);color:#fff;">Apply Changes</button>
                        </div>
                    </div>
                </div>
            `;
            this.chatList = document.getElementById('nl-chat-list');
            this.inputField = document.getElementById('nl-input');
            this.stagedTray = document.getElementById('nl-staged-tray');
            this.statusBadge = document.getElementById('nl-status');
            this.budgetRow = document.getElementById('nl-budget-row');
            this.budgetReadout = document.getElementById('nl-budget-readout');
            this._bindEvents();
            void this._initBudget();
            this._initChatFont();
        }
        /**
         * Adjustable chat text size, persisted per browser as `vw_nl_fontSize`.
         * Scales the message bubbles via the `--nl-fs` custom property so the
         * panel does not depend on the (fixed) surrounding chrome.
         */
        _initChatFont() {
            const MIN = 9, MAX = 20, DEFAULT = 12;
            const read = () => {
                const raw = parseInt(localStorage.getItem('vw_nl_fontSize') || '', 10);
                return Number.isFinite(raw) ? Math.min(MAX, Math.max(MIN, raw)) : DEFAULT;
            };
            const apply = (px) => {
                this.chatList?.style.setProperty('--nl-fs', `${px}px`);
            };
            apply(read());
            const bump = (delta) => {
                const next = Math.min(MAX, Math.max(MIN, read() + delta));
                localStorage.setItem('vw_nl_fontSize', String(next));
                apply(next);
            };
            document.getElementById('nl-font-dec')?.addEventListener('click', () => bump(-1));
            document.getElementById('nl-font-inc')?.addEventListener('click', () => bump(1));
        }
        /** Wire the budget row (task-422): persist each knob on change. */
        async _initBudget() {
            const toggle = document.getElementById('nl-budget-btn');
            toggle?.addEventListener('click', () => {
                if (!this.budgetRow)
                    return;
                this.budgetRow.style.display = this.budgetRow.style.display === 'none' ? 'block' : 'none';
            });
            const B = window.NlEditorBudget;
            const s = window.storage;
            const model = window.config?.model || null;
            const read = async (key) => {
                if (!s)
                    return undefined;
                const v = await s.getConfig(key);
                if (v === undefined || v === null || v === '')
                    return undefined;
                return isFinite(Number(v)) ? Number(v) : undefined;
            };
            const raw = s ? {
                maxIterations: await read('nl_max_iterations'),
                maxTokens: await read('nl_max_tokens'),
                maxMessages: await read('nl_max_messages'),
                recentTurnCount: await read('nl_recent_turns')
            } : {};
            const b = B ? B.clampBudget(raw, model) : null;
            this._setBudgetInputs('nl-budget-rounds', b?.maxIterations);
            this._setBudgetInputs('nl-budget-tokens', b?.maxTokens);
            this._setBudgetInputs('nl-budget-messages', b?.maxMessages);
            this._setBudgetInputs('nl-budget-recent', b?.recentTurnCount);
            const persist = (id, key) => {
                const el = document.getElementById(id);
                el?.addEventListener('change', () => {
                    if (s && el.value !== '')
                        void s.setConfig?.(key, el.value);
                });
            };
            persist('nl-budget-rounds', 'nl_max_iterations');
            persist('nl-budget-tokens', 'nl_max_tokens');
            persist('nl-budget-messages', 'nl_max_messages');
            persist('nl-budget-recent', 'nl_recent_turns');
        }
        _setBudgetInputs(id, value) {
            const el = document.getElementById(id);
            if (el && value !== undefined)
                el.value = String(value);
        }
        /** Live window/round readout; called on each llm:calling event. */
        setBudgetReadout(stats, iteration, maxIterations) {
            if (!this.budgetReadout)
                return;
            const parts = [];
            if (stats)
                parts.push(`context ${_k(stats.totalTokens)}/${_k(stats.maxTokens)}`);
            if (iteration && maxIterations)
                parts.push(`round ${iteration}/${maxIterations}`);
            this.budgetReadout.textContent = parts.join(' · ');
        }
        _bindEvents() {
            const sendBtn = document.getElementById('nl-send-btn');
            const resetBtn = document.getElementById('nl-reset-btn');
            const applyBtn = document.getElementById('nl-apply-btn');
            const rejectBtn = document.getElementById('nl-reject-btn');
            const clearStagedBtn = document.getElementById('nl-clear-staged-btn');
            const handleSend = () => {
                const text = this.inputField.value.trim();
                if (!text)
                    return;
                this.inputField.value = '';
                this.controller.send(text);
            };
            sendBtn?.addEventListener('click', handleSend);
            this.inputField?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                }
            });
            resetBtn?.addEventListener('click', () => {
                if (confirm('Reset NL Editor chat session?')) {
                    this.controller.reset();
                }
            });
            applyBtn?.addEventListener('click', async () => {
                applyBtn.disabled = true;
                applyBtn.textContent = 'Applying...';
                await this.controller.apply();
                applyBtn.disabled = false;
                applyBtn.textContent = 'Apply Changes';
            });
            const applySelectedBtn = document.getElementById('nl-apply-selected-btn');
            applySelectedBtn?.addEventListener('click', async () => {
                const ids = new Set();
                for (const [opId, checked] of this._checked) {
                    if (checked)
                        ids.add(opId);
                }
                if (ids.size === 0)
                    return;
                applySelectedBtn.disabled = true;
                applySelectedBtn.textContent = 'Applying...';
                await this.controller.applySelected(ids);
                applySelectedBtn.disabled = false;
            });
            rejectBtn?.addEventListener('click', () => {
                this.controller.staging.clear();
            });
            clearStagedBtn?.addEventListener('click', () => {
                this.controller.staging.clear();
            });
        }
        appendUserMessage(text) {
            if (!this.chatList)
                return;
            const bubble = document.createElement('div');
            bubble.style.cssText = 'align-self:flex-end;max-width:85%;background:var(--primary);color:#fff;padding:6px 10px;border-radius:8px 8px 0 8px;font-size:var(--nl-fs,11px);line-height:1.4;';
            bubble.textContent = text;
            this.chatList.appendChild(bubble);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }
        appendAssistantMessage(content, toolCalls = null) {
            if (!this.chatList)
                return;
            const bubble = document.createElement('div');
            bubble.style.cssText = 'align-self:flex-start;max-width:88%;background:var(--bg-card);border:1px solid var(--border);color:var(--text);padding:8px 10px;border-radius:8px 8px 8px 0;font-size:var(--nl-fs,11px);line-height:1.4;';
            let html = '';
            if (toolCalls && toolCalls.length > 0) {
                html += `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">`;
                for (const call of toolCalls) {
                    html += `<span class="badge" style="font-size:calc(var(--nl-fs,11px) - 2px);background:var(--border);padding:1px 5px;border-radius:3px;">🔧 ${call.function?.name || 'tool'}</span>`;
                }
                html += `</div>`;
            }
            if (content) {
                html += `<div>${this._escapeHtml(content).replace(/\n/g, '<br>')}</div>`;
            }
            bubble.innerHTML = html;
            this.chatList.appendChild(bubble);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }
        /** Divider after Apply: the world changed, the conversation did not. */
        appendAppliedNotice(appliedCount, remaining = 0) {
            if (!this.chatList)
                return;
            const chip = document.createElement('div');
            chip.style.cssText = 'align-self:center;font-size:calc(var(--nl-fs,11px) - 1px);color:var(--text-muted);padding:3px 8px;background:var(--bg-input);border-radius:10px;border:1px solid var(--border);';
            const pending = remaining > 0 ? ` · ${remaining} still staged` : '';
            chip.textContent = `✔ Applied ${appliedCount} change${appliedCount === 1 ? '' : 's'}${pending} — chat kept`;
            this.chatList.appendChild(chip);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }
        /** A muted, centered notice chip (e.g. the round-cap stop, task-422). */
        appendSystemNotice(text) {
            if (!this.chatList)
                return;
            const chip = document.createElement('div');
            chip.style.cssText = 'align-self:center;font-size:calc(var(--nl-fs,11px) - 1px);color:var(--text-muted);padding:3px 8px;background:var(--bg-input);border-radius:10px;border:1px solid var(--border);';
            chip.textContent = text;
            this.chatList.appendChild(chip);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }
        appendErrorMessage(text) {
            if (!this.chatList || !text)
                return;
            const bubble = document.createElement('div');
            bubble.style.cssText = 'align-self:flex-start;max-width:88%;background:rgba(248,81,73,0.12);border:1px solid var(--red,#f85149);color:var(--red,#f85149);padding:6px 10px;border-radius:8px;font-size:var(--nl-fs,11px);line-height:1.4;';
            bubble.textContent = `⚠ ${text}`;
            this.chatList.appendChild(bubble);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }
        /** Render the pre-Apply validation gate's findings (task-461). */
        showValidationIssues(issues, blocked = false) {
            if (!this.chatList || !issues || !issues.length)
                return;
            const bubble = document.createElement('div');
            bubble.style.cssText = 'align-self:flex-start;max-width:88%;background:rgba(210,153,34,0.12);border:1px solid #d29922;color:#d29922;padding:6px 10px;border-radius:8px;font-size:var(--nl-fs,11px);line-height:1.5;white-space:pre-wrap;';
            const shown = issues.slice(0, 8);
            const lines = shown.map(i => `• op #${(i.index ?? 0) + 1}${i.type ? ` [${i.type}]` : ''}: ${i.message}`);
            if (issues.length > shown.length)
                lines.push(`+${issues.length - shown.length} more`);
            bubble.textContent = `${blocked ? '⛔ Apply blocked — fix these first:' : '⚠ Validation:'}\n${lines.join('\n')}`;
            this.chatList.appendChild(bubble);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }
        appendToolEvent(name, result) {
            if (!this.chatList)
                return;
            const chip = document.createElement('div');
            chip.style.cssText = 'align-self:flex-start;font-size:calc(var(--nl-fs,11px) - 1px);color:var(--text-muted);padding:2px 6px;background:var(--bg-input);border-radius:4px;border:1px dashed var(--border);';
            const res = result;
            const resSummary = typeof result === 'object' ? (res.summary || (res.matches ? `${res.matches.length} matches` : JSON.stringify(result).slice(0, 40))) : String(result);
            chip.textContent = `↳ [${name}] ${resSummary}`;
            this.chatList.appendChild(chip);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }
        /** Show a live "running" chip for an in-flight tool call. */
        appendToolRunning(name) {
            if (!this.chatList)
                return;
            const chip = document.createElement('div');
            chip.style.cssText = 'align-self:flex-start;font-size:calc(var(--nl-fs,11px) - 1px);color:var(--primary);padding:2px 6px;background:var(--bg-input);border-radius:4px;border:1px dashed var(--primary);';
            chip.textContent = `⏳ ${name}…`;
            chip.dataset.nlrunning = '1';
            this.chatList.appendChild(chip);
            this.chatList.scrollTop = this.chatList.scrollHeight;
            return chip;
        }
        hideClarification() {
            const tray = document.getElementById('nl-clarify-tray');
            if (tray)
                tray.style.display = 'none';
        }
        showClarification(question, options) {
            const tray = document.getElementById('nl-clarify-tray');
            const qEl = document.getElementById('nl-clarify-question');
            const optsEl = document.getElementById('nl-clarify-options');
            if (!tray || !qEl || !optsEl)
                return;
            qEl.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
                    <span>${this._escapeHtml(question)}</span>
                    <button class="btn btn-sm btn-ghost" id="nl-clarify-dismiss" style="padding:0 4px;font-size:12px;color:var(--text-muted);" title="Dismiss question">✕</button>
                </div>
            `;
            optsEl.innerHTML = '';
            document.getElementById('nl-clarify-dismiss')?.addEventListener('click', () => {
                this.hideClarification();
            });
            (options || []).forEach((opt) => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-sm';
                btn.style.cssText = 'font-size:11px;padding:4px 8px;border:1px solid var(--primary);background:var(--bg-input);color:var(--primary);cursor:pointer;border-radius:4px;text-align:left;line-height:1.3;';
                btn.textContent = opt;
                btn.onclick = () => {
                    this.hideClarification();
                    this.controller.send(opt);
                };
                optsEl.appendChild(btn);
            });
            tray.style.display = 'block';
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }
        updateStagedOps(ops) {
            const tray = document.getElementById('nl-staged-tray');
            const listEl = document.getElementById('nl-staged-list');
            const countEl = document.getElementById('nl-staged-count');
            const applyBtn = document.getElementById('nl-apply-btn');
            const rejectBtn = document.getElementById('nl-reject-btn');
            const applySelectedBtn = document.getElementById('nl-apply-selected-btn');
            if (!tray || !listEl || !countEl)
                return;
            // Prune checkbox state for ops that disappeared; keep existing checks.
            const opIds = new Set(ops.map((o) => o.id));
            for (const id of this._checked.keys()) {
                if (!opIds.has(id))
                    this._checked.delete(id);
            }
            countEl.textContent = String(ops.length);
            if (ops.length === 0) {
                tray.style.display = 'none';
                if (applyBtn)
                    applyBtn.style.display = 'none';
                if (rejectBtn)
                    rejectBtn.style.display = 'none';
                if (applySelectedBtn)
                    applySelectedBtn.style.display = 'none';
                return;
            }
            tray.style.display = 'block';
            if (applyBtn)
                applyBtn.style.display = 'inline-block';
            if (rejectBtn)
                rejectBtn.style.display = 'inline-block';
            if (applySelectedBtn)
                applySelectedBtn.style.display = 'inline-block';
            listEl.innerHTML = '';
            ops.forEach((op) => listEl.appendChild(this._renderStagedRow(op)));
            this._updateApplySelectedCount(ops);
        }
        _renderStagedRow(op) {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;flex-direction:column;background:var(--bg-input);border-radius:3px;';
            if (!this._checked.has(op.id))
                this._checked.set(op.id, true);
            const head = document.createElement('div');
            head.style.cssText = 'display:flex;align-items:center;gap:5px;padding:3px 6px;';
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = this._checked.get(op.id) ?? false;
            cb.title = 'Include in Apply Selected';
            cb.style.cssText = 'accent-color:var(--primary);margin:0;cursor:pointer;flex-shrink:0;';
            cb.onchange = () => {
                this._checked.set(op.id, cb.checked);
                this._updateApplySelectedCount(this.controller.staging.getOps());
            };
            head.appendChild(cb);
            const summary = document.createElement('span');
            summary.textContent = op.summary ?? '';
            summary.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer;';
            summary.title = 'Click to edit op payload';
            head.appendChild(summary);
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm btn-ghost';
            editBtn.textContent = '✎';
            editBtn.style.cssText = 'padding:0 4px;font-size:11px;flex-shrink:0;';
            editBtn.title = 'Tweak op payload';
            head.appendChild(editBtn);
            const removeBtn = document.createElement('button');
            removeBtn.className = 'btn btn-sm btn-ghost';
            removeBtn.textContent = '✕';
            removeBtn.style.cssText = 'padding:0 4px;color:var(--red,#e57373);font-size:11px;flex-shrink:0;';
            removeBtn.title = 'Unstage op';
            head.appendChild(removeBtn);
            removeBtn.onclick = () => this.controller.staging.removeOp(op.id);
            row.appendChild(head);
            // ── Property-level diff preview (task-461) ──
            if (window.NLEditorDiff) {
                let lines = [];
                try {
                    lines = window.NLEditorDiff.summaryLines(op, {
                        nodes: (typeof worldState !== 'undefined' && worldState?.graph?.nodes) || {},
                        creations: this.controller.staging.getStagedCreations(),
                    });
                }
                catch (e) {
                    lines = [];
                }
                if (lines.length) {
                    const diffEl = document.createElement('div');
                    diffEl.style.cssText = 'padding:0 6px 4px 24px;font-size:10px;color:var(--text-muted);line-height:1.5;white-space:pre-wrap;';
                    diffEl.textContent = lines.join('\n');
                    row.appendChild(diffEl);
                }
            }
            // ── Inline payload tweaker ──
            const editor = document.createElement('div');
            editor.style.cssText = 'display:none;padding:4px 6px 6px;gap:4px;flex-direction:column;';
            const ta = document.createElement('textarea');
            ta.value = JSON.stringify(op.payload, null, 2);
            ta.rows = 4;
            ta.style.cssText = 'width:100%;box-sizing:border-box;font-family:monospace;font-size:10px;background:var(--bg-dark);color:var(--text);border:1px solid var(--border);border-radius:3px;padding:4px;resize:vertical;';
            const bar = document.createElement('div');
            bar.style.cssText = 'display:flex;gap:4px;justify-content:flex-end;';
            const saveBtn = document.createElement('button');
            saveBtn.className = 'btn btn-sm btn-primary';
            saveBtn.textContent = 'Save';
            saveBtn.style.cssText = 'font-size:10px;padding:2px 8px;';
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-sm btn-ghost';
            cancelBtn.textContent = 'Cancel';
            cancelBtn.style.cssText = 'font-size:10px;padding:2px 8px;';
            const err = document.createElement('div');
            err.style.cssText = 'font-size:10px;color:#f85149;display:none;';
            bar.appendChild(err);
            bar.appendChild(cancelBtn);
            bar.appendChild(saveBtn);
            editor.appendChild(ta);
            editor.appendChild(bar);
            row.appendChild(editor);
            const toggleOpen = () => {
                const open = editor.style.display === 'flex';
                editor.style.display = open ? 'none' : 'flex';
                err.style.display = 'none';
                if (!open) {
                    ta.value = JSON.stringify(op.payload, null, 2);
                    ta.focus();
                }
            };
            editBtn.onclick = toggleOpen;
            summary.onclick = toggleOpen;
            cancelBtn.onclick = toggleOpen;
            saveBtn.onclick = () => {
                try {
                    const payload = JSON.parse(ta.value);
                    if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
                        throw new Error('Payload must be a JSON object');
                    }
                    this.controller.staging.updateOp(op.id, payload);
                    editor.style.display = 'none';
                }
                catch (e) {
                    err.textContent = e instanceof Error ? e.message : String(e);
                    err.style.display = 'block';
                }
            };
            return row;
        }
        _updateApplySelectedCount(ops) {
            const btn = document.getElementById('nl-apply-selected-btn');
            if (!btn)
                return;
            const n = ops.filter((o) => this._checked.get(o.id) !== false).length;
            btn.textContent = `Apply Selected (${n})`;
        }
        /**
         * Persistent agent-activity indicator (task-739 follow-up): the status
         * badge is transient text, so after the model narrates and stops the
         * user cannot tell "still working" from "gave up". `stopped` = the turn
         * ended without running a single tool (it talked, it did not act).
         */
        setActivity(state) {
            const dot = document.getElementById('nl-activity-dot');
            const label = document.getElementById('nl-activity-label');
            if (!dot || !label)
                return;
            const colors = {
                working: 'var(--primary)', idle: 'var(--text-muted)',
                waiting: '#d29922', stopped: '#d29922', error: '#d13438'
            };
            const labels = {
                working: 'working', idle: 'idle', waiting: 'your turn',
                stopped: 'stopped — no action', error: 'error'
            };
            dot.style.color = colors[state] || 'var(--text-muted)';
            dot.style.animation = state === 'working' ? 'nl-activity-pulse 1s ease-in-out infinite' : 'none';
            label.textContent = labels[state] || state;
        }
        setStatus(status, isBusy = false) {
            if (!this.statusBadge)
                return;
            this.statusBadge.textContent = status;
            if (isBusy) {
                this.statusBadge.style.color = 'var(--primary)';
                this.statusBadge.style.borderColor = 'var(--primary)';
            }
            else {
                this.statusBadge.style.color = 'var(--text-muted)';
                this.statusBadge.style.borderColor = 'var(--border)';
            }
        }
        _escapeHtml(str) {
            if (!str)
                return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }
    }
    return { UI };
})();
