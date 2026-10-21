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
        static participantSignature = '';

        static getTalkativeness(name: string): number {
            const config = (window as any).config;
            if (config?.getTalkativeness) return config.getTalkativeness(name);
            return (window as any).VWSimultaneous?.TALKATIVENESS_DEFAULT_SECONDS || 25;
        }

        static setTalkativeness(name: string, value: number | string, persist = false): number {
            const mode = (window as any).VWSimultaneous;
            const pace = mode?.normalizeTalkativeness(value) || 25;
            const config = (window as any).config;
            if (config) config.talkativenessByCharacter[name] = pace;
            if (persist && config?.setTalkativeness) void config.setTalkativeness(name, pace);
            this.resetTimer(name);
            return pace;
        }

        static randomizeTalkativeness(name: string, persist = true): number {
            const mode = (window as any).VWSimultaneous;
            const min = mode?.TALKATIVENESS_MIN_SECONDS || 5;
            const max = mode?.TALKATIVENESS_MAX_SECONDS || 120;
            const pace = Math.floor(Math.random() * (max - min + 1)) + min;
            return this.setTalkativeness(name, pace, persist);
        }

        static start() {
            this.isRunning = true;
            if (!(window as any).CommonsState.isPaused) this.scheduleAll();
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
        }

        static resetTimer(charName: string) {
            const oldTimer = this.timers[charName];
            if (oldTimer) clearTimeout(oldTimer);
            delete this.timers[charName];
            delete this.deadlines[charName];

            const state = (window as any).CommonsState;
            const participant = state.participants?.[charName];
            if (!this.isRunning || state.isPaused || participant?.control_mode !== 'llm' || !participant.active || participant.blocked) {
                delete this.remainingMs[charName];
                return;
            }

            const savedRemaining = this.remainingMs[charName];
            const delayMs = Number.isFinite(savedRemaining)
                ? Math.max(0, savedRemaining)
                : (window as any).VWSimultaneous.jitteredCooldownMs(this.getTalkativeness(charName));
            delete this.remainingMs[charName];
            this.deadlines[charName] = Date.now() + delayMs;
            this.timers[charName] = setTimeout(async () => {
                delete this.timers[charName];
                delete this.deadlines[charName];
                try {
                    await this.actCharacter(charName);
                } finally {
                    if (this.isRunning && !(window as any).CommonsState.isPaused) this.resetTimer(charName);
                }
            }, delayMs);
        }

        static scheduleAll() {
            const participants = (window as any).CommonsState.participants || {};
            for (const name of Object.keys(participants)) {
                if (name !== 'User') this.resetTimer(name);
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

        static async stepOne(charName?: string) {
            const state = (window as any).CommonsState;
            const participants = state.participants || {};
            const available = Object.keys(participants).filter(n => n !== 'User' && participants[n].control_mode === 'llm' && participants[n].active && !participants[n].blocked);
            const manuallySelected = charName && available.includes(charName);
            if (!manuallySelected && available.length === 0) return;
            const chosen = manuallySelected
                ? charName
                : available[Math.floor(Math.random() * available.length)];
            await this.actCharacter(chosen, true);
        }

        static communicationTools(theme: string): any[] {
            const tools: any[] = [
                { type: 'function', function: { name: 'read_chat', description: 'Read messages from a channel you belong to. Use this before responding to messages you have not seen.', parameters: { type: 'object', properties: { channel_id: { type: 'string' }, mode: { type: 'string', enum: ['all', 'latest', 'range'] }, n: { type: 'integer', minimum: 1, maximum: 20 }, from_id: { type: 'integer' }, to_id: { type: 'integer' } }, required: ['channel_id'], additionalProperties: false } } },
                { type: 'function', function: { name: 'send_chat', description: 'Send a message to a channel you belong to. Replying is optional.', parameters: { type: 'object', properties: { channel_id: { type: 'string' }, text: { type: 'string' } }, required: ['channel_id', 'text'], additionalProperties: false } } },
                { type: 'function', function: { name: 'start_dm', description: 'Start or find a direct conversation and send its first message.', parameters: { type: 'object', properties: { recipient: { type: 'string' }, text: { type: 'string' } }, required: ['recipient', 'text'], additionalProperties: false } } },
                { type: 'function', function: { name: 'remember', description: 'Save a conversation fact or commitment worth remembering. Use only when useful.', parameters: { type: 'object', properties: { text: { type: 'string' }, importance: { type: 'integer', minimum: 1, maximum: 10 }, tags: { type: 'array', items: { type: 'string' } } }, required: ['text'], additionalProperties: false } } },
            ];
            if (theme !== 'town_board') tools.push(
                { type: 'function', function: { name: 'start_group', description: 'Create a group conversation with known characters and send its first message.', parameters: { type: 'object', properties: { group_name: { type: 'string' }, recipients: { type: 'array', items: { type: 'string' } }, text: { type: 'string' } }, required: ['group_name', 'recipients', 'text'], additionalProperties: false } } },
            );
            return tools;
        }

        static async executeCommunicationTool(
            charName: string, call: any, channels: any[], knownCharacters: string[], theme: string, api: any, signal: AbortSignal
        ): Promise<{ result: any; summary: string; readMessages: any[] }> {
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
                    return {
                        result: { ok: true, channel: channel.name, messages: messages.slice(-20).map((message: any) => ({ id: message.id, author: message.author, text: String(message.text || '').slice(0, 1000) })) },
                        summary: `read ${messages.length} message${messages.length === 1 ? '' : 's'} in #${channel.name || 'chat'}`,
                        readMessages: messages,
                    };
                }
                if (name === 'send_chat') {
                    const channel = channelFor(args.channel_id);
                    if (!channel) throw new Error('That channel is not available to this character.');
                    if (!text) throw new Error('Message text is required.');
                    if (channel.kind !== 'public' && Array.isArray(channel.members) && !channel.members.includes(charName)) throw new Error('This character is not a member of that channel.');
                    const posted = await api.postMessage(charName, text, channel.id, signal);
                    return { result: { ok: true, message_id: posted?.message?.id || posted?.id || null }, summary: `sent a message to #${channel.name || 'chat'}`, readMessages: [] };
                }
                if (name === 'start_dm') {
                    const recipient = String(args.recipient || '');
                    if (!knownCharacters.includes(recipient)) throw new Error('That recipient is not a known character.');
                    if (!text) throw new Error('Message text is required.');
                    const created = await api.createChannel({ creator: charName, kind: 'dm', other: recipient }, signal);
                    const channel = created?.channel;
                    if (!channel?.id) throw new Error('The direct conversation could not be created.');
                    const posted = await api.postMessage(charName, text, channel.id, signal);
                    return { result: { ok: true, channel_id: channel.id, message_id: posted?.message?.id || posted?.id || null }, summary: `started a direct conversation with ${recipient}`, readMessages: [] };
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
                    return { result: { ok: true, channel_id: channel.id, message_id: posted?.message?.id || posted?.id || null }, summary: `started group #${groupName}`, readMessages: [] };
                }
                if (name === 'remember') {
                    if (!text) throw new Error('Memory text is required.');
                    const importance = Math.max(1, Math.min(10, Number(args.importance) || 5));
                    const tags = Array.isArray(args.tags) ? args.tags.map(String).slice(0, 10) : ['conversation', 'chat'];
                    await api.storeMemory(charName, text, importance, tags, signal);
                    return { result: { ok: true }, summary: 'saved a conversation memory', readMessages: [] };
                }
                throw new Error(`Unknown communication tool: ${name || '(empty)'}`);
            } catch (error: any) {
                if (signal.aborted) throw error;
                return { result: { ok: false, error: String(error?.message || error) }, summary: '', readMessages: [] };
            }
        }

        static async actCharacter(charName: string, isManualStep: boolean = false) {
            const state = (window as any).CommonsState;
            if (!isManualStep && state.isPaused) return;
            const participant = state.participants?.[charName];
            if (!participant || participant.control_mode !== 'llm' || !participant.active || participant.blocked) return;
            if (this.controllers[charName]) return;

            const controller = new AbortController();
            this.controllers[charName] = controller;
            state.actingCharacter = charName;
            (window as any).CommonsState?.emit?.();
            const signal = controller.signal;
            const api = (window as any).CommonsApi;
            const llm = (window as any).llmClient;

            try {
                const [player, memories, phone] = await Promise.all([
                    api.getCharacterContext(charName, signal),
                    api.retrieveMemories(charName, 'conversation friends messages group chat', signal),
                    api.getState(charName),
                ]);
                if ((!isManualStep && state.isPaused) || signal.aborted) return;

                const memoryText = (memories.memories || [])
                    .map((memory: any) => String(memory.text || '').trim())
                    .filter(Boolean)
                    .slice(0, 5)
                    .map((line: string) => `- ${line}`)
                    .join('\n') || '- No relevant memories recalled.';
                const channels = phone.channels || [];
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
                let inner = '';
                const maxToolRounds = 6;
                for (let round = 0; round < maxToolRounds; round++) {
                    const reply = await llm.chatWithTools(messages, {
                        withTools: true, tools, tool_choice: 'auto', streaming: false, max_tokens: 360,
                        signal, label: 'commons/communication',
                    });
                    if ((!isManualStep && state.isPaused) || signal.aborted || !reply) return;
                    if (typeof reply.content === 'string') inner = reply.content.slice(0, 1000);
                    const calls = Array.isArray(reply.tool_calls) ? reply.tool_calls : [];
                    if (!calls.length) break;
                    messages.push({ role: 'assistant', content: reply.content || '', tool_calls: calls });
                    for (let index = 0; index < calls.length; index++) {
                        let outcome: any;
                        if (index > 0) {
                            outcome = { result: { ok: false, error: 'Only the first tool call was run. Review its result before choosing another action.' }, summary: '', readMessages: [] };
                        } else {
                            outcome = await this.executeCommunicationTool(charName, calls[index], channels, knownCharacters, theme, api, signal);
                            if (outcome.summary) summaries.push(outcome.summary);
                            readMessages.push(...outcome.readMessages);
                        }
                        messages.push({ role: 'tool', tool_call_id: calls[index].id, content: JSON.stringify(outcome.result) });
                    }
                }
                if ((!isManualStep && state.isPaused) || signal.aborted) return;
                if (state.characterContextCache) {
                    state.characterContextCache[charName] = player;
                }
                const memoriesToStore: string[] = [];
                if (readMessages.length) {
                    const summary = readMessages.slice(-4).map((message: any) =>
                        `${message.author}: ${String(message.text || '').replace(/[\r\n]+/g, ' ').slice(0, 180)}`
                    ).join('; ');
                    memoriesToStore.push(`I read the conversation: ${summary}.`);
                }
                if (memoriesToStore.length) {
                    await api.storeMemory(
                        charName,
                        memoriesToStore.join(' '),
                        5,
                        ['conversation', 'chat'],
                        signal
                    );
                }
                if (typeof state.recordTurn === 'function') {
                    state.recordTurn(charName, {
                        inner,
                        action: summaries.length ? summaries.join(' -> ') : 'think',
                        summary: summaries.length ? summaries.join('; ') : 'chose to stay quiet',
                        detail: { actions: summaries },
                    });
                }
            } catch (error) {
                if (!signal.aborted) console.error(`[CommonsAgent] Communication turn failed for ${charName}:`, error);
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
