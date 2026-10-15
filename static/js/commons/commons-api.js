"use strict";
/**
 * @module commons-api — HTTP client for The Commons endpoints
 * @contributes CommonsApi: fetch authorized channels, read, post, and manage membership
 * @powers The Commons communication with the backend
 * @relates routes/commons.py
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */
// Classic script IIFE publishing to window
(function () {
    'use strict';
    class CommonsApi {
        static async getState(as = 'User') {
            const res = await fetch(`/api/commons/state?as=${encodeURIComponent(as)}`);
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async getMessages(as, channelId, sinceId) {
            const params = new URLSearchParams({ as, channel_id: channelId });
            if (sinceId)
                params.set('since_id', String(sinceId));
            const res = await fetch(`/api/commons/messages?${params}`);
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async getCharacterContext(name, signal) {
            const res = await fetch(`/api/commons/characters/${encodeURIComponent(name)}`, { signal });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async retrieveMemories(name, query, signal) {
            const res = await fetch(`/api/players/${encodeURIComponent(name)}/memories/retrieve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, max_results: 5, reinforce: true }),
                signal,
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async createChannel(body, signal) {
            const res = await fetch('/api/commons/channels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal,
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async updateMembers(channelId, actor, add = [], remove = []) {
            const res = await fetch(`/api/commons/channels/${encodeURIComponent(channelId)}/members`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ actor, add, remove }),
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async postMessage(author, text, channelId = 'public', signal) {
            const res = await fetch('/api/commons/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author, text, channel_id: channelId }),
                signal,
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async readMessages(character, channelId = 'public', mode = 'all', n = 5, from_id, to_id, signal) {
            const res = await fetch('/api/commons/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ character, channel_id: channelId, mode, n, from_id, to_id }),
                signal,
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async updateParticipant(name, active, blocked) {
            const res = await fetch(`/api/commons/participants/${encodeURIComponent(name)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active, blocked })
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async storeMemory(name, text, importance = 5, tags = ['conversation', 'chat'], signal) {
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
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
    }
    window.CommonsApi = CommonsApi;
})();
