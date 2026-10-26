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
        static messages: *FIX*[] = [];
        static channels: *FIX*[] = [];
        static participants: Record<string, *FIX*> = {};
        static listeners: Function[] = [];
        // Opening/inspecting the phone is read-only. Character turns start
        // only after the user explicitly resumes the conversation.
        static manualPaused = true;
        static visibilityPaused = false;
        static liveEvents: EventSource | null = null;
        static perspective = 'User';
        static selectedChannelId = 'public';
        static theme = 'live_social';
        static knownCharacters: string[] = [];
        static actingCharacter: string | null = null;
        static lastActed: { charName: string; action: string; summary: string; timestamp: number } | null = null;
        static characterTurns: Record<string, Array<{
            inner: string;
            action: string;
            summary: string;
            detail?: *FIX*;
            timestamp: number;
        }>> = {};
        static selectedDrawerCharacter: string | null = null;
        static characterContextCache: Record<string, *FIX*> = {};

        static get isPaused(): boolean {
            return this.manualPaused || this.visibilityPaused;
        }

        static subscribe(fn: Function) {
            this.listeners.push(fn);
        }

        static emit() {
            for (const fn of this.listeners) {
                try { fn(); } catch (e) { console.error(e); }
            }
        }

        static async sync() {
            try {
                const data = await (window as *FIX*).CommonsApi.getState(this.perspective);
                this.channels = data.channels || [];
                this.participants = data.participants || {};
                (window as *FIX*).CommonsAgent?.reconcileParticipants?.();
                this.theme = data.theme === 'town_board' ? 'town_board' : 'live_social';
                this.knownCharacters = Array.isArray(data.known_characters) ? data.known_characters : [];
                if (!this.channels.some((channel: *FIX*) => channel.id === this.selectedChannelId)) {
                    this.selectedChannelId = this.channels[0]?.id || '';
                    this.messages = [];
                }
                if (this.selectedChannelId) {
                    const sinceId = this.messages.length
                        ? Math.max(...this.messages.map((message: *FIX*) => Number(message.id) || 0))
                        : undefined;
                    const result = await (window as *FIX*).CommonsApi.getMessages(
                        this.perspective, this.selectedChannelId, sinceId
                    );
                    if (sinceId) this.messages = [...this.messages, ...(result.messages || [])];
                    else this.messages = result.messages || [];
                }
                this.emit();
            } catch (err) {
                console.error('[CommonsState] Sync failed:', err);
            }
        }

        static async selectPerspective(name: string) {
            this.perspective = name || 'User';
            this.messages = [];
            this.selectedChannelId = 'public';
            await this.sync();
        }

        static async selectTheme(theme: string) {
            await (window as *FIX*).CommonsApi.setTheme(theme);
            await this.sync();
        }

        static async selectChannel(channelId: string, explicitRead = true) {
            if (!this.channels.some((channel: *FIX*) => channel.id === channelId)) return;
            this.selectedChannelId = channelId;
            this.messages = [];
            if (explicitRead) {
                await (window as *FIX*).CommonsApi.readMessages(this.perspective, channelId, 'all');
                const history = await (window as *FIX*).CommonsApi.getMessages(this.perspective, channelId);
                this.messages = history.messages || [];
            } else {
                const result = await (window as *FIX*).CommonsApi.getMessages(this.perspective, channelId);
                this.messages = result.messages || [];
            }
            await this.sync();
        }

        static setPaused(paused: boolean, source: 'manual' | 'visibility' = 'manual') {
            if (source === 'visibility') this.visibilityPaused = paused;
            else this.manualPaused = paused;

            if (this.isPaused) {
                (window as *FIX*).CommonsAgent.pause();
            } else {
                (window as *FIX*).CommonsAgent.resume();
            }

            if (this.visibilityPaused) this.stopLiveUpdates();
            else this.startLiveUpdates();

            (window as *FIX*).CommonsUI?.renderPauseState();
            this.emit();
        }

        static startLiveUpdates() {
            if (this.visibilityPaused || this.liveEvents || typeof EventSource === 'undefined') return;
            const source = new EventSource('/api/events');
            this.liveEvents = source;
            // Re-sync after opening or reconnecting so changes made while this tab
            // was disconnected are not lost.
            source.onopen = () => { void this.sync(); };
            source.onmessage = (message: MessageEvent) => {
                try {
                    const event = JSON.parse(message.data);
                    if (event?.type === 'world_changed'
                        && String(event.path || '').startsWith('/api/commons/')) void this.sync();
                } catch (error) {
                    console.warn('[CommonsState] Ignoring malformed live event:', error);
                }
            };
        }

        static stopLiveUpdates() {
            this.liveEvents?.close();
            this.liveEvents = null;
        }

        static receiveMessage(message: *FIX*) {
            if (!message) return;
            (window as *FIX*).CommonsAgent?.onMessageReceived?.(message);
            if (message.channel_id !== this.selectedChannelId) return;
            if (this.messages.some((existing: *FIX*) => existing.id === message.id)) return;
            this.messages.push(message);
            this.emit();
        }

        static recordTurn(charName: string, turn: { inner: string; action: string; summary: string; detail?: *FIX* }) {
            if (!this.characterTurns[charName]) this.characterTurns[charName] = [];
            const record = { ...turn, timestamp: Date.now() };
            this.characterTurns[charName].unshift(record);
            if (this.characterTurns[charName].length > 25) this.characterTurns[charName].pop();
            this.lastActed = { charName, action: turn.action, summary: turn.summary, timestamp: Date.now() };
            this.emit();
        }

        static openDrawer(charName: string) {
            if (!charName || charName === 'User') return;
            this.selectedDrawerCharacter = charName;
            this.emit();
        }

        static closeDrawer() {
            this.selectedDrawerCharacter = null;
            this.emit();
        }
    }

    (window as *FIX*).CommonsState = CommonsState;
})();
