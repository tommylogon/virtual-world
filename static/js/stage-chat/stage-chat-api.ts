/**
 * @module stage-chat-api — HTTP client for stage chat endpoints
 * @contributes StageChatApi: fetch authorized channels, read, post, and manage membership
 * @powers Stage Chat communication with the backend
 * @relates routes/stage_chat.py
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */

// Classic script IIFE publishing to window
(function () {
    'use strict';

    class StageChatApi {
        static async getState(as: string = 'User') {
            const res = await fetch(`/api/stage-chat/state?as=${encodeURIComponent(as)}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async getMessages(as: string, channelId: string, sinceId?: number) {
            const params = new URLSearchParams({ as, channel_id: channelId });
            if (sinceId) params.set('since_id', String(sinceId));
            const res = await fetch(`/api/stage-chat/messages?${params}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async getCharacterContext(name: string, signal?: AbortSignal) {
            const res = await fetch(`/api/stage-chat/characters/${encodeURIComponent(name)}`, { signal });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async retrieveMemories(name: string, query: string, signal?: AbortSignal) {
            const res = await fetch(`/api/players/${encodeURIComponent(name)}/memories/retrieve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, max_results: 5, reinforce: true }),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async createChannel(body: { creator: string; kind: 'group' | 'dm'; name?: string; members?: string[]; other?: string; }, signal?: AbortSignal) {
            const res = await fetch('/api/stage-chat/channels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async updateMembers(channelId: string, actor: string, add: string[] = [], remove: string[] = []) {
            const res = await fetch(`/api/stage-chat/channels/${encodeURIComponent(channelId)}/members`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ actor, add, remove }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async postMessage(author: string, text: string, channelId: string = 'public', signal?: AbortSignal) {
            const res = await fetch('/api/stage-chat/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author, text, channel_id: channelId }),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async readMessages(character: string, channelId: string = 'public', mode: string = 'all', n: number = 5, from_id?: number | null, to_id?: number | null, signal?: AbortSignal) {
            const res = await fetch('/api/stage-chat/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ character, channel_id: channelId, mode, n, from_id, to_id }),
                signal,
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

        static async storeMemory(name: string, text: string, importance: number = 5, tags: string[] = ['conversation', 'chat'], signal?: AbortSignal) {
            const res = await fetch(`/api/players/${encodeURIComponent(name)}/memories/entry`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text,
                    importance,
                    type: 'conversation',
                    tags,
                    category: 'social'
                }),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
    }

    (window as any).StageChatApi = StageChatApi;
})();
