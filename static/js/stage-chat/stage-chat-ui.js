"use strict";
/**
 * @module stage-chat-ui — DOM rendering and user interaction for Stage Chat
 * @contributes StageChatUI: renders messages, participants, monologue, handles inputs
 * @powers Stage Chat UI
 * @relates StageChatState, StageChatApi, StageChatAgent
 * @docs docs/virtualWorld/dev_tasks/todo/gameplay/task-824-stage-chat-turn-based-character-perspective-chat-page.md
 */
(function () {
    'use strict';
    class StageChatUI {
        static init() {
            const feed = document.getElementById('stage-chat-feed');
            const form = document.getElementById('stage-chat-form');
            const input = document.getElementById('stage-chat-input');
            const pauseBtn = document.getElementById('stage-pause-btn');
            const stepBtn = document.getElementById('stage-step-btn');
            if (form && input) {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const text = input.value.trim();
                    if (!text)
                        return;
                    input.value = '';
                    try {
                        await window.StageChatApi.postMessage('User', text);
                        await window.StageChatState.sync();
                        if (feed)
                            feed.scrollTop = feed.scrollHeight;
                    }
                    catch (err) {
                        console.error('Failed to post message:', err);
                    }
                });
            }
            if (pauseBtn) {
                pauseBtn.addEventListener('click', () => {
                    const state = window.StageChatState;
                    state.isPaused = !state.isPaused;
                    pauseBtn.textContent = state.isPaused ? '▶ Resume' : '⏸ Pause';
                    const chip = document.getElementById('stage-status-chip');
                    if (chip)
                        chip.textContent = state.isPaused ? 'Paused' : 'Active';
                });
            }
            if (stepBtn) {
                stepBtn.addEventListener('click', () => {
                    window.StageChatAgent.stepOne();
                });
            }
            window.StageChatState.subscribe(() => {
                this.render();
            });
        }
        static render() {
            this.renderMessages();
            this.renderParticipants();
            this.renderMonologues();
        }
        static renderMessages() {
            const feed = document.getElementById('stage-chat-feed');
            if (!feed)
                return;
            const msgs = window.StageChatState.messages || [];
            feed.innerHTML = msgs.map((m) => {
                const isUser = m.author === 'User';
                const timeStr = new Date(m.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                return `
                    <div class="chat-msg ${isUser ? 'user' : ''}">
                        <div class="chat-msg-header">
                            <span class="chat-msg-author">${escapeHtml(m.author)}</span>
                            <span class="chat-msg-time">${timeStr}</span>
                        </div>
                        <div class="chat-msg-text">${escapeHtml(m.text)}</div>
                    </div>
                `;
            }).join('');
        }
        static renderParticipants() {
            const list = document.getElementById('stage-participants-list');
            if (!list)
                return;
            const participants = window.StageChatState.participants || {};
            const names = Object.keys(participants);
            list.innerHTML = names.map(name => {
                const p = participants[name];
                const talkativeness = window.StageChatAgent.getTalkativeness(name);
                return `
                    <div class="participant-item">
                        <div class="participant-row">
                            <span class="participant-name">${escapeHtml(name)}</span>
                            <span class="participant-badge ${p.unread_count > 0 ? 'unread' : ''}">
                                ${p.unread_count > 0 ? `${p.unread_count} unread` : 'up to date'}
                            </span>
                        </div>
                        <div class="participant-controls">
                            <label><input type="checkbox" ${p.active ? 'checked' : ''} onchange="StageChatUI.toggleActive('${escapeHtml(name)}', this.checked)"> In Chat</label>
                            <label><input type="checkbox" ${p.blocked ? 'checked' : ''} onchange="StageChatUI.toggleBlocked('${escapeHtml(name)}', this.checked)"> Block</label>
                        </div>
                        <div class="talkativeness-control">
                            <div class="talkativeness-label">
                                <span>Pacing</span>
                                <span>~${talkativeness}s</span>
                            </div>
                            <input type="range" class="talkativeness-slider" min="5" max="120" value="${talkativeness}"
                                oninput="StageChatAgent.setTalkativeness('${escapeHtml(name)}', this.value); this.previousElementSibling.lastElementChild.textContent = '~' + this.value + 's';">
                        </div>
                    </div>
                `;
            }).join('');
        }
        static renderMonologues() {
            const list = document.getElementById('stage-monologue-list');
            if (!list)
                return;
            const monologues = window.StageChatState.monologues || [];
            list.innerHTML = monologues.map((m) => {
                const timeStr = new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                return `
                    <div class="monologue-card">
                        <div class="monologue-char">
                            <span>${escapeHtml(m.charName)}</span>
                            <span style="font-size: 11px; color: #718096;">${timeStr}</span>
                        </div>
                        <div class="monologue-action">Action: ${escapeHtml(m.actionType)}</div>
                        <div class="monologue-thought">${escapeHtml(m.thought)}</div>
                    </div>
                `;
            }).join('');
        }
        static async toggleActive(name, active) {
            await window.StageChatApi.updateParticipant(name, active, undefined);
            await window.StageChatState.sync();
        }
        static async toggleBlocked(name, blocked) {
            await window.StageChatApi.updateParticipant(name, undefined, blocked);
            await window.StageChatState.sync();
        }
    }
    function escapeHtml(str) {
        return (str || '').replace(/[&<>'"]/g, (tag) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
    }
    window.StageChatUI = StageChatUI;
})();
