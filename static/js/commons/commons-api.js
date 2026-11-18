"use strict";
/**
 * @module commons-api - HTTP client for The Commons endpoints
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
        static async setTheme(theme) {
            const res = await fetch('/api/commons/theme', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme }),
            });
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
        static async getRecentMemories(name, limit = 5, signal) {
            const res = await fetch(`/api/players/${encodeURIComponent(name)}/memories`, { signal });
            if (!res.ok)
                return { memories: [] };
            const data = await res.json();
            const list = Array.isArray(data?.memories) ? data.memories : (Array.isArray(data) ? data : []);
            const sorted = [...list].sort((a, b) => (Number(b?.tick ?? 0) - Number(a?.tick ?? 0)) || (Number(b?.timestamp ?? 0) - Number(a?.timestamp ?? 0)));
            return { memories: sorted.slice(0, limit) };
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
        static async setChannelMuted(channelId, actor, muted, signal) {
            const res = await fetch(`/api/commons/channels/${encodeURIComponent(channelId)}/mute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ actor, muted }),
                signal,
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async postMessage(author, text = '', channelId = 'public', attachments, signal, advanceTick) {
            const payload = { author, text, channel_id: channelId };
            if (attachments && attachments.length) {
                payload.attachments = attachments;
            }
            const shouldAdvance = typeof advanceTick === 'boolean'
                ? advanceTick
                : Boolean(window.config?.commonsAdvanceClockOnReply);
            if (shouldAdvance) {
                payload.advance_tick = true;
            }
            const res = await fetch('/api/commons/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal,
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async uploadAttachment(file, caption = '', signal) {
            const formData = new FormData();
            formData.append('file', file);
            if (caption)
                formData.append('caption', caption);
            const res = await fetch('/api/commons/attachments/upload', {
                method: 'POST',
                body: formData,
                signal,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || `HTTP ${res.status}`);
            }
            return await res.json();
        }
        static async editMessage(id, author, text, signal) {
            const res = await fetch(`/api/commons/messages/${encodeURIComponent(id)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author, text }),
                signal,
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async deleteMessage(id, author, signal) {
            const res = await fetch(`/api/commons/messages/${encodeURIComponent(id)}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author }),
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
        static async storeMemory(name, text, importance = 5, tags = ['conversation', 'chat'], signal, meta) {
            const payload = {
                text,
                importance,
                type: meta?.type || 'observation',
                tags,
                category: 'social',
            };
            if (meta?.entities?.length)
                payload.entities = meta.entities;
            if (meta?.memory_emotions?.length)
                payload.memory_emotions = meta.memory_emotions;
            if (typeof meta?.tick === 'number')
                payload.tick = meta.tick;
            const standalone = window.CommonsState?.useViwoState === false;
            const url = standalone
                ? `/api/commons/memories/${encodeURIComponent(name)}`
                : `/api/players/${encodeURIComponent(name)}/memories/entry`;
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal,
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async setMode(useViwoState) {
            const res = await fetch('/api/commons/mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ use_viwo_state: Boolean(useViwoState) }),
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async setClock(date, time, anchorDatetime) {
            const res = await fetch('/api/commons/clock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date, time, anchor_datetime: anchorDatetime }),
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async forkBranch(name, fromMessageId) {
            const res = await fetch('/api/commons/branches', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, from_message_id: fromMessageId }),
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async switchBranch(branchId) {
            const res = await fetch('/api/commons/branches/switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ branch_id: branchId }),
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
        static async resetSession(force = false) {
            const res = await fetch('/api/commons/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force }),
            });
            if (!res.ok)
                throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
    }
    window.CommonsApi = CommonsApi;
})();
