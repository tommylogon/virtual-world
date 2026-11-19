"use strict";
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
        static messages = [];
        static channels = [];
        static participants = {};
        static listeners = [];
        // Opening/inspecting the phone is read-only. Character turns start
        // only after the user explicitly resumes the conversation.
        static manualPaused = true;
        static visibilityPaused = false;
        static liveEvents = null;
        static perspective = 'User';
        static selectedChannelId = 'public';
        static theme = 'live_social';
        static useViwoState = true;
        static clockMode = 'scenario';
        static activeBranchId = 'main';
        static branches = [];
        static anchoredClock = null;
        static currentDatetime = null;
        static currentTimeLabel = null;
        static knownCharacters = [];
        static actingCharacter = null;
        static lastActed = null;
        static characterTurns = {};
        static messageTraces = {};
        static selectedDrawerCharacter = null;
        static selectedDrawerMessageId = null;
        static characterContextCache = {};
        static worldClock = {
            time_ticks: 0, time_per_tick_minutes: 5, clock_start_hour: 8, clock_start_minute: 0,
        };
        static get isPaused() {
            return this.manualPaused || this.visibilityPaused;
        }
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
        static async sync(forceFull = false) {
            try {
                const api = window.CommonsApi;
                const agent = window.CommonsAgent;
                const data = await api.getState(this.perspective);
                this.channels = data.channels || [];
                this.participants = data.participants || {};
                if (data.world_clock) {
                    this.worldClock = data.world_clock;
                }
                if (typeof data.use_viwo_state === 'boolean') {
                    this.useViwoState = data.use_viwo_state;
                }
                if (data.clock_mode === 'standalone' || data.clock_mode === 'scenario') {
                    this.clockMode = data.clock_mode;
                }
                if (typeof data.active_branch_id === 'string') {
                    this.activeBranchId = data.active_branch_id;
                }
                if (Array.isArray(data.branches)) {
                    this.branches = data.branches;
                }
                this.anchoredClock = data.anchored_clock || null;
                this.currentDatetime = data.current_datetime || null;
                this.currentTimeLabel = data.current_time_label || null;
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
                    const result = await api.getMessages(this.perspective, this.selectedChannelId, sinceId);
                    if (sinceId)
                        this.messages = [...this.messages, ...(result.messages || [])];
                    else
                        this.messages = result.messages || [];
                }
                this.emit();
            }
            catch (err) {
                console.error('[CommonsState] Sync failed:', err);
            }
        }
        static updateMessage(updated) {
            if (!updated)
                return;
            const index = this.messages.findIndex((m) => m.id === updated.id);
            if (index >= 0) {
                this.messages[index] = { ...this.messages[index], ...updated };
                this.emit();
            }
        }
        static removeMessage(messageId) {
            const index = this.messages.findIndex((m) => m.id === messageId);
            if (index >= 0) {
                this.messages.splice(index, 1);
                this.emit();
            }
        }
        static async selectPerspective(name) {
            this.perspective = name || 'User';
            this.messages = [];
            this.selectedChannelId = 'public';
            await this.sync();
        }
        static async selectTheme(theme) {
            const api = window.CommonsApi;
            await api.setTheme(theme);
            await this.sync();
        }
        static async selectChannel(channelId, explicitRead = true) {
            if (!this.channels.some((channel) => channel.id === channelId))
                return;
            this.selectedChannelId = channelId;
            this.messages = [];
            const api = window.CommonsApi;
            if (explicitRead) {
                await api.readMessages(this.perspective, channelId, 'all');
                const history = await api.getMessages(this.perspective, channelId);
                this.messages = history.messages || [];
            }
            else {
                const result = await api.getMessages(this.perspective, channelId);
                this.messages = result.messages || [];
            }
            await this.sync();
        }
        static setPaused(paused, source = 'manual') {
            if (source === 'visibility')
                this.visibilityPaused = paused;
            else
                this.manualPaused = paused;
            const agent = window.CommonsAgent;
            if (this.isPaused) {
                agent.pause();
            }
            else {
                agent.resume();
            }
            if (this.visibilityPaused)
                this.stopLiveUpdates();
            else
                this.startLiveUpdates();
            const ui = window.CommonsUI;
            ui?.renderPauseState();
            this.emit();
        }
        static liveChannel = null;
        static liveReleaseLeader = null;
        static startLiveUpdates() {
            if (this.visibilityPaused || this.liveEvents || this.liveChannel || typeof EventSource === 'undefined')
                return;
            const handleLiveEvent = (event) => {
                if (!event)
                    return;
                if (event.type === 'sse_open' || event.type === 'resync_required' || event.type === 'commons_changed') {
                    void this.sync();
                    return;
                }
                if (event.type === 'world_changed' && String(event.path || '').startsWith('/api/commons/')) {
                    void this.sync();
                }
            };
            // Pool into the origin-wide SSE leader (world_events_sse_leader +
            // BroadcastChannel('world_events')) so open Commons tabs never burn
            // extra HTTP/1.1 sockets and trigger browser fetch deadlocks.
            if (typeof BroadcastChannel !== 'undefined' && typeof navigator !== 'undefined' && navigator.locks) {
                const channel = new BroadcastChannel('world_events');
                this.liveChannel = channel;
                channel.onmessage = (e) => handleLiveEvent(e.data);
                void this.sync();
                let released = false;
                let releaseFn = null;
                this.liveReleaseLeader = () => {
                    released = true;
                    if (this.liveEvents) {
                        this.liveEvents.close();
                        this.liveEvents = null;
                    }
                    if (releaseFn) {
                        releaseFn();
                        releaseFn = null;
                    }
                };
                navigator.locks.request('world_events_sse_leader', { mode: 'exclusive' }, async () => {
                    if (released)
                        return;
                    return new Promise((resolve) => {
                        releaseFn = resolve;
                        let source = null;
                        try {
                            source = new EventSource('/api/events');
                            this.liveEvents = source;
                            source.onopen = () => {
                                const openEv = { type: 'sse_open' };
                                try {
                                    channel.postMessage(openEv);
                                }
                                catch { }
                                handleLiveEvent(openEv);
                            };
                            source.onmessage = (message) => {
                                try {
                                    const event = JSON.parse(message.data);
                                    try {
                                        channel.postMessage(event);
                                    }
                                    catch { }
                                    handleLiveEvent(event);
                                }
                                catch (error) {
                                    console.warn('[CommonsState] Ignoring malformed live event:', error);
                                }
                            };
                        }
                        catch {
                            resolve();
                            return;
                        }
                        if (typeof window !== 'undefined') {
                            window.addEventListener('beforeunload', () => {
                                try {
                                    source?.close();
                                }
                                catch { }
                                resolve();
                            }, { once: true });
                        }
                    });
                }).catch(() => { });
                return;
            }
            const source = new EventSource('/api/events');
            this.liveEvents = source;
            source.onopen = () => { void this.sync(); };
            source.onmessage = (message) => {
                try {
                    handleLiveEvent(JSON.parse(message.data));
                }
                catch (error) {
                    console.warn('[CommonsState] Ignoring malformed live event:', error);
                }
            };
        }
        static stopLiveUpdates() {
            if (this.liveReleaseLeader) {
                this.liveReleaseLeader();
                this.liveReleaseLeader = null;
            }
            if (this.liveChannel) {
                this.liveChannel.close();
                this.liveChannel = null;
            }
            this.liveEvents?.close();
            this.liveEvents = null;
        }
        static receiveMessage(message) {
            if (!message)
                return;
            const agent = window.CommonsAgent;
            agent?.onMessageReceived?.(message);
            if (message.channel_id !== this.selectedChannelId)
                return;
            if (this.messages.some((existing) => existing.id === message.id))
                return;
            this.messages.push(message);
            this.emit();
        }
        static _linkMessageTraces(record) {
            const detail = record.detail;
            const ids = Array.isArray(detail?.messageIds) ? detail.messageIds : [];
            for (const id of ids) {
                if (id !== undefined && id !== null && id !== '') {
                    this.messageTraces[String(id)] = record;
                }
            }
        }
        static upsertLiveTurn(charName, turnId, turn) {
            if (!this.characterTurns[charName])
                this.characterTurns[charName] = [];
            const tickVal = this.worldClock?.time_ticks;
            const list = this.characterTurns[charName];
            const existingIdx = list.findIndex((r) => r.turnId === turnId);
            const record = {
                ...(existingIdx >= 0 ? list[existingIdx] : {}),
                ...turn,
                turnId,
                timestamp: existingIdx >= 0 ? list[existingIdx].timestamp : Date.now(),
                worldTick: typeof tickVal === 'number' && Number.isFinite(tickVal) ? tickVal : (existingIdx >= 0 ? list[existingIdx].worldTick : undefined),
            };
            if (existingIdx >= 0) {
                list[existingIdx] = record;
            }
            else {
                list.unshift(record);
                if (list.length > 25)
                    list.pop();
            }
            this._linkMessageTraces(record);
            this.lastActed = { charName, action: record.action, summary: record.summary, timestamp: Date.now() };
            this.emit();
        }
        static recordTurn(charName, turn) {
            if (turn.turnId) {
                this.upsertLiveTurn(charName, turn.turnId, turn);
                return;
            }
            if (!this.characterTurns[charName])
                this.characterTurns[charName] = [];
            const tickVal = this.worldClock?.time_ticks;
            const record = {
                ...turn,
                timestamp: Date.now(),
                worldTick: typeof tickVal === 'number' && Number.isFinite(tickVal) ? tickVal : undefined,
            };
            this.characterTurns[charName].unshift(record);
            if (this.characterTurns[charName].length > 25)
                this.characterTurns[charName].pop();
            this._linkMessageTraces(record);
            this.lastActed = { charName, action: turn.action, summary: turn.summary, timestamp: Date.now() };
            this.emit();
        }
        static openDrawer(charName) {
            if (!charName || charName === 'User')
                return;
            this.selectedDrawerCharacter = charName;
            this.selectedDrawerMessageId = null;
            this.emit();
        }
        static openDrawerForMessage(charName, messageId) {
            if (!charName || charName === 'User')
                return;
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
    window.CommonsState = CommonsState;
})();
