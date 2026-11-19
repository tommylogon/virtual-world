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
            const autoReplyCb = document.getElementById('commons-auto-reply-toggle');
            if (autoReplyCb) {
                const cfg = window.config;
                if (cfg) {
                    void cfg._initPromise?.then(() => {
                        autoReplyCb.checked = Boolean(cfg.commonsAutoReplyOnMessage);
                    });
                    autoReplyCb.checked = Boolean(cfg.commonsAutoReplyOnMessage);
                }
                autoReplyCb.addEventListener('change', () => {
                    const c = window.config;
                    if (c) {
                        c.commonsAutoReplyOnMessage = autoReplyCb.checked;
                        void c.save?.();
                    }
                });
            }
            const advClockCb = document.getElementById('commons-advance-clock-toggle');
            if (advClockCb) {
                const cfg = window.config;
                if (cfg) {
                    void cfg._initPromise?.then(() => {
                        advClockCb.checked = Boolean(cfg.commonsAdvanceClockOnReply);
                    });
                    advClockCb.checked = Boolean(cfg.commonsAdvanceClockOnReply);
                }
                advClockCb.addEventListener('change', () => {
                    const c = window.config;
                    if (c) {
                        c.commonsAdvanceClockOnReply = advClockCb.checked;
                        void c.save?.();
                    }
                });
            }
            const memCfg = window.config;
            if (memCfg) {
                void memCfg._initPromise?.then(() => {
                    this.renderMemoryToggle();
                    if (window.CommonsState)
                        this.renderConversation();
                });
            }
            this.renderMemoryToggle();
            form?.addEventListener('submit', async (event) => {
                event.preventDefault();
                const text = input?.value.trim() || '';
                const state = window.CommonsState;
                const attachments = [...this.pendingAttachments];
                if ((!text && !attachments.length) || !state.selectedChannelId)
                    return;
                if (input)
                    input.value = '';
                this.pendingAttachments = [];
                this.renderAttachmentPreviews();
                try {
                    const result = await window.CommonsApi.postMessage(state.perspective, text, state.selectedChannelId, attachments);
                    state.receiveMessage(result.message);
                    const cfg = window.config;
                    if (cfg?.commonsAutoReplyOnMessage) {
                        const channel = (state.channels || []).find((item) => item.id === state.selectedChannelId);
                        if (channel)
                            void window.CommonsAgent?.triggerAutoReplyForChannel?.(channel, state.perspective);
                    }
                }
                catch (error) {
                    console.error('Failed to post message:', error);
                    if (input)
                        input.value = text;
                    this.pendingAttachments = attachments;
                    this.renderAttachmentPreviews();
                }
            });
            document.getElementById('commons-attach-btn')?.addEventListener('click', () => {
                document.getElementById('commons-file-input')?.click();
            });
            document.getElementById('commons-file-input')?.addEventListener('change', async (event) => {
                const fileInput = event.target;
                const file = fileInput.files?.[0];
                if (!file)
                    return;
                try {
                    const caption = window.prompt('Attachment caption (optional):') || '';
                    const uploaded = await window.CommonsApi.uploadAttachment(file, caption);
                    this.pendingAttachments.push(uploaded);
                    this.renderAttachmentPreviews();
                }
                catch (err) {
                    console.error('Upload failed:', err);
                    alert('Failed to upload attachment: ' + String(err));
                }
                finally {
                    fileInput.value = '';
                }
            });
            document.getElementById('commons-composer-previews')?.addEventListener('click', (event) => {
                const btn = event.target?.closest('.commons-composer-preview-remove');
                if (!btn)
                    return;
                const idx = Number(btn.dataset.index);
                if (!isNaN(idx)) {
                    this.pendingAttachments.splice(idx, 1);
                    this.renderAttachmentPreviews();
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
                    const target = event.target;
                    const randomButton = target.closest('[data-role="pace-random"]');
                    const name = randomButton?.dataset.character;
                    if (name) {
                        const pace = window.CommonsAgent.randomizeTalkativeness(name, true);
                        const slider = participantList.querySelector(`input[data-role="pace"][data-character="${CSS.escape(name)}"]`);
                        if (slider)
                            slider.value = String(pace);
                        const output = participantList.querySelector(`[data-pace-for="${CSS.escape(name)}"]`);
                        if (output)
                            output.textContent = `${pace}s`;
                        this.renderRateEstimate();
                        return;
                    }
                    const button = target.closest('[data-role="act"]');
                    const actName = button?.dataset.character;
                    if (actName) {
                        void window.CommonsAgent.stepOne(actName, true);
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
            document.getElementById('commons-viwo-state-toggle')?.addEventListener('change', async (e) => {
                const checked = Boolean(e.target.checked);
                await window.CommonsApi?.setMode?.(checked);
                await window.CommonsState?.sync?.(true);
            });
            document.getElementById('commons-clock-set-btn')?.addEventListener('click', async () => {
                const dateEl = document.getElementById('commons-clock-date');
                const timeEl = document.getElementById('commons-clock-time');
                if (!dateEl?.value && !timeEl?.value)
                    return;
                await window.CommonsApi?.setClock?.(dateEl?.value, timeEl?.value);
                await window.CommonsState?.sync?.(true);
            });
            document.getElementById('commons-branch-select')?.addEventListener('change', async (e) => {
                const bid = e.target.value;
                if (!bid)
                    return;
                await window.CommonsApi?.switchBranch?.(bid);
                await window.CommonsState?.sync?.(true);
            });
            document.getElementById('commons-branch-fork-btn')?.addEventListener('click', async () => {
                const name = window.prompt('New branch name (optional):', '') ?? undefined;
                if (name === null)
                    return;
                await window.CommonsApi?.forkBranch?.(name || undefined);
                await window.CommonsState?.sync?.(true);
            });
            document.getElementById('commons-reset-btn')?.addEventListener('click', async () => {
                if (!window.confirm('Reset this standalone Commons session (clears messages and custom groups)?'))
                    return;
                await window.CommonsApi?.resetSession?.(false);
                await window.CommonsState?.sync?.(true);
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
            document.getElementById('commons-feed')?.addEventListener('click', (event) => {
                const target = event.target;
                const editBtn = target.closest('.commons-msg-edit');
                if (editBtn) {
                    const msgId = Number(editBtn.dataset.msgId);
                    if (msgId) {
                        this.editingMessageId = msgId;
                        this.renderMessages();
                    }
                    return;
                }
                const saveBtn = target.closest('.commons-save-edit');
                if (saveBtn) {
                    const msgId = Number(saveBtn.dataset.msgId);
                    const container = saveBtn.closest('.chat-msg-edit-inline');
                    const input = container?.querySelector('.commons-edit-input');
                    const newText = (input?.value || '').trim();
                    if (msgId && newText) {
                        void this.saveMessageEdit(msgId, newText);
                    }
                    return;
                }
                const cancelBtn = target.closest('.commons-cancel-edit');
                if (cancelBtn) {
                    this.editingMessageId = null;
                    this.renderMessages();
                    return;
                }
                const deleteBtn = target.closest('.commons-msg-delete');
                if (deleteBtn) {
                    const msgId = Number(deleteBtn.dataset.msgId);
                    if (msgId) {
                        void this.confirmDeleteMessage(msgId);
                    }
                    return;
                }
                if (target.closest('button, a, input, textarea, .commons-msg-actions, .chat-msg-edit-inline'))
                    return;
                const selectedText = window.getSelection?.()?.toString?.() || '';
                if (selectedText.length > 0)
                    return;
                const msgEl = target.closest('article.chat-msg[data-msg-id]');
                const author = msgEl?.dataset.author;
                const msgId = msgEl?.dataset.msgId;
                if (msgEl && author && author !== 'User' && msgId) {
                    window.CommonsState.openDrawerForMessage(author, msgId);
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
            setText('commons-composer-action', townBoard ? 'Write as' : 'Message as');
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
                select.replaceChildren(document.createRange().createContextualFragment(names.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')));
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
            list.replaceChildren(document.createRange().createContextualFragment(channels.map((channel) => {
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
                    aria-label="${escapeHtml(`${channelLabel}${channel.muted ? ', muted' : ''}${unread ? `, ${unread} ${unreadLabel}` : ''}`)}">
                    <span class="commons-channel-icon ${escapeHtml(channel.kind)}">${icon}</span>
                    <span class="commons-channel-copy"><span class="commons-channel-name">${escapeHtml(channelLabel)}${channel.muted ? ' <span class="commons-muted-badge" style="font-size:10px;opacity:0.75;">[muted]</span>' : ''}</span>
                    <span class="commons-channel-preview">${escapeHtml(people || channel.kind)}</span></span>
                    ${unread ? `<span class="commons-unread-badge">${unread > 99 ? '99+' : unread}</span>` : ''}
                </button>`;
            }).join('') || '<div class="commons-empty-note">No conversations yet.</div>'));
        }
        static isMemoryRecordingEnabled() {
            const cfg = window.config;
            return cfg ? cfg.commonsRecordMemories !== false : true;
        }
        static renderMemoryToggle() {
            const count = document.getElementById('commons-channel-member-count');
            const muteBtn = document.getElementById('commons-mute-btn');
            const anchor = muteBtn || count;
            const header = anchor?.parentElement
                || document.querySelector('.commons-conversation-header')
                || document.querySelector('.commons-top-actions');
            let memBtn = document.getElementById('commons-memory-toggle');
            if (!memBtn && header) {
                memBtn = document.createElement('button');
                memBtn.id = 'commons-memory-toggle';
                memBtn.type = 'button';
                if (anchor && anchor.parentElement === header) {
                    anchor.insertAdjacentElement('afterend', memBtn);
                }
                else {
                    header.appendChild(memBtn);
                }
            }
            if (memBtn && !memBtn.dataset.bound) {
                memBtn.dataset.bound = '1';
                memBtn.addEventListener('click', () => {
                    const cfg = window.config;
                    const next = !this.isMemoryRecordingEnabled();
                    if (cfg) {
                        cfg.commonsRecordMemories = next;
                        void cfg.save?.(true);
                    }
                    this.renderMemoryToggle();
                    if (window.CommonsState)
                        this.renderConversation();
                });
            }
            const enabled = this.isMemoryRecordingEnabled();
            if (memBtn) {
                memBtn.className = `commons-small-btn commons-memory-toggle ${enabled ? 'is-on' : 'is-off'}`;
                memBtn.textContent = enabled ? '🧠 Memories: ON' : '🧠 Memories: OFF';
                memBtn.setAttribute('aria-pressed', enabled ? 'true' : 'false');
                memBtn.setAttribute('aria-label', enabled ? 'Character memory generation: ON' : 'Character memory generation: OFF');
                memBtn.title = enabled
                    ? 'Character memories are recorded from Commons activity (click to pause for dialogue testing)'
                    : 'Testing mode: messages will not generate character memories (click to re-enable)';
                memBtn.style.marginLeft = '6px';
                memBtn.style.borderRadius = '999px';
                memBtn.style.padding = '4px 10px';
                memBtn.style.fontSize = '11px';
                memBtn.style.fontWeight = '600';
                memBtn.style.whiteSpace = 'nowrap';
                if (enabled) {
                    memBtn.style.background = '#6c59dc';
                    memBtn.style.color = '#ffffff';
                    memBtn.style.border = '1px solid #8270eb';
                }
                else {
                    memBtn.style.background = '#21262d';
                    memBtn.style.color = '#8b949e';
                    memBtn.style.border = '1px solid #30363d';
                }
            }
            const input = document.getElementById('commons-input');
            if (input) {
                if (!enabled) {
                    input.placeholder = 'Testing mode: messages will not generate character memories';
                }
                else if (input.placeholder === 'Testing mode: messages will not generate character memories') {
                    input.placeholder = 'Write a message…';
                }
            }
        }
        static renderConversation() {
            const state = window.CommonsState;
            const viwoToggle = document.getElementById('commons-viwo-state-toggle');
            if (viwoToggle)
                viwoToggle.checked = state.useViwoState !== false;
            const clockControls = document.getElementById('commons-standalone-clock-controls');
            const resetBtn = document.getElementById('commons-reset-btn');
            const isStandalone = state.useViwoState === false;
            if (clockControls)
                clockControls.style.display = isStandalone ? 'inline-flex' : 'none';
            if (resetBtn)
                resetBtn.style.display = isStandalone ? 'inline-flex' : 'none';
            if (isStandalone && state.currentDatetime) {
                const dateEl = document.getElementById('commons-clock-date');
                const timeEl = document.getElementById('commons-clock-time');
                if (dateEl && document.activeElement !== dateEl)
                    dateEl.value = String(state.currentDatetime).slice(0, 10);
                if (timeEl && document.activeElement !== timeEl)
                    timeEl.value = String(state.currentDatetime).slice(11, 16);
            }
            const branchSel = document.getElementById('commons-branch-select');
            if (branchSel && Array.isArray(state.branches)) {
                branchSel.innerHTML = '';
                for (const b of state.branches) {
                    const opt = document.createElement('option');
                    opt.value = b.id;
                    opt.textContent = b.name || b.id;
                    opt.selected = Boolean(b.id === state.activeBranchId);
                    branchSel.appendChild(opt);
                }
            }
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
            let muteBtn = document.getElementById('commons-mute-btn');
            if (!muteBtn && count?.parentElement) {
                muteBtn = document.createElement('button');
                muteBtn.id = 'commons-mute-btn';
                muteBtn.type = 'button';
                muteBtn.className = 'commons-small-btn';
                muteBtn.style.marginLeft = '6px';
                muteBtn.addEventListener('click', async () => {
                    const st = window.CommonsState;
                    const activeChannel = (st.channels || []).find((item) => item.id === st.selectedChannelId);
                    if (!activeChannel)
                        return;
                    try {
                        await window.CommonsApi.setChannelMuted(activeChannel.id, st.perspective, !activeChannel.muted);
                        await st.sync(true);
                    }
                    catch (err) {
                        console.error('Failed to toggle channel mute:', err);
                    }
                });
                count.insertAdjacentElement('afterend', muteBtn);
            }
            this.renderMemoryToggle();
            let mutedBadge = document.getElementById('commons-header-muted-badge');
            if (!mutedBadge && title?.parentElement) {
                mutedBadge = document.createElement('span');
                mutedBadge.id = 'commons-header-muted-badge';
                mutedBadge.className = 'commons-muted-badge';
                mutedBadge.style.cssText = 'font-size:11px;opacity:0.75;margin-left:6px;font-weight:500;';
                mutedBadge.textContent = '[muted]';
                title.insertAdjacentElement('afterend', mutedBadge);
            }
            if (!channel) {
                if (title)
                    title.textContent = 'No conversation selected';
                if (subtitle)
                    subtitle.textContent = 'Choose a conversation to open your inbox.';
                if (avatar)
                    avatar.textContent = '·';
                if (count)
                    count.textContent = '';
                if (muteBtn)
                    muteBtn.style.display = 'none';
                if (mutedBadge)
                    mutedBadge.style.display = 'none';
                if (membersList)
                    membersList.replaceChildren();
                if (editor)
                    editor.replaceChildren();
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
            if (muteBtn) {
                const isMuted = Boolean(channel.muted);
                muteBtn.style.display = '';
                muteBtn.textContent = isMuted ? '🔕' : '🔔';
                muteBtn.title = isMuted ? 'Unmute conversation' : 'Mute conversation';
                muteBtn.setAttribute('aria-label', isMuted ? 'Unmute conversation' : 'Mute conversation');
                muteBtn.setAttribute('aria-pressed', isMuted ? 'true' : 'false');
            }
            if (mutedBadge) {
                mutedBadge.style.display = channel.muted ? '' : 'none';
            }
            if (feed)
                feed.setAttribute('aria-label', townBoard
                    ? (channel.kind === 'public' ? 'Town-board posts' : 'Private letters')
                    : 'Messages');
            if (send)
                send.textContent = townBoard
                    ? (channel.kind === 'public' ? 'Post notice' : 'Send letter')
                    : 'Send';
            if (input) {
                input.placeholder = !this.isMemoryRecordingEnabled()
                    ? 'Testing mode: messages will not generate character memories'
                    : (townBoard
                        ? (channel.kind === 'public' ? 'Write a public notice…' : 'Write a private letter…')
                        : 'Write a message…');
            }
            if (membersList) {
                membersList.replaceChildren(document.createRange().createContextualFragment(members.map((name, index) => `<span class="commons-member-chip commons-char-trigger" data-character="${escapeHtml(name)}" title="Inspect ${escapeHtml(name)} inner world"><span class="commons-member-avatar avatar-${index % 6}">${escapeHtml(initials(name))}</span>${escapeHtml(name)}</span>`).join('') || '<div class="commons-empty-note">No members listed.</div>'));
            }
            this.renderMemberEditor(channel);
            const allowed = channel.kind === 'public' || members.includes(state.perspective);
            // Pause controls autonomous character turns. The selected character can
            // still use the composer while those turns are paused.
            if (send)
                send.disabled = !allowed;
            if (input)
                input.disabled = !allowed;
            const hint = document.getElementById('commons-composer-hint');
            if (hint) {
                const otherDm = channel.kind === 'dm'
                    ? members.find((m) => m !== state.perspective)
                    : '';
                const otherPart = otherDm ? state.participants?.[otherDm] : null;
                if (otherDm && otherPart && otherPart.control_mode !== 'llm') {
                    hint.textContent = `${otherDm} is Human-controlled (won't auto-reply with LLM). Switch Phone owner to ${otherDm} or set them to LLM under Characters & pacing.`;
                }
                else if (state.isPaused) {
                    hint.textContent = `Simulation paused - click Resume for auto-replies, or open "Characters & pacing" -> Act on ${otherDm || 'a character'}.`;
                }
                else if (channel.kind === 'public' && (state.channels || []).length <= 1) {
                    hint.textContent = 'Tip: click "✉ New direct message" in the sidebar to text a character privately.';
                }
                else {
                    hint.textContent = '';
                }
            }
        }
        static renderMemberEditor(channel) {
            const editor = document.getElementById('commons-member-editor');
            if (!editor)
                return;
            const state = window.CommonsState;
            if (channel.kind !== 'group' || channel.created_by !== state.perspective) {
                editor.replaceChildren();
                return;
            }
            const available = Object.keys(state.participants || {})
                .filter((name) => !channel.members.includes(name));
            editor.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-member-edit-title">Manage members</div>
                <div class="commons-member-add-row"><select id="commons-member-to-add" class="commons-select" ${available.length ? '' : 'disabled'}>
                    ${available.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')}
                </select><button type="button" class="commons-small-btn" data-member-action="add" ${available.length ? '' : 'disabled'}>Add</button></div>
                <div class="commons-member-remove-list">${channel.members.filter((name) => name !== channel.created_by).map((name) => `<button type="button" class="commons-remove-member" data-member-action="remove" data-name="${escapeHtml(name)}">Remove ${escapeHtml(name)}</button>`).join('')}</div>`));
        }
        static editingMessageId = null;
        static pendingAttachments = [];
        static async saveMessageEdit(msgId, text) {
            try {
                const state = window.CommonsState;
                await window.CommonsApi.editMessage(msgId, state.perspective, text);
                this.editingMessageId = null;
                await state.sync(true);
            }
            catch (err) {
                console.error('Failed to edit message:', err);
                alert('Could not save message edit: ' + String(err));
            }
        }
        static async confirmDeleteMessage(msgId) {
            if (!window.confirm('Delete this message?'))
                return;
            try {
                const state = window.CommonsState;
                await window.CommonsApi.deleteMessage(msgId, state.perspective);
                if (this.editingMessageId === msgId)
                    this.editingMessageId = null;
                await state.sync(true);
            }
            catch (err) {
                console.error('Failed to delete message:', err);
                alert('Could not delete message: ' + String(err));
            }
        }
        static renderMessages() {
            const feed = document.getElementById('commons-feed');
            if (!feed)
                return;
            const wasNearBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 90;
            const messages = window.CommonsState.messages || [];
            const feedHtml = messages.map((message) => {
                const own = message.author === window.CommonsState.perspective;
                const wallTime = new Date(message.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const time = formatIsoLabel(message.world_datetime) || formatWorldTick(message.tick) || wallTime;
                const isEditing = this.editingMessageId === message.id;
                const editedBadge = message.edited ? '<span class="chat-msg-edited" title="Edited message">(edited)</span>' : '';
                const actionsHtml = own ? `<span class="chat-msg-actions">
                    <button type="button" class="commons-msg-btn commons-msg-edit" data-msg-id="${message.id}" title="Edit message" aria-label="Edit message">✏</button>
                    <button type="button" class="commons-msg-btn commons-msg-delete" data-msg-id="${message.id}" title="Delete message" aria-label="Delete message">🗑</button>
                </span>` : '';
                const bodyHtml = isEditing
                    ? `<div class="chat-msg-edit-inline" data-msg-id="${message.id}">
                        <input type="text" class="commons-edit-input" value="${escapeHtml(message.text)}" />
                        <div class="commons-edit-buttons">
                            <button type="button" class="commons-small-btn commons-save-edit" data-msg-id="${message.id}">Save</button>
                            <button type="button" class="commons-small-btn commons-cancel-edit" data-msg-id="${message.id}">Cancel</button>
                        </div>
                    </div>`
                    : (message.text ? `<div class="chat-msg-text">${escapeHtml(message.text)}</div>` : '');
                let attachmentsHtml = '';
                if (Array.isArray(message.attachments) && message.attachments.length) {
                    attachmentsHtml = `<div class="chat-msg-attachments">` + message.attachments.map((a) => `
                        <div class="chat-attachment-item">
                            <a href="${escapeHtml(a.url)}" target="_blank" rel="noopener noreferrer" class="chat-attachment-link" title="Click to enlarge">
                                <img src="${escapeHtml(a.url)}" alt="${escapeHtml(a.caption || 'Attachment')}" class="chat-attachment-thumb" />
                            </a>
                            ${a.caption ? `<div class="chat-attachment-caption">${escapeHtml(a.caption)}</div>` : ''}
                        </div>
                    `).join('') + `</div>`;
                }
                return `<article class="chat-msg ${own ? 'own' : ''}" data-msg-id="${escapeHtml(message.id)}" data-author="${escapeHtml(message.author)}"${message.author !== 'User' ? ' style="cursor:pointer;" title="Click to inspect the thinking and tool flow behind this message"' : ''}>
                    <div class="chat-msg-avatar avatar-${hash(message.author) % 6} commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(initials(message.author))}</div>
                    <div class="chat-msg-content"><div class="chat-msg-meta"><span class="chat-msg-author commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(message.author)}</span><time>${time}</time>${editedBadge}${actionsHtml}</div>
                    ${bodyHtml}${attachmentsHtml}</div>
                </article>`;
            }).join('') || (window.CommonsState.theme === 'town_board'
                ? `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Leave a notice or write a private letter.</p></div>`
                : `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Send a note, ask a question, or let the conversation find its way.</p></div>`);
            feed.replaceChildren(document.createRange().createContextualFragment(feedHtml));
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
            if (window.Lit?.html && window.Lit?.render) {
                const lit = window.Lit;
                const itemsTmpl = names.map(name => {
                    const participant = participants[name];
                    const pace = window.CommonsAgent.getTalkativeness(name);
                    const isActing = Boolean(window.CommonsAgent.controllers?.[name]);
                    const controlMode = participant.control_mode || 'unavailable';
                    const controlLabel = controlMode === 'human' ? 'Human' : controlMode === 'npc' ? 'Simple NPC' : controlMode === 'llm' ? '' : 'Unavailable';
                    const canAutoLlm = controlMode === 'llm';
                    const canManualAct = controlMode !== 'unavailable';
                    const actTitle = controlMode === 'human' ? `Force one LLM turn for ${name} (Human-controlled: skipped on auto-run)` : controlMode === 'npc' ? `Force one LLM turn for ${name} (Simple NPC)` : controlMode === 'llm' ? `Trigger an LLM turn for ${name}` : `${name} has no available character record`;
                    const presenceClass = isActing ? 'thinking' : participant.active && !participant.blocked ? 'online' : '';
                    const presenceLabel = isActing ? 'thinking...' : participant.blocked ? 'blocked' : participant.active ? 'active' : 'paused';
                    return lit.html `<div class="participant-item"><div class="participant-row">
                        <span class="participant-name commons-char-trigger" data-character="${name}" title="Inspect ${name} inner world">
                            ${name}${controlLabel ? lit.html ` <span class="commons-control-badge">${controlLabel}</span>` : ''}
                        </span>
                        <span class="participant-presence ${presenceClass}">${presenceLabel}</span>
                        <button type="button" class="commons-act-btn" data-character="${name}" data-role="act" title="${actTitle}" ?disabled=${!canManualAct || isActing || participant.blocked}>▶ Act</button>
                    </div><div class="participant-controls">
                        <label><input type="checkbox" data-character="${name}" data-role="active" .checked=${participant.active}> In chat</label>
                        <label><input type="checkbox" data-character="${name}" data-role="blocked" .checked=${participant.blocked}> Block</label>
                    </div>${canAutoLlm ? lit.html `<div class="talkativeness-control"><div class="talkativeness-label"><span>Turn pace</span><span class="talkativeness-value"><span data-pace-for="${name}">${pace}s</span><button type="button" class="commons-small-btn pace-random-btn" data-character="${name}" data-role="pace-random" title="Choose a random turn pace for ${name}" aria-label="Randomize ${name} turn pace">🎲</button></span></div>
                        <input type="range" class="talkativeness-slider" min="5" max="120" .value=${String(pace)} data-character="${name}" data-role="pace" aria-label="${name} automatic turn cooldown"></div>` : lit.html `<div class="participant-control-note">${controlMode === 'human' ? 'Human-controlled: skipped on auto-run (▶ Act works)' : controlMode === 'npc' ? 'Simple NPC: skipped on auto-run (▶ Act works)' : 'Control mode unavailable'}</div>`}</div>`;
                });
                lit.render(lit.html `${itemsTmpl}`, list);
            }
            else {
                list.replaceChildren(document.createRange().createContextualFragment(names.map(name => {
                    const participant = participants[name];
                    const pace = window.CommonsAgent.getTalkativeness(name);
                    const isActing = Boolean(window.CommonsAgent.controllers?.[name]);
                    const controlMode = participant.control_mode || 'unavailable';
                    const controlLabel = controlMode === 'human' ? 'Human' : controlMode === 'npc' ? 'Simple NPC' : controlMode === 'llm' ? '' : 'Unavailable';
                    const canAutoLlm = controlMode === 'llm';
                    const canManualAct = controlMode !== 'unavailable';
                    const actTitle = controlMode === 'human' ? `Force one LLM turn for ${name} (Human-controlled: skipped on auto-run)` : controlMode === 'npc' ? `Force one LLM turn for ${name} (Simple NPC)` : controlMode === 'llm' ? `Trigger an LLM turn for ${name}` : `${name} has no available character record`;
                    return `<div class="participant-item"><div class="participant-row">
                        <span class="participant-name commons-char-trigger" data-character="${escapeHtml(name)}" title="Inspect ${escapeHtml(name)} inner world">${escapeHtml(name)}${controlLabel ? ` <span class="commons-control-badge">${controlLabel}</span>` : ''}</span>
                        <span class="participant-presence ${isActing ? 'thinking' : participant.active && !participant.blocked ? 'online' : ''}">${isActing ? 'thinking...' : participant.blocked ? 'blocked' : participant.active ? 'active' : 'paused'}</span>
                        <button type="button" class="commons-act-btn" data-character="${escapeHtml(name)}" data-role="act" title="${escapeHtml(actTitle)}" ${!canManualAct || isActing || participant.blocked ? 'disabled' : ''}>▶ Act</button>
                    </div><div class="participant-controls">
                        <label><input type="checkbox" data-character="${escapeHtml(name)}" data-role="active" ${participant.active ? 'checked' : ''}> In chat</label>
                        <label><input type="checkbox" data-character="${escapeHtml(name)}" data-role="blocked" ${participant.blocked ? 'checked' : ''}> Block</label>
                    </div>${canAutoLlm ? `<div class="talkativeness-control"><div class="talkativeness-label"><span>Turn pace</span><span class="talkativeness-value"><span data-pace-for="${escapeHtml(name)}">${pace}s</span><button type="button" class="commons-small-btn pace-random-btn" data-character="${escapeHtml(name)}" data-role="pace-random" title="Choose a random turn pace for ${escapeHtml(name)}" aria-label="Randomize ${escapeHtml(name)} turn pace">🎲</button></span></div>
                        <input type="range" class="talkativeness-slider" min="5" max="120" value="${pace}" data-character="${escapeHtml(name)}" data-role="pace" aria-label="${escapeHtml(name)} automatic turn cooldown"></div>` : `<div class="participant-control-note">${controlMode === 'human' ? 'Human-controlled: skipped on auto-run (▶ Act works)' : controlMode === 'npc' ? 'Simple NPC: skipped on auto-run (▶ Act works)' : 'Control mode unavailable'}</div>`}</div>`;
                }).join('')));
            }
        }
        static renderGroupRoster() {
            const roster = document.getElementById('commons-group-roster');
            const state = window.CommonsState;
            if (!roster)
                return;
            const names = Object.keys(state.participants || {}).filter((name) => name !== 'User' && name !== state.perspective);
            roster.replaceChildren(document.createRange().createContextualFragment(names.map((name) => `<label class="commons-roster-option">
                <input type="checkbox" value="${escapeHtml(name)}"><span class="commons-member-avatar avatar-${hash(name) % 6}">${escapeHtml(initials(name))}</span><span>${escapeHtml(name)}</span></label>`).join('')));
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
                const optDis = document.createElement('option');
                optDis.value = '';
                optDis.disabled = true;
                optDis.selected = true;
                optDis.textContent = 'No known characters to contact';
                select.replaceChildren(optDis);
            }
            else {
                select.replaceChildren(document.createRange().createContextualFragment(eligibleNames.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')));
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
            const active = Object.keys(participants).filter(name => name !== 'User' && participants[name].control_mode === 'llm' && participants[name].active && !participants[name].blocked);
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
                const isErr = String(state.lastActed.summary || '').startsWith('LLM error:');
                chip.textContent = `Last acted: ${state.lastActed.charName} (${state.lastActed.summary})`;
                chip.className = isErr ? 'commons-actor-chip error' : 'commons-actor-chip idle';
                chip.style.color = isErr ? '#c93c37' : '';
            }
            else {
                chip.textContent = 'Idle';
                chip.className = 'commons-actor-chip idle';
                chip.style.color = '';
            }
        }
        static renderAttachmentPreviews() {
            const el = document.getElementById('commons-composer-previews');
            if (!el)
                return;
            el.replaceChildren(document.createRange().createContextualFragment(this.pendingAttachments.map((a, idx) => `
                    <div class="commons-composer-preview-item">
                        <img src="${escapeHtml(a.url)}" class="commons-composer-preview-thumb" alt="" />
                        <span>${escapeHtml(a.filename || 'image')}</span>
                        <button type="button" class="commons-composer-preview-remove" data-index="${idx}" title="Remove attachment">&times;</button>
                    </div>
                `).join('')));
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
            const intermediatorEl = document.getElementById('commons-drawer-intermediator');
            const recalledEl = document.getElementById('commons-drawer-recalled');
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
                const statusText = isActing ? 'Thinking right now...' : 'In conversation';
                if (window.Lit?.html && window.UiPrimitives?.StatusBadge) {
                    if (!presenceEl._$litPart$) {
                        presenceEl.textContent = '';
                    }
                    const badge = window.UiPrimitives.StatusBadge({
                        label: statusText,
                        color: isActing ? '#3b82f6' : '#22c55e',
                        icon: isActing ? '💭' : '🟢',
                        active: true
                    });
                    window.Lit.render(badge, presenceEl);
                }
                else {
                    presenceEl.textContent = statusText;
                    presenceEl.className = `commons-drawer-presence ${isActing ? 'thinking' : 'active'}`;
                }
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
                if (window.Lit?.html && window.UiPrimitives?.StatusBadge) {
                    const badges = traitKeys.map((t) => window.UiPrimitives.StatusBadge({
                        label: t,
                        color: 'var(--bg-inset, #242a33)'
                    }));
                    window.Lit.render(window.Lit.html `${badges}`, traitsEl);
                }
                else {
                    traitsEl.replaceChildren(document.createRange().createContextualFragment(traitKeys.map((t) => `<span class="commons-trait-badge">${escapeHtml(t)}</span>`).join('')));
                }
            }
            // Render turn history and monologue (or message-specific trace when clicked)
            const turns = state.characterTurns?.[charName] || [];
            const selectedMsgId = state.selectedDrawerMessageId;
            const msgTrace = selectedMsgId !== null && selectedMsgId !== undefined
                ? state.messageTraces?.[String(selectedMsgId)]
                : null;
            const latest = msgTrace || turns[0];
            const flowEl = document.getElementById('commons-drawer-flow');
            const flowScopeEl = document.getElementById('commons-drawer-flow-scope');
            if (flowScopeEl) {
                flowScopeEl.replaceChildren(document.createRange().createContextualFragment(msgTrace
                    ? `· message #${escapeHtml(selectedMsgId)} <button type="button" id="commons-drawer-latest-btn" class="commons-small-btn" style="margin-left:6px;font-size:10px;">Show latest</button>`
                    : ''));
                document.getElementById('commons-drawer-latest-btn')?.addEventListener('click', () => {
                    state.openDrawer(charName);
                });
            }
            if (flowEl) {
                const steps = Array.isArray(latest?.detail?.steps) ? latest.detail.steps : [];
                if (steps.length) {
                    flowEl.replaceChildren(document.createRange().createContextualFragment(steps.map((s, idx) => `<div class="commons-history-row" style="padding:5px 8px;margin-bottom:4px;border-left:2px solid var(--accent,#60a5fa);font-size:11px;">
                            <div style="font-size:10px;font-weight:600;color:var(--text-muted,#8b949e);">${idx + 1}. ${escapeHtml(s.label || s.kind || 'Step')}</div>
                            ${s.detail ? `<div style="margin-top:2px;">${escapeHtml(s.detail)}</div>` : ''}
                        </div>`).join('')));
                }
                else if (selectedMsgId !== null && selectedMsgId !== undefined) {
                    flowEl.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-drawer-empty-state">No causal trace recorded for message #${escapeHtml(selectedMsgId)} (it may have been loaded from an earlier session).</div>`));
                }
                else {
                    flowEl.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-drawer-empty-state">Trigger a turn with ▶ Act to observe the causal flow.</div>`));
                }
            }
            if (monologueEl) {
                if (latest?.inner) {
                    const latestTime = formatWorldTick(latest.worldTick)
                        || new Date(latest.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    monologueEl.replaceChildren(document.createRange().createContextualFragment(`<blockquote class="commons-inner-quote">"${escapeHtml(latest.inner)}"</blockquote>
                    <div class="commons-inner-time">${escapeHtml(latestTime)}</div>`));
                }
                else {
                    monologueEl.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-drawer-empty-state">No thoughts recorded yet for ${escapeHtml(charName)}. Trigger a turn with ▶ Act to observe their inner stream.</div>`));
                }
            }
            if (intermediatorEl) {
                const inter = latest?.detail?.intermediatorThought;
                if (inter) {
                    intermediatorEl.replaceChildren(document.createRange().createContextualFragment(`<blockquote class="commons-inner-quote">"${escapeHtml(inter)}"</blockquote>`));
                }
                else {
                    intermediatorEl.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-drawer-empty-state">No intermediator synthesis yet (fires when memories are recalled on read_chat).</div>`));
                }
            }
            if (recalledEl) {
                const recalled = Array.isArray(latest?.detail?.recalledMemories) ? latest.detail.recalledMemories : [];
                if (recalled.length) {
                    recalledEl.replaceChildren(document.createRange().createContextualFragment(recalled.map((m) => {
                        const text = typeof m === 'string' ? m : String(m?.text || '');
                        const meta = [];
                        if (m?.category)
                            meta.push(String(m.category));
                        if (typeof m?.tick === 'number')
                            meta.push(`tick ${m.tick}`);
                        if (typeof m?.score === 'number')
                            meta.push(`score ${m.score.toFixed(2)}`);
                        return `<div class="commons-history-row" style="padding:6px 8px;margin-bottom:5px;border:1px solid var(--border,#2d333b);border-radius:6px;font-size:11px;">
                                ${meta.length ? `<div style="font-size:10px;color:var(--text-muted,#8b949e);margin-bottom:2px;">${escapeHtml(meta.join(' · '))}</div>` : ''}
                                <div>${escapeHtml(text)}</div>
                            </div>`;
                    }).join('')));
                }
                else {
                    recalledEl.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-drawer-empty-state">No recalled memories recorded on the latest turn.</div>`));
                }
            }
            if (decisionEl) {
                if (latest) {
                    decisionEl.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-decision-card">
                        <div class="commons-decision-header">
                            <span class="commons-decision-action ${escapeHtml(latest.action)}">${escapeHtml(latest.action.replace('_', ' '))}</span>
                            <span class="commons-decision-summary">${escapeHtml(latest.summary)}</span>
                        </div>
                        ${latest.detail?.text ? `<div class="commons-decision-text">"${escapeHtml(latest.detail.text)}"</div>` : ''}
                    </div>`));
                }
                else {
                    decisionEl.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-drawer-empty-state">No recent decisions.</div>`));
                }
            }
            if (historyEl) {
                if (turns.length > 1) {
                    historyEl.replaceChildren(document.createRange().createContextualFragment(turns.slice(1, 8).map((t) => {
                        const turnTime = formatWorldTick(t.worldTick)
                            || new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                        return `
                        <div class="commons-history-row">
                            <div class="commons-history-header">
                                <span class="commons-decision-action small ${escapeHtml(t.action)}">${escapeHtml(t.action.replace('_', ' '))}</span>
                                <time>${escapeHtml(turnTime)}</time>
                            </div>
                            ${t.inner ? `<div class="commons-history-thought">"${escapeHtml(t.inner)}"</div>` : ''}
                        </div>
                    `;
                    }).join('')));
                }
                else {
                    historyEl.replaceChildren(document.createRange().createContextualFragment(`<div class="commons-drawer-empty-state">Earlier turns will appear here as the conversation continues.</div>`));
                }
            }
        }
    }
    function formatIsoLabel(iso) {
        if (typeof iso !== 'string' || !iso)
            return '';
        const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
        if (!m)
            return '';
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const mo = Math.max(1, Number(m[2]));
        return `${months[(mo - 1) % 12]} ${Number(m[3])}, ${Number(m[1])} · ${m[4]}:${m[5]}`;
    }
    function formatWorldTick(t) {
        if (typeof t !== 'number' || !Number.isFinite(t))
            return '';
        const wc = window.CommonsState?.worldClock || {};
        const mpt = Number(wc.time_per_tick_minutes ?? 5) || 5;
        const startH = Number(wc.clock_start_hour ?? 8);
        const startM = Number(wc.clock_start_minute ?? 0);
        const startMin = startH * 60 + startM;
        const total = Math.round(startMin + t * mpt);
        const dayMinutes = ((total % 1440) + 1440) % 1440;
        const hh = String(Math.floor(dayMinutes / 60)).padStart(2, '0');
        const mm = String(dayMinutes % 60).padStart(2, '0');
        const cfg = wc.calendar_config && typeof wc.calendar_config === 'object' ? wc.calendar_config : {};
        const dpm = Math.max(1, Math.floor(Number(cfg.days_per_month) || 30));
        const mpy = Math.max(1, Math.floor(Number(cfg.months_per_year) || 12));
        const curTick = Number(wc.time_ticks ?? 0) || 0;
        const curElapsedDays = Math.floor((startMin + curTick * mpt) / 1440);
        const curGameDay = Number(wc.game_day) || 1;
        const baseDay = cfg.start_year
            ? ((Number(cfg.start_year) - 1) * dpm * mpy + ((Number(cfg.start_month) || 1) - 1) * dpm + ((Number(cfg.start_day) || 1) - 1))
            : (curGameDay - curElapsedDays - 1);
        const targetElapsedDays = Math.floor(total / 1440);
        const absDay = baseDay + targetElapsedDays + 1;
        const yearIdx = Math.floor((absDay - 1) / (dpm * mpy)) + 1;
        const monthIdx = (Math.floor((absDay - 1) / dpm) % mpy) + 1;
        const dayIdx = ((absDay - 1) % dpm) + 1;
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const mname = months[((monthIdx - 1) % 12 + 12) % 12];
        if (yearIdx > 1 || cfg.start_year) {
            return `${mname} ${dayIdx}, ${yearIdx} · ${hh}:${mm}`;
        }
        return `${mname} ${dayIdx} · ${hh}:${mm}`;
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
