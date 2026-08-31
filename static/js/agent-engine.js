/**
 * AgentEngine — Character agent loop, turn management, and LLM orchestration
 * With thought->act->react, rest-skip, rate limiter, planning, and memory reflection
 */

const NOOP_VERBS = ['wait', 'nothing', 'pause', 'stay'];

// task-104: after a SUCCESSFUL action, the agent may chain ONE immediate
// follow-up from the verb list (same-turn, like the original dash chain).
// The LLM answers a quick decision prompt; invalid picks are discarded.
const CHAIN_RULES = {
    dash: ['go', 'wait'],
    lead: ['go', 'approach', 'release', 'wait'],
    grab: ['approach', 'release', 'wait'],
};

/** Possessive pronoun for a character, from its identity tags (female/male). */
function _possessivePronoun(name) {
    const tags = (worldState.players?.[name]?.tags) || [];
    if (tags.includes('female') || tags.includes('woman') || tags.includes('girl')) return 'her';
    if (tags.includes('male') || tags.includes('man') || tags.includes('boy')) return 'his';
    return 'their';
}

class AgentEngine {
    constructor() {
        this.characterHistories = {};
        this.turnQueue = [];
        this.currentTurnIndex = 0;
        this.turnNumber = 0;
        this.initiativeRolls = {};
        this._lastActionTime = 0;
        this.contextMgr = new ContextWindowManager({ maxTokens: 9500, maxMessages: 30, recentTurnCount: 6, criticalContextRetention: true });
        this._rateLimiter = new RateLimiter();
        this._stepping = false;
        this._cancelRequested = false;
        this._abortController = null;
        // task-101 experimental simultaneous mode: per-character act countdowns
        this._simCountdowns = {};
    }

    getHistory(charName) {
        if (!this.characterHistories[charName]) {
            const player = worldState.data?.players?.[charName];
            this.characterHistories[charName] = [{ role: 'system', content: PromptBuilder.buildCharacterSystemPrompt(charName, player, config.softMaxTokens) }];
        }
        return this.characterHistories[charName];
    }
    getDisplayHistory(charName) { return this.getHistory(charName).slice(1); }

    /** Current graph area node id for a character (entity link for memories). */
    _currentAreaEntityId(charName) {
        const area = worldState.data?.players?.[charName]?.current_area;
        if (!area) return '';
        return `area_${area.toLowerCase().replace(/\s+/g, '_')}`;
    }

    initializeTurnQueue() {
        TurnQueue.initialize();
    }

    async advanceTurn() {
        await TurnQueue.advance();
        events.renderQueueStrip();
    }
    getCurrentTurnCharacter() { return TurnQueue.getCurrentCharacter(); }

    async generatePlan(charName) {
        return PlanManager.generate(charName);
    }

    async reflect(charName) {
        await AgentMemory.reflect(charName);
    }

    _checkCancel() {
        if (!this._cancelRequested) return false;
        this._cancelRequested = false;
        if (this._abortController) { this._abortController.abort(); this._abortController = null; }
        config.busy = false;
        VW?.ui?.updateButtons();
        VW?.ui?.stopRateLimitMonitor();
        events.log("⏹️ Step cancelled.", "system-msg");
        VW?.ui?.showPlayPause(true, false);
        return true;
    }

    cancel() {
        this._cancelRequested = true;
        if (this._abortController) { this._abortController.abort(); this._abortController = null; }
        config.busy = false;
        config.running = false;
        VW?.ui?.updateButtons();
        VW?.ui?.stopRateLimitMonitor();
        VW?.ui?.setStatus("Cancelled.", "info");
        VW?.ui?.showPlayPause(true, false);
    }

    /** Common turn-end cleanup: log, clear busy, advance queue if needed. */
    async _endTurnEarly(logMsg, logClass = 'system-msg') {
        if (logMsg) events.log(logMsg, logClass);
        config.busy = false;
        VW?.ui?.updateButtons();
        if (config.running && config.turnBased && this.turnQueue.length > 0) {
            await TurnQueue.advance();
            if (worldState.data) VW?.ui?.renderAll(worldState.data);
        }
    }

    /**
     * Surface a character's freshly generated turn events (from the last
     * endTurn fetch) on the main stream.
     *
     * The 👾 lines are the SOLE surfacing mechanism for simple NPCs (they have
     * no dedicated thought/speech/action logging). LLM agents + humans already
     * surface everything through their own paths — thoughts, speech, action
     * results, emotes — and the backend ALSO records speak/emote as turn_events
     * for them, so re-logging here would double-post. Therefore only simple
     * NPCs ever get 👾 output.
     */
    _logActorTurnEvents(charName) {
        if (!charName) return false;
        const freshState = worldState.data;
        if (!freshState?.players?.[charName]?.simple_npc) return false;
        const npcEvents = (freshState?.turn_events || []).filter(evt => evt.actor === charName);
        if (npcEvents.length > 0) {
            for (const evt of npcEvents.slice(-5)) {
                events.log(`👾 ${evt.actor} ${evt.action}: ${evt.description}`, 'system-msg');
            }
            return true;
        }
        events.log(`👾 ${charName} did nothing this turn.`, 'system-msg');
        return false;
    }

    _isNoopAction(action) {
        return NOOP_VERBS.includes((action || '').split(' ')[0].toLowerCase());
    }

    async _speakLine(charName, player, speech, volume = 'say', target = null) {
        const v = volume || 'say';
        events.trackPhase(charName, 'speech', { speech, volume: v, target });
        events.trackAction(charName, null, speech, null, '');
        // Directed whisper (task-248): "whisper to <name>: text" reaches only
        // the target; the rest of the room sees the gesture, not the words.
        const directed = v === 'whisper' && target;
        const command = directed ? `whisper to ${target}: ${speech}` : `${v} ${speech}`;
        try {
            const data = await ApiClient.action(command, charName);
            const output = (data && data.output) || '';
            const blocked = (data && data.success === false) ||
                /no sound comes out|can't move or act|can't do that/i.test(output);
            if (blocked) {
                events.log(`🔇 ${player.name}: ${output.trim() || 'cannot speak.'}`, 'error-msg');
            } else if (directed) {
                // task-340: whispered lines get a distinct locked row in the stream.
                events.log(`🔒 ${player.name} → ${target}: "${speech}"`, "msg-whisper");
            } else {
                events.log(`[${player.name}] ${ActionNormalizer.volVerb(v)}: "${speech}"`, "msg-speech");
            }
            worldState.fetch();
        } catch (err) {
            events.log(`[${player.name}] ${ActionNormalizer.volVerb(v)}: "${speech}"`, "msg-speech");
            worldState.fetch();
        }
    }

