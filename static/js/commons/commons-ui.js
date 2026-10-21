"use strict";
/**
 * @module commons-ui - social conversation UI for The Commons
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
            const input = document.getElementById('commons-input');
            const participantList = document.getElementById('commons-participants-list');
            const channelList = document.getElementById('commons-channel-list');
            const perspective = document.getElementById('commons-perspective');
            const themeSelect = document.getElementById('commons-theme');
            const groupDialog = document.getElementById('commons-group-dialog');
            const dmDialog = document.getElementById('commons-dm-dialog');
            form?.addEventListener('submit', async (event) => {
                event.preventDefault();
                const text = input?.value.trim() || '';
                const state = window.CommonsState;
                if (!text || !state.selectedChannelId)
                    return;
                if (input)
                    input.value = '';
                try {
                    await window.CommonsApi.postMessage(state.perspective, text, state.selectedChannelId);
                    await state.sync();
                }
                catch (error) {
                    console.error('Failed to post message:', error);
                    if (input)
                        input.value = text;
                }
            });
            document.getElementById('commons-pause-btn')?.addEventListener('click', () => {
                const state = window.CommonsState;
                state.setPaused(!state.manualPaused, 'manual');
            });
            document.getElementById('commons-step-btn')?.addEventListener('click', () => {
                void window.CommonsAgent.stepOne();
            });
            perspective?.addEventListener('change', () => {
                void window.CommonsState.selectPerspective(perspective.value);
            });
            themeSelect?.addEventListener('change', async () => {
                const state = window.CommonsState;
                try {
                    await state.selectTheme(themeSelect.value);
                }
                catch (error) {
                    console.error('Failed to change Commons communication mode:', error);
                    themeSelect.value = state.theme;
                }
            });
            channelList?.addEventListener('click', (event) => {
                const button = event.target.closest('[data-channel-id]');
                if (button)
                    void window.CommonsState.selectChannel(button.dataset.channelId || '');
            });
            if (participantList) {
                participantList.addEventListener('click', (event) => {
                    const button = event.target.closest('[data-role="act"]');
                    const name = button?.dataset.character;
                    if (name) {
                        void window.CommonsAgent.stepOne(name);
                    }
                });
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
                        window.CommonsAgent.setTalkativeness(name, target.value, true);
                });
                participantList.addEventListener('input', (event) => {
                    const target = event.target;
                    const name = target?.dataset.character;
                    if (!target || target.dataset.role !== 'pace' || !name)
                        return;
                    window.CommonsAgent.setTalkativeness(name, target.value);
                    const output = participantList.querySelector(`[data-pace-for="${CSS.escape(name)}"]`);
                    if (output)
                        output.textContent = `${target.value}s`;
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
                const button = event.target.closest('[data-member-action]');
                if (!button)
                    return;
                if (button.dataset.memberAction === 'add') {
                    const select = document.getElementById('commons-member-to-add');
                    if (select?.value)
                        void this.changeMember(select.value, true);
                }
                if (button.dataset.memberAction === 'remove')
                    void this.changeMember(button.dataset.name || '', false);
            });
            document.getElementById('commons-drawer-close')?.addEventListener('click', () => {
                window.CommonsState.closeDrawer();
            });
            document.getElementById('commons-drawer-scrim')?.addEventListener('click', () => {
                window.CommonsState.closeDrawer();
            });
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && window.CommonsState.selectedDrawerCharacter) {
                    window.CommonsState.closeDrawer();
                }
            });
            document.addEventListener('click', (event) => {
                const trigger = event.target.closest('.commons-char-trigger');
                const charName = trigger?.dataset.character;
                if (charName && charName !== 'User') {
                    window.CommonsState.openDrawer(charName);
                }
            });
            window.CommonsState.subscribe(() => this.render());
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
            this.renderActorChip();
            void this.renderDrawer();
        }
        static renderTheme() {
            const state = window.CommonsState;
            const townBoard = state.theme === 'town_board';
            const themeSelect = document.getElementById('commons-theme');
            if (themeSelect)
                themeSelect.value = townBoard ? 'town_board' : 'live_social';
            const setText = (id, text) => {
                const element = document.getElementById(id);
                if (element)
                    element.textContent = text;
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
            const groupButton = document.getElementById('commons-new-group');
            if (groupButton)
                groupButton.hidden = townBoard;
            const dmButton = document.getElementById('commons-new-dm');
            if (dmButton)
                dmButton.textContent = townBoard ? '✉ Write a private letter' : '✉ New direct message';
            const perspective = document.getElementById('commons-perspective');
            if (perspective)
                perspective.setAttribute('aria-label', townBoard ? 'Read as character' : 'View conversations as');
        }
        static renderPerspective() {
            const select = document.getElementById('commons-perspective');
            if (!select)
                return;
            const state = window.CommonsState;
            const names = ['User', ...Object.keys(state.participants || {}).filter((name) => name !== 'User')];
            const signature = names.join('\0');
            if (select.dataset.signature !== signature) {
                select.innerHTML = names.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
                select.dataset.signature = signature;
            }
            select.value = state.perspective;
            const identity = document.getElementById('commons-composer-identity');
            if (identity)
                identity.textContent = state.perspective;
        }
        static renderChannels() {
            const list = document.getElementById('commons-channel-list');
            if (!list)
                return;
            const state = window.CommonsState;
            const channels = state.channels || [];
            list.innerHTML = channels.map((channel) => {
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
                    : `${(channel.members || []).filter((name) => name !== state.perspective).join(', ')}`;
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
            const state = window.CommonsState;
            const channel = (state.channels || []).find((item) => item.id === state.selectedChannelId);
            const title = document.getElementById('commons-channel-name');
            const subtitle = document.getElementById('commons-channel-subtitle');
            const avatar = document.getElementById('commons-channel-avatar');
            const count = document.getElementById('commons-channel-member-count');
            const membersList = document.getElementById('commons-channel-members');
            const editor = document.getElementById('commons-member-editor');
            const send = document.getElementById('commons-send-btn');
            const input = document.getElementById('commons-input');
            const townBoard = state.theme === 'town_board';
            const feed = document.getElementById('commons-feed');
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
                if (feed)
                    feed.setAttribute('aria-label', townBoard ? 'Posts and letters' : 'Messages');
                return;
            }
            const members = channel.kind === 'public'
                ? Object.keys(state.participants || {})
                : (channel.members || []);
            const subtitleText = channel.kind === 'public'
                ? (townBoard ? 'Public notice board · everyone can read and post' : 'Open conversation · anyone can join')
                : channel.kind === 'group' ? `Private group · ${members.length} members`
                    : (townBoard ? 'Private letters · just the two of you' : 'Direct message · just the two of you');
            if (title)
                title.textContent = townBoard && channel.kind === 'public' ? 'Town notice board' : channel.name;
            if (subtitle)
                subtitle.textContent = subtitleText;
            if (avatar)
                avatar.textContent = channel.kind === 'public'
                    ? (townBoard ? '▤' : '#')
                    : channel.kind === 'group' ? '◉' : (townBoard ? '✉' : '↗');
            if (count)
                count.textContent = `${members.length} ${members.length === 1 ? 'person' : 'people'}`;
            if (feed)
                feed.setAttribute('aria-label', townBoard
                    ? (channel.kind === 'public' ? 'Town-board posts' : 'Private letters')
                    : 'Messages');
            if (send)
                send.textContent = townBoard
                    ? (channel.kind === 'public' ? 'Post notice' : 'Send letter')
                    : 'Send';
            if (input)
                input.placeholder = townBoard
                    ? (channel.kind === 'public' ? 'Write a public notice…' : 'Write a private letter…')
                    : 'Write a message…';
            if (membersList) {
                membersList.innerHTML = members.map((name, index) => `<span class="commons-member-chip commons-char-trigger" data-character="${escapeHtml(name)}" title="Inspect ${escapeHtml(name)} inner world"><span class="commons-member-avatar avatar-${index % 6}">${escapeHtml(initials(name))}</span>${escapeHtml(name)}</span>`).join('') || '<div class="commons-empty-note">No members listed.</div>';
            }
            this.renderMemberEditor(channel);
            const allowed = channel.kind === 'public' || members.includes(state.perspective);
            // Pause controls autonomous character turns. The selected character can
            // still use the composer while those turns are paused.
            if (send)
                send.disabled = !allowed;
            if (input)
                input.disabled = !allowed;
        }
        static renderMemberEditor(channel) {
            const editor = document.getElementById('commons-member-editor');
            if (!editor)
                return;
            const state = window.CommonsState;
            if (channel.kind !== 'group' || channel.created_by !== state.perspective) {
                editor.innerHTML = '';
                return;
            }
            const available = Object.keys(state.participants || {})
                .filter((name) => !channel.members.includes(name));
            editor.innerHTML = `<div class="commons-member-edit-title">Manage members</div>
                <div class="commons-member-add-row"><select id="commons-member-to-add" class="commons-select" ${available.length ? '' : 'disabled'}>
                    ${available.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')}
                </select><button type="button" class="commons-small-btn" data-member-action="add" ${available.length ? '' : 'disabled'}>Add</button></div>
                <div class="commons-member-remove-list">${channel.members.filter((name) => name !== channel.created_by).map((name) => `<button type="button" class="commons-remove-member" data-member-action="remove" data-name="${escapeHtml(name)}">Remove ${escapeHtml(name)}</button>`).join('')}</div>`;
        }
        static renderMessages() {
            const feed = document.getElementById('commons-feed');
            if (!feed)
                return;
            const wasNearBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 90;
            const messages = window.CommonsState.messages || [];
            feed.innerHTML = messages.map((message) => {
                const own = message.author === window.CommonsState.perspective;
                const time = new Date(message.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `<article class="chat-msg ${own ? 'own' : ''}">
                    <div class="chat-msg-avatar avatar-${hash(message.author) % 6} commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(initials(message.author))}</div>
                    <div class="chat-msg-content"><div class="chat-msg-meta"><span class="chat-msg-author commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(message.author)}</span><time>${time}</time></div>
                    <div class="chat-msg-text">${escapeHtml(message.text)}</div></div>
                </article>`;
            }).join('') || (window.CommonsState.theme === 'town_board'
                ? `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Leave a notice or write a private letter.</p></div>`
                : `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Send a note, ask a question, or let the conversation find its way.</p></div>`);
            if (wasNearBottom)
                feed.scrollTop = feed.scrollHeight;
        }
        static renderParticipants() {
            const list = document.getElementById('commons-participants-list');
            if (!list)
                return;
            const activeElement = document.activeElement;
            if (activeElement && list.contains(activeElement) && activeElement.matches('input'))
                return;
            const participants = window.CommonsState.participants || {};
            const names = Object.keys(participants).filter(name => name !== 'User');
            list.innerHTML = names.map(name => {
                const participant = participants[name];
                const pace = window.CommonsAgent.getTalkativeness(name);
                const isActing = Boolean(window.CommonsAgent.controllers?.[name]);
                return `<div class="participant-item"><div class="participant-row">
                    <span class="participant-name commons-char-trigger" data-character="${escapeHtml(name)}" title="Inspect ${escapeHtml(name)} inner world">${escapeHtml(name)}</span>
                    <span class="participant-presence ${isActing ? 'thinking' : participant.active && !participant.blocked ? 'online' : ''}">${isActing ? 'thinking...' : participant.blocked ? 'blocked' : participant.active ? 'active' : 'paused'}</span>
                    <button type="button" class="commons-act-btn" data-character="${escapeHtml(name)}" data-role="act" title="Trigger a turn for ${escapeHtml(name)}" ${isActing || participant.blocked ? 'disabled' : ''}>▶ Act</button>
                </div><div class="participant-controls">
                    <label><input type="checkbox" data-character="${escapeHtml(name)}" data-role="active" ${participant.active ? 'checked' : ''}> In chat</label>
                    <label><input type="checkbox" data-character="${escapeHtml(name)}" data-role="blocked" ${participant.blocked ? 'checked' : ''}> Block</label>
                </div><div class="talkativeness-control"><div class="talkativeness-label"><span>Reply pace</span><span data-pace-for="${escapeHtml(name)}">${pace}s</span></div>
                    <input type="range" class="talkativeness-slider" min="5" max="120" value="${pace}" data-character="${escapeHtml(name)}" data-role="pace" aria-label="${escapeHtml(name)} reply cooldown"></div></div>`;
            }).join('');
        }
        static renderGroupRoster() {
            const roster = document.getElementById('commons-group-roster');
            const state = window.CommonsState;
            if (!roster)
                return;
            const names = Object.keys(state.participants || {}).filter((name) => name !== 'User' && name !== state.perspective);
            roster.innerHTML = names.map((name) => `<label class="commons-roster-option">
                <input type="checkbox" value="${escapeHtml(name)}"><span class="commons-member-avatar avatar-${hash(name) % 6}">${escapeHtml(initials(name))}</span><span>${escapeHtml(name)}</span></label>`).join('');
            const error = document.getElementById('commons-group-error');
            if (error)
                error.textContent = '';
        }
        static renderDmRecipients() {
            const select = document.getElementById('commons-dm-recipient');
            const state = window.CommonsState;
            if (!select)
                return;
            let eligibleNames = [];
            if (state.perspective === 'User') {
                eligibleNames = Object.keys(state.participants || {}).filter(name => name !== 'User');
            }
            else {
                const known = Array.isArray(state.knownCharacters) ? state.knownCharacters : [];
                eligibleNames = known.filter((name) => name !== 'User' && name !== state.perspective);
            }
            if (eligibleNames.length === 0) {
                select.innerHTML = '<option value="" disabled selected>No known characters to contact</option>';
            }
            else {
                select.innerHTML = eligibleNames.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
            }
            const error = document.getElementById('commons-dm-error');
            if (error)
                error.textContent = '';
        }
        static async createGroup(dialog) {
            if (window.CommonsState.theme === 'town_board')
                return;
            const state = window.CommonsState;
            const name = document.getElementById('commons-group-name')?.value.trim() || '';
            const selected = [...document.querySelectorAll('#commons-group-roster input:checked')]
                .map((input) => input.value);
            try {
                const result = await window.CommonsApi.createChannel({
                    creator: state.perspective, kind: 'group', name,
                    members: [state.perspective, ...selected],
                });
                dialog?.close();
                await state.sync();
                await state.selectChannel(result.channel.id, false);
                document.getElementById('commons-group-form')?.reset();
            }
            catch (error) {
                const message = document.getElementById('commons-group-error');
                if (message)
                    message.textContent = error instanceof Error ? error.message : String(error);
            }
        }
        static async createDm(dialog) {
            const state = window.CommonsState;
            const recipient = document.getElementById('commons-dm-recipient')?.value || '';
            try {
                const result = await window.CommonsApi.createChannel({
                    creator: state.perspective, kind: 'dm', other: recipient,
                });
                dialog?.close();
                await state.sync();
                await state.selectChannel(result.channel.id, true);
            }
            catch (error) {
                const message = document.getElementById('commons-dm-error');
                if (message)
                    message.textContent = error instanceof Error ? error.message : String(error);
            }
        }
        static async changeMember(name, add) {
            const state = window.CommonsState;
            const channel = (state.channels || []).find((item) => item.id === state.selectedChannelId);
            if (!channel)
                return;
            try {
                await window.CommonsApi.updateMembers(channel.id, state.perspective, add ? [name] : [], add ? [] : [name]);
                await state.sync();
            }
            catch (error) {
                console.error('Could not update conversation membership:', error);
            }
        }
        static async toggleParticipant(name, change) {
            await window.CommonsApi.updateParticipant(name, change.active, change.blocked);
            const state = window.CommonsState;
            await state.sync();
            window.CommonsAgent.resetTimer(name);
        }
        static renderRateEstimate() {
            const estimate = document.getElementById('commons-rate-estimate');
            if (!estimate)
                return;
            const participants = window.CommonsState.participants || {};
            const active = Object.keys(participants).filter(name => name !== 'User' && participants[name].active && !participants[name].blocked);
            const perMinute = active.reduce((sum, name) => sum + 60 / window.CommonsAgent.getTalkativeness(name), 0);
            estimate.textContent = `${active.length} active · about ${perMinute.toFixed(1)} scheduled turns/min`;
        }
        static renderPauseState() {
            const state = window.CommonsState;
            const pause = document.getElementById('commons-pause-btn');
            const chip = document.getElementById('commons-status-chip');
            const step = document.getElementById('commons-step-btn');
            if (pause)
                pause.textContent = state.isPaused ? '▶ Resume' : '⏸ Pause';
            const actingNames = Object.keys(window.CommonsAgent?.controllers || {});
            if (chip) {
                if (actingNames.length > 0) {
                    chip.textContent = `${actingNames[0]} thinking...`;
                    chip.className = 'commons-status thinking';
                }
                else if (state.isPaused) {
                    chip.textContent = state.visibilityPaused ? 'Paused · tab hidden' : 'Paused';
                    chip.className = 'commons-status paused';
                }
                else {
                    chip.textContent = 'Active';
                    chip.className = 'commons-status active';
                }
            }
            if (step)
                step.disabled = !state.isPaused || actingNames.length > 0;
        }
        static renderActorChip() {
            const chip = document.getElementById('commons-actor-chip');
            if (!chip)
                return;
            const state = window.CommonsState;
            const acting = state.actingCharacter;
            if (acting) {
                chip.textContent = `Acting: ${acting}...`;
                chip.className = 'commons-actor-chip acting';
            }
            else if (state.lastActed) {
                chip.textContent = `Last acted: ${state.lastActed.charName} (${state.lastActed.summary})`;
                chip.className = 'commons-actor-chip idle';
            }
            else {
                chip.textContent = 'Idle';
                chip.className = 'commons-actor-chip idle';
            }
        }
        static async renderDrawer() {
            const drawer = document.getElementById('commons-inner-drawer');
            const scrim = document.getElementById('commons-drawer-scrim');
            if (!drawer || !scrim)
                return;
            const state = window.CommonsState;
            const charName = state.selectedDrawerCharacter;
            if (!charName) {
                drawer.hidden = true;
                scrim.hidden = true;
                return;
            }
            drawer.hidden = false;
            scrim.hidden = false;
            const nameEl = document.getElementById('commons-drawer-name');
            const presenceEl = document.getElementById('commons-drawer-presence');
            const avatarEl = document.getElementById('commons-drawer-avatar');
            const personalityEl = document.getElementById('commons-drawer-personality');
            const traitsEl = document.getElementById('commons-drawer-traits');
            const monologueEl = document.getElementById('commons-drawer-monologue');
            const decisionEl = document.getElementById('commons-drawer-decision');
            const historyEl = document.getElementById('commons-drawer-history');
            if (nameEl)
                nameEl.textContent = charName;
            if (avatarEl) {
                avatarEl.textContent = initials(charName);
                avatarEl.className = `commons-drawer-avatar avatar-${hash(charName) % 6}`;
            }
            const isActing = Boolean(window.CommonsAgent?.controllers?.[charName]);
            if (presenceEl) {
                presenceEl.textContent = isActing ? 'Thinking right now...' : 'In conversation';
                presenceEl.className = `commons-drawer-presence ${isActing ? 'thinking' : 'active'}`;
            }
            // Fetch or get context
            let context = state.characterContextCache?.[charName];
            if (!context && window.CommonsApi?.getCharacterContext) {
                try {
                    context = await window.CommonsApi.getCharacterContext(charName);
                    state.characterContextCache[charName] = context;
                }
                catch (e) { }
            }
            if (personalityEl) {
                personalityEl.textContent = context?.personality || context?.description || 'No personality profile recorded.';
            }
            if (traitsEl) {
                const traitKeys = Object.keys(context?.traits || {}).filter(k => context.traits[k]);
                traitsEl.innerHTML = traitKeys.map((t) => `<span class="commons-trait-badge">${escapeHtml(t)}</span>`).join('');
            }
            // Render turn history and monologue
            const turns = state.characterTurns?.[charName] || [];
            const latest = turns[0];
            if (monologueEl) {
                if (latest?.inner) {
                    monologueEl.innerHTML = `<blockquote class="commons-inner-quote">"${escapeHtml(latest.inner)}"</blockquote>
                    <div class="commons-inner-time">${new Date(latest.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</div>`;
                }
                else {
                    monologueEl.innerHTML = `<div class="commons-drawer-empty-state">No thoughts recorded yet for ${escapeHtml(charName)}. Trigger a turn with ▶ Act to observe their inner stream.</div>`;
                }
            }
            if (decisionEl) {
                if (latest) {
                    decisionEl.innerHTML = `<div class="commons-decision-card">
                        <div class="commons-decision-header">
                            <span class="commons-decision-action ${escapeHtml(latest.action)}">${escapeHtml(latest.action.replace('_', ' '))}</span>
                            <span class="commons-decision-summary">${escapeHtml(latest.summary)}</span>
                        </div>
                        ${latest.detail?.text ? `<div class="commons-decision-text">"${escapeHtml(latest.detail.text)}"</div>` : ''}
                    </div>`;
                }
                else {
                    decisionEl.innerHTML = `<div class="commons-drawer-empty-state">No recent decisions.</div>`;
                }
            }
            if (historyEl) {
                if (turns.length > 1) {
                    historyEl.innerHTML = turns.slice(1, 8).map((t) => `
                        <div class="commons-history-row">
                            <div class="commons-history-header">
                                <span class="commons-decision-action small ${escapeHtml(t.action)}">${escapeHtml(t.action.replace('_', ' '))}</span>
                                <time>${new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
                            </div>
                            ${t.inner ? `<div class="commons-history-thought">"${escapeHtml(t.inner)}"</div>` : ''}
                        </div>
                    `).join('');
                }
                else {
                    historyEl.innerHTML = `<div class="commons-drawer-empty-state">Earlier turns will appear here as the conversation continues.</div>`;
                }
            }
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
    window.CommonsUI = CommonsUI;
})();
