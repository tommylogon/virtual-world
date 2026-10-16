/**
 * @module commons-ui — social conversation UI for The Commons
 * @contributes conversation list, messages, membership controls, and inputs
 * @powers The Commons phone/social surface
 * @relates CommonsState, CommonsApi, CommonsAgent
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */

(function () {
    'use strict';

    class CommonsUI {
        static init() {
            const form = document.getElementById('commons-form');
            const input = document.getElementById('commons-input') as HTMLInputElement | null;
            const participantList = document.getElementById('commons-participants-list');
            const channelList = document.getElementById('commons-channel-list');
            const perspective = document.getElementById('commons-perspective') as HTMLSelectElement | null;
            const themeSelect = document.getElementById('commons-theme') as HTMLSelectElement | null;
            const groupDialog = document.getElementById('commons-group-dialog') as HTMLDialogElement | null;
            const dmDialog = document.getElementById('commons-dm-dialog') as HTMLDialogElement | null;

            form?.addEventListener('submit', async (event) => {
                event.preventDefault();
                const text = input?.value.trim() || '';
                const state = (window as any).CommonsState;
                if (!text || !state.selectedChannelId) return;
                if (input) input.value = '';
                try {
                    await (window as any).CommonsApi.postMessage(
                        state.perspective, text, state.selectedChannelId
                    );
                    await state.sync();
                } catch (error) {
                    console.error('Failed to post message:', error);
                    if (input) input.value = text;
                }
            });

            document.getElementById('commons-pause-btn')?.addEventListener('click', () => {
                const state = (window as any).CommonsState;
                state.setPaused(!state.manualPaused, 'manual');
            });
            document.getElementById('commons-step-btn')?.addEventListener('click', () => {
                void (window as any).CommonsAgent.stepOne();
            });

            perspective?.addEventListener('change', () => {
                void (window as any).CommonsState.selectPerspective(perspective.value);
            });
            themeSelect?.addEventListener('change', async () => {
                const state = (window as any).CommonsState;
                try {
                    await state.selectTheme(themeSelect.value);
                } catch (error) {
                    console.error('Failed to change Commons communication mode:', error);
                    themeSelect.value = state.theme;
                }
            });
            channelList?.addEventListener('click', (event) => {
                const button = (event.target as HTMLElement).closest<HTMLButtonElement>('[data-channel-id]');
                if (button) void (window as any).CommonsState.selectChannel(button.dataset.channelId || '');
            });

            if (participantList) {
                participantList.addEventListener('change', (event: Event) => {
                    const target = event.target as HTMLInputElement | null;
                    const name = target?.dataset.character;
                    if (!target || !name) return;
                    if (target.dataset.role === 'active') void this.toggleParticipant(name, { active: target.checked });
                    if (target.dataset.role === 'blocked') void this.toggleParticipant(name, { blocked: target.checked });
                    if (target.dataset.role === 'pace') (window as any).CommonsAgent.setTalkativeness(name, target.value, true);
                });
                participantList.addEventListener('input', (event: Event) => {
                    const target = event.target as HTMLInputElement | null;
                    const name = target?.dataset.character;
                    if (!target || target.dataset.role !== 'pace' || !name) return;
                    (window as any).CommonsAgent.setTalkativeness(name, target.value);
                    const output = participantList.querySelector(`[data-pace-for="${CSS.escape(name)}"]`);
                    if (output) output.textContent = `${target.value}s`;
                    this.renderRateEstimate();
                });
                participantList.addEventListener('focusout', () => this.renderParticipants());
            }

            document.getElementById('commons-new-group')?.addEventListener('click', () => {
                this.renderGroupRoster();
                groupDialog?.showModal();
            });
            document.getElementById('commons-group-close')?.addEventListener('click', () => groupDialog?.close());
            document.getElementById('commons-group-cancel')?.addEventListener('click', () => groupDialog?.close());
            document.getElementById('commons-group-form')?.addEventListener('submit', (event) => {
                event.preventDefault();
                void this.createGroup(groupDialog);
            });

            document.getElementById('commons-new-dm')?.addEventListener('click', () => {
                this.renderDmRecipients();
                dmDialog?.showModal();
            });
            document.getElementById('commons-dm-close')?.addEventListener('click', () => dmDialog?.close());
            document.getElementById('commons-dm-cancel')?.addEventListener('click', () => dmDialog?.close());
            document.getElementById('commons-dm-form')?.addEventListener('submit', (event) => {
                event.preventDefault();
                void this.createDm(dmDialog);
            });

            document.getElementById('commons-member-editor')?.addEventListener('click', (event) => {
                const button = (event.target as HTMLElement).closest<HTMLButtonElement>('[data-member-action]');
                if (!button) return;
                if (button.dataset.memberAction === 'add') {
                    const select = document.getElementById('commons-member-to-add') as HTMLSelectElement | null;
                    if (select?.value) void this.changeMember(select.value, true);
                }
                if (button.dataset.memberAction === 'remove') void this.changeMember(button.dataset.name || '', false);
            });

            (window as any).CommonsState.subscribe(() => this.render());
        }

        static render() {
            this.renderTheme();
            this.renderPerspective();
            this.renderChannels();
            this.renderConversation();
            this.renderMessages();
            this.renderParticipants();
            this.renderRateEstimate();
            this.renderPauseState();
        }

        static renderTheme() {
            const state = (window as any).CommonsState;
            const townBoard = state.theme === 'town_board';
            const themeSelect = document.getElementById('commons-theme') as HTMLSelectElement | null;
            if (themeSelect) themeSelect.value = townBoard ? 'town_board' : 'live_social';
            const setText = (id: string, text: string) => {
                const element = document.getElementById(id);
                if (element) element.textContent = text;
            };
            setText('commons-brand-sub', townBoard ? 'town board & private letters' : 'a place to talk');
            setText('commons-perspective-label', townBoard ? 'Reading as' : 'Phone owner');
            setText('commons-inbox-eyebrow', townBoard ? 'TOWN BOARD' : 'INBOX');
            setText('commons-inbox-heading', townBoard ? 'Posts & letters' : 'Conversations');
            setText('commons-composer-verb', townBoard ? 'Write as' : 'Message as');
            setText('commons-dm-eyebrow', townBoard ? 'PRIVATE LETTER' : 'ONE TO ONE');
            setText('commons-dm-heading', townBoard ? 'Write a private letter' : 'Start a direct message');
            setText('commons-dm-recipient-label', townBoard ? 'Choose a recipient' : 'Choose a character');
            setText('commons-dm-submit', townBoard ? 'Open letter' : 'Open conversation');
            setText('commons-details-note', townBoard
                ? 'Private letters are visible only to their two writers.'
                : 'Private conversations are visible only from a member’s phone.');
            const groupButton = document.getElementById('commons-new-group') as HTMLButtonElement | null;
            if (groupButton) groupButton.hidden = townBoard;
            const dmButton = document.getElementById('commons-new-dm');
            if (dmButton) dmButton.textContent = townBoard ? '✉ Write a private letter' : '✉ New direct message';
            const perspective = document.getElementById('commons-perspective');
            if (perspective) perspective.setAttribute('aria-label', townBoard ? 'Read as character' : 'View conversations as');
        }

        static renderPerspective() {
            const select = document.getElementById('commons-perspective') as HTMLSelectElement | null;
            if (!select) return;
            const state = (window as any).CommonsState;
            const names = ['User', ...Object.keys(state.participants || {}).filter((name: string) => name !== 'User')];
            const signature = names.join('\0');
            if (select.dataset.signature !== signature) {
                select.innerHTML = names.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
                select.dataset.signature = signature;
            }
            select.value = state.perspective;
            const identity = document.getElementById('commons-composer-identity');
            if (identity) identity.textContent = state.perspective;
        }

        static renderChannels() {
            const list = document.getElementById('commons-channel-list');
            if (!list) return;
            const state = (window as any).CommonsState;
            const channels = state.channels || [];
            list.innerHTML = channels.map((channel: any) => {
                const townBoard = state.theme === 'town_board';
                const icon = channel.kind === 'public'
                    ? (townBoard ? '▤' : '#')
                    : channel.kind === 'group' ? '◉' : (townBoard ? '✉' : '↗');
                const unread = Number(channel.unread_count || 0);
                const channelLabel = townBoard
                    ? (channel.kind === 'public' ? 'Town board' : channel.name)
                    : channel.name;
                const people = channel.kind === 'public'
                    ? (townBoard ? 'Public notices' : 'Open conversation')
                    : `${(channel.members || []).filter((name: string) => name !== state.perspective).join(', ')}`;
                const unreadLabel = channel.kind === 'public' && townBoard ? 'new posts'
                    : channel.kind === 'dm' && townBoard ? 'new letters' : 'unread';
                return `<button type="button" class="commons-channel-row ${channel.id === state.selectedChannelId ? 'selected' : ''}"
                    data-channel-id="${escapeHtml(channel.id)}" aria-current="${channel.id === state.selectedChannelId ? 'true' : 'false'}"
                    aria-label="${escapeHtml(`${channelLabel}${unread ? `, ${unread} ${unreadLabel}` : ''}`)}">
                    <span class="commons-channel-icon ${escapeHtml(channel.kind)}">${icon}</span>
                    <span class="commons-channel-copy"><span class="commons-channel-name">${escapeHtml(channelLabel)}</span>
                    <span class="commons-channel-preview">${escapeHtml(people || channel.kind)}</span></span>
                    ${unread ? `<span class="commons-unread-badge">${unread > 99 ? '99+' : unread}</span>` : ''}
                </button>`;
            }).join('') || '<div class="commons-empty-note">No conversations yet.</div>';
        }

        static renderConversation() {
            const state = (window as any).CommonsState;
            const channel = (state.channels || []).find((item: any) => item.id === state.selectedChannelId);
            const title = document.getElementById('commons-channel-name');
            const subtitle = document.getElementById('commons-channel-subtitle');
            const avatar = document.getElementById('commons-channel-avatar');
            const count = document.getElementById('commons-channel-member-count');
            const membersList = document.getElementById('commons-channel-members');
            const editor = document.getElementById('commons-member-editor');
            const send = document.getElementById('commons-send-btn') as HTMLButtonElement | null;
            const input = document.getElementById('commons-input') as HTMLInputElement | null;
            const townBoard = state.theme === 'town_board';
            const feed = document.getElementById('commons-feed');
            if (!channel) {
                if (title) title.textContent = 'No conversation selected';
                if (subtitle) subtitle.textContent = 'Choose a conversation to open your inbox.';
                if (avatar) avatar.textContent = '·';
                if (count) count.textContent = '';
                if (membersList) membersList.innerHTML = '';
                if (editor) editor.innerHTML = '';
                if (send) send.disabled = true;
                if (input) input.disabled = true;
                if (feed) feed.setAttribute('aria-label', townBoard ? 'Posts and letters' : 'Messages');
                return;
            }
            const members = channel.kind === 'public'
                ? Object.keys(state.participants || {})
                : (channel.members || []);
            const subtitleText = channel.kind === 'public'
                ? (townBoard ? 'Public notice board · everyone can read and post' : 'Open conversation · anyone can join')
                : channel.kind === 'group' ? `Private group · ${members.length} members`
                    : (townBoard ? 'Private letters · just the two of you' : 'Direct message · just the two of you');
            if (title) title.textContent = townBoard && channel.kind === 'public' ? 'Town notice board' : channel.name;
            if (subtitle) subtitle.textContent = subtitleText;
            if (avatar) avatar.textContent = channel.kind === 'public'
                ? (townBoard ? '▤' : '#')
                : channel.kind === 'group' ? '◉' : (townBoard ? '✉' : '↗');
            if (count) count.textContent = `${members.length} ${members.length === 1 ? 'person' : 'people'}`;
            if (feed) feed.setAttribute('aria-label', townBoard
                ? (channel.kind === 'public' ? 'Town-board posts' : 'Private letters')
                : 'Messages');
            if (send) send.textContent = townBoard
                ? (channel.kind === 'public' ? 'Post notice' : 'Send letter')
                : 'Send';
            if (input) input.placeholder = townBoard
                ? (channel.kind === 'public' ? 'Write a public notice…' : 'Write a private letter…')
                : 'Write a message…';
            if (membersList) {
                membersList.innerHTML = members.map((name: string, index: number) =>
                    `<span class="commons-member-chip"><span class="commons-member-avatar avatar-${index % 6}">${escapeHtml(initials(name))}</span>${escapeHtml(name)}</span>`
                ).join('') || '<div class="commons-empty-note">No members listed.</div>';
            }
            this.renderMemberEditor(channel);
            const allowed = channel.kind === 'public' || members.includes(state.perspective);
            // Pause controls autonomous character turns. The selected character can
            // still use the composer while those turns are paused.
            if (send) send.disabled = !allowed;
            if (input) input.disabled = !allowed;
        }

        static renderMemberEditor(channel: any) {
            const editor = document.getElementById('commons-member-editor');
            if (!editor) return;
            const state = (window as any).CommonsState;
            if (channel.kind !== 'group' || channel.created_by !== state.perspective) {
                editor.innerHTML = '';
                return;
            }
            const available = Object.keys(state.participants || {})
                .filter((name: string) => !channel.members.includes(name));
            editor.innerHTML = `<div class="commons-member-edit-title">Manage members</div>
                <div class="commons-member-add-row"><select id="commons-member-to-add" class="commons-select" ${available.length ? '' : 'disabled'}>
                    ${available.map((name: string) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')}
                </select><button type="button" class="commons-small-btn" data-member-action="add" ${available.length ? '' : 'disabled'}>Add</button></div>
                <div class="commons-member-remove-list">${channel.members.filter((name: string) => name !== channel.created_by).map((name: string) =>
                    `<button type="button" class="commons-remove-member" data-member-action="remove" data-name="${escapeHtml(name)}">Remove ${escapeHtml(name)}</button>`
                ).join('')}</div>`;
        }

        static renderMessages() {
            const feed = document.getElementById('commons-feed');
            if (!feed) return;
            const wasNearBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 90;
            const messages = (window as any).CommonsState.messages || [];
            feed.innerHTML = messages.map((message: any) => {
                const own = message.author === (window as any).CommonsState.perspective;
                const time = new Date(message.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `<article class="chat-msg ${own ? 'own' : ''}">
                    <div class="chat-msg-avatar avatar-${hash(message.author) % 6}">${escapeHtml(initials(message.author))}</div>
                    <div class="chat-msg-content"><div class="chat-msg-meta"><span class="chat-msg-author">${escapeHtml(message.author)}</span><time>${time}</time></div>
                    <div class="chat-msg-text">${escapeHtml(message.text)}</div></div>
                </article>`;
            }).join('') || ((window as any).CommonsState.theme === 'town_board'
                ? `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Leave a notice or write a private letter.</p></div>`
                : `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Send a note, ask a question, or let the conversation find its way.</p></div>`);
            if (wasNearBottom) feed.scrollTop = feed.scrollHeight;
        }

        static renderParticipants() {
            const list = document.getElementById('commons-participants-list');
            if (!list) return;
            const activeElement = document.activeElement as HTMLElement | null;
            if (activeElement && list.contains(activeElement) && activeElement.matches('input')) return;
            const participants = (window as any).CommonsState.participants || {};
            const names = Object.keys(participants).filter(name => name !== 'User');
            list.innerHTML = names.map(name => {
                const participant = participants[name];
                const pace = (window as any).CommonsAgent.getTalkativeness(name);
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
            const roster = document.getElementById('commons-group-roster');
            const state = (window as any).CommonsState;
            if (!roster) return;
            const names = Object.keys(state.participants || {}).filter((name: string) => name !== 'User' && name !== state.perspective);
            roster.innerHTML = names.map((name: string) => `<label class="commons-roster-option">
                <input type="checkbox" value="${escapeHtml(name)}"><span class="commons-member-avatar avatar-${hash(name) % 6}">${escapeHtml(initials(name))}</span><span>${escapeHtml(name)}</span></label>`).join('');
            const error = document.getElementById('commons-group-error');
            if (error) error.textContent = '';
        }

        static renderDmRecipients() {
            const select = document.getElementById('commons-dm-recipient') as HTMLSelectElement | null;
            const state = (window as any).CommonsState;
            if (!select) return;
            const names = Object.keys(state.participants || {}).filter((name: string) => name !== 'User' && name !== state.perspective);
            select.innerHTML = names.map((name: string) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
            const error = document.getElementById('commons-dm-error');
            if (error) error.textContent = '';
        }

        static async createGroup(dialog: HTMLDialogElement | null) {
            if ((window as any).CommonsState.theme === 'town_board') return;
            const state = (window as any).CommonsState;
            const name = (document.getElementById('commons-group-name') as HTMLInputElement | null)?.value.trim() || '';
            const selected = [...(document.querySelectorAll('#commons-group-roster input:checked') as NodeListOf<HTMLInputElement>)]
                .map((input) => input.value);
            try {
                const result = await (window as any).CommonsApi.createChannel({
                    creator: state.perspective, kind: 'group', name,
                    members: [state.perspective, ...selected],
                });
                dialog?.close();
                await state.sync();
                await state.selectChannel(result.channel.id, false);
                (document.getElementById('commons-group-form') as HTMLFormElement | null)?.reset();
            } catch (error) {
                const message = document.getElementById('commons-group-error');
                if (message) message.textContent = error instanceof Error ? error.message : String(error);
            }
        }

        static async createDm(dialog: HTMLDialogElement | null) {
            const state = (window as any).CommonsState;
            const recipient = (document.getElementById('commons-dm-recipient') as HTMLSelectElement | null)?.value || '';
            try {
                const result = await (window as any).CommonsApi.createChannel({
                    creator: state.perspective, kind: 'dm', other: recipient,
                });
                dialog?.close();
                await state.sync();
                await state.selectChannel(result.channel.id, true);
            } catch (error) {
                const message = document.getElementById('commons-dm-error');
                if (message) message.textContent = error instanceof Error ? error.message : String(error);
            }
        }

        static async changeMember(name: string, add: boolean) {
            const state = (window as any).CommonsState;
            const channel = (state.channels || []).find((item: any) => item.id === state.selectedChannelId);
            if (!channel) return;
            try {
                await (window as any).CommonsApi.updateMembers(
                    channel.id, state.perspective, add ? [name] : [], add ? [] : [name]
                );
                await state.sync();
            } catch (error) {
                console.error('Could not update conversation membership:', error);
            }
        }

        static async toggleParticipant(name: string, change: { active?: boolean; blocked?: boolean }) {
            await (window as any).CommonsApi.updateParticipant(name, change.active, change.blocked);
            const state = (window as any).CommonsState;
            await state.sync();
            (window as any).CommonsAgent.resetTimer(name);
        }

        static renderRateEstimate() {
            const estimate = document.getElementById('commons-rate-estimate');
            if (!estimate) return;
            const participants = (window as any).CommonsState.participants || {};
            const active = Object.keys(participants).filter(name => name !== 'User' && participants[name].active && !participants[name].blocked);
            const perMinute = active.reduce((sum, name) => sum + 60 / (window as any).CommonsAgent.getTalkativeness(name), 0);
            estimate.textContent = `${active.length} active · about ${perMinute.toFixed(1)} scheduled turns/min`;
        }

        static renderPauseState() {
            const state = (window as any).CommonsState;
            const pause = document.getElementById('commons-pause-btn');
            const chip = document.getElementById('commons-status-chip');
            const step = document.getElementById('commons-step-btn') as HTMLButtonElement | null;
            if (pause) pause.textContent = state.isPaused ? '▶ Resume' : '⏸ Pause';
            if (chip) chip.textContent = state.isPaused ? (state.visibilityPaused ? 'Paused · tab hidden' : 'Paused') : 'Active';
            if (step) step.disabled = state.isPaused;
        }
    }

    function escapeHtml(value: unknown): string {
        return String(value || '').replace(/[&<>'"]/g,
            (tag: string) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
    }
    function initials(name: string): string {
        const parts = String(name || '?').trim().split(/\s+/);
        return (parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : parts[0].slice(0, 2)).toUpperCase();
    }
    function hash(value: string): number {
        return [...String(value || '')].reduce((total, character) => total + character.charCodeAt(0), 0);
    }

    (window as any).CommonsUI = CommonsUI;
})();
