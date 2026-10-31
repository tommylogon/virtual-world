"use strict";
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
        static timers = {};
        static deadlines = {};
        static remainingMs = {};
        static controllers = {};
        static isRunning = false;
        static burstCounts = {};
        static participantSignature = '';
        static getTalkativeness(name) {
            const config = window.config;
            if (config?.getTalkativeness)
                return config.getTalkativeness(name);
            return window.VWSimultaneous?.TALKATIVENESS_DEFAULT_SECONDS || 25;
        }
        static setTalkativeness(name, value, persist = false, shouldResetTimer = true) {
            const mode = window.VWSimultaneous;
            const pace = mode?.normalizeTalkativeness(value) || 25;
            const config = window.config;
            if (config)
                config.talkativenessByCharacter[name] = pace;
            if (persist && config?.setTalkativeness)
                void config.setTalkativeness(name, pace);
            if (shouldResetTimer)
                this.resetTimer(name);
            return pace;
        }
        static randomizeTalkativeness(name, persist = true, shouldResetTimer = true) {
            const mode = window.VWSimultaneous;
            const min = mode?.TALKATIVENESS_MIN_SECONDS || 5;
            const max = mode?.TALKATIVENESS_MAX_SECONDS || 120;
            const pace = Math.floor(Math.random() * (max - min + 1)) + min;
            return this.setTalkativeness(name, pace, persist, shouldResetTimer);
        }
        static start() {
            this.isRunning = true;
            if (!window.CommonsState.isPaused)
                this.scheduleAll(true);
        }
        static stop() {
            this.isRunning = false;
            this.clearScheduledTimers(false);
            for (const controller of Object.values(this.controllers))
                controller.abort();
            this.controllers = {};
        }
        static pause() {
            const now = Date.now();
            for (const name of Object.keys(this.timers)) {
                this.remainingMs[name] = Math.max(0, (this.deadlines[name] || now) - now);
            }
            this.clearScheduledTimers(true);
            for (const controller of Object.values(this.controllers))
                controller.abort();
        }
        static resume() {
            if (this.isRunning)
                this.scheduleAll();
        }
        static clearScheduledTimers(preserveRemaining) {
            for (const [name, timer] of Object.entries(this.timers)) {
                clearTimeout(timer);
                if (!preserveRemaining)
                    delete this.remainingMs[name];
            }
            this.timers = {};
            this.deadlines = {};
            this.burstCounts = {};
        }
        static resetTimer(charName, extraCooldownMs = 0) {
            const oldTimer = this.timers[charName];
            if (oldTimer)
                clearTimeout(oldTimer);
            delete this.timers[charName];
            delete this.deadlines[charName];
            const state = window.CommonsState;
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
            const baseCooldown = window.VWSimultaneous?.jitteredCooldownMs
                ? window.VWSimultaneous.jitteredCooldownMs(pace)
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
                let turnOutcome = false;
                try {
                    turnOutcome = await this.actCharacter(charName);
                }
                finally {
                    if (this.isRunning && !window.CommonsState.isPaused) {
                        this.handlePostTurnCadence(charName, turnOutcome);
                    }
                }
            }, delayMs);
        }
        static handlePostTurnCadence(charName, turnOutcome) {
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
            const hasTrait = (traitName) => {
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
                if (isImpulsive)
                    burstChance += 0.20;
                if (isReserved)
                    burstChance -= 0.20;
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
        static scheduleAll(initialStartup = false) {
            const state = window.CommonsState;
            const participants = state?.participants || {};
            const config = window.config;
            for (const name of Object.keys(participants)) {
                if (name === 'User')
                    continue;
                const participant = participants[name];
                // Strictly exclude non-LLM characters (simple NPCs, humans, blocked, inactive)
                if (participant?.control_mode !== 'llm' || !participant.active || participant.blocked)
                    continue;
                // Randomize unconfigured starting talkativeness
                if (config && (!config.talkativenessByCharacter || config.talkativenessByCharacter[name] === undefined)) {
                    this.randomizeTalkativeness(name, false, false);
                }
                // On cold start, stagger the countdown across the pace range so characters do not all fire at T=25s
                if (initialStartup && !Number.isFinite(this.remainingMs[name])) {
                    const pace = this.getTalkativeness(name);
                    const baseCooldown = window.VWSimultaneous?.jitteredCooldownMs(pace) || (pace * 1000);
                    const staggeredDelay = Math.max(2000, Math.round(baseCooldown * (0.15 + Math.random() * 0.70)));
                    this.remainingMs[name] = staggeredDelay;
                }
                this.resetTimer(name);
            }
        }
        static onMessageReceived(message) {
            if (!message || !this.isRunning || window.CommonsState?.isPaused)
                return;
            const author = String(message.author || '');
            const channelId = String(message.channel_id || '');
            const state = window.CommonsState;
            const channel = (state?.channels || []).find((c) => c.id === channelId);
            if (!channel)
                return;
            const members = channel.kind === 'public'
                ? Object.keys(state.participants || {})
                : (channel.members || []);
            const textLower = String(message.text || '').toLowerCase();
            for (const name of members) {
                if (name === author || name === 'User')
                    continue;
                const participant = state.participants?.[name];
                // Strictly exclude simple NPCs and non-LLM characters
                if (participant?.control_mode !== 'llm' || !participant.active || participant.blocked)
                    continue;
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
            const state = window.CommonsState;
            const participants = state.participants || {};
            const signature = Object.keys(participants).sort().map(name => {
                const participant = participants[name];
                return `${name}:${participant.control_mode || 'unavailable'}:${participant.active ? 1 : 0}:${participant.blocked ? 1 : 0}`;
            }).join('|');
            if (signature === this.participantSignature)
                return;
            this.participantSignature = signature;
            for (const [name, controller] of Object.entries(this.controllers)) {
                const participant = participants[name];
                if (participant?.control_mode !== 'llm' || !participant.active || participant.blocked)
                    controller.abort();
            }
            if (this.isRunning && !state.isPaused)
                this.scheduleAll();
        }
        static async stepOne(charName) {
            const state = window.CommonsState;
            const participants = state.participants || {};
            const available = Object.keys(participants).filter(n => n !== 'User' && participants[n].control_mode === 'llm' && participants[n].active && !participants[n].blocked);
            const manuallySelected = charName && available.includes(charName);
            if (!manuallySelected && available.length === 0)
                return;
            const chosen = manuallySelected
                ? charName
                : available[Math.floor(Math.random() * available.length)];
            await this.actCharacter(chosen, true);
        }
        static communicationTools(theme) {
            const tools = [
                { type: 'function', function: { name: 'read_chat', description: 'Read messages from a channel you belong to. Use this before responding to messages you have not seen.', parameters: { type: 'object', properties: { channel_id: { type: 'string' }, mode: { type: 'string', enum: ['all', 'latest', 'range'] }, n: { type: 'integer', minimum: 1, maximum: 20 }, from_id: { type: 'integer' }, to_id: { type: 'integer' } }, required: ['channel_id'], additionalProperties: false } } },
                { type: 'function', function: { name: 'send_chat', description: 'Send a message to a channel you belong to. Replying is optional.', parameters: { type: 'object', properties: { channel_id: { type: 'string' }, text: { type: 'string' } }, required: ['channel_id', 'text'], additionalProperties: false } } },
                { type: 'function', function: { name: 'start_dm', description: 'Start or find a direct conversation and send its first message.', parameters: { type: 'object', properties: { recipient: { type: 'string' }, text: { type: 'string' } }, required: ['recipient', 'text'], additionalProperties: false } } },
                { type: 'function', function: { name: 'remember', description: 'Save a conversation fact or commitment worth remembering. Use only when useful.', parameters: { type: 'object', properties: { text: { type: 'string' }, importance: { type: 'integer', minimum: 1, maximum: 10 }, tags: { type: 'array', items: { type: 'string' } } }, required: ['text'], additionalProperties: false } } },
            ];
            if (theme !== 'town_board')
                tools.push({ type: 'function', function: { name: 'start_group', description: 'Create a group conversation with known characters and send its first message.', parameters: { type: 'object', properties: { group_name: { type: 'string' }, recipients: { type: 'array', items: { type: 'string' } }, text: { type: 'string' } }, required: ['group_name', 'recipients', 'text'], additionalProperties: false } } });
            return tools;
        }
        static async executeCommunicationTool(charName, call, channels, knownCharacters, theme, api, signal) {
            const name = String(call?.function?.name || '');
            let args;
            try {
                args = typeof call?.function?.arguments === 'string' ? JSON.parse(call.function.arguments) : call?.function?.arguments;
            }
            catch (_) {
                return { result: { ok: false, error: 'Arguments were not valid JSON.' }, summary: '', readMessages: [] };
            }
            if (!args || typeof args !== 'object')
                return { result: { ok: false, error: 'Arguments must be an object.' }, summary: '', readMessages: [] };
            const channelFor = (id) => channels.find(channel => channel.id === String(id || ''));
            const text = typeof args.text === 'string' ? args.text.trim().slice(0, 4000) : '';
            try {
                if (name === 'read_chat') {
                    const channel = channelFor(args.channel_id);
                    if (!channel)
                        throw new Error('That channel is not available to this character.');
                    const mode = ['all', 'latest', 'range'].includes(args.mode) ? args.mode : 'all';
                    const n = Math.max(1, Math.min(20, Number(args.n) || 5));
                    const read = await api.readMessages(charName, channel.id, mode, n, args.from_id, args.to_id, signal);
                    const messages = Array.isArray(read?.messages) ? read.messages : [];
                    return {
                        result: { ok: true, channel: channel.name, messages: messages.slice(-20).map((message) => ({ id: message.id, author: message.author, text: String(message.text || '').slice(0, 1000) })) },
                        summary: `read ${messages.length} message${messages.length === 1 ? '' : 's'} in #${channel.name || 'chat'}`,
                        readMessages: messages,
                    };
                }
                if (name === 'send_chat') {
                    const channel = channelFor(args.channel_id);
                    if (!channel)
                        throw new Error('That channel is not available to this character.');
                    if (!text)
                        throw new Error('Message text is required.');
                    if (channel.kind !== 'public' && Array.isArray(channel.members) && !channel.members.includes(charName))
                        throw new Error('This character is not a member of that channel.');
                    const posted = await api.postMessage(charName, text, channel.id, signal);
                    const postRecord = posted?.message || posted;
                    if (postRecord)
                        window.CommonsState?.receiveMessage?.(postRecord);
                    return { result: { ok: true, message_id: postRecord?.id || posted?.message?.id || posted?.id || null }, summary: `sent a message to #${channel.name || 'chat'}`, readMessages: [] };
                }
                if (name === 'start_dm') {
                    const recipient = String(args.recipient || '');
                    if (!knownCharacters.includes(recipient))
                        throw new Error('That recipient is not a known character.');
                    if (!text)
                        throw new Error('Message text is required.');
                    const created = await api.createChannel({ creator: charName, kind: 'dm', other: recipient }, signal);
                    const channel = created?.channel;
                    if (!channel?.id)
                        throw new Error('The direct conversation could not be created.');
                    const posted = await api.postMessage(charName, text, channel.id, signal);
                    const postRecord = posted?.message || posted;
                    if (postRecord)
                        window.CommonsState?.receiveMessage?.(postRecord);
                    return { result: { ok: true, channel_id: channel.id, message_id: postRecord?.id || posted?.message?.id || posted?.id || null }, summary: `started a direct conversation with ${recipient}`, readMessages: [] };
                }
                if (name === 'start_group') {
                    if (theme === 'town_board')
                        throw new Error('Group conversations are unavailable on the town board.');
                    const groupName = String(args.group_name || '').trim().slice(0, 100);
                    const recipients = Array.isArray(args.recipients) ? [...new Set(args.recipients.map(String))] : [];
                    if (!groupName || !text)
                        throw new Error('A group name and first message are required.');
                    if (!recipients.length || recipients.some(recipient => recipient === charName || !knownCharacters.includes(recipient)))
                        throw new Error('Choose one or more known characters other than yourself.');
                    const created = await api.createChannel({ creator: charName, kind: 'group', name: groupName, members: [charName, ...recipients] }, signal);
                    const channel = created?.channel;
                    if (!channel?.id)
                        throw new Error('The group conversation could not be created.');
                    const posted = await api.postMessage(charName, text, channel.id, signal);
                    const postRecord = posted?.message || posted;
                    if (postRecord)
                        window.CommonsState?.receiveMessage?.(postRecord);
                    return { result: { ok: true, channel_id: channel.id, message_id: postRecord?.id || posted?.message?.id || posted?.id || null }, summary: `started group #${groupName}`, readMessages: [] };
                }
                if (name === 'remember') {
                    if (!text)
                        throw new Error('Memory text is required.');
                    const importance = Math.max(1, Math.min(10, Number(args.importance) || 5));
                    const tags = Array.isArray(args.tags) ? args.tags.map(String).slice(0, 10) : ['conversation', 'chat'];
                    await api.storeMemory(charName, text, importance, tags, signal);
                    return { result: { ok: true }, summary: 'saved a conversation memory', readMessages: [] };
                }
                throw new Error(`Unknown communication tool: ${name || '(empty)'}`);
            }
            catch (error) {
                if (signal.aborted)
                    throw error;
                return { result: { ok: false, error: String(error?.message || error) }, summary: '', readMessages: [] };
            }
        }
        static async actCharacter(charName, isManualStep = false) {
            const state = window.CommonsState;
            if (!isManualStep && state.isPaused)
                return;
            const participant = state.participants?.[charName];
            if (!participant || participant.control_mode !== 'llm' || !participant.active || participant.blocked)
                return;
            if (this.controllers[charName])
                return;
            const controller = new AbortController();
            this.controllers[charName] = controller;
            state.actingCharacter = charName;
            window.CommonsState?.emit?.();
            const signal = controller.signal;
            const api = window.CommonsApi;
            const llm = window.llmClient;
            try {
                const [player, memories, phone] = await Promise.all([
                    api.getCharacterContext(charName, signal),
                    api.retrieveMemories(charName, 'conversation friends messages group chat', signal),
                    api.getState(charName),
                ]);
                if ((!isManualStep && state.isPaused) || signal.aborted)
                    return;
                const memoryText = (memories.memories || [])
                    .map((memory) => String(memory.text || '').trim())
                    .filter(Boolean)
                    .slice(0, 5)
                    .map((line) => `- ${line}`)
                    .join('\n') || '- No relevant memories recalled.';
                const channels = phone.channels || [];
                const theme = phone.theme === 'town_board' ? 'town_board' : 'live_social';
                const knownCharacters = Array.isArray(phone.known_characters)
                    ? phone.known_characters.filter((name) => typeof name === 'string' && name !== charName && name !== 'User')
                    : [];
                const promptBuilder = window.PromptBuilder;
                if (typeof promptBuilder?.buildCommunicationPrompt !== 'function')
                    throw new Error('Shared character prompt module is unavailable');
                const userPrompt = promptBuilder.buildCommunicationPrompt(player, memoryText, channels, knownCharacters, theme);
                if (!llm || typeof llm.chatWithTools !== 'function')
                    throw new Error('LLM tool-calling client is not available');
                const messages = [
                    {
                        role: 'system',
                        content: theme === 'town_board'
                            ? 'Use the existing character identity and state in the user context. This is a town-board communication turn. Use the communication tools when useful, one at a time. Reading does not require replying. You may stop without taking an action. Do not invent physical delivery or claim messages you have not explicitly read.'
                            : 'Use the existing character identity and state in the user context. This is a phone communication turn. Use the communication tools when useful, one at a time. Reading does not require replying. You may stop without taking an action. Do not claim messages you have not explicitly read.',
                    },
                    { role: 'user', content: userPrompt },
                ];
                const tools = this.communicationTools(theme);
                const summaries = [];
                const readMessages = [];
                let inner = '';
                let didPost = false;
                const maxToolRounds = 6;
                for (let round = 0; round < maxToolRounds; round++) {
                    const reply = await llm.chatWithTools(messages, {
                        withTools: true, tools, tool_choice: 'auto', streaming: false, max_tokens: 360,
                        signal, label: 'commons/communication',
                    });
                    if ((!isManualStep && state.isPaused) || signal.aborted || !reply)
                        return false;
                    if (typeof reply.content === 'string')
                        inner = reply.content;
                    const calls = Array.isArray(reply.tool_calls) ? reply.tool_calls : [];
                    if (!calls.length)
                        break;
                    messages.push({ role: 'assistant', content: reply.content || '', tool_calls: calls });
                    for (let index = 0; index < calls.length; index++) {
                        let outcome;
                        if (index > 0) {
                            outcome = { result: { ok: false, error: 'Only the first tool call was run. Review its result before choosing another action.' }, summary: '', readMessages: [] };
                        }
                        else {
                            const toolName = String(calls[index]?.function?.name || '');
                            outcome = await this.executeCommunicationTool(charName, calls[index], channels, knownCharacters, theme, api, signal);
                            if (['send_chat', 'start_dm', 'start_group'].includes(toolName) && outcome?.result?.ok) {
                                didPost = true;
                            }
                            if (outcome.summary)
                                summaries.push(outcome.summary);
                            readMessages.push(...outcome.readMessages);
                        }
                        messages.push({ role: 'tool', tool_call_id: calls[index].id, content: JSON.stringify(outcome.result) });
                    }
                }
                if ((!isManualStep && state.isPaused) || signal.aborted)
                    return;
                if (state.characterContextCache) {
                    state.characterContextCache[charName] = player;
                }
                const memoriesToStore = [];
                if (readMessages.length) {
                    const summary = readMessages.slice(-4).map((message) => `${message.author}: ${String(message.text || '').replace(/[\r\n]+/g, ' ')}`).join('; ');
                    memoriesToStore.push(`I read the conversation: ${summary}.`);
                }
                if (memoriesToStore.length) {
                    await api.storeMemory(charName, memoriesToStore.join(' '), 5, ['conversation', 'chat'], signal);
                }
                if (typeof state.recordTurn === 'function') {
                    state.recordTurn(charName, {
                        inner,
                        action: summaries.length ? summaries.join(' -> ') : 'think',
                        summary: summaries.length ? summaries.join('; ') : 'chose to stay quiet',
                        detail: { actions: summaries },
                    });
                }
                return { didPost, player };
            }
            catch (error) {
                if (!signal.aborted)
                    console.error(`[CommonsAgent] Communication turn failed for ${charName}:`, error);
            }
            finally {
                if (this.controllers[charName] === controller) {
                    delete this.controllers[charName];
                    if (state.actingCharacter === charName)
                        state.actingCharacter = null;
                }
                window.CommonsState?.emit?.();
            }
        }
    }
    window.CommonsAgent = CommonsAgent;
})();
