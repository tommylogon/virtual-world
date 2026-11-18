/**
 * @module commons-state - authorized conversation state and live updates
 * @contributes CommonsState: selected perspective, channels, messages, SSE updates
 * @powers The Commons reactive data flow
 * @relates CommonsApi, CommonsUI
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */

interface CommonsChannel {
    id: string;
    kind: 'public' | 'group' | 'dm' | string;
    name?: string;
    members?: string[];
    created_by?: string;
    unread_count?: number;
    [key: string]: unknown;
}

interface CommonsMessage {
    id: number | string;
    author: string;
    text: string;
    timestamp: number;
    channel_id?: string;
    [key: string]: unknown;
}

interface CommonsParticipant {
    active: boolean;
    blocked: boolean;
    control_mode?: 'human' | 'npc' | 'llm' | 'unavailable' | string;
    state?: string;
    [key: string]: unknown;
}

interface CommonsTraceStep {
    kind: string;
    label: string;
    detail?: string;
}

interface CommonsTurnRecord {
    turnId?: string;
    inner: string;
    action: string;
    summary: string;
    detail?: {
        trigger?: string;
        steps?: CommonsTraceStep[];
        messageIds?: Array<string | number>;
        actions?: string[];
        recalledMemories?: unknown[];
        intermediatorThought?: string | null;
        [key: string]: unknown;
    } | unknown;
    timestamp: number;
    worldTick?: number;
}

interface CommonsCharacterContext {
    name: string;
    traits?: Record<string, unknown>;
    personality?: string;
    personality_dials?: Record<string, unknown>;
    description?: string;
    tags?: string[];
    state?: string;
    [key: string]: unknown;
}

interface CommonsApiResponse {
    channels?: CommonsChannel[];
    participants?: Record<string, CommonsParticipant>;
    messages?: CommonsMessage[];
    theme?: string;
    known_characters?: string[];
    [key: string]: unknown;
}