    async _performEmote(charName, emote) {
        try {
            const emoteResult = await ApiClient.emote(charName, emote);
            if (emoteResult?.description) {
                events.log(emoteResult.description, 'msg-emote');
                events.trackAction(charName, '', null, `emote: ${emote}`, emoteResult.description);
            }
        } catch (emoteErr) {
            events.log(`Emote error: ${emoteErr.message}`, 'error-msg');
        }
    }

    _storeReactionMemory(charName, memory, feltEmotion = null) {
        if (!memory?.text) return;
        const entityId = this._currentAreaEntityId(charName);
        const tick = worldState.data?.time_ticks || 0;
        const normalized = memory.text.trim().toLowerCase();
        const player = worldState.players?.[charName];
        const duplicate = (player?.memories || []).some(existing => {
            const sameText = (existing.text || '').trim().toLowerCase() === normalized;
            const sameTick = Math.abs((existing.tick || 0) - tick) <= 1;
            return sameText && sameTick;
        });
        if (duplicate) return;
        AgentMemory.storeMemory(charName, memory.text, memory.importance, 'reaction', tick, entityId ? [entityId] : [], memory.tags, feltEmotion, memory.emotions || null);
    }

    /**
     * Fire-and-forget spike of the character's affect map from an LLM-declared
     * feeling (task-96). Silent no-op when absent/malformed or backend misses.
     */
    _applyFeltEmotion(charName, emotion) {
        if (!emotion?.label || !worldState.players?.[charName]) return null;
        // task-350: when the feeling is TOWARD a specific person, pass `toward`
        // so the backend records it as an experience (felt_toward) and so
        // relationships/feelings can change toward that person. Otherwise it's
        // a global affect spike (legacy).
        const body = { emotion: emotion.label, intensity: Math.max(1, Math.min(10, emotion.intensity)) };
        if (emotion.toward) body.toward = emotion.toward;
        else body.delta = body.intensity * 1.5;
        try {
            return fetch(`/api/players/${encodeURIComponent(charName)}/emotions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            }).catch(() => {});
        } catch (e) { return null; }
    }

    /** task-350: record names the agent confirmed/deduced this turn (heard,
     *  name tag, sign, document, deduction). Fire-and-forget; engine validates
     *  they are real present players so the agent cannot invent a name tag. */
    _learnNames(charName, learnedNames) {
        if (!learnedNames?.length || !worldState.players?.[charName]) return;
        try {
            return fetch(`/api/players/${encodeURIComponent(charName)}/names`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ names: learnedNames })
            }).catch(() => {});
        } catch (e) { return null; }
    }

    /**
     * Human turn: pause the run loop and let the human compose their turn
     * through the scene-first panel (task-333). Mirrors the agent loop's
     * think→act→react shape (task-334): compose → [dash burst] → react →
     * pass. Execution rides the SAME pipeline an agent uses (_speakLine /
     * ApiClient.action / _performEmote / _storeReactionMemory). Targets the
     * character via setActivePlayer for clean multi-human handoff (task-245).
     */
    async _humanTurn(charName) {
        await ApiClient.setActivePlayer(charName);
        await worldState.fetch();
        const state = worldState.data;
        const player = state?.players?.[charName];
        if (!state || !player) {
            events.log(`⚠️ Human character "${charName}" not found.`, 'error-msg');
            return this._endTurnEarly(null);
        }
        if (state.scenario_ended) {
            events.log("🏁 Scenario ended via trigger.", "system-msg");
            if (state._restart_requested) {
                events.log("🔄 Restarting scenario...", "system-msg");
                await ApiClient.resetWorld();
                await worldState.fetch();
                events.log("✅ Scenario restarted.", "system-msg");
                VW?.ui?.renderAll?.(worldState.data);
                return;
            }
            this.stop();
            return;
        }
        const reply = await HumanTurnComposer.request(charName);

        if (config.running && config.turnBased && this.turnQueue.length === 0) {
            this.stop(); return;
        }
        let lastResult = '';
        if (!reply || reply.endTurn) {
            events.log(`🔜 ${charName} passed ${_possessivePronoun(charName)} turn.`, 'system-msg');
        } else {
            lastResult = await this._executeHumanReply(charName, player, reply);
            // Dash burst (task-334): dashing grants ONE more action slot
            // before the react step — unless the dash itself failed.
            const dashFailed = /locked|blocked|can't|could not|fail/i.test(lastResult);
            if (reply.action && reply.action.startsWith('dash ') && !dashFailed) {
                const burstReply = await HumanTurnComposer.request(charName, { burst: true, lastResult });
                if (burstReply && !burstReply.endTurn) {
                    const burstResult = await this._executeHumanReply(charName, player, burstReply);
                    if (burstResult) lastResult = burstResult;
                    if (burstReply.memory?.text) this._storeReactionMemory(charName, burstReply.memory);
                }
            }
            // Deterministic auto-memory (task-334): one instant, LLM-free
            // line per human turn so journaling is never the only record.
            const areaName = worldState.players?.[charName]?.current_area || '';
            const memoryBits = [
                reply.action ? `did ${reply.action}` : '',
                reply.speech ? `said "${reply.speech}"` : '',
            ].filter(Boolean).join(' and ');
            if (memoryBits) {
                this._storeReactionMemory(charName, {
                    text: `${memoryBits} (${areaName}, tick ${worldState.tick})`,
                    importance: 4,
                });
            }
            // React phase: say/emote/memory bound to the result — no second
            // world interaction, or the turn would never end.
            const reactReply = await HumanTurnComposer.react(charName, lastResult);
            if (reactReply && !reactReply.endTurn) {
                if (reactReply.speech) {
                    await this._speakLine(charName, player, reactReply.speech, reactReply.speechVolume, reactReply.target);
                }
                if (reactReply.emote) {
                    await this._performEmote(charName, reactReply.emote);
                }
                if (reactReply.memory?.text) {
                    this._storeReactionMemory(charName, reactReply.memory);
                }
            }
        }
        // Turn handoff is a turn-based concept (task-333 browser-test fix):
        // outside turn-based mode the human keeps control — no roster
        // rotation, the run loop just continues from here.
        if (config.running && config.turnBased && this.turnQueue.length > 0) {
            await TurnQueue.advance();
            if (worldState.data) VW?.ui?.renderAll(worldState.data);
        }
    }

    /**
     * Execute one human reply (speech → action → emote) through the agent
     * pipeline. Returns the action's result text (for the react phase).
     */
    async _executeHumanReply(charName, player, reply) {
        if (reply.speech) {
            await this._speakLine(charName, player, reply.speech, reply.speechVolume, reply.target);
        }
        // task-xxx: emote renders before the action result (consistent with the
        // agent decide phase) so the stream reads gesture → outcome.
        if (reply.emote) {
            await this._performEmote(charName, reply.emote);
        }
        let resultText = '';
        if (reply.action) {
            events.logPhase(charName, 'act', reply.action);
            if (!reply.action.startsWith('speak ')) events.log(`[Action] ${reply.action}`, "msg-action");
            try {
                const data = await ApiClient.action(reply.action, charName);
                if (data?.scenario_ended) {
                    events.log("🏁 Scenario ended via trigger.", "system-msg");
                    if (data?._restart_requested) {
                        events.log("🔄 Restarting scenario...", "system-msg");
                        await ApiClient.resetWorld();
                        await worldState.fetch();
                        events.log("✅ Scenario restarted.", "system-msg");
                        VW?.ui?.renderAll?.(worldState.data);
                    }
                } else {
                    const output = data?.output || '';
                    if (data?.system_messages) {
                        data.system_messages.forEach(systemMessage => events.log(systemMessage, 'system-msg'));
                    }
                    if (output && !output.includes('says:')) {
                        if (output.includes('ValueError')) events.log(output, 'error-msg');
                        else events.log(output, 'msg-result', { outcome: data?.success !== false ? 'success' : 'failure' });
                    }
                    config.lastActionResult[charName] = output;
                    events.trackAction(charName, '', null, reply.action, output);
                    const area = worldState.players?.[charName]?.current_area;
                    if (area) config.lastRoom[charName] = area;
                    resultText = output;
                }
                worldState.fetch();
            } catch (err) {
                events.log(`Action error: ${err.message}`, 'error-msg');
                worldState.fetch();
                resultText = err.message;
            }
        }
        return resultText;
    }

    async step() {
        if (this._checkCancel()) return;
        config.busy = true;
        let charName = config.controllingPlayer;
        if (config.turnBased && this.turnQueue.length === 0) TurnQueue.initialize();
        if (config.turnBased && this.turnQueue.length === 0) {
            config.running = false; config.busy = false; VW?.ui?.updateButtons();
            VW?.ui?.showPlayPause(true, false);
            VW?.ui?.setStatus("Stopped.", "error");
            events.log("⏹️ All dead.", "system-msg"); this.stop(); return;
        }
        if (config.turnBased && this.turnQueue.length > 0) { const ctc = TurnQueue.getCurrentCharacter(); if (ctc && charName !== ctc) charName = ctc; }
        if (charName && worldState.players?.[charName]?.state === 'dead' && !config.ghostMode) {
            return this._endTurnEarly(`⏭️ ${charName} dead.`);
        }
        // Human-controlled characters: pause the loop and let the human compose
        // their turn through the structured composer (task-244). This await
        // blocks the whole step until they act or skip, so the run loop waits
        // for them instead of skipping past (task-245: each human is prompted in
        // queue order, targeted via setActivePlayer).
        if (charName && !events.isAutonomous(charName)) {
            // The human turn is handled before the agent try/finally below, so
            // busy must be cleared here or it stays true forever (making every
            // later Step/Run report "Already running."). finally covers errors too.
            try {
                return await this._humanTurn(charName);
            } finally {
                config.busy = false; VW?.ui?.updateButtons();
                VW?.ui?.setStatus(config.running ? "Waiting..." : "Idle.", "info");
            }
        }
        if (this._rateLimiter.msUntilAvailable() > 0) {
            const sec = Math.ceil(this._rateLimiter.msUntilAvailable() / 1000);
            events.log(`⏱️ Cooldown ${sec}s...`, 'system-msg');
            VW?.ui?.syncRateLimitDisplay();
            while (this._rateLimiter.msUntilAvailable() > 0) {
                if (this._checkCancel()) {
                    VW?.ui?.stopRateLimitMonitor();
                    return;
                }
                await new Promise(resolve => setTimeout(resolve, 1000));
                VW?.ui?.syncRateLimitDisplay();
            }
        }
        this._rateLimiter.waitMs();
        VW?.ui?.updateButtons();
        if (!charName) {
            config.busy = false; VW?.ui?.updateButtons(); VW?.ui?.setStatus("Idle.", "info");
            return this._endTurnEarly("⚠️ No agent selected. Click an agent in the list first.", "system-msg");
        }

        let history = this.getHistory(charName);
        if (!config.lastActionResult[charName]) config.lastActionResult[charName] = '';
        VW?.ui?.setStatus("Thinking...", "info");

        try {
            if (!config.apiKey && !config.apiBase?.includes('localhost') && !config.apiBase?.includes('127.0.0.1')) { events.log("No API key.", "error-msg"); config.running = false; VW?.ui?.updateButtons(); return; }
            if (!config.model) { events.log("No model.", "error-msg"); config.running = false; VW?.ui?.updateButtons(); return; }
            if (!config.controllingPlayer) { events.log("No char.", "error-msg"); config.running = false; VW?.ui?.updateButtons(); return; }
            await ApiClient.setActivePlayer(config.controllingPlayer);
            if (this._checkCancel()) return;
            await worldState.fetch();
            delete this.characterHistories[charName];
            history = this.getHistory(charName);
            if (worldState.data?.scenario_ended) {
                events.log("🏁 Scenario ended via trigger.", "system-msg");
                if (worldState.data?._restart_requested) {
                    events.log("🔄 Restarting scenario...", "system-msg");
                    await ApiClient.resetWorld();
                    await worldState.fetch();
                    events.log("✅ Scenario restarted.", "system-msg");
                    VW?.ui?.renderAll?.(worldState.data);
                } else {
                    this.stop();
                }
                return;
            }
            const state = worldState.data;
            if (!state?.players?.[config.controllingPlayer]) { events.log("Char not found.", "error-msg"); config.running = false; VW?.ui?.updateButtons(); return; }

            const player = state.players?.[charName];

            // NPC turns: simple NPCs act via backend tick_turn — surface what
            // they did from the turn_events (or report they did nothing).
            if (player?.simple_npc) {
                config.busy = false; VW?.ui?.updateButtons();
                if (config.running && config.turnBased && this.turnQueue.length > 0) {
                    await TurnQueue.advance();
                    if (worldState.data) VW?.ui?.renderAll(worldState.data);
                }
                this._logActorTurnEvents(charName);
                return;
            }

            const currentArea = state.areas[state.current_area] || null;
            const lastResult = config.lastActionResult[charName] || '';

            if (AgentState.isBusy(charName, lastResult, player)) {
                const busyPlayer = worldState.players?.[charName];
                const act = busyPlayer?.activity;
                const busyAct = act?.type || (busyPlayer?.state && busyPlayer.state !== 'awake' ? busyPlayer.state : 'busy');
                let detail = '';
                if (act && act.duration_ticks != null) {
                    const remaining = Math.max(0, (act.duration_ticks || 0) - (act.elapsed_ticks || 0));
                    detail = ` — ${remaining} tick${remaining === 1 ? '' : 's'} left`;
                } else if (act) {
                    detail = " — no set end ('wake' stops it)";
                }
                return this._endTurnEarly(`⏳ ${charName} is ${busyAct}${detail}...`, 'system-msg');
            }

            // Unconscious check — skip actions, character cannot think or act
            if (player.state === 'unconscious') {
                const { message: unconsciousMsg } = AgentState.markUnconscious(charName, player, worldState.data, worldState);
                if (unconsciousMsg) events.log(unconsciousMsg, 'system-msg');
                return this._endTurnEarly(null);
            }
            // Just woke up from unconsciousness — skip this turn to let Energy stabilize
            const wakeMsg = AgentState.clearUnconscious(charName, player);
            if (wakeMsg) {
                events.log(wakeMsg, 'system-msg');
                AgentMemory.storeMemory(charName, `You wake up, groggy and disoriented, your Energy restored to ${player.vitals?.Energy || 'some'}%.`, 7, 'thought');
                return this._endTurnEarly(null);
            }
            if (!player) { config.busy = false; VW?.ui?.updateButtons(); return; }

            // Reflection every 5 turns
            if (this.turnNumber > 0 && this.turnNumber % 5 === 0 && config.reactiveMode) {
                AgentMemory.reflect(charName).catch(() => {});
            }

            const roomParts = PromptBuilder.buildRoomContextParts(state, charName, player, currentArea);
            const vitalsNL = PromptBuilder.describeVitals(player, state, charName);
            const emotionNL = PromptBuilder.buildEmotionContext(player);
            const insanityNL = PromptBuilder.buildInsanityContext(player);
            const relationshipNL = PromptBuilder.buildRelationshipContext(player, charName);
            const memoryNL = await PromptBuilder.buildMemoryContext(charName, { report: true });

            if (config.reactiveMode) {
                events.logPhase(charName, 'think', 'observing');
                VW?.ui?.setStatus("Thinking...", "info");
                const turnEvents = state.turn_events || [];

                // Threat check before OBSERVE — so the character naturally notices the threat
                const preObserveThreat = ThreatDetector.getThreatAlert(charName, player, currentArea, turnEvents);
                const threatNames = preObserveThreat
                    ? (preObserveThreat.match(/⚠️ IMMEDIATE DANGER: ([^.]+)/)?.[1]?.trim() || '')
                    : '';
                const threatObservationNote = threatNames
                    ? `\n⚠️ ${threatNames} — something about this person sets every instinct on edge. The blood, the emptiness in their eyes, the way they move. They are not here to help you.`
                    : '';

                // Observe uses the SAME full room context as decide/react, so the
                // agent always sees items, people, exits, and a WITNESSED section
                // (with fallback).
                const observeParts = Object.assign({}, roomParts, { extraNote: threatObservationNote || '' });

                // Threat-aware replan check — before deciding so the plan is fresh
                const threatAlert = ThreatDetector.getThreatAlert(charName, player, currentArea, turnEvents);
                const needsReplan = PlanTracker.shouldReplan(charName, this.turnNumber, threatAlert, player?.vitals);
                if (needsReplan) {
                    const plan = await PlanManager.generate(charName);
                    if (plan && plan.length > 0) {
                        PlanTracker.setPlan(charName, plan);
                        // task-340: crisis replans surface WHY (critical need or threat).
                        const crisisList = PlanTracker.criticalNeeds(player?.vitals);
                        const why = threatAlert ? 'threat detected' : (crisisList[0] || 'plan stalled');
                        events.log(`⚠️ ${charName} replanned — ${why}: ${plan.join(' → ')}`, 'msg-crisis');
                    }
                }
                if (this._checkCancel()) return;

                // CONVERSATION-STYLE LOOP: think + decide in ONE call, and the
                // prompt + response are pushed into the per-character history
                // ([system, user, assistant, ...]) so the agent remembers its own
                // earlier words across phases and turns — no more self-contradiction
                // between decide and react (e.g. changing a favorite color).
                const thinkDecidePrompt = PromptBuilder.buildReactionPrompt(player, observeParts, vitalsNL, emotionNL, relationshipNL, memoryNL, lastResult, false, true);
                const combinedPrompt = threatAlert ? threatAlert + '\n\n' + thinkDecidePrompt : thinkDecidePrompt;
                history.push({ role: 'user', content: combinedPrompt });
                const combinedResponse = await this._callLLMMessages(history, 'think-decide');
                history.push({ role: 'assistant', content: combinedResponse || '' });
                if (combinedResponse === null) {
                    events.log(`❌ LLM call failed for ${charName} (think/decide phase) — stopping agent`, 'error-msg');
                    VW?.ui?.setStatus("LLM Error - Stopped", "error");
                    config.running = false; return;
                }
                events.logPhase(charName, 'decide', 'deciding');
                VW?.ui?.setStatus("Deciding...", "info");
                let parsedDecide = ResponseParser.parseReaction(combinedResponse) ?? {inner:'',speech:null,speechVolume:'say',action:'',emote:null,memory:null,emotion:null,parseError:null};
                if (parsedDecide.parseError) parsedDecide = await this._retryOnceOnParseError(charName, history, 'think-decide', ResponseParser.parseReaction, parsedDecide);
                if (parsedDecide.parseError) {
                    events.logParseError(charName, 'think-decide', parsedDecide.parseError, combinedResponse);
                }
                let { inner, speech: decisionSpeech, speechVolume, action: finalAction, emote: decisionEmote, target: decisionTarget } = parsedDecide;
                this._applyFeltEmotion(charName, parsedDecide.emotion);
                this._learnNames(charName, parsedDecide.learnedNames);
                if (inner) { events.logThought(charName, inner); }
                events.trackAction(charName, inner, null, '', '');
                if (!config.lastRoom[charName] && player.current_area) config.lastRoom[charName] = player.current_area;
                let actionRejected = '';
                if (finalAction && !ActionNormalizer.isValidAction(finalAction, charName)) {
                    events.log(`⚠️ ${charName} invalid action: "${finalAction}" — skipping`, 'error-msg');
                    actionRejected = finalAction;
                    finalAction = '';
                }

                if (decisionSpeech) {
                    await this._speakLine(charName, player, decisionSpeech, speechVolume, decisionTarget);
                }

                // task-xxx: the act emote lands BEFORE the action's result so the
                // stream reads gesture → outcome instead of outcome → gesture.
                if (decisionEmote) {
                    await this._performEmote(charName, decisionEmote);
                }

                let actionResult = '';
                let actionSucceeded = true;
                if (actionRejected) {
                    actionResult = this._surfaceRejectedAction(charName, actionRejected);
                    actionSucceeded = false;
                    events.log(actionResult, 'msg-result', { outcome: 'failure' });
                }
                if (finalAction) {
                    events.logPhase(charName, 'act', finalAction);
                    const noopAction = this._isNoopAction(finalAction);
                    if (!finalAction.startsWith('speak ') && !noopAction) events.log(`[Action] ${finalAction}`, "msg-action");
                    if (this._checkCancel()) return;
                    if (noopAction) {
                        actionResult = 'You stand still and wait, watching and listening.';
                        actionSucceeded = true;
                        events.log(actionResult, 'msg-result', { outcome: 'minor' });
                    } else try {
                        const data = await ApiClient.action(finalAction, charName);
                        if (data?.scenario_ended) {
                            events.log("🏁 Scenario ended via trigger.", "system-msg");
                            if (data?._restart_requested) {
                                events.log("🔄 Restarting scenario...", "system-msg");
                                await ApiClient.resetWorld();
            await worldState.fetch();
            delete this.characterHistories[charName];
            history = this.getHistory(charName);
                                events.log("✅ Scenario restarted.", "system-msg");
                                VW?.ui?.renderAll?.(worldState.data);
                            } else { this.stop(); }
                            return;
                        }
                        actionResult = data?.output || '';
                        actionSucceeded = data?.success !== false;
                        PlanTracker.trackStep(charName, finalAction, actionResult, actionSucceeded);
                        let outputText = actionResult;
                        if (data?.system_messages) {
                            data.system_messages.forEach(systemMessage => events.log(systemMessage, 'system-msg'));
                        }
                        const narrationMode = window.narrationUI?.getMode();
                        let narratedText = null;
                        if (narrationMode === 'ai' && config.apiKey && config.model) {
                            narratedText = await window.narrationUI.getNarratedActionResult(outputText, charName, finalAction);
                            if (narratedText) outputText = narratedText;
                        }
                        config.lastActionResult[charName] = outputText;
                        // task-340: results are first-class rows — outcome-tinted,
                        // never card-breaking; AI-narrated substitutions are marked.
                        if (!outputText.includes('says:')) {
                            if (narratedText) events.log(outputText, 'msg-narrated');
                            else if (outputText.includes('ValueError')) events.log(outputText, 'error-msg');
                            else events.log(outputText, 'msg-result', { outcome: actionSucceeded ? 'success' : 'failure' });
                        }
                        events.trackAction(charName, '', null, finalAction, outputText);
                        const area = worldState.players?.[charName]?.current_area;
                        if (area) config.lastRoom[charName] = area;
                        worldState.fetch();
                    } catch (err) { events.log(`Action error: ${err.message}`, 'error-msg'); actionResult = `Error: ${err.message}`; }
                }

                // ── Invalid-action auto-retry (task-361) ──
                // One same-turn retry when the agent's action failed and the
                // setting is on. Not a new turn: no step/plan advance, and the
                // retry outcome becomes the actionResult used by the react phase.
                if (!actionSucceeded && config.autoRetryInvalid && actionResult) {
                    const retry = await this._autoRetryInvalidAction(charName, player, history, actionRejected || finalAction, actionResult, memoryNL);
                    if (retry) {
                        finalAction = retry.finalAction;
                        actionResult = retry.actionResult;
                        actionSucceeded = retry.actionSucceeded;
                    }
                }

                // ── Chained follow-up (task-104) ──
                // Dash→go was the original; generalized to verb families:
                // lead → go/approach/release, grab → approach/release.
                if (finalAction && actionResult && actionSucceeded) {
                    const chainVerb = finalAction.split(/\s+/)[0].toLowerCase();
                    const allowed = CHAIN_RULES[chainVerb];
                    if (allowed) {
                        actionResult = await this._runChainFollowUp(charName, player, actionResult, history, chainVerb, allowed);
                    }
                }

                if (actionResult) {
                    const isNowResting = actionResult.toLowerCase().includes('you rest');
                    const isUnconscious = actionResult.toLowerCase().includes('while unconscious');
                    if (isUnconscious) {
                        config.lastActionResult[charName] = actionResult;
                    } else if (!isNowResting) {
                        await worldState.fetch();
                        const freshState = worldState.data;
                        const freshPlayer = freshState?.players?.[charName] || player;
                        const freshRoom = freshState?.areas?.[freshState.current_area] || currentArea;
                        events.logPhase(charName, 'react', 'reacting');
                        VW?.ui?.setStatus("Reacting...", "info");
                        const movedViaDash = finalAction.split(/\s+/)[0].toLowerCase() === 'dash';
                        const tickNum = worldState.data?.time_ticks ?? 0;
                        const areaName = freshRoom?.name || freshState?.current_area || '';
                        const reactContext = movedViaDash
                            ? `[Tick ${tickNum}] You just sprinted and are now in ${areaName} — react to arriving here.`
                            : `[Tick ${tickNum}] You are still in ${areaName}. Your surroundings are unchanged — see your observation above in this conversation.`;
                        const reactPrompt = PromptBuilder.buildResultReactionPrompt(charName, freshPlayer, reactContext, vitalsNL, emotionNL, relationshipNL, inner, finalAction || '', actionResult, memoryNL, decisionSpeech);
                        history.push({ role: 'user', content: reactPrompt });
                        const reactResponse = await this._callLLMMessages(history, 'result-reaction');
                        history.push({ role: 'assistant', content: reactResponse || '' });
                        if (reactResponse === null) {
                            events.log(`❌ LLM call failed for ${charName} (reaction phase) — stopping agent`, 'error-msg');
                            VW?.ui?.setStatus("LLM Error - Stopped", "error");
                            config.running = false; return;
                        }
                        let parsedReact = ResponseParser.parseResultReaction(reactResponse) ?? {inner:'',speech:null,speechVolume:'say',emote:null,memory:null,emotion:null,parseError:null};
                        if (parsedReact.parseError) parsedReact = await this._retryOnceOnParseError(charName, history, 'result-reaction', ResponseParser.parseResultReaction, parsedReact);
                        if (parsedReact.parseError) {
                            events.logParseError(charName, 'result-reaction', parsedReact.parseError, reactResponse);
                        }
                        const { inner: reactionInner, speech: reactionSpeech, speechVolume: reactionVolume, emote: reactionEmote, memory: reactionMemory } = parsedReact;
                        if (reactionInner) { events.logThought(charName, reactionInner); }
                        this._applyFeltEmotion(charName, parsedReact.emotion);
                        this._learnNames(charName, parsedReact.learnedNames);
                        if (reactionSpeech) { await this._speakLine(charName, player, reactionSpeech, reactionVolume); }
                        if (reactionEmote) {
                            await this._performEmote(charName, reactionEmote);
                        }
                        this._storeReactionMemory(charName, reactionMemory, parsedReact.emotion);
                        events.trackAction(charName, reactionInner, reactionSpeech, null, '');
                    } else {
                        events.trackAction(charName, '', null, finalAction, actionResult);
                    }
                }
            } else {
                // ── Non-reactive (combined) mode ──
                VW?.ui?.setStatus("Thinking...", "info");
                const reactionPrompt = PromptBuilder.buildReactionPrompt(player, roomParts, vitalsNL, emotionNL, relationshipNL, memoryNL, lastResult, true);

                history.push({ role: 'user', content: reactionPrompt });
                const reactionResponse = await this._callLLMMessages(history, 'combined');
                history.push({ role: 'assistant', content: reactionResponse || '' });

                if (reactionResponse === null) {
                    events.log(`❌ LLM call failed for ${charName} — stopping agent`, 'error-msg');
                    VW?.ui?.setStatus("LLM Error - Stopped", "error");
                    config.running = false; return;
                }
                const parsedNonReactive = ResponseParser.parseReaction(reactionResponse) ?? {inner:'',speech:null,speechVolume:'say',action:'',emote:null,memory:null,emotion:null,parseError:null};
                if (parsedNonReactive.parseError) {
                    events.logParseError(charName, 'combined', parsedNonReactive.parseError, reactionResponse);
                }
                let { inner, speech, speechVolume, action, emote: reactionEmote, memory: reactionMemory, target: speechTarget } = parsedNonReactive;
                if (inner) { events.log(`[${player.name} inner] ${inner}`, "msg-thought"); }
                this._applyFeltEmotion(charName, parsedNonReactive.emotion);
                this._learnNames(charName, parsedNonReactive.learnedNames);
                if (speech) { await this._speakLine(charName, player, speech, speechVolume, speechTarget); }
                this._storeReactionMemory(charName, reactionMemory, parsedNonReactive.emotion);
                events.trackAction(charName, inner, speech, null, '');
                if (!config.lastRoom[charName] && player.current_area) config.lastRoom[charName] = player.current_area;
                const finalAction = action;
                const noopAction = this._isNoopAction(finalAction);
                if (finalAction && !finalAction.startsWith('speak ') && !noopAction) events.log(`[Action] ${finalAction}`, "msg-action");
                if (finalAction && noopAction) {
                    config.lastActionResult[charName] = 'You stand still and wait, watching and listening.';
                    events.trackAction(charName, inner, speech, 'wait', 'waits.');
                } else if (finalAction) {
                    ApiClient.action(finalAction, charName).then(async (data) => {
                        const output = data?.output || data?.error || '';
                        if (data?.system_messages) {
                            data.system_messages.forEach(systemMessage => events.log(systemMessage, 'system-msg'));
                        }
                        config.lastActionResult[charName] = output;
                        if (output && !output.includes('says:')) events.log(output, output.includes('ValueError') ? 'error-msg' : 'system-msg');
                        events.trackAction(charName, '', null, finalAction, output);
                        const area = worldState.players?.[charName]?.current_area;
                        if (area) config.lastRoom[charName] = area;
                        worldState.fetch();

                        if (reactionEmote && data?.success !== false) {
                            await this._performEmote(charName, reactionEmote);
                        }
                    }).catch(err => { events.log(`Action error: ${err.message}`, 'error-msg'); worldState.fetch(); });
                }
            }

    } finally {
            config.busy = false; VW?.ui?.updateButtons();
            VW?.ui?.syncRateLimitDisplay();
            VW?.ui?.setStatus(config.running ? "Waiting..." : "Idle.", "info");
        }
        if (config.running && config.turnBased && this.turnQueue.length > 0) {
            await TurnQueue.advance();
            if (worldState.data) VW?.ui?.renderAll(worldState.data);
        }
    }
    async stepOnce() {
        if (config.busy || config.running) { events.log("Already running.", "system-msg"); return; }
        if (config.turnBased && this.turnQueue.length === 0) TurnQueue.initialize();
        if (config.turnBased && this.turnQueue.length > 0) {
            config.controllingPlayer = TurnQueue.getCurrentCharacter();
        }
        await this.step();
        if (config.turnBased && this.turnQueue.length > 0) {
            await TurnQueue.advance();
            config.controllingPlayer = TurnQueue.getCurrentCharacter();
            if (worldState.data) VW?.ui?.renderAll(worldState.data);
        } else if (!config.turnBased && config.controllingPlayer) {
            // No turn-based mode: the stepped character's turn is one full
            // turn — end it so the clock advances and new-turn effects run
            // (behave like turn-based with a single-character queue).
            await TurnQueue.endTurn();
            this._logActorTurnEvents(config.controllingPlayer);
            if (worldState.data) VW?.ui?.renderAll(worldState.data);
        }
    }
    async start() {
        if (config.turnBased) { this.characterHistories = {};
            if (this.turnQueue.length === 0) { TurnQueue.initialize(); }
            if (this.turnQueue.length === 0) { events.log("No characters.", "error-msg"); return; }
            config.controllingPlayer = this.turnQueue[this.currentTurnIndex] || this.turnQueue[0];
        }
        else { if (!config.controllingPlayer) { events.log("No character selected.", "error-msg"); return; } }
        config.stepsRun = 0;
        const maxInput = document.getElementById('sim-max-steps');
        config.maxSteps = maxInput ? parseInt(maxInput.value) || 0 : 0;
        config.running = true; VW?.ui?.updateButtons(); VW?.ui?.setStatus("Running...", "info"); VW?.ui?.showPlayPause(false, true);
        VW?.ui?.updateMaxStepsDisplay();
        // A4: a stop/cancel from a PREVIOUS run must not ghost into this one
        // ("Step cancelled." firing on a fresh ▶ was the stale flag leaking).
        this._cancelRequested = false;
        (async () => { while (config.running) {
            if (config.simultaneousMode) { await this._simultaneousStep(); }
            else { await this.step(); }
            if (this._cancelRequested) { this.cancel(); break; }
            if (!config.turnBased && config.controllingPlayer && !config.simultaneousMode) { await TurnQueue.endTurn(); this._logActorTurnEvents(config.controllingPlayer); if (worldState.data) VW?.ui?.renderAll(worldState.data); }
            config.stepsRun++; const turnsRun = config.turnBased ? Math.floor(config.stepsRun / Math.max(1, this.turnQueue.length)) : config.stepsRun; VW?.ui?.updateMaxStepsDisplay(); if (config.maxSteps > 0 && turnsRun >= config.maxSteps) { this.stop(`⏹️ Run complete — ${config.maxSteps} turns done. Press ▶ to continue.`); break; }
            await new Promise(resolve => setTimeout(resolve, config.simultaneousMode ? 800 : 2000));
        } })();
    }

    /**
     * task-101 experimental simultaneous mode: every autonomous character has
     * its own act countdown (derived from traits/vitals — high Social acts
     * more often, impatient/sprinter faster, exhausted slower). Each engine
     * tick decrements all countdowns; the first character ready processes its
     * full turn through the normal per-character pipeline, then the countdown
     * restarts. Chaos by design — sequential mode is untouched.
     */
    async _simultaneousStep() {
        if (!worldState.data) await worldState.fetch();
        const players = worldState.data?.players || {};
        const names = Object.keys(players);
        for (const name of names) {
            if (this._simCountdowns[name] === undefined) {
                this._simCountdowns[name] = this._cooldownFor(players[name]);
            }
        }
        for (const name of names) {
            if (this._simCountdowns[name] > 0) this._simCountdowns[name] -= 1;
        }
        const ready = names.filter(name => {
            const p = players[name];
            if (!p) return false;
            if (!events.isAutonomous(name)) return false;   // humans compose their own turns
            if (p.state === 'dead' && !config.ghostMode) return false;
            return this._simCountdowns[name] <= 0;
        });
        if (!ready.length) return;
        const charName = ready[0];
        this._simCountdowns[charName] = this._cooldownFor(players[charName]);
        const prevControlling = config.controllingPlayer;
        config.controllingPlayer = charName;
        try {
            await this.step();
        } finally {
            config.controllingPlayer = prevControlling;
        }
    }

    /**
     * Act countdown for simultaneous mode: Social speeds it up, traits and
     * exhaustion slow it down. Returns a tick count (3–15).
     */
    _cooldownFor(player) {
        if (!player) return 8;
        const traits = player.traits || {};
        let c = 8 + Math.round((50 - (player.vitals?.Social ?? 50)) / 25);
        if (traits.impatient) c -= 2;
        if (traits.patient) c += 2;
        if (traits.sprinter) c -= 1;
        if ((player.vitals?.Energy ?? 100) < 35) c += 1;
        return Math.max(3, Math.min(15, c));
    }
    stop(reason = 'Agent stopped.') {
        config.running = false; VW?.ui?.updateButtons(); events.log(reason, 'system-msg');
        VW?.ui?.setStatus("Idle.", "info"); VW?.ui?.showPlayPause(true, false);
        VW?.ui?.updateMaxStepsDisplay();
    }
    reset() {
        this.stop();
        PlanTracker.resetAll();
        this.characterHistories = {};
        config.lastActionResult = {};
        config.lastRoom = {};
        this.turnQueue = [];
        this.currentTurnIndex = 0;
        this.turnNumber = 0;
        this.initiativeRolls = {};
    }
    nudge(charName, text) {
        if (!text || !charName) return;
        this.getHistory(charName).push({ role: 'user', content: `[Sensory event] ${text}` });
        events.log(`[Nudge -> ${charName}] ${text}`, 'system-msg');
    }

    /**
     * Give the agent feedback when its chosen action is rejected, instead of
     * silently dropping it. The rejection lands in lastActionResult (so DECIDE
     * sees it next turn) — no memory write: the hint is transient system
     * feedback, not something the character remembers.
     */
    _surfaceRejectedAction(charName, rejectedAction) {
        const text = `You try to ${rejectedAction}, but you can't do that.`;
        config.lastActionResult[charName] = text;
        return text;
    }

    /**
     * Invalid-action auto-retry (task-361): feed the failed action + reason
     * back to the agent and let it choose a different action ONCE, in the same
     * turn (no step/plan advance). Returns { finalAction, actionResult,
     * actionSucceeded } when a retry was performed, or null when there is
     * nothing to retry / the retry produced no valid action.
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {Array} history - Conversation history (mutated: retry prompt + response)
     * @param {string} failedAction - The action string that failed ('' if verb-rejected)
     * @param {string} failedResult - Result/error text from the failed action
     * @param {string} memoryNL - Memory context (parity with turn flow; unused here)
     * @returns {Promise<Object|null>} Retry outcome or null
     */
    async _autoRetryInvalidAction(charName, player, history, failedAction, failedResult, memoryNL) {
        const attempted = String(failedAction || '').trim() || '(invalid)';
        if (!failedResult || /while unconscious/i.test(failedResult)) return null;
        events.log(`↩️ ${charName}: auto-retry after failed action "${attempted}"`, 'system-msg');
        events.logPhase(charName, 'decide', 'auto-retry');
        VW?.ui?.setStatus?.('Retrying...', 'info');
        const prompt = PromptBuilder.buildRetryPrompt(attempted, failedResult);
        history.push({ role: 'user', content: prompt });
        const response = await this._callLLMMessages(history, 'auto-retry');
        if (response === null) {
            history.pop(); // LLM call failed — drop the retry prompt, keep history as before
            return null;
        }
        history.push({ role: 'assistant', content: response });
        let parsed = ResponseParser.parseReaction(response);
        if (parsed?.parseError) {
            parsed = await this._retryOnceOnParseError(charName, history, 'auto-retry', ResponseParser.parseReaction, parsed);
        }
        if (parsed?.parseError) {
            events.logParseError(charName, 'auto-retry', parsed.parseError, response);
            return null;
        }
        const retryAction = String(parsed?.action || '').trim();
        if (!retryAction || !ActionNormalizer.isValidAction(retryAction, charName)) {
            events.log(`⚠️ ${charName} retry chose an invalid action: "${retryAction || '(none)'}" — giving up`, 'error-msg');
            return null;
        }
        events.logPhase(charName, 'act', retryAction);
        events.log(`[Action] ${retryAction}`, 'msg-action');
        try {
            const data = await ApiClient.action(retryAction, charName);
            if (data?.scenario_ended) {
                events.log('🏁 Scenario ended via trigger.', 'system-msg');
                if (data?._restart_requested) {
                    events.log('🔄 Restarting scenario...', 'system-msg');
                    await ApiClient.resetWorld();
                    await worldState.fetch();
                    events.log('✅ Scenario restarted.', 'system-msg');
                } else { this.stop(); }
                return null;
            }
            const result = data?.output || '';
            const succeeded = data?.success !== false;
            config.lastActionResult[charName] = result;
            PlanTracker.trackStep(charName, retryAction, result, succeeded);
            events.trackAction(charName, '', null, retryAction, result);
            if (result && !result.includes('says:')) {
                events.log(result, result.includes('ValueError') ? 'error-msg' : 'msg-result', { outcome: succeeded ? 'success' : 'failure' });
            }
            return { finalAction: retryAction, actionResult: result, actionSucceeded: succeeded };
        } catch (err) {
            events.log(`Action error: ${err.message}`, 'error-msg');
            return { finalAction: retryAction, actionResult: `Error: ${err.message}`, actionSucceeded: false };
        }
    }

    /**
     * Chained follow-up (task-104 / task-104 generalization of dash→go):
     * after a successful action with a CHAIN_RULES entry, the agent gets one
     * immediate decision to continue with an allowed verb (go/approach/
     * release/wait). Returns the combined result text.
     */
    async _runChainFollowUp(charName, player, resultText, history, sourceVerb, allowedVerbs) {
        await worldState.fetch();
        const freshState = worldState.data;
        if (!freshState) return resultText;
        const freshPlayer = freshState?.players?.[charName] || player;
        const currentArea = freshState.areas?.[freshState.current_area] || null;
        const roomContext = PromptBuilder.buildRoomContext(freshState, charName, freshPlayer, currentArea);

        events.logPhase(charName, 'decide', `${sourceVerb} follow-up`);
        VW?.ui?.setStatus?.("Chain follow-up...", "info");
        const prompt = PromptBuilder.buildChainFollowUpPrompt(charName, roomContext, resultText, sourceVerb, allowedVerbs);
        history.push({ role: 'user', content: prompt });
        const response = await this._callLLMMessages(history, 'chain-follow-up');
        history.push({ role: 'assistant', content: response || '' });
        if (response === null) return resultText;

        const parsed = ResponseParser.parseReaction(response);
        if (parsed?.parseError) {
            events.logParseError(charName, 'chain-follow-up', parsed.parseError, response);
        }
        const followAction = parsed?.action || '';
        if (!followAction || this._checkCancel()) return resultText;

        const verb = followAction.split(/\s+/)[0].toLowerCase();
        const exitNames = Object.keys(currentArea?.exits || {}).map(e => e.toLowerCase());
        const allowed = allowedVerbs.includes(verb);
        const isExitName = exitNames.includes(followAction.toLowerCase());
        if (!ActionNormalizer.isValidAction(followAction, charName) || (!allowed && !isExitName)) return resultText;

        events.logPhase(charName, 'act', followAction);
        events.log(`[Action] ${followAction}`, "msg-action");
        try {
            const data = await ApiClient.action(followAction, charName);
            if (data?.scenario_ended) {
                events.log("🏁 Scenario ended via trigger.", "system-msg");
                if (data?._restart_requested) {
                    events.log("🔄 Restarting scenario...", "system-msg");
                    await ApiClient.resetWorld();
                    await worldState.fetch();
                    events.log("✅ Scenario restarted.", "system-msg");
                }
                return resultText;
            }
            const followResult = data?.output || '';
            events.trackAction(charName, '', null, followAction, followResult);
            if (followResult && !followResult.includes('says:')) {
                events.log(followResult, followResult.includes('ValueError') ? 'error-msg' : 'system-msg');
            }
            await worldState.fetch();
            return resultText + '\n' + followResult;
        } catch (err) {
            events.log(`${sourceVerb} follow-up error: ${err.message}`, 'error-msg');
            return resultText;
        }
    }

    /**
     * One automatic retry when a phase response came back as repaired/truncated
     * JSON (N1). The repair may have silently dropped fields (e.g. the emote);
     * re-asking once usually yields a complete reply. Never retries twice.
     */
    async _retryOnceOnParseError(charName, history, stepName, parser, parsed) {
        if (!parsed?.parseError || !history?.length) return parsed;
        events.log(`⚠️ ${charName}: ${stepName} response was repaired (truncated JSON) — retrying once.`, 'error-msg');
        history.pop(); // drop the broken assistant message so the retry isn't seeded by it
        const retried = await this._callLLMMessages(history, stepName);
        if (!retried) {
            history.push({ role: 'assistant', content: '' });
            return parsed;
        }
        history.push({ role: 'assistant', content: retried });
        const reparsed = parser(retried);
        if (reparsed && !reparsed.parseError) return reparsed;
        return parsed;
    }

    /** Thin wrapper: build message array and delegate to _callLLMMessages. */
    async _callLLM(prompt, history, stepName) {
        return this._callLLMMessages([...history, { role: 'user', content: prompt }], stepName);
    }

    // Send a pre-built message array as-is (system + accumulated history +
    // the new user message, already pushed by the caller). Pruned by the
    // context window when over the token/message limit.
    async _callLLMMessages(messages, stepName) {
        this.contextMgr.reset();
        messages.forEach((m,i) => this.contextMgr.addMessage(m, { importance: m.role==='system'?2:0, type: m.role, keepAlways: m.role==='system' }));
        const final = this.contextMgr.isOverLimit() ? this.contextMgr.prune(messages) : messages;
        // task-340: context pruning becomes a visible row instead of silent amnesia.
        const prunedCount = messages.length - final.length;
        if (prunedCount > 0) {
            const sig = `${stepName}:${prunedCount}`;
            if (this._lastPruneSig !== sig) {
                this._lastPruneSig = sig;
                events.log(`✂ Context pruned (${stepName}): dropped ${prunedCount} oldest messages`, 'msg-prune');
            }
        } else {
            this._lastPruneSig = null;
        }
        if (config.manualMode) {
            events.log(`✋ Manual mode — waiting for your response (${stepName})`, 'system-msg');
            return await this._showManualPrompt(final, stepName);
        }
        this._abortController = new AbortController();
        const streamId = `${stepName}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        events.startStreaming(streamId, stepName);
        const onChunk = c => events.appendStream(streamId, c);
        try {
            const r = await llmClient.chat(final, { streaming: config.streaming, max_tokens: config.maxTokens, signal: this._abortController.signal, onChunk, label: stepName });
            this._abortController = null;
            events.finishStreaming(streamId, r);
            return r;
        }
        catch (err) {
            if (err.name === 'AbortError') { events.finishStreaming(streamId); events.log('⏹️ LLM call cancelled.', 'system-msg'); return null; }
            events.log(`LLM error (${stepName}): ${err.message}`, "error-msg"); events.finishStreaming(streamId); return null;
        }
    }
}

const agent = new AgentEngine();
