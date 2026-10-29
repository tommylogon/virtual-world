"use strict";
/**
 * @module commons-state - authorized conversation state and live updates
 * @contributes CommonsState: selected perspective, channels, messages, SSE updates
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
        static liveEvents = null;
        static perspective = 'User';
        static selectedChannelId = 'public';
        static theme = 'live_social';
        static knownCharacters = [];
        static actingCharacter = null;
        static lastActed = null;
        static characterTurns = {};
        static selectedDrawerCharacter = null;
        static characterContextCache = {};
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
                const api = window.CommonsApi;
                const agent = window.CommonsAgent;
                const data = await api.getState(this.perspective);
                this.channels = data.channels || [];
                this.participants = data.participants || {};
                agent?.reconcileParticipants?.();
                this.theme = data.theme === 'town_board' ? 'town_board' : 'live_social';
                this.knownCharacters = Array.isArray(data.known_characters) ? data.known_characters : [];
                if (!this.channels.some((channel) => channel.id === this.selectedChannelId)) {
                    this.selectedChannelId = this.channels[0]?.id || '';
                    this.messages = [];
                }
                if (this.selectedChannelId) {
                    const sinceId = this.messages.length
                        ? Math.max(...this.messages.map((message) => Number(message.id) || 0))
                        : undefined;
                    const result = await api.getMessages(this.perspective, this.selectedChannelId, sinceId);
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
            const api = window.CommonsApi;
            await api.setTheme(theme);
            await this.sync();
        }
        static async selectChannel(channelId, explicitRead = true) {
            if (!this.channels.some((channel) => channel.id === channelId))
                return;
            this.selectedChannelId = channelId;
            this.messages = [];
            const api = window.CommonsApi;
            if (explicitRead) {
                await api.readMessages(this.perspective, channelId, 'all');
                const history = await api.getMessages(this.perspective, channelId);
                this.messages = history.messages || [];
            }
            else {
                const result = await api.getMessages(this.perspective, channelId);
                this.messages = result.messages || [];
            }
            await this.sync();
        }
        static setPaused(paused, source = 'manual') {
            if (source === 'visibility')
                this.visibilityPaused = paused;
            else
                this.manualPaused = paused;
            const agent = window.CommonsAgent;
            if (this.isPaused) {
                agent.pause();
            }
            else {
                agent.resume();
            }
            if (this.visibilityPaused)
                this.stopLiveUpdates();
            else
                this.startLiveUpdates();
            const ui = window.CommonsUI;
            ui?.renderPauseState();
            this.emit();
        }
        static startLiveUpdates() {
            if (this.visibilityPaused || this.liveEvents || typeof EventSource === 'undefined')
                return;
            const source = new EventSource('/api/events');
            this.liveEvents = source;
            // Re-sync after opening or reconnecting so changes made while this tab
            // was disconnected are not lost.
            source.onopen = () => { void this.sync(); };
            source.onmessage = (message) => {
                try {
                    const event = JSON.parse(message.data);
                    if (event?.type === 'world_changed'
                        && String(event.path || '').startsWith('/api/commons/'))
                        void this.sync();
                }
                catch (error) {
                    console.warn('[CommonsState] Ignoring malformed live event:', error);
                }
            };
        }
        static stopLiveUpdates() {
            this.liveEvents?.close();
            this.liveEvents = null;
        }
        static receiveMessage(message) {
            if (!message)
                return;
            const agent = window.CommonsAgent;
            agent?.onMessageReceived?.(message);
            if (message.channel_id !== this.selectedChannelId)
                return;
            if (this.messages.some((existing) => existing.id === message.id))
                return;
            this.messages.push(message);
            this.emit();
        }
        static recordTurn(charName, turn) {
            if (!this.characterTurns[charName])
                this.characterTurns[charName] = [];
            const record = { ...turn, timestamp: Date.now() };
            this.characterTurns[charName].unshift(record);
            if (this.characterTurns[charName].length > 25)
                this.characterTurns[charName].pop();
            this.lastActed = { charName, action: turn.action, summary: turn.summary, timestamp: Date.now() };
            this.emit();
        }
        static openDrawer(charName) {
            if (!charName || charName === 'User')
                return;
            this.selectedDrawerCharacter = charName;
            this.emit();
        }
        static closeDrawer() {
            this.selectedDrawerCharacter = null;
            this.emit();
        }
    }
    window.CommonsState = CommonsState;
})();
