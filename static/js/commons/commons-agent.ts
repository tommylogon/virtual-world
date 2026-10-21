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
            if (!this.isRunning || state.isPaused || !participant?.active || participant.blocked) {
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

        static async stepOne(charName?: string) {
            const state = (window as any).CommonsState;
            const participants = state.participants || {};
            const available = Object.keys(participants).filter(n => n !== 'User' && participants[n].active && !participants[n].blocked);
            if (available.length === 0) return;
            const chosen = (charName && available.includes(charName))
                ? charName
                : available[Math.floor(Math.random() * available.length)];
            await this.actCharacter(chosen, true);
        }

        static async actCharacter(charName: string, isManualStep: boolean = false) {
            const state = (window as any).CommonsState;
            if (!isManualStep && state.isPaused) return;
            const participant = state.participants?.[charName];
            if (!participant || !participant.active || participant.blocked) return;
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
                const responseParser = (window as any).ResponseParser;
                if (typeof promptBuilder?.buildCommunicationPrompt !== 'function'
                    || typeof responseParser?.parseCommunication !== 'function') {
                    throw new Error('Shared character prompt/parser modules are unavailable');
                }
                const userPrompt = promptBuilder.buildCommunicationPrompt(
                    player, memoryText, channels, knownCharacters, theme
                );
                if (!llm || typeof llm.chat !== 'function') throw new Error('LLM client is not available');
                const reply = await llm.chat([
                    {
                        role: 'system',
                        content: theme === 'town_board'
                            ? 'Use the existing character identity and state in the user context. This is a town-board and private-letter turn within The Commons: only choose a communication action. Do not invent physical delivery or claim messages you have not explicitly read.'
                            : 'Use the existing character identity and state in the user context. This is a phone communication turn: only choose a communication action. Do not claim messages you have not explicitly read.',
                    },
                    { role: 'user', content: userPrompt },
                ], {
                    streaming: false,
                    max_tokens: 360,
                    signal,
                    label: 'commons/communication',
                });
                if ((!isManualStep && state.isPaused) || signal.aborted || !reply) return;

                const decision = responseParser.parseCommunication(reply);
                if (decision.parseError) {
                    console.warn(`[CommonsAgent] Invalid communication decision from ${charName}: ${decision.parseError}`);
                    return;
                }

                let actionSummary = 'chose not to speak';
                if (decision.action === 'send_chat') {
                    const ch = channels.find((c: any) => c.id === decision.channelId);
                    actionSummary = `posted to #${ch?.name || 'chat'}`;
                } else if (decision.action === 'read_chat') {
                    const ch = channels.find((c: any) => c.id === decision.channelId)
                        || channels.find((c: any) => c.unread_count > 0);
                    actionSummary = `read messages in #${ch?.name || 'chat'}`;
                } else if (decision.action === 'start_dm') {
                    actionSummary = `sent direct message to ${decision.recipient || 'someone'}`;
                } else if (decision.action === 'start_group') {
                    actionSummary = `created group "${decision.groupName || 'group'}"`;
                }

                if (typeof state.recordTurn === 'function') {
                    state.recordTurn(charName, {
                        inner: decision.inner || '',
                        action: decision.action,
                        summary: actionSummary,
                        detail: {
                            text: decision.text,
                            channelId: decision.channelId,
                            recipient: decision.recipient,
                            groupName: decision.groupName,
                            memory: decision.memory,
                        }
                    });
                }
                if (state.characterContextCache) {
                    state.characterContextCache[charName] = player;
                }

                let readMessages: any[] = [];
                if (decision.action === 'read_chat') {
                    const selected = channels.find((channel: any) => channel.id === decision.channelId)
                        || channels.find((channel: any) => channel.unread_count > 0);
                    if (selected) {
                        const result = await api.readMessages(
                            charName, selected.id, decision.readMode, decision.n,
                            decision.fromId, decision.toId, signal
                        );
                        readMessages = result.messages || [];
                    }
                } else if (decision.action === 'send_chat' && decision.text) {
                    const selected = channels.find((channel: any) => channel.id === decision.channelId);
                    if (selected) await api.postMessage(charName, decision.text, selected.id, signal);
                } else if (decision.action === 'start_dm' && decision.recipient
                    && knownCharacters.includes(decision.recipient) && decision.text) {
                    const result = await api.createChannel({
                        creator: charName,
                        kind: 'dm',
                        other: decision.recipient,
                    }, signal);
                    await api.postMessage(charName, decision.text, result.channel.id, signal);
                } else if (decision.action === 'start_group' && decision.groupName
                    && theme !== 'town_board'
                    && decision.recipients.length > 0 && decision.text
                    && decision.recipients.every((name: string) => name !== charName && knownCharacters.includes(name))) {
                    const result = await api.createChannel({
                        creator: charName,
                        kind: 'group',
                        name: decision.groupName,
                        members: [charName, ...decision.recipients],
                    }, signal);
                    await api.postMessage(charName, decision.text, result.channel.id, signal);
                }

                if ((!isManualStep && state.isPaused) || signal.aborted) return;
                const memoriesToStore: string[] = [];
                if (readMessages.length) {
                    const summary = readMessages.slice(-4).map((message: any) =>
                        `${message.author}: ${String(message.text || '').replace(/[\r\n]+/g, ' ').slice(0, 180)}`
                    ).join('; ');
                    memoriesToStore.push(`I read the conversation: ${summary}.`);
                }
                if (decision.memory?.text) memoriesToStore.push(decision.memory.text);
                if (memoriesToStore.length) {
                    await api.storeMemory(
                        charName,
                        memoriesToStore.join(' '),
                        decision.memory?.importance || 5,
                        decision.memory?.tags?.length ? decision.memory.tags : ['conversation', 'chat'],
                        signal
                    );
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
