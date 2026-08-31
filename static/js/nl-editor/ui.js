/**
 * ui.js — User Interface components for Natural-Language Editor (task-387).
 *
 * Renders the side panel chat stream, staged ops tray, interactive clarification
 * buttons, and Cmd-L palette overlay.
 */

window.NLEditorUI = (() => {
    'use strict';

    class UI {
        constructor(controller) {
            this.controller = controller;
            this.container = null;
            this.chatList = null;
            this.inputField = null;
            this.stagedTray = null;
            this.statusBadge = null;
            this._checked = new Map(); // op.id -> bool (selective apply)
        }

        init(containerId = 'left-tab-nl-editor') {
            this.container = document.getElementById(containerId);
            if (!this.container) return;

            this.container.innerHTML = `
                <div class="nl-editor-root" style="display:flex;flex-direction:column;height:100%;font-size:12px;">
                    <div class="nl-header" style="padding:8px 10px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--bg-card);">
                        <div style="font-weight:600;display:flex;align-items:center;gap:6px;">
                            <span>✨ NL Editor</span>
                            <span id="nl-status" class="badge" style="font-size:10px;padding:2px 6px;background:var(--bg-input);border:1px solid var(--border);">Ready</span>
                        </div>
                        <div style="display:flex;gap:4px;">
                            <button class="btn btn-sm btn-ghost" id="nl-reset-btn" title="Reset Chat">🔄 Reset</button>
                        </div>
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

            this._bindEvents();
        }

        _bindEvents() {
            const sendBtn = document.getElementById('nl-send-btn');
            const resetBtn = document.getElementById('nl-reset-btn');
            const applyBtn = document.getElementById('nl-apply-btn');
            const rejectBtn = document.getElementById('nl-reject-btn');
            const clearStagedBtn = document.getElementById('nl-clear-staged-btn');

            const handleSend = () => {
                const text = this.inputField.value.trim();
                if (!text) return;
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
                    if (checked) ids.add(opId);
                }
                if (ids.size === 0) return;
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
            if (!this.chatList) return;
            const bubble = document.createElement('div');
            bubble.style.cssText = 'align-self:flex-end;max-width:85%;background:var(--primary);color:#fff;padding:6px 10px;border-radius:8px 8px 0 8px;font-size:11px;line-height:1.4;';
            bubble.textContent = text;
            this.chatList.appendChild(bubble);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }

        appendAssistantMessage(content, toolCalls = null) {
            if (!this.chatList) return;
            const bubble = document.createElement('div');
            bubble.style.cssText = 'align-self:flex-start;max-width:88%;background:var(--bg-card);border:1px solid var(--border);color:var(--text);padding:8px 10px;border-radius:8px 8px 8px 0;font-size:11px;line-height:1.4;';

            let html = '';
            if (toolCalls && toolCalls.length > 0) {
                html += `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">`;
                for (const call of toolCalls) {
                    html += `<span class="badge" style="font-size:9px;background:var(--border);padding:1px 5px;border-radius:3px;">🔧 ${call.function?.name || 'tool'}</span>`;
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

        appendToolEvent(name, result) {
            if (!this.chatList) return;
            const chip = document.createElement('div');
            chip.style.cssText = 'align-self:flex-start;font-size:10px;color:var(--text-muted);padding:2px 6px;background:var(--bg-input);border-radius:4px;border:1px dashed var(--border);';
            const resSummary = typeof result === 'object' ? (result.summary || (result.matches ? `${result.matches.length} matches` : JSON.stringify(result).slice(0, 40))) : String(result);
            chip.textContent = `↳ [${name}] ${resSummary}`;
            this.chatList.appendChild(chip);
            this.chatList.scrollTop = this.chatList.scrollHeight;
        }

        /** Show a live "running" chip for an in-flight tool call. */
        appendToolRunning(name) {
            if (!this.chatList) return;
            const chip = document.createElement('div');
            chip.style.cssText = 'align-self:flex-start;font-size:10px;color:var(--primary);padding:2px 6px;background:var(--bg-input);border-radius:4px;border:1px dashed var(--primary);';
            chip.textContent = `⏳ ${name}…`;
            chip.dataset.nlrunning = '1';
            this.chatList.appendChild(chip);
            this.chatList.scrollTop = this.chatList.scrollHeight;
            return chip;
        }

        hideClarification() {
            const tray = document.getElementById('nl-clarify-tray');
            if (tray) tray.style.display = 'none';
        }

        showClarification(question, options) {
            const tray = document.getElementById('nl-clarify-tray');
            const qEl = document.getElementById('nl-clarify-question');
            const optsEl = document.getElementById('nl-clarify-options');
            if (!tray || !qEl || !optsEl) return;

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

            (options || []).forEach(opt => {
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

            if (!tray || !listEl || !countEl) return;

            // Prune checkbox state for ops that disappeared; keep existing checks.
            const opIds = new Set(ops.map(o => o.id));
            for (const id of this._checked.keys()) {
                if (!opIds.has(id)) this._checked.delete(id);
            }

            countEl.textContent = ops.length;
            if (ops.length === 0) {
                tray.style.display = 'none';
                if (applyBtn) applyBtn.style.display = 'none';
                if (rejectBtn) rejectBtn.style.display = 'none';
                if (applySelectedBtn) applySelectedBtn.style.display = 'none';
                return;
            }

            tray.style.display = 'block';
            if (applyBtn) applyBtn.style.display = 'inline-block';
            if (rejectBtn) rejectBtn.style.display = 'inline-block';
            if (applySelectedBtn) applySelectedBtn.style.display = 'inline-block';

            listEl.innerHTML = '';
            ops.forEach(op => listEl.appendChild(this._renderStagedRow(op)));
            this._updateApplySelectedCount(ops);
        }

        _renderStagedRow(op) {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;flex-direction:column;background:var(--bg-input);border-radius:3px;';

            if (!this._checked.has(op.id)) this._checked.set(op.id, true);

            const head = document.createElement('div');
            head.style.cssText = 'display:flex;align-items:center;gap:5px;padding:3px 6px;';

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = this._checked.get(op.id);
            cb.title = 'Include in Apply Selected';
            cb.style.cssText = 'accent-color:var(--primary);margin:0;cursor:pointer;flex-shrink:0;';
            cb.onchange = () => {
                this._checked.set(op.id, cb.checked);
                this._updateApplySelectedCount(this.controller.staging.getOps());
            };
            head.appendChild(cb);

            const summary = document.createElement('span');
            summary.textContent = op.summary;
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
                if (!open) { ta.value = JSON.stringify(op.payload, null, 2); ta.focus(); }
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
                } catch (e) {
                    err.textContent = e.message;
                    err.style.display = 'block';
                }
            };

            return row;
        }

        _updateApplySelectedCount(ops) {
            const btn = document.getElementById('nl-apply-selected-btn');
            if (!btn) return;
            const n = ops.filter(o => this._checked.get(o.id) !== false).length;
            btn.textContent = `Apply Selected (${n})`;
        }

        setStatus(status, isBusy = false) {
            if (!this.statusBadge) return;
            this.statusBadge.textContent = status;
            if (isBusy) {
                this.statusBadge.style.color = 'var(--primary)';
                this.statusBadge.style.borderColor = 'var(--primary)';
            } else {
                this.statusBadge.style.color = 'var(--text-muted)';
                this.statusBadge.style.borderColor = 'var(--border)';
            }
        }

        _escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }
    }

    return { UI };
})();
