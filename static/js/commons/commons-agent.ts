/**
 * @module commons-agent - communication actions for existing Players
 * @contributes paced read, send, and direct-message actions
 * @powers autonomous character participation in The Commons
 * @relates CommonsApi, CommonsState, PromptBuilder, ResponseParser
 * @docs docs/virtualWorld/Gameplay/The Commons.md
 */

(function () {
    'use strict';

    class CommonsAgent {
        static timers: Record<string, ReturnType<typeof setTimeout>> = {};
        static deadlines: Record<string, number> = {};
        static remainingMs: Record<string, number> = {};
        static controllers: Record<string, AbortController> = {};
        static isRunning = false;
        static burstCounts: Record<string, number> = {};
        static participantSignature = '';

        static getTalkativeness(name: string): number {
            const config = (window as any).config;
            if (config?.getTalkativeness) return config.getTalkativeness(name);
            return (window as any).VWSimultaneous?.TALKATIVENESS_DEFAULT_SECONDS || 25;
        }

        static setTalkativeness(name: string, value: number | string, persist = false, shouldResetTimer = true): number {
            const mode = (window as any).VWSimultaneous;
            const pace = mode?.normalizeTalkativeness(value) || 25;
            const config = (window as any).config;
            if (config) config.talkativenessByCharacter[name] = pace;
            if (persist && config?.setTalkativeness) void config.setTalkativeness(name, pace);
            if (shouldResetTimer) this.resetTimer(name);
            return pace;
        }

        static randomizeTalkativeness(name: string, persist = true, shouldResetTimer = true): number {
            const mode = (window as any).VWSimultaneous;
            const min = mode?.TALKATIVENESS_MIN_SECONDS || 5;
            const max = mode?.TALKATIVENESS_MAX_SECONDS || 120;
            const pace = Math.floor(Math.random() * (max - min + 1)) + min;
            return this.setTalkativeness(name, pace, persist, shouldResetTimer);
        }

        static start() {
            this.isRunning = true;
            if (!(window as any).CommonsState.isPaused) this.scheduleAll(true);
        }

        static stop() {
            this.isRunning = false;
            this.clearScheduledTimers(false);
            for (const controller of Object.values(this.controllers)) controller.abort();
            this.controllers = {};
        }

        static pause() {
            const now = Date.now();
            for (const name of Object.keys(this.timers)) {
                this.remainingMs[name] = Math.max(0, (this.deadlines[name] || now) - now);
            }
            this.clearScheduledTimers(true);
            for (const controller of Object.values(this.controllers)) controller.abort();
        }

        static resume() {
            if (this.isRunning) this.scheduleAll();
        }

        static clearScheduledTimers(preserveRemaining: boolean) {
            for (const [name, timer] of Object.entries(this.timers)) {
                clearTimeout(timer);
                if (!preserveRemaining) delete this.remainingMs[name];
            }
            this.timers = {};
            this.deadlines = {};
            this.burstCounts = {};
        }

        static resetTimer(charName: string, extraCooldownMs: number = 0) {
            const oldTimer = this.timers[charName];
            if (oldTimer) clearTimeout(oldTimer);
            delete this.timers[charName];
            delete this.deadlines[charName];

            const state = (window as any).CommonsState;
            const participant = state.participants?.[charName];
            const pState = String(participant?.state || '').toLowerCase();
            const isUnconsciousOrSleeping = pState === 'sleeping' || pState === 'unconscious' || pState === 'dead';
            if (!this.isRunning || state.isPaused || participant?.control_mode !== 'llm' || !participant.active || participant.blocked || isUnconsciousOrSleeping) {
                delete this.remainingMs[charName];
                delete this.burstCounts[charName];
                return;
            }

            const savedRemaining = this.remainingMs[charName];
            const pace = this.getTalkativeness(charName);
            const baseCooldown = (window as any).VWSimultaneous?.jitteredCooldownMs
                ? (window as any).VWSimultaneous.jitteredCooldownMs(pace)
                : (pace * 1000);
            let delayMs = Number.isFinite(savedRemaining)
                ? Math.max(0, savedRemaining)
                : baseCooldown;
            if (extraCooldownMs > 0) {
                delayMs += extraCooldownMs;
            }
            delete this.remainingMs[charName];
            this.deadlines[charName] = Date.now() + delayMs;
            this.timers[charName] = setTimeout(async () => {
                delete this.timers[charName];
                delete this.deadlines[charName];
                let turnOutcome: any = false;
                try {
                    turnOutcome = await this.actCharacter(charName);
                } finally {
                    if (this.isRunning && !(window as any).CommonsState.isPaused) {
                        this.handlePostTurnCadence(charName, turnOutcome);
                    }
                }
            }, delayMs);
        }

        static handlePostTurnCadence(charName: string, turnOutcome: any) {
            const didPost = Boolean(turnOutcome?.didPost ?? turnOutcome);
            const playerContext = turnOutcome?.player || null;
            if (!didPost) {
                delete this.burstCounts[charName];
                this.resetTimer(charName);
                return;
            }

            const currentBurst = this.burstCounts[charName] || 0;
            const traits = playerContext?.traits || {};
            const tags = Array.isArray(playerContext?.tags) ? playerContext.tags : [];
            const hasTrait = (traitName: string) => {
                const lower = traitName.toLowerCase();
                return Boolean(traits[lower] || traits[traitName] || tags.includes(lower));
            };

            const isImpulsive = hasTrait('impulsive') || hasTrait('talkative') || hasTrait('excitable') || hasTrait('manic');
            const isReserved = hasTrait('stoic') || hasTrait('quiet') || hasTrait('reserved') || hasTrait('calm') || hasTrait('patient');

            const maxBursts = isImpulsive ? 3 : (isReserved ? 1 : 2);

            if (currentBurst < maxBursts) {
                const pace = this.getTalkativeness(charName);
                const paceFactor = Math.max(0, Math.min(1, (60 - pace) / 55));
                let burstChance = 0.08 + (paceFactor * 0.32);
                if (isImpulsive) burstChance += 0.20;
                if (isReserved) burstChance -= 0.20;
                burstChance = Math.max(0.05, Math.min(0.80, burstChance));

                if (Math.random() < burstChance) {
                    this.burstCounts[charName] = currentBurst + 1;
                    const burstDelay = Math.round(1500 + Math.random() * 2000);
                    this.remainingMs[charName] = burstDelay;
                    this.resetTimer(charName);
                    return;
                }
            }

            delete this.burstCounts[charName];
            const floorYield = currentBurst > 0 ? 8000 : 0;
            this.resetTimer(charName, floorYield);
        }
        static scheduleAll(initialStartup: boolean = false) {
            const state = (window as any).CommonsState;
            const participants = state?.participants || {};
            const config = (window as any).config;
            for (const name of Object.keys(participants)) {
                if (name === 'User') continue;
                const participant = participants[name];
                // Strictly exclude non-LLM characters (simple NPCs, humans, blocked, inactive)
                if (participant?.control_mode !== 'llm' || !participant.active || participant.blocked) continue;

                // Randomize unconfigured starting talkativeness
                if (config && (!config.talkativenessByCharacter || config.talkativenessByCharacter[name] === undefined)) {
                    this.randomizeTalkativeness(name, false, false);
                }

                // On cold start, stagger the countdown across the pace range so characters do not all fire at T=25s
                if (initialStartup && !Number.isFinite(this.remainingMs[name])) {
                    const pace = this.getTalkativeness(name);
                    const baseCooldown = (window as any).VWSimultaneous?.jitteredCooldownMs(pace) || (pace * 1000);
                    const staggeredDelay = Math.max(2000, Math.round(baseCooldown * (0.15 + Math.random() * 0.70)));
                    this.remainingMs[name] = staggeredDelay;
                }

                this.resetTimer(name);
            }
        }

        static onMessageReceived(message: any) {
            if (!message || !this.isRunning || (window as any).CommonsState?.isPaused) return;
            const author = String(message.author || '');
            const channelId = String(message.channel_id || '');
            const state = (window as any).CommonsState;
            const channel = (state?.channels || []).find((c: any) => c.id === channelId);
            if (!channel) return;
            const members: string[] = channel.kind === 'public'
                ? Object.keys(state.participants || {})
                : (channel.members || []);
            const textLower = String(message.text || '').toLowerCase();

            for (const name of members) {
                if (name === author || name === 'User') continue;
                const participant = state.participants?.[name];
                // Strictly exclude simple NPCs and non-LLM characters
                if (participant?.control_mode !== 'llm' || !participant.active || participant.blocked) continue;

                const isDm = channel.kind === 'dm';
                const nameLower = name.toLowerCase();
                const isMentioned = textLower.includes('@' + nameLower) || textLower.includes(nameLower);

                if (isDm || isMentioned) {
                    const currentDeadline = this.deadlines[name] || 0;
                    const now = Date.now();
                    const remaining = currentDeadline - now;
                    if (remaining > 3500 || !this.timers[name]) {
                        const fastTrackDelay = Math.round(1500 + Math.random() * 2000);
                        this.remainingMs[name] = fastTrackDelay;
                        this.resetTimer(name);
                    }
                }
            }
        }

        static reconcileParticipants() {
            const state = (window as any).CommonsState;
            const participants = state.participants || {};
            const signature = Object.keys(participants).sort().map(name => {
                const participant = participants[name];
                return `${name}:${participant.control_mode || 'unavailable'}:${participant.active ? 1 : 0}:${participant.blocked ? 1 : 0}`;
            }).join('|');
            if (signature === this.participantSignature) return;
            this.participantSignature = signature;
            for (const [name, controller] of Object.entries(this.controllers)) {
                const participant = participants[name];
                if (participant?.control_mode !== 'llm' || !participant.active || participant.blocked) controller.abort();
            }
            if (this.isRunning && !state.isPaused) this.scheduleAll();
        }

        static lastActedTickByChar: Record<string, number> = {};

        static _formatWorldTimeAndAgo(msgTick: unknown, playerContext: any, msgWorldDatetime?: unknown): { sent_time?: string; sent_ago: string } {
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            if (typeof msgWorldDatetime === 'string' && msgWorldDatetime) {
                const m = msgWorldDatetime.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/);
                if (m) {
                    const sent_time = `${months[(Math.max(1, Number(m[2])) - 1) % 12]} ${Number(m[3])}, ${Number(m[1])} ${m[4]}:${m[5]}`;
                    let sent_ago = 'just now';
                    if (typeof playerContext?.world_datetime === 'string' && playerContext.world_datetime) {
                        const msgMs = Date.parse(msgWorldDatetime);
                        const curMs = Date.parse(playerContext.world_datetime);
                        if (Number.isFinite(msgMs) && Number.isFinite(curMs)) {
                            const deltaSecs = Math.max(0, Math.round((curMs - msgMs) / 1000));
                            const deltaMins = Math.round(deltaSecs / 60);
                            if (deltaSecs >= 60 && deltaMins < 60) sent_ago = `${deltaMins}m ago`;
                            else if (deltaMins >= 60 && deltaMins < 1440) sent_ago = `~${Math.round(deltaMins / 60)}h ago`;
                            else if (deltaMins >= 1440) sent_ago = `~${Math.round(deltaMins / 1440)}d ago`;
                        }
                    }
                    return { sent_time, sent_ago };
                }
            }
            if (typeof msgTick !== 'number' || !Number.isFinite(msgTick)) return { sent_ago: 'just now' };
            const curTick = Number(playerContext?.time_ticks ?? 0) || 0;
            const mpt = Number(playerContext?.time_per_tick_minutes ?? 5) || 5;
            const startMin = (Number(playerContext?.clock_start_hour ?? 8) * 60) + Number(playerContext?.clock_start_minute ?? 0);
            const total = Math.round(startMin + msgTick * mpt);
            const dayMinutes = ((total % 1440) + 1440) % 1440;
            const hh = String(Math.floor(dayMinutes / 60)).padStart(2, '0');
            const mm = String(dayMinutes % 60).padStart(2, '0');
            const deltaMins = Math.max(0, Math.round((curTick - msgTick) * mpt));
            let sent_ago = 'just now';
            if (deltaMins > 5 && deltaMins < 60) sent_ago = `${deltaMins}m ago`;
            else if (deltaMins >= 60 && deltaMins < 1440) sent_ago = `~${Math.round(deltaMins / 60)}h ago`;
            else if (deltaMins >= 1440) sent_ago = `~${Math.round(deltaMins / 1440)}d ago`;

            const cfg = playerContext?.calendar_config && typeof playerContext.calendar_config === 'object' ? playerContext.calendar_config : {};
            const dpm = Math.max(1, Math.floor(Number(cfg.days_per_month) || 30));
            const mpy = Math.max(1, Math.floor(Number(cfg.months_per_year) || 12));
            const curElapsedDays = Math.floor((startMin + curTick * mpt) / 1440);
            const curGameDay = Number(playerContext?.game_day) || 1;
            const baseDay = cfg.start_year
                ? ((Number(cfg.start_year) - 1) * dpm * mpy + ((Number(cfg.start_month) || 1) - 1) * dpm + ((Number(cfg.start_day) || 1) - 1))
                : (curGameDay - curElapsedDays - 1);
            const targetElapsedDays = Math.floor(total / 1440);
            const absDay = baseDay + targetElapsedDays + 1;
            const yearIdx = Math.floor((absDay - 1) / (dpm * mpy)) + 1;
            const monthIdx = (Math.floor((absDay - 1) / dpm) % mpy) + 1;
            const dayIdx = ((absDay - 1) % dpm) + 1;
            const mname = months[((monthIdx - 1) % 12 + 12) % 12];
            const datePart = (yearIdx > 1 || cfg.start_year) ? `${mname} ${dayIdx}, ${yearIdx}` : `${mname} ${dayIdx}`;
            return { sent_time: `${datePart} ${hh}:${mm}`, sent_ago };
        }

        static async triggerAutoReplyForChannel(channel: any, sender: string) {
            const state = (window as any).CommonsState;
            const participants = state?.participants || {};
            const members: string[] = channel?.kind === 'public'
                ? Object.keys(participants)
                : (Array.isArray(channel?.members) ? channel.members : []);
            const targets = members.filter((name) => {
                if (!name || name === 'User' || name === sender) return false;
                const p = participants[name];
                if (!p || p.control_mode !== 'llm' || !p.active || p.blocked) return false;
                if (Array.isArray(p.muted_channels) ? p.muted_channels.includes(channel?.id) : Boolean(channel?.muted)) {
                    return false;
                }
                return true;
            });
            for (const name of targets) {
                await this.stepOne(name);
            }
        }

        static async stepOne(charName?: string, forceNonLlm: boolean = false) {
            const state = (window as any).CommonsState;
            const participants = state.participants || {};
            const available = Object.keys(participants).filter(n => n !== 'User' && participants[n].control_mode === 'llm' && participants[n].active && !participants[n].blocked);
            const target = charName && charName !== 'User' ? participants[charName] : null;
            const canForceManual = Boolean(charName && target && !target.blocked && target.control_mode !== 'unavailable' && (forceNonLlm || (target.control_mode === 'llm' && target.active)));
            if (!canForceManual && available.length === 0) return;
            const chosen = canForceManual
                ? charName!
                : available[Math.floor(Math.random() * available.length)];
            await this.actCharacter(chosen, true, forceNonLlm);
        }

        static communicationTools(theme: string): any[] {
            const tools: any[] = [
                { type: 'function', function: { name: 'read_chat', description: 'Read messages from a channel you belong to. Use this before responding to messages you have not seen.', parameters: { type: 'object', properties: { channel_id: { type: 'string' }, mode: { type: 'string', enum: ['all', 'latest', 'range'] }, n: { type: 'integer', minimum: 1, maximum: 20 }, from_id: { type: 'integer' }, to_id: { type: 'integer' } }, required: ['channel_id'], additionalProperties: false } } },
                { type: 'function', function: { name: 'send_chat', description: 'Send a message to a channel you belong to. Replying is optional.', parameters: { type: 'object', properties: { channel_id: { type: 'string' }, text: { type: 'string' } }, required: ['channel_id', 'text'], additionalProperties: false } } },
                { type: 'function', function: { name: 'start_dm', description: 'Start or find a direct conversation and send its first message.', parameters: { type: 'object', properties: { recipient: { type: 'string' }, text: { type: 'string' } }, required: ['recipient', 'text'], additionalProperties: false } } },
                { type: 'function', function: { name: 'recall', description: 'Actively search your memories for a specific person, event, or topic when trying to remember something.', parameters: { type: 'object', properties: { query: { type: 'string', description: 'What you are trying to remember (e.g. "7th grade sketchbook", "Evil Dead II")' } }, required: ['query'], additionalProperties: false } } },
                { type: 'function', function: { name: 'edit_message', description: 'Edit the text of a message you previously wrote in a channel. Use this to correct mistakes or clarify.', parameters: { type: 'object', properties: { message_id: { type: 'integer' }, text: { type: 'string' } }, required: ['message_id', 'text'], additionalProperties: false } } },
                { type: 'function', function: { name: 'delete_message', description: 'Retract and delete a message you previously wrote in a channel.', parameters: { type: 'object', properties: { message_id: { type: 'integer' } }, required: ['message_id'], additionalProperties: false } } },
                { type: 'function', function: { name: 'mute_chat', description: 'Mute or unmute notifications and auto-replies for a conversation you belong to.', parameters: { type: 'object', properties: { channel_id: { type: 'string' }, muted: { type: 'boolean' } }, required: ['channel_id', 'muted'], additionalProperties: false } } },
            ];
            if (theme !== 'town_board') tools.push(
                { type: 'function', function: { name: 'start_group', description: 'Create a group conversation with known characters and send its first message.', parameters: { type: 'object', properties: { group_name: { type: 'string' }, recipients: { type: 'array', items: { type: 'string' } }, text: { type: 'string' } }, required: ['group_name', 'recipients', 'text'], additionalProperties: false } } },
            );
            return tools;
        }

        static _isMemoryRecordingEnabled(): boolean {
            return (window as any).config?.commonsRecordMemories !== false;
        }

        static async executeCommunicationTool(
            charName: string, call: any, channels: any[], knownCharacters: string[], theme: string, api: any, signal: AbortSignal,
            playerContext?: any
        ): Promise<{ result: any; summary: string; readMessages: any[]; recalledMemories?: any[]; intermediatorThought?: string | null }> {
            const name = String(call?.function?.name || '');
            let args: any;
            try {
                args = typeof call?.function?.arguments === 'string' ? JSON.parse(call.function.arguments) : call?.function?.arguments;
            } catch (_) {
                return { result: { ok: false, error: 'Arguments were not valid JSON.' }, summary: '', readMessages: [] };
            }
            if (!args || typeof args !== 'object') return { result: { ok: false, error: 'Arguments must be an object.' }, summary: '', readMessages: [] };
            const channelFor = (id: unknown) => channels.find(channel => channel.id === String(id || ''));
            const text = typeof args.text === 'string' ? args.text.trim().slice(0, 4000) : '';
            try {
                if (name === 'read_chat') {
                    const channel = channelFor(args.channel_id);
                    if (!channel) throw new Error('That channel is not available to this character.');
                    const mode = ['all', 'latest', 'range'].includes(args.mode) ? args.mode : 'all';
                    const n = Math.max(1, Math.min(20, Number(args.n) || 5));
                    const read = await api.readMessages(charName, channel.id, mode, n, args.from_id, args.to_id, signal);
                    const messages = Array.isArray(read?.messages) ? read.messages : [];
                    const recentSlice = messages.slice(-20);
                    const topicQuery = recentSlice.slice(-4)
                        .map((m: any) => `${m.author || ''} ${String(m.text || '')}`.trim())
                        .filter(Boolean)
                        .join(' ')
                        .slice(0, 400);
                    let rawMemories: any[] = [];
                    let intermediatorThought: string | null = null;
                    const unreadCount = Math.max(0, Number(channel.unread_count || 0));
                    const newStartIdx = Math.max(0, recentSlice.length - unreadCount);
                    if (topicQuery) {
                        try {
                            const memRes = await api.retrieveMemories(charName, topicQuery, signal);
                            rawMemories = (Array.isArray(memRes?.memories) ? memRes.memories : []).slice(0, 6);
                            const pb = (window as any).PromptBuilder;
                            if (rawMemories.length && typeof pb?.synthesizeConsciousThought === 'function') {
                                const senders = [...new Set(recentSlice.slice(-4).map((m: any) => String(m.author || '')).filter(Boolean))];
                                const lines = recentSlice.slice(-4).map((m: any) => `${m.author}: ${String(m.text || '')}`);
                                const skipPersist = !this._isMemoryRecordingEnabled();
                                intermediatorThought = await pb.synthesizeConsciousThought(
                                    charName,
                                    String(playerContext?.current_area || 'unknown'),
                                    senders,
                                    lines,
                                    String(playerContext?.emotion || 'neutral'),
                                    rawMemories,
                                    `commons:${channel.id}:${topicQuery.slice(0, 120)}`,
                                    false,
                                    {
                                        currentTick: playerContext?.time_ticks,
                                        worldTime: playerContext?.world_time,
                                        ...(skipPersist ? { skipPersist: true } : {}),
                                    }
                                );
                            }
                        } catch (_) { /* recall/intermediator is best-effort */ }
                    }
                    const recalledTexts = rawMemories.map((mem: any) => String(mem?.text || '').trim()).filter(Boolean);
                    return {
                        result: {
                            ok: true,
                            channel: channel.name,
                            messages: recentSlice.map((message: any, idx: number) => {
                                let body = String(message.text || '');
                                if (Array.isArray(message.attachments) && message.attachments.length) {
                                    const captions = message.attachments
                                        .map((a: any) => a.caption ? `[Image: ${a.caption}]` : '[Image attachment]')
                                        .join(' ');
                                    body = body ? `${body} ${captions}` : captions;
                                }
                                const timing = this._formatWorldTimeAndAgo(message.tick, playerContext, message.world_datetime);
                                return {
                                    id: message.id,
                                    author: message.author,
                                    status: idx >= newStartIdx && unreadCount > 0 ? 'NEW' : 'earlier',
                                    tick: message.tick ?? null,
                                    sent_time: timing.sent_time,
                                    sent_ago: timing.sent_ago,
                                    text: body.slice(0, 1000),
                                    attachments: message.attachments || undefined,
                                };
                            }),
                            recalled_memories: recalledTexts,
                            intermediator_thought: intermediatorThought || undefined,
                        },
                        summary: `read ${messages.length} message${messages.length === 1 ? '' : 's'} in #${channel.name || 'chat'}`,
                        readMessages: messages,
                        recalledMemories: rawMemories,
                        intermediatorThought,
                    };
                }
                if (name === 'send_chat') {
                    const channel = channelFor(args.channel_id);
                    if (!channel) throw new Error('That channel is not available to this character.');
                    if (!text) throw new Error('Message text is required.');
                    if (channel.kind !== 'public' && Array.isArray(channel.members) && !channel.members.includes(charName)) throw new Error('This character is not a member of that channel.');
                    const posted = await api.postMessage(charName, text, channel.id, signal);
                    const postRecord = posted?.message || posted;
                    if (postRecord) (window as any).CommonsState?.receiveMessage?.(postRecord);
                    return { result: { ok: true, message_id: postRecord?.id || posted?.message?.id || posted?.id || null }, summary: `sent a message to #${channel.name || 'chat'}`, readMessages: [] };
                }
                if (name === 'start_dm') {
                    const recipient = String(args.recipient || '');
                    if (!knownCharacters.includes(recipient)) throw new Error('That recipient is not a known character.');
                    if (!text) throw new Error('Message text is required.');
                    const created = await api.createChannel({ creator: charName, kind: 'dm', other: recipient }, signal);
                    const channel = created?.channel;
                    if (!channel?.id) throw new Error('The direct conversation could not be created.');
                    const posted = await api.postMessage(charName, text, channel.id, signal);
                    const postRecord = posted?.message || posted;
                    if (postRecord) (window as any).CommonsState?.receiveMessage?.(postRecord);
                    return { result: { ok: true, channel_id: channel.id, message_id: postRecord?.id || posted?.message?.id || posted?.id || null }, summary: `started a direct conversation with ${recipient}`, readMessages: [] };
                }
                if (name === 'start_group') {
                    if (theme === 'town_board') throw new Error('Group conversations are unavailable on the town board.');
                    const groupName = String(args.group_name || '').trim().slice(0, 100);
                    const recipients: string[] = Array.isArray(args.recipients) ? [...new Set<string>(args.recipients.map(String))] : [];
                    if (!groupName || !text) throw new Error('A group name and first message are required.');
                    if (!recipients.length || recipients.some(recipient => recipient === charName || !knownCharacters.includes(recipient))) throw new Error('Choose one or more known characters other than yourself.');
                    const created = await api.createChannel({ creator: charName, kind: 'group', name: groupName, members: [charName, ...recipients] }, signal);
                    const channel = created?.channel;
                    if (!channel?.id) throw new Error('The group conversation could not be created.');
                    const posted = await api.postMessage(charName, text, channel.id, signal);
                    const postRecord = posted?.message || posted;
                    if (postRecord) (window as any).CommonsState?.receiveMessage?.(postRecord);
                    return { result: { ok: true, channel_id: channel.id, message_id: postRecord?.id || posted?.message?.id || posted?.id || null }, summary: `started group #${groupName}`, readMessages: [] };
                }
                if (name === 'recall') {
                    const query = typeof args.query === 'string' ? args.query.trim() : '';
                    if (!query) throw new Error('Recall query is required.');
                    const memRes = await api.retrieveMemories(charName, query, signal);
                    const rawMems = (Array.isArray(memRes?.memories) ? memRes.memories : []).slice(0, 6);
                    let synth: string | null = null;
                    const pb = (window as any).PromptBuilder;
                    if (rawMems.length && typeof pb?.synthesizeConsciousThought === 'function') {
                        const skipPersist = !this._isMemoryRecordingEnabled();
                        synth = await pb.synthesizeConsciousThought(
                            charName,
                            String(playerContext?.current_area || 'unknown'),
                            [],
                            [query],
                            String(playerContext?.emotion || 'neutral'),
                            rawMems,
                            `commons:recall:${query.slice(0, 120)}`,
                            false,
                            {
                                currentTick: playerContext?.time_ticks,
                                worldTime: playerContext?.world_time,
                                ...(skipPersist ? { skipPersist: true } : {}),
                            }
                        );
                    }
                    return {
                        result: {
                            ok: true,
                            recalled_memories: rawMems.map((m: any) => String(m?.text || '').trim()).filter(Boolean),
                            intermediator_thought: synth || undefined,
                        },
                        summary: `recalled memories about "${query.slice(0, 40)}"`,
                        readMessages: [],
                        recalledMemories: rawMems,
                        intermediatorThought: synth,
                    };
                }
                if (name === 'edit_message') {
                    const messageId = Number(args.message_id);
                    if (!messageId) throw new Error('A message id is required to edit.');
                    if (!text) throw new Error('New message text is required.');
                    const edited = await api.editMessage(messageId, charName, text, signal);
                    await (window as any).CommonsState?.sync?.(true);
                    return { result: { ok: true, message: edited?.message }, summary: `edited message #${messageId}`, readMessages: [] };
                }
                if (name === 'delete_message') {
                    const messageId = Number(args.message_id);
                    if (!messageId) throw new Error('A message id is required to delete.');
                    await api.deleteMessage(messageId, charName, signal);
                    await (window as any).CommonsState?.sync?.(true);
                    return { result: { ok: true, message_id: messageId }, summary: `retracted message #${messageId}`, readMessages: [] };
                }
                if (name === 'mute_chat') {
                    const channel = channelFor(args.channel_id);
                    if (!channel) throw new Error('That channel is not available to this character.');
                    if (typeof args.muted !== 'boolean') throw new Error('muted must be a boolean.');
                    const res = await api.setChannelMuted(channel.id, charName, args.muted, signal);
                    channel.muted = Boolean(res?.muted ?? args.muted);
                    await (window as any).CommonsState?.sync?.(true);
                    return {
                        result: { ok: true, channel_id: channel.id, muted: channel.muted },
                        summary: `${channel.muted ? 'muted' : 'unmuted'} #${channel.name || 'chat'}`,
                        readMessages: [],
                    };
                }
                throw new Error(`Unknown communication tool: ${name || '(empty)'}`);
            } catch (error: any) {
                if (signal.aborted) throw error;
                return { result: { ok: false, error: String(error?.message || error) }, summary: '', readMessages: [] };
            }
        }

        static async actCharacter(charName: string, isManualStep: boolean = false, forceNonLlm: boolean = false) {
            const state = (window as any).CommonsState;
            if (!isManualStep && state.isPaused) return;
            const participant = state.participants?.[charName];
            if (!participant || participant.blocked || participant.control_mode === 'unavailable') return;
            if (!forceNonLlm && (participant.control_mode !== 'llm' || !participant.active)) return;
            if (this.controllers[charName]) return;

            const controller = new AbortController();
            this.controllers[charName] = controller;
            state.actingCharacter = charName;
            (window as any).CommonsState?.emit?.();
            const signal = controller.signal;
            const api = (window as any).CommonsApi;
            const llm = (window as any).llmClient;

            try {
                const [player, memories, recentMemories, phone] = await Promise.all([
                    api.getCharacterContext(charName, signal),
                    api.retrieveMemories(charName, 'conversation friends messages group chat', signal),
                    api.getRecentMemories ? api.getRecentMemories(charName, 5, signal).catch(() => ({ memories: [] })) : Promise.resolve({ memories: [] }),
                    api.getState(charName),
                ]);
                if ((!isManualStep && state.isPaused) || signal.aborted) return;

                const combinedPreMemories: any[] = [];
                const seenMem = new Set<string>();
                for (const m of [...(recentMemories?.memories || []), ...(memories?.memories || [])]) {
                    const txt = String(m?.text || '').trim();
                    if (txt && !seenMem.has(txt)) {
                        seenMem.add(txt);
                        combinedPreMemories.push(m);
                    }
                }
                const memoryText = combinedPreMemories
                    .map((memory: any) => String(memory.text || '').trim())
                    .filter(Boolean)
                    .slice(0, 7)
                    .map((line: string) => `- ${line}`)
                    .join('\n') || '- No relevant memories recalled.';
                const channels = phone.channels || [];
                const totalUnread = channels.filter((c: any) => !c.muted).reduce((sum: number, c: any) => sum + Number(c.unread_count || 0), 0);
                const curWorldTick = Number(player?.time_ticks ?? 0) || 0;
                if (!isManualStep && totalUnread === 0 && this.lastActedTickByChar[charName] === curWorldTick) {
                    return false;
                }
                this.lastActedTickByChar[charName] = curWorldTick;
                const theme = phone.theme === 'town_board' ? 'town_board' : 'live_social';
                const knownCharacters = Array.isArray(phone.known_characters)
                    ? phone.known_characters.filter((name: string) => typeof name === 'string' && name !== charName && name !== 'User')
                    : [];
                const promptBuilder = (window as any).PromptBuilder;
                if (typeof promptBuilder?.buildCommunicationPrompt !== 'function') throw new Error('Shared character prompt module is unavailable');
                const userPrompt = promptBuilder.buildCommunicationPrompt(
                    player, memoryText, channels, knownCharacters, theme
                );
                if (!llm || typeof llm.chatWithTools !== 'function') throw new Error('LLM tool-calling client is not available');
                const messages: any[] = [
                    {
                        role: 'system',
                        content: theme === 'town_board'
                            ? 'Use the existing character identity and state in the user context. This is a town-board communication turn. Use the communication tools when useful, one at a time. Reading does not require replying. You may stop without taking an action. Do not invent physical delivery or claim messages you have not explicitly read.'
                            : 'Use the existing character identity and state in the user context. This is a phone communication turn. Use the communication tools when useful, one at a time. Reading does not require replying. You may stop without taking an action. Do not claim messages you have not explicitly read.',
                    },
                    { role: 'user', content: userPrompt },
                ];
                const tools = this.communicationTools(theme);
                const summaries: string[] = [];
                const readMessages: any[] = [];
                let recalledMemories: any[] = combinedPreMemories.slice(0, 6);
                let intermediatorThought: string | null = null;
                let inner = '';
                let didPost = false;
                const turnId = `${charName}:${Date.now()}:${Math.random().toString(36).slice(2, 6)}`;
                const unreadLabels = channels
                    .filter((c: any) => !c.muted && Number(c.unread_count || 0) > 0)
                    .map((c: any) => `${Number(c.unread_count || 0)} unread in #${c.name || c.id}`);
                const triggerSummary = unreadLabels.length
                    ? unreadLabels.join(', ')
                    : (isManualStep ? 'Manual ▶ Act trigger' : 'Ambient check');
                const traceSteps: Array<{ kind: string; label: string; detail?: string }> = [
                    { kind: 'notification', label: 'Notification', detail: triggerSummary },
                ];
                const messageIds: Array<string | number> = [];
                const pushLiveTrace = (actionLabel: string, summaryLabel: string) => {
                    state.upsertLiveTurn?.(charName, turnId, {
                        turnId,
                        inner,
                        action: actionLabel,
                        summary: summaryLabel,
                        detail: {
                            trigger: triggerSummary,
                            steps: traceSteps.map(s => ({ ...s })),
                            messageIds: [...messageIds],
                            actions: [...summaries],
                            recalledMemories,
                            intermediatorThought,
                        },
                    });
                };
                pushLiveTrace('thinking', 'Woke up on notification');
                const maxToolRounds = 6;
                for (let round = 0; round < maxToolRounds; round++) {
                    const reply = await llm.chatWithTools(messages, {
                        withTools: true, tools, tool_choice: 'auto', streaming: false, max_tokens: 360,
                        signal, label: 'commons/communication',
                    });
                    if ((!isManualStep && state.isPaused) || signal.aborted || !reply) return false;
                    if (typeof reply.content === 'string' && reply.content.trim() && (!didPost || !inner)) {
                        inner = reply.content.trim();
                        traceSteps.push({ kind: 'thought', label: 'Inner Monologue', detail: inner });
                        pushLiveTrace(summaries.length ? summaries.join(' -> ') : 'thinking', inner.slice(0, 80));
                    }
                    const calls = Array.isArray(reply.tool_calls) ? reply.tool_calls : [];
                    if (!calls.length) break;
                    messages.push({ role: 'assistant', content: reply.content || '', tool_calls: calls });
                    for (let index = 0; index < calls.length; index++) {
                        let outcome: any;
                        if (index > 0) {
                            outcome = { result: { ok: false, error: 'Only the first tool call was run. Review its result before choosing another action.' }, summary: '', readMessages: [] };
                        } else {
                            const toolName = String(calls[index]?.function?.name || '');
                            outcome = await this.executeCommunicationTool(charName, calls[index], channels, knownCharacters, theme, api, signal, player);
                            if (['send_chat', 'start_dm', 'start_group'].includes(toolName) && outcome?.result?.ok) {
                                didPost = true;
                            }
                            if (outcome.summary) summaries.push(outcome.summary);
                            if (Array.isArray(outcome.recalledMemories) && outcome.recalledMemories.length) {
                                recalledMemories = outcome.recalledMemories;
                            }
                            if (outcome.intermediatorThought) {
                                intermediatorThought = outcome.intermediatorThought;
                            }
                            const postedId = outcome?.result?.message_id ?? outcome?.result?.message?.id;
                            if (postedId !== undefined && postedId !== null && !messageIds.includes(postedId)) {
                                messageIds.push(postedId);
                            }
                            if (outcome.summary || outcome?.result?.ok) {
                                traceSteps.push({
                                    kind: ['read_chat', 'recall'].includes(toolName) ? 'recall' : 'decision',
                                    label: toolName,
                                    detail: outcome.summary || (outcome?.result?.ok ? 'ok' : String(outcome?.result?.error || '')),
                                });
                            }
                            if (outcome.intermediatorThought) {
                                traceSteps.push({
                                    kind: 'intermediator',
                                    label: 'Memory Summary (Intermediator)',
                                    detail: outcome.intermediatorThought,
                                });
                            }
                            pushLiveTrace(
                                summaries.length ? summaries.join(' -> ') : 'thinking',
                                summaries.length ? summaries.join('; ') : 'evaluating'
                            );
                            readMessages.push(...outcome.readMessages);
                        }
                        messages.push({ role: 'tool', tool_call_id: calls[index].id, content: JSON.stringify(outcome.result) });
                    }
                }
                if ((!isManualStep && state.isPaused) || signal.aborted) return;
                if (state.characterContextCache) {
                    state.characterContextCache[charName] = player;
                }
                if (typeof state.recordTurn === 'function') {
                    state.recordTurn(charName, {
                        turnId,
                        inner,
                        action: summaries.length ? summaries.join(' -> ') : 'think',
                        summary: summaries.length ? summaries.join('; ') : 'chose to stay quiet',
                        detail: {
                            trigger: triggerSummary,
                            steps: traceSteps,
                            messageIds,
                            actions: summaries,
                            recalledMemories,
                            intermediatorThought,
                        },
                    });
                }
                if (this._isMemoryRecordingEnabled() && inner && typeof api.storeMemory === 'function') {
                    const emoLabel = String(player?.emotion || 'neutral').trim();
                    const emoInt = Math.max(1, Math.min(10, Number(player?.emotion_intensity || 5)));
                    const memory_emotions = emoLabel && emoLabel !== 'neutral' ? [{ label: emoLabel, intensity: emoInt }] : undefined;
                    try {
                        await api.storeMemory(charName, inner, Math.max(5, Math.min(8, emoInt)), ['inner_monologue', 'thought'], signal, {
                            type: 'reflection',
                            tick: typeof player?.time_ticks === 'number' ? player.time_ticks : undefined,
                            memory_emotions,
                        });
                    } catch (_) { /* best-effort */ }
                }
                return { didPost, player };
            } catch (error) {
                if (!signal.aborted) {
                    const errMsg = error instanceof Error ? error.message : String(error);
                    console.error(`[CommonsAgent] Communication turn failed for ${charName}:`, error);
                    if (typeof state.recordTurn === 'function') {
                        state.recordTurn(charName, {
                            inner: '',
                            action: 'error',
                            summary: `LLM error: ${errMsg.slice(0, 120)}`,
                            detail: { error: errMsg },
                        });
                    }
                }
            } finally {
                if (this.controllers[charName] === controller) {
                    delete this.controllers[charName];
                    if (state.actingCharacter === charName) state.actingCharacter = null;
                }
                (window as any).CommonsState?.emit?.();
            }
        }
    }

    (window as any).CommonsAgent = CommonsAgent;
})();
