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
        static async getState(as: string = 'User') {
            const res = await fetch(`/api/commons/state?as=${encodeURIComponent(as)}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async setTheme(theme: string) {
            const res = await fetch('/api/commons/theme', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async getMessages(as: string, channelId: string, sinceId?: number) {
            const params = new URLSearchParams({ as, channel_id: channelId });
            if (sinceId) params.set('since_id', String(sinceId));
            const res = await fetch(`/api/commons/messages?${params}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async getCharacterContext(name: string, signal?: AbortSignal) {
            const res = await fetch(`/api/commons/characters/${encodeURIComponent(name)}`, { signal });
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

        static async getRecentMemories(name: string, limit: number = 5, signal?: AbortSignal) {
            const res = await fetch(`/api/players/${encodeURIComponent(name)}/memories`, { signal });
            if (!res.ok) return { memories: [] };
            const data = await res.json();
            const list = Array.isArray(data?.memories) ? data.memories : (Array.isArray(data) ? data : []);
            const sorted = [...list].sort((a: any, b: any) => (Number(b?.tick ?? 0) - Number(a?.tick ?? 0)) || (Number(b?.timestamp ?? 0) - Number(a?.timestamp ?? 0)));
            return { memories: sorted.slice(0, limit) };
        }

        static async createChannel(body: { creator: string; kind: 'group' | 'dm'; name?: string; members?: string[]; other?: string; }, signal?: AbortSignal) {
            const res = await fetch('/api/commons/channels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async updateMembers(channelId: string, actor: string, add: string[] = [], remove: string[] = []) {
            const res = await fetch(`/api/commons/channels/${encodeURIComponent(channelId)}/members`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ actor, add, remove }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async setChannelMuted(channelId: string, actor: string, muted: boolean, signal?: AbortSignal) {
            const res = await fetch(`/api/commons/channels/${encodeURIComponent(channelId)}/mute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ actor, muted }),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async postMessage(author: string, text: string = '', channelId: string = 'public', attachments?: any[], signal?: AbortSignal, advanceTick?: boolean) {
            const payload: any = { author, text, channel_id: channelId };
            if (attachments && attachments.length) {
                payload.attachments = attachments;
            }
            const shouldAdvance = typeof advanceTick === 'boolean'
                ? advanceTick
                : Boolean((window as any).config?.commonsAdvanceClockOnReply);
            if (shouldAdvance) {
                payload.advance_tick = true;
            }
            const res = await fetch('/api/commons/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async uploadAttachment(file: File, caption: string = '', signal?: AbortSignal) {
            const formData = new FormData();
            formData.append('file', file);
            if (caption) formData.append('caption', caption);
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

        static async editMessage(id: number | string, author: string, text: string, signal?: AbortSignal) {
            const res = await fetch(`/api/commons/messages/${encodeURIComponent(id)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author, text }),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async deleteMessage(id: number | string, author: string, signal?: AbortSignal) {
            const res = await fetch(`/api/commons/messages/${encodeURIComponent(id)}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author }),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async readMessages(character: string, channelId: string = 'public', mode: string = 'all', n: number = 5, from_id?: number | null, to_id?: number | null, signal?: AbortSignal) {
            const res = await fetch('/api/commons/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ character, channel_id: channelId, mode, n, from_id, to_id }),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async updateParticipant(name: string, active?: boolean, blocked?: boolean) {
            const res = await fetch(`/api/commons/participants/${encodeURIComponent(name)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active, blocked })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async storeMemory(
            name: string,
            text: string,
            importance: number = 5,
            tags: string[] = ['conversation', 'chat'],
            signal?: AbortSignal,
            meta?: { entities?: string[]; memory_emotions?: Array<{ label: string; intensity: number }>; tick?: number; type?: string }
        ) {
            const payload: Record<string, any> = {
                text,
                importance,
                type: meta?.type || 'observation',
                tags,
                category: 'social',
            };
            if (meta?.entities?.length) payload.entities = meta.entities;
            if (meta?.memory_emotions?.length) payload.memory_emotions = meta.memory_emotions;
            if (typeof meta?.tick === 'number') payload.tick = meta.tick;
            const standalone = (window as any).CommonsState?.useViwoState === false;
            const url = standalone
                ? `/api/commons/memories/${encodeURIComponent(name)}`
                : `/api/players/${encodeURIComponent(name)}/memories/entry`;
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async setMode(useViwoState: boolean) {
            const res = await fetch('/api/commons/mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ use_viwo_state: Boolean(useViwoState) }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async setClock(date?: string, time?: string, anchorDatetime?: string) {
            const res = await fetch('/api/commons/clock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date, time, anchor_datetime: anchorDatetime }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async forkBranch(name?: string, fromMessageId?: number) {
            const res = await fetch('/api/commons/branches', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, from_message_id: fromMessageId }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async switchBranch(branchId: string) {
            const res = await fetch('/api/commons/branches/switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ branch_id: branchId }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }

        static async resetSession(force: boolean = false) {
            const res = await fetch('/api/commons/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        }
    }

    (window as any).CommonsApi = CommonsApi;
})();
