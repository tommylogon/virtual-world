"use strict";
/**
 * @module stage-chat-ui — social conversation UI for Stage Chat
 * @contributes conversation list, messages, membership controls, and inputs
 * @powers Stage Chat phone/social surface
 * @relates StageChatState, StageChatApi, StageChatAgent
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */
(function () {
    'use strict';
    class StageChatUI {
        static init() {
            const form = document.getElementById('stage-chat-form');
            const input = document.getElementById('stage-chat-input');
            const participantList = document.getElementById('stage-participants-list');
            const channelList = document.getElementById('stage-channel-list');
            const perspective = document.getElementById('stage-perspective');
            const groupDialog = document.getElementById('stage-group-dialog');
            const dmDialog = document.getElementById('stage-dm-dialog');
            form?.addEventListener('submit', async (event) => {
                event.preventDefault();
                const text = input?.value.trim() || '';
                const state = window.StageChatState;
                if (!text || !state.selectedChannelId)
                    return;
                if (input)
                    input.value = '';
                try {
                    await window.StageChatApi.postMessage(state.perspective, text, state.selectedChannelId);
                    await state.sync();
                }
                catch (error) {
                    console.error('Failed to post message:', error);
                    if (input)
                        input.value = text;
                }
            });
            document.getElementById('stage-pause-btn')?.addEventListener('click', () => {
                const state = window.StageChatState;
                state.setPaused(!state.manualPaused, 'manual');
            });
            document.getElementById('stage-step-btn')?.addEventListener('click', () => {
                void window.StageChatAgent.stepOne();
            });
            perspective?.addEventListener('change', () => {
                void window.StageChatState.selectPerspective(perspective.value);
            });
            channelList?.addEventListener('click', (event) => {
                const button = event.target.closest('[data-channel-id]');
                if (button)
                    void window.StageChatState.selectChannel(button.dataset.channelId || '');
            });
            if (participantList) {
                participantList.addEventListener('change', (event) => {
                    const target = event.target;
                    const name = target?.dataset.character;
                    if (!target || !name)
                        return;
                    if (target.dataset.role === 'active')
                        void this.toggleParticipant(name, { active: target.checked });
                    if (target.dataset.role === 'blocked')
                        void this.toggleParticipant(name, { blocked: target.checked });
                    if (target.dataset.role === 'pace')
                        window.StageChatAgent.setTalkativeness(name, target.value, true);
                });
                participantList.addEventListener('input', (event) => {
                    const target = event.target;
                    const name = target?.dataset.character;
                    if (!target || target.dataset.role !== 'pace' || !name)
                        return;
                    window.StageChatAgent.setTalkativeness(name, target.value);
                    const output = participantList.querySelector(`[data-pace-for="${CSS.escape(name)}"]`);
                    if (output)
                        output.textContent = `${target.value}s`;
                    this.renderRateEstimate();
                });
                participantList.addEventListener('focusout', () => this.renderParticipants());
            }
            document.getElementById('stage-new-group')?.addEventListener('click', () => {
                this.renderGroupRoster();
                groupDialog?.showModal();
            });
            document.getElementById('stage-group-close')?.addEventListener('click', () => groupDialog?.close());
            document.getElementById('stage-group-cancel')?.addEventListener('click', () => groupDialog?.close());
            document.getElementById('stage-group-form')?.addEventListener('submit', (event) => {
                event.preventDefault();
                void this.createGroup(groupDialog);
            });
            document.getElementById('stage-new-dm')?.addEventListener('click', () => {
                this.renderDmRecipients();
                dmDialog?.showModal();
            });
            document.getElementById('stage-dm-close')?.addEventListener('click', () => dmDialog?.close());
            document.getElementById('stage-dm-cancel')?.addEventListener('click', () => dmDialog?.close());
            document.getElementById('stage-dm-form')?.addEventListener('submit', (event) => {
                event.preventDefault();
                void this.createDm(dmDialog);
            });
            document.getElementById('stage-member-editor')?.addEventListener('click', (event) => {
                const button = event.target.closest('[data-member-action]');
                if (!button)
                    return;
                if (button.dataset.memberAction === 'add') {
                    const select = document.getElementById('stage-member-to-add');
                    if (select?.value)
                        void this.changeMember(select.value, true);
                }
                if (button.dataset.memberAction === 'remove')
                    void this.changeMember(button.dataset.name || '', false);
            });
            window.StageChatState.subscribe(() => this.render());
        }
        static render() {
            this.renderPerspective();
            this.renderChannels();
            this.renderConversation();
            this.renderMessages();
            this.renderParticipants();
            this.renderRateEstimate();
            this.renderPauseState();
        }
        static renderPerspective() {
            const select = document.getElementById('stage-perspective');
            if (!select)
                return;
            const state = window.StageChatState;
            const names = ['User', ...Object.keys(state.participants || {}).filter((name) => name !== 'User')];
            const signature = names.join('\0');
            if (select.dataset.signature !== signature) {
                select.innerHTML = names.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
                select.dataset.signature = signature;
            }
            select.value = state.perspective;
            const identity = document.getElementById('stage-composer-identity');
            if (identity)
                identity.textContent = state.perspective;
        }
        static renderChannels() {
            const list = document.getElementById('stage-channel-list');
            if (!list)
                return;
            const state = window.StageChatState;
            const channels = state.channels || [];
            list.innerHTML = channels.map((channel) => {
                const icon = channel.kind === 'public' ? '#' : channel.kind === 'group' ? '◉' : '↗';
                const unread = Number(channel.unread_count || 0);
                const people = channel.kind === 'public'
                    ? 'Open conversation'
                    : `${(channel.members || []).filter((name) => name !== state.perspective).join(', ')}`;
                return `<button type="button" class="stage-channel-row ${channel.id === state.selectedChannelId ? 'selected' : ''}"
                    data-channel-id="${escapeHtml(channel.id)}" aria-current="${channel.id === state.selectedChannelId ? 'true' : 'false'}">
                    <span class="stage-channel-icon ${escapeHtml(channel.kind)}">${icon}</span>
                    <span class="stage-channel-copy"><span class="stage-channel-name">${escapeHtml(channel.name)}</span>
                    <span class="stage-channel-preview">${escapeHtml(people || channel.kind)}</span></span>
                    ${unread ? `<span class="stage-unread-badge">${unread > 99 ? '99+' : unread}</span>` : ''}
                </button>`;
            }).join('') || '<div class="stage-empty-note">No conversations yet.</div>';
        }
        static renderConversation() {
            const state = window.StageChatState;
            const channel = (state.channels || []).find((item) => item.id === state.selectedChannelId);
            const title = document.getElementById('stage-channel-name');
            const subtitle = document.getElementById('stage-channel-subtitle');
            const avatar = document.getElementById('stage-channel-avatar');
            const count = document.getElementById('stage-channel-member-count');
            const membersList = document.getElementById('stage-channel-members');
            const editor = document.getElementById('stage-member-editor');
            const send = document.getElementById('stage-send-btn');
            const input = document.getElementById('stage-chat-input');
            if (!channel) {
                if (title)
                    title.textContent = 'No conversation selected';
                if (subtitle)
                    subtitle.textContent = 'Choose a conversation to open your inbox.';
                if (avatar)
                    avatar.textContent = '·';
                if (count)
                    count.textContent = '';
                if (membersList)
                    membersList.innerHTML = '';
                if (editor)
                    editor.innerHTML = '';
                if (send)
                    send.disabled = true;
                if (input)
                    input.disabled = true;
                return;
            }
            const members = channel.kind === 'public'
                ? Object.keys(state.participants || {})
                : (channel.members || []);
            const subtitleText = channel.kind === 'public' ? 'Open conversation · anyone can join'
                : channel.kind === 'group' ? `Private group · ${members.length} members`
                    : 'Direct message · just the two of you';
            if (title)
                title.textContent = channel.name;
            if (subtitle)
                subtitle.textContent = subtitleText;
            if (avatar)
                avatar.textContent = channel.kind === 'public' ? '#' : channel.kind === 'group' ? '◉' : '↗';
            if (count)
                count.textContent = `${members.length} ${members.length === 1 ? 'person' : 'people'}`;
            if (membersList) {
                membersList.innerHTML = members.map((name, index) => `<span class="stage-member-chip"><span class="stage-member-avatar avatar-${index % 6}">${escapeHtml(initials(name))}</span>${escapeHtml(name)}</span>`).join('') || '<div class="stage-empty-note">No members listed.</div>';
            }
            this.renderMemberEditor(channel);
            const allowed = channel.kind === 'public' || members.includes(state.perspective);
            // Pause controls autonomous character turns. The phone owner can
            // still use the composer while those turns are paused.
            if (send)
                send.disabled = !allowed;
            if (input)
                input.disabled = !allowed;
        }
        static renderMemberEditor(channel) {
            const editor = document.getElementById('stage-member-editor');
            if (!editor)
                return;
            const state = window.StageChatState;
            if (channel.kind !== 'group' || channel.created_by !== state.perspective) {
                editor.innerHTML = '';
                return;
            }
            const available = Object.keys(state.participants || {})
                .filter((name) => !channel.members.includes(name));
            editor.innerHTML = `<div class="stage-member-edit-title">Manage members</div>
                <div class="stage-member-add-row"><select id="stage-member-to-add" class="stage-chat-select" ${available.length ? '' : 'disabled'}>
                    ${available.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')}
                </select><button type="button" class="stage-small-btn" data-member-action="add" ${available.length ? '' : 'disabled'}>Add</button></div>
                <div class="stage-member-remove-list">${channel.members.filter((name) => name !== channel.created_by).map((name) => `<button type="button" class="stage-remove-member" data-member-action="remove" data-name="${escapeHtml(name)}">Remove ${escapeHtml(name)}</button>`).join('')}</div>`;
        }
        static renderMessages() {
            const feed = document.getElementById('stage-chat-feed');
            if (!feed)
                return;
            const wasNearBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 90;
            const messages = window.StageChatState.messages || [];
            feed.innerHTML = messages.map((message) => {
                const own = message.author === window.StageChatState.perspective;
                const time = new Date(message.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `<article class="chat-msg ${own ? 'own' : ''}">
                    <div class="chat-msg-avatar avatar-${hash(message.author) % 6}">${escapeHtml(initials(message.author))}</div>
                    <div class="chat-msg-content"><div class="chat-msg-meta"><span class="chat-msg-author">${escapeHtml(message.author)}</span><time>${time}</time></div>
                    <div class="chat-msg-text">${escapeHtml(message.text)}</div></div>
                </article>`;
            }).join('') || `<div class="stage-feed-empty"><div class="stage-empty-orb">✳</div><h3>It starts here</h3><p>Send a note, ask a question, or let the conversation find its way.</p></div>`;
            if (wasNearBottom)
                feed.scrollTop = feed.scrollHeight;
        }
        static renderParticipants() {
            const list = document.getElementById('stage-participants-list');
            if (!list)
                return;
            const activeElement = document.activeElement;
            if (activeElement && list.contains(activeElement) && activeElement.matches('input'))
                return;
            const participants = window.StageChatState.participants || {};
            const names = Object.keys(participants).filter(name => name !== 'User');
            list.innerHTML = names.map(name => {
                const participant = participants[name];
                const pace = window.StageChatAgent.getTalkativeness(name);
                return `<div class="participant-item"><div class="participant-row">
                    <span class="participant-name">${escapeHtml(name)}</span>
                    <span class="participant-presence ${participant.active && !participant.blocked ? 'online' : ''}">${participant.blocked ? 'blocked' : participant.active ? 'active' : 'paused'}</span>
                </div><div class="participant-controls">
                    <label><input type="checkbox" data-character="${escapeHtml(name)}" data-role="active" ${participant.active ? 'checked' : ''}> In chat</label>
                    <label><input type="checkbox" data-character="${escapeHtml(name)}" data-role="blocked" ${participant.blocked ? 'checked' : ''}> Block</label>
                </div><div class="talkativeness-control"><div class="talkativeness-label"><span>Reply pace</span><span data-pace-for="${escapeHtml(name)}">${pace}s</span></div>
                    <input type="range" class="talkativeness-slider" min="5" max="120" value="${pace}" data-character="${escapeHtml(name)}" data-role="pace" aria-label="${escapeHtml(name)} reply cooldown"></div></div>`;
            }).join('');
        }
        static renderGroupRoster() {
            const roster = document.getElementById('stage-group-roster');
            const state = window.StageChatState;
            if (!roster)
                return;
            const names = Object.keys(state.participants || {}).filter((name) => name !== 'User' && name !== state.perspective);
            roster.innerHTML = names.map((name) => `<label class="stage-roster-option">
                <input type="checkbox" value="${escapeHtml(name)}"><span class="stage-member-avatar avatar-${hash(name) % 6}">${escapeHtml(initials(name))}</span><span>${escapeHtml(name)}</span></label>`).join('');
            const error = document.getElementById('stage-group-error');
            if (error)
                error.textContent = '';
        }
        static renderDmRecipients() {
            const select = document.getElementById('stage-dm-recipient');
            const state = window.StageChatState;
            if (!select)
                return;
            const names = Object.keys(state.participants || {}).filter((name) => name !== 'User' && name !== state.perspective);
            select.innerHTML = names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
            const error = document.getElementById('stage-dm-error');
            if (error)
                error.textContent = '';
        }
        static async createGroup(dialog) {
            const state = window.StageChatState;
            const name = document.getElementById('stage-group-name')?.value.trim() || '';
            const selected = [...document.querySelectorAll('#stage-group-roster input:checked')]
                .map((input) => input.value);
            try {
                const result = await window.StageChatApi.createChannel({
                    creator: state.perspective, kind: 'group', name,
                    members: [state.perspective, ...selected],
                });
                dialog?.close();
                await state.sync();
                await state.selectChannel(result.channel.id, false);
                document.getElementById('stage-group-form')?.reset();
            }
            catch (error) {
                const message = document.getElementById('stage-group-error');
                if (message)
                    message.textContent = error instanceof Error ? error.message : String(error);
            }
        }
        static async createDm(dialog) {
            const state = window.StageChatState;
            const recipient = document.getElementById('stage-dm-recipient')?.value || '';
            try {
                const result = await window.StageChatApi.createChannel({
                    creator: state.perspective, kind: 'dm', other: recipient,
                });
                dialog?.close();
                await state.sync();
                await state.selectChannel(result.channel.id, true);
            }
            catch (error) {
                const message = document.getElementById('stage-dm-error');
                if (message)
                    message.textContent = error instanceof Error ? error.message : String(error);
            }
        }
        static async changeMember(name, add) {
            const state = window.StageChatState;
            const channel = (state.channels || []).find((item) => item.id === state.selectedChannelId);
            if (!channel)
                return;
            try {
                await window.StageChatApi.updateMembers(channel.id, state.perspective, add ? [name] : [], add ? [] : [name]);
                await state.sync();
            }
            catch (error) {
                console.error('Could not update conversation membership:', error);
            }
        }
        static async toggleParticipant(name, change) {
            await window.StageChatApi.updateParticipant(name, change.active, change.blocked);
            const state = window.StageChatState;
            await state.sync();
            window.StageChatAgent.resetTimer(name);
        }
        static renderRateEstimate() {
            const estimate = document.getElementById('stage-rate-estimate');
            if (!estimate)
                return;
            const participants = window.StageChatState.participants || {};
            const active = Object.keys(participants).filter(name => name !== 'User' && participants[name].active && !participants[name].blocked);
            const perMinute = active.reduce((sum, name) => sum + 60 / window.StageChatAgent.getTalkativeness(name), 0);
            estimate.textContent = `${active.length} active · about ${perMinute.toFixed(1)} scheduled turns/min`;
        }
        static renderPauseState() {
            const state = window.StageChatState;
            const pause = document.getElementById('stage-pause-btn');
            const chip = document.getElementById('stage-status-chip');
            const step = document.getElementById('stage-step-btn');
            if (pause)
                pause.textContent = state.isPaused ? '▶ Resume' : '⏸ Pause';
            if (chip)
                chip.textContent = state.isPaused ? (state.visibilityPaused ? 'Paused · tab hidden' : 'Paused') : 'Active';
            if (step)
                step.disabled = state.isPaused;
        }
    }
    function escapeHtml(value) {
        return String(value || '').replace(/[&<>'"]/g, (tag) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
    }
    function initials(name) {
        const parts = String(name || '?').trim().split(/\s+/);
        return (parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : parts[0].slice(0, 2)).toUpperCase();
    }
    function hash(value) {
        return [...String(value || '')].reduce((total, character) => total + character.charCodeAt(0), 0);
    }
    window.StageChatUI = StageChatUI;
})();