(function () {
    'use strict';

    class CommonsState {
        static messages: CommonsMessage[] = [];
        static channels: CommonsChannel[] = [];
        static participants: Record<string, CommonsParticipant> = {};
        static listeners: Array<() => void> = [];
        // Opening/inspecting the phone is read-only. Character turns start
        // only after the user explicitly resumes the conversation.
        static manualPaused = true;
        static visibilityPaused = false;
        static liveEvents: EventSource | null = null;
        static perspective = 'User';
        static selectedChannelId = 'public';
        static theme = 'live_social';
        static useViwoState = true;
        static clockMode: 'scenario' | 'standalone' = 'scenario';
        static activeBranchId = 'main';
        static branches: Array<{ id: string; name: string; parent_id?: string | null; fork_message_id?: number | null; active?: boolean }> = [];
        static anchoredClock: { anchor_datetime?: string; anchor_real_epoch?: number } | null = null;
        static currentDatetime: string | null = null;
        static currentTimeLabel: string | null = null;
        static knownCharacters: string[] = [];
        static actingCharacter: string | null = null;
        static lastActed: { charName: string; action: string; summary: string; timestamp: number } | null = null;
        static characterTurns: Record<string, CommonsTurnRecord[]> = {};
        static messageTraces: Record<string, CommonsTurnRecord> = {};
        static selectedDrawerCharacter: string | null = null;
        static selectedDrawerMessageId: string | number | null = null;
        static characterContextCache: Record<string, CommonsCharacterContext> = {};
        static worldClock: {
            time_ticks: number;
            time_per_tick_minutes: number;
            clock_start_hour: number;
            clock_start_minute: number;
            game_day?: number;
            game_month?: number;
            game_year?: number;
            calendar_config?: Record<string, unknown>;
        } = {
            time_ticks: 0, time_per_tick_minutes: 5, clock_start_hour: 8, clock_start_minute: 0,
        };

        static get isPaused(): boolean {
            return this.manualPaused || this.visibilityPaused;
        }

        static subscribe(fn: () => void) {
            this.listeners.push(fn);
        }

        static emit() {
            for (const fn of this.listeners) {
                try { fn(); } catch (e) { console.error(e); }
            }
        }

        static async sync(forceFull = false) {
            try {
                const api = (window as unknown as { CommonsApi: { getState: (as: string) => Promise<CommonsApiResponse>; getMessages: (as: string, channelId: string, sinceId?: number) => Promise<CommonsApiResponse> } }).CommonsApi;
                const agent = (window as unknown as { CommonsAgent?: { reconcileParticipants?: () => void } }).CommonsAgent;
                const data = await api.getState(this.perspective);
                this.channels = data.channels || [];
                this.participants = data.participants || {};
                if ((data as any).world_clock) {
                    this.worldClock = (data as any).world_clock;
                }
                if (typeof (data as any).use_viwo_state === 'boolean') {
                    this.useViwoState = (data as any).use_viwo_state;
                }
                if ((data as any).clock_mode === 'standalone' || (data as any).clock_mode === 'scenario') {
                    this.clockMode = (data as any).clock_mode;
                }
                if (typeof (data as any).active_branch_id === 'string') {
                    this.activeBranchId = (data as any).active_branch_id;
                }
                if (Array.isArray((data as any).branches)) {
                    this.branches = (data as any).branches;
                }
                this.anchoredClock = (data as any).anchored_clock || null;
                this.currentDatetime = (data as any).current_datetime || null;
                this.currentTimeLabel = (data as any).current_time_label || null;
                agent?.reconcileParticipants?.();
                this.theme = data.theme === 'town_board' ? 'town_board' : 'live_social';
                this.knownCharacters = Array.isArray(data.known_characters) ? data.known_characters : [];
                if (!this.channels.some((channel) => channel.id === this.selectedChannelId)) {
                    this.selectedChannelId = this.channels[0]?.id || '';
                    this.messages = [];
                }
                if (this.selectedChannelId) {
                    const sinceId = (!forceFull && this.messages.length)
                        ? Math.max(...this.messages.map((message) => Number(message.id) || 0))
                        : undefined;
                    const result = await api.getMessages(
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

        static updateMessage(updated: CommonsMessage) {
            if (!updated) return;
            const index = this.messages.findIndex((m) => m.id === updated.id);
            if (index >= 0) {
                this.messages[index] = { ...this.messages[index], ...updated };
                this.emit();
            }
        }

        static removeMessage(messageId: number | string) {
            const index = this.messages.findIndex((m) => m.id === messageId);
            if (index >= 0) {
                this.messages.splice(index, 1);
                this.emit();
            }
        }

        static async selectPerspective(name: string) {
            this.perspective = name || 'User';
            this.messages = [];
            this.selectedChannelId = 'public';
            await this.sync();
        }

        static async selectTheme(theme: string) {
            const api = (window as unknown as { CommonsApi: { setTheme: (theme: string) => Promise<unknown> } }).CommonsApi;
            await api.setTheme(theme);
            await this.sync();
        }

        static async selectChannel(channelId: string, explicitRead = true) {
            if (!this.channels.some((channel) => channel.id === channelId)) return;
            this.selectedChannelId = channelId;
            this.messages = [];
            const api = (window as unknown as { CommonsApi: { readMessages: (as: string, channelId: string, mode: string) => Promise<unknown>; getMessages: (as: string, channelId: string) => Promise<CommonsApiResponse> } }).CommonsApi;
            if (explicitRead) {
                await api.readMessages(this.perspective, channelId, 'all');
                const history = await api.getMessages(this.perspective, channelId);
                this.messages = history.messages || [];
            } else {
                const result = await api.getMessages(this.perspective, channelId);
                this.messages = result.messages || [];
            }
            await this.sync();
        }

        static setPaused(paused: boolean, source: 'manual' | 'visibility' = 'manual') {
            if (source === 'visibility') this.visibilityPaused = paused;
            else this.manualPaused = paused;

            const agent = (window as unknown as { CommonsAgent: { pause: () => void; resume: () => void } }).CommonsAgent;
            if (this.isPaused) {
                agent.pause();
            } else {
                agent.resume();
            }

            if (this.visibilityPaused) this.stopLiveUpdates();
            else this.startLiveUpdates();

            const ui = (window as unknown as { CommonsUI?: { renderPauseState: () => void } }).CommonsUI;
            ui?.renderPauseState();
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

        static receiveMessage(message: CommonsMessage) {
            if (!message) return;
            const agent = (window as unknown as { CommonsAgent?: { onMessageReceived?: (message: CommonsMessage) => void } }).CommonsAgent;
            agent?.onMessageReceived?.(message);
            if (message.channel_id !== this.selectedChannelId) return;
            if (this.messages.some((existing) => existing.id === message.id)) return;
            this.messages.push(message);
            this.emit();
        }

        static _linkMessageTraces(record: CommonsTurnRecord) {
            const detail = record.detail as { messageIds?: Array<string | number> } | undefined;
            const ids = Array.isArray(detail?.messageIds) ? detail.messageIds : [];
            for (const id of ids) {
                if (id !== undefined && id !== null && id !== '') {
                    this.messageTraces[String(id)] = record;
                }
            }
        }

        static upsertLiveTurn(charName: string, turnId: string, turn: { turnId?: string; inner: string; action: string; summary: string; detail?: unknown }) {
            if (!this.characterTurns[charName]) this.characterTurns[charName] = [];
            const tickVal = this.worldClock?.time_ticks;
            const list = this.characterTurns[charName];
            const existingIdx = list.findIndex((r) => r.turnId === turnId);
            const record: CommonsTurnRecord = {
                ...(existingIdx >= 0 ? list[existingIdx] : {}),
                ...turn,
                turnId,
                timestamp: existingIdx >= 0 ? list[existingIdx].timestamp : Date.now(),
                worldTick: typeof tickVal === 'number' && Number.isFinite(tickVal) ? tickVal : (existingIdx >= 0 ? list[existingIdx].worldTick : undefined),
            };
            if (existingIdx >= 0) {
                list[existingIdx] = record;
            } else {
                list.unshift(record);
                if (list.length > 25) list.pop();
            }
            this._linkMessageTraces(record);
            this.lastActed = { charName, action: record.action, summary: record.summary, timestamp: Date.now() };
            this.emit();
        }

        static recordTurn(charName: string, turn: { turnId?: string; inner: string; action: string; summary: string; detail?: unknown }) {
            if (turn.turnId) {
                this.upsertLiveTurn(charName, turn.turnId, turn);
                return;
            }
            if (!this.characterTurns[charName]) this.characterTurns[charName] = [];
            const tickVal = this.worldClock?.time_ticks;
            const record: CommonsTurnRecord = {
                ...turn,
                timestamp: Date.now(),
                worldTick: typeof tickVal === 'number' && Number.isFinite(tickVal) ? tickVal : undefined,
            };
            this.characterTurns[charName].unshift(record);
            if (this.characterTurns[charName].length > 25) this.characterTurns[charName].pop();
            this._linkMessageTraces(record);
            this.lastActed = { charName, action: turn.action, summary: turn.summary, timestamp: Date.now() };
            this.emit();
        }

        static openDrawer(charName: string) {
            if (!charName || charName === 'User') return;
            this.selectedDrawerCharacter = charName;
            this.selectedDrawerMessageId = null;
            this.emit();
        }

        static openDrawerForMessage(charName: string, messageId: string | number) {
            if (!charName || charName === 'User') return;
            this.selectedDrawerCharacter = charName;
            this.selectedDrawerMessageId = messageId;
            this.emit();
        }

        static closeDrawer() {
            this.selectedDrawerCharacter = null;
            this.selectedDrawerMessageId = null;
            this.emit();
        }
    }

    (window as unknown as { CommonsState: typeof CommonsState }).CommonsState = CommonsState;
})();
