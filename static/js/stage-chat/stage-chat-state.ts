/**
 * @module stage-chat-state — authorized conversation state and polling
 * @contributes StageChatState: selected perspective, channels, messages, polling
 * @powers Stage Chat reactive data flow
 * @relates StageChatApi, StageChatUI
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */

(function () {
    'use strict';

    class StageChatState {
        static messages: any[] = [];
        static channels: any[] = [];
        static participants: Record<string, any> = {};
        static listeners: Function[] = [];
        // Opening/inspecting the phone is read-only. Character turns start
        // only after the user explicitly resumes the conversation.
        static manualPaused = true;
        static visibilityPaused = false;
        static pollingTimer: any = null;
        static perspective = 'User';
        static selectedChannelId = 'public';

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
                const data = await (window as any).StageChatApi.getState(this.perspective);
                this.channels = data.channels || [];
                this.participants = data.participants || {};
                if (!this.channels.some((channel: any) => channel.id === this.selectedChannelId)) {
                    this.selectedChannelId = this.channels[0]?.id || '';
                    this.messages = [];
                }
                if (this.selectedChannelId) {
                    const sinceId = this.messages.length
                        ? Math.max(...this.messages.map((message: any) => Number(message.id) || 0))
                        : undefined;
                    const result = await (window as any).StageChatApi.getMessages(
                        this.perspective, this.selectedChannelId, sinceId
                    );
                    if (sinceId) this.messages = [...this.messages, ...(result.messages || [])];
                    else this.messages = result.messages || [];
                }
                this.emit();
            } catch (err) {
                console.error('[StageChatState] Sync failed:', err);
            }
        }

        static async selectPerspective(name: string) {
            this.perspective = name || 'User';
            this.messages = [];
            this.selectedChannelId = 'public';
            await this.sync();
        }

        static async selectChannel(channelId: string, explicitRead = true) {
            if (!this.channels.some((channel: any) => channel.id === channelId)) return;
            this.selectedChannelId = channelId;
            this.messages = [];
            if (explicitRead) {
                await (window as any).StageChatApi.readMessages(this.perspective, channelId, 'all');
                const history = await (window as any).StageChatApi.getMessages(this.perspective, channelId);
                this.messages = history.messages || [];
            } else {
                const result = await (window as any).StageChatApi.getMessages(this.perspective, channelId);
                this.messages = result.messages || [];
            }
            await this.sync();
        }

        static setPaused(paused: boolean, source: 'manual' | 'visibility' = 'manual') {
            if (source === 'visibility') this.visibilityPaused = paused;
            else this.manualPaused = paused;

            if (this.isPaused) {
                (window as any).StageChatAgent.pause();
                this.stopPolling();
            } else {
                (window as any).StageChatAgent.resume();
                this.startPolling();
            }
            (window as any).StageChatUI?.renderPauseState();
        }

        static startPolling(intervalMs: number = 2500) {
            this.stopPolling();
            if (this.isPaused) return;
            void this.sync();
            this.pollingTimer = setInterval(() => {
                if (!this.isPaused) void this.sync();
            }, intervalMs);
        }

        static stopPolling() {
            if (this.pollingTimer) {
                clearInterval(this.pollingTimer);
                this.pollingTimer = null;
            }
        }
    }

    (window as any).StageChatState = StageChatState;
})();
