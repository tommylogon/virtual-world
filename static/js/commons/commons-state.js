"use strict";
/**
 * @module commons-state — authorized conversation state and polling
 * @contributes CommonsState: selected perspective, channels, messages, polling
 * @powers The Commons reactive data flow
 * @relates CommonsApi, CommonsUI
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */
(function () {
    'use strict';
    class CommonsState {
        static messages = [];
        static channels = [];
        static participants = {};
        static listeners = [];
        // Opening/inspecting the phone is read-only. Character turns start
        // only after the user explicitly resumes the conversation.
        static manualPaused = true;
        static visibilityPaused = false;
        static pollingTimer = null;
        static perspective = 'User';
        static selectedChannelId = 'public';
        static theme = 'live_social';
        static get isPaused() {
            return this.manualPaused || this.visibilityPaused;
        }
        static subscribe(fn) {
            this.listeners.push(fn);
        }
        static emit() {
            for (const fn of this.listeners) {
                try {
                    fn();
                }
                catch (e) {
                    console.error(e);
                }
            }
        }
        static async sync() {
            try {
                const data = await window.CommonsApi.getState(this.perspective);
                this.channels = data.channels || [];
                this.participants = data.participants || {};
                this.theme = data.theme === 'town_board' ? 'town_board' : 'live_social';
                if (!this.channels.some((channel) => channel.id === this.selectedChannelId)) {
                    this.selectedChannelId = this.channels[0]?.id || '';
                    this.messages = [];
                }
                if (this.selectedChannelId) {
                    const sinceId = this.messages.length
                        ? Math.max(...this.messages.map((message) => Number(message.id) || 0))
                        : undefined;
                    const result = await window.CommonsApi.getMessages(this.perspective, this.selectedChannelId, sinceId);
                    if (sinceId)
                        this.messages = [...this.messages, ...(result.messages || [])];
                    else
                        this.messages = result.messages || [];
                }
                this.emit();
            }
            catch (err) {
                console.error('[CommonsState] Sync failed:', err);
            }
        }
        static async selectPerspective(name) {
            this.perspective = name || 'User';
            this.messages = [];
            this.selectedChannelId = 'public';
            await this.sync();
        }
        static async selectTheme(theme) {
            await window.CommonsApi.setTheme(theme);
            await this.sync();
        }
        static async selectChannel(channelId, explicitRead = true) {
            if (!this.channels.some((channel) => channel.id === channelId))
                return;
            this.selectedChannelId = channelId;
            this.messages = [];
            if (explicitRead) {
                await window.CommonsApi.readMessages(this.perspective, channelId, 'all');
                const history = await window.CommonsApi.getMessages(this.perspective, channelId);
                this.messages = history.messages || [];
            }
            else {
                const result = await window.CommonsApi.getMessages(this.perspective, channelId);
                this.messages = result.messages || [];
            }
            await this.sync();
        }
        static setPaused(paused, source = 'manual') {
            if (source === 'visibility')
                this.visibilityPaused = paused;
            else
                this.manualPaused = paused;
            if (this.isPaused) {
                window.CommonsAgent.pause();
                this.stopPolling();
            }
            else {
                window.CommonsAgent.resume();
                this.startPolling();
            }
            window.CommonsUI?.renderPauseState();
        }
        static startPolling(intervalMs = 2500) {
            this.stopPolling();
            if (this.isPaused)
                return;
            void this.sync();
            this.pollingTimer = setInterval(() => {
                if (!this.isPaused)
                    void this.sync();
            }, intervalMs);
        }
        static stopPolling() {
            if (this.pollingTimer) {
                clearInterval(this.pollingTimer);
                this.pollingTimer = null;
            }
        }
    }
    window.CommonsState = CommonsState;
})();
