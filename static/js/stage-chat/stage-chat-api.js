"use strict";
/**
 * @module stage-chat-api — HTTP client for stage chat endpoints
 * @contributes StageChatApi: fetch state, messages, post, read, participants
 * @powers Stage Chat communication with the backend
 * @relates routes/stage_chat.py
 * @docs docs/virtualWorld/dev_tasks/todo/gameplay/task-824-stage-chat-turn-based-character-perspective-chat-page.md
 */
// Classic script IIFE publishing to window
(function () {
    'use strict';
    class StageChatApi {
        static async getState() {
            const res = await fetch('/api/stage-chat/state');
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async postMessage(author, text) {
            const res = await fetch('/api/stage-chat/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author, text })
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async readMessages(character, mode = 'latest', n = 3, from_id, to_id) {
            const res = await fetch('/api/stage-chat/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ character, mode, n, from_id, to_id })
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async updateParticipant(name, active, blocked) {
            const res = await fetch(`/api/stage-chat/participants/${encodeURIComponent(name)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active, blocked })
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async storeMemory(name, text, importance = 5) {
            const res = await fetch(`/api/players/${encodeURIComponent(name)}/memories/entry`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text,
                    importance,
                    type: 'reaction',
                    tags: ['chat', 'stage'],
                    category: 'social'
                })
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
    }
    window.StageChatApi = StageChatApi;
})();
