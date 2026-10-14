"use strict";
/**
 * @module stage-chat-state — State management and polling for Stage Chat
 * @contributes StageChatState: messages, participants, monologue history, polling
 * @powers Stage Chat reactive data flow
 * @relates StageChatApi, StageChatUI
 * @docs docs/virtualWorld/dev_tasks/todo/gameplay/task-824-stage-chat-turn-based-character-perspective-chat-page.md
 */
(function () {
    'use strict';
    class StageChatState {
        static messages = [];
        static participants = {};
        static monologues = [];
        static listeners = [];
        static isPaused = false;
        static pollingTimer = null;
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
                const data = await window.StageChatApi.getState();
                this.messages = data.messages || [];
                this.participants = data.participants || {};
                this.emit();
            }
            catch (err) {
                console.error('[StageChatState] Sync failed:', err);
            }
        }
        static logMonologue(charName, actionType, thought) {
            this.monologues.unshift({
                charName,
                actionType,
                thought,
                timestamp: Date.now()
            });
            if (this.monologues.length > 50)
                this.monologues.pop();
            this.emit();
        }
        static startPolling(intervalMs = 2000) {
            if (this.pollingTimer)
                clearInterval(this.pollingTimer);
            this.sync();
            this.pollingTimer = setInterval(() => {
                if (!this.isPaused)
                    this.sync();
            }, intervalMs);
        }
        static stopPolling() {
            if (this.pollingTimer) {
                clearInterval(this.pollingTimer);
                this.pollingTimer = null;
            }
        }
    }
    window.StageChatState = StageChatState;
})();
