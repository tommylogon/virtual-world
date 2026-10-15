"use strict";
/**
 * @module commons-agent — communication actions for existing Players
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
        static getTalkativeness(name) {
            const config = window.config;
            if (config?.getTalkativeness)
                return config.getTalkativeness(name);
            return window.VWSimultaneous?.TALKATIVENESS_DEFAULT_SECONDS || 25;
        }
        static setTalkativeness(name, value, persist = false) {
            const mode = window.VWSimultaneous;
            const pace = mode?.normalizeTalkativeness(value) || 25;
            const config = window.config;
            if (config)
                config.talkativenessByCharacter[name] = pace;
            if (persist && config?.setTalkativeness)
                void config.setTalkativeness(name, pace);
            this.resetTimer(name);
            return pace;
        }
        static start() {
            this.isRunning = true;
            if (!window.CommonsState.isPaused)
                this.scheduleAll();
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
        }
        static resetTimer(charName) {
            const oldTimer = this.timers[charName];
            if (oldTimer)
                clearTimeout(oldTimer);
            delete this.timers[charName];
            delete this.deadlines[charName];
            const state = window.CommonsState;
            const participant = state.participants?.[charName];
            if (!this.isRunning || state.isPaused || !participant?.active || participant.blocked) {
                delete this.remainingMs[charName];
                return;
            }
            const savedRemaining = this.remainingMs[charName];
            const delayMs = Number.isFinite(savedRemaining)
                ? Math.max(0, savedRemaining)
                : window.VWSimultaneous.jitteredCooldownMs(this.getTalkativeness(charName));
            delete this.remainingMs[charName];
            this.deadlines[charName] = Date.now() + delayMs;
            this.timers[charName] = setTimeout(async () => {
                delete this.timers[charName];
                delete this.deadlines[charName];
                try {
                    await this.actCharacter(charName);
                }
                finally {
                    if (this.isRunning && !window.CommonsState.isPaused)
                        this.resetTimer(charName);
                }
            }, delayMs);
        }
        static scheduleAll() {
            const participants = window.CommonsState.participants || {};
            for (const name of Object.keys(participants)) {
                if (name !== 'User')
                    this.resetTimer(name);
            }
        }
        static async stepOne() {
            const state = window.CommonsState;
            if (state.isPaused)
                return;
            const participants = state.participants || {};
            const available = Object.keys(participants).filter(n => n !== 'User' && participants[n].active && !participants[n].blocked);
            if (available.length === 0)
                return;
            const chosen = available[Math.floor(Math.random() * available.length)];
            await this.actCharacter(chosen);
        }
        static async actCharacter(charName) {
            const state = window.CommonsState;
            if (state.isPaused)
                return;
            const participant = state.participants?.[charName];
            if (!participant || !participant.active || participant.blocked)
                return;
            if (this.controllers[charName])
                return;
            const controller = new AbortController();
            this.controllers[charName] = controller;
            const signal = controller.signal;
            const api = window.CommonsApi;
            const llm = window.llmClient;
            try {
                const [player, memories, phone] = await Promise.all([
                    api.getCharacterContext(charName, signal),
                    api.retrieveMemories(charName, 'conversation friends messages group chat', signal),
                    api.getState(charName),
                ]);
                if (state.isPaused || signal.aborted)
                    return;
                const memoryText = (memories.memories || [])
                    .map((memory) => String(memory.text || '').trim())
                    .filter(Boolean)
                    .slice(0, 5)
                    .map((line) => `- ${line}`)
                    .join('\n') || '- No relevant memories recalled.';
                const channels = phone.channels || [];
                const knownCharacters = Object.keys(phone.participants || {})
                    .filter((name) => name !== charName && name !== 'User');
                const promptBuilder = window.PromptBuilder;
                const responseParser = window.ResponseParser;
                if (typeof promptBuilder?.buildCommunicationPrompt !== 'function'
                    || typeof responseParser?.parseCommunication !== 'function') {
                    throw new Error('Shared character prompt/parser modules are unavailable');
                }
                const userPrompt = promptBuilder.buildCommunicationPrompt(player, memoryText, channels, knownCharacters);
                if (!llm || typeof llm.chat !== 'function')
                    throw new Error('LLM client is not available');
                const reply = await llm.chat([
                    {
                        role: 'system',
                        content: 'Use the existing character identity and state in the user context. This is a phone communication turn: only choose a communication action. Do not claim messages you have not explicitly read.',
                    },
                    { role: 'user', content: userPrompt },
                ], {
                    streaming: false,
                    max_tokens: 360,
                    signal,
                    label: 'commons/communication',
                });
                if (state.isPaused || signal.aborted || !reply)
                    return;
                const decision = responseParser.parseCommunication(reply);
                if (decision.parseError) {
                    console.warn(`[CommonsAgent] Invalid communication decision from ${charName}: ${decision.parseError}`);
                    return;
                }
                let readMessages = [];
                if (decision.action === 'read_chat') {
                    const selected = channels.find((channel) => channel.id === decision.channelId)
                        || channels.find((channel) => channel.unread_count > 0);
                    if (selected) {
                        const result = await api.readMessages(charName, selected.id, decision.readMode, decision.n, decision.fromId, decision.toId, signal);
                        readMessages = result.messages || [];
                    }
                }
                else if (decision.action === 'send_chat' && decision.text) {
                    const selected = channels.find((channel) => channel.id === decision.channelId);
                    if (selected)
                        await api.postMessage(charName, decision.text, selected.id, signal);
                }
                else if (decision.action === 'start_dm' && decision.recipient
                    && knownCharacters.includes(decision.recipient) && decision.text) {
                    const result = await api.createChannel({
                        creator: charName,
                        kind: 'dm',
                        other: decision.recipient,
                    }, signal);
                    await api.postMessage(charName, decision.text, result.channel.id, signal);
                }
                if (state.isPaused || signal.aborted)
                    return;
                const memoriesToStore = [];
                if (readMessages.length) {
                    const summary = readMessages.slice(-4).map((message) => `${message.author}: ${String(message.text || '').replace(/[\r\n]+/g, ' ').slice(0, 180)}`).join('; ');
                    memoriesToStore.push(`I read the conversation: ${summary}.`);
                }
                if (decision.memory?.text)
                    memoriesToStore.push(decision.memory.text);
                if (memoriesToStore.length) {
                    await api.storeMemory(charName, memoriesToStore.join(' '), decision.memory?.importance || 5, decision.memory?.tags?.length ? decision.memory.tags : ['conversation', 'chat'], signal);
                }
            }
            catch (error) {
                if (!signal.aborted)
                    console.error(`[CommonsAgent] Communication turn failed for ${charName}:`, error);
            }
            finally {
                if (this.controllers[charName] === controller)
                    delete this.controllers[charName];
            }
        }
    }
    window.CommonsAgent = CommonsAgent;
})();
