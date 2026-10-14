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
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async postMessage(author: string, text: string) {
            const res = await fetch('/api/stage-chat/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author, text })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async readMessages(character: string, mode: string = 'latest', n: number = 3, from_id?: number, to_id?: number) {
            const res = await fetch('/api/stage-chat/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ character, mode, n, from_id, to_id })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async updateParticipant(name: string, active?: boolean, blocked?: boolean) {
            const res = await fetch(`/api/stage-chat/participants/${encodeURIComponent(name)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active, blocked })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async storeMemory(name: string, text: string, importance: number = 5) {
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
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
    }

    (window as any).StageChatApi = StageChatApi;
})();
